# Requirements Analysis — 澄清問題

- Intent：`260816-production-path-check`
- Scope：bugfix（8 stages，Minimal depth）
- 來源：GitHub issue [#509](https://github.com/opendiamonds/cloud-360/issues/509)

## 前言：不重問的事項

下列已由上游定案或屬既有事實，本站不重問：

| 事項 | 已定案於 | 內容 |
|---|---|---|
| 缺陷本身是否成立 | issue #509 + 本站實測 | 成立。見 Sources S-1、S-2 |
| 要不要修 | `aidlc_sync_buglist.py --accept 509` | 已接受，issue 已貼 `aidlc:accepted` |
| 是否需要回歸測試 | `org.md` `## Testing Posture` | bugfix scope 一律需要「針對該缺陷的回歸測試」，非選項 |
| 文件語言 | ADR-0009 | 繁體中文 |

---

## Sources（出題前的唯讀查證）

**S-1｜缺陷的機制** — `scripts/validate_repo_contract.py:356`

```python
changed_files = set(git_diff_name_only("--cached")) | set(git_diff_name_only())
```

輸入是 working tree 的 diff（staged ∪ unstaged）。

**S-2｜CI 是乾淨 checkout，兩個集合皆為空** — 實測於乾淨工作樹：

```
git diff --name-only --cached : 0 個檔案
git diff --name-only          : 0 個檔案
```

迴圈不會執行，函式必定回傳 0。**這道檢查在 CI 恆為 no-op。**

**S-3｜CI 的 checkout 未設 fetch-depth** — `.github/workflows/ci.yml` 的 `repo-contract` job：

```yaml
- uses: actions/checkout@v4
```

未指定 `fetch-depth`，預設為 1（淺 clone）。**`git diff origin/ut...HEAD` 在 CI 上拿不到 base 的歷史。**

**S-4｜CI 同時被兩種事件觸發** — `on: pull_request` 與 `on: push`（`main`／`ut`／`danniel/**`／`chore/**`）。兩者的 base 來源不同：PR 事件有 `github.base_ref`，push 事件只有 `github.event.before`。

**S-5｜全域掃描不會誤擋既有檔案** — 實測 `git ls-files` 逐段比對 path part：

```
含 prod／production／secrets 作為完整 path part 的檔案：0 個
```

**S-6｜path-part 比對的既有邏輯正確** — 有 10 個檔名含 `prod`／`secret` 字串但非完整 path part（如 `.claude/agents/aidlc-product-agent.md`），現行的 `Path(path).parts` 比對**不會**誤擋它們。這條邏輯無需變更。

**S-7｜規則層的宣稱強度高於機制** — `project.md` `## Forbidden`：

> NEVER 新增 path parts 含 `prod`、`production`、`secrets` 的檔案 — `scripts/validate_repo_contract.py` 會擋（CI 紅燈）。

`team.md` 已如實記載此落差（「這道檢查在 CI 恆為 no-op」），但一直沒有修。

---

## Q1：修法採哪一種比對基準？

**A. 全域掃描 `git ls-files`（不看 diff）**
把「不得**新增**」改為「不得**存在**」。不需要 base、不需要改 CI 設定（S-3 的淺 clone 問題直接消失）、不需要處理兩種事件的 base 差異（S-4）。實測目前 0 命中（S-5），所以不會誤擋既有檔案。語意比原規則更嚴格。

**B. PR base 比對 `git diff <base>...HEAD`**
維持「不得新增」的原語意。但需要同時改 `ci.yml`（加 `fetch-depth: 0`）並在腳本內處理 PR 與 push 兩種事件的 base 取得方式（S-3、S-4）。變更面較大。（原措辭稱淺 clone 為「CI 效能的刻意設定」，經 reviewer 查證 `git log -p --follow` 後確認 `fetch-depth` 從未被設定過，屬工具預設值而非已記錄的團隊決策，故此處更正。此更正不影響 Q1 的已選答案 A。）

**C. 兩者並用**
CI 用全域掃描（無 diff 依賴），本機保留 working tree diff 檢查（提交前的快速回饋）。行為依執行環境而異，需要一個明確的判斷依據（例如 `CI` 環境變數）。

**D. 其他（請說明）**

`[Answer]: A —— 全域掃描 git ls-files`

---

## Q2：`project.md` 的規則措辭是否同步更新？

若 Q1 選 A 或 C，規則的語意會從「不得新增」變成「不得存在」，`project.md` `## Forbidden` 的現行措辭（S-7）會與機制不符。

**A. 同步更新措辭**
把 `## Forbidden` 改為「不得**存在**」並註明檢查方式。規則與機制一致。

**B. 不更新，維持現狀**
措辭與機制的落差留待下次 practices-discovery 處理。本 intent 只改程式碼。

**C. 更新，且一併移除 `team.md` 的「已知落差」記載**
該記載（「這道檢查在 CI 恆為 no-op」）在修好後即不再成立，留著會誤導。

`[Answer]: C —— 更新 project.md 措辭，並移除 team.md 的落差記載`

> **關於 `team.md` 的編輯權限**：`team.md` 標頭寫「Edit at the gate, not directly」，
> 指的是**規則的新增與修改**須經 practices-discovery 的 affirmation gate。本次移除的是一條
> **事實記載**（「這道檢查在 CI 恆為 no-op」），它在修正後不再為真——這是事實更正，不是政策變更。
> 兩者性質不同，故本 intent 逕行移除，並在 `requirements.md` 記明此判斷依據。

---

## Assumption Confirmation

本站假設下列各項成立，請一併確認：

1. 修正範圍限於 `scripts/validate_repo_contract.py`（以及 Q1 選 B 時的 `ci.yml`），不擴及其他 contract 檢查。
2. 回歸測試須能在**乾淨工作樹**（即 CI 的實際條件）下重現原缺陷 —— 這是本次修正的核心驗收點。
3. `FORBIDDEN_NEW_PATH_PARTS` 的內容（`prod`／`production`／`secrets`）不變。
4. 本 intent 不處理 codekb 中發現的其他缺陷（`unsupported` 死契約、`fetch_icon_from_n8n` 的殘留靜默路徑），它們各自獨立。

`[Confirmed]: 四條假設全部確認（2026-08-17，於 requirements-analysis 的 stage gate）`

---

## Q3（追加）：`team.md` 的編輯權限 —— 由 reviewer M-2 觸發

reviewer 指出 Q2 的答案標籤（C：更新並移除落差記載）**沒有單獨確認**「是否繞過 practices-discovery 的 gate」這件事，而該段文字落在 `## Deployment`（gate 治理的五個 section 之一），不是 `## Corrections`（自由編輯區）。

**A. 本 intent 直接改，並記明這是有意識的例外**
保留已知為假的記載，代價高於一次越界編輯。變更僅限刪除失效描述，不新增規則、不放寬約束。

**B. 本 intent 不改 `team.md`，留給 practices-discovery**
完全尊重 gate 治理邊界，代價是 `team.md` 有一段時間寫著已不成立的事實。

**C. 不刪除，改為就地註記「已於 PR #XXX 修正」**
只追加狀態、不動實質內容，歷史記載也保留。

`[Answer]: A —— 本 intent 直接改，並在 requirements.md 記明這是有意識的例外、非先例；下次 practices-discovery 應覆核此處並決定五個 section 內純事實記載的維護權責`
