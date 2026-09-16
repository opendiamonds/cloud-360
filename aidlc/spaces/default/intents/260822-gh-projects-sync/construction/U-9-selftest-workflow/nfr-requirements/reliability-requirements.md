# 可靠性需求 — U-9 自我測試 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 本單元的失敗語意必須分成兩類，否則它會自我毀滅

[ad:services.md] 的 S-D 逐字把本單元定為**真閘門**：斷言失敗即 CI 紅燈。但第二段依賴外部服務，**外部錯誤也會讓它紅燈**——而這兩種紅燈的意義完全相反：

| 紅燈類型 | 意義 | 正確反應 |
| --- | --- | --- |
| **斷言失敗** | 同步機制真的壞了 | 修 code，不得重跑 |
| **外部錯誤**（API 5xx、配額、測試 Project 不存在） | 機制沒壞，環境有問題 | 重跑或修環境 |

**若兩者在 CI 上長得一樣，人會學會「紅了就重跑」——那正是第一類紅燈最不該得到的反應。**

**規則**：兩類必須在 **exit 訊息的第一行**即可分辨，且斷言失敗的訊息含預期與實得（`business-rules.md` R-1.1）。**本站不指定 exit code 的具體數值**（那是實作細節），但**指定必須可分辨**。

## 清理是可靠性需求，不是整潔問題

`business-rules.md` R-4 要求清理以 `if: always()` 等價形式宣告。理由已在該檔說明——殘留 item 會讓下一次執行假紅燈。

**這裡補一項後果的量級**：`business-logic-model.md` 的錯誤表把「清理失敗」定為**紅燈**且訊息須含殘留 item 的識別資訊。若清理失敗只記 warning，殘留會累積，而累積的殘留會讓本單元進入前一節描述的「紅了就重跑」狀態——**一個為了發現問題而存在的 workflow，變成問題的來源**。

## 對外部依賴的容忍度：不重試，直接紅燈

第二段的外部呼叫**不做自動重試**。

理由與 U-6／U-7 相反，且這個相反是刻意的：那兩者是生產路徑，重試換取的是「同步不因一次抖動而漏掉」；本單元是**驗證**路徑，重試換取的是「綠燈」——**而一個靠重試才綠的驗證，證明的東西比它宣稱的少**。若外部真的不穩到需要重試，那件事本身就該被看見。

**代價（誠實記載）**：本單元會比 U-6／U-7 更常因外部因素紅燈。這是前一節的分類規則存在的原因——外部錯誤紅燈必須一眼可辨，否則這個代價會轉成「重跑文化」。

## 本單元不可靠時的下游後果

本單元是六項繼承斷言（見 `../functional-design/domain-entities.md`）的**唯一**執行點。它不可靠的後果不是「少了一層保護」，而是**六條防線同時失效且無訊號**。

**這是 Bolt 4 的 Definition of Done 應該包含「三條突變各驗一次」的實質理由**——不是儀式，是這六條防線唯一的存在證明。

## 既有技術堆疊的承接

[ck:technology-stack.md] 記載 `ui-regression` 是本 repo 唯一的前端自動化驗證層且為真閘門（`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`，`retries: 1`、容忍 `stats.flaky`）。**本單元刻意不採用它的 `retries: 1`**——理由見上方「不重試」一節：Playwright 的 flaky 來自瀏覽器與時序，本單元的第二段沒有等價的不確定性來源，容忍 flaky 只會遮蔽真實問題。

## 與上游的對應

S-D 的「真閘門」失敗語意引自 [ad:services.md]；U-9 的完成判準與三條突變引自 [ug:unit-of-work.md]；R-1.1（訊息含預期與實得）、R-4（清理）與 R-3 見本單元的 `business-rules.md`；錯誤表與六項繼承斷言見 `../functional-design/business-logic-model.md` 與 `domain-entities.md`；U-6／U-7 的重試設定引自各自的 `business-rules.md`；`ui-regression` 的閘門形狀與 `retries: 1` 引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）與 `team.md`。
