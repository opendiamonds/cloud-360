# Logical Components — `U24 member-pages-ui`

> 本檔是 NFR 設計與 Infrastructure Design 之間的橋：以元件層視角說明
> NFR 樣式落在哪裡、失敗域邊界在哪、爆炸半徑多大。
> 單元類型 `ui`，故不含任何伺服器端或基礎設施元件。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/functional-design/frontend-components.md` | 元件樹、19 個 `data-testid`、宿主與操作列的分離 |
| `construction/member-pages-ui/nfr-requirements/tech-stack-decisions.md` | `TS-U24-4`（兩層抓取）、`TS-U24-6`（live region 由本單元自建） |
| `construction/member-pages-ui/nfr-design/nfr-design-questions.md` | `[ND1]`=A（live region 的掛載層與 role） |

## 一、邏輯元件清單

| 元件 | 類型 | 責任 | 持有狀態 | NFR 樣式落點 |
|---|---|---|---|---|
| `<MembersListPage>` | 頁面 | 清單渲染、邀請入口、`canManage` 推導 | 成員陣列、載入／錯誤、播報訊息 | `UIP-1` 渲染閘、`UIP-4` 單一請求、`BR22.3` |
| `<MemberDetailPage>` | 頁面 | 角色下拉、移出＋二次確認、變更紀錄 | 該成員、載入／錯誤、播報訊息 | `UIP-3` 就地更新、`UIP-5` 渲染閘（待命） |
| `<ReselectionBannerHost>` | `Layout` 內常駐 | **無條件**渲染、`role="status"`、只放要被朗讀的文字 | 無（文字由上層傳入） | `BR21.1`、`UIP-2` 的請求點 |
| `<ReselectionBannerActions>` | `Layout` 內 | 「知道了」與「查看成員」兩個控件 | 無 | `BR26.2`／`BR26.3`；**位於宿主之外**（`role="status"` 隱含 `aria-atomic="true"`，區域內不得放可互動內容） |
| `<LiveRegion />` | **本單元新建**、可共用 | 以 props 接收文字並渲染於帶 `role="status"` 的容器 | **無**（純 props 驅動） | `BR27.1`、`SEC-U24-6` 的播報面；`HO-U24-1` 要求可共用形狀 |
| 抓取函式層 | 純函式 | 發請求、回傳資料，**不碰 state** | 無 | `TS-U24-4`（`react-hooks/set-state-in-effect` 為 error 級） |

介面層形狀（≤15 行，說明設計決定，非實作）：

```tsx
// [ND1]=A：不持有狀態、role 固定、每頁各掛一個實例
export interface LiveRegionProps {
  message: string;      // 空字串＝不播報
  srOnly?: boolean;     // 預設 true，沿用 EstimateAdvicePanel.tsx:278 的 sr-only 先例
}
// role="status" 寫死於元件內，不開放 prop（[ND1]=C 被排除：assertive 會打斷朗讀，
// 而上游無任何需求區分 polite／assertive）
```

### 一之一、上游三處仍寫「由 `U23` 提供」（審查 `R-06`／Minor 對齊註記）

`[N4]`=A／`TS-U24-6`／`HO-U24-1` 已把 `<LiveRegion />` 的建造責任移進本單元，
但本站**消費的** functional-design 產出有四處字面仍指向 `U23`：

| 位置 | 逐字內容 |
|---|---|
| `rules.md:303-304`（`BR27.1` 的 `logic`） | 「文字寫入 **U23 提供的** live region 元件」，`source` 為 `[F3]`=A |
| `frontend-components.md:41`／`:46`（元件樹） | 「（由 `U23` 提供，`[F3]`=A）」 |
| `frontend-components.md:53` | 「**`<LiveRegion />` 不在本單元的新建清單裡**」 |

依 `[N4]`=A／`TS-U24-6` 應**讀為由 `U24` 自建**。依 `refined-mockups:c3`
**不回改已核可的上游**（且 `rules.md` 的 yaml 區塊自稱 `source-of-truth`，
而本站無權改寫它）；本節即為該落差的紀錄。

**為什麼需要單獨記**：本站自檢第 5 項把這個事實的落點只掃到本站三份產出，
並判「與上一站一致（不矛盾）」——漏了**同時被消費的 functional-design**。
跨檔傳播的掃查範圍應包含 `consumes` 清單裡的檔，不只本站 `produces`。

## 二、失敗域與爆炸半徑

| 失敗域 | 範圍 | 爆炸半徑 | 降級路徑 |
|---|---|---|---|
| 成員清單抓取失敗 | 單一頁面 | **一個頁面**：清單不顯示，其餘導覽與其他頁面不受影響 | 顯示錯誤文字 ＋ `SEC-U24-6` 的 console 訊號；重試由使用者重新進入頁面觸發（無自動重試） |
| 橫幅查詢失敗 | `Layout`（所有頁面） | **視覺上為零**：`BR21.3` 要求宿主保持空、不對使用者顯示錯誤 | 宿主留空；403 永久失敗本工作階段不再發請求，其餘下次落地重試；兩者皆須 console 訊號（`SEC-U24-6` 兜底規則）。**注意**：缺 `K3 view` 者根本不會走到這一列——`can("K3","view")` 是發出前置條件（`security-design.md` §一之二），故其請求數為 0 而非「失敗 1 次」 |
| 三種寫入操作失敗 | 單一操作 | **一列**：就地更新不發生，清單維持原狀 | 錯誤文字經 live region 播報；403 另需關閉 modal 並重抓一次清單（權限可能剛被改） |
| `U19` 端點整體不可用 | 本單元全部功能 | **本單元**：成員管理不可用，但應用其餘部分（`Layout`、其他頁面）照常 | 無降級可言——本單元沒有任何本地資料來源可退回；這是「零持久層」的代價，如實記載 |

**本單元不構成任何其他單元的失敗域**：它不提供端點、不被任何單元 import
（`U17 a11y-gate` 依賴它的**產出畫面**而非程式介面）。

## 三、共用資源與跨單元面

| 資源 | 共用者 | 本站的處置 |
|---|---|---|
| `<LiveRegion />` | `U24`（建）→ `U23`（沿用） | `[ND1]`=A 的無狀態 props 形狀使沿用只需 import，不需接線；`HO-U24-1` 指派本單元 `code-generation` 做成可共用形狀 |
| `Layout.tsx` 本身 | `U24`（橫幅）與既有成本橫幅（`Layout.tsx:16` 的 `data-slot="cost-banner"`） | **橫幅直接渲染於 `Layout.tsx` 的 React 樹內，不走既有的 slot portal**——理由見 §三之一。兩者並存，互不讀寫對方狀態 |
| `apiUrl()`（`frontend/src/config/api.ts:25`） | 全前端 52 處 | 沿用，不改 |
| 六個 `/api/membership` 端點 | `U19`（擁有）、`U24`（消費） | 只消費、不擴充；需要擴充的兩項已登記為 `OPEN-MP24-6`／`-7` |

### 三之一、掛載機制：直接渲染於 `Layout.tsx`，**不**走既有 slot portal（審查 `R-07`／Minor）

本單元唯一要碰的**共用檔**是 `Layout.tsx`（全檔 **22** 行），而初版只寫「兩者並存於
`Layout`」、未指定機制。既有機制是 `frontend/src/cost/slotRegistry.tsx` 的
`mountCostSlot()`：`:9` 以 `document.querySelector('[data-slot="..."]')` 取元素、
再 `createRoot(el)` 掛一個**獨立的 React root**。本站**不採用它**，三個理由各自可查：

| 理由 | 證據 |
|---|---|
| **獨立 root 取不到 `useAuth()`** | `AuthProvider` 在 `App.tsx:33`，位於每一個 `<Layout>` 之上；`createRoot` 另開的樹**不在它之下**，故 `can("K3","view")`（§一之二 的發出前置條件）與 `can("K3","edit")`（§一之三）在那棵樹裡都取不到 |
| **`SlotName` 是封閉聯集** | `slotRegistry.tsx:4` 逐字 `type SlotName = 'cost-overspend' \| 'cost-banner'`；加第三個 slot 本來就要改那支檔，省不下來 |
| **portal 失敗是靜默的** | `slotRegistry.tsx:9-10`：元素不存在時 `return () => undefined`——什麼都不做、不報錯。而 `BR21.1` 要求宿主**無條件渲染**，一個靜默 no-op 的掛載機制無法保證它 |

**改動範圍**：`Layout.tsx` 新增橫幅宿主與操作列兩個節點（在 `:16` 的
`data-slot="cost-banner"` 之後、`{children}` 之前）。這是一支**所有頁面共用**的檔，
與 §二 把「橫幅查詢失敗」的失敗域列為「`Layout`（所有頁面）」一致——
失敗域之所以是全域，正是因為宿主掛在全域共用檔裡。

## 四、`role="status"` 區域的數量（`[ND1]`=A 的殘留，誠實記載）

**先更正 `[ND1]`=A 的宣稱優勢**（審查 `R-08`／Minor）：`[ND1]` 選項 A 的文字逐字寫
「`Layout` 內維持**只有一個** `role="status"`（橫幅宿主），**不產生兩個互相競爭的
播報區**」。在 **DOM 語意上那是假的**——頁面內容渲染於 `Layout` 的 `{children}`
（`Layout.tsx:17`）之內，故 per-page 的 `<LiveRegion />` 在 DOM 上**也位於 `Layout`
之內**。「只有一個」只在「**被編輯的檔案**」這個語意上成立（`Layout.tsx` 這支檔內
只有橫幅宿主一個）。**A 相對 B 在播報區數量上的優勢為零——兩者皆為二。**
A 真正的理由是另外兩條：不新增一組 context（`team.md` 的 lint 結構約束要求 Context
拆兩檔），以及 `U23` 沿用時的依賴面較小（只需 import 元件，不需 `Layout` 接線）。

以下是它**沒有**消除的部分：

> 當成員頁被掛載時，**文件中同時存在兩個** `role="status"` 區域——
> `Layout` 的橫幅宿主，以及該頁自己的 `<LiveRegion />`。

為什麼仍可接受，以及它的真實風險：

- 橫幅宿主在沒有待確認交棒事件時**是空的**（`functional-spec.md:202` 逐字），
  故兩個區域同時變動的時機是「剛好有待確認交棒事件 ＋ 同時觸發載入或錯誤播報」。
- 該組合**可達**（不是不可能），此時兩筆播報的先後由瀏覽器與螢幕閱讀器決定，
  本設計不保證順序，也**不**宣稱已處置。
- `[ND1]`=B 不會改善這件事，只會把第二個區域從頁面移到 `Layout.tsx`——**數量相同**。
- **為什麼不能共用同一個區域**（審查 `R-05`／Major 更正）：初版的理由寫「違反
  `functional-spec.md` §二之二（宿主內不得放可互動內容，而橫幅有兩個控件）」，
  **那個前提不適用**——§二之二 的處置逐字就是「宿主**只放要被朗讀的那段文字**；
  兩個動作鈕與可展開的專案清單放在宿主**之外**的兄弟節點」，控件早已被移出，
  宿主本就是純文字區域。真正的阻礙有三條，且都在別處：
  1. `functional-spec.md:202` 要求無待確認事件時宿主「**此時為空**」——
     把頁面播報文字導進去會讓它在沒有交棒事件時非空。
  2. `BR21.3` 要求橫幅抓取失敗時宿主**保持空、不顯示錯誤**——
     而頁面播報正是要顯示錯誤，兩者對同一節點的要求直接相反。
  3. §二之二 的可觀察形式要求宿主 `textContent` 在展開／收合時**不變**——
     共用之後任何播報都會改變它。

列為 `OPEN-ND24-1`：**兩個 `role="status"` 區域同時變動時的播報順序未定義**。
落點 `U17 a11y-gate`（`unit-of-work.md:428` 逐字「　**被依賴**：`U17` `a11y-gate`」；
`U17` 在 `:53` 登記為 `packaging` 類、`standalone（CI 步驟 ＋ devDependency）`，
是本 intent 唯一以無障礙為標的的單元，且 `construction/a11y-gate/` 在磁碟上**不存在**
——未跑過任何 stage，故在游標之後，是有效指派）。本站不自行發明一個順序規則——沒有上游需求支持，
而憑空訂一個不會被任何工具檢查的規則等於寫一條死規則。

## 五、本站查出的跨站引用更正：`unit-of-work.md:426` 是空行

本站自檢第 3 項（引用逐字核對，**事實與定位分開驗**）查出一處跨站殘留：

| 項目 | 內容 |
|---|---|
| 被誤引的行號 | `unit-of-work.md:426` |
| 該行的實際內容 | **空行**（`U24` 區塊的 `**驗證方式**：Playwright e2e` 與 `**依賴**` 之間的空白） |
| 正確行號 | `U24` 的依賴在 **`:427`**（逐字「**依賴**：`U19` `membership-service`、`U3` `rbac-story-ids`（`K3` 的可見性把關）」）；被依賴在 **`:428`** |
| 附帶風險 | `:417` 另有一條「　**被依賴**：`U17` `a11y-gate`」，但它屬於**上一個**單元（`U23`，其依賴為 `U20`／`U7`／`U8`／`U3`，見 `:415-416`）。行號指錯時可能落到鄰近單元的同形句子上 |
| 殘留位置 | 本單元 `nfr-requirements` 的 `tech-stack-decisions.md`（`TS-U24-6`）、`traceability.json`、`nfr-requirements-questions.md` 的 `[N4]` 題幹，以及該站**兩輪審查記錄** |
| 本站的處置 | 依 `refined-mockups:c3`：**不回改已核可的上游產出**（且該站已 `UNIT_COMPLETED`、READY 收據新鮮，寫入會觸發 review-freeze）。本節即為該落差的紀錄，純比對兩份文件者請以本節為準 |

**為什麼值得單獨記一節**：兩輪審查都逐字「複驗」過 `:426` 並判定 accurate——
它驗的是**事實**（`U24` 的依賴只有 `U19`／`U3`，這是對的），沒有驗**定位**。
這是 `project.md` 的 `feasibility:cb353d32` 記過的形狀第三次在本 intent 出現，
而且這次是**我與審查員同時漏掉**。可執行補強：核對引用時，除了確認那句話還在，
還要把該行號的內容印出來看——空行與註解行都會通過「那句話還在不在」的檢查。
