# Functional Design — U-5 通報

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-5-notifier · kind: library -->

## CONDITIONAL 適用性判定

| 條款 | 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | 通報 issue 的標題與內文格式（含可搜尋的鍵與計數）完全未定義 |
| Complex business logic | ✅ | 收斂演算法的生命週期，見下方兩個缺口 |
| Business rules need design | ✅ | 同上 |
| Skip if simple logic changes | ❌ | 新模組 |

**判定：EXECUTE**（`kind: library` → 三份產出）。

## 已由上游定案、本站不重問

| 事項 | 出處 |
| --- | --- |
| 失敗身分 = `(intent_id, reason_code)`；**記憶就是 GitHub issue 本身**，不新增持久狀態 | [ad:decisions.md] ADR-A8（[Q5=A]） |
| 收斂演算法三步（搜尋開啟中 issue → 命中追加 comment ＋ 更新標題計數 → 未命中開新 issue） | 同上、[ad:component-methods.md] §C-5 |
| 新 issue 內文含 intent 識別字、stage 標識、ISO 8601 時間戳三者 | [req:FR-E3] |
| **通報本身失敗 → 拋**（不可遞迴通報） | [ad:component-methods.md] |
| issue 被人工關閉後下次會開新的——**這是想要的行為** | ADR-A8 的 Consequences |
| 哪些 `reason_code` **不使 workflow 紅燈** | [ad:component-methods.md]、[ad:services.md] |

## 本站發現的上游契約缺口

### 缺口 J-1：重複 issue 的收斂路徑在失敗持續時不成立

ADR-A8 的 Consequences 寫：「並行時可能短暫產生兩則同鍵 issue，**由下輪的 `resolve_if_open` 收斂**。」

但 `resolve_if_open` 的用途是「**失敗不再發生時**收斂」（[ad:component-methods.md] §C-5）。**失敗若持續發生，它不會被呼叫**——而重複 issue 正是在失敗發生時被開出來的。

同時，`notify` 的第 1 步「搜尋開啟中的通報 issue」**沒有定義命中多於一筆時的行為**。

**擋住**：ADR-A8 補回的二元 AC 要求「該鍵對應的**開啟中**通報 issue 數為 1」。有重複且失敗持續時，該 AC **失敗**，而設計上沒有任何路徑會修復它。
**落點**：本站 Q1 裁定。

### 缺口 J-2：`resolve_if_open` 的觸發時機未定義

方法存在、語意清楚（失敗不再發生時收斂），但**沒有任何上游 artifact 說它何時被呼叫**。

這在 ADR-A8 的「零新增持久狀態」前提下不是小事：機制**不記得**上一輪失敗過什麼，所以無法在成功時「針對那個鍵」收斂。可能的做法各有代價（見 Q2）。

**擋住**：[US:S-8] 的收斂語意——通報 issue 會**永遠**開著，即使問題早已解決。
**落點**：本站 Q2 裁定。

---

## 問題

### Q1. `notify` 搜尋命中多於一筆時怎麼辦？（缺口 J-1）

A. **命中多筆時：挑最舊的追加 comment，並把其餘同鍵 issue 關閉並註明「與 #<最舊> 重複」**。看得到的效果：重複在**下一次失敗發生時**就被收斂，不需等 `resolve_if_open`——修好了 ADR-A8 那條走不通的路徑；二元 AC（開啟中數為 1）在第二輪即成立。代價：`notify` 從「開或追加」變成「開、追加、或關閉重複」，職責變寬；且關閉別的 issue 是一個**破壞性動作**，若鍵的比對有 bug 會關掉不該關的。

B. **命中多筆時：只對最舊的追加 comment，不動其餘**。看得到的效果：`notify` 保持單純，不做破壞性動作。代價：**二元 AC 在有重複時永遠不成立**（開啟中數 > 1），而該 AC 正是 ADR-A8 為了補回 S-8 而寫的——等於接受一個已知會失敗的驗收條件。

C. **從源頭避免重複：以 concurrency 保證同一時間只有一個 run 會 `notify`**。看得到的效果：不需處理重複，因為不會有重複。代價：[ad:services.md] 的 S-A concurrency group 是**依分支**的，而排程對帳（S-B）自成一組——兩者可並行，正是 ADR-A8 所說的並行來源。要涵蓋它得讓兩條路徑共用一個 group，**而那會讓對帳被事件同步阻塞**，違反 NFR-P3「兩者可並行」的明文要求。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T12:14:28Z（讀自 date -u）· 挑最舊追加，關閉其餘同鍵 -->

### Q2. `resolve_if_open` 何時被呼叫？（缺口 J-2）

A. **每輪對「本輪成功處理的 intent」呼叫一次，鍵為該 intent ＋ 本輪實際得到的 `reason_code` 以外的全部值**：即「這個 intent 這次沒有以其他方式失敗」。看得到的效果：不需要記憶——用列舉代替記憶。代價：`ReasonCode` 有 6 個值，每個 intent 每輪要發 5 次搜尋；6 個 intent 就是 30 次額外呼叫，而 [req:FR-I4] 的單次操作上限**是已知未定值**（PRE-1 第 2 項）。

B. **每輪先列出「本 repo 全部開啟中的通報 issue」（一次搜尋），再對其中 intent 屬於本輪且本輪未再失敗的關閉**。看得到的效果：**每輪只多一次搜尋**，成本與 intent 數、`ReasonCode` 數皆無關；且它同時看得到 J-1 的重複 issue，可與 Q1 的處置合流。代價：需要一個能列舉「全部通報 issue」的查詢（label 即可），而那是本單元第一次需要「全域視野」——其餘方法都是逐鍵的。

C. **不自動收斂，由人關閉**：`resolve_if_open` 保留在介面上但不被任何流程呼叫。看得到的效果：零額外呼叫；且 ADR-A8 已明記「issue 被人工關閉後下次會開新的——這是想要的行為」，人關閉本來就是設計內的一環。代價：**通報 issue 會累積**。問題解決後沒有任何機制關閉它，P4 看到的開啟中通報數會持續失真，而 [US:S-8] 的價值正是「機制失敗會叫人」——叫了不收，久了就沒人看。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T12:14:28Z（讀自 date -u）· 每輪先列舉全部開啟中通報 issue -->
