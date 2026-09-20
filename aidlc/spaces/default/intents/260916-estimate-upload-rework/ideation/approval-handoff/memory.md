# Stage Memory: approval-handoff

## Interpretations

- 2026-09-16T07:00Z — 彙整型 stage 只問未被上游定案的事項。stage 檔範例題六題中省略三題（rough mockups 是否反映願景、market research 是否支持投資、mobs 是否已配置排程）：`rough-mockups`、`market-research`、`team-formation` 三站在本 scope 均為 SKIP，沒有產出可確認，問了也無從作答。省略清單登錄於問題檔 [S5]。
- 2026-09-16T07:00Z — 「所有關係人是否同意意圖與範圍」不重問：scope-definition Q8＝A 已定由 Danniel 一人代表三種角色驗收，intent-capture Q8＝B 已定各階段核可關卡即為確認機制。兩者合起來已經回答了這題。
- 2026-09-16T07:00Z — 「是否有預算／資源承諾」改寫為 Q2 的人力與平行度提問。本專案沒有預算概念，但 intent-backlog 的 open item 明載第一梯次能否平行取決於人力，且該答案直接決定 value-first 的實際順序與窗口期長度——這才是本專案脈絡下「資源承諾」的實質內容。

## Deviations

- 2026-09-16T07:00Z — `inline_context_paths` 的 21 個路徑與 scope-definition 進入時的集合**完全相同**（同一批檔案，僅順序不同），且已在本 session 的 scope-definition 階段逐一讀取、內容仍逐字在 context 中。本次未重複讀取。記錄此偏離以供稽核：若日後 context 曾被壓縮，此判斷即不成立，應重讀。
- 2026-09-16T07:00Z — 引擎於本 stage 進入時回報 `scope-definition` 漂移並建議重跑（[S4]）。未依建議重跑，理由與處置交由 Q4 由人工裁決，不由 conductor 逕自決定。

- 2026-09-16T07:20Z — 使用者在核可關卡提出「三朵雲想保留查詢官網 API 的功能」，推翻 IC-2、FE-5 與 ADR-0017 §1／§3。未逕自把它當成小幅澄清吸收掉，也未逕自啟動重跑：先以兩輪追問界定反轉範圍（是 agent 工具還是系統例行核對、查得的價格能否回寫明細、AH-1 的機械檢查是否被取代），再由使用者選擇收斂方式（Q＝A 修訂 ADR 並就地更新）。
- 2026-09-16T07:20Z — 使用者對「查得價格如何使用」初選 C（直接改寫明細），未照單全收。提出三項反對後改選 A（只寫進建議文字）。反對理由：官方目錄價是未折扣定價而估價表可能含 CUD／RI／SP，覆蓋會把對的改成錯的；agent 只查部分品項會使明細變成無標示的混合來源；與「上傳的估價表是主體」直接矛盾。

## Tradeoffs

- 2026-09-16T07:20Z — **就地修訂 vs 重跑上游**。選擇在 ADR-0017 追加 §8 並就地更新六份產出，而非重跑 feasibility 與 scope-definition。省下的是兩站共 18 題的重問；付出的是 `intent-statement.md` 與 `feasibility-questions.md` 的字面表述留在被推翻的狀態，下游若只讀上游檔會讀到錯的。已在 `phase-check-ideation.md` 的檢查一與檢查四各記一筆。
- 2026-09-16T07:20Z — **ADR 自我修訂 vs 另開 ADR-0018**。使用者選 A（修訂 0017）。好處是 `pricing_client` 的完整處置史留在同一份檔案，不必兩份對讀；代價是 §1 與 §3 現在必須配著 §8 才能讀，已在兩節各加「不得單獨引用」的標注。
- 2026-09-16T07:20Z — **`render-env.sh` 三種修法**。查證後發現這不是誤判：憑證管線本身違反 ADR-0001 與 `project.md` 的 C1 計價規則。因此未採「迴避字串」或「放寬 validator」，而是移除整條管線。代價是 AWS 查價退回公開 Bulk API（較慢），但該子系統本就在退場清單上。

## Open questions

- [open] ADR-0017 建立後 25 分鐘即自我修訂，顯示 ideation 的產品邊界到最後一站仍未收斂。本次選擇就地修補，但若 inception 再發生同類反轉，重跑 intent-capture 會比累積修補便宜。何時該從「修補」切換到「重跑」沒有既定判準。
- [open] `validate_no_obvious_secrets()` 只掃 `contract_files()`，不掃全部追蹤檔。`DEPLOY.md` 原本含 `AWS_SECRET_ACCESS_KEY=...` 的範例行卻不被檢查，比被擋下的 `render-env.sh` 危險。該範例行已於本次移除，但掃描範圍的缺口仍在，且與本 intent 無關。
- [open] CAP-8 的四條界線沒有機械強制手段。第 3 條（不得在明細加現價欄位）最容易在實作時被自然地跨越。
