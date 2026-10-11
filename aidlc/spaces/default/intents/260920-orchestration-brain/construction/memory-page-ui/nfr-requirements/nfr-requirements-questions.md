# NFR Requirements 問題檔 — `U15 memory-page-ui`

> 單元類型 **`ui`**。`produces_kinds` 使本站只產出四份：
> `performance-requirements`（`[service, ui]`）、`security-requirements`、
> `tech-stack-decisions`、`traceability`。**`scalability`／`reliability`／
> `observability` 三份為 `[service]`，不適用本單元**——不是漏寫。
>
> **識別字區段：`NFR*.90+`**。實測本 intent 全部 `nfr-requirements` 產出的既有子號
> 為 1–34、40–48、50–57、60–74、80–81（以 `grep -rhoE "NFR[0-9]+\.[0-9]+"` 掃
> `construction/*/nfr-requirements/` 取得），`.90` 起的十位區段完全空著。
>
> Depth **Minimal**：只問「預設錯了會造成真實重工或真實缺陷」的題目。

## 一、本站的適用性判定（逐項對照 stage condition）

stage condition 逐字：「Performance, security, scalability, reliability, or
observability requirements needed, or tech stack selection needed.」

| 子句 | 本單元 | 理由 |
|---|---|---|
| performance | **適用** | 每次開頁 3 個請求（`[M2]`=A）、情節記憶每頁筆數由上游指派本站覆核（`OPEN-MP15-3`） |
| security | **適用** | 清單含他人設為 `platform` 的列（`functional-spec.md §四之三`）；刪除為寫入操作且留稽核 |
| scalability／reliability／observability | 不產出 | `produces_kinds` 為 `[service]` |
| tech stack | **適用（沿用既有，無新選擇）** | 仍須逐項寫下沿用哪個既有機制與其副作用是否相容（`application-design:c15`） |

## 二、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 驗證方式 | **僅 Playwright e2e**；前端無 unit／component 測試框架 | `team.md` Testing Posture（D 項不採用） |
| 每區一個請求，共 3 個 | `[M2]`=A | `functional-design-questions.md` |
| 刪除後就地移除，不整區重抓 | `[M3]`=A | 同上 |
| 不顯示總筆數 | `[M1]`=A | 同上 |
| 非擁有者的列不渲染刪除鍵；前端不過濾 | `[M5]`=A；`BR31.3` | 同上；`rules.md` |
| 本單元無端點、無持久層、無授權判定 | 全部在 `U8` | `K-14` `authorization_responsibility` |
| 審查 `R-01`／`R-02` 的處置 | 使用者裁決**帶進 `U15` 的 code-generation 計畫**，設計檔不回改 | 本 session 的人工裁決；`functional-design/memory.md` Open questions |

## 三、`OPEN-MP15-3`（每頁 20 則）的覆核——以證據收斂，不出成題目

上游把「情節記憶每頁 20 則」指派本站覆核，並明記它**沒有上游來源**。本站查到兩項
可檢查的事實，使它不再是無來源的數字：

1. **repo 對「一頁幾列」已有先例值 20**：`backend/services/user_router.py:146-147`
   的 `DEFAULT_PAGE_SIZE = 20`、`MAX_PAGE_SIZE = 100`，且該值的消費端
   `AdminPage.tsx` 是本 repo 唯一的前端分頁清單。取 20 使兩個前端分頁清單的
   每頁筆數一致。
2. **`limit = 20 + 1 = 21` 不會被伺服器收斂**：`memory_service.py:151-155` 的
   `clamp_page_size` 只在超過 `MAX_LIST_PAGE_SIZE = 200`（`:72-73`）時收斂，
   故 `BR33.1` 的探測永遠有效。

兩項皆可機械複驗，且與 `[M1]`=A 的「不宣稱總數」不衝突。候選的另一個值 50
（`DEFAULT_LIST_PAGE_SIZE`）是伺服器預設而非畫面決定，選它沒有比 20 多出任何
證據。故本站**不出題**，`OPEN-MP15-3` 以本節收斂為 `UIP-2`（見
`performance-requirements.md`）。

若日後有實測顯示 20 則使首屏不可用，處置是改 `memoryPaging.ts` 的單一常數，
無契約影響——這是可逆的決定，不值得一輪提問成本。

## 四、問題

**本站無待問題目。** 四個適用面向的每一項要求都能由上游定案或磁碟事實推得；
唯一指派給本站的開放項 `OPEN-MP15-3` 已在 §三 以證據收斂。

不出題本身是一個判定，故把它寫成可被核對的形式：若審查或閘門認為 §三 的證據
不足以取代提問，處置是在本檔追加 `N1` 並重走作答，而不是在產出內改寫數字。

## 五、歧義分析（Step 4 的 MANDATORY 檢查）

| 檢查 | 結果 |
|---|---|
| 含糊答案 | **無**（無作答） |
| NFR 目標之間的矛盾 | **一處張力，非矛盾**：`[M3]`=A（刪除不重抓）與審查 `R-01` 的建議修法（刪除後背景重抓目前頁）會使「每次刪除的請求數」由 1 變為最多 2。本站把請求預算寫成**容許該修法**的上限（`UIP-3`），使 code-generation 選哪一種都不違反本站要求 |
| 缺少量化目標 | **無**。所有效能要求皆以請求次數、筆數上限或 DOM 狀態表達，皆二元可判；本單元**不訂毫秒級延遲目標**，理由寫在 `performance-requirements.md §三` |
