# 技術選型 — U-8 反向同步 workflow

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-8-reverse-workflow · kind: service -->

## 承載形式：純 Actions 兩檔拆分，與 U-6／U-7 一致

**`.github/workflows/aidlc-sync-reverse.yml`（cron 觸發 ＋ `workflow_dispatch`）＋ 其 `*-impl.yml`（`on: workflow_call`）**，純 Actions、`shell: bash`。本單元**不引入任何新工具、語言或服務**。

> **此處先前寫成 gh-aw 的 `.md` ＋ 編譯出的 `.lock.yml`，已更正。** 正確形式有三處一致的依據：[ug:unit-of-work.md] 的 U-8 交付欄逐字為「`aidlc-sync-reverse.yml` ＋ 其 `*-impl.yml`」，且 U-6 與 U-7 的 `tech-stack-decisions.md` 皆已定案為純 Actions 兩檔拆分（ADR-A10）。三支同步 workflow 用同一形狀。
>
> ADR-0013 §3 的承載位置對照表把同步 workflows 記為 `.github/workflows/aidlc-sync-*.md`（gh-aw 形式）並保留不變——**這是 ADR 與其下游 units-generation／construction 的落差**，收斂發生在 U-6 而非本單元。本站沿用 U-6 已定案的形狀，**不重開該決定**，僅記明落差存在：`project.md ## Forbidden` 收窄後的規則要求決定性邏輯放純 Actions 步驟，而反向同步的判定（雜湊比對）全是決定性的，純 Actions 是符合該規則的形狀。

因為不走 gh-aw，**NFR-M1 的 `.md` ↔ `.lock.yml` 漂移風險對本單元不適用**——沒有編譯步驟就沒有漂移。（該風險仍適用於 U-10b 要修改的四支既有 gh-aw workflow。）

## 開 PR 的憑證選擇是一個**尚未被上游決定**的分岔

本單元開 PR 可以用兩種憑證，而選哪一種同時決定三件事：

| | 用 workflow 的 `GITHUB_TOKEN` | 用本 intent 的專用憑證 |
| --- | --- | --- |
| 權限宣告落點 | workflow 的 `permissions:` 區塊 | 憑證鑄造時的勾選（NFR-S1 的集合） |
| 缺口 P-1 是否適用 | 否——`permissions:` 可隨時改，不需組織管理者 | **是**——見 `security-requirements.md` |
| 反向 PR 是否觸發 `on: pull_request` | **待實測**（見下） | **待實測** |

**第三列是本站無法從 repo 內容查證的事實。** 我在本 repo 的 11 支 workflow 與 `.lock.yml` 中找不到任何關於「某類憑證開的 PR 是否觸發 workflow」的設定或註解，因此**不在此斷言**。

**但它與 U-10b 直接相關**：U-10b 的存在理由正是「讓反向 PR 不觸發高成本 workflow」。若某一種憑證本來就不觸發，U-10b 的必要性與形狀都會變；若會觸發，U-10b 是必須的。

**處置**：列為 **PRE-1（Bolt 0）的實測項**——鑄出憑證後開一個測試 PR，觀察 `on: pull_request` 的 workflow 是否被觸發，結果決定憑證選擇與 U-10b 的形狀。**這與缺口 P-1 落在同一個閘門**，一次實測可同時解掉兩者，故指派成本近乎為零。**本站不預選憑證**——預選會讓一個可用一次實測消除的不確定性變成一個賭注。

## 分支命名：D-1 的擴充，因 E-2 而必要

`aidlc-sync/reverse/<intent_id>-<date>`，並掛 label `aidlc-sync-reverse`。

**U-6 的 D-1 裁定的原文是 `aidlc-sync/reverse/<date>`（無 intent_id）。** 本單元加入 `<intent_id>` **不是偏好而是必要**：E-2 定為一個 intent 一則 PR，同一天有兩個 intent 被人改動時，`<date>` 單獨無法區分，兩則 PR 會撞同一個分支名。**這是 E-2 的連帶後果，D-1 作成時尚無 E-2。**

D-1 的另一半（label `aidlc-sync-reverse`）**原樣沿用**——它是 U-6 用 `gh pr list --label` 查找 `reverse_pending` 的依據，不因本擴充改變。

**注意它不符 `team.md` 的 `<uploader>/<type>/<slug>`。** 這是刻意的：該規則明文「不適用於 `dependabot/*`、`release/*` 等**自動產生的分支**」，本單元的分支正是此類。**在實作 PR 中須明寫這個豁免依據**，否則下一個看到它的人會以為是違規。

## 既有技術堆疊的承接

**版本基準的警告必須隨本檔傳遞**：[ck:technology-stack.md] 開頭逐字寫「`origin/ut` 上的 gh-aw 已升級至 `v0.86.2`，本基準仍是 `v0.81.6`……本檔所有 gh-aw 相關版本只對 `9307dbc` 成立」，且 `actions-lock.json` 在兩版之間由 5 筆變 4 筆（`setup-cli` 條目消失）。**本單元的實作一律以 `ut` 當下的版本查證，不引用 codekb 的版本數字**；上表「待實測」的兩列也必須在該版本上測。

## 與上游的對應

NFR-M1、OQ-4、FR-G1 引自 `requirements.md`；承載形式的定案引自 ADR-0013 與 `project.md ## Forbidden`；分支命名與一 intent 一 PR 引自本單元的 `business-logic-model.md`；U-10b 的責任歸屬（R-5）與 R-4b 的 AC 分散對照引自本單元的 `business-rules.md`；自動產生分支的豁免引自 `team.md ## Way of Working`；本 repo 既有的 gh-aw／CI 堆疊事實引自 [ck:technology-stack.md]（`aidlc/spaces/default/codekb/cloud-360/technology-stack.md`）。
