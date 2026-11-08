# NFR Design 問答：U2 `u2-iac-ui`

> Stage: nfr-design · Unit: `u2-iac-ui`（ui）  
> 產物：performance／security／logical-components／traceability。  
> **成本揭露**：本題組共 4 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| busy≥90s；error.code；blob 下載；a11y AA 目標；既有 React＋MSW | [nfr-req] Q1–Q5 |
| Workspace 內頁；切圖忽略 in-flight；無 apply | [fd] |
| U1：bulkhead／Checkov／LRU／五後端元件 | U1 nfr-design |

## Sources

- [nfr-req] `../nfr-requirements/*`
- [fd] `../functional-design/functional-spec.md`、`frontend-components.md`
- U1 `../../u1-iac-api/nfr-design/logical-components.md`（整合點唯讀）

---

## Q1. 長請求 Abort／逾時設計？

A. **`AbortController` 對齊 ≥90s**；unmount／切圖 abort；忽略 stale 回應；按鈕 busy 至 settle。**（建議）**
B. 無 Abort，只靠 Promise 自然結束。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 錯誤與密文 UI 策略？

A. **集中 `error.code`→文案表**；toast／inline 只用短語；開發 build 亦禁止 dump HCL／密文到 console。**（建議）**
B. 集中表＋允許 `import.meta.env.DEV` 下 console.debug 完整 JSON（不含密文欄位需手動 scrub——風險高）。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. a11y 實作模式？

A. **確認 modal 用既有 dialog 模式**（focus trap／Esc／還原焦點到觸發鈕）；findings 嚴重度文字節點；步驟可 Tab。**（建議）**
B. 自研簡易 overlay，不保證 focus 還原。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. 前端邏輯元件邊界？

A. **`IacWorkspacePage`｜`IacApiClient`（含 MSW 可替換）｜`IacStepPanels`｜`IacDownloadConfirmModal`**；狀態在 Page／小型 store，不直操 U1 Store。**（建議）**
B. 單一巨頁無 client 抽象。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — AbortController ≥90s；切圖／unmount abort；忽略 stale。
2. **Q2=A** — error.code 文案表；禁止 console dump HCL／密文。
3. **Q3=A** — dialog focus trap／Esc／還原焦點；嚴重度文字。
4. **Q4=A** — WorkspacePage｜ApiClient｜StepPanels｜DownloadConfirmModal。

**將產出**：performance／security／logical-components／traceability。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
