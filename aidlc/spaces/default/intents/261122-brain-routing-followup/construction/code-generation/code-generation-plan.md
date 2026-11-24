# Code Generation 計畫：大腦路由延續回答與架構設計提問狀態

## Summary

- Builds: 路由帶對話歷程並以結尾截斷；架構設計只回提問時不判失敗、復原不在舊圖上放行；新開 ADR-0025
- Touches: backend/services/intent_routing_{decisions,context,port}.py、work_orchestrator{,_capabilities,_rules}.py、對應 tests、本 intent 的 decisions/0025
- Tests: 約 10 個 unittest（含 1 個 Hypothesis 性質測試、1 個復原回歸）；全後端套件維持綠燈

## 背景與現況

本 intent 為事後補走流程。分支 `danniel/fix/brain-routing-followup-context` 的工作樹已含下列修正（未 commit），本計畫將它們列為**已實作、待驗證**的步驟，並補上 requirements 新增的部分：

| 需求 | 現況 |
|---|---|
| FR1.1 Decisions `state` 帶最後 6 則歷程 | 已實作（`intent_routing_decisions.build_state`、`intent_routing_port.DecisionsRoutingPort.route`） |
| FR1.2 指示文字附延續規則 | 已實作（`CONTINUATION_RULE`） |
| FR1.3 結尾 400 字截斷（兩條路徑） | **未實作**：兩處目前都取開頭 |
| FR1.4 使用者這一句在最前、截斷無條件 | 已實作，待補性質測試 |
| FR2.1–FR2.4 等使用者回覆不判失敗、等待者不在舊圖執行 | 已實作（`judge_a1`、`_complete_awaiting_reply`、`_advance_dependents`） |
| FR2.5 復原掃描套用同一規則 | **未實作** |
| FR3.1 新開 ADR | **未實作** |
| FR3.2 `build_state` docstring | 已實作 |
| NFR2 Hypothesis 性質測試 | **未實作** |

## 影響範圍（Blast radius）

| 檔案 | 變更 | 影響 |
|---|---|---|
| `backend/services/intent_routing_decisions.py` | 已改＋結尾截斷 | 中：staging 路由輸入；`PRIMARY_CRITERIA` 不動 |
| `backend/services/intent_routing_context.py` | 結尾截斷 | 低：本機工具呼叫路徑的 prompt |
| `backend/services/intent_routing_port.py` | 已改（傳入歷程） | 低 |
| `backend/services/work_orchestrator_capabilities.py` | 已改（`awaiting_reply`） | 中：A1 判定 |
| `backend/services/work_orchestrator.py` | 已改＋復原規則 | 中：工作項狀態與等待者推進 |
| `backend/services/work_orchestrator_rules.py` | 已改（兩句新文字） | 低：容量測試自動涵蓋所有樣板 |
| `backend/tests/test_work_orchestrator_flow.py` | 新測試＋**修正既有復原測試的測資** | 既有 `test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans` 把架構設計改為「完成」卻未存回圖；FR2.5 之後此狀態代表「還在等回覆」，測資須補 `dispatchStage: result_persisted` 才符合該測試原意 |
| 其他測試檔 | 新增／更新 | — |

不碰：前端、`ws-contract.json`、OpenAPI、資料庫 schema、環境變數（故不觸發 `schema_rbac.sql`／`DEPLOY.md`／`LOCAL-DEV.md` 同步）。

## Testing Contract

```json
{
  "version": 1,
  "methodology": "custom",
  "source": "team",
  "ordering": "先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。",
  "scope": "bugfix",
  "test_strategy": "minimal",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. Specific\nmethodology — TDD, BDD, ATDD, or classic test-after — is captured by the\ntesting-strategy stage when it ships.\n\nUntil then, our default per scope is:\n- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside\n  code; minimum 80% line coverage; tests run in CI before merge.\n- `bugfix`, `security-patch` → regression test for the specific\n  bug/vulnerability; existing test suite must remain green.\n- `poc`, `refactor`, `workshop` → existing test suite remains green;\n  no new test floor required.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: custom\n- **Ordering**: 先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。\n- **Coverage Target**: 維持 `org.md` 最低 80% line coverage 目標宣稱。\n- **變更護欄義務**:\n  - **A — 授權矩陣變更需 allow/deny 雙向測試**：任何 role_permissions seed 變更需雙向驗證。\n  - **B — HTTP 端點變更需 TestClient 測試**：斷言 status code 與 response_model。\n  - **C — 前端資料形狀變更需 e2e 斷言**：涉及前端展示之結構變更需 Playwright 驗證。\n  - **D — 混合雲專屬測試集**：新增 `backend/tests/test_diagram_builder_compound.py`，完整斷言三雲 XML 群組、Hub-and-Spoke 空間佈局、跨雲直角折線與協議標籤、以及 n8n compound 上行與 fallback 降級。"
    },
    {
      "layer": "project",
      "text": "**Property-based testing 為 hard constraint**（ADR-0006）。下列核心模組的測試必須包含 property-based 測試，不得只有 example-based：IaC generator、cost calculator、agent routing。其餘模組沿用 `org.md` 的預設門檻。"
    }
  ],
  "obligations": {
    "strategy": "minimal",
    "strategy_volume": [
      "One verifiable test per requirement at the narrowest effective level.",
      "At least one happy-path unit test per component.",
      "Unit tests are the default; a bugfix/security scope floor may require an integration or E2E regression when that is the narrowest level that reproduces the defect."
    ],
    "scope_floor": [
      "Include a targeted regression for the bug or vulnerability.",
      "Keep the existing test suite green."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "custom",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Custom ordering - 先於 `backend/tests/test_diagram_builder_compound.py` 實作單元測試驗證 Hub-and-Spoke 幾何與 n8n 通訊，再進行前端 Toolbar 選單與對話串接。",
      "Implementation and tests - preserve that exact ordering; do not convert it to layer-local TDD.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:ad541167cfcb4cc6f72f9b724198401eada1710f4c69c0f32b852220c2e04f2a",
  "contract_sha256": "sha256:35fb80d939c7876a836ce12d3ad4465a463bfa0cebfdb33d2650a78a5ddc364d"
}
```

**Custom ordering 的適用說明**：team 層的 ordering 文字針對的是混合雲繪圖（`test_diagram_builder_compound.py` 先於前端），本 intent 不碰繪圖也不碰前端，該順序在此沒有可對應的層；依其精神（後端單元測試先於任何前端串接）沿用，不轉成逐層 TDD。本 intent 只有後端業務邏輯層，各步驟以「實作與該步驟的測試一起完成、跑綠」推進。

## 步驟

- [x] **Step 1：專案結構確認**——不新增模組或設定檔；確認上表所列檔案為唯一變更面（`git status` 與 `git diff --stat` 對照）。追溯：全部 FR。
- [x] **Step 2：測試 runner 確認**——以 `unit-test-instructions.md` 的指令在修改前先跑一次相關測試檔，記錄基準（預期全綠，因已實作部分已有測試）。追溯：NFR3。
- [x] **Step 3：FR1.3 結尾截斷（Decisions 路徑）**——`intent_routing_decisions.build_state` 每則歷程改取 `text[-message_chars:]`。測試：`test_intent_routing_decisions.py` 新增「1000 字提問、選項在最後」案例（含選項、不含開頭）。追溯：FR1.3。
- [x] **Step 4：FR1.3 結尾截斷（工具呼叫路徑）**——`intent_routing_context.build_routing_prompt` 同樣改取結尾。測試：`test_intent_routing_context.py` 新增同形案例；既有 `MinimalContextTest` 維持綠燈。追溯：FR1.3。
- [x] **Step 5：NFR2 性質測試**——`test_intent_routing_decisions.py` 新增 Hypothesis 測試：對任意訊息序列（任意長度、任意字元含換行）與使用者句子，`state` 滿足 (a) 以「使用者這一句：」開頭且其後為使用者句子（`text_chars` 內）；(b) 歷程行數 ≤ 6，且為原序列最後 min(6, n) 則、順序不變；(c) 每則本文長度 ≤ 400 且為原文結尾。追溯：NFR2、FR1.1、FR1.3、FR1.4。
- [x] **Step 6：FR1.1／FR1.2／FR2.1–FR2.4 驗證既有實作**——跑既有新增的測試（`test_follow_up_answer_carries_the_recent_conversation_into_state`、`A1JudgementTest` 兩案、`ArchitectureAwaitingReplyTest` 兩案、`PhraseTest`），全綠。追溯：FR1.1、FR1.2、FR2.1–FR2.4。
- [x] **Step 7：FR2.5 復原規則**——`work_orchestrator._recover` 第二輪：被等待項為架構設計、狀態為「完成」且 `dispatchStage != result_persisted` 時，以 `as_status=失敗`、`failure_phrase="dependency_awaiting_reply"` 推進等待者（沿用 `_advance_waiter` 的 `failure_phrase` 參數）。測試：`test_work_orchestrator_flow.py` 的 `RecoveryTest` 新增兩案——(a) `request_sent` 時成本以「還在等你回覆」結束且未呼叫成本 API；(b) `result_persisted` 時成本照常開始。追溯：FR2.5。
- [x] **Step 8：修正既有復原測試測資**——`test_orphan_waiter_is_advanced_once_even_with_two_concurrent_scans` 的 `arch.update` 補上 `"dispatchStage": "result_persisted"`，使其仍表達「架構設計已完成並存回圖」的原意；斷言不變。追溯：NFR3。
- [x] **Step 9：突變驗證**——對 Step 3、4、5、7 與既有 FR1.1／FR2.1／FR2.4 的實作逐一改回錯誤行為，確認對應測試變紅、還原後變綠；結果寫入 `code-summary.md`。追溯：NFR4。
- [x] **Step 10：全套回歸**——`cd backend && python3 -m unittest discover -s tests -t .` 全綠（基準 1624 個、3 skip，加上本計畫新增）；`python3 scripts/validate_repo_contract.py`、`python3 scripts/validate_env_contract.py` 通過。追溯：NFR3。
- [x] **Step 11：FR3.1 ADR**——新增 `aidlc/spaces/default/intents/261122-brain-routing-followup/inception/decisions/0025-decisions-routing-carries-conversation-history.md`（繁中；Context、Decision、Consequences、Alternatives Rejected；含 ADR-0006 四面向；註明修訂 ADR-0024「不帶歷程」一項，ADR-0024 本文不改；記錄 NFR1 staging 重量測為待辦）。追溯：FR3.1。
- [x] **Step 12：文件與追溯**——`code-summary.md`、`traceability.json`（直接以 FR／NFR ID）。追溯：全部。

## 不在本計畫

- NFR1 staging 重新量測：需部署後執行，屬 build-and-test 之後的部署驗證（requirements OQ1）。
- 審查 R-01～R-05（已於 requirements 閘門以 Accepted risk 核可）：不另行擴大範圍；其中 R-01（提示訊息為最後一則系統訊息）會在 NFR1 量測的「只回 A」案例中以真實歷程形狀（提問、提示依序為最後兩則）作為輸入，以實測驗證其影響。
