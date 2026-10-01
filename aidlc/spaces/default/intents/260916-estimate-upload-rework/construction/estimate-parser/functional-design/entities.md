# 實體模型：U1 `estimate-parser`

本 Unit 為 library，**不擁有資料庫表**。下列為記憶體內的值物件／結果形狀，與 contract C1 對齊；屬性型別為邏輯型別。

## Source of truth

```yaml
entities:
  - name: CloudDetection
    description: 雲別判定結果；判定失敗不拋例外
    attributes:
      - { name: status, type: enum, required: true, allowed_values: [resolved, ambiguous] }
      - { name: cloud, type: enum, required: false, allowed_values: [aws, azure, gcp], constraint: "required when status=resolved" }
      - { name: candidates, type: "CloudId[]", required: false, constraint: "when status=ambiguous" }
      - { name: reason, type: string, required: false }
    constraints:
      - "status=resolved ⇒ cloud 有值"
      - "status=ambiguous ⇒ cloud 為空"

  - name: LineItem
    description: 正規化後的一列估價明細（含無法辨識列）
    attributes:
      - { name: ordinal, type: integer, required: true, min: 0 }
      - { name: itemName, type: string, required: false }
      - { name: spec, type: string, required: false }
      - { name: serviceId, type: string, required: false, description: "GCP 等檔案欄；parse 只擷取不外呼" }
      - { name: specDescription, type: string, required: false, description: "parse() 不填；intake 可於寫庫前補" }
      - { name: quantity, type: number, required: false, nullable: true }
      - { name: amount, type: number, required: false, nullable: true }
      - { name: currency, type: string, required: false, nullable: true }
      - { name: parseStatus, type: enum, required: true, allowed_values: [parsed, unidentifiable] }
      - { name: rawText, type: string, required: true }
    constraints:
      - "parseStatus=parsed ⇒ quantity 與 amount 皆非 null"
      - "parseStatus=unidentifiable ⇒ quantity 或 amount 至少一者為 null"
      - "無法辨識判定：金額或數量無法解析為數值（FR2.2）"

  - name: EstimateTotals
    description: 表級總額與幣別（可能缺宣告總額）
    attributes:
      - { name: statedTotal, type: number, required: false, nullable: true }
      - { name: currency, type: string, required: false, nullable: true }

  - name: ParseResult
    description: parse() 的完整回傳
    attributes:
      - { name: detection, type: CloudDetection, required: true }
      - { name: lines, type: "LineItem[]", required: true }
      - { name: totals, type: EstimateTotals, required: true }
      - { name: sourceFormat, type: enum, required: true, allowed_values: [csv, xlsx] }
    relationships:
      - { from: ParseResult, to: CloudDetection, cardinality: "1:1", via: detection }
      - { from: ParseResult, to: LineItem, cardinality: "1:N", via: lines }
      - { from: ParseResult, to: EstimateTotals, cardinality: "1:1", via: totals }

  - name: TotalReconcileOutcome
    description: 總額對帳子結果
    attributes:
      - { name: attempted, type: boolean, required: true }
      - { name: withinTolerance, type: boolean, required: false, nullable: true }
      - { name: skippedReason, type: string, required: false, nullable: true, constraint: "attempted=false ⇒ skippedReason 非 null" }
      - { name: tolerancePercent, type: number, required: true, default: 0.5, const: 0.5 }

  - name: MechanicalCheckResult
    description: validate() 的回傳；不持久化
    attributes:
      - { name: currencyConsistent, type: boolean, required: true }
      - { name: currencyOffenders, type: "integer[]", required: true }
      - { name: currencyTie, type: boolean, required: true, default: false }
      - { name: quantityPositive, type: boolean, required: true }
      - { name: quantityOffenders, type: "integer[]", required: true }
      - { name: totalReconciled, type: TotalReconcileOutcome, required: true }
```

## 摘要

| 實體 | 角色 |
|---|---|
| CloudDetection | 雲別判定 |
| LineItem | 逐列明細 |
| EstimateTotals | 表級總額 |
| ParseResult | parse 出口 |
| MechanicalCheckResult | validate 出口 |
| TotalReconcileOutcome | 對帳細節 |

無生命週期狀態機（值物件，一次計算一次丟棄）。
