# External Dependency Map — 受外部阻擋的項目

## 判定範圍

「外部相依」指**本團隊無法自行完成、需要他人或他系統先動作**的項目。純粹的技術未知（例如 `createProjectV2Field` 能不能用）不算外部相依，那是實測；但**需要組織管理權限才能做的設定**算。

依 [ad:decisions.md] 的 CAP-11 補評估與 `requirements.md` 的假設清單逐項判定，本 intent 有四項外部相依，全部集中在 Bolt 0。

## 受阻項目

| # | 項目 | Owner | Lead time | 阻擋 | 若被拒的替代路徑 |
| --- | --- | --- | --- | --- | --- |
| E-1 | ~~**組織層安裝 GitHub App 並鑄出帶 Projects 寫入權的憑證**~~ **鑄出帶個人帳號 Projects v2 寫入權的憑證** | ~~組織管理者（非本團隊）~~ **repo／project 的擁有者本人（本團隊內）** | ~~未知~~ **已確認可行**（PRE-1 第四、五輪實測：`opendiamonds` token 帶 `project` scope，對 #16 `viewerCanUpdate: true`，並已實測建欄位、寫值、contents 寫入） | **全部 Bolt**。沒有憑證就沒有任何寫入路徑 | ~~無。這是本 intent 的存在前提；被拒則整個 intent 需回 approval-handoff 重新評估~~ **本項不再是外部依賴** |

> **經 ADR-0016 §1 更正**（2026-08-31T00:37:44Z）——**E-1 的外部性已消失，這是本輪對本檔最實質的改變**：`opendiamonds` 是個人帳號（實測 `GET /orgs/opendiamonds` → 404），**沒有組織管理者這個角色存在**，憑證由擁有者本人鑄造。原欄「被拒則整個 intent 需回 approval-handoff 重新評估」所描述的情境**結構上不可能發生**——沒有第三方可以拒絕。
>
> **仍然成立的部分**：Bolt 0 依舊需要人工動手（鑄憑證、建測試看板），只是那個人是團隊成員而非外部管理者；`project.md ## Mandated` 的「新增憑證型 secret 後須實地查證它落在 secrets 而非 variables」照常適用。
>
> **反向新增的依賴**：**PRE-1-c**（ADR-0016 §7）需要鑄一顆 `public_repo` ＋ `project` 的 classic PAT，同樣由擁有者本人執行，非外部依賴。見 `../decisions/0016-credential-topology-and-pre1-amendments.md`
| E-2 | **Project #16 存在且欄位結構可寫** | 看板擁有者 | 短（設定操作） | Bolt 1 | 若 `createProjectV2Field` 不可用（PRE-1 第 3 項），[US:S-5 AC 2] 走「開 issue 請人手動建立」那一支——AC 已寫成窮盡二分，兩支都可接受 |
| E-3 | **Repository Rulesets 的 file-path restriction 設定** | 組織／repo 管理者 | 短，但**適用性未知**（PRE-1-a） | Bolt 4 | 不適用時 [US:S-10 AC 5] 的第二個例子無機制可產生 403，該 AC 需回 user-stories 改寫。**不得**在 Bolt 4 直接標記通過 |
| E-4 | **分支保護對同步身分的實際行為** | repo 管理者 | 短 | Bolt 1 | `requirements.md` A-8 明記「同步身分對 feature 分支有寫入權且不受分支保護阻擋」**未驗證**。若受阻，回寫失敗 ⇒ 下次 push 又看不到綁定 ⇒ 每 push 一次多一張卡（[US:S-1 AC 6] 正是為此而設） |

## 不算外部相依的項目

以下三項曾被考慮但判定為**本團隊可自行完成**，列出以免下游誤判：

- **框架單次操作上限（C-T5）的實際值**（PRE-1 第 2 項）——實測即可得，不需他人動作。
- **`.md` ↔ `.lock.yml` 編譯漂移的收斂手段**——[req:OQ-4] 已指派 ci-pipeline，屬本專案內部工作。
- **既有三支 `scripts/aidlc_sync_*.py` 的遷移**——[req:OQ-7] 使用者已裁決為「遷移到 gh-aw／Actions」，但 [ug:unit-of-work.md] 明記那是**本 intent 之外**的工作，需另立 intent。不在本計畫的任何 Bolt 內。

## 排程層面的外部約束

對帳 workflow（Bolt 2）的 cron 時段不得與既有三支排程碰撞：`daily-digest`（`0 23 * * 1-5`）、`agentics-maintenance`（`37 0 * * *`）、`release-watch`（`39 16 * * 1`）。這不是「受他人阻擋」，但它是一個本團隊必須讓開的既有事實，`stories.md` 全域 DoD 已列為完成條件。
