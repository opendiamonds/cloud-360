## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

本單元的基礎設施面確實零新增，「deploy.yml 不執行任何遷移」屬實（deploy.yml、deploy/ 腳本與 backend/Dockerfile 對 migration、scripts/、psql 皆零命中），「不回滾欄位收斂」的論證也成立（U18 時期程式沒有任何寫入該欄的路徑）。但有兩項 Major：部署順序表第一列忽略本單元自己（BR47.4）引入的 create_all 第二條建表路徑，因而描述了一個不會發生的失敗；NFR20.16 的 N/A 理由引用了 P1–P14 實際不含的斷言。兩者都是文件與 repo 事實不符、修正成本低，故判 READY（兩項 Major 未超過上限），但應在核可前處置。CI 步驟 0/A–E 大體可行（database.py 預設 DATABASE_URL 與 service container 一致、腳本自行處理 sys.path、fixture 清除順序與外鍵相容）。

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | infrastructure-specification.md 第二節「部署順序」表第一列（U18 與 U20 同批上線、遷移未跑，表不存在，三個端點全部 500） | 此列忽略 BR47.4（functional-design/rules.md:444-450）要求本單元新增 SystemRequirementField ORM 模型。models.py 的 before_create 守門只掛在 memory 兩表（models.py:893-894），ProjectMember 與 ReselectionEvent 沒有；models.py 自己的註解（約 :520-541）與 test_membership_data.py 都明寫「create_all 是第二條建表路徑，在沒跑過遷移的既有資料庫上，後端啟動的 create_all 會先建出表」。所以 U20 上線後，表不存在時不是 500，而是啟動時被 create_all 靜默建出（無 COMMENT、約束僅以 ORM 為準）；之後遷移腳本的 CREATE TABLE IF NOT EXISTS 整段 no-op，只有 J) 區塊中無條件的 COMMENT ON 與條件式 DO 區塊會補上差異。規格寫的是不會發生的 500，而同樣的描述也會被抄進 DEPLOY.md 2.2.9。第二列（欄位為 integer 時只有帶代寫標示的寫入失敗）我推演後成立。建議處置：改寫第一列為「表不存在，後端啟動時由 ORM 建出（無 COMMENT），事後跑遷移腳本收斂」，並要求 ORM／DDL 一致性測試涵蓋 updated_on_behalf_of 的型別與無外鍵，否則 ORM 建出的表在這一欄可能與 schema_rbac.sql 不同。 | New |
| R-02 | Major | traceability.json 的 NFR20.16 列（N/A：CASCADE 已由 memory-schema 的 P1–P12 在真實 PostgreSQL 驗證） | 與 repo 不符。verify_meta_schema.sql 沒有任何斷言刪除 systems 列後檢查 system_requirement_fields 列數：P4 與 P7 刪的是 projects（驗 project_members 的 CASCADE 與 reselection_events 的存活），P9–P11 對該表只做 INSERT 與約束檢查，fixture 的 sid 隨 ROLLBACK 消失而從未被刪除。目前唯一碰到這條外鍵的是 run_meta_schema_migration.py 的 EXPECTED_FK_DELETE_ACTIONS（只驗 confdeltype 為 c 的結構），而 NFR20.16 的驗收寫的是行為（系統刪除後該系統的列數為 0）。cicd-pipeline.md 步驟 E 反而先刪 requirement field 再刪 system，把可順手驗證級聯的機會清掉。建議處置：把 NFR20.16 改為 OK，落點為步驟 E——先對 fixture 的 system 執行 DELETE，斷言其 requirement field 列數為 0（以 DO 區塊 RAISE EXCEPTION 讓斷言能令步驟失敗），之後才清 project 與 user。 | New |
| R-03 | Minor | cicd-pipeline.md 第二節步驟 C 與步驟 D | 「查該列的值仍為 cost」只寫了斷言，沒寫機制。psql 執行 SELECT 的結束碼恆為 0，不會令步驟紅燈，需用 DO 區塊加 RAISE EXCEPTION，或 psql -tA 取值後在 shell 比對。步驟 C 的 fixture 檔也應指定 -v ON_ERROR_STOP=1（同 ci.yml 既有 psql 步驟），否則 INSERT 失敗後仍會繼續。 | New |
| R-04 | Minor | cicd-pipeline.md 第二節「不新增 job，理由同該 job 的既有註解」 | 既有註解的理由只涵蓋「不另建第二座 service container」。但 ci.yml 的 concurrency job 註解（約 :417-422）明寫過相反的取捨：不擴充 memory-schema 的原因之一正是「把 pip install 加進去是串行地拖慢它」。本設計在 memory-schema 加入 setup-python 與 pip install，卻引用同一註解為據。結論可接受（增量約一分鐘、仍是訊號而非閘門），但應如實寫成對該取捨的有意違反與理由；並補上 DATABASE_URL 需為 postgresql+psycopg:// 形式（database.py 預設值剛好相符，但文件只寫「指向 service container」）。 | New |
| R-05 | Minor | cicd-pipeline.md 步驟 B 與 monitoring-design.md 第三節第 1 項 | nfr-design 已點明 FORBIDDEN_FKS 以（表、被參照表）為鍵，無法表達「updated_on_behalf_of 無外鍵但 updated_by 有」，所以必須修改 run_meta_schema_migration.py 新增欄位級檢查。本站規格沒有把它列為必改項，也沒提醒需同步更新該腳本的成功輸出與 DEPLOY.md 2.2.9「結束碼 0 等於…」那句清單（目前只在監控文件以「輸出包含此欄的型別檢查通過」暗示）。建議在規格中明列為 code-generation 的交付項。 | New |
| R-06 | Minor | monitoring-design.md 第三節第 2 項（以 K4.edit 帳號儲存一次，看到 requirement_field.written） | 此檢查無法偵測本站自己辨識的失敗模式：欄位仍為 integer 時，只有帶代寫標示的寫入失敗，使用者自填寫入完全正常，所以第 2 項會在失敗狀態下通過。真正能偵測的只有第 1 項（遷移結束碼），且依賴人工記得執行。建議補一條直接查證：查 information_schema.columns 中 system_requirement_fields.updated_on_behalf_of 的 data_type，預期 character varying。 | New |
| R-07 | Minor | traceability.json 的 NFR20.17 與 NFR20.31 列（N/A：應用層需求） | 這兩項的生產路徑是 PostgreSQL 方言的 on_conflict_do_update，nfr-requirements 自己寫明測試走 SQLite、正式為 PostgreSQL、由不同方言建構式產生，而 NFR20.17 的驗收案例也只在 SQLite 執行。結果是生產用的建構式（含它引用的約束名 uq_system_requirement_fields_group_key）在任何 CI 中從未執行，拼錯約束名只會在 staging 首次寫入時才發現。repo 已有針對 SQLite 盲區的 tests_pg 與 concurrency job。建議在 N/A 理由中如實記載此缺口與接受理由，或補一個 tests_pg 案例。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 人工查證：deploy.yml、deploy/ 腳本、backend/Dockerfile 對 migration、scripts/、psql、alembic 的搜尋 | 零命中 | 「deploy.yml 不執行遷移」成立 |
| 人工查證：models.py 的 before_create 守門與 SystemRequirementField 模型 | 守門只掛 memory 兩表；本表模型尚未存在（BR47.4 將新增） | 支持 R-01 |
| 人工查證：verify_meta_schema.sql 的 P1–P14 | 無刪除 systems 後檢查 system_requirement_fields 的斷言 | 支持 R-02 |
| 人工查證：run_meta_schema_migration.py 的 import 路徑與依賴 | 自行處理 sys.path；預設 DATABASE_URL 與 CI service container 相符 | 步驟 0、B、D 可行 |
| 人工查證：fixture 清除順序（field、system、project、user）對外鍵 | 與 projects.owner_user_id 無 ON DELETE、systems.project_id RESTRICT 相容 | 步驟 E 順序可行 |

### Summary

資源零新增與「不回滾欄位收斂」的結論可信，CI 收斂驗證的骨架可行；需修正的是部署順序表第一列（忽略 ORM create_all 這條由本單元自己引入的建表路徑）與 NFR20.16 的 N/A 理由（所引用的斷言不存在），其餘 Minor 可在 code-generation 一併收斂。
