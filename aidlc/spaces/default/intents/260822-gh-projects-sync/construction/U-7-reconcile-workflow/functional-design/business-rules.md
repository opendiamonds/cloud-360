# Business Rules — U-7 對帳 workflow 與編排器

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## R-1 群：清單成員身分（含 G-1 的修補）

每個被處理的 intent 依其 `reason_code` 或寫入結果**恰好**進入下表的一個桶，或不進任何桶。

| `reason_code` / 結果 | 進哪個清單 | 計入分母？ | 計入分子？ |
| --- | --- | --- | --- |
| `mapped`（成功寫入或已一致） | 無 | ✅ | 一致者否 |
| `suppressed` | `awaiting_human` | ❌ 排除 | — |
| `parked` | `parked` | ❌ 排除 | — |
| `unparseable` | `unparseable` | ✅ | ✅ |
| **`undecidable`** | **`undecidable`**（G-1 新增） | ✅ | ✅ |
| `whitelisted` | **無**（[US:S-3 AC 6] 明文） | ✅ | ✅ |
| `Aborted` | `aborted` | ✅ | ✅ |
| issue 已關閉而 Status ≠ `Done` | `issue_status_mismatch` | 不影響 | 不影響 |

**R-1.1**：`unparseable` 與 `undecidable` **不得合併成一個清單**。兩者的處置不同——前者修 record、後者修對照表。理由見 `domain-entities.md`。

**R-1.2**：`issue_status_mismatch` 是**正交維度**，不參與一致率計算。它回答的是 [US:S-9 AC 5] 的「issue 開關與 Status 相稱嗎」，與「看板值和 record 一致嗎」是兩個問題。

## R-2 群：一致率（維持上游）

| # | 規則 | 來源 |
| --- | --- | --- |
| R-2.1 | 分母 = 已綁定的 intent − `awaiting_human` − `parked` | [req:NFR-O2]、ADR-A5 |
| R-2.2 | 分子 = 分母內看板與 record 不一致者，**含 `aborted`** | 同上 |
| R-2.3 | **不得擴為三類排除** | ADR-A5 的 Alternatives Rejected |

**R-2.3 是明文禁止的**，不是本站的保守。ADR-A5 逐字：「`aborted` 計入分母且計入分子，但另列獨立清單」，理由是「那些 item 的看板值是機制自己判定無法擔保的，**本來就是真的不一致**」。

> **分子擴張的後果先前未被揭露（reviewer iteration 1 Major，2026-08-29T15:26:25Z）。** ADR-A5 逐字只討論 `aborted`；把 `unparseable` 與 `whitelisted` 也併入分子是本站的延伸。**它的直接後果是 NFR-O2 的「目標為 0」在白名單記錄（`260802-default`）存在期間結構性不可達**——那筆記錄永遠是 `whitelisted`，於是分子恆 ≥ 1。
>
> **本站維持這個延伸**（把「機制放棄擔保」的每一類都算進不一致，比只算 `aborted` 誠實），**但必須同時揭露它讓一個已核可的目標值變成不可達**。處置二選一，本站不單方面裁定：(a) NFR-O2 的目標改為「分子中不含 `mismatch` 類」而非絕對 0；(b) `whitelisted` 退出分子。**已由 ADR-0015 §9 承載**（先前僅在本檔留一則指派註記，而 `requirements.md` 的 NFR-O2 列零痕跡——與同專案處理 NFR-S1 時採用的 ADR-0014 先例相比強度不足，故改走 ADR）。**確認人為 Bolt 2 的 gate。**

**`undecidable` 的新增依同一邏輯計入分母與分子**——它也是「機制放棄擔保」，不是「機制刻意不動」。

> **本檔的規則群編號不依出現順序（iteration 3 F10 Minor）**：目前的檔內順序是 R-1 → R-2 → **R-8** → R-3 → R-4 → **R-6** → R-5，而 R-7 未使用。成因是兩次補號都選擇**避開既有編號空間**而非重排全檔——R-8 由 R-4 改號（撞號，iteration 2），R-6 為本輪新增。**不重排的理由**：編號已被 `business-logic-model.md`／`domain-entities.md` 與 U-6 的產出交叉引用，重排的傳播風險高於順序不整齊的閱讀成本（`project.md` 的 `units-generation:260822-ug-L1` 正是這類傳播失敗的教訓）。記在此處以免下一個讀者以為漏了一群。

## R-8 群：`read_issue_state` 的承接（送審前自檢第 2 項；編號由 R-4 改為 R-8，因與既有 R-4 群撞號——reviewer iteration 2 Major，2026-08-29T16:20:29Z。原文其餘不變）（2026-08-29T15:28:15Z）

> **`read_issue_state(binding) -> "open" | "closed"`（C-3）先前沒有任何呼叫者。** 全 intent 的 functional-design 產出中只有擁有者 U-3 提到它。[ad:component-methods.md] 逐字把它的用途記為「[US:S-9 AC 5] 的 issue 開關偵測」，而 S-9 的報告由**本單元**產出——**這與 `resolve_if_open` 是同一個形狀的孤兒契約，且它直接支撐一條 AC。**

| # | 規則 |
| --- | --- |
| R-8.1 | 逐 intent 對帳時，對每個已綁定 intent 呼叫一次 `read_issue_state(binding)` |
| R-8.2 | 回 `"closed"` 者列入報告的 issue 關閉清單，供 [US:S-9 AC 5] 的呈現使用 |
| R-8.3 | **issue 已關閉不影響一致率的分母與分子**——它是看板外的事實，與「看板是否與 record 一致」正交。不得順手把它併進任一類 |

**R-8.3 是刻意寫下的**：把「issue 關了」算成不一致，會讓一個與同步正確性無關的人為動作污染 NFR-O2 的指標。

## R-3 群：處理量上限

| # | 規則 |
| --- | --- |
| R-3.1 | 上限以 workflow input `reconcile_batch_size` 宣告（[US:S-7 AC 3]） |
| R-3.2 | 改該值後**下一輪**處理量隨之改變——這是該 AC 的可驗證點 |
| R-3.3 | **上限的實際值待 PRE-1 第 2 項實測 C-T5 後定**，本站不臆測一個數字 |

**R-3.4（本站新增）**：超出上限而未處理的 intent **必須可被辨識**——否則「今天沒處理到」與「今天處理了但一致」在報告上長得一樣。**指派（reviewer iteration 1 Major，2026-08-29T15:26:25Z）**：先前寫「本站不裁定具體形式」而沒有像 G-1 那樣的乾淨接手點——`bolt-plan.md` 的 Bolt 2 DoD **完全不知道這個缺口存在**，等同無聲落空。**明確指派（措辭已更正，2026-08-29T16:20:29Z）**：先前寫「`bolt-plan.md` 的 Bolt 2 DoD **增列一條**」，讀起來像已完成的編輯——**實際上沒有，該檔逐字重讀後無此條目**（reviewer iteration 2 Major）。`bolt-plan.md` 是已核可上游，**標出不逕改**。
本項已由 **ADR-0015 §3** 承載（該 ADR 是這批上游修訂的正式載體，先例為 ADR-0014），**確認人為 Bolt 2 的 gate**。形式仍待 PRE-1 第 2 項實測 C-T5 之後決定，但**接手點現在有名字了**。

處置：報告加一個 `deferred: [intent_id]` 欄位，或另記本輪的處理起訖位置。**本站不裁定具體形式**〔**先前此處寫「在 `latency_samples` 之外另記」，已於 2026-08-30T00:57:28Z 移除該指涉（reviewer iteration 3 F9）**——那句話把 `latency_samples` 講得像是本單元正在填的欄位，與 `domain-entities.md` 的判定（本單元**填不出**該欄位，量測的是事件觸發路徑的延遲；擁有權移轉由 ADR-0015 §7 承載）不一致〕（它取決於 R-3.3 的實測值決定批次是否真的會被觸發），但**記明：若上限真的會被觸發而報告無法區分「未處理」與「已處理且一致」，一致率就會失真**——分母把未處理的也算進去了。

> 這一項是 R-2.1 的分母定義與 R-3.1 的批次上限之間的**交界**，兩者各自都對，合起來才顯出問題。上游沒有寫，因為兩條規則來自不同的 AC。

## R-6 群：補平後回寫 `SyncState`（Q5=A 定案，2026-08-30T00:57:28Z）

**背景**：`components.md` 原先給 reconcile 的元件鏈是 `C-7 →（內部）C-2／C-1／C-3／C-5`——**沒有 C-4**，所以本單元補平看板後無法持久化任何欄位。後果不在本單元身上，而在 U-6：它的 `write_status` 以 `SyncState` 三欄作為 `expected`（「機制上次寫進看板的值」），本單元一補平就讓那三欄過期，U-6 下一輪必然回 `Aborted` 並開一則**假通報**——**補平愈成功、假通報愈多**。

functional-design 的 iteration 2 曾試圖從 U-6 那一側迴避（`expected` 改取當下 `read_item`），但那讓回讀比對恆真、`Aborted` 不可達，[req:FR-C1]／[req:FR-C3]／[US:S-3 AC 1–2] 全部不可滿足（iteration 3 C-1 Critical）。**人工裁決 Q5=A 選擇從源頭解決**：`components.md` 的 reconcile 元件鏈補上 C-4，由 **ADR-0015 §13** 承載。

| # | 規則 |
| --- | --- |
| R-6.1 | 每次成功補平一個 intent 的看板值後，呼叫 `write_sync_state` 更新該 intent 的 `last_status`／`last_field_value`／`last_reason_code`／`last_synced_at`，語意與 U-6 的 R-5.4 相同：**記錄「機制上次寫進看板的值」** |
| R-6.2 | **補平路徑（R-6.1）不得動 `managed_block_hash`**——reconcile 的元件集合補了 C-4 之後**仍不含 C-6**，補平只寫 Status 欄、不重寫受管區塊，該欄位維持原值。**本條不適用於 R-6.5 的修復路徑**，見 R-6.8 |
| R-6.3 | **未補平的 intent 不回寫**——**但 R-6.5／R-6.8 的修復路徑除外**。適用範圍限於「跳過」與「補平失敗」兩種；「判定一致」那一種由 R-6.5 決定要不要回寫（`SyncState` 與 `Decision` 相符則不寫，不符則修復） |
| R-6.4 | 回寫走 `commit_and_push`，與 U-4 的 R-3 群同路徑。推送失敗的處置沿用 R-4 群：**單一 intent 失敗不中止整輪**，計入報告後續跑 |
| **R-6.5** | **判定一致時，若 `SyncState` 三欄與本輪 `Decision` 不符，仍回寫三欄**（修復 U-6 遺失的回寫）。這是「看板 == record 而 `SyncState` ≠ 兩者」這個組合的唯一修復點 |
| **R-6.8** | **R-6.5 的修復同時回寫 `managed_block_hash` 與 `last_synced_at`**（iteration 5 點名兩個缺欄，2026-08-30T03:35:44Z 補齊第二個）。雜湊取自該次 `read_item` 回傳 `ItemState` 的 `managed_block_hash` 欄位（與 U-6 的 R-5.4 同一條取值路徑，故 ADR-0015 §10 的等價不變式成立）；`last_synced_at` 取本輪時刻——依 U-6 的 R-5.13 它標記「受管區塊上一次成功寫入的時刻」，而本修復正是在確認該區塊已存在於看板上。**這是 R-6.2 的唯一例外**——本單元仍不重寫受管區塊，只是把看板上**已經存在**的那個區塊的雜湊與時刻記進狀態檔 |
| **R-6.6** | 回寫與補平走**同一個** `commit_and_push`（每個 intent 至多一次推送），不因 R-6.1 與 R-6.5 是兩條規則就推兩次 |
| **R-6.7** | 補平時 `write_status` 的 **`expected` 取自本輪剛做的 `read_item` 回傳的 `ItemState`**，不取自 `SyncState`。這與 U-6 的 R-5.7 **刻意相反**，理由見下 |

> **R-6.8 是 iteration 5 Group A C-1 的修正（2026-08-30T02:47:00Z（依檔案 mtime 重建；原填 09:55:00Z 為未經 `date -u` 的編造值，已更正））。** R-6.5 先前只補**三欄**，而 U-6 的失敗場景 ②③（看板寫成功但回寫失敗）**同時**讓 `managed_block_hash` 落後——R-5.4 的五欄回寫是一個整體，失敗時五欄一起沒寫進去。R-6.2 又明文禁止本單元動那一欄，於是它**永久錯誤**：U-8 的 R-1.1 每天拿舊雜湊比新區塊 ⇒ 判定「有人改過看板」⇒ **在沒有任何人為變更的情況下，每天為該 intent 開一則反向 PR**。那正是 [ad:decisions.md] ADR-A6 點名的最危險失效模式，被本輪修法漏掉的那一欄重新打開。
>
> **修復雜湊不牴觸 R-6.2 的本意**：R-6.2 防的是「本單元重寫了受管區塊卻沒更新雜湊」（或反之）。R-6.8 兩者都不做——它不碰區塊，只把看板上**已經存在**（由 U-6 寫入）的那個區塊的雜湊記進狀態檔，取值路徑與 U-6 的 R-5.4 完全相同。

> **R-6.5 是 iteration 4 Group A C-1 的修復落點（2026-08-29 起連續兩輪，見下）。** U-6 的 R-5.9 原宣稱「`SyncState` 過期的唯一來源是 U-7 補平」並據此取消補救，那個「唯一」不成立——U-6 自己的 `commit_and_push` 回 `Rejected`、或 R-5.4 的回讀拋 `ExternalError`，都會留下「看板已寫成功但沒記錄」的狀態。後果是**永久卡死**：U-6 下一輪判 `Aborted` 而中止寫入鏈，`SyncState` 永遠追不上，每輪開一則假通報；而本單元依 R-6.3「未補平不回寫」也不會動它（看板此刻**等於** record，判定一致）。
>
> **為什麼修復點在本單元而不在 U-6**：U-6 在事件路徑上只有兩個座標（看板、`SyncState`），「我上輪寫的但沒記錄」與「別人改的」在它眼中**完全相同**——把兩者合併處理正是 iteration 3 C-1（守門恆真）的形狀，不可重蹈。本單元有第三個座標 **record**：當「看板 == record 而 `SyncState` ≠ 兩者」時，這個組合只可能來自遺失的回寫，因為人為改動不會恰好把看板改成 record 的值。**R-6.5 因此不削弱 U-6 的守門**——它修的是機制自己的記帳，不是替人為改動放行。

> **R-6.7 與 U-6 的 R-5.7 取法相反，這不是矛盾（iteration 4 Group A C-5，2026-08-30T01:31:09Z）**。兩者的守門目的不同：
>
> - **U-6（事件驅動）**要偵測的是「**我上次寫進去之後**有沒有別人動過」——基準必須是它自己上次寫的值，即 `SyncState`。若改取當下 `read_item`，比對恆真、守門作廢（那正是 iteration 3 的 C-1）。
> - **本單元（對帳）**要偵測的是「**我讀到當下狀態到我寫入之間**有沒有人插隊」——這是單輪內的樂觀鎖，基準本來就該是剛讀到的值。本單元的 `Aborted` 因此仍然可達：並行的 U-6 事件寫入（[req:NFR-P3] 明文允許兩路徑並行）會觸發它。
>
> **兩者不是同一條規則的兩種取法，是兩個不同的問題。** 先前本單元對 `expected` 的來源**全單元未定義**，而圖上唯一能推得的來源正是 U-6 那個被判死的恆真形狀——不寫清楚就會被下一個實作者讀成「兩邊該一致」而改錯任一邊。

**代價（誠實記載）**：本單元每日多一次 commit+push。`deploy.yml` 只在 PR merge 進 `ut` 或手動 `workflow_dispatch` 觸發，故**不觸發部署**；會被觸發的是 `ci.yml`，而 U-10a 已為 `sync-state.json` 設計 `paths-ignore`，沿用即可。

### R-7 群：排程觸發的分支落點（Q6=A 定案，2026-08-30T01:31:09Z）

> **先前此處標為「R-6 群不可實作、缺推送落點」，那個宣稱是錯的並已撤回（reviewer iteration 4 Group A M-1）。** `commit_and_push` 的「只推觸發分支」是**呼叫方式的描述、不是方法的內建限制**——`branch` 本來就是它的參數，而這正是 U-8 推自建 `aidlc-sync/reverse/*` 分支合法的前提（U-4 `business-rules.md` 的 R-3.1 註記已如此定案）。推送落點從來就有。

**真正的問題是讀取端**：GitHub 的 `schedule` **只在預設分支觸發**，而本 repo 的預設分支經 `git symbolic-ref refs/remotes/origin/HEAD` 實測為 **`main`**。若不處理，本單元會讀到 `main` 上的 record——而 `main` 落後於整合主幹 `ut`（`org.md`：`ut` 是整合主幹、`main` 是對外釋出線）⇒ **對帳拿過期的 record 去比看板**，一致率、補平判定、三份清單全部失真。

| # | 規則 |
| --- | --- |
| R-7.1 | `actions/checkout` **必須明訂 `ref: ut`**。不得依賴預設行為——預設會 checkout 觸發 ref（即 `main`），且**不會有任何錯誤**，失真是靜默的 |
| R-7.2 | 推送落點為**從 `ut` 分叉的自建分支**，比照 U-8 的形狀；不推 `main`、不推 `ut`（U-4 的 R-3.1） |
| R-7.3 | **本輪讀到的 `ut` HEAD SHA 必須寫進對帳報告**。這讓「報告依據的是哪一版 record」可被事後查核，也讓 R-7.1 被繞過時看得出來 |
| R-7.4 | 同一組規則**適用於 U-8**（反向同步亦為 `schedule` 觸發，同一個硬限制）。落點在該單元 |

**使用者裁決原話**：「不應該在main上跑」（見 `functional-design-questions.md` 的 Q6）。**workflow 定義仍由預設分支讀取**——這是 GitHub 的硬限制，無法繞過；能控制的是它讀寫什麼，而 R-7.1〜R-7.3 把那部分全部釘在 `ut` 上。

## R-4 群：單一 intent 失敗不中止整輪

[ad:component-methods.md] §C-7 逐字：「單一 intent 失敗不中止整輪；計入報告後續跑」。

**R-4.1**：與 U-6 的 R-2.5（`reverse_pending` 查詢失敗 → **整輪中止**）**刻意不同**。分界同樣是**影響範圍**：`reverse_pending` 是全輪共用的前提，缺了它每個 intent 的判定都不可信；單一 intent 的 API 失敗只影響那一個。

**R-4.2**：本單元同樣需要 `reverse_pending`（`awaiting_human` 清單即由它產生），因此**同樣適用 U-6 的 fail-closed**——查不到就整輪中止，不得視為空集合。

## R-5：排程不與既有 cron 碰撞

`stories.md` 的全域 DoD 明列：對帳排程不得與 `daily-digest`（`0 23 * * 1-5`）、`agentics-maintenance`（`37 0 * * *`）、`release-watch`（`39 16 * * 1`）碰撞。

**這是建置期檢查，非執行期行為**——同一份 DoD 已如此分類。本單元的 cron 值須避開上述三個時間點。

## 與上游的對應

`reconcile` 的契約與 `ReconcileReport` 引自 [ad:component-methods.md] §C-7；兩類排除與 `aborted` 的處置引自 [ad:decisions.md] ADR-A5；[req:FR-D1]／[FR-D3]／[FR-D4]／[NFR-O1]／[NFR-O2]／[FR-J5] 引自 `requirements.md`；[US:S-3 AC 6]／[US:S-7]／[US:S-9] 與全域 DoD 的排程項引自 `stories.md`；G-1 的來源與指派引自 [ug:unit-of-work.md]、[ug:unit-of-work-story-map.md]；`ReasonCode` 語意引自 U-1 的 `domain-entities.md`；`reverse_pending` 的 fail-closed 引自 U-6 的 `business-rules.md` R-2 群；S-B 的生命週期與並行性引自 [ad:services.md]；清單定義見本單元的 `domain-entities.md`，資料流見 `business-logic-model.md`。
