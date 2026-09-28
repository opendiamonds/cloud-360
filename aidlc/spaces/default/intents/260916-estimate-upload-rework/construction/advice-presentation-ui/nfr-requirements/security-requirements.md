# Security Requirements — U9

| ADR-0006 面向 | 適用 |
|---|---|
| IAM | JWT 僅 Authorization header；不把 token 放 query（不用裸 EventSource） |
| Encryption | 沿用既有 HTTPS／同源 nginx |
| Network exposure | 僅訂閱使用者已授權的 `set_id`（後端 U7／U2 再查） |
| Audit logging | 本 Unit 不寫 audit；錯誤 UI 不洩堆疊／原始 SSE |

錯誤呈現：固定短語或 `unavailable_reasons` 鍵的中文對照。


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
