# Application Design — 釐清問題

> Stage: application-design（Inception 2.6，inline）· Depth: Standard · Scope: mvp
> Intent: `260819-cost-finops`（C1 第一輪）
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。
> **成本揭露**：本題組共 5 題。答完後產出 components／methods／services／dependency／decisions。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 模組化單體；新三層 `cost_router` → `cost_service` → `cost_calculator` + `pricing_client` | [tp] Q4 |
| 禁止寫進 `user_router.py`／`wa_rule_engine.py`；擷取為新 overlay | [stories] C1-1 DoD |
| 產品四權：Alex 時數／區域、David 覆寫、David＋Hannah 預算；C1 view 才能進頁 | [req] FR、[stories] |
| 現有 C1 種子是 view／edit／review 三布林；Architect／Editor 的 `can_edit` 皆 False，FinOps 才 True | [code] `rbac_seed_data.py` |
| 估價狀態伺服器持久化；橫幅不能只靠瀏覽器 | [req] FR-7、[stories] |
| 第一段不掛預算／超支／橫幅元件 | [rm] AC-1.16 |
| 公開免帳號價目；禁止 Cost Explorer／帳單憑證 | [req] FR-2.5 |
| 路由建議 `/cost`；估價區域暫定 `<select>`；金額 USD | [rm] |
| 超支後的 LLM 修改建議另開 intent，本輪不夾帶 | [rm] §13 筆記 |
| 各雲公開端點 URL 留 infrastructure-design（OQ-3） | [req] |

## Sources

- [req] `../requirements-analysis/requirements.md`（OQ-1／OQ-2／OQ-5）
- [stories] `../user-stories/stories.md`
- [rm] `../refined-mockups/mockups.md`、`interaction-spec.md`
- [tp] `../practices-discovery/team-practices.md`
- [kb] `aidlc/spaces/default/codekb/cloud/architecture.md`、`component-inventory.md`
- [code] `backend/services/rbac.py`、`rbac_seed_data.py`、`backend/models.py`

---

## Q1. 四種變更權怎麼掛上現有 view／edit／review？（OQ-1）

> `Action` 只有 `view`／`edit`／`review`。單一 `C1.edit` 無法同時讓 Alex 改時數、禁止他覆寫、又讓 Hannah 改預算。Admin 權限矩陣也只有這三欄。

A. **保留 `C1` 當頁面 view 門禁**；另加四個 story id：`C1h`（時數）、`C1r`（區域）、`C1b`（預算）、`C1o`（覆寫）。每個仍用既有三布林，本輪只使用其 `edit`。種子：Alex=`C1h`+`C1r` edit；David=`C1o`+`C1b` edit；Hannah=`C1b` edit。改種子走 A 規則＋`force=False` 生效路徑。**（建議）** 不改 `role_permissions` 表形狀，Admin 矩陣可調。
B. **不新增 story id**；`cost_service` 用硬編碼角色表（Architect→時數／區域，FinOps→覆寫，FinOps|Editor→預算）。`C1.view` 仍管進頁。代價：Admin 矩陣調 `C1.edit` 無法分別授權；與「矩陣是單一真實來源」不一致。
C. **擴充 `role_permissions` 表**加四個 boolean 欄，並改 Admin 矩陣 UI。代價：schema／J3b 頁／OpenAPI 全動，超出 C1 本輪。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 保留 C1 當頁面 view 門禁；另加 C1h／C1r／C1b／C1o，本輪用其 edit。種子：Alex=C1h+C1r；David=C1o+C1b；Hannah=C1b。

---

## Q2. 估價狀態存在哪裡？

> 區域、每列時數、SKU／小時價覆寫、每圖預算、超支判定都要跨登入。`user_diagrams` 目前沒有 cost 欄。

A. **兩張新表**：`diagram_cost`（每圖一列：區域、預算）＋ `diagram_cost_line`（每圖×mxCell id：時數、指定 SKU、覆寫小時價）。外鍵 `user_diagrams.id`，圖刪則 cascade。**（建議）** 可查詢、可稽核、跟圖走對齊 FR-1.5。
B. **`user_diagrams` 加 JSONB 欄 `cost_state`**。代價：部分更新與稽核舊值較難；SQLite 測試與 Postgres JSONB 行為要分叉。
C. **只存在架構圖 XML 自訂屬性**。代價：FinOps 覆寫會改圖檔；與「估價跟圖走但不寫回 draw.io 模型」衝突。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 兩張新表 diagram_cost + diagram_cost_line，外鍵 user_diagrams.id，圖刪 cascade。

---

## Q3. 官方價快取與失敗（OQ-2）

> NFR-4：已快取、50 列內，已認證請求到總額 ≤ 5 秒。無 Redis。測試用 stub，禁止 Cost Explorer。

A. **Postgres 價目快取表**（鍵：雲＋SKU＋區域；值：小時 list price、來源時間、raw 可選）。TTL 24h；過期才打 `pricing_client`。失敗列不寫入正價，走「官方價取得失敗」。**（建議）** 無新基礎設施。
B. **每次開頁即時查價、不落庫**。代價：官方 API 慢或限流時難以保證 5 秒；也無法顯示穩定的來源時間。
C. **本輪只讀 repo 內 fixture 檔當「官方價」**。代價：staging 不是真 list price，FR-2.1 的「官方價」變成假的。
D. Not yet defined
X. Other (please specify)

[Answer]: A. Postgres 價目快取表（雲＋SKU＋區域），TTL 24h；失敗不寫入正價。

---

## Q4. SKU 對照表放哪？（OQ-5）

> 擷取後用 label／style 對到公開 SKU。一對多的建議清單 UI 可留 functional-design，但檔案格式本站要定。

A. **repo 內 YAML**（例如 `backend/cost/sku_map.yaml`），啟動時載入記憶體；改對照表走 PR。**（建議）** 可 diff、可測、不需遷移。
B. **Python dict 寫在模組裡**。代價：對照表與程式碼耦合，非工程師難改。
C. **DB 表，Admin 可改**。代價：本輪沒有 Admin 維護故事；還要種子與權限。
D. Not yet defined
X. Other (please specify)

[Answer]: A. repo 內 YAML（backend/cost/sku_map.yaml），啟動時載入；改對照表走 PR。

---

## Q5. 稽核查詢的 HTTP 路徑？

> AC-5.7／AC-6.3：操作者、時間、圖 id、舊值、新值。HEAD 沒有可查詢的應用稽核表。

A. **`GET /api/cost/diagrams/{diagram_id}/audit`**，C1 view 可讀該圖紀錄；寫入由 service 在覆寫／預算變更時插入 `cost_audit_event`。**（建議）** 與 REST 資源一致。
B. **`GET /api/cost/audit?diagram_id=`** 扁平 query。與現有部分 list 端點類似。
C. **本輪不做 HTTP**，人工查 DB。代價：e2e／TestClient 無法驗稽核；只符合故事的暫定條款，Construction 仍會缺掛點。
D. Not yet defined
X. Other (please specify)

[Answer]: A. GET /api/cost/diagrams/{diagram_id}/audit，C1 view 可讀該圖紀錄。

---

## Consolidated Summary Confirmation

1. **Q1=A** — `C1` 管 view；`C1h`／`C1r`／`C1b`／`C1o` 管四種 edit。
2. **Q2=A** — `diagram_cost` + `diagram_cost_line`。
3. **Q3=A** — Postgres 價目快取，TTL 24h。
4. **Q4=A** — YAML 對照表進 repo。
5. **Q5=A** — `GET /api/cost/diagrams/{diagram_id}/audit`。

金額顯示小數位本站定為 **USD 兩位小數**（可逆，不另提問）。公開端點 URL 仍留 infrastructure-design。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
