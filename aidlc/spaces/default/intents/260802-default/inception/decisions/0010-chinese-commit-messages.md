# ADR 0010: Commit message 一律繁體中文

- Status: Accepted
- Date: 2026-07-25
- Related: `.aidlc-overrides/commit-message.md`、ADR-0009（文件一律繁體中文）、`.aidlc-overrides/branch-naming.md`

### Context

ADR-0009 已把 `aidlc-docs/**/*.md` 與 CLAUDE.md 的文件語言統一為繁體中文，但 commit message 仍是英文 conventional commits，且從未有成文規範 — repo 內唯一相關的敘述是 `.aidlc-overrides/branch-naming.md` 順帶引用的 conventional commit type 清單。

實務上造成兩個問題：

1. **語言不一致**：文件、PR 討論、gh-aw agentic workflow 的留言都已是繁中，只有 commit history 是英文，讀 `git log` 與讀文件的語感斷裂。
2. **自動化產出無人管**：`deploy.yml` 的 revert PR 標題/body、Lint Fixer 的 push，都是英文硬編碼，沒有規範可依循，未來只會持續漂移。

### Decision

1. **Commit message 一律繁體中文**，涵蓋 type、描述、body 與 PR 標題。
2. **Conventional commit 的 type 一併中文化**（`功能`、`修正`、`文件`、`格式`、`重構`、`效能`、`測試`、`建置`、`整合`、`雜項`、`還原`），完整對照表見 `.aidlc-overrides/commit-message.md`。
3. **scope 與機器解析 token 維持英文**：`(rbac)` 等模組識別字、`BREAKING CHANGE:`、`!` 標記、`Co-Authored-By:` 等 trailer。
4. **branch naming 不跟進中文化**。`.aidlc-overrides/branch-naming.md` 的 `<type>` 維持英文，與 commit type 明確解耦 — 中文 branch 名稱在 `gh` CLI、URL 與部分 CI 工具需要 percent-encoding，風險大於可讀性收益。兩者以對照表換算。
5. **適用範圍含 CI 自動產出**：`deploy.yml` 的 revert commit 與 revert PR、gh-aw workflow 產生的 commit 一併中文化，避免人工與自動產出語言分裂。
6. **不溯及既往**：既有 commit 歷史不做 rewrite。
7. 以 override `.aidlc-overrides/commit-message.md` 落地（override 永遠勝出，升級 upstream 不受影響）。

### Consequences

**正面**：commit history 與文件、PR 留言語言一致；`git log` 對繁中團隊直接可讀；自動化產出首次納入規範，不再各自漂移。

**負面 / 風險**：

- **工具相容性**：中文 type 無法被 conventional-commits 生態的預設 parser 解析。目前專案未使用自動 changelog / semantic-release，影響為零；未來要接線時需自訂 parser preset，regex 與版本號對應已記在 override 文件裡。
- **非繁中貢獻者**：需查對照表才能寫出合規 commit。
- **無法自動強制**：`scripts/validate_repo_contract.py` 驗證的是檔案內容，不是 git 歷史，因此本規則無法納入 repo contract。強制方式為 PR review 加 AI agent 自動套用；若未來要硬性擋下，需另加 commit-msg hook 或 CI step 檢查 PR 標題。
