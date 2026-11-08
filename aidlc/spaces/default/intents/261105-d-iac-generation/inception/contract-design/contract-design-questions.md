# Contract Design — 釐清問題

> Stage: contract-design（Inception，inline）· Depth: Standard · Scope: feature  
> Intent: `261105-d-iac-generation`（Story D）  
> 契約＝跨邊界正式約定。本輪主邊界：`u1-iac-api`（provider）↔ `u2-iac-ui`（consumer）的 `/api/iac`；另含對既有圖 API／RBAC 的依賴面。  
> **成本揭露**：本題組共 5 題。答完並確認摘要後產出 `contract-summary.md`（含內嵌 OpenAPI 草案）。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 同步 HTTP JSON；非 SSE／Job（本輪） | [dd] ADR-003 |
| 獨立 `/api/iac/...`；不塞 `agent_router`／`user_router` | [tp]／[stories] |
| 執行 D3 需 D1∧D2 成功報告；無草稿／無權 → 4xx／403 | [stories] US4.1／US6.1 |
| OpenAPI 義務掛 `u1-iac-api` | [ug] Q3=A |
| 兩 unit 拓樸無 depends_on，但仍有整合點 `/api/iac` | [ug] Q5=A |

## Sources

- [ug] `../units-generation/unit-of-work.md`、`unit-of-work-dependency.md`
- [dd] `../domain-design/components.md`、`decisions.md`
- [req] `../requirements-analysis/requirements.md`
- [stories] `../user-stories/stories.md`

---

## Q1. `/api/iac` 資源命名風格？

> 需一組穩定 path，供 OpenAPI 與 UI／TestClient 共用。檔名禁 `d1_*`，但 URL 可用能力語彙。

A. **能力動詞資源**：`POST /api/iac/generate`、`POST /api/iac/scan`、`POST /api/iac/secrets/rewrite`、`GET /api/iac/session`（或 `/draft`）、`GET /api/iac/download`（zip）。**（建議）** 對齊產品語彙，短且可測。
B. **REST 名詞巢狀**：`/api/iac/drafts`、`/api/iac/drafts/{id}/scans`、`.../rewrites`。代價：行程內無強持久 id 時 REST 味重、實作仍偏 RPC。
C. **全部掛單一 `POST /api/iac/actions`＋action 欄位**。代價：OpenAPI 難表達各 action 的 schema。
D. Not yet defined
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 閘失敗（無草稿／無 D2 報告）用哪個 4xx？

> US4.1 要求執行 API 4xx 且 reason 可區分。開發者建議 409 或 422。

A. **422 Unprocessable Entity**＋穩定 `error.code`（如 `missing_draft`／`missing_scan_report`）；403 專留給 RBAC。**（建議）** 與「請求語意不滿足前置」一致。
B. **409 Conflict**＋同上 `error.code`。代價：語意偏「狀態衝突」，亦可；需全站一致。
C. **400** 統一，只靠 message 字串區分。代價：TestClient／UI 難穩健分支。
D. Not yet defined
X. Other (please specify)

[Answer]:Ａ

---

## Q3. 下載 zip 的傳輸契約？

> US5.1 要 zip；HIGH／CRITICAL 確認在 **UI**（非 API 閘）。

A. **`GET /api/iac/download`（或 POST）回 `application/zip` 二進位**；檔名用 `Content-Disposition`。UI 負責先弹 modal。**（建議）**
B. **JSON 內 base64 zip**。代價：體積膨脹、記憶體差。
C. **預簽 URL／物件儲存**。代價：本輪無物件儲存範圍。
D. Not yet defined
X. Other (please specify)

[Answer]:Ａ

---

## Q4. 契約版本與破壞性變更政策（本 intent）？

> 第一版即進同一 monorepo；UI 與 API 同 PR 常一起改。

A. **無 URL 版號**（`/api/iac`）；破壞性變更須同 PR 更新 OpenAPI＋UI＋TestClient；additive 欄位消費者忽略未知欄。**（建議）** 對齊現有 `/api/cost` 習慣。
B. **`/api/iac/v1` 起版**；破壞性改 v2。代價：本輪雙路徑噪音。
C. Not yet defined
X. Other (please specify)

[Answer]:Ａ

---

## Q5. 逾時／重試誰負責？

> 同步長請求；閘道可能有上限。

A. **伺服器設明確超時／取消**；客戶端（UI）**不自動重試**執行類 POST（避免重複生成）；使用者按重試鈕才再送。下載 GET 可重試。**（建議）**
B. **UI 自動重試 1 次**執行 POST。代價：可能雙重產物。
C. **完全依反代預設**，契約不寫超時。代價：行為不可測。
D. Not yet defined
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — 能力動詞資源：`POST /api/iac/generate`、`/scan`、`/secrets/rewrite`；`GET /api/iac/session`（或 `/draft`）、`GET /api/iac/download`。
2. **Q2=A** — 閘失敗用 **422**＋穩定 `error.code`（如 `missing_draft`／`missing_scan_report`）；**403** 專留給 RBAC。
3. **Q3=A** — 下載回 `application/zip` 二進位＋`Content-Disposition`；HIGH／CRITICAL 確認留在 UI。
4. **Q4=A** — 無 URL 版號；破壞性變更同 PR 更新 OpenAPI＋UI＋TestClient；additive 欄位消費者忽略未知欄。
5. **Q5=A** — 伺服器設明確超時／取消；執行類 POST **不自動重試**（使用者按鈕才再送）；下載 GET 可重試。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
