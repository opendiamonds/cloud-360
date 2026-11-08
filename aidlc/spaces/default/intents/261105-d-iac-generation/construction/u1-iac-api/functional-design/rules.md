# 業務規則：U1 `u1-iac-api`

## Source of truth

```yaml
rules:
  - id: BR1.1
    statement: 執行類 API 必須通過對應故事的 RBAC edit；下載需 D1 edit
    category: authorization
    applies_to: IacHttpSurface
    trigger: 任一 /api/iac 請求
    logic: >
      IF POST /generate 缺 D1 edit THEN 403；
      IF POST /scan 缺 D2 edit THEN 403；
      IF POST /secrets/rewrite 缺 D3 edit THEN 403；
      IF GET /session 缺 D1 view THEN 403；
      IF GET /download 缺 D1 edit THEN 403（Q3=A／關 R-01）；
      403 專留給 RBAC，不得與閘 422 混用
    violation: 無權回 2xx 或以 view 放行 download／執行
    source: FR7.1, FR7.2, US6.1, contract R-01

  - id: BR1.2
    statement: 所有執行與讀寫產物路徑必須帶有效 diagram_id
    category: validation
    applies_to: IacSessionKey, IacHttpSurface
    trigger: POST /generate|/scan|/secrets/rewrite；GET /session|/download
    logic: >
      IF diagram_id 缺席 THEN 422 missing_diagram_id；
      IF 非正整數／形狀非法 THEN 422 invalid_diagram；
      IF 提供之 diagram_id 與該 user 當前活躍 session 槽不一致（例如進行中切圖競態）THEN 422 diagram_mismatch；
      POST /scan 與 /secrets/rewrite 的 requestBody 必含 diagram_id（Q2=A／關 R-02；契約已對齊）
    violation: 省略 diagram_id 仍操作某預設 session
    source: contract advisory R-02, Q2=A

  - id: BR1.13
    statement: D3 省略 report_id 時採用最新一次成功掃描報告
    category: constraint
    applies_to: IacRewriteResult, IacScanReport
    trigger: POST /secrets/rewrite 且未帶 report_id
    logic: >
      IF request 省略 report_id THEN 選取該 (user, diagram) 槽內 createdAt 最新且 status=succeeded 的 IacScanReport；
      IF 無此報告 THEN 422 missing_scan_report；
      IacRewriteResult.reportId 必須等於實際採用之 reportId
    violation: 任意挑選非最新報告或寫入未定義 reportId
    source: US4.1, review R-06

  - id: BR1.3
    statement: 執行 D2／下載需要成功草稿
    category: constraint
    applies_to: IacDraft, IacScanReport
    trigger: POST /scan；GET /download
    logic: >
      IF 該 (user, diagram) 無 status=succeeded 的 IacDraft THEN 422 missing_draft；
      UI disabled 為輔，後端閘為準
    violation: 無草稿仍 2xx scan／zip
    source: US3.1, US5.1, FR6.2

  - id: BR1.4
    statement: 執行 D3 需要成功草稿且至少一次成功掃描報告
    category: constraint
    applies_to: IacDraft, IacScanReport, IacRewriteResult
    trigger: POST /secrets/rewrite
    logic: >
      IF 無 succeeded draft THEN 422 missing_draft；
      ELSE IF 無同 session 至少一次 status=succeeded 的 IacScanReport（允許零 finding）THEN 422 missing_scan_report；
      IF 請求帶 report_id 且已作廢／不屬於本 session THEN 422 stale_report_id；
      省略 report_id 時之選取見 BR1.13
    violation: 僅有 D1 即可 D3；或舊 report_id 仍可用
    source: US4.1, FR6.2 (D3 補強), Q5 risk

  - id: BR1.5
    statement: 切圖或 diagram_id 變更必須清空並作廢舊產物
    category: policy
    applies_to: IacSessionKey, IacDraft, IacScanReport, IacRewriteResult
    trigger: 觀測到同一 user 的活躍 diagram_id 變更；或顯式清空
    logic: >
      IF diagram_id 與既有槽不同 THEN 刪除／作廢舊 draft／reports／rewrites；
      進行中請求結果不得寫入新槽；對舊 report_id 的後續 D3 → 422 stale_report_id
    violation: 舊產物仍可下載或 D3
    source: US1.3

  - id: BR1.6
    statement: 回應、log 與下載物不得回洩 D3 已改寫前的明文密文樣式
    category: policy
    applies_to: IacRewriteResult, IacDraft, IacHttpSurface
    trigger: rewrite 成功後之任何讀取／download
    logic: >
      IF rewrite 曾替換可辨識明文樣式 THEN 後續 JSON／log sink／zip 抽樣不得再出現該樣式
    violation: zip 或 API 仍含明文賦值
    source: US4.1, US5.2, FR4.4

  - id: BR1.7
    statement: 平台不得提供 apply／destroy；亦不得寫入雲端 Secret Manager
    category: policy
    applies_to: IacHttpSurface, IacModuleGenerator, IacSecretRedactor
    trigger: 任何工具／OpenAPI／執行路徑
    logic: >
      IF 操作為雲端 apply／destroy 或 SM PutSecret 類寫入 THEN 不得存在於 API 或 agent 工具清單
    violation: OpenAPI 或執行路徑出現 apply／SM 寫入
    source: FR5, FR8, US5.1 DoD

  - id: BR1.8
    statement: 多雲資源不得靜默丟棄
    category: policy
    applies_to: IacDraft, IacModuleGenerator
    trigger: POST /generate 成功
    logic: >
      IF 輸入圖含非主要雲資源 THEN 產物須含對應內容或明確實驗性標記區塊；不得無提示省略
    violation: 非 AWS 資源消失且無標記
    source: US2.2, FR2.4

  - id: BR1.9
    statement: D1 失敗不得清空先前成功草稿（同 diagram）
    category: policy
    applies_to: IacDraft
    trigger: POST /generate 失敗
    logic: >
      IF generate 失敗且 diagram_id 未變 THEN 保留既有 succeeded draft 可供 GET session／download；
      回錯誤訊息供重試
    violation: 失敗即整段清空可下載草稿
    source: US2.3

  - id: BR1.10
    statement: HIGH／CRITICAL 下載確認不由 API 閘
    category: policy
    applies_to: IacHttpSurface
    trigger: GET /download
    logic: >
      IF 呼叫端已通過 BR1.1／BR1.3 THEN API 直接回 zip；
      不得因 maxSeverity∈{HIGH,CRITICAL} 而 4xx；確認 modal 屬 U2
    violation: API 因嚴重度拒下載
    source: US5.1, contract Q3

  - id: BR1.11
    statement: 執行類 POST 客戶端不自動重試；伺服器可超時取消
    category: workflow
    applies_to: IacHttpSurface
    trigger: POST generate｜scan｜secrets/rewrite
    logic: >
      IF 請求逾時 THEN 回 504 或等價；不得自動重送同一 POST；
      GET /download 允許重試
    violation: 閘道或 UI 自動重試導致雙重產物
    source: contract Q5

  - id: BR1.12
    statement: US6.1 成對測試錨點為 POST /generate
    category: authorization
    applies_to: IacHttpSurface
    trigger: 第一個落地的 D HTTP 驗證
    logic: >
      IF 實作第一個 D 執行路徑 THEN 同 PR 必須以 TestClient 成對覆蓋
      無權→403 與有權→2xx（Q4=A）；標明測的是 generate
    violation: 只測 happy path
    source: US6.1, Q4=A
```

## 規則摘要

| ID | 類別 | 一句話 |
|---|---|---|
| BR1.1 | authorization | RBAC；download＝D1 edit |
| BR1.2 | validation | diagram_id 必填 |
| BR1.3 | constraint | scan／download 需草稿 |
| BR1.4 | constraint | D3 需 D1∧D2 成功報告 |
| BR1.5 | policy | 切圖作廢舊產物 |
| BR1.6 | policy | 禁回洩明文 |
| BR1.7 | policy | 禁 apply／SM 寫入 |
| BR1.8 | policy | 多雲不靜默丟棄 |
| BR1.9 | policy | D1 失敗保留舊草稿 |
| BR1.10 | policy | 嚴重度不擋 API 下載 |
| BR1.11 | workflow | POST 不自動重試 |
| BR1.12 | authorization | generate 成對 403／2xx |
| BR1.13 | constraint | D3 省略 report_id → 最新成功報告 |
