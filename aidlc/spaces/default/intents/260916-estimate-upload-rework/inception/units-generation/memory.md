# Stage Memory: units-generation

## Interpretations

- 2026-09-18 — 本站只產出拓樸 DAG，不推薦實作順序或關鍵路徑（stage 檔 NOTE）；ideation 的 value-first 排序留給 delivery-planning。
- 2026-09-18 — Q1–Q7 全選 A，採草案九單元；Q3=A 刻意讓單元圖不鏡射元件圖上的 `CostAdviceAgent → PricingLookup`（FR5.10 可降級）。
- 2026-09-18 — Q6=A 共同部署約束僅 U3+U8；UI 已拆成 U8/U9，建議呈現（U9）不在同批約束內。

## Deviations

- 2026-09-18 — story-map 以 FR 取代 US（user-stories SKIP），符合 stage 檔 fallback。

## Tradeoffs

- 2026-09-18 — Q3=A：單元圖不鏡射 CostAdviceAgent→PricingLookup，換取建議與憑證管線解耦；行為約束寫進 U7。
- 2026-09-18 — Q4=A：UI 拆兩換拓樸獨立，接受 U8↔U9 合併衝突面。
- 2026-09-18 — U3 與 U8 同批部署寫成約束而非 depends_on，避免偽相依扭曲拓樸。

## Open questions

- 2026-09-18 — OQ-UG1／OQ-UG2 見 unit-of-work.md。
