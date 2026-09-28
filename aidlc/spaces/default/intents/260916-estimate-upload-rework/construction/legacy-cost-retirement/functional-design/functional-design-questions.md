# Functional Design 問答：U3 `legacy-cost-retirement`

本 Unit 是 **退場／刪除**（service）：拆掉舊「架構圖自動估價」路徑，**不交付新產品能力**。依 bolt-plan，**須與 U8（新估價工作區 UI）同批部署**；單獨合併會讓 `/cost` 中間一次不可用。

本站釘**退場邊界與順序**，不寫實作碼。

## Sources

- **[S1]** U3：`unit-of-work.md` — FR9.1–9.3、9.7–9.11；不含 FR9.4／9.5／9.6（U5／U1）
- **[S2]** FR9；contract A-CD1（舊 `/api/cost/diagrams/...` 與新 `/api/cost/v1` 不得錯誤並存）
- **[S3]** bolt-plan B5 = **U3＋U8** 同批；B4（U2 上傳 API）在價值路徑上通常先於本 Bolt
- **[S4]** 現況：`cost_router` 仍掛 `/api/cost`；`CostPage.tsx` 仍打 diagrams 舊 API；U1／U4／U6 程式已落地但**上傳 API／新頁尚未做**

---

## Q1 本 Unit 與 U8 的交付節奏（部署約束）

- **A.** **設計與實作可先做 U3，但合併／部署閘門必須 U8 同 PR（或同 squash 批次）**——與 Q6=A／B5 一致（建議）
- **B.** U3 可先合進 `ut`（舊 API 先刪），U8 稍後再上——接受短暫無成本頁
- **C.** 本 stage 只出退場清單，**程式變更整包延到 U8 開做時再動**
- **X.** Other (please specify)

[Answer]: A — 設計／實作可先做；合併／部署須與 U8 同批
---

## Q2 舊 HTTP 面退場範圍（FR9.1）

- **A.** 移除 `cost_router` 掛載與全部 diagrams／budget／calculator-export 等 **舊** operations；**新** `/api/cost/v1`（U2）不在本 Unit 新增也不預留 stub
- **B.** 先把舊 operations 改成 410 Gone／固定錯誤訊息，實體刪除延後
- **C.** 只刪 router 註冊，保留 `cost_service`／agent 模組檔案在 repo（半退場）
- **X.** Other (please specify)

[Answer]: A — 移除舊 cost_router／operations；不新增 v1 stub
---

## Q3 四張舊表（FR9.2）與 staging 既有資料

- **A.** DDL 雙軌同步刪除（`database.py::_ensure_cost_schema`＋`schema_rbac.sql`）＋更新 `DEPLOY.md`；staging **直接 drop**（FE-5／OQ5：不保留歷史）（建議）
- **B.** 同上，但 deployment-execution 前必須先備份 dump
- **C.** 表改名 archive_* 保留一季再刪
- **X.** Other (please specify)

[Answer]: C — 四張舊表改名 `archive_*`，保留一季後再刪
---

## Q4 Playwright Calculator 與 `playwright` 相依（FR9.3）

- **A.** 刪除 `azure_calculator_runner`／`gcp_calculator_*`／相關 spike，並從 `requirements.txt` **移除 Python `playwright` 相依**（前端 e2e 的 Playwright 不動）
- **B.** 刪模組但保留 `playwright` 套件「以備不時之需」
- **C.** 僅標記 deprecated，本 Unit 不刪檔
- **X.** Other (please specify)

[Answer]: A — 刪 Calculator 模組／spike；移除 Python playwright 相依
---

## Q5 必須保留給 U5 的最小集（不得誤刪）

- **A.** 明確排除清單寫進 rules：`pricing_sdk`、`pricing_client`、`config`＋YAML、`pricing_units`／`pricing_offer_parser`／`pricing_gcp`／`pricing_azure`／`pricing_query_parser`、`boto3`、相關 unittest（FR9.4／9.5）
- **B.** 本 Unit 可刪任何 `backend/cost/*`，U5 再重建
- **C.** 只保留 `pricing_sdk.py`，其餘查價模組可刪
- **X.** Other (please specify)

[Answer]: A — 排除清單寫進 rules（FR9.4／9.5 最小存活集）
---

## Q6 前端 e2e 與 Cost 頁（FR9.9）在「U8 尚未完成」時怎麼處理

- **A.** 本 Unit **刪除或改寫**依賴舊 `/api/cost/diagrams` 與 stub `$86.40` 的 e2e 段落；若 U8 未就緒，改為 skip／移除該段並在 U8 補新 e2e（建議，避免 CI 紅）
- **B.** 保留舊 e2e，靠 `COST_PRICING_STUB` 繼續綠——與退場矛盾
- **C.** 本 Unit 不動 e2e，留給 U8 一次改
- **X.** Other (please specify)

[Answer]: A — 刪／改舊 cost e2e；U8 未就緒則移除或 skip，由 U8 補新案
---

## Consolidated Summary Confirmation

**U3 `legacy-cost-retirement` 行為定案**

| 項 | 定案 |
|---|---|
| 與 U8 | 設計／實作可先；**合併／部署須同批**（Q1=A） |
| HTTP | 移除舊 `cost_router`／diagrams 等 operations；不新增 v1 stub（Q2=A） |
| 四張表 | **改名 `archive_*`，保留一季再刪**（Q3=C；偏離「直接 drop」建議） |
| Playwright 估價 | 刪模組／spike；移除 Python `playwright`（Q4=A） |
| 保留給 U5 | pricing_sdk／client／config／YAML 等排除清單（Q5=A） |
| e2e | 刪／改舊 cost 段；U8 補新（Q6=A） |

**將產出**：entities.md（待退場／待保留資產）、rules.md、functional-spec.md、traceability.json。

**後果**：code-gen 須實作 rename→保留期→刪除的表生命週期（或至少 rename＋文件化一季後刪）；不得誤刪 U5 最小集；合進 `ut`／部署時綁 U8。

[Answer]: Looks correct

請回覆 **Looks correct**（或指出要改的地方）。
