# Code Summary — estimate-intake-api（U2）

> Unit: `estimate-intake-api` · kind: **service**  
> 計畫：同目錄 `code-generation-plan.md`（6 步，全數完成）  
> Plan Approval：`Approve Plan`（fingerprint `sha256:8e8a9b50…0336`）

## 變更檔案

| 檔案 | 變更 | 對應 |
|---|---|---|
| `backend/models.py` | EstimateSet／Estimate／LineItem／Share／Audit／Advice ORM | Step 1 |
| `backend/database.py` | `_ensure_estimate_intake_schema()` | Step 1 |
| `schema_rbac.sql` | 新表 DDL；C1 seed；移除 C1h／C1r／C1o／C1b | Step 1–2 |
| `DEPLOY.md` | 表對照 2.2.5 | Step 1 |
| `backend/cost/estimate_access.py` | owner＋share；不查 collab | Step 2 |
| `backend/services/rbac_seed_data.py` | C1 語意＋edit 合併；刪 C1h～C1b | Step 2 |
| `backend/cost/estimate_intake_service.py` | 驗證／parse／持久化／checks 重算／enqueue | Step 3–5 |
| `backend/cost/estimate_audit.py` | 事件稽核（無金額／原文） | Step 5 |
| `backend/cost/estimate_intake_router.py` | C2 paths | Step 4 |
| `backend/main.py` | 掛載 `/api/cost/v1` | Step 4 |
| `backend/tests/test_estimate_intake_api.py` | 11 個 TestClient／seed 案 | Step 6 |
| `openapi.json`／`frontend/src/types/api.d.ts` | 重產 | Step 6 |
| `user_router`／`RolePermissionsPage` | C1 標籤；移除 C1h～C1b UI 文案 | Step 2 |

**未變更（刻意）**：`CostPage.tsx`（U8）、建議正文／SSE（U7）、查價（U5）、TCMS 手寫。

## 關鍵實作決定

1. **授權**：可見性＝擁有者 ∪ `estimate_shares`；`diagram_id` 純標籤。
2. **C1.edit**：原 C1h／C1r／C1o／C1b 的 edit 角色併入 C1（Architect／Editor／Admin／FinOps）。
3. **enqueue**：同 request 呼叫 `enqueue_advice_job` hook（U7 可替換）；失敗→Advice=`failed`＋`advice_enqueue_failed` audit；仍 201。
4. **機械檢查**：每次 Detail 以 U1 `validate` 重算，不落庫。
5. **錯誤 detail**：固定短語（`invalid file type`／`file too large`／`cloud ambiguous; provide cloud_overrides` 等）。

## 測試

| 指令 | 結果 |
|---|---|
| `cd backend && PYTHONPATH=. python3 -m unittest tests.test_estimate_intake_api -v` | 11 OK |
| `python3 scripts/dump_openapi.py --check` | 一致 |
| `npm run check:types`（frontend） | 一致 |
| `python3 scripts/validate_repo_contract.py` | exit 0 |
| `python3 scripts/validate_env_contract.py` | exit 0 |

## 與計畫的偏離

- Enqueue 採**同 request 同步呼叫 hook**（非 FastAPI `BackgroundTasks`），因 hook 本身不跑建議正文，且可與 TestClient 共用 in-memory DB；符合 BR2.8「同生命週期 enqueue、不跑完整建議」。
- list 另加 `page`／`page_size`（≤50）以滿足 NFR Q4；契約既有 `include_history` 保留。

## 不做（交其他 unit）

SPA／CostPage（U8）、SSE／建議正文（U7）、查價強化（U5）、TCMS 手寫。

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-19
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|


### Summary

estimate-intake-api code-generation READY。C2 路徑、ORM／DDL 雙軌、C1 seed、TestClient allow／deny、OpenAPI 已落地；範圍排除 SPA／SSE。
