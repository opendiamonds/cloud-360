# CI/CD 管線 — `U20 requirement-field-service`

## 一、自動撿到、不需改 workflow 的部分

| 產出 | 落點 | 為什麼不用改 |
|---|---|---|
| 後端單元／HTTP 測試 | `backend/tests/test_requirement_field_*.py` | `ci.yml` 的 backend job 以 `python -m unittest discover -s tests` 撿起 |
| OpenAPI 與型別檔 | `openapi.json`、`frontend/src/types/api.d.ts` | 既有漂移閘門（`dump_openapi.py --check`、`check:types`）會擋未重新產生的變更 |
| `verify_meta_schema.sql` 新斷言 | 既有檔案 | `memory-schema` job 已在跑這支（`ci.yml` 的 P1–P12 步驟） |

## 二、需要擴充的部分：`memory-schema` job 的收斂驗證（承 nfr-design `review-01` R-02）

**為什麼不能只用 `psql -f schema_rbac.sql`**：既有環境的演進路徑是 `run_meta_schema_migration.py`，
它的後條件（`NFR20.25`）才是會在 staging 擋下錯誤的那一道；只用 `psql -f` 驗，等於驗了一條
staging 不會走的路。

新增步驟（放在既有 P1–P12 斷言之後、purge 斷言之前；**不新增 job**，理由同該 job 的既有註解）：

| 步驟 | 動作 | 斷言／注意 |
|---|---|---|
| 0 | `actions/setup-python`（3.12）＋ 安裝 `backend/requirements.txt` | 與 backend job 同一版本；`DATABASE_URL` 指向 service container |
| A | `psql -f backend/scripts/ci/downgrade_requirement_fields.sql`：把 `updated_on_behalf_of` 改回 integer ＋ 指向 `users` 的外鍵 | 模擬「`U18` 先上線」的資料庫；此時表內無列，型別轉換不會失敗 |
| B | `cd backend && python scripts/run_meta_schema_migration.py` | 結束碼 0；後條件驗到 `character varying`、該欄無外鍵、`updated_by` 外鍵仍在 |
| C | `psql -f backend/scripts/ci/seed_requirement_field_fixture.sql`：建立一組 user／project／system fixture 並寫入一列 `updated_on_behalf_of = 'cost'`，**明確 `COMMIT`** | 不得放在 `verify_meta_schema.sql` 裡——那支檔以 `ROLLBACK` 結尾，寫入不會留下 |
| D | 再跑一次 `run_meta_schema_migration.py` | 結束碼 0；之後查該列的值仍為 `'cost'`（重跑不清資料） |
| E | 清除 C 的 fixture（依外鍵順序：requirement field → system → project → user） | 讓 job 結束時的資料庫回到只有 schema 與既有 fixture 的狀態，後續步驟不需要知道本單元的 fixture 存在 |

**誠實的限定**（沿用該 job 既有註解）：`ut` 沒有必要狀態檢查，這些步驟紅燈是訊號而不是
合併閘門（承 `OPEN-ID19-6`，不重複立項）。

## 三、部署管線

不改 `deploy.yml`。遷移仍為人工步驟，順序與失敗面寫在 `infrastructure-specification.md`
第二節，並同步進 `DEPLOY.md` 2.2.9（blocking 同步的一部分）。

## 四、`ui-regression`

不受影響：本單元沒有前端程式。`U23` 的 e2e 落地時才會觸及新端點。
