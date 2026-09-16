# Tech Stack Decisions — U-7 對帳 workflow 與編排器

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-7-reconcile-workflow · kind: service -->

## 決定

**`.github/workflows/aidlc-sync-reconcile.yml`（cron 觸發 ＋ `workflow_dispatch`）＋ 其 `*-impl.yml`（`on: workflow_call`）**，純 Actions、`shell: bash`，編排與 U-6 相同的五支 composite action。

## 缺口 M-1：對帳報告**發布在哪裡**未定義

[req:FR-D4] 要求「每次對帳產出一個**可讀取的數值**」，[ad:services.md] S-B 的產出欄只寫 `ReconcileReport`（**型別**）。**沒有任何上游 artifact 說它發布到哪裡讓人讀。**

四個候選各有實質差異：

| 落點 | 可讀性 | 保留期 | 公開？ |
| --- | --- | --- | --- |
| workflow log | 差（要點進 run） | 90 天（GitHub 預設） | 是（public repo） |
| **job summary**（`$GITHUB_STEP_SUMMARY`） | **好**（run 頁面直接顯示，支援 markdown 表格） | 同 run | 是 |
| 每日開／更新一則 issue | 好，且可訂閱 | 永久 | 是 |
| commit 進 repo 的檔案 | 好，可 diff 追蹤趨勢 | 永久 | 是 |

**本站裁定：job summary 為主，workflow log 為輔。** 理由：

1. **零新增狀態**——與 ADR-A8 的「記憶就是 GitHub 本身」同精神，不新增 issue、不新增檔案。
2. 開每日 issue 會與 U-5 的通報 issue 混在同一個列表，**稀釋通報的訊號**（U-5 的整個設計就是為了「叫了要有人看」）。
3. commit 進 repo 會每天產生一個 commit，**放大 [US:S-1 AC 7] 的 CI 觸發問題**，且需要擴大 U-10a 的 `paths-ignore`——那正是 `security-requirements.md` SEC-1 警告的方向。

**但趨勢追蹤因此不可得**：job summary 只存在於單次 run。**若 P4 需要看一致率的長期走勢，本裁定不夠**，屆時的落點是第四項（commit 進 repo）＋ 相應的 `paths-ignore` 擴大。**記明此限制，不假裝已解決。**

> 本項為**本站裁定**（未經人工提問），理由完整記載以便覆核。

## cron 時段必須避開的既有排程（[kb:technology-stack.md] 的盤點）

codekb 盤點本 repo 有 **11 支 gh-aw workflow**，其中三支為排程觸發，本單元的 cron 必須避開：

| workflow | cron | 為什麼會撞 |
| --- | --- | --- |
| `daily-digest` | `0 23 * * 1-5` | 同為每日排程 |
| `agentics-maintenance` | `37 0 * * *` | 每日 |
| `release-watch` | `39 16 * * 1` | 每週一 |

**碰撞的後果不是失敗，是資源競爭**：三者皆為 gh-aw（`engine: copilot`，含 LLM agent step），與本單元同時起跑會拉長彼此的 runner 排隊。[kb:technology-stack.md] 亦記載 `ui-regression` 曾在單一 PR 燒掉約 6 小時 runner 時間——**這個 repo 的 runner 用量不是可以忽略的變數。**

> 這一項在 `stories.md` 的全域 DoD 中被分類為**建置期檢查**（cron 是時間點不是時段，且「檢視設定」不是系統行為）。本站不改變該分類，只補上碰撞的實際成因。

## 工具

沿用既有形狀：`gh api graphql`（U-3 的 board client）、`gh issue`（U-5）、`jq`（U-4）。**本單元不引入任何新工具。**

`$GITHUB_STEP_SUMMARY` 是 GitHub Actions 內建，寫入即為 markdown 渲染，零依賴。

## 承接 bash 的既有代價

本單元是編排層，資料處理都在被呼叫的 action 內。唯一新增的是**報告的組裝**——把六份清單與兩個數字組成 markdown 表格。以 `jq` 與 `printf` 即可，**但須注意清單為空時的輸出**：空陣列應渲染為「（無）」而非空白列，否則報告會出現看不出是「沒有」還是「壞了」的空格。

## 與上游的對應

S-B 的觸發與產出引自 [ad:services.md]；`reconcile` 的契約引自 [ad:component-methods.md] §C-7；ADR-A10 的兩檔拆分與 ADR-A8 的零新增狀態引自 [ad:decisions.md]；[req:FR-D4]／[US:S-1 AC 7] 引自 `requirements.md` 與 `stories.md`；五支 action 的承載形式引自 U-1～U-5 的 `tech-stack-decisions.md`；`paths-ignore` 的窄化約束引自 U-10a 的 `security-requirements.md` SEC-1；六份清單見本單元的 `domain-entities.md`，規則見 `business-rules.md`，序列見 `business-logic-model.md`；單元交付引自 [ug:unit-of-work.md] 的 U-7。
