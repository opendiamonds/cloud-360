# A3 上傳＋多雲 — Functional Design（精簡）

> Requirements: `a3-upload-multicloud-requirements.md`  
> Branch: `luojingting/feat/a3-feature-updates`


### 1. 資料模型

| 變更 | 說明 |
|---|---|
| `architecture_reviews.diagram_id` | **可為 NULL**（未建檔評核） |
| `architecture_reviews.xml_snapshot` | TEXT，評核當下 XML（未建檔必填；有圖亦可存快照） |
| `wa_lenses.provider` | `aws`／`gcp`／`azure`；每雲至多一筆 `is_active=true`（同 `lens_id`） |

遷移：既有 `wa_lenses` 列 `provider='aws'`；既有 reviews 不變。

### 2. API

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/api/architecture/reviews/detect-provider` | body: `{xml_data}` → `{provider, scores}` |
| POST | `/api/architecture/reviews` | 擴充：`diagram_id?`、`xml_data?`、`save_diagram?`、`title?`、`provider`、`provider_override?` |
| GET/PUT | `/api/architecture/lens/active?provider=` | 分雲 Active Lens |

規則：`diagram_id` 與 `xml_data` 至少一個；`save_diagram=true` 時需 `xml_data`＋`title` 並建 `user_diagrams`。

### 3. 評核管線

1. 解析 XML → `parse_diagram_summary`  
2. `detect_provider`（可覆寫）  
3. `evaluate(xml, provider)` → 對應 rule pack  
4. `resolve_active_lens(db, provider)` → Agent 填答 → score → suggestions  

移除 `provider≠aws` → `unsupported`。

### 4. FE

- Assessment／Workspace：上傳 `.drawio`／`.xml`、可選建檔、顯示偵測雲別＋覆寫  
- Assessment：選圖／上傳後**架構圖預覽**；PDF 匯出附**架構圖對照頁**  
- Lens 編輯：雲別切換  
- gcp／azure 顯示五支柱對照標註  
- （相關 A1）Workspace：下載 `.drawio`  

### 5. 擴充點

- Rule pack：`wa_rule_engine.evaluate` 依 provider 分派  
- Lens：`provider` 欄位；新增雲只需 seed＋規則函式  
