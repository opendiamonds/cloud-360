# Requirements Analysis Questions — A1/A3 UX bugfix

> Intent: `260806-a1-a3-ux` · Scope: bugfix · Depth: Minimal  
> 來源：使用者列舉之六項 UX／安全需求＋Reverse Engineering 釐清結果

## 已確認（先前對話／RE 閘門）

以下視為已決，不再重問；寫入 requirements 時直接採用。

| ID | 決策 |
|---|---|
| D1 | App Sidebar 可收合，讓 A1 架構圖可全螢幕編輯（含與既有 Chat 收合協調） |
| D2 | 連線／箭頭不得與元件 icon 重疊；修法以 `diagram_builder` exit／entry／waypoint 為主 |
| D3 | Draw.io「退出」＝未儲存時確認後離開編輯／返回瀏覽 |
| D4 | Draw.io 儲存／退出原生動作須真正生效（對齊 embed 協定） |
| D5 | Undo／Redo 與 Ctrl+Z 須可用 |
| D6 | 使用者若要求變更 Cloud-360 自身 DB／系統值／API key／金鑰等 → 擋下並回「此需求毫無相關，請重新輸入」；作法＝進 agent 前預檢＋system prompt |
| D7 | Sidebar 依 user story 大類（A、J…）；A1／A3 為 A 下第二層；既有 A／J 先改，後續比照 |

---

## Clarifying Questions

### Q1. 全螢幕編輯時，哪些面板預設收合？

**Context**: 已有 Chat 收合；需求新增 App Sidebar 收合。

A. 全螢幕模式一次收合 **Sidebar＋Chat**（建議）
B. 只收合 **Sidebar**；Chat 維持使用者目前狀態
C. Sidebar／Chat **各自獨立**切換，不另設「全螢幕」模式（僅多 Sidebar 按鈕）
D. Other (please specify)

[Answer]: C

### Q2. Draw.io「退出」之後的畫面狀態？

**Context**: 已決「未儲存確認後離開編輯／返回瀏覽」。

A. 留在 Workspace；展開 Sidebar（與 Chat 依使用者偏好）；結束「全螢幕編輯」即可（建議）
B. 留在 Workspace；強制展開 Sidebar＋Chat
C. 導向其他頁（例如 Assessment）
D. Other (please specify)

[Answer]: A

### Q3. 原生 Draw.io「儲存」按下去應做什麼？

A. 與標題列「儲存架構圖」相同：呼叫既有 collab `PUT/POST` 持久化（建議）
B. 只下載 `.drawio` 檔，不寫後端
C. 兩者都做（先持久化，再可選下載）
D. Other (please specify)

[Answer]: A

### Q4. Ctrl+Z／Undo 在什麼焦點下必須有效？

A. 僅當焦點在 **draw.io iframe／畫布** 內（建議；符合一般 embed）
B. 即使焦點在左側 Chat，Ctrl+Z 也要撤銷畫布（需攔截全域快捷鍵）
C. A＋提供畫布工具列明確 Undo／Redo 按鈕確保可用
D. Other (please specify)

[Answer]: A

### Q5. Prompt 防衛套用範圍？

A. 僅 `POST /generate` 與 `POST /generate-wa-collab` 的使用者訊息（建議）
B. A ＋ Review Agent／lens agent 路徑一併擋
C. A ＋ 前端 Chat 送出前也擋（雙層）
D. Other (please specify)

[Answer]: A

### Q6. Sidebar 分層的預設展開行為？

A. 依目前路由自動展開所屬大類（在 A1 時展開「A」）（建議）
B. 全部大類預設展開
C. 全部大類預設收合，手動點開
D. Other (please specify)

[Answer]: A

---

## Consolidated Summary Confirmation

### 答案摘要

| 題 | 選擇 | 含義 |
|---|---|---|
| D1–D7 | 已決 | Sidebar 可收合、線不蓋 icon（builder ports）、退出=確認後離開編輯、儲存／退出須生效、Undo／Ctrl+Z、prompt 預檢＋固定拒答、Sidebar A／J 分層 |
| Q1 | C | Sidebar／Chat **各自獨立**切換，不另設「全螢幕」模式（僅多 Sidebar 收合） |
| Q2 | A | 「退出」後留在 Workspace；展開 Sidebar；Chat 依偏好 |
| Q3 | A | 原生 Draw.io 儲存＝標題列儲存＝collab 持久化 |
| Q4 | A | Undo／Ctrl+Z 僅畫布／iframe 焦點內必須有效 |
| Q5 | A | Prompt 防衛僅 `/generate` 與 `/generate-wa-collab` |
| Q6 | A | Sidebar 依目前路由自動展開所屬大類 |

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct