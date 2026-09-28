# Code Summary — cost-schema-rbac

## 實際產出

| 檔案 | 變更 |
|---|---|
| `backend/models.py` | 新增 C1 四表 ORM |
| `backend/database.py` | `_ensure_cost_schema()`；seed 後 `ensure_missing_role_permissions()` |
| `backend/services/rbac.py` | `ensure_missing_role_permissions()` |
| `backend/services/rbac_seed_data.py` | C1 權限種子 |
| `schema_rbac.sql` | C1 表 DDL + role_permissions 44 列 |
| `DEPLOY.md` | §2.2.4 C1 說明 |

## 關鍵決定

- **ensure_missing 只 INSERT**：既有環境升級不覆寫人工調整過的權限列。
- **啟動順序**：DDL → 通用 seed → C1 RBAC 補丁，避免 FinOps 角色在舊 DB 缺列。

## 驗證結果

| 項目 | 結果 |
|---|---|
| `python3 -m unittest discover -s tests` | **223/223 OK**（含 cost-api RBAC 斷言） |
| test stack `init_db` | C1 表與 352 列 role_permissions 可啟動 |

## Review

**Verdict:** READY  
**Reviewer:** aidlc-architecture-reviewer-agent  
**Date:** 2026-08-20T02:30:00Z  
**Iteration:** 1

### 摘要

B1 schema 與 RBAC 種子已落地，啟動補丁路徑與 DEPLOY 文件同步。無 Critical／Major。
