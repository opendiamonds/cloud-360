# Business Logic Model — U-6 正向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## 這個單元在做什麼

它是**正向同步的編排層**——把 U-1（映射）、U-2（受管區塊）、U-3（看板）、U-4（回寫）、U-5（通報）串成一輪執行。

交付 `aidlc-sync-forward.yml` ＋ 其 `*-impl.yml`（`on: workflow_call`，全參數化，[ad:decisions.md] ADR-A10）。驗證方式是 **⑥workflow 執行期**——不是 fixture、不是 API 呼叫，而是「這支 workflow 在真實事件下做對了嗎」。

**它本身不含商業邏輯**：判定在 U-1、格式在 U-2、寫入在 U-3、持久化在 U-4、通報在 U-5。本單元的內容是**順序、分流、與兩道自我排除**。

## 一輪執行的序列

```
事件（push 或 PR）
   │
   ├─ 防線②：HEAD commit 訊息含 [aidlc-sync]？ ──是──► 整輪 skip（結束）
   │                                              否
   ├─► 【迴圈之前】以 label aidlc-sync-reverse 列出開啟中 PR
   │        ├─ 查詢失敗 ──► 整輪中止、ExternalError、紅燈 ＋ 通報（結束）
   │        ├─ 成功（開啟中）──► 變更路徑 → intent id 集合 = Config.reverse_pending
   │        └─ 成功（關閉未合併）► 變更路徑 → intent id 集合 = reverse_rejected（R-6.2a，本輪執行期集合，不進 Config）
   │
   └─► 掃 intents.json registry 的全部 intent，逐一：
          │
          ├─ U-4 read_sync_state ──► SyncState（binding ＋ 六欄；未建檔則視為全空）
          ├─ U-1 composite action ──► Decision（四 output）＋ scope_note（第五 output）
          │      （action 內部：parse ──► ParsedRecord ──► map(…, Config) ──► Decision）
          │
          ├─ R-3.0 閘門：reason_code ∈ {unparseable, whitelisted}？
          │      └─ 是 ──► **本輪對它不做任何看板動作**（[req:FR-J3]）
          │                 ├─ 已綁定 ──► 僅 U-4 write_sync_state 記本輪判定
          │                 └─ 未綁定 ──► 連狀態檔都不建，直接跳過
          │
          └─ 否 ──► 依綁定分流：
                 ├─ 無綁定編號 ──► U-3 create_item ──► U-4 write_binding（首建，R-3.1）
                 └─ 已綁定 ──► 寫入理由判定（R-5.2 三欄比對 ∪ R-5.6 有告示待送）
                        ├─ 皆不成立 ──► 不寫（防線①，R-5.5）
                        └─ 任一成立 ──► 寫入鏈：
                             ├─ Decision.status 非 null ──► U-3 write_status
                             │      expected = 由 SyncState 三欄重建（R-5.7）
                             │      └─ Aborted／ExternalError ──► U-5 notify
                             │              └─► **整條鏈中止、完全不回寫**（R-5.12）
                             └─ Decision.status 為 null ──► 跳過 write_status（R-5.10 (a)）
                                      │
                                      ├─► U-3 write_field
                                      │     └─ Failed ──► U-5 notify；**不連坐**，續走；
                                      │                    last_field_value 維持原值（R-5.12）
                                      ├─► U-2 render(Decision, Context) ──► 區塊文字
                                      │        └─► U-3 write_body
                                      │              └─ Failed ──► U-5 notify；
                                      │                    managed_block_hash 維持原值（R-5.12）
                                      ├─► U-3 read_item ──► 取回 managed_block_hash（R-5.4）
                                      └─► U-4 write_sync_state（**逐欄回寫實際寫成功的部分**）
                                               └─► U-4 commit_and_push
                                                    └─ Rejected ──► U-5 notify（R-5.9 ②）

   └─► 迴圈之後：U-5 resolve_if_open（逐鍵關閉已不再成立的通報 issue，R-6.1a）
```

文字 fallback：先看是不是自己剛寫的 commit（是就整輪跳過）；接著在進入逐 record 迴圈**之前**，一次查出反向 PR——開啟中的算出哪些 intent 要暫停覆寫，關閉而未合併的算出哪些有告示待送（查不到就整輪中止）。

然後掃過 registry 的每一個 intent：先讀狀態檔、再算出本輪判定（**兩者都在綁定分流之前**）。判定為 `unparseable` 或 `whitelisted` 者，**本輪對它不做任何看板動作**（[req:FR-J3]）——已綁定的只把判定記進狀態檔，未綁定的連狀態檔都不建。其餘的依綁定分流：沒有綁定編號的走首建；已綁定的比三欄、或看有沒有告示待送，兩者任一成立才進寫入鏈。

寫入鏈依 `Decision.status` 分兩支——非 `null` 時先寫 Status（`expected` 取自狀態檔的三欄，代表「機制上次寫進去的值」；不符即中止並通報，**此時看板一個字都沒動，故完全不回寫**），為 `null` 時跳過 Status 寫入但其餘照走；接著寫自訂欄位、渲染受管區塊並寫進 issue body、**再回讀一次**取得該區塊的雜湊，最後把狀態檔**逐欄回寫實際寫成功的部分**並推送。自訂欄位或受管區塊寫失敗時各自通報且**不連坐**，對應的那一欄維持原值。推送失敗同樣通報。迴圈結束後逐鍵關閉已不再成立的通報 issue。

> **這張圖與 fallback 於 2026-08-30T00:57:28Z 整組重畫（reviewer iteration 3 C-2 Critical ＋ M-3 Major）。** 先前它有四處與 R-5 群不一致，而其中一處是 Critical：
>
> 1. **`U-2 render ──► content_hash`**（圖）與「含**剛寫進看板那份受管區塊的雜湊**」（fallback）是 2026-08-29T16:19:47Z **已撤回**的舊 R-5.4 路徑——型別不成立（`render -> string` 餵給 `content_hash(Block)`），更要緊的是等價性失效。**本單元就是寫入端，序列圖是實作者取用時序的第一份文件**，殘留在此的殺傷力不低於 U-8 那一處（後者已在其 `domain-entities.md` 寫下「這一處尤其不能留舊說法」）。依 ADR-0015 §10，該路徑失效的後果是「沒有任何人為變更的情況下，U-8 每天為每個受管 intent 各開一則反向 PR」。
> 2. **受管區塊沒有寫者**（Group A C-3／Group B F1）：圖上 `render` 之後直接接雜湊，沒有任何一步把區塊文字寫進 issue body。已補上 `U-3 write_body`（ADR-0015 §11）。
> 3. **`Decision.status = null` 的分支不存在**（M-3）：圖把「有漂移 → `write_status`」畫成無條件，而 `suppressed`／`parked` 這兩條最常走的路徑上 `status` 就是 `null`，`write_status` 的 `desired` 型別不含它。已補上 R-5.10 的分岔。
> 4. **R-5.6 的第二個寫入理由不在圖上**：判定節點原本只寫「三欄比對」，現改為「三欄比對 ∪ 有告示待送」。

## 缺口 F-4 在此關閉

U-1 的 functional-design 標出「誰負責算出 `reverse_pending`」無人擁有，並指派本單元。**本單元在此正式承接**：上圖的「【迴圈之前】」那一段就是它的落點，規則見 `business-rules.md` R-2 群。

三個要點：

1. **一次查詢**，不是逐 intent 查——成本與 intent 數無關。
2. **fail-closed**：查不到就整輪中止並紅燈（D-2）。這是 F-4 指派時明寫的要求（「不得靜默退化為空集合」）。
3. **不得偽裝成 `suppressed`**：那會讓受管區塊記下不存在的反向 PR，紀錄會說謊。

## 兩道自我排除防線的層級

**兩道都是整輪層級**（[ad:services.md] 明文選定，消除了「整個 run 還是只 gate 一個 record」的歧義）：

| 防線 | 何時生效 | 依賴判斷？ |
| --- | --- | --- |
| ① 結構性 | 逐 record 的漂移比對——回寫的內容就是剛寫進看板的值，故無漂移 | **否** |
| ② 顯式 | 整輪開頭的 commit 訊息檢查 | 是（字串比對） |

**防線①不依賴任何判斷，是真正的保底。** 防線②是快速路徑，且它的適用前提（同步身分的 push 會觸發 workflow）成立——[Q2=A] 選的是 GitHub App 而非 `GITHUB_TOKEN`。

**已知代價**：防線②觸發時整輪 skip，該次 run 內其他 intent 的漂移也一併不處理，等下一次事件或隔日對帳。[ad:services.md] 已記為 reviewer iteration 3 Minor，本站如實轉錄不弱化。

## 錯誤處理

| 情形 | 行為 | 紅燈 |
| --- | --- | --- |
| `reverse_pending` 查詢失敗 | 整輪中止 | **是**（R-2.5） |
| 單一 intent 的 `ExternalError` | **不中止整輪**——計入報告後續跑 **＋ 通報** | 是 |
| 單一 intent 的 `Aborted`／`CannotCreate` | 續跑 ＋ 通報 | 否 |
| `Rejected`（回寫被拒） | 續跑 ＋ 通報 | 是 |
| 五種正常判斷的 `reason_code` | 續跑，不通報 | 否 |

> **`ExternalError` 那一列先前漏了「＋ 通報」（reviewer iteration 1 Major，2026-08-29T15:26:59Z）。** 同表的 `Aborted`／`CannotCreate`／`Rejected` 三列都寫了通報，唯獨它沒有——而 U-5 的 R-1 表把 `ExternalError` 列為**無條件**「是通報」。[req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」保證因此在本單元的最主要失敗型別上落空。屬漏寫而非設計選擇，已補齊。

**「整輪中止」與「單一 intent 失敗」的分界**：`reverse_pending` 是**全輪共用的前提**，缺了它每一個 intent 的判定都不可信；單一 intent 的失敗只影響那一個。這個分界不是強度判斷，是**影響範圍**判斷。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| 無開啟中的反向 PR | `reverse_pending` 為空集合，一切照常 | R-2.4 |
| 反向 PR 含 intent X 不含 Y | X 暫停、**Y 照常寫** | R-2.2（[US:S-6 AC 3] 的反例要求） |
| 同分支高頻 push | 只保留一個 pending，第三個以後取消先前的 pending | R-1 的已知殘留（**不遺漏、只延遲**） |
| push 與同分支 PR 同時發生 | 落在同一 group，排隊不取消 | R-1.1／R-1.3 |
| 排程對帳同時在跑 | **可並行**，自成一組 | R-1.4（[req:NFR-P3]） |
| fixture record | 不在 registry，兩條路徑都不會選中 | R-3.3 |
| 回寫 commit 觸發 `ci.yml` | **不是本單元的責任**——歸 U-10a | R-5 |

## 與上游的對應

S-A 的生命週期、concurrency、選取分流、兩道防線與其代價逐字引自 [ad:services.md]；ADR-A10 的參數化要求引自 [ad:decisions.md]；元件職責與分層引自 [ad:components.md]，各元件的方法引自 [ad:component-methods.md]；[req:FR-A1]／[FR-A4]／[FR-C1]／[FR-G3]／[NFR-P3] 引自 `requirements.md`；[US:S-1 AC 1]／[US:S-2 AC 11–13]／[US:S-6 AC 3] 引自 `stories.md` 與 [ug:unit-of-work-story-map.md]；單元邊界、交付與完成判準引自 [ug:unit-of-work.md] 的 U-6。

**本檔對上游的補充**：缺口 F-4 的承接與其落點（一次查詢、fail-closed、不得偽裝），以及反向 PR 識別標記這個跨三單元契約（見 `domain-entities.md`）。**concurrency 字串、選取分流、兩道防線的層級一字未改。**

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:16:10Z
**Iteration**: 1

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| 1 | Critical | `business-logic-model.md:26-30`（序列圖「與 `sync-state.json` 比對」步驟）；`business-rules.md`（全檔無對應規則群） | **「有漂移才寫」的比對演算法整個未定義。** 序列圖把 `已綁定 → U-1 map(...) → 與 sync-state.json 比對 → 無漂移／有漂移` 畫成一個原子步驟，但全單元（`business-logic-model.md`、`business-rules.md`、`domain-entities.md`）沒有任何一條規則說明：(a) 誰呼叫 `read_sync_state`（U-1 的 `map()` 已在 iteration 1 被更正為不做任何 I/O，見 U-1 `domain-entities.md:66`；U-3 的 `write_status` 比對的是**看板現狀**`ItemState` 而非 `sync-state.json`，見 U-3 `business-rules.md` R-2 群；U-4 的 `business-logic-model.md:13-26` 資料流圖顯示 `read_sync_state` 是 **U-4 每次被呼叫時都會執行**的內部步驟，且圖上「本輪判定結果」直接流向 `write_sync_state`，沒有畫出「無漂移則不呼叫 U-4」的分支——代表「要不要呼叫 U-4」這道守門必須發生在 U-4 之外，只剩本單元)；(b) 比對哪些欄位（`Decision.status`／`field_value`／`reason_code` 三者是否都要與 `SyncState.last_status`／`last_field_value`／`last_reason_code` 逐一比對？任一不同即算漂移，還是只看 `status`？）；(c) 本單元若自己呼叫一次 `read_sync_state` 做比對，與 U-4 內部資料流圖裡**另一次** `read_sync_state` 是否為同一次呼叫、或是否接受兩次獨立讀取之間的競態視窗。本單元自陳「本單元的內容是順序、分流、與兩道自我排除」——這個比對正是「分流」的判斷依據，不是外部業務邏輯，理當由本站定義卻整份留白。這不是文字瑕疵：`business-rules.md` R-4.1「回寫 commit 的內容就是剛寫進看板的值 ⇒ 下一輪判定無漂移 ⇒ 不產生任何寫入——不依賴任何判斷」是本單元宣稱的核心不變式，它的成立與否**直接取決於**這個未定義的比較是否涵蓋 `field_value`。若一個自然但錯誤的實作只比對 `status`（三個值中最顯眼的一個），同一 Status 內的 stage 轉換（例如 `In progress` 從 stage A 換到 stage B）就不會被判為漂移，自訂欄位會靜默過期而 Status 不會，直接牴觸 [req:FR-A3] 與 `stories.md` S-5 的「這個欄位存在的目的是讓人看到哪一個 intent 走到哪一站」——且不會被任何紅燈或通報揭露，因為它落在「五種正常判斷」與「無漂移不寫」之間一個沒有規則覆蓋的縫隙。這正是本 intent 反覆出現、且 `project.md` 已明文記載的失敗模式（「狀態欄位三問：誰寫、誰讀、誰清，缺一即缺口」）在「誰讀＋怎麼比」這一問上的具體案例。 | 在 `business-rules.md` 新增一個規則群（例如接在 R-2 之後），明確定義：①本單元（不是 U-1、不是 U-4）在逐 record 迴圈內對已綁定者呼叫 `read_sync_state` 取得 `SyncState`；②逐欄比對 `Decision.status`／`field_value`／`reason_code` 與 `SyncState.last_status`／`last_field_value`／`last_reason_code`，三者任一不同即為「有漂移」；③說明這次讀取與 U-4 `business-logic-model.md` 資料流圖裡的 `read_sync_state` 是同一次呼叫（例如把 `SyncState` 沿呼叫鏈傳給 U-4，避免重讀）還是兩次獨立呼叫（若是，需比照 U-3 R-2.4 的做法明寫接受的競態視窗）。同時在「與上游的對應」補上對 [ad:component-methods.md] §C-4 的引用，讓 `upstream-coverage` sensor 能驗到這條路徑。 |
| 2 | Major | `domain-entities.md:15`；`functional-design-questions.md:40,44` | **D-1 裁定引用的技術理由「`branches-ignore` 讓 run 根本不被建立」經查證不成立，且已被同一 intent 的姊妹單元指出卻未回饋修正到本單元。** `domain-entities.md:15` 把「U-10b：`branches-ignore` 讓高成本 workflow 的 run 根本不被建立」當成分支名前綴的既定用途逐字寫進跨三單元契約表；`functional-design-questions.md:40` 的比較表對同一項打 ✅，:44 更把它寫成「單用 label 會讓 U-10b 做不到真正的排除——那是本項最強的約束，因此分支名前綴是必要的」，即 D-1 整個裁定的**唯一**強支撐理由（D-1 自己的表格顯示，U-6 查找與人一眼分辨兩欄都是 label 優於分支前綴，只有「U-10b 的排除」一欄支持分支前綴）。本次審查外部查證（GitHub 官方文件 workflow-syntax 頁與多個獨立來源交叉確認，見審查過程）：對 `pull_request` 事件，`branches`／`branches-ignore` 過濾的是 PR 的 **base** 分支，不是 head／來源分支。反向同步 PR 的 base 依 [req:FR-G1] 一律是 `ut`（與其他所有 PR 相同），因此對一個 `on: pull_request` 觸發的 workflow 加 `branches-ignore: [aidlc-sync/reverse/*]` **永遠不會排除任何 PR**——這條規則是死碼，不會讓 run「根本不被建立」，「同 U-10a 的 `paths-ignore`」這個類比本身也不成立：U-10a 自己的 `tech-stack-decisions.md:14-15` 實測記載 `ci.yml` 的 `pull_request` 觸發器「無任何 branches 或 paths 過濾」，因此**從未考慮**用 `branches-ignore`，直接採 `paths-ignore`。更關鍵的是：這不是本審查首次發現——U-10b 的 `nfr-requirements/tech-stack-decisions.md:26-45` 已獨立查證出同一個落差，明文寫「本單元不採用 `branches-ignore`……這與 D-1 的理由相左」，並把「`branches-ignore` 究竟過濾 base 還是 head」列為 PRE-1（Bolt 0）待實測項——但那份文件只更正了 **U-10b 自己**的技術選型，從未回頭修正 **D-1 本身**的敘述所在地（本單元）。依 `project.md` 已確立的處置模式（`functional-design:c22`「查證推翻的是選項的理由而非決定本身時，只修理由不改決定」），本單元本應在同一輪或下一輪同步補上更正說明，但至今兩處文件仍以「✅」的形式陳述一個已被證實不成立的技術事實。附帶：D-1／D-2 兩項裁定本身在 `functional-design-questions.md:26-28` 已明文自陳「這兩項原本要提問，使用者中止提問並指示繼續……它們不是人工裁決，不得被讀成使用者答過」——一個尚未經人工核可、且其中一項的核心理由已被證實錯誤的跨三單元契約，不應在未更正前視為可交付。 | 比照 U-10b 已示範的處置模式：在 `functional-design-questions.md` 的 D-1 段落補一段 Revision／更正附註，逐字記載「`branches-ignore` 對 `pull_request` 事件過濾的是 base 分支」這項已查證事實，並說明 D-1 的「分支前綴為必要」這個結論需要換一個站得住的理由（例如純粹的人一眼辨識與 `git branch` glob 便利性——即使這兩項在 D-1 自己的比較表中都判給 label 更優，「兩者並用」仍可能是合理的保守選擇，但論證必須誠實），或明確降級為「代價可接受、非嚴格必要」。同步修正 `domain-entities.md:15` 的「✅」斷言，避免任何下游讀者（含 U-6/U-8/U-10b 的實作者）把它當成已證實的事實。修法完成後，這兩項裁定應連同更正一併交付人工核可，而非停留在「使用者中止提問」的暫時狀態。 |
| 3 | Minor | `domain-entities.md:23-30` | `Config.reverse_pending`（本單元每輪即時計算、不落地）與 `sync-state.json` 的 `pending_reverse`（U-8 產生語意、U-4 持久化的欄位）是刻意不同的兩個概念，本檔已正確區分並明確聲明「本單元不寫此欄位」，與 U-1 `domain-entities.md:66`、U-4 `domain-entities.md:26` 三方一致，**這部分設計正確**。但兩者的命名僅是詞序對調（`reverse_pending` vs `pending_reverse`），對日後任何只讀一份文件的實作者或維護者構成不必要的混淆風險。 | 在 `domain-entities.md` 的 `Config` 組裝責任表後加一句顯式提示，例如：「不要與 U-8／U-4 的 `sync-state.json.pending_reverse` 混淆——後者是持久化、記錄人工變更的欄位；前者是本單元每輪即時算出、絕不落地的執行期集合。」降低未來誤植的機率。 |

### Validation Tool Results

本階段定義的驗證工具（`required-sections`／`upstream-coverage`／`linter`／`type-check`）為 sensor，非本次人工可直接執行的獨立指令；已以人工方式逐項核對其判準：`required-sections`（≥2 個 H2）三份產出檔皆遠超此門檻，通過；`upstream-coverage`（consumes: `unit-of-work`／`unit-of-work-story-map`／`requirements`／`components`／`component-methods`／`services`）逐一在「與上游的對應」段落核對，六項皆有 `[ug:...]`／`[req:...]`／`[ad:...]` 標籤引用，通過（但見 Finding 1：對 `component-methods.md` §C-4 的引用僅止於方法契約層級，未延伸到「誰在本單元呼叫它」這個關鍵細節）；`linter`／`type-check` 不適用——本產出不含 TypeScript/JavaScript 或 TSX 程式碼片段。

### Summary

本單元對 F-4 缺口的承接、`reverse_pending` 的 fail-closed 設計（D-2）、以及與 U-1／U-3／U-4／U-7／U-8 之間對 `Config.reverse_pending` 與 `sync-state.json.pending_reverse` 兩個概念的區分，經逐檔核對均與上游契約一致、可達、且無殘留矛盾。但本單元自陳擁有的「分流」邏輯中最關鍵的一步——「有漂移才寫」的比對演算法（誰呼叫 `read_sync_state`、比對哪些欄位）——整份文件未定義，使 R-4.1 這條核心不變式的成立與否無法驗證，一個自然的實作方式即可悄悄違反 [req:FR-A3]；同時 D-1 裁定賴以成立的關鍵技術理由（`branches-ignore` 對 `pull_request` 事件的過濾語意）經查證不成立，且已被姊妹單元 U-10b 獨立發現卻未回饋修正到本單元的原始文件。两者皆需在下一輪修正後再送審。

## Review (Iteration 2 — 雜湊與漂移比對的跨單元驗證)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T16:13:10Z
**Iteration**: 2
**涵蓋單元**: U-3 / U-4 / U-6 / U-8

> 本輪逐字重讀四單元的 `business-logic-model.md`／`business-rules.md`／`domain-entities.md`／`functional-design-questions.md`（U-3／U-4／U-8 三檔各自的既有 `## Review` 段落一併核對），並逐字重讀上游 `component-methods.md`、`components.md`、`decisions.md`（含其 iteration 3 驗證輪）、`bolt-plan.md`、`unit-of-work.md`、`unit-of-work-story-map.md`、`stories.md`、`requirements.md`。四項舊 Critical 在**技術內容**層面確有修正，但深入模擬「比對→寫入→回讀」的完整循環後，發現三個**新的**、獨立成立的 Critical，以及兩個 Major——分別落在四個單元之一或跨單元。

### 逐單元判定

| 單元 | Verdict | 說明 |
| --- | --- | --- |
| U-6 | **NOT-READY** | 2 Critical（新增 R-6.2 群對 AC 5 的告示機制實際上不會被觸發；R-5.4／R-7 群把 `render()` 的 `string` 輸出直接餵給要求 `Block` 的 `content_hash()`，型別未經核對）＋ 1 Major（R-6.1a 的 `resolve_if_open` 呼叫語意與其簽章矛盾） |
| U-3 | **NOT-READY** | 1 Critical（PRE-1-b 的傳遞管道經查證與其宣稱依循的 ADR-A2 先例不同構，`bolt-plan.md` 逐字核對後**仍未**含 PRE-1-b）＋ 1 Major（R-2.4 新理由本身站得住，但「必須在 Bolt 1 gate 揭露」未綁定到任何 DoD 條目） |
| U-4 | **NOT-READY** | 1 Critical（「U-7 補平後三欄過期但自癒」的推導經逐步模擬後不成立——下一輪 U-6 的回讀比對會因 `expected` 落在過期基準而回 `Aborted`，產生假的「回讀不符」issue，而非宣稱的冪等重寫） |
| U-8 | **READY** | 1 Major（`domain-entities.md` 的 `managed_block_hash` 四角色表把「產生」角色的擁有者誤標為「U-6」，應為「U-2」）；本身無 Critical，但**繼承** U-6 R-5.4／R-7 的型別缺口帶來的風險（見下方第 4 項），一併記錄供留痕 |

### 逐項查證（1–14）

**U-6**

1. **R-5.4 是否真的給了 `managed_block_hash` 一個寫者** — 是。`business-rules.md:75`（R-5.4：「看板寫入成功後，五欄一起回寫……以及 `managed_block_hash = content_hash(...)`」）與 `business-rules.md:97-112`（R-7 群，明確把 `read_sync_state`／`write_sync_state` 列為本單元對 C-4 的具名呼叫）互相印證；U-4 `domain-entities.md:32`（「`managed_block_hash` 的寫者是 U-6 的 R-5.4」）與 U-8 `domain-entities.md:15`（「寫入……現由 U-6 的 R-5.4 承接」）三方一致，寫者角色確實存在且具名可查。**無問題。**

2. **R-5.2 三欄比對與 R-4.1 核心不變式自己走一遍循環** — 對「正常」情境（回寫 commit 只觸及 `sync-state.json`／綁定編號，不觸及 `aidlc-state.md`）自洽：下一輪 `map()` 讀到的 record 不變 ⇒ `Decision` 不變 ⇒ 與剛回寫的 `last_status`／`last_field_value`／`last_reason_code` 逐欄相同 ⇒ `R-5.2` 判無漂移 ⇒ `R-5.5` 不寫，與 `R-4.1`「不依賴任何判斷」的宣稱相符。**但**深入模擬「R-6.2 的拒絕路徑」與「U-7 介入後的路徑」兩個情境時，這個循環會斷裂——見下方第 3 項與 U-4 第 9 項。

3. **R-6.2（[US:S-6 AC 5]）的歸屬論證與 `last_synced_at` 依賴** — **歸屬論證本身正確**：對照 `components.md:108`（`aidlc-sync-reverse.yml` 的元件鏈 `C-3(讀)→C-6(雜湊比對)→C-4(寫檔)→開 PR`，不含 `write_status`／`write_field`／`render`），U-8 結構上確實沒有任何寫回看板的路徑，AC 5 必須落在 U-6。這半沒有問題。

   **但 R-6.2 承載該 AC 的具體機制不成立，屬新的 Critical。** `business-rules.md:143`（R-6.2b：「對 `reverse_rejected` 內的 intent，本輪**照常覆寫**……但傳給 `render` 的 `Context` 須帶一則告示」）與同檔 `R-5.2`（:73，三欄比對）／`R-5.5`（:76，「無漂移時**不呼叫** `write_sync_state`……沒有東西要更新」）之間存在一個未被調和的矛盾：沿完整時序推演——PR 被拒（未合併）代表協作者對看板的改動從未進入 `ut`（依 U-8 `business-rules.md` R-6.0），亦即**record 本身自始至終沒有變過**；此時 `map()` 對該 intent 算出的 `Decision` 與上一輪機制自己寫入並記錄在 `SyncState.last_status`／`last_field_value`／`last_reason_code` 的值**完全相同**（因為 record 沒變）。依 `business-logic-model.md:26-31` 描繪的執行序列（「三欄比對 → 無漂移 → 不寫（防線①在此生效）」），這正是防線① R-4.1 要保底的情境——三欄比對判定**無漂移**，於是走 R-5.5 的「不呼叫 `write_sync_state`」分支，**整條 `U-3 write_status／write_field → U-2 render → U-4 write_sync_state` 的寫入鏈根本不會被觸發**。R-6.2b 所稱的「本輪照常覆寫」因此無從發生——沒有任何規則說明 `reverse_rejected` 成員身分應該**繞過**或**強制蓋過** R-5.2／R-5.5 的無漂移不寫閘門；`render` 從未被呼叫，帶告示的 `Context` 也就無處遞交。後果：AC 5 要求的「未被採納」記錄在最常見的情境（PR 關閉期間 record 未被其他事件觸碰）下**永遠不會出現在受管區塊**，[US:S-6] 的 benefit clause「送到人面前決定」在拒絕路徑上重新變回空話——正是這一輪修正意圖關閉、卻沒有真正關閉的那個缺口。

   **`last_synced_at` 依賴（任務指定要核對的子問題）**：R-6.2c（:146）以「PR 關閉時間晚於 `last_synced_at`」判定告示是否已出現過，並自陳「兩條規則互相依賴，缺一即失效」。R-5.4 本身確實存在（第 1 項已驗證），所以*如果*寫入真的發生過，`last_synced_at` 會被可靠回寫，不構成獨立的雞生蛋問題。**但這只是把問題往後推一層**：既然上述寫入鏈在典型情境下根本不會被觸發，`last_synced_at` 也就永遠停在 PR 開啟之前的舊值，於是 R-6.2c 的判定基準「PR 關閉時間 > `last_synced_at`」會在**每一輪**都持續成立（因為 `last_synced_at` 從未更新），該 intent 會永遠留在 `reverse_rejected` 集合中、R-6.2b 每輪都嘗試「照常覆寫」卻每輪都被 R-5.5 擋下——不是「告示重複出現」（原文擔心的方向），而是「告示永遠不出現，且這個嘗試會無聲地每天重跑一次而沒有任何紅燈或通報」。

4. **R-6.1（`resolve_if_open` 的呼叫者）與 R-7 群（呼叫的上游方法具名表）**

   - **R-6.1a 呼叫語意矛盾（Major）**：`business-rules.md:124`（「逐 record 迴圈結束之後**呼叫一次** `resolve_if_open`」）與 `component-methods.md:114-115`（`resolve_if_open: (FailureIdentity) -> `；`FailureIdentity = { intent_id, reason_code }`）對照，`resolve_if_open` 的簽章要求呼叫者提供**一個特定的 `(intent_id, reason_code)` 鍵**才能查找、關閉對應的通報 issue——它沒有「不帶鍵、關閉全部」的多載形式。「呼叫一次」在字面上讀不出這個鍵從何而來、要對哪些 `(intent_id, reason_code)` 組合各呼叫一次。更值得注意的是 `business-rules.md:125`（R-6.1b）明文主張「逐 intent 判斷會把『這一個好了』誤讀為『問題解決了』」，語氣上是在**排斥**逐 intent／逐鍵呼叫——但 `resolve_if_open` 的 API 形狀恰恰只能逐鍵呼叫，兩者直接衝突。這不是純措辭問題：一個依字面實作的開發者，要嘛猜一個列舉策略（例如對本輪所有處理成功的 intent、逐一嘗試各種 `reason_code` 呼叫 `resolve_if_open`），要嘛真的只呼叫一次卻不知道傳什麼鍵而卡住——這正是 `project.md`（`functional-design:user-1`）點名要求逐一核對的「契約端點是否真的有具名呼叫者」，本條雖有呼叫者但呼叫方式本身未定義完整。

   - **R-7 群的 `render`／`content_hash` 型別未核對（新 Critical）**：`business-rules.md:110`（R-7 群：「`render(Decision, Context) -> string` / `content_hash(Block) -> sha256` | **C-6** | 受管區塊的渲染與其雜湊（供 R-5.4 回寫）」）與 `component-methods.md:137-139` 逐字核對：`render: (Decision, Context) -> string`，`content_hash: (Block) -> sha256`——`content_hash` 的參數型別是 `Block`，不是 `string`；`Block` 這個型別在 `component-methods.md` 開頭的「共用型別」區塊**完全沒有定義**，全份契約中它只出現在 `parse: (issue_body) -> Block | null` 的回傳型別與 `content_hash` 的參數型別兩處。`R-5.4`（`business-rules.md:75`）與 `R-7` 都把 `content_hash` 直接套用在「剛由 U-2 `render` 產生」的東西上——即把 `render()` 回傳的 `string` 當作 `content_hash()` 要求的 `Block` 直接餵入，中間**沒有**經過 `parse()` 這一步。對照 U-8 自己的用法（`business-rules.md` R-4c：`parse(issue_body) -> Block` **然後** `content_hash(Block) -> sha256`，兩者型別完全銜接），U-6 這裡跳過了 `parse()`，型別上是否成立完全未被本站或任何上游文件核對過。這不是吹毛求疵：**這個雜湚必須與 U-8 日後讀回同一顆 issue、經 `parse(issue_body) -> Block -> content_hash` 算出的雜湚逐位元組相等**，整套「內容雜湚比對防迴圈」機制（`[req:FR-G4]`、`[ad:ADR-A6]`：「格式一旦上線即為契約……這是本設計最不易反轉的決定」）才站得住。若 `render()` 產生的字串與「該字串被 GitHub 儲存後再被 `parse()` 解析出的 `Block`」在正規化上有任何差異（例如換行符、markdown 轉義、HTML 註解排版），U-6 用「捷徑」（跳過 `parse` 直接雜湚）算出的值就會與 U-8 用「完整回讀路徑」（`read_item → parse → content_hash`）算出的值永久不相等——即使**沒有任何人為變更**，U-8 的 R-1.1 每天都會判定「有人改過」，對**每一個**受管 intent 各開一則反向 PR。這正是 `decisions.md` ADR-A6 自己點名的「本設計最危險的單一失誤模式」，只是觸發條件從「格式變更未重新基準化」換成「每一次正常的機制寫入本身」。四單元的產出中沒有任何一處明寫「`render()` 的輸出與 `parse()` 解析回來的 `Block` 在雜湚意義下等價」這個關鍵不變式，也沒有任何一處指派誰去驗證它。

5. **D-1 的 `branches-ignore` 降級傳播** — `domain-entities.md:21-25` 與 `functional-design-questions.md:44-46` 兩處逐字核對：更正時間戳（`2026-08-29T15:21:33Z`）相同、論證完全一致（`branches-ignore` 過濾 base 非 head → 反向 PR 的 base 一律 `ut` → 該過濾器不排除任何 PR → 裁定不改、理由降級為「代價可接受的附加」）。**傳播完整、誠實，無問題。**

**U-3**

6. **R-2.4「兜底」新理由是否站得住** — 新理由（`business-rules.md:53`：「Projects v2 沒有 compare-and-swap，唯一的替代是樂觀鎖式的『寫後再回讀比對、不符就重試』，那會把每次寫入的 API 呼叫數加倍並引入重試迴圈，對一個視窗寬度約為單次 mutation 往返時間的競態而言不成比例」）**技術上站得住**——這是誠實的工程取捨，且明確承認「這是一條使用者從未被告知的真實資料遺失路徑」，不是文過飾非。**但（Major）**：同一句話要求「這個代價必須在 Bolt 1 的 gate 被揭露」，卻沒有綁定到任何具體機制——`bolt-plan.md`（本輪重讀全文）Bolt 1 的 Definition of Done（「七個單元各自的完成判準……全部通過；`stories.md` 全域 DoD 中適用於本 Bolt 的項目……成立；PRE-1 第 1／3／4 項已綠」）**完全沒有**一條對應「揭露 write_status 回讀視窗的資料遺失風險」的條目。這與同一份文件（見下一項）自己成功示範過的正確做法（PRE-1-b 明確指名落點與確認人）形成對比——同一輪修正對兩個同樣重要的殘留風險採用了兩種不同嚴謹度的處置。

7. **PRE-1-b 的追加與指派是否與 ADR-A2 先例同構（新 Critical）** — 不同構，這是本輪送審前**必須**查證、且查證結果與其宣稱相反的一項。`decisions.md`「本站對 PRE-1 的追加實測項」（PRE-1-a）與 `bolt-plan.md` Bolt 0 的 PRE-1 表逐字核對：**PRE-1-a 之所以能被 `bolt-plan.md` 直接接住，是因為 `decisions.md`（application-design 的產出）在 `delivery-planning` 執行、`bolt-plan.md` 成文**之前**就已經定案**——`delivery-planning` 撰寫 `bolt-plan.md` 時，`decisions.md` 的追加段落是它讀得到、且理應併入的既有上游輸入。而 U-3 的 PRE-1-b 是在 **functional-design**（construction 階段、`delivery-planning` 之後）才被提出的，此時 `bolt-plan.md` 早已是一份成文（且推定已核可）的 inception 產出——它不會因為下游某個 per-unit functional-design 站新增了一段文字就自動改寫自己。`business-rules.md:63`（「本項刻意沿用同一形狀，因為那個管道已被證明會被接住」）這句話**把「這個形狀曾經有效」誤讀成「這個形狀在任何時間點使用都有效」**，忽略了兩者發生的階段順序完全不同。本輪重讀全份 `bolt-plan.md`：Bolt 0 的 PRE-1 表**確實只有 1、2、3、4、PRE-1-a 五列**，`bolt-plan.md:17` 的敘述文字也逐字停在「五項實測各一份記錄」——**沒有 PRE-1-b**。`business-rules.md:61`（「指派：`delivery-planning/bolt-plan.md` 的 PRE-1 表與 Bolt 1 的 DoD。確認人為 Bolt 0 的 gate」）雖然把落點與確認人都寫清楚（**形式**正確、且與 U-6 R-6.2 對 story-map 的指派手法一致），但**沒有任何機制保證**會有人真的回頭改 `bolt-plan.md`——它不是一個 CONDITIONAL、會再被自動跑一次的 stage，是一份已經定稿的檔案。若沒有人在 Bolt 1 開工前主動重新開啟並編輯 `bolt-plan.md`，`Issue.projectItems` 這個本 repo 從無先例、`read_item`／`write_status`／`create_item`／`write_field` 全部經由它的核心查找路徑，就會在完全未經一次真實呼叫驗證的情況下隨 Bolt 1 依 `deploy-on-merge` 直接上線——這正是本項存在的理由所要防止的事，而目前的傳遞方式**沒有真正防住它**。

8. **`read_item` 的 `ExternalError` 「混合形狀」是否與上游相符** — 相符。`component-methods.md:86`（C-3 `read_item`：「API 錯誤 → **拋** `ExternalError{http_status}`」）與 `write_status`／`write_field`／`ensure_field` 三者一致使用「回」（`:88-90`）；`WriteResult = Written | Aborted{...} | Failed{...}` 定義（`:25`）本身就不含 `ExternalError`，佐證它走例外路徑而非回傳值。U-3 `business-logic-model.md:61-65` 的更正（「正確的形狀是混合的：`Aborted`／`Failed`／`CannotCreate` 是回傳值……`ExternalError` 是例外」）與上游逐字相符。**無問題。**

**U-4**

9. **「U-7 補平後三欄過期但自癒」推導（新 Critical）** — 推導不成立。逐步代入 R-2.1（U-3 `business-rules.md:23`：「`write_status` 必先 `read_item`；`actual != expected` → 回 `Aborted{actual, expected}`，不送出寫入」）與 U-6 的執行序列（本單元不獨立呼叫 `read_item`，`expected` 只能來自 R-5.1 讀到的、尚未更新的 `SyncState`）：
   - U-7 對帳補平時直接呼叫 `write_status` 把看板寫成新值 X'，**不經 C-4**（`components.md:107`：`C-7 →（內部）C-2／C-1／C-3／C-5`，不含 C-4），所以 `sync-state.json` 的 `last_status` 仍停在補平前的舊值 X。
   - 下一次事件觸發 U-6：`read_sync_state` 讀到 `last_status = X`（過期）；`map()` 算出的 `Decision` 若與 X 不同（無論是因為 X 本來就跟 record 不一致、還是 record 又有新變化），R-5.2 判為有漂移，於是呼叫 `write_status(binding, expected=<由 X 重建的 ItemState>, desired=<新 Decision>)`。
   - 但看板此刻的**實際值**是 U-7 剛補平的 X'（可能等於也可能不等於新 Decision），`write_status` 內部的 `read_item` 讀到 `actual = X'`，與呼叫端傳入的 `expected(=X)` **不相等** → 依 R-2.1 回 `Aborted{actual: X', expected: X}`，**不送出寫入**。
   - 依 `component-methods.md:88` 與 `[req:FR-C1]`／[US:S-3 AC 1]，`Aborted` 會觸發「產生一則記錄該不符的 issue」——即使看板此刻的值（X'）其實已經是正確的（U-7 剛修好），或即使新 Decision 剛好等於 X'（寫入本應是 no-op），這條路徑都會被判定為「回讀不符」並開一則**假的**通報 issue。

   這不是罕見的競態視窗，而是 U-7（每日排程、`Bolt 2` 交付）與 U-6（事件驅動）**正常運作下的必然後果**：只要 U-7 曾經對某個已綁定 intent 執行過一次補平（這正是 U-7 存在的理由），該 intent 的下一次 U-6 事件觸發幾乎必然撞上這個過期 `expected` 基準，產生一則與事實不符的「回讀不符」通報。`domain-entities.md:27`（「下一次事件觸發時 U-6 判為有漂移，重寫一次相同的值（冪等），並順帶更新這三欄——自癒」）與 U-6 `business-rules.md:92`（同一段推導的複本，「下一次事件觸發時本單元會判為『有漂移』而重寫一次相同的值——冪等、無害」）**兩處都聲稱這是無害的冪等重寫**，但依 R-2.1 的回讀比對語意，這裡走的不是「重寫成功」而是「`Aborted` ＋ 假通報」。此為兩個檔案共享的同一個錯誤推導，非各自獨立的問題。

10. **「reconcile 不重寫受管區塊所以雜湚不受影響」對 `components.md` 的核對** — 正確。`components.md:107`（`aidlc-sync-reconcile.yml` 的元件鏈 `C-7 →（內部）C-2／C-1／C-3／C-5`）確實不含 C-6，佐證 U-4／U-6 的「reconcile 不碰受管區塊、`managed_block_hash` 不受影響」的推論。**無問題**（但注意：此結論的正確性不影響第 9 項——第 9 項的問題出在 `last_status` 等三欄，不在 `managed_block_hash`）。

11. **R-3.1 移除「／U-7」是否正確** — 正確。`components.md:107` 的元件鏈確認 reconcile 不含 C-4，U-4 `business-rules.md:40` 的更正與此一致；U-7 從無管道呼叫 `commit_and_push`。**無問題。**

**U-8**

12. **AC 5 歸屬論證對 `components.md` 的核對** — 正確。`components.md:108`（反向同步的元件鏈 `C-3(讀)→C-6(雜湚比對)→C-4(寫檔)→開 PR`）不含 `write_status`／`write_field`／`render`，U-8 結構上確實沒有寫回看板的路徑。`business-rules.md` R-4b 的歸屬更正論證成立。**無問題**（但其承接方——U-6 的 R-6.2——本身有第 3 項指出的 Critical，此為下游繼承的風險而非本單元自身的缺陷）。

13. **`managed_block_hash` 四角色表是否與 U-6 R-5.4 一致（Major）** — 「寫入」角色的敘述（`domain-entities.md:15`：「先前無人 → 現由 U-6 的 R-5.4 承接……」）與 U-6 `business-rules.md:75` 逐字相符，**這半正確**。但「產生」角色（`domain-entities.md:13`：「U-3 讀看板時，由 **U-6** 的 `parse` ＋ `content_hash` 算進 `ItemState`」）有事實錯誤——依 `unit-of-work.md`（「U-2 — 受管區塊渲染與雜湚 | 擁有 | [ad:C-6 `managed-block`] 的 `render`／`parse`／`content_hash`」）與 `components.md`（C-6 `managed-block` 屬呈現層，`### C-2 record-reader` 段明確標示 C-2 屬 U-1），`parse`／`content_hash` 屬 **C-6**，其擁有單元是 **U-2**，不是 U-6。這與 U-8 自己 `business-rules.md` R-4c（正確標為「C-6」、且已在本輪同一份文件中專門更正過「先前誤標為 C-2」）在同一個單元、相鄰段落卻給出不一致的歸屬——`business-rules.md` 正確地把方法對應到元件代號「C-6」，`domain-entities.md` 卻把它誤植為單元代號「U-6」（疑似 C-6／U-6 或 U-2／U-6 打字時混淆）。這正是本站「managed_block_hash 四角色」表存在的目的——防止角色歸屬混亂——結果表格自己出現了同型錯誤。

14. **R-4c「五個」與 `parse`／`content_hash` 改標 C-6 是否正確** — 正確。`business-rules.md` 標題現讀「本單元呼叫的**五個**上游方法」，表列 5 列（`read_item`、`parse`、`content_hash`、`write_sync_state`、`commit_and_push`）與標題一致；`parse`／`content_hash` 兩列的元件欄現讀「**C-6**」，與 `component-methods.md:137-139`（C-6 `managed-block` 的 `render`／`parse`／`content_hash`）相符。**無問題。**

### 新引入的問題

以下三項為本輪修正（`R-6.2` 群、`R-7` 群、`PRE-1-b`）在解決 iteration 1 已點名的缺口時，**修法本身**帶入的、先前未被抓到的問題：

1. **U-6 R-6.2（AC 5 的告示機制）與 R-5.2／R-5.5（無漂移不寫閘門）互相矛盾，導致 AC 5 在典型情境下永遠不會被滿足** ——見「逐項查證」第 3 項。這是本輪新增的 R-6.2 群自己引入的問題，不是 iteration 1 遺留。
2. **U-6 R-7 群把 `render()` 的 `string` 輸出直接餵給要求 `Block` 的 `content_hash()`，型別未經核對，可能使 U-6 記錄的雜湚與 U-8 日後回讀計算的雜湚永久不相等** ——見「逐項查證」第 4 項第二子點。R-5.4 的具體寫法源自 iteration 1，但 R-7 群（本輪新增，`2026-08-29T15:28:15Z`）把這個呼叫路徑第一次明確具名化，使這個先前被忽略的型別缺口第一次變得可核對、也因此第一次被抓到。
3. **U-3 PRE-1-b 的傳遞管道與其宣稱依循的 ADR-A2／PRE-1-a 先例不同構** ——見「逐項查證」第 7 項。這是本輪新增的段落，其論證方式本身建立在一個不成立的類比之上。

以下一項是 iteration 1 的修正遺留至今、本輪深入模擬多輪循環後才發現的問題，非本輪新增，但先前四輪 reviewer（U-3／U-4／U-6／U-8 iteration 1）均未發現：

4. **U-4「U-7 補平後自癒」的推導（`domain-entities.md`）與 U-6 `business-rules.md` 的同一段複本，兩處共享同一個不成立的回讀比對推導** ——見「逐項查證」第 9 項。

## Review (Iteration 3 — 驗證輪)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T00:14:43Z
**Iteration**: 3
**涵蓋單元**: U-3 / U-4 / U-6 / U-8

> 本輪逐字重讀四單元的四份產出、U-2 的四份產出（為核對 `Context.rejection_notice` 這個整合點），以及上游 `component-methods.md`、`components.md`、`bolt-plan.md`、`requirements.md`、`stories.md`、`ADR-0015`。**iteration 2 點名的 5 項與送審前自檢的 6 項逐項查證：12 項通過、3 項未通過。** 另發現 **3 個 Critical**，其中兩個是**修正動作本身引入或遺留**的——與 iteration 2 的形狀完全相同。

### 逐單元判定

| 單元 | Verdict | 理由（一句） |
| --- | --- | --- |
| U-6 | **NOT-READY** | 3 Critical（R-5.7 把 `write_status` 的回讀守門化為恆真，使 FR-C1／FR-C3／S-3 AC 1 不可滿足；序列圖與文字 fallback 仍載已撤回的 `render → content_hash`；受管區塊無寫者）＋ 1 Major（`Decision.status = null` 進入寫入鏈時無規則且型別不合） |
| U-3 | **NOT-READY** | 1 Critical（本單元被 U-2／U-6 兩處指名為受管區塊的寫者，但其六個方法無一能寫 issue body）＋ 1 Major（`business-logic-model.md:44` 仍逐字保留 `business-rules.md` R-2.4 已撤回的「反向同步兜底、只是慢一輪」） |
| U-4 | **NOT-READY** | 本輪的自癒更正把成立條件整個掛在 U-6 的 R-5.7 上（`domain-entities.md:27` 逐字），而 R-5.7 本身是 Critical ⇒ 該更正連同它一起失效，不是「已修好」 |
| U-8 | **READY（附 2 項必修）** | 四角色表的「產生 → U-2」與「寫入 → 回讀」兩處已正確；但 D-1 的 `branches-ignore` 更正未傳播到本單元（2 處），且 ADR-0015 §5 為反向路徑補的 C-5 在本單元無任何落點。**另注意**：C-3 成立時本單元 R-1.1 的比對基準恆為 `null`，核心機制不可運作——缺陷不在本單元檔內，但阻擋本單元交付 |

### 逐項查證（iteration 2 的 5 項 ＋ 送審前自檢的 6 項）

| # | 查證項 | 結論 | 依據（檔案:行 ＋ 引文） |
| --- | --- | --- | --- |
| 1 | R-5.6 是否真的讓 AC 5 的告示鏈可被觸發 | **通過（但被 C-3 架空）** | `business-rules.md:84` R-5.6 第二子句可達性經時序推演成立：PR 開啟期間 `map()` 回 `suppressed` ⇒ 三欄有差異 ⇒ 寫入 ⇒ `last_synced_at = T2`；PR 於 T3 > T2 關閉 ⇒ 下一輪 `closed_at > last_synced_at` 為真 ⇒ 告示待送。**規則本身可達。** 但告示的載體是受管區塊，而該區塊無寫者（見 C-3），故 AC 5 仍不可滿足 |
| 2 | R-6.2c 的 `last_synced_at` 判準是否可達、是否會永遠成立 | **通過** | iteration 2 擔心的「`last_synced_at` 永不前進 ⇒ 每輪重試」已由 R-5.6 解掉：告示本身即寫入理由 ⇒ R-5.4 回寫 `last_synced_at` ⇒ 下一輪判準轉偽 ⇒ 離開集合。單向收斂，非死迴圈 |
| 3 | R-5.4 改以「寫入後回讀」取值，型別是否銜接 | **通過** | `component-methods.md:24`（`ItemState = { status, field_value, managed_block_hash, issue_number, issue_state }`）確有 `managed_block_hash` 欄位；`:86`（`read_item: (binding, Config) -> ItemState`）。`business-rules.md:75` 的新寫法型別成立，且與 U-8 `read_item → parse → content_hash` 同路徑，等價性確由構造保證 |
| 3b | 「寫入後回讀」是否存在讀到舊值的風險 | **通過（不升為發現）** | 兩端走同一條讀取路徑；即使該次回讀讀到舊值，U-8 日後讀到的是穩定後的新值 ⇒ 兩值不等 ⇒ 開一則反向 PR。這是**單次、可自癒**（下一輪 U-6 寫入後重新對齊）的偽陽性，不是 ADR-0015 §10 所述的**永久**不相等。低於 Minor，記錄供 U-9 端到端斷言參考 |
| 4 | PRE-1-b 改由 ADR-0015 §1／§2 承載是否為有效管道 | **通過** | `bolt-plan.md` Bolt 0 的 PRE-1 表**仍只有 1／2／3／4／PRE-1-a 五列**（本輪逐字重讀確認），但 ADR-0015 以指標方式修訂、Status `Accepted`，且 `project.md ## Mandated` 有一條強制規則要求把 `inception/decisions/` 的既有 ADR 納入唯讀查證範圍——這是 `bolt-plan.md` 內的一句話所沒有的機制性可達性。先例為同 intent 的 ADR-0014。**指派不再是沒有收件人的便條** |
| 5 | U-8 四角色表的「產生」是否已由 U-6 改為 U-2 | **通過** | `U-8/domain-entities.md:13`：「產生 \| U-3 讀看板時，由 **U-2**（C-6 `managed-block`）的 `parse` ＋ `content_hash` 算進 `ItemState`」，與 `unit-of-work.md` U-2 段、`components.md` C-6 一致 |
| 6 | U-8 `domain-entities.md` 的「寫入」列是否已改為回讀取值 | **通過** | `:15`：「現由 **U-6 的 R-5.4** 承接：看板寫入成功後**再呼叫一次 `read_item`**，取其回傳 `ItemState` 的 `managed_block_hash` 欄位回寫」，與 `U-6/business-rules.md:75` 逐字一致；`:18-20` 的說明理由正確 |
| 7 | U-3 R-2.4 反證步驟 4 的新寫法（「回讀的時點在覆寫之後」）結論是否仍成立 | **通過** | 自行重走時間軸：協作者的 Y 在步驟 2 寫入 → 步驟 3 mutation 覆寫為 X → R-5.4 的回讀發生在**步驟 3 之後**，讀到的是 X → 記錄的雜湊為 X 的 → 下一輪 U-8 讀到看板現況亦為 X → 相同 → 不開 PR。**「Y 被靜默丟失、反向同步永遠抓不到」在新版 R-5.4 之下仍然成立**，理由改寫（「沒有回讀」→「回讀的時點在覆寫之後」）是正確的 |
| 8 | U-6 `Config` 組裝表補 `reverse_rejected` 後欄位數是否正確 | **通過（附 m-2）** | 實算：U-1 `domain-entities.md:63-68` 定義 4 欄（`whitelist`／`reverse_pending`／`record_root`／`field_max_length`）＋ U-6 的 `reverse_rejected` = **5**，與 `U-6/domain-entities.md:33` 的「合計 **五個**」相符 |
| 9 | R-6.2b 具名化為 `Context.rejection_notice` 後，讀者是否存在 | **通過** | `U-2/domain-entities.md:44`（`rejection_notice` 欄位定義，「由 U-6 的 R-6.2b 填入」）＋ `U-2/business-rules.md:15`（R-1.5 渲染規則，含「`null` 支的輸出與 R-1.5 引入前逐字相同」的可判定方式）。**契約兩端齊備**，且同批交付約束（兩者同為 Bolt 1）在兩檔各有一份 |
| 10 | R-6.2／AC 5 的 story-map 歸屬指派改引 ADR-0015 §4 | **通過** | `ADR-0015:34-36` §4 逐字承載該歸屬更正；`U-6/business-rules.md:171` 與 `U-8/business-rules.md:103` 兩處引用一致 |
| 11 | U-8 對 U-4 的 `pending_reverse` 指派由「待辦」改為「已承接」 | **通過** | `U-8/domain-entities.md:38`、`U-8/functional-design-questions.md:43` 均改為「已由 U-4 承接／早已落地」，與 `U-4/domain-entities.md:35` 的 schema 表列相符 |
| 12 | U-3 複雜度由「最重的」改為「並列兩個 L 級之一」 | **通過** | `U-3/business-logic-model.md:9` 與 `U-3/functional-design-questions.md:14` 措辭一致，與 `unit-of-work.md` 的 U-3／U-7 皆為 L 相符 |
| 13 | **R-5.7／R-5.8 是否真的修好了 U-4 的自癒推導** | **未通過（Critical C-1）** | 見下方 |
| 14 | **R-5.4 的更正是否傳播到本單元的序列圖與文字 fallback** | **未通過（Critical C-2）** | 見下方 |
| 15 | **`render` 的輸出由誰寫進 issue body** | **未通過（Critical C-3）** | 見下方 |

### 新引入的問題（本輪修正動作造成）

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| **C-1** | **Critical** | `U-6/business-rules.md:102-103`（R-5.7／R-5.8） | **R-5.7 把 `write_status` 的回讀守門變成恆真，使 FR-C1／FR-C3／S-3 AC 1／AC 2 全部不可滿足。** R-5.7 逐字：「進入寫入鏈前呼叫 `read_item(binding, Config)` 取得**當下**的 `ItemState`，以它作為 `write_status` 的 `expected`」。而 `write_status` 內部「必先回讀」再與 `expected` 比對（`component-methods.md:88`）——當 `expected` 本身就是幾百毫秒前的一次 `read_item` 結果時，`actual != expected` 只可能在 U-3 R-2.4 明文宣告**不設防、不可測試**的那個視窗內成立。`Aborted` 因此在實務上不可達，正是 `project.md` 的 `functional-design:c10` 所指的「偵測 X 狀態而 X 不可達」。**三份已核可上游直接反證這個語意**：①`stories.md:237` 逐字「P2 每一次正常使用看板（拖動卡片）……正向同步會**先讀到 P2 的值、判定不符、走 S-3 AC 1**」——它預設 `expected` 是機制上次寫入的值，不是當下看板值；②`requirements.md:73`（FR-C3）逐字「**後到者的回讀比對會偵測到前者已寫入的結果**，並依 FR-C1 的唯一結果處置：中止寫入並開 issue」——在 R-5.7 之下後到者的 `expected` 已含前者的結果，永遠偵測不到；③`requirements.md:71`（FR-C1）「不符即**中止寫入**並開 issue」。後果不是理論的：協作者在看板上改一格、同時 record 有變更（=有漂移），機制會**直接輾過去且不留任何痕跡**（無 `Aborted`、無 issue、無反向 PR——R-5.4 同輪把雜湊基準重置為機制自己的值），正是 [US:S-6] 存在的唯一理由。**連帶死碼**：`ReconcileReport.aborted`（`component-methods.md:159`）、`stories.md:264` S-9 AC 2 的第三份清單、`U-6/business-logic-model.md:70` 錯誤表的 `Aborted` 列，全部指涉一個不會發生的狀態。**這是修正 iteration 2 Critical #9（U-7 補平後的假通報）時引入的**：把「假陽性」換成了「所有真陽性一起消失」。修法方向：`expected` 仍取自 `SyncState` 三欄，另行處理 U-7 補平造成的過期（例如 U-7 亦回寫 `SyncState`，或 U-6 在 `actual != expected` 但 `actual == 新 Decision` 時判為「已被補平」而非 `Aborted`），而非取消守門本身。**任何改變已核可 AC 可滿足性的裁定須循 ADR-0015 的形狀開 ADR，不得只寫在單元規則裡** |
| **C-2** | **Critical** | `U-6/business-logic-model.md:31`、`:39` | **本檔的序列圖與文字 fallback 仍載已於 2026-08-29T16:19:47Z 撤回的 R-5.4 舊寫法。** `:31` 逐字「`└─► U-2 render ──► content_hash`」；`:39` 逐字「把五個欄位（含**剛寫進看板那份受管區塊的雜湊**）回寫」。兩處都是「對剛渲染的東西算 `content_hash`」，即 `business-rules.md:77-82` 明文撤回的那條路徑（型別不成立＋等價性失效）。**這一處的嚴重性不低於 U-8 那一處**：`U-8/domain-entities.md:18-20` 為同型殘留寫下「**這一處尤其不能留舊說法**……讀本檔的人會據此實作出一條與 U-6 不同的路徑」，而 U-6 **就是**寫入端本身，其序列圖是實作者取用時序的第一份文件。依 ADR-0015 §10，該路徑失效的後果是「沒有任何人為變更的情況下，U-8 每天為每個受管 intent 各開一則反向 PR」。順帶：序列圖也未反映 R-5.7 的寫入前 `read_item` 與 R-5.6 的第二個寫入理由，三處合計使該圖與 R-5 群整組不一致 |
| **C-3** | **Critical** | `U-2/business-logic-model.md:21`、`U-2/domain-entities.md:77`、`U-6/business-rules.md:169`、`U-3` 三份產出全檔 | **受管區塊沒有寫者——`render() -> string` 的輸出在全 stage 產出中沒有任何具名的持久化者。** 三方互相指認而無一成立：①`U-2/business-logic-model.md:21` 逐字「`render ─► 區塊文字 ──► （U-3 寫進 issue body）`」、`U-2/domain-entities.md:77` 逐字「issue body 中的受管區塊文字（**U-3 寫**）」；②但 `U-3/business-logic-model.md:7` 逐字列出本單元的**六個**方法「`read_item`、`create_item`、`write_status`、`write_field`、`ensure_field`、`read_issue_state`」，U-3 三份產出**零次**提到寫 issue body；③`U-6/business-rules.md:169` 逐字「受管區塊的寫入路徑是 `U-2 render → U-3 write_field`」，但 `component-methods.md:89` 的 `write_field: (binding, value) -> WriteResult` 目的欄逐字是「**自訂欄位寫入**」、錯誤處理是「欄位不存在 → 嘗試建立」（即 `ensure_field` 建的 Projects v2 自訂欄位），而 `component-methods.md:57-58` 明訂該自訂欄位「**長度上限 50 字元**」且「**完整敘述一律在受管區塊**……兩處不一致時以受管區塊為準」——自訂欄位與受管區塊是被上游明文區分的兩個東西。`components.md` §C-3 的公開介面同樣沒有任何寫 issue body 的方法。**後果**：`read_item` 回傳的 `managed_block_hash` 恆為 `null`（`U-3/business-logic-model.md:76` 逐字：「issue body 無受管標記 → `managed_block_hash` 為 `null`」），於是 R-5.4 每輪把 `null` 寫進 `SyncState`，U-8 的 R-1.1 拿 `null` 比 `null` 恆相同 ⇒ **反向同步（FR-G 全組、S-6 全部 AC）永遠不觸發**；同時 [US-OQ-3]、[req:FR-F3]、[req:FR-G4]、以及本輪剛修好的 R-5.6／R-6.2b／U-2 R-1.5 這條 AC 5 告示鏈**全部沒有載體**。**這是被本輪修正掩蓋的缺口**：R-5.4 舊寫法至少讓 `render()` 的輸出有一個消費者（`content_hash`），改為回讀取值之後，`render` 的輸出在整份設計中**再也沒有任何具名去處**——`project.md` 送審前自檢第 2 項（契約端點三問，範圍為整個 stage 產出）本應在此觸發。修法：在本 stage 或以 ADR 指名 C-3 增設一個寫 issue body 的方法（例如 `write_body(binding, block_text) -> WriteResult`），並更正 U-2／U-6 兩處互相矛盾的歸屬敘述 |

### 其餘發現

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| M-1 | Major | `U-3/business-logic-model.md:44`；`U-3/functional-design-questions.md:52` | **R-2.4 已撤回的「反向同步兜底」在同一單元的另外兩處原樣留存。** `U-3/business-rules.md:35` 逐字承認該宣稱「經 reviewer iteration 1 沿時間軸重演後**不成立**，已於 2026-08-29T15:23:54Z 更正」，但 `business-logic-model.md:44` 仍逐字寫「承接方式是下一輪反向同步的受管區塊雜湊比對——[US:S-6] 的『送到人面前決定』仍然成立，**只是慢一輪**」。`business-logic-model.md` 是本單元的主敘事檔，單獨查閱者會得到與 iteration 1 Critical 完全相同的錯誤印象。`functional-design-questions.md:52`（Q2 選項 A 本文）同樣載有該句——依 `project.md` 的 `functional-design:c22`，選項本文不改寫是對的，但該條同時要求「**在不成立的句子就地標註**」，目前無任何標註 |
| M-2 | Major | `U-8/functional-design-questions.md:18`、`:61` | **D-1 的 `branches-ignore` 更正未傳播到 U-8。** U-6 已於 2026-08-29T15:21:33Z 兩處更正（`U-6/domain-entities.md:21-25`、`U-6/functional-design-questions.md:44-46`），逐字結論是「該過濾器**不會排除任何 PR**」「U-10b 實際採用 `paths-ignore`」「任何下游不得再以『U-10b 需要它』為由主張其必要性」。但 U-8（**該標記的產生者**）`:18` 仍寫「U-10b 用它做 `branches-ignore`」，`:61` 更把它當成 E-2 裁定的成本論證基礎：「**U-10b 的 `branches-ignore` 對每個都生效**（前綴相同），成本不隨 PR 數放大」。E-2 的結論可能仍成立（改由 `paths-ignore` 承擔），但**支撐它的機制敘述已被證偽**——這正是 `U-6/domain-entities.md:23` 自己點名的「跨檔傳播失敗」在同一輪內再次發生 |
| M-3 | Major | `U-6/business-rules.md:73`、`:84`、`business-logic-model.md:30`；`component-methods.md:88`、`:12` | **`Decision.status = null` 進入寫入鏈時無規則，且型別不合。** `Decision.status` 值域為 `Status \| null`（`component-methods.md:12`），五種 `reason_code`（`parked`／`suppressed`／`unparseable`／`whitelisted`／`undecidable`）皆對應 `status = null`。R-5.2 比對三欄，`reason_code` 一變即為「有漂移」⇒ 進入寫入鏈；但寫入鏈第一步 `write_status(binding, expected, desired: Status)` 的 `desired` 型別**不含 null**。全單元沒有任何規則說明「`status` 為 `null` 時跳過 `write_status`、但仍渲染受管區塊記下原因」——而 [req:FR-G3]（暫停覆寫 Status）與 [US-OQ-3]（受管區塊記下不寫的原因與時間戳）正是要求這個分支。序列圖 `:30` 把「有漂移 ──► U-3 write_status／write_field」畫成無條件。這是 `suppressed`／`parked` 這兩條**最常走**的路徑上的實作阻塞 |
| M-4 | Major | `ADR-0015:38-40`（§5）對照 `U-8/business-rules.md:109-117`、`U-8/business-logic-model.md:48-53` | **ADR-0015 §5 為反向路徑補上 C-5，但 U-8 的設計沒有任何落點。** §5 逐字：「現行元件集合不含 C-5，使反向同步的外部失敗只會讓 workflow 紅燈而**不產生通報 issue**，[req:FR-E1]／[US:S-8 AC 1] 的『外部失敗 → issue』保證在該路徑上不成立」。本輪 grep 確認 `U-8/business-rules.md` 與 `U-8/business-logic-model.md` **零次**出現 `notify`／`C-5`／「通報」；R-4c 仍為「本單元呼叫的**五個**上游方法」且不含 `notify`；錯誤處理表（`:48-53`）只有「紅燈」欄、沒有「通報」欄。**這與 U-6 在 iteration 1 被抓到的 `ExternalError` 漏「＋ 通報」是同一個缺陷**，只是這次上游 ADR 已經指出而單元未接住。契約端點三問在此缺「誰呼叫」 |
| m-1 | Minor | `U-6/business-rules.md:82`；`ADR-0015:70` | 兩處都寫 R-5.4 的代價是「每次實際寫入**多一次讀取**」，但同一輪新增的 R-5.7 又加了一次寫入前 `read_item`。實算：每個有漂移的 intent 現需 **3 次 `read_item`**（R-5.7 一次、`write_status` 內部一次、R-5.4 一次）＋ mutation，相對於修正前的 1 次是 **3 倍**。而 [req:FR-I4] 的單次操作上限實際值是 PRE-1 第 2 項、`bolt-plan.md` 明訂**延後到 Bolt 2** 才綠，而 U-6 在 Bolt 1 上線。依 `project.md` 的 `delivery-planning:dp-L1`，該代價敘述須重算 |
| m-2 | Minor | `U-6/domain-entities.md:33-43`；`U-1/domain-entities.md:61`、`:72-80` | `Config` 新增第五欄 `reverse_rejected` 時只 grep 了同名衝突，未核對 U-1 的兩處**封閉列舉**：`:61` 逐字「本檔補上 `map` 與 `field_value_for` 這兩個 U-1 方法所需的部分；**C-3／C-7 所需的欄位**由那些單元各自補充」——而 `reverse_rejected` 的消費者是 U-6 的 workflow 層與 `render` 的 `Context`，不屬 C-1／C-3／C-7 任一；`:72-80` 的「`Config` 的承載形式」把 composite action 的 input 列舉為 2 個純量 ＋ 2 個集合，未含第五欄。兩處需擇一處置：把 `reverse_rejected` 移出 `Config`（它從不進 `map`），或補齊承載形式的列舉 |
| m-3 | Minor | `U-4/domain-entities.md:19` 對照 `U-6/business-rules.md:84`、`:177` | `last_synced_at` 的型別欄逐字為「ISO 8601 字串」，**不含 `null`**（同表其餘六欄皆明寫 `\| null`），但 R-2.2 允許欄位缺席補預設，且首建路徑是否寫 `SyncState` 未定義。R-5.6／R-6.2c 都以「PR 關閉時刻晚於 `last_synced_at`」為判準——該欄缺席或為 `null` 時的比較結果未定義 |

### Summary

**整組 NOT-READY（3 Critical、4 Major、3 Minor）。** iteration 2 點名的四項修正在**規則文字**層面確實到位（查證 1–12 有 12 項通過），但把時序與型別實走一遍後，三個 Critical 全部落在**上一輪修正動作的鄰接面**：C-1 是修 U-4「自癒」時引入的（用取消守門換掉假通報，代價是 FR-C1／FR-C3／S-3 AC 1 一起失效）；C-2 是修 R-5.4 時漏傳播到本檔序列圖（U-8 為同型殘留寫下「這一處尤其不能留舊說法」，而寫入端本身留著）；C-3 是修 R-5.4 時被掩蓋的——改以回讀取值之後，`render()` 的輸出在全 stage 產出中再無任何具名去處，而 U-2／U-6 對這個寫者給出兩個互不相容且都不成立的答案，使受管區塊、`managed_block_hash` 基準與整條反向同步鏈同時懸空。

三者互相牽動，建議依此順序處理：**C-3 先修**（它決定 R-5.4／R-5.6／R-6.2／U-2 R-1.5 這一整條鏈有沒有落地的可能）→ **C-1 次之**（牽涉已核可 AC 的可滿足性，修法須以 ADR 承載，並與 `U-4/domain-entities.md:27` 的自癒敘述同批改）→ **C-2 最後**（純文字同步，但須與前兩者的最終形狀一起畫，否則會再改一次）。`project.md` 的 `functional-design:c10` 已寫明「修正動作本身也要過這道檢查」；本輪證實其執行仍不足——修一條規則時，須把**被它取代的舊路徑的每一個消費者**重新問一次「現在誰接手」。

## Review (Iteration 4 — 驗證輪，回讀守門與 reconcile 回寫)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T01:19:06Z
**Iteration**: 4
**涵蓋單元**: U-4 / U-6 / U-7

> 本輪逐字重讀 U-4／U-6／U-7 的全部產出、ADR-0015 全文、上游 `component-methods.md`／`components.md`／`services.md`／`bolt-plan.md`／`requirements.md`／`stories.md`，並自行代入時序走完「兩個 run 並行」「寫入成功但回寫失敗」「`status = null` 的五種 `reason_code`」三組情境。**Q5=A 對 `expected` 語意的修正方向是對的，`Aborted` 確實重新可達**（見查證 1a）。但把「三欄過期」的來源集合、`resolve_if_open` 的鍵來源、以及 `status = null` 分支的寫入面實走一遍之後，發現 **5 個 Critical**——其中 4 個落在本輪修正動作的鄰接面：R-5.9 宣告了一個不封閉的集合並據此取消補救、R-5.10 讓一條已核可 AC 不可滿足、R-6.1b 的鍵來源型別上不可達、而 Q5=A 的整個承接（U-7 的 R-6 群）沒有傳播到 U-7 的序列圖。

### 逐單元判定

| 單元 | Verdict | 理由（一句） |
| --- | --- | --- |
| U-6 | **NOT-READY** | 3 Critical（R-5.9 的「唯一來源」不封閉，`commit_and_push` 失敗與回讀 `ExternalError` 各留下同樣的過期，且結果是永久卡死；R-5.10／R-3.1 三條寫入路徑各自違反 [US:S-3 AC 5]／[req:FR-J3] 逐字的「不對其產生任何看板寫入」；R-6.1b 的待關閉鍵在型別上不可達，缺口 J-2 未關閉）＋ 2 Major ＋ 4 Minor |
| U-7 | **NOT-READY** | 2 Critical（Q5=A 的承接 R-6 群完全沒有傳播到序列圖／fallback／與上游的對應——與 iteration 3 判 Critical 的 C-2 同型；本單元為 `write_status` 的具名呼叫者而 `expected` 來源全單元未定義，圖上唯一可推得的來源正是 iteration 3 判 C-1 的恆真形狀） |
| U-4 | **READY（附 2 項必修）** | 0 Critical；R-3.1 本文在實測結果代入後自我否定（同一條規則同時「不得推 `ut`／`main`」與「對帳（U-7）推其排程觸發分支」＝`main`），且 `:47` 仍以條件句寫「若預設分支就是 `main`」；`domain-entities.md:21-23` 框住表格的引言仍寫「不含 C-4／本站判定這是可接受的（而非宣稱 U-7 會寫）」，與已改的表格 `:27` 相反 |

### 逐項查證（任務指定的 1–5）

| # | 查證項 | 結論 | 依據（檔案:行 ＋ 引文） |
| --- | --- | --- | --- |
| 1a | R-5.7／R-5.8 是否真的讓 `Aborted` 重新可達（自走兩個 run 並行的時序） | **通過** | 代入 [req:NFR-P3]（`services.md:47` reconcile「自成一組，與 S-A 可並行」）：T0 兩者各讀 `SyncState = W`，看板 = W；T1 U-6 `write_status(expected=W, desired=X)`，內部回讀 `actual = W == W` ⇒ `Written`，看板 = X；T2 U-7 手上的 `expected` 仍為 W ⇒ 其 `write_status` 內部回讀 `actual = X ≠ W` ⇒ `Aborted`。**後到者確實偵測到前者的寫入**，[req:FR-C3]（`requirements.md:73`「後到者的回讀比對會偵測到前者已寫入的結果」）成立。人為改動路徑同理（`stories.md:237` 的 S-8 AC 1 前提①逐字描述的正是這條）。**R-5.7 的方向正確** |
| 1b | R-5.9「`SyncState` 過期的唯一來源是 U-7 補平」是否封閉 | **未通過（C-1）** | 見下方 C-1 |
| 1c | U-7 的 R-6 群是否關上「三欄過期」，特別是 R-6.3 不回寫的情形 | **未通過（C-1 的一部分）** | `U-7/business-rules.md:79` 逐字「R-6.3 \| **未補平的 intent 不回寫**（含判定一致、跳過、失敗三種）」——而 C-1 的卡死狀態下看板與 record 恰好一致，U-7 的比對基準是「看板 vs record」（`U-7/business-rules.md:29` R-2.2），判定一致 ⇒ 不補平 ⇒ **依 R-6.3 不回寫** ⇒ 過期的 `SyncState` 永遠不會被修好 |
| 1d | U-4 R-3.1 把「／U-7」加回、`domain-entities.md` 的「自癒」表整組改寫，兩處是否與 U-6／U-7 的新規則一致 | **部分通過（M-1／M-2）** | 表格層一致（`U-4/domain-entities.md:27`「U-7 補平後會一併回寫這三欄」↔ `U-7/business-rules.md:77` R-6.1 ↔ `U-6/business-rules.md:118` R-5.9），但**框住表格的引言與 R-3.1 本文未同步**，見 M-1／M-2 |
| 2 | §13 的 blocking 缺口是否誠實且完整——`commit_and_push` 的「只推觸發分支」是內建限制還是呼叫方式的描述 | **不成立（M-1）** | 見下方 M-1。**答案是「呼叫方式的描述」**，且這個讀法是 U-8 合法的前提，故 blocking 的形狀不對；另兩個候選也不窮盡 |
| 3a | R-5.10 的五種 `reason_code` 是否全部適用「照常走 `write_field` → `render` → `write_body`」 | **未通過（C-2）** | `unparseable`／`whitelisted` 不適用——見 C-2 |
| 3b | `field_value_for(Decision, Config)` 在 `status = null` 時回什麼；U-1 有沒有涵蓋 | **未通過（M-4）** | 見 M-4 |
| 3c | R-5.10 與 [req:FR-G3]／[US-OQ-3] 是否一致 | **通過** | `requirements.md:107` FR-G3 逐字只約束 Status（「須暫停覆寫該 intent 的 **Status**」／驗收「不對該 item 送出 **Status** 寫入」），未禁止自訂欄位與受管區塊；[US-OQ-3] 的載體由 ADR-0015 §11 的 `write_body` 承接（`component-methods.md:93-99` 有指標）。`suppressed`／`parked` 兩支上 R-5.10 的形狀正確，且 `parked` 支同時滿足 [req:FR-F4]（`requirements.md:99`）與 [US:S-4 AC 6]（`stories.md:153`） |
| 4 | 序列圖與 fallback 是否還有第五處與 R-5 群不一致 | **有一處（m-2）** | R-5.1／5.2／5.3／5.4／5.5／5.6／5.7／5.10／R-6.1a 九條逐行比對後與圖一致；**第五處**是 `:22` 的迴圈前查詢只產出 `Config.reverse_pending`，而 `:28` 消費的 `reverse_rejected` 在圖上沒有產生者（R-6.2a 要求同一次查詢同時取回關閉未合併者）。文字 fallback `:47` 有這一半，圖沒有 |
| 5a | m-1：R-5.4 的代價重算為「2 次 `read_item`、2 倍」 | **數字對，但只涵蓋一半分支，且未傳播到 ADR** | 自算：有漂移且 `status` 非 `null` ⇒ `write_status` 內部回讀 1 次 ＋ R-5.4 回讀 1 次 = **2**；修正前為 1（僅 `write_status` 內部）⇒ **2 倍**，`business-rules.md:84` 正確。**但**同一輪新增的 R-5.10 建立了一條沒有 `write_status` 的分支，該分支是 0 → 1 次；且 `ADR-0015:134` 仍逐字「代價是每次實際寫入**多一次讀取**」——iteration 3 的 m-1 同時點名 `ADR-0015`，只修了單元檔（併入 m-1） |
| 5b | m-2：`reverse_rejected` 移出 `Config`，U-1 `domain-entities.md:61` 與 `:72-80` 兩處封閉列舉是否相容 | **表格已相容，但同檔保留段自相矛盾（M-3）** | `U-1/domain-entities.md:61`「C-3／C-7 所需的欄位由那些單元各自補充」與 `:72-80`（2 純量 ＋ 2 集合）現在都與「四個欄位」相容 ✅；但 `U-6/domain-entities.md:47` 仍逐字「目前全 stage 的 `Config` 欄位共**五個**……本單元（`reverse_rejected`）」，見 M-3 |
| 5c | m-3：`last_synced_at` 補 `\| null` 與「`null` 時比較判為真」是否與 R-5.6／R-6.2c 一致；首建路徑是否真的留下 `null` | **通過** | `U-4/domain-entities.md:19` 定為「`null` 時該比較一律判為真」↔ `U-6/business-rules.md:89` R-5.6 逐字「`last_synced_at` 為 `null` 時該比較判為真，見 U-4 `domain-entities.md`」，兩處一致。首建可達性：序列圖 `:25` 的首建分支止於 `U-4 write_binding`，**不呼叫 `write_sync_state`**，故 `last_synced_at` 確實留在 `null`（或缺席由 R-2.2 補預設），`null` 非死值 |
| 5d | ADR-0015 §3／§5／§7／§9／§13 的就地指標是否真的存在、內容是否相符 | **五節全部存在且相符（附 m-3／m-5）** | §3 → `bolt-plan.md:64`（Bolt 2 DoD，逐字含「今天沒處理到／今天處理了且一致」與 R-3.4）✅；§5 → `components.md:112`（reverse 應含 C-5）✅；§7 → `component-methods.md:176`（`latency_samples` 擁有權移出 U-7、二選一、在此之前不填）✅**但落在程式碼圍籬內**（`:166` 開、`:177` 閉）；§9 → `requirements.md:154`（NFR-O2「目標為 0」結構性不可達、二選一、Bolt 2 gate）✅；§13 → `components.md:110`（reconcile 應含 C-4）✅**但未反映 §13 自己標注的 blocking 狀態**（m-5）。另核對 §1／§2 → `bolt-plan.md:28,30,54-56` ✅、§8 → `bolt-plan.md:23` ＋ `requirements.md:147` ✅、§11 → `component-methods.md:93-99` ✅、§12 → `component-methods.md:150` ✅ |

### 新引入或遺留的 Critical

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| **C-1** | **Critical** | `U-6/business-rules.md:118`（R-5.9）；連帶 `business-logic-model.md:33`、`U-7/business-rules.md:79` | **R-5.9 宣告的「唯一來源」不封閉，而它同時被用來取消補救——結果是永久卡死而非假通報。** R-5.9 逐字：「**`SyncState` 過期的唯一來源是 U-7 補平**，該來源已由 **ADR-0015 §13** 從源頭堵住……本單元因此**不需要**任何『已被補平』的例外判定」。至少兩條 **U-6 自己**的路徑產生完全相同的過期：**(a)** `write_status` 成功之後，R-5.4 的寫入後 `read_item` 拋 `ExternalError`（`component-methods.md:86`「API 錯誤 → 拋 `ExternalError{http_status}`」）⇒ 該 intent 走錯誤路徑（`business-logic-model.md:84`「不中止整輪——計入報告後續跑 ＋ 通報」）⇒ `write_sync_state` 從未被呼叫；**(b)** `commit_and_push` 回 `Rejected`（`U-4/business-rules.md:52` 分支保護／`:56` 重試 3 次後仍非快轉）⇒ runner 無狀態，本地寫好的 `sync-state.json` **從未進 repo**。兩者都留下「看板 = 新值 X、`SyncState` = 舊值 W」。**下一輪的推導**：R-5.2 三欄比對 X ≠ W ⇒ 有漂移 ⇒ R-5.7 以 W 重建 `expected` ⇒ `write_status` 內部回讀 `actual = X ≠ W` ⇒ `Aborted` ⇒ 依序列圖 `:33` 逐字「`Aborted ──► U-5 notify（FR-C1，不再往下走）`」⇒ `write_sync_state` **再次不執行** ⇒ **每一輪重複，永不收斂**，且每輪一則與事實不符的通報（看板此刻其實是正確的）。U-7 救不回：它比的是「看板 vs record」（`U-7/business-rules.md:29` R-2.2），此時兩者一致 ⇒ 不補平 ⇒ **R-6.3 明文不回寫**（`:79`）。**這正是 iteration 2 Critical #9 與 iteration 3 C-1 的同一個失敗模式**，Q5=A 只從 U-7 那一條入口堵住，另兩條入口原封不動；更關鍵的是 R-5.9 以「唯一來源已堵住」為由**主動排除**了補救判定，所以這不是漏寫。**附帶：修法本身提高了 (b) 的發生率**——`U-4/business-rules.md:66` 對 N=3 的理由逐字寫「真正的並行來源只剩『事件路徑與排程對帳同時跑』——那是**兩個**寫入者」，而 ADR-0015 §13 之後 U-7 每日也推 `sync-state.json`，同一份檔案的並行推送者從一個變兩個。**修法**：把「`SyncState` 過期」的來源改為窮舉推導（誰寫看板、誰寫檔、兩者之間有哪些失敗點），並為「看板已更新但 `SyncState` 未持久化」設一條可收斂的處置（例如 `Aborted` 且 `actual == desired` 時視為已對齊、當場回寫三欄；或把 `write_sync_state` ＋ `commit_and_push` 的失敗升為「下一輪必須先修復」的顯式狀態）。任一修法都要重跑 `project.md` 的 `functional-design:c10` 可達性檢查 |
| **C-2** | **Critical** | `U-6/business-rules.md:88`（R-5.10）、`:42`（R-3.1） | **R-5.10 與 R-3.1 讓 [US:S-3 AC 5]／[req:FR-J3] 不可滿足，且該 AC 逐字點名了今日就存在的 record。** `stories.md:129` 逐字：「**Given** 一個缺少 `## Stage Progress` 等必要區塊的 record（現況範例：`260802-default`），**When** 同步執行，**Then** **不對其產生任何看板寫入**」；`requirements.md:132` FR-J3 同義（「一律**跳過、不寫入看板**」／驗收「**不對其產生任何看板寫入**」）。而：①R-5.10 逐字「**`Decision.status` 為 `null` 時跳過 `write_status`，但**照常**走 `write_field` → `render` → `write_body` → 回讀 → `write_sync_state`**」，其說明段 `:114` 逐字「五種 `reason_code`（`parked`／`suppressed`／`unparseable`／`whitelisted`／`undecidable`）**全部**對應 `status = null`」——`write_field`（Projects v2 自訂欄位）與 `write_body`（issue body 受管區塊，ADR-0015 §11）**都是看板寫入**；②R-3.1 的無綁定分支更在 `map()` 之前就無條件 `create_item`（序列圖 `:25`「無綁定編號 ──► U-3 create_item」，`services.md:21` 同），而 `260802-default` 今日在 registry 內且無綁定 ⇒ Bolt 1 首次執行就會為它建卡。**三條寫入路徑各自獨立違反同一條 AC。** 上游自己劃了這條界線：`stories.md:102` S-2 AC 15 的 Given 逐字寫「任一**可解析**的 record（**即未被 S-3 AC 5 跳過者**）」——R-5.10 把六個 `reason_code` 一律當成「照常寫其餘三者」時抹平了它。**這是本輪 M-3 修法引入的**：M-3 只問了「`write_status` 的 `desired` 型別不含 `null` 怎麼辦」，沒有回頭問「這五種裡有哪一種根本不該碰看板」。**修法**：R-5.10 依 `reason_code` 分流——`parked`／`suppressed`／`undecidable` 走「跳過 `write_status`、其餘照走」，`unparseable`／`whitelisted` 走「整條鏈都不執行」；R-3.1 的首建分支加一道可解析性前置（或明寫首建與 FR-J3 的衝突並以 ADR 承載，因為 `services.md` 的 S-A 也是這樣寫的） |
| **C-3** | **Critical** | `U-6/business-rules.md:172`（R-6.1b）；連帶 `U-7/business-logic-model.md:83` | **R-6.1b 的待關閉鍵來源在型別上不可達 ⇒ 缺口 J-2（通報 issue 永不自動關閉）並未關閉。** R-6.1b 逐字：「**待關閉鍵的來源**：某 intent 上一輪記錄的 `SyncState.last_reason_code` **屬失敗類**，而本輪該 intent 處理成功 ⇒ 鍵為 `{intent_id, reason_code: 該 last_reason_code}`」。三項機械證據：①`U-4/domain-entities.md:17` 逐字把 `last_reason_code` 的型別定為 `ReasonCode \| null`，而 `component-methods.md:16-20` 的 `ReasonCode` 值域只有 `mapped`／`parked`／`unparseable`／`whitelisted`／`undecidable`／`suppressed` **六個，沒有任何失敗類值**；會產生通報 issue 的是 `ExternalError`／`Rejected`／`Aborted`／`CannotCreate`（本檔錯誤表 `:84-86`），它們不在該值域內。②即使把「失敗類」寬鬆讀成 `unparseable`／`undecidable`，`component-methods.md:139` 逐字「`reason_code` 為 `"suppressed"`／`"parked"`／`"unparseable"`／`"whitelisted"`／`"undecidable"` 時屬機制的正常判斷……**只有 `ExternalError` 與 `Rejected` 紅燈**」，本檔 `:87` 亦逐字「五種正常判斷的 `reason_code` \| 續跑，**不通報**」——沒有 issue 可關，`resolve_if_open` 依 `component-methods.md:123`「找不到既有 issue → no-op」。③寫入時點：`last_reason_code` 由 R-5.4 寫入，而 R-5.4 只在**看板寫入成功後**執行；真正失敗的那一輪根本走不到它。⇒ **`resolve_if_open` 永遠拿不到任何鍵**，J-2 的關閉是名義上的。這與 `project.md` 的 `functional-design:c10`（`pending_reverse` 因騎在唯一寫入路徑上而不可達）**是同一個形狀**，而該條明文要求「修正動作本身也要過這道檢查」；R-6.1b 正是 iteration 2 修 R-6.1a Major 時新寫的。U-7 `business-logic-model.md:83` 逐字「同 U-6 的 R-6.1」，同樣繼承且自己沒有鍵定義。**修法**：`FailureIdentity.reason_code` 的值域必須先被定義（它顯然不等於 `ReasonCode`——這是上游 `component-methods.md:126` 的缺口，須以 ADR 承載），再定義一個真的跨輪存活的失敗記錄落點；若不新增持久狀態，就改以「本輪成功後，以本 intent 可能的失敗鍵集合逐一 `resolve_if_open`」並明寫該集合 |
| **C-4** | **Critical** | `U-7/business-logic-model.md:13-40`、`:91`、`:93` | **Q5=A 的整個承接（R-6 群）在 U-7 的序列圖、文字 fallback 與「與上游的對應」中完全不存在。** 序列圖 `:31-33` 仍逐字「`└─ 不一致 ► 補平（write_status）` / `├─ Written ──► backfilled_count +1`」——**沒有 `write_sync_state`、沒有 `commit_and_push`、沒有 C-4**；fallback `:40` 逐字「不一致就補平；另外檢查 issue 開關與 Status 是否相稱。最後產出報告」，同樣沒有回寫；`:91` 仍逐字「元件分層與 reconcile 的元件集合（**含 C-5**）引自 [ad:components.md]」，未提 ADR-0015 §13 補上的 C-4；`:93`「**本檔對上游的補充**」仍只列 `undecidable` 與 R-3.4，且逐字宣稱「**一致率的兩類排除、`reconcile` 的簽章、單一 intent 失敗不中止整輪一字未改**」，讀起來像本輪沒有任何結構變更。錯誤處理表 `:64-70` 也沒有回寫失敗那一列（R-6.4 只在 `business-rules.md` 內）。**這與 iteration 3 判為 Critical 的 C-2（U-6 序列圖未傳播 R-5.4）是同一形狀**，而 iteration 3 的 Summary 已逐字寫下「修一條規則時，須把**被它取代的舊路徑的每一個消費者**重新問一次『現在誰接手』」。差別在於這一次落在**本輪唯一的核心修法**上：照 U-7 的序列圖實作 ⇒ 不回寫 ⇒ U-6 的 `expected` 過期 ⇒ 回到 iteration 3 C-1 要消滅的假通報 |
| **C-5** | **Critical** | `U-7/business-logic-model.md:29-33`；`U-7/business-rules.md` 全檔；`component-methods.md:88` | **U-7 是 `write_status` 的具名呼叫者，但它的 `expected` 從哪裡來，全單元沒有任何規則——而圖上唯一可推得的來源正是 iteration 3 判 C-1 的恆真形狀。** `component-methods.md:88` 的簽章逐字 `write_status: (binding, expected: ItemState, desired: Status) -> WriteResult`，`expected` 是必填參數。Q5=A 把它的語意升為規範（`U-6/business-rules.md:113` R-5.8 逐字「`SyncState` 的三欄……R-5.7 的 `expected`（『我們上次寫了什麼』）」），但只寫在 U-6。U-7 的序列圖 `:29-31` 是「`U-3 read_item ──► 與 record 判定比對 ├─ 一致… └─ 不一致 ► 補平（write_status）`」——照字面實作，`expected` 就是**剛剛那次 `read_item` 的回傳值**，於是 `write_status` 內部的「必先回讀」比對恆真，**對帳路徑的 `Aborted` 不可達**。連帶死碼：`ReconcileReport.aborted`（`component-methods.md:172`）、`U-7/business-rules.md:17` 的 `Aborted → aborted` 那一列、`U-7/business-logic-model.md:68` 的「補平時回讀不符」那一列、[US:S-9 AC 2] 的第三份清單、以及 `services.md:50`（S-B「與 S-A 的競爭」）逐字「兩者可能同時寫同一 item。處置在 C-3 的寫入前回讀——**後到者 `Aborted` 並列入 `aborted` 清單**（[req:FR-C3]，唯一結果）」。行為後果與 iteration 3 C-1 相同：協作者在看板上的改動會被每日對帳靜默輾掉。**Q5=A 修的是兩個呼叫者中的一個。** 修法：在 U-7 明寫 `expected` 由 `read_sync_state` 的三欄重建（它現在有 C-4 了，讀得到），並在 `business-logic-model.md` 的序列圖補上該讀取步驟 |

### 其餘發現

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| **M-1** | **Major** | `ADR-0015:114-121`（§13 排程分支的衝突）；`U-4/business-rules.md:38`、`:47`、`:49` | **blocking 的推導取了一個與 U-4 自己的定案相反的讀法，而那個讀法同時會讓 U-8 違法。** §13:118 逐字：「`commit_and_push` 的契約是「**只推觸發分支**」（§C-4），對排程觸發而言即 `main`」。但 `U-4/business-rules.md:49` 逐字已定案：「原文寫『只推觸發分支』，但 U-8 推的是新建的反向分支——字面上兩者衝突。這條規則的**實質**是『不得直接推整合主幹』，`branch` 本來就是 `commit_and_push` 的參數；『只推觸發分支』描述的是正向路徑的**呼叫方式**，不是方法的內建限制。」簽章 `(branch, paths, message)`（`component-methods.md:114`）佐證。**兩個讀法在同一 stage 的產出中並存**：取 U-4 的寬鬆讀法 ⇒ ADR 的候選 (1)「比照 U-8 推自建分支」不是候選而是**已經合規的做法**，blocking 不成立，剩下的只是 R-3.1 的列舉要改；取 §13 的嚴格讀法 ⇒ **U-8 現行設計（推 `aidlc-sync/reverse/*`）同樣違法**，而 U-8 已判 READY。兩者必須先擇一，「沒有任何合法的推送落點」在前者之下不成立。**附帶（同源）**：`U-4/business-rules.md:38` 的 R-3.1 本文仍逐字「**不得推 `ut`／`main`**。正向同步（**U-6**）只推觸發分支；**對帳（U-7）推其排程觸發分支**；反向同步（U-8）推自建的 `aidlc-sync/reverse/*` 分支」——在「預設分支＝`main`」代入後，同一條規則的第二子句要求 U-7 做第一子句禁止的事，**規則自我否定**；`:47` 的註記也仍是條件句「須在 Bolt 2 開工前確認——**若**預設分支就是 `main`，兩者直接衝突」，未依 2026-08-30T01:05:00Z 的實測結果改為事實陳述。**第三條路也未被列出**：`schedule` 只決定 workflow 檔從哪個 ref 讀取，`actions/checkout` 可 checkout 任一 ref——「觸發分支」與「工作樹分支」是兩件事，兩個候選都沒有分辨；且它連帶一個未被提出的問題：U-7 若在 `main` 的工作樹上跑，它讀到的 record 是**落後於 `ut`** 的版本（`org.md` 逐字「`main` … receives merges from `ut`」），對帳會拿舊 record 去比新看板 |
| **M-2** | **Major** | `U-4/domain-entities.md:21-23` | **改到表格，沒改到框住表格的敘述，兩者現在直接相反。** `:21` 仍逐字「**這些欄位有第二條「寫看板但不寫本檔」的路徑，必須寫明**……U-7 的對帳補平會經 C-3 `write_status` 直接寫看板，但依 [ad:components.md]，reconcile 的元件集合**不含 C-4**——**它無法更新本檔任何欄位**」，`:23` 逐字「**本站判定這是可接受的，並寫下界限**（**而非宣稱 U-7 會寫**）」；而緊接的表格 `:27` 已改為「**U-7 補平後會一併回寫這三欄**（ADR-0015 §13 給 reconcile 的元件鏈補上 C-4）」。段落標題所稱的「寫看板但不寫本檔」的路徑已不存在。單獨讀 `:21-23` 的人會得到與現行定案完全相反的結論 |
| **M-3** | **Major** | `U-6/domain-entities.md:45`、`:47`（對照 `:33`、`:41`、`:43`） | **移除欄位時「總數」這個衍生事實未重算，且保留段被明文宣告「仍然成立」。** `:41` 逐字「**`reverse_rejected` 已於 2026-08-30T00:57:28Z 移出 `Config`**」、`:43`「**不進 `Config`**」、`:33`「`Config` 的**四個**欄位……**本單元不增不減**」。但 `:45` 逐字「**下面這段仍然成立且值得留著**」，而它保留的內容逐字寫「……於是這個欄位在本單元自己的組裝表上沒有來源列，**『四個欄位』也成了未重算的數字**」（即主張四是錯的）；`:47` 更直述「**目前全 stage 的 `Config` 欄位共五個，來源分別為 U-1（四個定義）與本單元（`reverse_rejected`）**」。三處與同檔表格互斥。且保留段的論點本身已失效——它把 `reverse_rejected` 當成「各單元各自補 `Config` 欄位」這個開放問題的「第一個實例」，而該欄位既已判定不屬 `Config`，它就不是那個問題的實例。這是 `project.md` 的 `units-generation:rev1-L1`（「被計數的實體改變時，總數本身是受影響事實」）在本 intent 的又一次復發 |
| **M-4** | **Major** | `U-6/business-rules.md:88`（R-5.10）、`:153`（R-7 群）；`U-1/business-rules.md:76-85`（R-5 群）；`U-1/domain-entities.md:37-42` | **R-5.10 指名 `field_value_for` 供值，但 U-1 對四個 `status = null` 的 `reason_code` 都沒有規則。** R-7 群 `:153` 逐字「`field_value_for(Decision, Config) -> string` \| C-1 \| **在 `write_field` 之前**組出自訂欄位值」。而 `U-1/business-rules.md:76` 的格式逐字是「`<短前綴><stage-slug> (<編號>)`，前綴四選一（無／`parked @ `／`skipped `／`frozen: `）」，R-5.1～R-5.4 全部只談截斷，**沒有任何一條把 `reason_code` 映到前綴**：`suppressed` 與 `undecidable` 無對應前綴（`frozen: ` 從未被綁到任何 `reason_code`），落到「無（正常）」時該 item 的欄位會與正常同步的 item 長得一模一樣，[req:FR-G3] 的暫停事實在欄位上完全看不出來；更硬的是 `unparseable`／`whitelisted`——它們的 `map()` 輸入是 `Unparseable{intent_id, missing}`（`U-1/domain-entities.md:37-42`），**結構上沒有 `current_stage`／`stages`，`<stage-slug>` 無值可填**。而「填空字串」這個最自然的預設有既定語意：`component-methods.md:158` 逐字「一段固定說明：**「自訂欄位為空的 item 不由本機制維護」**（[Q6=A] 的規則落點）」——等於機制自己把 item 翻轉成「不受管」。（`unparseable`／`whitelisted` 兩支另由 C-2 判定為根本不該寫；本項對 `suppressed`／`undecidable` 兩支仍獨立成立） |
| **m-1** | Minor | `U-6/business-rules.md:84`；`ADR-0015:134` | 代價重算的數字正確（2 次／2 倍，已自算複驗），但**只涵蓋 `status` 非 `null` 的分支**——同一輪新增的 R-5.10 建立了一條沒有 `write_status` 的分支，該分支是 0 → 1 次 `read_item`。且 iteration 3 的 m-1 同時點名 `U-6/business-rules.md` 與 `ADR-0015`，而 `ADR-0015:134` 仍逐字「代價是**每次實際寫入多一次讀取**（僅在有漂移時發生）」，未同步 |
| **m-2** | Minor | `U-6/business-logic-model.md:22`（對照 `:28`、`:47`、`business-rules.md:193`） | **序列圖的第五處不一致**：`:22` 逐字「成功 ──► 變更路徑 → intent id 集合 = **`Config.reverse_pending`**」——迴圈前只產出一個集合；但 `:28` 的判定節點逐字消費「**R-5.6 有告示待送**」，其輸入 `reverse_rejected` 在圖上**沒有產生者**。R-6.2a（`business-rules.md:193`）明訂「迴圈之前的那次 label 查詢（R-2.1）**改為同時取回關閉而未合併**的反向 PR」，文字 fallback `:47` 也有這一半（「關閉而未合併的算出哪些有告示待送」），唯獨圖沒有 |
| **m-3** | Minor | `components.md:110,112,113`；`component-methods.md:148-151,166-177`；`U-6/business-rules.md:77-89,110-118` | **指標與說明性 blockquote 插在表格／圍籬中間，切斷了四處 markdown 結構。** `components.md` 的 workflow 對照表在 `:110`／`:112` 被兩個 blockquote 打斷，使 `aidlc-sync-selftest.yml` 那一列（`:113`）脫離表格；`component-methods.md` 的 C-6 表在 `:148-150` 被打斷，使 `content_hash` 那一列（`:151`）脫離；§7 的指標（`:176`）落在 `ReconcileReport` 的程式碼圍籬**內**（`:166` 開、`:177` 閉），會被當成型別定義的一部分渲染。同型問題也在本輪的產出裡：`U-6/business-rules.md` 的 R-5 表被 `:77-86` 的 blockquote 切斷，使 **R-5.5／R-5.10／R-5.6**（`:87-89`）落在無表頭的孤兒片段；R-5.7 表被 `:114-116` 切斷，使 **R-5.9**（`:118`）同樣脫落——恰好是本輪四條最關鍵的新規則 |
| **m-4** | Minor | `U-6/business-rules.md:62`、`:66`；`business-logic-model.md:103` | **同一檔內有兩個 H2 都叫 R-5**：`:62`「## R-5：本單元不擁有 U-10a 的 `paths-ignore`」與 `:66`「## R-5 群：漂移比對與狀態回寫」。`business-logic-model.md:103` 的邊界表以裸 `R-5` 引用前者，而全檔其餘 `R-5.x` 指後者。U-7 的同型撞號（兩個 R-4 群）在 iteration 2 被判 **Major** 並改號為 R-8（`U-7/business-rules.md:42` 有記載），U-6 這一處從未被處理 |
| **m-5** | Minor | `components.md:110` 對照 `ADR-0015:114` | §13 的就地指標只寫「`aidlc-sync-reconcile.yml` 的元件集合**應含 C-4**……確認人為 Bolt 2 的 gate」，**未反映 §13 自己逐字標注的「這是 §13 唯一未解的實作缺口，判定為 blocking」**。只讀 `components.md` 的人（含 Bolt 2 gate 的執行者）會把它讀成一項已收斂的修訂 |

### 已查證、未發現問題的項目

- **R-5.7／R-5.8 的方向**：`expected` 回到 `SyncState` 三欄是正確的，[req:FR-C1]／[req:FR-C3]／[US:S-3 AC 1–2] 在**沒有過期**的前提下全部可滿足（查證 1a 已自走時序）。C-1 打的是「過期來源不封閉」，不是這個決定。
- **R-5.10 對 `parked`／`suppressed` 兩支的形狀**：與 [req:FR-G3]（只約束 Status）、[req:FR-F4]、[US:S-4 AC 6]、[US-OQ-3] 一致（查證 3c）。
- **`last_synced_at` 的 `| null` 與「`null` 判為真」**：U-4 與 U-6 兩處逐字一致，且首建路徑確實留下 `null`，非死值（查證 5c）。
- **`Config` 欄位數還原為四**：與 U-1 `domain-entities.md:61` 與 `:72-80` 兩處封閉列舉相容（查證 5b 的表格層）。
- **ADR-0015 的五節指標**：§3／§5／§7／§9／§13 全部存在且內容與 ADR 相符（查證 5d），iteration 3 的 F5（「ADR 有十節而上游零處回指」）已實質關閉。
- **序列圖對 R-5.1～R-5.7、R-5.10、R-6.1a 的傳播**：逐行比對後一致，iteration 3 C-2 點名的四處已修掉（查證 4）。

### Summary

**整組 NOT-READY（5 Critical、4 Major、5 Minor）。** Q5=A 的方向是對的——`expected` 回到 `SyncState`、由寫看板者負責記錄自己寫了什麼，這個語意在兩個 run 並行的時序下確實讓 `Aborted` 重新可達。問題出在**修法的邊界被畫得比實際窄**：R-5.9 把「三欄過期」的來源集合宣告為單元素並據此取消補救，但 U-6 自己的 `commit_and_push` 失敗與寫入後回讀 `ExternalError` 兩條路徑產生完全相同的過期，且結果比原本的假通報更糟（`Aborted` 中止寫入鏈 ⇒ `SyncState` 永遠追不上 ⇒ 每輪重複，U-7 因 R-6.3 也不會回寫）；Q5=A 的承接只寫進 U-7 的 `business-rules.md`，序列圖、fallback、上游對應三處零傳播；`write_status` 的另一個呼叫者（U-7）的 `expected` 來源根本沒被問過，而圖上唯一可推得的來源正是 iteration 3 判 Critical 的恆真形狀。另外兩個 Critical 與 Q5 無關但同屬「契約端點懸空」：R-5.10 把六個 `reason_code` 一律送進看板寫入鏈，讓 [US:S-3 AC 5] 逐字的「不對其產生任何看板寫入」在一個**今日就存在的 record** 上不可滿足；R-6.1b 的待關閉鍵取自 `SyncState.last_reason_code`，而該欄位的型別（`ReasonCode`）不含任何失敗類值，`resolve_if_open` 因此永遠拿不到鍵。

**建議處理順序**：**C-3 與 C-2 先修**（兩者都是可獨立判定的型別／AC 衝突，不牽動其他修法的形狀）→ **C-1 次之**（它決定 R-5.9 的形狀，修法可能需要 ADR 承載，並與 `U-4/domain-entities.md` 的敘述同批改）→ **C-4／C-5 最後**（兩者都在 U-7，且 C-5 的 `expected` 來源會決定 C-4 的序列圖要畫成什麼樣）。M-1 的兩個讀法必須先擇一再談 §13 的 blocking——目前 U-8 的合法性與 §13 的 blocking 判定建立在同一句話的兩個相反解釋上。

`project.md` 的 `functional-design:c10` 逐字要求「**修正動作本身也要過這道檢查**」。本輪的 C-1（宣告一個不封閉的集合並據此取消補救）、C-2（修 `null` 分支的型別問題時沒問「哪一種根本不該寫」）、C-3（修 `resolve_if_open` 的呼叫方式時新寫的鍵來源不可達）三者都落在這條規則的直接適用範圍，而送審前自檢的第 1 項（可達性）與第 2 項（契約端點三問，範圍為整個 stage 產出）本應各自攔下其中兩項。

## Review (Iteration 5 — 變更面驗證)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T02:03:04Z
**Iteration**: 5
**涵蓋單元**: U-4 / U-6 / U-7

> 本輪**只驗變更面**（`2026-08-30T01:31:09Z` 前後的改動），不重審前四輪已通過的部分。做法是把 R-5.9 宣告的 ②③ 兩條路徑各自代入完整時序走到底（含 U-7 的 R-6.5 接手之後），再逐條把 R-5.10 兩支、R-5.12、R-6 群、R-7 群與序列圖／R-3.1／錯誤表／上游指標對照。**方向判斷：R-6.5 的「第三座標」論證成立，R-6.7 與 R-5.7 取法相反的論證也成立**——兩者確實是不同的問題（跨輪守門 vs 單輪內樂觀鎖），不是同一條規則的兩種取法。問題出在**修法的覆蓋面**：R-6.5 修好了 `SyncState` 五欄中的三欄，而 `managed_block_hash` 在同一批路徑上永久錯誤且被 R-6.2 明文禁止修復，其後果正是 ADR-0015 §10／ADR-A6 點名的最危險失敗模式；R-5.10 (b) 的「不首建」落在一條結構上到不了它的分支上；而序列圖第三度沒有跟上新規則。

### 逐單元判定

| 單元 | Verdict | 理由（一句） |
| --- | --- | --- |
| U-6 | **NOT-READY** | **C-1／C-2／C-3**（`managed_block_hash` 在 R-5.9 ②③ 路徑上永久錯誤且被禁止修復；R-5.10 (b) 的「不首建」與 R-3.1／序列圖直接矛盾且結構上不可達，[req:FR-J3] 仍不可滿足；序列圖未傳播 R-5.10 (b)／R-5.12，且 `:38`「失敗不連坐」與 R-5.12 字面相反）＋ M-3／M-4／M-7／M-8／M-10 ＋ m-3／m-7／m-8 |
| U-7 | **NOT-READY** | 無自身獨立 Critical，但 R-6.2 是 **C-1** 的禁止修復點（依「>2 Major ⇒ NOT-READY」亦成立）：**M-1**（R-6.3 與 R-6.5 在「判定一致」上直接矛盾）、**M-5**（R-7.4 對 U-8 的承接無收件人）、**M-6**（R-7.3 為上游型別 `ReconcileReport` 新增欄位而無承載）＋ m-4／m-9 |
| U-4 | **NOT-READY** | **M-2**（R-3.1 `:38` 與 U-7 新增的 R-7.2 直接矛盾、本文仍自我否定、`:47` 仍為條件句且仍稱 ADR「不裁定」——iteration 4 M-1 未解）、**M-3**（`domain-entities.md:18`／`:56` 仍寫 `managed_block_hash`「由 U-2 的 `content_hash` 產生」，與同檔 `:39` 及 R-5.4 相反）＋ m-5。**已關閉**：iteration 4 的 M-2（引言與表格已對齊）、m-3 的 `last_synced_at` 值域 |
| 跨檔／ADR | — | **M-9**（§14 的 Bolt 1 gate 未登錄 `bolt-plan.md`）＋ m-1／m-2／m-6 |

### 逐項查證（任務指定的 1–10）

| # | 查證項 | 結論 | 依據（檔案:行 ＋ 引文） |
| --- | --- | --- | --- |
| 1a | R-5.9 的三來源是否窮盡（自走 ②③ 完整時序） | **不窮盡（→ C-1）** | ②③ 的**三欄**部分確實被 R-6.5 接住（見 1c），但**第五欄未被涵蓋**；且 ②③ 之外另有一條同形路徑未列入：`write_status` 回 `Written` 後 `write_field`／`write_body` 回 `Failed` ⇒ 依 R-5.12（`U-6/business-rules.md:115`「寫入鏈中任一步失敗時，本輪不呼叫 `write_sync_state`」）同樣留下「看板已更新、`SyncState` 是舊值」。R-5.9（`:114`）只列 `commit_and_push` 回 `Rejected` 與 R-5.4 回讀 `ExternalError` 兩條 |
| 1b | R-5.12 ＋ R-5.11 是否產生新的卡死 | **不產生新卡死，但產生永久陳舊（→ C-1）** | 卡死本身被 R-6.5 解開（1c 已代入時序）✅。但 R-5.12 的說明段（`:132`）逐字宣稱「受管區塊**下一輪會重試**」——**該宣稱不成立**：下一輪 `expected`（舊）≠ `actual`（新）⇒ `Aborted` ⇒ 依序列圖 `:35`「不再往下走」，`write_body` 走不到；等 R-6.5 補平三欄之後 R-5.2 判無漂移 ⇒ 依 R-5.5 根本不進寫入鏈。**兩條路都不會重試** |
| 1c | U-7 的 R-6.5 是否真的接得住（②③ 之後的狀態是否滿足其觸發條件） | **三欄接得住，`managed_block_hash` 接不住（→ C-1）** | 代入 ②：U-6 `write_status`→`Written`、`write_field`／`write_body` 成功、`read_item` 取回新雜湊、本地 `write_sync_state` 完成、`commit_and_push` 回 `Rejected`（`U-4/domain-entities.md:85`「分支保護拒絕，**或**內部重試 N 次後仍非快轉」）⇒ repo 內 `sync-state.json` **完全未變**。U-7 次日：`read_item` 得看板＝X、`map()` 得 Decision＝X ⇒ `U-7/business-logic-model.md:37`「看板 == Decision」成立 ⇒ `:39` 觸發 R-6.5 ⇒ `:40` `write_sync_state（修復三欄）`。**觸發條件確實滿足** ✅。但 R-6.2（`U-7/business-rules.md:78`）逐字「**不得動 `managed_block_hash`**」，而該欄在 repo 內仍停在**上一次成功那輪**的值、看板上的受管區塊已是新內容 ⇒ 見 C-1 |
| 2a | R-5.10 兩支與 [req:FR-J3]／[US:S-3 AC 5] 逐字核對 | **(b) 支的文字正確** ✅ | FR-J3 逐字「一律跳過、不寫入看板……**不對其產生任何看板寫入**」↔ R-5.10 (b)（`U-6/business-rules.md:78`）「不 `write_status`、不 `write_field`、不 `write_body`、**且不首建**」相符；`whitelisted` 併入 (b) 有 [ad:component-methods.md]`:29`（「`Unparseable` 輸入回 `unparseable`（白名單內則 `whitelisted`）」）支持；`undecidable` 排除於 (b) 的理由（解析成功、只是訊號不落在對照表任一列）與 `component-methods.md:29`／判定順序第 7 條一致 |
| 2b | (b) 支是否可達（首建路徑） | **不可達（→ C-2）** | R-3.1（`U-6/business-rules.md:42`）逐字仍是「**無綁定編號**者 \| 走首建路徑（U-3 的 `create_item`，[req:FR-A1]）」，無任何可解析性前置；序列圖 `:26` 同（「無綁定編號 ──► U-3 create_item ──► U-4 write_binding」）；R-7 表 `:188` 逐字把 `map` 的呼叫時機定為「**已綁定路徑**的判定」。⇒ 首建分支上**根本不存在 `Decision`**，R-5.10 (b) 的「不首建」無從判斷。iteration 4 C-2 的修法逐字要求「R-3.1 的首建分支加一道可解析性前置」——**未執行** |
| 2c | (b) 支「僅回寫 `SyncState`」與 R-5.12／R-5.5 的相容性 | **與兩者相容，與 R-5.4／R-5.8 衝突（→ M-4）** | R-5.12 的前提是「寫入鏈」，(b) 支無寫入鏈 ⇒ 不衝突 ✅；R-5.5（`:76`）只在「無漂移**且**無待送告示」時禁寫 ⇒ 不衝突 ✅。**但** R-5.4（`:75`）逐字「**看板寫入成功後**，五欄一起回寫」是本檔唯一定義回寫動作的規則，而 (b) 支沒有看板寫入；R-5.8（`:113`）逐字把三欄定義為「**機制上次寫進看板的值**」。(b) 支要寫哪幾欄、`managed_block_hash`／`last_synced_at` 怎麼辦、是否 `commit_and_push`，全部未定義 |
| 2d | (b) 支未綁定時 `SyncState` 寫進哪裡；`binding` 為 `null` 時檔案是否存在 | **落點本身沒問題** ✅ | `component-methods.md:115` 逐字 `read_sync_state` / `write_sync_state` \| `(record_path[, state])` \| `<record>/sync-state.json`——**以 `record_path` 為鍵，不需要 `binding`**；`U-4/domain-entities.md:14` 把 `binding` 定為該檔的一個欄位（`整數 \| null`，`null` 代表尚未首建），跨版本規則 C-2（`:67`「讀取時對缺席欄位補預設值，不視為錯誤」）使檔案不存在亦可 read-modify-write。**此項不構成缺陷**，但被 2b 蓋掉——流程根本走不到 (b) 支 |
| 3a | R-6.1b／R-6.1d 的值域與 U-5 `domain-entities.md` 是否一致（U-5 四個 vs 此處五個） | **不一致（→ M-7）** | R-6.1b（`U-6/business-rules.md:219`）逐字「`reason_code` ∈ {`ExternalError`, `Rejected`, `Aborted`, `CannotCreate`, **`Failed`**}」＝**五個**；而**同一條規則自己的說明段** `:227` 逐字引 U-5「並列出實際值域（`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`）」＝**四個**。規則本文與其依據段在同一頁上差一個值。`Failed` 是 `WriteResult` 的成員（`component-methods.md:25`），R-5.12 確實要求它 `notify`，但**本檔錯誤表 `:83-89` 沒有 `Failed` 這一列** ⇒ 依現行錯誤表 `Failed` 不通報 ⇒ 沒有 issue 可關，該鍵是 no-op。R-6.1d（`:220`）「不得以 `SyncState.last_reason_code` 當鍵來源……兩個不同的命名空間」**成立且方向正確** ✅ |
| 3b | 「本輪處理成功」在 R-5.10 (b) 支之下的定義 | **未定義（→ M-8）** | 全 U-6 產出中 `處理成功` 只出現一次，即 R-6.1b（`:219`）本身，無任何定義。本輪新增的兩條無寫入路徑使它歧義：R-5.10 (b) 支**一個看板寫入都沒有**、R-5.5 的無漂移分支**連寫入鏈都不進**。若兩者算「處理成功」，則上一輪真的失敗（issue 已開）的 intent 在下一輪只要判為 `unparseable` 或無漂移，`resolve_if_open` 就會把仍然成立的告警關掉——`component-methods.md:139` 的二元 AC（「同一個鍵連續兩輪失敗 ⇒ 開啟中 issue 數為 1」）在這條路徑上失守 |
| 4a | `Context` 組裝表的內容正確性 | **通過** ✅ | U-2 `domain-entities.md:54-56` 的 `Context` 恰為三欄（`decided_at`／`scope_note`／`rejection_notice`），與 `U-6/business-rules.md:197-201` 的組裝表逐欄相符；`decided_at`「每輪必填、`status` 非 `null` 時 `render` 不輸出」↔ U-2 `:54` 逐字相同；`scope_note`「U-1 composite action 的第五個 output」↔ U-2 `:55`／`:62` 相同；`rejection_notice` ↔ R-6.2b 與 U-2 `:56` 相同。**契約端點三問在這三欄上現在答得出來** |
| 4b | 前綴對照表的指派依據；`undecidable` 標為「無對應前綴、指派 ADR-0015 §14」是否誠實 | **誠實且方向正確，但一處指派無來源（→ m-3）** | `component-methods.md:56` 逐字「短前綴限一個字元類，**四選一**：無（正常）、`parked @ `、`skipped `、`frozen: `」——**上游沒有把任何前綴綁到任何 `reason_code`**。`undecidable` 拒絕自行填補（`U-6/business-rules.md:154`「加第五個前綴是上游修訂……**實作不得自行猜一個前綴**」）＋ ADR-0015 §14（`:130-136`）＋ `component-methods.md:60` 指標，三處齊備且措辭一致 ✅ **誠實**。**但同一張表把 `suppressed` 綁到 `frozen: `，依據欄只寫「語意對應『凍結』」**——那是本站推論而非上游來源，與它為 `undecidable` 所主張的「前綴集合是上游定的格式契約」自相矛盾。另「會走到 `write_field` 的 `reason_code` 有四種」經實算為 `mapped` ＋ R-5.10 (a) 三種 ＝ **4** ✅ |
| 5 | 序列圖與 R-5 群逐條對應（R-5.10 兩支、R-5.12、`reverse_rejected` 的產生者） | **三處不一致，其中兩處是本輪新規則（→ C-3）** | ✅ **已修**：`reverse_rejected` 現在有產生者（`:22-23` 迴圈前查詢同時產出兩個集合，與 R-6.2a `:250` 相符，iteration 4 m-2 關閉）。❌ **未修**：①`:36` 逐字「`Decision.status 為 null ──► 跳過 write_status（R-5.10）`」——**只有 (a) 支**，(b) 支（不 `write_field`／不 `write_body`／不首建）在圖上完全不存在；②`:38` 逐字「`U-3 write_field（**失敗不連坐**）`」與 R-5.12「**任一步失敗即本輪不回寫**」直接相反；③`:42` 的 `write_sync_state` 是無條件節點，R-5.12 的失敗分支在圖上無落點。且 `:51` 的重畫 blockquote 仍逐字寫「於 **2026-08-30T00:57:28Z** 整組重畫」並只列 iteration 3 的四項——**本輪的改動未被記載** |
| 6a | R-7.1 的「不釘就會靜默讀到 `main`」是否正確 | **正確** ✅ | GitHub `schedule` 只在預設分支觸發，`actions/checkout` 預設 checkout 觸發 ref；`U-7/functional-design-questions.md:55` 記載預設分支經 `git symbolic-ref refs/remotes/origin/HEAD` **實測**為 `main`，`org.md` 逐字「`main` … receives merges from `ut`」佐證 `main` 落後。Q6 選項 A（`:59`）與 R-7.1／R-7.2（`:106-107`）逐字相符，[Answer]: A（`:65`）附真實時間戳與使用者原話 ✅ |
| 6b | R-7.3 的 SHA 記錄是否真的能讓「被繞過」變成可偵測 | **可偵測性成立但弱；且欄位無承載（→ M-6）** | 若 R-7.1 被拿掉，工作樹是 `main`，報告記下的就是 `main` 的 HEAD——**欄位名叫「`ut` HEAD SHA」而值不是**，要靠人拿去跟真實 `ut` HEAD 比對才看得出來，不是自證。更硬的問題：`ReconcileReport` 是上游型別（`component-methods.md:169-176`），新增欄位屬上游修訂，而 ADR-0015 §13（`:121`）只在敘述中提了一句、**未列為修訂節**，`component-methods.md` §C-7 的指標（`:179`）**零字提及**——對照組 `undecidable` 在同一處有逐字登錄（「`ReconcileReport` 亦須含 `undecidable: [intent_id]`」） |
| 6c | R-6.7 與 R-5.7 取法相反的論證是否成立 | **成立** ✅ | `U-7/business-rules.md:89-94` 的分辨是對的：U-6 是**跨輪**守門（基準必須是自己上次寫的值，取當下 `read_item` 會恆真，即 iteration 3 C-1）；U-7 是**單輪內**樂觀鎖（讀到與寫入之間有沒有人插隊，基準本來就是剛讀到的值）。可達性複驗：`services.md:47` reconcile「自成一組，與 S-A 可並行」＋`:50`「兩者可能同時寫同一 item……後到者 `Aborted`」⇒ U-7 的 `Aborted` 在並行 U-6 寫入下可達，`ReconcileReport.aborted`（`component-methods.md:173`）與 `U-7/business-rules.md:17` 不是死碼 ✅ |
| 7 | U-7 序列圖與 fallback 重畫、與上游對應段（iteration 4 C-4／C-5） | **C-5 已關閉；C-4 只關閉三處中的兩處（→ m-4）** | 序列圖 `:18-19` 有 `ref: ut` ＋ SHA（R-7.1／R-7.3）、`:26` 有 `read_sync_state`、`:36-40` 有三方比對與 R-6.5 的 `write_sync_state`、`:42` 明寫 `expected = 剛讀到的 ItemState`（R-6.7）、`:44` 有 R-6.1 回寫、`:45` 有 `Aborted` 不回寫（R-6.3）、`:49-50` 有 R-6.6 單次推送與 R-7.2 分支落點；fallback `:55` 逐句對應；`:57-62` 的重畫 blockquote 逐字記載 C-4／C-5 兩項。**R-6／R-7 群逐條在圖上都有落點** ✅。**但 C-4 逐字點名的是三處**（序列圖、fallback、「與上游的對應」），第三處未動：`:113` 仍逐字「reconcile 的元件集合（**含 C-5**）引自 [ad:components.md]」——未提 ADR-0015 §13 補上的 **C-4**；`:115` 仍逐字「**本檔對上游的補充**：`undecidable` 欄位……與分母／批次上限的交界（R-3.4）。**一致率的兩類排除、`reconcile` 的簽章、單一 intent 失敗不中止整輪一字未改。**」——本輪新增了 R-6 群（回寫 `SyncState`，需要 C-4）與 R-7 群（分支落點），該句讀起來仍像本輪無結構變更 |
| 8 | U-4：R-3.1 把「／U-7」加回、`domain-entities.md` 引言與表格對齊、`last_synced_at` 值域 | **一項通過、兩項未過（→ M-2／M-3）** | ✅ `last_synced_at`（`U-4/domain-entities.md:19`）值域含 `\| null` 且定義「`null` 時該比較一律判為真」，與 `U-6/business-rules.md:77` R-5.6 逐字一致；首建路徑確實留下 `null`（序列圖 `:26` 止於 `write_binding`，不呼叫 `write_sync_state`）⇒ 非死值。✅ `domain-entities.md:21-23` 的引言已改為「該路徑已被關閉」「本輪更正（iteration 4 Group A M-2）」，與 `:27` 的表格一致，iteration 4 M-2 **已關閉**。❌ **R-3.1（`business-rules.md:38`）一字未改**，仍逐字「**不得推 `ut`／`main`**……**對帳（U-7）推其排程觸發分支**」，而排程觸發分支經本輪實測就是 `main` ⇒ 同一條規則的第二子句要求做第一子句禁止的事；且它與本輪新增的 R-7.2（`U-7/business-rules.md:107`「推送落點為**從 `ut` 分叉的自建分支**……不推 `main`、不推 `ut`」）**直接矛盾**。❌ `:47` 仍逐字「**實作期須確認（ADR-0015 §13 標出、不裁定）**……**若**預設分支就是 `main`，兩者直接衝突」——而 §13（`:121`）已逐字「**決定**：`actions/checkout` 明訂 `ref: ut`」，既已裁定、也已實測，條件句與「不裁定」兩者皆過期。❌ 另 `domain-entities.md:18`／`:56` 見 M-3 |
| 9 | ADR-0015 §13 改寫、§14 新增、Amends／Amended 行、節數 14，以及 `components.md`／`bolt-plan.md` 的對應指標 | **內容相符，兩處登錄缺漏 ＋ 兩處編輯瑕疵（→ M-5／M-9／m-1／m-2）** | ✅ 節數：`:6`「節數：**14**」，實數 §1–§14 齊備（`grep '^### '` 實算 14）。✅ `:5` Amended 行涵蓋「§11〜§14 新增；§13 的 blocking 宣稱撤回並依 Q5=A／Q6=A 改寫」。✅ §13 的 blocking 撤回（`:117`）與 U-4 `business-rules.md:49` 的定案同向，M-1 的兩讀法擇一**已完成**（取寬鬆讀法，U-8 合法性保住）。✅ `components.md:111` 的 §13 指標內容與改寫後的 §13 相符（C-4 ＋ `ref: ut` ＋ 使用者原話），且**workflow 對照表結構已修好**（`:106-109` 四列連續）。✅ `bolt-plan.md:64-67` 的 Bolt 2 DoD 已就地登錄 §3／§9／§13 三條，與 §13 `:127` 的自述相符。❌ **§14 的「確認人為 Bolt 1 的 gate」未登錄** `bolt-plan.md` 的 Bolt 1 DoD（`:54-56` 只有 §2 兩條）——而 ADR `:7` 的 Amends 行自稱修訂「Bolt 1／Bolt 2 的 DoD」（M-9）。❌ **R-7.4 對 U-8 的承接無收件人**（M-5）。❌ `:115` 的 `%s` 未填（m-1）、`:7` 的「以下原文」是截斷片段（m-2） |
| 10 | markdown 結構修復四處，且無新破壞 | **四處已修，但新增一處破壞、另有三處未盤點（→ M-10／m-5）** | ✅ `components.md` workflow 對照表：`:106-109` 四列連續，blockquote 移到 `:111`／`:113` 表後。✅ `component-methods.md` C-6 表：`:145-149` 連續，blockquote 在 `:151` 之後。✅ `ReconcileReport` 圍籬：`:168` 開、`:177` 閉、§7 指標在 `:179`（圍籬**外**）。✅ `U-6/business-rules.md` 的 R-5 群表：`:70-78`（含 R-5.5／R-5.10／R-5.6）與 `:110-116`（含 R-5.9／R-5.12／R-5.11）皆為連續表格。❌ **新破壞**：`U-6/business-rules.md` 的 R-7 方法表（表頭 `:183-184`）被本輪插入的 `Context` 段（`:195-203`）切斷，`:204-206` 三列（`render`／`content_hash`、`commit_and_push`、`notify`／`resolve_if_open`）成為孤兒，且 `:204` 緊貼 `:203` 的 blockquote 而無空行 ⇒ 會被當成 blockquote 的延續段落吞掉（M-10）。❌ **未盤點的既存破壞**：`U-4/domain-entities.md:40`（`pending_reverse` 列脫離 `:11-12` 的 schema 表）、同檔 `:35`（`managed_block_hash` 列被 `:29-34` 的巢狀 blockquote 與 `:27` 切開）、`U-6/domain-entities.md:19`（`產生者` 列脫離 `:13-14` 的 D-1 表）（m-5） |

### Findings

| # | 嚴重度 | 類別 | 檔案:行 | 發現 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| **C-1** | **Critical** | **新引入** | `U-7/business-rules.md:78`（R-6.2）、`:81`（R-6.5）；`U-6/business-rules.md:114-116`（R-5.9／R-5.12／R-5.11）；`U-4/domain-entities.md:35` | **C-1 的修法只修好 `SyncState` 五欄中的三欄；`managed_block_hash` 在同一批路徑上永久錯誤，而 R-6.2 明文禁止修復它——後果是 ADR-0015 §10／ADR-A6 逐字點名的最危險失敗模式重新可達。** 代入 R-5.9 的 ②：`write_status`→`Written`、`write_field`／`write_body` 成功、`read_item` 取回**新**雜湊、本地 `write_sync_state`、`commit_and_push` 回 `Rejected` ⇒ repo 內 `sync-state.json` 完全未變。③ 同形（回讀在 `write_body` **之後**才拋，區塊已經寫進去了）。此時：看板上的受管區塊＝**新內容**，repo 內 `managed_block_hash`＝**上一次成功那輪的舊雜湊**。次日 U-7 依 R-6.5 補平三欄，但 R-6.2 逐字「**不得動 `managed_block_hash`**——reconcile 的元件集合補了 C-4 之後**仍不含 C-6**，本單元不重寫受管區塊，**該欄位維持 U-6 寫入的值**」——**最後那半句在 ②③ 上是假的：U-6 從來沒把它寫進 repo**。三欄補平之後 U-6 依 R-5.2 判無漂移、依 R-5.5 不進寫入鏈 ⇒ **永遠不會重算該雜湊**。於是 U-8 每日 `read_item → parse → content_hash` 得到的值恆不等於儲存值 ⇒ 判定「有人改過看板」⇒ 這正是 `U-6/business-rules.md:83` 逐字描述的「**在沒有任何人為變更的情況下，U-8 每天為每個受管 intent 各開一則反向 PR**」。**這是修正動作本身的缺口**：R-5.11 逐字把修復落點指給 R-6.5，而 R-6.5 的覆蓋面比 R-5.9 描述的損害面窄兩欄 | U-7 有 C-3，`read_item` 回傳的 `ItemState` 本來就含 `managed_block_hash`（`component-methods.md:88`／`U-6/business-rules.md:75` 同一取法）——**取得它不需要 C-6**。R-6.2 的理由（「不重寫受管區塊」）與結論（「不得記錄其雜湊」）之間沒有蘊含關係。修法：R-6.5 觸發時**連同 `managed_block_hash` 一併由本輪 `read_item` 的回傳值回寫**，並把 R-6.2 收窄為「不得**重算**（不得走 C-6），但得從 `read_item` 轉錄」。同時把 R-5.9 的來源集合補上 `write_field`／`write_body` 回 `Failed` 這第四條路徑 |
| **C-2** | **Critical** | **新引入** | `U-6/business-rules.md:78`（R-5.10 (b)）對照 `:42`（R-3.1）、`:188`（R-7 表）；`business-logic-model.md:26` | **R-5.10 (b) 的「且不首建」放在一條結構上到不了它的分支上 ⇒ [req:FR-J3]／[US:S-3 AC 5] 在 `260802-default` 上仍不可滿足，iteration 4 的 C-2 沒有真的關閉。** R-5.10 是以 `Decision.reason_code` 分流的規則，而 `Decision` 只在**已綁定**路徑上存在：R-3.1（`:42`）逐字「**無綁定編號**者 \| 走首建路徑（U-3 的 `create_item`，[req:FR-A1]）」，R-7 表 `:188` 逐字把 `map` 的呼叫時機定為「**已綁定路徑**的判定」，序列圖 `:26` 亦然。⇒ 對一個未綁定的 record，流程在算出 `reason_code` **之前**就已經 `create_item` 了，R-5.10 (b) 沒有機會生效。而 [US:S-3 AC 5] 逐字點名的 `260802-default` **今日就在 registry 內且無綁定** ⇒ Bolt 1 首次執行仍會為它建卡。R-5.10 的說明段 `:118` 自己也承認「`create_item` 的首建路徑**也在違反範圍內**（它在 R-5.10 之前分岔）」——**承認了問題，但沒有動 R-3.1，也沒有動圖**。iteration 4 C-2 的修法逐字要求兩件事（R-5.10 分流 ＋ R-3.1 加可解析性前置），只做了第一件 | 兩條路二選一：(a) 把 `parse` 提到綁定分岔**之前**（`parse(record_path)` 不需要 binding，`component-methods.md:148` 的簽章允許），首建分支加「可解析（含白名單判定）」前置，並同步改 R-3.1 與序列圖 `:26`；或 (b) 明寫「首建不受 FR-J3 約束」並以 ADR 承載該例外——但那需要回頭改 [US:S-3 AC 5] 的逐字驗收，成本高於 (a) |
| **C-3** | **Critical** | **新引入** | `business-logic-model.md:36`、`:38`、`:42`、`:51`（對照 `business-rules.md:78`、`:115`） | **序列圖第三度沒有跟上本輪的新規則，且其中一處與新規則字面相反。** 本檔 `:53` 自述「**本單元就是寫入端，序列圖是實作者取用時序的第一份文件**」。三處：①`:36` 逐字「`Decision.status 為 null ──► 跳過 write_status（R-5.10）`」——只畫了 (a) 支，(b) 支的「不 `write_field`／不 `write_body`／不首建」在圖上不存在；②`:38` 逐字「`U-3 write_field（**失敗不連坐**）`」，而 R-5.12（`business-rules.md:115`）逐字「寫入鏈中任一步失敗時，本輪**不呼叫** `write_sync_state`（……`write_field` 或 `write_body` 回 `Failed`……皆同）」——照圖實作的人會在 `write_field` 失敗後**繼續往下走並回寫 `SyncState`**，而 R-5.12 的說明段 `:130` 逐字說明那會讓「[US:S-6 AC 5] 的告示**永久靜默消失**……一次網路抖動換一條 AC 永久落空」；③`:42` 的 `write_sync_state` 仍是無條件節點。附帶：`:51` 的重畫 blockquote 仍逐字寫「於 **2026-08-30T00:57:28Z** 整組重畫」並只列 iteration 3 的四項，本輪對 `:22-23` 的改動未被記載。**這是 iteration 3 C-2、iteration 4 C-4 的第三次同型復發**，且落在本輪兩條新規則上 | 重畫 `:32-44` 的寫入鏈：在 `Decision.status 為 null` 之下分 (a)／(b) 兩支；(b) 支只留 `write_sync_state`；(a) 支與 `mapped` 支的 `write_field`／`write_body`／`read_item` 三處各加一條「失敗 ──► U-5 notify，**本輪不回寫**（R-5.12）」；刪掉 `:38` 的「失敗不連坐」（它是 `component-methods.md:99` 對**Status 寫入**不連坐的說法，在此處會被讀成對回寫不連坐）；更新 `:51` 的重畫記載 |
| **M-1** | Major | **新引入** | `U-7/business-rules.md:79`（R-6.3）對照 `:81`（R-6.5） | **同一張表的兩列在「判定一致」這個輸入上直接互斥，且落敗的那一支會讓 C-1 的卡死原封不動回來。** R-6.3 逐字「**未補平的 intent 不回寫**（**含判定一致**、跳過、失敗三種）。沒有寫看板就沒有新的『上次寫入值』可記」；R-6.5 逐字「**判定一致時**，若 `SyncState` 三欄與本輪 `Decision` 不符，**仍回寫三欄**」。R-6.3 的括號逐項列舉了「判定一致」，措辭是無條件禁令，**未加任何「除 R-6.5 外」的但書**。依字面實作 R-6.3 的人不會寫 R-6.5，而 R-6.5 是 ADR-0015 §13（`:125`）指定的唯一修復點 | R-6.3 改為「未補平**且不符 R-6.5 的情形**者不回寫」，或把「含判定一致」從其括號中移除並改由 R-6.5 涵蓋該分支 |
| **M-2** | Major | **新引入** | `U-4/business-rules.md:38`（R-3.1）、`:47`；對照 `U-7/business-rules.md:107`（R-7.2）、`ADR-0015:121` | **iteration 4 M-1 未解，且本輪新增的 R-7.2 讓它從「自我否定」升級為「兩個單元對同一個方法呼叫給出相反規定」。** R-3.1 一字未改，仍逐字「**不得推 `ut`／`main`**。正向同步（**U-6**）只推觸發分支；**對帳（U-7）推其排程觸發分支**；反向同步（U-8）推自建的 `aidlc-sync/reverse/*` 分支」——而排程觸發分支經本輪實測（`U-7/functional-design-questions.md:55`）就是 `main`，第二子句因此要求做第一子句禁止的事。R-7.2 則逐字「推送落點為**從 `ut` 分叉的自建分支**，比照 U-8 的形狀；**不推 `main`**、不推 `ut`（U-4 的 R-3.1）」——它引用 R-3.1 為依據，而 R-3.1 的字面說的是相反的事。`:47` 的註記也仍是條件句「**若**預設分支就是 `main`，兩者直接衝突」並仍稱「ADR-0015 §13 **標出、不裁定**」，而 §13（`:121`）已逐字「**決定**：`actions/checkout` 明訂 `ref: ut`」 | R-3.1 第二子句改為「對帳（U-7）推**從 `ut` 分叉的自建分支**（見 U-7 的 R-7.2）」；`:47` 由條件句改為事實陳述並指向已裁定的 §13 |
| **M-3** | Major | **既存漏審** | `U-4/domain-entities.md:18`、`:56`（對照同檔 `:39`）；`U-6/business-rules.md:204` | **已撤回的 `content_hash` 取法在兩個單元的型別／方法宣告裡存活，而它正是 ADR-0015 §10 點名要消滅的那條路徑。** `U-4/domain-entities.md:18` 逐字「`managed_block_hash` … 上一次寫入時受管區塊的雜湊（**由 U-2 的 `content_hash` 產生**，本單元只儲存）」、`:56` 逐字「**`managed_block_hash` 由 U-2 產生**、本單元只儲存」——而**同一個檔案**的 `:39` 逐字「本欄位先前有產生者（**U-3**）、儲存者（本單元）、讀取者（U-8）」，且 R-5.4（`U-6/business-rules.md:75`）逐字定為「寫入後再呼叫一次 **`read_item`**，取其回傳 `ItemState` 的 `managed_block_hash` 欄位」。同型殘留在 `U-6/business-rules.md:204`：R-7 方法表仍列「`render` / **`content_hash(Block) -> sha256`** \| C-6 \| 受管區塊的渲染與**其雜湊（供 R-5.4 回寫）**」——**把已撤回的來源當成本單元的具名呼叫**（且與 `:193` 的 `render` 列重複）。依 `:18`／`:204` 實作的人會對 `render()` 的輸出算雜湊，即 `:83` 逐字描述的「兩者會**永久不相等**……U-8 每天為每個受管 intent 各開一則反向 PR」 | `U-4/domain-entities.md:18`／`:56` 改為「由 U-3 的 `read_item` 回傳、本單元只儲存；不得由 U-2 的 `content_hash` 對 `render()` 輸出計算（ADR-0015 §10）」；刪除 `U-6/business-rules.md:204` 這一列（`render` 已在 `:193` 有列，`content_hash` 本單元不呼叫） |
| **M-4** | Major | **新引入** | `U-6/business-rules.md:78`（R-5.10 (b)）對照 `:75`（R-5.4）、`:113`（R-5.8）、`:252`（R-6.2c） | **(b) 支的「僅回寫 `SyncState`」沒有可實作的定義，且與三欄的既有語意衝突；在一個可達的組合上會讓 [US:S-6 AC 5] 永久靜默。** ①**語意衝突**：R-5.8 逐字把三欄定義為「**機制上次寫進看板的值**」，而 (b) 支一個字都沒寫進看板；R-5.4 是本檔唯一定義回寫動作的規則，其前提逐字是「**看板寫入成功後**，五欄一起回寫」。②**未定義**：(b) 支要寫哪幾欄、`managed_block_hash` 與 `last_synced_at` 怎麼處理、是否呼叫 `commit_and_push`，全部沒有規則。③**可達的 AC 落空**：一個 `unparseable` 且落在 `reverse_rejected` 內的 intent（該 intent 必定已綁定，因為 U-8 為它開過 PR）會依 R-5.6 進入寫入鏈，但依 (b) 支不產生任何看板寫入 ⇒ 告示無載體；若此時仍回寫並推進 `last_synced_at`，R-6.2c 的判準（「PR 關閉時刻晚於 `last_synced_at`」）下一輪不再成立 ⇒ **告示永久消失且無紅燈**——與 R-5.12 說明段 `:130` 要防的失敗完全同形 | (b) 支明寫只更新 `last_reason_code`（並明寫 `last_status`／`last_field_value`／`managed_block_hash`／`last_synced_at` **不動**，理由是三欄的語意是「寫進看板的值」）；並為「(b) 支 ∩ `reverse_rejected`」補一條處置（例如該組合不視為告示已送、`last_synced_at` 不前進） |
| **M-5** | Major | **新引入** | `U-7/business-rules.md:109`（R-7.4）；`components.md:111`；`bolt-plan.md:75` | **R-7.4 把一項 blocking 要求指派給 U-8，而該指派沒有收件人——這正是 ADR-0015 自己 Context 段（`:17`）批評的「沒有收件人的便條」。** R-7.4 逐字「同一組規則**適用於 U-8**（反向同步亦為 `schedule` 觸發，同一個硬限制）。**落點在該單元**」。三項機械證據：①U-8 的 functional-design 已判 READY 且不會重跑；②對 `U-8/business-rules.md` grep `checkout`／`ref: ut`／`預設分支`／`schedule`／`排程` **零命中**；③`components.md:111` 把這條要求（含「同樣適用於 `aidlc-sync-reverse.yml`」）掛在「確認人為 **Bolt 2** 的 gate」，而 `bolt-plan.md:72` 顯示 U-8 屬 **Bolt 3**、`:75` 的 Bolt 3 DoD **零字提及**。⇒ Bolt 2 的 gate 會在 U-8 尚不存在時通過，Bolt 3 沒有人被要求檢查。後果不輕：`services.md:56` 確認 S-C 為 `schedule` 觸發，U-8 若在 `main` 的工作樹上跑，它拿落後的 record 與看板比對，`bolt-plan.md:74` 的「diff 不含 `aidlc-state.md`」與 FR-G2 的驗收全部建立在錯的基準上 | `components.md:113`（§5 那則 Bolt 3 指標）併入 `ref: ut` 對 reverse 的要求，或在 `bolt-plan.md:75` 的 Bolt 3 DoD 增列一條；並在 ADR-0015 §13 明寫「U-8 的部分確認人為 **Bolt 3** 的 gate」 |
| **M-6** | Major | **新設計問題** | `U-7/business-rules.md:108`（R-7.3）；`component-methods.md:169-176`、`:179`；`ADR-0015:121` | **R-7.3 為上游型別 `ReconcileReport` 新增一個欄位，但沒有任何承載。** `ReconcileReport` 的欄位集合定義在 `component-methods.md:169-176`（八欄），屬已核可上游。本輪同批處理的兩個同類項都有登錄：`undecidable` 在 `:179` 逐字「`ReconcileReport` **亦須含** `undecidable: [intent_id]`」、`latency_samples` 擁有權有 ADR-0015 §7。**唯獨 `ut` HEAD SHA 沒有**——ADR-0015 §13（`:121`）只在敘述句裡帶過「R-7.3 把 `ut` HEAD SHA 寫進報告以便事後查核」，未列為修訂節、未進 `:7` 的 Amends 行、`component-methods.md` 零指標。ADR 的 Consequences（`:146`）自己逐字要求「**「指標」必須真的存在於被修訂的檔案裡**」。附帶：Q6 選項 A（`U-7/functional-design-questions.md:59`）的代價欄寫的是「加一條**斷言**」，R-7.3 把它實作成報告欄位，兩者不是同一件事，該漂移也未被記載 | 比照 `undecidable` 的先例，在 `component-methods.md` §C-7 的 §7 指標段補一句「亦須含 `source_ref_sha`（R-7.3）」，並把它列進 ADR-0015 §13 的修訂清單與 `:7` 的 Amends 行 |
| **M-7** | Major | **新引入** | `U-6/business-rules.md:219`（R-6.1b）對照同條說明段 `:227`；`business-logic-model.md:83-89`（錯誤表） | **R-6.1b 的失敗值域是五個，其唯一依據段引的是四個；而多出來的那個值在本單元的錯誤表裡不存在。** R-6.1b 逐字「`reason_code` ∈ {`ExternalError`, `Rejected`, `Aborted`, `CannotCreate`, **`Failed`**}」；`:227` 逐字「U-5 的 `domain-entities.md` 早已明文……並列出實際值域（`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`）」——**同一頁上差一個值，沒有任何一句話說明 `Failed` 為何被加進來**。而 R-5.12（`:115`）確實要求 `Failed` 走 `notify`，**但錯誤表 `:83-89` 五列裡沒有 `Failed`**（只有 `reverse_pending` 查詢失敗／`ExternalError`／`Aborted`＋`CannotCreate`／`Rejected`／五種正常 `reason_code`）。R-5.12 的說明段 `:128` 自己逐字承認「先前 U-6 對它的 `Failed` 零規則、**錯誤表也無該列**」——**承認了兩個缺口，只補了一個** | 錯誤表增列「單一 intent 的 `Failed`（`write_field`／`write_body`）\| 續跑 ＋ 通報 ＋ **本輪不回寫**（R-5.12）\| 否（`component-methods.md:141` 逐字「只有 `ExternalError` 與 `Rejected` 紅燈」）」；並在 R-6.1b 或其說明段寫明 `Failed` 是本站對 U-5 值域的擴充及其理由，或指派 U-5 補進值域 |
| **M-8** | Major | **新引入** | `U-6/business-rules.md:219`（R-6.1b） | **R-6.1b 的觸發條件「本輪**處理成功**」在全 U-6 產出中只出現這一次、沒有定義，而本輪新增的兩條「什麼都不寫」的路徑正好讓它歧義。** R-5.10 (b) 支不產生任何看板寫入、R-5.5 的無漂移分支連寫入鏈都不進——這兩種算不算「處理成功」？若算，則上一輪真的失敗（issue 已開）的 intent 在下一輪只要判為 `unparseable` 或無漂移，`resolve_if_open` 就會關掉一則**仍然成立**的告警，`component-methods.md:139` 的可補回 AC（「同一個鍵連續發生兩輪 ⇒ 開啟中 issue 數為 1」）在該路徑上失守；若不算，則 `unparseable` 的 intent 的舊 issue 永遠關不掉，缺口 J-2 在該子集上仍未關。**這是 `project.md` 的 `functional-design:c10`（偵測 X 前先驗 X 可達／可判定）在述詞層的版本**，而 R-6.1b 正是本輪整條改寫的規則 | 明寫定義，例如「處理成功 ＝ 本輪對該 intent 完整跑完其分流路徑且無 `ExternalError`／`Rejected`／`Aborted`／`CannotCreate`／`Failed`」，並明確涵蓋 R-5.5 與 R-5.10 (b) 兩條無寫入路徑 |
| **M-9** | Major | **新引入** | `ADR-0015:136`（§14）；`bolt-plan.md:54-56` | **§14 是本輪新增、對 U-6 為 blocking、指定「確認人為 Bolt 1 的 gate」，但 Bolt 1 的 DoD 沒有它。** §14 逐字「**在它落地之前，`undecidable` 的自訂欄位行為未定義——實作不得自行猜一個前綴**……**確認人為 Bolt 1 的 gate**」，而 `undecidable` 在 Bolt 1 就可達（`component-methods.md` 判定順序第 7 條的兜底分支）且 R-5.10 (a) 會把它送進 `write_field`（`U-6/business-rules.md:189`）。`bolt-plan.md:54-56` 的 Bolt 1 DoD 只有 §2 增列的兩條（PRE-1-b、揭露回讀視窗）——**§14 未登錄**，同屬 Bolt 1 gate 的 §4／§6／§11／§12 亦然。對照組：**同一輪** Bolt 2 的 DoD（`:64-67`）就補上了 §3／§9／§13 三條。ADR `:7` 的 Amends 行自稱修訂「Bolt 1／**Bolt 2** 的 DoD」，只做到後者 | 在 `bolt-plan.md:54` 之下比照 Bolt 2 的形狀增列 §14（以及 §4／§6／§11／§12）的 gate 條目 |
| **M-10** | Major | **新引入** | `U-6/business-rules.md:194-206` | **本輪插入的 `Context` 段把 R-7 方法表切成兩截，且孤兒列緊貼 blockquote 會被吞掉。** R-7 表的表頭在 `:183-184`，資料列 `:185-193`；`:195-201` 插入了 `Context` 組裝的敘述與**另一張表**、`:203` 是說明用 blockquote；然後 `:204-206` 又出現三列原表的資料列（`render`／`content_hash`、`commit_and_push`、`notify`／`resolve_if_open`）——**沒有表頭、也沒有分隔列**，且 `:204` 與 `:203` 之間**沒有空行**，在 GFM 的 lazy continuation 下會被併進 `:203` 那個 blockquote 的段落。後果：`commit_and_push` 與 `notify`／`resolve_if_open` 這兩個本單元核心呼叫在渲染後**不在方法表裡**。這與 iteration 4 m-3 點名的四處是同一形狀，那四處已修好，本輪又在同一份檔案製造一處 | 把 `:195-203` 的 `Context` 段整段移到 R-7 表**之後**（`:206` 之下），讓 `:183-206` 成為一張連續的表；並刪除 `:204` 的重複 `render` 列（見 M-3） |
| **m-1** | Minor | **新引入** | `ADR-0015:115` | 標題逐字「**排程分支的落點（Q6=A 人工裁決，`%s`）**」——**格式佔位符 `%s` 未被填入**，而該處要記的正是一次人工裁決的時間戳。`project.md` 的 `user-stories:260822-us-L1` 逐字要求「寫入任何時間戳……前一律執行 `date -u` 取值」；此處不是編造而是漏填，但落在人工裁決的來源行上，可查證性受損。真值在 `U-7/functional-design-questions.md:65`（`2026-08-30T01:31:09Z`） |
| **m-2** | Minor | **新引入** | `ADR-0015:7` | Amends 行的「**以下原文：**」之後從「**對照表、**」起頭——這是**截斷片段而非原文**（原句開頭的「`application-design/components.md` 的 workflow」不見了）。該段的目的正是保留被更正前的原文供比對，截斷使它無法履行此功能 |
| **m-3** | Minor | **新設計問題** | `U-6/business-rules.md:145-152` | 前綴對照表把 `suppressed` 綁到 `frozen: `，依據欄逐字只寫「語意對應『凍結』」——`component-methods.md:56` 只列出四個前綴，**未把任何前綴綁到任何 `reason_code`**，故這是本站推論而非上游來源，卻放在標題為「依據」的欄位裡。同一張表以「前綴集合是 [ad:component-methods.md] 定的**格式契約**，加第五個前綴是上游修訂」為由拒絕為 `undecidable` 指派——**同一個理由對 `suppressed` 的指派同樣適用**。附帶：`skipped ` 在本表之後成為無 `reason_code` 消費者的孤兒前綴，未被記載 |
| **m-4** | Minor | **新引入** | `U-7/business-logic-model.md:113`、`:115` | iteration 4 C-4 逐字點名**三處**（序列圖、fallback、「與上游的對應」），只修了前兩處。`:113` 仍逐字「reconcile 的元件集合（**含 C-5**）引自 [ad:components.md]」，未提 ADR-0015 §13 補上的 **C-4**（而 C-4 正是本輪 R-6 群成立的前提）；`:115` 仍逐字「**本檔對上游的補充**：`undecidable` 欄位……與分母／批次上限的交界（R-3.4）。**一致率的兩類排除、`reconcile` 的簽章、單一 intent 失敗不中止整輪一字未改。**」——本輪新增了 R-6／R-7 兩群，該句讀起來仍像本輪無結構變更 |
| **m-5** | Minor | **既存漏審** | `U-4/domain-entities.md:35`、`:40`；`U-6/domain-entities.md:19` | 三處與 iteration 4 m-3 同型、但不在其列舉四處內的表格斷裂：①`U-4/domain-entities.md:40` 的 `pending_reverse` 列與 `:11-12` 的 schema 表被 `:20-39` 的長 blockquote 隔開 ⇒ 該欄位在渲染後不在 schema 表內；②同檔 `:35` 的 `managed_block_hash` 列被 `:29-34` 的巢狀 blockquote 與 `:27` 切開；③`U-6/domain-entities.md:19` 的「產生者 \| U-8」列被 `:18` 的 blockquote 與 `:13-16` 的 D-1 表切開。**第 10 項的「四處」盤點不完整** |
| **m-6** | Minor | **新引入** | `bolt-plan.md:67` | 插入 §13 條目時把 Bolt 2 原有的 DoD 本文吞進了該子項——`:67` 以「規則落點為 U-7 的 R-6／R-7 群。」結束 §13 的敘述後，緊接（同一行、雙空格分隔）「U-7 完成判準通過；PRE-1 第 2 項……成立。」而那是本 Bolt 的**基線** DoD，不屬 §13。渲染後基線 DoD 讀起來像 ADR-0015 §13 的附註 |
| **m-7** | Minor | **新設計問題** | `U-6/business-rules.md:116`（R-5.11）；`business-logic-model.md:95-105`（邊界情形表） | R-5.11 逐字「本單元下一輪對這種 intent 會判 `Aborted`……**這是正確的**……`Aborted` ＋ 通報是 [req:FR-C1] 要的行為」。判斷本身可接受，但**未寫下它的時間界與代價**：從 ②③ 發生到次日 U-7 的 R-6.5 補平為止，該 intent 的**每一次 push** 都會產生一則與事實不符的 `Aborted` 通報（看板此刻其實是對的）。`component-methods.md:139` 的去重使它收斂為 1 則 issue ＋ N 則 comment，不是災難——但這正是 iteration 2 判為 Critical 的「假通報」的一個受限版本，邊界情形表 `:95-105` 未記載 |
| **m-8** | Minor | **新引入** | `U-6/business-rules.md:112-116` | R-5.7 表的列序為 R-5.7 → R-5.8 → R-5.9 → **R-5.12** → **R-5.11**，序數倒置。本 stage 已因編號問題吃過兩次 findings（U-7 的 R-4→R-8 撞號、U-6 的 R-5→R-9 撞號），且本檔 `:40`（U-7）已為「編號不依出現順序」寫過說明段——U-6 這一處沒有 |
| **m-9** | Minor | **新引入** | `U-7/business-logic-model.md:26` | 本輪重畫的序列圖逐字「`U-4 read_sync_state ──► SyncState（**三欄 ＋ binding**）`」，而 `U-4/domain-entities.md:11-19`／`:40` 的 schema 是**七欄**（`schema_version`／`binding`／`last_status`／`last_field_value`／`last_reason_code`／`managed_block_hash`／`last_synced_at`／`pending_reverse`）。「三欄 ＋ binding」是本單元**用到**的子集而非型別本身；C-1 的修法之一（見該項建議）需要 `managed_block_hash`，屆時這個縮寫會誤導 |

### Summary

**整組 NOT-READY（3 Critical、10 Major、9 Minor，共 22 項）。**

**先說站得住的部分**：Q5=A／Q6=A 這兩次人工裁決的承接，**方向都是對的**。R-6.5 的「第三座標」論證成立——U-7 確實有 U-6 沒有的 record 座標，「看板 == record 而 `SyncState` ≠ 兩者」確實只可能來自遺失的回寫，我代入 R-5.9 ② 的完整時序後確認觸發條件真的滿足（查證 1c）。R-6.7 與 R-5.7「取法相反」的論證也成立——跨輪守門與單輪內樂觀鎖是兩個問題，U-7 的 `Aborted` 在並行 U-6 寫入下可達，`ReconcileReport.aborted` 不是死碼（查證 6c）。iteration 4 的 C-4／C-5 在 U-7 的序列圖上確實已關（查證 7），M-2 在 U-4 的引言上確實已關，四處 markdown 破壞確實已修（查證 10），`reverse_rejected` 在 U-6 的圖上確實有了產生者（查證 5）。R-5.10 (b) 支的**文字**、`undecidable` 缺前綴的**處置**都誠實且正確（查證 2a／4b）。

**問題全部出在同一個地方：修法的覆蓋面比它宣告的損害面窄。** 三個 Critical 是同一句話的三種說法——(1) R-5.9 說 `SyncState` 會落後，R-6.5 只修了五欄中的三欄（漏掉 `last_synced_at` 與 `managed_block_hash`），而其中要緊的 `managed_block_hash` 被 R-6.2 明文禁止修復，其後果恰是 ADR-0015 §10／ADR-A6 逐字點名的「沒有任何人為變更卻每天為每個 intent 開一則反向 PR」；(2) R-5.10 (b) 說 `unparseable` 不首建，而首建分支在算出 `reason_code` 之前就分岔了，R-3.1 與序列圖一字未動，[US:S-3 AC 5] 逐字點名的 `260802-default` 仍會在 Bolt 1 首次執行時被建卡；(3) 序列圖第三度沒跟上新規則，其中 `:38` 的「失敗不連坐」與 R-5.12 字面相反，照圖實作會重現 R-5.12 自己說要防的「一次網路抖動換一條 AC 永久落空」。

**類別計數（本輪停止條件的判斷依據）**：

| 類別 | 數量 | 內容 |
| --- | --- | --- |
| **`新引入`** | **17** | C-1、C-2、C-3；M-1、M-2、M-4、M-5、M-7、M-8、M-9、M-10；m-1、m-2、m-4、m-6、m-8、m-9 |
| **`既存漏審`** | **2** | M-3（`content_hash` 舊取法殘留在 U-4 schema 與 U-6 方法表）、m-5（三處未盤點的表格斷裂） |
| **`新設計問題`** | **3** | M-6（`ReconcileReport` 新欄位無承載）、m-3（`suppressed → frozen: ` 指派無上游來源）、m-7（假 `Aborted` 的時間界未記載） |

**這個分布本身是本輪最重要的結論**：22 項中有 17 項是修正動作造成的，只有 3 項是新設計面帶出的真問題、2 項是前四輪漏審。**缺陷不是來自設計難度，而是來自修法的傳播**——`project.md` 已有四條規則直指這個形狀（`application-design:260822-ad-L1`「改完逐一 grep 全部產出檔」、`units-generation:260822-ug-L1`「按事實掃不按字串掃」、`units-generation:rev1-L1`「總數是受影響事實」、`functional-design:c10`「修正動作本身也要過可達性檢查」），而本輪三個 Critical 各自被其中一條涵蓋：C-1 是「損害面窄於宣告」（可達性檢查的變體：R-6.5 對 `managed_block_hash` **不可達**）、C-2 是「修了規則沒修被它取代的分岔點」、C-3 是「改了規則沒改圖」的第三次復發。

**建議處理順序**：**C-2 與 C-3 先修**（兩者都是本檔內部的規則／圖對齊，不牽動其他單元的形狀，且 C-3 的圖修好之後 C-2 的分岔點會自己浮出來）→ **C-1 次之**（它需要同時動 U-7 的 R-6.2／R-6.5 與 U-4 的 `domain-entities.md`，並連帶解掉 M-3）→ **M-2／M-5／M-9 一批**（三者都是「已裁定的事沒有傳播到它的登錄點」，改法機械）→ 其餘。

**送審前自檢的第 1、2 項本應攔下其中五項**：可達性（第 1 項）本應攔下 C-1（R-6.5 對第五欄不可達）、C-2（R-5.10 (b) 在首建分支不可達）與 M-8（「處理成功」未定義即不可判定）；契約端點三問（第 2 項，範圍為整個 stage 產出）本應攔下 M-3（`managed_block_hash` 的「誰寫」在兩個單元有兩個相反答案）與 M-6（`ReconcileReport` 新欄位「誰擁有」答不出來）。這兩項在 `project.md` 的 `functional-design:user-1` 中是 **blocking、且要求在 stage summary 逐項報告**。

---

## Review (Iteration 6 — 四項 Critical 修正的確認審)

**Verdict**: **NOT-READY**（整組）
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T03:27:39Z
**Iteration**: 6
**涵蓋單元**: 全部 10 個（U-1／U-2／U-3／U-4／U-5／U-6／U-7／U-8／U-9／U-11）

**本輪性質（極窄）**：只回答一個問題——**那四個 Critical 的修正改對了嗎？有沒有引入新的 Critical？** `construction/functional-design/open-items.md` 已登錄的 30 項為使用者已核可帶進閘門的既知缺口，**本輪未重審、未列入發現**；前五輪已判過的事項亦然。

### 1. 逐修正確認表

| 修正 | 確認結果 | 依據（檔名:行 ＋ 逐字引文） |
| --- | --- | --- |
| **修正 1（原 A:C-1）** `managed_block_hash` 的修復缺口 | **部分成立**——(a)(b)(c) 三問各自通過，**但修正 3 使 R-6.8 的觸發條件在 R-5.9 ③ 上失效（見 C-6.1）**，且 iteration 5 C-1 點名的兩個缺欄只補了一個 | (a) **取值路徑一致，確認通過**：`U-7/business-rules.md:82` 逐字「值取自該次 `read_item` 回傳 `ItemState` 的 `managed_block_hash` 欄位（與 U-6 的 R-5.4 同一條取值路徑，故雜湊等價不變式成立）」；對照 `U-6/business-rules.md:82` 逐字「`managed_block_hash` ＝ 寫入後再呼叫一次 `read_item(binding, Config)`，取其回傳 `ItemState` 的 `managed_block_hash` 欄位」；兩者的來源同為 `U-3/domain-entities.md:13` 逐字「由 issue body 經 U-2 的 `parse` ＋ `content_hash` 得出」，即 `ADR-0015:69`（§10）要求的「必須與 U-8 日後 `read_item → parse → content_hash` 算出的值**逐位元組相等**」那一條路徑。且 U-7 在該分支上**確實有** `read_item`（`U-7/business-logic-model.md:35` 逐字「`U-3 read_item ──► ItemState（看板現況）`」，位在三方比對之前，對「判定一致」的 intent 同樣執行）。<br>(b) **R-6.2 的限定不漏情形，確認通過**：`U-7/business-rules.md:78` 逐字「**補平路徑（R-6.1）不得動 `managed_block_hash`**……**本條不適用於 R-6.5 的修復路徑**」。補平只經 C-3 `write_status` 寫 Status 欄、不重寫受管區塊，看板上的區塊未變 ⇒ 該欄本就不該動，限定後無遺漏。<br>(c) **R-6.3 與 R-6.5 無矛盾，確認通過**：`:79` 逐字「**未補平的 intent 不回寫**——**但 R-6.5／R-6.8 的修復路徑除外**。適用範圍限於「跳過」與「補平失敗」兩種」，iteration 5 的 A:M-1（兩列字面互斥）已關閉。<br>**未關的部分**：iteration 5 C-1 逐字指出 R-6.5「只修了五欄中的三欄（漏掉 **`last_synced_at`** 與 `managed_block_hash`）」，本輪只補了後者——`:81` 仍是「仍回寫**三欄**」，`:82` 加一欄，`last_synced_at` 在修復路徑上仍不前進（見 M-6.1） |
| **修正 2（原 A:C-2）** FR-J3 的閘門層級 | **成立** | (a) **`create_item` 不再可能對 `unparseable` 發生，確認通過**：`U-6/business-rules.md:42`（R-3.0）逐字「**任何 intent，分流之前先算 `Decision`**（U-1 composite action）。`reason_code` ∈ {`unparseable`, `whitelisted`} ⇒ **本輪對它不做任何看板動作**——不首建、不寫入、不渲染」，且 `:43`（R-3.1）已改為「**通過 R-3.0 且**無綁定編號者」；序列圖 `business-logic-model.md:31-34` 的閘門節點位在 `:36`「否 ──► 依綁定分流」之上。閘門位於**全部**產生看板寫入之分支的共同上游，符合 `project.md` 的 `functional-design:c34`。此處無隱藏第三條分支：U-6 的看板寫入只有首建（`create_item`）與寫入鏈兩條。<br>(b) **「未綁定且 `unparseable` 連狀態檔都不建」不使既有規則失效，確認通過**：下一輪如何得知它被判過——`:50` 逐字「**該 intent 每輪重新判定，成本是一次純函式呼叫**」，`map()` 為純函式（`U-1/business-rules.md:107` 的總函式性），不需要跨輪記憶；U-7 側亦不受影響（`U-7/business-rules.md:28` R-2.1 逐字「分母 = **已綁定的** intent − …」，未綁定者本就不進分母，`U-7/business-logic-model.md:24` 逐字「`binding` 為 null 者跳過」）。<br>(c) **未綁定 intent 的 `read_sync_state` 有定義，確認通過**：序列圖 `:27` 逐字「`U-4 read_sync_state ──► SyncState（binding ＋ 六欄；**未建檔則視為全空**）`」。`map()` 不讀 `binding`（`U-1/business-rules.md:38-46` 的 R-3 判定表七條無一涉及 binding），故把它提到分流之前對 U-1 無影響 |
| **修正 3（原 A:C-3）** 序列圖與 R-5.12 | **不成立**——(c) 序列圖已對齊，但 (a)(b) 兩問的答案都是否定的，**本輪兩個新 Critical 皆源於此** | (a) **逐欄寫法無法同時滿足兩邊**。`write_field` 失敗的下一輪時序實走一遍，**這一支是對的**：`:122` 第二點「回寫 `last_status`／`last_reason_code`／`last_synced_at`，**`last_field_value` 維持原值**」⇒ 次輪 R-5.2 三欄比對在 `last_field_value` 上仍有差異 ⇒ 進寫入鏈 ⇒ `expected`（status 新、field 舊）與看板現況（status 新、field 舊，因寫入失敗未變）相符 ⇒ 不 `Aborted` ⇒ 重試 `write_field` ⇒ 自癒。**但第三點的兩種情形被合併處理，而它們的正確性相反**——`write_body` 回 `Failed` 時區塊未變（保留舊雜湊正確），R-5.4 回讀拋 `ExternalError` 時區塊**已變**（保留舊雜湊即永久錯誤），見 **C-6.1**。<br>(b) **`write_body` 失敗時 `last_synced_at` 會前進，[US:S-6 AC 5] 的告示因此不會重試**。`:122` 第三點逐字「⇒ **回寫前四欄**」，而五欄的順序由 `:82` 定為 `last_status`／`last_field_value`／`last_reason_code`／`last_synced_at`／`managed_block_hash` ⇒ 前四欄**含** `last_synced_at`。這與 `:137` 的修法自述逐字「`last_synced_at` 只在有欄位真的寫成功時前進，所以 R-6.2c 的告示條件在 `write_body` 失敗時仍然成立——**告示下一輪會重試，這正是 B:C-1 要的**」**直接相反**：`write_body` 失敗的那一輪 `write_status`／`write_field` 已成功，「有欄位真的寫成功」為真 ⇒ 前進。見 **C-6.2**。<br>(c) **序列圖與 R-5 群逐條一致，確認通過**：`:44`↔R-5.12①、`:48-49`↔R-5.12②、`:52-53`↔R-5.12③、`:38`↔R-5.2∪R-5.6、`:45`↔R-5.10 (a)、`:31-34`↔R-3.0，六處逐條核對相符，`:66` 的文字 fallback 亦同步。**唯一未上圖的分支**是 `:54` 的 `read_item` 回讀無錯誤出口（R-5.12 第三點的另一半情形），該遺漏正是 C-6.1 的圖側表現 |
| **修正 4（原 B:C-1）** 受管標記語法 | **成立**（核心目的達成），**附兩項 Major 未定義** | (a) **`parse` 簽章確實不需改，確認通過**：`U-2/domain-entities.md:87` 逐字「**`render` 的輸出一律含這一對標記**（首尾各一），這使 `write_body` 只需字串搜尋即可定位，**不需要 `parse` 回傳跨度**——`parse` 的簽章因此一字未改」；`U-3/business-rules.md:95`（R-6.3）逐字「本方法**自行以字串搜尋定位**，不需要呼叫端傳入跨度」，兩側一致。U-3 不再自建格式副本（`:94` 逐字「本單元**引用**它們，**不得自建副本**」），B:C-1 的核心損害（第二份格式知識落在 R-4 群互鎖之外）確實消除。<br>(b) **版本內嵌與既有兩節一致、無重複物化，確認通過**：`:83` 的值 `<!-- aidlc-sync:begin v=<format_version> -->` 與 `:11`（`Block.format_version` 逐字「**內嵌於區塊文字中**」）、`:94-96`（「版本必須是**區塊自己帶的**……`parse` 因此是**版本分派**的：先讀版本標記」）三處指同一份物化，無第二份。<br>(c) **R-6.6 與 `parse` 對同一情形的行為不一致**——`U-3/business-rules.md:96` 為「BEGIN 有、END 無」定了 `Failed` ＋ 通報，而 U-2 對 `parse` 的同一情形**全無規則**（`:96` 只涵蓋「找不到版本標記 → 回 `null`」，而此情形版本標記是找得到的，它內嵌於 `BEGIN`）。見 **M-2.1** |

### 2. 逐單元 verdict

| 單元 | Verdict | 依據 |
| --- | --- | --- |
| U-1 map-parse-action | **READY** | 本輪未變更。連帶影響已查：R-3.0 把 `map()` 提到綁定分流之前，而 `business-rules.md:38-46` 的 R-3 判定表七條無一讀 `binding`、`:107` 的總函式性保證任一輸入恰得一個 `Decision`，故提前呼叫不影響本單元；`domain-entities.md:23` 的 `ParsedRecord.binding` 反使該提前呼叫更自然。**無連帶影響** |
| U-2 managed-block | **READY**（2 Major，未達門檻） | 修正 4 的常數定義成立（見上表）。兩項 Major：**M-2.1**（`parse` 對「BEGIN 有、END 無」無規則，與 U-3 的 R-6.6 不對稱）、**M-2.2**（`MANAGED_BLOCK_BEGIN` 的值內嵌 `<format_version>`，使跨版本的字串比對語意未定義） |
| U-3 board-client | **READY**（1 Major，與 U-2 共用 M-2.2） | R-6.2／R-6.3 改為引用具名常數、R-6.6 新增，皆成立；`domain-entities.md:50` 已同步 R-5.12 的逐欄語意（逐字「維持 `managed_block_hash` 原值、其餘欄位照常回寫」），跨檔傳播到位 |
| U-4 binding-store | **READY**（1 Major） | 本輪未變更，但**有連帶影響**：修正 1 新增了 `managed_block_hash` 的第二個寫者（U-7 的 R-6.8），而本單元 `domain-entities.md:39` 仍逐字「**`managed_block_hash` 的寫者是 U-6 的 R-5.4**」——該欄位的「誰寫」在其**擁有者**的 schema 檔上現在是不完整的答案（**M-4.1**）。`:35` 那一列只講補平路徑，字面未被 R-6.8 推翻 |
| U-5 notifier | **READY** | 本輪未變更。R-5.12 的「每一種失敗都交 C-5 `notify`」與本單元 R-1 表值域的落差（`Failed` 不在表內）**已登錄為 open item A:M-7**，非本輪新引入。**無新的連帶影響** |
| U-6 forward-workflow | **NOT-READY** | **C-6.1**、**C-6.2** 兩個新 Critical 皆落在本單元的 R-5.12（`business-rules.md:122`）及其自述（`:137`） |
| U-7 reconcile-workflow | **NOT-READY** | **C-6.1 的另一端**：R-6.8 掛在 R-6.5 的觸發條件（`:81`「`SyncState` **三欄**與本輪 `Decision` 不符」）之下，而修正 3 讓 R-5.9 ③ 不再滿足該條件 ⇒ 修復路徑對它不可達。另 **M-6.1**（`last_synced_at` 在修復路徑上不前進） |
| U-8 reverse-workflow | **READY** | 本輪未變更，本單元文字無新的不一致。**但它是 C-6.1 的受害端**：`business-rules.md:9`（R-1.1）逐字「以 U-2 的 `content_hash` 與 `sync-state.json` 記錄的雜湊比對」、`:11`「雜湊已變 → 寫 `pending_reverse` 並開 PR」——C-6.1 使該比對恆不相等。此為 U-6／U-7 缺陷的爆炸半徑，不是本單元的缺陷 |
| U-9 selftest-workflow | **READY** | 本輪未變更、無連帶影響（R-1.1〜R-1.3 三條突變與 R-3 的觸發集合皆不涉及本輪四項修正所改的規則） |
| U-11 readme-pointer | **READY** | 本輪未變更、無連帶影響（`business-rules.md` 僅 R-1／R-2 兩條，與看板寫入鏈及受管標記零交集） |

### 3. 新引入的 Critical

**有，兩項。兩項皆由修正 3（R-5.12 改為逐欄）造成，其中 C-6.1 直接使修正 1 在它要防的那條路徑上失效。**

| # | 嚴重度 | 類別 | 檔案:行 | 發現 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| **C-6.1** | **Critical** | **新引入（修正 3 造成，抵銷修正 1）** | `U-6/business-rules.md:122`（R-5.12 第三點）、`:121`（R-5.9 ③）、`:123`（R-5.11）；`U-7/business-rules.md:81`（R-6.5）、`:82`（R-6.8）；`U-6/business-logic-model.md:54` | **R-5.12 把兩種正確性相反的失敗合併成同一條處置，於是 R-5.9 ③ 變成 `managed_block_hash` 的永久錯誤，且修正 1 的修復路徑對它不可達——ADR-A6／ADR-0015 §10 點名的最危險失效模式重新可達。** R-5.12 第三點逐字「`write_body` 回 `Failed` **或 R-5.4 的回讀拋 `ExternalError`** ⇒ 回寫前四欄，**`managed_block_hash` 維持原值**」。兩者的看板狀態相反：`write_body` 回 `Failed` 時區塊**沒寫進去**（保留舊雜湊正確）；R-5.4 的回讀在 `write_body` **成功之後**才執行（序列圖 `:52`→`:54` 的順序），拋 `ExternalError` 時區塊**已經是新內容**，保留舊雜湊即為錯誤。完整時序：①本輪 `write_status`／`write_field`／`write_body` 全部成功 → `read_item` 拋 `ExternalError` → 依 R-5.12 回寫**前四欄**、雜湊留舊值；②次輪 R-5.2 三欄比對——三欄**已在①寫成當輪 `Decision`**，`Decision` 未變 ⇒ **無漂移** ⇒ 依 R-5.5 不進寫入鏈 ⇒ 雜湊永遠不會被重算；③U-7 側同樣打不到：R-6.5 的觸發條件逐字是「`SyncState` **三欄**與本輪 `Decision` 不符」，而三欄此刻**相符** ⇒ R-6.5 不觸發 ⇒ 掛在它下面的 R-6.8 **不可達**；④U-8 每日 `read_item → parse → content_hash` 得新雜湊 ≠ 儲存的舊雜湊 ⇒ 依其 R-1.3 開 PR ⇒ **在沒有任何人為變更的情況下，每天為該 intent 開一則反向 PR**（`U-6/business-rules.md:90` 逐字描述的正是這個後果）。**修正 3 之前這條路徑是被覆蓋的**：舊 R-5.12「任一步失敗即完全不回寫」使三欄一併過期 ⇒ R-6.5 觸發 ⇒ R-6.8 修復。修正 3 把三欄補新之後，修正 1 唯一的入口就關上了。附帶：`:123`（R-5.11）逐字「**②③ 的修復落點在 U-7 的 R-6.5**」在 ③ 上不再成立；`business-logic-model.md:54` 的 `read_item` 節點也沒有錯誤出口，圖上看不出這條路徑存在 | 二選一，**建議 (a)**：(a) 把 R-5.12 第三點**拆成兩條**——`write_body` 回 `Failed`（區塊未變）⇒ 回寫前四欄、雜湊留舊值；**R-5.4 的回讀拋 `ExternalError`（區塊已變、雜湊未知）⇒ 該 intent 本輪完全不回寫**（回到全有全無），使三欄一併過期、R-6.5／R-6.8 重新可達，並同步更新 `:121` R-5.9 ③ 的敘述、`:123` R-5.11、序列圖 `:54` 的錯誤出口。(b) 為 U-7 的 R-6.5 增設**第四個觸發條件**：「三欄相符但 `SyncState.managed_block_hash` ≠ 本輪 `read_item` 回傳的 `managed_block_hash`」亦視為遺失的回寫，一併回寫該欄；(b) 的成本是 R-6.5 由三欄比對擴為四座標比對，且需同步 `U-7/business-logic-model.md:36-40` 的三方比對節點 |
| **C-6.2** | **Critical** | **新引入（修正 3 造成，重開 iteration 4 的 B:C-1）** | `U-6/business-rules.md:122`（R-5.12 第三點）、`:137`（修法自述）、`:84`（R-5.6）、`:265`（R-6.2c）、`:143`（B:C-1 原文） | **`write_body` 失敗時 `last_synced_at` 仍前進，使 [US:S-6 AC 5] 的告示永久靜默消失——這正是 iteration 4 B:C-1 的原文，而 R-5.12 的自述宣稱它不會發生。** 三條規則合起來即可機械判定：①`:122` 第三點「`write_body` 回 `Failed` ⇒ **回寫前四欄**」，而 `:82`（R-5.4）定義的五欄順序使「前四欄」**包含 `last_synced_at`**；②`:265`（R-6.2c）逐字「下一輪的查詢以 **PR 關閉時間晚於 `last_synced_at`** 為準」；③`:84`（R-5.6）的第二個漂移來源正是該條件。時序：某 intent 落在 `reverse_rejected` ⇒ R-5.6 判有漂移 ⇒ 進寫入鏈 ⇒ `write_status`／`write_field` 成功、`write_body` 一次暫時性失敗（**告示只存在於受管區塊，因此未送達**）⇒ 回寫前四欄，`last_synced_at` 前進到本輪 ⇒ 次輪 R-6.2c 的比較不再成立 ⇒ 該 intent 離開告示待送集合；同時三欄已與 `Decision` 相符 ⇒ 三欄比對亦無漂移 ⇒ **整條鏈不再啟動，告示永久消失且無紅燈，受管區塊永久凍在舊內容**。這與 `:143` 逐字記載的 B:C-1 完全同形（「一次網路抖動換一條 AC 永久落空」）。而 `:137` 的修法自述逐字「`last_synced_at` 只在有欄位真的寫成功時前進，所以 R-6.2c 的告示條件在 `write_body` 失敗時仍然成立——**告示下一輪會重試**」——`write_body` 失敗那一輪確實「有欄位真的寫成功」（Status 與自訂欄位），故該句的前提成立而結論相反，**規則本文與其自述互相否定** | R-5.12 第三點改為「`write_body` 回 `Failed` ⇒ 回寫 `last_status`／`last_field_value`／`last_reason_code`，**`last_synced_at` 與 `managed_block_hash` 皆維持原值**」——`last_synced_at` 的語意收斂為「上一次成功寫入**受管區塊**的時刻」時，R-6.2c 的告示重試與 R-5.6 的第二個漂移來源才會如 `:137` 所宣稱地成立；同時把 `:137` 的自述改寫為與規則本文一致，並在 `business-logic-model.md:52-53` 的 `write_body` 失敗出口補上「`last_synced_at` 亦維持原值」。**本項與 C-6.1 的修法必須一起看**：若採 C-6.1 的 (a) 方案，本項只需處理 `write_body` 回 `Failed` 這一支 |

### 4. 非 Critical 的連帶發現（不影響本輪判定，供 code-generation／閘門參考）

| # | 嚴重度 | 檔案:行 | 內容 |
| --- | --- | --- | --- |
| **M-6.1** | Major | `U-7/business-rules.md:81`（R-6.5）、`:82`（R-6.8） | **修正 1 只補了 iteration 5 C-1 點名的兩個缺欄之一。** 該項逐字指出 R-6.5「只修了五欄中的三欄（漏掉 **`last_synced_at`** 與 `managed_block_hash`）」；本輪 R-6.8 補了雜湊，`last_synced_at` 仍不在修復範圍。後果有界但真實：R-6.5 觸發的前提是「U-6 寫了看板但沒記錄」，那一次寫入的時刻無人記下，`last_synced_at` 停在更早的值 ⇒ 若該 intent 的反向 PR 關閉時刻落在兩者之間，R-6.2c 的判準會在下一輪再判一次「告示待送」⇒ **同一則告示出現兩次**，違反 R-6.2c 逐字的「告示只出現一次」。非永久性失效，故不列 Critical |
| **M-2.1** | Major | `U-2/domain-entities.md:96`；對照 `U-3/business-rules.md:96`（R-6.6） | **標記損壞的處置只定義了寫入側，未定義解析側。** U-3 的 R-6.6 為「找到 `BEGIN` 但找不到 `END`（或順序顛倒）」定了 `Failed` ＋ 通報；U-2 對 `parse` 的同一輸入**無任何規則**——`:96` 只涵蓋「找不到版本標記 → 視為無標記 → 回 `null`」，而此情形版本標記是**找得到**的（它內嵌於 `BEGIN`）。實作者必須自行決定 `parse` 在此回什麼，而該回傳值決定 `ItemState.managed_block_hash` 是 `null` 還是某個雜湊，進而決定 U-8 是「跳過不視為人為變更」還是「開 PR」 |
| **M-2.2** | Major | `U-2/domain-entities.md:83`；`U-3/business-rules.md:95`（R-6.3） | **`MANAGED_BLOCK_BEGIN` 的值內嵌 `<format_version>`，使 `write_body` 的字串比對在跨版本時語意未定義。** R-6.3 逐字「body 內**無** `MANAGED_BLOCK_BEGIN` 時，把區塊**附加**在既有內容之後」——若比對的是含版本的完整字面，看板上以 v=N 寫成的舊區塊在渲染器升到 v=N+1 之後**找不到**，於是**附加**出第二個受管區塊。這正好落在 ADR-A6／[Q1=C] 三道互鎖所規範的 bump ＋ 重新基準化那條路徑上（`U-2/domain-entities.md:88` 逐字「改動標記語法即格式變更，須 bump `format_version` 並於同一 PR 重新基準化」），而重新基準化恰恰需要定位舊版本的區塊。首次上線（v=1、既有受管 item 數為 0）不受影響，故非 Critical |
| **M-4.1** | Major | `U-4/domain-entities.md:39` | **`managed_block_hash` 的「誰寫」在其擁有者的 schema 檔上已成不完整的答案。** 該行逐字「**`managed_block_hash` 的寫者是 U-6 的 R-5.4**」，而修正 1 新增了第二個寫者（U-7 的 R-6.8）。這是 `project.md` 的 `units-generation:260822-ug-L1`（按事實掃、不按改過的字串掃）點名的形狀——同一個事實在 U-7、U-6、U-4 三處有三種表達，本輪只改了前兩處 |
| **m-6.1** | Minor | `U-6/business-rules.md:122`（R-5.12 第二點） | 第二點只列出 `write_field` 失敗時**寫哪三欄**（`last_status`／`last_reason_code`／`last_synced_at`），未說 `managed_block_hash` 是否回寫，而該支的鏈仍會走完 `write_body` 與 R-5.4 的回讀。因該支必留下三欄漂移、次輪會重跑整條鏈，不論怎麼解讀都會自癒，故僅列 Minor |
| **m-6.2** | Minor | `U-6/business-logic-model.md:40-56` | 寫入鏈的 ASCII 縮排把 `write_field`／`render`／`write_body`／`read_item`／`write_sync_state` 五步畫在「`Decision.status` 為 `null`」那一支之下，字面上讀不出 `mapped` 支也走這五步；`:66` 的文字 fallback 逐字「為 `null` 時跳過 Status 寫入但**其餘照走**；接著寫自訂欄位……」已消歧義，故僅列 Minor |
| **m-6.3** | Minor | `U-6/business-rules.md:79`（R-5.1）對照 `business-logic-model.md:27` | R-3.0 使序列圖把 `read_sync_state` 提到分流之前、對**全部** intent 執行（`:27` 逐字「未建檔則視為全空」），而 R-5.1 仍逐字「對每個**已綁定** intent 呼叫一次 `read_sync_state`」。兩者都可實作（圖是規則的超集），但同一個動作的適用範圍在兩份文件上不同 |
| **m-6.4** | Minor | 四項修正在四份檔案中的時間戳 | 四項修正一律標記 **2026-08-30T02:47:00Z（依檔案 mtime 重建；原填 09:55:00Z 為未經 `date -u` 的編造值，已更正）**（例：`U-7/business-rules.md:86`、`U-6/business-rules.md:135`、`U-2/domain-entities.md:77`、`U-3/business-rules.md:100`），而本輪以 `date -u` 取得的真實時刻為 **2026-08-30T03:27:39Z**，四份檔案的 mtime 分別落在 **02:44:39Z〜02:49:25Z**。標記值比實際寫入時刻**晚約 7 小時**且秒數為整。`project.md` 的 `user-stories:260822-us-L1` 逐字要求「寫入任何時間戳……前一律執行 `date -u` 取值」。本項不影響任何設計判斷，但它污染的是這一批修正的可查證性本身 |

### Summary

**四項修正中，修正 2 與修正 4 成立，修正 1 的三個確認點各自通過但被修正 3 抵銷，修正 3 不成立——它引入的兩個新 Critical 中，有一個直接把修正 1 的修復路徑關掉。**

修正 2（R-3.0 把 `Decision` 上提到分流之前）是四項中最乾淨的一項：閘門確實位在全部看板寫入分支的共同上游，(a)(b)(c) 三問全數通過。修正 4 消除了「U-3 自建第二份格式知識」這個核心損害，`parse` 簽章確實不需改，只留下兩項未定義（解析側的損壞處置、跨版本的標記比對），皆非首次上線可達。

**問題集中在修正 3。** 它把 R-5.12 由「全有全無」改為「逐欄」，而**逐欄的粒度切在錯誤的地方**：第三點把「`write_body` 回 `Failed`」（區塊未變，保留舊雜湊正確）與「R-5.4 的回讀拋 `ExternalError`」（區塊已變，保留舊雜湊即永久錯誤）合併成同一條處置。後者於是留下一個三欄皆新、雜湊過期的狀態——**這個狀態既不會讓 U-6 判出漂移，也不滿足 U-7 R-6.5 的觸發條件**，於是修正 1 新增的 R-6.8 對它不可達，U-8 每天為該 intent 開一則無人為變更的反向 PR（C-6.1）。同一點還讓 `last_synced_at` 在 `write_body` 失敗時前進，使 [US:S-6 AC 5] 的告示永久靜默——那正是 iteration 4 B:C-1 的原文，而 R-5.12 的自述（`:137`）逐字宣稱它不會發生（C-6.2）。

**這兩項與 iteration 5 的診斷同形**（「修法的覆蓋面比它宣告的損害面窄」），但形狀更窄一階：不是漏掉同一事實的其他表達面，而是**一條新規則的適用範圍涵蓋了兩種正確性相反的情形**。可執行的判準：把「本輪失敗時看板處於什麼狀態」逐一寫下來，再決定哪幾欄可以回寫——`write_status` 失敗（看板未動）、`write_field` 失敗（欄位未動、Status 已動）、`write_body` 失敗（區塊未動）、回讀失敗（**全部已動、只是沒讀回來**）是四種狀態，而 R-5.12 只給了三條。

**修法相依性**：C-6.1 採 (a) 方案（把回讀失敗拆回全有全無）時，C-6.2 只需處理 `write_body` 回 `Failed` 那一支，兩者共用同一次編輯；採 (b) 方案（擴充 R-6.5 為四座標比對）則兩項需分別修，且會動到 U-7 的序列圖。**兩項都落在 R-5.12 這一條規則及其自述上，不牽動修正 2 與修正 4**——後兩者已確認成立，重修時不需回頭動它們。

---

## Review (Iteration 7 — C-6.1／C-6.2 修法的最終確認)

**Verdict**: **NOT-READY**（整組）
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T03:47:14Z
**Iteration**: 7
**涵蓋單元**: 全部 10 個（U-1／U-2／U-3／U-4／U-5／U-6／U-7／U-8／U-9／U-11）

**本輪性質（極窄）**：只確認一項修正——iteration 6 的 C-6.1／C-6.2 修法是否成立、有沒有再引入新的 Critical。`construction/functional-design/open-items.md` 已登錄的既知缺口、iteration 6 的 4 Major／4 Minor 連帶發現、前六輪判過的事項，**本輪未重審、未列入發現**。

**結論一句話**：**規則層（`business-rules.md`）的修法成立，兩個 Critical 在規則本文上確實關閉；但修法只走到規則本文，沒有走到它的其他表達面**——`write_body` 失敗的處置在**四個**位置仍逐字載著修正前的行為（其中兩處是 iteration 6 建議欄逐字點名的落點），且新增的 R-5.13 與 U-7 既有的 R-6.1 直接矛盾。

### 1. 逐項確認表（(a)〜(e)）

| 項 | 結果 | 依據（檔名:行 ＋ 逐字引文） |
| --- | --- | --- |
| **(a)** C-6.1 是否真的關閉？ | **通過（規則層）**——且 U-6 與 U-7 **不會互相搶** | 修法逐字在 `U-6/business-rules.md:122`（R-5.12 第四點）：「**R-5.4 的回讀拋 `ExternalError`** ⇒ 受管區塊**已經寫成功**，只是算不出它的雜湊 ⇒ **完全不回寫**，交由 U-7 的 R-6.5／R-6.8 修復」。實走時序：①本輪三步全成功、回讀拋錯 ⇒ 五欄皆舊；②次輪 U-6 依 `:80`（R-5.2）三欄比對 `Decision`（新）↔ `SyncState`（舊）⇒ **有漂移** ⇒ 進寫入鏈 ⇒ `:119`（R-5.7）的 `expected` 由舊三欄重建 ⇒ `U-3/business-rules.md:23`（R-2.1）「`actual != expected` → 回 `Aborted{actual, expected}`，**不送出寫入**」⇒ 本檔 `:44` 逐字「**整條鏈中止、完全不回寫**（R-5.12）」。**看板一個字都沒被動、`SyncState` 也沒被動 ⇒ R-6.5 的觸發條件（看板 == record 而 `SyncState` ≠ 兩者）原封保留，不存在「U-6 先重寫一次而讓 R-6.5 失去觸發機會」**；`:124`（R-5.11）逐字「本單元下一輪對這種 intent 會判 `Aborted`……**這是正確的**」與此一致。③每日對帳 `U-7/business-rules.md:81`（R-6.5）＋ `:82`（R-6.8）補回三欄＋`managed_block_hash`＋`last_synced_at` ⇒ U-8 的雜湊比對恢復相等 ⇒ ADR-A6 的假反向 PR 不再每日重複。**另一支亦查**：`Decision.status` 為 `null` 時走 `:85`（R-5.10 (a)）跳過 `write_status`、沒有守門 ⇒ 鏈照走並在回讀成功的次輪自癒；重寫內容與看板現況相同，同樣不與 R-6.5 相爭 |
| **(b)** C-6.2 是否真的關閉？ | **通過（規則層）** | `:122`（R-5.12 第三點）逐字「**`write_body` 回 `Failed`** ⇒ 受管區塊**未被寫入**……回寫 `last_status`／`last_field_value`／`last_reason_code`，**`managed_block_hash` 與 `last_synced_at` 皆維持原值**」。兩輪時序：①`write_status`／`write_field` 成功、`write_body` 失敗 ⇒ 三欄回寫、`last_synced_at` **不前進**；②次輪 `:84`（R-5.6）第二來源「該 intent 在本輪的 `reverse_rejected` 內且其 PR 關閉時刻晚於 `last_synced_at`」**仍成立** ⇒ 進寫入鏈；`expected` ＝三欄（新）＝看板現況（新，Status／欄位已寫成功）⇒ **不 `Aborted`** ⇒ `:274`（R-6.2b）重新帶入 `Context.rejection_notice` ⇒ `write_body` 重試。**告示確實會重試。** 另確認 R-5.13 不傷 R-5.6 的另一個用途：三欄漂移判定在 `:80`（R-5.2）**完全不使用 `last_synced_at`**，語意收斂不影響它 |
| **(c)** R-5.13 與既有規則的相容性（第二種 vs 第三種對 `last_synced_at`） | **條件式通過 → 判 Major（M-7.2）** | **在「單一步驟失敗」的前提下兩者一致**：第二種（`write_field` 回 `Failed`）依 `U-3/business-rules.md:83`（R-4.1）「`write_field` 失敗回 `Failed`，**不影響 Status 寫入**」與本檔 `:48-49` 的「**不連坐**，續走」，該輪 `write_body` **是成功的** ⇒ 受管區塊確實寫入 ⇒ 依 R-5.13 推進 `last_synced_at` **正確**，兩支不矛盾。**但四種列舉沒有涵蓋同輪兩步皆失敗**（`write_field` 回 `Failed` ＋ `write_body` 回 `Failed`；兩者同為 GitHub API 呼叫，限流／中斷時同時失敗完全可達）：第二種要求寫 `last_synced_at`／`managed_block_hash`，第三種要求兩者維持原值，**字面互斥**。R-5.12 的統括句「**`SyncState` 逐欄記錄「實際寫成功」的部分**」＋R-5.13 可推導出正確處置（皆維持原值），故不判 Critical；但**這個互斥是本輪由三分改四分新產生的**——前一版第二、三種對 `last_synced_at` 的處置相同（皆寫），不存在互斥 |
| **(d)** R-6.8 寫 `last_synced_at` 是否與 R-5.13 相容 | **未通過 → C-7.1** | **R-6.8 本身相容，且不會誤殺告示**：`U-7/business-rules.md:82` 逐字「`last_synced_at` 取本輪時刻——依 U-6 的 R-5.13 它標記「受管區塊上一次成功寫入的時刻」，而本修復正是在確認該區塊已存在於看板上」；且該路徑只在「三欄與 `Decision` 不符」時觸發，而 `write_body` 失敗那一輪三欄**已相符** ⇒ R-6.5 不觸發 ⇒ 不會把待送告示的時刻推掉。**問題出在同一單元的另一條寫者**：`U-7/business-rules.md:77`（R-6.1）逐字「每次成功補平一個 intent 的看板值後，呼叫 `write_sync_state` 更新該 intent 的 `last_status`／`last_field_value`／`last_reason_code`／**`last_synced_at`**」，而 `:78`（R-6.2）逐字只擋一欄——「**補平路徑（R-6.1）不得動 `managed_block_hash`**……補平只寫 Status 欄、**不重寫受管區塊**」。**補平不寫受管區塊卻推進 `last_synced_at`，與 R-5.13 直接矛盾**；後果見 C-7.1 |
| **(e)** 有無因這項修正而新引入的 Critical | **有，2 項**（另 2 Major、1 Minor） | C-7.1（R-5.13 與 R-6.1 矛盾）、C-7.2（修法未傳播，四處仍載修正前行為）。詳見第 3 節 |

### 2. 逐單元 verdict 表

| 單元 | Verdict | 理由 |
| --- | --- | --- |
| U-1 map-parse-action | **READY** | 本輪未變更、無連帶影響（修法只動 `SyncState` 的回寫語意，不觸及 `parse`／`map` 的契約） |
| U-2 managed-block | **READY** | 本輪未變更、無連帶影響（`render`／`content_hash`／`Context` 契約未被修法觸及） |
| U-3 board-client | **NOT-READY** | **C-7.2 的兩個落點**：`business-rules.md:104`、`domain-entities.md:50` 逐字仍為「**其餘欄位照常回寫**」 |
| U-4 binding-store | **READY**（1 Minor） | `domain-entities.md:39` 的「兩個寫者」已補上、與 R-6.8 一致，傳播到位。Minor **m-7.1**：`:19` 的 `last_synced_at` 定義仍是「上一次成功寫入的時刻」，未隨 R-5.13 收斂為「受管區塊」——U-4 是該欄位 schema 的擁有者 |
| U-5 notifier | **READY** | 本輪未變更、無連帶影響（R-5.12 四種失敗皆交 C-5 `notify`；值域落差已登錄為 open item A:M-7，非本輪） |
| U-6 forward-workflow | **NOT-READY** | **C-7.2 主落點**（本檔 `:53`、`:66`）＋ **M-7.1**（本檔 `:54` 回讀無錯誤出口）＋ **M-7.2**（R-5.12 第二／三種在同輪雙失敗時互斥） |
| U-7 reconcile-workflow | **NOT-READY** | **C-7.1**：R-6.1 在不寫受管區塊的情況下推進 `last_synced_at`，與本輪新增的 R-5.13 矛盾，且 R-6.2 的限制只涵蓋 `managed_block_hash` |
| U-8 reverse-workflow | **READY** | 本輪未變更、無連帶影響。它是 C-7.1／C-7.2 的**受害端**（雜湊比對與告示皆由 U-6／U-7 的記帳決定），不是其缺陷 |
| U-9 selftest-workflow | **READY** | 本輪未變更、無連帶影響 |
| U-11 readme-pointer | **READY** | 本輪未變更、無連帶影響 |

### 3. 新引入的 Critical

**有，2 項。兩項都不是設計判斷錯誤——修法本身選對了；兩項都是修法沒有走完它自己的傳播面。**

| # | 嚴重度 | 類別 | 檔案:行 | 發現 | 建議修法 |
| --- | --- | --- | --- | --- | --- |
| **C-7.1** | **Critical** | **新引入**（R-5.13 與既有 R-6.1 的明文矛盾；底層行為缺陷既存，本輪的新規則使其成為可機械判定的矛盾） | `U-6/business-rules.md:123`（R-5.13）、`:84`（R-5.6）、`:275`（R-6.2c）；`U-7/business-rules.md:77`（R-6.1）、`:78`（R-6.2） | **U-7 的補平路徑在不寫受管區塊的情況下推進 `last_synced_at`，使 [US:S-6 AC 5] 的告示可經由「反向 PR 被拒 ＋ 當日對帳補平」這條組合永久靜默——與 C-6.2 同型後果，換一個入口。** 逐字比對即可判定：R-5.13「**`last_synced_at` 的語意是「上一次**受管區塊**成功寫入的時刻」**」 vs R-6.1「更新該 intent 的 `last_status`／`last_field_value`／`last_reason_code`／**`last_synced_at`**」，而 R-6.2 逐字「補平只寫 Status 欄、**不重寫受管區塊**」且其限制**只列 `managed_block_hash` 一欄**。時序：①反向 PR 於 T0 被關閉未合併 ⇒ 該 intent 待送告示；②U-6 是事件觸發、U-7 是每日排程，而 PR 關閉本身不 push 到 `ut`、**不觸發 U-6**，故 U-7 先跑的機率高；③該 intent 若同時有看板漂移（人為改動看板正是 U-8 存在的理由），U-7 補平並依 R-6.1 把 `last_synced_at` 推進到本輪（> T0），同時把三欄補為與 `Decision` 相符；④次輪 U-6：三欄無漂移（R-5.2）、R-5.6 第二來源因 T0 < `last_synced_at` 亦不成立 ⇒ **不進寫入鏈 ⇒ 告示永久不出現且無紅燈**。**U-7 結構上無法遞送告示**（其元件集合不含 C-6，`U-7/business-rules.md:78` 逐字），它只是推進了守門那個告示的時刻 | R-6.2 的限制由一欄擴為兩欄：「補平路徑（R-6.1）不得動 `managed_block_hash` **與 `last_synced_at`**」——理由與 `managed_block_hash` 完全相同（補平不重寫受管區塊）。R-6.8 的修復路徑仍為明文例外（該路徑已確認區塊存在於看板上）。同步更新 `U-7/business-logic-model.md` 補平節點的欄位清單與 `U-4/domain-entities.md:19` 的欄位定義 |
| **C-7.2** | **Critical** | **新引入**（本次編輯使原本正確的四處敘述變成錯的） | 本檔 `:53`、`:66`；`U-3/business-rules.md:104`；`U-3/domain-entities.md:50`（對照正本 `U-6/business-rules.md:122`） | **C-6.2 的修法只落在 R-5.12 本文，四個仍在流通的表達面逐字保留修正前的行為——其中兩處是 iteration 6 建議欄逐字點名的落點。** 四處逐字：①序列圖 `:53`「`Failed ──► U-5 notify；managed_block_hash 維持原值（R-5.12）`」——**只列一欄**；②文字 fallback `:66`「自訂欄位或受管區塊寫失敗時各自通報且**不連坐**，**對應的那一欄**維持原值」——單數，對 `write_body` 失敗即只保留 `managed_block_hash`；③`U-3/business-rules.md:104`「`write_body` 失敗時 `managed_block_hash` 維持原值、**其餘欄位照常回寫**」；④`U-3/domain-entities.md:50`「呼叫端依 U-6 的 R-5.12 **維持 `managed_block_hash` 原值、其餘欄位照常回寫**」。**「其餘欄位照常回寫」＝ `last_synced_at` 前進 ＝ C-6.2 的缺陷逐字重現**；依這四處任一實作，[US:S-6 AC 5] 的告示即永久靜默。對照 iteration 6 的建議欄逐字：「並在 `business-logic-model.md:52-53` 的 `write_body` 失敗出口補上「`last_synced_at` 亦維持原值」」——**未執行**。**本檔自身已立過這條 bar**：`:71` 的修訂註記逐字「**本單元就是寫入端，序列圖是實作者取用時序的第一份文件**」，iteration 3 即以此把同型的圖／規則不一致判為 Critical | 四處各補一句與 `:122` 第三點逐字一致的表述：序列圖 `:53` 改為「`managed_block_hash` **與 `last_synced_at`** 維持原值（R-5.12）」；fallback `:66` 把「對應的那一欄」改為分述兩支；`U-3` 兩處把「其餘欄位照常回寫」改為「`last_status`／`last_field_value`／`last_reason_code` 照常回寫，`managed_block_hash` 與 `last_synced_at` 維持原值」。**四處是同一個事實的四種表達形式**（`project.md` 的 `units-generation:260822-ug-L1`：按事實掃、不按改過的字串掃） |

**新引入的 Major／Minor（不影響本輪判定門檻，一併登錄）**

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| **M-7.1** | Major | 本檔 `:54`、`:66` | R-5.12 **第四種**（回讀拋 `ExternalError` ⇒ 完全不回寫）在序列圖與 fallback 皆不存在：`:54` 逐字「`├─► U-3 read_item ──► 取回 managed_block_hash（R-5.4）`」**沒有錯誤出口**，fallback 亦只寫「**再回讀一次**取得該區塊的雜湊」。iteration 6 的建議欄逐字點名「序列圖 `:54` 的錯誤出口」，未執行。判 Major 而非 Critical 的理由：圖上無 handler 時例外自然向上傳播 ⇒ `write_sync_state` 不執行 ⇒ 行為**恰好**與「完全不回寫」相同；但「該 intent 中止」與「整輪中止」在圖上仍不可分辨，且 `:122` 要求的「交 C-5 `notify`」在圖上無落點 |
| **M-7.2** | Major | `U-6/business-rules.md:122` | R-5.12 的四種以「單一步驟失敗」為隱含前提，**未定義同輪 `write_field` 與 `write_body` 皆失敗**：第二種要求寫 `last_synced_at`／`managed_block_hash`，第三種要求兩者維持原值，字面互斥。統括句「逐欄記錄實際寫成功的部分」＋R-5.13 可推導出正確解（皆維持原值），故非 Critical；但**這個互斥是本輪由三分改四分新產生的**，且落在 C-6.2 的同一條 AC 上（`project.md` 的 `functional-design:c34`：一條 AC 的違反面有幾個入口，閘門要位在全部分支的共同上游） |
| **m-7.1** | Minor | `U-4/domain-entities.md:19` | 該欄位 schema 的擁有者仍逐字定義 `last_synced_at` 為「**上一次成功寫入的時刻**」，未隨 R-5.13 收斂為「上一次**受管區塊**成功寫入的時刻」。同檔 `:39` 的「兩個寫者」已同步，可見本輪確實編輯過此檔而漏了這一列 |

### 4. Summary

**修法的判斷全部正確，兩個 Critical 在 `business-rules.md` 的規則本文上確實關閉**：R-5.12 拆成四種之後，「回讀失敗」那一支回到全有全無，使 R-6.5／R-6.8 的修復路徑重新可達（C-6.1 關閉，且與 U-6 次輪的 `Aborted` 不相爭）；`write_body` 失敗那一支不推進 `last_synced_at`，使 R-6.2c 的告示條件次輪仍成立（C-6.2 關閉）。R-5.13 是這兩者的共同支點，它與 R-5.6／R-6.2c／R-6.8 三處相容，且不影響 R-5.2 的三欄漂移判定。

**但修法只走到規則本文。** 兩個新 Critical 都不是設計錯誤：C-7.2 是**同一個事實的四個表達面沒有跟上**（其中兩處是 iteration 6 建議欄逐字寫出的落點），C-7.1 是**新規則沒有回頭檢查既有規則的相容性**（R-5.13 釘死了 `last_synced_at` 的語意，而 U-7 的 R-6.1 早就在不寫受管區塊的情況下寫它）。**`last_synced_at` 現在有三個寫者**（U-6 的 R-5.4、U-7 的 R-6.1、U-7 的 R-6.8），本輪只對其中兩個做了語意對齊——送審前自檢第 2 項（每個共享狀態欄位的誰寫／誰讀／誰清，範圍是整個 stage 產出）本應攔下這一項。

**本輪 5 項發現的分類：新引入 5／既存漏審 0／新設計問題 0。** 使用者停止迴圈的判準（`project.md` 的 `functional-design:c18`）在本輪再次被滿足，**不建議再開修正迴圈**——五項的落點與修法都已逐字定位，處置成本低且不需要獨立視角，應直接登錄進 `open-items.md` 並帶進閘門。

**帶進閘門時的優先序建議**：**C-7.1 與 C-7.2 應在 Bolt 1 開工前處理**，不宜留給 code-generation 自行判讀——兩者都會讓實作者在**沒有紅燈**的情況下做出違反 [US:S-6 AC 5] 的行為，而該 AC 的失效是靜默的（告示不出現、沒有錯誤、沒有通報）。M-7.1／M-7.2／m-7.1 可留給 code-generation，但 M-7.2 的判讀依賴 R-5.12 的統括句，實作時應在程式碼註解明寫「四種列舉是單步失敗的前提，多步失敗依統括句逐欄處理」。
