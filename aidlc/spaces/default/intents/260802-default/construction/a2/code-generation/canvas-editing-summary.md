# A2 Canvas Collaborative Editing — Implementation Summary (U-A2)

> Retrospective code summary for the already-implemented A2 core.  
> 已實作之 A2 核心的補寫 code summary。


### 結果

工作區提供 draw.io 相容畫布：可手動編輯、框選後以文字請 AI 針對性修改（Partial Update 保留既有連線）、儲存 XML 至 DB、多張圖下拉切換。進入工作區自動載入上次草稿（與 A4 銜接）。

### 資料

| 項目 | 說明 |
|---|---|
| `user_diagrams` | owner、title、`xml`（mxGraph XML） |
| `users.last_opened_diagram_id` | 進場自動選圖（A4 擁有） |

### API（`/api/collab` + `/api/architecture`）

| Method | Path | 說明 |
|---|---|---|
| GET/POST/PUT/DELETE | `/api/collab/diagrams`… | 圖 CRUD、改標題 |
| POST | `/api/architecture/generate` | 帶 `current_xml` → AI 局部更新；SSE 回 xml |

### 主要程式

| 層 | 檔案 | 職責 |
|---|---|---|
| BE | `services/collab_router.py` | diagrams CRUD |
| BE | `services/agent_router.py` | Partial Updates（`current_xml` merge、連線保留） |
| FE | `pages/WorkspacePage.tsx` | 圖選單、儲存、切圖 |
| FE | `components/DrawioCanvas.tsx` | 畫布嵌入、XML 載入／匯出 |
| FE | `components/ChatBox.tsx` | 送出局部修改請求 |

### AC 對照（stories A2）

| AC | 狀態 |
|---|---|
| 框選節點群組請 AI 修改 | ⚠️ 部分（draw.io 手動框選 + 文字描述；未抽取 selection 座標） |
| AI 替換／新增節點保留連線 | ✅ |
| 多人修改歷史 + 一鍵 Undo | ❌ 未實作（僅 draw.io 內建 undo） |
| 儲存 XML 至 DB、下次自動載入 | ✅（載入屬 A4 bootstrap） |

### 手動驗收

1. 開圖 → 手動編輯 → 儲存 → 重整還原  
2. 對既有圖請 AI「只加 WAF」→ 原節點與連線保留  
3. 下拉切換多張圖，內容互不污染  
4. 無編輯權限使用者 → 儲存／AI 修改被拒（403）

### 已知缺口（轉入後續計畫）

- selection 抽取、AI 變更歷史／Undo → 需另立 code generation plan
