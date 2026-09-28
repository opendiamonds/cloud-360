# Domain Entities — U-2 受管區塊渲染與雜湊

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-2-managed-block · kind: library -->

## `Block`

`parse` 的成功輸出，也是 `content_hash` 的輸入。[ad:component-methods.md] 給了三個方法的簽章但沒給這個型別的結構，本檔補上。

| 欄位 | 值域 | 語意 |
| --- | --- | --- |
| `format_version` | 正整數 | 產生此區塊的渲染器版本。**內嵌於區塊文字中**，見下方「為什麼版本要進區塊」 |
| `status` | `Status` \| `null` | 當時寫入的 Status；`null` 代表機制決定不寫 |
| `traceable_row` | 字串 \| `null` | `status` 非 `null` 時為命中的對照表列；`null` 時為 `null` |
| `reason_category` | `ReasonCode` \| `null` | `status` 為 `null` 時的原因類別；否則 `null` |
| `decided_at` | ISO 8601 字串 \| `null` | 該次判定的時間戳。**`status` 為 `null` 時非空；`status` 非 `null` 時為 `null`**——[US-OQ-3] 的必載內容逐字是「目前 Status 與其 `traceable_row`；**或**機制決定不寫的原因類別**與 ISO 8601 時間戳**」，時間戳只掛在後半支 |
| `scope_note` | 字串 | `[S]`（在 scope 內被跳過）與 `— SKIP`（不在 scope 內）的差別（[req:FR-F3]） |
| `rejection_notice` | `{ closed_at: ISO 8601 }` \| `null` | **[US:S-6 AC 5] 的「該次人工改動未被採納」告示**；`null` 代表本輪無告示。由 `Context` 同名欄位直接帶入 |

`status` 與 `reason_category` **恰有一個非 `null`**，且 `decided_at` 與 `reason_category` **同進退**（兩者都只出現在「決定不寫」那一支）。`rejection_notice` 與以上皆正交——它可在任一支上為非 `null`。

> **`decided_at` 的值域於 2026-08-30T01:31:09Z 補上 `| null`（reviewer iteration 4 Group B C-3 Critical）。** 先前宣告為非空 ISO 8601，但 `business-logic-model.md` 的 `render` 組成只在 `status = null` 的分支輸出它 ⇒ **最常走的 `mapped` 分支上 `parse` 取不回來**，型別與行為直接矛盾，而實作者無從判斷該改值域還是改區塊格式。
>
> **選擇改值域而非改格式**：[US-OQ-3] 的定案原文用的是「**或**」，時間戳字面上就只屬於「決定不寫」那一支——改格式等於擴張一個已核可的必載清單。**附帶收益**：這讓同檔 R-2.3 的 churn 隱憂只作用在不寫分支上——`mapped` 分支的 `Block` 不含隨輪變動的時間戳，語意相同的兩輪必得相同雜湊，`content_hash` 的穩定性因此比先前更強。

> **`rejection_notice` 是 iteration 3 補上的（2026-08-30T00:48:38Z，reviewer Group B F2 Critical）。** 先前只在 `Context` 定義它、卻宣稱它「經由 `Block` 進入 `content_hash` 涵蓋範圍」——**而 `Block` 當時根本沒有這個欄位**，該宣稱因此沒有依據，而它正是「機制自己寫的告示不會被 U-8 誤讀為人為變更」的唯一保證。同一段還把「只能來自 `Context` 的 `Block` 欄位」數成三個，實算為二（告示當時不是 `Block` 欄位）——`project.md` 的 `delivery-planning:dp-L1`（可算的數字先算再寫）在此再次被違反。
>
> **本欄位由 ADR-0015 §12 承載**（`Block` 的結構定義在上游 [ad:component-methods.md] §C-6，本檔只是補上上游未給的結構）。**它是一次 `format_version` bump**，見下方 R-4 群的互鎖與 `business-rules.md` 的 R-1.5。

> **先前此處寫「這直接對應 [ad:component-methods.md] 的『`reason_code` 一律非空』」，該對應不成立，已於 2026-08-29T16:14:22Z 更正（reviewer iteration 1 Minor）。** 兩者的 null 語意不同：`Decision.reason_code` **一律非空**（總函式性，[US:S-2 AC 15]）；而 `Block.reason_category` 在 `status` 非 `null` 時**就是 `null`**。前者是「永遠有值」，後者是「與另一欄互斥」——**是兩種不同的約束，不是同一條的兩種寫法**。
>
> 正確的關係是：`Block` 的互斥性是**渲染時**由 `Decision` 推導出來的（有 status 就渲染 status、否則渲染 reason），**它不繼承** `reason_code` 的非空保證。

兩段固定說明（OOS-2 的不自動關閉、「自訂欄位為空的 item 不由本機制維護」）是**渲染器的常數**，不是 `Block` 的欄位——它們逐字固定，不隨 intent 變化，因此不需要被 parse 回來，也不需要參與比對。

## `Context`（送審前自檢揭出的契約缺口，2026-08-29T23:42:35Z）

`render` 的簽章是 `(Decision, Context) -> string`（[ad:component-methods.md] §C-6），但 **`Context` 在上游與本 stage 的全部產出中都沒有定義**——`component-methods.md` 只在這一個簽章裡用到它，`Decision`／`Block`／`Config` 三個型別都有定義，唯獨它沒有。這與 U-1 承接的缺口 F-1（`Config` 在六個簽章被使用卻從未定義）是**同一種形狀**，落點同理在擁有該方法的單元，即本單元。

**它為什麼非有不可**：`Block` 現有**七個**欄位（原六個 ＋ ADR-0015 §12 增設的 `rejection_notice`），其中**三個**不可能從 `Decision` 推出來——

> **這個數字於 2026-08-30T00:48:38Z 重算（reviewer Group B F2）。** 先前寫「六個欄位裡有三個」：當時 `Block` 是六欄，而列在下表的第三項（告示）**不在那六欄之內**，故正確說法是「六欄裡有二」。補上 `Block.rejection_notice` 之後才成為「七欄裡有三」。兩個錯誤互相掩蓋，只有實際數一次才會發現。


| `Block` 欄位 | `Decision` 有嗎 | 只能從哪來 |
| --- | --- | --- |
| `decided_at` | ❌ `Decision` 是純函式輸出，四個欄位皆無時間戳（U-1 `domain-entities.md`） | `Context` |
| `scope_note` | ❌ `[S]`／`— SKIP` 的差別在 `ParsedRecord` 的 stage 行上，且 [req:FR-B3] 明訂它**對 Status 無影響**，故不進 `Decision` | `Context` |
| `rejection_notice` | ❌ 「上一次反向 PR 被關閉而未合併」是執行期事實，與映射判定無關 | `Context` |

`format_version` 不在此列——它是渲染器常數（見下一節），不是傳入值。

| 欄位 | 值域 | 語意 |
| --- | --- | --- |
| `decided_at` | ISO 8601 字串 | 本輪判定的時刻，由 **U-6 取本輪當前時間**（見其 R-5 群）。**`status` 為 `null` 時成為 `Block.decided_at`；`status` 非 `null` 時 `render` 不輸出它**（見上方 `Block` 表）——本欄位每輪必填，但不是每輪都被渲染 |
| `scope_note` | 字串 | `[S]`（在 scope 內被跳過）與 `— SKIP`（不在 scope 內）的差別。**來源為 U-1 composite action 的第五個 output**（見下方更正），由 U-6 轉交。直接成為 `Block.scope_note`；R-1.2 的可區分性由它承載 |
| `rejection_notice` | `{ closed_at: ISO 8601 }` \| `null` | **[US:S-6 AC 5] 的告示**。非 `null` 時，渲染出的區塊須載明「該次人工改動未被採納」與 `closed_at`。由 U-6 的 R-6.2b 填入，來源是該 intent 的反向 PR 關閉時刻 |

**呼叫端是 U-6**（正向同步是唯一寫受管區塊的路徑，[ad:components.md]）。`decided_at`／`scope_note` 每輪必填；`rejection_notice` 只在該 intent 落在 U-6 本輪的 `reverse_rejected` 集合時非 `null`。

> **`scope_note` 的來源已更正（2026-08-30T00:48:38Z，reviewer Group B F4 Major）。** 先前寫「由呼叫端自 `ParsedRecord` 取得」——**但 `ParsedRecord` 不跨 U-1 的 composite action 邊界**：U-1 `domain-entities.md` 的生命週期段逐字寫「由 composite action 的**四個 output** 交給呼叫端」，那四個是 `Decision` 的四個欄位，`ParsedRecord` 是 action 內部值。呼叫端 U-6 拿不到它，這是一個新的懸空契約。
>
> **處置**：U-1 的 composite action **增設第五個 output `scope_note`**（落點在 U-1 的 `domain-entities.md`，屬本 stage 自己的產出、閘門未觸發，故就地補而非指派）。這不動上游——`Decision` 的四欄未變、`map` 仍是純函式；新增的是 action 的輸出面，而 action 的 output 集合本來就由本 stage 定義。`decided_at` 無此問題：它是 U-6 取本輪的當前時刻，不來自 U-1。


> **`rejection_notice` 進不進 `content_hash`？進**——它是 `Block` 的欄位，而 `content_hash` 吃的是整個 `Block`。
>
> **先前為此附的「必要性論證」已撤回（2026-08-30T01:31:09Z，reviewer iteration 4 Group B m-1）**：原文寫「若它不改變雜湊，U-6 回寫後看板內容已變而記錄的雜湊未變，U-8 會誤判」。**該情境在 R-5.4 改為回讀取值之後構造上不可能**——U-6 記錄的雜湊來自寫入後的 `read_item`，讀到的就是含告示的區塊，兩者必然一致。那段論證停留在舊版 R-5.4（對 `render()` 輸出直接算雜湊）的世界。
>
> 現在的理由單純得多：**它是 `Block` 的一部分，沒有任何規則把它排除在雜湊之外**，也不需要為它開特例（同 `decided_at`，見同檔 R-2.3）。
>
> **告示是暫態的**：下一次有實質漂移的寫入會渲染出不帶告示的區塊，告示隨之消失。這不違反 AC 5——AC 5 要求的是「**下一次正向同步覆寫該 item 之前**受管區塊載有一則記錄」，是一個時點要求而非永久保存要求。此時雜湊會再變一次，而 R-5.4 同樣會在該次寫入後回寫，兩者仍同步。
>
> **本節不裁定告示的文字與版面**——那屬渲染細節，且會受 R-4 群的格式互鎖約束（新增欄位＝格式變更 ⇒ 須 bump `format_version` 並重新基準化）。**這是本節必須點名的連帶後果**：`rejection_notice` 是 `Block` 的新增資訊，其上線是一次 ADR-A6 意義下的格式變更，必須與 U-6 的 R-6.2 落在同一批交付（兩者同為 Bolt 1），不得先上 U-6 的告示填入而後補 U-2 的渲染。

> **缺口的來源與本站的處置**：U-6 的 R-6.2 原寫「**指派 U-2 定義 `Context` 的告示欄位與渲染形式**，確認人為 Bolt 1 的 gate」，但本單元三份產出當時**完全沒有提到 `Context`**——該指派沒有被接住。這不是上游缺口（`component-methods.md` 已定稿、確實沒定義它），是**同一個 stage 內兄弟單元之間的指派落空**，故依本 stage 已建立的立場**就地補上而非再指派**（指派給未來的自己只是把現在能做的事延後）。發現方式為 `project.md` 強制的送審前自檢第 2 項（契約端點三問）。

## 受管標記（marker）——本單元擁有的格式常數（iteration 5 Group B C-1 補，2026-08-30T02:47:00Z（依檔案 mtime 重建；原填 09:55:00Z 為未經 `date -u` 的編造值，已更正））

`parse` 的契約是「無標記回 `null`」（[ad:component-methods.md] §C-6），[ad:services.md] 要求「不得重複附加區塊——`parse` 先跑再 `render`」，而 ADR-0015 §11 的 `write_body` 又必須知道「要附加還是就地替換、替換哪一段」。**三者都依賴一個標記，而它的語法在上游與本 stage 的全部產出中從未定義**。

| 常數 | 值 | 用途 |
| --- | --- | --- |
| `MANAGED_BLOCK_BEGIN` | `<!-- aidlc-sync:begin v=<format_version> -->` | 區塊起點；**版本內嵌於此**（見下節），`parse` 的版本分派讀它 |
| `MANAGED_BLOCK_END` | `<!-- aidlc-sync:end -->` | 區塊終點 |

- **兩者皆為 HTML 註解**，在 GitHub issue body 的 markdown 呈現中不可見，不干擾人寫的內容。
- **`render` 的輸出一律含這一對標記**（首尾各一），這使 `write_body` 只需字串搜尋即可定位，**不需要 `parse` 回傳跨度**——`parse` 的簽章因此一字未改。
- **標記屬本單元的格式契約**，受 `business-rules.md` R-4 群三道互鎖約束：改動標記語法即格式變更，須 bump `format_version` 並於同一 PR 重新基準化。

> **為什麼這一節必須在本單元、不能留給 U-3**（reviewer iteration 5 Group B C-1 的原話）：`write_body` 若自行決定「受管標記長什麼樣」，就會在 U-3 產生**第二份格式知識**，而它落在 R-4 群的互鎖之外——bump 版本時沒有任何機制會發現 U-3 那一份沒跟上。這正是 ADR-A6 點名的最危險失效模式的另一個入口。**U-3 的 R-6 群引用的是本節的兩個具名常數，不是它自己的副本。**

## 為什麼 `format_version` 要進區塊

[Q1=C] 定案以「版本常數 ＋ 遷移登錄表 ＋ 三道 CI 互鎖」承載格式契約。要讓 `parse` 有能力處理**上一個版本產生的區塊**（遷移期間看板上必然新舊並存），版本必須是**區塊自己帶的**，而不是只存在於渲染器程式碼裡。

`parse` 因此是**版本分派**的：先讀版本標記，再套用對應的解析器。找不到版本標記 → 視為無標記 → 回 `null`（沿用 [ad:component-methods.md] 的既有錯誤處理）。

**代價（誠實記載）**：版本進區塊 ⇒ 版本進 `content_hash` ⇒ **bump 版本會讓所有既有 item 的雜湊改變**。這正是 ADR-A6 所警告的失效模式，其防線就是 [Q1=C] 的三道互鎖要求 bump 與重新基準化落在同一個 PR。**版本內嵌不是繞過 ADR-A6，是把它的觸發條件變得明確可偵測。**

## `content_hash` 的涵蓋範圍（[Q2=A] 的直接後果）

簽章是 `(Block) -> sha256`——**吃的是 parse 後的結構，不是渲染出來的字串**（[ad:component-methods.md] 逐字如此）。這帶來一個必須被寫下來的性質：

- **純外觀的格式調整**（空白、標題樣式、欄位順序），若 round-trip 回來得到**逐欄相同的 `Block`**，雜湊**不變**。
- **結構變化**（增刪欄位、改欄位語意）才會改變雜湊。

**這不是 ADR-A6 已否決的「欄位級比對」。** 該否決針對的是「為每個欄位定義比對規則」以**取代**單一雜湊；此處仍是單一雜湊、單一比對，只是雜湊的輸入是正規化後的結構。差別在於比對邏輯的數量（一個 vs 每欄一個），不在於雜湊算在哪一層。[req:FR-G4] 要求的「受管區塊**內容雜湊**比對」逐字成立。

`decided_at` **在**涵蓋範圍內（[Q2=A]）：不為時間戳開特例，`content_hash` 逐字是整個 `Block` 的雜湊。churn 由上游的漂移判定擋住，見 `business-rules.md` R-2.3 的隱含依賴警告。

## 生命週期

`Block` 是**單次 workflow run 內的程序內值**。它的持久化形式有兩處，兩者都不由本單元寫入：issue body 中的受管區塊文字（**U-3 的 `write_body`**，由 ADR-0015 §11 增設；先前此處寫「U-3 寫」而 U-3 當時沒有任何寫 issue body 的方法——更正於 2026-08-30T00:48:38Z）、`sync-state.json` 中的雜湊（U-4 寫）。本單元零 I/O，與 U-1 同。

## 與上游的對應

三個方法的簽章與錯誤處理引自 [ad:component-methods.md] §C-6；必載的四項內容引自同節（[US-OQ-3] 定案）；格式即契約與遷移要求引自 [ad:decisions.md] ADR-A6；`[S]`／`— SKIP` 的差別要求引自 `requirements.md` 的 FR-F3（其正本判定在 FR-B3）；三道防迴圈防線引自 FR-G4；單元邊界、完成判準與 ADR-A6 的指派引自 [ug:unit-of-work.md] 的 U-2；故事歸屬引自 [ug:unit-of-work-story-map.md]（S-4 AC 6、S-6 AC 6）；「有漂移才寫」引自 [ad:services.md] 的 S-A；元件職責引自 [ad:components.md]。
