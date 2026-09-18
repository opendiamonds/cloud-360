# A3 增量需求：自行上傳架構圖 ＋ 完善 GCP／Azure

> AIDLC Inception → Requirements Analysis  
> Branch: `luojingting/feat/a3-feature-updates`  
> 問答：`inception/plans/a3-upload-multicloud-questions.md`（2026-07-27）  
> 基準：`a3-well-architected-requirements.md`、`stories.md` §A3


### 1. Intent

| 項目 | 判定 |
|---|---|
| 使用者意圖 | 上傳自有架構圖做 Well-Architected 評核；並完善 GCP／Azure |
| 類型 | Brownfield 功能增量（A3／U-A3） |
| 複雜度 | High（雙入口上傳＋三雲規則／Lens 分拆） |
| Depth | Comprehensive |

### 2. 決策摘要（來自 Q1–Q9）

| # | 決策 |
|---|---|
| Q1 | **同一期**做上傳 ＋ 多雲 |
| Q2 | 上傳僅 **draw.io／`.drawio`／mxGraph XML** |
| Q3 | **可選建檔**：預設可一次性評核；可勾「同時存成架構圖」 |
| Q4 | **Assessment 與 Workspace 兩處皆可上傳** |
| Q5 | GCP／Azure **對齊 AWS 深度**（獨立 rule pack＋Lens／Agent 填答與建議可跑通） |
| Q6 | 本期 **統一以 AWS WA 五支柱對照**；UI 標註 GCP／Azure 圖以此對照評核 |
| Q7 | **自動偵測 provider**，可手動覆寫 |
| Q8 | **每雲一份 Active Lens**（aws／gcp／azure），設計需可隨時擴充規則／題目 |
| Q9 | **明確不做**：呼叫雲端官方 WA API。另：依 Q2 不做圖片／PDF 視覺評核；SPOF 模擬維持延後 |

### 3. Functional Requirements

#### 3.1 上傳與建檔

| ID | 需求 |
|---|---|
| FR-A3U-01 | Assessment：選圖區旁提供「上傳架構圖」（接受 `.drawio`／`.xml`，內容為 mxGraph） |
| FR-A3U-02 | Workspace：提供上傳，載入畫布（與既有 XML 流程相容）後可直接走 Well-Architected |
| FR-A3U-03 | 上傳後可勾選「同時存成架構圖」：勾選 → 寫入 `user_diagrams`（需命名）；未勾選 → 仍可發起評核（見 FR-A3U-04） |
| FR-A3U-04 | 未建檔評核：後端接受上傳 XML（或暫存 id）完成評核並寫入 `architecture_reviews`；歷史可查該次報告；工作區未必能再開同圖 |
| FR-A3U-05 | 非法／非 mxGraph 檔 → 明確錯誤，不建立評核 |
| FR-A3U-06 | 權限：上傳評核需 **A3.edit**；建檔需 **A1/A2 編輯語意**（與現有存圖權限一致，FD 對齊 `canArch('edit')`） |

#### 3.2 多雲 Provider

| ID | 需求 |
|---|---|
| FR-A3M-01 | 解除 `provider≠aws` → `unsupported`；**aws／gcp／azure** 皆可跑完整管線（規則→Lens 填答→打分→建議） |
| FR-A3M-02 | 依圖摘要／節點關鍵字 **自動偵測** provider；使用者可手動覆寫後再評核 |
| FR-A3M-03 | UI 在 gcp／azure 時顯示說明：「本期以 AWS Well-Architected 五支柱對照評核」 |
| FR-A3M-04 | **獨立 rule pack**：`wa-aws-*`、`wa-gcp-*`、`wa-azure-*`（服務／邊界關鍵字與啟發式 findings 對齊該雲語意，深度目標對齊現有 AWS） |
| FR-A3M-05 | Agent 填答與 Review Agent 建議需帶入 provider 與對應服務語彙；仍沿用 **Claude Agent SDK + OpenRouter**（與 A1／現有 A3 相同） |
| FR-A3M-06 | **每雲 Active Lens**：資料模型支援 `provider`（或 lens_id 命名空間）；編輯 UI 可切換雲別；儲存／讀取評核使用對應 Lens |
| FR-A3M-07 | Lens／規則擴充點文件化（新增雲或新規則不需改編排主流程） |

#### 3.3 相容與回歸

| ID | 需求 |
|---|---|
| FR-A3C-01 | 既有 AWS 評核、PDF、歷史、Lens 編輯（審核者）行為不回歸 |
| FR-A3C-02 | 舊 `wa_lenses` 單筆 active 遷移為 aws active（gcp／azure 可自檔案 seed 或空模板） |
| FR-A3C-03 | 無權限 → 403；pending 使用者不可評核 |

### 4. Out of Scope（本期）

- 呼叫 AWS WA Tool／Azure Review／GCP 官方評估 API  
- PNG／SVG／PDF 視覺或 OCR 評核  
- SPOF／AZ 中斷模擬動畫  
- 各雲官方框架支柱名稱 UI（留待下期；本期五支柱對照＋標註即可）

### 5. Non-Functional

| ID | 類別 | 需求 |
|---|---|---|
| NFR-A3U-01 | Security | 上傳檔大小／內容驗證；不把完整 XML 打進公開 log；RBAC |
| NFR-A3U-02 | Reliability | 單雲規則失敗不拖垮其他雲；LLM 失敗仍可 `rules_only` |
| NFR-A3U-03 | Testability | 各雲 rule pack 與 provider 偵測須 unit／PBT；上傳解析須測 |
| NFR-A3U-04 | Ops | schema／seed 變更同步 `schema_rbac.sql`＋`DEPLOY.md` |
| NFR-A3U-05 | Docs | aidlc-docs 繁中（ADR-0009） |

### 6. 建議後續階段

1. 修訂 `stories.md` §A3（上傳、多雲、每雲 Lens）  
2. Workflow Planning（本輪產出 execution plan）  
3. 精簡 FD → Code Gen（建議拆工作包：上傳／建檔 → provider 偵測＋rule packs → per-cloud lens → FE）  
4. Build & Test＋部署說明  

### 7. 核准

請確認本需求後進入／確認 Execution Plan，再開始 Construction。
