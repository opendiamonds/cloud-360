# 契約摘要：C1 估價表上傳

本檔為 contract-design 的唯一產出。規格區塊為平行開發時的契約真實來源；執行期 OpenAPI 仍以 repo 根目錄 `openapi.json` 為準（construction 時由本摘要落地並過 CI drift 閘門）。

## 契約一覽

| # | Provider Unit | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C1 | U1 `estimate-parser` | U2 `estimate-intake-api` | shared-schema | U1 |
| C2 | U2 `estimate-intake-api` | External: SPA（U8／U9）；U7（讀取批次） | OpenAPI REST | U2 |
| C3 | U7 `cost-advice-agent` | External: SPA（U9） | AsyncAPI SSE | U7 |

**不納入正式契約（附註）**

| 邊界 | 理由 | 承接 |
|---|---|---|
| U7 → U2 `EstimateAccessControl` | F1=B：同 process Python 呼叫 | functional-design 釘簽章 |
| U5 → U7 查價結果 | units Q7 排除 | 型別＋測試即可 |
| U2 → U7 觸發建議 | 內部 async | functional-design |

---

## C1 — 解析器輸出（U1 → U2）

**Owner:** U1　**Consumer:** U2　**Mechanism:** 同 process 函式呼叫，負載形狀如下。

```yaml
shared-schema:
  name: EstimateParseResult
  version: "1.0"
  description: >
    EstimateParser.parse(bytes, filename?) 的成功回傳形狀。
    判定失敗時回傳 detection.status=ambiguous，不拋例外。
  types:
    CloudId:
      enum: [aws, azure, gcp]
    ParseStatus:
      enum: [parsed, unidentifiable]
      description: >
        unidentifiable = 該列金額或數量無法解析為數值（FR2.2）。
        品項／規格缺漏但金額與數量完好者不屬此類。
    DetectionStatus:
      enum: [resolved, ambiguous]
    CloudDetection:
      fields:
        status: { type: DetectionStatus, required: true }
        cloud: { type: CloudId, required: false, when: "status=resolved" }
        candidates: { type: "CloudId[]", required: false, when: "status=ambiguous" }
        reason: { type: string, required: false }
    LineItem:
      fields:
        ordinal: { type: integer, required: true, minimum: 0 }
        itemName: { type: string, required: false }
        spec: { type: string, required: false }
        quantity: { type: number, required: false, nullable: true }
        amount: { type: number, required: false, nullable: true }
        currency: { type: string, required: false, nullable: true }
        parseStatus: { type: ParseStatus, required: true }
        rawText: { type: string, required: true }
      invariants:
        - "parseStatus=unidentifiable ⇒ quantity 或 amount 至少一者為 null"
        - "parseStatus=parsed ⇒ quantity 與 amount 皆非 null"
    EstimateTotals:
      fields:
        statedTotal: { type: number, required: false, nullable: true }
        currency: { type: string, required: false, nullable: true }
    ParseResult:
      fields:
        detection: { type: CloudDetection, required: true }
        lines: { type: "LineItem[]", required: true }
        totals: { type: EstimateTotals, required: true }
        sourceFormat: { type: string, enum: [csv, xlsx], required: true }
  validator_output:
    name: MechanicalCheckResult
    description: EstimateValidator.validate(ParseResult) 的輸出；不持久化，每次重算。
    fields:
      currencyConsistent: { type: boolean, required: true }
      currencyOffenders: { type: "integer[]", required: true, description: "異於多數幣別的 ordinal" }
      currencyTie: { type: boolean, required: true, default: false, description: "多數決平手時為 true" }
      quantityPositive: { type: boolean, required: true }
      quantityOffenders: { type: "integer[]", required: true }
      totalReconciled:
        type: object
        required: true
        fields:
          attempted: { type: boolean }
          withinTolerance: { type: boolean, required: false }
          skippedReason: { type: string, required: false, description: "attempted=false 時必填" }
          tolerancePercent: { type: number, const: 0.5 }
```

**錯誤**：解析器不 raise HTTP；I/O／格式完全無法開啟時由 U2 轉成 400 `{"detail": "..."}`。

---

## C2 — 對外 REST（U2 → SPA／U7）

**Owner:** U2　**Base path:** `/api/cost/v1`　**Auth:** 既有 JWT（與其他 `/api/*` 相同）　**錯誤形狀:** `{"detail": string | object}`（Q4=B）

```yaml
openapi: 3.1.0
info:
  title: Cloud-360 Estimate Upload API
  version: "1.0.0"
  x-cloud360-stability: draft
servers:
  - url: /api/cost/v1
paths:
  /sets:
    post:
      operationId: uploadEstimateSet
      summary: 上傳 1–3 個估價表檔，建立 EstimateSet
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [files]
              properties:
                files:
                  type: array
                  minItems: 1
                  maxItems: 3
                  items: { type: string, format: binary }
                diagram_id:
                  type: integer
                  nullable: true
                cloud_overrides:
                  type: string
                  description: JSON 陣列，對應 files 次序；元素為 aws|azure|gcp|null
      responses:
        "201":
          description: 已建立；含解析明細與機械檢查（重算）
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EstimateSetDetail" }
        "400": { description: "副檔名／魔數不符、或雲別仍 ambiguous 且未提供 override", content: { application/json: { schema: { $ref: "#/components/schemas/ErrorDetail" } } } }
        "401": { description: Unauthorized }
        "403": { description: "缺少 C1 故事權限" }
        "413": { description: "單檔 >5MB 或超過 3 檔", content: { application/json: { schema: { $ref: "#/components/schemas/ErrorDetail" } } } }
    get:
      operationId: listEstimateSets
      summary: 目前與歷史上傳清單（預設最近一筆為 current；含歷史）
      security: [{ bearerAuth: [] }]
      parameters:
        - name: include_history
          in: query
          schema: { type: boolean, default: true }
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  items:
                    type: array
                    items: { $ref: "#/components/schemas/EstimateSetSummary" }
  /sets/{set_id}:
    get:
      operationId: getEstimateSet
      security: [{ bearerAuth: [] }]
      parameters:
        - $ref: "#/components/parameters/SetId"
      responses:
        "200":
          content:
            application/json:
              schema: { $ref: "#/components/schemas/EstimateSetDetail" }
        "404": { description: Not found or not visible }
    delete:
      operationId: deleteEstimateSet
      security: [{ bearerAuth: [] }]
      parameters:
        - $ref: "#/components/parameters/SetId"
      responses:
        "204": { description: Deleted }
        "403": { description: Not owner }
  /sets/{set_id}/shares:
    get:
      operationId: listShares
      security: [{ bearerAuth: [] }]
      parameters: [{ $ref: "#/components/parameters/SetId" }]
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  shares:
                    type: array
                    items: { $ref: "#/components/schemas/ShareEntry" }
    put:
      operationId: replaceShares
      summary: 以完整名單覆寫分享對象（僅擁有者）
      security: [{ bearerAuth: [] }]
      parameters: [{ $ref: "#/components/parameters/SetId" }]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [user_ids]
              properties:
                user_ids: { type: array, items: { type: integer } }
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                properties:
                  shares:
                    type: array
                    items: { $ref: "#/components/schemas/ShareEntry" }
  /sets/{set_id}/advice:
    get:
      operationId: getAdviceSnapshot
      summary: 建議快照（非串流）；status=generating|completed|failed
      security: [{ bearerAuth: [] }]
      parameters: [{ $ref: "#/components/parameters/SetId" }]
      responses:
        "200":
          content:
            application/json:
              schema: { $ref: "#/components/schemas/AdviceSnapshot" }
        "404": { description: 尚無 Advice 列（極短窗） }
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  parameters:
    SetId:
      name: set_id
      in: path
      required: true
      schema: { type: integer }
  schemas:
    ErrorDetail:
      type: object
      required: [detail]
      properties:
        detail:
          oneOf:
            - type: string
            - type: object
    EstimateSetSummary:
      type: object
      required: [id, created_at, clouds, is_owner]
      properties:
        id: { type: integer }
        created_at: { type: string, format: date-time }
        note: { type: string, nullable: true }
        diagram_id: { type: integer, nullable: true }
        is_owner: { type: boolean }
        privacy: { type: string, enum: [private, shared] }
        clouds:
          type: array
          items:
            type: object
            properties:
              cloud: { type: string, enum: [aws, azure, gcp] }
              stated_total: { type: number, nullable: true }
              currency: { type: string, nullable: true }
              line_count: { type: integer }
              unparsed_count: { type: integer }
        advice_status:
          type: string
          enum: [none, generating, completed, failed]
          nullable: true
    LineItemView:
      type: object
      required: [ordinal, parse_status, raw_text]
      properties:
        ordinal: { type: integer }
        item_name: { type: string, nullable: true }
        spec: { type: string, nullable: true }
        quantity: { type: number, nullable: true }
        amount: { type: number, nullable: true }
        currency: { type: string, nullable: true }
        parse_status: { type: string, enum: [parsed, unidentifiable] }
        raw_text: { type: string }
    MechanicalCheckView:
      type: object
      description: 伺服器每次讀取時重算，不持久化
      required: [currency_consistent, currency_tie, quantity_positive, total_reconciled, offenders]
      properties:
        currency_consistent: { type: boolean }
        currency_tie: { type: boolean, description: "幣別多數決平手" }
        quantity_positive: { type: boolean }
        total_reconciled:
          type: object
          properties:
            attempted: { type: boolean }
            within_tolerance: { type: boolean, nullable: true }
            skipped_reason: { type: string, nullable: true, description: "attempted=false 時必填" }
        offenders:
          type: object
          properties:
            currency_ordinals: { type: array, items: { type: integer } }
            quantity_ordinals: { type: array, items: { type: integer } }
    CloudEstimateView:
      type: object
      required: [cloud, lines, checks]
      properties:
        cloud: { type: string, enum: [aws, azure, gcp] }
        stated_total: { type: number, nullable: true }
        currency: { type: string, nullable: true }
        lines:
          type: array
          items: { $ref: "#/components/schemas/LineItemView" }
        checks: { $ref: "#/components/schemas/MechanicalCheckView" }
    EstimateSetDetail:
      allOf:
        - { $ref: "#/components/schemas/EstimateSetSummary" }
        - type: object
          required: [estimates]
          properties:
            estimates:
              type: array
              maxItems: 3
              items: { $ref: "#/components/schemas/CloudEstimateView" }
    ShareEntry:
      type: object
      required: [user_id, username, shared_at]
      properties:
        user_id: { type: integer }
        username: { type: string }
        shared_at: { type: string, format: date-time }
    AdviceSnapshot:
      type: object
      required: [estimate_set_id, status]
      properties:
        estimate_set_id: { type: integer }
        status: { type: string, enum: [generating, completed, failed] }
        saving_text: { type: string, nullable: true }
        comparison_text: { type: string, nullable: true }
        quality_text: { type: string, nullable: true }
        unavailable_reasons:
          type: object
          additionalProperties: { type: string }
          description: "鍵為 saving|comparison|quality"
        started_at: { type: string, format: date-time, nullable: true }
        completed_at: { type: string, format: date-time, nullable: true }
```

**SLA／限制（契約層）**

- 單檔 ≤ 5 MB、單次 ≤ 3 檔；超過 → 413。
- 上傳＋解析為同步 HTTP；建議產生在 201 之後背景執行（見 C3）。
- 破壞性變更：新增 `/api/cost/v2`，與 v1 **重疊一個 Bolt 週期**後移除 v1（Q3=B）。

---

## C3 — 建議 SSE（U7 → SPA）

**Owner:** U7　**Endpoint:** `GET /api/cost/v1/sets/{set_id}/advice/stream`　**Auth:** 同 JWT；訂閱前經 U2 授權查詢（非正式化，F1=B）

沿用 A1／A3 慣例：`Content-Type: text/event-stream`，每則 `data:` 行為一個 JSON 物件。

```yaml
asyncapi: 3.0.0
info:
  title: Cloud-360 Estimate Advice Stream
  version: "1.0.0"
  x-cloud360-stability: draft
servers:
  production:
    host: "{api-host}"
    protocol: http
    pathname: /api/cost/v1
channels:
  adviceStream:
    address: sets/{set_id}/advice/stream
    parameters:
      set_id:
        description: EstimateSet id
    messages:
      AdviceEvent:
        payload:
          $ref: "#/components/schemas/AdviceEvent"
operations:
  subscribeAdvice:
    action: receive
    channel:
      $ref: "#/channels/adviceStream"
components:
  schemas:
    AdviceEvent:
      type: object
      required: [type]
      properties:
        type:
          type: string
          enum:
            - heartbeat
            - progress
            - partial
            - completed
            - failed
            - timeout
        content:
          type: string
          description: 人類可讀進度或錯誤摘要
        phase:
          type: string
          enum: [saving, comparison, quality, lookup]
          description: progress／partial 時建議帶上
        advice:
          description: type=completed 時帶完整快照
          $ref: "#/components/schemas/AdviceSnapshotInline"
        ts:
          type: string
          format: date-time
    AdviceSnapshotInline:
      type: object
      properties:
        status: { type: string, enum: [completed, failed] }
        saving_text: { type: string, nullable: true }
        comparison_text: { type: string, nullable: true }
        quality_text: { type: string, nullable: true }
        unavailable_reasons:
          type: object
          additionalProperties: { type: string }
```

**串流行為（契約層）**

| 規則 | 約定 |
|---|---|
| Heartbeat | 至少每 15s 送 `type=heartbeat`，避免 Cloudflare／反向代理 idle 斷線 |
| 逾時 | 自 `Advice.started_at` 起 5 分鐘仍未完成 → 送 `type=timeout` 後關閉串流；`Advice.status=failed`（或保留 generating 由逾時清理——functional-design 釘選，見 OQ-CD2） |
| 客戶端斷線 | **不**取消背景工作（F1=B／domain F1=B）；重連可再訂閱或改打 `GET .../advice` |
| 完成 | `type=completed` 後關閉串流；快照與 REST `GET .../advice` 一致 |
| 查價未接上 | 不得在 `saving_text` 等欄假裝有官網現價（units Q3=A 行為約束） |

---

## 契約所有權與變更政策

1. **Owner 對規格有最終解釋權**；Consumer 若需破壞性變更，開 RFC／PR 由 Owner 合併。
2. **加法變更安全**：Consumer 必須忽略未知欄位（JSON／SSE 皆然）。
3. **破壞性變更**：僅允許在新主版本路徑（`/api/cost/v2`）；v1 與 v2 重疊 **一個 Bolt 週期**，期間 SPA 切到 v2 後才撤 v1。
4. **C1 shared-schema** 無 URL 版號；破壞性變更（例如刪欄、改枚舉語義）須 U1＋U2 同 Bolt 合併。
5. **落地**：construction 將 C2 寫入 `openapi.json` 並 `npm run gen:types`；C3 事件形狀以本檔與前端訂閱程式為準，建議在 OpenAPI 用 `text/event-stream` 補充描述以免 drift 漏網。

---

## Open Questions

| Contract | Question | Blocks |
|---|---|---|
| C2 | 雲別 override 要以平行欄位陣列還是 `files[i].cloud` 複合 part 傳遞？本摘要暫用 `cloud_overrides` JSON 字串 | U2、U8 |
| C3 | 逾時後 `Advice.status` 要標 `failed` 還是另設 `timed_out`？ | U7、U9 |
| C2／C3 | SSE 路徑是否也要出現在 `openapi.json`（部分工具對 stream 支援差）？ | U3（OpenAPI 重產）、U9 |
| — | U7→U2 授權函式簽章（F1=B 排除） | U7 functional-design |

## Assumptions

- **A-CD1**：`/api/cost/v1` 與舊 `/api/cost/diagrams/...` 在 U3＋U8 同批部署前不得並存於同一對外行為——舊路徑隨 U3 刪除，新路徑隨 U2／U8 上線。
- **A-CD2**：機械檢查只出現在 C2 讀取回應，不另開 endpoint。
- **A-CD3**：分享採「完整名單覆寫」而非逐筆 POST／DELETE，減少中間態（可在 functional-design 改為增量，屬加法或小破壞，視實作）。

## Review

**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1
**Date:** 2026-09-18T10:38:01Z
**Verdict:** READY

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `contract-summary.md > C2 components.schemas.EstimateSetSummary` | `privacy` 未列入 `required`，但每個 `EstimateSet` 必有隱私狀態（private / shared），缺席時 U8 隱私徽章邏輯無明確 fallback。同層 `clouds[]` 物件的 `cloud` 欄（雲別識別符）亦未列入物件 required，但無 `cloud` 的 cloud entry 在語意上無意義。 | 在 `EstimateSetSummary` 的 `required` 清單補入 `privacy`；在 `clouds[]` 物件補 `required: [cloud, line_count, unparsed_count]`，或明確記錄缺席時的預設語意。 | New |
| R-02 | Minor | `contract-summary.md > C2 components.schemas.EstimateSetSummary > advice_status` | `advice_status` 同時設定 `nullable: true` 與 `enum: [none, generating, completed, failed]`，造成「尚無建議」可由 `null` 或 `"none"` 兩種形式表示，U8／U9 需判斷兩者語意是否等價。 | 擇一保留：若以 `"none"` 表示無建議，移除 `nullable: true`；若以 `null` 表示，移除 `"none"` 枚舉值，並在描述中說明兩者不並存。 | New |
| R-03 | Minor | `contract-summary.md > C3 components.schemas.AdviceSnapshotInline` | C3 `AdviceSnapshotInline`（`type=completed` 時內嵌）缺少 `started_at` 與 `completed_at`，而 C2 REST `AdviceSnapshot` 含這兩欄。U9 若需在 SSE 完成事件後顯示產生耗時，須另打 `GET .../advice` REST 端點取完整快照，文件未明言此設計意圖。 | 於 `AdviceSnapshotInline` 補入 `started_at`/`completed_at`，**或**在 C3 串流行為表中明確記錄「完整時間戳須由 REST 快照取得，inline 快照不含」，讓 U9 開發者無需猜測。 | New |
| R-04 | Minor | `contract-summary.md > C3 串流行為 > Endpoint` 與 OQ 第三條 | SSE 路徑 `GET /api/cost/v1/sets/{set_id}/advice/stream` 僅出現在 C3 AsyncAPI，未納入 C2 OpenAPI。CI 的 `npm run gen:types`（FR9.10）不會產生此路徑的 TypeScript 型別，U9 須手工維護 C3 payload 型別定義，與 C5「單一 `openapi.json` 為 API 契約真實來源」的精神有落差。OQ 已知悉但無解法時程。 | 在 construction 前決議 OQ-CD3（SSE 是否進 `openapi.json`）；若不納入，則在 contract-summary 明文記錄「U9 以 C3 AsyncAPI 為 SSE 型別定義唯一來源，不依賴 `gen:types`」，讓 U3（OpenAPI 重產）不必為此預留插槽。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 手動交叉比對（C1 × C2） | PASS | C1 `ParseResult` / `LineItem` 欄位與 C2 `LineItemView` / `CloudEstimateView` 對應完整；`parseStatus` 枚舉一致；`MechanicalCheckResult` 欄位與 `MechanicalCheckView` 對應正確，`totalReconciled` 巢狀結構匹配。 |
| 手動交叉比對（C2 × C3） | PASS（含一項附注） | `AdviceSnapshot`（C2 REST）與 `AdviceSnapshotInline`（C3 SSE）主體欄位一致；差異在 `started_at`/`completed_at` 缺席（R-03）及 C3 status 不含 `generating`（符合語意：SSE completed 事件只在建議完成或失敗時觸發）。 |
| 整合點覆蓋驗證（× unit-of-work-dependency.md） | PASS | 整合點表六條邊均已按 Q7=A / F1=B 定案：C1 覆蓋 U1→U2、C2 覆蓋 U2→U8/U7 HTTP、C3 覆蓋 U7→U9 SSE；U2→U7 觸發（async）、U7→U2 授權查詢（F1=B）、U5→U7 查價（Q7 排除）三條未正式化邊均有明確附註，無遺漏。 |
| FR 矛盾檢查（FR1.3/1.4/1.5、FR4.1-4.5、FR5.2、FR6.3/6.4/6.6） | PASS | 上傳限制（5MB×3 → 413）、魔數 400、雲別 ambiguous 400、機械檢查欄位分離、advice_status 四態、history GET、delete 204、shares PUT 均與需求一致；FR5.2「產生中 vs 本期未提供」由 `advice_status` + `unavailable_reasons` 共同承載，契約層足以區分。 |

### Summary

三份契約覆蓋了 units 整合點表所有應正式化的邊界，C1/C2/C3 schema 橫向一致，FR 矛盾項為零，四項發現均屬 Minor。最值得在 construction 前解決的是 R-04（SSE 路徑的 `openapi.json` 決議），因它直接影響 U9 的型別工具鏈；R-02 的雙重「無建議」表示法則會在 U8/U9 if-else 中製造混淆。
