# Functional Design 問答：U2 `u2-iac-ui`

> Stage: functional-design · Unit: `u2-iac-ui`（ui）· Bolt B2  
> 本 Unit＝Workspace IaC 工作區前端；**不含**後端核心／OpenAPI 義務（屬 U1）。  
> UI unit 產出：functional-spec、frontend-components、traceability（無 entities／rules）。  
> **成本揭露**：本題組共 4 題。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 消費 `/api/iac`；HIGH／CRITICAL 下載確認在 UI | [cd]／[rm] |
| 步驟可自由點開；footer 下一步僅導覽 | [stories]／[rm] |
| 無權入口 disabled＋說明；無 apply | [stories] |
| 可∥B1；真實 e2e 等 U1 D1 2xx 或合併後 | [dp] Q3=A |

## Sources

- [rm] `../../inception/refined-mockups/mockups.md`、`interaction-spec.md`
- [cd] `../../inception/contract-design/contract-summary.md`（已關 R-01／R-02）
- [ug] story-map U2 群集
- U1 FD（只讀契約行為，不複製規則檔）

---

## Q1. 前端落點？

A. **既有 Workspace 路由下新頁／區段**（例如取代 Coming Soon），元件放 `frontend/src/` 對齊現有 Workspace／Cost 語彙與 test-id。**（建議）**
B. 全新頂層路由 `/iac` 獨立於 Workspace。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. 進行中請求與切圖？

A. **切圖先提示清空**；若有 in-flight POST，取消／忽略回寫（對齊 US1.3）；執行鈕 busy 防重送。**（建議）**
B. 禁止切圖直到請求結束。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. API 錯誤呈現？

A. **依 `error.code` 分支文案**（missing_draft／missing_scan_report 等）；403 顯示缺權說明；不依賴 message 字串唯一分支。**（建議）**
B. 只顯示後端 message 字串。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. 無後端時（平行開發）？

A. **允許 MSW／stub** 回契約形狀，供 Playwright 殼與步驟；合併後改打真實 `/api/iac`。**（建議）**
B. 禁止 stub；UI 必須等 U1 合入才開工。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — Workspace 路由下新頁／區段；對齊既有語彙與 test-id。
2. **Q2=A** — 切圖提示清空；in-flight 忽略回寫；執行鈕 busy。
3. **Q3=A** — 依 `error.code` 分支；403 缺權說明。
4. **Q4=A** — 允許 MSW／stub；合併後打真實 API。

**將產出**：functional-spec.md、frontend-components.md、traceability.json。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
