# Tech Stack Decisions — `U15 memory-page-ui`

> 本單元的技術選擇全部是**沿用既有**，沒有一項新引入。本檔的價值在於把
> 「沿用哪一個、為什麼、以及該既有機制的副作用是否相容」逐項寫下
> ——`project.md` 的 `application-design:c15` 逐字要求後者。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `codekb/chiton/technology-stack.md` | 前端技術棧現況 |
| `construction/memory-page-ui/functional-design/frontend-components.md` | §一 的五項磁碟實測、§二 的模組清單、§五 的抓取形狀 |
| `inception/requirements-analysis/requirements.md` | `NFR8`（部署設定完整性）、`NFR10`（模型可替換性，本單元不適用） |
| `team.md` | Testing Posture 的 D 項不採用、Code Style 的前端 lint 結構約束與命名慣例 |

## 一、技術選擇（`TS-U15-n`）

| ID | 選擇 | 為什麼 | 該既有機制的副作用是否與本單元相容 |
|---|---|---|---|
| `TS-U15-1` | **零新前端依賴** | `team.md` Q4 定案 D 項不採用。三區清單、就地確認列、上一頁／下一頁兩鍵都用既有 React ＋ Tailwind 做得到 | **相容** |
| `TS-U15-2` | **驗證層只有 Playwright e2e** | `frontend/package.json` 的 `devDependencies` 只有 `@playwright/test` | **相容但如實記載限制**：`memoryPaging.ts` 的三個純函式（`frontend-components.md §五之二`）只能經 DOM 結果間接驗證；抽成純函式的價值是日後導入 unit／property-based 測試時零重構 |
| `TS-U15-3` | **URL 組裝用既有 `apiUrl()`**（`frontend/src/config/api.ts:25`） | `team.md` Code Style：既有 `fetch()` 一致沿用 | **相容** |
| `TS-U15-4` | **兩層抓取形狀**，落點 `frontend/src/memory/memoryApi.ts`，與 `frontend/src/membership/membershipApi.ts` 平行 | `react-hooks/set-state-in-effect` 為 error 級 | **相容**。`cancelled` flag 同時解決翻頁時舊請求晚到覆蓋新頁的競態 |
| `TS-U15-5` | **型別取自產生的 `frontend/src/types/api.d.ts`**（`components['schemas']['MemoryView']`） | 手寫 interface 與後端無編譯期連結（`team.md` Deployment 的 `tsc -b` 落差記載） | **相容**。`memory_id` 型別為 `string`，直接放進路徑 |
| `TS-U15-6` | **就地移除用 `filter` 回傳新陣列** | `react-hooks/immutability` 為 error 級；先例 `AdminPage.tsx` 的 `filter` 移除 | **部分相容——這是副作用檢查真的抓到東西的一處**：`AdminPage.tsx:198-203` 的先例在 `filter`（`:200`）之後另有分頁補償（`:201` 的 `setTotal` 遞減與 `:203` 的 `resyncCurrentPageInBackground(page)`），其註解 `:198-199` 逐字「不重抓的話，下一頁會靜默略過一個帳號」，而本單元的情節記憶**同樣是 offset 分頁**。若只照抄 `filter` 而略去補償，就是審查 `R-01` 查出的漏列缺陷。故沿用此先例時**必須連同補償一起考慮**，處置已列入 `security-requirements.md §四之一` 交接表 |
| `TS-U15-7` | **live region 沿用 `frontend/src/components/LiveRegion.tsx`**，每頁一個實例 | 元件契約明寫「每頁各掛一個實例，不走 context」 | **相容**。兩個 `role="status"` 並存的殘留沿用 `OPEN-ND24-1`，不另開項 |
| `TS-U15-8` | **不沿用 `PaginationControl`** | 其 `total` prop 無資料可餵（`BR33.2`） | 不適用——此為**不沿用**的決定，寫下是為了讓「已核可線框說沿用它」與本站的偏離可被追溯 |
| `TS-U15-9` | **零新環境變數** | 每頁 20 則是程式常數 | **相容**，使 `NFR8.90` 結構性滿足 |

## 二、不適用的選擇

| 項 | 理由 |
|---|---|
| 模型選擇（`NFR10`） | 本單元零 LLM 呼叫 |
| 資料庫、快取、佇列 | 本單元無持久層，全部在 `U8` |
| 新 Context | 記憶頁的 state 為頁面區域性，無跨路由消費者（`frontend-components.md §二`） |

## 三、孤兒宣告

`TS-U15-1`～`TS-U15-8` 無 inception NFR 父條（技術選擇本身不是 inception 要求），
在 `traceability.json` 的 `reverse` 段逐條宣告。`TS-U15-9` 為 `NFR8.90` 的承載，
不另宣告。
