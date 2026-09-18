# Unit of Work

> Cloud-360 inception — logical units of work for Construction.  
> Brownfield monolith：以 Module 切分；部署上仍為單一 backend + frontend。  
> Scope: **A1 / A2 / A3 / A4 / A5 / J**（A3 於 2026-07-23 Units Generation 新增）。


### 1. 拆分原則

| 原則 | 說明 |
|---|---|
| 部署模型 | **Monolith**：一個 FastAPI 服務 + 一個 React SPA；Unit = 邏輯 Module |
| 邊界依據 | API 模組：`/api/architecture`、`/api/collab`、`/api/auth`；A3 評核掛 `/api/architecture/reviews` |
| Story 對齊 | 已開發／進行中 story 各對一開發 unit；J1–J5 → `U-J` |
| 產品權限語意 | Admin 矩陣 **A1＝A2＝A4** 合併「架構圖生成」；**A3** 為獨立欄；開發 unit 仍分開 |
| 未涵蓋 | B–H 尚未建 unit |

### 2. Unit 一覽

| Unit ID | 名稱 | 類型 | Stories | Construction 目錄 |
|---|---|---|---|---|
| `U-J` | Identity & RBAC | Module | J1–J5 | `construction/j/` |
| `U-A1` | Architecture Design Generation | Module | A1 | `construction/a1/` |
| `U-A2` | Canvas Collaborative Editing | Module | A2 | `construction/a2/` |
| `U-A3` | Well-Architected Review | Module | A3 | `construction/a3/`（待 FD／Code） |
| `U-A4` | Chat & Last-Opened Persistence | Module | A4 | `construction/a4/` |
| `U-A5` | Diagram Sharing & Real-time Collab | Module | A5 | `construction/a5/` |

### 3. Unit 定義

#### U-J — Identity & RBAC

- **職責**：登入／JWT、RBAC、Admin、J5 授權閘門。
- **擁有**：`users`、`role_permissions`、`role_authorization_requests`；`/api/auth`。
- **狀態**：J1–J5 Core done；WS JWT 待補。

#### U-A1 — Architecture Design Generation

- **職責**：NL → Agent SDK／OpenRouter → draw.io XML；SSE。
- **擁有**：`POST /api/architecture/generate`；`design_agent`、`diagram_builder`。
- **狀態**：Code done；與 U-A3 **同 Agent SDK 家族**（peer，不合併模組）。

#### U-A2 — Canvas Collaborative Editing

- **職責**：畫布編輯、diagram CRUD、多圖、局部 AI。
- **擁有**：`/api/collab/diagrams`；`UserDiagram`。
- **狀態**：核心完成；部分 AC 缺口。

#### U-A3 — Well-Architected Review

- **故事**：A3  
- **職責**：對選定架構圖執行 WA 評核（規則引擎＋獨立 ReviewAgent／同 Agent SDK）；SSE；結果持久化；Assessment 儀表板＋Workspace／產圖 CTA；PDF；**增量**：`Security_Reviewer` 動態維護五大柱 Offline Lens（DB active JSON）。  
- **擁有實體**：`architecture_reviews`；**增量** `wa_lenses`（FD 細化）；API `/api/architecture/reviews*` ＋ lens 編輯 API。  
- **主要程式（目標）**：`review_router`／`wa_lens_engine`／`review_agent`；FE `AssessmentPage`（含 Lens 標準分頁）。  
- **相依**：U-J（A3 RBAC／角色）、U-A2（XML／選圖）、U-A1（產圖 CTA；peer Agent SDK）。  
- **狀態**：MVP Code done（含 PDF／Findings←Lens）；**Lens Editor Inception ✅**；Construction FD／Code 待核准。

#### U-A4 — Chat & Last-Opened Persistence

- **職責**：user×diagram 聊天、last-opened、bootstrap。
- **狀態**：Code done。

#### U-A5 — Diagram Sharing & Real-time Collab

- **職責**：分享、WS XML、協作狀態。
- **狀態**：核心完成；游標／WS JWT 待補。

### 4. 文字結構圖

```text
[U-J Identity & RBAC]
        |
        +-- auth / A3 RBAC for all gated APIs
        |
        v
[U-A1 Architecture Design] ---- XML ----> [U-A2 Canvas Editing]
        | peer Agent SDK                         |
        | (CTA after generate)                   +-- diagram_id --> [U-A4 Chat]
        v                                        |
[U-A3 Well-Architected Review] <--- xml_data ----+
        |                                        |
        +-- Assessment UI / SSE reviews          +-- share / WS --> [U-A5]
```
