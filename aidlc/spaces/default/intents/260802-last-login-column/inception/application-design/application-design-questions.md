# Application Design — 釐清問題

> Stage: application-design（Inception 2.6）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> **每題均附建議選項**，建議理由與代價寫在選項描述內。
> **成本揭露**：本題組共 3 題。Q1 是 ideation 的 raid-log R1 明列「留待設計階段選定」的必答項，Q2、Q3 是 Q1 之外實際會改變元件邊界的兩個決定。答完後產出 5 份設計文件（components、component-methods、services、component-dependency、decisions）並經 architecture-reviewer 審查。
> **已由上游定案、不重問**：欄位語意為「最後活動時間」非「最後登入」；逾期門檻 90 天（嚴格大於）；寫入頻率上限每 5 分鐘一次、計時基準為上一次成功寫入（滑動視窗）；時間格式與顯示規則；欄位位置；無紀錄態呈現；載入／錯誤態沿用既有模式。

## Sources

本站出題前的唯讀查證結果（供題幹與選項引用；技術細節留在此處，artifact 維持設計層表述）：

- [c1] `backend/services/auth.py:39-59` — `get_current_user()` 是所有認證請求的必經依賴（7 個 service 模組共 56 處引用）。其中 **`:57` 已執行 `db.query(User).filter(User.username == username).first()`**，即完整 User 物件與可用的 `db` Session 在此刻皆已在手。
- [c2] `backend/Dockerfile:37` — `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`，**未指定 `--workers`**，故目前為單一 worker process。
- [c3] `deploy/docker-compose.deploy.yml` — stack 僅 4 個服務（`db`、`backend`、`frontend`、`cloudflared`），**單一 backend 實例，無水平擴展**。
- [c4] backend 全域搜尋確認**無背景 worker、無排程器、無快取層**：`BackgroundTasks`、`celery`、`apscheduler`、`redis`、`create_task` 於 `backend/*.py` 與 `backend/services/*.py` 皆無實際使用（`wa_rule_engine.py:349`、`wa_lens_engine.py:402` 的 `redis` 命中是規則引擎的關鍵字比對清單，非依賴）。FastAPI 內建的 `BackgroundTasks` 仍可用（無需新依賴），但目前專案零使用先例。
- [c5] `backend/database.py:123-166` — **既有的既存資料庫補欄機制**。`init_db()`（`:38`）依序呼叫 `_ensure_a4_schema()`、`_ensure_j5_schema()`、`_ensure_a3_schema()`。其中**兩個就是往 `users` 表加欄位**：`:129` `ALTER TABLE users ADD COLUMN IF NOT EXISTS last_opened_diagram_id INTEGER`、`:157` `ALTER TABLE users ADD COLUMN IF NOT EXISTS authorization_status VARCHAR(32) DEFAULT 'approved'`。寫法為 statements 陣列 + `with engine.begin()` + 逐句 try。
- [c6] `backend/models.py:22-33` — `User` ORM 模型，`__tablename__ = "users"`，既有欄位含 `authorization_status`、`last_opened_diagram_id`。
- [tp] `team-practices.md` 本輪新增規則 B — 新增或修改 HTTP 端點需 `TestClient` 測試，斷言 status code 與 `response_model` 的欄位集合。
- [req] `requirements.md` FR-1.3（5 分鐘滑動視窗）、FR-3.1（90 天嚴格大於）、C-2／C-3（schema 與部署資產同步）。

---

## Q1. 寫入頻率的緩解手段（raid-log R1 必答項）

> requirements FR-1.3 已把約束定死：同一帳號的活動時間更新，寫入頻率不得高於**每 5 分鐘一次**，計時基準為上一次成功寫入的時刻。ideation 階段刻意只記錄方向（節流／彙整／非同步）而不選定手段，把選擇留給本站。
>
> 查證後有一項事實改變了三個方向的成本排序：**`get_current_user` 已經把完整 User 物件查出來了**［c1］。也就是說「距上次寫入是否已滿 5 分鐘」這個判斷，**資料已經在手，不需要任何額外查詢**。原本以為的「每次請求都要先讀再判斷」的成本並不存在。

A. **請求路徑內的條件式寫入** — 在 `get_current_user` 已取得的 User 物件上比較 `last_activity_at` 與當下時刻；未滿 5 分鐘則什麼都不做，滿了才發一次 UPDATE。**（建議）**
   - 讀取成本為零（資料已在手［c1］），絕大多數請求完全不碰資料庫寫入。
   - **無狀態**：判斷依據是資料庫裡的值本身，不是 process 記憶體。這代表即使日後加上 `--workers` 或多實例［c2］［c3］，行為依然正確 —— 不需要在擴展時回頭改設計。
   - 判斷邏輯可抽成純函式（輸入：上次時刻、當下時刻、間隔；輸出：是否該寫），直接符合既有測試實務（團隊為純函式寫測試的比例遠高於路由層），也讓 property-based 測試有明確落點。
   - 代價：判斷發生在請求路徑上，該寫入時會有一次同步 UPDATE 的延遲。單筆帶索引主鍵的 UPDATE 對 PostgreSQL 是次毫秒級，且每帳號每 5 分鐘至多一次。

B. **In-process 記憶體節流表** — 用一個 dict 記錄每個帳號上次寫入的時刻，未滿 5 分鐘直接跳過，連比較都不做。
   - 好處：省下 A 方案裡的欄位比較。
   - 代價：既然判斷在 A 已經是零額外成本，這裡省下的是一次記憶體內的時間比較 —— 近乎零的收益，卻換來 process-local 狀態。目前單 process［c2］下正確，但日後若加 worker，每個 worker 各持一份快取，同一帳號的實際寫入頻率會變成 worker 數的倍數，屆時 FR-1.3 的約束在字面上就被打破了。記憶體也隨活躍帳號數成長。

C. **非同步背景寫入** — 用 FastAPI 內建的 `BackgroundTasks` 把寫入丟到回應送出之後。
   - **這一項嚴格說不是節流手段**：它改變的是「寫入何時發生」，不是「寫入多常發生」。若不搭配 A 或 B 的判斷，它仍然每個請求寫一次，並不滿足 FR-1.3。要合格就得是「C + A」或「C + B」，成本是 A 或 B 再加上背景任務。
   - 另一個代價：背景任務的例外不會傳回請求端，若不額外處理就是靜默失敗 —— construction 階段護欄明列「silent failures are not acceptable」，因此需要額外的錯誤處理與記錄才算合格。專案目前零 `BackgroundTasks` 使用先例［c4］。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. 逾期判定由哪一端計算

> 「距今超過 90 天」這個判斷要在後端算好後隨 API 回傳，還是後端只給原始時間戳、由前端計算？
>
> refined-mockups 的 `LastActivityCell` 元件規格把 `isOverdue` 定為**由呼叫端傳入的 prop**（而非在 render 中計算，以避免 `react-hooks/purity` lint 錯誤），但沒有指定那個值從哪裡來 —— 這正是本題要定的。

A. **後端計算，API 回傳布林欄位** — response 同時帶原始時間戳與 `is_overdue`。**（建議）**
   - 90 天是**業務規則**，與「什麼算逾期」的稽核定義同源；放在定義它的那一端，只有一個真相來源。門檻若日後調整，改一處即可，前端不需同步修改。
   - **客戶端時鐘不可信**：前端計算的話，判定結果取決於使用者裝置的系統時間。裝置時鐘偏移或時區設定錯誤會讓同一份資料在不同機器上顯示不同的逾期狀態 —— 在稽核用途下，由客戶端時鐘決定合規標示是不能接受的。
   - 判斷邏輯是純函式（輸入：活動時刻、當下時刻、門檻天數；輸出：布林），與 Q1-A 的節流判斷同性質，測試落點一致。
   - 代價：response 多一個欄位；瀏覽器停在頁面上很久時，該值不會自己更新（需重新載入才反映跨過門檻）—— 但 90 天門檻下，這個延遲在實務上無意義。

B. **前端計算** — API 只回傳時間戳，前端比對當下時間。
   - 好處：response 較精簡；頁面停留期間可即時反映。
   - 代價：上述時鐘問題成立；且 90 天門檻會複製到前端，成為第二個需要同步維護的定義點。

C. **兩端都算** — 後端給布林、前端也自行驗算。
   - 代價：兩個真相來源不一致時該信誰沒有定義，是缺陷的溫床，且沒有帶來對應好處。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q3. 新欄位在既有資料庫的生效路徑

> 新增 `users` 欄位後，已經在跑的 staging 資料庫要怎麼拿到這個欄位？requirements C-2／C-3 已要求 `schema_rbac.sql` 與 `DEPLOY.md` 同步更新，但那兩份是**新建環境**的來源；既有環境的升級路徑是另一件事。
>
> 這裡有一個實際張力：重跑 `schema_rbac.sql` 會一併重跑權限矩陣的 seed，覆寫掉管理員後來在 Admin UI 上調整過的權限設定。所以「叫維運重跑那支 SQL」不是無害的操作。

A. **沿用既有的啟動補丁機制** — 在 `database.py` 新增（或擴充）一個 `_ensure_*_schema()`，內容為 `ALTER TABLE users ADD COLUMN IF NOT EXISTS ...`，由 `init_db()` 在啟動時執行；同時依 C-2／C-3 更新 `schema_rbac.sql` 與 `DEPLOY.md`。**（建議）**
   - 這**正是本專案既有的作法，且有兩個同類先例**：`_ensure_a4_schema` 加 `last_opened_diagram_id`、`_ensure_j5_schema` 加 `authorization_status`，兩者都是往 `users` 表加欄位、都用 `ADD COLUMN IF NOT EXISTS`［c5］。本 intent 要做的事與它們形狀完全相同。
   - 部署即生效，維運零手動步驟，且**完全不需要重跑會覆寫權限的 SQL** —— 直接解掉上述張力。
   - `IF NOT EXISTS` 使其可重複執行，多次部署安全。
   - 代價：schema 定義散在兩處（SQL 檔給新環境、Python 補丁給既有環境），需要靠 C-2／C-3 的同步要求維持一致 —— 但這個代價既有的兩個先例已經在承擔，本 intent 不新增這個問題。

B. **只更新 SQL 檔，由維運人工執行 ALTER** — 不寫補丁。
   - 代價：需要人工步驟才會生效，漏做就是欄位不存在導致的執行期錯誤；且偏離既有的兩個先例。

C. **引入資料庫 migration 工具（如 Alembic）** — 建立正式的版本化遷移。
   - 好處：長期而言是比 A 更嚴謹的作法，能解決 schema 定義散落的根本問題。
   - 代價：新增依賴、需要為既有 schema 建立 baseline 遷移、整個團隊的部署流程都要調整。這是獨立的工具鏈決策，成本遠超一個加欄 feature，不應由本 intent 夾帶（與 practices-discovery 對前端測試框架 D 項的判斷同理）。可列為技術債待辦。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Revision 1（2026-08-09）— 由 units-generation Q2 觸發

**修訂來源**：units-generation（Inception 2.7）的 Q2「單元間的整合契約以什麼為準」，使用者選 **B — 引入前後端共用的型別產生機制**（非建議選項）。

**衝突**：該選擇與本站已核可的 **AD-5**（「不新增執行單元、不新增部署單元、**不新增外部依賴**」）直接抵觸。依 `project.md ## Corrections` 的既有規則 —— 下游 stage 的答案觸發 scope 擴充時，須回跳上游以 Modify 模式疊加修訂並重走 approval gate，不得在下游擅自擴大已核可的範圍 —— 故回跳本站。

**處置**：既有的 Q1／Q2／Q3 與其答案**不動**；本站新增 **AD-9** 記載此例外及其範圍界線，AD-5 加註交叉引用（不改寫其原文）。舊版五份 artifact 已歸檔於 `<record>/archive/2026-08-09-application-design/`。

**使用者在衝突揭露後的選擇**：「回跳修訂 AD-5，保留 B」（另兩個選項為「改用 A，不動上游」與「型別產生另開一個 intent」）。

---

## Q4（Revision 1 新增）. 型別產生機制的取得方式

> 實測發現的硬約束：CI 的 frontend job 是獨立的（`npm ci` → `npm run lint` → `npm run build`，而 build 為 `tsc -b && vite build`），**後端不會在該 job 中運行**。因此「建置時打 live `/openapi.json` 產型別」在現行 CI 結構下不可行 —— 這不是偏好問題，是結構問題。
>
> 另一項實測（Revision 1 追加輪更正）：規格可在**不啟動服務、不連資料庫、不需環境變數**的前提下由程式碼取得 —— 實測產出 36 個 path、28 個 schema、OpenAPI 3.1.0。（原本寫的論據「CI backend job 的 import smoke 已證實」不成立：import smoke 只跑 `import main`，從未呼叫規格產生。結論為真，論據已更正為實測。）

A. **committed spec + 由它產型別 + CI 漂移檢查** — **（建議）**
   - 後端以一支腳本把 `app.openapi()` dump 成 repo 內的規格檔並 commit；前端在建置時由**該檔案**產生 TypeScript 型別（不需要後端運行）；CI 的 backend job 加一道「重新 dump 並比對」的檢查，規格與程式碼漂移即紅燈。
   - 這是唯一與現行 CI 結構相容的形狀：前端 job 只需讀 repo 內的檔案。
   - 代價：規格檔需與程式碼一起 commit（多一個需維護的產出物），且漂移檢查是新的 CI 步驟。

B. **建置時啟動後端取得規格** — 前端 job 先起後端再產型別。
   - 代價：把 frontend job 從「純前端」變成需要 Python 環境與後端依賴的複合 job，CI 時間與失敗面都顯著擴大。

C. **手寫共用型別檔，不用產生器** — 在 repo 內維護一份手寫的共用型別。
   - 代價：這其實是 Q2 選項 A 的變體（仍是人工對齊），沒有取得 B 所要的編譯期保證，卻多了一份要維護的檔案。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q5（Revision 1 新增）. 本 intent 要導入到什麼程度

> 型別產生機制一旦引入，影響面遠大於本 intent 的兩個欄位 —— 前端有 52 處 `fetch`、10 支檔案，全部都是候選的受益者（也是候選的破壞面）。

A. **只接上本 intent 觸及的端點，其餘維持現狀** — **（建議）**
   - 產生器涵蓋整份規格（那是它的運作方式），但**只有本 intent 觸及的使用者物件型別實際被前端採用**；其餘 51 處 `fetch` 的手寫型別不動。
   - 好處：把工具鏈引入的風險與加欄功能的風險分開 —— 若產生的型別與既有手寫型別衝突，爆炸半徑限於一處。
   - 代價：repo 內同時存在「產生的型別」與「手寫的型別」兩種形狀一段時間，需明確記載哪些已遷移。

B. **一次遷移全部 52 處** — 把所有 `fetch` 的回應型別都換成產生的型別。
   - 代價：本 intent 的 diff 會從「加一個欄位」變成「重寫前端所有 API 型別」，且那些端點多數沒有測試涵蓋（team-practices 已記載 router 層零 HTTP 測試），迴歸風險無法以既有測試攔截。

C. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Revision 1 追加（reviewer NOT-READY 後）

Revision 1 首版經 architecture-reviewer 判定 **NOT-READY（2 Critical、2 Major、4 Minor）**。兩個 Critical 都需要人工定案，故加開兩題。

## Q6. 規格檔與型別檔的存放位置

> **Critical 1 的實測**：前端映像的 build context 三處皆為 `frontend/`（`ci.yml`、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`），而 `frontend/Dockerfile` 是 `COPY . .` + `RUN npm run build`。規格檔由**後端**腳本產生，最自然的落點（repo 根目錄，與 `schema_rbac.sql`／`DEPLOY.md` 同層）**不在該 context 內** → 映像建置讀不到 → CI 第四道 gate 紅燈、staging 部署失敗。
>
> **Major 3 的實測**：`frontend/nginx.conf` 為 `root /usr/share/nginx/html` + `try_files $uri`，而 Vite 會把 `frontend/public/` 原樣複製進 `dist/`。規格檔若落在那裡，36 個 path、28 個 schema 的完整 API 地圖會對未認證訪客公開。

A. **改 commit 產生的型別檔** — **（建議・已定案）**
   - 型別產生**不進 `npm run build`**，只在開發與 CI 執行；產生的型別檔 commit 進 `frontend/src/`。
   - Docker 因此完全不需要規格檔 → `docker-build` **真的**不受影響（首版把它記為「無」是錯的，此案使它成真）。
   - 規格檔放 repo 根目錄（與既有的 `schema_rbac.sql`、`DEPLOY.md` 同層），**不進 `dist/`**，公網暴露風險消失。
   - 編譯期保護不減：`tsc -b` 對 commit 的型別檔檢查。
   - 代價：多一份 committed 產出物（型別檔）。

B. **規格檔放 `frontend/` 內** — 由後端腳本跨目錄寫入。
   - 代價：必須額外明文禁止它落在 `frontend/public/`；跨層寫入本身需在設計中明記為刻意行為。

C. **改 Docker build context 為 repo 根** — 影響三處編排檔與 `.dockerignore`，映像 context 從 `frontend/` 膨脹到整個 repo。收益與 A 相同而爆炸半徑最大。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q7. 漂移檢查的穩定性處置

> **Critical 2 的實測**（reviewer 實跑）：規格輸出在**同一組依賴版本下是位元決定性的** —— `PYTHONHASHSEED` 取 0／1／42／12345／999983 各 dump 一次，五份 sha256 完全相同。但**跨依賴版本不穩定** —— 同一份原始碼，僅把 `fastapi` 0.141.1／`pydantic` 2.13.4 換成 0.115.0／2.9.2，輸出即出現 20 行差異、sha256 改變。
>
> 而 `backend/requirements.txt` **12 行依賴、版本約束 0 行、無 lockfile**（實測確認），CI 每次 `pip install` 重新解析最新版。因此這道 gate 會在**完全無關的 PR** 上變紅，且訊號與真漂移不可區分。

A. **釘住 `fastapi` 與 `pydantic`** — **（建議・已定案）**
   - 兩行改動消除根因。
   - 額外好處：`team.md ## Code Style` 已記載「CI／Docker build／staging 部署三處各自解析當下最新版，可能彼此不同」為既有風險，本項是對它的局部改善。
   - 代價：形成「全 repo 未 pin」的局部例外，需在設計中明記理由；日後升版需人工。

B. **只比對正規化後的子集** — 漂移檢查只比對與前端契約相關的部分並剝除函式庫版本雜訊。
   - 代價：「要剝除哪些雜訊」是需隨函式庫演進維護的名單，本身會腐化；且 `additionalProperties` 這類差異可能直接出現在目標 schema 上。

C. **接受並如實標示為 flaky** — 不處理，只在 AD-9 明記。
   - 代價：會誤報的 gate 比沒有 gate 更糟 —— 它訓練人忽略紅燈，連帶削弱真漂移時的訊號價值。

D. Not yet defined
X. Other (please specify)

[Answer]: A

---

# Revision 1（2026-08-11）— PU-6 使用者清單分頁

> **觸發來源**：`scope-document.md` Revision 2 的 Must 能力 (f)。上游把**三個**決定明確指派給本站：requirements **OQ-6**（每頁筆數、回應 envelope 形式）、user-stories **AC-5.5 的處置分支**（非法參數：拒絕 vs 夾取）、以及 user-stories **AC-5.3／AC-5.6 的跨頁一致性策略**（offset 分頁下就地刪除會造成略過）。Q1〜Q7 的題幹、選項與答案**一律不動**。
>
> **已由上游定案、本節不重問**：頁碼式（rough-mockups）；控制項組成與版位、單頁／邊界處置、空清單態、44x44（refined-mockups Revision 1 的定案 5〜9）；不做排序／篩選；不做全域逾期計數；斷點 768px。
>
> **本節新增 3 題。每題均附建議選項。**

## Q8. 回應形狀：envelope 還是裸陣列＋標頭？

> FR-6.2 要求回應帶出總筆數、目前頁次、每頁筆數三個值。清單端點目前回 `List[UserSchema]` 裸陣列。**實測：全 repo 只有一個消費端**（`frontend/src/pages/AdminPage.tsx:41`），沒有其他呼叫者會被形狀變更波及。

A. **envelope：`{ items, total, page, page_size }`** —— **（建議）** 三個理由：①C-8 的型別產生由 OpenAPI schema 產出，envelope 是**具名 schema**、會產出可用的型別，HTTP 標頭不會進入型別契約，等於讓 C-8 對這三個值完全無保護；②三個值與資料同一個 JSON 物件，前端不需在兩個地方取值；③唯一消費端只有一處，改動成本明確且有界。代價：改變既有端點的回應形狀，`AdminPage.tsx:44-48` 的 `res.json()` → `DbUser[]` 會靜默拿到非陣列（這正是 C-8 存在的理由，且 US-5 的 DoD 已把型別契約同步列為交付條件）。
B. 裸陣列 ＋ `X-Total-Count` 等回應標頭 —— 好處：既有消費端不改也不會壞。代價：三個值進不了型別契約（C-8 對它們零保護）；前端要從兩處組資料；且「不改也不會壞」是假的好處 —— 前端不改就永遠只顯示第一頁而毫無察覺。
C. 新開一個分頁端點，保留舊端點 —— 代價：兩個端點回同一份資料、兩份序列化構造點（本 intent 已因三個構造點吃過虧），且舊端點的「回傳全部」正是 NFR-8 要消除的暴露面。
X. Other (please specify)

[Answer]: A. envelope `{ items, total, page, page_size }`（採納建議：唯一能讓 C-8 型別契約覆蓋三個分頁值的形狀，且唯一消費端改動成本有界）

---

## Q9. 每頁筆數的預設值與上限？

> requirements OQ-6 指名本站定案，且它是**上線前置依賴**（未定則 Must 集合不可完整交付）。NFR-8 另要求每頁筆數有上限。
>
> 實測脈絡：目前系統共 12 個帳號（`schema_rbac.sql` 種 1 個 admin、`database.py` 的 11 個 persona 僅在空表時建立）。桌面表格容器為 `max-h-[min(70vh,720px)]`，列高約 57px（`px-6 py-4` ＋ 內容），**720px 約可見 12 列**。

A. **預設 20、上限 100** —— **（建議）** 預設 20 略高於桌面一屏可見的 12 列，捲動一次即可看完一頁，不會讓稽核者為了看完一頁而反覆捲動；小螢幕卡片 20 張的捲動長度仍在可接受範圍。上限 100 給批次查驗留餘裕，同時讓單次回應有界（NFR-8）。20 也是整數倍好算（5 頁 = 100 個帳號），對稽核抄錄有實際便利。代價：以目前 12 個帳號而言只有一頁，分頁在正式環境短期內不可見 —— 但這是資料量的事實，不是設計缺陷；契約與控制項仍然存在且可測（AC-5.7 的單頁態正是為此定案）。
B. 預設 10、上限 50 —— 較小的頁，切頁更頻繁。代價：桌面一屏可見 12 列，預設 10 會讓表格下半永遠留白，且稽核掃讀被切得更碎。
C. 預設 50、上限 200 —— 較大的頁，切頁更少。代價：50 列在小螢幕是很長的卡片捲動；且單次回應的上界較鬆，NFR-8 的保護力下降。
D. Not yet defined —— 不建議：這是上線前置依賴，不定案則 Must 集合不可完整交付。
X. Other (please specify)

[Answer]: A. 預設 20、上限 100（採納建議：略高於桌面一屏 12 列、小螢幕捲動可接受、上限讓單次回應有界）

---

## Q10. 非法分頁參數：拒絕還是夾到合法範圍？（AC-5.5 的處置分支）

> AC-5.5 只定不變量，明文把分支選定交給本站。實測：全 backend **無任何既有的參數範圍約束慣例**（正確查法為只看 `Query(` 呼叫中的範圍關鍵字 —— `grep -rn "Query(" backend/ | grep -E "\\b(ge|le|gt|lt)="` 零命中；本題初稿曾引用一個會誤命中 `role=`／`title=` 的鬆散樣式，已於 reviewer Revision 1 Finding 3 更正，結論不變），所以沒有既有形狀可沿用，必須真的選一個。

A. **拒絕（回 422）—— 以框架原生的查詢參數約束表達** —— **（建議）** 四個理由：①零自訂程式碼 —— 在參數宣告上加範圍約束，框架自動產生 422 且**不會進入查詢層**，直接滿足 NFR-8 的「非法值不得傳入資料查詢層」；②約束會出現在 OpenAPI 規格中，因此**同時被 C-8 的型別契約與規格漂移 gate 覆蓋**；③錯誤回應可觀察、不回傳任何帳號資料，符合 AC-5.5 對「拒絕分支」的要求；④正常 UI 路徑產生不出非法值（控制項只送合法頁次），422 不是使用者可達的路徑。代價：若日後有人手動改網址帶入非法值，會看到整塊錯誤畫面而非優雅降級 —— 但那正確地表達了「這個請求不合法」。
B. 夾到合法範圍（回 200 並回顯夾取後的值）—— 好處：任何輸入都給得出畫面。代價：需自訂夾取邏輯（框架不做）；夾取後的值必須回顯否則與「照收後回空清單」無法區分（AC-5.5 明文要求）；且它讓「不合法輸入」與「合法但超出範圍」（FR-6.4）在使用者眼中變成同一件事，而 requirements 花了一整條 AC 去區分這兩者。
C. 逐參數分流（頁次夾取、每頁筆數拒絕）—— 代價：兩種語意並存，前端要處理兩條路徑，且沒有任何需求要求這種區分。
X. Other (please specify)

[Answer]: A. 拒絕，以框架原生查詢參數約束產生 422（採納建議：零自訂程式碼、約束進入 OpenAPI 規格因此被型別契約與漂移 gate 覆蓋、非法值結構上到不了查詢層）

---

## Consolidated Summary Confirmation — Revision 1

| # | 決定 | 落點 |
| --- | --- | --- |
| Q8 | 回應為 envelope `{ items, total, page, page_size }` | AD-10、C-4 的 Revision 1 擴充、C-9（新元件） |
| Q9 | 每頁筆數預設 **20**、上限 **100** | AD-10、C-9 |
| Q10 | 非法參數**拒絕**（框架原生約束 → 422） | AD-11、C-9 |
| 附帶 | 跨頁一致性策略（AC-5.3／AC-5.6 衝突的收斂） | **AD-12**（見下方說明） |

**AD-12 未單獨出題的理由**：AC-5.3／AC-5.6 的衝突（offset 分頁下就地刪除會讓下一頁略過一個帳號）在 Q8〜Q10 定案後只剩**一個**不違反任何已核可 AC 的解：刪除成功後先就地移除該列（維持 AC-5.6 的立即回饋與頁次不變），再**以目前頁次重抓該頁**重新同步（消除 offset 位移，且「重抓一頁」不是 AC-5.6 所禁止的「整份重抓清單」）。其餘候選皆與已核可決定牴觸：不重抓＝接受靜默略過（削弱 intent 核心價值）；改用游標式＝推翻 rough-mockups 已核可的頁碼式；刪除後回第 1 頁＝違反 AC-5.6。單一可行解不需出選擇題，理由記入 AD-12。

**範圍影響**：三項答案**皆不擴大**已核可範圍。Q8 改變既有端點的回應形狀 —— 這正是 scope Revision 2 的 (f) 明文授權的內容（「清單不再一次回傳全部帳號」），非本站新增。

**本輪新增的 assumptions**（依 `project.md` 的 correction 逐條列出，本關卡的作答即為確認）：

1. 每頁筆數 20 的依據是「桌面一屏約 12 列」的實測估算；若日後版面密度改變，此值需重新評估。
2. Q10 的 422 不是使用者可達路徑，前提是分頁控制只送合法頁次；若日後把分頁狀態寫入網址（線框列為未定），手動改網址就會變成可達路徑，屆時需重新評估是否要優雅降級。
3. AD-12 的「重抓當前頁」每次刪除多一次往返；以本系統的資料量與刪除頻率判斷可忽略，未做效能量測。

Does this all look correct before I revise the five design artifacts?

A. Looks correct
B. Request changes

[Answer]: A. Looks correct（2026-08-11）
