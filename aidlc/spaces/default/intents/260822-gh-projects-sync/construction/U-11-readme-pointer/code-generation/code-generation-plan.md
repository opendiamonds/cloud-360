# Code Generation Plan — U-11 README 指路段落

<!-- Stage: code-generation（Construction，per-unit）· Unit: U-11-readme-pointer
     Generated: 2026-08-30T06:54:35Z（讀自 date -u） -->

## 這個單元要交付什麼

`unit-of-work.md` 的 U-11 條目：**交付 = `README.md` 的一段新增文字**；複雜度 **XS**；`kind` 刻意留空（五類皆不合）故收完整設計矩陣。

只有兩條規則，兩條都直接來自 [US:S-11] 的 AC，functional-design **未新增任何規則**：

| # | 規則 | 可判定方式 |
| --- | --- | --- |
| R-1 | `README.md` 存在一段含 Project #16 連結的文字，說明該看板是需求清單的**正本** | grep 連結 |
| R-2 | `git diff --numstat -- README.md` 的**刪除行數為 0** | 第二欄讀數 |

**R-2 決定了實作形狀**：這是**純插入**，不得改動任何既有行。連調整鄰近段落的空行都不行——那會產生刪除行。

## 實作步驟

### Step 1 — 決定插入點
- [x] 在 `## Documentation`（README.md:138）**之前**插入新的 `## Requirements Source` 段
- **理由**：`## Documentation` 說的是「文件放哪」，本段說的是「需求的正本在哪」，語意相鄰；且插在兩個既有 H2 之間是純插入，不碰任何既有行
- **追溯**：[req:FR-H1]、[US:S-11 AC 1]

### Step 2 — 撰寫段落
- [x] 內容須明說 Project #16 **是需求清單的正本**（不只是「有一個看板」）
- [x] 連結：`https://github.com/orgs/opendiamonds/projects/16`
- [x] 繁體中文（ADR-0009；README 既有段落為中英並陳的既成形狀，沿用鄰近段落寫法，不自創格式）
- **追溯**：[req:FR-H1]、[US:S-11 AC 1]

### Step 3 — 驗證純插入
- [x] `git diff --numstat -- README.md` 確認**刪除欄為 0**
- [x] `grep -n 'projects/16' README.md` 確認連結存在
- **追溯**：[US:S-11 AC 2]、U-11 完成判準

### Step 4 — Contract 驗證
- [x] `python3 scripts/validate_repo_contract.py` 通過
- **註**：`REQUIRED_TEXT` 對 `README.md` 鎖的是 `Cloud-360`／`AWS`／`GCP`／`Azure`／`draw.io`／`Mobile Web`／`Cloud Security Posture`／`human approval gate`／`MCP & Skill Management` 等關鍵字（本站實讀 `scripts/validate_repo_contract.py`）。**純插入不會移除其中任何一個**，故此步預期為既有保護的複驗，不是新增檢查

## 不另設檢查（上游明文）

`unit-of-work.md` 的 U-11 實作註記與 [US:S-11 AC 2] 的註都指出本單元與全域 DoD 的 `validate_repo_contract.py` 有部分重疊，**下游不需為此另設檢查**。記在此處是為了避免下一個人把重疊誤讀成「有兩套規則要維護」。

## 測試步驟的說明（不是省略）

本單元**不新增測試檔**。理由：兩條規則的驗證方式在 functional-design 就已定為文字比對與 `git diff --numstat` 讀數，都是**一次性的交付檢查**而非需要回歸保護的行為；`org.md ## Testing Posture` 的「tests written alongside code」針對的是有行為的程式碼，本單元沒有可執行的行為。R-1 的關鍵字保護已由 `validate_repo_contract.py` 的 `REQUIRED_TEXT` 常態承接（見 Step 4 的註）。

**這是判斷，不是遺漏**——若你認為 README 段落也該有回歸保護（例如把 `projects/16` 加進 `REQUIRED_TEXT`），請選 Request Changes，那是一個真實的替代方案。

## 不在本單元範圍
- 看板本身的建立、欄位設定、issue 同步 — 分屬 U-3／U-5／U-6
- `README.md` 既有段落的任何改寫 — R-2 明文禁止
