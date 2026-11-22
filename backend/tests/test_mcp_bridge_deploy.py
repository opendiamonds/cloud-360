"""`U21 mcp-bridge` 的部署檔、CI 與文件斷言（CC-5、CC-7、IC-1–IC-9；`NFR21.16` ②、`NFR21.31`、`NFR21.32`）。

compose 以 `yaml.safe_load` 解析（CC-5）。既有 validator 只讀環境變數，不解析 `ports:`／`networks:`，
這些斷言是 compose 結構唯一的機械閘門。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / "deploy" / "docker-compose.deploy.yml"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DEPLOY_WF = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
DEPLOY_MD = REPO_ROOT / "DEPLOY.md"
LOCAL_DEV = REPO_ROOT / "LOCAL-DEV.md"
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
HEALTH_STEP = "Record mcp-bridge health (non-blocking)"


def compose():
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def service_block_text(name):
    """compose 原文中該服務區塊的文字（用來抓 `${`，safe_load 之後就看不到了）。"""
    lines = COMPOSE.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"  {name}:")
    end = next(i for i in range(start + 1, len(lines))
               if re.match(r"^  [a-z]", lines[i]) or re.match(r"^[a-z]", lines[i]))
    return "\n".join(lines[start:end])


class ComposeTest(unittest.TestCase):  # CC-5
    def setUp(self):
        self.doc = compose()
        self.svc = self.doc["services"]["mcp-bridge"]

    def test_network_membership(self):
        self.assertEqual(self.svc["networks"], ["mcp"])
        self.assertIs(self.doc["networks"]["mcp"]["internal"], True)
        members = {name for name, s in self.doc["services"].items() if "mcp" in (s.get("networks") or [])}
        self.assertEqual(members, {"backend", "mcp-bridge"})
        for net in ("edge", "internal"):
            self.assertFalse((self.doc["networks"][net] or {}).get("internal", False), net)
        self.assertEqual(self.doc["services"]["backend"]["networks"], ["edge", "internal", "mcp"])

    def test_no_exposure_and_no_environment(self):
        for key in ("ports", "environment", "env_file", "expose"):
            self.assertNotIn(key, self.svc)
        self.assertNotIn("${", service_block_text("mcp-bridge"))

    def test_shape(self):
        self.assertEqual(self.svc["build"], {"context": "../backend", "network": "host"})
        self.assertEqual(self.svc["build"], self.doc["services"]["backend"]["build"])
        self.assertEqual(self.svc["restart"], "unless-stopped")
        self.assertEqual(self.svc["command"], ["python", "-m", "mcp_bridge", "--backend-url",
                                               "http://backend:8000", "--host", "0.0.0.0", "--port", "8080"])
        self.assertEqual(self.svc["stop_grace_period"], "15s")
        self.assertEqual(self.svc["depends_on"], ["backend"])
        self.assertEqual(self.svc["deploy"]["resources"]["limits"]["memory"], "512m")
        self.assertEqual(self.svc["logging"], self.doc["services"]["db"]["logging"])
        test = " ".join(self.svc["healthcheck"]["test"])
        self.assertIn("http://127.0.0.1:8080/healthz", test)
        self.assertNotIn("8000", test)

    def test_service_count_comments(self):
        text = COMPOSE.read_text(encoding="utf-8")
        self.assertEqual(len(self.doc["services"]), 7)
        self.assertIn("50m x 5 x 7 services = 1.75GB", text)
        self.assertIn("REQUIRED RELATIONSHIP: stop_grace_period", text)


class DockerfileTest(unittest.TestCase):
    def test_route_a_dockerfile_untouched(self):
        self.assertNotIn("mcp", DOCKERFILE.read_text(encoding="utf-8").lower())


class CiTest(unittest.TestCase):
    def test_backend_job_has_drift_gate_and_timeout(self):
        job = yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"]["backend"]
        self.assertEqual(job["timeout-minutes"], 15)
        names = [s.get("name") for s in job["steps"]]
        gate = job["steps"][names.index("MCP tool spec drift")]
        self.assertEqual(gate["run"], "python scripts/gen_mcp_tools.py --check")
        self.assertNotIn("env", gate)
        self.assertLess(names.index("WS contract spec drift"), names.index("MCP tool spec drift"))
        self.assertLess(names.index("MCP tool spec drift"), names.index("Run unit tests"))


class DeployWorkflowTest(unittest.TestCase):  # CC-7、infrastructure-design R-02
    def setUp(self):
        steps = yaml.safe_load(DEPLOY_WF.read_text(encoding="utf-8"))["jobs"]["deploy"]["steps"]
        self.names = [s.get("name") for s in steps]
        self.step = steps[self.names.index(HEALTH_STEP)]

    def test_position(self):
        i = self.names.index(HEALTH_STEP)
        self.assertEqual(self.names[i - 1], "Wait for the public hostname to answer through the tunnel")
        self.assertTrue(self.names[i + 1].startswith("Verify sessions survive a Redis restart"))

    def test_tolerant_shape(self):
        run = self.step["run"]
        self.assertFalse(re.search(r"set -[a-z]*e", run))  # 不得因取值失敗而中止步驟
        for line in run.splitlines():
            if re.search(r"=\$\((docker|compose)", line):
                self.assertRegex(line.strip(), r"^(if|elif)\s|&&\s*OUT=", line)
        self.assertIn("ATTEMPTS: \"12\"", DEPLOY_WF.read_text(encoding="utf-8"))
        self.assertIn("sleep 5", run)
        self.assertNotIn("/mcp", run)
        self.assertNotIn("Authorization", run)
        self.assertIn("GITHUB_STEP_SUMMARY", run)
        self.assertIn("RestartCount", run)

    def test_blocking_once_a_real_client_exists(self):
        """觸發條件的機械化：任何地方出現 MCP bridge 的 client 時，健康步驟必須改為阻擋。

        程式審查 R-09：比對形狀放寬為「服務名 `mcp-bridge`（任何埠、含設定與組合字串的片段）或 `:8080/mcp`」，
        範圍涵蓋 backend（`mcp_bridge/` 與測試除外）、frontend 的原始碼、根目錄 `scripts/` 與 `deploy/`
        （定義服務本身的 compose 檔除外），檔型含程式、設定與 shell。比對不到的寫法（例如以變數拼出服務名）
        另由 `DEPLOY.md` §5.12 的人工檢查項承接。
        """
        client_files = scan_for_mcp_clients()
        run = self.step["run"]
        failure_tail = run[run.index("::warning::"):]
        if client_files:
            self.assertNotIn("continue-on-error", self.step,
                             f"已有 MCP client（{client_files}），健康步驟必須改為阻擋")
            self.assertIn("exit 1", failure_tail)
        else:
            self.assertIs(self.step.get("continue-on-error"), True)
            self.assertTrue(failure_tail.rstrip().endswith("exit 0"))


#: 單元名稱的敘述（`U21 mcp-bridge`）不是 client，以 lookbehind 排除。
CLIENT_PATTERN = re.compile(r"(?<!U21 )mcp-bridge|:8080/mcp\b")
SCAN_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".yml", ".yaml",
                 ".sh", ".conf", ".toml", ".ini", ".cfg"}


def scan_for_mcp_clients():
    roots = [
        (REPO_ROOT / "backend", {"mcp_bridge", "tests", "tests_pg", "tests_redis", "__pycache__", ".hypothesis"}),
        (REPO_ROOT / "frontend", {"node_modules", "dist", "test-results", "playwright-report"}),
        (REPO_ROOT / "scripts", set()),
        (REPO_ROOT / "deploy", set()),
    ]
    excluded_files = {COMPOSE.resolve()}
    hits = []
    for root, skip_dirs in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            rel = path.relative_to(root)
            if not path.is_file() or (rel.parts and rel.parts[0] in skip_dirs):
                continue
            if any(part in ("node_modules", "__pycache__") for part in rel.parts):
                continue
            is_env = path.name.startswith(".env") or path.name.endswith(".env")
            if path.suffix not in SCAN_SUFFIXES and not is_env:
                continue
            if path.resolve() in excluded_files:
                continue
            if CLIENT_PATTERN.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(path.relative_to(REPO_ROOT)))
    return hits


class DocumentationTest(unittest.TestCase):
    def setUp(self):
        self.deploy = DEPLOY_MD.read_text(encoding="utf-8")

    def test_deploy_md_sections(self):
        for needle in (
            "#### 5.12 MCP bridge（第七個服務，`U21`）",
            "**七個服務全部設了 `deploy.resources.limits.memory`",
            "> | `mcp-bridge` | `512m` |",
            "取七個容器的穩態用量",
            "十一個記憶體上限",
            "改 PR 更新這七個數字",
            "與七個上限同一形狀",
            "`50m × 5 × 7 = 1.75GB`",
            "| `mcp-bridge` 健康紀錄（`U21`） | `12 × 5 = 60s` |",
            "已知有界部分合計 **1320s**",
            "**≤ 480s（8 分鐘）**",
            "兩者合計是否 ≤ 480s",
            "**若合計超過 480s**",
            "`edge` 與 `internal` 兩個網段不帶 `internal: true`",
            "**四個 healthcheck 的已知盲點",
            "| `mcp-bridge` 的 `/healthz` | **不證明工具宣告正確、allowlist 生效，也不證明能呼叫 `backend`**",
            "**這不持久**",
            "經使用者接受的例外，不是符合",
            "host 可連 mcp-bridge:8080/healthz：是／否",
        ):
            with self.subTest(needle=needle[:30]):
                self.assertIn(needle, self.deploy)
        for stale in ("**六個服務全部設了", "`50m × 5 × 6 = 1.5GB`，成立", "≤ 540s", "合計 **1260s**，所以"):
            self.assertNotIn(stale, self.deploy)

    def test_unrelated_six_untouched(self):
        self.assertIn("**其餘六個 brain-infra 變數不要加成 secret**", self.deploy)
        self.assertIn("**其餘六個 brain-infra 變數不是 secret**", self.deploy)

    def test_local_dev(self):
        text = LOCAL_DEV.read_text(encoding="utf-8")
        self.assertIn("for p in 5432 6379 8000 5173 8080; do", text)
        self.assertIn("python -m mcp_bridge --backend-url http://127.0.0.1:8010", text)


if __name__ == "__main__":
    unittest.main()
