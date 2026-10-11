# Code Generation 問題檔 — `U22` `progress-channel`

> Stage：`code-generation`（3.5）　Unit：`U22` `progress-channel`（`library`，M）
> 建立時間：2026-10-04
>
> 本站只有一個關卡：**Plan Approval**。它涵蓋三份內容——`code-generation-plan.md`、
> 其中逐字貼入的 Testing Contract、以及 `unit-test-instructions.md`。

---

## Plan Approval

**核可範圍**：

| 檔 | 內容 |
|---|---|
| `code-generation-plan.md` | 12 個步驟、故事↔步驟追溯、不在範圍的四項、以及 **§〇 的 `B-1` 設計決定** |
| 其中的 Testing Contract | methodology `test-after`、strategy `standard`、`contract_sha256: sha256:1f0b6822601f52ff3e71a9bd20a949c9e106f87999f78c986398d5e1963f2f77` |
| `unit-test-instructions.md` | 12 個測試（7 行為 ＋ 5 契約閘門）、六項突變驗證（M1–M6）、精確的 unit-scoped 指令 |

**核可即同時核可一個設計站沒做、由本計畫代做的決定**（計畫 §〇）：

> `BR1.2` 新增的 `DuplicateChannelKey` 在哪裡被接住，從 `functional-design` 到
> `nfr-design` 一路都是假設而非設計。實測 `agent_router.py:124-128` 的
> `event_generator()` **沒有 `try/except`** 且包在 `StreamingResponse` 裡，而
> `functional-spec.md:34` 把 `open` 指派給入口端——所以該例外**不經**
> `design_agent.py:214`，使用者會得到一個**無聲中止的 SSE 串流**。
>
> **本計畫的處置（Step 7）**：在入口端把 `open()` 包進
> `try/except DuplicateChannelKey`，yield 一個**固定訊息**的 `error` 事件後結束該請求。
> 它是最小的封口（不改契約、不改 `BR1.2`、不新增型別），固定訊息沿用既有的
> `BR3.1`／`SEC-2`／`AC13.1.3` 要求故無新決定，且 handler 的存在性可被閘門 grep。
>
> `U22` 的三個設計站都已有終局收據，所以這個決定無法回到設計站做。

**一併封住的四項上游空隙**（都在計畫 §〇 的表內）：`B-2`（1e 的呼叫點枚舉來源）、
`B-3`（`U22-V7` 的 2／3 覆蓋）、`C-5`（`except ... as` 綁定數斷言）、
`C-1`（兩個洩漏點而非一個）。

**完整的跨單元發現清單**見同目錄 `gate-findings-consolidated.md`——其中 A 組
（`DEPLOY.md` 連不上資料庫、77 處失效行號）**不在本計畫範圍**，是獨立的待辦。

[Approval Fingerprint]: sha256:v3:10002f061693e943a83732f92b3cc1f103924aaa0c8776c0b2dc29e1081d460a
[Planned Source]: b6da81b2f101cafb46bf64105788f09e6b85a1697f248db9282710967340a4fc

- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan

[Answer]: Approve Plan
