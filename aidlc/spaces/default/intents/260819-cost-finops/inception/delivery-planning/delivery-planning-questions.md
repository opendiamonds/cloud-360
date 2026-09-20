# Delivery Planning — 釐清問題

> Stage: delivery-planning（Inception 2.8，inline）· Depth: Standard · Scope: mvp
> Intent: `260819-cost-finops`
> Lead: aidlc-delivery-agent
> 作答：在每題 `[Answer]:` 後填選項字母。
> **成本揭露**：本題組共 5 題。答完產出 Bolt 計畫。2.7 已定拓樸；本站選**經濟路徑**。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 五 unit、兩個根、api 依賴兩者、ui 依賴 api、banner 依賴 api+ui | `unit-of-work-dependency.md` |
| 第一段可單獨驗收；第二段才有預算／橫幅 | `stories.md`、ADR-C1-08 |
| API／UI 契約 = OpenAPI + generated `api.d.ts` | UG Q5=A |
| 全部 embedded；merge `ut` 即部署 staging | ADR-C1-01、`org.md`／`project.md` Deployment |
| **不跑 walking-skeleton 儀式**（第一 Bolt 仍是普通 Construction Bolt，無額外 skeleton gate） | `team.md` Walking Skeleton Q1 定案 A；本 intent 人工確認 |
| 1.5 team-formation SKIP → 全部 Bolt 由 `aidlc-developer-agent` 執行 | mvp scope |
| Operation 整段 SKIP | mvp |
| 公開價目可 stub；URL 留 infrastructure-design（OQ-3） | `requirements.md` |
| 超支 LLM 建議另 intent | refined-mockups §13 |

mvp scope 檔寫 `skeleton: on`，但 practices-discovery 已對**本 intent** 定 `skeleton: off`。本站不重問、也不把 Bolt 1 標成 walking-skeleton 儀式。

## Sources

- [req] `../requirements-analysis/requirements.md`
- [stories] `../user-stories/stories.md`
- [mockups] `../refined-mockups/mockups.md`
- [components] `../application-design/components.md`
- [uow] `../units-generation/unit-of-work.md`
- [dep] `../units-generation/unit-of-work-dependency.md`
- [map] `../units-generation/unit-of-work-story-map.md`
- [tp] `../practices-discovery/team-practices.md`

---

## Q1. 排序啟發法？

> 2.8 選路徑。DAG 允許先做 schema 或 calculator，但不表示那是該先**部署**的。

A. **依產品兩段增量（建議）**：Bolt 1 = 第一段 e2e（四 unit 捆在一起，因為單拆 schema／calculator 湊不出可展示的信心假說，且 OpenAPI 與 `cost-ui` 必須同批部署）；Bolt 2 = `cost-budget-banner`。啟發法：value-first（故事第一段可單獨上線）＋ risk-reduction（種子 no-op、擷取、pricing Port 放進會被使用者碰到的第一個部署）。**不是** walking-skeleton 儀式。  
B. **一 unit 一 Bolt**（五個部署）。代價：schema-only 或 calculator-only 的 merge 對使用者不可見（違反 `delivery-planning:c3`）；api 若先於 ui merge 會讓 staging 出現無消費者的 `/api/cost*`（`delivery-planning:c6`）。  
C. **單一 Bolt 包五 unit**。代價：第一段無法單獨合 Construction 閘；第二段缺陷會擋住第一段上線。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. **依產品兩段增量（建議）**

---

## Q2. 要不要正式打 WSJF 分數？

A. **不打表（建議）**：只有兩個有意義的 Bolt，故事已寫 C1-6／C1-7 依賴第一段總額。排序即增量序。  
B. **打 WSJF 表**（價值／時間／風險 ÷ 規模）。兩列分數幾乎必然 Bolt 1 > Bolt 2，產出成本高、決策不變。  
C. **風險分最高的 unit 單獨先做**（例如只先合 calculator PBT）。代價：同 Q1-B，無畫面假說。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. **不打表（建議）**

---

## Q3. Construction 設計文件的迭代軸？

> 引擎預設 `stage-major`：所有 unit 先跑完 functional-design，再一起 nfr-requirements…。`unit-major` 則是一個 unit 的四份設計寫完再換下一個。

A. **`stage-major`（建議／預設）**：Bolt 1 的四 unit 共享同一組 HTTP／OpenAPI 契約，適合一次定 `cost-api` 形狀再讓各 unit 的 FD 對齊。不呼叫 `set-construction-iteration`。  
B. **`unit-major`**：schema → calculator → api → ui 各把 3.1–3.4 走完再換。適合「每個 unit 設計必須自洽再往下」，但會讓 OpenAPI 形狀在 api 的 FD 才出現，前面 spec／library 的 FD 容易空轉。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **`stage-major`（建議／預設）**

---

## Q4. Bolt 能不能平行跑 Construction？

A. **嚴格序列（建議）**：Bolt 2 的 yaml 邊依賴 `cost-api` 與 `cost-ui`，且 deploy-on-merge 下不能在第一段未進 `ut` 時把橫幅合上去。  
B. **嘗試平行**：在 stub 頁上先做橫幅。違反 ADR-C1-08（第一段不得掛橫幅 DOM）與 DAG。  
C. Not yet defined  
X. Other (please specify)

[Answer]: A. **嚴格序列（建議）**

---

## Q5. 外部閘與最早要打掉的風險？

A. **無外部團隊閘**。外網價目：Bolt 1 用 `pricing_client` stub 讓 TestClient／e2e 綠；真實 URL 在 infrastructure-design（OQ-3）補，失敗路徑已有 `PriceMiss`／`PriceUnsupported`。最早打掉的風險：`force=False` 種子 no-op、extractor 誤用 `parse_diagram_summary`、無區域仍打價目。**（建議）**  
B. **Bolt 1 必須打到真實 AWS／GCP 公開價才算完成**。代價：OQ-3 未決時 Bolt 1 無法合閘；NFR-4 的 5 秒在 stub 下仍可測契約。  
C. **等 FinOps 人工核准價目表才開 Bolt 1**。超出本輪（無核准流）。  
D. Not yet defined  
X. Other (please specify)

[Answer]: A. **無外部團隊閘**。Bolt 1 用 stub；真實 URL 留 infrastructure-design。
