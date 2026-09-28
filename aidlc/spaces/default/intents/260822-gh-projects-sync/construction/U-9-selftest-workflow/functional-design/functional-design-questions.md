# Functional Design — U-9 自我測試 workflow（問題與裁定）

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## CONDITIONAL 適用性判定

| 條款 | 適用 | 理由 |
| --- | --- | --- |
| New data models | ✅ | fixture 集是本單元定義的新資料形狀（record 文字樣本、`Block` 序列化樣本、憑證樣式樣本），且有存放位置與版控決定 |
| Complex business logic | ✅ | 兩段式驗證的順序、失敗語意的兩類分辨、清理的失敗路徑，都是需要設計而非顯而易見的邏輯 |
| Business rules need design | ✅ | 六項繼承斷言的承接判定、A-5 的兩半拆分、觸發 allowlist 與 U-10a／U-10b 排除集合的無交集關係 |
| Skip if simple logic changes | ❌ | 不適用——本單元是新建的 workflow，非既有邏輯的小改 |

## 本站裁定（**未經人工提問**）

**授權來源**：使用者在本 session 中止一次 AskUserQuestion 並輸入「continue」，指示不再逐題提問、由 conductor 自行判斷。**以下各項均非人工裁決**，逐項標示的目的是讓任何讀者都不會把它們誤讀為已核可的上游事實。

### E-3. 六項繼承斷言的逐項判定

散在 U-1／U-2／U-8／U-10b、指向本單元的六項「規則已定但無斷言」，**逐項給判定而非整批收下**。判定表在 `domain-entities.md`。

**為何不整批收下**：U-8 的 `reliability-requirements.md` 明文要求本單元「**明確承接或明確拒收**」。整批收下等於沒有回答那個要求，且會讓「本單元到底要驗什麼」在 Bolt 4 才第一次被盤點。

**判定結果**：A-1、A-2、A-4、A-5、A-6 完全承接；A-3 承接並確認落點（U-2 原文已把 U-9 列為候選）。A-5 在 iteration 1 曾判為部分承接，iteration 2 後改為完全承接（見 E-4）。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T14:01:39Z（讀自 date -u） -->

### E-4. A-5 的承接範圍（**iteration 2 後已改寫**）

**iteration 1 的裁定**：拆成「run 內錯誤處理分支的斷言」（本單元）＋「執行期不變量的偵測」（指派 U-7 對帳）。

**iteration 2 撤回第二半。** U-8 的 R-6.0 推導出 `pending_reverse` 的寫入騎在反向分支上，它在 `ut` 上非 `null` **等價於「有一則反向 PR 合併過」**，於是原偵測條件（非 `null` 且從未有過 PR）的兩個子句自相矛盾、永不為真——U-7 依此實作出來的會是一段永不觸發的死碼，卻在文件上呈現為「已解決」。**這是我在 iteration 1 修正時引入的問題**，reviewer iteration 2 判為新的 Critical。

**現在的裁定**：A-5 **完全由本單元承接**，內容為 run 內的注入式斷言——注入一次必然失敗的 PR 建立呼叫，斷言 (1) 分支被刪除、(2) 該次執行紅燈且訊息含 intent id 與分支名。**U-7 的 `ReconcileReport` 不新增任何欄位，原指派撤回。**

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T14:24:03Z（讀自 date -u） -->

### E-5. 元件範圍擴張的揭露方式

繼承斷言使本單元觸及 [ad:components.md] 的 selftest 對照表未列的 C-6（A-2／A-3）與 C-4（A-4／A-5）。**明記為本 stage 造成的擴張而非上游錯誤**，並附時序論證。

**理由**：不寫這一句，單純比對 `components.md` 與本單元產出的人會判定兩者矛盾。這是 `project.md` 已記載的形狀（下游修正上游內部瑕疵時必須明記是對齊而非新定案）。

[Answer]: 本站裁定，非人工裁決  <!-- 2026-08-29T14:01:39Z（讀自 date -u） -->

## Revision — reviewer iteration 1 之後

reviewer 判定 NOT-READY（1 Critical、2 Major、1 Minor），四項全部修正：

| # | 發現 | 處置 |
| --- | --- | --- |
| 1（Critical） | `pending_reverse` 在 U-4／U-6／U-8 任一處都沒有清除時機，使 U-8 的防重複判斷只生效一次、且 A-5 指派給 U-7 的偵測在每次成功同步後都誤報 | **U-8 新增 R-6 群**（R-6.1 防重複改用即時查詢、R-6.2 正常解決後清除、R-6.3 從未有過 PR 則不清除並紅燈）；U-4 的指派敘述收斂；本單元 A-5 的偵測條件據此改寫為可實作的定義 |
| 2（Major） | A-3 的來源引用寫成 U-2 的 R-1 群（實為 R-2 群 R-2.3），且把「確認」寫成「更正」 | `domain-entities.md` 已更正兩處並加註說明原文為何 |
| 3（Major） | 本單元是唯一沒有 `functional-design-questions.md` 的單元，三項本站裁定沒有比照 U-6／U-8 的揭露格式 | **本檔即為補正** |
| 4（Minor） | `business-rules.md` 的 R-6 排在 R-5 之前 | 已互換 |

**reviewer 自陳的驗證缺口（原樣轉錄，不代為結案）**：讀取範圍被工具限制在具名整合點，未能讀取 U-3 與 U-10a 的任何檔案，因此「六項繼承斷言是否窮舉」對這兩個單元未經驗證。本站補做了該項核對——對全 intent 的 functional-design 與 nfr-requirements 產出 grep「落點為 U-9」「U-9 的斷言」等路由字樣，U-3 與 U-10a 均無指向本單元的項目，六項維持。**此為本站自行複驗，非 reviewer 的結論。**

## 與上游的對應

CONDITIONAL 條款引自 `.claude/aidlc-common/stages/construction/functional-design.md`；六項繼承斷言的原文分別引自 U-1 `security-requirements.md`、U-2 `business-rules.md` R-2 群與 `tech-stack-decisions.md`、U-8 `business-rules.md` 與 `reliability-requirements.md`、U-10b `tech-stack-decisions.md`；「明確承接或明確拒收」的要求引自 U-8 `reliability-requirements.md`；selftest 的元件職掌引自 [ad:components.md]；`pending_reverse` 的清除規則見 U-8 `business-rules.md` R-6 群；揭露格式比照 U-6 與 U-8 的同名檔。

## Revision — reviewer iteration 2（驗證輪）

verdict 仍為 NOT-READY，但性質不同：#2／#3／#4 三項修正經查證全部成立，**#1 只成立一半**，且我在修它時引入了一個新的 Critical。

| 項 | 結果 |
| --- | --- |
| #1 (a) 防重複開 PR 改即時查詢 | **成立**。與 U-6 的 R-2.1 無語意衝突 |
| #1 (b) R-6.2／R-6.3 的清除與偵測規則 | **不成立**——所描述的狀態構造上不可觀察。**已整組移除**，改寫為 R-6.0（推導）＋ R-6.2（不清除，因無讀者）＋ R-6.3（原子性失敗是 run 內條件） |
| #2 A-3 來源引用 | 成立（reviewer 逐字核對 U-2 第 18–29 行） |
| #3 本檔的揭露格式 | 成立（reviewer 以 `TZ=UTC stat` 與 audit shard 交叉驗證時間戳非造假） |
| #4 R-5／R-6 順序 | 成立 |

**本輪額外發現（reviewer 未提，本站自查）**：即使 R-6.2 的狀態可達，清除動作的**成本也不合理**——R-1.5 明訂 U-8 **不得直接推 `ut`**，所以「把欄位寫回 `null`」得為每一次反向事件再開一則 PR，讓人審一個沒有任何讀者的欄位歸零。

> **此處先前寫「無盡遞迴」，已更正（reviewer iteration 3 的 Minor）。** 一則寫 `null` 的清除 PR 合併後不會自動再製造出待清狀態，除非清除規則被天真地定義成對自己也適用。R-6.2 的結論不靠這個論證——它獨立地建立在「沒有任何讀者」這個已被查證的事實上。

**reviewer 揭露的驗證缺口，其中一項可以就地結案**：它把「讀不到 U-10a 的 `functional-design/` 四檔」記為工具限制下的推論。**那不是讀取限制——U-10a 沒有 functional-design 產出是事實**：該單元 `kind: packaging`，而 functional-design 的 produces 不涵蓋 packaging，本 intent 12 個單元中 U-10a／U-10b 兩個都只有 nfr-requirements 產出。它對 U-3 的 functional-design 四檔＋兩份 nfr 已通讀無漏接；U-3 剩餘三份 nfr 檔仍是未覆蓋項，如實保留。
