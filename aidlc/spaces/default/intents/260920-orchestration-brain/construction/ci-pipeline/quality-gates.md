# 品質閘門

> 精簡版：列出合併進 `ut` 之前實際會擋下 PR 的閘門，與 build-and-test 記錄的建置與測試指令逐一對照。本站不新增閘門。

## 閘門對照（build-and-test 指令 → CI 是否強制）

| build-and-test 記錄的檢查 | CI 落點 | 強制？ |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | `repo-contract` | 是 |
| `python3 scripts/validate_env_contract.py` | `repo-contract` | 是 |
| cost calculator／pricing lookup 邊界、embedding provider 值 | `repo-contract` | 是 |
| 前端 `npm run lint`（只擋 error；現有 2 warnings） | `frontend` | 是（error 級） |
| `npm run check:types`、`check:ws-types`、`npm run build` | `frontend` | 是 |
| `backend/scripts/dump_openapi.py --check`、`dump_ws_contract.py --check`、MCP tool spec 漂移 | `backend` | 是 |
| 後端 `python -m unittest discover -s tests` | `backend` | 是 |
| `tests_pg`（真實 PostgreSQL） | `concurrency` | 是 |
| 記憶 schema／角色邊界／清除行為斷言 | `memory-schema` | 是 |
| Docker 映像建置 | `docker-build` | 是（只建不推） |
| Playwright e2e（含需真實 stack 的三支 spec） | PR 上的 `ui-regression` | 是（`stats.unexpected` 非 0 即紅） |
| 同步機制自我測試 | `AI-DLC Sync Selftest` | 是 |

## 不是閘門、但需要知道的

- **覆蓋率**：無量測機制。`org.md` 的 80% 是宣告，不是閘門（`team.md` 如實記載）。
- **延遲目標**：build-and-test 矩陣的 14 個延遲數字目標沒有量測機制，也沒有後續擁有 stage，維持 `Unverified`。
- **branch protection 的必要檢查清單**：本站未能以唯讀 API 讀到 `ut` 的保護規則（未授權或未設定），因此「哪些 check 是 GitHub 層級的必要檢查」未查證。上表的「強制」指的是 job 失敗即紅燈，不代表 GitHub 會阻止合併。
- **衝突的 PR 不跑 PR 檢查**：見 `ci-config.md`。PR 與目標分支衝突時，上表凡依 `pull_request` 觸發的閘門都不會執行；push 事件的 CI 仍會跑，但 `ui-regression` 等 PR-only 閘門不會。

## 階段邊界檢查

結論寫在 `<record>/verification/phase-check-construction.md`。
