# Team-Level Rules

> This team's affirmed practices and corrections. Loaded after `org.md` as
> strict-additive guidance; contradictions with broader policy are rejected.
> Populated by the practices-discovery affirmation gate. Edit at the gate,
> not directly.
>
> Cloud-360 note: 本層為本專案自有規則（見 ADR-0011），以繁體中文撰寫；
> `org.md` 為 upstream 框架預設層，維持英文。識別字、路徑、指令維持原文。
> 下文的 `<record>/` 是作用中 intent 的 record 目錄簡寫，即
> `aidlc/spaces/<active-space>/intents/<slug>/`。

## Way of Working

### Branch 命名
所有新建分支必須遵循 `<uploader>/<type>/<slug>`：
- `<uploader>`：開分支者慣用的英文小寫 handle（例如 `doreen`、`danniel`）。
- `<type>`：限定 `feat`、`fix`、`docs`、`chore`、`refactor`、`test`。
- `<slug>`：英文小寫、連字號分隔、3–5 個詞概述變更目的。
- 本次功能採用合規分支：`doreen/feat/a1-compound-cloud-diagram`。

### Commit message 與 PR 標題
一律使用**繁體中文**，包含 type、描述、body 與 PR 標題。格式沿用 conventional commits，type 改為中文（如 `功能(a1): 新增混合雲三雲架構繪圖支援`）：
- `功能` (feat)、`修正` (fix)、`文件` (docs)、`格式` (style)、`重構` (refactor)、`測試` (test)、`雜項` (chore)。

### PR 合併方式
- **Construction Bolt 分支**：走 **squash-merge**，每個 Bolt 對應 `ut` 上一個 commit。
- **一般 feature／fix／chore PR**：維持 **merge commit**，延續既有實踐。

## Walking Skeleton

- **Stance**: `skeleton: off`
- **Rationale**: 本專案已有可運行的完整前後端、5 道 CI 閘門、自動部署與多組 agentic workflows。本次混合雲繪圖為既有 A1 繪圖引擎之功能擴充，無須重複打通端到端最小骨架，直接依技術依賴鏈推進實作。

## Testing Posture

- **Methodology**: custom
- **Ordering**: 先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。
- **Coverage Target**: 維持 `org.md` 最低 80% line coverage 目標宣稱。
- **變更護欄義務**:
  - **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 role_permissions seed 變更需雙向驗證。
  - **B — HTTP 端點變更需 TestClient 測試**：斷言 status code 與 response_model。
  - **C — 前端資料形狀變更需 e2e 斷言**：涉及前端展示之結構變更需 Playwright 驗證。
  - **D — 混合雲專屬測試集**：新增 `backend/tests/test_diagram_builder_compound.py`，完整斷言三雲 XML 群組、Hub-and-Spoke 空間佈局、跨雲直角折線與協議標籤、以及 n8n compound 上行與 fallback 降級。

## Deployment

- **CI 管線**：`repo-contract` → `frontend` (lint + `tsc -b` typecheck + build) → `OpenAPI spec drift 檢查` (`dump_openapi.py --check`) → `backend` (import smoke + unittest) → `docker-build`。
- **CD 管線**：PR closed (merge) 到 `ut` 或手動 `workflow_dispatch` 自動部署至 `192.168.10.10`（逾時 30 分鐘，`concurrency: deploy-10-10`）。
- **Rollback 機制**：部署失敗自動還原 last-good 並開立 revert PR，自癒修復。
- **相依性邊界**：本 intent 不新增任何非標準之外部依賴或未受控環境變數。

## Code Style

- **Backend**：Python 3.11+，遵循 PEP 8 規範，全模組採用完整型別標註 (`from __future__ import annotations`) 與繁體中文 Docstrings。幾何計算與 XML 組裝邏輯完整封裝於 `diagram_builder.py` 內部，維持純函式無狀態特性。
- **Frontend**：TypeScript + React 18，遵循 ESLint 規範與嚴格型別檢查 (`tsc -b`)。元件保持單一職責，狀態同步透過 Context 與標準事件傳遞。
## Forbidden

- ❌ **不得產生雙語分段**：文件不得保留或新增 `## 中文版` / `## English Version` 標題；文件為單一語言（繁體中文）。`scripts/validate_repo_contract.py` 會擋下 record 內殘留的 `## English Version`（CI 紅燈）。
- ❌ **不得自動寫 decisions log**：使用者沒有明確要求時，不要寫 `<record>/decisions-log.md`。AIDLC 階段事件由引擎寫進 `<record>/audit/` 的 per-clone shard，不要手動編輯；架構級決策開 ADR。舊的 per-turn `.ailog/` 機制已於 PR #17 整體移除，不得重建。
- ❌ **不得把敏感資料寫進任何 log 或決議紀錄**：token、API key、production credential 一律遮罩為 `[REDACTED]` 並提醒使用者。

## Mandated

- ✅ **文件語言：繁體中文**（ADR-0009，取代 upstream 的 bilingual-docs 與 ADR-0005）。AI-DLC 工作產出（`aidlc/spaces/*/intents/**/*.md`）、`CLAUDE.md`、`aidlc/spaces/*/memory/team.md`、`aidlc/spaces/*/memory/project.md` 一律繁體中文。例外：程式碼、指令、識別字、專有名詞維持原文；upstream 框架自身的英文檔（`.claude/**`、`aidlc/spaces/*/memory/org.md`、`phases/*.md`）不在此限。修改既有文件時，若見殘留英文版分段一併清除。
- ✅ **決議紀錄（on-demand）**：當使用者**明確要求**記錄當下對話的決議時（「記錄這個決議」、「把這個決定記下來」、「log this decision」等；以判斷而非死記字串，不確定就先反問），把決議追加到 `<record>/decisions-log.md`，append-only、繁體中文，每筆為 H3：

  ```markdown
  ### YYYY-MM-DD HH:MM:SS +TZ — <短標題（5–10 字）>

  **Decision / 決議**: <1–3 句獨立可懂的決議內容>
  **Context / 背景**: <為何有這個決議；簡短背景>
  **Trigger / 觸發語**: <使用者要求記錄時的原文>
  **Related / 相關**: <PR、ADR、branch、commit、issue 連結；無則 N/A>
  ```

  短標題概述決策本身，不要寫成「使用者問 X」。Decision 區塊要能脫離對話上下文獨立理解。
- ✅ **小步前進**：每個 stage 完成後產出 stage-completion summary，附 extension compliance（compliant / non-compliant / N/A 與理由），等使用者確認再進下一階段。
- ✅ **問題格式**：向使用者提問時使用 A/B/C/D/E 多選題與 `[Answer]:` tag。
- ✅ **內容驗證**：建檔前驗證 Mermaid 語法、ASCII 圖與特殊字元跳脫；Mermaid 一律附文字 fallback。

## Corrections

<!-- Self-learning loop appends here. -->
- 下游 stage 經人工確認的語意變更（如欄位語意由「最後登入」重新定錨為「最後活動」），不回改已核可的上游 artifact；以該 stage 問題檔的確認紀錄為準向下游傳遞，避免重開上游的核可狀態 (learned 2026-08-03) <!-- cid:feasibility:c3 -->
