# Security Requirements — U-4 record 回寫與同步狀態

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-4-binding-store · kind: library -->

> **本單元是機制唯一寫回 repo 的地方。** U-3 持有憑證的 Projects 那一半，本單元用的是**repo 內容寫入**那一半。

## ADR-0006 security baseline 的四面向逐項判定

| 面向 | 判定 | 內容 |
| --- | --- | --- |
| **IAM** | **完全適用** | 見 SEC-1、SEC-2 |
| **Encryption** | **適用（由平台承擔）** | git over HTTPS；本單元不儲存憑證、不落地機敏檔案（NFR-S4） |
| **Network exposure** | **不適用** | 只有對 GitHub 的出站 push（NFR-S5） |
| **Audit logging** | **完全適用，且本單元就是稽核紀錄的產生點** | 見 SEC-3 |

## SEC-1：`paths` 白名單是介面約束，不是權限約束

`business-rules.md` 的 R-3.2 規定 `paths` 限 record 目錄下的綁定編號與 `sync-state.json`。但憑證擁有的是**整個 repo 的內容寫入權**——白名單擋的是本元件的正確實作，不是憑證的能力。

這與 U-3 的 SEC-2 是**同一個結構性事實的另一面**：NFR-S1 定義的權限集合（**ADR-0014 更正後為三項**：組織層 Projects 讀寫 ＋ repo 內容寫入 ＋ Issues 寫入）是**一份憑證**，而各單元各用其中一部分、各自沒有機制限制自己只用那一部分。U-5 另需 Issues 那一份。

> **權限集合現為四項（ADR-0015 §8）**：ADR-0014 補入的是第三項 Issues 寫入，而 §8 進一步指出**開 PR 與推分支在 GitHub 權限模型中是兩個獨立權限**，第四項為 `Pull requests: write`（佐證：`deploy.yml:174-175` 在本 repo 上正在運行的設定即分列兩行）。本檔沿用的是 NFR-S1 當時的三項計數，更正指令與閘門（Bolt 0，須在憑證鑄造前）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。指標補於 2026-08-30T01:31:09Z。

具體後果：一個把 `paths` 寫錯（或忘記過濾）的實作**不會被權限擋下**。[US:S-10 AC 5] 的第二個例子（改 record 目錄以外的檔案應回 403）在本設計下**無機制可產生 403**，候選機制 Repository Rulesets 的 file-path restriction 已列 **PRE-1-a**。

**PRE-1-a 若判定可行，它保護的正是本單元**——那是全機制中唯一會寫 repo 內容的地方。這一點值得在 PRE-1-a 的實測記錄中寫明，因為它決定了該項的優先級。

## SEC-2：`[aidlc-sync]` 標記可被任何有推送權的人觸發

[req:FR-A4] 的自我排除依賴 commit 訊息含 `[aidlc-sync]`，而 [ad:services.md] 的防線②是「workflow 層在 HEAD commit 訊息含該標記時**整輪 skip**」。

**任何有推送權的人都能讓一輪同步整個跳過**——只要在自己的 commit 訊息裡放這個字串。可能是刻意，也可能是把同步的 commit 訊息複製貼上時無意造成。

**嚴重度判定：低，但必須記載。**

- 推送權本身已蘊含相當程度的信任，這不是權限提升。
- [ad:services.md] 的防線①（**結構性**：回寫後 `sync-state.json` 與看板一致 ⇒ 下一輪判定無漂移）**不依賴任何判斷**，因此正確性不受影響。
- 實際後果是**該輪不處理**，下一次事件或隔日對帳會自然補上——[ad:services.md] 已把這個延遲記為防線②的已知代價（reviewer iteration 3 Minor）。

**不建議為此加防護**：要區分「同步身分寫的」與「人寫的但訊息剛好含該標記」需要同時比對身分，而那會讓防線②從一個字串比對變成一個身分判定，複雜度上升而收益是防一個低嚴重度、且有結構性防線兜底的情形。**記載它，不修它。**

## SEC-3：commit 歷史是稽核紀錄，`[aidlc-sync]` 是它的索引

NFR-S6 要求每次 Status 變更可回答「哪個 intent、哪個 stage、什麼時間」。本單元產生的 commit 同時滿足三者：路徑含 intent id、內容含 stage 資訊、commit 時間即時刻。

**`[aidlc-sync]` 標記的第二個用途**（除了自我排除）是讓這些 commit 在歷史中**可被機械篩選**——`git log --grep='\[aidlc-sync\]'` 即得完整的機器寫入紀錄。這一點沒有被上游明寫，但它是本標記的實際價值之一，值得記下以免未來有人改標記格式時只考慮自我排除那一面。

**連帶約束**：commit 訊息**不得**包含 Status 之外的 record 內容摘要。訊息的用途是標記與追溯，不是資料傾印；record 的實際內容已在 diff 中。

## SEC-4：`git config` 身分不得沿用 runner 預設

見 `tech-stack-decisions.md`：本單元須明確設定同步身分。**若沿用 runner 預設，[US:S-1 AC 5] 的「由同步身分推送」那一半無從判定**——這不只是稽核問題，它會讓 FR-A4 的防線②失去一個判定依據。

## 與上游的對應

四面向依據為 `requirements.md` 的 NFR-S1／S4／S5／S6 與 `project.md` 的 ADR-0006 落點；`paths` 白名單與 `[aidlc-sync]` 要求引自 [ad:component-methods.md] §C-4；防線①②與其代價引自 [ad:services.md] 的 S-A；403 半邊缺口與 PRE-1-a 引自 [ad:decisions.md] ADR-A2；FR-A3／FR-A4 引自 `requirements.md`；[US:S-1 AC 5]／[US:S-10 AC 5] 引自 `stories.md`；單元邊界與驗證方式引自 [ug:unit-of-work.md] 的 U-4，AC 歸屬引自 [ug:unit-of-work-story-map.md]；本單元的規則見 `business-rules.md`、schema 見 `domain-entities.md`、資料流見 `business-logic-model.md`；元件分層引自 [ad:components.md]。
