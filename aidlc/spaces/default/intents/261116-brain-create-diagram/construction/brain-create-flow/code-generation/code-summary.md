# Code Summary — U2 brain-create-flow

> 全部單元的總覽、完整測試結果與部署前置見 `../../code-generation/code-summary.md`。分支 `danniel/feat/brain-create-diagram`，未 commit。

## 檔案

| 檔案 | 改動 |
|---|---|
| `backend/services/brain_diagram_creation.py`（新） | `decide`、`make_title`、`creation_change_texts`（純函式）；候選建構（純函式）；`create_draft`、`record_creation`、`load_target_facts`、`list_owned_systems`（I/O） |
| `backend/services/intent_routing_decisions.py`、`intent_routing_port.py`、`intent_routing_types.py`、`intent_routing.py` | `wants_new_diagram` 題併入同一次請求；`new_diagram_probability` 留在 `IntentDecision`（行程內、不 repr、不進觀測） |
| `backend/services/work_orchestrator_capabilities.py` | `CapabilityError.draft_rejected`；`create_diagram`；`put_diagram(finalize=…)` |
| `backend/services/work_orchestrator_rules.py` | `PHRASES["draft_rejected"]`、`failure_for_status` 的 409 分支 |
| `backend/services/brain_ws_contract.py`、`ws-contract.json`、`frontend/src/types/ws-contract.d.ts` | `ClarifyPayload.kind` 加四值；`ClarifyCandidate` 加 `systemId`／`diagramId`／`action` |
| `backend/services/brain_gateway_rules.py` | `TargetRef.diagram_id`（選填） |
| `backend/services/brain_gateway.py` | 新建流程（判定 → `user_can_arch` 預檢 → 建草稿 → 記變更紀錄 → 切換對象 → 交辦）；四種反問與點選（候選集合比對 ＋ `set_work_target` 重新驗證 ＋ 失效重列）；`_reread_target` 比對 `diagram_id`；log 白名單加非內容欄位；`build_brain_gateway` 注入 `CapabilityClient` |

## 本單元的測試

- 36 個後端測試（純函式 18，含 6 個 @given；流程 18）＋ 同步既有測試；執行指令見 `unit-test-instructions.md`。
- 後端全套變更後 `Ran 1601 tests … OK (skipped=3)`（stage 層級實跑結果）。

## 與計畫的偏差

- **判定表第三列與 FR6.3 衝突的處置**：作業對象是**草稿**且 p ≥ t 時判為「修改（接著畫同一張）」而非新建——同一句「幫我畫一張…」的 p 必然 ≥ t，照表會違反 FR6.3b 的「再說一次不另建」。已在 `decide` docstring 標〔推導〕，可推翻。
- **新反問說明文字的落點**：`ClarifyPayload` 沒有文字欄，且輪次狀態機不允許先送 token 再送 clarify；故 FR3.6 的「其餘請用切換對象選取」附在最後一筆候選的標籤後；FR3.5 失效時「重新列出」做到了，但「回覆說明」那一句無處可放（未做）。
- **NFR4 的判定類別記在閘道事件 `diagram_decision`**，不在路由觀測事件——判定需要作業對象事實，只有閘道有。
- **`wants_new_diagram` 缺題時為 `None`（視為不明）**，不判 `MalformedRouting`；出現但越界仍拒絕。
- **閘道新建流程以 `diagram_client_factory` 是否注入為開關**：`build_brain_gateway` 一律注入；既有閘道測試的替身組裝不注入，行為不變。

## 修訂 1（2026-11-19 核可關卡要求修改；計畫 Step 21–25）

來源：本單元審查 `reviews/review-02.md` R-01、R-03、R-04、R-05、R-06、R-09、R-10；整體審查 R-05、R-06。偏差 #2 已由使用者接受，未改。

| Step | 檔案 | 改動 |
|---|---|---|
| 21 | `backend/services/brain_gateway.py` | 常數 `DIAGRAM_CREATE_TIMEOUT_SEC = 15.0`（模組常數，不新增環境變數）與建構參數 `diagram_create_timeout_sec`；`_create_and_dispatch` 的建圖呼叫包在 `self.timing.wait_for(...)`；`asyncio.TimeoutError` → `CREATE_UNKNOWN_MESSAGE`、不重試、不交辦，log 事件 `diagram_create_timeout`（只有 turnId） |
| 22 | `backend/services/brain_gateway.py` | `_on_select` 意圖分支重建 `IntentDecision` 時帶回 `pending.decision.new_diagram_probability` |
| 23 | `backend/models.py`、`backend/services/rbac.py`、`backend/services/work_orchestrator_capabilities.py`、`backend/services/brain_gateway.py` | `ARCH_FORBIDDEN_DETAIL_PREFIX`（`rbac.require_arch_action` 改用它組 detail，文字不變）；`CapabilityError.arch_forbidden`（403 且 detail 以前綴開頭，只存布林）；閘道 403 分流：缺架構權限 → `NEED_ARCH_EDIT_MESSAGE`，其餘 403 → 新常數 `CREATE_FORBIDDEN_MESSAGE` |
| 24 | `backend/tests/test_brain_diagram_creation.py`、`backend/tests/test_brain_gateway_startup.py` | 性質 1 改為直接斷言結果（p ≥ t 不得 MODIFY／NO_DIAGRAM_TO_MODIFY，草稿作業對象除外且此時必為 MODIFY；p ≤ 1−t 不得 CREATE）；性質 4 改為「同區兩個 p（不明區含 None）結果相同」，p 依區域構造；新增 `build_brain_gateway` 注入 `diagram_client_factory` 的接線測試 |
| 25 | `backend/services/brain_diagram_creation.py` | `TITLE_MAX_CODEPOINTS = 200`（與 `collab_router.MAX_DIAGRAM_TITLE_CHARS` 以測試鎖相等）；`_truncate_graphemes` 同時受 30 可見字元與 184 碼位（扣「 架構圖」與重名後綴預留 12）限制，以整個可見字元為單位停止；開頭落單的組合記號／ZWJ 先去掉 |

新增測試（`test_brain_diagram_creation_flow.py`）：建圖真的卡住→逾時後同一連線仍可處理下一則；403 兩種文字；意圖反問後保留 p（FR2.4）；端點層級的 403 分類（FinOps_Analyst → `arch_forbidden=True`；撤掉 K2 edit → `False`）。

**與計畫的偏差（修訂 1）**

- **Step 23 的「既有文字」**：repo 內沒有對應 K2 403 的既有文字；`PHRASES["forbidden"]` 套上能力名會變成「你沒有使用架構設計的權限」，又指回架構權限。故新增 `CREATE_FORBIDDEN_MESSAGE`（不指向角色申請、不含系統名）。需要人確認文字。
- **Step 21 的期限值 15 秒由本站選定**：審查要求「數值由人定」；15 秒遠高於同進程 ASGI 一次 INSERT 的正常值，可在關卡上調整。
- **Step 25 取名在單一可見字元超過碼位預算時**：不收入主題、退回「<系統名> 架構圖」，而不是截斷該字元。
- **審查 R-04 後半（`pick_system` 候選未依 K2 edit 過濾）未處理**：計畫 Step 23 只要求文字分流；點到不可掛載的系統時現在會得到正確的說明。
- **`models.py` 本輪也被本單元改動**（加 `ARCH_FORBIDDEN_DETAIL_PREFIX`），但它已列在 `diagram-drafts` 的 manifest，未在本單元 manifest 重複列出。
