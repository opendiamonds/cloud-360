# Team Allocation — Bolt 對 mob 的指派

## 團隊來源

**`team-formation`（1.5）未執行**。本 intent 的 ideation 只跑了 intent-capture、feasibility、scope-definition、approval-handoff 四站（`<record>/ideation/` 目錄實測），沒有 team-formation 的產出可引用。

依 delivery-planning stage 檔的規定，1.5 為 SKIP 時**全部 Bolt 由 `aidlc-developer-agent`（AI）執行**。本檔因此不是 Program Board——團隊數為 1，沒有跨團隊的介面要協調。

## 指派

| Bolt | 單元 | 執行者 | 人工介入點 |
| --- | --- | --- | --- |
| Bolt 0（關卡） | 無 | **人**（需組織管理權限） | 全部五項——見 `external-dependency-map.md` |
| Bolt 1 | U-1～U-6、U-10a | `aidlc-developer-agent` | Bolt gate 一次 |
| Bolt 2 | U-7 | `aidlc-developer-agent` | Bolt gate 一次；G-1 修補是否被 skip 需確認 |
| Bolt 3 | U-8、U-10b | `aidlc-developer-agent` | Bolt gate 一次 |
| Bolt 4 | U-9 | `aidlc-developer-agent` | Bolt gate 一次；PRE-1-a 結論若為否，需回 user-stories |
| Bolt 5 | U-11 | `aidlc-developer-agent` | Bolt gate 一次 |

**Bolt 0 是唯一不由 AI 執行的項目**：~~它的五項實測中，組織層 App 安裝與 Repository Rulesets 設定需要組織管理權限，agent 沒有也不應該有。~~ 這一點在 `external-dependency-map.md` 有 owner 與 lead time。

> **經 ADR-0016 §1／§7 更正**（2026-08-31T00:37:44Z）：①本表現為**七項**（增 PRE-1-b、PRE-1-c，見 `bolt-plan.md` 的 PRE-1 表）；②「組織層 App 安裝」**不適用**——無組織、無 App，憑證改由擁有者本人鑄造；③「Repository Rulesets 設定」**經 PRE-1-a 實測為不可行**（`422 Source public repos cannot have push rules` ＋ `Source only org-owned repos can have push rules`），不是權限不足而是功能不適用於本 repo。
>
> **本項的判斷結論不變**（Bolt 0 仍不由 AI 執行），但**理由改變**：不再是「agent 沒有組織管理權限」，而是**鑄造憑證與建立測試看板需要帳號持有者本人在 GitHub 網頁操作**。這個區別要緊——原理由若成立，把 agent 加進組織即可解決；實際理由不能靠授權解決。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`

## Construction 的設計階段迭代方式

依 [Q5=B] 採 **`unit-major`**：一個單元的四份設計文件（functional-design、nfr-requirements、nfr-design、infrastructure-design）連續寫完，再進下一個單元。

**理由**：12 個單元中 5 個是 `library`（純函式，無獨立執行期）、4 個是 `service`（workflow 執行期行為）、2 個是 `packaging`（既有檔案的觸發設定調整）、1 個依設計未分類（U-11，[ug:unit-of-work.md] 明記五類皆不合）。「這個單元需要哪些設計文件」的答案在這些 `kind` 之間差異很大——`kind` 標註本來就是為此而設。逐單元寫時，寫 U-3 的 NFR 時它的 functional design 剛寫完還在手邊。

**已知代價**（[Q5=B] 選項本文即已載明，不是事後才發現）：四個 per-stage gate 仍然存在，但會**延後並在設計區塊末端連續觸發**——一次 stage 一次人工核可，四次擠在一起。

執行方式：`bun .claude/tools/aidlc-state.ts set-construction-iteration unit-major`（本站 Step 7 執行）。
