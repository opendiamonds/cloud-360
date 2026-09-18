# Code Generation Plan — Unit `a1-a3-ux`

> Intent: `260806-a1-a3-ux` · Requirements: `inception/requirements-analysis/requirements.md`  
> Test strategy: **Minimal**（每項需求至少一則單元測試／happy path）  
> 無 `unit-of-work.md`（bugfix 設計）；以 requirements + codekb 為範圍依據

## Traceability

| Plan Step | FR / NFR |
|---|---|
| 1–3 | FR-GUARD-* / NFR-02 |
| 4 | FR-EDGE-* |
| 5–7 | FR-NAV-* / NFR-03 |
| 8–10 | FR-DRAW-* |
| 11–12 | 測試與摘要 |

## Steps

### Step 1: Prompt 預檢模組（backend）
- [x] 新增 `backend/services/prompt_guard.py`：偵測「變更 Cloud-360 自身 DB／系統值／API key／金鑰／credentials」等意圖
- [x] 匯出 `is_platform_self_modification(text) -> bool` 與固定拒絕訊息常數
- [x] 對應：FR-GUARD-01／02

### Step 2: 串接 generate 路徑
- [x] 在 `agent_router.py` 的 `/generate` 與 `/generate-wa-collab` 進入 Design Agent **前**呼叫預檢；命中則 SSE／JSON 回固定拒答、不呼叫 LLM
- [x] 對應：FR-GUARD-01／02／04

### Step 3: System prompt 補強
- [x] 更新 `backend/prompts/cloud_architecture_system_prompt.md`（或 `build_system_prompt`）加入拒答政策
- [x] 對應：FR-GUARD-03

### Step 4: diagram_builder 邊線 ports
- [x] 修改 `backend/services/diagram_builder.py`：edge 帶 `exitX/Y`、`entryX/Y`（與必要時 waypoint），避免穿過 image icon
- [x] 對應：FR-EDGE-01／02／03

### Step 5: Layout／Sidebar 收合
- [x] `Sidebar`／`Layout` 支援收合；localStorage 鍵（如 `cloud360.nav.sidebarCollapsed`）
- [x] 收合後主內容吃滿寬度；提供 `data-testid`（如 `sidebar-toggle`）
- [x] 對應：FR-NAV-01／02、NFR-03

### Step 6: Sidebar IA 分層（A／J）
- [x] 大類 A → A1 Workspace、A3 Assessment；大類 J → 使用者角色／授權申請／權限矩陣
- [x] 依路由自動展開所屬大類（Q6=A）
- [x] 對應：FR-NAV-03／04／05

### Step 7: Workspace 與 layoutEpoch 聯動
- [x] Sidebar 收合變更時遞增 `layoutEpoch`（與 Chat 收合相同機制）
- [x] 「退出」後展開 Sidebar（FR-DRAW-02）
- [x] 對應：FR-NAV-02、FR-DRAW-02

### Step 8: DrawioCanvas — save／exit
- [x] 處理 embed `save` → 呼叫既有 `onSaveClick`／父層持久化
- [x] 處理 embed `exit` → 髒資料確認 → `onExit`（父層展開 Sidebar、留在 Workspace）
- [x] 對應：FR-DRAW-01／02

### Step 9: DrawioCanvas — Undo 修復
- [x] 避免 autosave 觸發無謂 `action: load`（僅真實換圖／merge 才 load）
- [x] 確保畫布焦點下 Undo／Ctrl+Z 可用
- [x] 對應：FR-DRAW-03／04、Q4=A

### Step 10: WorkspacePage 配線
- [x] 接上 save／exit／layout；確認標題列儲存與 embed 儲存同路徑
- [x] 對應：FR-DRAW-*

### Step 11: 測試（Minimal）
- [x] `backend/tests/test_prompt_guard.py`：命中／未命中案例
- [x] `backend/tests/test_diagram_builder_edges.py`（或擴充既有）：edge 含 exit／entry
- [x] 既有 backend unittest 維持綠色

### Step 12: 文件產出
- [x] 勾選本計畫完成項
- [x] 撰寫 `code-summary.md`

## Out of scope（本單元）
- Review／lens 路徑防衛
- DB migration
- 其他 pillar（B–H）Sidebar 掛載
