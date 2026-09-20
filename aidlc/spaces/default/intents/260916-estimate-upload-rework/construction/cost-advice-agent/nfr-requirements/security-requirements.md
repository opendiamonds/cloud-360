# Security Requirements — cost-advice-agent

> Unit: U7 · kind: service · Q1–Q6=A

## ADR-0006

| 面向 | 判定 | 處置 |
|---|---|---|
| IAM | 消費 U5／U4 既有 | 不擴大帳單 API |
| Encryption | 出站 HTTPS（OpenRouter／定價） | 金鑰僅 env |
| Network | 出站；SSE 入站經既有 API | JWT＋U2 授權 |
| Audit | 沿用 U2 事件；本 unit 可加 advice_* 短事件 | 無金額／原文 |

## NFR9.1 — 日誌與錯誤（Q3=A）

例外／log／SSE content **不得**含密鑰值、估價表全文、金額明細全文；可含 set_id、status、短語意碼。unittest 覆蓋。

## NFR9.2 — 授權

SSE／內部寫入前經 `EstimateAccessControl`（BR7.8）。

## NFR7.1 — 可測試性（Q6=A）

本 stage 不手寫 TCMS；unittest＋mock OpenRouter／pricing。

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
