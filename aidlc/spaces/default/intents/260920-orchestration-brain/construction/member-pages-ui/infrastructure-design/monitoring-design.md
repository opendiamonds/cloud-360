# Monitoring Design — `U24 member-pages-ui`

## 零、這份檔在做什麼，以及它誠實地不做什麼

本單元**不交付任何 metrics 收集、告警規則或 SLI／SLO**。形狀沿用同 intent 的
`brain-infra` 先例（該站的 `monitoring-design.md` 以同樣的「不交付什麼」開篇）。

理由一句話：**本 intent 至今沒有任何告警通道或 dashboard**
（`U10` 已登記為 `OPEN-N10-4`），而本單元是純前端單元，連伺服器端指標面都沒有。
把「有指標」寫成「有監控」是本 repo 已記過的失敗形狀，本檔不重犯。

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/nfr-design/security-design.md` | §四 的 `FailureSignal` 形狀與 `SEC-U24-6` 的兜底規則 |
| `construction/member-pages-ui/nfr-design/logical-components.md` | §二 的四個失敗域與降級路徑 |
| `construction/member-pages-ui/nfr-design/performance-design.md` | `UIP-1`–`UIP-5` 的量測方式（全為 Playwright e2e） |

## 一、今日的可觀測面（完整清單，只有兩項）

| # | 訊號 | 誰消費 | 保留 |
|---|---|---|---|
| 1 | `FailureSignal` 的 console 輸出（`kind` ＋ `endpoint` 兩個字面值聯集欄位） | **開發者的瀏覽器 devtools** ＋ e2e 的 `page.on('console')` 斷言 | 不保留——瀏覽器 session 結束即消失 |
| 2 | Playwright e2e 的執行結果（`junit.xml` → Kiwi TCMS） | `ui-regression` 的 `post-steps` 閘門 ＋ Kiwi 的歷史結果 | Kiwi 保留，per-run |

**第 1 項不是監控。** 生產環境沒有人在看瀏覽器 console，這是 `[N3]`=B 選項文字
逐字揭露的代價（「生產環境沒有人在看 console，等於只對開發期有用」）。它的價值在
開發期與 e2e 可斷言性，不在運行期可觀測性。

## 二、Metrics & KPIs — **本單元不交付任何 metrics 收集**

| 候選指標 | 為什麼不交付 |
|---|---|
| 成員頁載入失敗率 | 無收集機制（前端無 telemetry 送出路徑），而新增一條會推翻「零新端點」的結構宣稱——`[N3]`=C 被排除的理由 |
| 橫幅查詢的請求量（`UIP-2` 的未設界負載） | 同上。該負載已在 `performance-design.md` §三 與 `security-design.md` §六 的 DoS 列**如實記為未設界**，而不是記為已觀測 |
| 100 列上限的實際觸發次數 | 同上。`OPEN-MP24-6`（>100 成員的專案無法管理）因此**不會被自動發現**——只會由使用者回報 |

## 三、Alerts — **本單元不交付任何告警規則**

通道不存在（`OPEN-N10-4`）。本站**刻意不另立一個同義缺口**——沿用 `U10` 那一條，
與 `U11` 在 `observability-requirements.md` 的處置一致（該站的教訓逐字：
「在它關閉之前，這些指標的實際消費方式是人工查詢——不把『有指標』寫成『有監控』」）。

值得告警但目前無處可送的訊號有二：① 成員頁載入失敗率異常；
② 橫幅查詢的 403 比例異常（可能意味 RBAC seed 被改壞）。登記在此供 `OPEN-N10-4`
關閉時一併接上，**不在本站新開缺口編號**。

## 四、SLIs／SLOs — **本單元不交付**

`org.md` 的 operation phase guardrail 要求 SLO 量化到百分比與時間窗，而本單元：

- 沒有自己的服務可定義可用性——六個端點的可用性屬 `U19`。
- `NFR11.80`／`NFR11.81`（頁面切換次數）是**次數**判定而非比率，且其計分母體屬
  `user-stories` 的 `M-3`（見 `performance-design.md` §一 的更正），本單元只是貢獻者。
- 唯一屬於本單元的二元判定是 `UIP-1`–`UIP-5` 的 e2e 斷言——那是**閘門**不是 SLO。

## 五、Logs & Tracing

| 面向 | 本單元 |
|---|---|
| 結構化日誌 | **無**。前端不送日誌；`SEC-U24-1` 另禁止 console 含使用者文字或識別字（本 repo 為 public、Actions log 公開可讀） |
| correlation id 傳遞 | **無**。本單元不新增跨服務呼叫；六個消費點都是單一 HTTP 往返 |
| 分散式追蹤 | **不適用**。無新服務邊界 |
| 伺服器端日誌 | 由 `U19` 的端點承載，本單元不影響 |

## 六、本單元對「可觀測性」的唯一實質貢獻：讓失敗**可斷言**

不是讓失敗可觀測，而是讓它**可被測試抓到**——這是本單元在無通道前提下能做的事：

| 失敗路徑 | 可斷言的形式 | 來源 |
|---|---|---|
| 成員清單抓取失敗 | console 有一筆 `kind: 'members-fetch-failed'` | `SEC-U24-6` |
| 橫幅查詢任何非 2xx 與網路失敗 | console 各有一筆（403 與 500 各構造一次） | `SEC-U24-6`（審查 `R-07` 的兜底規則） |
| 邀請的 422 物件陣列型 `detail` | console 有一筆 `kind: 'invite-validation-failed'` | `BR23.1`／`SEC-U24-4` |
| 任一訊號含使用者文字 | 同一條 e2e 斷言訊號**不含**受測帳號的 `display_name` 與 email | `SEC-U24-1` |

這四條合起來使 `construction.md` 的 phase guardrail（「silent failures are not
acceptable」）在本單元**可被機械驗證**，而不只是一句宣言。
