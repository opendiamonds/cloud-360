# Infrastructure Specification — `U24 member-pages-ui`

> 本站是**設計**站：描述需要什麼基礎設施與為什麼，不寫 IaC。
> 本單元的結論是**零新基礎設施**，而下面每一條都附可複驗的指令或行號——
> 「什麼都不用改」若沒有證據支撐，與「沒查」在文件上長得一樣。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/nfr-design/logical-components.md` | 六個邏輯元件、四個失敗域、共用資源表、`Layout.tsx` 的掛載機制（§三之一） |
| `construction/member-pages-ui/nfr-design/security-design.md` | 零新通道／零新儲存／零新環境變數；`can("K3","edit")` 的前置判定 |
| `construction/member-pages-ui/nfr-design/performance-design.md` | `UIP-1`–`UIP-5` 的達成手段 |
| `construction/member-pages-ui/functional-design/functional-spec.md` | 六個 API 消費點（皆 `U19` 既有） |
| `inception/domain-design/components.md` | 元件目錄（架構脈絡） |
| `inception/contract-design/contract-summary.md` | `K-16` 的四個 http 方法與 `residual_gap` |

## 一、部署架構：**零變更**（逐項附證據）

| 面向 | 本單元的需求 | 既有現況是否已滿足 | 證據 |
|---|---|---|---|
| 運算 | 無新進程 | ✅ | 前端為靜態資產，由既有 nginx 容器提供；`deploy/docker-compose.deploy.yml` 的服務集合不變 |
| 網路（反向代理） | 六個 `/api/membership/*` 端點需可達 | ✅ **已涵蓋** | `frontend/nginx.conf:16` 逐字 `location /api/ {`、`:17` `proxy_pass http://backend:8000;`——`/api/` 前綴規則涵蓋全部 membership 端點，不需新 `location` |
| 儲存 | 無新持久層 | ✅ | 本單元零 DB 寫入；`reselection_events`／`project_members` 由 `U19` 擁有 |
| 瀏覽器儲存 | **明文禁止** | ✅ | `NFR4.80`：`localStorage`／`sessionStorage`／`IndexedDB` 三識別字零命中為可測不變量 |
| 環境變數 | **零新增** | ✅ | `TS-U24-7`／`NFR8.80`。故 `deploy/render-env.sh` ＋ `deploy/.env.example` 的同步義務為**空集合** |
| CI 測試 stack | 無新變數、無新服務 | ✅ | `deploy/docker-compose.test.yml` 的 `backend.environment` 全部自帶預設（`${VAR:-default}` 形狀）；本單元不新增任何它需要供應的值 |
| 環境數量 | 三個（本機 dev／CI 測試／部署） | ✅ 不變 | `project.md` 的 env contract 三範圍不受本單元影響；`python3 scripts/validate_env_contract.py` 的檢查面無新標的 |

## 二、唯一要碰的共用檔：`Layout.tsx`

| 項目 | 內容 |
|---|---|
| 檔案 | `frontend/src/components/Layout.tsx`（全檔 **22** 行） |
| 改動 | 在 `:16` 的 `<div data-slot="cost-banner" />` 之後、`:17` 的 `{children}` 之前，新增交棒橫幅的宿主與操作列兩個節點 |
| 機制 | **直接渲染於 React 樹內**，不走 `frontend/src/cost/slotRegistry.tsx` 的 portal。三個理由見 `logical-components.md` §三之一，其中最硬的一條是：portal 在目標元素不存在時 `return () => undefined`（`slotRegistry.tsx:9-10`）——**靜默 no-op**，而 `BR21.1` 要求宿主**無條件渲染** |
| 爆炸半徑 | `Layout` 被 `App.tsx` 的**每一個**路由包覆（`:52`／`:65`／`:78`／`:91`／`:103`／`:116` 等），故此檔的錯誤影響所有頁面。這與 `logical-components.md` §二 把「橫幅查詢失敗」的失敗域列為「`Layout`（所有頁面）」一致 |
| 回滾 | 單檔改動，`git revert` 即可；無 schema、無設定、無資料遷移 |

## 三、`project.md` 兩條 blocking 規則的逐項判定

| 規則 | 觸發條件 | 本單元判定 |
|---|---|---|
| **schema ↔ deploy 同步**（`schema_rbac.sql` ＋ `DEPLOY.md`） | 新增／刪除／更名表或欄位、索引／約束變更、seed 語意變更、ORM／啟動補丁引入新 DDL | **不觸發**：本單元零 DDL、零 seed 變更。`role_permissions` 的 `K3` 種子**未改動**——本單元只**讀取** `can("K3","edit")` 的既有結果 |
| **`LOCAL-DEV.md` 同步** | 異動 `backend/database.py` 的 schema 補丁、`deploy/nginx.conf`、任一 `.env.example` 或 `render-env.sh` | **不觸發**：四個路徑本單元皆不碰。**附帶一項本站查出的規則缺陷**，見 §四 |

## 四、本站查出：`deploy/nginx.conf` 從未存在（規則層缺陷，非本單元問題）

`project.md` 與 `CLAUDE.md` 的 `LOCAL-DEV.md` 同步規則都以 `deploy/nginx.conf`
為觸發條件之一，而該路徑**在版控史上從未存在**：

| 查證 | 結果 |
|---|---|
| `git log --all -- deploy/nginx.conf` | **零筆** |
| 真實檔案 | `frontend/nginx.conf`（由 commit `755c67a` 加入） |
| `local-dev-drift` workflow 的觸發 `paths:` | 第 9 行為 `deploy/nginx.conf`；說明表 `:58` 亦同 |
| `LOCAL-DEV.md:569` | **它自己寫對了**：「`frontend/nginx.conf` 的 `proxy_buffering off` 與 600 秒 timeout **是功能前提，不是效能調校**。少了它們，A1／A3 的 SSE 串流會被緩衝住……或提前斷線」 |

**後果**：那道提醒**永遠不會觸發**。任何人改 `frontend/nginx.conf`——而
`LOCAL-DEV.md` 自己說那兩個設定是串流的功能前提——都不會收到同步提醒。
這是「偵測 X 狀態的規則要先驗 X 可達」那一類：規則完整，而它盯的路徑不存在。

`project.md` 本身的 tie-break（「本條是正式來源；workflow 的觸發 paths 只是它的
實作，兩者若不一致以本條為準，該修的是 workflow」）在此**解不開**——兩邊錯得一樣，
正式來源自己指向不存在的路徑。

**本站不自行修**：三處都在本單元範圍之外（`project.md` 的規則層照約定在關卡上修、
`CLAUDE.md` 是 contract 檔、workflow 在 `.github/` 下，而 `project.md` 另有一條
禁止以 repo 內實作程式承載無人值守自動化的規則需一併考量）。列為 `OPEN-ID24-1`，
**無自然承接站**（它不屬任何單元，是專案規則層的缺陷），於核可關卡提交使用者。
