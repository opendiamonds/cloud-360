# Business Rules — U-9 自我測試 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## R-1：三條完成判準都是**突變驗證**，不是「有跑就算」

[ug:unit-of-work.md] 的完成判準逐字給了三個突變與各自的預期紅燈：

| # | 突變 | 必須發生 |
| --- | --- | --- |
| R-1.1 | 把映射改壞（`[?]` → `In progress`） | CI 紅燈，**且輸出指出預期與實得** |
| R-1.2 | 把判定搬進 agent step | **靜態檢查**失敗 |
| R-1.3 | 憑證做範圍外寫入 | 回 **403** |

**R-1.1 的「輸出指出預期與實得」不是附帶要求。** 一個只印 `FAILED` 的斷言，在三個 Bolt 之後沒有人能從 CI log 判斷是映射改錯了還是 fixture 過期了。**斷言訊息必須含預期值與實得值兩者**。

**這三條與 `project.md ## Mandated` 的 `tcms-test-cases` 必做 3 是同一件事的兩處記載**：該規則要求「把修正改回錯的行為、確認測試紅燈、還原複驗」。本單元的完成判準就是它在本 intent 的具體化，**不是兩套要求**。

## R-2：靜態檢查（R-1.2）檢的是承載形式，不是程式碼品質

`project.md ## Forbidden` 於 2026-08-23 收窄後的規則，加上 ADR-0013，共同要求決定性的映射邏輯放在純 Actions 步驟、判斷性的工作才交給 gh-aw 的代理式引擎。

**R-1.2 是這條規則唯一的機械化落點。** 沒有它，「有人把判定搬進 agent step」只會被 code review 攔——而 code review 對「這段 prompt 裡多了一行判斷」的檢出率，本 repo 的三塊結構性盲區之一（所有 LLM 路徑）已經給過答案。

檢查的形狀：解析編譯後的 `.lock.yml`，斷言 `aidlc-sync-*` 系列 workflow 的**決定性 job**（映射、解析、回寫）不含任何代理式引擎步驟。**檢 `.lock.yml` 而非 `.md`**——NFR-M1 記載的漂移風險正是「改了 `.md` 未重編」，檢 `.md` 會被那條漂移繞過。

## R-3：本單元的觸發不得與 U-10a／U-10b 的排除相衝突

本單元的 `paths:` allowlist 涵蓋**同步機制本身**的檔案：`.github/workflows/aidlc-sync-*.md`／`.lock.yml`、`.github/actions/aidlc-sync-map/**` 與其 fixture 集。

**它不涵蓋 `<record>/sync-state.json`。** 這使 U-10a／U-10b 排除的那條 glob 與本單元的觸發集合**無交集**——反向 PR 不會觸發自我測試（它改的是資料不是機制），而改機制的 PR 一定會觸發自我測試且不會被任何 `paths-ignore` 擋掉。

**A-6 斷言的正是這個關係**：U-8 實際寫入的路徑集合 ⊆ `paths-ignore` glob 集合，且該 glob 集合 ∩ 本單元的 allowlist ＝ ∅。**兩個條件必須一起斷言**——只驗前者，某天有人把機制檔加進 `paths-ignore` 時不會有東西失敗，而那會讓自我測試對機制變更靜默失效。

## R-4：清理必須在失敗路徑上也執行

測試 item 是本次執行專屬（見 `domain-entities.md`）。**清理步驟必須以 `if: always()` 等價形式宣告**，否則斷言失敗時 item 留在測試 Project 上，下一次執行看到殘留。

殘留的後果不是髒資料而是**假紅燈**：下一次執行可能因為看到不屬於自己的 item 而失敗，於是有人開始把自我測試的紅燈當成雜訊。**一個會誤報的閘門，比沒有閘門更快失去作用。**

## R-5：本單元不擁有的部分

| 事項 | 擁有者 |
| --- | --- |
| 映射邏輯本身（[ad:components.md] 的 C-1） | U-1 |
| 受管區塊的 `render`／`parse`／`content_hash`（C-6，[ad:component-methods.md] 列為純函式） | U-2 |
| 反向 PR 的產生 | U-8 |
| `paths-ignore` 的實際設定 | U-10a（`ci.yml`）／U-10b（四支 gh-aw） |
| 反向 PR 的原子性失敗**在 run 內**的錯誤處理 | **U-8**（R-6.3 定義行為）；**本單元驗它**（A-5 完全承接，不再拆半——對 U-7 的指派已於 reviewer iteration 2 撤回） |

## R-6：本單元擁有 [US:S-10] 的**全部**五條 AC，且只擁有這一則故事

[ug:unit-of-work-story-map.md] 的對照表逐字記「**S-10** 映射端到端與權限都有斷言 | AC 1–5 | U-9」，且反向的單元→故事表只列 `U-9 | S-10`。

**這在本 intent 的十二個單元中是唯一的一對一。** 其餘單元多半承載跨故事的片段（U-8 只拿 S-6 的 AC 1–5，AC 6、7 在別處）。後果有二：

- **本單元完成 ＝ S-10 完成**，不需要跨單元協調驗收；
- 但反過來，**沒有別的單元會替它補任何一條 AC**。漏掉一條就是那條沒有承接者。

[ad:services.md] 對 S-D 的「失敗語意」欄逐字寫「**這是真閘門**：斷言失敗 → CI 紅燈（[US:S-10 AC 1／AC 2]）」，且「突變驗證」欄寫明它「**是 AC 本身的一部分，不是另立的元層次 AC**」——這與 `project.md` 的既有教訓（元層次 AC 驗收的是有沒有寫測試而非功能對不對）一致，R-1 的三條突變因此是行為斷言而非交付條件。

## 與上游的對應

三條完成判準與突變內容引自 [ug:unit-of-work.md] 的 U-9；[ad:S-D] 的兩段式驗證引自 `application-design`；承載形式的規則引自 `project.md ## Forbidden`（2026-08-23 收窄版）與 ADR-0013；`tcms-test-cases` 的突變驗證要求引自 `project.md ## Mandated`；三塊結構性盲區引自同檔；NFR-M1 的 `.md` ↔ `.lock.yml` 漂移引自 `requirements.md`；A-6 與 `paths-ignore` glob 集合引自 U-10b 的 `tech-stack-decisions.md`；U-8 的寫入路徑引自其 `business-logic-model.md`；S-D 的失敗語意與突變驗證的定位引自 [ad:services.md]；selftest 的元件職掌與四支 workflow 的觸發對照引自 [ad:components.md]；`render`／`content_hash` 的純函式性質與 `get_field` 的行錨定語意引自 [ad:component-methods.md]；S-10 的 AC 歸屬（AC 1–5 全歸 U-9）引自 [ug:unit-of-work-story-map.md]。
