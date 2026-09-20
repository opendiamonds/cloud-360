# Practices Discovery — 釐清問題（re-run）

> Stage: practices-discovery（Inception 2.2）· Depth: Standard · Scope: mvp · Intent: `260819-cost-finops`
> 本輪為 **re-run**：`team.md` 五段已核可。只問草稿與三份盲評仍無法定案的項。
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。

## 已由既有 team.md／intent 定案、不重問

- Branch 命名 `<uploader>/<type>/<slug>`；commit／PR 中文 type（ADR-0010）
- 團隊預設 `skeleton: off`（逐案可開）
- 測試底線 A（RBAC allow/deny）／B（新 HTTP 用 TestClient）／C（前端資料形狀 e2e）／D 不引入前端單元測試框架
- Construction 與 Operations 連續、deploy-on-merge 至自有 staging
- 前端 lint 結構約束（Context 拆檔、資料抓取兩層、immutability）
- 新模組走三層；不趁機從 `user_router.py`／`collab_router.py` 抽 service
- 本 intent 本輪做 C1 TCO（含 cost calculator）；C2／C3 不做
- 只用公開免帳號官方價目；禁止 production credentials、Cost Explorer、客戶帳單（intent／feasibility 已鎖）
- ADR-0006：cost calculator 落地後必須有 property-based tests（無模組時為 N/A，不是豁免）

## Sources

- [team] `aidlc/spaces/default/memory/team.md` 五段
- [codekb] `aidlc/spaces/default/codekb/cloud/code-quality-assessment.md`
- [draft] `team-practices.md`／`discovered-rules.md`／`evidence.md`
- [spoke] `contributions/aidlc-quality-agent.md`、`aidlc-developer-agent.md`、`aidlc-devsecops-agent.md`

## Q1. 本 intent 要不要開 Walking Skeleton？

> 團隊預設 `skeleton: off`。team.md 允許「引入全新技術層」的大型 intent 逐案開啟。本輪會新增 calculator 模組、cost router、Cost 頁，但仍是 FastAPI／React／PostgreSQL，不是新語言或新基礎設施。

A. 維持 `skeleton: off` — 第一個 Bolt 照常跑，不另開 skeleton 儀式。
B. 本 intent 開啟 `skeleton: on` — 先做一個可估價的 walking skeleton Bolt 並單獨 gate。
C. 現在不定 — 留給 delivery-planning 再決定。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 維持 `skeleton: off` — 第一個 Bolt 照常跑，不另開 skeleton 儀式。

## Q2. 「C1 只准公開免帳號價目、禁止 Cost Explorer／帳單 API／雲端價目憑證」要不要升格寫進 team.md Forbidden？

> intent／feasibility 已鎖這條。盲評指出草稿若只寫「獨立 pricing port」，字面上仍可能打到需帳號的 API。升格後每次 practices-promote 都會帶著走。

A. 升格 — 寫進本輪 `discovered-rules.md` Forbidden，affirm 後進 `team.md`。
B. 不升格 — 留在本 intent 的 scope／project Corrections，不進團隊 Forbidden。
C. 升格但範圍更窄 — 只禁 production credentials，staging 價目憑證仍可評估。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 升格 — 寫進本輪 `discovered-rules.md` Forbidden，affirm 後進 `team.md`。

## Q3. 第一個 C1 HTTP 端點的授權測試深度？

> 規則 A 綁的是「改 `role_permissions` 種子」。若本輪種子不變、只新增 `/api/cost*`，A 字面不觸發。規則 B 要求 TestClient 斷言 status 與欄位，未明寫 403。

A. 即使種子不變，第一個 C1 消費者也必須有 allow／deny（含 403）TestClient。
B. 種子不變就只做規則 B（2xx／欄位）；deny／403 等真的改種子再補。
C. 授權測到 service 層 `user_can` 即可，不強制 HTTP 403。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 即使種子不變，第一個 C1 消費者也必須有 allow／deny（含 403）TestClient。

## Q4. cost calculator 的模組落點？

> 既有規則：新模組走三層；不趁機改 `user_router`。盲評擔心 TCO 被追加進 `wa_rule_engine`（那邊已有 `COST-*` 啟發式）。

A. 新三層：`cost_router` → `cost_service` → 純函式 `cost_calculator`（另獨立 `pricing_client`）。禁止寫進 `user_router`／`wa_rule_engine`。calculator 內不得 httpx／DB／HTTPException。
B. calculator 可與 `wa_rule_engine` 同檔或同套件，因為都是「成本」相關。
C. 先塞進既有 router，Construction 再抽層。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 新三層：`cost_router` → `cost_service` → 純函式 `cost_calculator`（另獨立 `pricing_client`）。禁止寫進 `user_router`／`wa_rule_engine`。calculator 內不得 httpx／DB／HTTPException。

## Assumption Confirmation

本檔無新增 assumption 清單需確認（re-run 沿用既有 team.md）。Looks correct / X。

[Answer]: Looks correct.
