# Evidence — Cloud-360 Practices Discovery（Lead Integration，practices-discovery re-run）

> 逐項記載本輪檢視了什麼、推斷了什麼、依據為何、訪談如何定案，以及向下游（design／
> construction）傳遞的實作事實。所有主張皆有 codekb 或 repo 檔案路徑支撐；沒有證據
> 支撐的內容不寫進 `team-practices.md`，只在此處標示為開放問題。

## 檢視的上游證據來源

- `aidlc/spaces/default/codekb/cloud-360/code-quality-assessment.md`（326 行）——技術債根因叢集 C1–C5、測試現況、linting／CI/CD 護欄評估、文件品質評估。**本輪查明其部分數字與草稿轉引有落差**，見「轉引誤差修正」一節。
- `aidlc/spaces/default/codekb/cloud-360/technology-stack.md`（184 行）——語言／框架版本、依賴 pin 狀態、建置系統、版本治理現況。
- `aidlc/spaces/default/codekb/cloud-360/code-structure.md`（前 80 行）——backend 模組分類（router／orchestrator／engine／foundation 四型）、頂層目錄結構。
- `aidlc/spaces/default/codekb/cloud-360/architecture.md`、`business-overview.md`、`dependencies.md`、`component-inventory.md`、`api-documentation.md`——未逐行精讀，由 `code-quality-assessment.md` 與 `technology-stack.md` 交叉引用其結論。
- `git log --oneline -25`、`git log --oneline --merges -15`、`git branch -a`——驗證既有 commit message 型態、PR 合併型態與分支命名慣例的實測落地情況。
- `AGENTS.md`（repo 根目錄）——確認無新規則遺漏。
- `aidlc/spaces/default/memory/{org,team,project}.md`、`phases/inception.md`——既有規則基準線，逐字比對避免遺漏或覆寫。
- **三位 support agent 的獨立唯讀查證**（`contributions/aidlc-quality-agent.md`、`aidlc-developer-agent.md`、`aidlc-devsecops-agent.md`）——皆以本輪對 repo 的直接讀取為據，非僅轉引 codekb，發現並修正了多處草稿／codekb 的轉引誤差（見下節）。
- `practices-discovery-questions.md`（Q1–Q6，全數作答）——人工訪談定案來源。

## 轉引誤差修正（三位 support agent 盲審發現，已核實並採用）

以下為草稿或 codekb 的事實性錯誤，已在整合時修正，**不採用**原草稿的錯誤數字／描述：

| 項目 | 草稿／codekb 原述 | 實測修正 | 來源 |
|---|---|---|---|
| 前端 `fetch()` 數量 | 32 處、8 支檔，無集中抽象 | **52 處、10 支檔**；URL 組裝已集中於 `config/api.ts`（`apiUrl()`／`wsUrl()`），未集中的是認證標頭（40 處手寫）、401 處理、錯誤解包、回應型別 | [D] |
| 角色清單物化份數 | 3 處（`rbac.py`／`schema_rbac.sql`／`AdminPage.tsx`） | **5 份以上**：正本 `rbac.py::CANONICAL_ROLES`；手寫副本 `auth.py::require_any_user`（brief 與 codekb 皆未發現）、`user_router.py::ROLE_DISPLAY_NAMES`、`AdminPage.tsx::AVAILABLE_ROLES`（已與正本**順序漂移**，非假設性風險）、`schema_rbac.sql` seed；`user_router.py:26` 的 `import CANONICAL_ROLES` 不是副本，codekb 誤記 | [D] |
| ESLint 結構性規則範圍 | 僅 `react-refresh` 與 `set-state-in-effect` 兩條 | `eslint-plugin-react-hooks@7.1.1` flat recommended 開了 **16 條 error 級規則**（含 `immutability`、`purity`、`static-components`、`preserve-manual-memoization` 等），另 3 條為 warn；CI 的 `npm run lint` **無 `--max-warnings 0`**，即「error 擋、warning 不擋」，現況 `0 errors, 3 warnings` | [D] |
| 模組 docstring 品質 | 「18 支中 16 支已載明職責／安全邊界／契約」（全稱） | codekb 原文是「**多數**明確載明」；`user_router.py` docstring 僅單行功能清單，無安全邊界、無契約段。正確表述：「模組級 docstring 覆蓋率 16/18；router 類多為單行摘要，`agent_router.py` 的『契約（前端依賴，請勿變更）』是最完整的樣板」 | [D] |
| CI frontend job 內容 | lint + build | 遺漏 `tsc -b` typecheck 這道獨立責任；且該 typecheck 對前後端 schema 落差**無效**（`AdminPage.tsx` 的 `DbUser` 為手寫本地 interface，`res.json()` 的 `any` 被直接放行） | [Q][D] |
| `validate_repo_contract.py` 的作用域 | 「已落地的機制」，未查證實際涵蓋範圍 | `validate_no_obvious_secrets()` 只看 `contract_files()`（contract 檔），看不到 `backend/`／`frontend/`／`deploy/`；`validate_no_production_config_added()` 以 `git diff` 為輸入，CI 乾淨 checkout 上恆為 no-op | [S] |
| `user_router.py` 測試涵蓋 | 「零測試」 | 精確表述應為「**零 HTTP 層測試**」——`test_j5_authz.py` 直接測試了其私有 helper `_build_role_catalog`、`_hard_delete_user`；路由函式本身（HTTP 層、`Depends` 鏈、`response_model` 序列化）才是零覆蓋 | [Q] |
| 前端測試能力 | 草稿未載 | **完全沒有** unit／component 測試框架（`package.json` 僅 `@playwright/test`），對本 intent（`AdminPage.tsx` 交付物）是決策關鍵事實 | [Q] |
| 正面實務認列 | 草稿完全未提 | 近四次功能 commit（`b19e0d6`、`92f7f29`、`a4de2c3`、`b77d456`）皆在同 commit 內附後端測試，非事後補 | [Q] |
| `ui-regression` 閘門性質 | 未強調 | 是**真閘門**，`post-steps` 讀 `.stats.unexpected` 重新拉紅，非諮詢性報告 | [Q] |
| rollback job 權限放寬 | 草稿判定「刻意放寬，非疏漏」（已評估無虞） | 過早判定：三項權限（`contents: write`＋`pull-requests: write`＋`actions: write`）宣告在 job 層，該 job 內任何步驟皆繼承；是否可縮窄從未被評估過。正確表述：「刻意放寬且尚未評估可否縮窄（對應 `code-quality-assessment.md` T20）」 | [S] |

## 逐項推斷與依據

### Way of Working

| 推斷 | 依據 | 確定度 |
|---|---|---|
| 既有分支命名先於本規則已呈現 `<name>/<type>/<slug>` 形狀 | `git branch -a` 列出 `doreen/feat/a1-nl-to-architecture`、`luojingting/fix/a1-issue-fixes` 等 | 高（直接觀測） |
| PR 合併方式為 merge commit，非 `org.md` 宣稱的 squash-merge | `git log --oneline --merges -15` 顯示 `Merge pull request #465`、`#433` 等合併 commit，且 `ut` 上保留了來源分支的完整 commit 序列 | 高（直接觀測），**已由訪談 Q2 定案為 C（視情況並用：Bolt 分支 squash、一般 PR 維持 merge commit）**，不再是開放問題 |
| 規則生效前的 PR 標題中英混用 | `git log --oneline -25` 可見 `feat(A1): improve workspace chat UX`（純英文）與 `功能(a3): ...`（中文，規則生效後） | 高（直接觀測），不溯及既往 |

### Testing Posture

| 推斷 | 依據 | 確定度 |
|---|---|---|
| Backend 用 `unittest`＋`hypothesis`，非 pytest | `code-quality-assessment.md` L50、`technology-stack.md` L36-37，[Q] 獨立核實 | 高 |
| 80% 覆蓋率門檻目前無法量測／強制 | `code-quality-assessment.md` L100-106；[Q] 獨立核實無 `.coveragerc`／`coverage`／`pytest-cov`／CI coverage step | 高。**訪談 Q1 定案 C**：不在 `team.md` 弱化 `org.md` 的宣稱，改以 Testing Posture 新增的 A/B/C 三項變更範圍門檻作為現階段實際生效的門檻 |
| PBT hard constraint 目前無可驗證落點 | `code-quality-assessment.md` L65-86，對照 `business-overview.md` 能力表確認 IaC generator／cost calculator 尚無實作模組；[Q] 判定「非豁免、非違反，N/A」 | 高 |
| 零 HTTP 層測試（精確表述，見轉引誤差表） | [Q] 直接讀 `test_j5_authz.py` 核實 | 高，且與當前 intent（改 `user_router.py`／`UserSchema`）直接相關 |
| 六道現有 CI 閘門對本 intent 的失敗路徑全部無效 | [Q] 逐道查證：`repo-contract` 純子字串比對、ESLint 不看資料形狀、`tsc -b` 因手寫 interface 無效、import smoke 不驗行為、`unittest` 無涉及 `list_users`／`UserSchema` 的測試、Playwright 6 case 無一到 Admin 頁 | 高，**是訪談 Q4 的核心論據** |

### Deployment

| 推斷 | 依據 | 確定度 |
|---|---|---|
| CI 四道 gate 與觸發條件 | `code-quality-assessment.md` L142-151 | 高 |
| `deploy.yml` rollback／並行控制細節 | `code-quality-assessment.md` L153-163 | 高 |
| `schema_rbac.sql` 重跑會清空 Admin UI 對 `role_permissions` 的調整（T4） | `code-quality-assessment.md` L210（第 178 行 `DELETE FROM role_permissions;` 無條件執行） | 高，**技術債觀察，非既有規則**，未寫入 `discovered-rules.md`，列於下方開放問題 |
| `validate_no_obvious_secrets()`／`validate_no_production_config_added()` 作用域小於 `project.md` 宣稱 | [S] 直接讀 `scripts/validate_repo_contract.py:273`、`:330`、`:347` 核實 | 高，已列入 `discovered-rules.md` 待補承載機制 |
| rollback job 權限放寬（`contents:write`＋`pull-requests:write`＋`actions:write`）尚未評估可否縮窄 | [S] 對照 `code-quality-assessment.md` T20 | 高 |

### Code Style

| 推斷 | 依據 | 確定度 |
|---|---|---|
| Frontend ESLint 規則已影響程式碼結構形狀（非僅風格），範圍為 16 條 error 級規則 | [D] 實跑 `npx eslint .` 得 `0 errors, 3 warnings`，讀 `eslint-plugin-react-hooks@7.1.1` 規則清單核實 | 高，且此形狀對當前 intent（`AdminPage` 新增最後活動時間欄位）直接適用 |
| Backend 完全無 linter／formatter／type checker | [D] 以 `find` 掃遍 repo 確認無 `pyproject.toml`／`ruff.toml`／`.flake8`／`mypy.ini`／`.prettierrc` | 高 |
| Backend 依賴 100% 未 pin、無 lockfile | `technology-stack.md` L139-159；[S] 逐行讀 `requirements.txt` 核實共 12 行皆無版本約束 | 高 |
| 零 TODO／FIXME／HACK／XXX 標記，模組級 docstring 慣例良好但非全稱 | `code-quality-assessment.md` L27-38；[D] 核實 docstring 措辭應為「多數」非「16/18 皆完整」 | 高 |
| 命名慣例：4 項一致、3 項已知不一致 | [D] 逐項 grep 核實（router／WA 引擎前綴／`*Page.tsx` 一致；非元件 TS 檔名、logger 命名、`HTTPException` 呼叫風格不一致） | 高 |
| 後端分層依模組家族而異，宜依落點分流而非宣告統一 service 層 | [D] 對照 `code-quality-assessment.md` 修復順序「T9 `user_router.py` 拆分排第 11 位，建議在 T10 測試保護之後才做」 | 高，本輪採用此分流寫法而非宣告式規則 |

## 訪談定案摘要（Q1–Q6，`practices-discovery-questions.md` 全數作答）

| 題 | 定案 | 落點 |
|---|---|---|
| Q1 | C — 分層寫：`team.md` 只寫現況，「補上承載機制」列為明確待辦 | 定案框架，貫穿全部整合 |
| Q2 | C — 視情況並用：Bolt 分支 squash、一般 feature PR 維持 merge commit | `team-practices.md ## Way of Working` |
| Q3 | A — `skeleton: off`（初答 C，經成本確認後改 A） | `team-practices.md ## Walking Skeleton` |
| Q4 | A + B + C（D 不採）— 授權矩陣雙向測試、HTTP 端點 `TestClient` 測試、前端 e2e 斷言；不引入前端 unit 框架 | `team-practices.md ## Testing Posture` |
| Q5 | A — ADR-0006 security baseline 補進 `discovered-rules.md ## Mandated` | `discovered-rules.md` |
| Q6 | A — 確認 `J3a:view` 同時解鎖使用者清單與升權申請佇列的範圍可接受，不回改上游 scope 文件 | 見下節 |

## Q6 範圍確認的完整記載（不回改上游 artifact）

`Security_Reviewer` 對 `J3a` 目前在兩處 seed（`backend/services/rbac_seed_data.py:299`、`schema_rbac.sql:475`）皆為 `(view=false, edit=false, review=false)`，本 intent 要把 `view` 翻為 `true`。查證發現 `J3a:view` 這一個 guard 同時解鎖兩個端點／頁面：

1. `GET /api/users/list`（`user_router.py:437`）→ `/admin/users` 使用者清單（含新的最後活動時間欄），scope 文件 (d) 明確要的範圍。
2. `GET /api/users/authorization-requests`（`user_router.py:462`）→ `/admin/authorization-requests` **升權申請佇列**，可看到申請人與所申請角色——scope 文件 (d) 未明確揭露此頁面。

權限邊界本身未改變（一直都是同一個 `J3a:view`），但第 2 個頁面的存在在 scope-definition 階段未被明確揭露。**人工訪談 Q6 確認 A：此範圍可接受**（稽核角色本就該看得到誰在申請權限），依 `team.md` correction「下游 stage 經人工確認的語意變更，不回改已核可的上游 artifact；以該 stage 問題檔的確認紀錄為準向下游傳遞」，本檔即為該確認紀錄，向 design／construction 階段傳遞：**`Security_Reviewer` 開通 `J3a:view` 後，會同時看到升權申請佇列頁面，此為已知且已確認可接受的範圍，不需回頭修訂 scope 文件**。

## 向下游傳遞的關鍵實作發現（非 practices 規則，但 construction 階段必須知道）

1. **`UserSchema` 三個具名構造點，其中兩個已在靜默漏傳 `requested_role`（本 intent 唯一會產生使用者可見 bug 的既有實作事實）**：`user_router.py` 內 `UserSchema` 以具名引數逐欄構造三次——`list_users`（L451-458，6 欄，含 `requested_role`）、`update_user_active`（L602-608，**5 欄，漏 `requested_role`**）、`update_user_role`（L705-711，**5 欄，漏 `requested_role`**）。後兩者靠 `requested_role: Optional[str] = None` 的預設值靜默填 `None`，即這兩個 PUT 端點的回應現在就在回報錯誤的 `requested_role`，沒有任何工具會報錯。**新欄位若只加進 `UserSchema` 而不同步三個構造點，會完全複製這個失敗模式**：`/api/auth/list` 有值，但 `PUT /{id}/role`、`PUT /{id}/active` 回 `null`，而前端 `handleRoleChange`（`AdminPage.tsx:89`）正是用 PUT 的回應更新列——結果是**使用者改完角色後該列的最後活動時間會變空白，重新整理才會回來**，且 e2e 不會抓到（`regression.spec.ts` 未斷言表格內容）。建議 construction 階段把三個構造點全部補齊，或收斂成單一 `_serialize_user(u, requested=None)` helper（`user_router.py` 已有 `_serialize_auth_request` 形狀先例，L250-261，可直接套用）。`UserSchema` 的 `class Config: orm_mode = True`（Pydantic v1 語法，`pydantic` 未 pin 實際解析到 v2）目前是死設定，不要嘗試改用 `from_orm`／`model_validate` 取代手寫構造。
2. **權限稽核軌跡的實際保存期約等於兩次部署間隔**：`_audit_append()`（`user_router.py:186`）實作為 `logger.info(...)`，寫進容器 stdout；`deploy/docker-compose.deploy.yml` 未設定任何 logging driver 或保存上限；`.github/workflows/deploy.yml:119` 每次合併都執行 `docker compose up -d --build --remove-orphans`，backend 容器被重建、舊容器連同其日誌一併移除。在 deploy-on-merge 模式下，稽核事件（誰改了誰的角色、誰重設了權限矩陣）的保存期可能只有數小時。本 intent 的價值主張是「提供稽核查驗能力」，但平台自身對「誰改了誰的權限」的稽核軌跡是易失的——這一點應在 nfr-requirements 階段被明確處理（是否需要超出容器生命週期的保存），本輪不列為硬規則。
3. **ESLint 的 `react-hooks/set-state-in-effect` 已迫使 `AdminPage` 採特定資料抓取形狀**：純抓取函式（`fetchUserList`，不碰 state）＋ 呼叫端於 `.then/.catch/.finally` 更新 state（`fetchUsers`）＋ `useEffect` 內 `cancelled` flag 防卸載後 setState，三段結構缺一即觸發 error 級規則、CI 紅燈。新增欄位的資料處理必須沿用此三段結構，不得把新欄位的取得塞進 `useEffect` 或在 `fetchUserList` 內 setState。
4. **時間欄位的既有序列化樣板可直接沿用**：`AuthorizationRequestsPage.tsx` 已是「admin 表格＋時間欄」的完整先例——前端 interface 欄位型別為 `string`（非 `Date`）：`created_at?: string;`；渲染 `{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}`；未引入任何日期函式庫（`package.json` 無 dayjs／date-fns）。後端對應：DB 欄位 `DateTime(timezone=True)`，產生時間用 `datetime.now(timezone.utc)`（不要抄 `auth.py` 的 `datetime.utcnow()`，屬 deprecated 用法），Schema 型別 `Optional[datetime]` 交給 Pydantic 序列化。`database.py` 的 `_ensure_a4_schema()`／`_ensure_j5_schema()` 是既有的 `ALTER TABLE users ADD COLUMN IF NOT EXISTS` 先例，本 intent 應新增同形狀函式並掛進 `init_db()`。

## 未採納的 support agent OBJECT 與理由

- **[S] Q9–Q13（backend 依賴 pin 政策、JWT 預設值處置、掃描器導入範圍、端點授權宣告明文化、RBAC 雙處同步是否成為 blocking 規則）**：這些是有價值的追加訪談題，但**本輪訪談僅涵蓋 Q1–Q6**（lead 原始 6 題，措辭已依三位 agent 的 OBJECT 修訂），Q9–Q13 未被實際提出並作答。依「只收錄已由人類定案的內容」原則，這些項目**不**寫入 `team-practices.md` 或 `discovered-rules.md` 作為新規則，僅以事實形式記入本檔（見上方「逐項推斷與依據」與 `discovered-rules.md` 的「待補承載機制」），留待下一輪 practices-discovery 或獨立技術債任務決定。
- **[D] Q-dev-1（角色清單改用 `GET /api/auth/roles`＋一致性 unittest）、Q-dev-2（`UserSchema` 收斂為單一 helper）**：同理，未被納入本輪正式訪談。已將其查證事實（角色清單 5 份物化、`UserSchema` 三構造點漏欄位風險）完整記入本檔「向下游傳遞的關鍵實作發現」，具體是否本輪順手處理，留待 construction 階段依實際 PR 範圍決定，不在 practices-discovery 階段預先強制。
- **[S] D-1／D-2／D-3（RBAC 雙處同步證據附帶要求、權限授予以端點為評估對象、風險接受具名留存）**：內容有理，且與本 intent 高度相關，但同樣未經正式訪談定案為規則。已完整記入本檔供 design／construction 階段參考，其中 D-2（評估對象為端點而非欄位）已透過 Q6 的範圍確認間接落地（見上）。
