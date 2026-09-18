# Stage Memory — TCMS Test Cases

> 本 stage 執行期間的觀察日誌。四個標準 H2，新條目 append 到既有標題下。

## Interpretations

- 2026-08-19T07:44:00Z — stage 檔說「Do not write a manual case for something the
  automated suite already asserts」，而本 intent 的受測對象是一支不連網、不呼叫 LLM、
  不讀環境變數的 CLI 腳本 —— 撰寫標準 §1 的四種「不能或不該自動化」情形一項都不成立。
  因此手動案例數判定為 **0**，並在 `manual-test-cases.md` 內把判定理由與 14 項行為的
  逐項分桶寫完整。**零案例不等於零產出**：那份檔案要能讓下一個人看懂為何是零，
  否則會被誤讀成漏寫。
- 2026-08-19T07:44:30Z — `/tcms-verify` skill 的第 2 層七點審查，在零手動案例下有六點
  沒有審查對象。仍逐點寫出 N/A 與理由，而不是只回一句「無案例故略過」——
  `project.md` 的既有 correction 要求「缺一不可型判定表不留空白，不適用項一律附理由」，
  同一形狀適用於此。
- 2026-08-19T07:45:00Z — 第 2 層第 7 點要求對照 `stories.md` 的 AC，但本 intent 的
  `user-stories` stage 依 bugfix scope 跳過（引擎的 `consumes_absent` 已標記該檔缺席）。
  解讀為：該點的意圖是「規格與已核可的需求一致」，`stories.md` 只是本專案 feature scope
  的載體。改對照 `requirements.md` 的 AC-1～AC-6，逐條給出實測證據。

## Deviations

- 2026-08-19T07:45:30Z — `/tcms-verify` skill 說在 stage 內執行時把報告「寫入
  `<record>/construction/tcms-test-cases/`」，字面上會產生第 4 個檔案。改為併入
  `tcms-sync-report.md` 的第 1、2 節，依據是 `project.md` 的既有 correction：
  「stage 步驟文字提及、但 outputs 清單未列的產出，併入既有 produces artifact 的段落
  表達，不自創檔案 —— produces 清單是 artifact 集合的正式來源」。
- 2026-08-19T07:46:00Z — 撰寫標準 §4.4 的規格註解要求 `/** */` 區塊，那是 TypeScript
  語法。新測試是 Python，改用 class docstring 承載同一組標記（`@purpose`／`@given`／
  `@step`／`@pass`／`@story`）。刻意**不填** `@api`／`@ui`：受測對象既無端點也無 UI
  route，捏造一個過得了 `openapi.json` 比對的假端點比省略更糟。這是格式契約對非 HTTP、
  非 UI 受測對象的真實缺口（OI-4），不是本測試的瑕疵。

## Tradeoffs

- 2026-08-19T07:46:30Z — 核可關卡提出四支候選腳本，使用者選擇只寫 shallow clone 那一支
  （B-11）。未寫的三支**留在「待自動化」桶並逐項寫出風險與具體寫法**，不轉手動、
  不降級為「不需要」—— 轉手動會把「還沒寫測試」偽裝成「有人會去測」，那正是這個 stage
  存在的理由所要防的事。代價：`main()` 佈線（B-12）仍無測試釘住，而它與 #509 屬同一種
  靜默失效形狀（函式對、但沒被呼叫，測試與 CI 全綠）。
- 2026-08-19T07:47:00Z — B-11 的 fixture 用兩個 commit 而非一個，把違規路徑放進**不會被
  抓取**的第一個 commit。多一次 commit 的成本換到的是：測試真的踩在 shallow 的語意上，
  而不是「clone 了一份剛好也只有一個 commit 的 repo」。配合 `rev-list --count HEAD == 1`
  的守衛，退化的 fixture 會紅燈而非空洞通過（已以突變實測）。

## Open questions

- 2026-08-19T07:47:30Z — `tcms_validate.py` 的 `DEFAULT_MANUAL` 寫死指向
  `260802-last-login-column`（上一個 intent）。`--all` 因此讀起來像「全部都驗了」，
  實際只驗了一份會越來越舊的檔案。這是**規則宣稱強於機制**的又一例 —— 與本 intent
  正在修的 #509 同型（project.md 的 Mandated 寫「執行 `--all`」，而 `--all` 看不到當前
  intent 的產出）。記為 OI-3，值得下一輪優先處理。
- 2026-08-19T07:48:00Z — backend 的 223 個測試在 TCMS 上完全不可見（junit 回寫只接
  Playwright、`--spec` 只解析 `.ts`）。判讀「測試涵蓋範圍」的人在 TCMS 上只看得到前端
  6 個 e2e 案例，會嚴重低估實際覆蓋。修法要同時動 `ci.yml` 與 `tcms_sync.py`，
  本 intent 的 NFR-1 明訂不動 `ci.yml`，故只能記為 OI-1。
- 2026-08-19T07:48:30Z — 這個 record 內第三次遇到同一族問題：**規則層或工具的宣稱範圍
  大於它實際碰得到的範圍**（#509 的 diff 基準、`validate_no_obvious_secrets()` 的掃描
  範圍、`tcms_validate.py --all` 的寫死路徑）。三者成因不同但形狀相同，值得下一輪
  practices-discovery 當成一個類別來處理，而不是各修各的。
