# Functional Design 問答：U1 `u1-iac-api`

> Stage: functional-design · Unit: `u1-iac-api`（service）· Bolt B1  
> 本 Unit＝後端 Session＋三核心＋`/api/iac`；**不含** React UI（屬 U2）。  
> 設計層：實體／規則／工作流；禁止完整實作碼。  
> **成本揭露**：本題組共 5 題。答完確認後產出 entities／rules／functional-spec／traceability。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 同步 HTTP；能力動詞路徑；422＋`error.code`；403＝RBAC | [cd] Q1–Q2 |
| zip 二進位下載；無 URL 版號；執行 POST 不自動重試 | [cd] Q3–Q5 |
| 行程內產物；切圖清空；D3 需 D1∧D2 成功報告 | [dd]／[stories] |
| B1 DoD 必關契約 R-01／R-02 | [dp] Q4=A |
| 禁 apply／雲端 SM 寫入；PBT 三核心；可 stub agent | [req]／[ug] |

## Sources

- [ug] `../../inception/units-generation/unit-of-work.md`
- [cd] `../../inception/contract-design/contract-summary.md`
- [dd] `../../inception/domain-design/components.md`
- [stories] `../../inception/user-stories/stories.md`
- [dp] `../../inception/delivery-planning/bolt-plan.md`

---

## Q1. 模組落點（後端套件形狀）？

A. **新建 `backend/iac/` 套件**：`session`／`generator`／`scanner`／`redactor`／`router`（或等價拆分），由 `main.py` 掛載 prefix `/api/iac`；**不**塞進 `agent_router`／`user_router`。**（建議）**
B. 全部塞進既有 `backend/services/` 單一大檔。
C. 僅 router 在 services；核心放 `backend/iac/`。
X. Other (please specify)

[Answer]: A
---

## Q2. 關閉契約 R-02：`diagram_id` 規則？

A. **`POST /scan` 與 `/secrets/rewrite` 的 `diagram_id` 必填**（與 `GET /session`／`/download` 對稱）；缺則 422 `invalid_diagram` 或新增 `missing_diagram_id`。**（建議）**
B. 可省略：以「該使用者最近活躍 diagram_id」解析；無法解析 → 新 error.code。
X. Other (please specify)

[Answer]: A
---

## Q3. 關閉契約 R-01：`GET /download` 的 story action？

A. **要求 D1 `edit`**（與「不得以僅 view 放行執行語意」一致；下載視為帶走產物）。**（建議）**
B. 要求 D1 `view` 即可下載（僅擋完全無權）。
C. 要求 D3 `edit`（改寫後才准下載）。代價：未改寫亦不可下載，過嚴。
X. Other (please specify)

[Answer]: A
---

## Q4. US6.1「第一個落地的 D HTTP」選哪支做成對 403／2xx？

A. **`POST /api/iac/generate`（D1 edit）** 為成對測試錨點；其餘執行路徑同模式跟進。**（建議）** 最早可測、前置最少。
B. `POST /scan`（需先有草稿 stub）。
C. `POST /secrets/rewrite`（前置最重）。
X. Other (please specify)

[Answer]: A
---

## Q5. 行程內產物存放抽象？

A. **行程級 in-memory store**（process 字典／模組單例），鍵 `(user_id, diagram_id)`；重載即失；單測可注入 fake store。**（建議）** 對齊 ADR-002。
B. 本輪就落 Postgres 新表（偏離 ADR-002）。
C. 純請求作用域（無跨請求 session）——無法支援 GET session／多步閘。
X. Other (please specify)

[Answer]: A
---


## Consolidated Summary Confirmation

1. **Q1=A** — `backend/iac/` 套件；`main.py` 掛 `/api/iac`；不進 agent_router／user_router。
2. **Q2=A** — `/scan`／`/secrets/rewrite` 的 `diagram_id` **必填**；缺 → 422（關 R-02）。
3. **Q3=A** — `GET /download` 需 **D1 `edit`**（關 R-01）。
4. **Q4=A** — US6.1 成對測試錨點＝`POST /generate`。
5. **Q5=A** — 行程級 in-memory store，鍵 `(user_id, diagram_id)`。

**將產出**：entities.md、rules.md、functional-spec.md、traceability.json（無 frontend-components）。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
