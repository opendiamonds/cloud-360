# Monitoring Design — `U15 memory-page-ui`

> **本站無可交付的監控設計**，原因是現況而非省略：本 intent 沒有任何 dashboard
> 或告警通道（先例 `U24` 的同一判定），前端也沒有遙測管道。本檔記下本單元
> **有**哪些訊號、誰消費它們，以及缺口在哪。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/memory-page-ui/nfr-design/security-design.md` | `SEC-U15-5`（console 不含記憶內容） |
| `construction/memory-page-ui/nfr-design/performance-design.md` | 補償重抓失敗的處置 |
| `construction/memory-page-ui/nfr-design/logical-components.md` | 各元件的失效範圍 |

## 一、本單元產生的訊號

| 訊號 | 產生點 | 內容 | 消費者 |
|---|---|---|---|
| 區塊錯誤態 | `MemoryZone` 的 `error` 態 | 可見文字「無法載入」＋ 重試鍵 | 使用者 |
| 刪除失敗 | `MemoryItem` 的 `failed` 態 ＋ `LiveRegion` 播報 | 就地錯誤訊息 | 使用者、螢幕閱讀器 |
| console 錯誤 | 抓取或刪除的失敗路徑 | 只含狀態碼與操作名（`SEC-U15-5`），不含記憶內容 | 開發者 devtools、e2e 的 `page.on('console')` 斷言 |
| 後端 HTTP 記錄 | `U8` 既有的 uvicorn access log | 方法、路徑、狀態碼 | 維運者（staging 主機上的容器 log） |

## 二、缺口（如實記載）

- **無前端錯誤彙整**：使用者端的失敗不會回傳到任何伺服器。若刪除在 staging 上
  系統性失敗，唯一的偵測面是後端 access log 的 5xx。
- **補償重抓失敗的可見性**：nfr-design 審查 `R-02` 指出目前設計在補償重抓失敗時
  靜默，而先例 `AdminPage.tsx:128-130` 會顯示提示。是否補上提示由 code-generation
  計畫依該審查定案；本站不另設監控通道。
- **待核准帳號存取記憶 API 的稽核**：「已核准」檢查落地後，被拒的請求只在 access log
  留下 403，無專屬稽核事件。屬 `U8` 的稽核設計範圍，本站不新增。

## 三、為什麼不在本單元建立監控

建立前端遙測或告警通道是跨全站的基礎設施決定，不屬單一 UI 單元；本 intent 的
可觀測性學科在 `project.md ## Deployment` 第 4 點已列為「仍是真實待辦」。
