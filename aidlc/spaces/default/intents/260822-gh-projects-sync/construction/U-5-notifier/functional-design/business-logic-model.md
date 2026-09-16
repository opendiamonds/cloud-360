# Business Logic Model — U-5 通報

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-5-notifier · kind: library -->

## 這個單元在做什麼

當機制失敗時開一則 issue 叫人，而且**不重複叫**。它的記憶不是任何資料庫或狀態檔——**記憶就是 GitHub issue 本身**（[ad:decisions.md] ADR-A8 的 [Q5=A] 定案，零新增持久狀態）。

兩個方法（[ad:component-methods.md] §C-5）：`notify(FailureIdentity, detail) -> IssueRef`、`resolve_if_open(FailureIdentity)`。

本單元做**網路 I/O**（GitHub Issues API），與 U-3／U-4 同類、與 U-1／U-2 不同。複雜度 **S**——它的難度不在演算法，在生命週期。

## `notify` 的四支分流（[Q1=A]）

```
以 (intent_id, reason_code) 搜尋開啟中的通報 issue
   ├─ 0 筆 ──► 開新 issue（內文含 FR-E3 三要素 ＋ 機器可讀鍵首行）
   ├─ 1 筆 ──► 追加 comment、標題計數 +1
   └─ >1 筆 ─► 取編號最小者追加 ＋ 計數 +1
                其餘同鍵 issue ──► 關閉 ＋ 註明「與 #<最舊> 重複」
```

文字 fallback：依搜尋命中的筆數分三支——沒有就開新的、剛好一則就追加、多於一則就選最舊的追加並把其餘關掉。

**第三支是本站新增的**，它修的是 ADR-A8 一條走不通的路徑。完整理由與其安全約束（**必須以內文的機器可讀鍵逐字比對，不得以標題比對**）見 `business-rules.md` R-2 群。

## `resolve_if_open` 的觸發（[Q2=A]）

**每輪同步的最後一步執行一次**，不是逐鍵呼叫：

```
一次查詢：label=aidlc-sync-alert 的全部開啟中 issue
   └─► 逐則解析內文首行的機器可讀鍵
          ├─ intent 屬本輪 且 本輪未再產生該 reason_code ──► 關閉 ＋ 註明
          ├─ intent 屬本輪 且 本輪仍失敗 ─────────────────► 不動
          └─ intent 不屬本輪 ──────────────────────────► 不動（無資訊可判）
```

文字 fallback：每輪結束時把所有開啟中的通報 issue 拉一次，逐則看它的鍵；本輪處理過且不再失敗的關掉，其餘一律不動。

**成本是每輪一次查詢**，與 intent 數與 `reason_code` 值域大小都無關。被否決的逐鍵方案在 6 個 intent × 5 個 `reason_code` 下是 30 次額外呼叫，而 [req:FR-I4] 的上限是已知未定值。

**這個做法沒有破壞 ADR-A8 的「零新增持久狀態」**：第 3 步判定所需的資料全在本輪記憶體內（本輪每個 intent 的 `Decision` 與寫入結果）。見 `business-rules.md` R-3.1。

## 通報與紅燈是兩件事

| 情形 | 通報 | 紅燈 |
| --- | --- | --- |
| `Aborted`、`CannotCreate` | ✅ | ❌ |
| `ExternalError`、`Rejected` | ✅ | ✅ |
| 五種正常判斷的 `reason_code` | ❌ | ❌ |

`Aborted` 與 `CannotCreate` 是「通報但不紅燈」的存在證明——兩者都需要人知道，但都不代表機制壞了。完整表與規則見 `business-rules.md` R-1 群。

## 錯誤處理

**通報本身失敗 → 拋，不遞迴通報**（[ad:component-methods.md] 逐字）。

理由：通報失敗時再開一則「通報失敗」的通報，在 GitHub API 持續失敗時會產生無限迴圈。拋出後由 workflow 層紅燈，人從 workflow log 看到。

這是本單元**唯一**會拋例外的路徑——其餘全部以回傳值表達，與 U-1～U-4 的形狀一致。

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| 同鍵有兩則開啟中 issue | 取最舊追加，其餘關閉 | R-2 第 4 步（[Q1=A]） |
| 標題被人編輯過 | **仍能命中**——比對用的是內文首行的機器可讀鍵 | `domain-entities.md`、R-2.1 |
| issue 被人工關閉後同一失敗再發生 | **開新的**——這是想要的行為 | ADR-A8 的 Consequences 逐字 |
| 本輪未處理到的 intent 有開啟中通報 | **不動** | R-3.2（刻意，非疏漏） |
| 通報 API 失敗 | 拋 → workflow 紅燈 | R-4 |
| `reason_code` 為五種正常判斷之一 | **根本不呼叫 `notify`** | R-1 |

## `resolve_if_open` 的呼叫者（reviewer iteration 1 Critical，2026-08-29T15:25:28Z 補）

> **本方法先前沒有任何單元呼叫它。** 本單元是 `kind: library`，沒有自己的執行期；U-6／U-7／U-8 三份設計全文都沒提過它，也沒有任何一處像 F-4→U-6、G-1→U-7 那樣寫下「本單元在此正式承接」。**照當時的設計，通報 issue 永遠不會自動關閉**——正是缺口 J-2 與 [US:S-8] 要防的結果。

| 呼叫者 | 時機 | 依據 |
| --- | --- | --- |
| **U-6**（已承接） | 逐 record 迴圈**結束之後**，每輪一次 | 該單元的 **R-6.1**；其元件集合含 C-5 |
| **U-7**（本站標出，落點在該單元） | 每日全掃結束後 | 其元件集合亦含 C-5，且每日全掃最適合收殘留 |
| U-8 | **呼叫** | 其元件集合原不含 C-5，**已由 ADR-0015 §5 補上**；落點為該單元 R-4c 的方法表與錯誤處理表的「通報」欄（2026-08-30T01:31:09Z 更正，reviewer iteration 4 Group B M-6） |

**為何在迴圈之後而非之內**：通報 issue 的成立與否要看整輪結果，逐 intent 判斷會把「這一個好了」誤讀為「問題解決了」。

**這個缺口已關閉（2026-08-30T01:31:09Z）**：本單元的 R-1 表宣稱 `ExternalError` **無條件**「是通報」，而 U-8 的元件集合原本沒有 C-5，所以反向同步的外部失敗只會讓 workflow 紅燈，**不會產生通報 issue**。這使 [req:FR-E1]／[US:S-8 AC 1] 的「外部失敗 → issue」保證在反向路徑上不成立。**元件集合在 [ad:components.md]（已核可上游），故標出不逕改**——**本項已由 ADR-0015 §5 承載**（送審前自檢遷移，2026-08-29T23:42:35Z；先前寫「指派 application-design 的 workflow 對照表」，而 application-design 已定稿、不會為了下游的一句指派再跑一次，理由見 ADR-0015 的 Context 段）。**確認人維持 Bolt 3 的 gate。**

## 與上游的對應

方法簽章、收斂演算法與「不可遞迴通報」引自 [ad:component-methods.md] §C-5；ADR-A8 的定案、Consequences 與被否決方案引自 [ad:decisions.md]；紅燈語意引自 [ad:services.md]；FR-C1／FR-E3／FR-I4 引自 `requirements.md`；[US:S-7 AC 5]／[US:S-8] 引自 `stories.md`；單元邊界、複雜度與完成判準引自 [ug:unit-of-work.md] 的 U-5；AC 歸屬引自 [ug:unit-of-work-story-map.md]；元件分層引自 [ad:components.md]。

**本檔對上游的補充**：通報 issue 的可搜尋形狀（label、標題慣例、內文機器可讀鍵）、`notify` 命中多筆時的處置（缺口 J-1，[Q1=A]）、`resolve_if_open` 的觸發時機（缺口 J-2，[Q2=A]）。**`FailureIdentity`、三步演算法的前兩支、通報／紅燈分流一條未改。**

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:12:11Z
**Iteration**: 1

### 查證方法

本輪審查逐字讀取 U-5 全部四份產出（`business-logic-model.md`／`business-rules.md`／`domain-entities.md`／`functional-design-questions.md`）、U-5 的 `nfr-requirements`（`security-requirements.md`／`tech-stack-decisions.md`），並依 dispatch 的 exempt 清單逐檔核對 U-6／U-7／U-8 三個單元各自的 `business-logic-model.md`／`business-rules.md`／`domain-entities.md`（六類驗證方式表把 U-5 歸為「⑤Issues REST 行為」、U-6～U-9 歸為「⑥workflow 執行期」，兩者互相呼叫是唯一能驗證的跨單元路徑），以及 `application-design` 五份（`components.md`／`component-methods.md`／`services.md`／`decisions.md`）、`decisions/0014-permission-set-and-alert-convergence.md`、`requirements.md`、`stories.md`（S-8、PRE-1）、`unit-of-work.md`、`unit-of-work-story-map.md`。另以 `Read`／`grep` 直讀本次 dispatch 的 audit shard（`audit/jiangzhengdaodemacbook-pro-local-82da74e002f9.md`），核對 Q1／Q2 的人工作答時序（見 Finding 5 的查證，非缺陷）。

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
|---|---|---|---|---|
| 1 | Critical | `business-logic-model.md:27-29`、`functional-design-questions.md`（Q2=A）vs U-6／U-7／U-8 各自的 `business-logic-model.md`／`business-rules.md`／`domain-entities.md` | **`resolve_if_open` 在目前已核可的呼叫端設計裡沒有任何呼叫者。** U-5 宣稱 Q2=A 的決定（「每輪同步的最後一步執行一次，不是逐鍵呼叫」）關閉了缺口 J-2（「`resolve_if_open` 的觸發時機未定義」，functional-design-questions.md 原文）。U-5 是 `kind: library`（`unit-of-work.md`），本身無獨立執行期，這個方法只能被 `service` 類單元呼叫。逐字核對三個目前僅有的 `service` 類已完成單元：U-6 的序列圖（`business-logic-model.md` 第 13-32 行）只在 `commit_and_push` 失敗處呼叫 `U-5 notify`，全檔（含 `business-rules.md` R-1～R-5、`domain-entities.md`）**無一處**提及 `resolve_if_open` 或「每輪最後一步」的收斂呼叫；U-7 的序列圖（掃描 → 判定 → 補平 → 產出報告）與其 `business-rules.md`／`domain-entities.md`**全篇不含 C-5 或 notify／resolve_if_open 的任何引用**；U-8 的 `business-rules.md` R-4c 明文列出「本單元呼叫的上游方法」（`read_item`／`parse`／`content_hash`／`write_sync_state`／`commit_and_push`），C-5 不在其中。三份「與上游的對應」段落也都沒有把這條責任接下來（對照 U-6 對缺口 F-4、U-7 對缺口 G-1 都有清楚的「本單元在此正式承接」字句，`resolve_if_open` 的呼叫沒有任何單元做出對等的承接聲明）。這不是三份設計各自的局部瑕疵，而是 U-5 本身對「誰呼叫我」這件事沒有指派任何一個下游單元——`project.md ## Corrections`（`units-generation:260822-ug-L2`）要求「指派需指出誰要確認，否則指派會無聲落空」，而這裡連指派本身都不存在。實際後果：只要工程師照 U-6／U-7／U-8 目前的 functional-design 實作，`resolve_if_open` 永遠不會被呼叫，通報 issue 在問題解決後**永不自動關閉**——這正是 [US:S-8] 與缺口 J-2 想避免、而 Q2 選項本文明寫「叫了不收，久了就沒人看」的那個結果，如今只是被文件單方面宣稱「已解決」。 | 在 U-5（或回 units-generation／application-design，若判斷這是遺漏的跨單元契約）明確指派一個 `service` 單元承接「每輪同步最後一步呼叫 `resolve_if_open`」的責任，並要求該單元的 `business-logic-model.md` 補上這一步、在「與上游的對應」引用 C-5，寫下等同 F-4／G-1 的承接聲明。依 Q2=A 的語意（「一次列舉全部開啟中通報 issue」需要全域視野），最自然的落點是每輪都掃過全部 registry 的單元；若刻意選其他單元，需說明理由。 |
| 2 | Major | `business-rules.md` R-1 群（「ExternalError │ 是 │ 是 │ [ad:services.md] 的兩種紅燈之一」）vs U-6 `business-rules.md` 錯誤表、U-7 `business-logic-model.md`＋`business-rules.md`（全檔無 C-5 引用）、U-8 `business-rules.md` R-4c＋其錯誤表 | U-5 的 R-1 表把 `ExternalError` 定為無條件「是通報 且 是紅燈」。但逐檔核對三個呼叫端：**U-6** 的錯誤表對「單一 intent 的 `ExternalError`」只寫「不中止整輪——計入報告後續跑」，不像同一張表的 `Aborted／CannotCreate`、`Rejected` 兩列那樣明寫「＋通報」；**U-7** 的錯誤表（`reverse_pending` 查不到、單一 intent 的 API 失敗）與其「與上游的對應」全篇**不含 C-5 或 notify 的任何引用**；**U-8** 的 R-4c 明文列出本單元呼叫的上游方法（`read_item`／`parse`／`content_hash`／`write_sync_state`／`commit_and_push`），**C-5 不在其中**，但其錯誤表把「讀看板失敗」「開 PR 失敗」都標為 `ExternalError`、紅燈:是。三個呼叫端裡有兩個（U-7、U-8）完全沒有把 `ExternalError` 接到 `notify()`，第三個（U-6）只在一條路徑（`commit_and_push` 失敗）明確接上。照現有三份 functional-design 實作，[req:FR-E1]／[US:S-8 AC 1]「外部錯誤 → workflow 紅燈且產生一則 issue」這條保證在對帳（U-7）與反向同步（U-8）兩條路徑上不成立——這兩個 workflow 的 API 失敗只會紅燈，不會開 issue。 | U-5 的 R-1 表對「ExternalError 是通報」的宣稱需要限定其實際覆蓋範圍；或反過來把「每個 ExternalError 呼叫點都要接 `notify()`」列為對 U-6／U-7／U-8 的明確指派，要求三個單元各自在錯誤表補上「＋通報」並在「與上游的對應」引用 C-5，而不是把這個假設留在 U-5 自己的表格裡、指望呼叫端自動遵守一個它們的文件裡完全沒提過的契約。 |
| 3 | Major | `requirements.md:147`（NFR-S1「驗收判準」欄）vs `security-requirements.md` K-1 vs `decisions/0014-permission-set-and-alert-convergence.md` Decision 第 1 點 | U-5 的 K-1 宣稱「`requirements.md` NFR-S1……皆已加上指標」，暗示現況已與 ADR-0014 一致。但逐字核對 `requirements.md:147`：ADR-0014 的更正註記只掛在「需求」欄（緊接在「機制需要的權限為……」之前），**「驗收判準」欄本身逐字仍是「憑證實際被授予的權限集合等於上述兩項，無額外授予」**，且該欄唯一附帶的指標指向「下方『已解消的矛盾 R-1』」——那是一段討論「不索取 repo 內容寫入權」失效的**舊**修正，通篇不提 Issues 寫入權，也不指向 ADR-0014。這與 ADR-0014 Decision 第 1 點的明文要求（「驗收準則的『等於上述兩項，無額外授予』隨之改為『等於上述三項』」）不符。對照組 `stories.md:389-390` 的 PRE-1 第 1 項處理得正確：原文保留之外，緊接著用一段「經 ADR-0014 擴充」的引用把「三項權限各至少一次真實呼叫，其中必須包含一次開 issue」直接寫進本文，讓讀該欄的人不需要跳到 ADR 也拿得到正確準則。NFR-S1 的「驗收判準」欄沒有做到這件事——若有人（或未來的自動化檢查）只讀該欄操作，會依字面把 Issues 寫入判為「額外授予」而判定不合格，直接卡死本單元賴以運作的憑證，且該欄現有的指標還會把人導向一段不相關的舊修正。 | 把「驗收判準」欄本身改寫為「等於上述三項，無額外授予」（比照 `stories.md` PRE-1 的處理方式），或至少在該欄內就近補上指向 ADR-0014 的指標，取代／並列現有指向 R-1 的指標。 |
| 4 | Minor | U-8 `business-rules.md` R-4c 標題「本單元呼叫的四個上游方法」 | 標題宣稱「四個」，但緊接的表格實際列出 5 個方法（`read_item`／`parse`／`content_hash`／`write_sync_state`／`commit_and_push`）。可算的數字未重算（`project.md ## Corrections` `delivery-planning:dp-L1`）。 | 標題改為「五個」；若刻意把 `parse`＋`content_hash` 視為一組，宜在正文註明理由。 |
| 5 | 非缺陷（查證記錄） | `functional-design-questions.md` Q1／Q2 的 `[Answer]: A` 時間戳（`2026-08-29T12:14:28Z`） | 任務要求核對「本站裁定（未經人工提問）是否成立」。直讀 audit shard（`audit/jiangzhengdaodemacbook-pro-local-82da74e002f9.md:11859-11877`）：`12:10:50Z` `DECISION_RECORDED`「U-5 兩題：notify 命中多筆的處置（缺口 J-1）、resolve_if_open 的觸發時機（缺口 J-2）」→ `12:13:26Z` `HUMAN_TURN` → `12:14:28Z` `QUESTION_ANSWERED`「Q1=A 挑最舊追加、關閉其餘同鍵；Q2=A 每輪先列舉全部開啟中通報 issue」——與檔內 `[Answer]: A` 的內容、時間戳逐秒相符，`HUMAN_TURN` 先於作答，形狀合法。**判定：這兩題確實經過人工提問與作答，非本站單方裁定。** | 無須動作；記錄於此供稽核追溯。 |

### 對 Task 五個重點的逐項小結

1. **去重機制**（key／`×N`／race／ADR-0014 承接）：key 的唯一性、`×N` 更新規則本身自洽；`notify` 對「命中多筆」的收斂（R-2 群第 4 步）**正確承接了 ADR-0014 對 J-1 的裁決**，設計與 ADR 文字逐字一致，這部分沒有發現問題。但收斂機制的**另一半**——`resolve_if_open` 的關閉——經 Finding 1 查證為系統上無法觸發，`×N` 計數會持續累積而永不歸零。
2. **恆真／不可達規則**：R-2／R-3 群本身沒有發現不可達的規則；真正不可達的不是某條規則的字面，而是整個 `resolve_if_open` 方法（見 Finding 1）。
3. **跨單元契約主張**：逐一開檔核對 U-6／U-7／U-8，找到 Finding 1（`resolve_if_open` 零呼叫者）與 Finding 2（`notify` 對 `ExternalError` 的覆蓋在 U-7／U-8 缺席）兩項落差。
4. **權限**：ADR-0014 補的第三項 Issues 寫入權，K-1 段落本身敘述正確，但下游 `requirements.md` NFR-S1 的「驗收判準」欄未同步（Finding 3）。
5. **本站裁定合法性**：Finding 5，經 audit shard 核對為合法人工提問，非缺陷。

### Summary

Critical 1 項、Major 2 項：U-5 自身的通報開/追加/收斂三步邏輯與去重演算法設計正確、且正確承接了 ADR-0014 對 J-1 的裁決，Q1／Q2 兩題也確實經過合法的人工提問（非本站裁定）。但 U-5 對外的兩個核心跨單元假設——「`resolve_if_open` 會在每輪同步的最後一步被呼叫」與「`ExternalError` 一律觸發 `notify`」——在唯一可驗證的三個呼叫端（U-6／U-7／U-8）現有的已核可 functional-design 裡並不成立：前者完全沒有呼叫者，後者只有三分之一的呼叫端部分接上。這使得 U-5 宣稱已關閉的缺口 J-2（issue 永遠開著）在系統層級仍然存在，且不會在任何一個單獨單元的實作或測試中被發現——因為每個單元各自看都「沒錯」，缺陷只存在於它們之間的落差。另外 `requirements.md` NFR-S1 的「驗收判準」欄未依 ADR-0014 同步，構成一個字面上會擋下本設計所需憑證的風險。判定 NOT-READY。

## Review (Iteration 2)

**Verdict**: READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T16:13:50Z
**Iteration**: 2

### 查證方法

本輪為驗證輪，範圍限定為 iteration 1 的三項發現是否落地。逐字重讀 U-5 全部四份產出（`business-logic-model.md`／`business-rules.md`／`domain-entities.md`／`functional-design-questions.md`）與 `nfr-requirements/security-requirements.md`；依 dispatch 的承接落點清單開檔核對 U-6 的 `business-rules.md`／`business-logic-model.md`、U-3 的 `domain-entities.md`；核對上游 `application-design`（`components.md`／`component-methods.md`／`decisions.md`）、`decisions/0014-permission-set-and-alert-convergence.md`、`requirements.md`（NFR-S1 逐字、其指向的「已解消的矛盾 R-1」段）、`stories.md`（S-2 AC 4、S-9 AC 1/2/5/6）、`delivery-planning/bolt-plan.md`（Bolt 0／1／2／3 的 DoD 全文）。未重新開啟 U-7 以外的其餘 iteration-1 已通過查證項（如 audit shard 的時間戳合法性）。

### 逐項查證表

| # | 查證項 | 結果 | 依據 |
|---|---|---|---|
| 1 | `resolve_if_open` 的三個承接（U-6 的 R-6.1、U-7 的錯誤表列、U-8 明記不呼叫）是否真的落地、內容一致 | **通過**。U-6 `business-rules.md` R-6.1a/b/c（:116-128）逐字承接，含相同的「迴圈之後而非之內」理由；U-6 `business-logic-model.md` 序列圖（:36）與邊界情形表皆已畫出該呼叫。U-7 `business-logic-model.md` 邊界情形表（:83）「迴圈結束後 │ 呼叫 C-5 resolve_if_open...│ U-5 的 J-2；同 U-6 的 R-6.1」與其上方 iteration-1 補正說明（:85-87）一致標出、非逕改。U-8：`components.md` 的 workflow 對照表（:108）`aidlc-sync-reverse.yml` 的元件集合為「C-3（讀）→ C-6（雜湊比對）→ C-4（寫檔）→ 開 PR」，**確實不含 C-5**，與 U-5 的主張逐字相符。三處承接皆為真實內容，非空頭宣稱 | `business-logic-model.md:78-86`；U-6 `business-rules.md:116-128`；`components.md:108` |
| 2 | 「迴圈之後而非之內」的理由是否成立 | **結論成立，但陳述的理由不是主導理由**。U-5／U-6 均把理由寫成「通報 issue 的成立與否要看整輪結果，逐 intent 判斷會把『這一個好了』誤讀為『問題解決了』」（`business-logic-model.md:84`）。但 `FailureIdentity = (intent_id, reason_code)` 使每個判定本就是逐 intent 獨立的（見 `domain-entities.md:5-13`），一個 intent 在迴圈中處理完當下就能確定它這輪是否還產生該 `reason_code`，逐 intent 判斷不會產生「這一個好了≠問題解決了」的誤讀。**真正站得住的理由是 R-3 群自己寫的成本考量**（`business-rules.md:42`：「每輪多一次查詢，與 intent 數、`ReasonCode` 數皆無關」）——用「一次列舉全部開啟中 issue」取代「每 intent 逐鍵搜尋」，若要在迴圈內做到同樣的一次查詢成本，需要在迴圈開始前就把全部通報 issue 一次拉好、逐 intent 只比對記憶體內的清單——這其實**可以**在迴圈內完成，「之後」並非唯一能達到低成本的位置。結論（迴圈之後執行）本身不影響正確性，設計無缺陷，僅陳述的理由偏弱，判 Minor | `business-logic-model.md:84`、`business-rules.md:33-46` |
| 3 | `notify()` 的 `ExternalError` 涵蓋：U-6／U-7 錯誤表補正是否到位；U-8 的「指派而非就地修」判斷是否正確 | **U-6／U-7 已到位**。U-6 `business-logic-model.md:74`「`ExternalError` 那一列先前漏了『＋通報』（reviewer iteration 1 Major）...已補齊」，逐字對照其錯誤表（:69）確認「單一 intent 的 `ExternalError` │ 不中止整輪...＋通報 │ 是」。U-7 `business-logic-model.md:82`「單一 intent 的 `ExternalError` │ 續跑其餘 ＋ 通報（C-5）│ [req:FR-E1]、[US:S-8 AC 1]」亦已補上。**U-8 的指派判斷正確**：`components.md` 已核可上游確實不含 C-5（同查證項 1），U-5 用「標出不逕改」明文聲明未動上游（`business-logic-model.md:86`），指派落點與確認人（Bolt 3 的 gate）具體、非空泛。**但延伸查證發現**：`bolt-plan.md` 的 Bolt 3 DoD（:67）逐字只有「U-8 與 U-10b 完成判準通過；CAP-11 補評估...over-suppression 已實測」，**沒有任何一句提及這項 C-5 指派**——「確認人為 Bolt 3 的 gate」目前只是 U-5 自己文件內的一句宣告，`bolt-plan.md` 本身未見對應追蹤行。這與 iteration 1 已通過的 G-1（在 `bolt-plan.md` Bolt 2 DoD 有顯式落地，見 :60）的處置深度不同。**因 U-5 已誠實揭露「標出不逕改」、未過度宣稱既成事實**（對照 U-7 iteration 2 review 的 Major #1，措辭上有實質差別），判 Minor，非 Major | `business-logic-model.md:74`（U-6）、`:82`（U-7）；`bolt-plan.md:62-68` |
| 4 | NFR-S1 驗收判準欄的過度宣稱是否已更正為如實記載＋指派 Bolt 0 gate | **通過，如實**。`security-requirements.md:9`「但 `requirements.md` 的 NFR-S1 只有『需求』欄補了指標，『驗收判準』欄仍逐字寫著『等於上述兩項，無額外授予』，且其指標指向的是一個不相干的較早更正（R-1），不是 ADR-0014」——逐字核對 `requirements.md:147`：驗收判準欄確實仍是「憑證實際被授予的權限集合等於上述兩項，無額外授予。**見下方『已解消的矛盾 R-1』**」，未同步為三項。追蹤該指標到 `requirements.md:180-182` 的 R-1 段：其主體討論的是「不索取 repo 內容寫入權」這條**不同**的 IAM 矛盾（兩項 vs 加了適用前提的兩項），僅在段落末尾以括號附註一句「（後續：ADR-0014 再補入第三項 Issues 寫入...）」——與 K-1 缺口（漏了 Issues 寫入權）並非同一議題，稱其「不相干」大致成立，僅略有過度（畢竟該括號確實含 ADR-0014 的連結）。**核心事實與 lead 描述一致**：驗收判準欄逐字未同步，且指標的主要內容確實答非所問。K-1 段落本身也正確標出「本站不逕自改上游」與確認人（Bolt 0 gate），且 `bolt-plan.md` 的 PRE-1 第 1 項（:23）已實際反映 ADR-0014 的三項權限與「必須包含一次開 issue」——**這一項的 Bolt 0 追蹤確實有落地**，與查證項 3 的 U-8／Bolt 3 情形不同 | `security-requirements.md:5-13`；`requirements.md:147,176-182`；`bolt-plan.md:23` |
| 5 | 送審前自檢與整體一致性 | 逐一核對 U-5 三份規則檔（R-1／R-2／R-3／R-4 群）與 U-6／U-7 的錯誤表、邊界情形表在 `Aborted`／`CannotCreate`／`ExternalError`／`Rejected`／五種正常判斷的通報與紅燈判定上**完全一致**，無新的矛盾 | `business-rules.md`（U-5）R-1 群；U-6 `business-logic-model.md:64-76`；U-7 `business-logic-model.md:62-83` |

### 新引入的問題（本輪修正）

無 Critical／Major。上一輪的 Critical #1（`resolve_if_open` 孤兒契約）已完整關閉；Major #2（`ExternalError` 涵蓋）與 Major #3（NFR-S1 過度宣稱）均已妥善收斂為如實記載＋具名指派，其中一項（K-1→Bolt 0）指派已在 `bolt-plan.md` 落地，另一項（U-8-C5→Bolt 3）指派尚未在 `bolt-plan.md` 落地但已誠實標出，降級為 Minor 記載於查證表，不視為新缺陷。

### Summary

Iteration 1 的三項發現（Critical 1、Major 2）在本輪查證中全部得到實質、可驗證的修正：`resolve_if_open` 現有 U-6（已完整承接）與 U-7（已標出承接）兩個真實呼叫端，U-8 的例外經 `components.md` 核實為真且指派方式合乎本專案既有的「標出不逕改」慣例；`ExternalError` 通報涵蓋在 U-6／U-7 均已補齊，U-8 的殘留缺口誠實揭露而非隱藏；NFR-S1 的過度宣稱已自我更正為準確描述，且與其對應的 Bolt 0（PRE-1）追蹤確已落地於 `bolt-plan.md`。本輪僅發現兩項 Minor（`resolve_if_open` 觸發理由的論證強度、U-8 的 C-5 指派尚未在 `bolt-plan.md` Bolt 3 DoD 顯式追蹤），皆不影響開發者依本檔獨立實作的能力。判定 READY。
