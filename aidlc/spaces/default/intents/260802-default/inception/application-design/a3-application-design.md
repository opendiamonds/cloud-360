# A3 Application Design (Consolidated)

> Consolidates `a3-components.md`, `a3-component-methods.md`, `a3-services.md`, `a3-component-dependency.md`.


### 決策摘要

| 決策 | 選擇 |
|---|---|
| Agent | **獨立** `ReviewAgent`＋Anthropic Agent SDK／OpenRouter（與 A1 同框架，不併入 `design_agent`） |
| API | `/api/architecture/reviews` + **SSE** |
| 編排 | `ReviewService` 先規則後 Agent |
| UI | 新頁 Assessment（Sidebar）＋ Workspace 按鈕／產圖 CTA |

### 產物索引

| 檔案 | 內容 |
|---|---|
| `a3-components.md` | 元件職責 |
| `a3-component-methods.md` | 方法／路由簽名 |
| `a3-services.md` | 編排與 SSE／Agent 對照 |
| `a3-component-dependency.md` | 相依與資料流 |

### 下一階段

Units Generation：將 `U-A3` 寫入 `unit-of-work*.md`。Construction FD 再細化規則表與 schema。
