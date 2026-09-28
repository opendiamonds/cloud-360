# Business Rules — U-5 通報

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-5-notifier · kind: library -->

## R-1 群：什麼該通報、什麼該紅燈

兩件事**不是同一件事**，[ad:component-methods.md] 與 [ad:services.md] 對兩者分別定義。

| `reason_code` / 結果 | 通報？ | 紅燈？ | 依據 |
| --- | --- | --- | --- |
| `suppressed`／`parked`／`unparseable`／`whitelisted`／`undecidable` | **否** | 否 | 機制的正常判斷 |
| `Aborted`（回讀不符） | **是** | **否** | [req:FR-C1] 的主動中止 |
| `CannotCreate`（欄位建不出來） | **是** | 否 | 交 C-5 通報「需人工建立欄位」 |
| `ExternalError` | 是 | **是** | [ad:services.md] 的兩種紅燈之一 |
| `Rejected` | 是 | **是** | 另一種 |
| 對帳成功補平 | 否 | 否 | [US:S-7 AC 5] |

**R-1.1**：通報與紅燈**各自獨立判定**，不得以其中一個推導另一個。`Aborted` 與 `CannotCreate` 是「通報但不紅燈」的存在證明。

## R-2 群：`notify` 的收斂演算法（[Q1=A]）

1. 以 `FailureIdentity` 為鍵搜尋**開啟中**的通報 issue（label `aidlc-sync-alert` ＋ 內文首行的機器可讀鍵）。
2. **命中 0 筆** → 開新 issue，內文含 intent 識別字、stage 標識、ISO 8601 時間戳（[req:FR-E3]）＋ 機器可讀鍵首行。
3. **命中 1 筆** → 追加一則 comment（本輪時間戳與細節），標題計數 +1。
4. **命中 >1 筆（[Q1=A] 新增）** → 取 **issue 編號最小者**（最舊）追加 comment 與計數；其餘同鍵 issue **關閉**並各留一則 comment 註明「與 #<最舊> 重複」。

**第 4 步修的是 ADR-A8 一條走不通的路徑**：該 ADR 的 Consequences 說重複「由下輪的 `resolve_if_open` 收斂」，但 `resolve_if_open` 只在**失敗不再發生時**被呼叫——重複正是在失敗持續時產生的。改由 `notify` 自己收斂後，**下一次失敗發生時**重複即被清掉，ADR-A8 補回的二元 AC（開啟中數為 1）因此在第二輪成立。

**R-2.1（安全約束）**：第 4 步是本單元唯一的**破壞性動作**。關閉條件必須是「內文首行的機器可讀鍵**逐字相符**」，**不得**以標題比對——標題會被人編輯。鍵不相符即不關，寧可留下重複。

**R-2.2**：「最舊」以 **issue 編號**判定，不以建立時間——編號單調遞增且不受時區或 API 回傳格式影響。

## R-3 群：`resolve_if_open` 的觸發（[Q2=A]）

**每輪同步的最後一步**，執行一次：

1. 以 label `aidlc-sync-alert` 列舉**全部開啟中**的通報 issue（**一次**查詢）。
2. 解析各自內文首行的機器可讀鍵，得 `(intent_id, reason_code)`。
3. 對其中 `intent_id` **屬於本輪處理範圍**、且本輪**未再產生該 `reason_code`** 的 issue：關閉，並留一則 comment 說明「本輪未再發生」。
4. `intent_id` 不屬於本輪處理範圍者：**不動**（本輪沒有資訊可判定它）。

**成本：每輪多一次查詢**，與 intent 數、`ReasonCode` 數皆無關。被否決的逐鍵列舉（Q2=B）在 6 個 intent × 5 個 reason_code 下是 30 次額外呼叫，而 [req:FR-I4] 的單次操作上限是已知未定值（PRE-1 第 2 項）。

**R-3.1**：第 3 步的「本輪未再產生」判定所需的資料**全部在本輪的記憶體內**（本輪每個 intent 的 `Decision` 與寫入結果），不需要任何跨輪持久狀態——**ADR-A8 的「零新增持久狀態」前提維持成立**。

**R-3.2**：第 4 步的「不動」是刻意的。排程對帳（S-B）處理全部 intent，事件同步（S-A）在 [ad:services.md] 的 registry 驅動選取下也掃全部 registry——所以實務上第 4 步很少觸發。但把它寫明，是為了讓「本輪沒看到的 intent 不會被誤關」成為規則而非巧合。

## R-4：通報本身失敗

**拋，不遞迴通報**（[ad:component-methods.md] 逐字）。

理由值得寫明：通報失敗時再開一則「通報失敗」的通報，會在 GitHub API 持續失敗的情況下產生無限迴圈。拋出後由 workflow 層紅燈，人從 workflow log 看到。

## 與上游的對應

收斂演算法與 `FailureIdentity` 引自 [ad:decisions.md] ADR-A8 與 [ad:component-methods.md] §C-5；通報／紅燈的分流引自同處與 [ad:services.md]；FR-C1／FR-E3／FR-I4 引自 `requirements.md`；[US:S-7 AC 5]／[US:S-8] 引自 `stories.md`；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-5；AC 歸屬引自 [ug:unit-of-work-story-map.md]；issue 的可搜尋形狀見本單元的 `domain-entities.md`，資料流見 `business-logic-model.md`；元件分層引自 [ad:components.md]。
