# Stage Memory — Code Generation

> 本 stage 執行期間的觀察日誌。四個標準 H2，新條目 append 到既有標題下。

## Interpretations

- 2026-08-18T01:00:00Z — bugfix scope 無 unit-of-work（`consumes_absent` 明示 `expected: true`），我起初依引擎給的 `memory_path`（`construction/code-generation/memory.md`，不含 unit-name）推斷 produces 也該摺疊掉 unit 層，把 plan／questions／summary 直接放 `construction/code-generation/`。**這個推斷是錯的**，`report --result completed` 被 artifact guard 擋下。
- 2026-08-18T02:10:00Z — 上一條的更正與根因：**引擎自身的兩處路徑解析不一致**。`aidlc-state.ts:1035-1045` 的 `producesDirsForStage()` 在 stage 宣告 `for_each: unit-of-work` 時（`code-generation.md` frontmatter 第 11 行即是），一律走 per-unit 分支 —— `readdirSync(construction)` 後找每個子目錄下的 `<unit>/code-generation/`，**不因 scope 無 unit 而摺疊**；但同一個 directive 給的 `memory_path` 卻是摺疊過的。兩者用不同規則。處置：produces 移到 `construction/production-path-check/code-generation/`（unit 名取本 intent 主題），`memory.md` 留在引擎指定的 `construction/code-generation/`。**教訓：`memory_path` 不能拿來推斷 produces 的落點** —— 兩者在引擎裡由不同函式解析，而 artifact guard 只認 `producesDirsForStage()` 的規則。
- 2026-08-18T01:00:30Z — 「story-to-code-step traceability」在本 intent 無 user story 可對（issue 驅動的 bugfix），故追溯表的上游改為 FR／AC 並在計畫中明寫此替代，不留空欄也不捏造 story id。

## Deviations

- 2026-08-18T01:01:00Z — 計畫 Step 1 寫「**新增** `git_ls_files()` helper」，實作改為**取代** `git_diff_name_only()`。理由正確且應被追認：該 helper 只有一個呼叫點（即被修的函式），保留會留下死碼，而 `team.md` 明列「零 TODO／FIXME／HACK／XXX 標記，且無死碼區塊」是應保護的既有紀律。**計畫的字面與規則層的紀律衝突時，以規則層為準並記錄偏離**。
- 2026-08-18T01:01:30Z — 實作採 `git ls-files -z` 而非計畫寫的 plain form。原因是 plain form 會套用 `core.quotePath` 把非 ASCII 檔名逸出成 `"\344\270\255..."`，破壞 path-part 比對。本 repo 目前 0 個非 ASCII 追蹤檔名，所以這在測試中不會顯現 —— 但這是一個繁體中文文件 repo，風險是真實且會在未來某次新增檔案時無聲觸發。**計畫沒想到的邊界，實作者在動手時想到並記錄，是正確的偏離方向**。
- 2026-08-18T01:02:00Z — 計畫 Step 4 只列 `project.md` 與 `team.md`，實作階段發現 `CLAUDE.md:66` 也寫著同一條規則的舊語意（「不得新增」）。經人工確認後一併改（錨點：audit shard 的 `HUMAN_TURN 2026-08-17T23:40:58Z`；`CLAUDE.md` 實際寫入於 `23:41:16Z`，晚於它 18 秒。決策本身記於同 stage 的 `code-generation-questions.md` Q2（附 `[Answer]: A` tag），比照 Q3 的形式可獨立複驗）。判斷依據：`CLAUDE.md` 第 4 章自述「本章為摘要，衝突時以 memory 層為準」，是 `project.md` 的**衍生落點**而非獨立規則，所以這是 FR-6 漏了一個落點，不是範圍擴張。已實測 contract 的 `REQUIRED_TEXT` 未鎖該句，改動不影響 CI。

## Tradeoffs

- 2026-08-18T01:02:30Z — 回歸測試放 `backend/tests/`（測的卻是 repo 根目錄的 `scripts/` 腳本），位置語意不直觀。接受此代價的依據來自 requirements 的 FR-8：那是**唯一**會被既有 CI job（`ci.yml:135` 的 `unittest discover -s tests`）自動探索到的 Python 測試落點，且不需要改 `ci.yml`（NFR-1）。**一個放在語意正確位置卻永不執行的測試，正是這次要修的缺陷本身** —— 「會被自動執行」的重要性高於「目錄語意純粹」。
- 2026-08-18T01:03:00Z — 函式名 `validate_no_production_config_added` 與常數 `FORBIDDEN_NEW_PATH_PARTS` 在語意上已不精確（`added`／`NEW` 對全域掃描而言是錯的），但刻意不改名：兩者在 `requirements.md`、`project.md`、`team.md` 被逐字引用，改名會斷掉追溯鏈。**接受一處命名不精確，換取跨文件引用的可機械複驗性**；若日後要改名，應與那些引用同一批處理。
- 2026-08-18T01:03:30Z — 防復發同時用了兩種手段：回歸測試（機制）＋ docstring 內的「不要改回 diff 基準」警告與原因（人）。單靠測試不足 —— 這道檢查的失敗模式是靜默的，而改回 diff 基準的人若不知道原因，會把測試一起改掉。

## Open questions
- 2026-08-18T02:00:00Z — reviewer 兩輪都判 READY，但連續兩輪盯同一件事，最後逼出一個比原 finding 更深的問題，完整記下來因為它是這個 record 裡最有價值的一課：
  - **第一輪**：reviewer 讀 audit shard 發現「Plan Approval 到五步完成回報之間沒有 HUMAN_TURN」，據此推論 `CLAUDE.md` 的擴增落點是在自主區間內決定的。時間戳觀察正確，因果反了 —— 那筆 `HUMAN_TURN 23:40:58Z` 就是核可，`CLAUDE.md` 的 mtime `23:41:16Z` 晚它 18 秒。我當時的修法是**補上時間戳錨點**，並在說明中引用「實作者把此決定留給人決定」作為佐證。
  - **第二輪**：reviewer 指出那句佐證**物理上不在持久化紀錄裡** —— `aidlc-log-subagent.ts:43` 把 SUBAGENT_COMPLETED 訊息硬截斷至 200 字元，而 `HUMAN_TURN` 事件只有時間戳、沒有內容欄位（全檔 9 筆皆然）。**它能證明「此刻有一次人類回合」，不能證明「這個回合在核准什麼」。**我的第一輪修法因此只做到一半：把「查無此事」換成了「一半可查、一半查不到」。
  - **最終處置**：比照 `requirements-analysis-questions.md` 的 Q3，在本 stage 的問題檔補一則正式 Q2 並附 `[Answer]` tag。這不是補寫沒發生的事 —— 那次問答確實以 structured question 提出並取得回答，只是**沒被記到它該在的地方**。
  - **教訓（比第一輪寫的那條更精確）**：宣稱人工確認時，光給 audit 時間戳不夠，因為 audit 不記內容。**唯一可獨立複驗的形式是問題檔裡的 Q&A + `[Answer]` tag** —— 那是這個專案裡「決策內容」真正被持久化的地方。任何只存在於對話記憶中的佐證，對下一個讀 record 的人（或全新 session 的 agent）等於不存在。

- 2026-08-18T01:04:00Z — 新測試沒有 `project.md` 所要求的 TCMS spec 註解。`test-case-authoring.md` §4.4 的格式要求至少一個 `@api` 或 `@ui`（兩者都會被機械比對 `openapi.json`／`App.tsx`），但這支測試既無端點也無 UI route，本 intent 亦無 user story 可填 `@story`。**這是格式契約對「非 HTTP、非 UI 測試」的真實缺口**，不是本次的疏漏；捏造假的 `@api` 會比省略更糟（會讓機械比對失去意義）。留給 `tcms-test-cases` stage 判定。
- 2026-08-18T01:04:30Z — `discovered-rules.md` 第 4 項（屬 `260802-last-login-column` record）仍描述這道檢查為 no-op。本 intent 不逕行修改他人 record；`team.md` 已加指標。待下一輪 practices-discovery 標為已解決。
- 2026-08-18T01:05:00Z — 語意由「不得新增」轉為「不得存在」後的豁免機制仍未定義（承接 requirements-analysis 的同一開放問題）。目前 0 命中，不預先設計。
- 2026-08-18T02:30:00Z — reviewer 對**下一站**的預警（本 stage 無法修，交接給 build-and-test 的 conductor）：`build-and-test` 宣告 consumes `code-generation-plan`／`code-summary` 且 `required: true`，但 `emitRunStageForSlug`（`aidlc-orchestrate.ts:2777-2793`）對非 per-unit stage **一律**傳 `UNIT_NAME_PLACEHOLDER`，而 `splitConsumesByPresence`（同檔 1186-1209）看到路徑含 placeholder 就視為 present、不做存在性檢查。所以下一個 directive 的必要輸入欄位會是字面的 `.../construction/{unit-name}/code-generation/code-summary.md`，**不是** `production-path-check` 的真實路徑。**這與產出資料夾取什麼名字無關**，換名字解決不了；接手的 conductor 需自行解析真實路徑。這是引擎在「per-unit 產出 × 零 unit scope 的下游消費者」上的既有缺口，與本 stage 撞到的 `producesDirsForStage` 不摺疊是同一個根源的兩個面向。
