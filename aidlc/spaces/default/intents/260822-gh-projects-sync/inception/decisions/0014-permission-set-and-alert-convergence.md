# ADR 0014: 憑證權限集合補入 Issues 寫入，與通報 issue 重複收斂路徑的更正

- Status: Accepted
- Date: 2026-08-29
- Amends: **`requirements.md` 的 NFR-S1**（權限集合）、**`application-design/decisions.md` 的 ADR-A2**（憑證與分支保護）與 **ADR-A8**（失敗收斂）、**`stories.md` 的 PRE-1 第 1 項**（實測範圍）。四者的原文皆維持，本 ADR 只更正其中被本文點名的部分
- Related: ADR-0013（本 intent 的映射層級與承載形式）、ADR-0006（security baseline 四面向）

## Context

Construction 的 nfr-requirements 逐單元檢視憑證與權限時，發現兩處已核可決定與設計本身矛盾。兩者性質不同，但都屬「已核可 artifact 的內容不成立」，依 ADR-0012 → ADR-0013 的先例合併於一份 ADR 記錄。

### 缺口 K-1：NFR-S1 的權限集合漏了 Issues 寫入

`requirements.md` 的 NFR-S1 宣告機制所需權限為 **「組織層 Projects 讀寫 ＋ repo 內容寫入」**，驗收準則逐字為「憑證實際被授予的權限集合**等於上述兩項，無額外授予**」。同一集合亦見於 ADR-A2 的 Decision 與其 ADR-0006 判定表。

**但 GitHub App 的 `Issues` 是獨立於 `Contents` 與 `Projects` 的第三種權限**，而本設計至少五處需要它：

| 需要 Issues 寫入之處 | 出處 |
| --- | --- |
| 回讀不符時開 issue | `requirements.md` FR-C1 |
| 同步失敗時自動開 issue | FR-E1 |
| C-5 `notifier` 的全部行為（開、追加 comment、關閉） | `component-methods.md` §C-5、ADR-A8 |
| C-3 的 `read_issue_state` | `component-methods.md` §C-3（[US:S-9 AC 5]） |
| 看板 item 的載體本身 | [US:S-1 AC 1]「Project #16 出現一則對應的 **issue**」 |

**最要緊的不是宣告不完整，是它會通過 PRE-1。** PRE-1 第 1 項為「憑證確實帶組織層看板寫入權——以最小可行呼叫實測」。若那次實測只呼叫 Projects 的 mutation，它**會通過**；缺 Issues 寫入權的憑證要到 Bolt 1 第一次真實執行時才失敗，而那時 PRE-1 已經簽過。

### 缺口 J-1：ADR-A8 的重複收斂路徑不可達

ADR-A8 的 Consequences 寫：「並行時可能短暫產生兩則同鍵 issue，**由下輪的 `resolve_if_open` 收斂**」（`component-dependency.md` 的資料流表亦複述此句）。

但 `resolve_if_open` 的用途是「**失敗不再發生時**收斂」（`component-methods.md` §C-5）。**重複 issue 正是在失敗持續發生時被開出來的**，此時該方法不會被呼叫，重複不會被收掉。

而 ADR-A8 為了補回 [US:S-8] 而寫的二元 AC 要求「該鍵對應的**開啟中**通報 issue 數為 1」——有重複且失敗持續時該 AC 失敗，且設計上沒有任何路徑會修復它。

## Decision

**1. NFR-S1 的權限集合由兩項更正為三項**：組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入 ＋ **Issues 寫入**。驗收準則的「等於上述兩項，無額外授予」隨之改為「等於上述三項」。

**2. PRE-1 第 1 項的實測必須涵蓋三項權限各至少一次真實呼叫**，其中**必須包含一次開 issue**。只驗 Projects 寫入不構成該項通過。此為 Bolt 0 的完成條件之一。

**3. ADR-A8 的重複收斂改由 `notify` 承擔**：搜尋命中多於一筆時，取 issue 編號最小者追加 comment 與計數，其餘同鍵 issue 關閉並註明重複。關閉條件必須是**內文首行機器可讀鍵逐字相符**，不得以標題比對。

第 3 點的具體規則已落在 U-5 的 `business-rules.md` R-2 群（人工裁定 [Q1=A]，2026-08-29）。**ADR-A8 的其餘部分（失敗身分定義、零新增持久狀態、issue 被人工關閉後開新的、被否決的兩個替代方案）維持有效。**

## Consequences

- **PRE-1 的成本略增**：第 1 項從一次呼叫變成三次。相對於「Bolt 1 才發現憑證不可用」，這是可忽略的代價。
- **NFR-S1 的「無額外授予」仍然有意義**：三項是完整清單，不是放寬——Issues 寫入本來就是設計必需，先前的兩項宣告才是錯的。**這不是擴大權限，是把實際需要的權限如實寫下來。**
- **U-3 的 SEC-2 與 U-4 的 SEC-1 記載的「單元拿到的權限大於它需要的」不受影響**，且現在更完整：宣告的集合**同時過大**（沒有機制限制各單元只用自己那一份）**與過小**（漏了 Issues）。兩者不矛盾。
- **`notify` 的職責變寬**：從「開或追加」變成「開、追加、或關閉重複」。關閉是本設計中少數的破壞性動作，其安全約束已定（見 Decision 第 3 點）。
- ADR-A8 的「零新增持久狀態」前提**不受影響**——收斂仍以 GitHub issue 本身為記憶。

## Alternatives Rejected

- **K-1：把 Issues 寫入視為 `Contents` 的一部分而不更正宣告。** 不成立——GitHub App 的權限模型中兩者是不同項目，鑄憑證時必須分別勾選。把它當成「已包含」正是會讓 PRE-1 通過而 Bolt 1 失敗的那個誤解。
- **K-1：不動 NFR-S1，只在 PRE-1 補測。** 會留下一份與設計矛盾的已核可需求，且下一個讀 NFR-S1 的人仍會據以鑄出不足的憑證。**驗收準則的「無額外授予」會主動阻止正確的憑證。**
- **J-1：維持 ADR-A8 原文，接受二元 AC 在有重複時不成立。** 等於接受一個已知會失敗的驗收條件，而該 AC 正是 ADR-A8 自己為了補回 S-8 而寫的。
- **J-1：以 concurrency 從源頭避免重複。** `services.md` 的 S-A concurrency group 依分支為界，而排程對帳（S-B）自成一組、兩者可並行——正是 ADR-A8 所指的並行來源。要涵蓋它得讓兩條路徑共用一個 group，**而那會讓對帳被事件同步阻塞，違反 NFR-P3「兩者可並行」的明文要求**。

## Reversibility

- **第 1、2 點：低**。權限一旦鑄出並安裝於組織層，變更需要組織管理者操作（見 `external-dependency-map.md` 的 E-1）。**因此更正必須在 Bolt 0 之前生效**，這也是本 ADR 急迫性的來源。
- **第 3 點：高**。屬 U-5 的內部行為，改動範圍限於一個單元。
