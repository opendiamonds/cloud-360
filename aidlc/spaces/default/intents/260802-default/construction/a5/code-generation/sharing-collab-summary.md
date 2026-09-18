# A5 Diagram Sharing & Real-time Collaboration — Implementation Summary (U-A5)

> Retrospective code summary for the implemented A5 core.  
> 已實作之 A5 核心的補寫 code summary。


### 結果

圖表擁有者（或可編輯者）可經 ShareModal 勾選協作者與權限；被分享者依 can_view／can_edit／can_review 取得不同體驗。多人開同一張圖時經 WebSocket 廣播 XML 即時共編；狀態列顯示「協作中／單機模式」。

### 資料

| 項目 | 說明 |
|---|---|
| `diagram_shares` | diagram ↔ user、權限旗標 |

### API（`/api/collab`）

| 類型 | Path | 說明 |
|---|---|---|
| REST | share 相關 endpoints | 建立／查詢分享 |
| WS | `/ws/{workspace_id}` | XML 更新雙向廣播 |

### 主要程式

| 層 | 檔案 | 職責 |
|---|---|---|
| BE | `services/collab_router.py` | share API、WS fan-out、ACL |
| FE | `components/ShareModal.tsx` | 勾選使用者／權限 |
| FE | `hooks/useCollaboration.ts` | WS 連線、收送 XML、連線狀態 |
| FE | `pages/WorkspacePage.tsx` | 協作中／單機標籤、唯讀模式 |

### 權限語意（對齊 role-permission-design）

| 旗標 | 行為 |
|---|---|
| can_edit | 畫布可寫、AI 聊天可用（`DEFAULT_WELCOME`） |
| can_review | 唯讀 + 審核（`REVIEW_ONLY_WELCOME`） |
| can_view | 唯讀（`VIEW_ONLY_WELCOME`），聊天唯讀 |

### AC 對照（stories A5）

| AC | 狀態 |
|---|---|
| ShareModal 勾選授權 | ✅ |
| 多編輯者 WS 即時同步 XML | ✅ |
| 連線狀態標籤（協作中／單機） | ✅ |
| 檢視／編輯／審核歡迎詞與隔離 | ✅ |
| 多人游標可見 | ❌ 未實作（WS 僅廣播 XML） |
| WS JWT 驗證強化 | ⏳ 待補（見 role-permission plan #14） |

### 手動驗收

1. Alex 分享給 Hannah（編輯）＋ Ian（檢視）  
2. 兩人開圖：Hannah 可寫、Ian 唯讀＋警告詞  
3. Hannah 改圖 → Alex 畫布即時更新；斷線 → 標籤轉「單機模式」

### 已知缺口

- cursor 廣播協定、WS JWT → 後續 plan
