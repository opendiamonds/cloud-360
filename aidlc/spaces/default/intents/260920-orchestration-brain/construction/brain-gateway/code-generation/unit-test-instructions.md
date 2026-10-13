# Unit Test Instructions — `U13 brain-gateway`

## 一、框架與設定

- 後端：Python 內建 `unittest` ＋ `unittest.mock` ＋ `hypothesis`（純函式性質）＋ `starlette.testclient.TestClient.websocket_connect`，**不是 pytest**。
- 非同步：`unittest.IsolatedAsyncioTestCase`；時間一律經建構子注入的 `GatewayTiming`（可推進的 `monotonic`、立即返回的 `sleep`），不依賴第三方假時鐘工具。
- Redis：既有替身（`tests/test_session_store_behaviour.py` 的形狀）。**替身證明不了真實原子性與真實網路逾時**，在 code-summary 揭露。
- DB：`backend/tests/helpers.py` 的 in-memory SQLite；授權走真實 `get_user_from_token`、`user_can`、`mint_principal`，**不 mock `user_can`**。
- 嵌入：替身拋**實際**例外類型 `EmbeddingProviderUnavailable`（以 `raise … from httpx.ReadTimeout/ConnectError` 包裝），另一支契約測試以真實 `OllamaAdapter` 的包裝方式（不連網）鎖住例外鏈形狀。
- 限制揭露：TestClient 下「不 accept」表現為關閉碼 1000，真實 uvicorn 為 HTTP 403。
- 前端：本單元只做 DEMO 移除與 e2e 落地頁改寫，以 `npm run lint`、`npx tsc -b` 驗證；e2e 由 CI `ui-regression` 執行。

## 二、本單元的執行指令（皆限定本單元的檔案）

在 `backend/` 目錄：

```bash
# 就緒檢查（Step 2）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_session_store_behaviour -v

# 本單元測試（Step 4／6／8）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_ws_contract tests.test_brain_gateway_rules tests.test_brain_gateway_handshake tests.test_brain_gateway_turn tests.test_brain_gateway_fanout tests.test_brain_gateway_memory tests.test_brain_gateway_limits tests.test_brain_gateway_startup -v

# 受影響的既有測試（跨單元修改後須仍綠）
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tests.test_dump_ws_contract tests.test_intent_routing_structure tests.test_work_orchestrator_flow tests.test_session_store_behaviour -v

# 契約閘門
python3 scripts/dump_ws_contract.py --check
python3 scripts/dump_openapi.py --check
```

在 `frontend/`：

```bash
npm run check:ws-types
npm run lint
npx tsc -b
```

## 三、測試清單與數量（standard：每元件 5–8 個；純函式含 PBT）

| 檔案 | 元件 | 案例 |
|---|---|---|
| `test_ws_contract.py`（修改） | 契約 | §十一之二 的既有行修改；C-1..C-7 每欄正向一案、錯值負向一案 |
| `test_brain_gateway_rules.py` | 純函式 | `parse_subprotocol_offer`（順序不限、`split('.',1)`、缺協定名、空白與逗號邊界）；session key 往返；`resolve_segment`；`TurnLedger`（每輪恰一終止、零內容 → EMPTY_RESPONSE）；`error_for` 封閉對應；`match_referent`；`scan_targets_in_utterance` 性質 (a) 命中皆為目錄中完整名稱 (b) 被較長名稱覆蓋者剔除 (c) 不同專案同名不互相比較 |
| `test_brain_gateway_handshake.py` | 握手 | 雙子協定 → 只回送 `cloud360.brain.v1`；缺協定名 → 不 accept；token 只在 query string → 拒絕（AC8.1.3 兩案）；4401／4403／4400；`record=True` 更新最後活動（AC8.1.2）；併發 N+1 握手不超過全域 200／每人 10 上限；握手納入限流 |
| `test_brain_gateway_turn.py` | 一輪 | prompt_guard 命中 → 固定訊息＋`done` 且不呼叫 LLM、不寫歷程；clarify `kind=intent` 與 `kind=target`；句中指名系統（AC1.1.5，含未選專案、專案 > 50）；反問選定後原句掃描命中一律反問；Redis 不可用：握手 1011、連線後該輪 `error(INTERNAL_ERROR)` 且連線保留 |
| `test_brain_gateway_fanout.py` | 扇出 | 多連線皆收狀態訊息；推播只給本人（AC7.1.1–7.1.3）；載入中佇列順序與溢位 1011；送出失敗的連線被 close(1011)；`emit_turn` 新 turnId 以 `done` 終止 |
| `test_brain_gateway_memory.py` | 記憶 | 預取經 ContextVar 交給 U11；熔斷只在逾時／連線類開啟；半開試探遇 `BUSY_SKIPPED` 清除 probing 且熔斷可恢復；`CancelledError` 重拋；episodic 只在有交辦且 `done` 後背景寫入、失敗只記 WARNING；執行器為實例屬性、shutdown 只關自己的 |
| `test_brain_gateway_limits.py` | 限流與重驗 | 每人 20 則／60 秒、每連線 120 訊框／60 秒（關閉後重連不重置）；訊框 > 65536 拒絕且計入關閉門檻；每則重驗與 60 秒重驗（停用帳號 → 4401）；AST 禁止直呼計時函式 |
| `test_brain_gateway_startup.py` | 啟動 | 建立順序（`configure_intent_routing_env` 之後、`init_db` 之前）；缺 `REDIS_*` 啟動失敗；單行程守門（`WEB_CONCURRENCY`／`UVICORN_WORKERS`）；`/api/brain/ws` 恰一條路由；DEMO 模組不存在 |

## 四、突變驗證（每項：套用 → 確認紅 → 還原 → 確認綠）

執行突變時設 `HYPOTHESIS_NO_SHRINK=1`（測試設定讀它以關閉 shrinking）。

| 突變 | 對應帶入項 | 預期紅燈 |
|---|---|---|
| 句中掃描改回子字串比對 | 1 | rules 性質 (b)、turn「測試這張圖」案例 |
| 佔位計數移到 accept／登錄之後 | 7 | handshake 併發 N+1 |
| 熔斷改為監聽 httpx 例外而非例外鏈 | 8 | memory 逾時開啟熔斷案例 |
| `BUSY_SKIPPED` 出口不清 probing | 18 | memory 熔斷可恢復 |
| `run` 以 `except BaseException` 吞取消 | 19 | memory 取消重拋 |
| 最後一條連線關閉時刪除頻率視窗 | 20 | limits 重連不重置 |
| 送出失敗只取消登錄不 close | 21 | fanout close(1011) |
| 執行器改回類別屬性 | 22 | memory 兩個實例 shutdown 互不影響 |
| 回送 `bearer.<jwt>` 子協定 | GW1 | handshake 只回送協定名 |
| `record=False` | AC8.1.2 | handshake 最後活動 |

結果記入 `code-summary.md`。

## 五、覆蓋率

repo 無覆蓋率量測機制（`team.md`）；以每元件 5–8 案、純函式 PBT 與突變驗證為實際門檻，不宣稱百分比。

## 六、Mock 與測試資料

- 身分：測試建立 `User` 並簽發 JWT（既有測試樣板）；角色經 `ensure_role_permissions_seeded(db, force=True)` 播種。
- 專案／系統：經 `HierarchyFacade` 建立，不直接插表；專案 > 50 的案例以迴圈建立。
- U11／U12：以替身取代 `IntentRouter.classify` 與 `WorkOrchestrator`，介面依已交付簽章；不呼叫任何 LLM。
- 唯一標記字串：token、使用者原句各以 `uuid4()` 產生，斷言 log、回應標頭與送出訊息不含它。
