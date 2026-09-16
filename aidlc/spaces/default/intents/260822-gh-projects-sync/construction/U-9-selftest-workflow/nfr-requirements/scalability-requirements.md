# 擴充性需求 — U-9 自我測試 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 本單元**不隨 intent 數成長**，這是它與其餘同步單元的根本差異

| 單元 | 隨 intent 數成長？ |
| --- | --- |
| U-6 正向 | 是（每次事件處理一個，但事件數隨 intent 成長） |
| U-7 對帳 | **是**——每輪 O(N) |
| U-8 反向 | **是**——每輪 O(N) |
| **U-9 自我測試** | **否**——fixture 是靜態的，第二段固定一張測試 item |

**這是刻意的設計後果，不是巧合**：[ad:component-methods.md] 定案「事件路徑與排程路徑一律以 `intents.json` 的 registry 為選取來源」，而 fixture record 不註冊進 registry。**同一個決定既讓 fixture 不會變成第 7 個 intent，也讓本單元的成本與 intent 數脫鉤。**

## 真正會成長的是 fixture 集

fixture 集隨**被斷言的行為數**成長，而那隨單元數與規則數成長。目前已知的六項繼承斷言（`../functional-design/domain-entities.md`）加上 U-1 的七條判定順序與 `get_field` 四行為，是第一版的規模。

| 成長來源 | 影響 |
| --- | --- |
| 新增同步行為（未來的 FR） | fixture 增加，第一段耗時線性增加 |
| 新增元件 | 可能需要擴張本單元的元件範圍（本 intent 已發生過一次，見 `../functional-design/domain-entities.md` 的擴張說明） |

**第一段是純文字比對、秒級**，即使 fixture 數翻十倍仍在 `performance-requirements.md` 的 10 分鐘上界內很遠的地方。**fixture 集的成長不是效能問題，是維護問題**——每個 fixture 都是一份必須跟著行為更新的資料。

## 一個不隨規模擴張、但會隨時間腐化的東西

fixture 反映的是**寫下它的當時**的行為。行為變了而 fixture 沒變時，兩種結果：

| 情形 | 結果 | 好壞 |
| --- | --- | --- |
| 行為改對了、fixture 沒更新 | **紅燈** | **好**——這正是閘門該做的 |
| 行為改錯了、fixture 被一起改成錯的 | 綠燈 | **壞**——閘門靜默失效 |

第二列沒有自動化解法。**緩解是 R-3 的 allowlist 涵蓋 fixture 集本身**：改 fixture 必然觸發本單元，於是那個改動至少會出現在一次 CI 執行的 diff 裡，而不是悄悄過去。**這是緩解不是解決**，如實記載。

## 並行

`business-rules.md` 與 `../functional-design/domain-entities.md` 已定：測試 item 為**本次執行專屬**，故多個 PR 並行時各寫各的 item。**[ad:ADR-A3] 的「並行 CI 寫同一 item 觸發回讀不符而自動增生 issue」路徑因此不成立**——這是 [Q4=A] 選擇獨立測試 Project 時就已納入的理由。

**本單元不需要 concurrency group。** 這與 U-8 的 P-2（必須自成第三組）相反，差別在於：U-8 的兩次執行會寫同一份 `sync-state.json`，本單元的兩次執行寫的是不同的 item。

## 與上游的對應

fixture record 不進 registry 的選取邊界與 `get_field` 四行為引自 [ad:component-methods.md]；[ad:ADR-A3] 的回讀不符增生與 [Q4=A] 的獨立測試 Project 引自 [ad:services.md] 與 [ug:unit-of-work.md] 的 U-9 實作註記；六項繼承斷言、元件範圍擴張與測試 item 生命週期見 `../functional-design/domain-entities.md`；R-3 的 allowlist 與 R-4 見本單元的 `business-rules.md`；10 分鐘上界見本單元的 `performance-requirements.md`；U-7／U-8 的 O(N) 掃描引自各自的 `business-logic-model.md`；U-8 的 P-2 concurrency 裁定引自其 `performance-requirements.md`；本 repo 既有 CI 與 gh-aw 盤點引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。
