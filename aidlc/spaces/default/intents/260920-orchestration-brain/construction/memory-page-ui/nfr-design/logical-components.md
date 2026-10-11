# Logical Components — `U15 memory-page-ui`

> 本單元的邏輯元件、失效範圍與共用資源。基礎設施面**沒有新增任何元件**：
> 零新進程、零新容器、零新環境變數；所有元件都是既有前端 bundle 內的模組。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `functional-design/frontend-components.md` | §二 元件樹與四個非元件模組 |
| `nfr-requirements/tech-stack-decisions.md` | `TS-U15-1`～`TS-U15-9` |
| `nfr-design/performance-design.md`、`security-design.md` | 各設計落在哪個元件 |

## 一、元件清單與失效範圍

| 元件 | 種類 | 失效時的影響範圍（blast radius） | 隔離手段 |
|---|---|---|---|
| `memoryApi.ts` | 純抓取模組 | 三區同時無資料 | 每區各自呼叫、各自 `catch`，故實際只影響發出失敗請求的那一區 |
| `memoryPaging.ts` | 純函式模組 | 情節記憶的頁次與計數錯誤 | 不碰 state、不碰 `fetch`，可單獨推理 |
| `memoryEntry.ts`（`canSeeMemoryEntry`） | 純判定 | Sidebar 項不出現 | 唯一判定，INV-3 的承載者 |
| `memoryLabels.ts` | 映射表 | 區標題或 test id 錯誤 | 集中一處，API 值與 test id 不互相代用 |
| `MemoryPage` | 頁面 | 整頁 | `ProtectedRoute` 以外不加任何守衛 |
| `MemoryZone` × 3 | 區塊 | **僅該區**（`BR32.2`） | 各自 state、各自 effect、各自 `cancelled` flag |
| `MemoryItem` × N | 條目 | **僅該則**（`BR34.3`） | `deleting` 為條目自身 state |
| `EpisodicPager` | 控件 | 僅情節記憶區的翻頁 | 無 state、純 props |
| `LiveRegion`（既有） | 共用元件 | 播報失效，視覺不受影響 | 既有契約，不修改 |

## 二、共用資源

| 資源 | 共用者 | 本單元的使用方式 |
|---|---|---|
| `apiUrl()`（`frontend/src/config/api.ts`） | 全前端 | 只讀呼叫，不修改 |
| `useAuth()`（`frontend/src/context/auth-context.ts`） | 全前端 | 只讀 `user.id`，不修改 Context |
| 產生的型別 `frontend/src/types/api.d.ts` | 全前端 | 只讀 `MemoryView`，由 CI 的型別漂移檢查維護 |
| `Sidebar.tsx` | 全站導覽 | **新增一項**，放在 `/brain` DEMO SCOPE 區塊之外 |
| `App.tsx` 路由表 | 全站 | **新增一條** `/memory` 路由 |
| 記憶 API（`U8`） | 本頁、大腦脈絡組裝 | 只消費 `GET` 與 `DELETE` |

## 三、與基礎設施的關係

本單元對 infrastructure-design 的輸入為**空集合**：沒有新服務、沒有新的對外端點、
沒有新的設定值、沒有新的儲存。唯一的跨單元改動是 `security-design.md §四` 的後端
授權缺口修補，它落在既有的 `memory_router.py`，同樣不新增任何基礎設施元件。
