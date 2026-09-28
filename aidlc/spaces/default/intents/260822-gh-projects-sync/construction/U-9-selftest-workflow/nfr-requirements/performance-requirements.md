# 效能需求 — U-9 自我測試 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 兩段的順序就是本單元的效能設計

| 段 | 需要什麼 | 典型耗時 | 失敗訊息的精確度 |
| --- | --- | --- | --- |
| 第一段 fixture dry-run | 無網路、無憑證 | 秒級 | **高**——指得出是哪一條判定、預期與實得 |
| 第二段端到端 | 憑證、外部服務、建立與刪除測試 item | 分鐘級，且受 GitHub API 與 runner 排隊影響 | 較低——失敗可能是外部的 |

**第一段全綠才跑第二段。** 這不只是省時間：一個 fixture 級的錯誤若以「端到端失敗」的面貌出現，診斷成本高一個量級，而診斷成本高的閘門會被當成雜訊。

## 執行時間必須有上界，且本單元的手段與 `ui-regression` 不同

`ui-regression.md` 的註解逐字記載本 repo 上真實發生過的事：PR #510 上一個 stalled browser download 跑了 5h59m24s 才被 GitHub 在 6 小時上限砍掉、無可下載 log，重跑又 stall 一次，**單一 PR 約七小時 runner、零測試執行**。

它同時記載了為何顯而易見的修法無效：**gh-aw v0.81.6 在編譯 pre-agent-steps 時會靜默丟棄 `timeout-minutes`**（`env`／`id`／`if`／`uses`／`with`／`working-directory`／`continue-on-error` 都保留，`timeout-minutes` 不保留）且回報 0 errors / 0 warnings，因此該檔的每個長步驟改用 `run:` 內的 `timeout(1)` 包住。

**本單元不受這個限制**：它是純 Actions（見 `tech-stack-decisions.md`），沒有 gh-aw 編譯步驟，**`timeout-minutes` 正常生效**。

| 層級 | 上界 | 理由 |
| --- | --- | --- |
| workflow 層 `timeout-minutes` | **10** | 第一段秒級、第二段分鐘級；超過即代表卡住而非慢 |
| 第二段的每個 API 呼叫 | 沿用 U-3 的重試與逾時設定 | 不另立一套 |

**10 分鐘不是量測值而是估計值**，須在 Bolt 4 首次真實執行後複核。**寫下它的理由是：沒有上界的預設是 GitHub 的 360 分鐘，而這個 repo 已經被那個預設咬過一次。**

## 觸發頻率

`pull_request`，且僅當同步機制相關路徑變動（`business-rules.md` R-3 的 allowlist；**該 allowlist 必須涵蓋 `.github/workflows/aidlc-sync-*.yml` 而非 `*.md`／`*.lock.yml`**——四支 workflow 為純 Actions，2026-08-30T06:11:59Z 更正）。本 intent 交付完成後，**觸及那些路徑的 PR 會是少數**——這支 workflow 的常態是不執行。

**這是刻意的，也是它的弱點**：一支很少跑的閘門，壞掉時不會立刻被發現。緩解是 R-3 的 allowlist 涵蓋 fixture 集本身（改壞 fixture 等於改壞斷言，必然觸發），以及 Bolt 4 的完成判準要求三條突變各驗一次。

## 既有技術堆疊的承接

[ck:technology-stack.md] 記載本 repo 的 CI 現況為 `ci.yml`（4 job）＋ `deploy.yml`（3 job）＋ 11 組 gh-aw，且其 gh-aw 基準為 `v0.81.6` 而 `origin/ut` 已是 `v0.86.2`。**上述 `timeout-minutes` 被丟棄的行為是對 v0.81.6 的實測，未在 v0.86.2 複驗**——本單元不依賴它（純 Actions），但 U-10b 要修改的四支 gh-aw workflow 仍在該風險面上。

## 與上游的對應

S-D 的兩段生命週期引自 [ad:services.md]；U-9 的完成判準引自 [ug:unit-of-work.md]；`ui-regression` 的七小時事件與 `timeout-minutes` 被靜默丟棄引自 `.github/workflows/ui-regression.md` 的註解（本站實讀）與 [ck:technology-stack.md] 的盤點；觸發 allowlist（R-3）、突變三條（R-1）與清理規則（R-4）見本單元的 `business-rules.md`；兩段順序的理由與錯誤表見 `../functional-design/business-logic-model.md`；U-3 的重試與逾時引自該單元的 `business-rules.md`；本 repo 既有 CI 與 gh-aw 版本落差引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。
