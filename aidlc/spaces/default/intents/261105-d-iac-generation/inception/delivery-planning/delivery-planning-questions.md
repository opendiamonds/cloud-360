# Delivery Planning — 釐清問題

> Stage: delivery-planning（Inception capstone）· Depth: Standard · Scope: feature  
> Intent: `261105-d-iac-generation`（Story D）  
> **Bolt**＝一次 Construction 建置切片（可含一個或多個 Unit），結束時要有可驗證的完成定義與信心假設。  
> units 的 DAG 給拓樸；本站選**經濟路徑**（順序／打包）。  
> **成本揭露**：本題組共 5 題。答完並確認摘要後產出 bolt-plan／team-allocation／risk-and-sequencing-rationale／external-dependency-map。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 兩 unit：`u1-iac-api`（service）＋`u2-iac-ui`（ui）；DAG **無 depends_on**（可平行） | [ug] |
| 整合點 `/api/iac`；OpenAPI 義務掛 U1；契約 C1 已釘 | [cd] |
| 本 intent **`skeleton: off`**（不另開 walking-skeleton 儀式閘） | [tp]／team.md |
| Construction Bolt 分支 → squash-merge 進 `ut`；deploy-on-merge staging | [tp]／[org] |
| 禁 apply／寫入雲端 SM；行程內產物；三核心 PBT | [req]／[dd] |
| US7.1 Should／本輪不建 unit | [ug] story-map |

## Sources

- [ug] `../units-generation/unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`
- [cd] `../contract-design/contract-summary.md`（含 advisory R-01／R-02）
- [dd] `../domain-design/components.md`
- [stories] `../user-stories/stories.md`
- [tp] `../practices-discovery/team-practices.md`
- [ug-review] units R-02：US6.2 跨 unit 成功態宜同 Bolt 細化

---

## Q1. 排序啟發式？

> 兩 unit 拓樸可平行；經濟上仍要決定「先證明什麼」。

A. **風險／閘優先**：先落地 U1（`/api/iac`＋D1→D2→D3 閘＋US6.1 403／2xx＋PBT 核心），再開 U2 UI。**（建議）** 閘被繞過與無權非 403 是最高失敗模式；契約 R-01／R-02 也在 U1。
B. **價值／可見優先**：先 U2 殼與步驟 UI（mock／stub API），再補 U1。代價：易出現「有按鈕無真實閘」的部分交付窗口。
C. **混合薄切片**：單一 Bolt 同時含 U1＋U2 最小端到端（選圖→D1→下載），其餘後補。代價：與 `skeleton: off` 不衝突，但單 Bolt 變大、平行度降。
D. **正式 WSJF 打分**後排序。
X. Other (please specify)

[Answer]:Ａ

---

## Q2. Bolt 粒度與 US6.2／US5.1 打包？

> 跨 unit 故事：下載（US5.1）與多角色演示（US6.2）需兩端可觀察成功態。

A. **兩 Bolt**：B1＝U1；B2＝U2。US5.1／US6.2 的 U1 部分進 B1 DoD、U2 部分進 B2 DoD；B2 完成才算端到端演示就緒。**（建議）** 對齊 DAG 可平行拓樸，但仍用 DoD 串起整合。
B. **單一粗 Bolt**：U1＋U2 同 Bolt，端到端一次交付。代價：失去平行與較小 PR。
C. **三＋ Bolt**：再把 U1 拆成「generate／scan／rewrite」多 Bolt。代價：DAG 未要求；契約面重複開工。
X. Other (please specify)

[Answer]:Ａ

---

## Q3. 平行度？

> DAG 無邊；是否真的雙軌開工。

A. **允許 B1∥B2 平行**（兩 worktree／兩人），但 B2 對真實 `/api/iac` 的 e2e／Playwright 等 U1 至少有 D1 2xx stub 或合併後再跑。**（建議）** 對齊「可平行」拓樸。
B. **強制串行**：必先合入 U1 再開 U2。
C. **僅設計平行、建置串行**：FD 可平行，code-gen 串行 U1→U2。
X. Other (please specify)

[Answer]:Ａ

---

## Q4. 契約 advisory R-01／R-02 放哪裡關？

> R-01：`GET /download` 具名 story action；R-02：`/scan`／`/rewrite` 的 `diagram_id` 必填或明文解析。

A. **B1（U1）DoD 必關**：OpenAPI／router／TestClient 落地前釘死；不開新 contract-design 輪。**（建議）**
B. **另開契約修訂輪**後再進 Construction。
C. **延到 functional-design** 再釘，B1 DoD 不強制。
X. Other (please specify)

[Answer]:Ａ

---

## Q5. 最擔心哪件事（決定是否插入去風險工作）？

A. **D2→D3 閘被繞過**／舊 `report_id` 仍可用（含行程內狀態機）。**（建議主風險）**
B. LangGraph／OpenRouter 慢或不通（可 stub，但演示路徑脆）。
C. zip／HIGH modal／Playwright 找不到 test-id。
D. OpenAPI drift／RBAC 種子與 US6.1 成對測試漏寫。
X. Other (please specify)

[Answer]:Ａ

---

## Consolidated Summary Confirmation

1. **Q1=A** — 風險／閘優先：經濟上先證明 U1 閘與授權，再開 U2 可見面。
2. **Q2=A** — 兩 Bolt：B1＝U1、B2＝U2；US5.1／US6.2 分拆進各自 DoD，B2 完成才算端到端演示就緒。
3. **Q3=A** — 允許 B1∥B2 平行；B2 真實 e2e 等 U1 有 D1 2xx stub 或合併後再跑。
4. **Q4=A** — 契約 R-01／R-02 在 **B1 DoD 必關**（不另開 contract-design）。
5. **Q5=A** — 主風險＝D2→D3 閘／舊 `report_id`；B1 DoD 必須含閘繞過與作廢測。

**草案 Bolt 表**

| Bolt | Units | 平行 | DoD 要點 | 信心假設 |
|---|---|---|---|---|
| B1 | U1 `u1-iac-api` | ∥ B2 | `/api/iac`＋閘＋PBT；US6.1 成對 403／2xx；關 R-01／R-02；無 apply | 無法繞過 D3；無權＝403 |
| B2 | U2 `u2-iac-ui` | ∥ B1 | 步驟殼／選圖／findings／Secrets／下載 modal；消費契約；US6.2 UI 成功態 | 有權使用者可走完可見路徑 |

**不採用** walking-skeleton 儀式（`skeleton: off`）。Team-formation 未另組 mob → 預設 `aidlc-developer-agent`。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
