# Business Logic Model — U-2 受管區塊渲染與雜湊

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-2-managed-block · kind: library -->

## 這個單元在做什麼

把一個 `Decision` 變成 issue body 裡的一段**受管區塊文字**，並提供把它讀回來與算雜湊的能力。零 I/O——不讀 issue、不呼叫 API，只吃字串吐字串（與 U-1 同，[ad:components.md] 的呈現層（[ad:components.md] 把 C-6 列為呈現層，不是純函式層——先前誤植）約束）。

三個方法（簽章逐字沿用 [ad:component-methods.md] §C-6）：

| 方法 | 簽章 | 角色 |
| --- | --- | --- |
| `render` | `(Decision, Context) -> string` | 產生區塊。`Context` 的三欄定義見 `domain-entities.md`（上游未定義它，本單元承接的契約缺口）；`rejection_notice` 非 `null` 時的渲染規則為 `business-rules.md` 的 R-1.5 |
| `parse` | `(issue_body) -> Block \| null` | 取出既有區塊 |
| `content_hash` | `(Block) -> sha256` | 防迴圈第一道（[req:FR-G4]） |

## 資料流

```
Decision（U-1 產出，四個 output）──┐
scope_note（U-1 第五個 output）───┤
decided_at（U-6 取本輪時刻）──────┼─► Context ─┐
rejection_notice（U-6 R-6.2b）───┘            ├─► render ─► 區塊文字 ──► U-3 write_body ─► issue body
                                    Decision ─┘

issue body（U-3 read_item）──► parse ─► Block ─► content_hash ─► sha256
                                    └► null（無標記／版本不明／版本過新）
```

文字 fallback：`Decision` 的四欄與 `Context` 的三欄（`scope_note`／`decided_at`／`rejection_notice`）一起進 `render`，產出區塊文字，由 **U-3 的 `write_body`** 寫進 issue body；日後同一段文字被 `read_item` 取回、`parse` 成 `Block`、`content_hash` 算出 sha256，該值即 U-8 反向比對的基準。

> **這張圖於 2026-08-30T00:48:38Z 兩處更正（reviewer iteration 3，Group A C-3／Group B F1 與 F7）。**
>
> 1. **寫者先前不存在。** 圖上原寫「（U-3 寫進 issue body）」，但 U-3 的六個方法（`read_item`／`create_item`／`write_status`／`write_field`／`ensure_field`／`read_issue_state`）**無一寫 issue body**——`write_field` 寫的是 Projects v2 自訂欄位，[ad:component-methods.md] §自訂欄位格式明訂它「長度上限 50 字元」且「完整敘述一律在受管區塊」，上游把兩者定義為不同的東西。後果是 `read_item` 回傳的 `managed_block_hash` 恆為 `null`，U-8 拿 `null` 比 `null` ⇒ **反向同步永遠不觸發且無任何紅燈**。已由 **ADR-0015 §11** 增設 `write_body: (binding, block_text) -> WriteResult`。
> 2. **`Context` 先前不在圖上。** 它於 2026-08-29T23:42:35Z 才被定義（`domain-entities.md`），但本檔與 `functional-design-questions.md` 未同步——與 iteration 2 對本單元的唯一 Major 同型復發。

文字 fallback：`render` 把判定與情境組成一段文字；`parse` 是它的反向，讀不出來就回 `null`；`content_hash` 對 parse 出來的結構算雜湊。三者之間沒有共享狀態，每一次呼叫都獨立。

## `render` 的組成序列

1. 寫入版本標記（`format_version`，見 `domain-entities.md` 的「為什麼版本要進區塊」）。
2. 依 `Decision.status` 是否為 `null` 走兩支之一：
   - 非 `null` → 寫 Status 與 `traceable_row`。
   - 為 `null` → 寫 `reason_code` 的原因類別與 `decided_at` 的 ISO 8601 時間戳。
3. 寫 `Context.scope_note`（`[S]`／`— SKIP` 的差別，[req:FR-F3]；值域與推導見 U-1 的 R-6 群）。
4. **`Context.rejection_notice` 非 `null` 時，寫一段「該次人工改動未被採納」與其 `closed_at`**（R-1.5，[US:S-6 AC 5]）；為 `null` 時不寫該段。
5. 附兩段固定說明（OOS-2 的不自動關閉、「自訂欄位為空的 item 不由本機制維護」）。

第 2 步的二分是窮盡的——`Decision` 的 `status` 與 `reason_code` 恰有一個表達「有寫」、另一個一律非空（[ad:component-methods.md]），所以不存在第三支。**`decided_at` 只出現在第 2 步的 `null` 支**，這是 [US-OQ-3] 必載內容的字面（「……**或**機制決定不寫的原因類別與 ISO 8601 時間戳」），亦即 `Block.decided_at` 的值域含 `null`。

> **第 3〜5 步於 2026-08-30T01:31:09Z 補上（reviewer iteration 4 Group B m-2）**：`Context` 與 R-1.5 於 iteration 3 引入後，本檔的組成序列仍停在四步且無告示，與 `business-rules.md` 的 R-1.5、`domain-entities.md` 的 `Context`／`Block` 表不一致。原第 3 步只寫「`[S]`／`— SKIP` 的差別」而未指名它來自 `Context.scope_note`。

## `parse` 的版本分派

```
讀版本標記 ─┬─ 缺失／不可解析 ──────────► null
            ├─ 高於當前 FORMAT_VERSION ──► null（保守：不用舊規則猜新格式）
            └─ 在已知版本集合內 ─────────► 套用該版本的解析器 ► Block
```

文字 fallback：先看版本，再決定用哪一套解析規則；三種讀不出來的情形全部回 `null`，不拋例外。規則與各自的理由見 `business-rules.md` R-3 群。

> **三條路徑回的是同一個 `null`，呼叫端分不出來（reviewer iteration 1 Critical；本節於 2026-08-29T16:14:22Z 補上揭露）。** 上圖看起來像三種不同的結果，實際上型別只有 `Block | null`——「完全沒有標記」與「版本高於當前渲染器」對呼叫端**完全一樣**。而已承諾的呼叫端行為是「不得重複附加區塊——`parse` 先跑再 `render`」，於是 `null` 最自然的實作是「沒偵測到區塊 ⇒ 渲染一個寫進去」。
>
> **後果**：R-3.4 宣稱的「該 item 不被覆寫」**目前不成立**。缺口與兩條修法已在 `business-rules.md` 的 R-3.4 下標出並指派（Bolt 1 gate）。**在修正落地前不得預設該保護已生效。**

## 格式契約的互鎖機制

ADR-A6 把這件事**指派給本 stage**：設計一個機制（而非流程紀律）使格式變更與重新基準化不能脫鉤。[Q1=C] 定案為三道 CI 互鎖（快照一致、版本等於登錄表末筆、末筆含非空的基準化說明），完整規則與其**天花板**見 `business-rules.md` R-4 群。

要點在此重述一次，因為它是本單元最重要的設計決定：**三道互鎖保證作者無法「忘記」重新基準化，但不保證他「做了」。** 唯一能保證做了的形狀（格式指紋 ＋ 自動重新基準化）會把 ADR-A6 的單一 PR 遷移改成逐 item 惰性遷移，屬對已核可 ADR 的實質變更；取捨已由人裁定。

## 錯誤處理

與 U-1 同形：**本單元不拋例外、不設 exit code**。唯一的「失敗」表達是 `parse` 回 `null`，其語意是「這個 issue body 沒有本機制認得的受管區塊」——不是錯誤，是一個正常的判定結果（該 item 不受管）。

理由與 U-1 相同：[ad:services.md] 定死「機制的正常判斷不使 workflow 紅燈」，只有 `ExternalError` 與 `Rejected` 紅燈，而本單元不碰外部系統，產不出那兩者。若以非零 exit code 結束，會把一個正常判定變成紅燈。

`phases/construction.md` 的「錯誤必須被表面化」在此的落點是 `null` 這個明確回傳值與呼叫端對它的分支處理，不是吞掉。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| issue body 完全沒有標記 | `parse` 回 `null` | R-3.1 |
| 有標記但版本標記壞掉 | `parse` 回 `null` | R-3.2 |
| 區塊由更新版本的機制寫入 | `parse` 回 `null`。**「不被覆寫」目前不成立**——呼叫端無法把它與「完全沒有標記」分辨開，見上方揭露與 `business-rules.md` R-3.4 的指派 | R-3.4（保守選擇，**無告警**；且保護本身待修） |
| 兩次判定語意相同、時間不同 | 雜湊不同，但**不會重寫**（上游「有漂移才寫」） | R-2.3 的隱含依賴 |
| 純外觀的格式調整且 round-trip 後 `Block` 逐欄相同 | 雜湊**不變** | `content_hash` 吃 `Block` 而非字串 |
| `[S]` 與 `— SKIP` 只差在這一點的兩個 record | Status 相同（U-1 的 R-3.6）、區塊內容**可區分**（本單元 R-1.2） | [req:FR-B3]／[req:FR-F3] |

## 與上游的對應

方法簽章、必載內容與錯誤處理引自 [ad:component-methods.md] §C-6；純函式層與零 I/O 約束引自 [ad:components.md]；失敗語意引自 [ad:services.md]；格式契約與本站的設計指派引自 [ad:decisions.md] ADR-A6；FR-F3／FR-G4 引自 `requirements.md`；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-2；承接的 AC（S-4 AC 6、S-6 AC 6）引自 [ug:unit-of-work-story-map.md]。

**本檔對上游的補充**：`Block` 的欄位結構、`format_version` 的內嵌與 `parse` 的版本分派（三者皆為上游只給簽章未給結構之處），以及 [Q1=C]／[Q2=A] 兩項裁定的落地形式。方法簽章、必載內容、防迴圈三道防線**一條未改**。

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:08:58Z
**Iteration**: 1

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| 1 | Critical | `business-logic-model.md:70`、`business-rules.md:38,40`（對照 `component-methods.md:138`「`parse` \| `(issue_body) -> Block \| null`」、`services.md:25`「不得重複追加受管區塊（C-6 的 `parse` 先於 `render`）」、`decisions.md` ADR-A6） | **R-3.1（無標記）與 R-3.4（有標記但版本高於當前渲染器）在 `parse` 的型別層面完全不可區分——兩者都回傳同一個 `null`，但本檔宣稱兩者需要不同的呼叫端行為，而這個行為差異無法從回傳值推導。** `business-logic-model.md:70` 的邊界情形表明文斷言：「區塊由更新版本的機制寫入 → `parse` 回 `null`，**該 item 被當作不受管、不被覆寫**」；`business-rules.md:40` 重申：「回 `null` 使該 item 被當作不受管，**機制不會覆寫它**」。但 `parse` 的簽章（`component-methods.md:138`，本檔逐字沿用、`domain-entities.md:26` 亦重申）是 `(issue_body) -> Block \| null`——R-3.1（issue body 完全沒有標記，`business-rules.md:35`）與 R-3.4 回傳的是**同一個** `null` 值，型別上沒有第三種結果可供呼叫端分辨「這是全新、該渲染」還是「這是他人較新版本、不該覆寫」。而呼叫端（正向同步 S-A）的冪等機制**已由已核可的 `services.md:25` 明文指定為「`parse` 先於 `render`」**——即用 `parse` 的回傳值決定要不要（或如何）寫入。在這個唯一已知的呼叫端邏輯下，`null` 的最自然實作是「未偵測到既有區塊 ⇒ 呼叫 `render` 並寫入」，這正是 R-3.4 想要避免、但實際會發生的行為：對一個已有（僅是版本較新而讀不懂的）區塊的 issue **附加第二個區塊**，而非「不被覆寫」。同一個歧義在反向同步（S-C）側更嚴重：ADR-A6（`decisions.md`）把「改格式不重新基準化 ⇒ 下一輪反向同步把全部受管 item 誤判為人為變更 ⇒ 巨大反向 PR」列為「本設計最危險的單一失誤模式」，而 S-C 的雜湊比對防線（[req:FR-G4]）同樣要呼叫 `parse` 取得 `Block` 才能算雜湊——若 `parse` 對「未來版本」與「真的沒有標記」一樣回 `null`，S-C 沒有依據能把前者判為「不該比對、不該開 PR」而非「偵測到人為變更、開 PR」，這正是 ADR-A6 明文列為最危險情境的觸發路徑之一，而 R-3.4 聲稱自己是為了**避免**這個情境而做的「保守選擇」。**可達性**：這不是罕見角落案例——`services.md:22`／`components.md:106` 明文本機制的正向同步觸發條件是「push（**任一分支**，含 `danniel/**`）」，即任何開發分支的每次 push 都會即時把該分支當下的渲染格式寫進**真實**看板（Project #16，非測試看板）；只要一次格式變更（bump `FORMAT_VERSION`）的開發分支曾推送過，而 `ut` 尚未合併該變更（或該變更之後被 `還原`／revert——`team.md` 明文允許的 commit type），`ut` 上執行的舊版渲染器就會在下一輪遇到自己讀不懂的新版區塊。這使 R-3.4 的情境成為常規開發流程（分支開發、還原）下的常見路徑，不是需要極端條件才觸發的邊界。 | 在本站（`parse` 的型別設計屬於本站職權範圍，`kind: library`、零 I/O、純函式層設計）解決型別層的不可區分性，而非把它留給尚未執行的下游 stage（U-6／U-8 的 functional-design）猜測呼叫端行為。兩個方向皆可：(a) 讓 `parse` 回傳一個能區分「無標記」與「有標記但無法解析（含版本過新）」的第三態（例如 `Block \| Absent \| Unrecognized`，或至少讓 `Unrecognized` 攜帶「偵測到標記但版本 X 高於當前 Y」的資訊），使呼叫端能依此分流；或 (b) 明確定義並公開一個獨立於 `parse` 的輕量介面（例如 `has_marker(issue_body) -> bool`，只做字串層的標記存在性判斷，不做版本解析），讓呼叫端在 `parse` 回 `null` 時能另外呼叫它以分辨「全新」與「有標記但讀不懂」。無論哪一個，本檔與 `business-rules.md` 的 R-3.4 描述都需要同步改寫：「不被覆寫」不能只是 `parse` 回 `null` 的自然推論，必須明確寫出呼叫端要用什麼機制達成它。 |
| 2 | Minor | `domain-entities.md:18`（對照 `component-methods.md:28`） | `domain-entities.md:18` 稱「`status` 與 `reason_category` 恰有一個非 `null`——這直接對應 [ad:component-methods.md] 的『`reason_code` 一律非空』」，但兩者語意不同：`component-methods.md:28` 的「`reason_code` 一律非空」指的是上游 `Decision.reason_code` **在任何情況下都非空**（含 `status` 非 `null` 時，`reason_code = "mapped"`）；而 `Block.reason_category` 依 `domain-entities.md:14` 的定義是「`status` 為 `null` 時的原因類別；**否則 `null`**」——即 `status` 非 `null` 時 `reason_category` **是** `null`，與上游「一律非空」字面相反。實際依據是 `business-rules.md` R-1.1（受管區塊只在「不寫」時才需要顯示原因類別，屬渲染層的呈現取捨），不是 component-methods.md 那句話的直接推論；「直接對應」一詞誤導了引用關係。 | 把 `domain-entities.md:18` 的來源改為 R-1.1（受管區塊必載內容的呈現規則），而非把它寫成「直接對應」`component-methods.md` 的「`reason_code` 一律非空」——後者描述的是 `Decision` 這個不同型別的性質。 |
| 3 | Minor | `business-logic-model.md:7`（對照 `components.md:31,84`） | 稱「零 I/O……（與 U-1 同，[ad:components.md] 的純函式層約束）」，但 `components.md:31` 明文把 C-1／C-2 標為「（純函式層）」，`components.md:84` 則把 C-6 標為「（**呈現層**）」——兩者是 `components.md` 自己畫出的不同層級，C-6 並不在「純函式層」之列。C-6 的零 I/O 性質可由 `component-methods.md` 的方法簽章（三個方法皆無 I/O 型參數）合理推出，但引用來源寫成「[ad:components.md] 的純函式層約束」在事實上不準確——那條約束按 `components.md` 自己的分層明文只涵蓋 C-1／C-2。 | 改為「零 I/O……（與 U-1 同樣零 I/O，但屬 `components.md` 的呈現層 C-6，非純函式層 C-1／C-2；零 I/O 性質推自 `component-methods.md` 的方法簽章）」，避免把呈現層的元件誤植為純函式層的既有約束。 |
| 4 | Minor | `business-rules.md:29` | R-2.3 隱含依賴的承接建議寫「建議的承接方式：在 **U-6** 的自我測試中加一條……斷言——但那是 **U-6／U-9** 的落點」。依 `unit-of-work.md`，「自我測試 workflow」是 **U-9** 的專屬定義（U-6 是「正向同步 workflow」，`unit-of-work.md` 的 U-6 條目「擁有」欄沒有任何自我測試職責）；U-6 沒有自己的「自我測試」可承接這條斷言，「U-6／U-9」的並列選項因此有一半不成立，只是建議、不影響本單元可否實作，故列 Minor 而非更高。 | 把「在 U-6 的自我測試中」改為「在 U-9 的自我測試（`aidlc-sync-selftest.yml` 對獨立測試 Project 的端到端驗證）中」，並移除「U-6／U-9」的並列措辭，只指名 U-9。 |

### Summary

Critical #1 直接命中本單元被 ADR-A6 指派的核心設計目標——「設計一個機制（而非流程紀律）使格式變更與重新基準化不能脫鉤」，但 `parse` 的 `Block \| null` 簽章讓「全新、該渲染」與「他人較新版本、不該覆寫」這兩個呼叫端必須區分對待的情境回傳同一個值，使 R-3.4 聲稱的「不被覆寫」保證在唯一已知的呼叫端邏輯（`services.md:25` 的「`parse` 先於 `render`」）下無法成立，且與反向同步（S-C）的雜湊比對防線疊加後，恰好落入 ADR-A6 自己列為「本設計最危險的單一失誤模式」的觸發路徑。這不是罕見邊界案例——「push 任一分支即寫入真實看板」的既有觸發條件與正常的分支開發／還原流程即可重現。三項 Minor 都是可查證的引用或措辭不準確，不阻擋 READY，但 Critical #1 未解前不得判 READY。

## Review (Iteration 2)

**Verdict**: READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T16:11:20Z
**Iteration**: 2

### 逐項查證表

| # | Iteration 1 發現 | 處置 | 查證方式 | 結論 |
| --- | --- | --- | --- | --- |
| 1 | Critical：`parse` 對 R-3.1（無標記）與 R-3.4（未來版本）回傳同一個 `null`，使「不被覆寫」在現行簽章下不成立 | 未逕改 `component-methods.md` 的簽章（該檔已通過 application-design 三輪 reviewer）；改在 `business-rules.md` R-3.4 下方加誠實說明：標出缺口、給兩條候選修法（三態回傳 / `has_managed_marker` 述詞）、指派「Bolt 1 gate」為人工確認點、明寫「在修正落地前，R-3.4 的保護不存在」 | 讀 `business-rules.md:42-52` 全文；核對 `units-generation:260822-ug-L2`（發現上游契約缺口時「標出、寫明後果、指派落點與修法，不逕自改上游」）與本檔的處置形狀逐項對照 | **處置形狀本身合規**：(a) 「指派目標 stage 為 EXECUTE，無被 skip 的風險」逐字滿足 `units-generation:260822-ug-L2` 要求的 CONDITIONAL 風險註記（雖未指名具體 stage slug，但已指名確認人「Bolt 1 gate」，滿足「指出誰要確認」）；(b) 兩條候選修法（三態回傳／`has_managed_marker`）在型別層面都能讓呼叫端區分「無標記」與「有標記但讀不懂」，方向正確；(c) 「保護不存在」的誠實記載完整、且寫入 `business-rules.md` 正文（非僅 Review 附錄），呼叫端會看到。**但傳播不完整，見下方新發現 #1（Major）** |
| 2 | Minor：`domain-entities.md:18` 稱「`status` 與 `reason_category` 恰有一個非 `null` 這直接對應 `component-methods.md` 的『`reason_code` 一律非空』」，但兩者是不同型別的不同語意，「直接對應」措辭誤導 | — | 重讀 `domain-entities.md:18`，逐字比對 iteration 1 發現引文 | **未修正**。`domain-entities.md:18` 現況逐字仍是：「`status` 與 `reason_category` **恰有一個非 `null`**——這直接對應 [ad:component-methods.md] 的『`reason_code` 一律非空』與 [US:S-2 AC 15] 的總函式性。」與 iteration 1 引用完全相同，一字未動。Minor 不阻擋 READY，如實記載 |
| 3 | Minor：`business-logic-model.md:7` 把 C-6 的零 I/O 約束誤植為「[ad:components.md] 的純函式層約束」，但 `components.md` 自己把 C-6 標為呈現層（C-1／C-2 才是純函式層） | 改寫為「（與 U-1 同，[ad:components.md] 的呈現層（[ad:components.md] 把 C-6 列為呈現層，不是純函式層——先前誤植）約束）」 | 重讀 `components.md:31,84`：C-1／C-2 標「（純函式層）」、C-6 標「（呈現層）」，與現行 `business-logic-model.md:7` 的更正內容比對 | **核心內容已修正**：C-6＝呈現層、非純函式層的錯誤標籤已更正，與 `components.md` 現況相符。句子結構稍嫌迂迴（雙重巢狀 `[ad:components.md]`），且「零 I/O」性質仍掛在「呈現層…約束」而非如 iteration 1 建議的「零 I/O 性質推自 `component-methods.md` 的方法簽章」——`components.md` 對 C-6 並無明文的零 I/O 約束陳述（只有 C-1／C-2 有「不擁有：任何 I/O」字樣）。這是殘留的精確度落差，但已不構成原 Finding 指控的「誤植純函式層」問題，判定為已解決，殘留精確度問題列非阻擋觀察 |
| 4 | Minor：`business-rules.md` R-2.3 的承接建議誤寫「U-6／U-9」並列，但 U-6（正向同步 workflow）依 `unit-of-work.md` 無自我測試職責，只有 U-9 是自我測試層 | 加註「先前誤寫為 U-6」 | 重讀 `business-rules.md:29` 全句 | **僅部分修正，且產生新的自相矛盾，見下方新發現 #2（Minor）** |

### 新引入的問題

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| 1 | Major | `business-logic-model.md:70`（「邊界情形」表）與 `:40-48`（「`parse` 的版本分派」節） | Critical #1 的誠實揭露只寫進 `business-rules.md` 的 R-3.4，**本檔（同一單元的主敘事文件）自己的「邊界情形」摘要表在同一輪未同步**：`business-logic-model.md:70` 仍逐字斷言「區塊由更新版本的機制寫入 → `parse` 回 `null`，**該 item 被當作不受管、不被覆寫**」，「依據」欄只寫「R-3.4（保守選擇，**無告警**——告警落點未指派）」——完全沒有提示 R-3.4 這個保證在現行簽章下**不成立**。`parse` 的版本分派」節（`:40-48`）同樣維持原敘述，只在段尾寫「規則與各自的理由見 `business-rules.md` R-3 群」，讀者若只看這兩處（本檔是「業務邏輯模型」，是最可能被單獨查閱的主敘事文件），會得到與 iteration 1 Critical 完全相同的錯誤印象：以為「不被覆寫」是已生效的保證。雖然表格「依據」欄的「R-3.4」三字技術上構成一條指回 `business-rules.md` 的追溯路徑（跟隨它確實能找到完整說明），但摘要表本身的斷言用詞（「該 item 被當作不受管、不被覆寫」）與其指向的來源現況（「保護不存在」）直接矛盾，這正是 `project.md` 反覆記載的「修訂後未同步跨檔傳播」同型失誤（`application-design:260822-ad-L1`、`units-generation:260822-ug-L1`）——差別只在這次是同一檔案內部的兩個小節互不一致，而非跨檔案。 | 在 `business-logic-model.md:70` 該列補一句限定語（例如：「`parse` 回 `null`（**現行簽章下此保證未生效**，見 `business-rules.md` R-3.4 說明與 Bolt 1 gate 待決事項）），並在 `:40-48` 的「`parse` 的版本分派」節末補一句等價提示，使兩處與 `business-rules.md` 的誠實揭露一致。這是純文字補丁，不涉及任何設計改動。 |
| 2 | Minor | `business-rules.md:29` | 修正 Minor #4 時只在句首加了「（先前誤寫為 U-6）」的括號註記，但**句尾殘留的「但那是 U-6／U-9 的落點，本站只標出」未同步修改**，使同一句話自相矛盾：前半剛更正「唯一的自我測試層是 U-9」，後半立刻又把 U-6 放回並列選項。逐字：「建議的承接方式：在 **U-9**（本 intent 唯一的自我測試層；先前誤寫為 U-6）的斷言中加一條……的斷言——但那是 **U-6／U-9** 的落點，本站只標出。」 | 刪除句尾「但那是 U-6／U-9 的落點」中的「U-6／」，改為「但那是 U-9 的落點，本站只標出」，使全句內部一致。 |

### Summary

Critical #1 的處置形狀（標出缺口、給候選修法、指派 Bolt 1 gate 人工確認、誠實記載「保護目前不存在」）符合 `project.md` 對「發現已核可上游契約缺口」的既定紀律，且該誠實記載確實寫入了 `business-rules.md` 的正文（R-3.4 之下），不只是 Review 附錄——這是本輪修正最重要的部分，判定為已妥善處置。但同一單元的主敘事文件 `business-logic-model.md` 自己的「邊界情形」摘要表與「`parse` 的版本分派」節未同步這份誠實揭露，仍逐字斷言「不被覆寫」為已生效的保證，構成一個新的、範圍明確、修法簡單（純文字補丁）的 Major 傳播缺口。Minor #2（`reason_category` 的「直接對應」誤述）本輪未修正，如實記載，不阻擋 READY。Minor #4 的修正引入了一個小的自相矛盾殘留（句尾「U-6／U-9」未隨句首更正同步），亦不阻擋 READY 但應一併清理。零 Critical、1 Major、2 Minor（1 個為本輪新增的傳播缺口小殘留、1 個為未解決的原 Minor），依 `≤2 Major` 門檻判 READY；建議在下一次任何原因需要重開本單元文件時，把上表兩項新發現一併以純文字補丁清掉。
