# 實體模型：U2 `estimate-intake-api`

本 Unit 為 **service**：持久化估價批次與明細、分享、稽核；對外 REST `/api/cost/v1`。  
**Advice** 實體由 U7 擁有；本 Unit 僅觸發產生與（Q5=A）薄讀代理。  
**不含** SPA／frontend-components（U8／U9）。

## Source of truth

```yaml
entities:
  - name: EstimateSet
    description: 一次上傳批次（最多三朵雲）；分享／歷史／建議／稽核的掛載根
    attributes:
      - { name: id, type: integer, required: true, identity: true }
      - { name: ownerUserId, type: integer, required: true }
      - { name: createdAt, type: datetime, required: true }
      - { name: diagramId, type: integer, required: false, nullable: true, description: "純標籤；不參與授權（Q3=A）" }
      - { name: note, type: string, required: false, nullable: true }
    constraints:
      - "每次 POST /sets 成功建立一筆新 EstimateSet（FR6.2）；不原地覆寫舊批次"
      - "diagramId 若有值僅須為正整數；不驗證圖存在／可見"

  - name: Estimate
    description: 批次內單一雲別的估價表彙總
    attributes:
      - { name: id, type: integer, required: true, identity: true }
      - { name: estimateSetId, type: integer, required: true }
      - { name: cloud, type: enum, required: true, allowed_values: [aws, azure, gcp] }
      - { name: statedTotal, type: number, required: false, nullable: true }
      - { name: currency, type: string, required: false, nullable: true }
      - { name: parsedLineCount, type: integer, required: true }
      - { name: unparsedLineCount, type: integer, required: true }
      - { name: sourceFormat, type: enum, required: true, allowed_values: [csv, xlsx] }
    constraints:
      - "同一 EstimateSet 內 cloud 唯一（最多三筆）"

  - name: EstimateLineItem
    description: 逐列明細（解析結果持久化；機械檢查不持久化）
    attributes:
      - { name: id, type: integer, required: true, identity: true }
      - { name: estimateId, type: integer, required: true }
      - { name: ordinal, type: integer, required: true }
      - { name: itemName, type: string, required: false, nullable: true }
      - { name: spec, type: string, required: false, nullable: true }
      - { name: quantity, type: number, required: false, nullable: true }
      - { name: amount, type: number, required: false, nullable: true }
      - { name: currency, type: string, required: false, nullable: true }
      - { name: parseStatus, type: enum, required: true, allowed_values: [parsed, unidentifiable] }
      - { name: rawText, type: string, required: true }
    constraints:
      - "機械檢查結果每次 GET 重算，不存欄位／子表"

  - name: EstimateShare
    description: 批次分享關聯（擁有者＋名單）
    attributes:
      - { name: estimateSetId, type: integer, required: true }
      - { name: userId, type: integer, required: true }
      - { name: sharedAt, type: datetime, required: true }
    constraints:
      - "主鍵 (estimateSetId, userId)"
      - "僅擁有者可 PUT 覆寫名單"

  - name: EstimateAuditEvent
    description: 事件層級稽核（不含金額／明細全文）
    attributes:
      - { name: id, type: integer, required: true, identity: true }
      - { name: actorUserId, type: integer, required: true }
      - { name: estimateSetId, type: integer, required: true }
      - { name: eventType, type: string, required: true, description: "upload|share_replace|delete|advice_enqueue|…" }
      - { name: occurredAt, type: datetime, required: true }
      - { name: cloud, type: string, required: false, nullable: true }
      - { name: parsedLineCount, type: integer, required: false, nullable: true }
      - { name: unparsedLineCount, type: integer, required: false, nullable: true }
    constraints:
      - "不得寫入金額、列原文、檔案內容（FR8.2／FR1.6）"

  - name: Advice
    description: 建議列（U7 擁有）；本 Unit 觸發建立／更新狀態，並提供 GET 薄代理（Q5=A）
    attributes:
      - { name: estimateSetId, type: integer, required: true, unique: true }
      - { name: status, type: enum, required: true, allowed_values: [generating, completed, failed] }
      - { name: savingText, type: string, required: false, nullable: true }
      - { name: comparisonText, type: string, required: false, nullable: true }
      - { name: qualityText, type: string, required: false, nullable: true }
      - { name: unavailableReasons, type: object, required: false, nullable: true }
      - { name: startedAt, type: datetime, required: false, nullable: true }
      - { name: completedAt, type: datetime, required: false, nullable: true }
    constraints:
      - "estimateSetId UNIQUE；重複 enqueue 不得建第二列（domain 審閱）"
      - "本 Unit 不寫三類建議正文（屬 U7）"

  - name: IntakeHttpSurface
    description: 本 Unit 掛載的 REST 面
    attributes:
      - { name: modules, type: list, required: true, example: "estimate_intake_router／estimate_intake_service／access／audit" }
      - { name: mountPrefix, type: string, required: true, const: "/api/cost/v1" }
      - { name: operations, type: list, required: true, description: "sets POST/GET、sets/{id} GET/DELETE、shares GET/PUT、advice GET" }
    constraints:
      - "不實作 SPA；不掛 /api/cost/v1/.../advice/stream（C3／U7）"
```

## 摘要

| 實體 | 擁有者 Unit | 本 Unit 責任 |
|---|---|---|
| EstimateSet／Estimate／LineItem | U2 | CRUD 持久化 |
| EstimateShare | U2 | 覆寫／查詢 |
| EstimateAuditEvent | U2 | 寫事件 |
| Advice | U7 | 觸發＋薄讀 |
| IntakeHttpSurface | U2 | OpenAPI 落地 |
