# Performance Requirements — `U15 memory-page-ui`

> 單元類型 `ui`，故 `produces_kinds` 使本站只產出 performance／security／
> tech-stack／traceability 四份；**scalability／reliability／observability 三份為
> `[service]`，不適用本單元**（不是漏寫）。
>
> **識別字**：可繼承 inception NFR 的用 `NFR<parent>.90+`；**無法誠實繼承任何
> inception NFR 的，以 `UIP-n` 宣告為孤兒**並在 §二 寫明理由（沿用 `U24` 的同形處置）。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/memory-page-ui/functional-design/functional-spec.md` | `W1`–`W5`、§四的 API 實際形狀、§四之一的每頁 20 則 |
| `construction/memory-page-ui/functional-design/rules.md` | `BR32.2`、`BR33.1`、`BR33.3`、`BR34.3`、`BR34.4` |
| `construction/memory-page-ui/functional-design/frontend-components.md` | §四之一（`user.id` 未決視窗）、§五（請求參數） |
| `inception/requirements-analysis/requirements.md` | `NFR1`–`NFR11` 的逐條原文 |
| `inception/contract-design/contract-summary.md` | `K-08`（記憶 API）、`K-14`（本單元） |
| `codekb/chiton/technology-stack.md` | 前端技術棧現況 |

## 一、可繼承 inception NFR 的要求

**無**。`NFR1`–`NFR11` 中與效能相關的三條（`NFR1` 準確率、`NFR3` 首字回應時間、
`NFR11` 頁面切換次數）都不以本單元為量測對象，逐條理由見 `traceability.json`。
本單元的效能要求因此全部以 `UIP-n` 宣告於 §二。

## 二、本單元自有的效能要求（`UIP-n`，無 inception 父條）

| ID | 要求 | 目標 | 量測方式 | 來源 |
|---|---|---|---|---|
| `UIP-1` | 開啟記憶頁時的請求數有上限 | `GET /api/memory/records` **恰 3 次**（每 kind 一次），且三者**並行**發出 | Playwright `page.on('request')` 計數並比對三個 `kind` 參數；並行以三者的發出時間皆早於任一者的回應完成時間斷言 | `[M2]`=A；`BR32.2` |
| `UIP-2` | 情節記憶每頁筆數 | 每頁渲染 **≤ 20** 則；請求帶 `limit=21` | Playwright 攔截請求斷言 `limit=21`，並以 21 則種子資料斷言第一頁渲染 20 則 | `OPEN-MP15-3` 經本站收斂（`nfr-requirements-questions.md §三`）；`BR33.1` |
| `UIP-3` | 刪除一則記憶的請求預算 | 每次刪除 **1 次 `DELETE` ＋ 至多 1 次** `GET`（僅限該 kind、僅限目前頁）；**不得**重抓另外兩區 | Playwright 計刪除前後的請求，斷言沒有任何其他 `kind` 的 `GET` | `[M3]`=A；`BR34.4`；並容許審查 `R-01` 的背景重抓修法（見 §三之一） |
| `UIP-4` | 翻頁只重抓情節記憶區 | 翻頁時**恰 1 次** `GET ?kind=episodic`，語意與程序兩區的 DOM 不重渲染為 `loading` | Playwright 斷言翻頁期間 `memory-zone-semantic`／`memory-zone-procedural` 未出現 loading 標記 | `BR32.2`、`functional-spec.md` `W3` 第 2 步 |
| `UIP-5` | 語意與程序記憶一次取得的上限 | 請求帶 `limit=200`；回傳 200 筆時區標題顯示「200+ 則」 | Playwright 攔截請求斷言 `limit=200`；以路由攔截餵 200 筆斷言標題 | `BR33.3`、`BR32.4`；`memory_service.py:72-73` |
| `UIP-6` | 刪除進行中不阻塞其他條目 | `deleting` 期間其他條目的刪除入口仍可點擊 | Playwright 以延遲回應的路由攔截讓 `DELETE` 掛住，對另一則點刪除並斷言確認列展開 | `BR34.3` |

### 二之一、為什麼這六條不繼承任何 inception NFR（逐條，不留空白）

- `UIP-1`、`UIP-3`、`UIP-4`：請求次數是本單元設計選擇的直接後果，`NFR1`–`NFR11`
  沒有任何一條以「前端請求數」為標的。最接近的 `NFR9`（成本原則）逐字限定為
  「本平台自身的 **LLM** 花費」，本單元零 LLM 呼叫。
- `UIP-2`、`UIP-5`：筆數上限源自伺服器的 `clamp_page_size` 與本站覆核，非 inception 要求。
- `UIP-6`：互動回應性，源自 `interaction-spec.md` 的 States 表。

## 三、刻意不訂的目標

### 三之一、`UIP-3` 為何寫成「至多 1 次 GET」而非「0 次」

`[M3]`=A 的字面是「就地移除，不重抓」，照字面應為 0 次。但審查 `R-01` 查出
「就地移除 ＋ offset 分頁」會使翻頁漏掉遞補上來的列，且刪空第一頁會誤顯示
`empty`。使用者已裁決把該修法帶進 code-generation 計畫。若本站寫成「0 次」，
就等於在設計層預先否決了那個修法。故預算寫成「至多 1 次、僅限該 kind、僅限目前頁」
——它同時容許兩種實作，並守住 `[M3]`=A 要防的真正失敗：**另外兩區被無故重抓與閃動**。

### 三之二、不訂毫秒級延遲目標

本單元的延遲完全由 `U8` 的 `GET`／`DELETE` 決定，前端沒有可調的計算熱點
（三個 `memoryPaging.ts` 純函式皆為 O(n)、n ≤ 200）。在這裡訂一個 p95 毫秒數，
量到的會是 `U8` 與網路，而不是本單元——那會讓一個與本單元無關的退化在本單元的
驗收上紅燈。延遲目標屬 `U8` 的 NFR。

### 三之三、不訂 `user.id` 未決視窗的時間上限

`frontend-components.md §四之一` 規定 `user.id` 成為 number 前不掛載三區。該視窗
長度等於 `/api/auth/me` 的回應時間，同樣不屬本單元可控。**但它有一個本單元必須
處理的失敗面**：審查 `R-03` 查出 `login()` 吞掉 `/me` 失敗時 `user.id` 永遠是
`undefined`，頁面會無限轉圈。這是可靠性缺口而非效能目標，處置隨 `R-01`／`R-02`
一起帶進 code-generation 計畫（`security-requirements.md §四之一` 交接表）。
