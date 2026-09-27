# Unit Test Instructions — `U1 brain-infra`

## 一、這個單元的測試在測什麼，以及它不能宣稱什麼

`U1 brain-infra` 交付的是 compose YAML、shell、SQL、workflow 與文件。本檔規劃的測試
**只覆蓋其中兩個真的有受測對象的元件**：

| 元件 | 測試檔 | 為什麼可測 |
|---|---|---|
| vector extension bootstrap | `backend/tests/test_vector_extension_bootstrap.py` | `backend/database.py` 是 Python，呼叫順序可用 `unittest.mock` 斷言 |
| `deploy/render-env.sh` | `backend/tests/test_render_env_redis.py` | shell 腳本可用 `subprocess` 執行並斷言結束碼與輸出 |

**不可測、且本檔不假裝可測的部分**（如實列出，不是省略）：

- compose 的服務集合、`networks:` 分段、記憶體上限、`logging:`、`healthcheck`、
  `depends_on` — 本 repo 沒有任何解析 compose 的測試層。
  `infrastructure-specification.md` `§六` 已把補閘門 (a)–(d) 明文列為**不屬本單元交付**，
  所以這些改動落地後的自動化保護是**零**，只有 `validate_env_contract.py` 看得到其中
  變數注入那一小塊。
- `deploy.yml` 的探測步驟 — 它只在真實部署時執行，本 repo 無 workflow 單元測試層。
- `DEPLOY.md`／`LOCAL-DEV.md` 的內容正確性 — 僅第 11 項的 blocking 同步有一個
  「兩份檔都要提到 vector extension」的機械斷言（見下）；其餘靠人讀。
- `AC2.1.4`（backend 重啟後脈絡完整還原） — 本單元只交付儲存層，
  還原是否完整取決於 `U10` 寫了什麼、`U14` 讀了什麼。**本單元的任何測試都不得宣稱驗證了它。**

## 二、測試框架與設定

**沿用既有，不新增任何依賴。**

- 框架：Python 內建 `unittest` ＋ `unittest.mock`（`team.md` 記載：本 repo **不使用 pytest**）
- DB 策略：沿用 `backend/tests/helpers.py`——在任何 DB import 之前
  `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite
- 子行程測試的既有形狀：`backend/tests/test_repo_contract_production_paths.py`
  已示範在暫存目錄執行外部程式並斷言結果，`test_render_env_redis.py` 比照它
- 新檔放進 `backend/tests/` 即被既有的 `unittest discover` 撿到，**不需要改 CI**

## 三、如何執行「這個單元」的測試

**本單元專屬命令**（不是全專案命令——`unscoped` 的 `python -m unittest` 會讓
Build and Test 每個單元重跑整套）：

```bash
cd backend && python -m unittest tests.test_vector_extension_bootstrap tests.test_render_env_redis -v
```

兩支驗證器（本單元的主要閘門，從 repo 根執行）：

```bash
python3 scripts/validate_env_contract.py
python3 scripts/validate_repo_contract.py
```

既有套件保持綠（Testing Contract 的 `scope_floor` 要求，從 `backend/` 執行）：

```bash
cd backend && python -m unittest discover -s tests -v
```

**執行器就緒性**：以上命令在本單元的第一個測試寫出來之前就已經可執行（brownfield，
執行器既有）。Step 1 是**驗證**這件事，不是 bootstrap。

## 四、規劃的測試案例

### `test_vector_extension_bootstrap.py`（6 個）

| # | 測什麼 | 通過條件 |
|---|---|---|
| 1 | `_ensure_vector_extension` 存在且可呼叫 | `hasattr(database, "_ensure_vector_extension")` 為真 |
| 2 | **呼叫順序**：它在 `create_all` 之前 | 以 `mock.patch` 攔截兩者並記錄呼叫序，斷言 `_ensure_vector_extension` 的索引 < `create_all` 的索引 |
| 3 | 冪等：重複呼叫不炸 | 連呼兩次無例外；送出的 SQL 含 `IF NOT EXISTS` |
| 4 | SQLite 測試環境下不炸 | 在 `helpers.py` 的 mock 環境呼叫 `init_db()` 無例外 |
| 5 | `schema_rbac.sql` 含 extension 宣告 | 檔內含 `CREATE EXTENSION IF NOT EXISTS vector` |
| 6 | **blocking 同步**：`DEPLOY.md` 也提到它 | `schema_rbac.sql` 提到 vector extension ⇒ `DEPLOY.md` 亦須提到（把 `project.md ## Mandated` 的同步規則變成可執行檢查） |

案例 2 是這一組的核心——它是清單第 12 項「呼叫點在 `create_all()` 之前」這條**二元判準**
的唯一自動化守門者，而既有六支 `_ensure_*` 全在之後，實作者照既有形狀做就會放錯邊。

### `test_render_env_redis.py`（5 個）

以 `subprocess` 在暫存目錄執行 `bash deploy/render-env.sh`，注入不同的環境變數。

| # | 測什麼 | 通過條件 |
|---|---|---|
| 1 | 空的 `REDIS_PASSWORD` | **非零退出**（清單第 4a 項的可測判準） |
| 2 | 含 `$` 的 `REDIS_PASSWORD` | **非零退出**（清單第 4b 項；`project.md ## Forbidden` 的硬規則） |
| 3 | 正常值 | 零退出，且產生的 `deploy/.env` 含七個新變數名 |
| 4 | 六個非機敏變數是**字面值**而非空字串 | 產生的 `.env` 中 `REDIS_USER`／`EMBEDDING_PROVIDER`／`REDIS_URL`／`OLLAMA_BASE_URL`／`OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL` 皆有非空值 |
| 5 | `REDIS_PASSWORD` 的值等於傳入值 | 逐字相等，未被截斷 |

案例 4 直接對應審查 R-40 指出的失敗模式（把六者做成 `env:` 傳入會讓它們變成空字串，
`EMBEDDING_PROVIDER` 依 `K-01` 無預設會讓 backend 大聲失敗 → deploy 紅燈 → 自動 rollback）。
案例 2 對應的失敗是**無聲的**：compose 內插會把 `ab$cd` 截成 `ab`，Redis 以遠弱於預期的
密碼運行且沒有任何錯誤訊息。

## 五、覆蓋率目標

- **Standard 策略**要求每個元件 5–8 個測試：兩個可測元件各 6／5 個，合計 **11 個新測試**，符合。
- **`org.md` 的 80% line coverage**：本 repo **沒有覆蓋率量測機制**（無 `.coveragerc`、
  無 `coverage`／`pytest-cov`、CI 無 coverage step）。`team.md` 已逐字記載它
  「既無法量測也無法強制，是宣告而非閘門」。本單元**不新增**覆蓋率工具（獨立的工具鏈決策，
  不由本單元夾帶），也**不宣稱**達成 80%。這是如實記載，不是豁免申請。
- **`scope_floor`**：既有套件必須保持綠。

## 六、Mock／Stub 指引

- **DB**：沿用 `helpers.py` 的 psycopg2 mock ＋ in-memory SQLite。**不要**在測試中連真實 PostgreSQL。
- **呼叫順序斷言**：用 `unittest.mock.patch` 搭配共用的 `Mock` parent（`mock_calls` 保序），
  不要用兩個獨立 mock 再比對時間戳。
- **`render-env.sh`**：以真實 `bash` 子行程執行，**不要** mock shell。這支腳本的價值
  正在於它的實際退出行為；mock 掉就什麼都沒測到。在 `tempfile.TemporaryDirectory()` 內
  執行並把 `deploy/.env` 的輸出導到該目錄，測試結束即消失。
- **`gh api`**（清單第 4d 項）：**不寫自動化測試**——它查的是這個 repo 的實際 secret 設定，
  mock 掉等於什麼都沒查。它是一個**人工必做步驟**，結果記進完成摘要。

## 七、測試資料管理

- 不需要 fixture 檔。兩組測試的輸入都是環境變數與既有 repo 檔案。
- `render-env.sh` 的測試**不得**使用任何真實憑證值；用明顯的假值（如 `test-only-value`）。
  含 `$` 的那一例用 `ab$cd` 這種最小重現字串。
- **絕不**把任何真實 token、API key 或部署憑證寫進測試檔——本 repo 為 public。
