**Collaborator:** aidlc-quality-agent

## Contribution

> 本檔為品質視角的獨立審視。所有事實主張皆由我自行對 repo 唯讀查證，未僅轉引
> `code-quality-assessment.md`；與 codekb 有出入之處逐項標明。以下內容寫成可由 lead
> 直接整合進 `team-practices.md` / `evidence.md` 的形式。

---

### A. 核心判斷：本 intent 的六道 CI 閘門全部可以在功能壞掉的情況下亮綠燈

這是我審視後最重要的一項發現，lead 草稿沒有以這個形式陳述。

本 intent 的交付面是「`users` 加最後活動欄位 → `list_users` 回應多一欄 → `AdminPage`
表格多一欄」。逐一對照現有六道閘門對這條路徑的實際斷言能力：

| 閘門 | 對本 intent 的斷言能力 | 判定 |
|---|---|---|
| `repo-contract` | 只驗必要檔案存在與必要**字串**存在（`validate_repo_contract.py:302` 為 `term not in text` 純子字串比對）。不驗欄位、不驗同步 | 結構性無效 |
| `frontend` lint | ESLint 不看資料形狀 | 結構性無效 |
| `frontend` typecheck (`tsc -b`) | `AdminPage.tsx:6` 的 `DbUser` 是**手寫本地 interface**，`fetchUserList` 內 `const data = await res.json(); return data;`（`AdminPage.tsx:42-46`）把 `any` 直接放行為 `DbUser[]`。前端型別與後端 `UserSchema` 無任何編譯期連結 | 結構性無效 |
| `backend` import smoke | 只驗 `import main` 成功，不驗行為 | 結構性無效 |
| `backend` unittest | 14 個測試檔中**沒有任何一個**涉及 `list_users` 或 `UserSchema` 序列化；`python -m unittest discover` 對未被覆蓋的變更必然通過 | 結構性無效 |
| `ui-regression`（Playwright） | 6 個 case，無一導覽至 Admin 頁；`regression.spec.ts` 對 RBAC 只斷言側欄連結可見，從未點進去 | 結構性無效 |

**結論**：後端漏掉欄位、序列化成 `null`、前端渲染成空白，六道閘門全綠。這不是
「覆蓋率不足」的程度問題，是**這條變更路徑上沒有任何自動化斷言存在**的有無問題。
訪談應以此為前提，而不是以「覆蓋率百分比」為前提。

補充一個 lead 未提的事實：`ui-regression` 是**真閘門**，不是諮詢性報告 ——
`.github/workflows/ui-regression.md` 的 `post-steps` 讀 `pw-report.json` 的
`.stats.unexpected`，非 0 即 `exit 1`（agentic 留言只是附帶產物，`continue-on-error`
在前、紅燈在後重新拉起）。容忍 `stats.flaky`、`retries: 1`。所以「補一個 e2e case」
確實會變成有牙齒的閘門，值得投資。

---

### B. `## Testing Posture` 建議段落（可直接整合，取代草稿該節）

草稿該節的事實大致正確但有兩處缺漏（前端測試能力、正面實務認列），以下為建議改寫：

**既成事實（已查證）**

- Backend 測試框架為 Python 內建 `unittest` + `hypothesis` + `unittest.mock`，
  **未使用 pytest**。CI 以 `python -m unittest discover -s tests -v` 執行
  （`ci.yml`）。測試 DB 策略見 `backend/tests/helpers.py`：在任何 DB import 前
  `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite，
  每 session `ensure_role_permissions_seeded(db, force=True)`。
- 規模：`backend/tests/` 14 個測試檔 + `helpers.py` + `__init__.py`。
- Property-based：5 個檔共 8 個 `@given`（`test_diagram_builder` 2、
  `test_design_agent` 2、`test_wa_rule_engine` 2、`test_auth` 1、`test_collab` 1），
  皆落在純函式模組。屬自發實踐，非規則要求。
- **Frontend 完全沒有 unit／component 測試框架**。`frontend/package.json` 的
  `devDependencies` 只有 `@playwright/test`，無 vitest、無 jest、無
  `@testing-library/*`；`scripts` 只有 `test:e2e`。前端的唯一自動化驗證層就是
  那 6 個 e2e case。（此項 lead 草稿未載，但對本 intent 是決策關鍵事實。）
- **零 HTTP 層測試**：全 repo 無 `TestClient` 使用。46 個端點的路由綁定、
  `Depends` 鏈、guard 組合、`response_model` 序列化沒有任何測試涵蓋。
- **完全沒有覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、
  CI 無 coverage step）。

**測試落點模式（lead 未指出，但這是「團隊怎麼工作」的核心答案）**

測試缺口不是隨機分布的，是**沿架構分層**的。我把 `backend/services/` 逐模組對照
測試引用：

| 層 | 模組 | 測試狀態 |
|---|---|---|
| engine／service（純函式為主） | `wa_rule_engine`(973)、`wa_lens_engine`(556)、`diagram_builder`(288)、`rbac`(272)、`lens_service`(203)、`collab_suggestions`(147)、`llm_limits`(64) 等 | 皆有對應測試檔 |
| router（HTTP 層） | `review_router`(484)、`agent_router`(148)、`lens_router`(108) | **完全無測試檔引用** |
| router（HTTP 層） | `user_router`(831) | 僅 3 個私有 helper（`_build_role_catalog`、`_hard_delete_user`）被 `test_j5_authz.py` 直接呼叫；**路由函式本身零覆蓋** |

也就是說：**團隊會為可直接呼叫的純函式寫測試，不為需要組裝請求的路由寫測試。**
這比「覆蓋率不足」精確得多，也直接指出補救點。

**應被認列的正面實務（lead 草稿完全未提）**

近四次功能 commit 皆在**同一個 commit 內**附上後端測試，非事後補：

| commit | 附加測試 |
|---|---|
| `b19e0d6` 功能(a3) | `test_wa_lens_engine.py` +48、`test_wa_rule_engine.py` +16 |
| `92f7f29` 功能(a1) | `test_diagram_builder.py` +51 |
| `a4de2c3` 功能(A1/A3) | `test_collab_suggestions.py` +52、`test_llm_limits.py` +41、`test_wa_collab.py` +48 |
| `b77d456` 功能(A3) | `test_wa_rule_engine.py` +34 |

`org.md` 的「tests written alongside code」在本專案是**已落地的實務**，不是待
affirm 的理想。但邊界要一併寫清楚：這些測試無一落在 router 層，無一落在前端。
建議 `team.md` 的 Testing Posture 明文追認這個實務**並**明文承認其邊界，讓下一位
開發者（或 agent）知道自己踩在哪條線上。

---

### C. 覆蓋率門檻：lead 的兩個選項都有結構問題

`org.md` 為 `feature` scope 宣告「最低 80% line coverage；tests run in CI before
merge」。事實是無法量測。lead 的 Q3 給了兩個選項：(a) 降級為「目標」、
(b) 維持門檻語氣並列技術債。

**(a) 會製造 `team.md` ↔ `org.md` 的矛盾。** `team.md` 是 strict-additive，只能疊加、
不能弱化 `org.md`。把「80% 是目標不是閘門」寫進 `team.md`，正是 §13 learning
admission check 要擋的形狀。值得注意的是 lead 對 squash-merge 那題**已經正確標註**
「若要記載本專案採 merge commit，屬於與 org.md 矛盾的層級，需走學習准入而非直接
寫入」——同構的問題，同樣的處理沒有套用到覆蓋率題。這是草稿內部的不一致。

**(b) 是把一個沒人會據以行動的數字繼續掛著。** 以現況（測試集中在 engine 層、
router 與前端零覆蓋）估，即使裝上 `coverage.py`，實測數字也會遠低於 80%，
結果是每次 PR 都紅或每次都豁免，兩者都會侵蝕整個規則層的可信度。

**建議的第三條路（品質視角推薦）**：不要在 `team.md` 寫任何百分比，改為承諾一條
**變更範圍內、二元可判、零工具成本**的門檻：

> 每個新增或修改的 HTTP 端點，PR 內必須至少有一個 `TestClient` 測試，斷言其
> status code 與 `response_model` 的欄位集合。

理由：百分比門檻衡量的是**存量**（改不動、也不是本次 PR 的責任），端點門檻衡量的是
**增量**（正是 PR 作者能控制的）。它在 PR diff 上直接可審，不需要任何量測工具，
而且不與 `org.md` 矛盾——它是在 `org.md` 之上追加一條更窄的具體要求，符合
strict-additive。至於 80% 本身，正確的處理是把「導入 `coverage.py` 量測」列為技術債
待辦，等有了真實數字再回頭談門檻，而不是現在對一個量不到的數字表態。

---

### D. 採用 `TestClient` 的實際成本（已查證，Q4 缺這一段）

Q4 問「是否要把 TestClient 測試定為新規則」，但沒有揭露成本。專案自己的 correction
已寫明「不揭露成本的確認不是知情確認」。我實測後補上：

- **零新依賴**。`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`
  ——`starlette.testclient.TestClient` 的全部前置條件已滿足。
- **零 CI 變更**。新測試檔放進 `backend/tests/` 即被現有
  `python -m unittest discover -s tests` 撿到。
- **依賴覆寫可行且不破壞受測邏輯**。`get_db`（`database.py:31`）與
  `get_current_user`（`services/auth.py:39`）都是穩定的模組層函式，可用
  `app.dependency_overrides` 覆寫。`require_story_action` 是 closure factory
  （`services/rbac.py:225`）不可直接覆寫，但它的 `_dep` 依賴上述兩者 ——
  這反而是好事：**真實的 `user_can` 授權路徑仍會被執行**，測試同時涵蓋序列化與
  authz，價值高於一般 smoke test。
- **可繞過 startup**。`main.py` 的 `@app.on_event("startup")` 會呼叫 `init_db()`；
  以 `TestClient(app)` 直接使用（不進 context manager）不會觸發 lifespan，
  不需要真實 DB。

成本評估：第一個測試檔含 fixture 約半天，之後每端點增量很小。以本 intent 而言，
這是唯一能驗證「回應真的多了那一欄」的手段。

---

### E. 本 intent 的「完成」定義（品質視角，可作為 user-stories 階段的驗收輸入）

依 inception phase guardrail「每項需求須有明確 pass/fail 準則」，本 intent 的最低
測試集：

1. **HTTP 層（`TestClient`，後端）**：`GET /api/auth/list` 回應每列含新欄位；
   涵蓋三態 —— 有值、從未有活動（null／佔位）、以及既有 6 個欄位未回歸。
2. **授權未鬆動**：同一端點對無 `J3a.view` 權限的角色仍回 403。加欄很容易在改
   `response_model` 時動到 `Depends`，這是低成本高價值的回歸斷言。
3. **欄位寫入路徑**：所選事件確實更新該欄位；未選定的路徑不誤觸（feasibility 已把
   「節流／彙整／非同步」列為設計階段必答，若最終採節流，該純函式適合以
   `hypothesis` 補一條單調性性質：新值不早於舊值、重複事件冪等）。
4. **前端 e2e（Playwright）**：新增至少一個 case —— admin 登入 → 進入使用者角色頁
   → 斷言表頭出現該欄位、且至少一列顯示值或 rough-mockups 已定的「從未」佔位。
   這是目前**唯一**能碰到 `AdminPage` 的自動化層；不補這一 case，前端交付物就完全
   沒有自動化保護。
5. **schema／部署同步的實測**：`schema_rbac.sql` 重跑後新欄位仍在，且
   `role_permissions` 的既有調整不被清空（對應 T4）。

**PBT 適用性判定**：`project.md` 的 ADR-0006 hard constraint 點名 IaC generator、
cost calculator、agent routing 三個模組，本 intent 均未觸及，故該 hard constraint
對本 intent 為 **N/A**（非豁免、非違反）。僅第 3 項若引入節流純函式時適用。

---

### F. 訪談題目的增修建議

針對 lead 的 8 題中與品質相關的兩題：

- **Q3（覆蓋率門檻定位）——問法要改。** 現行選項會誘導出違反 strict-additive 的答案
  （見 C 段）。建議改問「以下何者為本輪對 `org.md` 80% 門檻的處置」：
  A. 導入 `coverage.py` 量測、先只報數不設閘（取得真實基線後再談門檻）；
  B. 不動百分比，改在 `team.md` 追加變更範圍內的端點測試門檻（見 C 段建議）；
  C. A + B 皆做；
  D. 兩者皆不做，維持現狀並記為技術債；
  E. 其他。
- **Q4（HTTP 端點測試規則）——題目對，但要補三件事。**（1）補上成本揭露（D 段）；
  （2）規則措辭要把斷言內容寫死（status code + `response_model` 欄位集合），
  否則會退化成「有測試就算」的儀式；（3）**必須配一題前端**，見下。

**建議新增的題目**（品質視角認為比現行部分題目更迫切）：

- **【新增，高優先】前端變更的最低驗證要求**：前端目前無任何 unit／component 測試
  能力，`AdminPage` 也無任何 e2e 斷言。本 intent 的前端交付物完全沒有自動化保護。
  請選擇：A. 本輪只補一個 Admin 表格 e2e case，不引入前端 unit 框架；
  B. 引入 vitest + Testing Library 並要求新元件附測試；C. A + B；D. 兩者皆不做。
  （我的建議是 A —— e2e 已是真閘門、成本最低、且直接覆蓋本 intent 的缺口；
  B 屬獨立的工具鏈決策，不該由一個加欄 feature 夾帶。）
- **【新增】schema↔deploy 同步規則的執行者**：`project.md` 已把該同步列為 blocking，
  但**沒有任何自動化在執行它** —— `repo-contract` job 跑的 `validate_repo_contract.py`
  只檢查 `project.md` 這份檔案裡含有 `schema_rbac.sql`／`DEPLOY.md` 這兩個**字串**
  （`REQUIRED_TEXT`，純子字串比對），完全不檢查本次變更是否真的同步了。本 intent
  正好會觸發該規則。是否要在本輪補一個檢查？（可延後，但必須讓決策者知道這條
  blocking 規則目前純靠人／agent 自律。）

**建議可省的**：Q8（`DEPLOY.md` 雙語殘留）與本 intent 無關，且 lead 自己已註明無關聯。
依專案 correction「與當前 intent 無關的題目應省略並記明理由」，建議移出訪談、
直接記為 T16 待辦，減少 gate 的認知負擔。

---

### G. 給整合階段的操作性提醒（非規則，是會弄紅 CI 的機關）

`practices-promote` 會**整段替換** `team.md` 的五個 section。而
`validate_repo_contract.py` 的 `REQUIRED_TEXT` 要求 `team.md` 內必須出現
`<uploader>/<type>/<slug>`、`danniel`、`功能`、`修正`、`feat`／`fix`／`docs`／
`chore`／`refactor`／`test` 等字串，這些**全部位於 `## Way of Working` 段內**
——正是會被整段替換的段落之一。lead 目前的草稿逐字保留了該段內容（正確），
但整合時任何「順手潤稿」都會直接讓 contract 紅燈。

建議：整合完成後、`practices-promote` 執行後，各跑一次
`python3 scripts/validate_repo_contract.py`。另外，`## Testing Posture` 在
`team.md` 目前是空的，所以該節內容為純新增，無此風險。

## Positions

- AGREE: `discovered-rules.md` 判定「本輪無新發現的人類明述硬約束」正確 —— 技術債
  觀察（如 T4 的 `DELETE FROM role_permissions`）確實是事實發現而非團隊決議，
  把它留在 evidence 交由訪談裁決是對的做法。
- AGREE: 「80% 覆蓋率目前既無法量測也無法強制，是宣告而非閘門」的事實判定與我獨立
  查證一致（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step）。
- AGREE: PBT hard constraint「目前無可驗證落點，既未違反也未滿足」的判定正確；
  本 intent 亦不觸及那三個模組，故對本 intent 為 N/A。
- AGREE: 把「新增／修改 HTTP 端點須有 `TestClient` 測試」列為候選新規則，方向正確，
  是本輪最高槓桿的一題。
- OBJECT: Q3（覆蓋率門檻）的選項會誘導出「在 `team.md` 把 80% 降級為目標」的答案，
  而那正是 `team.md` 弱化 `org.md`、應在 §13 learning admission 被擋下的形狀 ——
  lead 對 squash-merge 這個同構問題已正確標註「需走學習准入」，同一處理未套用到
  覆蓋率題，草稿內部不一致（建議改法見 C 段）。
- OBJECT: `## Testing Posture` 漏載「frontend 完全沒有 unit／component 測試框架」
  （`frontend/package.json` 僅 `@playwright/test`），而本 intent 的前端交付物正是
  `AdminPage.tsx` —— 這是該節最具決策相關性的缺口，卻只字未提，且 8 題訪談中沒有
  任何一題涵蓋前端變更的驗證要求。
- OBJECT: Q4 未揭露採用成本，違反專案自己的 correction「不揭露成本的確認不是知情
  確認」。實際成本為零新依賴（`httpx`、`fastapi[standard]` 已在 `requirements.txt`）、
  零 CI 變更、`get_db`／`get_current_user` 可覆寫且真實 authz 路徑仍會執行。
- OBJECT: 草稿未認列可證實的正面實務 —— 近四次功能 commit（`b19e0d6`、`92f7f29`、
  `a4de2c3`、`b77d456`）皆在同 commit 內附後端測試。practices-discovery 的主要職責是
  發現「團隊怎麼工作」，只列缺口不列既成良好實務，會讓 affirm 的對象失真。
- OBJECT: `evidence.md` 的「零 HTTP 層測試」該列在轉引 codekb 時掉了限定語，
  寫成「`user_router.py`、`review_orchestrator.py` 等關鍵模組零測試」。實際上
  `test_j5_authz.py` 直接測試了 `user_router` 的 `_build_role_catalog`、
  `_hard_delete_user`，`test_review_authz.py` 亦引用 `review_orchestrator`。精確表述
  應為「零 HTTP 層測試（路由函式、`Depends` 鏈、`response_model` 序列化未被涵蓋）」，
  否則下游會誤判補救範圍。
- OBJECT: `## Deployment` 把 frontend job 記為「lint＋build」，遺漏 `tsc -b` typecheck
  這道獨立責任（`ci.yml` 該步驟註解明寫涵蓋 typecheck）。更關鍵的是：本 intent 恰好
  證明這道 typecheck 對前後端 schema 落差**無效** —— `AdminPage.tsx:6` 的 `DbUser` 是
  手寫本地 interface，`fetchUserList` 內 `res.json()` 的 `any` 被直接放行。
  「看似有型別保護、實際沒有」必須在 artifact 裡講明，否則會被誤當成已有的護欄。
- OBJECT: `## Deployment` 提到 T4 重跑風險，但漏掉更根本的一層：`project.md` 的
  schema↔deploy 同步 blocking 規則**沒有任何自動化執行者**。
  `validate_repo_contract.py` 的 `REQUIRED_TEXT` 只做純子字串比對，驗的是
  `project.md` 這份檔案裡有沒有 `schema_rbac.sql`／`DEPLOY.md` 這兩個字串，
  與本次變更是否真的同步了完全無關。本 intent 會觸發該規則，決策者應被告知它目前
  純靠人／agent 自律。
