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

## 共用檔異動後重新驗證（計畫 §八）

<!-- 寫入時間：2026-10-29T15:42:57Z（date -u 取值） -->

來源：整站送審被擋（`REQUIRED_SOURCE_WORK_MISSING`）。本節不改任何程式或測試。

### Step 18 — 自 review-04 以來的變動（逐檔）

**比對基準**：`reviewed-source-90c2466fff25.tsv`（mtime 2026-10-27T06:50:38+0800，為 review-04〔2026-10-27T07:10:04+0800〕之前最後一份收據，22 檔）。逐檔以 `shasum -a 256` 比對工作樹現況，並以 `git show HEAD:<path>` 確認工作樹相對 HEAD 無未提交變動。review-04 之後的兩個 commit：`7a50a40`（2026-10-27T07:58:35+0800）觸及清單內 12 檔，其中 11 檔的內容與收據逐位元相同（即 review-04 當時的未提交工作樹被原樣提交）；`c6a40f9` 未觸及任何清單內檔案。

| 檔案 | 與 review-04 收據 | 相對 HEAD |
|---|---|---|
| `.github/workflows/ci.yml` | 相同 | 無變動 |
| `DEPLOY.md` | **不同**（見下） | 無變動 |
| `backend/main.py` | 相同 | 無變動 |
| `backend/models.py` | 相同 | 無變動 |
| `backend/scripts/ci/downgrade_requirement_fields.sql` | 相同 | 無變動 |
| `backend/scripts/ci/seed_requirement_field_fixture.sql` | 相同 | 無變動 |
| `backend/scripts/run_meta_schema_migration.py` | 相同 | 無變動 |
| `backend/scripts/verify_meta_schema.sql` | 相同 | 無變動 |
| `backend/services/requirement_field_definitions.py` | 相同 | 無變動 |
| `backend/services/requirement_field_errors.py` | 相同 | 無變動 |
| `backend/services/requirement_field_facade.py` | 相同 | 無變動 |
| `backend/services/requirement_field_router.py` | 相同 | 無變動 |
| `backend/services/requirement_field_service.py` | 相同 | 無變動 |
| `backend/services/requirement_field_types.py` | 相同 | 無變動 |
| `backend/tests/test_requirement_field_data.py` | 相同 | 無變動 |
| `backend/tests/test_requirement_field_facade.py` | 相同 | 無變動 |
| `backend/tests/test_requirement_field_http.py` | 相同 | 無變動 |
| `backend/tests/test_requirement_field_service.py` | 相同 | 無變動 |
| `backend/tests_pg/test_requirement_field_pg.py` | 相同 | 無變動 |
| `frontend/src/types/api.d.ts` | 相同 | 無變動 |
| `openapi.json` | 相同 | 無變動 |
| `schema_rbac.sql` | 相同 | 無變動 |

**`DEPLOY.md` 的差異內容**：review-04 當時的版本從未單獨提交（`7a50a40` 把本單元 Step 16 與第 26 項的改寫一併提交），故以重建驗證：取現行 `DEPLOY.md`，只反向套用 `git diff -U0 624c170 7a50a40 -- DEPLOY.md` 中位於 §5.13 的兩個 hunk（現行第 2229 行「…`rollback` 還原 last-good、交 Deploy Doctor，**但不開 revert PR**…」、第 2239 行「…自動流程只還原 last-good（不開 revert PR）…」），所得檔案的 sha256 為 `27898f427f650c669ca984f4bf7faf50c3a3bd86b1e2509281cf159cdae23406`，**與收據逐位元相同**。因此自 review-04 以來 `DEPLOY.md` 的全部差異恰為合併前必修第 26 項（`entry-page-ui`）對 §5.13（`#### 5.13 入口頁部署後實測`，第 2223 行起）的這兩行改寫；本單元的 2.2.9（第 617 行起）、第 730–738 行的 U20 說明與第 791 行起的驗證指令皆未被觸及。

**結論**：本單元程式碼、測試、schema、CI、OpenAPI／型別檔自 review-04 以來零變動；唯一變動是第 26 項對 `DEPLOY.md` §5.13 的兩行改寫，未觸及本單元段落。

### Step 19 — 回歸（在 scratchpad 副本執行，工作樹未產生任何快取）

以 `rsync` 把 `backend/`（排除 `.venv`、`.hypothesis`、`__pycache__`）、`scripts/`、`schema_rbac.sql`、`openapi.json`、`frontend/src/types/api.d.ts` 複製到 scratchpad，以工作樹的 `backend/.venv`（Python 3.13.7）在副本執行，設 `PYTHONDONTWRITEBYTECODE=1` 並加 `-B`；用完即刪副本。兩支 contract 驗證腳本不寫檔，在工作樹以 `PYTHONDONTWRITEBYTECODE=1 python3 -B` 執行，前後比對 `scripts/` 下的 `__pycache__`／`.pyc` 與 ignored 檔清單，無變化。

| 指令 | 結果 |
|---|---|
| 本單元 SQLite：`unittest tests.test_requirement_field_data tests.test_requirement_field_service tests.test_requirement_field_facade tests.test_requirement_field_http` | `Ran 35 tests` — `OK`（與第 24 項處置後相同） |
| `python scripts/dump_openapi.py --check`（副本） | 規格檔與後端程式碼一致 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |

本輪未重跑：`tests_pg`（程式未變，沿用第 24 項處置段的 `Ran 14 tests — OK`）、`npm run check:types`（`openapi.json` 與 `api.d.ts` 與收據逐位元相同，沿用前次結果）、突變驗證（程式未變）。未連 staging 或任何共用 DB／Redis；未觸發 CI；未 commit。

## 合併前必修共用檔修正後的回歸驗證（計畫 §九，2026-11-07T23:55:00Z）

本輪**未改任何程式或測試**。本單元在 `merge-blockers.md` 的唯一一列（第 24 列）已修正，本輪 Request Changes 指定的列無一劃給本單元。

### Step 20 — 共用檔重驗

**比對基準**：`reviewed-source-939a1074e36d.tsv`（mtime 2026-10-29T23:49:58+0800，review-05〔23:56:25+0800〕之前最後一份收據，22 檔）。註：收據放在本單元 `code-generation/` 目錄，不在 `.aidlc-engine/`。以 `sha256` 逐檔比對工作樹，並另比對 `git show HEAD:<path>`：**22 檔在 HEAD 全部與收據相同**，故本輪的差異全部是工作樹相對 HEAD 的未提交改動，以 `git diff HEAD -- <path>` 讀取。

| 檔案 | 與收據 | 改動內容（他單元） | 是否碰到本單元 |
|---|---|---|---|
| 本單元 `requirement_field_*.py` 六支、四支 `tests/test_requirement_field_*.py`、`tests_pg/test_requirement_field_pg.py`、`main.py`、`models.py`、`scripts/ci/` 兩支 SQL | 相同（15 檔） | 無 | — |
| `schema_rbac.sql` | 不同 | 檔頭清單加 `I)` 說明；`I)` 區塊新增記憶專用角色 `cloud360_memory`（第 592–612 行）；`J)` 區塊開頭加純註解（第 642–652 行，第 31 列 (c)(g)） | **否**。`system_requirement_fields` 的 DDL（第 752–764 行起）與其後的條件式收斂 `DO $$` 區塊無任何 hunk |
| `backend/scripts/run_meta_schema_migration.py` | 不同 | `EXPECTED_FK_DELETE_ACTIONS` 改以欄位為鍵並列滿 `J)` 的 7 條外鍵；新增 `cloud360_memory` 後條件 | **碰到但相容**：新增的 `("public","system_requirement_fields","updated_by","users","a")` 與 DDL 第 760 行 `updated_by INTEGER NOT NULL REFERENCES users (id)`（無 `ON DELETE` → NO ACTION）一致；`system_id` CASCADE 仍在。本單元的三條欄位級後條件未動。本機實跑見 Step 21 |
| `backend/scripts/verify_meta_schema.sql` | 不同 | 新增 `P17`：`system_requirement_fields` 恰為 9 欄 | **碰到但相容**：9 欄與 DDL 及 `DEPLOY.md` 第 686 行一致；`P15`／`P16` 未動。本機實跑通過 |
| `.github/workflows/ci.yml` | 不同 | 新增記憶角色邊界步驟；P1-P16 → P1-P17 的名稱與註解；`tests_pg` 步驟改名（含 `requirement field G1-G4`） | **否**。`U20 step 0`／`A`–`E`（第 438–535 行）無 hunk |
| `openapi.json` | 不同 | 記憶端點的 `maxLength 4000`、503 宣告與說明（hunk 全在第 5491 行之前，均屬 `/api/memory/*`） | **否**。`/api/requirements/…` 兩條 path（第 5505、5573 行起）的 403／404／422 宣告無 hunk |
| `frontend/src/types/api.d.ts` | 不同 | 對應上列的記憶操作 503 與說明（hunk 全在第 4583 行之前） | **否**。三個 requirement 操作（第 4583、4632、4698 行起）無 hunk |
| `DEPLOY.md` | 不同 | 記憶角色小節（第 613–663 行）、第 27／28／21／31／32／34／36／37 列的段落；2.2.9 內兩處計數同步（第 767–768 行「7 條外鍵」、第 856–860 行「17 條斷言」） | **2.2.9 內兩處計數改動與本單元相容**（數字逐一對過 migration 與 verify 檔）；U20 小節（第 868 行起）與原「約第 730–738 行」的 U20 說明（因上方插入已位移至第 779–797 行）**無 hunk**，內容仍為「`create_all` 建表、只缺 COMMENT 與收斂」 |

**本單元依賴的授權入口**（不在收據清單內，另以 `git diff HEAD -U0` 查 hunk 位置）：`HierarchyFacade.get_project_of_system`（`hierarchy_facade.py:636`）、`HierarchyFacade._authorize`（第 219 行）、`mint_principal`（第 195 行）——hunk 只在第 96–114 行與 `delete_project`／`delete_system`（第 314、349 行起），**未觸及**；`MembershipFacade.resolve_project_role`（`membership_facade.py:209`）未觸及（hunk 在第 110–120 行 `_authorize_global`、第 386 行起 `change_role`、第 570 行起新方法、第 624 行起改選讀取）；`membership_service.resolve_project_role`（第 289 行）未觸及（hunk 自第 430 行起）；`rbac.py`／`rbac_seed_data.py`／`auth.py` 相對 HEAD 無改動。

**計畫文字的一處不符（不改計畫）**：Step 20 寫「`main.py` 的 `/api/requirement-fields` 掛載」，實際掛載為 `main.py:138` 的 `prefix="/api/requirements"`（與 `openapi.json` 一致），屬計畫筆誤。

### Step 21 — 回歸（scratchpad 實體副本，`backend/.venv` Python 3.13.7，`-B`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=.`、`HYPOTHESIS_STORAGE_DIRECTORY` 指向 scratchpad）

| 指令 | 結果 |
|---|---|
| 本單元 SQLite：`unittest tests.test_requirement_field_data tests.test_requirement_field_service tests.test_requirement_field_facade tests.test_requirement_field_http` | `Ran 35 tests` — `OK` |
| `python scripts/dump_openapi.py --check`（副本） | 結束碼 0，「規格檔與後端程式碼一致」 |
| `python3 -B scripts/validate_repo_contract.py`（工作樹） | passed |
| `python3 -B scripts/validate_env_contract.py`（工作樹） | passed |
| `tests_pg.test_requirement_field_pg`（本機一次性 PostgreSQL 17 ＋ pgvector 0.8.1，`listen_addresses=127.0.0.1`、port 55437、關閉 Unix socket，套用 `schema_rbac.sql` 一次） | `Ran 4 tests` — `OK`（G1–G4 皆 ok） |
| 同一個一次性資料庫：再套用 `schema_rbac.sql` 一次 → `verify_meta_schema.sql` | 結構類 P1…P17 與行為類 P4／P7／P10／P11 全部通過 |
| 同一個資料庫：CI `U20 step A`（downgrade）→ `run_meta_schema_migration.py` → `step C`（fixture）→ 重跑遷移 → CASCADE 檢查（交易內刪 system 後 `ROLLBACK`） | A 結束碼 0；B 結束碼 0、輸出「U20 欄位收斂 本次**有執行**」「7 條已逐條核對」；C 結束碼 0；D 結束碼 0、「本次未執行」、代寫值仍為 `cost`；刪 system 後孤兒需求欄位列 0 |

資料庫用完即停止並刪除資料目錄。此為本機、PostgreSQL 17、Python 3.13 的實跑，**不等於** CI（pg18、Python 3.12）的實跑證據。未連 staging 或任何共用 DB／Redis；未連網；未觸發 CI。

**為 Step 23 的勾選判定另跑的兩項**（同一副本）：
- 完整後端套件 `unittest discover -s tests`：`Ran 1391 tests`，1 error——`tests.test_legacy_cost_retirement` 讀 `frontend/tests/e2e/regression.spec.ts`，而副本起初未複製 `frontend/`；補複製 `frontend/`（排除 `node_modules`）後該模組 `Ran 6 tests — OK`。其餘全綠（skipped=3）。
- 完整 `tests_pg`（同一個一次性資料庫）：`Ran 15 tests`，**1 failure**：`test_membership_concurrency.test_C3_assert_can_deactivate_takes_no_lock`（`'passed' != 'guard'`，「守門沒有判定出唯一管理者」）。研判與工作樹未提交的 `membership_service.projects_losing_last_admin` 改動（合併前必修第 21 列「獨自一人的專案不擋」，hunk 第 662–745 行）有關，屬 `membership-service` 單元；**不是本單元的程式或測試**，本單元四案皆綠。依計畫本節不擴大範圍，未處置，交 conductor。

收尾：`git status --porcelain | grep -E '\.pyc|\.hypothesis|__pycache__'` 為空（見本節末）。

### Step 22 — 前輪審查的未結 Minor（review-04／05）

| ID | 現況（行號為本輪實讀） | 處置 |
|---|---|---|
| R-02 | 未改：`requirement_field_definitions.py:33` 仍為 `re.compile(r"^[a-z0-9_]{1,64}$")`，以 `.match` 使用於 `requirement_field_errors.py:99`、`requirement_field_definitions.py:97`、`:109`；結尾換行仍可通過 | 需改程式 → 已知限制，交 conductor |
| R-03 | 未改：`requirement_field_router.py:173` `body: bytes = Depends(_read_raw_body)` 仍排在 `:174` `current_user` 之前 | 需改程式 → 已知限制，交 conductor |
| R-04 | 未改：`ci.yml:445-446` 仍 `pip install -r backend/requirements.txt`；仍無 CI 實跑證據。本輪有本機等價流程實跑（Step 21 最後一列），僅能作為輔助證據 | 只記紀錄；最小安裝屬 CI 改動，若要做交 conductor |
| R-05 | 交接仍在本檔第 135 行（`K-16` 矛盾句）與「給 `U21 mcp-bridge` 與 `U13 brain-gateway`」段（第 145–152 行）；無法由本單元確認對方已讀到 | 只記紀錄；確認傳達屬 conductor |
| R-06 | 未改：`user_router.py:510-516` 的刪除預檢仍列 `system_requirement_fields`（`updated_by == uid` 且 `system_id` 不在清除範圍）；`tests/`、`tests_pg/` 對該類別字串 `"system_requirement_fields"` 與標籤「系統需求欄位的最後修改者紀錄」在測試中**0 個案例斷言 409 類別**（命中的三檔只是表名常數或 schema 期望）。`tests/test_user_delete_audit_counts.py:66-128` 只鎖「空預設專案連帶清除需求欄位值的筆數」，不鎖 409 預檢 | 需新增測試（落點在 `user_router` 的刪除路徑，非本單元）→ 已知限制，交 build-and-test／conductor |
| R-09 | 未改：`requirement_field_router.py:103-110` 的 422 說明仍未列「值含 NUL」（固定訊息在 `requirement_field_errors.py:132`）；本輪 `openapi.json` 雖因他單元重 dump，但本單元未改程式，故未順手補 | 需改程式並重產 `openapi.json`／`api.d.ts` → 已知限制，交 conductor |
| R-10 | `tests_pg/test_requirement_field_pg.py:246` G4 本輪由開發者在本機一次性 PostgreSQL 17 實跑 ok（Step 21）；**仍非審查員的獨立重跑** | 只記紀錄 |

### Step 23 — 勾選重設（Step 1–19 逐格）

| Step | 判定 | 依據 |
|---|---|---|
| 1 | 勾 | `backend/scripts/ci/` 兩支 SQL 與收據相同 |
| 2 | 勾 | 本輪重跑 `tests.test_membership_data`：`Ran 12 tests — OK` |
| 3 | 勾 | 四支相關檔有他單元改動，但 `J)` 中本單元 DDL 與收斂區塊無 hunk；本輪本機實跑收斂（A–D）與 P15／P16 通過；CI 步驟 0／A–E 無 hunk |
| 4–8 | 勾 | 程式與測試與收據相同；本輪 SQLite 35 案與 PG G1–G4 綠 |
| 9 | 勾 | router、`main.py` 相同；`dump_openapi.py --check` 綠；`openapi.json`／`api.d.ts` 中本單元的 path 與 operation 無 hunk |
| 10 | 勾 | 測試相同且綠；`--check` 綠；突變驗證的對象程式未變 |
| **11** | **改為未勾** | `npm run check:types` 本輪依 brief 不可執行（會改寫 gitignored 檔），而 `frontend/src/types/api.d.ts` 自收據後已被他單元改動（記憶操作的 503 與說明），故「型別檔與 `openapi.json` 同步」既非逐位元相同、也未在本輪重驗。兩支 contract 腳本本輪通過 |
| 12 | 勾 | `DEPLOY.md` 2.2.9 內兩處計數改動已逐一對過、U20 小節無 hunk；`source-manifest.json`、`traceability.json` 未變且內容仍成立（`traceability.json` 合法 JSON，未改） |
| 13–15 | 勾 | NUL 拒絕程式與測試未變；本輪 H10（SQLite）與 G4（PG）綠；突變對象未變 |
| 16 | 勾 | 原約第 730–732 行的段落已因上方插入位移至第 788–797 行，內容未變，仍與 U20 小節一致 |
| **17** | **改為未勾** | 該格宣告「完整後端套件、`tests_pg` … 全綠」。本輪重驗：完整後端套件綠（見上），但完整 `tests_pg` 有 1 failure（`test_membership_concurrency` C3，他單元）。本單元的 `tests_pg` 四案綠，`--check` 與兩支 contract 綠；失敗不在本單元，但該格的字面宣告在現行工作樹不成立 |
| 18 | 勾 | 其結論限定在 review-04 → review-05 區間，該區間已由 review-05 獨立確認；之後的區間由本輪 Step 20 取代 |
| 19 | 勾 | 本輪以同樣指令重跑，結果相同 |

**實算**（全檔，`grep -c '^\s*- \[x\]'`／`grep -c '^\s*- \[ \]'`，於 Step 24 勾選後執行）：已勾 **22**、未勾 **2**（Step 11、Step 17）。

### 需由 conductor 併入 `merge-blockers.md` 的已知限制（需改程式或測試，本輪未改）

1. R-02：`KEY_PATTERN` 改 `fullmatch`（或 `\Z`），定義檔自我檢查同步。
2. R-03：`write_requirement_field` 的 `current_user` 排在 `body` 之前，或讀取原始本體時設上限。
3. R-06：為 `user_router` 刪除預檢的 `system_requirement_fields` 409 類別補一個 TestClient 案例。
4. R-09：`ERROR_RESPONSES` 的 422 說明補「值含 NUL」，重產 `openapi.json`／`api.d.ts`。
5. （他單元，觀察所得）`tests_pg/test_membership_concurrency.py` C3 在現行工作樹紅燈，研判與第 21 列的 `projects_losing_last_admin` 改動有關。

### 本輪改動檔

`code-generation-plan.md`（只改勾選字元，前後 diff 已確認）與本檔（append 本節）。`traceability.json`、`source-manifest.json` 未改。未 commit、未 push、未觸發 CI、未以 `gh` 寫入。
