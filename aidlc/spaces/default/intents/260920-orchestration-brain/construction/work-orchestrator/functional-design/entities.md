# Entities — `U12 work-orchestrator`

> 本單元擁有一個實體（`WorkItem`）與兩個值物件。`WorkItem` **不另建資料表**：
> 依 `[WO3]`=A 存放在 `U10` 的大腦工作階段（同一個 Redis key、同一個到期時間），
> 由本單元在 `U10 SessionStore` 上新增的讀寫方法承載（跨單元修改，見 `functional-spec.md` 第六節）。
> 傳輸形狀以已交付的 `brain_ws_contract.WorkItem` 為準（`backend/services/brain_ws_contract.py:132`）；
> 本檔多出的欄位是**伺服器內部欄位**，不送到前端。
>
> **修訂 1（2026-10-12，`reviews/review-01.md`）**：儲存形狀改為「每個工作項一個欄位」（R-10）；
> `dispatchStage` 增 `persisting`（R-10）；新增 `deadlineAt`、`segmentId`（R-03、R-07）；
> `requestText` 寫明來源（R-07）；`targetSystemId` 改為「目標圖集合的來源」（R-01）。
>
> **修訂 2（2026-10-12，`reviews/review-02.md`）**：比對後寫入同時比對 `status` 與 `dispatchStage`（R-10）；
> 等待中項目的復原與「被等待者停掉」依能力分流（R-03、R-08）。

```yaml
entities:
  - name: WorkItem
    description: >
      一次交辦的單位。一句話經路由層判讀出 N 個意圖，就落成 N 個工作項（[RA:FR5.1]）。
      每個工作項有自己的狀態、交辦的能力，以及停掉時是否留下東西的誠實說明。
    owner: U12 work-orchestrator
    storage: 大腦工作階段的 Redis key 內，每個工作項一個欄位 wi:<workItemId>（[WO3]=A；與 session 同一個到期時間；BR52.4）
    attributes:
      - name: workItemId
        type: string
        required: true
        unique: true
        constraints: uuid4 字串；伺服器產生，correct_work_item 以它定址
      - name: sessionKey
        type: string
        required: true
        constraints: 所屬大腦工作階段；由 U13 握手推導，本單元只接收
      - name: label
        type: string
        required: true
        constraints: 給使用者看的說明，依能力與作業對象以固定句型產生（BR52.2）；不含使用者原句全文
      - name: status
        type: enum
        required: true
        allowed_values: [處理中, 等待中, 完成, 失敗, 已停掉]
        constraints: 轉換只依 BR54 的轉換表；每次更新皆為比對後寫入，比對 status 與 dispatchStage（BR52.7）
      - name: capability
        type: enum
        required: true
        allowed_values: [architecture-design, well-architected-review, cost-finops]
        constraints: 取自 intent_routing_types.ROUTABLE_CAPABILITIES，不另抄一份
      - name: waitingOn
        type: string
        required: false
        constraints: status 為等待中時必為非 null，內容為被等待那一項的 label（BR53.1）；其他狀態為 null
      - name: failureReason
        type: string
        required: false
        constraints: status 為失敗時必為非 null，為固定句型（BR56／BR57），不含例外原文；其他狀態為 null
      - name: sideEffect
        type: string
        required: true
        default: none
        constraints: "none／unknown／說明文字（K-11）；停掉時依 BR55.1 決定，在途存檔成功後依 BR55.7 更新"
      - name: createdAt
        type: timestamp
        required: true
      - name: estimateSetId
        type: integer
        required: false
        constraints: 僅 cost-finops 工作項；取得估價表後立即寫入（X-01 的不變量；BR56.3）
      # ---- 伺服器內部欄位（不送前端）----
      - name: dependsOn
        type: string
        required: false
        constraints: 被等待那一項的 workItemId（BR53.1）；與 waitingOn 同時有值或同時為 null
      - name: targetDiagramId
        type: integer
        required: false
        constraints: architecture-design／well-architected-review 的目標圖（BR56.1）
      - name: targetSystemId
        type: integer
        required: false
        constraints: >
          作業對象只指定系統時的系統；經 list_diagrams_of_system 換成目標圖集合（BR56.1／BR56.3）。
          系統下的圖多半 system_id 為空（OPEN-H11），故這條路徑常回零張
      - name: segmentId
        type: string
        required: true
        constraints: 交辦當輪訊息所屬的段，由 U13 傳入；作業對象取自這一段（BR52.6）
      - name: deadlineAt
        type: timestamp
        required: false
        constraints: 進入處理中時寫入（BR56.6，含由等待中推進者）；等待中為 null；逾期掃描以它判定（BR56.7）
      - name: dispatchStage
        type: enum
        required: true
        default: not_dispatched
        allowed_values: [not_dispatched, request_sent, persisting, result_persisted]
        constraints: 對既有能力的呼叫走到哪一步；BR55.1 據此決定停掉時的 sideEffect；persisting 只用於 architecture-design 的 PUT 在途；是比對後寫入的第二個比對欄位（BR52.7），故停掉與背景推進交錯時 sideEffect 依儲存的真實值決定
      - name: requestText
        type: string
        required: true
        max: 2000
        constraints: 本輪使用者原句（U13 傳入的 utterance）前 2000 字；多意圖時每項都是完整原句（BR52.6）；只存在伺服器內部，不出現在 log
    entity_constraints:
      - "status=等待中 ⇔ waitingOn 與 dependsOn 皆非 null"
      - "status=失敗 ⇔ failureReason 非 null"
      - "capability=cost-finops 且 status=完成 ⇒ estimateSetId 非 null"
      - "同一 sessionKey 內 workItemId 唯一"
      - "status=處理中 ⇔ deadlineAt 非 null"
    relationships:
      - target: BrainSession（U10）
        cardinality: many-to-one
        direction: WorkItem → BrainSession
      - target: WorkItem（dependsOn）
        cardinality: many-to-one
        direction: WorkItem → WorkItem（同一次交辦內）

value_objects:
  - name: WorkItemStatus
    allowed_values: [處理中, 等待中, 完成, 失敗, 已停掉]
    terminal: [完成, 失敗, 已停掉]
  - name: DispatchStage
    allowed_values: [not_dispatched, request_sent, persisting, result_persisted]
```

## 摘要

- **一個實體 `WorkItem`**：存在大腦工作階段裡，每項一個欄位，隨工作階段一起到期（`[WO3]`=A）。
  送到前端的欄位與已交付的 WebSocket 契約一致；`dependsOn`、`targetDiagramId`、`targetSystemId`、
  `segmentId`、`deadlineAt`、`dispatchStage`、`requestText` 是伺服器內部欄位。
- **`dispatchStage`** 讓「停掉時有沒有留下東西」可以如實判斷：還沒送出請求、已送出、存檔在途、已把結果存回。
- **`deadlineAt`** 讓重啟後殘留的處理中項目能被判定為失敗，而不必知道是哪個行程在跑它。
- 三個終態（完成／失敗／已停掉）沒有向外的轉換。
