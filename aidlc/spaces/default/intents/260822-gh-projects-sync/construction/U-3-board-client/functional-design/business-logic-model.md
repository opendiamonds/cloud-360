# Business Logic Model — U-3 看板客戶端

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-3-board-client · kind: library -->

## 這個單元在做什麼

它是**唯一**碰 Projects v2 與 GitHub Issues API 的地方。**七個**方法（[ad:component-methods.md] §C-3）：`read_item`、`create_item`、`write_status`、`write_field`、`ensure_field`、`read_issue_state`、**`write_body`**。

> **`write_body` 由 ADR-0015 §11 增設（2026-08-30T00:48:38Z，reviewer iteration 3 兩組各自獨立抓到的 Critical）。** 原本的六個方法**無一寫 issue body**，而 C-6 的 `render` 產生的受管區塊只能存在於 issue body——`render()` 的輸出因此在整份設計中沒有任何具名去處。
>
> **`write_field` 不是它**：[ad:component-methods.md] §自訂欄位格式明訂自訂欄位「長度上限 50 字元」且「**完整敘述一律在受管區塊**……兩處不一致時以受管區塊為準」，上游自己把兩者定義為不同的東西。先前 U-6 的 R-6.2 把受管區塊的寫入路徑誤述為 `U-2 render → U-3 write_field`，已一併更正。
>
> **後果鏈（缺它時）**：issue body 永無受管標記 ⇒ `read_item` 的 `managed_block_hash` 恆為 `null`（本檔下方「無標記 → `null`」逐字如此）⇒ U-6 的 R-5.4 每輪把 `null` 寫進 `SyncState` ⇒ U-8 的 R-1.1 `null` 比 `null` 恆相同 ⇒ **反向同步永遠不觸發、且沒有任何紅燈**。
>
> **權限**：`Issues: write`，已在 ADR-0014 的集合內，不擴大權限面。**不牴觸**本單元的權限邊界（「不得提供推 commit 到 `ut` 或改 record 目錄以外的檔案的方法」）——寫 issue body 兩者皆非。

與 U-1／U-2 的關鍵差別：**本單元不是純函式，它做真實的網路 I/O**，因此也是三者中唯一會產生 `ExternalError`、唯一能讓 workflow 紅燈的一個。複雜度 **L**，與 U-7 並列為十二個單元中僅有的兩個 L 級（先前寫「最重的」隱含唯一性，與 [ug:unit-of-work.md] 不符；iteration 1 Minor #4 只修了 `functional-design-questions.md` 一處，本處於送審前自檢補上，2026-08-29T23:42:35Z）。

本 repo **無 Projects v2 先例**（[kb] 實測 11 支 workflow 沒有一支寫過），分頁、欄位 id 解析、錯誤碼全部新寫。

## 主要資料流

```
binding（issue 編號）
   │
   ├─► read_item ─► Issue.projectItems ─► 過濾出 Config 的 Project
   │                                        ├─ 0 筆 ──► ItemState（值皆 null）
   │                                        ├─ 1 筆 ──► ItemState
   │                                        └─ >1 筆 ─► ExternalError
   │
   └─► write_status(binding, expected, desired)
          └─► read_item ─► actual == expected？
                             ├─ 否 ──► Aborted（不送出寫入、不開 issue）
                             └─ 是 ──► mutation ─► Written
                                        └─ ⚠ 此處到 mutation 之間有競態視窗
```

文字 fallback：讀取路徑由 issue 反查它的 project items，過濾出設定指定的那個 Project，依筆數分三支；寫入路徑先走一次讀取做比對，不符即中止，相符才送出 mutation——而比對與 mutation 之間存在一個無法消除的視窗。

## `read_item` 的查找路徑（[Q1=A]）

不列舉整個 Project，改由 `Issue.projectItems` 反查。三個後果與其代價見 `domain-entities.md`；規則（含**必須先經 PRE-1 實測**的 R-1.0、多 Project 過濾的 R-1.2、零筆與多筆的處置）見 `business-rules.md` R-1 群。

**R-1.2 的過濾是這個選擇引入的新責任**：列舉整個 Project 時目標 Project 是查詢起點，不可能拿到別的 Project 的 item；反查 issue 則會拿到它所屬的**全部** Project。

## `write_status` 的三步與其視窗（[Q2=A]）

1. `read_item` 取得 `actual`。
2. `actual != expected` → 回 `Aborted`，結束。
3. 送出 mutation。

**第 2 步與第 3 步之間的視窗被明確接受**（[Q2=A]）。Projects v2 沒有 compare-and-swap，這個視窗在平台層無法消除。

> **先前此處寫「承接方式是下一輪反向同步的受管區塊雜湊比對——[US:S-6] 的『送到人面前決定』仍然成立，只是慢一輪」。該宣稱已於 2026-08-29T15:23:54Z 被 reviewer iteration 1 推翻**（完整反證見 `business-rules.md` 的 R-2.4 段），本處為 iteration 3 M-1 的補正（2026-08-30T00:05:00Z）：主敘事檔漏改，單獨查閱者會得到與原始 Critical 完全相同的錯誤印象。
>
> **正確的敘述**：視窗內被覆寫的協作者改動**沒有任何兜底**——不是慢一輪，是永遠不會被偵測。機制自己的回寫會在同一輪把雜湊比對基準重置成自己寫的值。接受它的理由不是「有兜底」，而是替代方案（樂觀鎖式的寫後回讀重試）與視窗寬度不成比例；該代價已由 **ADR-0015 §2** 綁進 Bolt 1 的 DoD 揭露項。

**這個視窗沒有測試涵蓋**，理由與代價見 `business-rules.md` R-2.4。**不得把「有回讀比對」讀成「寫入是原子的」**：R-2.1 擋的是上一輪之後、本輪回讀之前的改動，擋不掉回讀之後的。

## 錯誤處理

本單元是三個 library 單元中唯一會產生**紅燈級**錯誤的：

| 產出 | 紅燈？ | 依據 |
| --- | --- | --- |
| `ExternalError { http_status }` | **是** | [ad:services.md] 明列的兩種紅燈之一 |
| `Aborted { actual, expected }` | 否 | [req:FR-C1] 的主動中止，屬正常判斷 |
| `Failed { http_status, message }` | 否 | `write_field` **與 `write_body`** 專屬，且**不連坐** Status 寫入。`write_body` 失敗的連帶後果須被呼叫端看見：該輪受管區塊未更新 ⇒ U-6 的 R-5.4 回讀取得的仍是舊雜湊（或 `null`），故**該輪不得把新雜湊寫進 `SyncState`**，否則基準與看板現況脫鉤 |
| `CannotCreate` | 否 | 交 C-5 通報「需人工建立欄位」 |

`phases/construction.md` 要求「在整合邊界一律有錯誤處理」「錯誤必須被表面化」——本單元**就是**那個整合邊界，上表四個型別即是它的表面化形式。

> **先前此處寫「四者都是回傳值而非例外，與 U-1／U-2 的形狀一致」，該敘述不成立，已於 2026-08-29T15:23:54Z 更正。** [ad:component-methods.md] 對 `read_item` 的錯誤處理逐字寫「API 錯誤 → **拋** `ExternalError{http_status}`」——用的是「拋」，與其餘三型的「回」不同。
>
> **正確的形狀是混合的**：`Aborted`／`Failed`／`CannotCreate` 是**回傳值**（呼叫端必須檢查回傳型別）；`ExternalError` 是**例外**（會沿呼叫堆疊往上傳播，呼叫端若不攔就整輪中止）。這個差別直接決定 bash 實作對 HTTP 層失敗的傳播方式，**不能混為一談**。
>
> 這也與 U-1／U-2「不拋例外」的明文設計**相反**而非一致——那兩者是純函式，本單元不是。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| issue 尚未在看板上 | `ItemState` 的 `status`／`field_value` 皆 `null`，不視為錯誤 | R-1.3 |
| 同一 issue 在同一 Project 有兩筆 item | `ExternalError`，**不猜** | R-1.4 |
| record 已有綁定編號時再跑首建 | 不建、回既有值 | R-3.1（[US:S-1 AC 6]） |
| 回寫失敗導致綁定編號不存在 | **R-3.1 攔不住**——真正的防線是 U-4 的 `Rejected` 紅燈 ＋ 通報 | `requirements.md` A-8（未驗證） |
| 自訂欄位建立失敗 | `CannotCreate` → 通報；**Status 照寫** | R-4.1／R-4.2 |
| issue body 無受管標記 | `managed_block_hash` 為 `null`（U-2 的 `parse` 回 `null`） | `domain-entities.md` |
| 「改 record 目錄以外的檔案」 | 介面不提供，但**產生不出 403** | R-5.2 ＋ PRE-1-a |

## 與上游的對應

七個方法（含 ADR-0015 §11 增設的 `write_body`）、錯誤型別與權限邊界引自 [ad:component-methods.md] §C-3；元件分層與「唯一碰外部 API 的元件」引自 [ad:components.md]；失敗語意與紅燈規則引自 [ad:services.md]；403 半邊缺口引自 [ad:decisions.md] ADR-A2，獨立測試 Project 引自 ADR-A3；FR-C1／FR-C2／FR-A1／FR-A2／FR-F2／FR-I4 與假設 A-8 引自 `requirements.md`；單元邊界、複雜度與「無 Projects v2 先例」引自 [ug:unit-of-work.md] 的 U-3；承接的 AC 引自 [ug:unit-of-work-story-map.md]。

**本檔對上游的補充**：`binding` → item 的查找路徑（[Q1=A]，**含一項須加進 PRE-1 的未實測前提**）、多 Project 過濾與零／多筆的處置、回讀競態視窗的明確接受與其承接方式（[Q2=A]）。方法簽章、錯誤型別、權限邊界**一條未改**。

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:11:38Z
**Iteration**: 1

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| 1 | Critical | `business-rules.md:27-39`（R-2.4，尤其 :35「被蓋掉的改動會在下一輪反向同步被受管區塊雜湊比對偵測到並開 PR 送人決定」）對照 `../U-6-forward-workflow/functional-design/business-logic-model.md:26-31`（U-6 一輪執行序列：`write_status` 成功後**立即** `→ U-2 render → U-4 commit_and_push`，中間**沒有**任何回讀步驟）與 `../U-8-reverse-workflow/functional-design/business-logic-model.md:19-23`（U-8 的偵測序列：`U-3 read_item → U-2 parse+content_hash → 與 sync-state.json 記錄的雜湊比對`） | **R-2.4 賴以接受競態視窗的「反向同步backstop」，對它自己要防的那個場景實際上抓不到——這是一個「偵測 X」型規則的可達性問題，X 在這個場景下不可達。** 沿時間軸推演：(a) `write_status` 的 `read_item` 讀到 `actual == expected`，判定可寫；(b) **視窗內**協作者把看板改成 Y；(c) `write_status` 的 mutation 執行，把 Y 覆寫成機制的 `desired`（記為 X）；(d) 依 U-6 的序列，**同一輪**forward-sync 緊接著呼叫 `render(desired) → content_hash → commit_and_push`，把 `sync-state.json` 的 `managed_block_hash`（及 issue body 的受管區塊文字）更新為 X 的雜湊——**這一步沒有先重新讀一次看板現況，直接拿 `desired` 去算雜湊並寫入**。(e) 下一輪 U-8 反向同步執行：讀看板現況（此刻仍是 X，因為自 (c) 之後沒有人再動過）→ 算「現況雜湊」→ 與 `sync-state.json` 記錄的雜湊（也是 X 的雜湊，來自 (d)）比對 → **相同 → 判定「無人為變更，跳過」**（U-8 `business-logic-model.md:22`）。協作者在 (b) 寫入的 Y 從未被機制讀過、也從未被任何地方記錄，(d) 這一步把「機制自己剛寫的值」直接蓋成新的比對基準，使 (b) 的存在在雜湊層面**沒有留下任何痕跡**可供 (e) 偵測。此推導不依賴「現況雜湊」究竟是重新解析 issue body 文字、還是用即時讀到的 Status 重新渲染再雜湊——兩種讀法下，(e) 時點看板的「現況」都已經是 X（機制自己寫的），不是 Y（協作者寫的、已被蓋掉的）。換言之：R-2.4 的視窗只有在**協作者的變更發生在機制完成整輪回寫（含 (d) 的雜湊更新）之後**才會被下一輪反向同步抓到；而它明文要接受、且宣稱「靠反向同步兜底」的那個視窗，指的正是**回寫完成之前**的那段（read→mutate 之間），這正是 backstop 覆蓋不到的部分。這使 [US:S-6]「送到人面前決定」在這個視窗內**不是「慢一輪」，而是完全不會發生**——協作者的判斷被機制的值永久覆蓋且無任何後續機制能發現。**可達性不是理論性的**：U-3 是唯一持續輪詢並主動寫看板的單元，且 [req:NFR-P3] 明文允許事件路徑與排程對帳並行執行，兩者都會呼叫 `write_status`（見 `services.md` S-B「與 S-A 的競爭」），協作者在看板上手動操作（拖卡片）與機制的排程/事件寫入本就是本設計要處理的核心情境（[US:S-6] 的整個存在理由），視窗雖窄但不是邊界案例。 | 在本站（`write_status` 的競態視窗處置屬本單元職權）重新裁定 R-2.4，而不是留給 construction 的其他站默默繼承一個不成立的保證：(a) 誠實記載「這個視窗目前無任何偵測機制」，移除「反向同步兜底」的宣稱，把殘留風險交由 delivery-planning／PRE-1 決定是否可接受；或 (b) 改採 functional-design-questions.md Q2 選項 B（寫入後再回讀一次驗證），至少讓視窗內的覆寫被**偵測到**（即使已經覆寫）並開 issue，而非宣稱一個實際不存在的下游安全網。兩者皆可，但**不得**維持現狀繼續宣稱 U-8 的雜湊比對會抓到這個場景——它結構上抓不到。 |
| 2 | Critical | `business-rules.md:9`（R-1.0：「`Issue.projectItems` 這條路徑必須先被 PRE-1 實測確認可用，才可據以實作。本站未實測」）與 `domain-entities.md:32`（「它必須被加進 PRE-1 的實測清單」）對照 `../../../inception/delivery-planning/bolt-plan.md:21-27`（PRE-1 的 5 項實測表：①三項憑證權限 ②操作次數上限 ③`createProjectV2Field` 可用性 ④A-1/A-2/A-3/A-8 ⑤PRE-1-a 的 Rulesets）與 `bolt-plan.md:51`（Bolt 1 的 Definition of Done：「PRE-1 第 1／3／4 項已綠」） | **R-1.0 要求「加進 PRE-1 的實測清單」，但已核可的 `delivery-planning/bolt-plan.md`（inception 2.8，先於本站執行）的 PRE-1 表**沒有**這一項，而 Bolt 1（承載 U-3）的 DoD 只檢查 PRE-1 第 1／3／4 項，第 2 項與 PRE-1-a 分別延後到 Bolt 2／Bolt 4——`Issue.projectItems` 反查既不在任何一項裡，也不在 Bolt 1 的把關範圍內。**這代表 Bolt 1 可以在完全沒有驗證過 `read_item` 的核心查找路徑（[Q1=A]，本設計唯一選中的選項）是否真的可行的情況下被判定 DoD 全綠並依 `project.md` 的 deploy-on-merge 直接上線**——而 `read_item` 是 R-2.1 要求「必先」呼叫的路徑，`write_status`／`create_item`／`write_field` 全部經它。本站對這個缺口的處置方式（只在 prose 裡說「必須被加進」）**低於同一個 intent 內已示範過的正確處置標準**：`decisions.md` 的 ADR-A2 發現同型缺口（PRE-1-a 需要新增但 `stories.md` 的 PRE-1 清單不可回改）時，開了一個獨立、明確標記的「本站對 PRE-1 的追加實測項」表格段落並指名「由 construction 併入 PRE-1 執行」，`bolt-plan.md` 隨後**確實**把它併入（PRE-1-a 列在表格第 5 項，且是 Bolt 4 的顯式閘門）。本站的 R-1.0 只是一句嵌在規則表裡的陳述，沒有等價的、會被下一站看見並落實的傳遞機制，也沒有指名「誰」「何時」把它併進 `<record>/construction/pre-1-findings.md`（`bolt-plan.md:19` 指定的留痕位置）。若不補這道傳遞，`Issue.projectItems` 這個本 repo**從無先例、本站明言「無法實地驗證」**的 GraphQL 查詢，有真實機率在完全未經測試的狀態下進入 Bolt 1 的可展示範圍。 | 比照 ADR-A2 的處置形狀：在本站（或緊接的 nfr-requirements／delivery-planning 銜接點）明確新增一條「本站對 PRE-1 的追加實測項」記載，指名它必須在 Bolt 1 開工前併入 `<record>/construction/pre-1-findings.md` 並列為 Bolt 1 DoD 的第 5 項（目前只列 1／3／4）。在該記載存在、且能證明會被下一個讀者（delivery-planning 或 Bolt 1 實際執行者）看到之前，不得視為「已交代」。 |
| 3 | Major | `business-logic-model.md:56-59`（錯誤處理表 ＋「四者都是回傳值而非例外，與 U-1／U-2 的形狀一致」）對照 `../../../inception/application-design/component-methods.md:86`（C-3 `read_item` 錯誤處理欄逐字：「API 錯誤 → **拋** `ExternalError{http_status}`」，動詞為「拋」而非其餘三種錯誤型別一律使用的「回」） | **U-3 自己的判斷與其引用的上游契約字面直接矛盾。** `component-methods.md` 對 C-3 的四個錯誤型別**不是統一動詞**：`read_item` 的 `ExternalError` 用「拋」（例外／中斷式），`write_status`／`write_field`／`ensure_field` 的 `Aborted`／`Failed`／`CannotCreate` 用「回」（回傳值）——且 `WriteResult = Written \| Aborted \| Failed` 這個聯合型別本身**不含** `ExternalError`，意味著上游把 `ExternalError` 設計成會從 `read_item`（進而從內部呼叫它的 `write_status`／`create_item`）**中斷式地往外傳**，而非包進正常回傳值裡讓呼叫端 `switch`。這與 U-1／U-2「不拋例外」的**明文**設計（`component-methods.md` C-1／C-2 兩行皆逐字寫「不拋例外」）恰恰相反，U-3 卻宣稱「與 U-1／U-2 的形狀一致」。這不是純措辭：`tech-stack-decisions.md`（本單元自己的 nfr-requirements 產出）明訂 bash 實作必須「檢查兩層——exit code 與回應 body 的 `.errors`」，隱含 HTTP 層失敗（`ExternalError` 的來源）天然以**非零 exit code**（中斷式）表現；若本檔堅持「四者皆回傳值」，實作者會被引導去**吞掉**那個非零 exit code、包成 JSON 回傳，再由呼叫端另行判斷是否要重新致命失敗——這是一條完全合理但**與上游字面相反**、且從未被本檔或 `tech-stack-decisions.md` 明確選定的實作路徑，兩種讀法都可能被不同的實作者選中，造成 U-6（呼叫端）對「這一步失敗後 workflow 是否自動紅燈」的假設不一致。 | 在本檔明確定案並改寫：要嘛承認 `ExternalError`（僅限 `read_item`／及其內部呼叫者）走例外式中斷（與 `component-methods.md:86` 一致，此時「四者都是回傳值」一句需限定為「除 `ExternalError` 外的三者」），要嘛明確裁定本單元的 bash 實作統一改為回傳值式（此時需同步標註「與 [ad:component-methods.md] 的動詞不同，本站裁定收斂為統一回傳值，理由是……」，而不是宣稱兩者一致）。二擇一，但不得讓兩種語意同時以矛盾的措辭並存。 |
| 4 | Minor | `functional-design-questions.md:14`（「本單元複雜度 **L**，是十二個單元中唯一的 L 級之一」）與 `business-logic-model.md:9`（「複雜度 **L**，是十二個單元中最重的」）對照 `../../../inception/units-generation/unit-of-work.md`（U-3 段：「複雜度 \| **L**」；U-7 段：「複雜度 \| **L**」） | 這是一個可算的數字：`unit-of-work.md` 的 12 個單元複雜度標註為 U-1 M、U-2 S、U-3 **L**、U-4 M、U-5 S、U-6 M、U-7 **L**、U-8 M、U-9 M、U-10a XS、U-10b XS、U-11 XS——**L 級有兩個（U-3、U-7），不是一個**。`functional-design-questions.md:14` 的「唯一的 L 級之一」本身字面自相矛盾（「唯一」與「之一」不能並存），`business-logic-model.md:9` 的「十二個單元中最重的」則隱含「唯一最重」，與 U-7 同為 L 級的事實不符——U-3 是**並列**最重，不是**獨自**最重。 | 兩處改為「複雜度 L，是十二個單元中複雜度最高的兩者之一（另一為 U-7）」或等價的、不隱含唯一性的措辭。 |

### Summary

兩項 Critical 都命中「規則賴以成立的機制其實不可達／未落地」這個模式：R-2.4 宣稱的反向同步 backstop，對它自己要接受的那個競態視窗結構上抓不到（雜湊比對基準在同一輪就被機制自己的回寫重置）；R-1.0 宣稱的 PRE-1 補項，沒有走本 intent 已示範過、確實有效的傳遞管道（ADR-A2 式的獨立追加表格），使 Bolt 1 有真實機率在核心讀取路徑從未實測的情況下被判定完成並依 deploy-on-merge 上線。兩者都不是「設計選錯」，而是「設計決定所依賴的保護機制，實際上不存在或不會被執行」——這正是本次審查被要求優先驗證的兩個項目。Major #3 是一個會誤導 bash 實作走向的上游字面矛盾，Minor #4 是可算數字的誤述。四項合計已超過 NOT-READY 門檻（任一 Critical 即 NOT-READY）。

## Review (Iteration 4 — 驗證輪，受管區塊寫者鏈與契約)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T01:22:06Z
**Iteration**: 4
**涵蓋單元**: U-1 / U-2 / U-3 / U-5 / U-8

> 本輪逐檔（不用目錄操作，全部以確切路徑）重讀 U-1／U-2／U-3／U-5／U-8 的 `functional-design/` 與 `nfr-requirements/` 產出，加上 U-6 的四份產出（為核對 `write_body`／`Context` 的呼叫端）、ADR-0015 全文，以及被它 `Amends` 的五份上游檔。**iteration 3 兩組共 6 個 Critical／6 個 Major 的修法逐項查證：12 項通過、5 項未通過。** 另發現 **3 個 Critical**，其中 **兩個直接落在本輪新增的 `write_body` 與 `Block` 欄位上**——與前三輪完全相同的形狀：修正動作本身帶進下一個 Critical。

### 逐單元判定

| 單元 | Verdict | 一句理由 |
| --- | --- | --- |
| **U-1** | **READY（附 1 項必修）** | 第五個 output `scope_note` 已增設且計數正確（實測 `grep -c "^| output"` = **5**），但它沒有值域、沒有推導規則、`business-rules.md` 與 `domain-entities.md` 的型別段對它零命中（M-3） |
| **U-2** | **NOT-READY** | 1 Critical（`Block.decided_at` 宣告為非 `null`，而 `render` 只在 `status = null` 的分支輸出它 ⇒ 最常走的 `mapped` 分支上 `parse` 取不回來，C-3）＋ 1 Major（`Context.decided_at` 宣告「呼叫端是 U-6」而 U-6 對它零命中，M-2）＋ 2 Minor。`Block` 欄數實數為 **7**、來源分配無缺無重（下方逐欄列出），這部分正確 |
| **U-3** | **NOT-READY** | 1 Critical（`write_body` 的 `Failed` 在呼叫端無任何處置，且 U-3 自己宣告的連帶規則在 U-6 不存在，C-1）＋ 2 Major（`business-rules.md` 對 `write_body` **零規則**，M-4；SEC-2 的「只需要 Projects 那一半」被 `write_body` 推翻，M-5） |
| **U-5** | **READY（附 1 項必修）** | §5 的回填逐字相符；但 `business-logic-model.md:82`／`:86` 仍以「U-8 的元件集合不含 C-5」為據宣告一個**已被本輪關閉**的缺口（M-6） |
| **U-8** | **READY（附 1 項必修）** | M-4（`notify`／C-5）與 M-2（`branches-ignore`→`paths-ignore`）兩項必修**全部落地並經逐字複驗**；殘留為 IAM 判定未隨自己的修正更新（M-5） |

**整組 NOT-READY**：任一 Critical 即整組 NOT-READY，本輪 3 個。

### 逐項查證（dispatch 指定的 1–5 項）

#### 1. 受管區塊的寫者（`write_body`）

| # | 查證項 | 結論 | 依據（檔案:行 ＋ 逐字引文） |
| --- | --- | --- | --- |
| 1a | `component-methods.md` §C-3 的就地指標是否存在、是否與 ADR §11 相符 | **通過** | `component-methods.md:93-99`：「**經 ADR-0015 §11 增設 `write_body`（指標補於 2026-08-30T00:48:38Z）**：上表六個方法**無一寫 issue body**……」＋一張與 ADR §11 :84 **逐欄相同**的方法表（`(binding, block_text) -> WriteResult`／「把受管區塊寫進 issue body」／「與 `write_field` 同形……失敗回 `Failed`，不連坐 Status 寫入」）。:99 另附「**注意 `write_field` 不是它**」與確認人（Bolt 1 的 gate） |
| 1b | U-3 的方法數是否已由六改七 | **部分通過（M-4）** | 已改：`business-logic-model.md:7`「**七個**方法……`write_body`」、`domain-entities.md:57`「七個方法（含 ADR-0015 §11 增設的 `write_body`）」、`functional-design-questions.md:10`「七個方法（含 ADR-0015 §11 的 `write_body`）」。**未改**：`nfr-requirements/tech-stack-decisions.md:36` 逐字仍為「C-3 的**六個方法**與錯誤型別引自 [ad:component-methods.md] §C-3」 |
| 1c | 誰呼叫 `write_body`？U-6 的規則與序列圖是否具名 | **通過** | U-6 `business-rules.md:155`（R-7 群）：「`write_status` / `write_field` / **`write_body`** \| C-3 \| ……**`write_body` 寫受管區塊進 issue body**（ADR-0015 §11 增設）」；序列圖 `business-logic-model.md:38`：「`└─► U-3 write_body（ADR-0015 §11）`」 |
| 1d | 寫入順序在 U-3／U-6／ADR 三側是否一致 | **通過** | ADR §11 :88「`write_status` → `write_field` → **`write_body`** → 回讀 `read_item` 取 `managed_block_hash`」；U-6 序列圖 :32→:36→:38→:39→:40 同序；U-6 R-5.10（`business-rules.md:88`）「照常走 `write_field` → `render` → `write_body` → 回讀 → `write_sync_state`」。三處同序 |
| 1e | **`write_body` 失敗的連帶後果：U-6 的規則有沒有真的寫下這一條** | **未通過（Critical C-1）** | 見下方 C-1。實測 grep U-6 四份產出正文對 **`Failed` 零命中** |
| 1f | 權限：`Issues: write` 是否在集合內、各單元 IAM 判定是否同步 | **權限在集合內（通過）；IAM 判定未同步（Major M-5）** | ADR-0015 §11 :86「所需權限 `Issues: write` 已在 ADR-0014 的集合內，不擴大權限面」，與 §8 更正後的四項集合（組織層 Projects／repo 內容／Issues／Pull requests）相容。但 U-3 `security-requirements.md:34`、U-8 同名檔 :35 兩處的 IAM 判定與此矛盾——見 M-5 |

#### 2. `Block.rejection_notice` 與 `format_version` bump

| # | 查證項 | 結論 | 依據 |
| --- | --- | --- | --- |
| 2a | **`Block` 現在幾欄？來源分配是否每欄都有來源、無遺漏無重複** | **通過（實數 7）** | 逐行數 `U-2/domain-entities.md:11-17`：`format_version`／`status`／`traceable_row`／`reason_category`／`decided_at`／`scope_note`／`rejection_notice` = **7**，與 :35「`Block` 現有**七個**欄位」相符。來源分配自行分派：**渲染器常數 1**（`format_version`，:46「不是傳入值」）＋ **`Decision` 3**（`status`／`traceable_row`／`reason_category`，:27「渲染時由 `Decision` 推導」）＋ **`Context` 3**（:40-44 的三欄推導表）= 7。無無源欄位、無雙重來源。:37 的重算說明（「六欄裡有二」→「七欄裡有三」）誠實且正確 |
| 2b | R-1.5 的可判定方式改寫後是否仍二元可判 | **通過** | `U-2/business-rules.md:17`：「兩個只在此欄不同的 `Context` 產生**可區分**的區塊文字，且兩者 `parse` 回來的 `Block.rejection_notice` 分別為該值與 `null`」——兩個子句都是 fixture 可判的等式，且第二個子句順帶補上 F2 要求的「`parse` 如何把它讀回來」。:21 逐字撤回「`null` 支輸出逐字相同」，:23「**保留的是 bump，撤回的是「逐字相同」**」。**F3 的不可同真已解除** |
| 2c | **「Bolt 1 首次上線時既有受管 item 數為 0」是否為真** | **通過（宣稱成立）** | 核對 `decisions.md:131-135` ADR-A7：「既有 **71 個未綁定** item 不處理，空欄位即『不受管』」「不對既有 71 項做任何寫入」；`requirements.md:203` A-7、:214 OOS-3、:80 FR-D2「既有 71 個未綁定 item 不被讀取也不被寫入」。那 71 個 item **沒有綁定編號、沒有受管區塊**，故「既有**受管** item 數為 0」與「既有 item 數為 71」兩個陳述指涉不同集合、**不衝突**。三處落點（`ADR-0015:137`、`component-methods.md:150`、`U-2/business-rules.md:23`）措辭一致，本項**不構成發現** |
| 2d | R-4 群三道互鎖是否涵蓋這次 bump | **通過** | `U-2/business-rules.md:69-73`：R-4.1（golden fixture 逐位元）→ R-4.2（`FORMAT_VERSION` 等於登錄表末筆）→ R-4.3（末筆含非空的重新基準化說明）。新增 `Block` 欄位會改變 `render` 輸出 ⇒ R-4.1 紅燈 ⇒ 必須更新快照 ⇒ R-4.2 紅燈 ⇒ 必須 bump ⇒ R-4.3 紅燈 ⇒ 必須登錄。**三道確實鎖住這次變更**，:77 的天花板（登錄表可寫成空殼）已誠實記載 |

#### 3. `Context` 的三個欄位與 `scope_note` 的取得

| # | 查證項 | 結論 | 依據 |
| --- | --- | --- | --- |
| 3a | U-1 的介面表、生命週期段、[Q1=A] 敘述是否一致、有無殘留「四個 output」 | **通過** | 介面表 `U-1/business-logic-model.md:32` 新增第五列 `scope_note`（實測 `grep -c "^| output"` = **5**）；:34-36 的更正 blockquote 明寫「這不改 [Q1=A] 的決定……`Decision` 的型別、`map` 的簽章與純函式性一字未動」；:38 同步改為「另有第五個 output `scope_note` 不屬 `Decision`」；`domain-entities.md:92` 由「四個 output」改為「**五個** output（`Decision` 的四欄 ＋ `scope_note`）」。**全 U-1 無「四個 output」殘留** |
| 3b | **`scope_note` 的值域有定義嗎？一個字串怎麼承載多行 stage 的差別** | **未通過（Major M-3）** | 見下方 M-3 |
| 3c | **`decided_at` 由 U-6 取本輪時刻——U-6 的規則裡有具名嗎** | **未通過（Major M-2）** | 實測 grep U-6 四份產出：**`decided_at` 零命中** |
| 3d | **`Context` 的三欄在 U-6 側是否都有寫者（契約端點三問）** | **未通過（Major M-2）** | 只有 `rejection_notice` 有（R-6.2b，`U-6/business-rules.md:194`）。`scope_note` 僅出現在序列圖 :27，且該處把它畫成 `map()` 的輸出——與 U-1 :32「**不進 `Decision`**、由 `parse` 推導、是 action 的第五個 output」矛盾。`decided_at` 完全沒有 |

#### 4. ADR-0015 的承載完整性（§1／§2／§6／§8／§11／§12 逐節）

| 節 | 指標是否存在 | 位置是否正確 | 內容是否相符 | 依據 |
| --- | --- | --- | --- | --- |
| §1 | ✅ | ✅ `bolt-plan.md:30`（PRE-1 表之後） | ✅ | 逐字「**PRE-1-b 由 ADR-0015 §1 增列**……本表先前只有五項……故上方『五項實測各一份記錄』現應讀作**六項**」——連衍生計數都一併更正 |
| §2 | ✅ | ✅ `bolt-plan.md:54`（Bolt 1 DoD）＋ :56 展開 | ✅ | :56 把「靜默丟失……沒有反向 PR、沒有紅燈、沒有通報」逐字寫進 DoD，與 ADR §2 :29 同義且明標「**本條要求核可者看見它**，不是技術檢查」 |
| §6 | ✅ | ✅ `component-methods.md:148`（§C-6 `parse` 列之後） | ✅ | 兩條候選修法（三態／`has_managed_marker`）與確認人（Bolt 1 gate）逐字對應 ADR §6 :45 |
| §8 | ✅ | ✅ `requirements.md:147`（NFR-S1 列內）＋ `bolt-plan.md:23`（PRE-1 第 1 項） | ✅ **本輪已補齊更正指令與閘門** | ADR §8 :57-60 現含編號的兩條更正指令（NFR-S1「三項」→**四項**、驗收判準「兩項」→「四項」；`bolt-plan.md` PRE-1 第 1 項「三項」→四項）＋「**確認人：Bolt 0 的 gate**，且必須在憑證鑄造之前」。iteration 3 F6 判的「只陳述事實而未給指令或閘門」**已解除**。`requirements.md:147` 與 `bolt-plan.md:23` 兩處指標與之逐字相符 |
| §11 | ✅ | ✅ `component-methods.md:93-99`（§C-3 表之後） | ✅ | 見上方 1a |
| §12 | ✅ | ✅ `component-methods.md:150`（§C-6 區） | ✅ | 逐字「型別為 `{ closed_at: ISO 8601 } \| null`……**這是一次格式變更**，須 bump `format_version` 並於同一個 PR 重新基準化（ADR-A6）」，與 ADR §12 :94-96 相符 |

**指標處數實算**：`grep -c "0015"` 於五份被 `Amends` 的檔 = `bolt-plan.md` **5**、`component-methods.md` **5**、`requirements.md` **2**、`components.md` **2**、`unit-of-work-story-map.md` **1** = **15 行**；併掉續行（`bolt-plan.md:56` 屬 :54 的展開、:93-99 為單一區塊）後為 **13 個獨立指標**，與 lead 的自述相符。**iteration 3 F5 判的「零命中」已解除。**

**U-8 的 P-1（權限實為四項）是否真的被 §8 涵蓋**：**是**。`U-8/nfr-requirements/security-requirements.md:29` 逐字「**該新 ADR 已存在：ADR-0015 §8 的「附帶」段逐字承載本缺口**（權限實為四項，`deploy.yml:174-175` 為本 repo 上正在運行的佐證）」；其 :20-25 的四項表與 ADR §8 :55／:58 的四項列舉逐項對應（組織層 Projects 讀寫／repo 內容寫入／Issues 寫入／**Pull requests 寫入**）。**F6 的「本輪無法查證」缺口已由本輪 dispatch 把該檔納入 `exempt` 而消除，查證結果為通過。**

**但 §13 的承載不完整——見 Critical C-2。**

#### 5. 其餘落地查證

| # | 查證項 | 結論 | 依據 |
| --- | --- | --- | --- |
| 5a | U-8 M-4：`notify`／C-5 是否已進 R-4c 方法表與錯誤表「通報」欄；**方法數自己數** | **通過** | `U-8/business-rules.md:109` 標題「本單元呼叫的**六個**上游方法」，表列 :113-118 逐行數為 **6**（`read_item`／`parse`／`content_hash`／`write_sync_state`／`commit_and_push`／**`notify`**）——標題與列數一致。錯誤表 `business-logic-model.md:48-53` 已加第四欄「**通報**」，三列外部失敗皆「**是**（C-5 `notify`）」，:55 的更正說明「**紅燈與通報是兩件事**」正確 |
| 5b | U-3 M-1：已撤回的「反向同步兜底」兩處是否都處理 | **通過** | `U-3/business-logic-model.md:54-56` 已改寫（「主敘事檔漏改，單獨查閱者會得到與原始 Critical 完全相同的錯誤印象」＋「**正確的敘述**：視窗內被覆寫的協作者改動**沒有任何兜底**……不是慢一輪，是永遠不會被偵測」）。`functional-design-questions.md` 的 Q2 選項本文依 `functional-design:c22` 不改寫，**已就地標註**（同檔的更正說明可追溯） |
| 5c | U-8 M-2：`branches-ignore` → `paths-ignore` 是否傳播到兩處 | **通過** | `U-8/functional-design-questions.md:20`（D-1 段）：「`branches-ignore` 過濾的是 PR 的 base 而非 head……故該過濾器**不排除任何 PR**；U-10b 實際採用的是 `paths-ignore`」；:65（E-2 成本論證）：「**成本論證的機制已更換**……支撐它的是 U-10b 的 `paths-ignore`……**只修理由不改決定**」。兩處皆到位且引用 `functional-design:c22` |
| 5d | U-2 F7：`Context`／R-1.5 是否傳播到另兩份產出；F8 前言範圍限定是否誠實 | **部分通過（Minor m-2）** | F8 **通過**：`business-rules.md:7` 已改為「**R-1.1～R-1.4** 四項皆為 [US-OQ-3] 定案……**R-1.5 是本站新增**……故下表共五條」，前言自身即可判。F7 **只落地 1/4**：資料流圖（`business-logic-model.md:19-30`）已補 `Context`／五個 output／`write_body`；但 `render` 的組成序列（:39-48）**仍是四步、無告示步驟**、邊界情形表（:80-87）**無 `rejection_notice` 列**、:93「本檔對上游的補充」**仍未列 `Context`**。`functional-design-questions.md` 已補 :31-34 三列裁定 ✅，但 :20 逐字仍為「受管區塊**必載的四項內容**」 |
| 5e | U-5：§5 的回填是否逐字相符 | **引用相符，但其結論已被本輪推翻（Major M-6）** | `U-5/business-logic-model.md:86` 引用 ADR-0015 §5、確認人 Bolt 3 的 gate，與 `ADR-0015:39-41` 逐字對應——**引用本身正確**。問題在同段的事實面已變，見 M-6 |

### 新引入的問題（本輪修正動作造成）

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| **C-1** | **Critical** | `U-3/business-logic-model.md:68`；`U-6/business-rules.md:75`（R-5.4）、`:88`（R-5.10）、`:195`（R-6.2c）；`U-6/business-logic-model.md:81-88`（錯誤表） | **`write_body` 是本輪新增的一個「可失敗」的寫入步驟，而它的 `Failed` 在呼叫端完全沒有處置——後果是 [US:S-6 AC 5] 的告示會被永久靜默丟棄。** U-3 已為它宣告了一條連帶規則：`business-logic-model.md:68` 逐字「`write_body` 失敗的連帶後果須被呼叫端看見：該輪受管區塊未更新 ⇒ U-6 的 R-5.4 回讀取得的仍是舊雜湊（或 `null`），故**該輪不得把新雜湊寫進 `SyncState`**，否則基準與看板現況脫鉤」。**但呼叫端沒有這條規則**：實測 grep U-6 四份產出正文，`Failed` **零命中**；R-5.4（`:75`）逐字「看板寫入成功後，**五欄一起回寫**」是無條件的；R-5.10（`:88`）逐字「照常走 `write_field` → `render` → `write_body` → 回讀 → `write_sync_state`」也沒有失敗分支；錯誤表（`business-logic-model.md:81-88`）五列為 `reverse_pending` 查詢失敗／`ExternalError`／`Aborted`+`CannotCreate`／`Rejected`／五種正常 `reason_code`——**沒有 `Failed` 列**。<br><br>**可達性與後果（每一步可逐字核對）**：`write_body` 依 `component-methods.md:97` 與 ADR §11 :84「與 `write_field` 同形：回傳值而非例外；失敗回 `Failed`，不連坐 Status 寫入」，且 `U-3/business-logic-model.md:68` 判它**不紅燈**。於是一次暫時性 API 失敗 ⇒ 受管區塊未更新，而 R-5.4 仍把五欄（含 `last_synced_at`）回寫。代入 R-6.2c（`U-6/business-rules.md:195`）逐字「告示只出現一次——寫入後該 intent 即離開 `reverse_rejected`（下一輪的查詢以 PR 關閉時間晚於 `last_synced_at` 為準；R-5.4 在該輪把 `last_synced_at` 推進到寫入時刻，使下一輪此條不再成立）」⇒ **告示永久遺失，無紅燈、無通報、無重試**。同一路徑上三欄也被寫成本輪 `Decision` ⇒ 下一輪 R-5.2 判無漂移 ⇒ R-5.5 不寫 ⇒ 該 intent 的受管區塊**永久停在舊內容**，[US-OQ-3] 的必載內容與 [req:FR-F3] 的 `[S]`／`— SKIP` 差別在其上永不出現。<br><br>**這正是本輪修正動作自己製造的**：`write_body` 把一個先前不存在的可失敗步驟插進寫入鏈，而「它失敗了誰接、`SyncState` 還能不能推進」沒有被問過——`project.md` 送審前自檢第 2 項（契約端點三問，範圍為整個 stage 產出）在新方法上再度落空。<br><br>**附帶：U-3 自己寫的那條規則本身也已過期。** 它說「不得把**新雜湊**寫進 `SyncState`」，而 R-5.4 自 2026-08-29T16:19:47Z 起改為「**寫入後回讀取得**」（`U-6/business-rules.md:75`、ADR-0015 §10），構造上根本不存在「新雜湊」——回讀到的必然等於看板現況，雜湊欄反而是唯一**不會**脫鉤的。真正的危害在 `last_synced_at` 與三欄，那一句瞄準了錯的欄位。<br><br>**修法**：在 U-6 新增一條規則（例如 R-5.11）：`write_body` 回 `Failed` 時，該輪**不得推進 `last_synced_at`、不得回寫三欄**（或至少不得清掉告示待送狀態），並交 C-5 `notify`；同步在 U-6 錯誤表增列 `Failed` 一列、在 U-3 把 :68 的「新雜湊」改為正確的欄位集合。**這是 [US:S-6 AC 5] 可滿足性的前提，須與 §11／§12 同批交付。** |
| **C-2** | **Critical** | `ADR-0015:114-127`（§13 的「排程分支的衝突」）；`U-6/business-rules.md:106`、`:118`（R-5.9）、`:134-139`；`bolt-plan.md:64`（Bolt 2 DoD）；`components.md:110` | **ADR-0015 §13 自陳 blocking 且「在拿到落點之前不可實作」，U-6 卻把它當成已完成的事實；而它指名的 Bolt 2 gate 在 `bolt-plan.md` 上沒有任何收件人。** ADR §13 :114-121 逐字：「**排程分支的衝突（已實測確認，非假設——2026-08-30T01:05:00Z）**：這是 §13 唯一未解的實作缺口，**判定為 blocking**」，並列出四條互相牴觸的事實（`schedule` 只在預設分支執行／本 repo 預設分支實測為 **`main`** 而非 `ut`／`commit_and_push` 契約是「只推觸發分支」／U-4 的 R-3.1 明訂「不得推 `ut`／`main`」），結論逐字「**U-7 在本節要求它回寫 `SyncState` 的同時，沒有任何合法的推送落點**……它使 §13 **在拿到落點之前不可實作**」，:123 「**兩個候選形狀，本 ADR 不裁定**」，:127「**確認人為 Bolt 2 的 gate**，且必須在 U-7 開工前定案」。<br><br>**但 U-6 以完成式陳述它**：`business-rules.md:118`（R-5.9）逐字「**`SyncState` 過期的唯一來源是 U-7 補平**，該來源已由 **ADR-0015 §13** 從源頭堵住……本單元因此**不需要**任何『已被補平』的例外判定」；:106「過期問題改從**源頭**解決」；:138「**由 U-7 當場回寫，不過期**……**不再需要「自癒」這個概念**」。一個 blocking、未裁定、可能無解的修法，在下游被寫成既成事實。<br><br>**而閘門是空的**：實測 `bolt-plan.md` 五處 `0015` 指標（:23、:30、:54、:56、:64）逐行核對，Bolt 2 的 DoD（:64）只載 **§3 與 §9**，**無 §13**；`components.md:110` 的 §13 指標只寫「元件集合**應含 C-4**」與確認人，**完全未提那個 blocking 的推送落點衝突**。於是 ADR 自己在 Context 段點名的失敗形狀——「在單元產出裡寫『指派 X，確認人為 Bolt N gate』，對已定稿的上游而言是**一張沒有收件人的便條**」——**在它自己最 blocking 的一節上原樣重演**，只是這次便條是 ADR 自己寫的。<br><br>**兩條分支都壞**：若該衝突未在 U-7 開工前定案 ⇒ U-7 不回寫 `SyncState` ⇒ U-6 的 `expected` 過期 ⇒ **iteration 2 Critical #9 的假 `Aborted` ＋ 假通報原樣復發**（[req:FR-C1] 為一個不存在的不符開 issue，而 `write_status` 其實該成功）；若改為推 `ut` ⇒ 直接違反 U-4 的 R-3.1 與 `component-methods.md:114` 的「**只推觸發分支**」。<br><br>**修法**：(1) 把 §13 的 blocking 缺口寫進 `bolt-plan.md` 的 Bolt 2 DoD（比照 §3／§9 的指標形式），明列「兩個候選形狀擇一定案」為 U-7 開工的前置；(2) 把 U-6 的 R-5.9／:106／:138 由完成式改為條件式（「**待 ADR-0015 §13 的推送落點定案後**成立；在此之前 `SyncState` 過期的風險仍在，本單元不另設例外判定的決定以該定案為前提」）；(3) `components.md:110` 的指標補上該 blocking 條款。 |
| **C-3** | **Critical** | `U-2/domain-entities.md:15`、`:50`、`:54`；`U-2/business-logic-model.md:42-44`；`U-2/business-rules.md:13`（R-1.1）、`:33`（R-2.3）、`:32`（R-2.2）；`component-methods.md:155` | **`Block.decided_at` 宣告為非 `null`，但 `render` 只在 `status = null` 的分支輸出它——最常走的 `mapped` 分支上 `parse` 取不回來，型別契約在該分支不成立。** 逐字對照四處：<br>① `domain-entities.md:15`：「\| `decided_at` \| **ISO 8601 字串** \| 該次判定的時間戳（[US-OQ-3] 定案的必載內容）\|」——**值域欄沒有 `\| null`**，而同表 :12／:13／:14／:17 四欄**全部明寫** `\| null`（`Status \| null`、`字串 \| null`、`ReasonCode \| null`、`{...} \| null`）。作者對可空性的標記是刻意且一致的，故此欄為刻意的非空宣告。<br>② `business-logic-model.md:42-44`（`render` 的組成序列第 2 步）：「非 `null` → 寫 Status 與 `traceable_row`。**為 `null` → 寫 `reason_code` 的原因類別與 `decided_at` 的 ISO 8601 時間戳**。」——`decided_at` **只在 `null` 支被渲染**；第 1、3、4 步分別是版本標記、`scope_note`、兩段固定說明，都不含它。<br>③ R-1.1（`business-rules.md:13`）「含目前 Status 與其 `traceable_row`；**或**機制決定不寫的原因類別與 ISO 8601 時間戳」與其上游正本 `component-methods.md:155`（[US-OQ-3] 定案）**同樣是二選一**——時間戳只在「不寫」那一支是必載內容。<br>④ 而 `domain-entities.md:54` 逐字「`decided_at`／`scope_note` **每輪必填**」，R-2.3（`business-rules.md:33`）「`decided_at` **在**涵蓋範圍內」，R-2.2（`:32`）「**任一欄位不同必得不同雜湊**」。<br><br>**四者不可同真**：`parse` 是 `render` 的反向（`business-logic-model.md:37` 逐字「`parse` 是它的反向」），一個沒有被渲染進文字的欄位無法被 parse 回來。在 `reason_code = "mapped"`（`status` 非 `null`，即**最常走的分支**）上，`parse` 只能給出 `decided_at = null`／缺席，直接違反 ① 的值域宣告與 ④ 的「每輪必填」，而 R-2.2／R-2.3 又要求它參與雜湊。<br><br>**這阻擋實作**：開發者寫 `render`／`parse` 時必須二擇一，而兩條路的代價不同、都超出 U-2 的職權——(a) 把值域改為 `ISO 8601 字串 \| null`（承認它只在一支存在，並同步改 :54 的「每輪必填」與 `Context.decided_at` 的語意）；(b) 讓 `render` 在**兩支**都輸出時間戳（那會改變區塊文字的形狀，且與 R-1.1／`component-methods.md:155` 的 [US-OQ-3] 逐字原文相牴觸，屬需要 ADR 承載的格式決定）。無法從現有文件推出該選哪一條，符合「開發者必須回頭問架構師」的判準。<br><br>**為什麼是本輪才浮現**：`decided_at` 本是原六欄之一，但 `Context` 於 2026-08-29T23:42:35Z 才被定義並寫下「每輪必填」，`Block` 於本輪被明確定為 `content_hash` 的完整輸入（:35-37 的重算、R-2.2 的逐欄要求），兩者疊加後這個矛盾才變成可機械判定的。iteration 3 查證 8「`Block` 六欄的來源分配是否無遺漏」判**通過**——那一項只問了「有沒有來源」，沒問「來源在每一條分支上都給得出值嗎」。 |

### 其餘發現

| # | 嚴重度 | 檔案:行 | 發現 |
| --- | --- | --- | --- |
| **M-2** | **Major** | `U-2/domain-entities.md:50`、`:54`；`U-6/business-rules.md:147-159`（R-7 群）、`U-6/domain-entities.md`（全檔）；`U-6/business-logic-model.md:27` | **`Context` 的三欄只有一欄有寫者——iteration 3 F4 的建議只落地了上游那一半。** F4 的 recommendation 逐字要求「**無論哪一支，U-6 的 R-7 群與 `Context` 組裝責任表都必須新增對應列，使『誰寫 `Context` 的每一欄』可被指名**」。上游半邊做了（U-1 第五個 output，見 3a），**下游半邊沒有**：實測 grep U-6 四份產出，**`decided_at` 零命中**；`scope_note` 只在序列圖 `:27` 出現一次。R-7 群（`:147-159`）——該表存在的目的逐字是「送審前自檢第 2 項（每個宣告的方法都要有具名呼叫者）」——列了 `render(Decision, Context)`（`:157`）卻**沒有任何一列說誰組 `Context`**；`U-6/domain-entities.md` 只有 `Config` 的組裝責任表，**沒有 `Context` 的**。而 `U-2/domain-entities.md:54` 逐字「**呼叫端是 U-6**……`decided_at`／`scope_note` 每輪必填」、`:50`「本輪判定的時刻。直接成為 `Block.decided_at`」——契約的**讀者端齊備、寫者端只有一句「呼叫端是 U-6」而 U-6 自己不知道**。這與 `write_body` 之前的 `render` 是完全相同的形狀，只是落在 `render` 的輸入側。<br>**附帶錯誤歸屬**：`U-6/business-logic-model.md:27` 序列圖逐字「`U-1 map(ParsedRecord, Config) ──► Decision ＋ scope_note`」，把 `scope_note` 畫成 `map()` 的輸出——與 `U-1/business-logic-model.md:32`（「**不進 `Decision`**」）、:36（「`map` 的簽章與純函式性一字未動」）及 `component-methods.md:34`（`map: (...) -> Decision`）三處直接矛盾。`scope_note` 是 **composite action 的第五個 output、由 `parse` 推導**，不是 `map` 的產物。 |
| **M-3** | **Major** | `U-1/business-logic-model.md:32`；`U-1/business-rules.md`（全檔）、`U-1/domain-entities.md`（型別段）、`U-1/functional-design-questions.md`（全檔）；`U-2/business-rules.md:14`（R-1.2） | **`scope_note` 是一個沒有值域、沒有推導規則、也無法承載多行差別的新 output。** 實測 grep U-1 三份產出：`business-rules.md` **0 命中**、`functional-design-questions.md` **0 命中**、`domain-entities.md` 僅 `:92` 生命週期一句。它**唯一**的定義處是介面表 `:32`：「字串 \| `[S]`（在 scope 內被跳過）與 `— SKIP`（不在 scope 內）的差別（[req:FR-F3]）。由 `parse` 解析出的 stage 行推導」。<br>三個具體缺口：<br>(a) **不在型別段**——`U-1/domain-entities.md` 的抬頭逐字「本檔定義 U-1 擁有的型別、它們的欄位語意與生命週期」，其型別段列了 `ParsedRecord`／`stages[]`／`Unparseable`／`Decision`／`Config`／`Config` 的承載形式，**沒有 `scope_note`**。<br>(b) **演算法沒有它**——`business-logic-model.md:62-69` 的 `parse` 六步（取 `intent_id`→`get_field` 四欄→取 `binding`→`list_stages`→R-2.4 下限檢查→組 `ParsedRecord`）與 `:44-58` 的主流程圖，**都沒有產出 `scope_note` 的步驟**。「由 `parse` 解析出的 stage 行推導」在演算法上無落點。<br>(c) **多行縮併未定義**——`ParsedRecord.stages` 是**陣列**（`domain-entities.md:22`），每個元素各自帶 `checkbox`（可為 `"S"`）與 `in_scope`（布林，`:29-33`），**多個 stage 可同時各自是 `[S]` 或 `— SKIP`**。把 N 行的差別壓成一個無格式的字串是一次未定義的化約：是列舉？是計數？是只取 `current_stage` 那一行？對照組 `field_value_for`（`:101`）明確錨定在單一 stage（「**該 stage** 的 `checkbox == "S"`」），`scope_note` 連錨點都沒有。<br>**連帶**：消費端 U-2 的 R-1.2 可判定方式（`business-rules.md:14`）逐字「兩個只在此處不同的 **`Decision`** 產生**可區分**的區塊文字」——但 `scope_note` 明訂**不進 `Decision`**（`U-1:32`），該可判定方式指向了錯的變數，改成第五個 output 之後未同步。 |
| **M-4** | **Major** | `U-3/business-rules.md`（全檔）、`:100`；`U-3/domain-entities.md:50`；`U-3/nfr-requirements/tech-stack-decisions.md:36` | **U-3 的規則檔對第七個方法零規則，另兩處衍生落點未同步。** (a) 實測 grep `U-3/business-rules.md`：`write_body` **0 命中**。其五個規則群 R-1（`read_item` 查找）／R-2（`write_status` 回讀）／R-3（`create_item` 首建）／R-4（`write_field`＋`ensure_field`）／R-5（權限邊界）**唯獨沒有新增方法的**，`:100` 的「與上游的對應」也**未引用 ADR-0015**。這使 `U-3/business-logic-model.md:68` 宣告的那條失敗語意（見 C-1）在本單元的**正式規則檔**裡沒有落點——`business-rules.md` 才是這個 stage 的規則正本。(b) `domain-entities.md:50` 的錯誤型別表逐字「\| `Failed { http_status, message }` \| **`write_field` 失敗** \| 不影響 Status 寫入 \|」——未加 `write_body`，而同單元 `business-logic-model.md:68` 已寫「`write_field` **與 `write_body`** 專屬」，同一單元兩份產出對同一個型別的產生點給出不同答案。(c) `nfr-requirements/tech-stack-decisions.md:36` 逐字「C-3 的**六個方法**與錯誤型別引自 [ad:component-methods.md] §C-3」——方法數殘留。三處合起來正是 `units-generation:rev1-L1` 的形狀：主計數改對了（7 ✓），衍生落點沒跟上。 |
| **M-5** | **Major** | `U-3/nfr-requirements/security-requirements.md:30`、`:34`；`U-8/nfr-requirements/security-requirements.md:24`、`:35`；`U-1/…/security-requirements.md:11`、`U-5/…/security-requirements.md:7` | **本輪的兩個修正各自推翻了一個 IAM 判定，兩處都沒更新。** (a) **U-3**：`:34` 逐字「**本單元只需要 Projects 那一半**，但它拿到的是完整的憑證」——而 ADR-0015 §11 把 `write_body`（寫 **issue body**）交給 U-3，U-3 自己的 `business-logic-model.md:15` 逐字承認「**權限**：`Issues: write`，已在 ADR-0014 的集合內」。同一單元的兩份產出直接矛盾，而其中一份是該單元的 IAM 正式記載。(b) **U-8**：`:35` 逐字「本單元用到上表第 1、2、4 項；**不需要第 3 項**」——而本輪 M-4 修正（2026-08-30T00:57:28Z）已把 `notify`（C-5，**開 issue**）加進 `business-rules.md:118` 的六方法表與 `business-logic-model.md:50-52` 的三列「通報」欄；同一份檔案的 `:24` 自己把第 3 項的用途逐字寫成「**通報 issue**、讀寫受管區塊」。(c) **附帶**：`U-1/…:11`、`U-3/…:30`、`U-5/…:7` 三處仍以「**三項**」陳述權限集合，而 ADR-0015 §8 已更正為**四項**並在 `requirements.md:147`／`bolt-plan.md:23` 補上指標——per-unit 的 IAM 記載未在同一批傳播。<br>**為什麼是 Major 而非 Minor**：ADR-0006 的 IAM 是本專案 hard constraint（`project.md ## Mandated` 逐字要求每項變更檢查四面向並在該 stage 產出中明列處置），而憑證於 Bolt 0 鑄造、事後變更需組織管理者操作（ADR-0015 Risk 段、`external-dependency-map.md` E-1）。一份說「本單元不需要 Issues 寫入」的 per-unit IAM 記載，正是最小權限盤點時會被拿來用的東西。 |
| **M-6** | **Major** | `U-5/business-logic-model.md:82`、`:86`；`U-6/business-rules.md:179` | **兩處仍以「U-8 的元件集合不含 C-5」為據，而 ADR-0015 §5 已把 C-5 補進反向路徑、U-8 也已接住。** `U-5/business-logic-model.md:82` 逐字「\| U-8 \| **不呼叫** \| 其元件集合（[ad:components.md]）**不含 C-5** \|」；`:86` 整節標題逐字「**U-8 不呼叫 C-5 的連帶後果（誠實記載）**」，內文宣稱「反向同步的外部失敗只會讓 workflow 紅燈，**不會產生通報 issue**。這使 [req:FR-E1]／[US:S-8 AC 1] 的『外部失敗 → issue』保證在反向路徑上**不成立**」——**而同一段的下一句就引用了讓它成立的 ADR-0015 §5**。事實面已變：`components.md:112` 已補 §5 指標（「元件集合**應含 C-5**」）、`U-8/business-rules.md:118` 的 R-4c 已列 `notify`／C-5、`U-8/business-logic-model.md:48-55` 的錯誤表已有三列「是（C-5 `notify`）」。U-6 `business-rules.md:179` 同句：「U-8 的元件集合不含 C-5，不在此列。」<br>**後果**：U-5 的正文向讀者宣告一個**已於本輪關閉**的缺口仍然開著，而那句話是 U-5 的 R-1 表「`ExternalError` 無條件是通報」的唯一限定語——限定語過期後，U-5 與 U-8 對同一條路徑給出相反的描述。依 `functional-design:c22`，決定（U-8 是否呼叫 `resolve_if_open`）可以不改，但**理由必須就地標註為不成立**。 |
| **M-7** | **Major** | `component-methods.md:176`（§C-7 區）；`ADR-0015`（全檔）；`component-methods.md:167-174`（`ReconcileReport`） | **斷掉的交叉引用：`undecidable` 的唯一指標指向一個不承載它的 ADR 節。** `component-methods.md:176` 逐字「另 **§12 相關**：`ReconcileReport` 亦須含 `undecidable: [intent_id]`（G-1，[US:S-2 AC 4]）」。實測 `grep -n "undecidable" ADR-0015` → **0 命中**；`grep "^### "` 確認 §12 的標題逐字是「`Block` 增設 `rejection_notice` 欄位，並確認它是一次 `format_version` bump」，全節與 `ReconcileReport` 無關。而 `ReconcileReport`（`:167-174`）逐行核對確實**仍無 `undecidable` 欄位**（有 `unparseable`），[US:S-2 AC 4] 要求的「無法判定」清單因此仍無承接——`units-generation:260822-ug-L2` 指派的正是這個缺口，本輪給它的指標卻解析不到。**加重情節**：該行位於 `:166` 開啟、`:177` 關閉的 code fence **之內**，會被渲染成 `ReconcileReport` 型別區塊裡的字面文字，且其確認人（「Bolt 2 的 gate」）是掛在 §7 的 `latency_samples` 上的，`undecidable` 這一句沒有自己的閘門。 |
| **m-1** | Minor | `U-2/domain-entities.md:61` | **已被推翻的「必要性論證」原樣保留。** 逐字「若它不改變雜湊，U-6 的 R-5.4 回寫後看板內容已變而記錄的雜湊未變，U-8 下一輪會把機制自己寫的告示讀成人為變更並開一則反向 PR」。iteration 3 F2 的 (d)(e) 已證此句兩個支點皆不成立：R-5.4 自 2026-08-29T16:19:47Z 起以**寫入後回讀**取雜湊（`U-6/business-rules.md:75`、ADR-0015 §10），兩端走同一條 `read_item → parse → content_hash`，「看板已變而記錄未變」**構造上不可能**；且若告示不進 `Block`，比對兩側同樣看不到它 ⇒ 雜湊相等 ⇒ **不會**開 PR，與該句結論相反。F2 的 (b)（計數）已修（見 2a），(d)(e) 未修。**決定本身正確且已由 §12 獨立支撐**（`Block` 結構變更本身即 ADR-A6 意義下的格式變更），故依 `functional-design:c22` 只需就地標註該理由不成立，不必改決定。 |
| **m-2** | Minor | `U-2/business-logic-model.md:39-48`、`:80-87`、`:93`；`U-2/functional-design-questions.md:20` | **F7 的四個子項只落地一個**（詳見 5d）。最要緊的是 `render` 的組成序列（`:39-48`）——那是實作者取用的逐步規格——**仍是四步、完全沒有 R-1.5 的條件性告示段**；`:48` 的「第 2 步的二分是**窮盡的**……所以不存在第三支」在 R-1.5 之後字面仍成立（告示是附加段而非第三支），但讀者無從得知渲染器多了一段條件輸出。邊界情形表（`:80-87`）無告示列；`:93`「本檔對上游的補充」列了「`Block` 的欄位結構、`format_version` 的內嵌與 `parse` 的版本分派」，**未列 `Context`**（本批最大的新增）。`functional-design-questions.md:20` 逐字仍為「受管區塊**必載的四項內容**」。iteration 2 對 U-2 的唯一 Major、iteration 3 的 F7，與本項是**同一個檔案、同一種失誤的第三次**。 |
| **m-3** | Minor | `ADR-0015:5`（`Amended:`）、`:6`（`Amends:`） | **ADR 的自述與實際改動不符（`functional-design:c17`）。** `Amended:` 逐字「新增 **§11、§12**，並補齊 §8 的更正指令與閘門」——**未提 §13**，而 §13 是本輪唯一自陳 blocking 的一節（`:100-127`，其內部時間戳 2026-08-30T00:57:28Z 與 01:05:00Z 皆晚於 00:48:38Z 那一批，確為本輪新增）。`Amends:` 點名 `component-methods.md` 的部分逐字只有「`parse` 簽章與 §C-7 `latency_samples`」，**未含 §11 修訂的 §C-3、§12 修訂的 §C-6**——即本輪兩項最重的修訂不在 `Amends` 清單上。實數：`grep "^### "` 確認 ADR 共 **13** 節（iteration 3 當時為 10 節）。 |
| **m-4** | Minor | `component-methods.md:143-151`（§C-6）、`:166-177`（§C-7） | **兩處指標插入造成 markdown 結構破壞**（`team.md ## Mandated` 的「內容驗證」要求建檔前驗證結構與特殊字元）。(a) §C-6 的方法表在 `:146`（`parse` 列）之後被 `:147` 空行與 `:148-150` 的 blockquote 截斷，`:151` 的 `content_hash` 列因此**脫離表格**，會被渲染成孤立的表格片段而非該表的第三列。(b) §C-7 的 §7 指標（`:176`）落在 `:166` 開啟、`:177` 關閉的 code fence **之內**，會被渲染成 `ReconcileReport` 型別定義裡的字面文字（並使 M-7 的錯誤引用更不容易被看見）。兩者皆為本輪回填動作造成。 |

### 契約端點三問（本輪三個新增項）

| 新增項 | 誰擁有／誰寫 | 誰呼叫／誰讀 | 誰清／失敗時誰接 | 判定 |
| --- | --- | --- | --- | --- |
| `write_body`（方法） | C-3 / U-3（`component-methods.md:93-99`、`U-3/business-logic-model.md:7`）✅ | U-6（`U-6/business-rules.md:155`、序列圖 `:38`）✅ | **無人**——`Failed` 在 U-6 零命中，U-3 宣告的連帶規則在呼叫端不存在 ❌ | **C-1** |
| `Block.rejection_notice`（欄位） | U-6 R-6.2b 填 `Context`（`U-6/business-rules.md:194`）✅ | U-2 R-1.5 渲染、`parse` 讀回（`U-2/business-rules.md:17`）✅ | R-6.2c 的一次性離開 `reverse_rejected`（`:195`）✅——**但該收斂騎在 `write_body` 成功之上** ⚠ | 三問齊備，唯受 C-1 波及 |
| `scope_note`（action output） | U-1 composite action（`U-1/business-logic-model.md:32`）⚠ **無推導規則、無值域** | U-6 轉交（**未具名**）→ U-2 `Context.scope_note`（`U-2/domain-entities.md:51`）❌ | 每輪重算，不需清 ✅ | **M-2 ＋ M-3** |

### 可算的數字（實算，非引述）

| 項目 | 實算值 | 方法 | 文件宣稱 | 一致？ |
| --- | --- | --- | --- | --- |
| `Block` 欄數 | **7** | 逐行數 `U-2/domain-entities.md:11-17` | 「七個欄位」（`:35`） | ✅ |
| `Block` 的來源分配 | 常數 1 ＋ `Decision` 3 ＋ `Context` 3 = **7** | 逐欄分派（`:27`／`:40-44`／`:46`） | 「三個不可能從 `Decision` 推出來」（`:35`） | ✅ 無遺漏無重複 |
| U-3 方法數 | **7** | `component-methods.md` §C-3 表 6 列 ＋ `:97` 的 `write_body` | 「七個方法」（三處） | ✅（但 `tech-stack-decisions.md:36` 殘留「六個」，M-4） |
| U-8 方法數 | **6** | 逐行數 `U-8/business-rules.md:113-118` | 「六個上游方法」（`:109`） | ✅ |
| U-1 action output 數 | **5** | `grep -c "^\| output" U-1/business-logic-model.md` = 5 | 「五個 output」（`domain-entities.md:92`） | ✅ |
| ADR-0015 節數 | **13** | `grep "^### "` 逐行 | `Amended:` 只列 §11、§12 | ❌ m-3 |
| ADR-0015 就地指標 | **15 行／13 個獨立指標** | `grep -c "0015"` 五檔：5＋5＋2＋2＋1 | 「13 處」 | ✅ |
| `undecidable` 在 ADR-0015 的出現次數 | **0** | `grep -n "undecidable"` | `component-methods.md:176` 稱「§12 相關」 | ❌ M-7 |

### Summary

**整組 NOT-READY（3 Critical、6 Major、4 Minor）。** iteration 3 的 6 個 Critical 在**規則文字**層面確實全部到位——`write_body` 已由 ADR-0015 §11 增設且三側寫入順序一致、`Block` 已增為七欄且來源分配無缺、R-1.5 的「逐字相同」已撤回而 bump 保留且互鎖涵蓋、`scope_note` 的第五個 output 已增設、13 個就地指標實測存在且內容相符、§8 已補齊可執行的更正指令與閘門、U-8 的 `notify` 與 `paths-ignore` 兩項必修完整落地。「既有受管 item 數為 0」這個宣稱經 ADR-A7／A-7／OOS-3 三方核對**成立**（那 71 個 item 未綁定、無受管區塊，與「受管 item」是不同集合）。

但三個 Critical 全部落在**本輪修正動作的鄰接面**，與前三輪形狀完全相同：**C-1** 是把 `write_body` 這個可失敗的新步驟插進寫入鏈，卻沒問「它失敗了誰接」——`Failed` 在 U-6 零命中，而 R-6.2c 的「告示只出現一次」騎在該次寫入成功之上，於是一次暫時性 API 失敗就讓 [US:S-6 AC 5] 的告示**永久靜默消失**，同時把受管區塊凍在舊內容；**C-2** 是 §13 這一節自陳 blocking、不裁定、「在拿到落點之前不可實作」，而 U-6 用完成式寫「已從源頭堵住」，且它指名的 Bolt 2 gate 在 `bolt-plan.md` 上**沒有任何指標**——ADR 自己 Context 段點名的「沒有收件人的便條」在它最 blocking 的一節上重演；**C-3** 是 `Context` 定義下「每輪必填」的 `decided_at` 與 `render` 只在 `null` 支輸出它兩件事撞在一起，使 `Block.decided_at` 的非空值域在最常走的 `mapped` 分支上無法成立，開發者必須回頭問才知道該改值域還是改區塊格式。

六個 Major 中有四個是**同一種**跨檔傳播失敗：`Context` 的寫者只補了上游一半（M-2）、`scope_note` 有介面沒有規則與值域（M-3）、`write_body` 沒有進 U-3 的規則檔與另兩處衍生落點（M-4）、以及兩個 IAM 判定被自己的修正推翻而未更新（M-5）。M-6 與 M-7 則是「引用還在、被引用的事實已變」——U-5／U-6 仍以「U-8 不含 C-5」為據，`undecidable` 的指標指向一個不承載它的節。

建議處理順序：**C-1 先**（它決定 §11／§12 這條剛建好的鏈在失敗路徑上會不會靜默斷掉，且修法要與 §11／§12 同批交付）→ **C-3 次之**（它是 `render`／`parse` 的實作阻塞，且選項 (b) 會牽動格式決定，須先定案再畫最終區塊形狀）→ **C-2 再次之**（純承載機制，但必須在 U-7 開工前落到 `bolt-plan.md` 上）→ Major 群一併掃：本輪請按**事實**列舉（「`write_body` 的失敗語意」「`Context` 的三個欄位」「U-3 的方法數」「權限集合」「U-8 是否含 C-5」），每個事實把它在本 stage 的**每一種表達形式**各開一次檔，而不是 grep 本輪改過的字串——M-4 的三處與 M-5 的兩處都不含本輪改過的任何字串，這正是 `units-generation:260822-ug-L1` 補強那條規則要防的形狀。

## Review (Iteration 5 — 變更面驗證，契約與格式)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-30T02:30:51Z
**Iteration**: 5
**涵蓋單元**: U-1 / U-2 / U-3 / U-5 / U-8

> **本輪只驗變更面**，不重審前四輪已通過的部分。先逐字讀本檔的 `## Review (Iteration 4 …)` 段作為對照，再逐檔（確切路徑，無目錄操作）讀 U-1／U-2／U-3／U-5／U-8 的 `functional-design/` 與 `nfr-requirements/` 產出。另因 dispatch 第 7 項明文要求做 `write_body` 的契約端點三問（「誰負責先跑 `parse`」），開了 **U-6 的 `business-rules.md`** 這一份兄弟檔；以及 ADR-0015 全文、`component-methods.md`、`services.md`、`requirements.md` 的 NFR 段。
>
> **結果：1 Critical、5 Major、10 Minor。** Critical 與四個 Major 全部落在本輪新增的內容上（U-3 的 R-6 群、U-1 的 R-6 群、U-2 的 `decided_at` 值域、U-5 的 U-8 那一列）——**與前四輪形狀完全相同：修正動作本身帶進下一個缺陷**。

### 逐單元判定

| 單元 | Verdict | 一句理由 |
| --- | --- | --- |
| **U-1** | **READY（附 2 項必修）** | R-6 群補齊了 `scope_note` 的值域與推導（M-3 的 (a)(c) 已解），但**同一檔出現兩個 `## R-6`**（新群 vs 既有的「總函式性」），使 `business-logic-model.md:95` 的交叉引用同時指向兩處（M-1）；權限集合的「三項」殘留未隨 ADR-0015 §8 更新（M-5） |
| **U-2** | **READY（附 1 項必修）** | `Block` 實數 7 欄、來源分配無缺無重、`decided_at \| null` 的讀法經 `component-methods.md:157` 逐字核對**成立**、`render` 五步與 R-1 群一致、m-1 的撤回正確——本輪主線全部通過；殘留為 ADR-0006 audit-logging 判定未隨自己的值域變更重判（M-4） |
| **U-3** | **NOT-READY** | **1 Critical**：R-6.2／R-6.3 要求「只覆寫受管標記界定的區塊／有標記則就地替換」，而全設計**沒有任何方法或規格給出標記的形式或跨度**（C-1）；**1 Major**：R-6.3 指名的「呼叫端須先經 `parse` 判定」在唯一呼叫端 U-6 零命中，且 `write_body` 的簽章無參數可承接該判定（M-2） |
| **U-5** | **READY（附 2 項必修）** | M-6 的修正**改過頭**：把 U-8 寫進 **`resolve_if_open` 的呼叫者**表，而 ADR-0015 §5 補的是通報鏈、U-8 的 R-4c 六方法只有 `notify`（M-3）；權限「三項」殘留（M-5） |
| **U-8** | **READY** | 本輪指定的三項全部通過且經實數複驗：R-4c 標題「六個」＝表列 6（自行逐行數）、錯誤表「通報」欄三列到位、`security-requirements.md:35` 的「不需要第 3 項」已改為「用到上表**全部四項**」並附推翻理由。本單元自身無本輪新增缺陷 |

**整組 NOT-READY**：任一 Critical 即整組 NOT-READY。

### 逐項查證（dispatch 指定的 1–11 項）

| # | 查證項 | 結論 | 依據（檔案:行 ＋ 逐字引文） |
| --- | --- | --- | --- |
| **1** | `Block` 增設 `rejection_notice`；**自己數欄數**並逐欄確認來源無缺無重 | **通過（實數 7）** | 逐行數 `U-2/domain-entities.md:11-17`：`format_version`／`status`／`traceable_row`／`reason_category`／`decided_at`／`scope_note`／`rejection_notice` = **7**，與 `:39`「`Block` 現有**七個**欄位（原六個 ＋ ADR-0015 §12 增設的 `rejection_notice`）」相符。來源自行分派：**渲染器常數 1**（`format_version`，`:50`「不是傳入值」）＋ **`Decision` 3**（`status`／`traceable_row`／`reason_category`，`:31`「渲染時由 `Decision` 推導」）＋ **`Context` 3**（`:44-48` 的三欄表）= **7**。無無源欄位、無雙重來源。`:41` 的「六欄裡有二 → 七欄裡有三」重算誠實且正確 |
| **2a** | `Block.decided_at` 補 `\| null`；**核對 [US-OQ-3] 的「或」讀法** | **通過** | `component-methods.md:157` 逐字：「目前的 Status 與其對照表列（`traceable_row`），**或**機制決定不寫的原因類別與 **ISO 8601 時間戳**。」——時間戳字面上只掛在「決定不寫」那半支，**讀法成立**。`U-2/domain-entities.md:15` 現為「ISO 8601 字串 \| `null`」＋「**`status` 為 `null` 時非空；`status` 非 `null` 時為 `null`**」，`:23` 的理由（「改格式等於擴張一個已核可的必載清單」）與該原文一致 |
| **2b** | `decided_at` 與 `reason_category`「同進退」是否與 `render` 組成序列一致 | **通過** | `U-2/domain-entities.md:19`「`decided_at` 與 `reason_category` **同進退**（兩者都只出現在「決定不寫」那一支）」；`U-2/business-logic-model.md:43-44` 第 2 步：「非 `null` → 寫 Status 與 `traceable_row`。／為 `null` → 寫 `reason_code` 的原因類別**與 `decided_at` 的 ISO 8601 時間戳**。」——兩欄確實同支出現。`:49` 的「`decided_at` 只出現在第 2 步的 `null` 支」與值域宣告一致 |
| **2c** | **附帶**：「`mapped` 分支雜湊更穩定」的副作用是否與 U-8 的 R-1.1、R-2.3 的 churn 論述相容 | **相容，但兩處敘述未同步（m-1）** | 相容性成立：U-8 的 R-1.1（`U-8/business-rules.md:9`）比的是「看板現況雜湊 ↔ `SyncState` 記錄的雜湊」，而 ADR-0015 §10 已把記錄端改為**寫入後回讀**，兩端同路徑，`decided_at` 在哪一支出現都不影響等價性。**但**：`U-2/business-logic-model.md:88` 的邊界情形表逐字仍為「兩次判定語意相同、時間不同 \| 雜湊**不同**，但不會重寫」——該列在 `mapped` 分支上**已經不成立**（該分支的 `Block` 不含時間戳，雜湊會**相同**）；`U-2/business-rules.md:36` 與 `U-2/domain-entities.md:94` 的 R-2.3 churn 敘述同樣未加分支限定，與 `domain-entities.md:23` 新寫的「只作用在不寫分支上」互相矛盾 |
| **3** | R-1.5 的可判定方式改寫後是否仍二元可判；R-1 群前言的範圍限定是否誠實 | **通過** | `U-2/business-rules.md:17`：「兩個只在此欄不同的 `Context` 產生**可區分**的區塊文字，且兩者 `parse` 回來的 `Block.rejection_notice` 分別為該值與 `null`」——兩個子句皆為 fixture 可判的等式，二元可判。前言 `:7`「**R-1.1～R-1.4** 四項皆為 [US-OQ-3] 定案……**本站一項未增未減**；**R-1.5 是本站新增**……故下表共五條」——我逐條把 R-1.1～R-1.4 對回 `component-methods.md:157-160`，**四條逐字對應**，該範圍限定**誠實** |
| **4** | `render` 組成序列由四步改為五步 | **通過** | `U-2/business-logic-model.md:41-47` 現為五步：①版本標記 ②`status` 二分（含 `decided_at` 只在 `null` 支）③`Context.scope_note`（具名，並指向「U-1 的 R-6 群」）④`Context.rejection_notice` 非 `null` 時的告示段（R-1.5）⑤兩段固定說明。與 `business-rules.md` 的 R-1.1～R-1.5 逐條對得上，與 `domain-entities.md` 的 `Block`／`Context` 兩表逐欄對得上。`:51` 的更正說明與實際改動一致 |
| **5** | `domain-entities.md` 撤回「必要性論證」是否正確、新理由是否成立 | **通過** | `U-2/domain-entities.md:67` 撤回逐字：「**該情境在 R-5.4 改為回讀取值之後構造上不可能**——U-6 記錄的雜湊來自寫入後的 `read_item`，讀到的就是含告示的區塊，兩者必然一致。」我回頭核對 `U-6/business-rules.md:75`（R-5.4「`managed_block_hash` ＝ 寫入後再呼叫一次 `read_item`……」）與 ADR-0015 §10 —— **撤回正確**。新理由（`:69`「它是 `Block` 的一部分，沒有任何規則把它排除在雜湊之外」）在 R-2.1「`content_hash` 的輸入是 `Block`」之下**成立**，且與 `decided_at` 的處置同形 |
| **6a** | R-6.2 的兩類蒐集是否窮盡；`in_scope` 真且 `checkbox` 為 `"x"`／`" "` 落在哪 | **通過（刻意非窮盡，且正確）** | `U-1/business-rules.md:81`：`skipped-in-scope` ＝ `in_scope` 真且 `checkbox == "S"`；`out-of-scope` ＝ `in_scope` 假。`in_scope` 真且 `checkbox ∈ {" ","x","-","?","R"}` 的 stage **兩類皆不入**——這是**正確的**：本欄位承載的是 [req:FR-F3] 的「`[S]` 與 `— SKIP` 的差別」，正常執行的 in-scope stage 不屬於那個差別。兩類是**蒐集**而非**分割**，不需窮盡 `stages[]` |
| **6b** | R-6.3 的固定格式能否被 `parse` 原樣取回；slug 含 `,`／`;` 會怎樣 | **通過（但依賴一個未寫下的前提）** | `U-1/business-rules.md:90` 的連帶約束逐字要求「`parse` 必須能從區塊文字把這個字串**原樣**取回（round-trip）」。**round-trip 成立**：`Block.scope_note` 是**單一字串**，U-2 的 `parse` 只需整段取回、不需解析其內部結構，故 slug 內的 `,`／`;` 不破壞 round-trip。**換行才會破壞**，而 R-2.1 逐行解析保證 slug 不含換行。前提是「`parse` 取整欄而非再切分」——這一點兩邊都沒寫，但也沒有任何規則要求切分，故不列為發現 |
| **6c** | R-6.4「依出現順序、不排序」對雜湊穩定性是否足夠 | **通過** | 給定同一份 record 內容，`stages[]` 的順序即 `## Stage Progress` 的行序，**決定性**；同一 record 連續兩輪必得同一 `scope_note`、同一 `Block`、同一 sha256。R-6.4 自己寫明理由（「順序一變雜湊就變」）正確。**但**見 m-6：`scope_note` 進雜湊卻**不在** U-6 R-5.2 的漂移三欄內 |
| **6d** | 型別段新增的 `scope_note` 條目與介面表第五個 output 是否一致 | **通過** | `U-1/domain-entities.md:59-61`（新增的型別段）「字串，由 `ParsedRecord.stages` 純函式推導……**不是 `Decision` 的欄位**……消費者是 U-6（轉交進 `Context`）與 U-2（渲染進 `Block.scope_note`）」與介面表 `business-logic-model.md:32`「由 `parse` 解析出的 stage 行推導，**不進 `Decision`**」一致。M-3 的 (a) 已解。output 數自數 `:28-32` = **5**，與 `domain-entities.md:96`「**五個** output」相符 |
| **7a** | U-3 新增 R-6 群（`write_body`）：R-6.1～R-6.5 是否可實作 | **未通過（Critical C-1）** | 見 C-1。R-6.2／R-6.3 要求定位並就地替換受管區塊，而 U-2 的三個方法（`render`／`parse`／`content_hash`）**無一回傳標記的字面或跨度**，全 stage 產出亦無標記語法規格 |
| **7b** | **誰負責先跑 `parse`（U-3 還是 U-6）——契約端點三問** | **未通過（Major M-2）** | `U-3/business-rules.md:95`（R-6.3）逐字：「呼叫端須先經 C-6 `parse` 判定（[ad:services.md]「不得重複附加區塊——`parse` 先跑再 `render`」）」。上游原文核對通過：`services.md:25` 逐字「不得重複追加受管區塊（C-6 的 `parse` 先於 `render`）」。**但呼叫端沒有這一步**：`U-6/business-rules.md:183-206` 的 R-7 群（該表存在的目的逐字是「每個宣告的方法都要有具名呼叫者」）**沒有 `parse` 這一列**；R-5.10 (a) 的寫入鏈逐字為「`write_field` → `render` → `write_body` → 回讀 → `write_sync_state`」，**無 `parse` 步驟**。且 `write_body: (binding, block_text) -> WriteResult` **無參數可承接判定結果** |
| **7c** | `Failed` 列已含 `write_body`；`tech-stack-decisions.md` 方法數由六改七 | **通過** | `U-3/domain-entities.md:50`：「`Failed { http_status, message }` \| `write_field` **或 `write_body`** 失敗 \|……呼叫端依 U-6 的 **R-5.12** 不得回寫 `SyncState`」；`U-3/nfr-requirements/tech-stack-decisions.md:36`：「C-3 的**七個**方法（含 ADR-0015 §11 增設的 `write_body`，2026-08-30T01:31:09Z 更正）」。**交叉引用 R-5.12 實地驗證存在**：`U-6/business-rules.md:115` 逐字「**寫入鏈中任一步失敗時，本輪不呼叫 `write_sync_state`**（`write_status` 回 `Aborted`／`write_field` 或 `write_body` 回 `Failed`／回讀拋 `ExternalError` 皆同）」——iteration 4 的 C-1 **已實質關閉** |
| **8** | U-5 的「U-8 不呼叫 C-5」改為「呼叫」；三份產出是否一致；U-8 的 R-4c 與「通報」欄；**自己數 U-8 方法數** | **部分通過（Major M-3）** | **U-8 側全部通過**：`U-8/business-rules.md:109` 標題「本單元呼叫的**六個**上游方法」，逐行數 `:113-118` = **6**（`read_item`／`parse`／`content_hash`／`write_sync_state`／`commit_and_push`／**`notify`**），標題與列數一致；`U-8/business-logic-model.md:48-53` 錯誤表第四欄「通報」三列外部失敗皆「**是**（C-5 `notify`）」。**U-5 側未通過**：見 M-3——`U-5/business-logic-model.md:74` 該節標題逐字是「**`resolve_if_open` 的呼叫者**」，而 `:82` 把 U-8 填成「呼叫」並以 `notify` 的落地當依據 |
| **9a** | U-3 的「只需要 Projects 那一半」更正 | **通過** | `U-3/nfr-requirements/security-requirements.md:38` 逐字：「**「本單元只需要 Projects 那一半」已被本 stage 自己的改動推翻**……ADR-0015 §11 為 §C-3 增設 `write_body`……需要 **`Issues: write`**」，`:36` 同步改為「本單元需要 Projects 讀寫**與 Issues 寫入**兩項」 |
| **9b** | U-8 的「不需要第 3 項」更正 | **通過** | `U-8/nfr-requirements/security-requirements.md:35` 逐字：「本單元用到上表**全部四項**。**先前寫「不需要第 3 項（Issues 寫入）」，已被本 stage 自己的改動推翻**……開通報 issue 需要 `Issues: write`」 |
| **9c** | **五份 `security-requirements.md` 的 §8 指標（權限四項）** | **未通過（Major M-5，1/3）** | 逐檔開啟後的實況：**U-3 已補**（`:32` 一整段「**權限集合現為四項（ADR-0015 §8）**……第四項為 `Pull requests: write`」，與 ADR-0015 §8 `:56`／`:59` 的四項列舉逐項相符）；**U-8 本就正確**（`:20-25` 四項表 ＋ `:29` 指向 §8）；**U-2 不適用**（IAM 判定為「不適用」，全檔無權限計數宣稱）；**U-1 未補**——`:11` 逐字仍為「（**ADR-0014 更正後為三項**：組織層 Projects 讀寫 ＋ repo 內容寫入 ＋ Issues 寫入）」，全檔對 `0015` **零命中**；**U-5 未補**——`:7` 逐字「權限集合已更正為**三項**」、`:42` 「須同步改為**三項**」（`:13` 雖引用 §8，但那是「驗收判準欄補指標」這件事的承載，不是四項計數的更正）。iteration 4 M-5(c) 點名的三處（U-1／U-3／U-5）**只修了 U-3** |
| **10a** | ADR-0015 §14 新增、`Amended:`／`Amends:`、節數 14 | **部分通過（Minor m-7）** | §14 存在（`:130`「§自訂欄位格式的前綴集合缺 `undecidable` 的對應」），內容與 `component-methods.md:60` 的指標**逐字相符**。節數自數 `### ` 標題 = **14**（§1 `:21`／§2 `:27`／§3 `:32`／§4 `:36`／§5 `:40`／§6 `:44`／§7 `:48`／§8 `:52`／§9 `:63`／§10 `:67`／§11 `:73`／§12 `:91`／§13 `:101`／§14 `:130`），與 `:6`「節數：**14**」與 `:151`「本 ADR 現有 **14 節**（初版十節……各再揭出兩節）」三者一致 ✅。`Amended:` `:5` 現為「§11〜§14 新增；§8 補齊更正指令與閘門；§13 的 blocking 宣稱撤回並依 Q5=A／Q6=A 改寫」——iteration 4 m-3 的兩項（漏 §13、漏 §C-3／§C-6）**皆已補**。**殘留**：`Amends:` `:7` 的「以下原文：」保留片段自「對照表、」**起始**，前兩項與 `components.md 的 workflow` 前綴整段缺失（m-7） |
| **10b** | `component-methods.md` §自訂欄位格式的 §14 指標 | **通過** | `component-methods.md:60`：「**經 ADR-0015 §14 標記（指標補於 2026-08-30T01:31:09Z）**：上述前綴為四選一，但 `undecidable`……**沒有對應前綴**……**在此之前 `undecidable` 的自訂欄位行為未定義，實作不得自行猜**……確認人為 Bolt 1 的 gate」——與 ADR §14 `:132-136` 逐句對應 |
| **10c** | B:M-7 的指標更正（先前誤寫「§12 相關」） | **通過（附殘留 m-9）** | `component-methods.md:179` 現為：「另 **G-1**……`ReconcileReport` 亦須含 `undecidable: [intent_id]`……**先前此處誤寫為「§12 相關」，而 §12 是 `Block.rejection_notice`、且 ADR 全文不含 `undecidable`——指標解析不到（2026-08-30T01:31:09Z 更正，reviewer iteration 4 Group B M-7）**」——**斷掉的交叉引用已修**。殘留見 m-9 |
| **11** | markdown 結構修復（C-6 表、`ReconcileReport` code fence），且無新破壞 | **兩處已修；但在 U-6 發現同型新破壞（m-10）** | **§C-6 已修**：`component-methods.md:145-149` 為表頭＋分隔列＋**三列連續**（`render`／`parse`／`content_hash`），blockquote `:151-153` 落在表**之後**，`content_hash` 不再脫離表格 ✅。**§C-7 已修**：code fence `:168` 開、`:177` 關，§7／G-1 的 blockquote `:179` 落在 fence **之外** ✅。§C-3 的 `:95-101` blockquote 內含巢狀表格，語法合法、不破壞外層。**但 `U-6/business-rules.md:204-206` 有同型新破壞**（m-10） |

### 發現

| # | 嚴重度 | **類別** | 檔案:行 | 發現 |
| --- | --- | --- | --- | --- |
| **C-1** | **Critical** | **新設計問題** | `U-3/business-rules.md:94`（R-6.2）、`:95`（R-6.3）；對照 `component-methods.md:145-149`（§C-6 三方法）、`U-2/domain-entities.md:79-81`、`U-2/business-rules.md:44` | **R-6.2／R-6.3 要求 `write_body` 在 issue body 內「只覆寫受管標記界定的區塊」並「有標記時就地替換」，但整份設計沒有任何方法或規格讓它找得到那個區塊。** R-6.2 逐字：「**只覆寫受管標記界定的區塊**，issue body 的其餘內容（人寫的敘述）一字不動。」R-6.3 逐字：「body 內**無**受管標記時，把區塊**附加**在既有內容之後；有標記時**就地替換**。」<br><br>**要做到這兩條，`write_body` 必須知道標記的字面與它在 body 中的起訖位置。兩者都不存在：**（a）C-6 的公開介面只有三個方法（`component-methods.md:145-149`）——`render` 回 `string`、`parse` 回 `Block \| null`、`content_hash` 回 `sha256`，**沒有一個回傳標記的字面或跨度**；（b）標記的**語法本身在全 stage 產出中從未被定義**——`U-2/domain-entities.md:79-81` 只說「先讀版本標記，再套用對應的解析器。找不到版本標記 → 視為無標記 → 回 `null`」，`U-2/business-rules.md:44` 只說「無受管標記的 issue body → 回 `null`」，而 `U-2/domain-entities.md:73` 明文「**本節不裁定告示的文字與版面**——那屬渲染細節」。<br><br>**於是實作者只有兩條路，兩條都超出 U-3 的職權**：(a) 在 U-3 內自行實作一份標記偵測與切片——**這正是 U-3 自己在 `domain-entities.md:17` 拒絕過的形狀**（「若本元件自己算雜湊，U-2 的格式知識就會有第二份物化，違反 `team.md` 的「單一真實來源」」），而且那份副本**落在 U-2 的 R-4 群三道互鎖之外**：R-4.1 只比對「golden fixture 快照 ↔ 當前**渲染器**輸出」（`U-2/business-rules.md:71`），一次改動標記的 `format_version` bump 會讓快照與登錄表同步更新、三道全綠，而 U-3 那份 matcher 悄悄失配 ⇒ **每個既有 item 被當成「無標記」而被附加第二個區塊**——正是 ADR-A6 點名的最危險失敗模式，只是換了觸發點；(b) 為 C-6 新增一個方法（例如回傳跨度，或 `replace_managed_block(body, block_text) -> string`），那是對已核可上游 `component-methods.md` 的修訂，須走 ADR-0015 的承載形式。<br><br>**無法從現有文件推出該選哪一條**，符合 iteration 4 C-3 用過的同一判準（開發者必須回頭問架構師）。**這也是 `write_body` 從 §11 增設至今第一次被寫出規則**——前一輪只有方法與失敗語意，沒有人問過「它怎麼知道要換掉哪一段」。<br><br>**修法**：二擇一並記入 ADR-0015 —— (a) C-6 增設一個把「既有 body ＋ 新區塊文字」合成「新 body」的純函式（標記知識留在 U-2，U-3 只負責 API 呼叫，與 `managed_block_hash` 的既有分工同形，且自動落進 R-4 群互鎖）；或 (b) 明確定義標記的字面與其版本無關的不變部分，並把它列為 R-4 群的第四道互鎖對象。**(a) 與本 stage 既有的分工紀律一致，成本也較低。** |
| **M-1** | **Major** | **新引入** | `U-1/business-rules.md:74`（`## R-6 群：scope_note …`）與 `:107`（`## R-6：總函式性`）；引用點 `U-1/business-logic-model.md:95`；未同步 `U-1/business-rules.md:125` | **同一檔出現兩個 `## R-6`，使「U-1 的 R-6」同時指向兩個不相干的東西。** `:74` 是本輪新增的「`scope_note` 的推導與值域」（R-6.1～R-6.5），`:107` 是既有的「總函式性（[US:S-2 AC 15]）」——後者是本單元自稱「**最重要的不變式**」（`:109`）。而 `business-logic-model.md:95` 逐字「最後一條是窮盡二分的另一半，保證總函式性（`business-rules.md` **R-6**）」現在解析不到唯一目標。<br><br>**這正是 `project.md` 的 `functional-design:c17` 點名的形狀**（「使同一詞在同一檔內指向兩個不同狀態」）。**加重情節是同一輪內的雙重標準**：`U-6/business-rules.md:62` 的標題逐字寫著「**R-9**：本單元不擁有 U-10a 的 `paths-ignore`（**編號由 R-5 改為 R-9——同檔兩個 H2 撞號，reviewer iteration 4 m-4**；U-7 的同型撞號已在 iteration 2 以同樣方式處理）」——**本 stage 已經為這個問題建立了 renumber 的處置先例並在本輪套用於 U-6，卻在 U-1 新造了一個。**<br><br>**連帶**：新群插在 R-4 與 R-5 之間，使檔內順序成為 R-1→R-2→R-3→R-4→**R-6**→R-5→**R-6**；且 `:125`「本檔新增的規則：R-2.3／R-2.4……R-4.3……R-5.3／R-5.4……R-3.6 對「動過」的定義」**未把本輪新增的整個 R-6 群列入**。<br><br>**修法**：把新群改編為 `R-7 群`（比照 U-6 的 R-9 處置），同步 `U-1/domain-entities.md:61`、`U-2/business-logic-model.md:45`、`U-2/domain-entities.md`、`U-1/business-rules.md:125` 四處引用。（U-3 的 R-6 群不撞號，只是排在 R-5 之前，屬可不動的排版問題。） |
| **M-2** | **Major** | **新引入** | `U-3/business-rules.md:95`（R-6.3 後半句）；對照 `U-6/business-rules.md:183-206`（R-7 群方法表）、`:78`（R-5.10 (a) 的寫入鏈）；上游 `services.md:25` | **R-6.3 把「先跑 `parse`」指派給呼叫端，而唯一呼叫端 U-6 既沒有這一步，也沒有通道把結果交回來——上游 `services.md:25` 的冪等契約因此在正向路徑上無擁有者。** 三項實據：(1) `U-6/business-rules.md` 的 **R-7 群方法表**（該表存在的目的逐字是「送審前自檢第 2 項（每個宣告的方法都要有具名呼叫者）」，`:181`）列了 `read_binding`／`create_item`／`write_binding`／`map`／`field_value_for`／`read_sync_state`／`write_sync_state`／`write_status`／`write_field`／`write_body`／`read_item`／`render`／`content_hash`／`commit_and_push`／`notify`／`resolve_if_open`——**沒有 `parse`**；(2) R-5.10 (a)（`:78`）的寫入鏈逐字「照常走 `write_field` → `render` → `write_body` → 回讀 → `write_sync_state`」，**無 `parse` 步驟**；(3) `write_body: (binding, block_text) -> WriteResult`（`component-methods.md:99`）**沒有任何參數**能承接呼叫端的 `parse` 判定。<br><br>**後果是雙向的**：往一邊看，R-6.3 的後半句是**惰性條款**——寫了也不會有人執行；往另一邊看，若 `write_body` 真的自己判斷（R-6.3 前半句的字面），那 C-1 的標記知識問題就必然成立。**兩個子句互相假設對方負責。**<br><br>**附帶（不另計）**：這個缺口讓 U-2 的 R-3.4「不覆寫較新版本的區塊」在**新的路徑上**再次落空——`parse` 對「無標記」與「版本過新」回同一個 `null`（已由 ADR-0015 §6 承載），而 R-6.3 的「有標記則就地替換」會讓較新版本的區塊被**就地覆寫**（比先前的「附加第二個區塊」更具破壞性）。這一點在 §6 的兩條候選修法（三態／`has_managed_marker`）落地前**必須被寫下來**。<br><br>**修法**：與 C-1 一併裁定。若採 C-1 的 (a)（C-6 提供合成函式），R-6.3 後半句改為「本方法不做標記判定，由 C-6 的合成函式承擔」，並在 U-6 的 R-7 表與 R-5.10 寫入鏈補上該呼叫。 |
| **M-3** | **Major** | **新引入** | `U-5/business-logic-model.md:82`；傳播至 `U-6/business-rules.md:236`；對照 `U-8/business-rules.md:109-118`、`ADR-0015:40-42`（§5） | **M-6 的修正改過頭：把 U-8 寫進 `resolve_if_open` 的呼叫者名單，而 ADR-0015 §5 補的是通報鏈、U-8 對 `resolve_if_open` 零命中。** `U-5/business-logic-model.md:74` 的節標題逐字是「**`resolve_if_open` 的呼叫者**」，其表的三欄為「呼叫者 \| 時機 \| 依據」。`:82` 現為「U-8 \| **呼叫** \| 其元件集合原不含 C-5，**已由 ADR-0015 §5 補上**；落點為該單元 **R-4c 的方法表與錯誤處理表的「通報」欄**」。<br><br>**三項實據推翻它**：(1) ADR-0015 §5（`:40-42`）全節逐字只談通報——「使反向同步的外部失敗只會讓 workflow 紅燈而**不產生通報 issue**，[req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」保證在該路徑上不成立」，**全節不含 `resolve_if_open`**；(2) 它援引的落點 `U-8/business-rules.md:109-118` 的六方法表**只有 `notify`**，我逐行數過，**沒有 `resolve_if_open`**；(3) `U-8/business-logic-model.md:48-53` 的「通報」欄三列同樣只寫 `notify`。**U-8 三份產出對 `resolve_if_open` 零命中。**<br><br>**iteration 4 M-6 的 recommendation 逐字是**「依 `functional-design:c22`，**決定（U-8 是否呼叫 `resolve_if_open`）可以不改**，但**理由必須就地標註為不成立**」——本輪改了決定而沒有承接，**方向與建議相反**。而「時機」欄填成「呼叫」也不是時機（另兩列分別是「逐 record 迴圈結束之後，每輪一次」「每日全掃結束後」）。<br><br>**同一誤述已傳播**：`U-6/business-rules.md:236`（在 `### R-6.1 — resolve_if_open 的呼叫者是本單元` 之下）逐字「**U-8 現在也在此列**——其元件集合原不含 C-5，已由 ADR-0015 §5 補上」。<br><br>**後果**：`resolve_if_open` 的契約端點三問中的「誰呼叫」在反向路徑上得到一個**假的肯定答案**——U-8 的實作者讀自己的產出不會實作它，而任何盤點「反向路徑會不會收斂通報 issue」的人讀 U-5／U-6 會以為會。**修法**：兩處改回「不呼叫（僅 `notify`）」並就地標註「§5 補的是通報鏈，不含 `resolve_if_open`」；若確實要 U-8 收斂，須在 U-8 的 R-4c 與序列上新增規則（那是 U-8 的落點）。 |
| **M-4** | **Major** | **新引入** | `U-2/nfr-requirements/security-requirements.md:14`；對照本輪改動的 `U-2/domain-entities.md:15`、`U-2/business-logic-model.md:43-44`、`requirements.md:152`（NFR-S6） | **`decided_at \| null` 的值域變更推翻了 U-2 自己的 ADR-0006 audit-logging 判定，而該判定未被重判。** `security-requirements.md:14` 逐字：「**Audit logging** \| **部分適用，且比 U-1 更直接** \| 受管區塊本身**就是**稽核紀錄的一部分——它**必載 `decided_at`（ISO 8601）與 Status／原因類別**，正好對應 NFR-S6 的三要素中的兩項」。<br><br>**本輪之後這句話字面不成立**：`domain-entities.md:15` 現在明訂 `decided_at` 在 `status` 非 `null` 時**為 `null`**，`business-logic-model.md:43` 的 `render` 第 2 步在該支只寫「Status 與 `traceable_row`」。於是**受管區塊在「有寫 Status」的那一支完全沒有時間戳**——而 NFR-S6（`requirements.md:152`）針對的正是「每次 **Status 變更**皆可回答『哪個 intent、哪個 stage、**什麼時間**』」。兩者恰好相反：**時間戳只出現在不寫 Status 的分支上。**<br><br>**這不是需求失敗**（NFR-S6 的驗收判準逐字為「見 FR-E3；且成功的寫入亦在 **workflow log** 中留下同樣三項資訊」，log 那一半仍成立），**但它是一個 hard constraint 的判定被自己的改動推翻而沒有重判**——`project.md ## Mandated` 逐字要求「對每一項變更檢查 ADR-0006 security baseline 的四個面向……須在該 stage 產出中明列 security 影響與處置」。這與 iteration 4 M-5 判 Major 的理由同形（IAM 判定被自己的改動推翻）。<br><br>**修法**：`:14` 改寫為分支限定（「`status` 為 `null` 時載 `decided_at`；`status` 非 `null` 時區塊不含時間戳，該支的「什麼時間」由 workflow log 與 issue metadata 承擔」），並確認 NFR-S6 的承接在該支仍完整。同檔 `:35` 的 SEC-2 揭露表已經是分支形狀（「原因類別與 `decided_at`」自成一列），只有 `:14` 沒跟上。 |
| **M-5** | **Major** | **既存漏審** | `U-1/nfr-requirements/security-requirements.md:11`；`U-5/nfr-requirements/security-requirements.md:7`、`:42`（對照已修的 `U-3/…:32`） | **iteration 4 M-5(c) 點名的三處「三項」只修了一處。** M-5(c) 逐字：「`U-1/…:11`、`U-3/…:30`、`U-5/…:7` **三處**仍以「**三項**」陳述權限集合，而 ADR-0015 §8 已更正為**四項**」。本輪實況：**U-3 已補**（`:32` 一整段四項說明 ＋ §8 指標）；**U-1 未補**——`:11` 逐字仍為「`requirements.md` NFR-S1 定義的權限（**ADR-0014 更正後為三項**：組織層 Projects 讀寫 ＋ repo 內容寫入 ＋ Issues 寫入）」，全檔對 `0015` 零命中；**U-5 未補**——`:7` 逐字「權限集合已更正為**三項**」、`:42` 「驗收準則的「等於上述兩項」須同步改為**三項**」（`:13` 的 §8 引用承載的是「驗收判準欄補指標」這件事，不是四項計數）。<br><br>**為什麼仍是 Major**：理由與 iteration 4 相同——ADR-0006 的 IAM 是本專案 hard constraint，憑證於 **Bolt 0 鑄造**且事後變更需組織管理者操作（ADR-0015 Risk 段、`external-dependency-map.md` E-1）。per-unit 的 IAM 記載正是最小權限盤點時會被拿來用的東西，而現在同一批產出裡三份說三項、兩份說四項。<br><br>**修法**：U-1 與 U-5 各補一段與 `U-3/…:32` 同形的 §8 指標。**U-5 的 `:15-46` 屬「本節以下維持原文」的歷史記載（`:13` 明文），不動；只需更新 `:7` 的狀態行。** |
| **m-1** | Minor | **新引入** | `U-2/business-logic-model.md:88`；`U-2/business-rules.md:36`；`U-2/domain-entities.md:94` | **`decided_at \| null` 的副作用只寫進 `domain-entities.md:23`，另三處的 churn 敘述未加分支限定。** `business-logic-model.md:88` 邊界情形表逐字「兩次判定語意相同、時間不同 \| 雜湊**不同**，但不會重寫」——在 `mapped` 分支上雜湊現在會**相同**；`business-rules.md:36` 逐字「兩次語意相同的判定會有不同的 `decided_at` ⇒ 不同雜湊」、`domain-entities.md:94` 逐字「`decided_at` **在**涵蓋範圍內……churn 由上游的漂移判定擋住」——兩者皆未限定分支，與 `domain-entities.md:23` 新寫的「這讓同檔 R-2.3 的 churn 隱憂**只作用在不寫分支上**」互相矛盾。**結論本身不變**（有漂移才寫 ⇒ 兩支都不 churn），錯的是三處敘述的適用範圍。 |
| **m-2** | Minor | **既存漏審** | `U-2/business-rules.md:14`（R-1.2 的可判定方式） | **R-1.2 的可判定方式指向錯的變數，且與同表 R-1.5 不一致。** `:14` 逐字：「兩個只在此處不同的 **`Decision`** 產生**可區分**的區塊文字」——但 `scope_note` 明訂**不進 `Decision`**（`U-1/business-logic-model.md:32`、`U-1/domain-entities.md:61`），故「兩個只在 `scope_note` 上不同的 `Decision`」**構造不出來**，這個 fixture 寫不出來。同表 R-1.5（`:17`）本輪已正確改用「兩個只在此欄不同的 **`Context`**」。`U-2/domain-entities.md:55` 也逐字寫「R-1.2 的可區分性由**它**（`Context.scope_note`）承載」——同一單元兩份產出對同一條規則的驗證變數給出不同答案。iteration 4 M-3 的末段已點名，本輪未修。 |
| **m-3** | Minor | **既存漏審** | `U-1/business-logic-model.md:44-58`（主流程圖）、`:62-69`（`parse` 六步） | **演算法段仍沒有產出 `scope_note` 的步驟。** iteration 4 M-3(b) 逐字：「`business-logic-model.md:62-69` 的 `parse` 六步……與 `:44-58` 的主流程圖，**都沒有產出 `scope_note` 的步驟**」。本輪 R-6 群補上了規則（M-3 的 (a)(c) 已解），但 `parse` 仍是六步（`intent_id`→`get_field`→`binding`→`list_stages`→R-2.4→組 `ParsedRecord`）、主流程圖仍終於 `field_value_for(Decision, Config)`，**第五個 output 在演算法上仍無落點**。規則檔已足以實作，故僅 Minor。 |
| **m-4** | Minor | **新引入** | `U-1/domain-entities.md:102` | **新增型別段之後，「本檔新增而上游沒有的**有兩項**」成為過期計數。** 本輪在 `:59-61` 新增了 `### scope_note`（第五個 output，型別段補記）——它**正是**「本檔新增而上游沒有的」第三項（上游 `component-methods.md` 的 §共用型別無此物）。`:102` 逐字仍為「有兩項：`Config` 的欄位（F-1）與 `missing` 的 `"stage-lines"` 值」，`:104` 的說明 blockquote 也只區分「兩」與「四項缺口」，未涵蓋新增項。屬 `units-generation:rev1-L1` 的形狀（被計數的實體增加，總數是衍生後果）。 |
| **m-5** | Minor | **新設計問題** | `U-1/business-rules.md:80`（R-6.1）、`:84`（R-6.5）；對照 `U-1/domain-entities.md:37-42`（`Unparseable`） | **`scope_note` 在 `Unparseable` 路徑上無定義值。** R-6.1 逐字「由 `ParsedRecord.stages`……推導」，但該路徑上 `map` 收到的是 `Unparseable`，其欄位只有 `intent_id` 與 `missing`（`domain-entities.md:39-42`），**沒有 `stages`**；而 composite action 的五個 output 每輪都必須有值，R-6.5 又逐字禁止空字串。自然的補法是「無 `stages` ⇒ 兩類皆空 ⇒ `skipped-in-scope: none; out-of-scope: none`」，但規則沒有這麼寫。**影響小**：`U-6/business-rules.md:78` 的 R-5.10 (b) 支明訂 `unparseable`／`whitelisted` 不產生任何看板寫入，該值不會被渲染。補一句即可。 |
| **m-6** | Minor | **既存漏審** | `U-1/business-rules.md:83`（R-6.4）；對照 `U-6/business-rules.md:73`（R-5.2） | **`scope_note` 進 `content_hash` 卻不在漂移判定的三欄內，非當前 stage 的 scope 變動不會觸發重寫。** R-6.4 逐字「本欄位進 `Block` 進而進 `content_hash`」，而 U-6 的 R-5.2 逐字只比「`Decision.status` ↔ `last_status`、`Decision.field_value` ↔ `last_field_value`、`Decision.reason_code` ↔ `last_reason_code`」**三欄**。若某個**非當前** stage 的 `— EXECUTE/SKIP` 尾綴被改（例如一次 `/aidlc compose` 重新規劃）而三欄不變 ⇒ 判無漂移 ⇒ 不重寫 ⇒ 看板上的 `scope_note` 停在舊值，[req:FR-F3] 的「差別看得見」由過期資料承擔。**當前 stage 的變動不受影響**（`field_value_for` 的前綴會變 ⇒ `field_value` 變 ⇒ 判有漂移），故範圍窄。欄位自 iteration 3 即存在，非本輪引入，但 R-6.4 把它明確送進雜湊之後才變成可機械判定的。 |
| **m-7** | Minor | **新引入** | `ADR-0015:7`（`Amends:` 行） | **`Amends:` 的「以下原文：」保留片段自句中起始，讀者無法據以複驗原文。** 本輪為補 §C-3／§C-6 而重寫該行，保留的舊文逐字自「**對照表、**」開始——前面的 `bolt-plan.md` 的 PRE-1 表與 DoD、`unit-of-work-story-map.md` 的 S-6 AC 5 歸屬、以及「`components.md` 的 workflow」這個前綴全部缺失，於是「以下原文」承諾的東西只交付了一部分，末句「各原文皆維持，本 ADR 只更正其中被本文點名的部分」也失去主詞。 |
| **m-8** | Minor | **新引入** | `ADR-0015:115`（§13） | **未替換的格式佔位符 `%s` 留在正文裡。** 逐字：「**排程分支的落點（Q6=A 人工裁決，%s）**：」——該處應為 `date -u` 的時間戳（同節其餘處置皆有，如 `:117` 的 iteration 4 Group A M-1 引用）。`project.md` 的 `user-stories:260822-us-L1` 要求「寫入任何時間戳前一律執行 `date -u` 取值」，而這裡連值都沒填。 |
| **m-9** | Minor | **既存漏審** | `component-methods.md:179`（§C-7 區）；`:169-176`（`ReconcileReport`） | **M-7 的斷掉引用已修，但它指出的另兩半仍在。** (a) `ReconcileReport` 的型別區塊（`:169-176`）逐行核對**仍無 `undecidable` 欄位**（有 `unparseable`），而更正後的指標寫「該缺口……**已於 U-7 關閉**」——上游型別未動、也沒有任何 ADR 節承載它（ADR-0015 的 §1～§14 標題無一是 `ReconcileReport`／`undecidable` 的欄位增設；§14 管的是**自訂欄位前綴**，是另一件事）。(b) 該句的確認人仍與 §7 的 `latency_samples` **共用同一個「Bolt 2 的 gate」**，`undecidable` 這一項沒有自己的閘門——iteration 4 M-7 的原話「`undecidable` 這一句沒有自己的閘門」未被處理。 |
| **m-10** | Minor | **新引入** | `U-6/business-rules.md:195-206`（**落點在 U-6，非本組單元**） | **本輪插入 `Context` 組裝責任表時打斷了 R-7 群的方法表，並製造一列重複。** R-7 表（表頭 `:183`「方法 \| 元件 \| 本單元何時呼叫」）的資料列在 `:193`（`render`）之後被 `:195` 的散文、`:197-201` 的兩欄 `Context` 表與 `:203` 的 blockquote 截斷，而 `:204-206` 的三列（`render`／`content_hash`、`commit_and_push`、`notify`／`resolve_if_open`）**仍是三欄格式**，會被渲染成 `Context` 表（兩欄）的畸形延續或孤立片段。同時 `render(Decision, Context) -> string` 在 `:193` 與 `:204` **各出現一次**——插入時複製了既有列而未刪除原列。與 iteration 4 m-4（`component-methods.md` 的兩處結構破壞）**完全同型**，而那兩處本輪已修好；本輪在另一個檔案重現。**本組不寫 U-6 的產出**，在此標出供 Group A／conductor 處置。 |

### 契約端點三問（本輪新增／變更的四個項目）

| 項目 | 誰擁有／誰寫 | 誰呼叫／誰讀 | 誰清／失敗時誰接 | 判定 |
| --- | --- | --- | --- | --- |
| `write_body` 的**標記定位能力** | **無人** —— C-6 三方法皆不回傳標記字面或跨度；標記語法全 stage 未定義 ❌ | U-3 的 R-6.2／R-6.3 需要它 ✅ | — | **C-1** |
| `write_body` 之前的 `parse` 判定 | U-3 R-6.3 指派給「呼叫端」 ⚠ | **U-6 無此步** —— R-7 表無 `parse`、R-5.10 寫入鏈無 `parse` ❌ | `write_body` 簽章無參數承接 ❌ | **M-2** |
| `resolve_if_open` 在反向路徑 | U-5（C-5）✅ | **U-5／U-6 宣稱 U-8 呼叫，U-8 三份產出零命中** ❌ | — | **M-3** |
| `Block.decided_at`（值域變更後） | U-6 組 `Context`（`U-6/business-rules.md:199`）✅ | U-2 `render` 只在 `null` 支輸出 ✅；U-8 經 `parse` 讀回 ✅ | 每輪重算 ✅ | 三問齊備；但 U-2 的 ADR-0006 判定未重判（**M-4**） |

### 可算的數字（實算，非引述）

| 項目 | 實算值 | 方法 | 文件宣稱 | 一致？ |
| --- | --- | --- | --- | --- |
| `Block` 欄數 | **7** | 逐行數 `U-2/domain-entities.md:11-17` | 「七個欄位」（`:39`） | ✅ |
| `Block` 來源分配 | 常數 1 ＋ `Decision` 3 ＋ `Context` 3 = **7** | 逐欄分派（`:31`／`:44-48`／`:50`） | 「其中**三個**不可能從 `Decision` 推出來」 | ✅ 無遺漏無重複 |
| U-3 方法數 | **7** | §C-3 表 6 列（`component-methods.md:88-93`）＋ `:99` 的 `write_body` | 「七個方法」（4 處，含 `tech-stack-decisions.md:36`） | ✅ |
| U-8 方法數 | **6** | 逐行數 `U-8/business-rules.md:113-118` | 「**六個**上游方法」（`:109`） | ✅ |
| U-1 action output 數 | **5** | 逐行數 `U-1/business-logic-model.md:28-32` | 「五個 output」（`domain-entities.md:96`） | ✅ |
| ADR-0015 節數 | **14** | 逐行數 `### ` 標題（`:21`～`:130`） | `:6`「節數：14」、`:151`「現有 14 節」 | ✅ |
| U-1 `business-rules.md` 的 `## R-6` 個數 | **2** | `:74`、`:107` | （無宣稱） | ❌ **M-1** |
| `U-1`／`U-5` security 檔的權限項數 | **3**（兩檔） | `U-1:11`、`U-5:7` 逐字 | ADR-0015 §8：**四項** | ❌ **M-5** |
| U-8 產出提及 `resolve_if_open` 的次數 | **0** | 逐檔讀 `business-rules.md`／`business-logic-model.md`／`domain-entities.md` | U-5 `:82`「呼叫」 | ❌ **M-3** |

### Summary

**整組 NOT-READY：1 Critical、5 Major、10 Minor。**

**本輪指定的 11 個查證項中，主線的修正絕大多數確實落地並經逐字複驗**：`Block` 實數七欄且來源分配無缺無重；`decided_at | null` 的讀法回 `component-methods.md:157` 的 [US-OQ-3] 原文核對**成立**（「或」確實只把時間戳綁在不寫那一支），且「同進退」與 `render` 第 2 步一致；R-1.5 的可判定方式二元可判、R-1 群前言的範圍限定誠實；`render` 由四步補為五步且與 R-1 群、`Block`／`Context` 兩表逐條對得上；`domain-entities.md` 撤回的「必要性論證」撤得正確、新理由成立；U-1 的 `scope_note` 值域與推導補齊（兩類蒐集**刻意非窮盡且正確**、round-trip 成立、順序決定性足夠、型別段與介面表一致）；U-3 的方法數與 `Failed` 列全部同步且其引用的 U-6 **R-5.12 實地存在**（iteration 4 的 C-1 已關）；U-8 自身三項全通過且方法數實算為 6；ADR-0015 的 §14、`Amended:`、節數 14、§14 指標、B:M-7 的斷掉引用**全部到位**；iteration 4 m-4 的兩處 markdown 破壞（§C-6 表、§C-7 fence）**都已修好**。

**但 Critical 與四個 Major 仍全部落在本輪新寫的內容上，形狀與前四輪一模一樣。** 最重的一項是 **C-1**：`write_body` 從 §11 增設至今第一次被寫出規則，而規則要求它「只覆寫受管標記界定的區塊／有標記則就地替換」——**沒有人問過它怎麼知道要換掉哪一段**。C-6 的三個方法無一回傳標記的字面或跨度，標記語法在全 stage 產出中從未定義，於是實作者只能在 U-3 自建一份 U-2 格式知識的副本，而那份副本**落在 R-4 群三道互鎖之外**，一次 `format_version` bump 就能讓它在三道全綠的情況下失配並把每個既有 item 附加第二個區塊——ADR-A6 點名的最危險失敗模式換了個觸發點回來。**M-2** 是它的另一面：R-6.3 把「先跑 `parse`」丟給呼叫端，而 U-6 的 R-7 具名呼叫者表與 R-5.10 寫入鏈**都沒有這一步**，`write_body` 的簽章也沒有參數能承接——兩個子句互相假設對方負責。**M-3** 是修正過頭：iteration 4 M-6 明說「決定可以不改，理由必須標註不成立」，本輪卻改了決定，把 U-8 寫進 `resolve_if_open` 的呼叫者名單，而 ADR-0015 §5 補的是通報鏈、U-8 對該方法零命中。**M-1** 最刺眼——本 stage 已經為「同檔 H2 撞號」建立了 renumber 的處置先例並在**同一輪**套用於 U-6（R-5→R-9），卻在 U-1 新造了一個。**M-4** 是 `decided_at` 值域變更推翻了 U-2 自己的 ADR-0006 audit-logging 判定而未重判。唯一的 **既存漏審 Major（M-5）** 是 iteration 4 M-5(c) 的三處「三項」只修了一處。

**三類計數：新引入 9 項**（M-1、M-2、M-3、M-4、m-1、m-4、m-7、m-8、m-10）、**既存漏審 5 項**（M-5、m-2、m-3、m-6、m-9）、**新設計問題 2 項**（C-1、m-5）。**新引入仍佔 9/16**，且含 Critical 之外的四個 Major 全部在內——這一輪與前四輪的差別只在於缺陷從「規則缺席」移到了「規則寫了但兩端接不上」。

**建議處理順序**：**C-1 先**（它與 M-2 是同一個決定的兩面，且會改動 C-6 的介面，須與 §11／§12 同批進 ADR-0015）→ **M-3 次之**（純事實更正，兩處，五分鐘）→ **M-1**（機械 renumber ＋ 四處引用同步，已有 U-6 的現成先例可照抄）→ **M-4／M-5**（兩項都是 ADR-0006 hard constraint 的 per-unit 判定未同步，一併掃）→ Minor 群。**本輪請特別注意 m-10**：iteration 4 才修好 `component-methods.md` 的同型結構破壞，本輪就在 `U-6/business-rules.md` 重現一個——插入表格與 blockquote 之前，先確認插入點不在既有表格的資料列之間。

