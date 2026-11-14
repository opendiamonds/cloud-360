# CI/CD — `U7 hierarchy-service`

## 一、判定：不新增任何 job 或 step，但有三項既有閘門必須被滿足

本單元不新增 CI job、不新增 workflow、不改 `deploy.yml`。
既有管線（`ci.yml`）依序為 `repo-contract` → `frontend` → **OpenAPI drift 檢查** →
`backend`（import smoke ＋ `unittest`）→ `docker-build`。

下列三項是**本單元必須讓它們綠燈**的既有閘門，其中第 1 項是本單元新增端點的
直接後果：

| # | 閘門 | 本單元的義務 | 漏了會怎樣 |
|---|---|---|---|
| 1 | **OpenAPI drift**（`backend/scripts/dump_openapi.py --check`） | 五個 path 落地後同步重 dump `openapi.json`；**且 409 須顯式宣告** `responses={409: {...}}`（`NFR5.1`／`NFR5.2`、規則 `BR6.6`） | 漏 dump → CI 紅燈（會被抓到）。**但漏宣告 409 → CI 保持綠燈**，契約不進 spec、前端產不出型別——`unit-of-work.md:447` 逐字「非 2xx/422 的宣告數為 0」。這是本單元唯一**不會被閘門抓到**的遺漏 |
| 2 | **backend `unittest`**（`python -m unittest discover -s tests -v`） | 新測試檔放進 `backend/tests/` 即被撿到；須含 `import tests.helpers  # noqa: F401` 以安裝 psycopg2 stub | 測試不執行而無人察覺 |
| 3 | **`repo-contract`**（`validate_repo_contract.py` ＋ `validate_env_contract.py`） | 本單元宣稱零新部署設定（`NFR8.1`），兩支 validator 須綠燈 | CI 紅燈 |

## 二、測試義務彙整（驗證落點全部在 `code-generation`）

來自 `team.md` 的 A＋B 規則與 `project.md` 的交叉要求，共五項：

1. **allow/deny 雙向 `TestClient`**：具 `K2` → 2xx、無 `K2` → 403，缺一不可。
2. **列範圍斷言**（`BR6.1`）：他人的列不得出現在任何列舉回應中。
3. **寫入面斷言**（`BR6.5`）：以他人的專案為目標建立系統／刪除必須被拒。
4. **`BR6.4` 最小欄位斷言**：判定支援型查詢不得回傳名稱或可列舉的集合。
5. **409 顯式宣告**（`BR6.6`／`NFR5.2`）＋ 重 dump `openapi.json`。

**採用成本為零**：`backend/requirements.txt` 已含 `fastapi[standard]` 與 `httpx`，
`starlette.testclient.TestClient` 的前置條件已滿足；`get_db`（`database.py:31`）與
`get_current_user`（`services/auth.py:39`）為穩定的模組層函式，可用
`app.dependency_overrides` 覆寫；以 `TestClient(app)` 直接使用不觸發
`@app.on_event("startup")` 的 `init_db()`，不需要真實 DB。

## 三、`tcms-test-cases` 的前置提醒（blocking，但不在本站）

`project.md` 的 `## Mandated` 逐字要求每個 intent 的 construction 必經
`tcms-test-cases` stage 並完成四項產出，**未完成不得進入部署階段**。
本單元的行為中，第 2–4 項測試義務屬「待自動化」桶（可用 `TestClient` 覆蓋），
第 5 項屬機械檢查。本站只記下這個前置，不代該 stage 產出。
