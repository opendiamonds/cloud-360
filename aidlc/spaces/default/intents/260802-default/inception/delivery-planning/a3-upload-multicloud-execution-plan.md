# A3 上傳＋多雲 — Execution Plan（Workflow Planning）

> Requirements: `inception/requirements/a3-upload-multicloud-requirements.md`  
> Answers: `inception/plans/a3-upload-multicloud-questions.md`  
> Branch: `luojingting/feat/a3-feature-updates`


### 1. 範圍與影響

| 面向 | 判定 |
|---|---|
| 架構 | 同 monolith；擴充 A3 評核管線與 FE 入口 |
| 資料模型 | **是** — `wa_lenses` 依 provider 分 active；評核／暫存上傳欄位（FD 定案） |
| API | **是** — 上傳／可選建檔、評核接受 inline XML、lens CRUD 帶 provider |
| 規則引擎 | **是** — gcp／azure rule pack 對齊 AWS 深度 |
| FE | Assessment＋Workspace 上傳；provider 自動偵測＋覆寫；Lens 分雲編輯 |
| 部署契約 | schema／seed → `schema_rbac.sql`＋`DEPLOY.md` |

### 2. 階段取捨

| 階段 | 執行？ | 理由 |
|---|---|---|
| WD／RE | 跳過 | 已完成 |
| RA／WP | ✅ 本輪 | 問答已收 |
| User Stories | ✅ 修訂 A3 | 追加 AC |
| Application Design | 精簡併 FD | 不重畫系統架構 |
| Construction FD | ✅ | 上傳流、暫存 vs 建檔、per-cloud lens schema、rule pack 介面 |
| NFR | 精簡併 FD | 沿用 A3 NFR＋上傳安全 |
| Infrastructure | 跳過 | 無新 infra |
| Code Generation | ✅ | 建議分 4 包（見下） |
| Build & Test | ✅ | 三雲規則＋上傳＋回歸 AWS |
| Operations | checklist 增量 | 部署／遷移注意 |

### 3. Construction 工作包（建議順序）

1. **資料與契約**  
   - `wa_lenses` 加 `provider`（或每雲一列 `lens_id`）；遷移既有列 → `aws`  
   - seed gcp／azure 預設 Lens（可由 AWS 模板複製後換服務用詞）  
   - `schema_rbac.sql`／`DEPLOY.md`／`_ensure_*_schema`

2. **上傳＋可選建檔**  
   - API：接受 multipart／raw XML；驗證 mxGraph  
   - 勾選建檔 → 既有 collab diagrams POST  
   - 未建檔 → 評核 API 支援 `xml_data`（或 short-lived upload id）  
   - FE：Assessment＋Workspace 上傳 UI

3. **Provider 偵測＋多雲 rule pack**  
   - `detect_provider(summary)`＋手動覆寫  
   - 實作 `wa-gcp-*`、`wa-azure-*`（深度對齊現有 AWS 啟發式）  
   - 移除／限縮 `unsupported` 路徑  
   - Review／Lens Agent prompt 帶 provider

4. **Per-cloud Active Lens**  
   - resolve／save 依 provider  
   - Lens 編輯 UI 雲別切換；擴充點說明（方便後續加規則）  
   - 評核管線讀對應 Lens

5. **測試與文件**  
   - unit：解析上傳、偵測、三雲規則、lens 分雲、權限  
   - 更新 stories／go-live checklist／code summary

### 4. 風險

| 風險 | 緩解 |
|---|---|
| Q5「對齊 AWS 深度」工期長 | 先定規則清單與對照表；PBT 鎖行為；可先合併 PR1 上傳＋偵測骨架再補規則 |
| 未建檔評核與歷史／權限 | FD 明確：review 列存 xml 快照或 blob 參照；授權仍綁發起者 |
| 三份 Lens 維護成本 | 共用題目結構；差異僅 choices／hints／riskRules；UI 可「自 AWS 複製」 |
| 自動偵測誤判 | 必顯示偵測結果＋一鍵覆寫；評核前確認 |

### 5. 建議實作切分（若需多 PR）

| PR | 內容 |
|---|---|
| PR1 | 上傳＋可選建檔＋評核接受 XML（仍可僅 AWS） |
| PR2 | Provider 偵測＋解除 unsupported＋GCP／Azure rule pack |
| PR3 | Per-cloud Lens＋編輯 UI＋遷移 |

（若你希望單 PR 也可；預設依上序在同一 branch 連續完成。）

### 6. 核准門檻

請回覆核准 Execution Plan（可指定「單 PR」或「PR1→PR3」），通過後進入 Functional Design → Code Generation。
