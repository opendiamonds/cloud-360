**Collaborator:** aidlc-quality-agent

## Contribution

盲評範圍僅限測試姿勢、覆蓋率工具、CI 品質閘門、測試／程式形狀，以及訪談必須解開的缺口。未讀 sibling `contributions/`。證據對照：`code-quality-assessment.md`（HEAD `c3de2c8`）、`team.md`／`project.md` 的 `## Testing Posture`、lead 三份草稿。

### 已定案、訪談不得重問

下列不是本輪 practices 問題，證據與既有規則已足夠。把它們再丟進 `practices-discovery-questions.md` 會把 re-run 變成重開 Q4／ADR-0006。

| 項目 | 為何已定案 | C1 的正確用法 |
|---|---|---|
| 規則 A（`role_permissions` 預設變更 → allow/deny 雙向） | `team.md` Q4 定案 A+B+C | 僅在本 intent **改 C1 相關種子**時觸發；擴充既有 `test_rbac.py`／`test_j5_authz.py` 形狀，零新依賴 |
| 規則 B（新／改 HTTP 端點 → `TestClient`，status + `response_model` 欄位集） | 同上 | 若新增 `/api/cost*`，仿 `test_user_list_endpoint.py`；`unittest discover` 會撿到；OpenAPI drift 會逼 `openapi.json` 同 PR 更新 |
| 規則 C（前端資料形狀 → Playwright e2e） | 同上 | 新建 `CostPage` 或 Sidebar C 組入口時，從零補 e2e；前端仍無 unit runner |
| 規則 D（引入 Vitest／Jest／Testing Library） | Q4 **不採** | C1 是全新頁而非「加欄」，但 D 的否決理由是獨立工具鏈決策、不夾帶 feature。本輪仍不得重開 |
| ADR-0006 PBT | `project.md ## Testing Posture` hard constraint；現況模組 ABSENT | **N/A，不是豁免、不是違反。** calculator 一旦出現在 `backend/services/`，Hypothesis `@given` 立即 blocking。形狀已有七檔／十三個 `@given` 先例，不必再問「要不要用 Hypothesis」 |
| `tcms-test-cases` | `project.md ## Mandated` blocking | construction 必跑；LLM／真實 Pricing API／需人判斷的路徑進手動桶，能斷言的進自動化。分流標準已在 `test-case-authoring.md` |
| 80% line coverage | `org.md` 宣告；`team.md` 已拒絕在本層弱化 | 無 `.coveragerc`、CI 無 coverage step。維持「宣告而非閘門」+ A/B/C 當增量門檻。`coverage.py` 已在待補表，本輪不導入 |
| backend `unittest` + `hypothesis`，非 pytest | 既成事實 | C1 新測檔放 `backend/tests/test_*.py`，第一行 `import tests.helpers` |
| `ui-regression` 是真閘門 | `stats.unexpected != 0` → `exit 1` | 寫進 e2e 的東西會擋 PR；不得把 LLM 或付費雲端 Pricing 打進這條路徑 |

Lead 把 A/B/C 映射到 C1（種子改則 A、新 router 則 B、新頁／入口則 C）是正確的規則適用，**不是新規則**。`evidence.md` Gap 1–4、6 的政策含義與此一致。不要為 C1 再發明平行的「必須有 cost 測試」條款。

### 草稿寫對的現況（品質視角核可）

- 測試盤點已跟上 HEAD：`backend/tests/` 21 檔、13 個 `@given`、唯一 `TestClient` 在 `test_user_list_endpoint.py`。現行 `team.md` 仍寫 14 檔、8 個 `@given`、「零 HTTP 層測試」、e2e 六案且未進 Admin——promote 時必須用草稿這段替換，否則會把已關閉的債寫回去（`practices-promote` 整段替換）。
- C1／pricing 測試 **ABSENT** 應記成 greenfield 缺口，不可寫成「覆蓋率不足、補測即可」。無 `test_cost*`、`'C1'` 在 `backend/tests/` 0 命中、無成本頁 e2e。
- WA `COST-*` findings 零測試，且 findings ≠ TCO。測試與測案不得把它們當金額預言。這是 A3 債，不是本 intent 用「補測 COST-*」來假裝 C1 已有計算能力。
- 新模組走三層、純運算下沉、不讀 DB——這是 PBT 能落地的前置形狀，與 `code-quality-assessment.md` 建議一致。calculator 不存在時，這條是設計約束而非當下測試義務。
- CI 對 C1 新端點的實際閘門是：`unittest discover`（撿新檔）+ OpenAPI drift（漏 dump 即紅）+ `ui-regression`（有寫 e2e 才擋）。`tsc -b` 仍不保護手寫 interface；不能當成 C1 schema 護欄。

### 對草稿的挑戰

**1. 把 PBT 形狀丟進訪談，是重開已定案。**

`discovered-rules.md` Mandated 的 PBT 條寫「ALWAYS calculator 一旦建立必須有 Hypothesis」，底下又 `[proposed — 待訪談] 是否在本 intent 建立 calculator 模組，以及 PBT 採用 Hypothesis + @given 的形狀確認。`

- 「模組一旦存在就必須 PBT」已在 `project.md`，不是本輪發現。再列 ALWAYS 會在 promote 時重複蓋章進 `## Mandated`。
- 「要不要建 calculator」是 scope／product，不是 Testing Posture。
- 「PBT 要不要 Hypothesis `@given`」已由 ADR-0006 + 現有測檔形狀鎖定。

請從訪談題刪除 PBT 工具鏈選項。若本 intent 建了模組，品質閘門是「第一個 commit 就要有 property，不得只交 example-based」——這是執行既有約束，不是新實踐。最小不變量（非負金額、覆寫優先於 list price、加總等於分項）可留在設計／NFR，**不要**當 team practice 訪談選項。

**2. C1 特化 NEVER 目前寫成已生效 Forbidden，但無人陳述。**

stage 規定 `discovered-rules.md` 的 ALWAYS／NEVER **只收人工已說的 hard constraint**。四條 C1 Forbidden（`COST-*` ≠ TCO、Assessment 下拉 ≠ Manual Override、C1 種子 ≠ router／CostPage、禁止把 Pricing API 混進既有 `httpx` 呼叫點）來源是 codekb overlay，且**未**標 `[proposed — 待訪談]`。品質在意的是第一條與第四條：它們會變成測試預言與 CI 網路邊界。未核可就放在 Forbidden，promote 會把推論寫進 `project.md`。

這四條應降為訪談候選（核可則進 Forbidden，否決則留在 `evidence.md`）。不要在未問之前當成已 mandated。

**3. A/B/C 字母覆蓋 C1，但「種子未改的第一個消費者」是空洞。**

A 的觸發是「預設值變更」，不是「第一次出現執行期消費者」。證據：種子已有 `FinOps_Analyst` 與 C1 欄，`test_rbac.py` 仍 0 命中 C1。本 intent 若只加 `user_can(..., "C1", ...)` 守衛與 CostPage、**不改種子**，A 不觸發，矩陣測試可以繼續缺席。

B 的字母只要求 status code 與欄位集。一個只 assert 200 + JSON keys 的 `TestClient` 就能過 B，卻測不到「無 C1 權限應 403」。對種子領先、第一個執行期消費者，這正是會漏掉的路。

這不是要新造規則 D2，而是訪談必須決定：**第一個 C1 消費者在種子不變時，是否仍要 allow/deny（service 層或 HTTP 403）**。證據無法代答。

**4. coverage 待補列修復方案，本輪不應升級成閘門題。**

待補表寫「引入 `coverage.py`，先量再訂門檻」是機制債紀錄，與「不在 `team.md` 弱化 org 80%」相容。訪談若問「本 intent 要不要上 coverage gate」，等於重開上次已延期的承載。品質立場：維持待補；C1 的增量門檻仍是 A/B/C，不是存量百分比。

### 訪談必須問（品質透鏡，僅限證據建不成的判斷）

Brownfield re-run：只問草稿與盲評建不成的題。建議三題，其餘不要。

1. **第一個 C1 消費者的授權測試（種子不變時）**  
   A：種子未改則不強制 C1 allow/deny，只在改預設時走規則 A。  
   B：只要本 intent 讓 C1 第一次有 router 或頁面消費者，即使種子不變，也必須有 allow/deny（service 層與／或 `TestClient` 403）。  
   這題解的是 A 的空洞，不是重問 A 要不要存在。

2. **規則 B 對 C1 新端點的最小深度**  
   A：200 + `response_model` 欄位集即滿足 B（與 Q4 字母一致）。  
   B：C1 新端點另須含未授權 403（建議含未登入 401），否則種子領先的守衛等於沒鎖。  
   若第 1 題已選 B，本題可合併，不要拆成兩次問同一件事。

3. **C1 四條 NEVER 是否升格為人工 hard constraint**  
   逐條 Approve／Reject。品質強制核可的是：測試不得以 `COST-*` 為 TCO 預言；unittest／`ui-regression` 不得打真實雲端 Pricing API（用 stub／fake／fixture catalog）。後者僅在本 intent **真的做 live pricing client** 時才有執行意義；若 scope 不做 live client，仍可核可為預防條款，或 Reject 並留在 evidence。

**條件題（scope 不含則刪，不要預先問）：** 若後續 scope 確認本 intent 會打雲端 Pricing API，再問 CI 測試雙重策略（預設應為禁止 live、禁止憑證進 unittest）。現在 calculator／pricing client 皆 ABSENT，把「怎麼測 live API」當必問會超前 scope。

### 明確不要問

- 要不要對 calculator 做 PBT／用不用 Hypothesis／`@given` 長什麼樣子  
- A/B/C/D 要不要重採  
- 本輪要不要引入 `coverage.py` 或把 80% 寫成 CI 閘門  
- 要不要為 CostPage 引入前端 unit 框架  
- calculator 模組要不要建（那是 scope-definition／user-stories，promote 進 Testing Posture 會污染實踐層）  
- 要不要為 `COST-*` 在本 intent 補 A3 單元測試（可記 residual risk，不是團隊實踐選擇）  
- Walking Skeleton 是否開啟：屬 Q3 子條款，品質只註記——若開啟，skeleton 完成定義仍須可測（至少一條 `TestClient` + 一條不打 LLM／live pricing 的 e2e）；不另造測試規則

### 殘餘風險（記 evidence，不升級為規則）

- 前端繼續只有 Playwright：CostPage 複雜度上升會加重冰淇凌甜筒，但 D 已否決，本輪接受。  
- HTTP 層仍極薄（僅 auth list）：C1 是該形狀的第一個新域，B 會把它拉起來；不要回推要求先幫 `user_router`／`collab_router` 補齊才能做 C1。  
- `hypothesis` 未 pin：與 backend lockfile 待補同一桶，不是測試姿勢題。  
- 突變驗證屬 `construction.md`，不是本 stage 新實踐。

## Positions

- AGREE: A/B/C 直接適用 C1、不另造平行測試規則 — Q4 已定案；C1 只是觸發條件（改種子／新端點／新頁），不是新姿勢
- AGREE: ADR-0006 PBT 在無 calculator 時為 N/A 而非豁免 — 與 `project.md`、`code-quality-assessment.md` 一致；模組落地當下轉 blocking
- AGREE: 測試盤點以 HEAD `c3de2c8` 覆寫過時 `team.md` 數字 — 21 檔、13 個 `@given`、已有 `TestClient`；整段替換否則會倒退
- AGREE: 80% 維持 org 宣告、本輪不上 coverage 閘門 — 避免 `team.md` 弱化 `org.md`；A/B/C 仍是可執行增量門檻
- AGREE: D 不重開、CostPage 只走規則 C 的 e2e — 前端仍無 unit runner；`ui-regression` 已是真閘門
- AGREE: `COST-*` 不得當 TCO 測試預言 — findings 無金額、連 example-based 都沒有，補測它也不等於有 calculator
- OBJECT: 訪談確認 PBT／Hypothesis `@given` 形狀 — 重開 ADR-0006；「建不建模組」也不是 Testing Posture
- OBJECT: 把既有 PBT ALWAYS 當本輪新 Mandated 候選 — promote 會對 `project.md` 重複蓋章
- OBJECT: 四條 C1 NEVER 未標待訪談卻寫進 Forbidden — 非 human-stated；品質相關兩條（TCO 預言、live Pricing 進 CI）必須先問
- OBJECT: 未把「種子不變的第一個 C1 消費者」列為訪談缺口 — A 不觸發、B 字母可不含 403，證據建不出團隊意圖
