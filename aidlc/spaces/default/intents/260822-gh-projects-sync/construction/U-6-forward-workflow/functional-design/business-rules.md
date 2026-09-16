# Business Rules — U-6 正向同步 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-6-forward-workflow · kind: service -->

## R-1 群：觸發與 concurrency

| # | 規則 | 來源 |
| --- | --- | --- |
| R-1.1 | concurrency group 為 `aidlc-sync-event-${{ github.repository }}-${{ github.event.pull_request.head.ref \|\| github.ref_name }}` | [ad:services.md] S-A（逐字） |
| R-1.2 | `cancel-in-progress: false`——**排隊不取消**（[req:NFR-P3]） | 同上 |
| R-1.3 | push 與**同分支** PR 事件必須落在**同一個** group | [ug:unit-of-work.md] U-6 完成判準第一條 |
| R-1.4 | 排程對帳（S-B）**自成一組**，與本單元可並行 | [req:NFR-P3] 明文 |

**R-1.1 的表達式為什麼是那個形狀**：`github.ref_name` 在 `pull_request` 事件下是 PR 的 merge ref 而非來源分支，兩種事件因此會落在不同 group——`github.event.pull_request.head.ref || github.ref_name` 讓兩者收斂到同一個分支名。R-1.3 靠的就是這個。

**已知殘留**（[ad:services.md] 逐字記載，本站不弱化）：GitHub 只保留一個 pending run，同分支高頻 push 時第三個以後到達會取消先前的 pending。**因選取為漂移驅動，被取消 run 的工作由下一次執行涵蓋——不造成遺漏、只造成延遲。**

## R-2 群：`reverse_pending` 的取得（承接缺口 F-4）

**每輪在逐 record 迴圈之前執行一次**：

| # | 規則 |
| --- | --- |
| R-2.1 | 以 label `aidlc-sync-reverse` 列出**開啟中**的 PR（一次查詢） |
| R-2.2 | 對每則，取其變更路徑，映射為 intent id 集合 |
| R-2.3 | 該集合即 `Config.reverse_pending`，傳入 U-1 的 `map()` |
| R-2.4 | 無開啟中的反向 PR → **空集合**（正常情形，非錯誤） |
| R-2.5 | **查詢失敗 → 整輪中止，`ExternalError`，紅燈 ＋ 通報**（D-2） |

**R-2.5 是 fail-closed，且不得改成 fail-open。** 完整理由見 `functional-design-questions.md` 的 D-2；要點是 `reverse_pending` 的用途就是「哪些 intent 不該被覆寫」，算不出來即等於不知道該不該覆寫，而 [req:FR-C1] 的精神是「拿不準時不寫」。

**R-2.6（不得偽裝）**：查詢失敗時**不得**把全部 intent 記為 `suppressed`。那會讓受管區塊寫下「因反向 PR 而暫停」而實際上沒有反向 PR——**紀錄會說謊**，違反本設計的核心價值。

**R-2.2 的逐 intent 性質**：路徑本來就是逐 intent 的，[US:S-6 AC 3] 的反例要求（X 在 PR 內、Y 不在，Y 照常寫）由此自然成立。

## R-3 群：registry 驅動的選取分流

[ad:services.md] S-A 逐字：「單次執行掃過 `intents.json` registry 內的**全部** intent，逐一分流」。

| # | 分流 | 動作 |
| --- | --- | --- |
| **R-3.0** | **任何 intent，分流之前先算 `Decision`**（U-1 composite action）。`reason_code` ∈ {`unparseable`, `whitelisted`} ⇒ **本輪對它不做任何看板動作**——不首建、不寫入、不渲染（[req:FR-J3] 逐字：「機制**不對其產生任何看板寫入**」）。僅回寫 `SyncState` 記錄本輪判定（該 intent 若無 `sync-state.json` 則連這一步也沒有——見下） |
| R-3.1 | 通過 R-3.0 且**無綁定編號**者 | 走首建路徑（U-3 的 `create_item`，[req:FR-A1]） |
| R-3.2 | 通過 R-3.0 且**已綁定**者 | 比對 `sync-map` 判定與 `sync-state.json`，**有漂移才寫** |

> **R-3.0 是 iteration 5 Group A C-2 的修正（2026-08-30T02:47:00Z（依檔案 mtime 重建；原填 09:55:00Z 為未經 `date -u` 的編造值，已更正））。** iteration 4 的 C-2 指出 `unparseable`／`whitelisted` 不得產生任何看板寫入（[req:FR-J3]、[US:S-3 AC 5]，點名的 `260802-default` 今日就在 registry 內且無綁定），我當時把排除寫進 **R-5.10 (b)**——**但那條規則位在寫入鏈裡，而寫入鏈在 R-3.2 之下**；R-3.1 的首建分岔發生在它之前，且 R-3.1 一字未動。於是 `260802-default` 仍會被 `create_item` 建出 item，FR-J3 依然不可滿足。**我只是把違規從寫入端挪到了首建端。**
>
> **正確的落點是分流之前**：`reason_code` 要靠 `map()` 才算得出來，所以 `Decision` 的計算必須上提到綁定判斷之前。這也讓 R-5.10 (b) 從「寫入鏈裡的例外」降為「不會走到寫入鏈」——兩者現在說的是同一件事，(b) 支保留作為深度防禦。
>
> **未綁定且 `unparseable` 的 intent 連 `SyncState` 都不寫**：`sync-state.json` 的建立本身屬首建路徑，而首建已被 R-3.0 擋下。這是刻意的——為一個機制拒絕處理的 record 建立狀態檔，等於在 record 目錄產生一個沒有對應 item 的孤兒檔。**該 intent 每輪重新判定，成本是一次純函式呼叫。**

**兩支並存、互不覆蓋**——不是「已綁定 AND 有漂移」的單一 AND 條件。[ad:services.md] 明記此為 reviewer iteration 2 的 Critical 修正：寫成 AND 會讓 [req:FR-A1]／[US:S-1 AC 1] 永不觸發。

**R-3.3**：**不得依事件 diff 推導要處理哪些 record**（[ad:component-methods.md] §C-2 的「intent 選取的邊界」）。fixture record 不註冊進 registry，因此兩條路徑都不會選中它。

## R-4 群：自我排除的兩道防線

[ad:services.md] S-A 逐字，**兩道都是整輪層級，不是逐 record 層級**：

| # | 防線 | 性質 |
| --- | --- | --- |
| R-4.1 | **結構性**：回寫 commit 的內容就是剛寫進看板的值 ⇒ 下一輪判定**無漂移** ⇒ 不產生任何寫入 | **不依賴任何判斷** |
| R-4.2 | **顯式**：HEAD commit 訊息含 `[aidlc-sync]` 時整輪 skip | 快速路徑 |

**已知代價**（[ad:services.md] 記為 reviewer iteration 3 Minor，本站不弱化）：整輪 skip 意謂該次 run 內**其他 intent 的漂移也一併不處理**，要等下一次事件或隔日對帳。

**R-4.3**：R-4.2 的適用前提是「同步身分產生的 push 會觸發 workflow」。[Q2=A] 於 application-design 選的是 **GitHub App**（非 `GITHUB_TOKEN`），故防線②**確實會被執行**——若當初選 `GITHUB_TOKEN`，平台本身即不觸發，該防線會變成恆真而由平台承接。

## R-9：本單元不擁有 U-10a 的 `paths-ignore`（編號由 R-5 改為 R-9——同檔兩個 H2 撞號，reviewer iteration 4 m-4；U-7 的同型撞號已在 iteration 2 以同樣方式處理）

回寫 commit 不觸發 `ci.yml` 這件事歸 **U-10a**。本單元的 R-4 管的是**同步自己不被自己觸發**，兩者是不同的迴圈。

## R-5 群：漂移比對與狀態回寫（reviewer iteration 1 Critical 的修正）

> **先前序列圖把「與 `sync-state.json` 比對」畫成一個原子步驟，但全單元沒有任何一條規則說它怎麼做。** 這不是文字瑕疵：R-4.1 這條核心不變式（「回寫的內容就是剛寫進看板的值 ⇒ 下一輪無漂移 ⇒ 不寫」）的成立與否**直接取決於**這個比對涵蓋哪些欄位。一個只比 `status` 的自然實作，會讓同一 Status 內的 stage 轉換靜默不寫、自訂欄位過期，而**不會有任何紅燈或通報**——直接牴觸 [req:FR-A3] 與 [US:S-5]。

| # | 規則 |
| --- | --- |
| R-5.1 | **本單元**（不是 U-1、不是 U-4）在逐 record 迴圈內，對每個已綁定 intent 呼叫一次 `read_sync_state(record_path)` 取得 `SyncState` |
| R-5.2 | **三欄逐一比對**：`Decision.status` ↔ `SyncState.last_status`、`Decision.field_value` ↔ `last_field_value`、`Decision.reason_code` ↔ `last_reason_code`。**任一不同即為「有漂移」** |
| R-5.3 | R-5.1 取得的 `SyncState` **沿呼叫鏈往下傳**給 U-4，不重讀。這消除了「兩次獨立 `read_sync_state` 之間的競態視窗」——本單元不接受該視窗，也不需要接受 |
| R-5.4 | 看板寫入成功後，**五欄一起回寫**：`last_status`、`last_field_value`、`last_reason_code`、`last_synced_at`，以及 **`managed_block_hash` ＝ 寫入後再呼叫一次 `read_item(binding, Config)`，取其回傳 `ItemState` 的 `managed_block_hash` 欄位** |
| R-5.5 | 無漂移**且無待送告示**時不呼叫 `write_sync_state`——沒有東西要更新，且多一次寫入會產生多一個 commit |
| **R-5.6** | **「有漂移」的定義含第二個來源**：三欄比對有差異，**或**該 intent 在本輪的 `reverse_rejected` 內且其 PR 關閉時刻晚於 `last_synced_at`（有一則 [US:S-6 AC 5] 的告示待送；`last_synced_at` 為 `null` 時該比較判為真，見 U-4 `domain-entities.md`）。**任一成立即進入寫入鏈。** |
| **R-5.10** | **`Decision.status` 為 `null` 時分兩支，依 `reason_code` 決定**，不是單一分支：<br>**(a) `parked`／`suppressed`／`undecidable`** → 跳過 `write_status`，但照常走 `write_field` → `render` → `write_body` → 回讀 → `write_sync_state`。Status 欄維持原值（[req:FR-G3]），不寫的原因與時間戳由自訂欄位與受管區塊承載（[US-OQ-3]）。<br>**(b) `unparseable`／`whitelisted`** → **走不到這裡**——已由 **R-3.0** 在分流之前擋下（[req:FR-J3]）。本支保留為**深度防禦**：若實作漏了 R-3.0，此處仍不得 `write_status`／`write_field`／`write_body`；已綁定者僅回寫 `SyncState` 記錄本輪判定，未綁定者連狀態檔都不建 |

> **R-5.4 的雜湊來源已更正（reviewer iteration 2 Critical，2026-08-29T16:19:47Z）。** 先前寫成「對剛由 `render` 產生的東西算 `content_hash`」，有兩個問題：
>
> 1. **型別不成立**：`render: (Decision, Context) -> string`，而 `content_hash: (Block) -> sha256`（[ad:component-methods.md]）。中間少了 `parse`。
> 2. **更要緊的是等價性**：這個雜湊必須與 U-8 日後 `read_item → parse → content_hash` 算出的值**逐位元組相等**。若 `render()` 的輸出與「該字串被 GitHub 儲存後再 parse 回來的 `Block`」在正規化上有任何差異（換行、markdown 轉義、HTML 註解排版），兩者會**永久不相等**——於是在**沒有任何人為變更**的情況下，U-8 每天為每個受管 intent 各開一則反向 PR。這是 [ad:decisions.md] ADR-A6 點名的最危險失敗模式，觸發者變成機制自己每一次正常的寫入。
>
> **改以回讀取得的值為準，等價性由構造保證**——U-6 記錄的與 U-8 日後計算的，走的是同一條 `read_item → parse → content_hash` 路徑。此不變式與其驗證落點（U-9 第二段）已登錄於 **ADR-0015 §10**。

> **代價的實算（iteration 3 m-1，2026-08-30T00:57:28Z）**：先前寫「每次實際寫入多一次讀取」。實際數一次——每個進入寫入鏈**且走 R-5.10 (a) 支或 `mapped`** 的 intent 需要 **2 次 `read_item`**：`write_status` 內部一次（回讀比對）、R-5.4 的寫入後回讀一次。相對於修正前的 1 次是 **2 倍**，不是「多一次」那句話聽起來的線性小增量。**R-5.10 (b) 支（`unparseable`／`whitelisted`）一次也不讀**——它不產生任何看板寫入。（iteration 2 的 R-5.7 曾再加一次寫入前 `read_item` 使其成為 3 次，但該規則已依 Q5=A 撤回，見上。）
>
> **無漂移的 intent 完全不讀看板**（R-5.5 的不寫分支），而 registry 中多數 intent 每輪都無漂移，所以放大係數作用在「有漂移」這個小得多的分母上。即便如此，[req:FR-I4] 的單次操作上限**實際值未知**——PRE-1 第 2 項（C-T5）在 `bolt-plan.md` 明訂延後到 **Bolt 2** 才綠，而本單元在 **Bolt 1** 上線。這個順序本身是已知風險，不由本規則新增，但本節的倍數必須誠實記載以免 Bolt 2 實測時對不上帳。

> **R-5.6 是 reviewer iteration 2 的 Critical 修正（2026-08-29T16:19:47Z）。** 先前 R-6.2 的告示機制**結構上永遠不會被觸發**：PR 被拒代表協作者的改動從未進入 `ut`（U-8 的 R-6.0），亦即 **record 自始至終沒有變過**，於是 `map()` 算出的 `Decision` 與 `SyncState` 記錄的三欄**完全相同** ⇒ 三欄比對判無漂移 ⇒ 走 R-5.5 的不寫分支 ⇒ **整條 `write_status → render → write_sync_state` 鏈不會執行**，帶告示的 `Context` 無處遞交。
>
> 連帶後果更糟：因為不寫，`last_synced_at` 也不會前進，該 intent **永遠留在 `reverse_rejected` 裡且沒有紅燈**。
>
> AC 5 針對的正是「PR 被拒」這個情境，而先前的設計恰好在那個情境下失效。R-5.6 把「有告示待送」升為與三欄差異並列的寫入理由，鏈才會啟動。

### R-5.7 — `write_status` 的 `expected` 取自 `SyncState` 三欄（Q5=A 定案）

`write_status(binding, expected: ItemState, desired: Status)` 內部「必先回讀」並與 `expected` 比對，不符即回 `Aborted`（[ad:component-methods.md]、U-3 的 R-2.1）。

> **這一組規則在 iteration 2 與 iteration 3 各被改過一次，兩次的方向相反，值得完整記下來。**
>
> - **iteration 2（2026-08-29T16:19:47Z，Critical）**：發現 `expected` 取自 `SyncState` 時，U-7 每一次正常補平都會製造一則假通報。時序：record 變更 → 本單元寫入失敗（外部錯誤）→ `SyncState` 與看板都停在舊值 → U-7 對帳偵測到看板≠record，補平看板為新值（但 reconcile 無 C-4，不更新 `SyncState`）→ 下一輪本單元以舊值當 `expected`，而看板已是新值 ⇒ `Aborted` ＋ 假通報。當時的修法是改取當下 `read_item`。
> - **iteration 3（2026-08-30T00:57:28Z，Critical C-1）**：那個修法把守門整個廢掉了。`expected` 若是幾百毫秒前剛讀的值，`write_status` 內部的回讀比對**恆真**，`Aborted` 實務上不可達——而 [req:FR-C3] 逐字要求「後到者的回讀比對會偵測到前者已寫入的結果」，`stories.md:237` 同義，[req:FR-C1]「不符即中止寫入並開 issue」亦然。連帶 `ReconcileReport.aborted`、[US:S-9 AC 2] 的第三份清單、本單元錯誤表的 `Aborted` 列全部成為死碼。**把假陽性換成了所有真陽性一起消失。**
>
> **定案（人工裁決 Q5=A）**：`expected` 回到 `SyncState`，過期問題改從**源頭**解決——ADR-0015 §13 給 reconcile 的元件鏈補上 C-4，U-7 補平後一併回寫三欄。誰寫看板誰就負責記錄自己寫了什麼。
>
> **這也是為什麼不採「U-6 多一層『已被補平』判定」**（Q5=B）：它零上游變更，但留一個真實漏洞——U-7 補平為 X' 後 record 又變為 X''，`actual`／`expected`／`desired` 三者互異，仍是假 `Aborted`。

| # | 規則 |
| --- | --- |
| R-5.7 | `write_status` 的 `expected` 由 **R-5.1 讀到的 `SyncState`** 三欄重建（`last_status`／`last_field_value`／`last_reason_code`），代表「**機制上次寫進看板的值**」。**不得**改取當下的 `read_item`——那會讓 `write_status` 內部的回讀比對恆真 |
| **R-5.7a** | **首寫例外（2026-09-06 依 Project #16 實測補入）**：`expected` 為空（`SyncState` 從未記錄一次成功的 Status 寫入）而 `write_status` 回 `Aborted` 且 `actual` 非空時，**以該 `actual` 為 `expected` 重試一次**；重試仍 `Aborted` 則照 R-5.12 處置。理由：R-5.7 守的是「我上次寫入**之後**有沒有人動過」，首寫前沒有「上次寫入」可守；此時的 `actual` 來自看板自動化（#16 實測：item 加入即為 `Backlog`），不是人為變更。不重試的後果已實測：`260816-production-path-check` 首建後每輪 `Aborted`、永遠寫不進第一筆 Status、每次 push 對通報 issue 追加一則留言。**這不是 iteration 2 那種「改取當下 `read_item`」**——例外只在從未寫入時成立一次，首寫成功後 `last_written_status` 就有值，R-5.7 全額生效。已知殘餘：若有人在機制首寫**之前**就手動移動該卡，那一次移動會被首寫覆蓋（僅此一次，之後受 R-5.7 保護）。 |
| R-5.8 | `SyncState` 的三欄有**兩個**用途且不可互相取代：R-5.2 的漂移判定（「我們的判定變了嗎」——比的是 `Decision` ↔ `SyncState`），以及 R-5.7 的 `expected`（「我們上次寫了什麼」——交給 `write_status` 去比看板現況）。它**不是**「看板現在是什麼」的代理——後者只有 `read_item` 答得出來，而那正是 `write_status` 內部自己會做的事 |
| R-5.9 | **`SyncState` 落後於看板有三個來源**，不是一個：①U-7 補平（已由 ADR-0015 §13 從源頭堵住——reconcile 補上 C-4，補平後一併回寫）；②**本單元自己**的 `commit_and_push` 回 `Rejected`；③**本單元自己**的 R-5.4 回讀拋 `ExternalError`。②③的共同形狀是「看板已寫成功，但記錄那次寫入的動作失敗了」 |
| **R-5.12** | **`SyncState` 逐欄記錄「實際寫成功」的部分**，依失敗步驟分**四**種，不是三種：<br>• `write_status` 回 `Aborted` 或拋 `ExternalError` ⇒ **完全不回寫**（看板一個字都沒動）。<br>• `write_field` 回 `Failed` ⇒ 回寫 `last_status`／`last_reason_code`／`last_synced_at`／`managed_block_hash`，**`last_field_value` 維持原值**。<br>• **`write_body` 回 `Failed`** ⇒ 受管區塊**未被寫入**，故舊雜湊仍然正確 ⇒ 回寫 `last_status`／`last_field_value`／`last_reason_code`，**`managed_block_hash` 與 `last_synced_at` 皆維持原值**（後者是告示是否送達的標記，見 R-5.13）。<br>• **R-5.4 的回讀拋 `ExternalError`** ⇒ 受管區塊**已經寫成功**，只是算不出它的雜湊 ⇒ **完全不回寫**，交由 U-7 的 R-6.5／R-6.8 修復。<br>每一種失敗都交 C-5 `notify` |
| **R-5.13** | **`last_synced_at` 的語意是「上一次**受管區塊**成功寫入的時刻」**，不是「上一次任何欄位成功寫入的時刻」。R-5.6 與 R-6.2c 用它判斷 [US:S-6 AC 5] 的告示是否已送達，而告示載體就是受管區塊——兩者必須同步前進 |
| R-5.11 | **②③ 的修復落點在 U-7 的 R-6.5**，不在本單元。本單元下一輪對這種 intent 會判 `Aborted`（`expected` 是舊值、看板是新值），**這是正確的**——本單元無法分辨「我上輪寫的但沒記錄」與「別人改的」，兩者在本單元的視野內完全相同。`Aborted` ＋ 通報是 [req:FR-C1] 要的行為 |

> **R-5.10 的 (b) 支是 iteration 4 Group A C-2 的修正（2026-08-30T01:31:09Z）。** 先前 R-5.10 只有一支，讓五種 `reason_code` **全部**照走 `write_field` → `write_body`，這**直接違反 [req:FR-J3] 的逐字驗收**：「解析不出必要欄位的 record 一律**跳過、不寫入看板**……機制**不對其產生任何看板寫入**」。而該條點名的 `260802-default` **今日就在 registry 內且無綁定**——第一次上線就會撞到，且 `create_item` 的首建路徑也在違反範圍內（它在 R-5.10 之前分岔，先前完全沒被考慮）。
>
> `whitelisted` 與 `unparseable` 同屬 FR-J3：[ad:component-methods.md] 逐字「`Unparseable` 輸入回 `reason_code = "unparseable"`（白名單內則 `"whitelisted"`）」——白名單只改 `reason_code`，不改「解析不出」這個事實。
>
> **`undecidable` 不在 (b) 支**：FR-J3 管的是「解析不出必要欄位」，而 `undecidable` 的 record **解析成功**、只是訊號不落在對照表任一列（[US:S-2 AC 4]）。兩者的處置本來就不同。

> **R-5.10 (a) 支是 iteration 3 M-3 的修正（2026-08-30T00:57:28Z）。** `Decision.status` 的值域是 `Status | null`（[ad:component-methods.md]），五種 `reason_code`（`parked`／`suppressed`／`unparseable`／`whitelisted`／`undecidable`）**全部**對應 `status = null`；而 R-5.2 只要 `reason_code` 一變就判為有漂移 ⇒ 進入寫入鏈 ⇒ 撞上 `write_status(binding, expected, desired: Status)` 的 `desired` **型別不含 `null`**。先前全單元沒有任何規則說明這個分支怎麼走，而 `suppressed`／`parked` 正是**最常走**的兩條路徑——這是實作阻塞，不只是文件缺漏。
>
> **為什麼是「跳過 `write_status` 但照常寫其餘三者」**：[req:FR-G3] 要求暫停覆寫的是 **Status**，不是整個 item；[US-OQ-3] 要求受管區塊記下「不寫的原因類別與 ISO 8601 時間戳」——若整條鏈都跳過，那筆記錄就沒有載體，而 `Block.status`／`reason_category`「恰有一個非 `null`」的互斥設計（U-2 `domain-entities.md`）正是為這個分支存在的。

> **R-5.12 於 2026-08-30T03:35:44Z 再次改寫（iteration 6 確認審的 C-6.1／C-6.2，兩項皆 Critical）。** 前一版把四種失敗壓成三種，其中**第三種把兩個後果相反的情形合併**了：
>
> - `write_body` 回 `Failed` ⇒ 受管區塊**沒被寫入** ⇒ 留舊雜湊**正確**。
> - R-5.4 的回讀拋 `ExternalError` ⇒ 受管區塊**已經寫成功** ⇒ 留舊雜湊**永久錯誤**。
>
> 合併的後果（C-6.1）：後者留下「三欄皆新、雜湊過期」⇒ 本單元下一輪判無漂移而不重寫、U-7 的 R-6.5 因「三欄相符」而不觸發 ⇒ **R-6.8 不可達** ⇒ U-8 每天為該 intent 開一則無人為變更的反向 PR。**這條路徑在改為逐欄之前是被舊 R-5.12 的全有全無覆蓋的——我把它打開了。** 現改為「完全不回寫」，讓 R-6.5 的觸發條件（看板 == record 而 `SyncState` ≠ 兩者）成立。
>
> 第二個後果（C-6.2）：前一版「回寫前四欄」依 R-5.4 的欄序**包含 `last_synced_at`** ⇒ `write_body` 失敗那一輪告示未送達卻讓 `last_synced_at` 前進 ⇒ R-6.2c 次輪不再成立 ⇒ **[US:S-6 AC 5] 的告示永久靜默**，正是 iteration 4 的 B:C-1 原樣重開。而該版自述逐字宣稱「告示下一輪會重試」——**規則本文與自述互相否定**。R-5.13 把 `last_synced_at` 的語意釘死在受管區塊上，兩者不再脫鉤。

> **R-5.12 的上一版（iteration 5 Group A C-3）由「任一步失敗即完全不回寫」改為「逐欄」。** 原寫法與 `write_field` 的「**失敗不連坐**」（[US:S-5 AC 2]）字面相反，但更嚴重的是它**會自己製造 R-5.9 ②③ 那個卡死**：欄位寫失敗 ⇒ 不回寫 ⇒ 下一輪 `expected`（舊）≠ `actual`（新，Status 已寫成功）⇒ `Aborted` ⇒ 鏈中止 ⇒ 永遠追不上。我為了修 B:C-1（告示因暫時性失敗而永久消失）引入的規則，把 A:C-1 剛堵住的洞從另一側打開。
>
> **逐欄記錄同時滿足兩邊**：`SyncState` 的語意始終是「機制上次**成功**寫進看板的值」（R-5.8），沒有任何一欄會宣稱一個沒發生的寫入；而 `last_synced_at` 只在有欄位真的寫成功時前進，所以 R-6.2c 的告示條件在 `write_body` 失敗時仍然成立——**告示下一輪會重試，這正是 B:C-1 要的**。
>
> **`write_status` 失敗是唯一的全有全無情形**：它失敗代表看板一個字都沒動（`Aborted` 明文「不送出寫入」），此時回寫任何欄位都會是謊。

> **R-5.12 的原始動機是 iteration 4 Group B C-1（2026-08-30T01:31:09Z）。** `write_body` 是本輪新插進寫入鏈的**可失敗步驟**，而先前 U-6 對它的 `Failed` 零規則、錯誤表也無該列。後果不只是「少一層錯誤處理」：
>
> R-6.2c 的「告示只出現一次」判準是 **PR 關閉時刻晚於 `last_synced_at`**，而 `last_synced_at` 由 R-5.4 在回寫時推進。若 `write_body` 一次暫時性失敗、而本輪**仍然**回寫了 `SyncState`，`last_synced_at` 就會前進、該 intent 離開 `reverse_rejected` ⇒ **[US:S-6 AC 5] 的告示永久靜默消失**，且受管區塊永久凍在舊內容（下一輪無漂移、不再寫）。一次網路抖動換一條 AC 永久落空。
>
> **R-5.12 把「有沒有寫成功」與「有沒有記錄」綁在一起**：任一步失敗就不回寫，於是 `last_synced_at` 不前進、告示條件下一輪仍成立、受管區塊下一輪會重試。代價是本輪的部分成功（例如 Status 寫成了但 `write_body` 失敗）在狀態檔上看不出來——但那正是 R-5.9 ②③ 描述的情形，其修復落點已在 U-7 的 R-6.5。

> **R-5.9 於 2026-08-30T01:31:09Z 由「唯一來源」改為三個來源（reviewer iteration 4 Group A C-1 Critical）。**
>
> 先前寫「唯一來源是 U-7 補平，已從源頭堵住」，並據此宣告本單元**不需要**任何補救。那個「唯一」不成立，而**取消補救的宣告讓缺口變成永久卡死**：
>
> 1. 本單元寫看板成功 → `commit_and_push` 回 `Rejected`（或 R-5.4 的回讀拋 `ExternalError`）⇒ 看板是新值、`SyncState` 是舊值。
> 2. 下一輪：`expected`（舊）≠ `actual`（新）⇒ `Aborted` ⇒ **寫入鏈中止** ⇒ `SyncState` 仍是舊值。
> 3. U-7 也不會修：看板此刻**等於** record（第 1 步寫成功了），對帳判定一致，依 R-6.3「未補平的 intent 不回寫」而不動作。
> 4. 回到第 2 步。**每一輪都開一則假通報，而狀態永遠追不上。**
>
> **修復落點選 U-7 而非本單元**（新增其 R-6.5）：本單元在事件路徑上**無法分辨**「我上輪寫的但沒記錄」與「別人改的」——兩者在它的視野內都是「看板 ≠ 我記得的值」，而把兩者合併處理正是 iteration 3 C-1（守門恆真）的形狀。U-7 有本單元沒有的第三個座標——**record**：當「看板 == record 而 `SyncState` ≠ 兩者」時，這個組合只可能來自遺失的回寫，因為人為改動不會恰好把看板改成 record 的值。

> **前綴對照（iteration 4 Group A M-4，2026-08-30T01:31:09Z）**：[ad:component-methods.md] 的自訂欄位前綴是**四選一**（無／`parked @ `／`skipped `／`frozen: `），而會走到 `write_field` 的 `reason_code` 有四種。逐一對照：
>
> | `reason_code` | 前綴 | 依據 |
> | --- | --- | --- |
> | `mapped` | 無 | 上游預設 |
> | `parked` | `parked @ ` | 語意直接對應 |
> | `suppressed` | `frozen: ` | 反向 PR 開啟中而暫停覆寫，語意對應「凍結」 |
> | `undecidable` | **無對應前綴** | 四個前綴皆不適用——`skipped ` 對應的是 `[S]` 標記（scope 內被跳過），與「訊號不落在對照表任一列」是兩回事 |
>
> **`undecidable` 的缺口不在本站自行填補**：前綴集合是 [ad:component-methods.md] 定的格式契約，加第五個前綴是上游修訂。**指派 ADR-0015 新增一節**，確認人為 **Bolt 1 的 gate**（本單元於該 Bolt 交付）。**在它落地之前，`undecidable` 的自訂欄位行為未定義**——實作不得自行猜一個前綴，那會讓一個格式契約在沒人核可的情況下擴張。`undecidable` 本身是 U-7 在 G-1 標出、由 functional-design 新增的 `reason_code`，這個連帶缺口是它的直接後果。

**R-5.8 是這一組 Critical 的根本更正**：`SyncState` 記的是「機制上次寫進看板的值」，`ItemState` 記的是「看板現在是什麼」。兩者仍是不同的問題，但**保持一致的責任已從 U-6 移到寫入者本身**——依 Q5=A 與 ADR-0015 §13，U-7 補平後會一併回寫 `SyncState`，所以「後者變了而前者沒變」這個狀態不再產生（R-5.9）。

### R-5.4 是本 intent 唯一寫 `managed_block_hash` 的地方

**先前沒有任何單元寫它。** U-3 把它算進 `ItemState`（讀看板時）、U-4 宣告並儲存它、U-8 的 R-1.1 拿它當比對基準——**三個角色齊備，就是沒有寫者**。

後果不是「少一層保護」：儲存值恆為 `null`，與看板現況永遠不同，**U-8 每輪都會判定「有人改過看板」並為每個已綁定 intent 各開一則反向 PR**。這與 `pending_reverse` 是同一類缺陷（狀態欄位少一個角色），由 reviewer iteration 1 抓出。

### U-7 的補平**會**回寫狀態檔（Q5=A 定案，2026-08-30T00:57:28Z 改寫）

> **本節先前的標題是「U-7 的補平**不**回寫狀態檔，這是刻意的」，並據 [ad:components.md] 把 reconcile 的元件集合記為 `C-7 →（內部）C-2／C-1／C-3／C-5`（無 C-4）。**那個現況正是 C-1 這個 Critical 的成因**：補平改變看板而不更新 `SyncState`，於是本單元下一輪的 `expected` 必然過期。iteration 2 曾試圖從 U-6 這一側迴避（改取當下 `read_item`），結果讓守門恆真。**人工裁決 Q5=A 選擇從源頭解決**：ADR-0015 §13 為 reconcile 補上 C-4。
>
> 「刻意」這個詞當時也不準確——上游沒有為這個排除給過理由，本站是在**描述**現況而非轉述一個決定。

依 **ADR-0015 §13**，U-7 補平看板後比照本單元的 R-5.4 回寫 `SyncState`。以下界限仍然適用：

| 欄位 | 補平後的狀態 | 後果 |
| --- | --- | --- |
| `last_status` 等三欄 | **由 U-7 當場回寫，不過期** | 本單元下一輪讀到的是最新值，`expected` 因此可信。**不再需要「自癒」這個概念**——先前兩輪各自試過的兩種自癒說法（冪等重寫、當下回讀）都不成立，見上方 R-5.7 的完整記載 |
| `managed_block_hash` | **不受影響** | 補平只寫 Status 欄位（C-3 `write_status`），**不重寫受管區塊**——reconcile 的元件集合經 ADR-0015 §13 補上 C-4 之後**仍不含 C-6**，所以區塊雜湊沒有變，U-7 回寫時不得動這一欄 |

第二列是關鍵：若補平會重寫受管區塊而雜湊沒更新，U-8 就會誤判為人為變更。**因為 reconcile 不碰受管區塊，這條路徑不成立。**

## R-7 群：本單元呼叫的上游方法（具名，2026-08-29T15:28:15Z 補）

> **送審前自檢第 2 項（每個宣告的方法都要有具名呼叫者）跑全站後發現的。** 本單元先前用「U-4 write（首建路徑）」「U-1 map()」這類籠統說法指涉上游，於是 `read_binding`／`write_binding`／`field_value_for` 三個方法在全 intent 的 functional-design 產出中**只有擁有者提到、沒有任何呼叫者**——與 `resolve_if_open` 同一個形狀，只是後果較輕（實作者仍會從元件契約推出來，但「誰呼叫」不該靠推）。

| 方法 | 元件 | 本單元何時呼叫 |
| --- | --- | --- |
| `read_binding(record_path) -> int \| null` | C-4 | 逐 record 迴圈開頭，判定走首建或已綁定路徑；回 `null` 即首建 |
| `create_item(intent_id, Config) -> binding` | C-3 | 首建路徑 |
| `write_binding(record_path, issue_number)` | C-4 | 首建成功後立刻寫回綁定編號 |
| `map(ParsedRecord, Config) -> Decision` | C-1 | 已綁定路徑的判定 |
| `field_value_for(Decision, Config) -> string` | C-1 | **在 `write_field` 之前**組出自訂欄位值；純函式。**只在 R-5.10 (a) 支與 `mapped` 時呼叫**——(b) 支不產生任何看板寫入 |
| `read_sync_state` / `write_sync_state` | C-4 | R-5.1 讀一次、R-5.4 回寫五欄 |
| `write_status` / `write_field` / **`write_body`** | C-3 | 有漂移時的看板寫入。`write_status` 寫 Status 欄（`Decision.status` 為 `null` 時跳過，R-5.10）、`write_field` 寫自訂欄位、**`write_body` 寫受管區塊進 issue body**（ADR-0015 §11 增設） |
| `read_item` | C-3 | R-5.4 的寫入後回讀，取 `managed_block_hash` |
| `render(Decision, Context) -> string` | C-6 | 受管區塊的渲染。**`Context` 由本單元組裝**，三欄來源見下 |

**`Context` 的組裝責任在本單元**（[ad:component-methods.md] 只用 `Context` 而未定義它；型別定義在 U-2 的 `domain-entities.md`）：

| `Context` 欄位 | 本單元的來源 |
| --- | --- |
| `decided_at` | 本輪的當前時刻（`date -u` 等價物）。每輪必填；`Decision.status` 非 `null` 時 `render` 不輸出它 |
| `scope_note` | **U-1 composite action 的第五個 output**，逐字轉交，本單元不加工 |
| `rejection_notice` | R-6.2b——該 intent 落在本輪 `reverse_rejected` 內時為 `{ closed_at }`，否則 `null` |

> **這張表是 iteration 4 Group B M-2 補上的（2026-08-30T01:31:09Z）**：`Context` 於 iteration 3 在 U-2 定義後，本單元只在 R-6.2b 提過 `rejection_notice` 一欄，`decided_at` 在全單元**零命中**、`scope_note` 只出現在序列圖且被誤畫成 `map()` 的輸出（實際是 composite action 的第五個 output，`map` 的簽章一字未動）。契約端點三問的「誰寫」在這三欄上原本答不出來。
| `render(Decision, Context) -> string` / `content_hash(Block) -> sha256` | **C-6** | 受管區塊的渲染與其雜湊（供 R-5.4 回寫） |
| `commit_and_push(branch, paths, message)` | C-4 | 回寫的推送 |
| `notify` / `resolve_if_open` | C-5 | 失敗通報；迴圈結束後的關閉（R-6.1） |

## R-6 群：本單元承接的兩項跨單元缺口（reviewer iteration 1）

### R-6.1 — `resolve_if_open` 的呼叫者是本單元（U-5 的 Critical）

U-5 的 `resolve_if_open`（關閉已不再成立的通報 issue）**先前沒有任何單元呼叫它**。U-5 是 `kind: library`，沒有自己的執行期；U-6／U-7／U-8 三份設計全文都沒提過它。缺口 J-2（通報 issue 永不自動關閉）因此其實沒被關掉。

**本單元在此正式承接**（沿用本 intent 對跨單元缺口指派的既有形狀，如 F-4→U-6、G-1→U-7）：

| # | 規則 |
| --- | --- |
| R-6.1a | **逐 record 迴圈結束之後**，對本輪蒐集到的每一個待關閉鍵各呼叫一次 `resolve_if_open(FailureIdentity)` |
| R-6.1b | **待關閉鍵的來源**：對本輪**處理成功**的每一個 intent，以 U-5 列舉的失敗值域**逐一**構成鍵——`{intent_id, reason_code}`，`reason_code` ∈ {`ExternalError`, `Rejected`, `Aborted`, `CannotCreate`, `Failed`}。`resolve_if_open` 對不存在的 issue 是 no-op（[ad:component-methods.md] §C-5），所以「多問幾個鍵」零成本 |
| R-6.1d | **不得**以 `SyncState.last_reason_code` 當鍵來源。它的型別是 `ReasonCode`（U-1 的映射結果），**與 `FailureIdentity.reason_code` 是兩個不同的命名空間**；且它只在寫入成功時才被寫 |
| R-6.1c | **失敗不影響本輪的同步結果**：關閉 issue 失敗只記 log 與紅燈，不回滾已寫入看板的內容 |

> **R-6.1a／R-6.1b 已更正（reviewer iteration 2 Major，2026-08-29T16:19:47Z）。** 先前寫「呼叫一次 `resolve_if_open`」，但其簽章是 `(FailureIdentity) -> `，`FailureIdentity = { intent_id, reason_code }`——**它只能逐鍵呼叫，沒有「不帶鍵、關閉全部」的形式**。更矛盾的是先前的 R-6.1b 明文排斥逐 intent 判斷，而 API 形狀恰恰只允許逐鍵。依字面實作的人會卡在「一次呼叫要傳什麼鍵」。
>
> **R-6.1b 於 2026-08-30T01:31:09Z 整條改寫（reviewer iteration 4 Group A C-3 Critical）。** 先前寫「鍵來自某 intent 上一輪的 `SyncState.last_reason_code` 屬失敗類」，那條規則**永遠拿不到任何鍵**，兩個獨立的理由各自就足以讓它失效：
>
> 1. **型別錯誤**：`SyncState.last_reason_code` 的型別是 `ReasonCode`，其六個值（`mapped`／`parked`／`suppressed`／`unparseable`／`whitelisted`／`undecidable`）**沒有一個是失敗類**。U-5 的 `domain-entities.md` 早已明文「`reason_code` 在此的值域**不等於** U-1 的 `ReasonCode`」並列出實際值域（`ExternalError`／`Rejected`／`Aborted`／`CannotCreate`）——本規則取錯了命名空間。
> 2. **時機錯誤**：`last_reason_code` 由 R-5.4 在**寫入成功後**才回寫。失敗的那一輪根本不會留下任何記錄。
>
> 兩者合起來使 `resolve_if_open` 成為一個永遠不會被有效呼叫的方法，缺口 J-2（該方法無呼叫者）**在文件上看起來已關閉、實際沒有**——這正是 `project.md` 的 `functional-design:c10`（偵測 X 而 X 不可達）在方法層的版本。
>
> **改法為什麼是「逐一試全部失敗值」而不是「記住上輪失敗了什麼」**：後者需要一份跨輪的失敗記憶，而 ADR-A8 的 [Q5=A] 明文選了「記憶體是 GitHub issue 本身，**不新增任何持久狀態**」。逐一試是它的直接後果——失敗值域是有限小集合，且 `resolve_if_open` 對不存在的 issue 是 no-op。

> **「在迴圈之後」的理由也一併收窄**：不是因為「逐 intent 判斷會誤讀」（那句已刪，它與 API 形狀衝突），而是因為**鍵的蒐集需要整輪跑完**——某 intent 本輪是否成功，要等它被處理過才知道。收集在迴圈內，呼叫在迴圈後。

**U-7 也應呼叫它**（它同樣在 [ad:components.md] 的元件集合中有 C-5，且每日全掃最適合收殘留），但**那是 U-7 的落點，本站只標出**。**U-8 現在也在此列**——其元件集合原不含 C-5，已由 ADR-0015 §5 補上（2026-08-30T01:31:09Z 更正，reviewer iteration 4 Group B M-6）。

### R-6.2 — [US:S-6 AC 5] 的「未被採納」告示（U-8 的 Critical）

[US:S-6 AC 5] 逐字：「**Given** 該反向 PR 被**關閉而未合併**，**When** 下一次正向同步覆寫該 item 之前，**Then** 該 item 的 issue 受管區塊載有一則記錄，指出該次人工改動未被採納與其時間戳。」

**先前無任何單元覆蓋它。** [ug:unit-of-work-story-map.md] 把 S-6 的 AC 1–5 全歸 U-8，但——

> **這個歸屬對 AC 5 不成立，且是可機械判定的。** AC 5 要求的是「**受管區塊**載有一則記錄」，而受管區塊的寫入路徑是 `U-2 render → U-3 write_body`，只在**本單元**（正向同步）執行。〔**先前此處誤寫 `write_field`**——那是 Projects v2 的自訂欄位（≤50 字元），[ad:component-methods.md] §自訂欄位格式明訂「完整敘述一律在受管區塊」，兩者是上游明文區分的東西。該誤述使受管區塊看起來有寫者而實際沒有，reviewer iteration 3 兩組各自獨立抓到（Group A C-3／Group B F1）；`write_body` 由 ADR-0015 §11 增設，更正於 2026-08-30T00:57:28Z〕U-8 從不寫受管區塊——它的元件集合是 `C-3（讀）→ C-6（雜湊比對）→ C-4（寫檔）→ 開 PR`（[ad:components.md]），沒有任何一步寫回看板。
>
> **處置**：實作落在本單元；**story map 的 AC 5 歸屬需更正**。story map 是已通過 gate 的上游產出，故**標出不逕改**——**本項已由 ADR-0015 §4 承載**（送審前自檢遷移，2026-08-29T23:42:35Z；先前只寫「指派 `units-generation` 的 `unit-of-work-story-map.md`」，而 `units-generation` 已定稿、不會為了下游的一句指派再跑一次——那是 ADR-0015 Context 段點名的「沒有收件人的便條」）。**確認人維持 Bolt 1 的 gate**（本單元於 Bolt 1 交付，屆時必須確認這條 AC 有承接者）。

| # | 規則 |
| --- | --- |
| R-6.2a | 迴圈之前的那次 label 查詢（R-2.1）**改為同時取回關閉而未合併**的反向 PR，映射為 intent id 集合 **`reverse_rejected`（本單元 workflow 層的本輪執行期集合，不進 `Config`）** |
| R-6.2b | 對本輪 `reverse_rejected` 內的 intent，本輪**照常覆寫**（[req:FR-G3]：關閉即恢復覆寫），且把 **`Context.rejection_notice = { closed_at: <該 PR 的關閉時刻> }`** 傳給 `render`（欄位定義見 U-2 `domain-entities.md`，渲染規則為 U-2 的 R-1.5，並經 `Block.rejection_notice` 進入 `content_hash` 涵蓋範圍——ADR-0015 §12）。不在該集合內的 intent，此欄位為 `null` |
| R-6.2c | 告示只出現一次——寫入後該 intent 即離開 `reverse_rejected`（下一輪的查詢以 PR 關閉時間晚於 `last_synced_at` 為準；R-5.4 在該輪把 `last_synced_at` 推進到寫入時刻，使下一輪此條不再成立） |

**R-6.2c 的判定基準是 `last_synced_at`**，而該欄位由 R-5.4 回寫——**兩條規則互相依賴，缺一即失效**：沒有 R-5.4 就沒有可信的 `last_synced_at`，告示會每輪重複出現。

**本單元不裁定告示的文字與版面**——那是受管區塊的呈現，屬 U-2 的 `render` 契約。**已由 U-2 承接**：`Context` 的三個欄位（`decided_at`／`scope_note`／`rejection_notice`）定義於 U-2 的 `domain-entities.md`，渲染規則為該單元的 R-1.5。

> **這個承接是送審前自檢補上的（2026-08-29T23:42:35Z）。** 先前此處寫「指派 U-2 定義」，而 U-2 三份產出當時**完全沒有提到 `Context`**——`Context` 是 `render` 簽章的第二個參數，上游 [ad:component-methods.md] 只用它、從未定義它，形狀與 U-1 承接的缺口 F-1（`Config`）相同。兄弟單元之間的指派沒有任何機制保證會被接住，且兩者同屬本 stage、閘門尚未觸發，故就地補齊而非留給下一站。
>
> **連帶約束**：`rejection_notice` 是 `Block` 的新增資訊，其上線在 ADR-A6 意義下是一次格式變更（須 bump `format_version` 並重新基準化）。因此 R-6.2 與 U-2 的 R-1.5 **必須同批交付**（兩者同為 Bolt 1），不得先上本單元的填入而後補 U-2 的渲染——那會讓 `Context` 多一個沒有讀者的欄位，而 AC 5 在該期間仍不成立。

## 與上游的對應

concurrency、生命週期、選取分流、兩道防線與其代價逐字引自 [ad:services.md] 的 S-A；[req:FR-A1]／[req:FR-A4]／[req:FR-C1]／[req:FR-G3]／[req:NFR-P3] 引自 `requirements.md`；[US:S-1 AC 1]／[US:S-2 AC 11–13]／[US:S-6 AC 3] 引自 `stories.md` 與 [ug:unit-of-work-story-map.md]；選取邊界引自 [ad:component-methods.md] §C-2；缺口 F-4 的指派來源為 U-1 的 `functional-design-questions.md`；完成判準引自 [ug:unit-of-work.md] 的 U-6；`Config` 的欄位見 U-1 的 `domain-entities.md`，本單元的組裝責任見同輪的 `domain-entities.md`。
