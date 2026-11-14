# Tech Stack Decisions — `U24 member-pages-ui`

> 本單元的技術選擇全部是**沿用既有**，沒有一項新引入。本檔的價值在於把
> 「沿用哪一個、為什麼、以及該既有機制的副作用是否相容」逐項寫下
> ——`project.md` 的 `application-design:c15` 逐字要求後者。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `codekb/chiton/technology-stack.md` | 前端技術棧現況 |
| `construction/member-pages-ui/functional-design/frontend-components.md` | §一 的三項磁碟實測、§五 的抓取形狀 |
| `inception/requirements-analysis/requirements.md` | `NFR8`（部署設定完整性）、`NFR10`（模型可替換性，本單元不適用） |
| `team.md` | Testing Posture 的 D 項不採用、Code Style 的前端 lint 結構約束 |

## 一、技術選擇（`TS-U24-n`）

| ID | 選擇 | 為什麼 | 該既有機制的副作用是否與本單元相容 |
|---|---|---|---|
| `TS-U24-1` | **零新前端依賴** | `team.md` 的 Q4 定案 D 項不採用（引入 Vitest 等屬獨立工具鏈決策，不由 feature 夾帶）。本單元的需求（表格、對話框、下拉、橫幅）用既有 React ＋ Tailwind 都做得到 | **相容**。唯一被排除的選項是 `[N1]`=C 的虛擬滾動（需新依賴或自寫），而 `[N1]`=A 的 100 列上限使它不必要 |
| `TS-U24-2` | **驗證層只有 Playwright e2e** | `team.md` 既成事實：`frontend/package.json` 的 `devDependencies` 只有 `@playwright/test`，無 vitest／jest／`@testing-library/*` | **相容但要如實記載其限制**：本單元 19 條 `BR2x.y` 全部設計成外部可觀察，正是為了讓唯一可用的驗證層碰得到它們。代價是純函式層級的斷言（例如 `BR22.3` 的推導邏輯）只能透過 DOM 結果間接驗證 |
| `TS-U24-3` | **URL 組裝用既有 `apiUrl()`**（`frontend/src/config/api.ts:25`） | 既有 52 處 `fetch()`、10 支檔一致沿用（`team.md` Code Style） | **相容**。不自造 URL 組裝 |
| `TS-U24-4` | **兩層抓取形狀**（純抓取函式 ＋ 呼叫端更新 state ＋ `useEffect` 的 `cancelled` flag） | `react-hooks/set-state-in-effect` 是 **error** 級，違反即 CI 紅燈（`team.md` Code Style 的結構約束） | **相容**。這是本 repo 前端新增資料來源的唯一合規形狀 |
| `TS-U24-5` | **就地更新用既有 `map`／`filter` 形狀** | 既有三個先例：`AdminPage.tsx:153`／`:179`／`:200`（後者是 `filter` 移除） | **相容，但先例的另兩行不適用**：`:201` 的 `setTotal` 遞減與 `:203` 的背景重抓是**分頁**的補償（註解在 **`:198-199`**，被引用的那一句在 `:199`；`:197` 是 `if (!res.ok) throw new Error(...)`。**審查 `R-05` 更正**：原寫 `:197-198`，事實對、定位偏一行），而 `list_members` 無分頁參數，故無 offset 位移可補。**這一項是 `application-design:c15` 要求的副作用檢查真的抓到東西的一處** |
| `TS-U24-6` | **live region 元件由本單元（`U24`）自建，`U23` 之後沿用** | `[N4]`=A。**這是對齊已核可 Bolt 計畫的更正，不是本站新定案**：`[F3]`=A 原選「`U23` 建、`U24` 沿用」，其理由是「`U23` 較早落地」——該排序事實是**反的**。已核可的交錯順序（`bolt-plan.md:494`）逐字為 `B1 → B10 → B2 → B11 → B3 → B12 → B13 → B4 → B5 → B6 → B7 → B8 → B9`，而 `U24` 在 **B12**（`:480`）、`U23` 在 **B13**（`:479`），故 `U24` **先**施工；`unit-of-work.md:426` 的 `U24` 依賴清單也只有 `U19` 與 `U3`，無任何一條指向 `U23`。審查 `R-01`（Critical）查出，本站複驗後以 `[N4]` 交使用者裁決 | **相容，且解掉一條不可滿足的完成條件**。原寫法把「`U23` 已提供該元件」寫成 `U24` 的完成條件，而它在 B12 被施工的那一刻不可能為真；改由 `U24` 自建後，本單元在 B12 自給自足，與已核可的依賴圖一致，**不需要改動任何已核可的 Bolt 順序**。代價：`U23` 屆時的技術選擇變成「沿用 `U24` 的」，已於 §四 登記為交接事項。仍**不得**沿用 `AdminPage.tsx:104` 的 4 秒 toast（實測無 `role`／`aria-live`，且 `frontend-components.md:176` 明文禁止） |
| `TS-U24-7` | **零新環境變數** | 本單元無設定項：上限 100 是程式常數、不快取是行為、console 層級沿用既有 | **相容**，且使 `NFR8.80` 成為結構性滿足（同步義務為空集合） |

### 一之一、哪些 `TS-U24-*` 進了 `traceability.json` 的孤兒段，哪些沒有（**不是漏寫**）

`TS-U24-1`～`TS-U24-6` **六項**在 `traceability.json` 的 `reverse` 段逐條宣告為孤兒——
11 條 inception NFR 無一涵蓋前端依賴、驗證層、URL 組裝、抓取形狀或 live region 來源。

**`TS-U24-7` 刻意不在那段裡**：它不是孤兒。零新環境變數正是 `NFR8.80` 的依據，
而 `NFR8.80` 以 `OK` 出現在 `coverage` 段（父條 `NFR8`）。把它同時列進 `reverse`
會讓同一項決定在兩段各出現一次、且兩段的語意相反（有父條／無父條）。

## 二、刻意不選的（與其理由）

| 不選 | 理由 |
|---|---|
| 虛擬滾動（`react-window` 等） | 需新依賴，與 `TS-U24-1` 衝突；`[N1]`=A 的 100 列上限使它不必要 |
| 前端快取層（含 TanStack Query） | `[N2]`=A 選不快取；引入快取庫同時違反 `TS-U24-1`，且會帶來 `[N2]`=B 的分頁不一致問題 |
| 前端 unit／component 測試框架 | `team.md` 的 D 項不採用；屬獨立工具鏈決策 |
| 任何瀏覽器儲存 | `SEC-U24-2`／`NFR4.80` 明文禁止——`AC12.4.4` 的跨裝置語意只有伺服器端能滿足 |
| 改 `U19` 的端點加分頁 | `[N1]`=D 的代價：`U19` 的 code-generation 已完成且在游標之前（同 `OPEN-MP24-1` 的形狀） |

## 三、`NFR10` 為何不適用

`NFR10`（路由層模型的可替換性）逐字是「編排層（意圖識別）與功能 agent 得使用
不同模型」。**本單元不呼叫任何模型**，六個 API 消費點全部是 `U19` 的成員管理端點。
故該條對本單元不適用——不是豁免，是範圍外。

## 四、交接事項（`[N4]`=A 的下游後果）

| 項目 | 內容 | 落點 |
|---|---|---|
| `HO-U24-1` | **`U24` 自建的 live region 元件須做成可共用的形狀**（不是只給成員頁用的內嵌片段），因為 `U23` 之後要沿用它。這是 `[N4]`=A 相對於 `[N4]`=C（兩站各建一份）的差別所在——C 被排除的理由是 `team.md` 的「單一真實來源」 | 本單元 `code-generation`（`ALWAYS`、construction、在本單元游標之後，已查 `stage-graph.json`） |
| `HO-U24-2` | **`U23` 的技術選擇方向反轉**：由「建」改為「沿用 `U24` 的」。`U23` 的 `nfr-requirements`／`code-generation` 皆**未執行且在游標之後**，故這是一個有效的下游指派，不是死指派 | `U23` 的 `nfr-requirements`（`CONDITIONAL`；若被判不適用，轉移至 `U23` 的 `code-generation`，`ALWAYS`） |
| `HO-U24-3` | 上游 `functional-spec.md:42` 與 `frontend-components.md:**53**-55` 的字面仍寫「沿用 `U23` 的」（審查 `R-09` 更正：原寫 `:54-55`，而該句起於 `:53` 逐字「**`<LiveRegion />` 不在本單元的新建清單裡**——`[F3]`=A 定它由 `U23` 建、`U24` 沿用」；`:54-55` 只含其後的跨單元依賴句。**來源是審查自己上一輪 Location 欄的措辭，我原樣沿用**——與 `refined-mockups:b6cf84a4` 同形）。依 `refined-mockups:c3` **不回改已核可的上游**；本表即為該落差的紀錄，純比對兩份文件者請以本表為準 | 無須承接（紀錄性質） |
