# Security Requirements — U-10b 反向 PR 的高成本 workflow 排除

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-10b-reverse-pr-workflow-exclusion · kind: packaging -->

## SEC-1：本單元**縮小的是既有安全閘門的觸發覆蓋範圍**

`paths-ignore` 不是「對反向 PR 關閉」，它是**對任何 diff 全部落在該 glob 內的 PR 關閉**——包含人手動開的。

被縮小覆蓋的四支中，`contract-guard` 是實質的安全相關閘門（它驗 repo contract，而 contract 涵蓋禁止路徑與禁止內容的掃描）。

| 問 | 答 |
| --- | --- |
| 只改 `sync-state.json` 的 PR 能繞過 contract 檢查嗎？ | **在 PR 階段是的** |
| 那 contract 就沒被驗了嗎？ | **不是。** `ci.yml` 的 `repo-contract` job 在 `push` 到 `main`／`ut` 時仍會跑（U-10a 的 `paths-ignore` 同樣不阻止合併後的 push 觸發），且 `validate_repo_contract.py` 的禁止路徑檢查已於 issue #509 改為 `git ls-files` **全域掃描**——它不看 diff，任何已納入版控的違規路徑都會紅燈 |
| 殘餘風險 | 違規內容從進入 PR 到被 `ut` 上的 push 觸發抓到之間有一個視窗。**這個視窗本來就存在於任何 `paths-ignore`**，不是本單元新增的性質 |

**這一項須在實作 PR 中明寫**，否則下一個看到 `contract-guard` 被加了 `paths-ignore` 的人會合理地認為那是誤加。

## SEC-2：`ui-regression` 是真閘門，被排除的後果須說清楚

`team.md` 記載 `ui-regression` 的 `post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1`——**它不是提醒型 workflow**。

反向 PR 被排除後，它合併進 `ut` 時未經任何 UI 回歸驗證。**這是可接受的**，理由不是「風險低」而是「相關性為零」：反向 PR 的 diff 只含一個 JSON 檔的欄位，該檔不被前端讀取、不進 build、不影響任何 UI。

**但這個理由的有效性完全依賴前一句的「只含一個 JSON 檔」**，也就是 `tech-stack-decisions.md` 記載的 E-1 前提。前提破了，這裡的可接受性也一起破，而**兩者都不會發出任何訊號**。

## ADR-0006 四面向判定

| 面向 | 判定 |
| --- | --- |
| IAM | **不適用**。本單元不觸及任何憑證或權限；修改的是 workflow 的 `on:` 區塊 |
| Encryption | **不適用**。不處理資料 |
| Network exposure | **不適用**。不新增服務或端點 |
| Audit logging | **適用且已處置**：被排除的 workflow 在 GitHub 的 Actions 頁面上會顯示為「未觸發」而非「跳過」，兩者在 UI 上不易分辨。實作時應在被修改的 workflow 的 `paths-ignore` 旁加註解逐字說明**為何**排除、以及**哪個單元**是它的來源（U-8 的反向 PR），讓後續讀者不必回溯這份文件 |

## 本單元沒有自己的 `business-rules`，責任由 U-8 明確交出

U-10b 的 `kind` 是 `packaging`，functional-design 的 produces 不涵蓋這一類，所以它**沒有自己的 `business-rules.md`**。責任的交界寫在消費端：

- **U-8 的 `business-rules.md` R-5** 逐字把「高成本 workflow 的排除」判為**不屬於 U-8**，指向本單元。這是本單元存在的直接依據——沒有它，「反向 PR 開了之後誰負責讓 gauntlet 不跑」會是無主的。
- **同檔 R-4b** 的 AC 分散對照表把 [US:S-6] 的七條 AC 拆給三個單元，其中 **AC 7 歸 U-10b**，AC 1–5 歸 U-8、AC 6 歸 U-2。**本單元完成不等於 S-6 完成，反之亦然**——這也是為什麼本單元的完成判準必須自己說清楚（見 `tech-stack-decisions.md`），不能靠故事層的驗收帶過。

## 與上游的對應

NFR-C1、NFR-S3 與 FR-G1／FR-G2 引自 `requirements.md`；[US:S-6 AC 7] 與單元的完成判準引自 [ug:unit-of-work.md] 的 U-10b；E-1 的前提與反向 PR 的 diff 邊界引自 U-8 的 `business-logic-model.md`；`ui-regression` 為真閘門（`post-steps` 讀 `.stats.unexpected`）與 `contract-guard` 的性質引自 `team.md`；`validate_repo_contract.py` 改為 `git ls-files` 全域掃描（issue #509）引自 `project.md ## Forbidden`；ADR-0006 四面向的逐項判定形式依 `project.md ## Mandated`；既有 workflow 集合的盤點引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）；本單元與 U-8 的責任交界（R-5）與 S-6 的 AC 分散對照（R-4b）引自 U-8 的 `business-rules.md`。
