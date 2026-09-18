# 業務總覽（Business Overview）

> Reverse Engineering 合成產物｜repo `cloud`｜commit `8c90f40`｜intent `260806-a1-a3-ux`（bugfix）

## 產品定位與價值主張

Cloud-360 是 AI-native 的多雲（AWS / GCP / Azure）架構設計與運維平台。核心價值是把「用自然語言描述架構需求 → 產生可編輯的 draw.io 架構圖 → 以 Well-Architected（WA）lens 審核與改善」串成一條連續工作流，並以 RBAC 控制誰可檢視、編輯、審核。

目前可運行能力集中在自有 staging（`cloud360.danniel.cc`，見 ADR-0007）；雲端供應商正式 production 環境仍在範圍外（ADR-0001 / ADR-0002）。方法論以 Spec-Driven Development 與 AI-DLC v2 為基礎。

## 主要使用者旅程

| 故事／領域 | 主角 | 目標 | 入口 |
|---|---|---|---|
| A1 架構圖生成 | 架構師／工程師 | 以聊天提示產生／迭代架構圖，於 embed.diagrams.net 畫布編輯並持久化 | `/workspace` → `WorkspacePage` |
| A3 評估與審核 | 審核者／架構師 | 對已存架構圖執行 WA review、檢視 findings／scores、管理 lens | `/assessment` → `AssessmentPage` |
| J 管理（權限） | 管理員 | 使用者、角色授權請求、角色–故事權限矩陣 | Admin 頁、`RolePermissionsPage` |
| 協作 | 協作者 | 架構圖 CRUD、聊天歷史、分享、WebSocket 同步 | `/api/collab` + WS |

權限以故事級旗標（如 A1／A3 的 `view`／`edit`／`review`，J3a／J3b）驅動側欄與路由守衛；`Sidebar` 依 `can`／`canArch` 決定可見項。

## 範圍與邊界

**In scope（目前 codekb 所見）**

- 後端 FastAPI：認證／RBAC、架構產生（agent）、協作圖庫、WA review／lens
- 前端 React SPA：Workspace（A1）、Assessment（A3）、管理面
- PostgreSQL schema（`schema.sql`、`schema_rbac.sql`）與 staging Docker 部署
- CI contract／lint／build／unittest／Docker；合併至 `ut` 後部署 staging

**Out of scope（除非新 ADR）**

- 雲端供應商 production credentials、destructive cloud IaC apply
- Native iOS／Android app

## 與本 intent 的業務關聯

Intent `260806-a1-a3-ux` 聚焦 A1／A3 UX 缺陷，而非新業務能力。業務上使用者已能完成 generate→canvas 與 review，但下列摩擦直接傷害 A1／A3 的信任感與產出品質，屬 bugfix 優先修正項：

1. App 側欄固定寬度、不可收合 → 畫布有效工作區偏小  
2. 產生圖的邊線／圖示重疊 → 圖面可讀性下降  
3. draw.io 儲存／離開事件未處理 → 工作流不完整  
4. Undo 失效 → 編輯代價升高  
5. 無 prompt refusal（擋 DB／API key／credential／系統值變更）→ 安全與平台完整性風險  
6. 側欄扁平 IA（缺 A／J story-group 巢狀）→ 導覽認知負擔
