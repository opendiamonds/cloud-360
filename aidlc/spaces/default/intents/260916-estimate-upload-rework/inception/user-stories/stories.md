# User Stories — C1 估價工作區後補能力（工作負載／教學／SKU 描述）

<!-- 補跑／補交 user-stories（原 stage SKIP，僅 FR fallback）。
     本檔覆蓋 PR 契約要求之 FR1.7、FR12、FR13；其餘 FR 仍見 requirements.md
     與 `../units-generation/unit-of-work-story-map.md`。
     故事 ID：C1-W1／C1-G1／C1-S1（W=Workload、G=Guide、S=SKU）。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）
- **personas**（`./personas.md`）
- **units map**（`../units-generation/unit-of-work-story-map.md`）
- **實作**：`EstimateWorkloadForm.tsx`、`EstimateCalculatorGuideModal.tsx`、`backend/cost/sku_catalog.py`
- **自動化**：`backend/tests/test_workload_context.py`、`test_estimate_intake_api.py`、`test_sku_catalog.py`

## 與 SKIP 的關係（決策說明）

- 本 intent 初始化時 `user-stories` 為 SKIP，units-generation 以 FR 當上游 ID。
- 因 `/cost` 後補工作區能力屬**使用者可見 feature**，SDD／PR review contract 要求至少有 `stories.md` 可追溯。
- **定案**：補交本檔（不回溯重跑整個 inception 閘門）；`unit-of-work-story-map.md` 改標「故事＋FR 雙追溯」。不另開豁免 ADR。

## 優先序

三則皆 **Must Have**（後補工作區最佳化）。彼此獨立可驗收；上傳主路徑不依賴教學彈窗是否開啟。

```
C1-W1 (workload) ----\
                      +--> 上傳／建議上下文（既有 FR5.4）
C1-S1 (SKU desc) ----/
C1-G1 (guide) 獨立於上傳，可單獨交付
```

---

## C1-W1 上傳前填寫選填工作負載／預算上下文

> **As a** Alex（David 具 C1 edit 亦可），
> **I want** 在 `/cost` 上傳區上方填寫選填的系統說明、資訊需求、費用限制、流量與常用負載指標，
> **so that** 之後產生的 AI 建議能對到真實工作負載，而不是只看估價表數字。

**優先序**：Must Have  
**建置依賴**：無（未填不得擋上傳）  
**涵蓋**：FR1.7、FR5.4（上下文進 prompt）  
**實作**：`frontend/src/components/cost/EstimateWorkloadForm.tsx`、`EstimateUploadZone.tsx`；`backend/cost/workload_context.py`；intake multipart `workload_context`  
**測案**：`backend/tests/test_workload_context.py`；`test_estimate_intake_api.py::test_upload_persists_workload_context_for_advice`

### 驗收標準

**AC-W1.1 表單可見且選填**
- **Given** 使用者具 C1 edit 並開啟 `/cost`
- **When** 檢視上傳區上方
- **Then** 出現工作負載／預算表單（`data-testid="estimate-workload-form"`）
- **And** 所有欄位皆可留空；留空時仍可成功上傳估價表

**AC-W1.2 有填則持久化**
- **Given** 使用者填了至少一欄（例如系統說明）
- **When** 上傳合法估價表
- **Then** API 回 201，回應與該 `EstimateSet` 持久化內容含對應 `workload_context`
- **And** 後續建議產生路徑可讀到該上下文（FR5.4）

**AC-W1.3 空／非法 JSON 不擋上傳**
- **Given** 未傳 `workload_context` 或傳空物件／非法 JSON
- **When** 上傳
- **Then** 上傳主路徑仍成功；工作負載欄位為空或不被寫入垃圾資料（見 `normalize_workload_context`）

---

## C1-G1 三雲官方估價教學彈窗

> **As a** Alex，
> **I want** 在 `/cost` 用按鈕開啟 AWS／GCP／Azure 各自的估價教學（含截圖與匯出格式），
> **so that** 我知道要去哪個官方計算機、匯出哪種檔，而不只是被丟一個外連。

**優先序**：Must Have  
**建置依賴**：無  
**涵蓋**：FR12.1–FR12.5  
**實作**：`EstimateOfficialCalculators.tsx`、`EstimateCalculatorGuideModal.tsx`；靜態圖 `frontend/public/cost-guides/`  
**測案**：成本頁 e2e／手動（requirements OQ9：教學彈窗走 e2e）

### 驗收標準

**AC-G1.1 三雲按鈕而非裸外連**
- **Given** 使用者開啟 `/cost`
- **When** 檢視官方估價教學區
- **Then** AWS、GCP、Azure 各有一顆按鈕
- **And** 點擊開啟對話框，不是只在當下以裸 `<a>` 取代教學

**AC-G1.2 分頁教學與匯出格式**
- **Given** 任一雲教學彈窗已開啟
- **When** 翻閱 2–3 頁
- **Then** 每頁含官網畫面截圖與關鍵控件呼出（建立估價／加入服務／匯出等）
- **And** 文案標明該雲應匯出格式：AWS CSV、GCP CSV、Azure XLSX

**AC-G1.3 官方連結與靜態資產**
- **Given** 教學彈窗最後頁
- **When** 使用者需要前往官方站
- **Then** 提供該雲官方計算機連結
- **And** 截圖來自版控靜態資產；執行期不得再啟動 Playwright 抓頁（FR9.3／NFR8）

---

## C1-S1 目錄形 SKU 自動補規格描述

> **As a** David（Alex 亦可讀明細），
> **I want** 當規格欄看起來像雲目錄 SKU 時，系統自動查目錄並顯示人類可讀描述，
> **so that** 我不必對照外部價目表才能看懂明細列。

**優先序**：Must Have  
**建置依賴**：上傳／解析主路徑（U1／U2）  
**涵蓋**：FR13.1–FR13.6、FR3.1（規格欄呈現）、FR5.5（描述例外、不含單價回寫）  
**實作**：`backend/cost/sku_catalog.py`；明細 `spec_description`；UI `EstimateCloudCard`  
**測案**：`backend/tests/test_sku_catalog.py`（@story FR13）；手動案 M-4（真實目錄）

### 驗收標準

**AC-S1.1 僅目錄形 SKU 才外呼**
- **Given** 規格為人類可讀機型或區域字串（如 `m5.large`、`us-east-1`）
- **When** 執行 `looks_like_catalog_sku`／enrich
- **Then** 不觸發目錄查詢
- **And** GCP `XXXX-XXXX-XXXX`、Azure `DZH*`／`Standard_*`、AWS 符合長度之英數 SKU 可觸發查詢

**AC-S1.2 只寫描述、不寫單價**
- **Given** 目錄查詢回傳描述字串
- **When** 上傳完成並寫入 `EstimateLineItem`
- **Then** `spec_description` 有值；原始 `spec` 保留
- **And** 不得把 hourly／單價寫入任何金額欄；intake 寫入路徑不得 import `pricing_client`／`pricing_sdk`

**AC-S1.3 失敗靜默降級**
- **Given** 查詢逾時、缺憑證或查無資料
- **When** 上傳
- **Then** 該列維持原始規格、上傳仍 201
- **And** 不得因單一 SKU 失敗整批失敗；互異 SKU 外呼有上限（實作 `_MAX_UNIQUE`）

**AC-S1.4 UI 優先顯示描述**
- **Given** 列上已有 `spec_description`
- **When** 使用者檢視雲別明細卡
- **Then** 規格欄優先顯示該描述，原始 SKU 為副標或次要資訊

---

## 追溯矩陣（故事 → FR → 實作／測案）

| Story | FR | 主要實作 | 自動化／手動 |
|---|---|---|---|
| C1-W1 | FR1.7、FR5.4 | `EstimateWorkloadForm`、`workload_context`、intake multipart | `test_workload_context`、`test_estimate_intake_api` |
| C1-G1 | FR12.1–12.5 | `EstimateOfficialCalculators`、`EstimateCalculatorGuideModal`、`public/cost-guides/` | e2e／手動 |
| C1-S1 | FR13.*、FR3.1、FR5.5 | `sku_catalog.py`、`EstimateCloudCard` | `test_sku_catalog`；手動 M-4 |
