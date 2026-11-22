# Practices Discovery — 團隊實踐探索問卷

> Stage: practices-discovery（Inception 2.2）· Depth: Standard · Scope: feature
> 基準依據：`aidlc/spaces/default/memory/team.md`、`project.md` 既有團隊決策與 codekb 逆向工程發現。
> 作答方式：本問卷已依據既有團隊實踐與三方支援代理人（Quality, Developer, DevSecOps）盲審共識預填推薦答案（選項 A）。請確認各項實踐方針。

## Sources

- [lead] `team-practices.md`、`evidence.md`（pipeline-deploy-agent 草稿）
- [Q] `contributions/aidlc-quality-agent.md` — 品質代理人盲審：確認專屬單元測試集防護與 CI 閘門覆蓋
- [D] `contributions/aidlc-developer-agent.md` — 開發者代理人盲審：確認 `diagram_builder.py` 封裝與 `provider="compound"` 契約
- [S] `contributions/aidlc-devsecops-agent.md` — 安全代理人盲審：確認 n8n 通訊 fallback 容錯與零外部依賴
- [team] `aidlc/spaces/default/memory/team.md` — 現行團隊實踐基準線

---

## Q1. 工作方式 (Way of Working)

查證：當前分支已採用合規命名 `doreen/feat/a1-compound-cloud-diagram`，commit 訊息沿用繁體中文 conventional commits（如「功能(a1): 新增混合雲三雲架構繪圖支援」），PR 合併維持視情況並用（Bolt 分支 squash、一般 feature PR 維持 merge commit）[team:Way of Working]。

- A. 確認維持現有分支命名、繁中 Commit 與 PR 合併分流實踐（推薦）
- B. 調整分支命名或 Commit 格式（請於 Other 說明）
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q2. 最小可行骨架 (Walking Skeleton)

查證：Build a thin end-to-end slice first? A walking skeleton is a minimal version that runs the whole way through, built first to prove the pieces connect before the real features go in.（是否先建構一個貫穿全鏈路的最小版本來驗證管線連通？）本專案前後端架構、自動部署與測試管線皆已高度成熟，且本功能屬既有 A1 繪圖引擎之功能性擴充，無重新 bootstrap 骨架之必要 [team:Walking Skeleton]。

- A. 確認維持 `skeleton: off`，直接按依賴順序推進實作，省去一次額外 Gate 與驗證輪次（推薦）
- B. 宣告 `skeleton: on`，要求第一個 Bolt 僅打通空的三雲群組骨架並經獨立核准
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q3. 測試姿態 (Testing Posture)

查證：維持 `org.md` 最低 80% line coverage 目標宣稱；針對本次混合雲繪圖功能，建立專屬單元測試集 `backend/tests/test_diagram_builder_compound.py`，完整涵蓋 Hub-and-Spoke 幾何佈局、三雲 XML 群組共存、跨雲折線與協議標籤、以及 n8n compound 上行通訊與 fallback 降級 [Q:Contribution] [team:Testing Posture]。

- A. 確認維持測試目標，並新增專屬單元測試集 `test_diagram_builder_compound.py` 作為核心護欄（推薦）
- B. 測試集與既有 `test_diagram_builder.py` 合併，不另立新檔
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q4. 部署與發布流程 (Deployment)

查證：維持現行 5 道 CI 閘門（`repo-contract` → `frontend lint/tsc -b` → `dump_openapi.py --check` → `backend unittest` → `docker-build`）與自動部署至 `192.168.10.10` 及自動化 rollback 機制；本次變更不新增外部套件或機敏環境變數 [S:Contribution] [team:Deployment]。

- A. 確認維持現有 CI/CD 管線與部署機制，不新增外部依賴（推薦）
- B. 需修改或新增部署步驟
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Q5. 代碼風格與架構邊界 (Code Style)

查證：後端代碼維持 Python 3.11+ / PEP 8 規範與繁體中文 Docstrings，混合雲幾何計算完整封裝於 `diagram_builder.py` 內部，維持純函式無狀態特性；前端遵循 TypeScript 嚴格型別檢查與 ESLint 規範 [D:Contribution] [team:Code Style]。

- A. 確認維持現有代碼風格與模組職責邊界（推薦）
- B. 需調整模組封裝模式
- C. 尚未定義 (Not yet defined)
- X. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

在依據上述答案正式產生 team-practices.md、discovered-rules.md、evidence.md 與 practices-discovery-timestamp.md 前，請確認彙整內容正確。

- **工作方式 (Q1)**: [A] 維持 `doreen/feat/*` 分支命名、繁中 Commit 與 PR 合併分流。
- **骨架驗證 (Q2)**: [A] 維持 `skeleton: off`，無須為成熟管線重複跑 minimal slice。
- **測試姿態 (Q3)**: [A] 新增專屬單元測試集 `test_diagram_builder_compound.py`，覆蓋幾何佈局、三雲 XML、跨雲 edges 與 n8n compound 上行。
- **部署流程 (Q4)**: [A] 維持現行 5 道 CI 閘門與自動部署，零新增外部依賴。
- **代碼風格 (Q5)**: [A] 後端幾何邏輯封裝於 `diagram_builder.py` 保持純函式無狀態，前端維持嚴格型別檢查。

Does this all look correct before I generate the artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct
