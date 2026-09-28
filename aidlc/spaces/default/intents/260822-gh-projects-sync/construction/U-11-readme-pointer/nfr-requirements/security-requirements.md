# Security Requirements — U-11 README 指路段落

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-11-readme-pointer
     `kind` 依 [ug:unit-of-work.md] 刻意留空，故解析出**全部五份**產出。 -->

## ADR-0006 security baseline 的四面向逐項判定

`project.md ## Mandated` 要求**對每一項變更**逐項判定四面向，判定為不適用者一律附理由、不留空白。

| 面向 | 判定 | 理由 |
| --- | --- | --- |
| **IAM** | **不適用** | 本單元不持有憑證、不呼叫任何 API、不需要任何權限。`requirements.md` NFR-S1 定義的權限全部落在 U-3／U-4／workflow 層 |
| **Encryption** | **不適用** | 無傳輸、無儲存。README 的遞送由 GitHub 的 HTTPS 承擔，與本變更無關 |
| **Network exposure** | **不適用** | NFR-S5 已判定整個機制此面向不適用；本單元更是連出站呼叫都沒有 |
| **Audit logging** | **不適用** | NFR-S6 要求每次 Status 變更可回答三要素；本單元不產生 Status 變更。變更本身的稽核由 git 歷史承擔 |

## SEC-1：這段文字會揭露什麼

**本 repo 為 public**，README 是它的門面，內容對全世界可讀。本單元新增的段落含 **Project #16 的連結**。

**判定：不構成新的暴露。** 三項依據：

1. Project #16 的存取控制由 GitHub 自身承擔——**連結可見不等於內容可讀**。無權限者點進去看到的是 404 或權限頁。
2. `README.md` 本來就公開，本單元不改變它的可見性。
3. 該段落的內容是「需求清單的正本在哪裡」，不含任何憑證、端點、內部主機名或組態值。

**約束（給實作）**：這段文字**不得**包含 Project 的 GraphQL node id、任何 token、或 `192.168.10.10` 這類內部位址。它只放人可點的 Project URL 與一句說明。這條約束二元可判——PR 上 grep 即可。

## SEC-2：不得夾帶其他變更

[US:S-11 AC 2] 要求 `git diff --numstat` 對 `README.md` 的**刪除行數為 0**。這條的原意是「只增不動」，但它同時構成一道安全性質的護欄：**本單元不得藉機修改 README 既有的任何敘述**，包括部署位址、環境說明或任何既有連結。

`project.md ## Forbidden` 的兩條（不得 commit 憑證字串、版控中不得存在 `prod`／`production`／`secrets` 路徑）由全域 DoD 的 `validate_repo_contract.py` 承接，本單元不另設檢查——[ug:unit-of-work.md] 的 U-11 實作註記明文「不需另設檢查」。

## 與上游的對應

四面向的依據為 `requirements.md` 的 NFR-S1～S6 與 `project.md` 的 ADR-0006 落點；AC 引自 `stories.md` 的 S-11；完成判準與「不需另設檢查」引自 [ug:unit-of-work.md] 的 U-11；規則 R-1／R-2 見同輪的 `business-rules.md`，無執行序的判定見 `business-logic-model.md`；repo 為 public 與既有 contract 驗證的事實引自 `project.md` 與 [kb:technology-stack.md]。
