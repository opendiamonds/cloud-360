Discovered: 2026-08-09T01:29:15Z at commit 8c90f40372ac810cc8f6ef41c46fc7a723031a1e

Re-affirmed: 2026-08-11 at commit 8c90f40372ac810cc8f6ef41c46fc7a723031a1e（未重跑訪談）

本站因 scope-definition Revision 2（新增 PU-6 使用者清單分頁）回跳上游而重跑。
重跑時以確定性驗證取代重新訪談：`HEAD` 仍為原掃描基準 commit `8c90f40`，且
`git diff 8c90f40 -- backend frontend scripts deploy .github schema.sql schema_rbac.sql DEPLOY.md`
與同範圍的 `git status --porcelain` 皆為空集合 —— 本站的產出（team-practices、
discovered-rules、evidence）全部由**程式碼與流程資產的實況**推導，該實況零變更，
故四份 artifact 的內容維持不變。PU-6 是**範圍**變更，不是**實踐**變更：分頁改的是
既有端點的回應契約，不改變測試框架、lint 工具鏈、CI 閘門、分支或 commit 慣例。

判定理由記於本站 `memory.md` 的 ## Deviations。
