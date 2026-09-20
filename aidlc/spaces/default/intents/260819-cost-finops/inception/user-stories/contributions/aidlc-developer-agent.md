**Collaborator:** aidlc-developer-agent

## Contribution

開發者視角（可實作性、故事尺寸、既有 codekb／HEAD 落點）的 Round 1 盲審。未改 `stories.md`／`personas.md`。主張以本輪對 repo 的直接讀取為據，行號基準為工作樹現況（與 codekb HEAD `c3de2c8` overlay 一致處不再重複轉引）。

本輪核對：

- `backend/services/wa_rule_engine.py::parse_diagram_summary`（L125–164）
- `backend/services/rbac_seed_data.py` C1 列（L82–92）與 `rbac.py::user_can`（僅 `view`／`edit`／`review`）
- `schema_rbac.sql` `user_diagrams`（L49–55）、`backend/models.py::UserDiagram`（L80–89）
- `backend/main.py` 五組 router mount（無 `/api/cost`）
- `frontend/src/App.tsx` 路由表（無 `/cost`；`path="*"` → `DefaultRedirect`）
- `frontend/src/components/Sidebar.tsx`（「架構」「系統管理」；無 C 組）
- `frontend/src/pages/WorkspacePage.tsx` 成功卡 CTA（L955–976：繼續編輯／生成 IaC／Well-Architected）
- `openapi.json`：`cost`／`/api/cost` 0 命中
- `backend/tests/`：`test_cost*`／C1 0 命中

---

### 一、C1-1 不是一則故事，是整個 greenfield bounded context

C1-1 的「涵蓋」把 FR-1.1～1.3／1.5、FR-2.1／2.2／2.5、FR-3.1／3.4～3.6、FR-4、FR-5、FR-7.1 第一段、FR-8.1、NFR-1／2／4 全塞進同一則。對 Construction 這等於一次交付：

| 層 | 今日 HEAD | C1-1 要新增 |
|---|---|---|
| HTTP | `main.py` 僅 `/api/architecture`、`/api/collab`、`/api/auth` | 新 `cost_router`、新 prefix、OpenAPI dump |
| 領域 | 無 `*cost*`／`*pricing*` 檔 | `cost_service`＋純函式 `cost_calculator`＋`pricing_client` |
| 擷取 | `parse_diagram_summary` 只出 id／label／style（見第三節） | **新**可估價 overlay（不可共用 WA 函式） |
| 價目 | 無公開價目 client；`httpx` 只用在 n8n 與 PNG | 公開免帳號查價、區域閘、未定價列、雲別覆蓋清單 |
| 持久化 | `user_diagrams` 僅 `xml_data` | 區域、列時數預設 24、mxCell `id` 對齊列（FR-7.1 第一段） |
| UI | 無 `CostPage`、無 Sidebar C、成功卡無成本 CTA | 頁、入口、空狀態、圓餅、假設列、產圖 CTA |
| 契約／部署 | 無 C1 DDL 義務 | 新表或新欄 → `schema_rbac.sql`＋`DEPLOY.md`＋`_ensure_*` |
| 測試 | 無 `test_cost*`、無成本 e2e | TestClient 403＋Playwright（僅此兩項寫在 C1-1 DoD） |

`org.md` 的分支壽命是 1–2 天。上表無法在單一 Bolt／單一 sprint 內驗證「這則故事完成了嗎」——失敗模式互不相同（擷取列數、出站查價、UI 入口、DDL 升級、OpenAPI drift）。Q2=A 拒絕「一 FR 一則偽故事」是對的，但不授權把第一段產品面整包成 C1-1。

建議（仍是使用者可感知切片，不是技術任務）：

1. **入口＋空狀態＋列擷取（跟圖走、未定價佔位、區域必填提示）** — Alex 看得到「這張圖有哪些可估價列」，即使還沒有官方價。
2. **官方價＋總額＋圓餅＋定價假設** — 依賴 1；此則才引入 `pricing_client`。
3. **產圖 CTA** — 可與 1 同分支，但不要與查價綁死。

時數編輯（C1-2）與覆寫（C1-3）維持獨立是對的；問題在 C1-1 自己已經大於那兩則之和。

---

### 二、沒有 schema 就無法實作 AC-1.5／AC-1.10／AC-2.5／AC-3.7／AC-4.3／AC-5.3

`user_diagrams` 欄位只有 `id, user_id, title, xml_data, updated_at`。沒有 region、hours、SKU、override、budget、last_total、overspend、稽核表。`UserDiagram` ORM 同期。把狀態塞進 `xml_data` 或新 JSON 欄都是**猜測**，且會與「跟圖走：每次以目前 XML 重擷取」打架（XML 被改寫 vs 估價狀態獨立）。

故事把持久化寫成使用者可見 AC，卻沒有任何一則 DoD 認領 `project.md ## Mandated` 的 blocking 部署資產：

- 新表／新欄／seed 語意 → `schema_rbac.sql`（IF NOT EXISTS、檔頭涵蓋清單）
- `DEPLOY.md`「會建立的表／欄位」＋既有環境升級（`_ensure_*` 或針對性 SQL）
- `database.py` ensure：staging 表已存在，`create_all` 不會 ALTER

C1-1 DoD 只有 Playwright 與讀取 403。C1-2／C1-4／C1-5 **沒有 Definition of Done**。C1-3 DoD 有 PBT 與覆寫 TestClient，仍沒有 schema／OpenAPI。追溯表把 (h) 寫成「各故事 DoD + requirements DoD」，等於把 requirements 六條交付條件懸空——Construction 會只抄故事本文的兩行 DoD。

**稽核更嚴重。** AC-3.7／AC-4.3 要求「可查出」誰／何時／圖／舊值／新值。HEAD 沒有可查詢的應用稽核表：`review_orchestrator.audit_log` 是 A3 logger；`user_router._audit_append`（L210–225）只寫應用 logger，註解已寫明不再落檔。沒有新表就無法做「可查出一筆紀錄」。不得猜「沿用 A3 logger 就算通過」。

---

### 三、AC-1.4 與 `parse_diagram_summary` 不相容；DoD 未禁止寫進 `wa_rule_engine`

AC-1.4 的可估價節點：vertex、非空 label、style 不含 `group`／`swimlane`／`container=1`。HEAD `parse_diagram_summary`（`wa_rule_engine.py:147–164`）：

- 輸出只有 `id`／`label`／`style[:200]`，**沒有 SKU、時數、區域、金額**
- 空 label 但 style 含 `swimlane` 或 `shape=` 的 cell **會進 nodes**（L161：`if not value and "swimlane" not in style and "shape=" not in style: continue`）
- **不**排除 `group`、`container=1`
- 連線另存 `edges`，但 nodes 集合 ≠ AC-1.4 列集合

若 Construction 重用此函式（codekb 把它列為「既有可重用鉤子」），AC-1.4／AC-1.5 **必然失敗**。requirements 已寫「不得把 `parse_diagram_summary` 的輸出當成已有 SKU」；故事 AC 與 DoD 都沒有把這句落到交付面，也沒有寫「擷取 overlay 必須是新模組，禁止追加進 `wa_rule_engine.py`／`user_router.py`」。

`team.md`／requirements 已鎖定三層：`cost_router` → `cost_service` → `cost_calculator`＋`pricing_client`。C1-1 是第一個會建立這些檔的故事，其 DoD 卻只提 HTTP 403 與 e2e。阻力最小路徑仍是在 `user_router` 加 handler，或在 `wa_rule_engine` 加 TCO——兩者皆為已肯定 forbidden。

---

### 四、RBAC 種子是 view／edit／review，產品動詞是四種變更；現況種子與 AC 直接衝突

`rbac.py` 的 `Action` 只有 `"view" | "edit" | "review"`。C1 種子：

| 角色 | C1 (view, edit, review) | 故事要求的變更 |
|---|---|---|
| `Project_Architect`（Alex） | `(True, False, False)` | **要能**改時數、估價區域（AC-2.3／AC-2.4） |
| `FinOps_Analyst`（David） | `(True, True, False)` | 覆寫單價／指定 SKU；**不能**改時數 |
| `Project_Editor`（Hannah） | `(True, False, False)` | **要能**改預算（AC-4.2）；不能改時數／覆寫 |

後果：

1. **不改種子，C1-2／C1-4 的 allow 路徑無法成立。** Architect／Editor 的 `can_edit` 皆為 False；`require_story_action("C1", "edit")` 會 403 掉 Alex 改時數與 Hannah 改預算。
2. **只把 Architect 或 Editor 的 C1:edit 翻成 True，四則 403 AC 互打。** 單一 `can_edit` 無法同時表達「Alex 改時數、Hannah 改預算、David 覆寫、Alex 不能覆寫、David 不能改時數」。OQ-1 把映射留給 application-design 可以；故事卻把四種 403 寫成已可驗收的 AC，Construction 會在沒有映射的情況下猜 API 守衛。
3. 種子語意變更觸發 team.md **A 規則**（allow／deny 雙向）與 `schema_rbac.sql`／`DEPLOY.md` 同步。C1-2／C1-4 無 DoD，這筆工作沒有主人。`ensure_role_permissions_seeded(..., force=False)` 在已有列時 no-op——只改 Python／SQL 預設值，staging 既有矩陣不會變（與 last-login US-4 同一條生效路徑）。

Persona 把產品權寫對了；故事把「C1 view」當入口守衛也對（與種子 view=True 一致）。錯的是把四種產品動詞當成 HEAD 已經能執行的授權契約。

---

### 五、AC-3.3 公式不可編碼：覆寫是月費還是小時價？

AC-3.3：David「覆寫單價（月費）」且「小計使用覆寫值與 C1-2 同一套時數公式」。C1-2 公式是 `小時價 × 每日時數 × 30`。若覆寫值已是月費，再乘時數會重複計價；若覆寫是小時價，括號「月費」是錯的。FR-2.3 寫「小計 = 覆寫月費（見 FR-3.2）」把兩種讀法並置。calculator 無法在不猜測輸入量綱的情況下寫 PBT。必須在故事 AC 定錨其一（建議：覆寫為月費小計，**不再**套時數公式；或覆寫為小時 list price，Then 刪「月費」）。

AC-2.2 的「小時價為 730／730」是 FR-3.2 `月價 / 730` 的寫法，可實作，但請改成「小時價為 `730 / 730`（即 1）」以免被讀成兩個 730。

---

### 六、其餘 HEAD 對齊（記載，部分升 OBJECT）

- **AC-1.1 路徑：** 今日不存在成本路由；`App.tsx` `path="*"` 走 `DefaultRedirect`（有 A1 view 會進 `/workspace`），不是 403。落地後 SPA 慣例是 `CapabilityRoute` → `Navigate to="/403"`（頁面，HTTP 仍 200）。真正 HTTP 403 只在 `/api/cost*`。AC 把 UI 與 API 寫成同一句「得到 403」，e2e 會對錯層。應拆：無 C1 view → 無 Sidebar 連結且開成本 **頁** 看到 Forbidden；API 無權 → 403。
- **AC-1.2 CTA：** 成功卡現有三顆鈕（`WorkspacePage.tsx:955–976`），沒有「查看預估成本」。可加，但是 C1-1 的第 N 個前端落點，強化第一節尺寸問題。
- **OpenAPI／generated types：** CI 自 `c3de2c8` 起有 `dump_openapi.py --check`。任何新端點未重 dump 即紅燈。C1-1 引入第一個 `/api/cost*`，DoD 未列 `openapi.json` 與 `frontend/src/types/api.d.ts`。
- **NFR-3 PBT 掛在 C1-3** 合理（calculator 在覆寫優先於 list price 時才完整），但 C1-1 若先上總額／圓餅，計算核心已存在；若不在 C1-1 建立純函式 `cost_calculator`，C1-1 實作會把加總寫進 service／router，C1-3 再抽離即返工。
- **AC-3.6**「系統設定與程式不出現 Cost Explorer 憑證路徑」可測（repo grep／env 範本），同意留在 C1-3。
- **C1-4 AC-4.4／C1-5 AC-5.6** 分段隱藏 UI 可實作，屬 feature flag／路由未掛，不是 schema 問題；但橫幅「每次進入受保護頁」仍需要伺服器端超支狀態（FR-7.1 第二段），回到第二節。

## Positions

- AGREE: Q2=A 依使用者切片、不寫 C2／C3、第一段可單獨上線 — 一 FR 一則會產出無 persona 的擷取／持久化任務。
- AGREE: 時數（C1-2）與單價覆寫（C1-3）分開 — HEAD 種子與產品權本就不是同一 bit，混成一則 BDD 會更難驗 403。
- AGREE: 第二段獨立 Must、第一段 AC 不驗橫幅（Q4=A）— 與 FR-7.1 分段一致，可排兩個 Bolt。
- AGREE: 禁止 Cost Explorer／Billing 憑證路徑（AC-3.6）與「未定價 ≠ 0」— 與 `project.md` Forbidden 及 codekb「COST-* ≠ TCO」一致，可 grep／單元測。
- AGREE: 跟圖走以 mxCell `id` 對齊（AC-1.5／AC-3.8）作為產品規則可實作 — 前提是估價狀態有獨立 schema，不是 `parse_diagram_summary` 的暫存。
- AGREE: Persona 三角色與「無 C1 view 無入口」與種子 view 旗標方向一致。

- OBJECT（事實／專業可裁決）: **C1-1 過大，無法作為單一 sprint／Bolt。** 它同時引入新 bounded context 的 router／service／calculator／pricing_client、新擷取 overlay、公開查價、Cost 頁、Sidebar C、產圖 CTA、持久化與 OpenAPI。`org.md` 1–2 天分支模型裝不下；失敗模式不同類的工作不應共用一則「完成了嗎」。建議拆成入口＋擷取、官方價＋總額／圓餅、CTA 三個仍有 Alex 價值的切片。
- OBJECT（事實／專業可裁決）: **多則故事在沒有 schema 契約下無法開工。** `user_diagrams` 無 cost 欄；無稽核表。AC-1.5／1.10／2.5／3.7／4.3／5.3 都要求伺服器持久化或「可查出紀錄」。實作者只能猜表形狀（獨立表 vs JSON 欄 vs 改 XML）。C1-1／C1-2／C1-4／C1-5 DoD 均未列出 `schema_rbac.sql`、`DEPLOY.md`、`database.py` `_ensure_*`（`project.md` Mandated blocking）。
- OBJECT（事實／專業可裁決）: **C1-1／C1-2／C1-4／C1-5 DoD 漏 OpenAPI 與 generated types。** 第一個 `/api/cost*` 會觸發 `dump_openapi.py --check`；漏 dump 則 CI 紅。requirements DoD 第 6 條未落到任何故事本文。
- OBJECT（事實／專業可裁決）: **AC-1.4 與 HEAD `parse_diagram_summary` 矛盾。** 該函式納入空 label 的 swimlane／shape cell、不排除 group／container、只回 id／label／style。DoD 未要求新 overlay，也未禁止把 TCO／擷取寫進 `wa_rule_engine.py` 或 `user_router.py`。C1-1 必須在 DoD 寫明三層新檔與這兩條 NEVER。
- OBJECT（事實／專業可裁決）: **產品四種變更權無法用現有 C1 `view`／`edit`／`review` 種子實作。** Architect／Editor 皆為 edit=False，與 AC-2.3／AC-2.4／AC-4.2 的 allow 路徑衝突；單一 `can_edit` 無法同時滿足 David 能覆寫、Alex 能改時數、Hannah 能改預算且互斥。OQ-1 未解前，403 AC 不是可編碼契約。種子若改，須 A 規則測試＋既有 DB 生效路徑（`force=False` no-op），C1-2／C1-4 無 DoD 認領。
- OBJECT（事實／專業可裁決）: **AC-3.3 量綱自相矛盾，`cost_calculator` 無法寫而不猜。** 「覆寫月費」與「同一套時數公式（小時價 × 時數 × 30）」不能同時成立。須在 AC 定錨覆寫是月費小計還是小時價。
- OBJECT（事實／較輕）: **AC-1.1 把 SPA Forbidden 與 API HTTP 403 寫成同一結果。** 現行無成本路由時 `*` 是 `DefaultRedirect`；落地後 `CapabilityRoute` 是 `Navigate to="/403"`。應分層陳述，否則 Playwright 會對 HTTP status 寫死而失敗。
