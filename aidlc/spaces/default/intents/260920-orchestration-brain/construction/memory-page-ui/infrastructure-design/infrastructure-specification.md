# Infrastructure Specification — `U15 memory-page-ui`

> 本站是設計站，不寫 IaC。本單元的結論是**零新基礎設施**，每一條附可複驗的
> 指令或行號——「什麼都不用改」若沒有證據支撐，與「沒查」在文件上長得一樣。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/memory-page-ui/nfr-design/logical-components.md` | 元件清單、共用資源表、§三「對基礎設施的輸入為空集合」 |
| `construction/memory-page-ui/nfr-design/security-design.md` | 零新通道／儲存／設定；§四 後端授權缺口 |
| `construction/memory-page-ui/nfr-design/performance-design.md` | `UIP-1`～`UIP-6` 的達成手段（全在前端） |
| `construction/memory-page-ui/functional-design/functional-spec.md` | 兩個 API 消費點（皆 `U8` 既有） |
| `inception/domain-design/components.md` | `MemoryStore` 的擁有邊界 |
| `inception/contract-design/contract-summary.md` | `K-08`、`K-14` |

## 一、部署架構：零變更

| 面向 | 本單元的需求 | 現況是否已滿足 | 證據 |
|---|---|---|---|
| 運算 | 無新進程 | ✅ | 前端為靜態資產，由既有 nginx 容器提供 |
| 網路 | `/api/memory/records` 需可達 | ✅ 已涵蓋 | `frontend/nginx.conf:16` `location /api/ {`、`:17` `proxy_pass http://backend:8000;` |
| 儲存 | 無新持久層 | ✅ | 記憶表由 `U5`／`U8` 擁有；本單元只經 HTTP 讀刪 |
| 瀏覽器儲存 | **明文禁止** | ✅ | `NFR4.90`、`NFR7.90` |
| 環境變數 | **零新增** | ✅ | `NFR8.90`；`deploy/render-env.sh` ＋ `deploy/.env.example` 的同步義務為空集合 |
| CI 測試 stack | 可種記憶資料 | ✅ | `deploy/docker-compose.test.yml:102` `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-stub}`——e2e 可經 `POST /api/memory/records` 種資料，不需 Ollama |

## 二、要碰的共用檔

| 檔案 | 改動 | 爆炸半徑 | 回滾 |
|---|---|---|---|
| `frontend/src/App.tsx` | 新增 `/memory` 路由（`ProtectedRoute` 包覆） | 僅新路由 | `git revert` |
| `frontend/src/components/Sidebar.tsx` | 新增「我的記憶」一項，置於 `:209-216` DEMO SCOPE 區塊**之外** | 全站導覽；錯誤影響所有頁面的側欄 | `git revert` |
| `backend/services/memory_router.py` 或 `memory_facade.py` | 「已核准」檢查（使用者裁決併入；落點由 code-generation 計畫依 nfr-design 審查 `R-05` 定案） | 記憶 API 的全部消費者，含大腦脈絡組裝 | `git revert`；無 schema、無資料遷移 |

## 三、`project.md` blocking 規則的逐項判定

| 規則 | 本單元判定 |
|---|---|
| schema ↔ deploy 同步（`schema_rbac.sql` ＋ `DEPLOY.md`） | **不觸發**：零 DDL、零 seed 變更。「已核准」檢查讀取既有的 `users.authorization_status`，不改結構 |
| `LOCAL-DEV.md` 同步 | **不觸發**：不碰 `backend/database.py` schema 補丁、nginx 設定、`.env.example`、`render-env.sh` |
| env contract（`validate_env_contract.py`） | **無新標的** |
