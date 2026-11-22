# NFR Requirements 問答：U1 `u1-iac-api`

> Stage: nfr-requirements · Unit: `u1-iac-api`（service）· Bolt B1  
> 本 Unit＝後端 Session＋三核心＋`/api/iac`；**不含** UI a11y（NFR5 → U2）。  
> 產出：performance／security／scalability／reliability／observability／tech-stack／traceability。  
> **成本揭露**：本題組共 6 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| ADR-0006：IAM／encryption／network／audit；PBT 三核心 | [req] NFR1／NFR2；`project.md` |
| 密文不進 log／回應／zip；禁 apply／雲端 SM 寫入 | [req] NFR3／約束；BR1.5／BR1.7 |
| 第一個 D HTTP 含 403；規則 A／B／C | [req] NFR4；BR1.12 |
| 新碼於 `backend/iac/`；logger `cloud360.*`；禁 `d1_*` | [req] NFR6 |
| 行程級 in-memory `(userId, diagramId)`；重載即失 | [fd] Q5=A |
| 同步 HTTP；執行 POST 不自動重試；422＋`error.code` | [cd] |
| 不做自研掃描引擎；本 intent 不新增 CI IaC scan job | [req] 約束／範圍外 |
| Tech stack 基底：Python 3.12／FastAPI／Hypothesis／既有 LangGraph＋OpenRouter | [codekb] |

## Sources

- [fd] `../functional-design/functional-spec.md`、`rules.md`
- [req] `../../../inception/requirements-analysis/requirements.md`（NFR1–NFR7、OQ2）
- [cd] `../../../inception/contract-design/contract-summary.md`
- [codekb] `aidlc/spaces/default/codekb/cloud/technology-stack.md`

---

## Q1. D1 `POST /generate` 延遲目標（含 LLM）？

> D1 走 agent／LLM，與純函式 scan／rewrite 量級不同；需可測數字，不能寫「夠快」。

A. **Staging 務實**：p95 ＜ 60s、硬逾時 90s；逾時回 504／明確 `error.code`；不承諾互動級 API 延遲。**（建議）**
B. 更嚴：p95 ＜ 30s、硬逾時 45s（可能提高失敗率／需較快模型）。
C. 更寬：p95 ＜ 120s、硬逾時 180s（演示優先、容忍慢模型）。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 非 LLM 路徑（`/session`、`/scan`、`/secrets/rewrite`、`/download`）延遲？

> 這些應為本機／CPU 為主；需與 Q1 分開訂。

A. **p95 ＜ 2s**（單圖典型草稿／報告體積）；zip 組裝另計 p95 ＜ 5s；超過視為缺陷。**（建議）**
B. 更嚴：上述 API p95 ＜ 500ms；zip p95 ＜ 2s。
C. 更寬：上述 API p95 ＜ 5s；zip p95 ＜ 15s。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. D2 掃描工具選型（承接 OQ2）？

> 約束：不自研引擎、本 intent 不新增 CI scan job；此題只定**執行期** U1 呼叫的工具。

A. **Checkov CLI**（Terraform／HCL），版本釘在 `tech-stack-decisions`；找不到 CLI → 明確失敗碼，不靜默空報告。**（建議）**
B. **tfsec CLI**（同釘版與失敗語意）。
C. **雙工具**（Checkov＋tfsec）合併 findings（實作與對應成本較高）。
D. **先 stub／規則表**，工具點名延到 NFR Design／code-gen 前再開 ADR。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. In-memory session 容量與併發？

> 重載即失已定；需防單一使用者／行程打爆記憶體。

A. **每 user 最多 3 個活躍 `diagram_id` 槽**；超出淘汰最舊。同槽同時僅 1 個 in-flight 寫入 POST（其餘 409 或忽略後寫，對齊切圖語意）。草稿／報告合計硬上限 **16 MiB／槽**。**（建議）**
B. 每 user 1 槽；硬上限 8 MiB／槽；同槽串行。
C. 不設槽數上限；只設單槽 32 MiB 與行程總 256 MiB 警戒。
X. Other (please specify)

[Answer]:Ａ

---

## Q5. 可靠性姿態（鑑於 in-memory）？

> 無持久化 ⇒ RPO＝進程生命週期；需明示 SLO 預期，避免被解讀成 99.9% 多副本。

A. **單進程 best-effort**：重啟／部署清空 session 為**預期行為**；可用性跟 staging 主機走，不另訂多 AZ／failover。文件與 UI 錯誤文案可提示「請重新產生」。**（建議）**
B. 本輪仍 in-memory，但 NFR 預留「下一 intent 可換 Redis／DB」介面約束（Port），本輪不實作。
C. 改口要求本輪持久化（**與 FD Q5=A 衝突，需回改 FD／ADR**）。
X. Other (please specify)

[Answer]:Ａ

---

## Q6. 觀測深度（承接 NFR7）？

> 密文不得進 log；需定最小可診斷集合。

A. **結構化 log（`cloud360.iac.*`）＋每請求 `request_id`／`diagram_id`／`error.code`／耗時**；D1 另記 model／token 粗量（無 prompt／密文）。**暫無** Prometheus 指標與分散式 tracing 義務。**（建議）**
B. A 再加上 RED 指標（QPS／error／latency histogram）暴露給既有 staging 監控。
C. A＋B，再加 OpenTelemetry trace（跨 generate→LLM）。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — D1 generate：p95＜60s、硬逾時 90s；逾時明確錯誤碼。
2. **Q2=A** — 非 LLM API p95＜2s；zip p95＜5s。
3. **Q3=A** — D2 用 Checkov CLI（釘版）；缺 CLI→明確失敗，不空報告。
4. **Q4=A** — 每 user ≤3 槽、16 MiB／槽、同槽單 in-flight。
5. **Q5=A** — 單進程 best-effort；重啟清空為預期。
6. **Q6=A** — 結構化 log＋request_id／error.code／耗時；暫無 metrics／tracing。

**將產出**：performance／security／scalability／reliability／observability／tech-stack-decisions／traceability。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
