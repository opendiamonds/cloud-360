# Domain Entities — U-9 自我測試 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 繼承的斷言清單（本站逐項核對，非概括承受）

六項散在四個單元的「規則已定但沒有斷言」被指向本單元。**上游有一項明文要求本單元「明確承接或明確拒收」**（U-8 的 `reliability-requirements.md`），故本檔逐項給判定，不整批收下。

| # | 斷言內容 | 來源 | 本站判定 |
| --- | --- | --- | --- |
| A-1 | U-1 的 output 不含憑證樣式 | U-1 `security-requirements.md`（[Q2=A]） | **承接**。fixture 驅動，純字串比對 |
| A-2 | 同一個 `Block` 在兩次獨立執行中序列化逐位元相同（涵蓋三種情形各一例） | U-2 `tech-stack-decisions.md` | **承接**。純函式，最容易斷言的一項 |
| A-3 | 受管區塊在無漂移時不重寫（連續兩輪） | U-2 `business-rules.md` **R-2 群**（R-2.3 的說明段） | **承接並確認落點**——見下方註 |
| A-4 | 反向 PR 的 diff 不含 `aidlc-state.md` 任何一行（[US:S-6 AC 2]） | U-8 `business-rules.md` R-2.1 | **承接** |
| A-5 | PR 建立失敗時分支被刪除；刪除也失敗則保留孤兒分支，**兩者都在同一次執行內紅燈**並附 intent id 與分支名 | U-8 `reliability-requirements.md`、`business-rules.md` R-6.3 | **完全承接**（run 內），見下方 |
| A-6 | U-8 實際寫入的路徑集合 ⊆ U-10a／U-10b 的 `paths-ignore` glob 集合 | U-10b `tech-stack-decisions.md` | **承接**。這是靜態的跨檔一致性檢查，不需執行期 |

> **A-3 的引用先前有兩處與原文不符，已更正。** 其一，來源在 U-2 的 **R-2 群**（雜湊）而非 R-1 群。其二，先前寫成「該註寫『在 U-6 的自我測試中』」並據此宣稱本站做了落點更正——**U-2 的原文是「但那是 U-6／U-9 的落點，本站只標出」**，U-9 本來就在候選清單內。本站做的是**確認並承接**，不是發現並更正。結論（落在 U-9）不變，但「來源在哪」與「本站做了什麼」兩點都要如實寫。

### A-5：先前拆成兩半，reviewer iteration 2 後**撤回其中一半**

**先前的處置**：拆成「run 內錯誤處理分支的斷言」（U-9）＋「執行期不變量的偵測」（指派 U-7 對帳，偵測「`pending_reverse` 非 `null` 卻無對應開啟中 PR」）。

**撤回第二半的理由**：U-8 的 `business-rules.md` **R-6.0** 推導出——`pending_reverse` 的寫入騎在反向分支上，所以它在 `ut` 上非 `null` **等價於「有一則反向 PR 合併過」**。於是那個偵測條件的兩個子句自相矛盾，**永遠不會為真**。U-7 依此規格實作出來的欄位會是一段永不觸發的死碼，卻在文件上呈現為「已解決」。

**這是我在 iteration 1 修正時引入的問題，不是原始缺口**。原始缺口（`pending_reverse` 無清除時機）的 (b) 半邊實際上不存在——那個「不一致狀態」構造上就不可達。

**現在的處置**：A-5 **完全由本單元承接**，內容改為 run 內可斷言的部分——注入一次必然失敗的 PR 建立呼叫，斷言 (1) 分支被刪除、(2) 該次執行紅燈且訊息含 intent id 與分支名。**對 U-7 的指派已撤回**，U-7 的 `ReconcileReport` 不新增任何欄位。

**仍然驗不到的部分（誠實記載）**：真實失敗（配額、網路、權限）下的行為。注入式測試驗的是錯誤處理分支存在且正確，不是它在所有真實失敗形態下都會被走到。

## fixture 集

| fixture | 驅動什麼 | 為何是 fixture 而非真實呼叫 |
| --- | --- | --- |
| record 文字樣本（`<record>/.test-fixtures/`，見下） | U-1 的七條判定順序與 `get_field` 四行為 | [US:S-10 AC 1] 的前提是 U-1 可被純文字驅動，**不得有網路或檔案系統 I/O** |
| `Block` 序列化樣本 | A-2 的逐位元相同 | 同上 |
| 憑證樣式樣本 | A-1 | 必須是**不會通過 secret 掃描器的假樣式**——見下 |

> **fixture record 的位置與它為何不會變成第 7 個 intent。** [ad:component-methods.md] 已定案：事件路徑（S-A）與排程路徑（S-B／S-C）**一律以 `intents.json` 的 registry 為選取來源**，不得依事件 diff 推導 record；fixture record 不註冊進 registry，所以 `<record>/.test-fixtures/` 兩條路徑都不會選中它。**本單元沿用該落點，不另尋位置**——換位置等於重新打開那個已由 reviewer iteration 1 Finding 2（Critical）收斂過的問題。（另注：`.test-fixtures` 不以 `.aidlc-` 開頭，不落入 `.gitignore:52` 的排除，故可進版控。）

> **A-1 的 fixture 有一個必須先解的衝突。** 要斷言「output 不含憑證樣式」，最直覺的做法是準備一個含憑證樣式的輸入。但 `project.md ## Forbidden` 逐字警告：`validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS`「**不分辨『示範』與『洩漏』，會直接紅燈**」。
>
> **處置**：fixture 使用**結構相同但不觸發掃描器**的假樣式（例如把 PEM 標頭與雲端 secret 環境變數名做字元替換），並在 fixture 檔內註明為何不能用真樣式。**這一點必須寫進實作註解**，否則下一個「修好」它的人會讓 CI 紅燈且不明所以。

## 繼承斷言把本單元的元件範圍**擴張**到上游記載之外

[ad:components.md] 的 workflow 對照表把 `aidlc-sync-selftest.yml` 的職掌記為「以 fixture 驅動 **C-1／C-2**；對獨立測試 Project 驅動 **C-3**」。但上表六項斷言中有四項不在這個集合內：

| 斷言 | 觸及的元件 | 在上游記載的 selftest 範圍內？ |
| --- | --- | --- |
| A-1 | C-1（`sync-map` 的 output） | 是 |
| A-2、A-3 | **C-6 `managed-block`**（`render`／`content_hash`，[ad:component-methods.md] 列為純函式） | **否** |
| A-4、A-5 | **C-4**（寫檔與 `commit_and_push`） | **否** |
| A-6 | 無執行期元件（靜態跨檔比對） | 不適用 |

**這不是上游寫錯，是本 stage 造成的擴張。** 那四項的路由決定都發生在 construction 的 per-unit 設計中（U-2、U-8、U-10b），時間上晚於 application-design。**必須明記為擴張而非迴歸**——否則單純比對 `components.md:109` 與本檔的人會判定兩者矛盾。

**擴張的合理性**：A-2／A-3 觸及的 `render`／`content_hash` 是[ad:component-methods.md] 明列的**純函式**，用純文字 fixture 驅動與 C-1／C-2 同一形狀、同一段（第一段），不引入任何新能力。A-4／A-5 落在第二段，本來就要對測試 Project 做真實讀寫。**因此擴張的是覆蓋範圍，不是本單元的技術形狀。**

## 測試 item 的生命週期

[ug:unit-of-work.md] 的實作註記已點名危害：常駐測試 item 於 #16 會成為第 72 張卡進入 P3 視野，且並行 CI 寫同一 item 會觸發回讀不符而**自動增生 issue**（[ad:ADR-A3]）。

| 屬性 | 決定 |
| --- | --- |
| 位置 | **獨立測試 Project**，不在 #16 |
| 生命週期 | **本次執行專屬**——建立於執行開始，刪除於結束（含失敗路徑） |
| 並行 | 每次執行自己的 item ⇒ 並行 CI 不互相寫同一個 item ⇒ ADR-A3 的增生路徑不成立 |

**獨立測試 Project 是一個外部依賴**（需組織層建立），與 E-1 的憑證屬同一類。它是否已列入 `external-dependency-map.md` 的 E-1～E-4，本站未逐項核對——**列為 Bolt 4 前必須確認的一項**。

## 與上游的對應

本單元的擁有範圍、交付物、完成判準（三項突變）與測試 item 的危害引自 [ug:unit-of-work.md] 的 U-9；[ad:S-D] 的兩段式驗證與 [ad:ADR-A3] 的回讀不符增生引自 `application-design`；[US:S-10 AC 1]、[US:S-6 AC 2] 引自 `stories.md`；六項繼承斷言的原文分別引自 U-1、U-2、U-8、U-10b 的對應 artifact；`FORBIDDEN_CONTENT_PATTERNS` 不分辨示範與洩漏引自 `project.md ## Forbidden`；`ReconcileReport` 的欄位契約引自 U-7 的 `domain-entities.md`；`aidlc-sync-selftest.yml` 的元件職掌引自 [ad:components.md] 的 workflow 對照表；`get_field` 四行為、`render`／`content_hash` 為純函式、以及 fixture record 不進 registry 的選取邊界引自 [ad:component-methods.md]；S-D 的兩段生命週期、[Q4=A] 的獨立測試 Project 理由與「突變驗證是 AC 本身的一部分」引自 [ad:services.md]；本單元擁有 [US:S-10] 全部 AC（1–5）且只擁有這一則故事，引自 [ug:unit-of-work-story-map.md]。
