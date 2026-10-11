# Code Generation 問題檔 — `U11 intent-router`

> 本站只有一個關卡：**Plan Approval**。前四站（`functional-design`／
> `nfr-requirements`／`nfr-design`／`infrastructure-design`）已把全部設計決定定案，
> 本站不重問任何一項——計畫是它們的執行化，不是新的設計。

## 上游已定案、本站不重問

| 事項 | 出處 |
|---|---|
| 反問判定寫成候選清單上的述詞 `can_single_out` | `functional-design` 的 `[IR1]`=A |
| 路由層模型＝`typesafe/jev-1.13` | `OQ-4`（使用者 `2026-10-03T11:48:31Z`，`nfr-requirements` 的 `[N1]`=C 再確認） |
| P50 ≤ 800 ms、硬逾時 5 秒、每輪 1 次呼叫、重試 0 次 | `nfr-requirements` 的 `[N2]`=A |
| `OQ-10` 承接 `build-and-test` | `nfr-requirements` 的 `[N3]`=A |
| tool schema 採**扁平陣列 ＋ `slot` 索引** | `nfr-design` 的 `[D1]`=A |
| `NFR1` 量測改由 `workflow_dispatch` 手動 job 承載 | `infrastructure-design` 的 `[I1]`=A |
| `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` 由 `render-env.sh` 寫字面值 `0.7` | `infrastructure-design` 的 `[I2]`=A |
| 不建 circuit breaker、不設 fallback 模型、不引入 tracing、不建 dashboard | `nfr-design/reliability-design.md` §三／§五；`observability-design.md` §三／`monitoring-design.md` §五 |
| 零新依賴 | `tech-stack-decisions.md` 的 `TS-5` |

## 計畫摘要（供關卡判讀）

**12 個步驟**，其中 **3 個明確標為「不適用」**（資料模型、API 端點、前端）——
它們不是跳過，是本單元的設計邊界（`NFR4.70` 無狀態、`SEC-2` 無端點、無前端）。

- **Step 1–2**：型別／例外／設定骨架 ＋ **驗證既有 test runner**（brownfield，runner 已存在）
- **Step 4–5**：L0 讀取 I/O（`SessionStore` 唯讀、`MemoryFacade.search` 的 `kinds`
  以**模組層常數**排除情節記憶）＋ 其測試
- **Step 6–7**：三個純函式層（L2 組裝／L4 解析／L5 述詞）＋ 其測試，
  含 **ADR-0006 的七條 property**
- **Step 9**：L3 model-port（專用 client factory、單節點 `StateGraph`、tool schema）＋ 七個替身測試
- **Step 11**：五個環境變數三處同步 ＋ `LOCAL-DEV.md`
- **Step 12**：`source-manifest.json`／`code-summary.md`／`traceability.json`

**七個新模組**全部在 `backend/services/`，檔名刻意避開 `_router.py` 字尾
（該字尾在 `team.md` 慣例裡專指有 `APIRouter` 的 HTTP 路由模組，而本單元沒有）。

## 單元測試指引摘要

- **框架**：Python 內建 `unittest` ＋ `hypothesis`（**不是 pytest**），零新依賴
- **scoped 指令**：`cd backend` → `python3 -m unittest -v tests.test_intent_routing_{predicate,parser,context,port,structure}`
  ——**不是** `python`（本機無此指令），**不是**專案層指令（`build-and-test` 會對每個單元各跑一次）
- **五個測試檔**，策略 standard（每元件 5–8 個）
- **PBT 的生成策略有兩個硬性要求**：`scoresAvailable` 與 `len(slots)` 都必須由策略
  **顯式驅動**——Hypothesis 不會因為某個分支從未被抽到而報錯，而 `BR3.3`（無分數）
  與多槽位正是最容易長期零覆蓋的兩個分支
- **本單元的測試一律不需要 `OPENROUTER_API_KEY`**，與既有 LLM 測試做法一致

## Plan Approval

本題涵蓋 `code-generation-plan.md`（含其內嵌的 Testing Contract）與
`unit-test-instructions.md` 兩份檔案的**全部內容**。

[Approval Fingerprint]: sha256:v3:111f34d6cb6b96126df5df292ad9bbebfce389fc6a09c69f95235f61e3acedbe
[Planned Source]: df1523e01a0365485a31fa659b34fbdb2d2588cff472881c22af1cb87c82a60d

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
