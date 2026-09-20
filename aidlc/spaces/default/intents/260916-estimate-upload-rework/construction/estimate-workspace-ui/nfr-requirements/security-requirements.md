# Security — U8

## ADR-0006
| 面向 | 判定 |
|---|---|
| IAM | 經 CapabilityRoute C1.view／edit 閘 |
| Encryption | HTTPS 既有 |
| Network | 僅呼叫 `/api/cost/v1` |
| Audit | 不在前端寫稽核 |

## NFR-S.1 錯誤面（Q2=A）
UI 只顯示後端固定 `detail`；不渲染堆疊／路徑。

## NFR-S.2 Token
沿用 localStorage JWT；不把 token 寫入 URL／log。

<!-- confirmed: Looks correct -->

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-19T20:00:00Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|

### Summary
NFR READY after GATE_REJECTED floor reset; empty findings.
