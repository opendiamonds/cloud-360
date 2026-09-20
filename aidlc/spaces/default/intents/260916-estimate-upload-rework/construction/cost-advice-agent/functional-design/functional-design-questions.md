# Functional Design 問答：U7 `cost-advice-agent`

本 Unit 是 **service**：`CostAdviceAgent`／`AdviceOrchestrator`、`Advice` 正文與狀態、SSE 訂閱；可選呼叫 U5 查價。

**不含**：SPA（U8／U9）、上傳持久化（U2）、查價 Port 本體（U5）、LangGraph 執行骨架（U6）。

## Sources

- **[S1]** U7：`unit-of-work.md` — 三類建議、SSE、5 分鐘逾時、可選 U5
- **[S2]** C3 AsyncAPI：`GET .../advice/stream`；逾時 `type=timeout`；斷線不取消背景
- **[S3]** C2：`GET .../advice` 快照；`advice_status` 四態
- **[S4]** FR5.1–5.4、FR5.10；NFR1／NFR2；U2 enqueue hook；U6 `invoke_graph`／`astream_graph`
- **[S5]** OQ-CD2（逾時 status）、OQ-CD3（SSE 是否進 openapi）、OQ-DD3（generating 卡住清理）

---

## Q1 模組落點

- **A.** `backend/cost/advice_orchestrator.py`（生命週期／enqueue 實作）＋`cost_advice_agent.py`（圖節點／提示）＋`advice_stream_router.py`（SSE）；由 `main.py` 掛在 `/api/cost/v1`；`estimate_intake_service.enqueue_advice_job` 改呼叫 orchestrator（建議）
- **B.** 全部塞進單一 `cost_advice.py`
- **C.** 路由放 `services/`，cost 只留 agent 純函式
- **X.** Other

[Answer]: A — orchestrator＋agent＋SSE router；替換 enqueue hook

---

## Q2 背景執行模型

- **A.** **同 process 執行緒／可配置 worker**：enqueue 後非同步跑建議；重啟可能卡住 generating → 啟動或讀取時依 `started_at` 逾時標 failed（承接 OQ-DD3）（建議）
- **B.** 外置佇列（Redis／RQ）——本期新基礎設施（違反 NFR8 精神，不建議）
- **C.** 僅同步於 SSE 連線內跑（斷線即停——違反 F1=B）
- **X.** Other

[Answer]: A — 同 process 非同步；逾時清理 generating

---

## Q3 逾時後 `Advice.status`（OQ-CD2）

- **A.** 標 **`failed`**，`unavailable_reasons` 含 `timed_out`（或等價鍵）；SSE 送 `type=timeout` 後關閉（建議；不新增 `timed_out` 枚舉以免 C2／U9 分叉）
- **B.** 新增 status=`timed_out`
- **C.** 維持 `generating` 直到人工清理
- **X.** Other

[Answer]: A — status=failed＋unavailable_reasons.timed_out；SSE type=timeout

---

## Q4 重複觸發／去重

- **A.** `Advice.estimate_set_id` 已 UNIQUE／PK：若已 `generating` 則 enqueue **no-op**；若 `completed`／`failed` 則**不**自動重跑（需未來顯式 API 才重產）（建議）
- **B.** 每次上傳覆蓋重跑（含 completed）
- **C.** 允許並行多 Advice 列（違反 UNIQUE）
- **X.** Other

[Answer]: A — generating 去重 no-op；completed／failed 不自動重跑

---

## Q5 查價（U5）掛接

- **A.** Orchestrator **可選**呼叫 `fetch_hourly`；失敗／Miss／未接 → 建議繼續，正文**不得**捏造現價；可在 quality／saving 註明「無目錄價」（建議；單元相依不含 U5）
- **B.** 強制查價成功才產出建議
- **C.** 本期完全不呼叫 U5
- **X.** Other

[Answer]: A — 可選查價；失敗不中止、不捏造現價

---

## Q6 SSE 是否進 `openapi.json`（OQ-CD3）

- **A.** **是**——以 `text/event-stream` 操作記載於 OpenAPI（型別／路徑給 U9）；細節以 C3 AsyncAPI 為事件語意真實來源（建議）
- **B.** 否——僅 C3 AsyncAPI；U9 手維型別
- **X.** Other

[Answer]: A — SSE 路徑進 openapi.json；事件語意以 C3 為準

---

## Consolidated Summary Confirmation

**U7 `cost-advice-agent` 行為定案**

| 項 | 定案 |
|---|---|
| 模組 | orchestrator＋agent＋SSE router；替換 enqueue（Q1=A） |
| 執行 | 同 process 非同步；逾時清 generating（Q2=A） |
| 逾時 status | failed＋timed_out 理由；SSE timeout（Q3=A） |
| 去重 | generating no-op；完成／失敗不自動重跑（Q4=A） |
| 查價 | 可選；失敗不中止、不捏造（Q5=A） |
| OpenAPI | SSE 路徑納入（Q6=A） |

[Answer]: Looks correct

確認後產出 entities／rules／functional-spec／traceability。
