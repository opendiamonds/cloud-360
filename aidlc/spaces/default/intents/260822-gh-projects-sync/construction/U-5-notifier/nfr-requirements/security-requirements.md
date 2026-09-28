# Security Requirements — U-5 通報

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-5-notifier · kind: library -->

## 缺口 K-1（**優先級最高**）：NFR-S1 的權限集合漏了 Issues 寫入

> **狀態：已由 ADR-0014 收斂（2026-08-29），其後由 ADR-0015 §8 再度更正（2026-08-30T05:10:02Z）。** ADR-0014 把權限集合更正為三項，PRE-1 第 1 項的實測範圍擴充為「三項各至少一次真實呼叫，必須包含一次開 issue」，`stories.md` 的 PRE-1 與 `bolt-plan.md` 的 Bolt 0 表已實質更新。
>
> **現行集合為四項**：ADR-0015 §8 指出開 PR 與推分支是兩個獨立權限，第四項為 `Pull requests: write`。**本檔下方第 42 行的「須同步改為三項」亦應讀作四項。** 更正指令與閘門（Bolt 0，須在憑證鑄造前）見 `../../../inception/decisions/0015-functional-design-upstream-amendments.md` §8。此為 `open-items.md` 的 B:M-5。
>
> **但 `requirements.md` 的 NFR-S1 只有「需求」欄補了指標，「驗收判準」欄仍逐字寫著「等於上述**兩項**，無額外授予」，且其指標指向的是一個不相干的較早更正（R-1），不是 ADR-0014**（reviewer iteration 1 Major，2026-08-29T15:26:25Z 更正本檔先前「皆已加上指標」的過度宣稱）。
>
> **這不是文字瑕疵**：ADR-0014 自己的 Alternatives 段明文指出「驗收準則的『無額外授予』**會主動阻止正確的憑證**」——一個照著該判準鑄憑證的人，會鑄出一個缺 Issues 寫入權的憑證，而它會通過 PRE-1。
>
> **指派**：`requirements.md` 的 NFR-S1 驗收判準欄補上指向 ADR-0014 的指標（比照 `stories.md` 的 PRE-1 已做的實質改寫）。**本項已由 ADR-0015 §8 承載**（送審前自檢遷移，2026-08-29T23:42:35Z；`requirements-analysis` 已定稿，單元產出內的指派無收件人——理由見 ADR-0015 的 Context 段）。**確認人維持 Bolt 0 的 gate**——它必須在鑄憑證之前生效。**本節以下維持原文**，它是缺口被發現時的記載與論證，不因收斂而改寫。

`requirements.md` 的 NFR-S1 逐字宣告機制所需權限為 **「組織層 Projects 讀寫 ＋ repo 內容寫入」**，並把驗收準則寫成：

> 憑證實際被授予的權限集合**等於上述兩項，無額外授予**。

**但 GitHub App 的 `Issues` 是獨立於 `Contents` 與 `Projects` 的第三種權限**，而本設計至少四處需要它：

| 需要 Issues 寫入的地方 | 出處 |
| --- | --- |
| 回讀不符時**開 issue** | `requirements.md` FR-C1 |
| 同步失敗時**自動開 issue** | FR-E1 |
| 本單元的全部行為（開 issue、追加 comment、**關閉** issue） | [ad:component-methods.md] §C-5、ADR-A8 |
| U-3 的 `read_issue_state`（[US:S-9 AC 5] 的 issue 開關偵測） | [ad:component-methods.md] §C-3 |

此外 [US:S-1 AC 1] 要求「Project #16 出現一則對應的 **issue**」——看板 item 的載體本身就是 issue。

**後果的嚴重度**：NFR-S1 的驗收準則若被逐字執行（「等於上述兩項，無額外授予」），鑄出的憑證**不會有 Issues 寫入權**，於是：

- 本單元（U-5）的每一次呼叫都失敗 → 而 [ad:component-methods.md] 明定「通報本身失敗 → **拋**」→ workflow 紅燈。
- FR-C1 與 FR-E1 的「開 issue」全部失敗。
- **失敗會在 Bolt 1 的第一次真實執行時才浮現**，而那時 PRE-1 已經簽過。

**與 PRE-1 的關係（這是本缺口最要緊的一點）**：PRE-1 第 1 項是「憑證確實帶組織層看板寫入權——**以最小可行呼叫實測**」。若那次實測只呼叫 Projects 的 mutation，它會**通過**——然後整個機制在 Bolt 1 才發現開不了 issue。

**落點與確認人**：

| 項目 | 內容 |
| --- | --- |
| **修訂落點** | `requirements.md` 的 **NFR-S1**——權限集合須補入 `Issues: write`，驗收準則的「等於上述兩項」須同步改為三項 |
| **確認人與時機** | **Bolt 0（PRE-1）執行前**。PRE-1 第 1 項的實測**必須同時涵蓋開 issue 與寫 Projects 欄位**，否則該項通過不代表憑證可用 |
| **本站不逕自改上游** | requirements-analysis 已執行完畢，本站只登記待修訂（與 F-3 同形）；但**急迫性高於 F-3**——F-3 影響一條 AC 的措辭，本項影響憑證能不能用 |

> **這也讓 U-3 的 SEC-2 更完整**：那裡記載「本單元拿到的權限大於它需要的」，而本項顯示**另一個方向也成立**——宣告的集合同時**過大**（每個單元只用一部分）**與過小**（漏了 Issues）。兩者不矛盾：前者是「沒有機制限制各單元只用自己那一半」，後者是「宣告本身不完整」。

## ADR-0006 四面向逐項判定

| 面向 | 判定 | 內容 |
| --- | --- | --- |
| **IAM** | **完全適用** | 見 K-1 與 SEC-1 |
| **Encryption** | 適用（平台承擔） | HTTPS；本單元不儲存憑證、不落地機敏檔案 |
| **Network exposure** | 不適用 | 只有對 GitHub API 的出站呼叫 |
| **Audit logging** | **完全適用** | 通報 issue **就是**面向人的稽核紀錄；FR-E3 的三要素（intent 識別字、stage 標識、ISO 8601 時間戳）由本單元寫入 |

## SEC-1：本單元會**關閉**別人看得到的 issue

`business-rules.md` 的 R-2 第 4 步（關閉重複的同鍵 issue）與 R-3 第 3 步（失敗不再發生時關閉）是本單元的兩個**破壞性動作**。

**約束（已在 `business-rules.md` R-2.1 定案，此處記其安全理由）**：關閉條件必須是**內文首行機器可讀鍵逐字相符**，不得以標題比對。標題可被任何有 issue 權限的人編輯——若以標題比對，一個把自己的 issue 標題改成通報格式的人（或一次無意的複製貼上）就會讓機制關掉不該關的 issue。

**這與 U-4 的 SEC-2（`[aidlc-sync]` 標記可被任何人觸發）是同一族的問題**，但**嚴重度不同**：U-4 那個的後果是「跳過一輪」（有結構性防線兜底），本項的後果是「關掉別人的 issue」（**不可自動復原**——重開的是新 issue，原本的討論串斷了）。因此本項的防護不是可選的。

## SEC-2：通報內容會出現在公開 issue 上

本 repo 為 public，通報 issue 公開可讀。

**約束**：`notify` 的 `detail` 參數**不得**包含完整的 API 回應 body 或任何標頭。這與 U-3 的 SEC-4 是同一條規則的兩端——U-3 負責不把敏感內容放進 `message`，本單元負責不把收到的東西原樣貼上 issue。

**兩邊都要守**：只守一邊時，另一邊仍會洩漏。

## 與上游的對應

NFR-S1～S6 與 ADR-0006 落點引自 `requirements.md` 與 `project.md`；FR-C1／FR-E1／FR-E3 引自 `requirements.md`；C-5 的方法契約與「不可遞迴通報」引自 [ad:component-methods.md]，收斂演算法引自 [ad:decisions.md] ADR-A8；[US:S-1 AC 1]／[US:S-9 AC 5] 引自 `stories.md`；PRE-1 的實測清單引自 `stories.md` 的 PRE-1 節；單元邊界引自 [ug:unit-of-work.md] 的 U-5，AC 歸屬引自 [ug:unit-of-work-story-map.md]；本單元的規則見 `business-rules.md`、issue 形狀見 `domain-entities.md`、資料流見 `business-logic-model.md`；紅燈語意引自 [ad:services.md]；元件分層引自 [ad:components.md]。
