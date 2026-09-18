# A3 NFR Requirements — Well-Architected Review

> Unit `U-A3` · Decisions: `construction/plans/a3-nfr-requirements-plan.md`


### 1. 決策摘要

| Q | 決策 |
|---|---|
| 1 | 規則階段 **p95 ≤ 5s**（不含 LLM） |
| 2 | Agent 建議 **60s** timeout；**不限制**同使用者並行評核數 |
| 3 | JWT＋A3 RBAC＋**結構化 audit**（無 XML／建議全文） |
| 4 | **Best-effort** 可用性；SSE 可因重啟中斷 |
| 5 | PBT：**規則引擎核心** ≥3 條 Hypothesis 性質 |
| 6 | 結構化 log；metrics 計數**有則做、無則延後**（以 log 為準） |
| 7 | **完全沿用**現有 tech stack；無新基礎設施 |
| 8 | UX 與 Workspace 同等；無 WCAG 正式驗收 |

### 2. 需求表

| ID | 類別 | 需求 | 驗收要點 |
|---|---|---|---|
| NFR-A3-01 | Security | JWT；A3 view／edit；Pending 拒絕；完整 XML／建議全文不進公開 log | 手動／UT authz；log 抽樣 |
| NFR-A3-01a | Security／Audit | 發起／讀取／重試建議寫結構化 audit：`user_id`, `review_id`, `diagram_id`, `action` | log 欄位存在且無敏感全文 |
| NFR-A3-02 | Testability | `WaRuleEngine` deterministic；Hypothesis ≥3（加權分數、扣分、同 XML 不變性） | CI unittest |
| NFR-A3-03 | Reliability | 規則與 LLM 失敗分離；`rules_only`＋重試建議 | FD 流程＋UT |
| NFR-A3-04 | Performance | 規則 `evaluate` **p95 ≤ 5s**（中大型示範 XML）；Agent **60s** 逾時 → rules_only | 基準／手動計時＋逾時測 |
| NFR-A3-04a | Performance | 同使用者可多評核並行（無 409 併發閘）；仍受進程資源限制 | 文件化；不強制壓測 |
| NFR-A3-05 | Docs | 本 unit aidlc-docs 雙語 | validate_repo_contract |
| NFR-A3-06 | Availability | Best-effort；無獨立 HA／佇列；客戶端可重開詳情／重試 | 手動：中斷 SSE 後 GET 仍可读已存結果 |
| NFR-A3-07 | Observability | 結構化 log：`review_id`、status 轉換、規則／Agent 耗時、錯誤碼；成功／rules_only／unsupported **計數**若現有 metrics 管線存在，否則僅 log | Code review |
| NFR-A3-08 | Usability | Assessment 載入／空／錯誤文案與現有產品語氣一致；無正式 a11y audit | 手動走查 |
| NFR-A3-09 | Maintainability | 規則包版本欄 `rule_pack_version`；權重快照入 scores_json | schema／UT |

### 3. Extension 對齊

| Extension | 狀態 |
|---|---|
| security/baseline | compliant（JWT、RBAC、audit 最小集、禁敏感 log） |
| property-based | compliant（規則核心 ≥3 性質） |
| bilingual-docs | compliant |
| resiliency | N/A（未啟用；採 best-effort） |

### 4. 明確不做（本期）

- 背景佇列／Redis worker  
- 正式 99% SLO／外部 APM 強制  
- WCAG 2.1 AA 驗收  
- 同使用者評核併發上限  
