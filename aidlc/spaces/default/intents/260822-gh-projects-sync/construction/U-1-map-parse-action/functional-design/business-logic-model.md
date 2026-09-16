# Business Logic Model — U-1 映射與解析 composite action

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-1-map-parse-action
     本檔是演算法與資料流；可判定的規則清單在 business-rules.md，
     型別語意在 domain-entities.md。三份不重複，互相引用。 -->

## 這個單元在做什麼

把一個 record 的**文字**變成一個**決定**。輸入是三段字串（`aidlc-state.md` 內容、`intents.json` 內容、record 路徑）加上設定，輸出是一個 `Decision`。全程零 I/O：不讀檔、不呼叫 API、不寫 log（[ad:components.md] 的 C-1／C-2 約束）。

這個限制不是潔癖——它是 [US:S-10 AC 1] 的前提。`aidlc-sync-selftest.yml` 要用純文字 fixture 驅動它，任何 I/O 都會讓 fixture 驅動失效。

## 承載形式

單一 composite action `.github/actions/aidlc-sync-map/action.yml`。**本 repo 無 composite action 先例**（`.github/actions/` 不存在），此為首例。

### 介面（[Q1=A] 定案）

| 方向 | 名稱 | 型別 | 說明 |
| --- | --- | --- | --- |
| input | `state_md` | 字串 | `aidlc-state.md` 全文 |
| input | `intents_json` | 字串 | `intents.json` 全文 |
| input | `record_path` | 字串 | record 目錄路徑，`intent_id` 由此推導 |
| input | `record_root` | 字串 | record 根目錄（[F1=A] 不得寫死） |
| input | `field_max_length` | 字串（數字） | 自訂欄位上限，預設 `50` |
| input | `whitelist` | 字串 | **換行分隔**的 intent id 集合；空字串為空集合 |
| input | `reverse_pending` | 字串 | **換行分隔**的 intent id 集合（[Q2=A]） |
| output | `status` | 字串 | `Ready`／`In progress`／`In review`／`Done`／**空字串**（決定不寫） |
| output | `field_value` | 字串 | 自訂欄位值 |
| output | `reason_code` | 字串 | **一律非空** |
| output | `traceable_row` | 字串 | 命中的對照表列或不寫的理由 |
| output | **`scope_note`** | 字串 | **`[S]`（在 scope 內被跳過）與 `— SKIP`（不在 scope 內）的差別**（[req:FR-F3]）。由 `parse` 解析出的 stage 行推導，**不進 `Decision`**——[req:FR-B3] 明訂它對 Status 無影響 |

> **第五個 output 於 2026-08-30T00:48:38Z 增設（reviewer iteration 3 Group B F4 Major）。** 起因：U-2 的 `Context.scope_note` 原寫「由呼叫端自 `ParsedRecord` 取得」，但 `ParsedRecord` 是本 action 的**內部值**、不跨 action 邊界，呼叫端（U-6）拿不到它——而 [req:FR-F3] 要求 `[S]`／`— SKIP` 的差別必須在受管區塊上看得見（U-2 的 R-1.2）。
>
> **這不改 [Q1=A] 的決定**：該題問的是「`Decision` 的四個欄位怎麼跨 action 邊界」，答案仍是四個獨立 output；`scope_note` 不是 `Decision` 的欄位，是本 action 額外輸出的第五個值。`Decision` 的型別、`map` 的簽章與純函式性一字未動。

**`Decision` 走四個獨立 output 而非單一 JSON**（[Q1=A]；另有第五個 output `scope_note` 不屬 `Decision`，見上）：呼叫端 `${{ steps.map.outputs.reason_code }}` 直接可用，YAML 層一眼看得出這個 action 產出什麼。`status` 的 `null` 以空字串表達——因為 `reason_code` 一律非空，「`status` 空字串」與「決定不寫」是同一件事，不引入第三種狀態。

**集合型 input 用換行分隔而非 JSON**：跳脫處理正是 [Q1=B] 的 JSON 方案被放棄的理由，同一個理由不應該在輸入側被反向套用。詳見 `domain-entities.md` §Config 的承載形式。

## 主流程

```
輸入：state_md, intents_json, record_path, Config
  │
  ├─► 步驟 1：parse(state_md, intents_json, record_path)
  │      ├─ 無 ## Stage Progress 區塊 ──────► Unparseable{missing:["stage-progress-section"]}
  │      ├─ 區塊在但零行 match（R-2.4）────► Unparseable{missing:["stage-lines"]}
  │      └─ 否則 ─────────────────────────► ParsedRecord
  │
  └─► 步驟 2：map(上一步的結果, Config)
         ├─ 輸入是 Unparseable
         │     ├─ intent_id ∈ whitelist ──► Decision{null, "", "whitelisted", …}
         │     └─ 否則 ──────────────────► Decision{null, "", "unparseable", …}
         └─ 輸入是 ParsedRecord ─────────► 走判定順序（R-3.1 → R-3.7）
                                            └─► field_value_for(Decision, Config)
```

文字 fallback：先解析，解析不出來就依白名單分成 `whitelisted` 或 `unparseable` 兩種「不寫」；解析得出來就跑七條有序判定，命中哪一條就產生對應的 `Decision`，再組出自訂欄位值。

## 步驟 1：`parse` 的演算法

1. 從 `record_path` 取 `intent_id`（目錄名），**不從內文取**。
2. `get_field` 取 `Current Stage`、`Status`、`Parked`、`Parked At Stage` 四個欄位（規則見 `business-rules.md` R-1 群）。
3. 從 `intents_json` 取該 intent 的綁定編號 → `binding`（無則 `null`）。
4. `list_stages`：切出 `## Stage Progress` 區塊，逐行套 R-2.1 的形狀。
5. 套 R-2.4 的下限檢查：零行 match 即 `Unparseable`。
6. 組出 `ParsedRecord`。

**不拋例外**。任何缺失都走 `Unparseable` 這條路——[req:FR-J3] 要求「跳過不寫」而非中止整輪，一個壞掉的 record 不得讓其餘 record 停擺。

## 步驟 2：`map` 的判定順序

七條，優先序由高至低，逐字沿用 [ad:component-methods.md]。完整條件與 `reason_code` 對照見 `business-rules.md` R-3 群。

決策樹（先到先得，命中即停）：

```
parked 非空？ ──是──► null / parked
   │否
intent_id ∈ reverse_pending？ ──是──► null / suppressed
   │否
runtime_status == "Completed"？ ──是──► Done / mapped
   │否
任一 in-scope stage 的 checkbox == "?"？ ──是──► In review / mapped
   │否
任一 in-scope stage 的 checkbox ∈ {"-","R"}？ ──是──► In progress / mapped
   │否
全部 in-scope stage 的 checkbox ∈ {" ", "S"}？ ──是──► Ready / mapped
   │否
└──────────────────────────────────────► null / undecidable
```

文字 fallback：由上而下逐條測試，第一個成立的條件決定輸出，其餘不再評估。最後一條是窮盡二分的另一半，保證總函式性（`business-rules.md` R-7；2026-08-30T06:40:39Z 前編號為 R-6，見該處對照註）。

**第 3 條先於第 4／5 條是刻意的**：`Completed` 的 record 不應因殘留的 `[?]` 而回退。這是上游的判斷，本站沿用並在此記明理由，以免下游讀到「順序看起來可以調換」。

## 步驟 3：`field_value_for` 的組值與截斷

1. 選前綴：`parked` 非空 → `parked @ `；該 stage 的 `checkbox == "S"` → `skipped `；[req:FR-B3] 的 `— SKIP` 情形 → `frozen: `；其餘 → 無前綴。
2. 組出 `<前綴><current_stage> (<intent_id>)`。
3. 若長度 > `field_max_length`：**只截 stage-slug 的尾端**，前綴與 `(<編號>)` 完整保留（R-5.1／R-5.2）。
4. slug 截到零長度仍超過上限時：**照寫**（R-5.4）。

第 4 步是刻意違反上限。理由與連帶約束（U-3 不得二次截斷）見 `business-rules.md` R-5 群。

## 錯誤處理

本單元**只有一種錯誤表達方式**：回傳 `Unparseable`，或回傳 `reason_code` 非 `"mapped"` 的 `Decision`。不拋例外、不設 exit code、不寫 stderr。

理由是呼叫端的失敗語意由 [ad:services.md] 定死：機制的正常判斷（`parked`／`unparseable`／`suppressed`／`undecidable`／`whitelisted`）**不使 workflow 紅燈**，只有 `ExternalError` 與 `Rejected` 紅燈——而那兩者都不是本單元產得出來的（本單元不碰外部系統）。**若本單元以非零 exit code 結束，就會讓一個「機制正常判斷」的情形變成紅燈**，直接違反 [US:S-8 AC 1] 的適用前提。

`phases/construction.md` 要求「錯誤必須被表面化，不得靜默失敗」——本單元的表面化形式是 `reason_code` 與 `traceable_row`，兩者都非空、都會被寫進受管區塊與對帳報告，不是吞掉。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| `Parked` 欄位缺席 | 視為未暫停 | R-1.3；現況 record 就是這樣 |
| `Parked` 欄位存在但空 | 視為未暫停 | R-1.2 ＋ `domain-entities.md` 的三態壓二態 |
| `## Stage Progress` 有 `Per unit: [TBD]` | 靜默略過該行 | R-2.3；這是**現在就存在**的行 |
| 全部 in-scope stage 都是 `[ ]` | `Ready` | R-3.6 |
| in-scope stage 有 `[S]` 其餘 `[ ]` | **是** `Ready`——`[S]` **不**算動過 | R-3.6 的「動過」定義（iteration 1 後更正）。與其 `— SKIP` 孿生 record 得到相同 Status，[req:FR-B3]／[US:S-2 AC 5] 成立 |
| record 同時 `Parked` 且 `Completed` | 實務上不可達 | `handlePark` 在 `Status == "Completed"` 時拒絕（實測 `aidlc-state.ts:830-832`） |
| fixture record | **不會被選中** | [ad:component-methods.md] §C-2「intent 選取的邊界」——兩條路徑都以 `intents.json` registry 為來源 |

## 與上游的對應

演算法來源：[ad:component-methods.md]（判定順序、`get_field` 語意、欄位格式）、[ad:components.md]（元件職責與零 I/O）、[ad:services.md]（失敗語意、狀態只存在兩處）、`requirements.md`（FR-B 對照表、FR-G3、FR-J3／J4／J5／J6）、[ug:unit-of-work.md]（U-1 的交付與完成判準）、[ug:unit-of-work-story-map.md]（本單元承載 S-2 與 S-3 的哪些 AC）。

本檔對上游的補充是**已標出的四個缺口**中屬於本單元的兩個落點：`Config` 的欄位定義（F-1）與 `reverse_pending` 的資料進入路徑（F-2，[Q2=A] 裁定）。另兩項不落在本單元——F-3 指派回上游 `component-methods.md`、F-4 指派 U-6 的 functional-design，兩者的完整記載見 `functional-design-questions.md`。判定順序、欄位格式、`get_field` 行為**一條未改**。

> 先前此處寫「唯二補充是兩個缺口」，在 F-3／F-4 加入後即為過期計數（reviewer iteration 2 Major）。

## Review

**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-29T11:54:08Z
**Iteration:** 3（iteration 2 修正的驗證輪）
**Verdict:** READY

iteration 2 的 1 Critical／1 Major／3 Minor 中，五項修正全數落地且無一引入新 Critical：Critical #1（F-2 的 sync-state.json 殘留）、Major（缺口計數殘留「兩項」）、Minor（表格被夾斷）、Minor（溯源清單漏 S-3 AC4）四項**完整解決**；F-4 的新增（把「誰讀反向 PR 算 reverse_pending」標成缺口並指派 U-6）**裁定與落點皆正確**，經對照 `unit-of-work.md` 的 U-6／U-8 條目與 `services.md` S-A 逐字核對成立。本輪新找到 **1 Major**（F-4 的落點是 CONDITIONAL 且尚未執行的 stage，卻未依 `project.md`（`units-generation:260822-ug-L2`）附上「該 stage 可能被 skip」的風險與指定確認人，而本文件自己引用的正是同一條規則）與 **2 Minor**（iteration 2 的 Minor #4／R-6 property 仍未補；`domain-entities.md:98` 的「只有兩項」在同一份文件兩度「兩項→四項」更正之後仍缺乏歷史框定，讀起來像未同步的殘留）。0 Critical、1 Major、2 Minor，未達「>2 Major 或任何 Critical」的 NOT-READY 門檻，判定 **READY**——但 Major #F4-1 建議在下一個接觸 F-4 的動作（無論是本站小修還是 U-6 functional-design 開站前）補上。

### 五項修正的逐項判定

1. **Critical #1（F-2 的 `sync-state.json` 殘留）— 完整落地**。`functional-design-questions.md:48` 原本逐字保留的「那份狀態在 `<record>/sync-state.json`……」一句已從缺口說明本文移除，第 2 條判定的來源改寫為「三個來源都不含反向同步狀態」（不再點名任何具體位置），並在 `:52` 插入一段獨立的更正 blockquote：明白宣告「原文寫『那份狀態在 `<record>/sync-state.json`……』——那是錯的」，指向 `unit-of-work.md` 的 U-8 實作註記為正確依據，並自陳「此處不是『作答當下的紀錄』……寫錯就該改，不受『不改寫題幹與選項』那條保護」——這正是 iteration 2 recommendation 要求的處置形狀（更正、不是保留）。全檔（含 `business-rules.md`、`domain-entities.md`）逐一 `grep "sync-state.json"` 複查：僅存的 5 處提及全部是（a）`business-rules.md:50` 與 `domain-entities.md:66`／`:83` 的既有正確更正／既有事實陳述、（b）`functional-design-questions.md:52` 的新更正 blockquote 本身、（c）Q2 選項 A 本文與 Revision 1 表——兩者依規則不可改寫，是作答當下的歷史紀錄，性質與已判定不成立的 F-2 缺口說明不同。**沒有任何一處殘留把 `sync-state.json` 當作 `reverse_pending` 現行來源陳述**。

2. **Major（缺口計數殘留「兩項」）— 完整落地**。`functional-design-questions.md:37` 已改為「**四項**（reviewer iteration 2 Major 後更正——先前寫『兩項』，是 F-3 加入後未同步的計數；F-4 為本輪新增）」，`:39` 新增「兩種性質不可混同：F-1／F-2／F-4 是上游的缺漏……F-3 是對已核可約束的鬆綁……」的分類說明，解掉 iteration 2 抓到的「前言自稱兩項、內文卻有三個小節且 F-3 自陳性質不同」的自相矛盾。`business-logic-model.md:127` 同步改為「已標出的**四個缺口**中屬於本單元的兩個落點……另兩項不落在本單元——F-3 指派回上游 `component-methods.md`、F-4 指派 U-6 的 functional-design」，`:129` 以歷史框定的 blockquote 保留舊主張作對照（「先前此處寫『唯二補充是兩個缺口』，在 F-3／F-4 加入後即為過期計數（reviewer iteration 2 Major）」）。兩處「先前寫『兩項』／『唯二補充』」的殘留都明確標注為「先前……已更正」，屬合法的歷史引用而非疏漏殘留——與被推翻的 Q2 本文／`[Answer]` 保護理由一致（記錄「作答或判定當下寫了什麼」，不是對現況的陳述）。

3. **F-4 新增（誰算 `reverse_pending`）— 裁定與落點正確，但缺口本身的處置形狀不完整**。`functional-design-questions.md:67-77` 新增「缺口 F-4：誰負責算出 `reverse_pending`？」，主張 U-8「擁有的是**產生**反向 PR」、「**讀取**開啟中的反向 PR 並映射為 intent id 集合，是**正向同步 workflow（U-6）**在每一輪開始時要做的事，而 U-6 的擁有清單裡沒有它」。對照passed contract `unit-of-work.md`：U-8 條目的「擁有」欄（`:126`）確為「[ad:S-C] 的排程觸發、看板讀取、雜湊比對、**開 PR**、逐 intent 歸屬判定、防迴圈三道防線」——只有產出 PR，沒有讀取別的 PR；U-6 條目的「擁有」欄（`:103`）為「[ad:S-A] 的觸發設定、registry 驅動的選取與分流……分支界 concurrency group……[aidlc-sync] 的兩道整輪層級自我排除」——**確實沒有**「讀反向 PR」這一項。`services.md` S-A 的生命週期欄（`:21`）「單次執行掃過 `intents.json` registry 內的全部 intent，逐一分流」確認 S-A 是單次執行、內部逐 intent 迴圈的模型，與 [Q2=A]「迴圈前算好一次」的裁定架構相容；S-A 描述行文本身沒有指派「讀反向 PR」這個步驟，僅在 S-C 段落的「對 S-A 的影響」列描述了**效果**（暫停覆寫）而未指派**機制**——確認 F-4 指出的缺口是真實、目前無主的，U-6（不是 U-8、也不是與此無關的 U-7）是唯一合理落點。`:77` 也誠實記載「本項與 F-3 的處置形狀相同，但先前漏了……同一輪內對兩個同型問題採不同標準，是不一致而非判斷差異」，回應了 iteration 2 對這個不一致的點名。**但**`project.md`（`units-generation:260822-ug-L2`）除了「標出缺口、寫明擋住哪條 AC、指派落點」之外，還有一條「附帶必做的檢查」：**若指派的目標 stage 為 CONDITIONAL，必須額外註明「該 stage 可能被 skip」的風險並指出誰要確認，否則指派會無聲落空**——而該規則舉的範例正是「指派 functional-design 增設 `undecidable: [intent_id]`……而 functional-design 恰好是 CONDITIONAL 且 per-unit」，與 F-4 的情境（指派到 **U-6 的 functional-design**）逐字同構：`.claude/aidlc-common/stages/construction/functional-design.md:4` 確認 `execution: CONDITIONAL`，U-6 尚未走過自己的 functional-design（本 intent 目前只有 U-1 在跑這一站），故這是一個**真實、未來、尚待判定**的 skip 風險，不是已執行完畢的既成事實。F-4 的三個小節（擋住／落點／不逕自指派）**完全沒有**這句必做的風險註記與確認人指名——這與 F-3 不同：F-3 的落點是**已經執行完畢**的 `component-methods.md`（application-design 早已跑完，通過三輪 reviewer），沒有「該 stage 未來被 skip」的風險，`:77` 那句「處置形狀相同」因此在這一個面向上不成立。這是本文件自己引用的 MANDATED 規則的一次不完整套用，且風險是實質的：若 U-6 的 functional-design 被判定為「簡單邏輯變更」而 skip，`Config.reverse_pending` 的算法就永遠沒有人實作，[req:FR-G3]／[US:S-6 AC 3] 會在生產環境靜默失效（依本單元自己的失敗語意設計，`suppressed` 之類的機制判斷本就不觸發紅燈，這個落空不會被任何既有 CI 閘門攔下）——見下方新缺陷 #F4-1。

4. **Minor（表格被夾斷）— 完整落地**。`functional-design-questions.md:20-33` 的「已由上游定案、本站不重問」表現為單一連續表格（`:22-31`，表頭＋分隔列＋7 列資料，逐字比對即為移除 50 字元上限那列後的既有 7 列，無新增無遺漏），移除 50 字元上限的說明 blockquote 已移到整個表格之後（`:32`），不再插在表格中間。以「連續 `|` 起始行區塊」規則重新掃描四份文件的全部表格（見下方「跨檔一致性與 markdown 完整性」），未發現任何斷裂或缺表頭的表格延續。

5. **Minor（溯源清單漏 S-3 AC4）— 完整落地**。`domain-entities.md:96` 現在明列「**另有三條 partial**——S-2 AC 4 與 S-3 AC 6 的**判定**屬本單元、清單成員身分屬 U-7（見 `business-rules.md` R-4 群與上游標出的缺口 G-1）；**S-3 AC 4**（分岔仍寫入並開 issue）的判定屬本單元、開 issue 屬 U-5」。對照 passed contract `unit-of-work-story-map.md:26`——「S-3 | AC 4（分岔仍寫入並開 issue）| U-1 ＋ U-5」——逐字相符；`:99` 的「S-2 的 AC 1–3、5–10、14、15」與story-map 的「AC 1–3、5–7、9、10、14、15」＋另列的「AC 8」合併後的連續區間一致（AC8 落在 5–10 之間，合併無誤）；「S-3 的 AC 3、5 完整屬本單元」對照 story-map 的 AC3／AC5 行亦相符。三條 partial（S-2 AC4、S-3 AC4、S-3 AC6）現在全部命名，圓括號配對正確（三組開合共 3 對，逐字核對平衡）。

### 修正引入的新缺陷

| # | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| F4-1 | Major | `functional-design-questions.md:67-77`（對照 `project.md` `units-generation:260822-ug-L2`、`.claude/aidlc-common/stages/construction/functional-design.md:4`） | **F-4 指派到一個 CONDITIONAL 且尚未執行的 stage（U-6 的 functional-design），卻缺少本文件自己引用的規則所要求的「該 stage 可能被 skip」風險註記與指定確認人。** `project.md`（`units-generation:260822-ug-L2`）明文：「若指派的目標 stage 為 CONDITIONAL，必須額外註明『該 stage 可能被 skip』的風險並指出誰要確認，否則指派會無聲落空」，且該規則舉的例子（指派到「恰好是 CONDITIONAL 且 per-unit」的 functional-design）與 F-4 的情境逐字同構。`functional-design.md:4` 確認該 stage 確為 `execution: CONDITIONAL`；U-6 在本 intent 中尚未執行過自己的 functional-design（此為真實、未來的風險，非既成事實）。F-4 的「擋住」「落點」「不逕自指派」三小節全文沒有一句提及「U-6 的 functional-design 可能被判定為簡單變更而 skip」，也沒有指出誰要在 U-6 進站前／進站時確認這件事沒有被漏接。相對地，F-3 的落點（`component-methods.md`）是application-design 早已執行完畢的既有文件，沒有「未來被 skip」的風險，`:77`「本項與 F-3 的處置形狀相同」的自我比對因此在這一點上不成立。若 U-6 的 functional-design 真的被 skip，`Config.reverse_pending` 的計算邏輯會永遠無人實作，[req:FR-G3]／[US:S-6 AC 3] 在生產環境靜默失效——且依本單元自己的失敗語意設計，這類機制判斷不觸發紅燈，不會被既有 CI 閘門攔下。 | 在 F-4 小節補一句風險註記（例如：「若 U-6 的 functional-design 因『簡單邏輯變更』被判定 CONDITIONAL-skip，本缺口會無人接手；建議 U-6 進站的 CONDITIONAL 適用性判定必須明確把『讀反向 PR → reverse_pending』列入 complex business logic 的理由，或由 delivery-planning／Bolt 規劃階段的負責人在 U-6 開站前確認本缺口已被接住」），並指名誰要做這個確認。 |
| F4-2 | Minor | `domain-entities.md:98` | **「本檔新增而上游沒有的只有兩項」在同一份設計套件已對「兩項」計數兩度更正（`functional-design-questions.md:37`、`business-logic-model.md:129`）之後，仍以現行語氣（無「先前」框定）陳述，讀起來像未同步的殘留，即使實際內容可能仍然正確。** 這句話統計的是「本檔」（domain-entities.md）自己新增的項目，範圍與系統層級的「四項缺口」計數不同——`Config` 的欄位（F-1 的落點）與 `missing` 的 `"stage-lines"` 值（[Q3=C] 的連帶）確實是本檔獨有的兩項新增，F-3 落在 `business-rules.md`、F-4 落在其他單元，兩者都不在本檔——就數字本身而言站得住。但本檔的 `Config` 表（`:63-68`）同時是 F-2（`reverse_pending` 的資料進入路徑）的部分落地位置（`business-logic-model.md:127` 明文「`reverse_pending` 的資料進入路徑（F-2……）」屬本單元的落點之一），`:98` 卻只點名 F-1、完全未提 F-2，讀者無法從這句話判斷「F-2 沒有落在本檔」是刻意的範圍界定，還是又一次遺漏——考量本輪與上一輪已在同一份文件裡三次犯過同型的計數殘留（`project.md` `units-generation:rev1-L1`／`units-generation:260822-ug-L1` 記載的正是這個失誤形狀），這裡的沉默本身構成可疑之處。 | 把 `:98` 改為明確排除式陳述，例如「只有兩項是本檔獨有的新增：`Config` 的欄位（F-1 的落點）與 `missing` 的 `"stage-lines"` 值；F-2 雖然部分落在本檔的 `Config.reverse_pending` 欄位，但其判定邏輯落在 `business-rules.md` R-3.2，不重複計入本檔」，或至少加一句「F-2 的資料承載雖然也在本檔的 Config 表，但其缺口本體記在 `business-rules.md`」，消除「有沒有漏算 F-2」的疑慮。 |
| — | 已解決（不再列入） | `functional-design-questions.md:48`／`:37`；`business-logic-model.md:127`；`functional-design-questions.md:20-33`；`domain-entities.md:96` | iteration 2 新缺陷 #1（Critical，F-2 殘留）、#2（Major，缺口計數）、#3（Minor，表格斷裂）、#5（Minor，溯源清單）——四項本輪逐一核對後確認完整解決，見上方判定 1、2、4、5。 | — |
| — | 未解決（延續） | `business-rules.md:89-95` | iteration 2 新缺陷 #4（Minor，R-6 property 未補「`[S]` 與 `— SKIP` 互換不變性」）——本輪的五項修正未觸及 R-6 段落，`:89-95` 仍是修正前的既有敘述，這條 Minor 未被本輪處理，非本輪引入、亦非本輪解決，予以延續列管。 | 同 iteration 2 recommendation：在 R-6 段落補一句具名 property。 |

### 跨檔一致性與 markdown 完整性

- **markdown 表格完整性**：對四份檔案的全部 `^\|` 起始行重新逐行掃描（見上方指令輸出），確認每一段連續的表格列都緊接表頭與分隔列，沒有任何表格被空行或非表格文字從中截斷——iteration 2 抓到的 `functional-design-questions.md:20-33` 斷裂已修復（現為 `:22-31` 單一連續表格），本輪未發現新的斷裂。
- **七條判定順序與 `reason_code` 值域**：`business-logic-model.md` 決策樹（`:75-88`）與 `business-rules.md` R-3 表（`:38-46`）逐字一致，本輪未被任何修正觸及；六個 `reason_code` 值（`parked`／`suppressed`／`mapped`／`undecidable`／`whitelisted`／`unparseable`）在全部四檔中出現處對應一致。
- **`Config` 欄位與 action I/O 清單**〔iteration 3 更正：output 已由 4 增為 **5**（新增 `scope_note`），下方數字為當時的盤點〕：`business-logic-model.md` 介面表（`:19-31`）為 **7 個 input**（`state_md`、`intents_json`、`record_path`、`record_root`、`field_max_length`、`whitelist`、`reverse_pending`）與 **4 個 output**（`status`、`field_value`、`reason_code`、`traceable_row`）——重新逐行點算，`domain-entities.md` 的 `Config` 表（`:63-68`，4 欄位）與承載形式段（`:72-79`，量／集合分兩類、共 4 個 Config 衍生 input，加上 3 個非-Config input＝7）完全對得上。（iteration 2 review 先前的跨檔一致性小節誤記為「四個 input」，本輪核對後為 7，已在本次改寫中更正，不影響先前判定的實質結論。）
- **`[S]` 語意**：`domain-entities.md`（`:32-35`）、`business-rules.md`（R-3.6 與 `field_value_for` 前綴邏輯）、`business-logic-model.md`（決策樹與邊界情形表）三處對「`[S]` 不算動過但差異仍需可見」的表達一致，本輪未被觸及、無新矛盾。
- **F-1／F-2／F-3／F-4 缺口編號**：`functional-design-questions.md:37/39` 與 `business-logic-model.md:127/129` 現在對「四項、兩種性質」的計數與分類一致；`domain-entities.md:59` 的「（缺口 F-1 的落點）」與 `:98` 的「兩項」共存但範圍不同（見新缺陷 #F4-2，判定為可疑但非確定錯誤的 Minor）。
- **G-1 交叉引用**：`domain-entities.md:96` 引用的「上游標出的缺口 G-1」經核對 `unit-of-work-story-map.md:99` 存在且內容相符（`ReconcileReport` 缺 `undecidable` 欄位），非捏造引用。

### Attempted refutations that did not hold

- **嘗試主張 F-4 的機制（U-6 在自己執行期內讀取「當下開啟中的反向同步 PR」的 diff）與 `services.md` S-A 的「為什麼不用事件 diff」原則矛盾**：查證後不成立，理由與 iteration 2 對 reverse_pending 來源機制的同一項查證相同——S-A 的「不用事件 diff」原則管的是**選取**（決定要處理哪些 record，`services.md:21` 明文「不是本次事件的 diff」），F-4 讀的是**另一個**、當下開啟中的反向 PR 的 diff，只用於建構 suppression 集合，不影響選取（選取仍是 registry 驅動）。兩者是不同的 diff、不同的用途，本輪重新核對後結論不變。
- **嘗試主張 F-4 的落點應該是 U-8 而非 U-6**：查證 `unit-of-work.md` 的 U-8「擁有」欄（`:126`）與 U-6「擁有」欄（`:103`）逐字後不成立——U-8 只擁有「開 PR」（產出），沒有任何「讀取」職責；U-6 才是需要在每輪開始前知道「哪些 intent 要暫停」的消費端。U-7（對帳）也不是候選——U-7 的擁有清單（排程、`ReconcileReport`）與讀取開啟中的反向 PR 無關。F-4 指派 U-6 正確。
- **嘗試主張 `domain-entities.md:98` 的「只有兩項」與 `functional-design-questions.md:37` 的「四項」直接矛盾、應同步改寫**：不完全成立——兩者統計範圍不同（前者是「本檔獨有新增」的局部計數，後者是「本單元發現的缺口總數」的系統計數），數字本身不需要相等。但範圍不同不代表沒有問題：`:98` 完全沒提及本檔同時是 F-2 的部分落地位置，這個沉默本身是可疑的（見新缺陷 #F4-2）——判定為 Minor 而非「直接矛盾」，因為找不到任何一句話literal 上與「四項」衝突，只有「該不該提及 F-2」的完整性疑慮。
- **嘗試在 R-3.6／R-6 之外，重新對整個七條判定序列（含未受本輪修正觸及的 R-3.1～R-3.5、R-3.7）尋找因為 F-3／F-4 的新增而產生的新邊界案例（例如 `reverse_pending` 集合與 `parked` 同時命中時的優先序是否仍然明確）**：未找到新問題。R-3.1（`parked`）與 R-3.2（`reverse_pending`）的優先序在本輪修正前後逐字未變（`parked` 仍優先於 `suppressed`），F-3／F-4 均未修改判定順序本身（F-3 動的是 R-5 群的截斷規則、F-4 動的是 R-3.2 輸入來源的**指派**而非**判定邏輯**），七條規則的互斥與窮盡性不受影響。
- **嘗試主張本輪對 F-4 的 Major finding（CONDITIONAL-skip 風險未註記）應升級為 Critical，因為它涉及生產環境的靜默失效**：判定不成立，維持 Major。理由：本單元（U-1）自身的設計不因此變得不可實作——一個開發者仍可完整、無歧義地把 U-1 build 出來，不需要回頭問任何問題；風險落在**跨單元的流程治理**（U-6 未來是否會漏接這個指派），屬「會造成顯著重工／需要後續動作」的 Major 定義，而非「導致本單元實作或執行期失敗」的 Critical 定義。且 `project.md`（`application-design:c4`）只點名「repairs 本身引入的 Critical」不可豁免，未把同類 Major 排除在正常的 ≤2 Major 容忍度之外。
