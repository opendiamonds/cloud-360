# NFR Requirements 問答：U2 `u2-iac-ui`

> Stage: nfr-requirements · Unit: `u2-iac-ui`（ui）· Bolt B2  
> 產物僅：performance／security／tech-stack／traceability（無 scale／reliability／observability 檔）。  
> **成本揭露**：本題組共 5 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| Workspace 內頁；busy／切圖忽略 in-flight；`error.code` 分支；MSW stub | [fd] Q1–Q4=A |
| HIGH／CRITICAL 下載 modal；無 apply UI；無權 disabled | [stories]／[rm] |
| U1：D1 p95＜60s／硬逾時 90s；非 LLM p95＜2s | U1 NFR Q1–Q2=A |
| NFR5 a11y 歸本 unit；NFR2／PBT／Checkov 歸 U1 | [req]；U1 NFR |
| Tech 基底：React／Vite／Tailwind／Playwright | [codekb]／`project.md` |

## Sources

- [fd] `../functional-design/functional-spec.md`、`frontend-components.md`
- [req] `../../../inception/requirements-analysis/requirements.md`（NFR5／NFR7）
- [rm] `../../../inception/refined-mockups/mockups.md`
- U1 NFR（只讀延遲上限，不複製服務端義務）

---

## Q1. D1 長等待的 UI 表現（對齊 U1 90s）？

> 後端可到 90s；UI 須避免「假死」與過早放棄。

A. **busy＋`iac-agent-status` 可見進行中**；前端 fetch／Abort 對齊後端硬逾時（≥90s 或略寬）；逾時／失敗顯示可重試＋`error.code`；**不**另做假進度條百分比。**（建議）**
B. 加確定性假進度條（與真實 LLM 無關）。
C. 縮短前端超時至 30s（會比後端先失敗）。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 客戶端保密與錯誤面？

A. **不得**把 HCL／改寫前後明文、完整 response body、stack 打进 console／toast；只顯示對照後的中文短語＋`error.code`；下載用瀏覽器 blob，不經可快取的明文 URL query。**（建議）**
B. 開發模式允許 console 印完整 JSON（含 HCL）。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. 無障礙底線（NFR5）？

A. **桌面優先 WCAG 2.1 AA 目標**：步驟／findings／下載／確認 modal 可鍵盤操作；嚴重度**不只靠顏色**（文字標籤）；確認 modal 有 dialog 語意、Esc／取消、初始 focus；關鍵控件有既定 test-id。**（建議）**
B. 僅視覺完成，a11y 延後。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. 前端技術棧？

A. **沿用 React／Vite／Tailwind／既有 Workspace 語彙＋Playwright**；允許 MSW／stub；**不**新引入 UI component library。**（建議）**
B. 引入新 component library（需點名）。
X. Other (please specify)

[Answer]:Ａ

---

## Q5. UI 層可觀測性？

> 服務端 log 屬 U1；此題只定瀏覽器側。

A. **以 UI 狀態＋`error.code` 為主**；不強制瀏覽器 RUM／前端 metrics SDK。**（建議）**
B. 接入既有前端錯誤追蹤（若有）並 scrub 密文。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — busy＋status；前端逾時 ≥90s；失敗可重試＋error.code；無假進度％。
2. **Q2=A** — 不把 HCL／密文／完整 body 打进 console／toast；blob 下載。
3. **Q3=A** — 鍵盤可操作；嚴重度有文字；modal dialog／Esc／focus；test-id。
4. **Q4=A** — 既有 React／Vite／Tailwind／Playwright＋MSW；不新引入 UI library。
5. **Q5=A** — UI 狀態＋error.code；不強制 RUM／metrics SDK。

**將產出**：performance／security／tech-stack-decisions／traceability。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
