# Code Summary — `U20 requirement-field-service`

> 產出時間：2026-10-12T01:45:40Z（`date -u`）。方法論依核可計畫內嵌的 Testing Contract
> （`contract_sha256` `sha256:1f0b6822…f77`）為 **test-after**：資料模型 → 資料存取 → 業務邏輯 →
> API 四層，逐層「實作 → 寫並跑該層測試」。計畫 Step 1–12 全數勾選；計畫與
> `unit-test-instructions.md` 除勾選框外未改任何位元組。

## 一、檔案

### 新建（13）

| 檔案 | 內容 |
|---|---|
| `backend/services/requirement_field_definitions.py` | 兩組七欄常數（`cost` 5 欄、`architecture` 2 欄，標籤取自 `entities.md` 的 `field_definitions_v1`）、`MAX_VALUE_LENGTH=2000`、`INPUT_HINT`；匯入時自我檢查（key 格式、重複、`display_order`） |
| `backend/services/requirement_field_errors.py` | 四個領域例外（皆不繼承 `HTTPException`）；訊息全部來自固定集合，不含值 |
| `backend/services/requirement_field_types.py` | `FilledState`、`FieldView`／`FieldGroupView`／`FieldSetView`、請求本體 `RequirementFieldWriteIn`（`extra="forbid"`、`strict`） |
| `backend/services/requirement_field_service.py` | 資料存取：一次讀取、依方言的單一 upsert ＋ `RETURNING`、條件式清空 `UPDATE … WHERE value IS NOT NULL RETURNING`、no-op 時取現況；時間戳由呼叫端傳入 |
| `backend/services/requirement_field_facade.py` | 唯一授權入口：`BR41`（四步授權）、`BR42`（白名單）、`BR43`（值語意）、`BR44`（三態合成與計數同源）、`BR45`（溯源）、`BR46.2`（交易）；log 事件三種 |
| `backend/services/requirement_field_router.py` | `GET`／`PUT`／`DELETE`；路徑參數全以字串接收、`PUT` 讀原始本體、授權後才由 facade 解析；三路由一致宣告 403／404／422（`RequirementFieldErrorOut`） |
| `backend/scripts/ci/downgrade_requirement_fields.sql` | CI 步驟 A：把欄位改回 `U18` 舊定義（含前置「表為空」與後置「已是舊定義」自我確認） |
| `backend/scripts/ci/seed_requirement_field_fixture.sql` | CI 步驟 C：寫入 user／project／system ＋ 一列 `updated_on_behalf_of='cost'` 並 `COMMIT` |
| `backend/tests/test_requirement_field_data.py` | `D1`–`D5` |
| `backend/tests/test_requirement_field_service.py` | `S1`–`S8`，以及共用的 `QueryCounter` |
| `backend/tests/test_requirement_field_facade.py` | `F1`–`F8`，以及共用的 `RequirementFieldFixture` |
| `backend/tests/test_requirement_field_http.py` | `H1`–`H7` |
| `backend/tests_pg/test_requirement_field_pg.py` | `G1`–`G3`（真實 PostgreSQL） |

### 修改（9，含重新產生 2）

| 檔案 | 變更 |
|---|---|
| `schema_rbac.sql` | `J)` 區塊：`updated_on_behalf_of` 改為 `VARCHAR(64)` 無外鍵；建表後加條件式收斂 `DO` 區塊；該欄 COMMENT 改寫；區塊標頭記下 `OPEN-RF20-8` 的例外 |
| `backend/models.py` | 新增 `SystemRequirementField`（與 DDL 等價，**不掛** `before_create` 守門） |
| `backend/main.py` | 掛 `/api/requirements` |
| `backend/scripts/run_meta_schema_migration.py` | 欄位級後條件三條（`verify_column_postconditions`）、收斂 NOTICE 收集、成功輸出與「不塞任何資料」聲明改寫 |
| `backend/scripts/verify_meta_schema.sql` | `P15`（型別 `character varying(64)`）、`P16`（該欄無外鍵、`updated_by` 外鍵恰 1 條） |
| `.github/workflows/ci.yml` | `memory-schema` job 新增步驟 0／A–E（位置：P1–P12 之後、R1–R10 之前），並寫明這是對 `concurrency` job 註解所述取捨的有意違反與理由 |
| `DEPLOY.md` | 2.2.9：表格欄位說明、結束碼語意補欄位級三條、驗證指令補 `information_schema` 查詢、斷言數 14→16、新增「`U20` 的欄位收斂」小節（收斂行為、部署順序與 `create_all` 的實際行為、上線確認、回滾）；2.2.10 一句補例外說明 |
| `openapi.json` | `dump_openapi.py` 重新產生（+451 行，純新增） |
| `frontend/src/types/api.d.ts` | `npm run gen:types` 重新產生（+288 行，純新增） |

## 二、關鍵決定

1. **授權全在 facade**（`BR41.2`）：`U13` 是同進程呼叫端，router 只掛 `get_current_user`。
2. **本體與 `system_id` 不給框架驗證**：`system_id`／`agent_group`／`field_key` 以字串接收，
   `PUT` 以非同步 dependency 讀原始位元組（handler 仍為同步、跑在 threadpool），facade 授權
   通過後以 `model_validate_json` 解析。因此本 router 沒有任何框架 422；`openapi_extra`
   宣告 `requestBody` 使型別檔仍有本體形狀；`responses` 的 422 以 `RequirementFieldErrorOut`
   覆寫框架預設的 `HTTPValidationError`。`detail` 為固定字串（沿用 `membership_router` 形狀）。
3. **upsert 以欄位物件指定衝突目標**（`index_elements`），不寫約束名稱——約束名拼錯不會只在
   PostgreSQL 才爆（infrastructure-design `review-01` R-07 的同一顧慮）。
4. **清空為單一條件式 `UPDATE`**：從未填過、已清空、第四種列皆得 0 列而自然 no-op。
5. **收斂 `DO` 區塊**：只在 `integer` 時動作；外鍵以 `conkey` 比對；`USING NULL` 並以 NOTICE
   回報清掉筆數（依計畫，未改為 `RAISE EXCEPTION`）；`lock_timeout` 只在轉型期間設為 5s 並還原；
   catalog 查詢皆限定 `public`。
6. **ORM 不掛守門**（`OPEN-ID19-1` 先例）；`DEPLOY.md` 照實寫「表不存在時由 `create_all` 建出、
   只缺 COMMENT」，不寫「500」。

## 三、測試結果（全部實際執行）

| 指令（工作目錄） | 結果 |
|---|---|
| `python3 -m unittest tests.test_membership_data -v`（`backend/`，Step 2 執行器檢查） | 8 tests OK |
| `python3 -m unittest tests.test_requirement_field_data tests.test_requirement_field_service tests.test_requirement_field_facade tests.test_requirement_field_http -v`（`backend/`） | **28 tests OK**（5＋8＋8＋7） |
| `DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/u20_verify python3 -m unittest tests_pg.test_requirement_field_pg -v`（`backend/`） | **3 tests OK**（本機 PostgreSQL，見下） |
| 同上 `python3 -m unittest discover -s tests_pg` | 9 tests OK（含既有 `C1`–`C3`、purge 測試） |
| `python3 scripts/dump_openapi.py --check`（`backend/`） | 「規格檔與後端程式碼一致」 |
| `npm run check:types`（`frontend/`） | 「API 型別檔與規格檔一致」；另 `npx tsc -b` exit 0 |
| `python3 scripts/validate_env_contract.py`、`python3 scripts/validate_repo_contract.py` | 兩者 passed |
| `JWT_SECRET=x python3 -m unittest discover -s tests`（`backend/`，全套） | **770 tests，4 failures**——與變更前基準（742 tests，4 failures）完全相同：皆為 `test_progress_channel_contract` 對本機 `.kilo/worktrees/secret-deposit/...` 的兩個 call site（已知、與本單元無關）。新增 28 個測試全綠，無新失敗 |

**PostgreSQL 的執行範圍，如實記載**：本機有一個 Homebrew PostgreSQL **17.7**（pgvector 0.8.1），
不是 CI 的 `pgvector/pgvector:pg18`。我在其上建立暫用資料庫 `u20_verify`，套用 `schema_rbac.sql`
兩次、跑 `verify_meta_schema.sql`（P1–P16 全過），再把 `ci.yml` 中 U20 步驟 A–E 的 `run:` 文字
以 YAML 解析取出、只把 `-d cloud360` 換成 `-d u20_verify` 後逐步執行，**五步全部 exit 0**
（`NFR20.23`／`NFR20.16` 的 NOTICE 皆出現）。步驟 0（setup-python／pip）只在 CI 有意義，未在本機
執行；本機沒有 `python` 指令，以 scratchpad 的 `python → python3` shim 代替。**CI 上的實跑尚未發生**，
版本差（17 vs 18）下的行為未經驗證。完成後已刪除 `u20_verify`。

## 四、突變驗證（`unit-test-instructions.md §四`，每項：套用 → 確認紅 → 還原 → 確認綠，並以 sha256 確認檔案真的改了、也真的還原了）

| # | 突變 | 結果 |
|---|---|---|
| M1 | 拿掉 per-project 成員判定（`if role is None` → `if False`） | **紅 13 項**：`H1` ②⑩⑫ 各 3 方法、`F7` 的 outsider read／write 與 root write、`F8` |
| M2 | 拿掉全域 `K4` 檢查 | **紅 15 項**：`H1` ③⑤ 的 PUT／DELETE、④⑧ 三方法、⑨、`H2`、`F7` 的 no_k4／viewer／viewer 代寫 |
| M3 | 拿掉待核准檢查 | **紅 5 項**：`H1` ⑥ 三方法、`H2`、`F7` 的 pending（HTTP 與同進程皆紅） |
| M4 | 清空改回「先讀後改」（`clear_if_filled` 先 `fetch_row`、`UPDATE` 去掉 `value IS NOT NULL`） | **`G3` 紅**：「兩個併發清空應恰一個生效，實際 2 個」（本機 PostgreSQL） |
| M5 | 收斂 `DO` 區塊改為無條件轉型（`IS DISTINCT FROM 'integer'` → `IS NULL`） | **CI 步驟 D 紅**（本機實跑）：先由「本次未執行」的 grep 守衛擋下；直接執行步驟 D 的值斷言亦紅：`NFR20.23 FAILED … 實際 <NULL>` |
| M6 | log 改為帶入值（written 事件訊息帶 `value=`） | **`F8` 紅**：`'marker-…' unexpectedly found in 'requirement_field.written value=marker-…'` |
| 附 | 收斂改為 no-op（`IF true THEN RETURN`）後跑 `run_meta_schema_migration.py`（計畫外，驗 `NFR20.25`） | exit 1，列出「應為 character varying(64)，實際 integer」與「不得有外鍵…實際有 1 條」 |

全部還原後：28 個 SQLite 測試 OK、3 個 PostgreSQL 測試 OK、步驟 A–E 全綠。

## 五、NFR 的 grep 型判準（本單元新增的 6 支 `services/requirement_field_*.py`）

`lru_cache|cache` 0、`getLogger(__name__)` 0、`text(`／`execute(f` 0、`require_story_action(` 0、
`TODO|FIXME|HACK|XXX` 0（測試檔亦 0）；對本表的 `DELETE` 在 service／facade 中 0。

## 六、偏離計畫或設計文件之處（逐項附理由）

1. **回應欄位用 snake_case**（`unfilled_count`、`filled_state`…），而 `functional-spec.md` 2.3 以
   camelCase 記名。本 repo 的回應模型一律 snake_case，且 `K-17` 的字面本來就是 `unfilled_count`
   ——這反而讓 `OPEN-RF20-5`／FD `review-02` R-07 的「`unfilled_count` 命名」**不需追認**。
2. **`FieldSetView` 多一欄 `input_hint`**（「請勿填入密碼、金鑰或個人資料」）：`OPEN-RF20-9` 要求
   `U23` 顯示它，依「單一真實來源」由後端隨回應送出。屬 `K-17` 的增量，併入下方追認清單。
3. **log 訊息除 `extra=` 外，也以同一組白名單欄位作為 `%` 參數**：`observability-design.md` 寫
   「欄位以 `extra=` 帶入、不拼進訊息字串」，但後端 log 以 `logging.basicConfig` 的預設格式輸出，
   只帶 `extra` 時 `docker compose logs backend` 看不到任何欄位，`monitoring-design.md` 第三節的
   人工確認就做不到。參數只有整數與封閉集合字串（`agent_group`／`field_key` 取自定義而非輸入），
   「不記值」仍由 `F8` 機械斷言（突變 M6 證實會紅）。
4. **facade 多一個 `write_field_from_body`**（HTTP 用）：計畫要求「授權通過後才由 facade 解析」，
   而 `K-17` 的 `write_field` 簽章是已解析的參數。同進程呼叫端仍用 `write_field`。列入追認清單。
5. **`UnknownFieldKey` 的訊息只在路徑片段符合識別字形狀時才回顯**，否則只寫「未宣告的需求欄位」
   ——比 `BR46.3` 更保守，不改變狀態碼。
6. **CI 步驟 B／D 比計畫多兩道檢查**：B 之後再跑一次 `verify_meta_schema.sql`（讓 P15／P16 面對
   真的經過收斂的資料庫），並以 grep 斷言腳本輸出含「本次**有執行**」；D 以 grep 斷言「本次未執行」。
   目的：讓「步驟 A 沒生效所以 B 其實沒事可做」與「收斂條件失效所以每次都重做」都會紅。
7. **`DEPLOY.md` 2.2.10 也改了一句**（「那一支目前純 DDL」補上 `U20` 例外），避免與 2.2.9 新小節矛盾。
8. `test_requirement_field_http.py` 為 7 個測試方法；十二列矩陣在 `H1` 內以 `subTest` 逐列逐方法
   斷言（共 34 個子案例）。

**未處理而揭露的既存不一致**：`DEPLOY.md` 2.2.9 的「結束碼 0 ⟺ … 7 個索引」與腳本實際的
`EXPECTED_INDEXES`（8 個，含 `U8` 的 HNSW）不符，早於本單元，未改動。

## 七、交接（計畫 §二 末列）

### 契約追認（`OPEN-RF20-5`，下一輪契約修訂，與 `U15` 的 `K-08` 追認同批）

`K-17` 與實作的全部差異：① 回應增量 `title`／`label`／`filled_count`／`total_count`／`input_hint`；
② `system_id` 實為 `int`（HTTP 路徑以字串接收、facade 收斂；`K-17` 寫 `str`）；③ `write_field`
多拋 `RequirementFieldValidationError`；④ `on_behalf_of` 收窄為已宣告的 group_key；⑤ 全域層在
facade——**`K-17` 的 `own_responsibility` 與 `anti_double_check` 兩處字面都寫「由 router 的
require_story_action 承擔」，須一併改寫**（FD `review-02` R-07）；⑥ 使用者空值寫入即清空、代寫
空值被拒；⑦ 新增 `write_field_from_body`。另 **`K-16` 的 `two_facade_layers.anti_double_check`
逐字寫「`U20` 不得重複呼叫 require_story_action（它的 router 已經做了）」，與實作相反**——`U13`／`U21`
的實作者若依字面假設 router 已檢查，會漏掉同進程路徑的全域層。`unfilled_count` 命名因採 snake_case
**已與 `K-17` 一致**，不需追認。

### 已凍結設計檔的揭露（FD `review-02` R-05）

`functional-spec.md` 第九節自檢 5 仍寫「規則數 33」，實數為 **37**（`rules.md` YAML 實算：
6＋5＋7＋6＋5＋4＋4；本站以 regex 解析 `id: BR4x.y` 得 37 並與 `traceability.json` 比對一致）。
依 `refined-mockups:c3` 不回改已核可的設計檔。

### 給 `U21 mcp-bridge` 與 `U13 brain-gateway`

- **代寫路徑一律帶 `on_behalf_of`**：`BR42.5` 只保護有自報代寫身分的呼叫；省略它時，空字串會走
  `BR43.2` 被當成使用者清空，並記成「本人清空」（FD `review-02` R-03）。`U21` 宜在工具 schema 層
  直接拒絕空值或強制帶標示。
- **要清空用 `DELETE`／`clear_field`**，不要以空值 `PUT`。
- **不得繞過 facade 直讀直寫表**（無機械強制，與 `U7`／`U19` 同一殘留）。
- 代寫標示可被自填（`OPEN-RF20-1`），真偽需 `U21` 的 agent 身分機制（`OQ-15`）。

### 給 `U23 project-pages-ui`

- 總覽籤與需求籤讀**同一次** `GET`；儲存或清空成功後**重讀 `GET`**，不得本地加減計數（`OPEN-RF20-3`）。
- 組標題、欄位標籤、`input_hint` 以回應為準，不在前端另抄（`OPEN-RF20-4`／`OPEN-RF20-9`）。
- 錯誤一律 `{"detail": "<固定字串>"}`，只有這一種 422 形狀。
- 同欄位兩人同時編輯為最後寫入者勝（`OPEN-RF20-2`）。

### 部署（ID `review-01` R-06 已落地）

`DEPLOY.md` 2.2.9 的上線確認改為直接查 `information_schema.columns` 的 `data_type`（應為
`character varying`／64）與該欄外鍵數（應為 0），不只看「儲存成功」。合併後須在 staging 手動執行
`cd backend && python scripts/run_meta_schema_migration.py`（`deploy.yml` 不跑遷移）。

## 八、ADR-0006 四面向（逐格對照 `functional-spec.md` 第七節，無一格相反）

| 面向 | 判定 | 本站落點 |
|---|---|---|
| IAM | 適用 | 四步授權在 facade；十二列矩陣 ＋ 三個突變（M1–M3）皆紅 |
| Encryption | 適用（不在本單元） | 不經手 token、無新傳輸路徑 |
| Network exposure | 適用（不在本單元） | 新 router 掛在既有 `/api/` 之下，零新進程、零新埠、零新環境變數 |
| Audit logging | 適用 | 列上的 `updated_by`／`cleared_at`／`updated_on_behalf_of`；拒絕與寫入 log 不含值（`F8`、M6） |

**PBT**：不適用（與上游一致；本單元不屬 IaC generator、cost calculator、agent routing），未使用 `hypothesis`。

## 九、code-generation Request Changes（2026-10-20）重新查驗（2026-10-23）

19 項合併前必修中無一項劃給本單元（計畫 §六），**本輪未改任何程式或測試**。以 `backend/.venv`（釘選版依賴）、`PYTHONDONTWRITEBYTECODE=1` 實際重跑：

| 指令 | 結果 |
|---|---|
| `python -m unittest tests.test_requirement_field_data tests.test_requirement_field_facade tests.test_requirement_field_http tests.test_requirement_field_service` | `Ran 28 tests` — `OK` |
| `python -m unittest discover -s tests`（全套，涵蓋前序單元本輪的修正） | `Ran 1269 tests` — `OK (skipped=3)` |
| `python scripts/dump_openapi.py --check` | 規格檔與後端程式碼一致 |

前序單元本輪的改動（`hierarchy-service` 的待核准檢查、`membership-service` 的改選與鎖等待、`user_router.py` 的刪除前置檢查與系統帳號保護）均未讓本單元任何測試轉紅。Step 1–12 的勾選狀態維持不變，無需重新實作。突變驗證沿用 §四 的結果（程式未變，不重跑）。

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-26T00:13:04Z -->

以既有實作逐步查驗已核可計畫，未修改任何程式碼。

- **計畫勾選**：12／12。
- **測試**（`backend/`，快取導向 scratchpad）：
  - 全套 `unittest discover -s tests`：1319 OK（skipped=3）。
  - 本單元 SQLite 測試 34 OK（data 5、service 8、facade 12、http 9；H1 十二列矩陣）。
  - `tests_pg.test_requirement_field_pg`：3 OK（一次性本機 PostgreSQL 17＋pgvector，用完即刪；未連任何共享資料庫）。
  - 於同一個一次性 PG 依序重現 `memory-schema` job 步驟 0／A–E：`schema_rbac.sql` 套兩次 0 ERROR、verify 通過、遷移首次「有執行」移除 `updated_on_behalf_of` 外鍵、重跑「未執行」、CASCADE 成立。D／E 以 scratchpad 的等價 SQL 斷言，非 `ci.yml` heredoc 本身。
  - `dump_openapi.py --check`、`check:types`、`validate_env_contract.py`、`validate_repo_contract.py`：皆通過。
- **PBT**：不適用（非 ADR-0006 點名模組），測試檔不 import `hypothesis`，與 §八 一致。
- **ADR-0006 四面向**：與 §八 一致，無一格相反。
- **NFR grep 判準**（§五）：6 支 src 全部 0 命中；service／facade 無 DELETE 敘述。
- **與既有文字不符之處（如實記載）**：
  1. 合併前必修清單現為 23 項，第 14 項（`project-pages-ui`，`[PP-MB14]`=A）把本單元三個端點的「非成員」回應由 403 改為與「系統不存在」相同的 404，測試已同步（H1 ②⑩⑫、H8、H9）。計畫 §六「19 項中沒有一項劃給本單元」已過時；不違反計畫 §二（未規定非成員狀態碼）。
  2. `DEPLOY.md` 第 730–732 行稱 U19／U20 查詢會報 `relation "project_members" does not exist`，與 U20 小節（約第 842 行，`create_all` 建表、不是 500）矛盾，疑為 U18 時期舊文字，留 build-and-test 修正。

## 第 24 項處置（合併前必修，計畫 §七 Step 13–17）

<!-- 寫入時間：2026-10-26T22:44:42Z（date -u 取值） -->

來源：`construction/functional-design/merge-blockers.md` 第 24 項；`reviews/review-03.md` R-01（Major）＋ `DEPLOY.md` 矛盾。上一段第 2 點的「留 build-and-test 修正」已由本段處置取代。

### 程式（Step 13）

| 檔案 | 改動 |
|---|---|
| `backend/services/requirement_field_facade.py:374-380` | `_write_authorized` 在型別檢查之後、`strip()` 之前，值含 `\x00` 即拋 `RequirementFieldValidationError("value", "nul_char")`。放在 `strip()` 之前是因為 NUL 不是空白、`strip()` 不會去掉它 |
| `backend/services/requirement_field_errors.py:130-132` | 登錄固定訊息 `("value", "nul_char")`：「value 不得含 NUL 字元（U+0000）」，不回顯值；模組 docstring 的例外對照表（第 15 行）補上此原因 |

router 未改：`RequirementFieldValidationError` 原本就由 `_translate()` 轉 422。

**入口盤點（全部入口都在共同上游擋下）**：值寫進資料庫的路徑只有 `requirement_field_service.upsert_value`，其在 `backend/`（不含測試）唯一的呼叫者是 `_write_authorized`；而 `_write_authorized` 是 `write_field`（同進程，`U13` 代寫）與 `write_field_from_body`（HTTP PUT）的共同上游。本單元**沒有批次寫入**；agent 代填即 `write_field` 帶 `on_behalf_of`，同一條路徑。其他會落入資料表的字串：`on_behalf_of` 已以已宣告組的白名單擋下、`agent_group`／`field_key` 以程式內定義白名單比對、`system_id` 轉整數——三者都不可能帶 NUL 進資料庫。清空（`clear_if_filled`）不寫任何使用者字串。

### 測試（Step 14）

| 案例 | 位置 | 斷言 |
|---|---|---|
| `H10` | `backend/tests/test_requirement_field_http.py:257` | 四種形狀（值中夾 NUL、空白包住的 NUL、單獨一個 NUL、代寫路徑帶 NUL）以 PUT 送出皆 422，本體恰為 `{"detail": <固定訊息>}`、不含 `uuid4()` 唯一標記；同樣四個值以同進程 `write_field` 皆拋 `(value, nul_char)`；最後列數 0 |
| `G4` | `backend/tests_pg/test_requirement_field_pg.py:246` | 真實 PostgreSQL：直接呼叫 PUT 路由函式得 `HTTPException` 422 與固定 `detail`；同進程帶代寫標示得 `(value, nul_char)`；session 未卡在失敗交易；該系統 0 列；再以同一路由寫正常值成功、恰 1 列（排除 422 來自授權或定址失敗） |

兩案皆附規格註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`／`@api`）。

### 突變驗證（Step 15，只在 scratchpad 副本）

以 `rsync` 把 `backend/`（排除 `.venv`、`.hypothesis`、`__pycache__`）複製到 scratchpad，只在副本把 `if "\x00" in value:` 改為 `if False:`，以工作樹的 `.venv` 直譯器在副本目錄執行兩案：

| 突變 | 結果 |
|---|---|
| 拿掉 NUL 檢查 | **紅**：`H10` 9 個失敗（四個 PUT 子案 `200 != 422`——SQLite 接受 NUL 並寫入；四個同進程子案 `RequirementFieldValidationError not raised`；列數 `1 != 0`）；`G4` 為 ERROR：`sqlalchemy.exc.DataError: (psycopg.DataError) PostgreSQL text fields cannot contain NUL (0x00) bytes`——即 R-01 描述的 500 成因在真實 PostgreSQL 上重現 |
| 還原 | 副本兩案 `Ran 2 tests — OK`；`diff -q` 確認副本 facade 與工作樹逐位元相同 |

工作樹從未被改壞；副本與一次性資料庫用完即刪。

### 文件（Step 16）

`DEPLOY.md:730-738`（原第 730–732 行那一段）改為與 2.2.9 的 U20 部署順序表一致：忘了跑遷移**不會**沒有表——`create_all()` 依 ORM（`ProjectMember`、`ReselectionEvent`、`SystemRequirementField`）建出三張表，約束與 DDL 等價、只缺 COMMENT（`OPEN-ID19-1`），不是 500；表若以舊定義存在則缺的是 `U20` 的欄位收斂，只在帶代寫標示的寫入時以 500 出現。只改該段，其餘未動。

### 回歸（Step 17，全部實際執行，`backend/.venv` Python 3.13.7）

| 指令 | 結果 |
|---|---|
| 本單元 SQLite：`unittest tests.test_requirement_field_data tests.test_requirement_field_service tests.test_requirement_field_facade tests.test_requirement_field_http` | `Ran 35 tests` — `OK`（上輪 34 ＋ `H10`） |
| 全套 `unittest discover -s tests`（`JWT_SECRET` 為測試用假值） | `Ran 1322 tests` — `OK (skipped=3)` |
| `unittest discover -s tests_pg`（一次性 PostgreSQL 17＋pgvector，`initdb` 於 scratchpad、`listen_addresses=127.0.0.1`、`unix_socket_directories=''`、高埠，套 `schema_rbac.sql`；用完 `pg_ctl stop` 並刪資料夾） | `Ran 14 tests` — `OK`（其中本單元 `G1`–`G4` 4 個；修改前基準為 13） |
| `python scripts/dump_openapi.py --check` | 規格檔與後端程式碼一致 |
| `npm run check:types`（frontend） | API 型別檔與規格檔一致 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |

未連 staging 或任何共用 DB／Redis；未觸發 CI／workflow；未 commit。

### 追溯與其他

- `traceability.json`：逐列檢查後**沒有**因本項變為不實的註記（各列描述的是既有 422／500 行為與 H5 的四類，修正後仍成立），依「只更正不實註記」不改動。
- `source-manifest.json`：本項未新增檔案，改動的五支檔（facade、errors、兩支測試、`DEPLOY.md`）皆已在清單內，不改動。
- **已知未處理（Minor，如實記載）**：router `ERROR_RESPONSES` 的 422 說明文字列舉了各種原因，未列「值含 NUL」。補上會改動 `openapi.json` 與 `frontend/src/types/api.d.ts`，超出 Step 13「router 照既有轉譯」的範圍，故未改。
