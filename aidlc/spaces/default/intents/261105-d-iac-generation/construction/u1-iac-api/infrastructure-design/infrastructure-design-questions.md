# Infrastructure Design 問答：U1 `u1-iac-api`

> Stage: infrastructure-design · Unit: `u1-iac-api`（service）  
> 設計層：部署／監控／CI 要什麼；禁止完整 IaC／IAM 文件。  
> **成本揭露**：本題組共 4 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 自有 staging `192.168.10.10`＋Cloudflare Tunnel；`ut`→deploy.yml | ADR-0007／`project.md` |
| 三環境設定分離；`render-env.sh` 唯一寫 deploy/.env | env contract |
| 單進程 in-memory；無 Redis／多 AZ；無 metrics／OTel | [nfr] |
| Checkov CLI 執行期；**不**新增 CI IaC scan job；禁 apply | [req]／[nfr] |
| 既有 backend Docker＋compose 部署面 | [codekb] |

## Sources

- [nfr] `../nfr-design/*`、`../nfr-requirements/*`
- [fd] `../functional-design/functional-spec.md`
- [dd] `../../../inception/domain-design/components.md`
- [cd] `../../../inception/contract-design/contract-summary.md`

---

## Q1. Checkov 在 staging／CI 映像如何提供？

A. **打進 backend Docker image**（釘版安裝）；本機 dev 文件化可選本機 CLI；缺 CLI → D2 明確失敗。**（建議）**
B. 僅掛載 host 二進位（staging 手動維護）。
C. 獨立 sidecar 容器專跑掃描（本輪過重）。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 機密與 LLM 金鑰？

A. **沿用既有 deploy／dev env**（OpenRouter 等經 `render-env.sh`／`.env.example`）；本 unit **不**新增 Secrets Manager／vault；禁止把金鑰寫進映像層。**（建議）**
B. 本輪新增獨立 secret 後端（需另開 ADR）。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. 監控與告警？

A. **只擴充結構化 log**（`cloud360.iac.*`＋request_id）；沿用既有主機／容器 log 管線；**不**新增 Prometheus／Grafana 面板義務。**（建議）**
B. 新增最小 RED 指標暴露（與 NFR Q6=A 衝突，需回改 NFR）。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. CI／CD 對本 unit 的變更範圍？

A. **沿用 ci.yml／deploy.yml**；code-gen 補 unittest／Hypothesis 進既有測試 job；**不**加 Checkov CI job、不改 deploy-on-merge 拓撲；映像 build 需含 Checkov（對齊 Q1=A）。**（建議）**
B. 新增獨立 workflow 只測 `/api/iac`。
C. 新增 CI Checkov 掃 repo（違反 requirements 約束）。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — Checkov 打進 backend Docker image（釘版）。
2. **Q2=A** — 沿用既有 env／render-env；不新增 vault。
3. **Q3=A** — 只擴充結構化 log；不新增 Prometheus／Grafana。
4. **Q4=A** — 沿用 ci／deploy；測案進既有 job；不加 CI Checkov scan。

**將產出**：infrastructure-specification／monitoring-design／cicd-pipeline／traceability。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
