# Unit of Work — Story D IaC

> Stage: units-generation · Intent: `261105-d-iac-generation`  
> Q1–Q5=A；Plan／Looks correct 已核可。  
> **本檔不定施工順序**；拓樸見 `unit-of-work-dependency.md`。

## 拆分原則

| 原則 | 說明 |
|---|---|
| 依部署面 | `iac-api`（既有 FastAPI）＋`iac-ui`（既有 Vite）；非微服務 |
| Embedded | 進現有 backend／frontend 映像與 compose（Q4=A） |
| 三核心不拆 unit | Generator／Scanner／Redactor 為 `iac-api` 內模組（Q2=A） |
| OpenAPI | 義務掛 `iac-api`（Q3=A） |
| 可平行 | 兩 unit 拓樸無依賴（Q5=A）；整合點 `/api/iac` |
| 禁止 | 代 apply；寫入雲端 SM；挖 collab 私函；`d1_*` 檔名前綴；塞進 `agent_router`／`user_router` |

## Unit 一覽

| Unit ID | Directory | kind | 複雜度 | 部署 |
|---|---|---|---|---|
| U1 | `u1-iac-api` | service | L | embedded — 既有 backend 容器 |
| U2 | `u2-iac-ui` | ui | M | embedded — 既有 frontend bundle |

Construction 路徑前綴：`construction/<directory>/`（units-generation 命名；實際落碼仍在 `backend/iac/`、`frontend/src/...`）。

## Unit 定義

### U1 — u1-iac-api（service）

- **邊界**：`IacWorkspaceSession`＋`IacModuleGenerator`／`IacStaticScanner`／`IacSecretRedactor`；`/api/iac/*`；OpenAPI 漂移義務；RBAC `require_story_action("D1"|"D2"|"D3")`；行程內產物鍵與 D2→D3 閘。
- **職責**：同步 HTTP 執行生成／掃描／改寫／下載；PBT 三核心；第一個 D HTTP 的 2xx／403 TestClient；agent 經 `langgraph_runtime`（可 stub）。
- **不職責**：React UI；Diagram 擁有權；CI IaC scan job；Postgres 新產物表（本輪 ADR-002）。
- **部署**：embedded shared backend process。
- **複雜度**：L。
- **驗證失敗模式**：閘被繞過（無 D2 可 D3）；舊 report_id 仍可用；無權非 403；PBT／突變紅燈；OpenAPI drift。

### U2 — u2-iac-ui（ui）

- **邊界**：`IacWorkspaceUi`（步驟殼、選圖、findings、Secrets、下載 modal、空／錯／進行中態）；Workspace「生成 IaC」入口。
- **職責**：對齊 refined-mockups test-id；消費 `/api/iac`；無權入口 disabled＋說明；不提供 apply。
- **不職責**：決定性核心／RBAC 種子邏輯；自建圖庫。
- **部署**：embedded 既有 SPA。
- **複雜度**：M。
- **驗證失敗模式**：Playwright 找不到步驟／下載確認；自由檢視被做成硬精靈；切圖無清空提示。

## 跨 unit 整合點

| 從 | 到 | 契約 |
|---|---|---|
| U2 | U1 | 同步 JSON `/api/iac/*`（OpenAPI 由 U1 維護） |
| U1 | 既有圖 API | list／get／upload；僅 `diagram_id` |
| U1 | RBAC | story action view／edit |
