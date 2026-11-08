<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->


- 2026-11-06T06:06:00Z — Q1–Q5=A：backend/iac、diagram_id 必填、download＝D1 edit、US6.1＝generate、in-memory store；關 R-01／R-02。
<!-- aidlc-wave-memory:u1-iac-api:79c6d79988d6790ac7233dd9df27ee51b68e1b06338815b826fc5180500253b2 -->


- 2026-11-06T06:20:00Z — Q1–Q4=A：Workspace 內頁、切圖忽略 in-flight、error.code 分支、允許 MSW stub。
<!-- aidlc-wave-memory:u2-iac-ui:482cb12e635f57952294f89bc614f05bf8ca3a12061199b81f2848e51133dd11 -->

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->


- 2026-11-06T06:06:00Z — error.code 對缺 diagram_id 採 missing_diagram_id／invalid_diagram（規則層）；與契約枚舉對齊於 code-gen 補進 OpenAPI。
<!-- aidlc-wave-memory:u1-iac-api:0be8716aca09b2bde1bf4d97e5ed3f41ee3a7a8288b71611b54ad19428c50fee -->


- 2026-11-06T06:20:00Z — UI unit 不產 entities／rules；閘權威留 U1，本檔只釘互動與 test-id。
<!-- aidlc-wave-memory:u2-iac-ui:5161fd1530e2b480dc52ab79007c2abe05ca82f14405ea5ea0f81bad7e1da1cf -->

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
