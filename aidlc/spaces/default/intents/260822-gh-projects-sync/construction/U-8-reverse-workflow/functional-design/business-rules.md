# Business Rules — U-8 反向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## R-1 群：何時開 PR

| # | 規則 | 來源 |
| --- | --- | --- |
| R-1.1 | 讀看板現況 → 以 U-2 的 `content_hash` 與 `sync-state.json` 記錄的雜湊比對 | [ad:services.md] S-C |
| R-1.2 | **雜湊未變 → 不產生 PR**（[ug:unit-of-work.md] U-8 完成判準第二條） | 同上 |
| R-1.3 | 雜湊已變 → 寫 `pending_reverse` 並開 PR | E-1 |
| R-1.4 | **每個有變更的 intent 各開一個 PR**（E-2） | 本站裁定 |
| R-1.5 | PR 的 base 為 `ut`；**不得直接推 `ut`** | [req:FR-G1] |

**R-1.2 是防迴圈第一道防線在反向側的體現**：機制自己寫的區塊，雜湊與記錄相同，因此不會把自己的寫入誤判為人為變更。

## R-6 群：`pending_reverse` 的生命週期（reviewer iteration 1／2 之後的定案）

**iteration 1 抓到的缺口是真的，但 iteration 1 的修法是錯的。** 兩輪合起來的結論如下。

### R-6.0 — 這個欄位在 `ut` 上非 `null`，**等價於「有一則反向 PR 合併過」**

推導鏈（每一步都可回頭核對）：

1. 寫入不落在 `ut`：R-4c 明列本單元對 `commit_and_push` 的用法是推**新建的反向分支**，而非觸發分支。
2. 這與 E-1 一致——`business-logic-model.md` 寫「PR 的 diff **結構上只含該檔**」。若先寫進 `ut` 再開分支，該 PR 對 `ut` 的 diff 會是空的，沒有東西可審。**寫入本身就是 PR 的 payload。**
3. 所以該 commit 進入 `ut` 的唯一路徑是**這則 PR 被合併**。
4. PR 開不成時，[R-6.3] 要求連分支帶 commit 一起刪；**即使刪除也失敗**，孤兒分支仍是未合併狀態，`ut` 從頭到尾沒被改過。

### R-6.1 — 防重複開 PR 用**即時查詢**，不看儲存欄位

開 PR 前以 label `aidlc-sync-reverse` 查該 intent 是否已有**開啟中**的反向 PR，有則不開第二個。與 U-6 的 R-2.1 同一份事實來源。**儲存欄位是 PR 的內容，不是 PR 是否存在的證據**——把兩者混為一談正是 iteration 1 那個 Critical 的成因。

### R-6.2 — **本機制不清除這個欄位**，也不需要清除

| 問 | 答 |
| --- | --- |
| 有任何單元讀它做控制流嗎？ | **沒有**。R-6.1 用即時查詢；R-1.1 比的是 `managed_block_hash`；U-6 用的是每輪即時算出的 `Config.reverse_pending`（該單元 R-2 群），與本欄位無關 |
| 那它是什麼？ | **最近一次反向觀察的紀錄**，隨下一次反向事件被覆寫（R-1.3） |
| 不清除會壞掉嗎？ | 不會。沒有讀者就沒有陳舊問題 |

> **iteration 1 寫的 R-6.2／R-6.3（「有已關閉/已合併 → 寫回 `null`」「從未有過 PR → 不清除並紅燈」）已整組移除**，兩條都不成立：
>
> - 依 R-6.0，「`pending_reverse` 非 `null` 且**從未**有過任何 PR」的兩個子句**自相矛盾**，該條永遠不會為真。
> - 「已關閉未合併」的 PR，其 commit 從未進入 `ut`，不可能是非 `null` 的成因；若此刻恰好非 `null`，那是**另一則更早、已合併**的 PR 留下的，與這則無關。
> - **且清除動作的成本不合理**：R-1.5 明訂本單元**不得直接推 `ut`**，所以「把欄位寫回 `null`」得為每一次反向事件再開一則 PR，讓人審一個沒有任何讀者的欄位歸零。（此處先前寫「無盡遞迴」，已依 reviewer iteration 3 的 Minor 更正——那是誇大：清除 PR 本身不會再製造待清狀態。本條的結論不靠這個論證，靠的是上表「沒有讀者」那一行。）

### R-6.3 — E-1 的原子性失敗是 **run 內**的條件，當場偵測、當場紅燈

`pending_reverse` 已 commit 但 PR 開不成時：**刪除該分支**；刪除也失敗則保留孤兒分支。**兩種情形都在同一次執行內記入報告並紅燈**，附 intent id 與分支名。

**不留給下一輪、也不留給 U-7**——依 R-6.0，這個狀態在 `ut` 上根本不可觀察，任何跨輪的欄位檢查都打不到它。這也是 U-9 撤回 A-5 對 U-7 指派的理由。

## R-2 群：PR 的內容邊界

| # | 規則 |
| --- | --- |
| R-2.1 | diff **不得含 `aidlc-state.md` 的任何一行**（[req:FR-G2]、C-N3） |
| R-2.2 | diff 只含該 intent 的 `<record>/sync-state.json` |
| R-2.3 | 分支名 `aidlc-sync/reverse/<intent_id>-<date>`，label `aidlc-sync-reverse` |

**R-2.1 在 E-1 之下是結構性成立的**，不靠紀律：本單元唯一寫的檔就是 `sync-state.json`。

**但仍須有斷言**——[US:S-6 AC 2] 逐字要求「檢視其 diff，不含 `aidlc-state.md` 的任何一行」。**結構上不可能發生的事，仍要有測試證明它沒發生**，否則未來有人擴大寫入範圍時沒有東西會失敗。落點為 U-9。

## R-3 群：逐 intent 的暫停（over-suppression 的處置）

| # | 規則 |
| --- | --- |
| R-3.1 | 一個 PR 對應一個 intent（E-2） |
| R-3.2 | U-6 讀 PR 的 diff 路徑算 `reverse_pending`，每則 PR 貢獻**一個** intent id |
| R-3.3 | PR 合併**或關閉**後，該 intent 恢復覆寫（[req:FR-G3] 逐字：「直到對應 PR 被合併**或關閉**」） |

**R-3.3 的「或關閉」是 [US:S-6] benefit clause 誠實邊界的來源**：`stories.md` 明記在**拒絕**路徑上，PR 被關閉（未合併）時也恢復覆寫，P2 的改動仍會被輾回去，只是慢了一輪。該故事的 benefit 因此寫成「**送到人面前決定**」而非「我的判斷會被保留」。**本站不改寫該邊界。**

## R-4：over-suppression 的風險狀態（誠實記載）

[ad:decisions.md] 的 CAP-11 補評估把 over-suppression 標為「**本路徑的真正風險**，未實測」。

**E-2 沒有消除「未實測」，但改變了失敗模式**：

| | 上游形狀（單一 PR 含全部 intent） | E-2（一 intent 一 PR） |
| --- | --- | --- |
| 判定方式 | 從 diff 路徑**推導**哪些 intent 在內 | **結構上就是**——PR 只含一個 |
| 失敗時的後果 | **全域誤暫停**——一個 PR 讓所有 intent 停寫 | 該 intent 未暫停（漏一個，不是多停全部） |
| 嚴重度 | 高 | 顯著降低 |

**仍需 Bolt 3 實測**：[US:S-6 AC 3] 的反例（X 在 PR 內、Y 不在，Y 照常寫）在 E-2 下應**平凡成立**，但「平凡成立」與「實際成立」是兩件事。

## R-4b：S-6 的七條 AC 分散在三個單元（[ug:unit-of-work-story-map.md]）

本單元**不擁有** S-6 的全部 AC。story-map 的對照如下：

| AC | 內容 | 落點 |
| --- | --- | --- |
| AC 1–4 | 開 PR、不動 `aidlc-state.md`、逐 intent 暫停、合併與拒絕兩條路徑 | **U-8（本單元）** |
| **AC 5** | PR 關閉未合併時，受管區塊須載有「該次人工改動未被採納」的記錄與時間戳 | **U-6**——見下方更正 |
| AC 6 | 受管區塊雜湊比對防線 | **U-2** |
| AC 7 | 反向 PR 不觸發高成本 workflow | **U-10b** |

> **AC 5 的歸屬已更正（reviewer iteration 1 Critical）。** [ug:unit-of-work-story-map.md] 把 S-6 的 AC 1–5 全歸本單元，但 AC 5 要求的是「**受管區塊**載有一則記錄」，而本單元的元件集合是 `C-3（讀）→ C-6（雜湊比對）→ C-4（寫檔）→ 開 PR`（[ad:components.md]）——**沒有任何一步寫回看板**。寫受管區塊的路徑只在正向同步（U-6）上。
>
> 先前本單元三份產出**完全沒有提到 AC 5**，而 story map 又說它歸本單元——這個組合會讓該條 AC 在兩邊都落空。實作已由 **U-6 的 R-6.2** 承接；story map 的歸屬更正**已由 ADR-0015 §4 承載**（送審前自檢遷移，2026-08-29T23:42:35Z；先前寫「指派 units-generation」，而該 stage 已定稿，指派無收件人——理由同 ADR-0015 的 Context 段）。**確認人維持 Bolt 1 的 gate。**
>
> **後果值得寫明**：沒有 AC 5，[US:S-6] 的 benefit clause「送到人面前決定」在**拒絕**路徑上是空的——人的改動被輾回去，而他從來不會知道。

**這意謂本單元完成不等於 S-6 完成。** 三者分屬 Bolt 1（U-2）與 Bolt 3（U-8、U-10b），而 U-8 與 U-10b 是真捆綁——**AC 6 的機制必須先在 Bolt 1 就位**，否則本單元的 R-1.1 雜湊比對沒有對象。

## R-4c：本單元呼叫的**六個**上游方法（[ad:component-methods.md] 的簽章）

| 方法 | 元件 | 本單元的用法 |
| --- | --- | --- |
| `read_item(binding, Config) -> ItemState` | C-3 | 取回看板現況；其 `managed_block_hash` 欄位即比對對象的一端 |
| `parse(issue_body) -> Block \| null` | **C-6** | `null` 代表該 item 不受管——**跳過，不視為人為變更** |
| `content_hash(Block) -> sha256` | **C-6** | 現況雜湊 |
| `write_sync_state(record_path, state)` | C-4 | 寫 `pending_reverse` |
| `commit_and_push(branch, paths, message) -> Pushed \| Rejected` | C-4 | 推反向分支；**`branch` 為 `aidlc-sync/reverse/...` 而非觸發分支** |
| **`notify(FailureIdentity, detail)`** | **C-5** | **外部失敗時開通報 issue**（[req:FR-E1]／[US:S-8 AC 1]）。落點見下方錯誤處理表的「通報」欄 |

> **`notify` 是 2026-08-30T00:57:28Z 補上的（reviewer iteration 3 Group A M-4）。** `components.md` 給 `aidlc-sync-reverse.yml` 的元件鏈原本是 `C-3(讀) → C-6(雜湊比對) → C-4(寫檔) → 開 PR`，**不含 C-5**；**ADR-0015 §5 已為此開出修訂**，但本單元三份產出當時對 `notify`／C-5／「通報」**零次**提及——上游 ADR 已經指出，單元卻沒有接住。
>
> **後果**：反向同步的外部失敗只會讓 workflow 紅燈而**不產生通報 issue**，[req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」保證在這條路徑上不成立。這與 U-6 在 iteration 1 被抓到的 `ExternalError` 漏「＋ 通報」是**同一個缺陷**，只是這次上游已先指出。契約端點三問在此缺的是「誰呼叫」。

> **兩處已更正（reviewer iteration 1 Major）**：標題原寫「四個」而表列五列；`parse` 與 `content_hash` 原標為 **C-2**，實際屬 **C-6 `managed-block`**（[ad:components.md] 把 C-6 列為呈現層，C-2 是 U-1 的 `record-reader`，有一個不相干的同名 `parse`）。本單元自己的序列圖引用這兩個方法時寫的是「U-2」——**同一份產出內互相矛盾**，屬憑印象引用而非開檔核對。

**最後一列是本單元對 C-4 契約的一個特殊用法**：U-4 的 R-3.1 規定 `commit_and_push`「**只推觸發分支**」，而本單元推的是新建的反向分支。

**這不是違反，是 U-4 的規則在正向路徑的表述**——其 R-3.1 的原意是「不得推 `ut`／`main`」（該單元的完成判準逐字如此）。**但字面上兩者衝突，必須寫明**：`commit_and_push` 的 `branch` 參數本來就是參數，U-4 的「只推觸發分支」描述的是**正向同步的呼叫方式**，不是該方法的內建限制。**已直接修正 U-4 的 R-3.1**（該檔是本站自己的產出、閘門尚未觸發，就地對齊比指派給未來的自己誠實）：實質是「不得推 `ut`／`main`」，「只推觸發分支」描述的是正向路徑的呼叫方式。`pending_reverse` 亦已併入 U-4 的 `domain-entities.md` 並註明**必須在 `schema_version` 1 就存在**（U-4 在 Bolt 1、U-8 在 Bolt 3）。

## R-5：高成本 workflow 的排除不由本單元實作

[US:S-6 AC 7]（反向 PR 不觸發高成本 workflow）歸 **U-10b**。本單元的責任只是**產生可被排除的標記**（R-2.3 的分支名前綴）。

**兩者是同批次約束**（`unit-of-work-dependency.md` 的真捆綁）：U-8 先上而 U-10b 未上線 ⇒ 每個反向 PR 都送進含 6 次 LLM agent 執行的完整 gauntlet。

## 與上游的對應

S-C 的生命週期與寫入邊界引自 [ad:services.md]；[req:FR-G1]／[FR-G2]／[FR-G3] 與 C-N3 引自 `requirements.md`；[US:S-6] 全部 AC 與其 benefit clause 的誠實邊界引自 `stories.md`；over-suppression 的風險記載引自 [ug:unit-of-work.md] 的 U-8 與 [ad:decisions.md] 的 CAP-11；`content_hash` 引自 U-2 的 `business-rules.md` R-2 群；`reverse_pending` 的讀取引自 U-6 的 `business-rules.md` R-2 群；`sync-state.json` 的 schema 與相容規則引自 U-4 的 `domain-entities.md`；同批次約束引自 `unit-of-work-dependency.md`；本單元的型別見 `domain-entities.md`，序列見 `business-logic-model.md`。
