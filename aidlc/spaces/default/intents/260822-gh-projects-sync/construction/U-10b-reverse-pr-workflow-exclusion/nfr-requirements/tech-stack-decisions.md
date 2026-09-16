# Tech Stack Decisions — U-10b 反向 PR 的高成本 workflow 排除

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-10b-reverse-pr-workflow-exclusion · kind: packaging -->

## 實測的既有觸發設定（本站查證，非引用）

對 `.github/workflows/*.md` 逐檔解析 `on:` 區塊，**六支** gh-aw workflow 吃 `pull_request`：

| workflow | `pull_request` 過濾 | 反向 PR 會觸發嗎 |
| --- | --- | --- |
| `ui-regression` | `types` only，**無 paths** | **會** |
| `pr-reviewer` | `types` only，**無 paths** | **會** |
| `lint-fix` | `types` only，**無 paths** | **會** |
| `contract-guard` | `types` only，**無 paths** | **會** |
| `code-drift-alert` | `paths:` allowlist（`backend/main.py`、`backend/services/**`…） | 否——已被 allowlist 自我排除 |
| `local-dev-drift` | `paths:` allowlist（`backend/database.py`、`deploy/nginx.conf`…） | 否——同上 |

加上 `ci.yml`（`on: pull_request` 無任何過濾，四個 job），**一則反向 PR 會發動五組 workflow**。

## 決定：`paths-ignore`，與 U-10a 同一個機制、同一條 glob

**對上表前四支加 `paths-ignore`，涵蓋 `<record>/sync-state.json` 的 glob。** `ci.yml` 那一份由 U-10a 負責（同一條 glob，不同檔），本單元不重複。

**選它的理由是排除法，不是偏好：**

- **label 機制不存在於觸發層。** 單元定義寫「或等價的 label 機制」，但 GitHub Actions 的 `on:` 只有 `branches-ignore`／`paths-ignore`／`tags-ignore`——**沒有 `labels-ignore`**（本站查證）。label 只能做到 job 層的 `if:`，那仍會配一台 runner 並跑完 checkout 之前的所有事，對一個自述燒過近七小時的 workflow 而言，省的不是要省的那一段。
- **`branches-ignore` 是否可用，取決於一個本站無法在 repo 內複驗的語意。** 對 `pull_request` 事件，`branches`／`branches-ignore` 過濾的是 **base** 而非 head——若此說成立，反向 PR 的 base 是 `ut`（與所有其他 PR 相同），用它會把**全部 PR** 一起排除掉。本站在本 repo 的 workflow 與 `.lock.yml` 中找不到可據以複驗的設定，**故不把此說當成已證實**。

## 與 U-6 的 D-1 裁定不一致，須明記

U-6 的 `functional-design-questions.md` D-1 在選擇「分支名前綴 ＋ label 並用」時，把 **U-10b 的排除**列為分支名前綴那一欄的優點，逐字寫「✅ `branches-ignore` 讓 run **根本不被建立**（同 U-10a 的 `paths-ignore`）」。

**本單元不採用 `branches-ignore`。** 這與 D-1 的**理由**相左，但與它的**裁定**不相左：

| D-1 的內容 | 本單元 |
| --- | --- |
| 裁定：分支前綴 `aidlc-sync/reverse/*` ＋ label `aidlc-sync-reverse` | **不改**。兩個標記照舊產生 |
| 理由之一：分支前綴使 `branches-ignore` 可用於 U-10b | **不依賴它**。改用 `paths-ignore` |
| 理由之二：GitHub 沒有 `labels-ignore`，label 只能做 job 層 `if:` | **同意且複驗過**——本站獨立查證得到同一結論 |

**選 `paths-ignore` 的決定性理由是它在兩種讀法下都正確**：無論 `branches-ignore` 過濾的是 base 還是 head，`paths-ignore` 都會因「變更檔案全部命中 glob」而跳過。加上 U-10a 已為 `ci.yml` 加同一條 glob，本單元等於沿用一個已被採納的機制而非另闢一條。

**D-1 的分支前綴仍有獨立價值**（人一眼分辨、`git branch` glob、push 事件上的 `branches-ignore` 確實過濾 head），**故本站不建議撤除它**，只是不把 U-10b 的成立押在它上面。

**指派**：`pull_request` 的 `branches-ignore` 究竟過濾 base 還是 head，**列為 PRE-1（Bolt 0）的實測項**——與缺口 P-1 的憑證實測同一個閘門、同一則測試 PR 即可觀察。結果不影響本單元的機制選擇，但會決定 D-1 那一列理由是否需要更正。

## 這個機制成立的唯一前提，以及它的失敗模式

`paths-ignore` 的語意是：**變更的檔案「全部」命中 ignore pattern 時才跳過**。命中率不是多數決——多一個沒命中的檔，整條排除就失效。

反向 PR 只改一個檔，這**不是巧合而是 E-1 的直接後果**：U-8 的 `business-logic-model.md` 把 [req:FR-G2] 的「同步專用檔案」定為 `sync-state.json` 的 `pending_reverse` 欄位，於是該 PR 的 diff 結構上只可能含那一個檔。

**若哪天有人為反向 PR 多加一個檔，本單元的排除會靜默失效**——沒有錯誤、沒有紅燈，只是那五組 workflow 又開始跑。**這是本單元最需要被寫進實作註解的一句話**，因為它的成因在另一個單元（U-8）而後果在這裡。

## 完成判準要不要擴大

單元定義的完成判準逐字為「反向 PR 開啟後，`ui-regression` 未對其執行」，只點名一支。但上表顯示會被觸發的是四支（本單元範圍內）。

**本站裁定：完成判準擴大為四支皆未執行**（未經人工提問）。理由：`ui-regression` 是成本最大的一支（`ui-regression.md` 的註解逐字記載 PR #510 上「~7 hours of runner time on one PR for zero tests executed」），但 `pr-reviewer`／`lint-fix`／`contract-guard` 的 `engine` 皆為 `copilot`——它們是 **LLM 路徑**，會對一個機器產生的單檔 PR 產出 AI 審查留言並消耗額度。只擋最貴的一支而放行其餘三支，達不到 [US:S-6 AC 7] 的意圖。

## 本單元沒有自己的 `business-rules`，責任由 U-8 明確交出

U-10b 的 `kind` 是 `packaging`，functional-design 的 produces 不涵蓋這一類，所以它**沒有自己的 `business-rules.md`**。責任的交界寫在消費端：

- **U-8 的 `business-rules.md` R-5** 逐字把「高成本 workflow 的排除」判為**不屬於 U-8**，指向本單元。這是本單元存在的直接依據——沒有它，「反向 PR 開了之後誰負責讓 gauntlet 不跑」會是無主的。
- **同檔 R-4b** 的 AC 分散對照表把 [US:S-6] 的七條 AC 拆給三個單元，其中 **AC 7 歸 U-10b**，AC 1–5 歸 U-8、AC 6 歸 U-2。**本單元完成不等於 S-6 完成，反之亦然**——這也是為什麼本單元的完成判準必須自己說清楚（見 `tech-stack-decisions.md`），不能靠故事層的驗收帶過。

## 與上游的對應

[US:S-6 AC 7]、單元的擁有範圍、交付物、完成判準與 `ui-regression` 的成本註記引自 [ug:unit-of-work.md] 的 U-10b；NFR-C1（既有 CI 四道關卡不得被破壞）與 FR-G1／FR-G2 引自 `requirements.md`；反向 PR 只動一個檔的結構性保證與 E-1 的裁定引自 U-8 的 `business-logic-model.md`；U-10a 的同機制同 glob 引自該單元的 `tech-stack-decisions.md`；`ci.yml` 與 11 組 gh-aw 的既有盤點引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）；六支 workflow 的 `on:` 區塊為本站逐檔實測；本單元與 U-8 的責任交界（R-5）與 S-6 的 AC 分散對照（R-4b）引自 U-8 的 `business-rules.md`。
