# Entities — A3 Assessment LangGraph 迁徙

> Intent `261001-a2-langgraph`｜functional-design｜行為不變重構  
> 本輪**不新增**持久化資料表；實體為評核執行期與契約上的邏輯物件。  
> YAML 為 source of truth。

```yaml
entities:
  - name: AssessmentReviewSession
    description: 一次 A3 評核執行的執行期工作階段（對應既有 review 流程，非新表）
    attributes:
      - { name: review_id, logical_type: identifier, required: true, unique: true }
      - { name: diagram_id, logical_type: identifier, required: true }
      - { name: cloud_provider, logical_type: enum, required: false, allowed_values: [aws, gcp, azure, other] }
      - { name: phase, logical_type: enum, required: true, allowed_values: [rules, lens, suggestions, complete, failed] }
      - { name: suggestions_text, logical_type: text, required: false }
    constraints:
      - 前端不傳 LLM model 名；model 由後端預設／環境決定
    relationships:
      - { to: ReviewSuggestionStream, cardinality: "1:0..1", direction: owns }
      - { to: LensAnswerSet, cardinality: "1:0..1", direction: owns }

  - name: ReviewSuggestionStream
    description: Review graph 產出的建議文字串流（對外仍為 suggestion_delta）
    attributes:
      - { name: delta_text, logical_type: text, required: true }
      - { name: cumulative_text, logical_type: text, required: true }
    relationships:
      - { to: AssessmentReviewSession, cardinality: "0..1:1", direction: belongs_to }

  - name: LensAnswerSet
    description: Lens graph 以結構化 schema 產出的答案集合（取代 MCP emit_lens_answers）
    attributes:
      - { name: answers, logical_type: structured_map, required: true }
      - { name: schema_version, logical_type: string, required: false }
    constraints:
      - 形狀須與現況 orchestrator 消費的 lens 結果相容
    relationships:
      - { to: AssessmentReviewSession, cardinality: "0..1:1", direction: belongs_to }

  - name: ReviewGraphRun
    description: 獨立 compiled Review graph 的一次執行
    attributes:
      - { name: model_name, logical_type: string, required: true, default: "google/gemini-3.7-flash" }
      - { name: runtime, logical_type: enum, required: true, allowed_values: [langgraph_runtime] }
    relationships:
      - { to: ReviewSuggestionStream, cardinality: "1:1", direction: produces }

  - name: LensGraphRun
    description: 獨立 compiled Lens graph 的一次執行
    attributes:
      - { name: model_name, logical_type: string, required: true, default: "google/gemini-3.7-flash" }
      - { name: runtime, logical_type: enum, required: true, allowed_values: [langgraph_runtime] }
    relationships:
      - { to: LensAnswerSet, cardinality: "1:1", direction: produces }
```

## 摘要

本迁徙的邏輯實體集中在**評核執行期**：Session、Review 串流、Lens 答案集，以及兩個獨立 graph run。不引入新的 ORM 表；持久化仍沿用既有 `architecture_reviews` 等結構。
