# Units Generation — 釐清問題

> Stage: units-generation（Inception，inline）· Depth: Standard · Scope: feature  
> Intent: `261105-d-iac-generation`（Story D）  
> 本站只定 **依賴拓樸（DAG）**，不定實作／出貨順序（那是 Delivery Planning）。  
> **成本揭露**：本題組共 5 題＋計畫確認。答完並 Approve Plan 後產出 unit-of-work 三件組＋traceability。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 五 Domain 元件：Ui、Session、Generator、Scanner、Redactor | [dd] Q1／Q3／Q6b=A |
| 產物行程內；同步 HTTP；圖走公開 API；`backend/iac/` | [dd] ADR-002–005／[tp] |
| Walking skeleton：**off**（本 intent） | [tp] |
| 不另開獨立雲端服務代 apply | [req]／[stories] |

## Sources

- [dd] `../domain-design/components.md`、`decisions.md`
- [req] `../requirements-analysis/requirements.md`
- [stories] `../user-stories/stories.md`
- [tp] `../practices-discovery/team-practices.md`
- [kb] 現況為單一 FastAPI＋Vite 部署（staging compose）

---

## Q1. Unit 邊界用什麼策略切？

> Domain 元件 ≠ 可獨立出貨的 Unit。Brownfield 已是單後端＋單前端進程。

A. **依部署面**：`iac-api`（service：Session＋三核心＋`/api/iac`）＋`iac-ui`（ui：`IacWorkspaceUi`）。**（建議）** 對齊現有 compose；核心仍是目錄模組但同一 service unit。
B. **依 Domain 元件**：五個 unit（ui／session／generator／scanner／redactor）。代價：多數無法獨立部署，DAG 吵、Construction 目錄碎。
C. **依故事垂直切片**：每組 US（選圖、D1、D2、D3、下載）一個 unit。代價：跨步閘與共用 Session 會交叉依賴。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. 三個決定性核心要不要拆成可平行的 library units？

> Generator／Scanner／Redactor 互不直連（[dd]），理論上可平行開發；但仍掛進同一 FastAPI 進程。

A. **不拆**：三核心＋Session 同屬 `iac-api` service unit；平行只發生在 unit **內** 的檔案／PR 分工。**（建議）** 少目錄、少跨 unit 契約，符合「同進程」。
B. **拆三個 `library` units**（`iac-generator`／`iac-scanner`／`iac-redactor`），`iac-api` `depends_on` 它們；`iac-ui` 只依 `iac-api`。代價：多三個 Construction 目錄與 story-map 列，換可宣告的平行拓樸。
C. **只拆一個 `iac-cores` library**（三核心同庫），`iac-api` 依它；Ui 另 unit。折衷。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. OpenAPI／契約要不要獨立 `spec` unit？

> 第一個 D HTTP 需 OpenAPI 漂移閘與 TestClient；contract-design 仍會做契約細化。

A. **不獨立**：OpenAPI 變更義務掛在 `iac-api` service unit 內（與現有後端契約習慣一致）。**（建議）**
B. **獨立 `iac-openapi` spec unit**，`iac-api`／`iac-ui` 都 depends_on 它。代價：多一個 unit；利於契約先凍。
C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q4. 部署模型（拓樸語意，非出貨順序）？

> staging 現況：同一 host 上 backend／frontend 容器。Domain ADR 未要求新微服務。

A. **Embedded**：IaC 程式進既有 backend／frontend 映像與 compose 服務；無新 deployable。Unit 的 deployment=embedded／shared。**（建議）**
B. **Hybrid**：後端仍 embedded；前端 IaC 可選獨立 chunk／lazy route，但仍同一 Vite app。
C. **Independent**：新 `iac-service` 進程／容器。代價：超出本輪 practices／範圍，需新 ADR。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5. 無關單元之間是否允許「可平行」邊（拓樸上無依賴）？

> 本站可標示平行開發機會；**不**決定誰先做。若 Q1=A 且 Q2=A，實際可平行對多半是 api↔ui（ui 可對 stub／契約）。

A. **允許**：DAG 上無依賴的 unit 標為可平行（例如 api 與 ui 在契約穩定後可平行）。**（建議）**
B. **強制串列拓樸**：即使可獨立也畫成 ui depends_on api（僅表達「需契約」）。代價：縮小 delivery-planning 的排序自由度。
C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Plan Approval（分解計畫確認）

依 Q1–Q5=A 的分解計畫：

- **Units（2）**
  - `U1`／`u1-iac-api` — **service**：`IacWorkspaceSession`＋三核心＋`/api/iac`＋OpenAPI 義務；deployment=embedded（既有 backend 映像）
  - `U2`／`u2-iac-ui` — **ui**：`IacWorkspaceUi`；deployment=embedded（既有 frontend 映像）
- **DAG**：兩 unit **互不 depends_on**（可平行拓樸）；整合點為 `/api/iac` 同步 JSON 契約（於 api unit 內維護 OpenAPI）
- **不拆** library／spec unit；不定出貨順序（交 Delivery Planning）
- **Kinds**：service + ui

Does this decomposition plan look correct?

- Approve Plan
- Revise Plan

[Answer]: Approve Plan

---

## Consolidated Summary Confirmation

1. **Q1=A** — 依部署面兩 unit：`iac-api`（service）＋`iac-ui`（ui）。
2. **Q2=A** — 三核心不拆 library；同屬 `iac-api`。
3. **Q3=A** — OpenAPI 義務掛在 `iac-api`，不獨立 spec unit。
4. **Q4=A** — Embedded 進既有 backend／frontend 映像。
5. **Q5=A** — DAG 允許可平行（兩 unit 互不 depends_on）。
6. **Plan** — U1 `u1-iac-api`／U2 `u2-iac-ui`；整合點 `/api/iac`；不定出貨順序。

Does this all look correct before I generate the artifacts?

- Looks correct
- Request changes

[Answer]: Looks correct
