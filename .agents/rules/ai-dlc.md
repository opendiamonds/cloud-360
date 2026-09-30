# AI-DLC Workflow

本專案採用 AI-DLC v2。

當使用者啟用 AI-DLC 時：

1. 讀取並遵循 `.claude/skills/aidlc/SKILL.md`（框架結構見 `.claude/CLAUDE.md`）。
2. 讀取 `aidlc/spaces/<active-space>/memory/` 的規則層，順序為 `org.md` → `team.md` → `project.md` → `phases/<phase>.md`，strict-additive：較窄的層只能疊加，不得與較寬的層矛盾。
3. 新增專案規則一律寫進 `team.md` / `project.md`，不要改 `.claude/` 內的 upstream 檔（升級時會被整批覆蓋）。

專案指引全文見 `CLAUDE.md`。所有回應與文件產出使用繁體中文；程式碼、變數、API、識別字維持英文。
