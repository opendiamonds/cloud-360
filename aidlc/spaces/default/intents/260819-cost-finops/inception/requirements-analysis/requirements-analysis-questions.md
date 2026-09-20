# Requirements Analysis — 釐清問題

> Stage: requirements-analysis（Inception 2.3）· Depth: Standard · Scope: mvp
> Intent: `260819-cost-finops`（C1 第一輪）
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 本輪只做 C1；不做 C2／C3、本輪 TCO 不含 egress、不做核准流、不做 inbox | intent／scope |
| 兩段增量皆 Must；第一段可單獨上線 | scope:Q1 |
| 公開免帳號官方價目；無端點的雲走 Manual Override；禁止 Cost Explorer／帳單／價目憑證 | feas:Q2／Q1a、practices Forbidden |
| 未定價列名、不計入總額、顯示 N 項尚未定價 | feas:Q7 |
| 時數只在資源列就地改；單價僅缺價／失敗時可改並標 Manual Override | rough-mockups Q1／Q4、intent:Q15 |
| 預算掛單張架構圖；超支時總額旁「已超支」＋進產品橫幅（不能永遠關閉） | feas:Q4／Q6、rough-mockups |
| 架構師改時數；FinOps＋工程主管設預算；僅 FinOps 覆寫單價 | feas:Q5 |
| Sidebar C＋成功卡「查看預估成本」；空狀態與圖下拉 | intent:Q13、rough-mockups |
| 三層 `cost_router` → `cost_service` → `cost_calculator` + `pricing_client`；不得寫進 `user_router`／`wa_rule_engine` | practices Q4 |
| 第一個 C1 HTTP 要 allow／deny（含 403）TestClient；calculator 要 PBT | practices Q3、ADR-0006 |
| WA `COST-*` 不是 TCO | codekb／project Forbidden |
| 權限切法（view／edit／review 是否夠用）留設計 | feas R2 |
| 價目快取／重試手段留設計 | feas R5 |
| 覆寫與預算變更必須有稽核（誰改了什麼） | feas 合規掃描 |
| 時數／覆寫／預算／每圖估價須持久化（否則橫幅無法跨登入） | 本站解釋，見 memory |

## Sources

- [intent] `ideation/intent-capture/intent-statement.md`
- [scope] `ideation/scope-definition/scope-document.md`
- [feas] `ideation/feasibility/feasibility-assessment.md`
- [ux] `ideation/rough-mockups/wireframes.md`、`user-flow.md`
- [codekb] `aidlc/spaces/default/codekb/cloud/`（HEAD `c3de2c8`：無 SKU、無 calculator、無 `/api/cost*`）
- [practices] `inception/practices-discovery/team-practices.md`、`discovered-rules.md`

## Q1. 圖上沒有 SKU 時，如何得到可查價的資源身分？

> 查證：`parse_diagram_summary` 只有 id／label／style；節點契約無 sku／instance_type／region [codekb]。「對到圖上資源」目前只能列名。對應規則未定，會讓官方價路徑無法寫可測 FR。

A. 以 label／style 做最佳對應到一份本輪維護的公開 SKU 對照；對不到或一對多 → 列為未定價，FinOps 可選 SKU 或覆寫單價。
B. 本輪不做自動對應：擷取只產生列名，每一列都先未定價，直到 FinOps 指定 SKU 或覆寫單價。
C. 每列必填 SKU 型前搜尋（架構師或 FinOps）；沒選就不列在估價表。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 以 label／style 做最佳對應到一份本輪維護的公開 SKU 對照；對不到或一對多 → 列為未定價，FinOps 可選 SKU 或覆寫單價。

## Q2. 官方 list price 需要區域與幣別。圖上沒有這些欄，本輪怎麼定？

> 沒有區域／幣別就無法打公開價目或重現同一總額。線框示意 USD，非正式定案。

A. 每張架構圖必填「估價區域」＋幣別固定 USD；官方價與假設列都顯示這兩個值。
B. 全站單一預設（例如 `us-east-1`＋USD），寫在定價假設；本輪使用者不能改。
C. 能從 label 讀到區域就用，否則該列未定價（走 Manual Override），幣別 USD。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 每張架構圖必填「估價區域」＋幣別固定 USD；官方價與假設列都顯示這兩個值。

## Q3. 第一次擷取時，列上「每日時數」的預設值？

> 時數可就地改已定。未填時總額公式需要預設，否則 QA 無法重算。

A. 預設 24（全天開機），可改。
B. 預設 0，總額為 0，直到架構師填時數。
C. 預設 8（工作時段），可改。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 預設 24（全天開機），可改。

## Q4. 圓餅怎麼切？

> 線框用 compute／db／other 示意。切法決定 FR 與前端資料形狀（e2e 要斷言什麼）。

A. 固定四大類：compute／database／network／other（對不到的進 other）。
B. 一列一切塊（資源名），超過 N 列時其餘合併為 other。
C. 依對到的官方服務家族（例如 AmazonEC2、AmazonRDS）；未對到的為 other。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 固定四大類：compute／database／network／other（對不到的進 other）。

## Q5. 使用者同時有多張圖超支時，進產品橫幅怎麼呈現？

> 線框只畫一張圖。feasibility 鎖定「每次進入都看到、不能永遠關閉」，沒鎖定多圖。

A. 一條橫幅：列出超支圖數量，並點名至少一張；「前往成本畫面」預選第一張超支圖，可用下拉切換。
B. 每張超支圖一條橫幅，最多顯示 3 條，其餘以「還有 N 張」附註。
C. 一條橫幅只寫「有架構圖超過每月預算」，不點名；進成本頁再選圖。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 一條橫幅：列出超支圖數量，並點名至少一張；「前往成本畫面」預選第一張超支圖，可用下拉切換。

## Q6. 「每日時數」如何換成「每月總額」（calculator 的核心不變量）？

> 成功指標是用每日時數重算每月總費用。公開價目可能是小時價或月價。公式不定，PBT 無法寫。

A. 統一先換成小時 list price，再 `月費 = 小時價 × 每日時數 × 30`。只有月價的 SKU：`小時價 = 月價 / 730`。未定價列不參與。
B. 一律把官方價當「每月 24 小時開機」的月費，再線性縮放：`月費 = 官方月價 × (每日時數 / 24)`。
C. 本輪只接受小時價 SKU；只有月價的列視為未定價，除非 Manual Override 填的是月費。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 統一先換成小時 list price，再 `月費 = 小時價 × 每日時數 × 30`。只有月價的 SKU：`小時價 = 月價 / 730`。未定價列不參與。

## Consolidated Summary Confirmation

以下為本站 6 題答案與已鎖上游（不重問）一併列出。確認後才會產生 `requirements.md`。

1. **Q1=A** — label／style 最佳對應公開 SKU；對不到或一對多 → 未定價，FinOps 可選 SKU 或覆寫單價。
2. **Q2=A** — 每圖必填估價區域；幣別 USD；官方價與假設列都顯示。
3. **Q3=A** — 每日時數預設 24，可改。
4. **Q4=A** — 圓餅固定 compute／database／network／other。
5. **Q5=A** — 多圖超支時一條橫幅（數量＋至少點名一張）；前往成本畫面預選第一張超支圖。
6. **Q6=A** — 月費 = 小時價 × 每日時數 × 30；僅有月價時小時價 = 月價／730；未定價列不計入。

已鎖（節錄）：C1 兩段 Must、公開免帳號價目、未定價列名、列級時數、FinOps 單價覆寫、每圖預算、進產品橫幅、Sidebar C＋CTA、三層模組、403 TestClient、PBT、無 C2／C3／egress／inbox／核准流／Cost Explorer。

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
