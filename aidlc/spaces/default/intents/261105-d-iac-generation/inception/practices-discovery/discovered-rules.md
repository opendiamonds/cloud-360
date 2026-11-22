# 發現規則（Discovered Rules）

> practices-discovery 產物｜intent `261105-d-iac-generation`｜HEAD `0bffc82`｜2026-11-05T15:48:45Z
>
> **Final Integration（Step 5）**：含既有 Story D 相關 hard constraints，以及本輪訪談 Affirm 的新增 ALWAYS／NEVER（Q2／Q4／Q5／Q6／Q7）。本檔於確認授權後由 orchestrator 重存（recovery）。
> Q3=A：不把 CI IaC scan job 寫進 Mandated。Q1=A／Q8=A 記入 `team-practices.md`，不另造 Forbidden。

---

## Mandated

- **ALWAYS** 在 commit 前執行 `python3 scripts/validate_repo_contract.py`（違反 = CI 紅燈）。
- **ALWAYS** 在變更資料庫結構或部署必知的 schema／seed 行為時同步更新 `schema_rbac.sql` 與 `DEPLOY.md`（blocking）。Story D 若改動 D1／D2／D3 的 `role_permissions` 預設值或新增 DDL，即觸發本條。
- **ALWAYS** 讓三個環境設定分離且完整，並在 commit 前執行 `python3 scripts/validate_env_contract.py`；部署 `.env` 唯一產生點為 `deploy/render-env.sh`。
- **ALWAYS** 在異動 `backend/database.py` schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh` 時同步更新 `LOCAL-DEV.md`。
- **ALWAYS** 在任何 high-risk action（production write、**IaC apply**、IAM 變更）前先給 plan＋impact＋rollback，並通過 human approval gate。
- **ALWAYS** 對每一項變更檢查 ADR-0006 security baseline 四面向（IAM、encryption、network exposure、audit logging）。
- **ALWAYS** 在每個 intent 的 construction 執行 `tcms-test-cases`（含覆蓋盤點、手動／自動化、突變驗證、`/tcms-verify`）——blocking。
- **ALWAYS** 對 ADR-0006 點名的 **IaC generator** 核心模組納入 property-based testing（不得只有 example-based）。模組尚未存在時為 N/A；落地即 blocking（`project.md ## Testing Posture`）。
- **ALWAYS**（本輪 Affirm，Q5=B）本專案 IaC 柱純函式核心——**generator、scanner 與／或 redactor**——測試必須含 property-based testing（Hypothesis），不得只有 example-based；落點於 `backend/iac/` 領域套件的純函式層（對齊 C1 `backend/cost/` 形狀）。此條擴大 ADR-0006 對 generator 的既有約束，將 scanner／redactor 升格為同級 PBT 核心；後續宜開 ADR 追認。
- **ALWAYS**（本輪 Affirm，Q2=A）D1／D2／D3 **任一**故事的第一個 HTTP 消費者落地時，即使 `role_permissions` seed 未改，仍須 allow／deny 雙向 TestClient：有權 → 2xx，無權 → 403（不得只測 happy path）。
- **ALWAYS**（本輪 Affirm，Q4=A）D3 Secret 處理落地時，必須有負向測試＋redaction 突變驗證：注入明文樣式後，回應／log／artifact 不得出現該明文；拿掉遮罩後測試應紅、還原後應綠。contract 掃描作用域擴大不阻塞本條。
- **ALWAYS**（本輪 Affirm，Q6=A）每個 D 故事先交付可離線斷言的決定性核心（generator／scanner 報告形狀／redactor），再接 LLM 編排；D1／D2／D3 agents 一律走 `langgraph_runtime`＋OpenRouter，禁止再增 Claude-SDK-only／Anthropic-only 路徑。
- **ALWAYS** 新模組／新業務邏輯採三層形狀，純運算下沉到不讀 DB 的函式；不得在 `user_router.py`／`collab_router.py` 之外新建「router 直寫商業邏輯」模組；D 柱實作為 `backend/iac/` 領域套件（Q5=B）。
- **ALWAYS** 授權矩陣變更需 allow／deny 雙向測試；新增／修改 HTTP 端點需 TestClient；前端資料形狀變更需 Playwright e2e（`team.md` A／B／C）。
- **ALWAYS** 文件語言為繁體中文（ADR-0009）；使用者未明確要求時不得自動寫 `decisions-log.md`。
- **ALWAYS** 權限種子或權限頁欄名可先於產品面存在時，codekb／設計必須標明「矩陣領先實作」，不得把 D1／D2／D3 種子或 Coming Soon stub 當成已有 router／頁／表／掃描能力（`project.md` Corrections `reverse-engineering:c9`）。

## Forbidden

- **NEVER**（本輪 Affirm，Q7=A）D 柱 API／agent 不得代使用者對雲端執行 apply／destroy；產品能力以產生 IaC 與掃描報告為界。人工 high-risk 核准閘不得被解讀為授權平台代 apply。
- **NEVER** 讓版控中存在 path parts 含 `prod`、`production`、`secrets` 的檔案（`git ls-files` 全域掃描；issue #509 已修復機制）。D3 模組／產物路徑亦不得使用完整 path part 名為 `secrets` 的目錄或檔名。
- **NEVER** commit 私鑰或 AWS／Azure／GCP credential 字串（樣式見 `validate_repo_contract.py`；不要把樣式字面複製進 contract 檔）。
- **NEVER** 在未取得 human approval 的情況下執行 production write、IaC apply 或 IAM 變更。
- **NEVER** 直接編輯 `.claude/` 下的 upstream 框架檔來表達專案規則——規則寫入 `aidlc/spaces/<space>/memory/{team,project}.md`。
- **NEVER** 把敏感資料寫進任何 log 或決議紀錄（遮罩為 `[REDACTED]`）。
- **NEVER** 產生雙語分段（`## English Version` 等）。
- **NEVER** 以 repo 內新增的實作程式承載無人值守的流程自動化與外部系統同步（觸發來源判準見 `project.md`）；人在迴圈內的 stage／slash 工具不在此限。
- **NEVER** 把雲端供應商 production、environment-specific secrets、direct production IaC、destructive cloud operations 納入本 repo 範圍（除非新 ADR）（`project.md ## Scope Overrides`）。

<!-- Q3=A：本 intent 不 Mandated CI IaC scan job；工具品牌不預填。 -->
<!-- C1 專屬 Forbidden／Mandated 仍在 memory 生效，本檔不重複全文。 -->
