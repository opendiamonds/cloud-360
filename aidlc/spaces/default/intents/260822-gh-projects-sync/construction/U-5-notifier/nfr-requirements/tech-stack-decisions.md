# Tech Stack Decisions — U-5 通報

<!-- Stage: nfr-requirements（Construction，per-unit）· Unit: U-5-notifier · kind: library -->

## 決定

**獨立的 composite action `.github/actions/aidlc-sync-notify/`，`shell: bash`，以 `gh issue` 子命令與 `gh api` 操作 Issues，憑證經 `env: GH_TOKEN`。**

## 為什麼獨立於 U-3

兩者都做 GitHub API I/O，但**打的是不同的 API 面**：U-3 是 Projects v2 GraphQL，本單元是 Issues（REST 即足）。更重要的是**驗證方式不同**——[ug:unit-of-work.md] 記 U-3 為「③真實 Projects v2 API」、U-5 沒有獨立列出但其完成判準（連續兩輪後開啟中 issue 數為 1、comment 數 +1）需要的是 **issue 生命週期**的觀察，不是 Projects 的。

合併會讓「這個單元完成了嗎」同時指涉兩種驗證對象。

## 工具

| 決定 | 理由 |
| --- | --- |
| `gh issue list --label` / `gh issue comment` / `gh issue close` | 本單元的四種操作都有現成子命令，不需手寫 GraphQL。與 U-3 的 `gh api graphql` 形成對照：**哪一層用什麼，取決於該 API 面有沒有現成子命令** |
| 搜尋用 **label ＋ 內文 grep**，不用 `gh search issues` | `domain-entities.md` 定的鍵在**內文首行**。`gh issue list --label aidlc-sync-alert` 一次拿到候選（[Q2=A] 本來就要列舉全部），再於本地比對鍵——**不依賴 GitHub 搜尋索引的即時性**，而搜尋索引有已知的延遲 |
| 憑證經 `env: GH_TOKEN` | 與 U-3／U-4 同，repo 既有形狀 |

**「不依賴搜尋索引」是本站的實質決定**，不是實作偏好：GitHub 的 issue 搜尋索引在剛建立的 issue 上有延遲，而 ADR-A8 的收斂演算法**恰好**依賴「立刻找得到剛開的 issue」——並行的第二個 run 若因索引延遲而找不到，就會開出重複（正是缺口 J-1 的成因之一）。改用 `list --label` ＋ 本地比對後，讀的是 issue 的即時狀態而非索引。

> 這不消除 J-1（真正的並行仍可能兩個 run 同時看到 0 筆），但它**移除了一個非並行也會發生的重複來源**。J-1 的處置（`notify` 命中多筆時收斂）仍然必要。

## 承接 bash 的既有代價

U-1 記「沒有原生 `null`」、U-2 記「正規化序列化難做」、U-3 記「GraphQL 錯誤在 HTTP 200 的 body 裡」、U-4 記「`jq` 的兩種寫法只在跨版本時顯現差異」。

**本單元的代價較輕**：`gh issue` 子命令的失敗以非零 exit code 表現（不像 GraphQL 那樣藏在 body），所以錯誤偵測單純。唯一要注意的是 `gh issue list` 的輸出解析——須用 `--json` 取結構化輸出再以 `jq` 處理，**不得**解析人類可讀的表格輸出（欄寬與截斷會隨內容改變）。

## 與上游的對應

C-5 的方法與收斂演算法引自 [ad:component-methods.md] §C-5 與 [ad:decisions.md] ADR-A8；缺口 J-1／J-2 的處置見本單元的 `business-rules.md`（[Q1=A]／[Q2=A]），issue 的可搜尋形狀見 `domain-entities.md`，資料流見 `business-logic-model.md`；權限缺口見同輪的 `security-requirements.md` K-1；單元邊界與完成判準引自 [ug:unit-of-work.md] 的 U-5；FR-E3 引自 `requirements.md`；`GH_TOKEN` 的 env 形狀為實測 `.github/workflows/` 的既有先例（並見 [kb:technology-stack.md]）；紅燈語意引自 [ad:services.md]。
