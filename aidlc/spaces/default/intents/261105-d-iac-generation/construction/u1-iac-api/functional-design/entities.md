# 實體模型：U1 `u1-iac-api`

本 Unit 為 **service**：行程內 IaC 工作階段、三核心編排、`/api/iac` HTTP。  
產物**不**落新 Postgres 表（ADR-002／Q5=A）。**不含** SPA（U2）。

## Source of truth

```yaml
entities:
  - name: IacSessionKey
    description: 行程內產物字典的查找鍵（非持久化列）
    attributes:
      - { name: userId, type: integer, required: true }
      - { name: diagramId, type: integer, required: true, constraints: ["positive integer"] }
    constraints:
      - "同一 process 內以 (userId, diagramId) 唯一對應一組產物槽"
      - "diagramId 變更或切圖＝新鍵；舊鍵產物作廢且不得再寫回"

  - name: IacDraft
    description: D1 成功後的多檔 HCL 模組樹草稿
    attributes:
      - { name: draftId, type: string, required: true, identity: true }
      - { name: diagramId, type: integer, required: true }
      - { name: userId, type: integer, required: true }
      - { name: status, type: enum, required: true, allowed_values: [succeeded, failed] }
      - { name: files, type: "FileEntry[]", required: true }
      - { name: createdAt, type: datetime, required: true }
    constraints:
      - "status=succeeded 時 files 至少含 main.tf／variables.tf／outputs.tf 或設計核准等價拆分"
      - "僅行程內；重載 process 後可消失"

  - name: FileEntry
    description: 模組樹中的單一相對路徑檔
    attributes:
      - { name: path, type: string, required: true }
      - { name: content, type: string, required: true }
    constraints:
      - "path 為相對模組根；不得含絕對路徑逃逸"

  - name: IacFinding
    description: D2 掃描的單一 finding
    attributes:
      - { name: id, type: string, required: true }
      - { name: severity, type: enum, required: true, allowed_values: [INFO, LOW, MEDIUM, HIGH, CRITICAL] }
      - { name: title, type: string, required: true }
      - { name: detail, type: string, required: false, nullable: true }
      - { name: path, type: string, required: false, nullable: true }

  - name: IacScanReport
    description: D2 成功／失敗掃描報告
    attributes:
      - { name: reportId, type: string, required: true, identity: true }
      - { name: draftId, type: string, required: true }
      - { name: diagramId, type: integer, required: true }
      - { name: status, type: enum, required: true, allowed_values: [succeeded, failed] }
      - { name: findings, type: "IacFinding[]", required: true }
      - { name: maxSeverity, type: enum, required: true, allowed_values: [NONE, INFO, LOW, MEDIUM, HIGH, CRITICAL] }
      - { name: createdAt, type: datetime, required: true }
    constraints:
      - "status=succeeded 允許 findings 為空陣列；此時 maxSeverity=NONE"
      - "切圖或 draft 作廢後，舊 reportId 不得再通過 D3 閘"

  - name: IacRewriteResult
    description: D3 改寫結果摘要
    attributes:
      - { name: rewriteId, type: string, required: true, identity: true }
      - { name: draftId, type: string, required: true }
      - { name: reportId, type: string, required: true }
      - { name: status, type: enum, required: true, allowed_values: [succeeded, failed] }
      - { name: rewrittenPaths, type: "string[]", required: true }
      - { name: createdAt, type: datetime, required: true }
    constraints:
      - "成功後 session 內 draft 內容為改寫後版本；不得回洩改寫前明文密文樣式"

relationships:
  - { from: IacDraft, to: IacSessionKey, cardinality: "many-to-one", direction: "draft belongs to session key" }
  - { from: IacScanReport, to: IacDraft, cardinality: "many-to-one", direction: "report references draft revision" }
  - { from: IacRewriteResult, to: IacDraft, cardinality: "many-to-one", direction: "rewrite updates draft" }
  - { from: IacRewriteResult, to: IacScanReport, cardinality: "many-to-one", direction: "rewrite requires prior succeeded report" }
  - { from: IacFinding, to: IacScanReport, cardinality: "many-to-one", direction: "finding contained in report" }
  - { from: FileEntry, to: IacDraft, cardinality: "many-to-one", direction: "file contained in draft" }
```

## 摘要

| 實體 | 生命週期 |
|---|---|
| IacSessionKey | 請求帶入的 `(user, diagram)`；切圖換鍵 |
| IacDraft | generate 成功寫入；失敗不覆蓋先前成功草稿（US2.3） |
| IacScanReport | scan 成功寫入；可零 finding |
| IacRewriteResult | rewrite 成功；並更新 draft 內容 |
| IacFinding／FileEntry | 報告／草稿的內嵌值物件 |
