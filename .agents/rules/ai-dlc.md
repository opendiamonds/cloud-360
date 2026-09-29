# AI-DLC Workflow

本專案採用 AI-DLC v2。

當使用者啟用 AI-DLC 時：

1. 讀取並遵循 `.claude/skills/aidlc/SKILL.md`（框架結構見 `.claude/CLAUDE.md`）。
2. 讀取 `aidlc/spaces/<active-space>/memory/` 的規則層，順序為 `org.md` → `team.md` → `project.md` → `phases/<phase>.md`，strict-additive：較窄的層只能疊加，不得與較寬的層矛盾。
3. 新增專案規則一律寫進 `team.md` / `project.md`，不要改 `.claude/` 內的 upstream 檔（升級時會被整批覆蓋）。

## 測試案例

**產生任何測試案例前，先讀 [`TESTING.md`](TESTING.md)** —— 它是測試案例格式契約的唯一真實來源，不限工具（Claude Code／Cursor／Antigravity／純手寫皆適用）。

- **必要欄位一個都不能少**：目的、受測介面、前置條件、測試步驟、通過條件、追溯。回歸案例另外必須有「背景」（症狀、錯誤訊息逐字、既有自動化層為何沒抓到）。選用欄位可依場景自行增刪。
- 「受測介面」的 API 端點與 UI 路徑會被**機械比對** `openapi.json` 與 `frontend/src/App.tsx` 的路由表——寫了不存在的端點或路徑會被擋下。
- 預期結果不得寫「正常」「成功」這類無法判定的詞。
- 寫完**必須**跑 `python3 scripts/tcms_validate.py --all`。**ERROR 一律阻擋**，未通過不得同步進 TCMS。
- 手動案例與自動化案例的真實來源不同，不可互抄：自動化案例的描述寫在 code 旁的規格註解（`@purpose`／`@api`／`@step` 等），**不在 TCMS 手寫**。

專案指引全文見 `CLAUDE.md`。所有回應與文件產出使用繁體中文；程式碼、變數、API、識別字維持英文。
