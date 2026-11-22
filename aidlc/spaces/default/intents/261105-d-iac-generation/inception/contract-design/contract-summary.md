# 契約摘要：Story D IaC `/api/iac`

本檔為 contract-design 的唯一產出。規格區塊為平行開發時的契約真實來源；執行期 OpenAPI 仍以 repo 根目錄 `openapi.json` 為準（construction 時由本摘要落地並過 CI drift 閘門）。

> Q1–Q5=A；Looks correct 已核可。

## 契約一覽

| # | Provider Unit | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C1 | U1 `u1-iac-api` | U2 `u2-iac-ui`；External: TestClient／自動化 | OpenAPI REST（同步 HTTP JSON；download 為 zip 二進位） | U1 |

**不納入本輪新建正式契約（附註）**

| 邊界 | 理由 | 承接 |
|---|---|---|
| U1 → 既有圖公開 API | ADR-005：僅存 `diagram_id`；讀寫沿用既有公開契約 | 不在本檔重寫；缺公開包裝則圖域加最小端點 |
| U1 → RBAC `require_story_action` | 既有依賴注入；本契約只釘 D1／D2／D3 的 view／edit 映射 | US6.1 TestClient 成對 403／2xx |
| U1 內 Session ↔ 三核心 | 同 process 呼叫；非跨 unit | functional-design 釘簽章／PBT |

---

## C1 — IaC Workspace HTTP（U1 → U2／TestClient）

**Owner:** U1　**Base path:** `/api/iac`　**Auth:** 既有 JWT（與其他 `/api/*` 相同）  
**錯誤形狀（閘失敗）:** HTTP **422**＋穩定 `error.code`；**403** 專留給 RBAC（Q2=A）  
**版本政策:** 無 URL 版號；破壞性變更須同 PR 更新 OpenAPI＋UI＋TestClient；additive 欄位消費者忽略未知欄（Q4=A）  
**逾時／重試:** 伺服器設明確超時／取消；執行類 POST **不自動重試**（使用者按鈕才再送）；`GET /download` 可重試（Q5=A）。具體秒數見下方 Open questions。

### 操作與 RBAC 映射

| Method／Path | Story action | 前置閘（失敗 → 422＋code） |
|---|---|---|
| `POST /generate` | D1 `edit` | 有效 `diagram_id`；無權 → 403 |
| `POST /scan` | D2 `edit` | 同 session 有 D1 成功草稿；否則 `missing_draft` |
| `POST /secrets/rewrite` | D3 `edit` | D1 成功草稿 **∧** 至少一次 D2 `status=succeeded`；否則 `missing_draft`／`missing_scan_report`；舊／作廢 `report_id` → 422 |
| `GET /session` | D1 `view`（或更高） | 無權 → 403；無產物時回空態結構（非 404） |
| `GET /download` | D1 `edit`（不得以僅 `view` 放行；FD Q3=A／關 R-01） | 無草稿 → `missing_draft`；HIGH／CRITICAL **確認在 UI**，API 不閘 |

### 行為不變量（契約層）

- 切圖／`diagram_id` 變更：清空行程內產物並作廢舊 `report_id`；進行中請求不得寫回新脈絡。
- 回應／log／下載物不得回洩 D3 已改寫前的明文樣式。
- OpenAPI／工具清單靜態斷言：**無** apply／destroy。
- 行程內產物；重新整理可丟失（ADR-002）。

```yaml
openapi: 3.1.0
info:
  title: Cloud-360 IaC Workspace API
  version: "1.0.0"
  x-cloud360-stability: draft
  description: >
    Story D 同步 HTTP。能力動詞資源（Q1=A）。無 URL 版號（Q4=A）。
servers:
  - url: /api/iac
paths:
  /generate:
    post:
      operationId: iacGenerate
      summary: D1 — 對脈絡圖產生多檔 HCL 模組樹草稿
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [diagram_id]
              properties:
                diagram_id: { type: integer, minimum: 1 }
      responses:
        "200":
          description: 草稿已寫入行程內 session
          content:
            application/json:
              schema: { $ref: "#/components/schemas/GenerateResponse" }
        "401": { description: Unauthorized }
        "403": { description: 缺少 D1 edit }
        "422":
          description: 語意前置失敗（如無效／不可見 diagram）
          content:
            application/json:
              schema: { $ref: "#/components/schemas/GateError" }
        "504": { description: 伺服器／閘道超時（具體秒數見 Open questions） }

  /scan:
    post:
      operationId: iacScan
      summary: D2 — 對成功草稿執行靜態掃描
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [diagram_id]
              properties:
                diagram_id:
                  type: integer
                  minimum: 1
                  description: 必填；對齊 session 鍵（FD Q2=A／關 R-02）
      responses:
        "200":
          description: 掃描報告（允許 zero findings）
          content:
            application/json:
              schema: { $ref: "#/components/schemas/ScanResponse" }
        "401": { description: Unauthorized }
        "403": { description: 缺少 D2 edit }
        "422":
          description: missing_draft／missing_diagram_id／invalid_diagram／diagram_mismatch
          content:
            application/json:
              schema: { $ref: "#/components/schemas/GateError" }
        "504": { description: 超時 }

  /secrets/rewrite:
    post:
      operationId: iacSecretsRewrite
      summary: D3 — 在有 D2 成功報告後改寫疑似密文為 SM 參考語法
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [diagram_id]
              properties:
                diagram_id: { type: integer, minimum: 1, description: 必填；對齊 session 鍵 }
                report_id:
                  type: string
                  description: 可選；若省略則使用該 session 最新一次 succeeded 報告；若提供須未作廢
      responses:
        "200":
          description: 改寫結果；不得含明文密文樣式
          content:
            application/json:
              schema: { $ref: "#/components/schemas/RewriteResponse" }
        "401": { description: Unauthorized }
        "403": { description: 缺少 D3 edit }
        "422":
          description: missing_draft／missing_scan_report／stale_report_id／missing_diagram_id／invalid_diagram／diagram_mismatch
          content:
            application/json:
              schema: { $ref: "#/components/schemas/GateError" }
        "504": { description: 超時 }

  /session:
    get:
      operationId: iacGetSession
      summary: 讀取目前行程內草稿／報告／改寫摘要（空態非 404）
      security: [{ bearerAuth: [] }]
      parameters:
        - name: diagram_id
          in: query
          required: true
          schema: { type: integer, minimum: 1 }
      responses:
        "200":
          content:
            application/json:
              schema: { $ref: "#/components/schemas/SessionSnapshot" }
        "401": { description: Unauthorized }
        "403": { description: 缺少 D1 view }

  /download:
    get:
      operationId: iacDownloadZip
      summary: 下載目前草稿模組樹 zip（二進位）；HIGH／CRITICAL 確認由 UI 負責
      security: [{ bearerAuth: [] }]
      parameters:
        - name: diagram_id
          in: query
          required: true
          schema: { type: integer, minimum: 1 }
      responses:
        "200":
          description: application/zip 二進位
          headers:
            Content-Disposition:
              schema: { type: string }
              description: 'attachment; filename="iac-<diagram_id>.zip"'
          content:
            application/zip:
              schema: { type: string, format: binary }
        "401": { description: Unauthorized }
        "403": { description: 無權下載 }
        "422":
          description: missing_draft
          content:
            application/json:
              schema: { $ref: "#/components/schemas/GateError" }

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    GateError:
      type: object
      required: [error]
      properties:
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
              enum:
                - missing_draft
                - missing_scan_report
                - stale_report_id
                - missing_diagram_id
                - invalid_diagram
                - diagram_mismatch
              description: >
                穩定機器碼；UI／TestClient 依此分支。
                missing_diagram_id＝缺欄；invalid_diagram＝非正整數等形狀錯；
                diagram_mismatch＝body／query 的 diagram_id 與該 user 活躍槽不一致
            message:
              type: string
              description: 人類可讀；不得作為唯一分支依據
    FileEntry:
      type: object
      required: [path, content]
      properties:
        path:
          type: string
          description: 相對模組樹路徑（如 main.tf）
        content: { type: string }
    ModuleTree:
      type: object
      required: [files]
      properties:
        files:
          type: array
          minItems: 0
          items: { $ref: "#/components/schemas/FileEntry" }
          description: >
            status=succeeded 時至少含 main.tf／variables.tf／outputs.tf（或等價）；
            status=failed 時可為空陣列
    DraftSummary:
      type: object
      required: [draft_id, diagram_id, status, module_tree]
      description: >
        status=succeeded 時 module_tree 必含至少 main／variables／outputs（或等價）；
        status=failed 時 module_tree.files 可為空陣列（仍必填欄位，避免省略鍵）
      properties:
        draft_id: { type: string }
        diagram_id: { type: integer }
        status: { type: string, enum: [succeeded, failed] }
        module_tree: { $ref: "#/components/schemas/ModuleTree" }
        created_at: { type: string, format: date-time }
    Finding:
      type: object
      required: [id, severity, title]
      properties:
        id: { type: string }
        severity:
          type: string
          enum: [INFO, LOW, MEDIUM, HIGH, CRITICAL]
          description: 機器枚舉；UI 另顯示可讀文字
        title: { type: string }
        detail: { type: string }
        path: { type: string }
    ScanReport:
      type: object
      required: [report_id, draft_id, diagram_id, status, findings, max_severity]
      properties:
        report_id: { type: string }
        draft_id: { type: string }
        diagram_id: { type: integer }
        status: { type: string, enum: [succeeded, failed] }
        findings:
          type: array
          items: { $ref: "#/components/schemas/Finding" }
        max_severity:
          type: string
          enum: [NONE, INFO, LOW, MEDIUM, HIGH, CRITICAL]
          description: NONE＝零 finding
        created_at: { type: string, format: date-time }
    RewriteResult:
      type: object
      required: [rewrite_id, draft_id, report_id, status, rewritten_paths]
      properties:
        rewrite_id: { type: string }
        draft_id: { type: string }
        report_id: { type: string }
        status: { type: string, enum: [succeeded, failed] }
        rewritten_paths:
          type: array
          items: { type: string }
          description: 空陣列＝無可改寫項
        created_at: { type: string, format: date-time }
    GenerateResponse:
      type: object
      required: [draft]
      properties:
        draft: { $ref: "#/components/schemas/DraftSummary" }
    ScanResponse:
      type: object
      required: [report]
      properties:
        report: { $ref: "#/components/schemas/ScanReport" }
    RewriteResponse:
      type: object
      required: [rewrite, draft]
      properties:
        rewrite: { $ref: "#/components/schemas/RewriteResult" }
        draft:
          $ref: "#/components/schemas/DraftSummary"
          description: 改寫後草稿（無明文密文樣式）
    SessionSnapshot:
      type: object
      required: [diagram_id]
      properties:
        diagram_id: { type: integer }
        draft:
          allOf: [{ $ref: "#/components/schemas/DraftSummary" }]
          nullable: true
        latest_scan:
          allOf: [{ $ref: "#/components/schemas/ScanReport" }]
          nullable: true
        latest_rewrite:
          allOf: [{ $ref: "#/components/schemas/RewriteResult" }]
          nullable: true
```

---

## 契約所有權規則

1. **Owner = U1 `u1-iac-api`**：維護本檔 OpenAPI 草案 → construction 落地 `openapi.json`＋router；CI drift 閘門掛在 U1。
2. **Consumer = U2**：僅經本契約消費；不得直呼三核心或私有 session 結構。
3. **破壞性變更**：同 PR 更新 OpenAPI＋U2＋TestClient；禁止先合入破壞性 API 再補 UI。
4. **Additive 欄位**：消費者忽略未知 JSON 欄位；枚舉擴充須向後相容或同 PR 改消費者。
5. **錯誤碼穩定**：`GateError.error.code` 為公開契約；更名視為破壞性。
6. **UI 專屬行為**：HIGH／CRITICAL 下載確認 modal、複製剪貼簿、步驟空態——不進本 OpenAPI 閘。

---

## Open questions

| Contract | Question | Blocks |
|---|---|---|
| C1 | 同步執行 POST／反代的明確超時秒數（契約寫 504，數值未釘） | U1 實作＋閘道設定；可於 functional-design／NFR 釘 |
| C1 | zip 內部目錄佈局／根檔名慣例（超出 `Content-Disposition`） | U1 download；US5.x DoD 抽樣 |
| C1 | 掃描 CLI 品牌與 finding 對映（可 stub） | U1 Scanner；不擋契約路徑 |
| C1 | 多雲「實驗性」HCL 標記字串慣例 | U1 Generator 產物；UI 僅預覽 |
| C1 | PBT 範圍是否另開 ADR 擴張 | 測試設計；非本契約路徑 |

以上 OQ 不阻擋本 stage 核准；Delivery Planning／functional-design 承接。
