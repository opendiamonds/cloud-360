# Stage Memory: scope-definition

## Interpretations

- 2026-09-16T05:35Z — 本 stage 為 `execution: ALWAYS`，不做適用性判定。出題前先以唯讀方式查證 code 現況（`cost_router.py` 的 9 個端點、`models.py` 的 4 張表、`CostPage.tsx` 964 行、`App.tsx` 的 `/cost` 路由、`Sidebar.tsx` 的 C1 權限入口），結果登錄於問題檔 `## Sources` [S1]–[S5]，供題幹與選項引用；查證細節不寫進 ideation artifact。
- 2026-09-16T05:35Z — 上游 intent-capture（6 項）與 feasibility（10 項）已定案的產品邊界與技術約束一律不重問，可引用的具體選項字母逐項列於 [S7]。本 stage 只問範圍邊界、優先序、排除清單與交付批次。
- 2026-09-16T05:35Z — 把上游審查與 RAID 留下的四個待處置項（R-01 三類全必備的執行風險、R-03 指標缺量級錨點、R-04 驗收代表、ISSUE-01 的 M2 ADR 時點）各自轉成一題，而非留在文件裡等下游發現。ISSUE-01 阻擋 construction，越晚指派改寫成本越高。

## Deviations

- 2026-09-16T05:35Z — 問題檔初稿誤把八題的 `[Answer]:` 連同 Consolidated Summary Confirmation 一併預填成自己推測的選項，等同代使用者作答。發現後以腳本清空全部九處，再向使用者提問。此為 `user-stories:260822-us-L2`（答案拿到才寫回）的反向違例：答案還沒拿到就先寫了。

## Tradeoffs

- 2026-09-16T05:50Z — Q1 的答案（省錢建議為核心 Must、另兩類降 Should）與 intent-capture 已核可的「三類全必備、不分先後」牴觸。判定為**審查指派的收斂**而非下游擅自縮小範圍：R-01 的 required action 逐字寫「若存有任何優先順序共識，應在 scope-definition 明確登錄」。依 team.md 的 correction（下游經人工確認的語意變更不回改已核可的上游 artifact），`intent-statement.md` 不動，以本 stage 問題檔的確認紀錄向下游傳遞，並在 scope-document 的 CAP-4 就地註明降級依據。
- 2026-09-16T05:50Z — CAP-5（品質檢查）雖降為 Should，但它是 RISK-01（解析靜默錯誤）的唯一防線。選擇在 scope-document 把這個落差就地寫明，而不是讓 MoSCoW 等級單獨代表它的重要性——只看等級的人會低估拿掉它的後果。
- 2026-09-16T05:50Z — intent-backlog 不做 WSJF／RICE 數值評分。單一決策者、多數為 Must、依賴序由技術結構決定，沒有真實的相對價值輸入；此條件下的分數是虛假精確（沿用 `scope-definition:c5`）。

## Open questions

- 2026-09-16T05:50Z — Q3（同批部署）與 Q7（value-first）合起來會產生一段產品能力低於現狀的窗口期：自動估價已移除、明細可用、但建議尚未交付。兩個答案各自成立，是組合才浮現的後果，故不另開題，改為在 Consolidated Summary Confirmation 明白揭露後果讓使用者在確認前看到（沿用 `requirements-analysis:260822-ra-c5` 的形狀）。窗口期長度移交 delivery-planning。
- 2026-09-16T05:50Z — PU-2 的結構化資料模型會決定 PU-8 能否做機械檢查。若 domain-design 把明細存成無型別 JSON blob，品質檢查就只剩 LLM 一條路，RISK-01 的緩解空間會在設計階段被無聲關閉。已登錄於 intent-backlog 的 open items。
