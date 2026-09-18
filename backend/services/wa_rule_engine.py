"""
wa_rule_engine.py — A3 Well-Architected 啟發式規則引擎（純函式、可 PBT）。

解析 draw.io mxGraph XML 的 mxCell value／style，產出支柱分數與 findings。
不連 AWS API；不讀 DB。
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger("cloud360.wa_rule_engine")

RULE_PACK_VERSION = "wa-aws-mvp-1"
RULE_PACK_BY_PROVIDER = {
    "aws": "wa-aws-mvp-1",
    "gcp": "wa-gcp-mvp-1",
    "azure": "wa-azure-mvp-1",
}
SUPPORTED_PROVIDERS = frozenset(RULE_PACK_BY_PROVIDER)

PILLARS = (
    "operational_excellence",
    "security",
    "reliability",
    "performance_efficiency",
    "cost_optimization",
)

WEIGHTS: dict[str, float] = {
    "operational_excellence": 0.10,
    "security": 0.30,
    "reliability": 0.30,
    "performance_efficiency": 0.15,
    "cost_optimization": 0.15,
}

SEVERITY_DEDUCT = {
    "critical": 25,
    "high": 15,
    "warn": 8,
    "info": 2,
}


@dataclass
class Finding:
    code: str
    pillar: str
    severity: str
    title: str
    message: str
    node_ids: list[str] = field(default_factory=list)
    recommendation_hint: str = ""


@dataclass
class RuleResult:
    provider: str
    rule_pack_version: str
    pillar_scores: dict[str, float]
    overall_score: float
    weights_snapshot: dict[str, float]
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "rule_pack_version": self.rule_pack_version,
            "pillar_scores": self.pillar_scores,
            "overall_score": self.overall_score,
            "weights_snapshot": self.weights_snapshot,
            "findings": [asdict(f) for f in self.findings],
        }


def _cell_text(value: str | None) -> str:
    if not value:
        return ""
    # strip simple HTML tags from draw.io labels
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip().lower()


_XML_ILLEGAL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Named HTML entities that ElementTree rejects (only lt/gt/amp/apos/quot are predefined in XML).
_HTML_NAMED_ENTITY = re.compile(r"&([a-zA-Z][a-zA-Z0-9]+);")
_BARE_AMP = re.compile(r"&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#\d+|#x[0-9a-fA-F]+);)")
# `<` that is not a tag / PI / comment / CDATA start (common in agent labels: "A < B").
_BARE_LT = re.compile(r"<(?![/?!]?[A-Za-z_]|!(?:--|\[CDATA\[))")


def sanitize_mxgraph_xml(xml: str) -> str:
    """Make draw.io / agent XML parseable by ElementTree without changing structure.

    Draw.io labels and LLM-produced diagrams often contain bare ``&`` / ``<`` or
    HTML-only entities such as ``&nbsp;``, which raise ParseError (invalid token /
    undefined entity).
    """
    from html.entities import name2codepoint

    text = (xml or "").lstrip("\ufeff")
    text = _XML_ILLEGAL_CHARS.sub("", text)

    def _named_to_numeric(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in {"lt", "gt", "amp", "apos", "quot"}:
            return match.group(0)
        code = name2codepoint.get(name)
        if code is not None:
            return f"&#{code};"
        # Unknown entity → escape the ampersand so the rest stays literal text.
        return f"&amp;{name};"

    text = _HTML_NAMED_ENTITY.sub(_named_to_numeric, text)
    text = _BARE_AMP.sub("&amp;", text)
    text = _BARE_LT.sub("&lt;", text)
    return text


def parse_diagram_summary(xml: str) -> dict[str, Any]:
    """Lean mxCell extract for rules + ReviewAgent input (no full XML)."""
    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    if len(xml) > 2 * 1024 * 1024:
        logger.warning("WA rule engine: XML size %d bytes > 2MB; continuing", len(xml))
    raw = xml or ""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as first_err:
        cleaned = sanitize_mxgraph_xml(raw)
        if cleaned == raw:
            raise ValueError(f"invalid_mxgraph_xml: {first_err}") from first_err
        try:
            root = ET.fromstring(cleaned)
            logger.info(
                "WA rule engine: sanitized mxGraph XML after parse error: %s",
                first_err,
            )
        except ET.ParseError as e:
            raise ValueError(f"invalid_mxgraph_xml: {e}") from e

    for cell in root.iter("mxCell"):
        cid = cell.attrib.get("id") or ""
        value = _cell_text(cell.attrib.get("value"))
        style = (cell.attrib.get("style") or "").lower()
        edge = cell.attrib.get("edge") == "1"
        if edge:
            edges.append(
                {
                    "id": cid,
                    "source": cell.attrib.get("source") or "",
                    "target": cell.attrib.get("target") or "",
                }
            )
            continue
        if not value and "swimlane" not in style and "shape=" not in style:
            continue
        nodes.append({"id": cid, "label": value, "style": style[:200]})
    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


def _labels(summary: dict[str, Any]) -> str:
    return " ".join(n.get("label", "") for n in summary.get("nodes", []))


def _find_nodes(summary: dict[str, Any], *keywords: str) -> list[str]:
    ids: list[str] = []
    for n in summary.get("nodes", []):
        blob = f"{n.get('label', '')} {n.get('style', '')}"
        if any(k in blob for k in keywords):
            ids.append(n["id"])
    return ids


def _run_rules(summary: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    labels = _labels(summary)
    nodes = summary.get("nodes") or []

    def add(
        code: str,
        pillar: str,
        severity: str,
        title: str,
        message: str,
        node_ids: list[str],
        hint: str,
    ) -> None:
        findings.append(
            Finding(
                code=code,
                pillar=pillar,
                severity=severity,
                title=title,
                message=message,
                node_ids=node_ids,
                recommendation_hint=hint,
            )
        )

    # --- Reliability ---
    az_ids = _find_nodes(summary, "az-", "availability zone", "availabilityzone")
    if len(az_ids) <= 1 and (
        _find_nodes(summary, "rds", "aurora", "dynamodb", "ec2", "ecs", "eks")
        or "vpc" in labels
    ):
        add(
            "REL-SINGLE-AZ",
            "reliability",
            "high",
            "疑似單一／不足 AZ 佈署",
            "圖面未清楚標示多個 Availability Zone；高可用風險偏高。",
            az_ids,
            "至少跨兩個 AZ 放置關鍵工作負載與資料層。",
        )

    db_ids = _find_nodes(summary, "rds", "aurora", "database", "dynamodb")
    standby = _find_nodes(summary, "standby", "replica", "secondary", "multi-az")
    if db_ids and not standby:
        add(
            "REL-DB-NO-STANDBY",
            "reliability",
            "critical",
            "資料庫缺少備援／複本標註",
            "偵測到資料庫元件，但未見 standby／replica／Multi-AZ 標註。",
            db_ids,
            "為 RDS/Aurora 啟用 Multi-AZ 或讀取複本並在圖上標示。",
        )

    if db_ids and not _find_nodes(summary, "backup", "snapshot", "pit"):
        add(
            "REL-NO-BACKUP",
            "reliability",
            "high",
            "缺少備份／快照標註",
            "資料層未標示 backup／snapshot 策略。",
            db_ids,
            "標註自動備份與保留週期；關鍵系統考慮跨區域複寫。",
        )

    if not _find_nodes(summary, "asg", "auto scaling", "autoscaling") and _find_nodes(
        summary, "ec2", "ecs", "eks"
    ):
        add(
            "REL-NO-ASG",
            "reliability",
            "warn",
            "運算層缺少 Auto Scaling 標註",
            "有運算節點但未見 Auto Scaling Group／自動擴展標註。",
            _find_nodes(summary, "ec2", "ecs", "eks"),
            "為無狀態服務加上 ASG 或多副本部署。",
        )

    # --- Security ---
    if "0.0.0.0" in labels or "0.0.0.0/0" in labels or "open to world" in labels:
        add(
            "SEC-PUBLIC-SG",
            "security",
            "critical",
            "疑似對全世界開放的安全組",
            "圖面文字出現 0.0.0.0/0 或對全世界開放語意。",
            _find_nodes(summary, "0.0.0.0", "security group", "sg "),
            "將入站限制為必要 CIDR／前置元件；避免全開 0.0.0.0/0。",
        )

    edge_ids = _find_nodes(summary, "alb", "nlb", "api gateway", "cloudfront", "apigateway")
    if edge_ids and not _find_nodes(summary, "waf"):
        add(
            "SEC-NO-WAF",
            "security",
            "high",
            "邊緣入口缺少 WAF",
            "有負載平衡／API／CDN 入口但未見 WAF。",
            edge_ids,
            "在 CloudFront／ALB／API Gateway 前加上 AWS WAF。",
        )

    if not _find_nodes(summary, "iam", "role", "oidc", "cognito") and nodes:
        add(
            "SEC-NO-IAM-HINT",
            "security",
            "warn",
            "缺少 IAM／身分標註",
            "圖上未見 IAM Role／身分提供者標註，最小權限難以審查。",
            [],
            "為運算與整合路徑標註專用 IAM Role 與信任邊界。",
        )

    if _find_nodes(summary, "s3") and not _find_nodes(
        summary, "kms", "sse", "encryption", "加密"
    ):
        add(
            "SEC-S3-NO-ENCRYPT",
            "security",
            "high",
            "S3 缺少加密標註",
            "偵測到 S3 但未標示加密／KMS。",
            _find_nodes(summary, "s3"),
            "啟用 SSE-S3 或 SSE-KMS，並限制公開存取。",
        )

    # --- Cost ---
    if _find_nodes(summary, "xlarge", "4xlarge", "metal"):
        add(
            "COST-OVERSIZE-HINT",
            "cost_optimization",
            "info",
            "可能過大的執行個體規格",
            "標籤含 xlarge／metal 等大規格，請確認需求。",
            _find_nodes(summary, "xlarge", "4xlarge", "metal"),
            "以工作負載量測後右調規格；考慮 Savings Plans／Spot。",
        )

    if _find_nodes(summary, "s3", "ebs", "efs") and not _find_nodes(
        summary, "lifecycle", "glacier", "intelligent-tiering"
    ):
        add(
            "COST-NO-LIFECYCLE",
            "cost_optimization",
            "warn",
            "儲存缺少 lifecycle 標註",
            "有儲存元件但未見 lifecycle／階層儲存標註。",
            _find_nodes(summary, "s3", "ebs", "efs"),
            "為物件儲存設定 lifecycle 與 Intelligent-Tiering。",
        )

    if not _find_nodes(summary, "nat gateway", "natgateway") and "private" in labels:
        # informational only when private present without cost note — skip noise
        pass

    if _find_nodes(summary, "nat"):
        add(
            "COST-NAT-HINT",
            "cost_optimization",
            "info",
            "NAT 閘道成本提醒",
            "圖含 NAT；請確認流量模式與多 AZ NAT 成本。",
            _find_nodes(summary, "nat"),
            "評估 NAT Gateway 數量與 VPC endpoint 以降低資料傳輸費。",
        )

    # --- Performance ---
    if _find_nodes(summary, "rds", "aurora", "dynamodb") and not _find_nodes(
        summary, "cache", "elasticache", "redis", "memcached", "cloudfront"
    ):
        add(
            "PERF-NO-CACHE",
            "performance_efficiency",
            "warn",
            "讀路徑缺少快取標註",
            "有資料層但未見 ElastiCache／CloudFront 等快取。",
            [],
            "對讀多路徑加入快取或 CDN。",
        )

    region_hits = len(re.findall(r"\b(us-|ap-|eu-|cn-)", labels))
    if region_hits <= 1 and _find_nodes(summary, "alb", "api", "cloudfront", "users", "client"):
        add(
            "PERF-SINGLE-REGION-LAT",
            "performance_efficiency",
            "info",
            "單區域延遲風險",
            "架構似乎集中於單一區域，跨區使用者可能延遲較高。",
            [],
            "對全球使用者考慮 CloudFront 或多區域作用中架構。",
        )

    # --- Operational Excellence ---
    if not _find_nodes(
        summary, "cloudwatch", "monitor", "grafana", "prometheus", "x-ray", "otel"
    ):
        add(
            "OE-NO-MONITOR",
            "operational_excellence",
            "warn",
            "缺少監控元件標註",
            "圖上未見 CloudWatch／可觀測性元件。",
            [],
            "加入指標、日誌與追蹤（CloudWatch／X-Ray 等）。",
        )

    if not _find_nodes(summary, "alarm", "pager", "sns", "opsgenie", "alert"):
        add(
            "OE-NO-ALARM",
            "operational_excellence",
            "warn",
            "缺少告警／通報標註",
            "未見 alarm／SNS／pager 類標註。",
            [],
            "為關鍵 SLO 設定告警並串接通報管道。",
        )

    if not _find_nodes(summary, "ci", "cd", "pipeline", "codepipeline", "github actions"):
        add(
            "OE-NO-PIPELINE",
            "operational_excellence",
            "info",
            "缺少 CI/CD 標註",
            "圖上未標示部署管線（可接受若本圖僅 runtime）。",
            [],
            "若此圖含變更路徑，請標註 CI/CD 與審核關卡。",
        )

    if summary.get("node_count", 0) == 0:
        add(
            "OE-EMPTY-DIAGRAM",
            "operational_excellence",
            "high",
            "架構圖幾乎空白",
            "未能解析出可辨識的架構節點。",
            [],
            "請確認已儲存含 AWS 元件標籤的 draw.io 圖再評核。",
        )

    return findings


def _run_rules_gcp(summary: dict[str, Any]) -> list[Finding]:
    """Google Cloud Well-Architected Framework–aligned heuristics (five WA pillar ids).

    Ref: https://docs.cloud.google.com/architecture/framework
    """
    findings: list[Finding] = []
    labels = _labels(summary)

    def add(
        code: str,
        pillar: str,
        severity: str,
        title: str,
        message: str,
        node_ids: list[str],
        hint: str,
    ) -> None:
        findings.append(
            Finding(
                code=code,
                pillar=pillar,
                severity=severity,
                title=title,
                message=message,
                node_ids=node_ids,
                recommendation_hint=hint,
            )
        )

    zone_ids = _find_nodes(summary, "zone", "europe-", "us-", "asia-", "australia-")
    compute = _find_nodes(
        summary, "gce", "compute engine", "gke", "cloud run", "cloud sql", "spanner"
    )
    if len(zone_ids) <= 1 and (compute or "vpc" in labels):
        add(
            "GCP-REL-SINGLE-ZONE",
            "reliability",
            "high",
            "[GCAF] 疑似單一 zone／區域佈署",
            "Google Cloud Well-Architected Reliability 強調以冗餘建立高可用；圖面未清楚標示多個 zone。",
            zone_ids,
            "關鍵工作負載跨至少兩個 zone（regional MIG／multi-zone），資料層考慮多區域。",
        )

    db_ids = _find_nodes(
        summary, "cloud sql", "spanner", "firestore", "bigtable", "alloydb", "database"
    )
    standby = _find_nodes(
        summary, "replica", "standby", "regional", "multi-region", "high availability", "ha "
    )
    if db_ids and not standby:
        add(
            "GCP-REL-DB-NO-HA",
            "reliability",
            "critical",
            "[GCAF] 資料庫缺少 HA／複本標註",
            "偵測到資料庫元件，但未見 replica／regional／HA 標註。",
            db_ids,
            "為 Cloud SQL 啟用高可用，或使用 Spanner／多區域資料服務並在圖上標示。",
        )

    # GCAF Reliability: horizontal scalability
    if compute and not _find_nodes(
        summary,
        "mig",
        "managed instance group",
        "autoscal",
        "auto scale",
        "hpa",
        "cloud run",
        "horizontal",
    ):
        add(
            "GCP-REL-NO-SCALE",
            "reliability",
            "warn",
            "[GCAF] 缺少水平擴展標註",
            "有運算層但未見 MIG／autoscaling／水平擴展標註（GCAF：Take advantage of horizontal scalability）。",
            compute,
            "使用 regional MIG、GKE autoscaling 或 Cloud Run 自動伸縮。",
        )

    # GCAF Reliability: recovery / multi-regional
    if (db_ids or compute) and not _find_nodes(
        summary,
        "multi-region",
        "multiregion",
        "cross-region",
        "backup",
        "dr ",
        "disaster",
        "failover",
    ):
        add(
            "GCP-REL-NO-DR",
            "reliability",
            "high",
            "[GCAF] 缺少多區域／復原標註",
            "圖上未見 multi-region／backup／failover 等復原路徑標註。",
            db_ids or compute,
            "標示跨區域複本或備份還原路徑，並定義 RPO/RTO。",
        )

    if compute and not _find_nodes(
        summary,
        "cloud armor",
        "armor",
        "load balancing",
        "https load",
        "glb",
        "iap",
        "identity-aware",
    ):
        add(
            "GCP-SEC-NO-EDGE",
            "security",
            "high",
            "[GCAF] 缺少邊緣防護／負載平衡標註",
            "GCAF Security 強調 security by design／zero trust；有運算層但未見 Cloud Armor、全球 LB 或 IAP。",
            compute,
            "在對外入口加入 Cloud Load Balancing 與 Cloud Armor；管理面考慮 IAP。",
        )

    if not _find_nodes(
        summary, "kms", "cloud kms", "secret manager", "secretmanager"
    ) and (
        _find_nodes(summary, "sql", "storage", "bucket", "gcs") or "database" in labels
    ):
        add(
            "GCP-SEC-NO-KMS",
            "security",
            "high",
            "[GCAF] 缺少 KMS／Secret Manager 標註",
            "有資料儲存但未見加密金鑰或密鑰管理元件。",
            [],
            "使用 Cloud KMS（CMEK）與 Secret Manager 管理金鑰與密文。",
        )

    if db_ids and not _find_nodes(
        summary, "memorystore", "cdn", "cloud cdn", "cache"
    ):
        add(
            "GCP-PERF-NO-CACHE",
            "performance_efficiency",
            "warn",
            "[GCAF] 讀路徑缺少快取標註",
            "GCAF Performance optimization：有資料層但未見 Memorystore／Cloud CDN。",
            [],
            "對讀多路徑加入快取或 CDN，並依負載規劃資源配置。",
        )

    if not _find_nodes(
        summary,
        "cloud monitoring",
        "monitoring",
        "cloud logging",
        "logging",
        "ops agent",
        "cloud trace",
    ):
        add(
            "GCP-OE-NO-MONITOR",
            "operational_excellence",
            "warn",
            "[GCAF] 缺少 CloudOps 可觀測性標註",
            "GCAF Operational excellence 強調 CloudOps；圖上未見 Cloud Monitoring／Logging／Trace。",
            [],
            "加入 Monitoring、Logging、SLO 與告警政策。",
        )

    if not _find_nodes(
        summary, "cloud build", "cloud deploy", "cloudbuild", "tekton", "github actions"
    ):
        add(
            "GCP-OE-NO-PIPELINE",
            "operational_excellence",
            "info",
            "[GCAF] 缺少變更自動化（CI/CD）標註",
            "GCAF Ops：Automate and manage change；圖上未標示 Cloud Build／Deploy 等管線。",
            [],
            "若含變更路徑，請標註 CI/CD（Cloud Build／Cloud Deploy）。",
        )

    if _find_nodes(summary, "compute engine", "gce") and not _find_nodes(
        summary, "committed use", "cud", "spot", "preemptible", "autoscal", "lifecycle"
    ):
        add(
            "GCP-COST-NO-COMMIT",
            "cost_optimization",
            "info",
            "[GCAF] 運算／資源成本優化標註不足",
            "GCAF Cost：Optimize resource usage；有 GCE 但未見 CUD／Spot／自動伸縮標註。",
            [],
            "評估 CUD、Spot VM 或自動伸縮以降低成本。",
        )

    if summary.get("node_count", 0) == 0:
        add(
            "OE-EMPTY-DIAGRAM",
            "operational_excellence",
            "high",
            "架構圖幾乎空白",
            "未能解析出可辨識的架構節點。",
            [],
            "請確認已儲存含 GCP 元件標籤的 draw.io 圖再評核。",
        )

    return findings


def _run_rules_azure(summary: dict[str, Any]) -> list[Finding]:
    """Azure Well-Architected–aligned heuristics (mapped to WA five pillars)."""
    findings: list[Finding] = []
    labels = _labels(summary)

    def add(
        code: str,
        pillar: str,
        severity: str,
        title: str,
        message: str,
        node_ids: list[str],
        hint: str,
    ) -> None:
        findings.append(
            Finding(
                code=code,
                pillar=pillar,
                severity=severity,
                title=title,
                message=message,
                node_ids=node_ids,
                recommendation_hint=hint,
            )
        )

    az_ids = _find_nodes(
        summary, "availability zone", "availabilityzone", "az-", "zone"
    )
    compute = _find_nodes(
        summary,
        "app service",
        "aks",
        "virtual machine",
        "vmss",
        "functions",
        "azure sql",
        "cosmos",
    )
    if len(az_ids) <= 1 and (compute or "vnet" in labels or "virtual network" in labels):
        add(
            "AZ-REL-SINGLE-ZONE",
            "reliability",
            "high",
            "疑似單一 Availability Zone 佈署",
            "圖面未清楚標示多個 AZ；高可用風險偏高。",
            az_ids,
            "關鍵工作負載跨至少兩個 Availability Zone。",
        )

    db_ids = _find_nodes(
        summary, "azure sql", "cosmos", "sql database", "database", "synapse"
    )
    standby = _find_nodes(
        summary, "geo-replica", "failover", "zone redundant", "replica", "secondary"
    )
    if db_ids and not standby:
        add(
            "AZ-REL-DB-NO-HA",
            "reliability",
            "critical",
            "資料庫缺少備援／區域備援標註",
            "偵測到資料庫元件，但未見 replica／failover／zone-redundant 標註。",
            db_ids,
            "啟用 zone-redundant 或 geo-replication 並在圖上標示。",
        )

    if compute and not _find_nodes(
        summary,
        "application gateway",
        "front door",
        "waf",
        "azure firewall",
        "load balancer",
    ):
        add(
            "AZ-SEC-NO-EDGE",
            "security",
            "high",
            "缺少邊緣防護／閘道標註",
            "有運算層但未見 Application Gateway／Front Door／WAF。",
            compute,
            "在對外入口加入 Application Gateway 或 Front Door 與 WAF。",
        )

    if not _find_nodes(summary, "key vault", "keyvault") and (
        db_ids or _find_nodes(summary, "storage", "blob")
    ):
        add(
            "AZ-SEC-NO-KEYVAULT",
            "security",
            "high",
            "缺少 Key Vault 標註",
            "有資料儲存但未見 Azure Key Vault。",
            [],
            "使用 Key Vault 管理密鑰與憑證。",
        )

    if db_ids and not _find_nodes(
        summary, "redis", "cdn", "front door", "cache", "azure cache"
    ):
        add(
            "AZ-PERF-NO-CACHE",
            "performance_efficiency",
            "warn",
            "讀路徑缺少快取標註",
            "有資料層但未見 Redis／CDN 類快取。",
            [],
            "對讀多路徑加入 Azure Cache for Redis 或 CDN。",
        )

    # WARA themes (diagram-adapted; not live collector): DR / backup / health
    # Ref: https://github.com/Azure/Well-Architected-Reliability-Assessment
    if (db_ids or compute) and not _find_nodes(
        summary,
        "geo-replica",
        "geo replication",
        "paired region",
        "secondary region",
        "site recovery",
        "asr",
        "multi-region",
        "multiregion",
        "failover group",
    ):
        add(
            "AZ-REL-NO-DR",
            "reliability",
            "high",
            "[WARA] 缺少跨區域／災難復原標註",
            "WARA Reliability 強調恢復與跨區域備援；圖上未見 geo-replica／Site Recovery／paired region 等標註。",
            db_ids or compute,
            "標示次要區域、geo-replication 或 Azure Site Recovery，並定義 RPO/RTO。",
        )

    if (db_ids or _find_nodes(summary, "storage", "blob")) and not _find_nodes(
        summary,
        "backup",
        "recovery vault",
        "recovery services",
        "pitr",
        "point-in-time",
    ):
        add(
            "AZ-REL-NO-BACKUP",
            "reliability",
            "high",
            "[WARA] 缺少備份／復原標註",
            "有資料層但未見 Backup／Recovery Services Vault／PITR 標註。",
            db_ids,
            "為關鍵資料啟用備份與還原測試，並在圖上標示。",
        )

    if compute and not _find_nodes(
        summary,
        "health probe",
        "health check",
        "health endpoint",
        "readiness",
        "liveness",
        "auto-heal",
        "auto heal",
    ):
        add(
            "AZ-REL-NO-HEALTH",
            "reliability",
            "warn",
            "[WARA] 缺少健康探針／自癒標註",
            "有運算層但未見 health probe／auto-heal 等運維復原機制標註。",
            compute,
            "在負載平衡／App Service／AKS 標示健康探針，並規劃故障自動隔離。",
        )

    if not _find_nodes(
        summary,
        "monitor",
        "application insights",
        "log analytics",
        "azure monitor",
    ):
        add(
            "AZ-OE-NO-MONITOR",
            "operational_excellence",
            "warn",
            "缺少監控元件標註",
            "圖上未見 Azure Monitor／Application Insights。",
            [],
            "加入 Monitor、Log Analytics 與告警。",
        )

    if not _find_nodes(
        summary, "devops", "pipeline", "github actions", "cicd", "ci/cd"
    ):
        add(
            "AZ-OE-NO-PIPELINE",
            "operational_excellence",
            "info",
            "缺少 CI/CD 標註",
            "圖上未標示 Azure DevOps／GitHub Actions 管線。",
            [],
            "若含變更路徑，請標註 CI/CD。",
        )

    if _find_nodes(summary, "virtual machine", "vm ") and not _find_nodes(
        summary, "reserved", "spot", "autoscale", "vmss"
    ):
        add(
            "AZ-COST-NO-COMMIT",
            "cost_optimization",
            "info",
            "運算成本優化標註不足",
            "有 VM 但未見 Reserved／Spot／自動伸縮標註。",
            [],
            "評估 Reserved Instances、Spot 或 VMSS 自動伸縮。",
        )

    if summary.get("node_count", 0) == 0:
        add(
            "OE-EMPTY-DIAGRAM",
            "operational_excellence",
            "high",
            "架構圖幾乎空白",
            "未能解析出可辨識的架構節點。",
            [],
            "請確認已儲存含 Azure 元件標籤的 draw.io 圖再評核。",
        )

    return findings


def score_findings(findings: list[Finding]) -> tuple[dict[str, float], float]:
    pillar_scores = {p: 100.0 for p in PILLARS}
    for f in findings:
        if f.pillar not in pillar_scores:
            continue
        deduct = SEVERITY_DEDUCT.get(f.severity, 2)
        pillar_scores[f.pillar] = max(0.0, pillar_scores[f.pillar] - deduct)
    overall = sum(pillar_scores[p] * WEIGHTS[p] for p in PILLARS)
    return pillar_scores, round(overall, 2)


def detect_provider(summary: dict[str, Any]) -> dict[str, Any]:
    """Score cloud keywords; return best provider + raw scores (manual override OK)."""
    labels = _labels(summary)
    style_blob = " ".join(n.get("style", "") for n in summary.get("nodes") or [])
    blob = f"{labels} {style_blob}"

    scores = {"aws": 0, "gcp": 0, "azure": 0}
    aws_kw = (
        "aws",
        "amazon",
        "vpc",
        "ec2",
        "ecs",
        "eks",
        "lambda",
        "aurora",
        "rds",
        "dynamodb",
        "s3",
        "cloudfront",
        "waf",
        "alb",
        "nlb",
        "cloudwatch",
        "kms",
        "mxgraph.aws",
    )
    gcp_kw = (
        "gcp",
        "google cloud",
        "gce",
        "compute engine",
        "gke",
        "cloud run",
        "cloud sql",
        "spanner",
        "firestore",
        "bigquery",
        "cloud armor",
        "memorystore",
        "cloud cdn",
        "cloud monitoring",
        "cloud kms",
        "mxgraph.gcp",
    )
    azure_kw = (
        "azure",
        "microsoft",
        "vnet",
        "virtual network",
        "aks",
        "app service",
        "functions",
        "cosmos",
        "azure sql",
        "key vault",
        "front door",
        "application gateway",
        "azure monitor",
        "mxgraph.azure",
    )
    for k in aws_kw:
        if k in blob:
            scores["aws"] += 2 if k.startswith("mxgraph") or k in ("aws", "amazon") else 1
    for k in gcp_kw:
        if k in blob:
            scores["gcp"] += 2 if k.startswith("mxgraph") or k in ("gcp", "google cloud") else 1
    for k in azure_kw:
        if k in blob:
            scores["azure"] += (
                2 if k.startswith("mxgraph") or k in ("azure", "microsoft") else 1
            )

    best = max(scores, key=lambda p: scores[p])
    if scores[best] == 0:
        best = "aws"
    return {"provider": best, "scores": scores}


def evaluate(xml: str, provider: str = "aws") -> RuleResult:
    provider = (provider or "aws").lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"provider_not_supported_by_rule_engine:{provider}")
    summary = parse_diagram_summary(xml or "")
    if provider == "gcp":
        findings = _run_rules_gcp(summary)
    elif provider == "azure":
        findings = _run_rules_azure(summary)
    else:
        findings = _run_rules(summary)
    pillar_scores, overall = score_findings(findings)
    pack = RULE_PACK_BY_PROVIDER[provider]
    return RuleResult(
        provider=provider,
        rule_pack_version=pack,
        pillar_scores=pillar_scores,
        overall_score=overall,
        weights_snapshot=dict(WEIGHTS),
        findings=findings,
    )
