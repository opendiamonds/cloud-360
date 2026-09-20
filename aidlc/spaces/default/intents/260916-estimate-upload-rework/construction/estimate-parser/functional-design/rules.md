# 業務規則：U1 `estimate-parser`

## Source of truth

```yaml
rules:
  - id: BR1.1
    statement: 每朵雲只接受一種主格式——AWS CSV、Azure XLSX、GCP CSV
    category: constraint
    applies_to: ParseResult.sourceFormat
    trigger: parse 開始
    logic: IF 副檔名／內容格式不屬於該雲對應格式 THEN 不得標為該雲的 resolved（應 ambiguous 或由其他雲候選）
    violation: detection.status=ambiguous 或排除錯誤雲別
    source: FR1.2

  - id: BR1.2
    statement: 依標頭欄位自動判定雲別；判不出則 ambiguous，不拋例外
    category: validation
    applies_to: CloudDetection
    trigger: parse 讀取標頭後
    logic: IF 標頭可唯一對應一雲 THEN status=resolved 且 cloud=該雲；ELSE status=ambiguous 且填 candidates
    violation: 不得逕自拒絕或 raise HTTP
    source: FR1.5

  - id: BR2.1
    statement: 擷取品項、規格、數量、金額，以及表總額與幣別
    category: calculation
    applies_to: LineItem, EstimateTotals
    trigger: 格式讀取器執行時
    logic: IF 列可讀 THEN 填入對應欄位；表級 totals 自頁尾／合計列擷取，缺則 null
    violation: 不中止整份；單列不足則該列走 BR2.2
    source: FR2.1

  - id: BR2.2
    statement: 金額或數量無法解析為數值的列標為 unidentifiable，保留 rawText
    category: validation
    applies_to: LineItem.parseStatus
    trigger: 單列正規化時
    logic: IF amount 或 quantity 無法解析為數值 THEN parseStatus=unidentifiable 且對應欄 null；品項／規格缺漏但兩者皆可解析 THEN 仍為 parsed
    violation: 不得因單列失敗而使整份 parse 失敗
    source: FR2.2

  - id: BR2.3
    statement: 解析器與驗證器模組不得依賴 HTTP 客戶端、DB session、Web 框架
    category: policy
    applies_to: estimate_parser.py, estimate_validator.py
    trigger: CI／靜態檢查
    logic: IF 模組 import httpx|requests|sqlalchemy|fastapi THEN 檢查失敗
    violation: CI 紅燈
    source: FR2.3, FR9.6

  - id: BR2.4
    statement: 解析與驗證行為須可用 property-based 測試描述
    category: policy
    applies_to: parse, validate
    trigger: 測試套件
    logic: IF 核心正規化／檢查規則變更 THEN 對應 PBT 必須更新且通過
    violation: 測試失敗不得合併
    source: FR2.4

  - id: BR4.1
    statement: 幣別一致性——以可解析列的多數幣別為準；異於多數者為 offender
    category: validation
    applies_to: MechanicalCheckResult.currencyConsistent
    trigger: validate
    logic: >
      IF 可解析列中無任何非空 currency THEN currencyConsistent=true 且 offenders=[]；
      ELSE 取出現次數最多的 currency 為 majority；
      IF 兩個以上 currency 同為最高票 THEN 取字典序最小者為 majority 且 currencyTie=true；
      凡 currency 非空且 ≠ majority 的列 ordinal 列入 currencyOffenders；
      currencyConsistent = (offenders 為空)
    violation: currencyConsistent=false，列出 ordinals
    source: FR4.1

  - id: BR4.2
    statement: 數量不得為負；零允許
    category: validation
    applies_to: MechanicalCheckResult.quantityPositive
    trigger: validate
    logic: IF 列 parseStatus=parsed 且 quantity < 0 THEN 列入 quantityOffenders；quantityPositive = (offenders 為空)；quantity 為 null 的 unidentifiable 列不檢查
    violation: quantityPositive=false
    source: FR4.2

  - id: BR4.3
    statement: 總額對帳容差 0.5%
    category: calculation
    applies_to: TotalReconcileOutcome
    trigger: validate 且 attempted=true 時
    logic: >
      sum = 所有 parseStatus=parsed 列的 amount 加總；
      IF statedTotal = 0 THEN withinTolerance = (sum = 0)；
      ELSE IF |sum - statedTotal| / |statedTotal| ≤ 0.005 THEN withinTolerance=true ELSE false
      （不使用未定義的 epsilon；零總額採精確相等分支）
    violation: withinTolerance=false
    source: FR4.3

  - id: BR4.4
    statement: 存在無法辨識列或無宣告總額時跳過對帳
    category: constraint
    applies_to: TotalReconcileOutcome.attempted
    trigger: validate
    logic: >
      IF 任一列 parseStatus=unidentifiable THEN attempted=false 且 skippedReason 說明因 N 列無法辨識；
      ELSE IF statedTotal is null THEN attempted=false 且 skippedReason 說明無宣告總額；
      ELSE attempted=true 並執行 BR4.3
    violation: 不得在應跳過時給出 withinTolerance 結論
    source: FR4.4

  - id: BR9.1
    statement: CI 邊界腳本須同時檢查 estimate_parser.py 與 estimate_validator.py
    category: policy
    applies_to: validate_cost_calculator_boundary.py
    trigger: CI repo-contract
    logic: IF 任一目標檔缺失或含禁止 import THEN 失敗
    violation: CI 紅燈
    source: FR9.6

  - id: BR3.1
    statement: 內容毀損或無可用標頭時回傳 ambiguous 空表
    category: validation
    applies_to: ParseResult
    trigger: parse 無法建立欄位對應時
    logic: IF 無法讀出標頭／列結構 THEN detection.status=ambiguous 且 lines=[] 且 totals={statedTotal:null, currency:null}（不拋 HTTP）
    violation: 不得 raise 框架例外
    source: FD-Q3
```

## 規則摘要

| ID | 類別 | 一句話 |
|---|---|---|
| BR1.1 | constraint | 一雲一格式 |
| BR1.2 | validation | 雲別判定／ambiguous |
| BR2.1 | calculation | 擷取欄位 |
| BR2.2 | validation | 無法辨識列 |
| BR2.3 | policy | 純函式 import 禁令 |
| BR2.4 | policy | PBT |
| BR4.1 | validation | 幣別多數決 |
| BR4.2 | validation | 數量 ≥ 0 |
| BR4.3 | calculation | 0.5% 對帳 |
| BR4.4 | constraint | 跳過對帳條件 |
| BR9.1 | policy | CI 守兩檔 |
| BR3.1 | validation | 毀損→ambiguous 空表 |
