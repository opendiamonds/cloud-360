# 實體模型：U3 `legacy-cost-retirement`

本 Unit 為**退場**型 service：不新增業務實體。下列為「待處置資產」與「保留資產」的邏輯分類；屬性為盤點欄位。

## Source of truth

```yaml
entities:
  - name: LegacyHttpSurface
    description: 舊架構圖估價 HTTP 面（將整包移除）
    attributes:
      - { name: routerModule, type: string, required: true, example: "cost.cost_router" }
      - { name: mountPrefix, type: string, required: true, const: "/api/cost" }
      - { name: operations, type: list, required: true, description: "diagrams／budget／calculator-export 等舊 operations" }
    constraints:
      - "本 Unit 不新增 /api/cost/v1（屬 U2）"
      - "合併部署須與 U8 同批（Q1=A）"

  - name: LegacyCostTable
    description: 四張舊成本表；本 Unit 改名 archive_* 後保留一季再刪（Q3=C）
    attributes:
      - { name: liveName, type: string, required: true, allowed_values: [diagram_cost, diagram_cost_line, pricing_cache, cost_audit_event] }
      - { name: archiveName, type: string, required: true, description: "archive_<liveName>" }
      - { name: retentionDays, type: int, required: true, const: 90 }
      - { name: ddlTracks, type: list, required: true, description: "database.py::_ensure_cost_schema 與 schema_rbac.sql" }
    constraints:
      - "應用程式碼不得再讀寫 liveName；僅允許遷移／維運用讀取 archive_*"
      - "一季到期後的物理 DROP 可屬後續 chore／operation，但本 Unit 必須完成 rename＋文件化到期日"

  - name: PlaywrightCalculatorBundle
    description: 瀏覽器自動化估價路徑（整包刪除）
    attributes:
      - { name: modules, type: list, required: true }
      - { name: pythonDependency, type: string, required: true, const: "playwright" }
    constraints:
      - "前端 e2e 的 @playwright/test 不在本實體範圍"

  - name: PricingSurvivalSet
    description: 留給 U5 的最小存活集（本 Unit 不得刪）
    attributes:
      - { name: modules, type: list, required: true, description: "pricing_sdk、pricing_client、config＋YAML、pricing_units、pricing_offer_parser、pricing_gcp、pricing_azure、pricing_query_parser" }
      - { name: dependencies, type: list, required: true, description: "boto3 等" }
      - { name: tests, type: list, required: true, description: "test_pricing_sdk、test_pricing_client 相關" }

  - name: LegacyToolingDebt
    description: 隨退場須修正／清理的工具與文件
    attributes:
      - { name: warmCacheScript, type: string, example: "scripts/warm_aws_pricing_cache.py" }
      - { name: orphanPrompt, type: string, example: "backend/prompts/cost_pricing_agent_system.md" }
      - { name: openapiAndTypes, type: string, description: "同 PR 重產 openapi.json／前端型別（FR9.10）" }
      - { name: e2eCostSection, type: string, description: "舊 diagrams／stub 金額段落（FR9.9）" }
```

## 摘要

| 實體 | 處置 |
|---|---|
| LegacyHttpSurface | 刪除 |
| LegacyCostTable | rename → archive_*，保留 ≥90 天後再刪 |
| PlaywrightCalculatorBundle | 刪除（含 Python playwright） |
| PricingSurvivalSet | **保留** |
| LegacyToolingDebt | 修正／刪除／重產 |

無新業務狀態機；表生命週期僅 `live → archived → dropped`。
