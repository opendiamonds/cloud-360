# NFR Design — 釐清問題（cost-schema-rbac）

> Stage: nfr-design（3.3）· Unit: `cost-schema-rbac` · kind: **spec**  
> 上游：`../nfr-requirements/security-requirements.md`、`../functional-design/business-rules.md`。

## 已由上游定案、不重問

| 事項 | 來源 |
|---|---|
| 四表 DDL + 44 列 C1* 種子 | FD BR-S-* |
| `ensure_missing_role_permissions()` 只 INSERT | SEC-S-1 |
| brownfield 禁止 DELETE 全表 | SEC-S-1、high-risk rollback |
| 無 logical-components（spec kind） | `produces_kinds` |

---

## Q1. IAM 變更的 human approval 落點？

A. **併入 B1 Bolt squash-merge gate**；PR 描述含 plan／impact／rollback 摘要。**（建議，對齊 team.md skeleton off）**  
B. 獨立 ADR 後才可 merge。代價：與 delivery-planning 脫節。  
C. Not yet defined  

[Answer]: A. **B1 merge gate**

---

## Q2. 稽核表由誰寫入？

A. **`cost-api` `record_audit()` 唯一寫入路徑**；本 unit 只交付表契約。**（建議）**  
B. DB trigger 自動 audit。代價：與 FD 不符。  
C. Not yet defined  

[Answer]: A. **service 層寫入**

---

## Plan Approval

- [x] 計畫已核可（Q1–Q2=A）
