# Stage Memory — Reverse Engineering

> 本 stage 執行期間的觀察日誌。四個標準 H2，新條目 append 到既有標題下。

## Interpretations

- 2026-08-17T00:05:00Z — codekb 有兩份並存（`codekb/cloud-360/` 與 `codekb/cloud/`），基準 commit 相同但屬不同 intent；依 `codekb-path` 的解析結果只更新 `cloud-360`，不觸碰 `cloud`。判定依據是工具輸出而非目測，避免兩份互相覆寫。
- 2026-08-17T00:05:30Z — 測試數量以靜態計數（`grep -c`）取得而非實際執行（agent 環境缺 `fastapi`／`hypothesis`，Playwright 需完整 stack）；artifact 內每個測試數字都標註計數方式，並明寫「repo 內有 212 個測試函式」不等於「212 個測試通過」。三個驗證器與 ESLint 是真的跑過的，可引用為執行結果。

## Deviations

- 2026-08-17T00:06:00Z — conductor 的 brief 寫「CI 實際有 5 個 job」，architect 解析 `ci.yml` 的 `jobs:` 區塊實測為 **4 個**（`repo-contract`／`frontend`／`backend`／`docker-build`）；照實測寫入 codekb 並在表格中區分「job 數（4）」與「實質檢查步驟數（11）」，第 5 道阻擋來源是 `ci.yml` 之外的 `ui-regression`。brief 的數字來自 conductor 的 `grep -cE "^  [a-z-]+:$"`，該 regex 會誤匹配非 job 的鍵。
- 2026-08-17T00:06:30Z — developer scan 報「45 個 operation 中 29 個無 HTTP 層測試」，architect 複驗為 **42/45**：scan 只算了四個零測試 router，漏掉 `user_router` 其餘 13 個未覆蓋的 operation。以複驗值寫入。
- 2026-08-17T00:07:00Z — developer scan 把「`aidlc_sync_*.py` 不存在」判為規格與實作脫節。實際是那三支腳本只存在於未合併的 `danniel/feat/github-sync-phase1`（PR #508 仍 OPEN）；以 `git branch --contains` 與 `git merge-base --is-ancestor` 逐一確認後，記為「正確的前瞻引用」而非文件漂移，並把「PR #508 合併」列為觸發完整重跑的條件。

## Tradeoffs

- 2026-08-17T00:07:30Z — 採 pipeline（developer 掃描 → architect 綜合）而非單一 agent 全包：換得 context 隔離與獨立複驗（architect 實際推翻了 scan 的兩個數字）。代價是兩段式的總時長約 35 分鐘。中間結果走 scratchpad 檔案傳遞，不把 586 行掃描結果貼進 brief。
- 2026-08-17T00:08:00Z — 實測發現 `team.md` 有 7 項記載已過時（依賴釘選、型別契約鏈、CI 檢查步驟等），但**未修改規則層**。理由：規則層變更須走 practices-discovery 的 affirmation gate，RE stage 逕行修改會繞過該 gate。改為在 `code-quality-assessment.md` 與 `dependencies.md` 記載落差並標註待覆核，同時另列「複驗後仍成立」的 9 項，避免下游誤以為整段 `team.md` 都過期。

## Open questions

- 2026-08-17T00:08:30Z — `team.md` 的 7 項落差待下次 practices-discovery 覆核；在那之前，讀 `team.md` 的 stage 應併讀 `code-quality-assessment.md` 的落差節。
- 2026-08-17T00:09:00Z — `unsupported` 是一組雙向皆死的契約（前端兩處處理、後端從未產生），且所有 CI 檢查全綠。修法是只清實例，還是同時補「SSE 事件名契約」的機制？後者才防得住下一個事件名再壞。留給 requirements-analysis 判定是否納入本 intent 範圍——本 intent 的 bug 是 contract 檢查的 diff 基準，兩者無直接關聯。
- 2026-08-17T00:09:30Z — `codekb/cloud/` 與 `codekb/cloud-360/` 並存且基準不同，本次只更新後者。兩份是否該合併、或明確定義各自的適用範圍，尚無定論。
- 2026-08-17T00:10:00Z — `fetch_icon_from_n8n()` 殘留一條無 log 的降級路徑（回應為 JSON dict 且巢狀 `data` 也取不到 SVG 時），記為 T-17。屬 PR #499／#508 的範圍，不在本 intent 內。
