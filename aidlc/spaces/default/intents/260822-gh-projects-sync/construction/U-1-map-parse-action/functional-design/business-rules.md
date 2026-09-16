# Business Rules — U-1 映射與解析 composite action

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-1-map-parse-action
     本檔是可判定的規則清單。每條規則都要能被一組純文字 fixture 判真偽——
     寫不出 fixture 的「規則」不是規則，是願望。 -->

## R-1 群：`get_field` 的四條行為

逐字沿用 [ad:component-methods.md] §C-2，[US:S-2 AC 7–10]。四條**全部**可用純文字 fixture 驗。

| # | 規則 | fixture 形狀 | 預期 |
| --- | --- | --- | --- |
| R-1.1 | 正式欄位之前另有同名行 → 回**第一個** match | 檔案前段先出現 `- **Status**: Draft`，後段才是正式的 `- **Status**: Completed` | 回 `"Draft"` |
| R-1.2 | 欄位存在但值為空 → 回**空字串**，不是下一行的內容 | `- **Parked**: ` 後直接換行接 `- **Revision Count**: 0` | 回 `""`，**不是** `"- **Revision Count**: 0"` |
| R-1.3 | 欄位完全缺席 → 回 `null` | 檔案中無任何 `- **Parked**` 行 | 回 `null`，且呼叫端走**與空字串不同**的分支 |
| R-1.4 | 縮排的 `  - **X**: ` → **不視為 match** | 巢狀清單下的 `  - **Status**: Foo` | 略過，繼續往後找 |

**R-1.3 與 R-1.2 的區分是安全關鍵**，不是潔癖：[ad:component-methods.md] 明記現況 record 的 `## Runtime State` 只有 `- **Revision Count**: 0`，`Parked` 是缺席。若把 R-1.3 實作成回空字串，R-1.2 與 R-1.3 就無法區分——但兩者在 `map` 的第 1 條判定上**結論相同**（都是「未暫停」），所以這個錯誤不會被判定結果暴露，只會在未來某個依賴該區分的呼叫端悄悄出錯。因此本規則的驗證必須直接斷言 `get_field` 的回傳值，**不得只斷言最終 `Decision`**。

## R-2 群：stage 行的解析（[Q3=C] 定案）

| # | 規則 |
| --- | --- |
| R-2.1 | 只有形如 `- [<c>] <slug> — <EXECUTE\|SKIP>` 的行算 stage 行。`<c>` 為方括號內單一字元（含空格） |
| R-2.2 | `in_scope = (尾綴 == "EXECUTE")` |
| R-2.3 | `## Stage Progress` 區塊內不match R-2.1 的行**一律靜默略過**——含 `### <PHASE> PHASE` 標題、HTML 註解、`Per unit: [TBD]` |
| R-2.4 | **下限檢查**：若整個 `## Stage Progress` 區塊**一行都沒 match**，回 `Unparseable{missing: ["stage-lines"]}` |
| R-2.5 | 無 `## Stage Progress` 區塊 → `Unparseable{missing: ["stage-progress-section"]}`（沿用 [ad:component-methods.md] §C-2 的 `list_stages`） |

**R-2.4 存在的理由**（[Q3] 選項本文即已載明）：只有 R-2.1–2.3 時，引擎若改變尾綴寫法，整批 stage 會被讀成非 stage 行 → `stages` 為空 → 判定第 6 條命中 → **誤判為 `Ready` 且不報錯**。R-2.4 把這個靜默誤判變成可觀察的失敗。

**R-2.4 抓不到的**（誠實記載，非缺陷）：只有**部分**行的寫法改變時，R-2.4 不會觸發，那些行被靜默略過。這是 [Q3=C] 已知並接受的殘留。

## R-3 群：判定順序

優先序由高至低，逐字沿用 [ad:component-methods.md] §C-1，**本站一條未改**。

| # | 條件 | `status` | `reason_code` |
| --- | --- | --- | --- |
| R-3.1 | `parked` 為**非空字串** | `null` | `parked` |
| R-3.2 | `intent_id ∈ Config.reverse_pending` | `null` | `suppressed` |
| R-3.3 | `runtime_status == "Completed"` | `Done` | `mapped` |
| R-3.4 | 任一 in-scope stage 的 `checkbox == "?"` | `In review` | `mapped` |
| R-3.5 | 任一 in-scope stage 的 `checkbox ∈ {"-", "R"}` | `In progress` | `mapped` |
| R-3.6 | 無任何 in-scope stage 動過 | `Ready` | `mapped` |
| R-3.7 | 以上皆不符 | `null` | `undecidable` |

**R-3.2 的輸入來源**依 [Q2=A]：`Config.reverse_pending` 由 workflow 層在逐 record 迴圈**之前**組出，`map` 自己不做任何 I/O。

> **來源更正（reviewer iteration 1 Critical #1）**：先前寫「呼叫一次 C-4 `read_sync_state`」是錯的。[ug:unit-of-work.md] 的 U-8 實作註記明文記載已核可的偵測機制是**讀開啟中的反向同步 PR 的 diff 是否含該 intent 的 record 路徑**，由 U-8 擁有，不是 `sync-state.json`；且 [ad:component-methods.md] 的 `read_sync_state` 簽章是 `(record_path[, state])`，**逐 record**，「迴圈前呼叫一次」在該簽章下不成立。
>
> 正確來源：workflow 層在迴圈前讀一次開啟中的反向 PR 的變更路徑集合，映射為 intent id 集合。**[Q2=A] 的決定不變**（`Config` 承載、迴圈前算好、`map` 維持已核可簽章且仍是純函式），改的是那個集合怎麼算出來——依 `project.md`（`functional-design:c22`）只修理由不改決定。
>
> **逐 intent 判定**（[US:S-6 AC 3]）在更正後的來源下仍然成立，且更直接：PR diff 的路徑本來就是逐 intent 的。**已知風險**：[ad:decisions.md] 的 CAP-11 補評估把 over-suppression 標為「未驗證」——先例以 `--all-intents` 開單一 PR，該形狀下一個開著的 PR 會讓全部 intent 一起 `suppressed`。實測落在 Bolt 3（U-8），不在本單元。

**R-3.6 的「動過」定義**（reviewer iteration 1 Critical #2 後更正）：in-scope stage 的 `checkbox` 全部落在 `{" ", "S"}`。**`"S"`（jump 跳過）不算動過**。

> **先前版本寫「`"S"` 算動過」，那是錯的，且違反已核可的上游 AC。** `requirements.md` FR-B3 的驗收逐字要求「兩個只在 `[S]`／`— SKIP` 上不同的 record 產出**相同**的 Status」（[US:S-2 AC 5] 同）。推導：`— SKIP` 的孿生 record 中該 stage **不在 in_scope**，其餘 in-scope stage 全為 `[ ]` ⇒ 命中 R-3.6 ⇒ `Ready`。若 `[S]` 算動過，`[S]` 那一個就落到 R-3.7 ⇒ `undecidable`／`status = null` ⇒ **兩者 Status 不同**，AC 直接失敗。而 `--stage`／`--phase` jump 是本框架的一級機制，不是人造角落案例。
>
> **差別不會因此消失**：FR-B3 同一條也要求兩者的差別「出現在自訂欄位或 issue 受管區塊中」，那由 R-5 的 `skipped ` 前綴與 S-4 承接。Status 相同、差別可見，兩個要求同時滿足。

**R-3.1 與 R-3.3 互斥**（實測 `aidlc-state.ts:830-832`，`handlePark` 在 `Status == "Completed"` 時直接拒絕），故兩者的優先序在實務上不會被行使；順序仍照上游寫明，以免未來引擎放寬該限制時行為未定義。

## R-4 群：`Unparseable` 與白名單

| # | 規則 |
| --- | --- |
| R-4.1 | `map` 收到 `Unparseable` 且 `intent_id ∈ Config.whitelist` → `status = null`，`reason_code = "whitelisted"` |
| R-4.2 | `map` 收到 `Unparseable` 且不在白名單 → `status = null`，`reason_code = "unparseable"` |
| R-4.3 | **白名單只對 `Unparseable` 生效**，不影響可解析 record 的判定 |

R-4.3 是本站的補充：上游只寫「`Unparseable` 輸入回 `unparseable`（白名單內則 `whitelisted`）」，未說白名單是否也豁免其他情形。定為「只對 `Unparseable` 生效」的理由是 [req:FR-J5] 的白名單是「已知結構性例外」——它豁免的是解析失敗，不是判定結果。

## R-6 群：`scope_note` 的推導與值域（iteration 4 Group B M-3 補，2026-08-30T01:31:09Z）

第五個 output `scope_note` 於 iteration 3 增設時**只給了名字，沒給值域、沒給推導規則、不在型別段、`parse` 的演算法也沒有它**——它承載 [req:FR-F3]／U-2 的 R-1.2（受管區塊必須讓 `[S]` 與 `— SKIP` 的差別看得見），卻沒有任何規則說那個差別怎麼從多行 stage 縮併成單一字串。本群補上。

| # | 規則 |
| --- | --- |
| R-6.1 | 型別為**字串**，由 `ParsedRecord.stages`（R-2.1 解析出的 `{slug, checkbox, in_scope}` 序列）推導，**純函式** |
| R-6.2 | 分兩類蒐集：**`skipped-in-scope`** ＝ `in_scope` 為真且 `checkbox` 為 `"S"` 的 slug；**`out-of-scope`** ＝ `in_scope` 為假的 slug |
| R-6.3 | 格式固定為 `skipped-in-scope: <slug>, <slug>; out-of-scope: <slug>, <slug>`。**兩個分段一律都出現**，該類為空時寫 `none`（例：`skipped-in-scope: none; out-of-scope: market-research`） |
| R-6.4 | slug **依 record 內的出現順序**排列，不排序、不去重、不截斷。順序必須是決定性的——本欄位進 `Block` 進而進 `content_hash`，順序一變雜湊就變 |
| R-6.5 | 兩類皆空時為 `skipped-in-scope: none; out-of-scope: none`，**不是空字串**。空字串與「解析不出」在 `parse` 側無法分辨 |

**為什麼是「全部列出」而不是只列當前 stage**：[req:FR-B3] 的驗收要求兩個只在 `[S]`／`— SKIP` 上不同的 record 產出**相同的 Status**，而 U-2 的 R-1.2 要求那個差別在**別處**看得見。若只列當前 stage，兩個 record 在非當前 stage 上的差別就看不見，R-1.2 只被滿足了一部分。

**長度不設限**：本欄位落在受管區塊（無長度上限），不是 50 字元的自訂欄位。**R-5 群的截斷規則不適用於它。**

**連帶約束（給 U-2）**：`parse` 必須能從區塊文字把這個字串**原樣**取回（round-trip），否則 ADR-0015 §10 的雜湊等價不變式在本欄位上不成立。R-6.3 的固定格式與 R-6.5 的非空保證正是為此。

## R-5 群：自訂欄位值的格式與截斷

格式 `<短前綴><stage-slug> (<編號>)`，前綴四選一（無／`parked @ `／`skipped `／`frozen: `），上限 `Config.field_max_length`（預設 50）。以上沿用上游。

| # | 規則（[Q4=A] 定案） |
| --- | --- |
| R-5.1 | 超出上限時，**只截斷 stage-slug 的尾端** |
| R-5.2 | 前綴與 `(<編號>)` **永遠完整**，任何情況下不截斷 |
| R-5.3 | slug 可被截到**零長度**——此時 `field_value` 形如 `parked @  (<編號>)`（前綴與左括號之間留原本的空格） |
| R-5.4 | 前綴 ＋ 編號本身已超過上限時，**照寫且允許超過上限** |

**R-5.4 是刻意違反上限，不是漏判。** 優先序的理由：這個欄位存在的目的是讓人看到「哪一個 intent 走到哪一站」（[US:S-5]），狀態訊號（前綴）與可追溯的編號是它的全部價值；截掉任一個，欄位就同時失去兩者。完整敘述仍在受管區塊，兩處不一致時以受管區塊為準（[ad:decisions.md] ADR-A4）。

**連帶約束（給下游）**：U-3 `board-client` 的 `write_field` **不得**對 `field_value` 做二次截斷。若 Projects v2 本身有欄位長度上限而拒絕寫入，那是 `Failed` 而非靜默截斷，交 C-5 通報。

## R-7：總函式性（[US:S-2 AC 15]）

> **本群於 2026-08-30T06:40:39Z 由 `R-6` 改編為 `R-7`**（`open-items.md` 的 **B:M-1**，Major，落點指派 code-generation，比照 U-6／U-7 的 renumber 前例）。原因：iteration 4 新增 `scope_note` 群時也用了 `R-6`，同檔兩個 `## R-6` 使交叉引用指向兩處。**本檔下方 `## Review` 段內的歷史 `R-6` 引用一律指本群（總函式性），未改寫**——改寫會使那些 iteration 的紀錄與當時實況不符。

**對任一輸入，`map` 恰好產生一個 `Decision`，且 `reason_code` 非空。** 這是本單元最重要的不變式，也是唯一適合 property-based 測試的規則——`team.md ## Testing Posture` 記載本 repo 已有 8 個 `@given` 全落在純函式模組，落點慣例吻合。

property 的形狀：對任意 `(checkbox 組合 × runtime_status × parked × in_scope 組合)` 生成的輸入，`map` 不拋例外、回傳的 `reason_code` 在值域內、且 `status != null` 恰好蘊含 `reason_code == "mapped"`。

R-3.7 的存在保證了總函式性：它是窮盡二分的另一半，不是防禦性程式碼。

## `list_stages` 是內部方法，**不是孤兒契約**（送審前自檢第 2 項，2026-08-29T15:28:49Z）

自檢「每個宣告的方法都要有具名呼叫者」跑全站後，`list_stages` 是唯一只在本單元出現的方法。**這是正確的，不是缺口**：它是 C-2 `record-reader` 內部由 `parse` 呼叫的子方法（逐檔解析 stage 清單，[req:FR-J4] 要求不寫死），**不跨單元**。

**寫下它是為了讓下一次自檢不必重新判斷**——與 `resolve_if_open`／`read_issue_state`／`read_binding` 那幾個真孤兒的差別是：那些的用途明文指向別的單元（通報關閉、[US:S-9 AC 5]、首建路徑），本方法的用途只在 `parse` 內部。

## 與上游的對應

規則來源：[ad:component-methods.md]（R-1、R-3、R-5 的格式）、[ad:components.md]（C-1 不擁有 I/O）、[ad:services.md]（狀態只存在兩處）、`requirements.md`（FR-B3、FR-G3、FR-J3、FR-J4、FR-J5、FR-J6）、[ug:unit-of-work.md]（U-1 的完成判準）、[ug:unit-of-work-story-map.md]（S-2 與 S-3 的 AC 歸屬）。

**本檔新增的規則**：R-2.3／R-2.4（[Q3=C]）、R-4.3（白名單適用範圍）、R-5.3／R-5.4（[Q4=A]，並見下方 F-3）、R-3.6 對「動過」的定義（iteration 1 後更正為「`"S"` 不算動過」，理由見該處）。其餘皆為上游的逐字轉錄。
