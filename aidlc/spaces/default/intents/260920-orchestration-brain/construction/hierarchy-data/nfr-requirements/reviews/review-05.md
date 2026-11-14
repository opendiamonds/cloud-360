## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站產出（security-requirements.md、tech-stack-decisions.md、traceability.json）自洽度高，ADR-0006 四面向皆有逐項判定。但前次 review-04 的三項 Major 仍留在凍結產出裡：驗證計畫 U4-V1 至 U4-V6 沒有 CI 承載者且殘餘風險表未列、U4-R1 仍指向不含 90 天內容的 rules.md、部署與上游引用行號失效。已落地的 ci.yml 與 deploy.yml 與設計主張不一致。三項 Major 超過門檻，判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/hierarchy-data/nfr-requirements/security-requirements.md > 六 殘餘風險表；三 U4-V1 至 U4-V6 | 前次 review-04 R-01 已提，仍未處置。U4-V1 預設「NFR6 已要求的那個真實 PostgreSQL CI job」存在。HEAD 的 .github/workflows/ci.yml:340 確有 pgvector service，job 名為 Memory schema (real PostgreSQL)，但 ci.yml 對 hierarchy 與 run_hierarchy_migration 的命中為 0，.github 下無任何呼叫 scripts/run_hierarchy_migration.py 的步驟（僅 DEPLOY.md:348、:408 出現）。ci.yml:399 以下的遷移步驟屬 U20 的 run_meta_schema_migration.py。U4-V2 前置狀態、V3 不變量查詢、V5 重跑斷言、V6 靜止窗口因此全無承載者；殘餘風險表五列都不是這一項，表讀起來是完整的。程式落地的一邊是對的：job 存在但範圍未含 U4。 | 在六增列殘餘風險：U4-V1 至 U4-V6 目前零承載者，唯一承接是 S-6，並連到 S-6 的 skip 風險；或把三的措辭改為「S-6 落地後該 job 才涵蓋 U4」。 | New |
| R-02 | Major | security-requirements.md > 二 U4-R1 的「可驗證方式」欄 | 前次 review-04 R-02 已提，仍未處置。該欄寫「規則本身寫在本檔與 rules.md 的消費端義務」，但 functional-design 的 rules.md 不含 90 天保存規則（90 天是本站 Q3=A 才定案，順序在 functional-design 之後），交叉引用從寫下當天就指向空內容。U4-R1 另一半驗證又落在未定案的 S-5，整條需求無可驗證落點。 | 刪掉「與 rules.md 的消費端義務」，或改為對 functional-design 的具名回補義務並登錄進四回補表與 traceability.json。 | New |
| R-03 | Major | security-requirements.md:145、:170 與 S-9 列（引用 deploy.yml:121–124、:126、:451）；tech-stack-decisions.md:66；tech-stack-decisions.md:36（stories.md:451）；traceability.json 對應列 | 前次 review-04 R-03 已提，僅部分處置。requirements.md:523 與 stories.md:432 已改對。仍失效：(1) 產出引用 deploy.yml:121–124 為單一 up -d --build，實際在 deploy.yml:129；:126、:451 的引用同樣漂移，S-9 與 U4-V6 的核心論據依賴這些行號。(2) tech-stack-decisions.md:36 引用 stories.md:451，實際「遷移的歸屬規則與回復方式」在 stories.md:450。事實本身仍成立（單一 up -d --build 一次拉起整座 stack），只有定位錯。 | 以現行行號重核所有 deploy.yml 與 stories.md 引用，或改為不帶行號的步驟名與 AC 編號定位，使其不再隨上游修訂失效。 | New |
| R-04 | Minor | security-requirements.md > 二 U4-R1、U4-R3 | 前次 review-04 R-08 已提。全檔 created_at 命中為 0，未指名 90 天截止欄位；schema_rbac.sql 與 DEPLOY.md 已以 U4-R1 為權威寫成 created_at 為截止欄位並建索引 ix_diagram_change_records_created_at。已落地的部署資產引用了本站沒說的事。 | 在 U4-R1 明寫截止欄位為 created_at 並指名該索引。 | New |
| R-05 | Minor | tech-stack-decisions.md > D-7；backend/tests/test_hierarchy_migration.py:27 | 前次 review-04 R-10 已提。D-7 已否決「calculation 為 0 故無 property」之理由，但測試檔 docstring 第 27 行仍帶該被否決推理。結論（PBT 對本單元不適用）一致，故非正確性缺陷；落地程式的這一邊是舊的。 | 在 D-7 登錄此落差，由後續維護同步 docstring。 | New |
| R-06 | Minor | security-requirements.md > 四 回補表結尾句；tech-stack-decisions.md > 四 結尾句 | 前次 review-04 R-05 已提。計數句（「五項」與表列數、「三項」補入說法）曾與表內不一致，未逐項複驗全部衍生計數；建議以腳本重算 S-5 至 S-9 列數與敘述一致。 | 重算並同步所有被計數實體的敘述。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep ci.yml 對 hierarchy 與 migration | 無 U4 相關步驟；有 pgvector service（:340）與 U20 遷移步驟 | 確認 R-01：U4 驗證無 CI 承載者 |
| grep deploy.yml 對 up -d | 命中 :129，非 :121–124 | 確認 R-03 的行號漂移 |
| grep created_at 於 security-requirements.md | 0 | 確認 R-04 |
| 欄位 pipe 檢查 | 每列 7 個未跳脫 pipe | 格式合規 |
