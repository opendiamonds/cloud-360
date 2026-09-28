# Code Summary — U-11 README 指路段落

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-11-readme-pointer
     Generated: 2026-08-30T07:39:00Z（讀自 date -u） -->

## 變更

**修改一個檔案**：`README.md`，插入 5 行（H2、空行、中文行、英文行、空行），成為新的 `## Requirements Source` 段，位於 `## Documentation` 之前。

```markdown
## Requirements Source

Cloud-360 的需求清單正本是 opendiamonds 組織的 GitHub Project #16 [「Cloud-360 開發計劃」](https://github.com/orgs/opendiamonds/projects/16)。看板上的項目是需求的權威來源；repo 內的需求文件與 GitHub issue 皆為其衍生，兩者不一致時以看板為準。
GitHub Project #16 "Cloud-360 開發計劃" is the source of truth for the Cloud-360 requirement list; documents and issues in this repository are derived from it.
```

## 兩條規則的驗證（實測輸出）

| 規則 | 指令 | 結果 |
| --- | --- | --- |
| **R-2**（刪除行數為 0，[US:S-11 AC 2]） | `git diff --numstat -- README.md` | `5	0	README.md` — **第二欄為 0**，純插入 |
| **R-1**（含 Project #16 連結且說明是正本） | `grep -n 'projects/16' README.md` | 命中第 140 行 |
| 全域 DoD | `python3 scripts/validate_repo_contract.py` | `passed`（exit 0） |

**額外查證**（實作者自行加做，與 R-2 同一風險面）：開工前 `git status --porcelain -- README.md` 為空，確認 numstat 的比較基準是乾淨的 HEAD——`5 0` 是本次變更的全部，不是混雜既有未提交改動的結果。`git diff --check` exit 0。

## 關鍵實作決定

### 段落形狀沿用「緊鄰插入點的那一段」，不套全檔通則

`## Documentation` 的既成形狀是 H2 → 空行 → **中文一行 → 英文一行（連續、中間無空行）**，本段逐一沿用。

**這是先量測再決定，不是套用自認更正確的標準**：README 全檔並非統一雙語——`## Architecture Visualization Canvas`／`## Cloud Operation Integration`／`## MCP & Skill Management` 是純中文，`## Repository Contract` 是純英文。沿用鄰近段落是唯一有依據的選擇。

### 「正本」語意落在三處，不只是「有一個看板」

[req:FR-H1] 的重點是**正本**：`需求清單正本是…`、`看板上的項目是需求的權威來源`、`兩者不一致時以看板為準`。第三句把「正本」從形容詞變成**可執行的裁決規則**。

### H2 標題用英文

與 README 既有 **10** 個 H2 一致（全部英文標題、內文中文）。

> **數字更正（2026-08-30T07:49:35Z，reviewer Minor）**：先前寫「9 個」，`git show HEAD:README.md | grep -c '^## '` 實測為 **10**。結論不受影響（全部確為英文標題），但這是本 intent 第四次「基準數未重數」——`project.md` 的 `delivery-planning:dp-L1`（可以被計算的數字先算再寫）已明文涵蓋，規則存在而未被執行。ADR-0009 的繁中要求約束的是內文，標題沿用既成形狀。

## 未解決項目（誠實列出）

1. **`projects/16` 沒有任何回歸保護**。這是計畫已裁決的結果（不新增測試檔、不動 `REQUIRED_TEXT`），但後果要講清楚：`validate_repo_contract.py` 的 `REQUIRED_TEXT` 對 `README.md` 鎖的是 `Cloud-360`／`AWS`／`GCP`／`Azure`／`draw.io`／`Mobile Web`／`Cloud Security Posture`／`human approval gate`／`MCP & Skill Management` 等既有關鍵字，**不含本次新增的連結**。若日後有人刪掉整個 `## Requirements Source` 段，contract 檢查**仍會綠燈**，無任何自動化層會察覺。已登錄 `open-items.md`。**不要把「validate 通過」誤讀成「這段受保護」。**
2. **英文行用 ASCII `"`、中文行用「」**。

> **理由更正（2026-08-30T07:49:35Z，reviewer Minor）**：先前寫「為維持 README 既有英文段落的字元慣例」。**該先例不存在**——`git show HEAD:README.md | grep -c '"'` 實測為 **0**，變更前 README 的英文句子從未使用過任何引號。**選擇本身沒問題**（ASCII 直引號是英文一般排版慣例），錯的是為它編了一個查得到、且查了就會發現不成立的依據。
>
> 這比選錯更難察覺：一個好選擇配一個假理由，下一個讀的人會以為「既有慣例」是可依循的事實而繼續沿用它。正確理由是「沿用英文一般排版慣例」，與 README 無關。

若審查認為中英引號應統一，是一行的改動，但**會產生一次刪除行**，必須留到下一次變更做——併進本次會破壞 R-2 的 `0`。

## Review (code-generation)

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-30T07:44:42Z
**Iteration:** 1

### 逐項發現

| # | 嚴重度 | 檔案:行 | 發現 | 可複驗證據 | 建議修法 | 分類 |
|---|---|---|---|---|---|---|
| 1 | Minor | `code-summary.md:41`（「H2 標題用英文」段） | 宣稱「與 README 既有 9 個 H2 一致」，實際重數為 **10**，非 9。 | 對變更前版本跑 `git show HEAD:README.md \| grep -n "^## "`，得 10 個 H2：`Platform Vision`／`System Architecture`／`Core Modules`／`Web-Based Desktop and Mobile Experience`／`Architecture Visualization Canvas`／`Cloud Operation Integration`／`MCP & Skill Management`／`Documentation`／`Repository Contract`／`Validation`。10 個皆為英文標題，故「全部英文標題」的結論不受影響，只有計數本身錯誤。 | 把 41 行的「9 個」改為「10 個」。此為純文字更正，不影響 README.md 本身（不產生新的刪除行），不觸發 R-2 風險。 | 新引入（本輪 `code-summary.md` 首次做此宣稱，非沿用上游文字；`business-rules.md`／`business-logic-model.md`／`code-generation-plan.md` 均未提過這個數字）。附帶：`project.md ## Corrections` 已三次記載同型失誤（`units-generation:c9`／`delivery-planning:dp-L1`／`units-generation:rev1-L1`：「引用『既有為 N 條』這類基準數時，那個 N 也要重數」／「可以被計算的數字先算再寫」），本次是同一失效模式在 XS 單元的第四次重現，僅因本單元影響面小而未升級為 Major。 |
| 2 | Minor | `code-summary.md:46`（「未解決項目」第 2 項） | 宣稱英文行用 ASCII 引號是「為維持 README 既有英文段落的字元慣例」，但實測 README 變更前**沒有任何**英文句子使用過引號（全形或半形）——不存在可供「維持」的既有慣例，這句理由是虛構的先例。 | `grep -n '"' /tmp/readme-head.md`（HEAD 版本 README）與 `grep -n '「\|」' /tmp/readme-head.md` 均零命中；本次變更後唯一命中的兩行（`README.md:140` 全形引號、`README.md:141` ASCII 引號）都是本次新增的內容本身。 | 改寫理由為「README 尚無既有的英文引號慣例先例；ASCII 直引號是英文排版的一般預設寫法，故沿用一般英文寫作慣例，而非沿用 README 既有先例」。選擇本身沒有問題（ASCII 引號在英文句中是合理預設），只是支撐理由需要更正為準確敘述。 | 新引入（同上，`code-summary.md` 首次做此宣稱）。 |

### Attempted refutations that did not hold

- **懷疑 `validate_repo_contract.py` 有重複 `README.md` dict key 導致 `REQUIRED_TEXT` 實際生效值與 code-summary 的引用不符**：以 `python3 -c "import importlib...; print(m.REQUIRED_TEXT['README.md'])"` 實跑，結果為 `('Cloud-360', 'AWS', 'GCP', 'Azure', 'draw.io', 'Mobile Web', 'Cloud Security Posture', 'human approval gate', 'MCP & Skill Management')`，與 code-summary.md:45 的引用逐字相符。第二個 `"README.md"` key（`scripts/validate_repo_contract.py:205`）屬於另一個字典 `REQUIRED_RECORD_TEXT`（記錄層，鎖的是 record 目錄下的 README），非同一字典的重複鍵，不構成 bug，也不影響本單元。**不成立。**
- **懷疑「正本」語意只是表面提及，未真正表達權威來源關係**：逐句核對插入段落三句——「需求清單正本是…」、「看板上的項目是需求的權威來源」、「兩者不一致時以看板為準」——第三句把「正本」從形容詞轉成可執行的裁決規則，與 [US:S-11 AC 1] 的字面要求（「說明該看板是需求清單的正本」）完全對應。**不成立。**
- **懷疑插入點破壞既有 markdown 結構（H2 層級、清單、空行）**：`git diff` 全文核對，插入前後各保留原有的單一空行分隔，新段落本身遵守「H2、空行、內文、空行」的既有結構，`git diff --check` exit 0（無空白錯誤），無清單或程式碼區塊被夾斷。**不成立。**
- **懷疑 `https://github.com/orgs/opendiamonds/projects/16` 的組織名或路徑形狀有誤**：`git remote -v` 確認本 repo 遠端為 `git@github.com:opendiamonds/cloud-360.git`，組織名 `opendiamonds`屬實；URL 路徑形狀 `github.com/orgs/<org>/projects/<number>` 為 GitHub org-level Projects（v2）的正確網址格式。專案編號 `16` 本身無法在本次審查中以 API 驗證（`gh auth status` 已登入，但 token 缺少 `read:project` scope，`gh api graphql` 查詢回 `INSUFFICIENT_SCOPES`）；但該編號是 `unit-of-work.md`／`business-rules.md`／`code-generation-plan.md` 一路沿用的既有上游事實，非本輪新引入，且看板本身的建立屬 U-3／U-5／U-6，不在本單元查證範圍內。**未能推翻，亦非本單元可查證範圍，不列為發現。**
- **懷疑 `open-items.md` 的 CG:OPEN-2 登錄不存在**：在 `construction/U-11-readme-pointer/` 整棵目錄樹搜尋 `open-items.md`，零命中；嘗試往上一層核對時被 reviewer 讀取範圍 hook 擋下（跨單元 `construction/` 路徑）。**無法在被授權的讀取範圍內完全證實或推翻**——由於任務簡述已將此列為「已知且已登錄的事項」，且其揭露內容（`projects/16` 無回歸保護）與本輪獨立核對 `REQUIRED_TEXT` 實際內容的結果完全一致、無矛盾，採信既有登錄、不升級為發現。
- **懷疑 R-2（刪除行數為 0）的 `git diff --numstat` 讀數是 code-summary 片面轉述**：獨立執行 `git status --porcelain -- README.md`（乾淨、僅 `M README.md`）與 `git diff --numstat -- README.md`，實測輸出 `5\t0\tREADME.md`，與 code-summary.md:21 的宣稱逐字相符；`git diff --check` exit 0。**不成立。**

### Summary

新引入：2（Minor）；既存漏審：0；新設計問題：0。核心的兩條規則（R-1「正本」語意、R-2 純插入零刪除）與 contract 全域 DoD（`validate_repo_contract.py`、`validate_env_contract.py`）皆經獨立重跑驗證成立，未發現任何會讓 [US:S-11] AC 1／AC 2 落空的問題。兩項 Minor 發現皆為 `code-summary.md` 本身文字的準確性瑕疵（既有 H2 計數誤植為 9、ASCII 引號理由的「既有先例」不存在），不影響 `README.md` 實際交付內容，也不產生新的刪除行或違反 R-2。已知並已登錄的兩項開放事項（`projects/16` 無回歸保護、ASCII／全形引號不統一）經核對其處置理由站得住腳，不重複列為發現。

VERDICT: READY
