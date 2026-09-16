# Security Requirements — U-7 對帳 workflow 與編排器

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## ADR-0006 四面向

| 面向 | 判定 | 內容 |
| --- | --- | --- |
| **IAM** | **完全適用** | 與 U-6 同：憑證從 workflow secret 進入各 action 的入口。權限集合依 **ADR-0014** 為三項 |
| **Encryption** | 適用（平台承擔） | HTTPS；不落地憑證 |
| **Network exposure** | 不適用 | 只有出站呼叫 |
| **Audit logging** | **完全適用，且本單元的產出就是稽核材料** | 見 SEC-2 |

> **權限集合現為四項（ADR-0015 §8）**：ADR-0014 補入的是第三項 Issues 寫入，而 §8 進一步指出**開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限**，第四項為 `Pull requests: write`（佐證：`deploy.yml:174-175` 在本 repo 上正在運行的設定即分列兩行）。本檔沿用的是 NFR-S1 當時的三項計數，更正指令與閘門（Bolt 0，須在憑證鑄造前）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。指標補於 2026-08-30T01:31:09Z。

## SEC-1：本單元讀取**全部** record，是機制中讀取面最廣的一個

U-6 由事件驅動，實務上也掃全部 registry；但本單元是**設計上就要掃全部**——它的價值就在於覆蓋完整。

**這放大了兩件已記載的事**：

1. **U-3 的 SEC-4**（錯誤訊息可能挾帶憑證片段）：本單元每天對每個 intent 各發約 4 次呼叫，**產生錯誤訊息的機會是 U-6 的數倍**。該約束（交給 C-5 的 `message` 只得含 `errors[].message` 與 HTTP 狀態碼）在此更要緊。
2. **U-5 的 SEC-2**（通報內容出現在公開 issue）：同理。

**兩者都不是本單元新增的風險，是既有約束在此的暴露面放大。**

## SEC-2：報告發布在公開的 job summary 上

`tech-stack-decisions.md` 的缺口 M-1 裁定報告落在 `$GITHUB_STEP_SUMMARY`。**本 repo 為 public，該摘要公開可讀。**

逐項檢視報告的六份清單與兩個數字：

| 內容 | 揭露什麼 | 判定 |
| --- | --- | --- |
| 六份清單（皆為 `[intent_id]`） | 哪些 intent 處於哪種狀態 | **無敏感性**——intent id 即 record 目錄名，已公開 |
| `backfilled_count`、一致率 | 機制的健康度 | 無敏感性 |
| `latency_samples` | 同步耗時 | 無敏感性 |

**判定：不構成暴露。** 報告全部由已公開的事實聚合而成。

**約束（二元可判）**：報告**不得**包含各 intent 的 `Decision.traceable_row` 全文、record 內容片段、或任何 API 回應 body。它只放 id 與數字。**理由與 U-3 的 SEC-4 同族**：聚合視圖是最容易在除錯時被順手加上「多印一點細節」的地方。

## SEC-3：一致率是安全性質的指標，不只是品質指標

[req:NFR-O2] 的一致率量的是「看板值與 record 是否相符」。**看板不相符不只是資訊過時——它是 [US:S-3] 所防的「看板說謊」。**

而 `scalability-requirements.md` 記載的 R-3.4 交界（批次上限被觸發時一致率**偏高**）在此有安全意涵：**偏高的比率會讓人以為看板可信，而實際上有一部分從未被檢查過。**

**這是「指標本身失真」的風險，比「指標顯示有問題」嚴重**——後者會引來注意，前者會消除注意。

## SEC-4：`workflow_dispatch` 的觸發權限

本單元同時支援 cron 與 `workflow_dispatch`（手動觸發，[US:S-7] 的可展示性需要它）。

**`workflow_dispatch` 的觸發權限由 repo 的 Actions 設定決定，不由本 workflow 控制。** 有寫入權的人都能手動觸發一輪對帳。

**嚴重度：低。** 對帳是**冪等且只做補平**的操作——手動多跑幾輪的後果是多幾次 API 呼叫，不會產生錯誤狀態。**與 U-4 的 SEC-2（`[aidlc-sync]` 可被任何人觸發）同族，同樣是「有推送權即有此能力」，同樣記載不修。**

## 與上游的對應

四面向依據為 `requirements.md` 的 NFR-S1／S4～S6 與 `project.md` 的 ADR-0006 落點，權限集合依 **ADR-0014**；[req:NFR-O2]／[FR-D4] 引自 `requirements.md`；[US:S-3]／[US:S-7]／[US:S-9] 引自 `stories.md`；U-3 的 SEC-4、U-5 的 SEC-2、U-4 的 SEC-2 引自各自的 `security-requirements.md`；報告落點的裁定與其限制見同輪的 `tech-stack-decisions.md`（缺口 M-1），R-3.4 的交界見 `scalability-requirements.md` 與 `business-rules.md`，清單定義見 `domain-entities.md`，序列見 `business-logic-model.md`；S-B 的生命週期引自 [ad:services.md]，`reconcile` 的契約引自 [ad:component-methods.md]；單元邊界引自 [ug:unit-of-work.md] 的 U-7。
