# 實體：U7 `cost-advice-agent`

## Source of truth

```yaml
entities:
  - name: Advice
    description: 每 EstimateSet 至多一列建議（PK=estimate_set_id）；U7 擁有正文與狀態轉換
    fields:
      - { name: estimate_set_id, type: int, required: true, pk: true }
      - { name: status, type: enum, required: true, allowed_values: [generating, completed, failed] }
      - { name: saving_text, type: string, required: false }
      - { name: comparison_text, type: string, required: false }
      - { name: quality_text, type: string, required: false }
      - { name: unavailable_reasons, type: object, required: false, note: "如 comparison: insufficient_clouds；timed_out: true" }
      - { name: started_at, type: datetime, required: false }
      - { name: completed_at, type: datetime, required: false }
    invariants:
      - UNIQUE(estimate_set_id)
      - status=completed 時至少 saving_text 非空（Must）；Should 類可空但須在 unavailable_reasons 說明

  - name: AdviceEvent
    description: SSE 事件（不持久化）
    fields:
      - { name: type, type: enum, allowed_values: [progress, heartbeat, completed, failed, timeout] }
      - { name: content, type: object, required: false }
      - { name: advice, type: AdviceSnapshotInline, required: false, when: "type in completed|failed" }

  - name: AdviceOrchestrator
    description: 生命週期、去重、逾時、呼叫 agent、寫 Advice
    fields:
      - { name: timeout_minutes, type: int, default: 5 }

  - name: CostAdviceAgent
    description: LangGraph 建議圖；經 U6 runtime 呼叫 OpenRouter
    fields:
      - { name: optional_pricing, type: bool, default: true }

  - name: CatalogPriceNote
    description: 查價結果僅作文案材料；非明細欄位
    fields:
      - { name: kind, type: enum, allowed_values: [hit, miss, unsupported, skipped] }
      - { name: hourly, type: decimal, required: false }
```
