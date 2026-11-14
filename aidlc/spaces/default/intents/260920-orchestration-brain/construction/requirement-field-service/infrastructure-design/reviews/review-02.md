## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元基礎設施面確實零新增，「deploy.yml 不執行遷移」與「欄位收斂不回滾」的論證成立，CI 收斂驗證骨架可行。前次 review-01 的兩項 Major（部署順序表忽略 create_all 路徑、NFR20.16 的 N/A 理由）在已落地的程式與 DEPLOY.md 都已處置（ci.yml 步驟 E 已先刪 system 並斷言 CASCADE；DEPLOY.md 已改寫為「create_all 建出表，只缺 COMMENT，不是 500」），但凍結的 infrastructure-specification.md 與 traceability.json 仍留著舊錯誤文字，與程式矛盾，程式那一邊是對的。其餘為 Minor。兩項 Major 未超過上限，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/requirement-field-service/infrastructure-design/infrastructure-specification.md 第二節「部署順序」表第一列 | 前次 review-01 已提。第一列寫「遷移未跑、表不存在 → 三個端點全部 500」。實際上 BR47.4 新增了 SystemRequirementField ORM 模型（backend/models.py:696），其上刻意不掛 before_create 守門（models.py:687 註解；守門只掛記憶兩表，models.py:967-968），所以 create_all 會在啟動時建出表（只缺 COMMENT）。已落地的 DEPLOY.md:808 正確寫成「不是 500」。設計與落地矛盾，落地那邊是對的。 | 以更正註記或 corrections 檔取代第一列，改為「表由 create_all 建出（無 COMMENT），事後跑遷移補 COMMENT」，使下游不再引用舊文字。 | New |
| R-02 | Major | construction/requirement-field-service/infrastructure-design/traceability.json 的 NFR20.16 列（第 22 行）與 cicd-pipeline.md 第二節步驟 E | 前次 review-01 已提。traceability 仍標 N/A，理由引用 P1–P12 已驗 CASCADE，但 verify_meta_schema.sql 沒有刪 systems 後檢查本表的斷言；cicd-pipeline.md 步驟 E 也仍只寫「依外鍵順序清除」。實際 ci.yml 步驟 E 已改為先 DELETE system 並以 RAISE EXCEPTION 斷言列數為 0（ci.yml 約 489-515 行），落地是對的，凍結的設計文件與追溯表沒有跟上。 | 將 NFR20.16 改為 OK 並指向 ci.yml 步驟 E，同步更正 cicd-pipeline.md 步驟 E 的描述。 | New |
| R-03 | Minor | construction/requirement-field-service/infrastructure-design/cicd-pipeline.md 步驟 C、D | 前次 review-01 已提。「查值仍為 cost」只寫斷言未寫機制。落地的 ci.yml 已用 DO 區塊 RAISE EXCEPTION 並加 ON_ERROR_STOP，設計文件未記載。 | 在設計文件補一句機制說明（DO 區塊加 RAISE EXCEPTION，psql 帶 ON_ERROR_STOP=1）。 | New |
| R-04 | Minor | construction/requirement-field-service/infrastructure-design/cicd-pipeline.md 第二節「不新增 job，理由同該 job 的既有註解」 | 前次 review-01 已提。該既有註解的理由只涵蓋不另建 service container，ci.yml concurrency job 的註解反而記過不往 memory-schema 加 pip install 的取捨。本設計加入 setup-python 與 pip install 卻引用同一註解為據，未如實承認這是對該取捨的有意違反；DATABASE_URL 需為 postgresql+psycopg 形式也未寫明。 | 如實記載為有意違反並說明增量成本，補上 DATABASE_URL 格式。 | New |
| R-05 | Minor | construction/requirement-field-service/infrastructure-design/infrastructure-specification.md 與 cicd-pipeline.md 步驟 B | 前次 review-01 已提。run_meta_schema_migration.py 需要新增欄位級後條件（FORBIDDEN_FKS 以表與被參照表為鍵，表達不了同表一欄無外鍵、另一欄有），但規格未明列為交付項，也未提醒同步 DEPLOY.md 2.2.9 的結束碼清單。落地的 DEPLOY.md:686 已涵蓋，屬文件缺口。 | 在規格明列此腳本修改為交付項。 | New |
| R-06 | Minor | construction/requirement-field-service/infrastructure-design/monitoring-design.md 第三節第 2 項 | 前次 review-01 已提。「以 K4.edit 帳號儲存一次、看到 requirement_field.written」在欄位仍為 integer 時仍會通過（只有代寫標示的寫入失敗），偵測不到本站自己辨識的失敗模式。落地的 DEPLOY.md:751-754 已有 information_schema 型別查證，設計文件未納入。 | 在監控設計補上該 data_type 查證作為確認項。 | New |
| R-07 | Minor | construction/requirement-field-service/infrastructure-design/traceability.json 的 NFR20.17、NFR20.31 列 | 前次 review-01 已提。以「應用層需求」標 N/A，但生產路徑是 PostgreSQL 方言的 on_conflict_do_update，測試走 SQLite，約束名拼錯只會在 staging 首次寫入才發現，N/A 理由未記載此缺口與接受理由。 | 在 N/A 理由記載缺口，或補 tests_pg 案例。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 人工查證 backend/models.py:687-726、967-968 | SystemRequirementField 存在且無 before_create 守門；updated_on_behalf_of 為 String(64) 無外鍵 | 支持 R-01：create_all 會建表，設計的 500 描述不成立 |
| 人工查證 .github/workflows/ci.yml 約 399-515 | 步驟 0、A–E 已落地，步驟 E 先刪 system 並斷言 CASCADE；步驟 D 用 DO 區塊斷言 | 支持 R-02、R-03：落地已修正，凍結設計未更新 |
| 人工查證 DEPLOY.md:686、751、808 | 已更正為 create_all 建表、含 data_type 查證 | 落地文件正確，與凍結設計矛盾 |
| 人工查證 verify_meta_schema.sql P15/P16 | 存在，驗型別與無外鍵 | 欄位收斂有 CI 斷言 |
