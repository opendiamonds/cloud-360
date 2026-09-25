# 業務規則：U2 `estimate-intake-api`

## Source of truth

```yaml
rules:
  - id: BR2.1
    statement: 上傳必須通過副檔名、魔數、大小與檔數限制
    category: validation
    applies_to: IntakeHttpSurface, EstimateSet
    trigger: POST /api/cost/v1/sets
    logic: >
      IF 任一檔副檔名非 .csv/.xlsx、魔數不符、單檔 >5MB、或檔數不在 1..3 THEN
      拒絕（400／413，contract C2）；不得呼叫 Parser；不得持久化；原始位元組不得落地
    violation: 未驗證即 parse 或寫入磁碟
    source: FR1.3, FR1.4, FR1.6, NFR3

  - id: BR2.2
    statement: 雲別判定失敗時必須允許 override，不得逕自拒絕
    category: policy
    applies_to: Estimate, EstimateSet
    trigger: 解析後 detection.status=ambiguous
    logic: >
      IF detection 為 ambiguous 且請求未提供對應檔的 cloud_overrides 有效值 THEN 400；
      IF 有有效 override（aws|azure|gcp）THEN 以 override 建 Estimate 並繼續；
      IF detection 為 resolved THEN 忽略同檔 override 或僅作稽核註記（實作擇一，不得改雲別與標頭衝突 silently 成錯雲）
    violation: ambiguous 直接拒檔且無 override 路徑
    source: FR1.5, C2

  - id: BR2.3
    statement: 原始檔解析完成後必須丟棄，不得保存
    category: policy
    applies_to: EstimateSet
    trigger: parse 結束
    logic: >
      IF parse（成功或轉 400）完成 THEN 請求中的檔案位元組不得寫入物件儲存／DB blob／暫存檔長駐；
      僅持久化結構化 Estimate／LineItem 等
    violation: 原始檔可於之後讀回
    source: FR1.6, FR8.3

  - id: BR2.4
    statement: 機械檢查結果不得持久化，每次讀取重算
    category: policy
    applies_to: EstimateLineItem, EstimateSet
    trigger: GET detail／上傳 201 回應
    logic: >
      IF 回傳 MechanicalCheckView THEN 必須由 EstimateValidator.validate(ParseResult 等價物) 當場計算；
      不得存 checks 欄或檢查快照表
    violation: DB 有 checks 快照且與重算不一致
    source: FR4, C1/C2, domain

  - id: BR2.5
    statement: 可見性只看擁有者與分享名單，不查架構圖
    category: authorization
    applies_to: EstimateSet, EstimateShare
    trigger: 任何讀寫／分享／advice GET
    logic: >
      IF 呼叫者非 owner 且不在 EstimateShare THEN 404 或 403（對外「不可見」採 C2：get→404）；
      diagramId 不參與判斷；不得 import collab_router 私有授權函式
    violation: 依架構圖權限放行／拒絕估價表
    source: FR6.5, FR6.6, FR7.3, domain Q6=B, Q3=A

  - id: BR2.6
    statement: 分享名單以完整覆寫語意更新，僅擁有者可改
    category: authorization
    applies_to: EstimateShare
    trigger: PUT /sets/{id}/shares
    logic: >
      IF 非 owner THEN 403；
      IF owner THEN 以 user_ids 完整取代既有分享列（可空陣列＝收回全部）
    violation: 部分 patch 導致名單與請求不一致
    source: FR6.6, C2

  - id: BR2.7
    statement: 刪除為硬刪並級聯，僅擁有者
    category: policy
    applies_to: EstimateSet
    trigger: DELETE /sets/{id}
    logic: >
      IF 非 owner THEN 403；
      IF owner THEN 硬刪 Set 及其 Estimate／LineItem／Share／AuditEvent，
      以及已存在的 Advice 列（或等價 DB ON DELETE CASCADE）；回 204
    violation: 軟刪殘留可被 list；或級聯漏表
    source: FR6.4, Q4=A

  - id: BR2.8
    statement: 上傳成功後必須背景 enqueue 建議，HTTP 立即 201
    category: workflow
    applies_to: EstimateSet, Advice
    trigger: POST /sets 持久化成功
    logic: >
      IF 批次與明細已 commit THEN 於同 request 生命週期 enqueue U7 工作後立即回 201；
      不得在上傳 request 內同步跑完整建議；
      enqueue 失敗須寫 AuditEvent，Advice 可不建或建 failed（擇一寫進實作計畫）
    violation: 同步阻塞建議或完全不觸發
    source: C2 SLA, Q2=A, FR5 觸發面

  - id: BR2.9
    statement: GET advice 為授權後薄代理；無列時 none／短窗 404
    category: workflow
    applies_to: Advice, IntakeHttpSurface
    trigger: GET /sets/{id}/advice
    logic: >
      IF 呼叫者不可見該 Set THEN 404；
      IF 可見且無 Advice 列 THEN advice_status=none 或 404 短窗（與 C2／Summary 對齊，實作釘一種）；
      IF 有列 THEN 回 AdviceSnapshot 欄位；本 Unit 不產生建議正文
    violation: 未授權讀到他入建議；或本 Unit 寫入三類建議文字
    source: C2, Q5=A

  - id: BR2.10
    statement: RBAC story C1 語意更新並移除 C1h／C1r／C1o／C1b seed
    category: policy
    applies_to: IntakeHttpSurface
    trigger: 本 Unit 合併
    logic: >
      IF 本 Unit 完成 THEN rbac_seed_data（或等價）中 C1 語意為「上傳與檢視估價表」，
      且 C1h／C1r／C1o／C1b 列不存在；須有 allow／deny 雙向測試覆蓋新 C1
    violation: 舊 story id 仍 seed；或無授權測
    source: FR7.1, FR7.2, Q6=A

  - id: BR2.11
    statement: 模組必須採 estimate_intake_* 三層形狀並掛 /api/cost/v1
    category: constraint
    applies_to: IntakeHttpSurface
    trigger: code-generation
    logic: >
      IF 實作 HTTP THEN 使用 estimate_intake_router／estimate_intake_service（＋ access／audit），
      main 掛載 prefix /api/cost/v1；不得重建舊 diagrams cost_router 行為
    violation: 路由混在 collab 或服務層直接 SQL 無邊界
    source: NFR6, Q1=A

  - id: BR2.12
    statement: 稽核只記事件層級，不含金額與檔案
    category: policy
    applies_to: EstimateAuditEvent
    trigger: upload／share／delete／enqueue
    logic: >
      IF 寫 AuditEvent THEN 可含 actor、時間、雲別、列數、事件型別、set id；
      不得含 amount／rawText／檔名路徑／secret
    violation: 稽核可重建明細金額或檔案
    source: FR8.1, FR8.2

  - id: BR2.13
    statement: 寫庫前可對目錄形 SKU 補規格描述，不得寫入價格
    category: policy
    applies_to: EstimateLineItem
    trigger: POST /sets parse 成功後、insert 前
    logic: >
      IF 列 spec 符合 FR13.1 的目錄 SKU 形狀 THEN 得呼叫 cost.sku_catalog.enrich_line_specs；
      僅可把描述寫入 specDescription／spec_description；
      禁止寫入 amount／quantity／任何 hourly 欄；
      不得 import pricing_client／pricing_sdk；
      查詢失敗、逾時、缺憑證、超過互異 SKU 上限 THEN 該列描述留空並繼續寫庫
    violation: 明細金額被目錄價覆寫；或缺描述導致整批 5xx
    source: FR13, FR5.5, AH-6, NFR10
```

## 規則摘要表

| ID | 一句話 |
|---|---|
| BR2.1 | 上傳驗證：副檔名／魔數／大小／檔數 |
| BR2.2 | ambiguous 須可 override |
| BR2.3 | 原始檔即棄 |
| BR2.4 | 機械檢查每次重算 |
| BR2.5 | 授權＝擁有者＋分享 |
| BR2.6 | 分享完整覆寫 |
| BR2.7 | 硬刪級聯 |
| BR2.8 | 201 後背景 enqueue |
| BR2.9 | advice GET 薄代理 |
| BR2.10 | C1 seed 更新 |
| BR2.11 | estimate_intake_*＋v1 |
| BR2.12 | 稽核無金額／檔 |
| BR2.13 | SKU 描述可寫、價格不可寫 |
