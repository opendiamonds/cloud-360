# Code Generation 摘要 — `U9 memory-purge`

> 方法論 `test-after`（契約 `sha256:1f0b682…`）。每一層先實作、再寫並跑該層的測試。
> `API / endpoint` 與 `Frontend behavior` 兩層對本單元不適用（零端點、零前端面）；
> `Repository / data access` 由 `Data model / database behavior` 吸收——清除沒有
> ORM 層，它就是 SQL。

## 一、交付物（13 個檔：7 新、6 改）

| # | 路徑 | 新／改 | 一句話理由 |
|---|---|---|---|
| 1 | `schema_rbac.sql` | 改 | 新 `K)` 區塊：保留系統 actor 的 seed ＋ `COMMENT ON TABLE users`（寫明四道鎖與刪掉它的後果）；檔頭 TOC 與注意事項各加一條 |
| 2 | `backend/scripts/seed_retention_system_actor.py` | **新** | 既有環境取得那一列的路徑；解析 `K)` 區塊、單一交易、COMMIT 前逐項查證後條件 |
| 3 | `backend/scripts/purge_expired_memory.sql` | **新** | 清除本體。兩個顯式交易**同在一檔**，故交易邊界不依賴 workflow 怎麼切步驟 |
| 4 | `backend/scripts/purge_dry_run.sql` | **新** | 不可逆操作的前置驗證：只讀，印計數**與選取範圍的邊界**（審查 `R-02`） |
| 5 | `backend/scripts/verify_purge_sql.sql` | **新** | `R1`–`R10` 行為斷言。以 `\i` 引入第 3 項，故 CI 與生產跑同一份文字 |
| 6 | `backend/tests_pg/test_purge_atomicity.py` | **新** | `A1`–`A3`：真實 PostgreSQL ＋ 兩條連線，證明 `R-01` 的最壞情況安全 |
| 7 | `backend/tests/test_retention_purge_contract.py` | **新** | 10 條靜態契約斷言（零資料庫、零網路） |
| 8 | `.github/workflows/memory-retention-purge.yml` | **新** | 自架 runner、每日 17:41 UTC ＋ `workflow_dispatch`（含 `dry_run`） |
| 9 | `.github/workflows/memory-retention-watchdog.yml` | **新** | GitHub 託管、每日 06:23 UTC、`status=success`＋`event=schedule`、3 天門檻、去重 |
| 10 | `.github/workflows/ci.yml` | 改 | `memory-schema` job 加一步跑第 5 項；S 系列步驟名改為 `S1-S13` |
| 11 | `DEPLOY.md` | 改 | 新 §2.2.11（**blocking 同步**）＋ §2.2 表格新增 `K` 一列 |
| 12 | `backend/scripts/verify_memory_schema.sql` | 改 | 新增 `S13`（哨符列存在 ＋ 三道可在資料庫層查證的鎖） |
| 13 | `backend/scripts/run_meta_schema_migration.py` | 改 | 註解 ＋ `BLOCK_SENTINELS` 登錄 `K`（見偏離 `D-2`）；`BLOCKS_TO_RUN` 未變 |

**不動**：`openapi.json`、`frontend/src/types/api.d.ts`（零端點）、`LOCAL-DEV.md`
（觸發清單四者皆不動）、`deploy/` 的任何檔案、`backend/database.py`（diff 為空，
開工前記錄基準、收尾複驗）。

## 二、與計畫的偏離（5 項，逐項附理由與證據）

### `D-1`（**最嚴重**）：`--env-file deploy/.env` 會讓清除**每天失敗**

計畫 Step 8.1 逐字要求 compose 呼叫為
`docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env exec -T db psql …`
（審查 `R-01` 的第一半）。**後半不可行**：

| 事實 | 逐字依據 |
|---|---|
| `deploy.yml` 每次執行結束都刪掉那個檔 | `deploy.yml:376-378` 的 `- name: Remove the generated env file` ＋ `if: always()` ＋ `rm -f deploy/.env` |
| rollback job 也刪 | `deploy.yml:472` |
| 指向不存在的 env file 是**硬錯誤** | `docker compose --env-file <missing>` 直接失敗，不是警告 |

**後果**：每日排程會天天紅燈，清除永不執行；watchdog 每 3 天開一個 issue。

**也不能省略 `--env-file`**：compose 在任何子指令之前先內插整個 project model，而
`deploy/docker-compose.deploy.yml:345` 的
`volumes: - ${CLOUDFLARED_CREDENTIALS_FILE}:/etc/cloudflared/creds.json:ro`
在該變數為空時是一個無效的 volume spec。

**處置**：`-f` 原樣照計畫（固定 compose 檔，不依賴預設工作目錄；`name: cloud360`
使 project 解析同樣不依賴 CWD），`--env-file` 改指 **`deploy/.env.example`**。
它版控、**零機密**，且 `scripts/validate_env_contract.py` 的
`validate_deploy_template_is_complete()` 已在 CI 強制它涵蓋 deploy compose 要求的
每一個變數——所以「它能滿足內插」是 CI 保證的事實，不是假設。
它的**值無關緊要而且可證明**：`exec` 附著到一個**已在運行**的容器、不重建任何東西，
而 psql 的身分與資料庫名是從**容器自己的環境**讀的（見 `D-3`）。

**被否決的替代方案**：在本 workflow 內呼叫 `deploy/render-env.sh` 產生一份。那會把
三顆部署 secret 拉進這個 workflow，並與並行的部署**搶同一個檔案路徑**——我們的
`rm -f` 可能把一個正在進行的部署的 env 檔刪掉。那個交換比 `R-01` 擔心的連線中斷
嚴重得多。

### `D-2`：`extract_blocks()` 無法直接重用於新字母（計畫 Step 2.5／2.6）

計畫 Step 2.5 要求對 `run_meta_schema_migration.py` **只加註解、不改任何可執行行為**，
Step 2.6 要求 `from run_meta_schema_migration import extract_blocks` 取得解析器。
**兩者不能同時成立**：該函式以 `BLOCK_SENTINELS[letter]` 查它**自己模組層**的
dict，未登錄的字母直接 `KeyError`。實測：

```
RuntimeError / KeyError: 'K'
  File ".../run_meta_schema_migration.py", line 223, in extract_blocks
    for sentinel in BLOCK_SENTINELS[letter]:
```

**處置**：在 `BLOCK_SENTINELS` 登錄 `"K"` 的三個結構性哨兵（一行 dict 條目），
並在該 dict 上方寫明「這是『區塊 → 哨兵』的登錄表，不是『要執行哪些區塊』的清單」。
`BLOCKS_TO_RUN` **未變**，故該腳本的行為與輸出完全不變——已實跑複驗（仍只套用
`X)`／`I)`／`J)`，仍輸出「不塞任何資料」那句，`K-15` 未被破壞）。
`K)` 的哨兵**刻意不含哨符 username 字面值**，否則它會變成第四處物化而無人鎖它。

### `D-3`：psql 的「預設身分」敘述有一半是錯的（計畫 Step 8.1／`NFR6.10`）

`security-requirements.md` 的 `NFR6.10` 二元判準逐字寫
「`docker compose exec -T db psql` 的預設身分即 `POSTGRES_USER`」。
psql 的預設身分是**容器內的 OS 使用者**、預設資料庫是**與該使用者同名的那一個**
——**不是 `POSTGRES_DB`**。前半在本部署只因為 `POSTGRES_USER` 的值字面上就是
`postgres`（`deploy/render-env.sh:97`）而碰巧成立；**資料庫名那一半在任何情況下
都是錯的**——不給 `-d` 就會連到 `postgres` 這個資料庫，而 `memory` schema 不在那裡。

**處置**：
```
exec -T db sh -c 'PGUSER="$POSTGRES_USER" PGDATABASE="$POSTGRES_DB" exec psql -v ON_ERROR_STOP=1'
```
兩個值都來自**容器自己的環境**（compose 在建立容器時從真實 `deploy/.env` 寫入的），
故與 `D-1` 的範本值無關。**判準原文仍然滿足**：沒有身分覆寫旗標、沒有連線字串、
沒有密碼；把身分釘在 `POSTGRES_USER` 是設計指名的那個身分，不是提權——那是本系統
唯一的資料庫身分。記為 `OPEN-CG9-4`。

### `D-4`：`schema_rbac.sql` 檔頭以**區塊名**而非行號指出 `DELETE FROM role_permissions`

計畫 Step 2.4 要求「逐字指出 `:715` 的 `DELETE FROM role_permissions`」。
我先照做，寫完發現該敘述已因本輪插入的 `K)` 區塊位移到 `:780`——**同一輪的插入
讓同一輪寫下的行號失效**。改為「下方 `C) RBAC` 區塊開頭那條逐字為
`DELETE FROM role_permissions;` 的敘述」：同樣逐字可查，而且不會隨這個檔案的
下一次編輯漂走。

### `D-5`：契約斷言比對「剝掉註解後的可執行 SQL」而非整個檔案

計畫 Step 7 的斷言寫成「同檔含／不含 `<字串>`」。對整檔做子字串比對有兩個方向的
缺陷，而第二個讓斷言失去全部意義：

* 偽陽性：一句解釋禁令的註解讓禁令的斷言永遠紅燈。
* **偽陰性**：第 2 條要求 `kind = 'episodic'` **存在**，而該字串也出現在同檔註解裡
  ——把它從 `WHERE` 子句刪掉之後測試仍會綠燈。

故實作 `executable_sql()`（丟掉 `\` 開頭的 psql 元指令、每行在第一個 `--` 處截斷），
並加一條 `test_sql_comment_stripping_assumptions_hold` 機械驗證它的三個前提
（無 `/* */`、無 `$$`、`--` 不在未閉合字串內）。斷言數因此由 8 增為 **10**
（第 9 條是 `CANONICAL_ROLES` 的程式層比對，第 10 條是這個前提守衛）。

**這個決定在突變驗證中救了兩條斷言**，見第四節的突變 3 與 6。

## 三、計畫沒有預料到的發現（4 項）

### `F-1`（**最嚴重**，既有缺陷）：`POST /api/auth/login` 有一個今天就可用的帳號存在性 oracle

計畫 §1.4 把 `OPEN-CG9-2`（`verify_password` 應捕捉 `ValueError`）寫成「資料庫內
**任何來源的畸形 hash** 都會觸發的既有潛在 500」。**實測後它比那個描述嚴重得多**：
觸發**不需要**資料庫裡有畸形 hash，**攻擊者自己的輸入就夠**。

`bcrypt.checkpw` 對**超過 72 位元組的明文**也拋
`ValueError: password cannot be longer than 72 bytes`，與 hash 的格式無關。
而 `verify_password`（`auth.py:37-40`）沒有 `try/except`，`user_router.py:403-406`
又是**先查使用者、再比對密碼**。以 `TestClient` 對真實 `app` 實測三組：

| 請求 | HTTP |
|---|---|
| 已存在的 username ＋ 72 位元組密碼 | `401` |
| **已存在的** username ＋ **73 位元組**密碼 | **`500`** |
| 不存在的 username ＋ 73 位元組密碼 | `401` |

即：送一個 73 位元組的密碼，`500` ⇒ 該帳號存在、`401` ⇒ 不存在。
**未經驗證、遠端可觸發、對任何帳號皆可**。

**本單元不修**：`auth.py` 不屬本 `packaging` 單元，且 `team.md` 明文反對在功能變更
的同一個 PR 夾帶既有共用程式的重構。**也刻意不為它寫斷言**——斷言它會拋等於把缺陷
鎖進契約，斷言它不拋會讓 CI 為一個不在範圍內的既有問題紅燈。記為 `OPEN-CG9-2`
（優先度高於原本的評估，建議另開 issue）。本單元的哨符 hash 設計**不受影響**：
它是格式合法的 bcrypt hash，合法長度的任何明文都乾淨地回 `False`（契約第 7 條驗證）。

### `F-2`：`infrastructure-specification.md §五` 第 2 步的「唯一路徑」是破壞性操作

該步逐字寫「**重跑 `schema_rbac.sql`**（既有環境取得 seed 的唯一路徑）」。
該檔是**單一交易**，而 `C) RBAC` 區塊開頭逐字為 `DELETE FROM role_permissions;`
（檔頭注意事項也警告過：「role_permissions 會 DELETE 後重播預設（Admin UI 調過
請先備份）」）。照該指示在既有環境操作，會**清掉任何經 Admin UI 調整過的權限矩陣**。

計畫 §1.2 已預見此事並以新腳本處置；本輪補的是把更正**寫進操作者會讀的地方**
（`DEPLOY.md` §2.2.11 的「明文更正」區塊 ＋ `schema_rbac.sql` 檔頭）。
記為 `OPEN-CG9-3`。

### `F-3`：watchdog 若只過濾 `status=success`，一次 `dry_run=true` 會把時鐘歸零

計畫 Step 9.2 與 `cicd-pipeline.md §四之一` 只要求 `status=success`。但本單元同時
交付了一個 `dry_run` 輸入——而一次 `dry_run=true` 的手動觸發**成功而什麼都沒刪**。
只過濾 `status=success` 會讓它重設新鮮度時鐘，**蓋掉數週沒有真正清除的事實**，
而那正是這個 workflow 存在要抓的失敗。

**處置**：查詢另加 `event=schedule`。代價是一次手動的**真實**清除也不會重設時鐘
（最壞情況：3 天後多一個 issue）——保守方向正確。契約第 8 條同時鎖住兩個過濾條件
（兩者各自的移除都已實測紅燈）。

### `F-4`：`verify_purge_sql.sql` 無法回滾，故它需要一道前置守衛

`verify_memory_schema.sql` 的行為類斷言以 `BEGIN; … ROLLBACK;` 包起來，不留痕跡。
**本檔做不到**：它 `\i` 引入的清除 SQL 自己帶 `COMMIT`。對一個**有真實資料**的
資料庫執行它，會真的刪掉逾期的 episodic 記憶。

**處置**：在 `\i` **之前**加一道前置守衛——若存在不屬於本檔 fixture 的逾期 episodic
記憶或逾期稽核列，就 `RAISE EXCEPTION` 中止。已實測：對一個放了 scratch 資料的
資料庫執行，守衛以可讀訊息中止且**兩張表一列都沒動**。`tests_pg` 的 `setUp` 有同形
的守衛。

## 四、突變驗證（6 項計畫項目 ＋ 3 項自加變體，全部實測）

每一項：改成錯的行為 → 確認指定測試**紅燈** → 還原 → 確認**綠燈**。

### 突變 1 — 清除 SQL 移除 `kind = 'episodic'`

期望紅燈：`verify_purge_sql.sql` 的 `R4` ＋ 契約第 2 條。**兩者皆紅。**

```
psql:backend/scripts/verify_purge_sql.sql:371: ERROR:  R4 FAILED (FR4.5 僅約束 episodic):
kind = semantic 而帶有過去 expires_at 的列（fixture c）**必須保留**，實際 0 列。
清除的 WHERE 少了 kind = episodic 這個條件——那是永久資料損失，且 FR4.5 明文不約束
這類列。NFR7.10 的二元判準文字漏了這個條件（OPEN-CG9-1），實作刻意收窄
psql rc=3
```
```
AssertionError: "kind = 'episodic'" not found in "…WHERE expires_at < now()\n  RETURNING id…"
: purge_expired_memory.sql 的可執行 SQL 不含 kind = 'episodic'…
Ran 1 test in 0.002s
FAILED (failures=1)
```
還原後：`verify_purge_sql rc=0`、契約 `Ran 10 tests … OK`。

### 突變 2 — `RETURNING id` → `RETURNING *`

期望紅燈：契約第 1 條。**紅。**
```
AssertionError: Lists differ: ['RETURNING *'] != []
Ran 1 test in 0.002s
FAILED (failures=1)
```
還原後：`Ran 1 test … OK`。

### 突變 3 — `K)` 區塊移除 `ON CONFLICT (username) DO NOTHING`

期望紅燈：契約第 5 條 ＋ `memory-schema` 的「第二次套用」步驟。

**第一次跑：`memory-schema` 的第二次套用紅了，契約第 5 條卻綠燈。**
```
  first apply rc=0
psql:schema_rbac.sql:754: ERROR:  duplicate key value violates unique constraint "ix_users_username"
  re-apply rc=3
SELECT count(*) FROM role_permissions;  -->  352     ← 交易中止，C) 區塊從未執行
```
```
（契約第 5 條）Ran 1 test in 0.001s
OK                                      ← **偽陰性**
```
**那是我自己測試的缺陷**：`K)` 區塊的註解逐字解釋為什麼
`ON CONFLICT (username) DO NOTHING` 不可省，於是整個區塊的子字串比對被**註解**
滿足了。已修（`K)` 相關斷言一律跑在剝除註解後的文字上，`K_BLOCK_INSERT` 的 regex
亦然，前提守衛的覆蓋範圍擴及 `K)` 區塊）。重跑同一個突變：
```
AssertionError: 'ON CONFLICT (username) DO NOTHING' not found in
'…INSERT INTO users (username, password_hash, role, is_active)\nVALUES (…);\n\nCOMMENT ON TABLE users IS…'
: schema_rbac.sql 的 K) 區塊缺少 ON CONFLICT (username) DO NOTHING…
Ran 1 test in 0.002s
FAILED (failures=1)
```
還原後：契約第 5 條 `OK`、`re-apply rc=0`。
**附帶證實了計畫 §1.2／§5.1 的推理**：`role_permissions` 停在 352 列，代表整支檔
確實從那一行起全部中止、`C)` 區塊從未執行。

### 突變 4 — CTE 拆成兩條獨立敘述並在中間 `COMMIT`

期望紅燈：`tests_pg` 的 `test_terminated_before_commit_deletes_nothing`。**紅**，
但是由 `setUpClass` 的結構守衛攔下（它指名了真正的缺陷）：
```
RuntimeError: purge_expired_memory.sql 應有恰好 2 個顯式交易，解析到 3 個。
本檔以單獨成行的 BEGIN;／COMMIT; 為界切敘述——該檔的交易邊界被改過
Ran 0 tests in 0.075s
FAILED (errors=1)
```

**突變 4b（自加，為了證明 A1 的斷言本身不是恆真）**：在 CTE 最後一行後面接一個
行內 `COMMIT;`。檔案仍只有兩對獨立成行的 `BEGIN;`／`COMMIT;`，所有結構守衛都通過
——**只有原子性斷言能抓到它**：
```
AssertionError: Tuples differ: (0, 1) != (1, 0)
: 另一條連線在 COMMIT 之前就看到了未提交的變更——隔離等級不是預期的那樣
Ran 1 test in 0.135s
FAILED (failures=1)
```
還原後：`Ran 3 tests … OK`。

### 突變 5 — 稽核清除的 `- interval '90 days'` 改 `+`

期望紅燈：`R8`／`R9`。**紅（rc=3）**，但第一條失敗的是 `R5`：
```
psql:…:371: ERROR:  R5 FAILED (NFR7.11／FR4.7): 本次清除刪除了 1 列 episodic 記憶，
故應新增恰好 1 筆 purged_by_retention 稽核列，實際 0 筆
```
原因是 `+ 90 days` 讓交易二的截止點落在**未來**，於是它刪掉整張稽核表——包含交易一
剛寫的那一列。`R5` 在同一個 `DO` 區塊內較早求值，所以先短路。
**為了證明 `R8`／`R9` 各自不是恆真，自加兩個只動邊界的變體**：

| 突變 | 第一條失敗的斷言 |
|---|---|
| 5b：`90 days` → `900 days` | `R8 FAILED (NFR7.2／NFR7.10): 91 天前的稽核列（fixture e）應已被刪除，實際仍有 1 列…` |
| 5c：`90 days` → `80 days` | `R9 FAILED (NFR7.2): 89 天前的稽核列（fixture f）必須保留，實際 0 列。保存期被算短了` |

三者還原後皆 `rc=0`。

### 突變 6 — watchdog 的查詢移除 `status=success`

期望紅燈：契約第 8 條。**第一次跑：綠燈——又一個偽陰性。**
`grep -c` 顯示檔內還剩 1 處 `status=success`，在一句 issue 文案裡
（`:176`），而斷言是對整個檔案比對的。**與突變 3 完全同形，而這是我在同一輪犯的
第二次。** 已修：改為先取出**非註解**且含 `/runs?` 的那一行（並斷言恰有一行），
再對**那一行**比對。重跑：
```
AssertionError: 'status=success' not found in
'            "repos/${GH_REPO}/actions/workflows/${PURGE_WORKFLOW}/runs?event=schedule&per_page=1" \'
: memory-retention-watchdog.yml 的 run 查詢沒有過濾 status=success…
Ran 1 test in 0.002s
FAILED (failures=1)
```
**突變 6b（自加）**：移除 `event=schedule`（`F-3` 的那一半）：
```
AssertionError: 'event=schedule' not found in '…/runs?status=success&per_page=1" \'
: …少了它，一次 dry_run=true 的手動觸發（它成功但什麼都沒刪）會把新鮮度時鐘歸零…
Ran 1 test in 0.002s
FAILED (failures=1)
```
兩者還原後：`Ran 10 tests … OK`。

### 突變驗證的一個結論，寫下來而不是帶過

**六項突變裡有兩項（3 與 6）第一次跑的時候是綠的，而兩項都是同一個形狀**：
一條文字斷言被**被測檔案自己的註解或文案**滿足。我在寫契約測試時已經為兩個 `.sql`
檔識別出這個陷阱並做了剝除器（偏離 `D-5`），**卻沒有把同一個判準套到
`K)` 區塊與 workflow 上**——那正好是 `project.md` 記過的「同一個缺陷有幾個入口、
只修被點名的那一個」。**沒有突變驗證，這兩條斷言會以『已覆蓋』的樣貌進入 CI。**

## 五、實際執行的指令與結果

### 單元範圍指令（三個載體；全部限定於本單元）

```bash
cd backend && python3 -m unittest tests.test_retention_purge_contract -v
#   Ran 10 tests in 1.219s / OK

cd backend && DATABASE_URL='postgresql+psycopg://…/<db>' \
  python3 -m unittest tests_pg.test_purge_atomicity -v
#   Ran 3 tests in 0.146s / OK

psql "<db>" -v ON_ERROR_STOP=1 -f backend/scripts/verify_purge_sql.sql   # 於 repo 根目錄
#   NOTICE: R1-R10 全部通過…  /  rc=0
```

### CI job 的逐步重現（真實 PostgreSQL 17.7 ＋ pgvector 0.8.1，全新資料庫）

`memory-schema` job：
```
  schema_rbac.sql                               rc=0
  schema_rbac.sql（第二次套用，BR1.3）           rc=0
  backend/scripts/verify_memory_schema.sql      rc=0   ← 含新的 S13
  backend/scripts/verify_meta_schema.sql        rc=0
  backend/scripts/verify_purge_sql.sql          rc=0   ← 本輪新增的步驟
```

`concurrency` job（套用 schema 一次 ＋ `discover -s tests_pg`）：
```
  Ran 6 tests in 3.330s / OK      ← U19 的 C1-C3（3 條）＋ 本單元的 A1-A3（3 條）
```
`ci.yml` **不需要為 `tests_pg` 新增任何東西**（該 job 已是 `discover -s tests_pg`，
新檔自動被撿到），與計畫 Step 10.3 的預測一致。

### 既有環境的 seed 路徑（實跑）

```
$ cd backend && DATABASE_URL=… python3 scripts/seed_retention_system_actor.py
目標資料庫：host=localhost database=u9_verify
… 已套用 schema_rbac.sql 的 K) 區塊
保留系統 actor 的 seed 完成（U9 memory-purge / NFR7.11）：
  username        SYSTEM.retention-purge
  role            system（不在 role_permissions 的授權集合內）
  is_active       false
  password_hash   符合 bcrypt 格式（值不輸出——沒有人需要讀它）
終檢通過：…
EXIT=0
$ （重跑一次）EXIT=0 ；該 username 的列數 = 1   ← 可重跑
```
`run_meta_schema_migration.py` 複驗：仍只套用 `X)`／`I)`／`J)`，輸出仍含
「本指令**不驗證** schema_rbac.sql 的其餘區塊，**也不塞任何資料**」，`EXIT=0`。

### dry-run（實跑，含資料時）

```
would_delete_memories=1  oldest/newest_expires_at 皆列出  cutoff_now 列出
（對照組）kind=semantic  must_be_kept=1  ← 不該被刪的逾期列也印出來
would_delete_audit_rows=1  oldest/newest_occurred_at 列出  cutoff_occurred_at 列出
system_actor_rows=1  all_inactive=t
rc=0 ；兩張表的列數**完全未變**（2|1 → 2|1）
grep -c 'secret conversation' <輸出> = 0      ← 零記憶內容洩漏
```

### 前置守衛（實跑）

對一個含 scratch 資料的資料庫執行 `verify_purge_sql.sql`：
```
ERROR:  前置守衛中止（這不是斷言失敗）：目標資料庫有 1 列不屬於本檔 fixture 的
逾期 episodic 記憶。本檔引入的清除 SQL 自己帶 COMMIT，**無法回滾**…
→ 兩張表的列數 2|1，一列都沒動
```

### watchdog 判定邏輯（以 stub 化的 `gh` ＋ GNU `date` 實測四個分支）

| 情境 | `state` | `age_days` | `overdue` |
|---|---|---|---|
| 1 天前成功 | `found` | `1` | `false` |
| 5 天前成功 | `found` | `5` | `true` |
| 從無成功 run | `never` | — | `true` |
| 讀不到（404） | `unreachable` | — | `true` |

兩個 workflow 的全部 `run:` 區塊 `bash -n` 皆 `rc=0`；兩檔 YAML 皆可被
`yaml.safe_load` 解析。

### 收尾核對

```
git diff --stat -- backend/database.py        → 空
python3 scripts/validate_repo_contract.py     → Cloud-360 repository contract validation passed.
python3 scripts/validate_env_contract.py      → Cloud-360 environment configuration contract validation passed.
cd backend && python3 -m unittest discover -s tests
                                              → Ran 533 tests in 33.951s / OK
cd backend && python3 scripts/dump_openapi.py --check
                                              → 規格檔與後端程式碼一致。
git diff -- deploy/ | grep -ci 'purge|retention'  → 0   （本單元未碰 deploy/）
```

公開輸出禁令的機械複驗：五個交付檔中 `DATABASE_URL`／`content`／`embedding`／
`PGPASSWORD` 的每一處命中都逐行開檔確認為**註解或變數名**，無任何一處是輸出。

## 六、本單元的實際測試門檻

| 載體 | 數量 | 由誰執行 |
|---|---|---|
| 靜態契約斷言（`backend/tests/`） | **10** | `backend` job 的 `discover -s tests` |
| 原子性（`backend/tests_pg/`，真實 PostgreSQL ＋ 雙連線） | **3** | `concurrency` job |
| 行為斷言（`psql`，真實 PostgreSQL） | **`R1`–`R10` ＋ `S13` = 11** | `memory-schema` job |
| **合計** | **24** 條二元可判斷言 | 三個 job |

計畫預估 22 條；實際 24（契約由 8 增為 10：第 9 條是 `CANONICAL_ROLES` 的程式層
比對、第 10 條是剝除器的前提守衛）。

**覆蓋率**：`org.md` 宣告 80% line coverage。本 repo **沒有覆蓋率量測機制**
（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」），且本單元交付 SQL 與
YAML，Python 覆蓋率工具量不到它們。**本摘要不宣稱滿足該數字，也不弱化它**：
以上 24 條斷言 ＋ 9 項突變驗證作為本單元的實際門檻，並如實記載這個落差。

**PBT**：`N/A（非豁免）`——本單元無任何自己擁有的純函式，與
`security-requirements.md §四`、`security-design.md §四`、
`infrastructure-specification.md §六` 三站一致。

## 七、ADR-0006 四面向

**本單元不改任何一格的判定**（逐格對照上游三站的同名表）。

| 面向 | 判定 | 本單元的落點 |
|---|---|---|
| **IAM** | 適用；`NFR6.10` 不構成邊界（恆真，`[ND2]`=A），保留「不得顯式覆寫」 | SQL 與 workflow 皆無身分覆寫（契約第 3 條，掃 SQL 檔 ＋ workflow 的非註解 `psql` 行）。**新增一個 IAM 主體**（系統 actor），四道鎖全部落在既有程式上：大寫 username（契約第 6 條）／格式合法但不可比對的 hash（契約第 7 條）／非授權 role（契約第 9 條 ＋ `S13`）／`is_active = FALSE`（契約第 9 條 ＋ `S13`）。**新增的權限面**是 watchdog 的 `issues: write`（`OPEN-ID9-2`，無先例） |
| **Encryption** | 本單元無增量（承 `U5` 的 `NFR6.1`／`NFR6.2`） | 清除流量留在 compose 內部（`exec -T`）；watchdog 只打 HTTPS 的 GitHub API，且**不傳輸任何記憶內容**。哨符 `password_hash` 是**無已知前像**的 bcrypt hash，不構成新機密 |
| **Network exposure** | 零增量 | `db` 不取得 host port、無新 tunnel、無新監聽埠（`deploy/` 整個目錄未被改動）。watchdog 是**出向**呼叫，不接受入向連線 |
| **Audit logging** | 適用（本單元核心之一） | `NFR7.11` 由 CTE **結構性**保證（稽核列來自 DELETE 的 `RETURNING`，不是另一條會重新求值的敘述），驗於 `R5`／`R6`／`R7` ＋ `A2`；`NFR7.15` 由交易二的「只 DELETE」保證，驗於 `R8`／`R9`／`R10`。**另新增一層**：watchdog 開的 issue 本身是「清除漏跑」這件事的紀錄，且它在 GitHub 上、不在那台可能離線的主機上 |

## 八、不在本單元範圍（逐項附承接；完整清單見 `traceability.json` 的 `open_items`）

| id | 內容 | 承接 |
|---|---|---|
| `OPEN-CG9-1` | `NFR7.10` 的二元判準文字漏了 `kind = 'episodic'` | 下一輪 `nfr-requirements` 修訂或 practices-discovery |
| `OPEN-CG9-2` | **`F-1` 的登入 500 oracle**（既有缺陷，優先度高於原評估） | 擁有 `auth.py` 的後續單元或 intent；建議另開 issue |
| `OPEN-CG9-3` | `infrastructure-specification.md §五` 第 2 步的「唯一路徑」是破壞性操作（`F-2`） | 下一輪 `infrastructure-design` 修訂 |
| `OPEN-CG9-4` | `NFR6.10` 判準中「psql 的預設身分／資料庫」的敘述有誤（`D-3`） | 下一輪 `nfr-requirements` 或 `nfr-design` 修訂 |
| `OPEN-CG9-5` | 3 天門檻的「`> 3`」與「容忍兩次連續失敗」差一天（已在 workflow 內註明，未靜默擇一） | 下一輪 `infrastructure-design` 修訂 |
| `OPEN-ND9-1` | 系統 actor 列會出現在 Admin 清單上（`/api/auth/list` 的 `total` +1） | `U19`／既有端點，或後續 intent |
| `OPEN-ND9-2` ＋ `OPEN-CG5-1` | 是否新增真正受限的資料庫角色；grant 邊界未被 CI 驗證 | 同一個決定；後續 intent |
| `OPEN-ID9-1` | 沒有人監看監看者（依賴面已最小化） | 已接受的殘留風險 |
| `OPEN-ID9-2` | `issues: write` 無先例；替代方案已寫明 | 關卡上的具名權限增量 |
| `OPEN-ID9-3` | 既有 SQLite 測試路徑看不到 seed——本輪以 `S13` ＋ `R1`–`R10` **部分關閉** | 餘留 |
| `tcms-test-cases` | **blocking，且至今未對本 intent 的任何單元執行過** | construction 階段，部署之前 |

## 重新查驗與合併前必修第 11、17 項

> 紀錄時間：2026-10-22T08:25:56Z（`date -u` 取值）。背景：使用者對 code-generation 送 Request Changes，本單元承接 `merge-blockers.md` 第 11、17 項；裁決見計畫第十節。

### 一、Steps 1–12 重新查驗（全部重新勾回）

逐格開檔查證，皆成立。真實 PostgreSQL 的斷言本輪**有實跑**：本機無 Docker，於 scratchpad 以 Homebrew `postgresql@17`（17.7，含 pgvector）臨時建叢集（TCP `localhost:55439`、僅本輪使用），跑完以 `pg_ctl stop` 停掉。

| 檢查 | 實際結果 |
|---|---|
| `schema_rbac.sql` 全新資料庫套用兩次 | 兩次 rc=0（`K)` 的 `ON CONFLICT` 可重跑） |
| `verify_memory_schema.sql`（含 `S13`） | rc=0，`S13` 通過（後續單元新增的 `S14`／`S15` 一併通過） |
| `verify_purge_sql.sql`（`R1`–`R10`，於 repo 根目錄） | rc=0，「R1-R10 全部通過」 |
| `tests_pg.test_purge_atomicity` | `Ran 3 tests` / `OK` |
| `seed_retention_system_actor.py`（列已存在的重跑路徑） | rc=0，終檢三項通過，未輸出 `DATABASE_URL` |
| `tests.test_retention_purge_contract` | `Ran 10 tests` / `OK` |
| `git diff --stat HEAD -- backend/database.py` | 空 |

計畫 1.4（開工前「尚無 `K)` 標題」）是開工時的前置條件；現況為**恰好一個** `K)` 標題（`schema_rbac.sql:811`），無重複字母，故勾回。Step 11（突變）在計畫中無勾選框，前輪結果見本檔第四節，本輪未重跑。後續單元的合法改動：`ci.yml` 的 `memory-schema` job 已擴充為 `P1-P16` 等步驟，`verify_purge_sql.sql` 步驟仍在（`ci.yml:543`）。

### 二、第 11 項（Step 13）——已完成

| 檔案 | 改動 |
|---|---|
| `backend/services/system_accounts.py`（新） | `RETENTION_SYSTEM_ACTOR_USERNAME`、`RESERVED_SYSTEM_USERNAMES`、`RESERVED_ACCOUNT_CONFLICT_DETAIL`、`is_reserved_system_account(user)`（大小寫敏感逐字比對）。不讀 DB、不 raise `HTTPException` |
| `backend/services/user_router.py` | 新 `ReservedAccountConflict` model 與 `_reserved_account_response()`；`GET /list` 查詢層排除（:846，`total` 與分頁共用同一基底查詢）；`POST /authorization-requests/{id}/approve`（:925）、`.../reject`（:974）、`PUT /{id}/active`（:1055）、`DELETE /{id}`（:1173）、`PUT /{id}/role`（:1243）對保留帳號回 409。疊加在 `hierarchy-data`（刪除預檢 409）與 `membership-service`（停用 500／503）之上，未覆蓋它們 |
| `openapi.json`、`frontend/src/types/api.d.ts` | 重 dump／重產 |
| `DEPLOY.md` §2.2.11 | 「它會出現在 Admin 使用者清單上」一段在本修正後為假，改寫為新的保護範圍與其邊界（同一事實的傳播，非第 17 項的過渡程序） |

409 的回應形狀：刪除與拒絕沿用既有宣告的 `DeleteUserConflict`（`blocking_references` 為空清單）；改角色與核准宣告 `ReservedAccountConflict`；啟停用的 409 宣告改為 `Union[LastAdminGuardReport, ReservedAccountConflict]`——原守門報告形狀不變（`MemberDetailPage` 依賴它），`npx tsc -b` rc=0。

新測試 `backend/tests/test_system_account_protection.py`（含結構化規格註解）：A1 刪除 409 且列仍在；A2 改角色 409 且角色仍為 `system`；A3 啟用 409 且仍停用；A4 列表分兩頁取回皆 `total=2`、聯集恰為兩位一般使用者；A5 以 AST 從 seed 腳本解析 `SENTINEL_USERNAME` 與常數比對；A6 拒絕授權申請 409、帳號與 pending 申請皆不動；A7 保留名的全小寫變體停用帳號仍可刪除（判定未被放寬）。`Ran 7 tests` / `OK`。

突變（每項先 `grep -c MUTATION-MB11` 確認寫入＝1，還原後＝0）：

| 突變 | 結果 |
|---|---|
| 刪除端點的保留判定改為 `if False:` | A1 紅：`AssertionError: 200 != 409 : {"ok":true,"deleted_username":"SYSTEM.retention-purge"}`；還原後 7/7 綠 |
| 列表基底查詢拿掉排除條件 | A4 紅：`AssertionError: 3 != 2`；還原後 7/7 綠 |

### 三、第 17 項（Step 14）——**未執行，待重新裁決**

裁決是「併入 `main` 前以 `workflow_dispatch`、`ref=ut` 手動觸發過渡」。執行前查證發現它**做不到**：GitHub 文件 *Events that trigger workflows* 的 `workflow_dispatch` 一節逐字為「This event will only trigger a workflow run if the workflow file exists on the default branch」（與 `schedule` 同一句），而 `git ls-tree --name-only origin/main .github/workflows/` 沒有 `memory-retention-purge.yml` 與 `memory-retention-watchdog.yml`（`origin/ut` 目前亦無）。照該程序操作，手動觸發會因找不到 workflow 而失敗。附帶：監看只計 `status=success&event=schedule` 的 run（`memory-retention-watchdog.yml:124`），過渡期內手動觸發的監看必然判為逾期並開 issue，不提供訊號。

依指示，裁決會製造新的正確性問題時停下回報、不自行改變裁決：`DEPLOY.md` 的過渡程序**未寫入**（寫一份做不到的程序比不寫更糟），`merge-blockers.md` 第 17 列記為「待重新裁決」，計畫 Step 14 兩格與 Step 15 第二格維持未勾。

### 四、各命令實際結果

| 命令 | 結果 |
|---|---|
| `cd backend && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests` | `Ran 1241 tests in 94.345s` / `OK` |
| `backend/.venv/bin/python backend/scripts/dump_openapi.py` → `--check` | 「規格檔與後端程式碼一致。」rc=0 |
| `cd frontend && npm run gen:types` → `npm run check:types` | 「API 型別檔與規格檔一致。」rc=0 |
| `cd frontend && npx tsc -b` | rc=0 |
| `python3 scripts/validate_repo_contract.py` | passed |
| `python3 scripts/validate_env_contract.py` | passed |

### 五、未驗項與偏離

- **偏離（擴充）**：計畫只點名拒絕路徑；核准授權申請也會改保留帳號的角色，故同樣擋下並宣告 409（正常流程不會為它產生申請，屬縱深防禦）。啟停用的 409 擋下**兩個方向**（重送停用會觸發與它無關的自動改選）。
- **未涵蓋（新發現）**：`GET /api/collab/users`（`collab_router.py:304`，分享對象清單）仍列出保留帳號；`team.md` 反對趁機改動 `collab_router.py`，記為後續項。資料庫層直接 `DELETE` 不受應用程式保護。
- `openapi.json`／`api.d.ts` 相對 `HEAD` 的 diff 也含先前單元（`hierarchy-data`、`membership-service`）尚未 commit 的改動，本輪無法把自己的差量從工作樹中單獨分離；`--check` 與 `check:types` 皆綠。
- `OPEN-ND9-1`（系統 actor 出現在 Admin 清單）由本輪處置關閉。

### 第 17 項重新裁決（conductor，`2026-10-22T23:26:39Z`）

上節記載的「2026-10-20 裁決無法執行」由 conductor 向使用者說明（`workflow_dispatch` 同樣要求 workflow 檔在預設分支上），並指出關鍵事實：記憶是本分支新增的功能，部署前沒有任何記憶列，第一筆最早要在部署後 90 天才到期。使用者重新裁決：**接受延後，設期限——本分支第一次部署到 staging 後，`ut` 須在 90 天內併入 `main`**。

處置：不改程式與 workflow；`DEPLOY.md` §2.2.11 補寫手動觸發同樣不可行、期限與理由、以及「部署日＋90 天」須記在可見位置；`merge-blockers.md` 第 17 列改為「以期限處置，屬持續中的人工義務」；`traceability.json` 的 `MB-17` 維持 `Deferred` 並更新說明。

**計畫 Step 14 兩格維持未勾**：其字面內容（手動觸發程序、「每週手動觸發」的人工義務）已被重新裁決取代，勾上會讓計畫宣稱一件沒有做、也做不到的事。Step 15 第二格（紀錄回填）於本節完成後勾上。

### 審查後補正（conductor，`2026-10-22T23:32:29Z`）

本站審查（`reviews/review-03.md`）判定 READY（1 Major、3 Minor）。審查查證了 #17 的前提成立（`origin/ut` 的 `schema_rbac.sql` 無 `memory_records`；唯一寫入路徑 `memory_service.create_record` 設 `expires_at = created_at + 90 天`）。

| 發現 | 處置 |
|---|---|
| Major：新裁決使 `workflow_dispatch` 在併入 `main` 前不可用，而排程一律真實清除，`OPEN-ID9-4` 的「首次真實清除前先 dry-run」失去順序 | `DEPLOY.md` §2.2.11 補寫順序：併入 `main` 後**立即**在 `main` 上 `dry_run=true` 跑一次；因部署日＋90 天前排程選取皆為零列，dry-run 仍先於第一次實際刪除；若已有測試資料使計數不為 0，先停用排程再核對。`traceability.json` 的 `OPEN-ID9-4` 說明同步更新 |
| Minor 4：期限沒有負責人 | `DEPLOY.md` 指名負責人 Danniel，唯一記錄位置為部署當天開立的 GitHub issue |
| Minor 2：核准申請路徑無測試；改角色／啟用／拒絕未做突變 | 未處置，以已接受風險進入紀錄 |
| Minor 3：`GET /api/collab/users` 仍列出保留帳號 | 未處置（不影響清除完整性；`team.md` 反對趁機改 `collab_router.py`），以已接受風險進入紀錄 |

## 重做（Code Generation 自頭重來，2026-10-25）

<!-- 寫入時間：2026-10-25T07:32:06Z（`date -u` 取值） -->

Code Generation 依使用者裁決自頭重來；本單元計畫重新核可後，逐步查驗既有程式碼，**程式碼改動為 0**。後續單元對共用檔的改動一律保留。**安全**：本輪未觸發任何 workflow，未連任何共用或 staging 資料庫，清除 SQL 只在 scratchpad 的一次性資料庫上執行。

### 計畫 51 格：勾 45、留 6

| 格 | 理由 |
|---|---|
| Step 1.4「目前沒有 `K)`」 | 開工前的前置檢查，`K)` 現已存在，照字面不可能成立；其目的（無重複字母）成立：`grep -c "^-- K) "` 為 1 |
| Step 2.6「role 不在 `CANONICAL_ROLES`」 | 實作改以資料庫 `role_permissions` 判定（`seed_retention_system_actor.py` 的 `verify_postconditions`），理由寫在程式內：import `services.rbac` 會經 `auth._resolve_secret_key`，在 staging 可能崩潰；`CANONICAL_ROLES` 的字面比對改由 `test_sentinel_role_is_not_canonical` 承擔 |
| Step 8.1 `--env-file deploy/.env` | 實作為 `--env-file deploy/.env.example`（`memory-retention-purge.yml:188`）：`deploy.yml` 每次部署結束會刪除 `deploy/.env`（`:632`、`:726`），照計畫寫每天都會失敗；實際連線帳號與資料庫由容器內讀取，不依賴範本值（理由見 workflow `:34-65`、`:180-182`）。8.1 其餘項目皆成立 |
| Step 13 第四格 | 測試 A1–A7 皆通過，但框內含突變驗證，本輪未重跑 |
| Step 14 兩格 | 「`ref=ut` 手動觸發過渡、每週手動」已被 2026-10-23 的 90 天期限裁決取代（`workflow_dispatch` 同樣要求 workflow 檔在 `main`）；`DEPLOY.md` 與 merge-blockers 第 17 列寫的是新裁決 |

### 合併前必修第 11、17 項

- **#11**：`system_accounts.py` 與 `user_router.py` 對保留帳號回 409——刪除 `:1173`、改角色 `:1243`、啟用 `:1055`、拒絕申請 `:974`、核准 `:925`；清單於查詢層排除（`:846`，`total` 亦排除）。`test_system_account_protection.py` 7 個測試全綠。仍未涵蓋（第 11 列已記）：`GET /api/collab/users` 仍列出它、資料庫層直接 DELETE 仍可行。
- **#17**：`DEPLOY.md:1140-1158` 載明 `workflow_dispatch` 同樣需要檔案在 `main`、首次部署 staging 後 90 天內 `ut` 須併入 `main`、負責人、以 issue 記錄期限、併入後先 dry-run。**附帶後果**：watchdog 只計 `event=schedule` 的成功 run，故在 `ut` 併入 `main` 之前它一旦執行就會判逾期並開 issue——第 17 列有寫，`DEPLOY.md` 的期限段落未明講。

### 測試與閘門（本輪實跑，`backend/.venv`，快取導向 scratchpad，未寫入 repo）

| 指令 | 結果 |
|---|---|
| `tests.test_retention_purge_contract` ＋ `tests.test_system_account_protection` | `Ran 17 tests`、`OK` |
| `discover -s tests` | `Ran 1319 tests`、`OK (skipped=3)` |
| `dump_openapi.py --check`、`npm --prefix frontend run check:types` | 皆一致 |
| `validate_repo_contract.py`、`validate_env_contract.py` | 皆 passed |
| PG：`schema_rbac.sql` 套用兩次 | 兩次 exit 0 |
| PG：`verify_memory_schema.sql` | S1–S15 全部通過（含 S13） |
| PG：`verify_purge_sql.sql`（repo 根執行） | 刪除記憶 1 列、寫稽核 1 列、刪除舊稽核 1 列，R1–R10 全部通過 |
| PG：`tests_pg.test_purge_atomicity` | `Ran 3 tests`、`OK` |
| PG：`seed_retention_system_actor.py`、`purge_dry_run.sql` | 終檢通過；dry-run exit 0，系統帳號 1 列、`all_inactive` 為 t |

PG 環境：Homebrew PostgreSQL **17.7** ＋ pgvector 0.8.1，scratchpad 一次性叢集，只走 TCP（`127.0.0.1:55439`，Unix socket 路徑超過 103 bytes 上限故停用）；跑完 `pg_ctl stop`、刪除資料目錄、無殘留程序。CI 用 pg18。

### 與已核可計畫／測試說明的落差（凍結文件不改，以本節為準）

- 計畫 §2 說 `run_meta_schema_migration.py`「只加註解」，實際另有 `BLOCK_SENTINELS["K"]`（`:120-130`）這筆資料，不改變執行行為；`BLOCKS_TO_RUN` 仍為 `("X","I","J")`。
- Step 3.1 的「非 canonical」同樣以 `role_permissions` 判定（SQL 看不到 Python 常數）。
- Step 6.2 第二個測試名為 `test_committed_purge_writes_one_audit_row_per_deleted_memory`，與計畫字面不同、與測試說明一致。
- 測試說明 §3.1 列 8 條，實為 10 條；第 11 項測試列 A1–A5，實為 A1–A7。
- 行號：`schema_rbac.sql:715`→`:886`、`:478`→`:511`、`:460-461`→`:473`；`user_router.py:403/406/408`→約 `:716/:719`；`memory-retention-purge.yml` 註解引用的 `deploy.yml:376-378/472`→`:632/:726`、`:124/:471`→`:129/:725`（皆為註解或文件，事實本身仍成立）。

`source-manifest.json` 的 18 條路徑全部存在且仍屬本單元；`backend/services/system_accounts.py` 與 `backend/tests/test_system_account_protection.py` 目前為 untracked，**提交時須一併納入**。

## 共用檔異動後的重新驗證（計畫 §十一，2026-10-29 使用者裁決）

<!-- 寫入時間：2026-10-30T15:57:08Z（`date -u` 取值） -->

本輪只做重新驗證與紀錄：**程式碼、workflow、共用檔改動皆為 0**；`merge-blockers.md` 未動。未觸發任何 workflow、未連任何資料庫、未跑 `tests_pg` 與 `psql`。本輪寫入的檔只有本檔、`code-generation-plan.md` 的勾選、`traceability.json`（新增 `OPEN-CG9-6`，見第三節）。

### 一、`DEPLOY.md` 重驗

**收據比對**：最新收據 `reviewed-source-dec2b735dbb4.tsv`（2026-10-25）列 18 檔，逐檔 `shasum -a 256` 與現況比對：**17 檔逐位元相同**，只有 `DEPLOY.md` 不同（收據 `2608a131…`、現況 `d9b0571c…`）。`git diff --stat HEAD -- DEPLOY.md` 為空，現況即 `HEAD`（`c6a40f9`）；該檔最後一次異動在 `7a50a40`（2026-10-27）。

**找出收據之後新增的 hunk（獨立驗證，不依賴他單元結論）**：收據版不在任何 commit 內（它是 `7a50a40` 之前的工作樹），故改用撤回組合法——以 `difflib` 取 `624c170:DEPLOY.md` → `HEAD` 的全部 19 個 hunk，窮舉 2^19 = 524,288 種撤回子集合，各自計算 sha256 與收據比對。**恰有一組吻合：{h3, h17, h18}**，即收據之後新增的正是這三處（腳本：scratchpad `mp_deploy_combo.py`，只讀 repo）。

| hunk | 現況行號 | 所屬章節（章節範圍） | 內容 |
|---|---|---|---|
| h3 | `DEPLOY.md:730-738`（原 3 行 → 9 行） | §2.2.9 U18 專案中繼資料（`:617-950`） | 「誠實的代價」改寫：忘了跑遷移時 `create_all()` 會建出三表、只缺 COMMENT；`U20` 欄位收斂缺失時帶代寫標示的寫入以 500 出現 |
| h17 | `DEPLOY.md:2229` | §5.13 入口頁部署後實測（`:2223-2254`） | 6a 失敗只回滾、不開 revert PR 的機制說明 |
| h18 | `DEPLOY.md:2239` | §5.13 | 同上，Cloudflare 剝除的處置改為只還原 last-good |

**判定：三處都沒有碰到本單元負責或引用的段落。**

- 本單元負責的 §2.2.11 為 `DEPLOY.md:1074-1181`，三個 hunk 都在其外。
- 本單元引用的其他段落：§2.2 表格的 `K` 列（`DEPLOY.md:252`，在 h3 之前，不受影響）、§2.1（`seed_retention_system_actor.py:145` 的錯誤訊息「既有環境見 DEPLOY.md 第 2.1 節」；§2.1 為 `:189-231`，不受影響）。
- **唯一副作用是行號位移**：h3 使 `:739-2228` 之間的內容相對收據**下移 6 行**。§2.2.11 的內容逐位元未變，但本檔先前引用的收據時點行號因此失效——重做節（2026-10-25）寫的 `DEPLOY.md:1140-1158` 現為 `:1146-1164`（第 17 項期限段，h13 於 `HEAD` 的範圍為 `:1147-1164`）；review-04 R-03 的 `:1138-1154`、R-07 的 `:1132-1155` 同樣各需 +6。事實本身不變。

### 二、回歸（scratchpad 副本）

`rsync`（排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis`）至 scratchpad `mp-copy/`，以 `backend/.venv` 的直譯器、`-B -P`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=<副本>/backend` 執行：

| 指令 | 結果 |
|---|---|
| `unittest -v tests.test_retention_purge_contract tests.test_system_account_protection`（`unit-test-instructions.md` §2.1） | **`Ran 17 tests`、`OK`**（契約 10 ＋ 保護 A1–A7） |
| `unittest discover -s <副本>/backend/tests -t <副本>/backend`（為重驗計畫 Step 12.5／Step 15 的「全綠」宣稱而加跑） | **`Ran 1326 tests`、`OK (skipped=3)`**（前一輪 1319；差 7 案，推測來自收據後他單元的測試增加，**本輪未逐案核對來源**；本單元兩檔仍為 17 案） |

路徑確認：載入前先印出 `tests.test_retention_purge_contract`、`tests.test_system_account_protection`、`services.user_router` 的 `__file__`，三者皆在副本內；兩支測試以 `Path(__file__)` 取檔，故讀的也是副本。完整套件輸出中有 5 段 traceback（1 段 `run_hierarchy_migration.py` 的終檢失敗分支、4 段 `membership_service.py:1077` 的 `run_auto_reselection`），皆為被測程式以 log 記錄的例外、套件整體 `OK`，路徑全在副本內；指向原 repo 的 191 筆皆為直譯器的 `.venv/site-packages`，指向原 repo 原始碼者 0 筆。

**副產物處置（如實揭露）**：完整套件以原 repo 根為工作目錄執行，Hypothesis 因此在原 repo 根建立 `.hypothesis/`（23:51 建立、自帶 `*` 的 `.gitignore`，故 `git status` 看不到）。它不在本輪允許寫入的範圍內，且會改變引擎的 workspace source 指紋（`project.md` 已記載的死結成因），故已 `rm -rf` 移除；之後以 `find -newer` 確認原 repo 自本輪開始只剩引擎自身檔與本 record 的異動。

**`tests_pg`（§2.2）與 `psql`（§2.3）本輪未跑**（需真實 PostgreSQL），沿用 2026-10-25 重做節的紀錄：`tests_pg.test_purge_atomicity` `Ran 3 tests`、`OK`；`verify_purge_sql.sql` R1–R10 全部通過；`verify_memory_schema.sql` S1–S15 全部通過。這三者的被測檔（`purge_expired_memory.sql`、`verify_purge_sql.sql`、`verify_memory_schema.sql`、`test_purge_atomicity.py`、`schema_rbac.sql`）自收據後逐位元相同，故前輪結論的前提未變。

`validate_env_contract.py`：passed（本輪實跑）。`git diff --stat 624c170 HEAD -- backend/database.py` 與工作樹皆為空。

### 三、review-04 未結發現逐項複核（已知限制，由 conductor 併入 `merge-blockers.md`；已有對應列者引用之）

| ID | 現況（本輪附行號重驗） | 仍成立？ | 既有 merge-blockers 列是否涵蓋 |
|---|---|---|---|
| R-01 | `backend/tests_pg/test_purge_atomicity.py:58` 仍手寫 `SENTINEL_USERNAME = "SYSTEM.retention-purge"`（`:146`、`:149`、`:174`、`:384`、`:412` 使用）；`test_sentinel_username_has_one_source` 只解析 seed 腳本（`test_retention_purge_contract.py:379`）、`K)` 區塊與清除 SQL，未涵蓋此第四處。另 `backend/services/system_accounts.py` 的 `RETENTION_SYSTEM_ACTOR_USERNAME` 為第五處，由 A5 鎖住與 seed 腳本相等 | **成立**（需改測試檔，本輪不改） | **無**。第 11 列只談保留帳號的端點保護，未提哨符副本 |
| R-02 | `backend/services/auth.py:37-40` 的 `verify_password` 仍直接 `return bcrypt.checkpw(...)`、無 try/except；超過 72 位元組的密碼對既有帳號拋 `ValueError` → 500 | **成立**（既有缺陷，不屬本單元） | **無**。仍僅以 `traceability.json` 的 `OPEN-CG9-2` 另案追蹤（`landing`：擁有 `auth.py` 的後續單元或 intent）。確認仍為另案追蹤；未見對應 issue 或 merge-blockers 列 |
| R-04 | `backend/tests/test_system_account_protection.py` 仍只有 7 個測試（`:84`、`:100`、`:116`、`:132`、`:159`、`:172`、`:199`），**無核准授權申請案例**；`user_router.py:885` 的 `/approve` 路由在 `:925` 擋保留帳號，無斷言保護。改角色（`:1243`）、啟用（`:1055`）、拒絕（`:974`）三處從未做過突變；`PUT /active` 以 `is_active=false` 重送亦無斷言 | **成立**（需改測試，本輪不改） | **部分**。第 11 列列出核准 `:925` 為已修正入口，且只宣稱兩項突變（刪除、列表），未宣稱核准有測試——敘述正確，但「核准無測試、三處未突變」這個缺口本身未登記 |
| R-05 | `backend/services/collab_router.py:298-303`，`get_users` 以 `User.id != current_user.id` 列出全部使用者，未排除保留帳號 | **成立**（不得在本單元改 `collab_router.py`） | **有**：第 11 列處置欄「**未涵蓋**：`GET /api/collab/users`（分享對象清單）仍列出它」。R-05 要求的「有承接者的 `open_items` 條目」本輪已補：`traceability.json` 新增 `OPEN-CG9-6` |
| R-07 | `memory-retention-watchdog.yml:124` 仍查 `status=success&event=schedule`，查無成功 run 時 `:141` 寫 `state=never`、`:174-176` 判逾期；404 亦判逾期（`:128-130`）。`DEPLOY.md` 全檔 `grep` 「假警報／第一天／首次執行」**0 命中**——併入 `main` 第一天（監看 06:23 UTC 早於清除 17:41 UTC）的假警報仍未記載。本檔重做節（上方「合併前必修第 11、17 項」小節 `#17` 那一點）寫「在 `ut` 併入 `main` 之前它一旦執行就會判逾期並開 issue」——**方向錯誤，以本列為準**：併入前兩支 workflow 都不在 `main`、不會執行；風險在併入後第一天。`merge-blockers.md` 第 17 列逐字核對**沒有**這句錯誤說法（它寫的是「監看只計 `event=schedule` 的成功 run，手動清除不會讓它轉綠」，正確），故只有本檔需更正 | **成立**（需改共用檔 `DEPLOY.md`，本輪不改） | **部分**。第 17 列涵蓋「併入 `main` 前排程不跑」與期限，未涵蓋併入後第一天的假警報 |
| R-08 | `memory-retention-purge.yml:38`、`:42-43`、`:74`、`:88`、`:166` 的 `deploy.yml` 行號引用（`376-378`、`472`、`124/471`、`20-22`、`149`）仍是舊值。`deploy.yml` 已再漂移：「Remove the generated env file」現為 `:640`、其 `rm -f deploy/.env` 為 `:642`，rollback 的 `rm -f deploy/.env` 為 `:737`（review-04 寫的 `:630-632`／`:726` 與重做節寫的 `:632`／`:726` 也都已過期）。事實本身仍成立 | **成立**（需改 workflow 註解，本輪不改） | **無** |
| R-09 | `memory-retention-purge.yml:188` 的 `COMPOSE=(… --env-file deploy/.env.example)`、`:192` 的 `ps --status running --services \| grep -qx db`、`:199` 的 `PGUSER="$POSTGRES_USER" PGDATABASE="$POSTGRES_DB"` 這條容器路徑仍從未實際執行；`DEPLOY.md` 全檔 `grep` 「煙霧／smoke」**0 命中**，§2.2.11 的併入後 dry-run 步驟（現 `DEPLOY.md:1158-1164`）只要求核對計數，未要求確認這條路徑成功 | **成立**（需改共用檔 `DEPLOY.md`，本輪不改） | **部分**。第 17 列與 `OPEN-ID9-4` 涵蓋「併入後先 dry-run」，未把它定義為 compose 路徑的首次煙霧測試 |

**彙總給 conductor**：R-01、R-02、R-08 無任何 merge-blockers 列涵蓋；R-04、R-07、R-09 部分涵蓋於第 11／17 列但缺口本身未登記；R-05 已由第 11 列涵蓋。

### 四、勾選重設

基準：2026-10-25 重做節「計畫 51 格：勾 45、留 6」。本輪判準：證據相關檔案自收據後逐位元相同，或本輪重驗。

- **重勾 45 格**：Steps 1–12、13、15 的證據檔中只有 `DEPLOY.md` 變動，而唯一依賴它的 Step 12.1（§2.2.11）已於第一節重驗未受影響。另於本輪重驗：1.1（`backend/tests_pg/__init__.py:60` 的 `require_pg_url` 存在）、1.3／12.5（`backend/database.py` 無異動）、12.5／Step 15 第一格（完整套件 1326 案綠、`validate_env_contract.py` passed、`validate_repo_contract.py` 見第五節）、Step 13 第五格（`openapi.json`、`frontend/src/types/api.d.ts` 自收據後逐位元相同）、Step 15 第二格（`merge-blockers.md` 第 11、17 列處置仍在，`:20`、`:26`）。
- **維持未勾 6 格**（理由與前輪相同，本輪複核仍成立）：Step 1.4（`K)` 已存在，`grep -c "^-- K) " schema_rbac.sql` 為 1，前置條件照字面不可能成立，目的仍成立）；Step 2.6（以 `role_permissions` 判定而非 `CANONICAL_ROLES`）；Step 8.1（`--env-file deploy/.env.example`，`memory-retention-purge.yml:188`；`deploy.yml` 現於 `:642`、`:737` 刪除 `deploy/.env`）；Step 13 第四格（框內突變本輪未重跑，且 R-04 指出核准無測試）；Step 14 兩格（已被 2026-10-23 的 90 天期限裁決取代）。
- **§十一 五格**：本輪完成，全勾。

`grep -c` 實算全檔：**已勾 50、未勾 6**（共 56 格 ＝ 舊 51 ＋ §十一 5）。

### 五、收尾

- `traceability.json`：新增 `open_items` 的 `OPEN-CG9-6`（R-05 的 `GET /api/collab/users`），`python3 -m json.tool` 驗證為合法 JSON。其餘條目未動。
- `python3 scripts/validate_repo_contract.py`（repo 根，本節寫入後實跑）：`Cloud-360 repository contract validation passed.`

## 2026-11-07 第 32 列剩餘項

<!-- 寫入時間：2026-11-07T01:35:30Z（`date -u` 取值） -->

依計畫 §十二執行合併前必修第 32 列中交給本單元的 (a)(c)(e)，並查證 (b)(d)(f)。**只改測試檔、`tests_pg` 檔、workflow 註解與本 record**；`user_router.py`、`DEPLOY.md`、`merge-blockers.md` 及其他共用檔未動。未觸發任何 workflow、未連任何資料庫／Redis／網路服務、未用 `gh` 寫入、未 commit。

### 一、改動檔:行

| 檔 | 改動（現行行號） |
|---|---|
| `backend/tests_pg/test_purge_atomicity.py` | `:51-60` 新增 `from services.system_accounts import RETENTION_SYSTEM_ACTOR_USERNAME as SENTINEL_USERNAME`（附註解）；刪除原 `:58` 的手寫 `SENTINEL_USERNAME = "SYSTEM.retention-purge"`。其餘用法（`SENTINEL_USERNAME` 五處）不變 |
| `backend/tests/test_retention_purge_contract.py` | `:51-55` 加 `ast`／`os`／`warnings` import；`:142-186` 新增 `SENTINEL_LITERAL_ALLOWLIST`（`:149`）、`_PY_SCAN_SKIP_DIRS`、`py_string_constant_hits()`（`:162`，AST 走訪、整個字串字面值相等才算、不跟隨 symlink、解析失敗即大聲失敗）；`test_sentinel_username_has_one_source`（`:406`）的 docstring 補 §4.4 規格註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`，無端點無 UI 故不寫 `@api`／`@ui`），`:455-475` 加全 repo `.py` 掃描兩道斷言：允許清單外不得出現、允許清單不得過期 |
| `backend/tests/test_system_account_protection.py` | `:199` 新增 A8 `test_approve_authorization_request_cannot_promote_reserved_account`；`:231` 新增 A9 `test_resend_deactivate_of_reserved_account_is_rejected`。兩者皆附 §4.4 規格註解 |
| `.github/workflows/memory-retention-purge.yml` | `:38-40`、`:43-46`、`:58`、`:77`、`:91-92`、`:170-172`：`deploy.yml` 的行號引用改為 job／步驟名或 key（`Build and start the stack`、`Remove the generated env file`、`Restore the last-good deployment`、`Set the memory-only database role password`、`concurrency.group`）。另把 `:58` 的 `deploy/docker-compose.deploy.yml:345`（現實為 `:405`，同樣過時）改為「service `cloudflared`」——同檔同類，超出計畫字面一處，於此揭露 |

`.github/workflows/memory-retention-purge.yml` 只動註解的證明：`git diff -U0` 中非 `#` 開頭的增刪行 **0**；以 `backend/.venv` 的 `yaml.safe_load` 載入 `git show HEAD:` 版本與現行版本，結果 `yaml equal: True`。改後全檔 `grep -n 'deploy\.yml:[0-9]'` 為 0 命中。

### 二、測試輸出（scratchpad 的 rsync 副本，`backend/.venv/bin/python -B`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=.`、`HYPOTHESIS_STORAGE_DIRECTORY` 指向副本外的 scratchpad 目錄）

副本以 `rsync -a` 排除 `.git`、`node_modules`、`.venv`、`__pycache__`、`.hypothesis` 建立（`.venv` 一併排除：直譯器直接用 repo 的 `backend/.venv`，且掃描本來就略過 `.venv`）；跑前 `diff -rq` 副本 `backend/` 與 repo `backend/` 無差異。

| 指令 | 實跑結果 |
|---|---|
| `unittest -v tests.test_retention_purge_contract tests.test_system_account_protection`（§2.1） | `Ran 19 tests in 2.607s`、`OK`（契約 10 ＋ 保護 A1–A9；前一輪 17） |
| `unittest discover -s tests` | `Ran 1377 tests in 100.176s`、`OK (skipped=3)`（前一輪 1326；差額來自他單元新增測試與本輪 2 案，未逐案核對來源） |
| `tests_pg.test_purge_atomicity` 不連資料庫 import（`env -u DATABASE_URL`） | `imported …/dev-u9/backend/tests_pg/test_purge_atomicity.py`；`SENTINEL_USERNAME is canonical: True`。**未跑**（需真實 PostgreSQL） |
| `scripts/dump_openapi.py --check`（副本） | `規格檔與後端程式碼一致。` |
| `npm --prefix frontend run check:types`（repo；只寫 OS 暫存目錄） | `API 型別檔與規格檔一致。` |
| `python3 -B scripts/validate_repo_contract.py`（repo） | `Cloud-360 repository contract validation passed.` |
| `python3 -B scripts/validate_env_contract.py`（repo） | `Cloud-360 environment configuration contract validation passed.` |

完整套件輸出中有 `ERROR:cloud360.*` 開頭的 log 行（如 `session_backend_unavailable … redis_unreachable`、`hierarchy migration 失敗`、`mcp_bridge startup_failed`），皆為被測程式以 log 記錄的預期失敗分支，套件整體 `OK`。

repo 內快取數前後：`pyc=243 pycache=14 hyp=1` → `pyc=243 pycache=14 hyp=1`（不變；那一個 `.hypothesis` 為既存的 `backend/.hypothesis`，非本輪產生，`find -newer` 本輪起點標記檔為 0 筆）。副本與 Hypothesis 目錄已刪除。

### 三、突變驗證（全部在副本；每次以 `cp` 還原後 `cmp` 與 repo 原檔逐位元相同）

| # | 突變 | 紅燈的測試 | 還原後 |
|---|---|---|---|
| a | `tests_pg/test_purge_atomicity.py:68` 重新手寫 `SENTINEL_USERNAME = "SYSTEM.retention-purge"` | `test_sentinel_username_has_one_source`：`AssertionError: Lists differ: ['backend/tests_pg/test_purge_atomicity.py:68'] != []`（`Ran 10`、`FAILED (failures=1)`） | `cmp` 相同；`Ran 10`、`OK` |
| c1 | `user_router.py:975`（核准）的 `if is_reserved_system_account(target):` → `if False:` | A8 `test_approve_authorization_request_cannot_promote_reserved_account`（`FAILED (failures=1)`）。**新增 A8 之前沒有任何測試會紅**（其餘 8 案在此突變下皆綠） | `cmp` 相同 |
| c2 | `:1024`（拒絕）同上 | A6 `test_reject_authorization_request_cannot_delete_reserved_account`（`failures=1`） | `cmp` 相同 |
| c3 | `:1106`（啟停用）同上 | A3 `test_activate_reserved_account_is_rejected` ＋ A9 `test_resend_deactivate_of_reserved_account_is_rejected`（`failures=2`） | `cmp` 相同 |
| c3' | `:1106` 收窄為 `… and request.is_active:`（只擋啟用方向） | 只有 A9 紅（`failures=1`）——A3 綠，故 A9 是抓這個變體的唯一測試 | `cmp` 相同 |
| c4 | `:1295`（改角色）同上 | A2 `test_change_role_of_reserved_account_is_rejected`（`failures=1`） | `cmp` 相同 |
| c5 | `:1224`（刪除）同上（計畫只要求四處，順帶重跑） | A1 `test_delete_reserved_account_is_rejected_and_row_survives`（`failures=1`） | `cmp` 相同 |
| c6 | `:896` 清單排除 `.filter(User.username.notin_(…))` 拿掉（為重勾 Step 13 第四格而重跑） | A4 `test_list_excludes_reserved_account_from_items_and_total`（`failures=1`） | `cmp` 相同 |

全部還原後 `tests.test_system_account_protection`：`Ran 9 tests`、`OK`。**守門本身未發現缺陷**，`user_router.py` 未改。

### 四、(b)(d)(f) 查證

- **(b)**：`backend/services/auth.py:37-40` 的 `verify_password` 仍直接 `return bcrypt.checkpw(...)`，無 try/except；`traceability.json` 的 `OPEN-CG9-2`（`kind: pre-existing-defect`）仍在且內容未改。本輪未改、未開 issue。
- **(d)**：`DEPLOY.md:1250-1260` 記載假警報辨識。與 workflow 逐項核對一致：issue 標題 `[memory-retention] 90 天清除已逾期未成功執行` ＝ `memory-retention-watchdog.yml:101` 的 `ISSUE_TITLE_PREFIX`；原因句 ＝ `:176` 的 `reason=找不到任何一次成功的排程清除（status=success 且 event=schedule）。`；`state=never` ＝ `:141`；監看 06:23 UTC ＝ `:56` 的 `23 6 * * *`、清除 17:41 UTC ＝ `memory-retention-purge.yml:112` 的 `41 17 * * *`；「監看者只去重、不自動關閉」——watchdog 全檔無 `gh issue close`。附註（非不一致）：監看另有第三種原因 `:180`（讀不到清除 workflow 的執行歷史），只在 workflow 不在預設分支時出現，併入 `main` 當天不會發生，故 `DEPLOY.md` 的辨識條件 (1) 仍足以區分。
- **(f)**：`DEPLOY.md:1244-1249` 把併入 `main` 後的 `workflow_dispatch` ＋ `dry_run=true` 定為首次煙霧測試、失敗即 Disable workflow。輸入名 `dry_run` ＝ `memory-retention-purge.yml:115`（`type: boolean`、`default: true`）；dry-run 走 `purge_dry_run.sql` ＝ 同檔 Decide 步驟。一致。

**結論**：(d)(f) 與 workflow 實際行為一致，無須登記已知限制。

### 五、勾選重設

基準為前一輪「已勾 50、未勾 6」；本輪計畫共 62 格（舊 56 ＋ §十二 6）。最新收據 `reviewed-source-8ece40a809de.tsv`（2026-10-31）18 檔逐檔 `shasum -a 256`：**相同 7 檔**（watchdog、`purge_dry_run.sql`、`purge_expired_memory.sql`、seed 腳本、`verify_memory_schema.sql`、`verify_purge_sql.sql`、`system_accounts.py`）、**不同 11 檔**（`ci.yml`、`memory-retention-purge.yml`、`DEPLOY.md`、`run_meta_schema_migration.py`、`user_router.py`、兩支 `backend/tests` 測試、`tests_pg` 測試、`api.d.ts`、`openapi.json`、`schema_rbac.sql`；其中 4 檔為本輪改動，其餘為他單元改動），故依賴不同檔的格逐格以現況重驗：

- `schema_rbac.sql`：`K)` 在 `:869`，位於 `J)`（`:615`）之後、`C)`（`:924`）之前；`ON CONFLICT (username) DO NOTHING` `:918`；`COMMENT ON TABLE users` `:920-921`；檔頭 TOC `:15`、注意事項 `:43-50` → 2.1–2.4 成立。
- `run_meta_schema_migration.py`：`BLOCKS_TO_RUN = ("X", "I", "J")`（`:95`），`:101-103` 註解說明 `K` 刻意不在內 → 2.5 成立。
- `ci.yml`：`memory-schema` job（`:322`）仍有「Re-apply schema_rbac.sql (BR1.3 idempotency)」（`:369`），且 `:560-565`「Verify memory purge behaviour (R1-R10)」跑 `verify_purge_sql.sql`，位於 P1-P17 步驟之後；`concurrency` job `:649` 為 `discover -s tests_pg` → 3.2、10.1–10.4 成立。
- `DEPLOY.md` §2.2.11 現為 `:1153-1277`；表格 `K` 列 `:252`、seed 路徑 `:1185`、「不要重跑整支」更正 `:1194-1195`、驗證指令 `:1205`、排程與 dry-run 段 `:1225-1265` → 12.1 成立。
- `user_router.py`／`openapi.json`／`api.d.ts`：409 守門五處與清單排除經上表突變逐一證實；OpenAPI 與型別兩道漂移檢查一致 → Step 13 五格成立。**Step 13 第四格前兩輪未勾（框內突變未重跑），本輪已重跑刪除與清單兩項並另補四處，改為勾**。
- `tests_pg` 測試：三個測試（`:277`、`:327`、`:372`）與 `require_pg_url` 仍在，本輪只換常數來源（值以 `is` 證實為同一物件）→ 6.1、6.2 勾；**本輪未對真實 PostgreSQL 執行**，沿用 2026-10-25 重做節的 `Ran 3 tests`、`OK`。
- §十一 五格：工作已於 2026-10-30 完成並記於上一節，紀錄仍在 → 勾。§十二 六格：本節完成 → 勾。

**維持未勾 7 格**：

| 格 | 理由 |
|---|---|
| 1.3 `git diff --stat -- backend/database.py` 必須為空 | **本輪不成立（新）**：工作樹的 `backend/database.py` 有未提交的 `+72` 行（記憶專用資料庫連線，註解標為合併前必修第 20／29 列、2026-10-31 裁決；檔案 mtime 2026-11-01）。不是本單元的改動，本單元也未碰它，但計畫字面的條件不成立 |
| 1.4 確認目前沒有 `K)` | 同前輪：`K)` 已存在，前置條件照字面不可能成立；目的（無重複字母）成立 |
| 2.6 `role` 不在 `CANONICAL_ROLES` | 同前輪：實作以 `role_permissions` 判定 |
| 8.1 `--env-file deploy/.env` | 同前輪：實作為 `deploy/.env.example`（`memory-retention-purge.yml:193`） |
| 12.5 收尾核對 | **本輪不成立（新）**：驗證器兩支綠、完整套件 1377 案綠，但其中「`backend/database.py` 仍為空」一項同 1.3 不成立 |
| Step 14 兩格 | 同前輪：已被 2026-10-23 的 90 天期限裁決取代 |

`grep -c` 實算全檔：**已勾 55、未勾 7**（共 62 格）。

### 六、紀錄檔

- `traceability.json`：`upstream_ids` 加 `MB-32`；`coverage` 新增 `MB-32`（`OK`，記 (a)(c)(e) 的處置與 (b)(d)(f) 的查證）；`R-01` 的 note 改以步驟名引用 `deploy.yml`；`MB-11` 的 note 補「A8、A9」；`open_items` 新增 `OPEN-CG9-7`（第 32 列現況、merge-blockers 回填與重審交 conductor、(a) 掃描只抓整個字串字面值的範圍限制）。`python3 -I` `json.load` 驗證合法（coverage 37、open_items 8）。
- `source-manifest.json`：本輪無新檔（四個改動檔皆已列），未改。

### 七、交 conductor

1. `backend/database.py` 的未提交 `+72` 行使計畫 1.3、12.5 照字面不成立；屬第 20／29 列的工作，請確認它的歸屬與提交時機。
2. `merge-blockers.md` 第 32 列的處置欄需由 conductor 回填（(a)(c)(e) 已處置、(b) 續由 `OPEN-CG9-2` 追蹤、(d)(f) 已查證一致），並安排 memory-purge 重審。
3. `tests_pg/test_purge_atomicity.py` 的模組 docstring 仍寫 `deploy.yml:124／:471`（`:8`），屬同類過時行號，但不在 (e) 的 workflow 檔範圍內，本輪未改。

## 整站重跑後的勾選回復（2026-11-08T13:44:35Z）

- 背景：2026-11-08T06:40:14Z 使用者決定重跑整個 code-generation 階段（整站關卡因審查收據失效卡死，唯一出路）。引擎把本計畫勾選全部重設為未勾。
- 依據：以 Python `hashlib` 重算上一次審查留下、與現況最吻合的收據 `reviewed-source-7cb3888048dc.tsv`：15 同、3 變（`backend/scripts/verify_memory_schema.sql`、`frontend/src/types/api.d.ts`、`openapi.json`，交審查員判定是否碰到本單元）。本輪 `REVIEW_REQUESTED` 當下引擎另會產生一份新收據，以那份為準。既有勾選依 HEAD 版回復（差異僅勾選字元）。
- 現況（實算）：55 勾／7 未勾；未勾格沿用 HEAD 的未勾理由：
  - - [ ] 1.3 `git diff --stat -- backend/database.py` 必須為空（開工前記錄基準）
  - - [ ] 1.4 確認 `schema_rbac.sql` 目前**沒有** `K)` 區塊標題（避免 `extract_blocks` 的重複字母 `RuntimeError`）
  - - [ ] 2.6 `backend/scripts/seed_retention_system_actor.py`：`from run_meta_schema_migration import extract_blocks` 取得解析器（**不複製**），執行 `K)` 區塊，在 COMMIT **之前**逐項查證後
  - - [ ] 8.1 `.github/workflows/memory-retention-purge.yml`：
  - - [ ] 12.5 收尾核對：`git diff --stat -- backend/database.py` 仍為空；`python3 scripts/validate_repo_contract.py` 與 `python3 scripts/validate_env_contract.py` 皆綠燈；`cd ba
  - - [ ] 不改程式與 workflow。`DEPLOY.md` 的 90 天清除小節新增「合併進 `ut` 之後、併入 `main` 之前」的程序：① 以 `workflow_dispatch`、`ref=ut`、`dry_run=true` 跑一次並核對預覽（即 `OPEN-ID9-4` 要求的第一次真實執行前的 
  - - [ ] `merge-blockers.md` 第 17 列處置改為「已處置為人工義務：合併 `main` 前每週手動觸發」，並標明這是**持續中的人工義務**而非已修正。
