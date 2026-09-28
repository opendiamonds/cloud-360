<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-24T10:22:44Z — CONDITIONAL 適用性：Execute。condition 為「需要新元件或服務、或需服務層設計時執行；僅修改既有元件時 skip」。本 intent 新增七個元件與四支 workflow，且 `.github/actions/` 目錄在本 repo **不存在**（無 composite action 先例），屬新建而非修改，命中無疑義。
- 2026-08-24T10:22:44Z — 出題前的唯讀查證發現 **V-1：gh-aw 的 concurrency group 由編譯器依觸發型別產生、作者寫不了，PR 觸發型固定 `cancel-in-progress: true`**，與已核可的 `NFR-P3`（兩事件路徑共用一組且不取消）直接牴觸。這項事實把 Q1 從「偏好題」變成「其中一個選項會讓已核可需求不成立」，因此寫進問題檔的 V 表供題幹引用，並成為 ADR-A1 的決定性理由。
- 2026-08-24T10:22:44Z — 七個元件的切分判準是「若兩者總是一起改就是同一個」：C-1 sync-map 與 C-2 record-reader 併入同一個 composite action（對照表的輸入形狀由解析器決定），而 C-3 board-client 獨立（外部 API 契約與內部映射各自演化）。四個葉節點互不依賴，編排集中在 workflow 層與 C-7。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-08-24T15:46:28Z — **同一站連續兩輪犯同型錯誤：改一份 artifact 不掃其餘四份。** reviewer iteration 2 的 6 項發現、iteration 3 的 1 項新發現，**全部**是我修正時的跨檔傳播失敗（403 過度宣稱只改了 `decisions.md`、concurrency 字串只改了 `services.md`、選取演算法只改了一處而 `components.md`／`component-dependency.md` 仍假設舊行為、補 FR-H1 標籤時沒注意同表下方已寫「無元件」、修 NFR 標籤時又製造出「已列出卻寫不重複列」）。沒有一項是新的設計錯誤——設計本身撐過了兩輪對抗審查。`project.md` 既有的 `units-generation:c6b` 講的是「同步衍生的數字與引用」，不涵蓋「跨檔案傳播同一個決定的改動」，這是它的缺口。
- 2026-08-24T15:46:28Z — 第三輪才用對方法：**動手改之前先列出「本輪要改動的每一個主張」，改完逐一 grep 全部產出檔**，而不是改完再回想哪裡可能提過。第一版掃查腳本本身還有 shell 引號與 Python 的 bug、把表格簡寫（`FR-B1、B2、B3` 前綴只掛第一個）誤報為未覆蓋——**掃查腳本本身也要驗**。
- 2026-08-24T10:22:44Z — **未逐字讀完 `inline_context_paths` 的 27 個檔案**。`mode: inline` 要求載入 lead 與兩個 support persona 及其 knowledge。三個 persona 已全讀；knowledge 側只讀了與本站直接相關者，未讀 `cdk-best-practices`／`cost-optimization-patterns`／`infrastructure-guide`／`well-architected-framework`（本 intent 無 AWS 元件）與 `accessibility-wcag`／`wireframing-guide`（本 intent 無新 UI，看板是既有第三方介面）。理由：這六份的內容對「GitHub Actions ＋ Projects v2」這個標的沒有可套用的判準，讀它們只會稀釋注意力。如實記載而非宣稱全讀。
- 2026-08-24T10:22:44Z — **Q1 的回覆不是選項之一而是重新框定**（希望機制可被所有採用 AI-DLC 的專案使用）。未直接採納，而是先查證後發現使用者提的兩條路（extension/skill vs 共用 gh-aw）**不等價**——前者是人在迴圈內觸發，與 `FR-B4`／`NFR-P1` 直接牴觸。以追問 F1 把這個落差攤開再請裁決，而非自行挑一條。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-08-24T15:46:28Z — reviewer 建議 finding 2／3 分別以「S-A 加 registry 核對」與「評估 `queue: max` 或更細的 concurrency group」處理；我改用單一上游修法（選取改為 registry 驅動）同時解掉兩者，並在 brief 中主動要求 reviewer 最用力打這個偏離。代價是它引出一個我沒想到的新問題（首建被排除），但那是措辭疏失而非方向錯誤——iteration 3 確認方向成立。**主動請 reviewer 打自己的偏離修法是有回報的**。
- 2026-08-24T10:22:44Z — ADR-A1 選純 Actions 而非 gh-aw：放棄 `safe-outputs` 的便利（自動注入權限、自動開 issue）與 `update-project` 這個現成的看板寫入型別，換得 `NFR-P3` 照字面成立、全路徑零 LLM、以及 composite action 可被 fixture 驅動。代價中最實的一項是 **Projects v2 的 GraphQL 呼叫本 repo 無先例**，分頁／欄位 id／錯誤碼全部新寫。
- 2026-08-24T10:22:44Z — ADR-A5 維持上游 NFR-O2 的兩類排除而非擴為三類：接受「一致率在 `aborted` 被清理前不為 0」。判準是那兩類排除的共同性質為「機制刻意且正確地不維護它」，而 `aborted` 是待清理的真實不一致，不同類。P4 的分辨需求改由三份獨立清單滿足。
- 2026-08-24T10:22:44Z — ADR-A4 採 [Q3=C] 的兩處並用，並自行定案「不一致時以受管區塊為準」。使用者只選了「並用」，優先序是本站補的——因為不定它下游會各自猜測。此為設計決定，已在 ADR 的 Decision 段明寫而非藏在內文。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-08-24T15:46:28Z — [US:S-10 AC 5] 的第二個例子（改 record 目錄以外的檔案應回 403）**在本設計下無機制可產生**，候選是 GitHub Repository Rulesets 的 file-path restriction，已列為 PRE-1-a 實測項。若實測不可行，該 AC 需回 user-stories 依 `user-stories:c4` 改寫——這是 construction 開工前就該知道的事。
- 2026-08-24T10:22:44Z — **ADR-A6 是本設計最不易反轉的決定**：受管區塊格式一旦上線即為契約，改格式而不重新基準化雜湊，會讓下一輪反向同步把**全部**受管 item 誤判為有人為變更，並使正向對全部 intent 進入 `suppressed`。construction 階段的任何格式調整都必須走遷移路徑。
- 2026-08-24T10:22:44Z — **兩處對既有檔案的修改被本設計逼出來，但本站只確立必要性、未指定手段**：①`ci.yml` 需加 `paths-ignore` 或等價手段，否則 [US:S-1 AC 7]（回寫 commit 不得取消既有 CI run）無法通過 ②高成本的 `on: pull_request` workflow（至少 `ui-regression`）需對反向 PR 跳過，否則 [US:S-6 AC 7] 不成立。兩者都是 `.github/` 內既有檔案的修改，不是新機制。
- 2026-08-24T10:22:44Z — **可重用性「可以」與「已驗證」的區別未被任何 AC 覆蓋**（ADR-A10 的 Consequences 已明寫）。本次沒有任何斷言驗證這套 workflow 在另一個 repo 跑得起來。若日後有人把它當成可安裝的產品，這個落差會在那時才被發現。
- 2026-08-24T10:22:44Z — **CAP-11 的 over-suppression 風險未被實測**：本設計以「讀 PR 的 diff 是否含該 intent 的 record 路徑」做逐 intent 判定，但先例（`--all-intents` 開單一 PR）的形狀與此不同。[US:S-6 AC 3] 已含反例要求，實測落在 construction。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
