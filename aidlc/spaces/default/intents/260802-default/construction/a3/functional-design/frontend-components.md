# A3 Frontend Components — Assessment & Workspace Entry

> Unit `U-A3` · Story A3 MVP  
> Route: **`/assessment`** · Sidebar：「**評估儀表板**」（Q8=A）


### 1. 路由與守衛

| 路徑 | 元件 | 可見／可進 |
|---|---|---|
| `/assessment` | `AssessmentPage` | **A3.view**；Pending → Waiting 頁 |
| Workspace（既有） | CTA／按鈕擴充 | A3.edit 才顯示發起；A3.view 可看結果連結 |

`App.tsx`：註冊 `/assessment`。`Sidebar`：A3.view 時顯示「評估儀表板」。

### 2. AssessmentPage

**職責**：選圖、發起評核、歷史列表、詳情（分數／發現／建議）。

**狀態（建議）**

| State | 說明 |
|---|---|
| `diagrams` | 有權限圖列表（U-A2 API） |
| `selectedDiagramId` | |
| `provider` | 預設 `aws`；gcp／azure **disabled** 或可選但會走 unsupported |
| `replaceLatest` | checkbox，對應 `replace_latest` |
| `reviews` | 歷史（非 archived 預設） |
| `activeReview` | 詳情／進行中 |
| `ssePhase` | idle｜rules｜suggestions｜done｜error｜unsupported |

**UI 區塊**

1. 工具列：圖下拉、provider、`replace_latest`、「執行評核」
2. 進行中：進度（規則完成 → 建議串流）
3. 分數卡：總分 + 五支柱條／數字（權重可 tooltip）
4. 發現表：severity、pillar、title、message；可展開 hint
5. 建議區：串流文字；`rules_only` 時錯誤＋「重試建議」
6. 歷史列表：時間、總分、status、發起者；點開詳情
7. **下載 PDF**（FR-A3-11）：`complete`／`rules_only` 且 A3.view 時顯示；前端 html2canvas＋jsPDF 產生檔案（含分數、RiskCounts、發現、建議、meta）

**API**

- `POST /api/architecture/reviews`（fetch stream／EventSource 模式，帶 Bearer）
- `GET /api/architecture/reviews?diagram_id=`
- `GET /api/architecture/reviews/{id}`
- `POST /api/architecture/reviews/{id}/retry-suggestions`

### 3. Workspace 入口

| 入口 | 行為 |
|---|---|
| 產圖後 CTA「進行 Well-Architected 評估」 | 對**當前圖** `POST` reviews（可導向 `/assessment?diagramId=&reviewId=` 或頁內面板） |
| 「Well-Architected」按鈕 | 同上，針對目前選中 diagram |

可選：輕量 `ReviewPanel` 抽屜消費同一 SSE；或直接 `navigate('/assessment?...')`。

### 4. Sidebar

- 標籤：**評估儀表板**
- 條件：`permissions.A3.view`
- 連結：`/assessment`

### 5. 互動要點

1. SSE：先渲染 `rules_done`，再追加 `suggestion_delta`。
2. `unsupported`：顯示「本期僅支援 AWS」類訊息，仍出現在歷史。
3. 無權限按鈕隱藏（非僅 disabled），與既有 RBAC Sidebar 模式一致。
4. Fiona／Hannah：同一 `review_id` 詳情只讀（有 diagram 分享＋A3.view）。

### 6. Out of scope UI

SPOF 模擬動畫、畫布上故障標示（下期）。PDF 下載已納入本期（見 UI 區塊 7）。
