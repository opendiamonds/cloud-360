# NFR Design 問題檔 — `U24 member-pages-ui`

> 單元類型 **`ui`**。`produces_kinds` 使本站只產出四份：
> `performance-design`（`[service, ui]`）、`security-design`（無限制）、
> `logical-components`（`[service, ui, library]`）、`traceability`。
> **`scalability-design` / `reliability-design` / `observability-design` 三份為
> `[service]`，不適用本單元**——不是漏寫。
>
> **引擎自己的 `consumes` 解析與此一致**：directive 只交付五份輸入
> （本站三份 nfr-requirements 產出 ＋ `functional-spec.md` ＋ `contract-summary.md`），
> 並未要求那三份 `[service]` 專屬的需求檔，儘管 stage 檔把它們標為 `required: true`。
> 這與 `OPEN-MP24-4` 記載的 `functional-design` 自我矛盾**方向相反**（那裡 sensor
> 無條件要求被 `produces_kinds` 排除的 `rules.md`），本站無矛盾，如實記載。
>
> Depth **Minimal**，故只問「預設錯了會造成真實重工」的題目。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 不快取橫幅查詢 | `[N2]`=A（`UIP-2`：每次 `Layout` 掛載各一次） | 本單元 `nfr-requirements` |
| 清單規模上限 | `[N1]`=A（`UIP-1`：100 列，來源 `MAX_PAGE_SIZE`） | 同上 |
| console 訊號義務 | `[N3]`=B ＋ 審查 `R-07` 的兜底規則（`SEC-U24-6`） | 同上 |
| 零新依賴／零新端點／零新環境變數 | `TS-U24-1`／`TS-U24-7`、`security-requirements` §一 | 同上 |
| 橫幅宿主無條件渲染 ＋ `role="status"` ＋ 內不得放可互動內容 | `BR21.1`、`functional-spec.md` §二之一／§二之二 | functional-design |
| 載入／錯誤一律經 live region，**不得**用 `AdminPage.tsx:104` 的 4 秒 toast | `BR27.1`、`frontend-components.md:176` | 同上 |
| live region 元件**由本單元自建**、`U23` 之後沿用 | `[N4]`=A（推翻 `[F3]`=A 的排序理由） | 本單元 `nfr-requirements` §四 `HO-U24-1` |
| 失敗行為（403 永久失敗不重試、其餘保持空不顯示錯誤） | `BR21.3` logic 兩分支 | functional-design |
| 三層以上的韌性樣式（circuit breaker／bulkhead／retry backoff） | **本單元無標的**：零自有端點、零外呼、零持久層；重試策略已由 `BR21.3` 定案為「403 不重試、其餘下次落地重試」 | 本檔 §三 |

## 二、問題

## ND1. 新建的 `<LiveRegion />` 要掛在哪一層、用什麼 role？

`[N4]`=A 把這個元件的建造責任移進本單元，而它的形狀至今**沒有任何上游決定**
（`frontend-components.md:53` 原本逐字寫「不在本單元的新建清單裡」）。實查前端現況：

| 查證 | 結果 |
|---|---|
| 既有可重用的 live region 元件 | **不存在**。全前端只有兩處 `aria-live` 命中，皆在 `EstimateAdvicePanel.tsx`（`:278` 的 `sr-only` ＋ `aria-live="polite"`、`:291` 的可見 `<p>`），都是就地內嵌、非元件 |
| 既有 `role="status"`／`role="alert"` | **0 處** |
| `Layout.tsx` | 僅 **22** 行；`:16` 為 `<div data-slot="cost-banner" />`、`:17` 為 `{children}` |
| 本單元的使用點 | **兩處**（成員清單頁、成員詳情頁，見 `frontend-components.md:41`／`:46`） |
| 同層的另一個 live region | `BR21.1` 要求橫幅宿主帶 `role="status"` 且位於 `Layout`（`[F1]`=A） |

- **A. 每頁各掛一個，元件不持有狀態（props 驅動）、固定 `role="status"`**：
  貼合唯一既有先例（`EstimateAdvicePanel` 自己掛自己的）。`Layout` 內維持**只有一個**
  `role="status"`（橫幅宿主），不產生兩個互相競爭的播報區。`U23` 以同樣方式沿用，
  依賴面只有「元件檔存在」。代價是兩個頁面各自持有訊息狀態、各自接線一次。
- **B. `Layout` 層單例 ＋ context 推送訊息**：只有一個實例，頁面用 hook 送訊息。
  代價有三：`Layout` 內會出現**第二個** `role="status"` 區域（與橫幅宿主並存）；
  `team.md` 的 lint 結構約束要求 Context 拆兩檔（`.tsx` provider ＋ `.ts` hook），
  為此新增一組 context 是本單元唯一的新增全域狀態面；且 `U23` 之後要沿用的不只是
  一個元件，而是 `Layout` 的接線，依賴面變大。
- **C. 每頁各掛一個，但 role 由 prop 切換（`status`／`alert`）**：錯誤可用 assertive 播報。
  代價是 `role="alert"` 會**打斷**使用者當下的朗讀，而上游沒有任何需求區分 polite／
  assertive（`BR27.1` 逐字只要求「存在帶 `role` 的 live region」）；多一個旋鈕會讓
  `U23`／`U24` 兩站用法不一致，而沒有任何測試能鎖住一致性。
- **D. 不建元件，兩頁各自內嵌 `sr-only` ＋ `aria-live="polite"`**（照 `EstimateAdvicePanel` 做法）：
  零新元件。代價是直接牴觸 `HO-U24-1`（必須做成可共用形狀供 `U23` 沿用）與
  `team.md` 的「單一真實來源」——兩份內嵌副本且前端沒有 unit 測試框架可寫
  「鎖住兩者一致」的測試；這正是 `[N4]`=C 被排除的同一個理由。

`[Answer]`: A
<!-- 作答時間 2026-10-11T01:01:49Z（先執行 `date -u` 取值後才寫入本行；本 session 已在 `nfr-requirements` 站因『先寫時間戳再跑 date』被自己抓到一次，見該站日記）。選項全文已於提問前逐字寫入本檔，選單內容與本檔一致。 -->
