# 業務規則：U3 `legacy-cost-retirement`

## Source of truth

```yaml
rules:
  - id: BR9.1
    statement: 舊 /api/cost diagrams 等 HTTP operations 必須整包移除
    category: policy
    applies_to: LegacyHttpSurface
    trigger: 本 Unit 合併
    logic: >
      IF 本 Unit 進入可部署狀態 THEN cost_router 掛載與全部舊 operations 必須不存在；
      不得只回 410；不得在本 Unit 新增 /api/cost/v1 stub
    violation: 舊路徑仍可被呼叫，或誤加 v1 stub
    source: FR9.1, Q2=A

  - id: BR9.2
    statement: 四張舊表改名 archive_* 並保留至少一季，不得在本 Unit 直接 DROP
    category: policy
    applies_to: LegacyCostTable
    trigger: schema 變更
    logic: >
      IF 處置 diagram_cost／diagram_cost_line／pricing_cache／cost_audit_event THEN
      必須在 database.py::_ensure_cost_schema 與 schema_rbac.sql 雙軌改為 archive_*（或等價遷移），
      並更新 DEPLOY.md；保留期 ≥90 天；應用程式碼不得再依賴 live 表名
    violation: 直接 DROP 而未 archive；或只改單軌 DDL
    source: FR9.2, Q3=C

  - id: BR9.3
    statement: Playwright Calculator 自動化與 Python playwright 相依必須移除
    category: policy
    applies_to: PlaywrightCalculatorBundle
    trigger: 相依與模組清理
    logic: >
      IF 本 Unit 完成 THEN azure_calculator_runner／gcp_calculator_*／相關 spike 不存在，
      且 requirements.txt 無 Python playwright；前端 @playwright/test 保留
    violation: 殘留 runner 或 Python playwright 相依
    source: FR9.3, Q4=A

  - id: BR9.4
    statement: U5 最小存活集不得被本 Unit 刪除
    category: constraint
    applies_to: PricingSurvivalSet
    trigger: 任何 backend/cost 刪除
    logic: >
      IF 刪除或大幅改寫 cost 套件 THEN 必須保留 pricing_sdk、pricing_client、config＋YAML、
      pricing_units、pricing_offer_parser、pricing_gcp、pricing_azure、pricing_query_parser、
      boto3 與相關 unittest
    violation: 誤刪導致 U5 無法接上
    source: FR9.4, FR9.5, Q5=A

  - id: BR9.5
    statement: 合併／部署必須與 U8 同批
    category: constraint
    applies_to: LegacyHttpSurface, U8
    trigger: 合併至 ut 或部署
    logic: >
      IF 本 Unit 的破壞性變更要進 trunk／staging THEN 必須與 U8 新估價工作區 UI
      同一 PR 或同一 squash 批次；禁止只合 U3
    violation: 中間狀態無可用成本頁
    source: bolt-plan B5, U3 Q6=A, Q1=A

  - id: BR9.6
    statement: 舊 cost e2e 必須刪除或改寫，不得靠 COST_PRICING_STUB 續命
    category: policy
    applies_to: LegacyToolingDebt
    trigger: CI／e2e
    logic: >
      IF 存在依賴 /api/cost/diagrams 或 stub 金額 $86.40 的 e2e THEN 本 Unit 必須刪除或改寫；
      若 U8 尚未提供新案 THEN 允許移除或 skip，並由 U8 補新 e2e
    violation: CI 仍斷言舊 API／stub 金額
    source: FR9.9, Q6=A

  - id: BR9.7
    statement: warm_aws_pricing_cache 與孤兒 prompt 必須隨退場修正或移除
    category: policy
    applies_to: LegacyToolingDebt
    trigger: 表改名／agent 拆除
    logic: >
      IF price_cache／舊 agent 路徑退場 THEN warm_aws_pricing_cache.py 必須改指向存活模組
      或刪除；cost_pricing_agent_system.md 等孤兒 prompt 必須處理；同 PR 重產 openapi／型別
    violation: 腳本 import 斷裂或 orphan 檔殘留導致維運困惑
    source: FR9.7, FR9.10, FR9.11

  - id: BR9.8
    statement: FR9.6 邊界腳本改指向不屬本 Unit
    category: constraint
    applies_to: scripts/validate_cost_calculator_boundary.py
    trigger: 範圍檢查
    logic: IF 變更邊界腳本目標 THEN 屬 U1（已完成）；本 Unit 不得回退其指向
    violation: 把邊界腳本改回 cost_calculator 或刪除腳本
    source: FR9.6, U3 boundaries
```

## 規則摘要

| ID | 一句話 |
|---|---|
| BR9.1 | 舊 HTTP 整包移除 |
| BR9.2 | 表改 archive_*，保留 ≥90 天 |
| BR9.3 | 刪 Calculator＋Python playwright |
| BR9.4 | 不碰 U5 存活集 |
| BR9.5 | 與 U8 同批部署 |
| BR9.6 | 舊 cost e2e 必須處理 |
| BR9.7 | 工具鏈／orphan／OpenAPI 同步 |
| BR9.8 | 不回退 U1 邊界腳本 |
