# Unit Test Instructions — `U4 hierarchy-data`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: hierarchy-data · kind: spec -->

## 一、測試框架（既成事實，不新增依賴）

- Python 內建 **`unittest`**，**不是 pytest**（`team.md` 的既成事實）。
- `hypothesis` 已在 `requirements.txt`，但**本單元不用它**：`rules.md §二` 實算的
  `calculation` 類規則數為 **0**，沒有值域性質可寫成 property；`ADR-0006` 的 PBT
  hard constraint 點名的三個模組（IaC generator、cost calculator、agent routing）
  不含本單元。判定為 **N/A 而非豁免**。
- 測試 DB：沿用 `backend/tests/helpers.py` 的既有策略——在任何 DB import **之前**
  `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite。
  新測試檔第一行 import 必須是：

  ```python
  import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import
  ```

---

## 二、**本單元的精確執行指令**

在 `backend/` 目錄下執行：

```bash
python -m unittest tests.test_hierarchy_migration -v
```

**不得使用裸的 `python -m unittest discover -s tests`**——Build and Test 會逐單元執行
每個單元的指令，未限定範圍會讓整套測試被跑 N 次。

此指令在第一個測試步之前即可執行（brownfield，執行器已存在），符合 Testing Contract 的
`runner_ready_before_first_test: true`。

---

## 三、測試檔與案例配置（Standard 策略：每元件 5–8 個）

單一測試檔 `backend/tests/test_hierarchy_migration.py`，三個 `TestCase` 類對應三層：

| 類 | 層 | 案例數 | 涵蓋 |
|---|---|---|---|
| `TestHierarchySchema` | 資料模型 | 5 | 兩個部分唯一約束各自擋住第二筆；兩層 `RESTRICT` 各自擋住；`system_id` 可為空；`actor_user_id` 必填；`source` 拒絕未定義值 |
| `TestHierarchyMigrationData` | 資料讀寫 | 3 | 兩位使用者各自掛入自己的預設 system；不持有圖者不建預設專案；既有四欄逐欄未變 |
| `TestHierarchyMigrationLogic` | 業務邏輯 | 5 | 終檢殘留時 **raise**（非 warning）；三個計數值正確；重跑無第二組且無重新指派；部分失敗後重跑可補完；獨立指令失敗時非零結束碼 |

**合計 13 個案例、三個元件**，落在 Standard 的每元件 5–8 區間內（資料讀寫層 3 個略低，
理由是該層的行為面窄——它只有「掛入」與「不動既有欄位」兩件事，硬湊到 5 個會寫出重複斷言）。

---

## 四、逐案例的斷言要點（避免寫出恆真測試）

`construction.md` 逐字禁止「不論實作如何都會通過」的測試。本單元最容易寫成恆真的三處：

1. **終檢的測試**必須斷言它 **raise**，不是斷言「有 log」。
   `assertRaises` 包住呼叫，並斷言例外訊息含殘留列數。
2. **重跑的測試**必須先跑一次遷移、**再跑第二次**，然後斷言預設 project／system 的
   **列數仍為每位使用者 1**、且圖的 `system_id` 與第一次相同。只斷言「沒有錯誤」是恆真的。
3. **「既有欄位未變」的測試**必須**逐欄比對**遷移前後的值，不是只斷言列還在。

---

## 五、Mocking 與測試資料

- **不 mock 遷移自己的邏輯**。只沿用 `helpers.py` 既有的 `psycopg2` stub。
- 測試資料以 factory 形狀就地建立（既有測試檔的慣例），不引入 factory 套件。
- 每個 `TestCase` 自建自己的資料；不共用可變狀態（`construction.md` 的測試獨立性要求）。
- **SQLite 與 PostgreSQL 的落差必須誠實對待**：部分唯一索引（`WHERE is_default`）
  在 SQLite 與 PostgreSQL 的語法不同。若某個約束在 SQLite 上無法忠實重現，
  **該案例標記為只能在真實 PostgreSQL 驗證**並記進 `code-summary.md` 的 open items，
  由 `U4-V1`–`U4-V5` 的真實 PG CI job 承接（`S-6`）——
  **不得為了讓測試變綠而弱化約束或改寫成寬鬆版本**。

---

## 六、覆蓋率目標

- `org.md` 宣告最低 80% line coverage。**本 repo 目前沒有覆蓋率量測機制**
  （無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step），
  所以這個數字**無法量測也無法強制**（`team.md` 逐字如此記載）。
- 本單元的實際門檻是上表 13 個案例全綠，以及既有 21 個測試檔維持全綠
  （Testing Contract 的 `scope_floor`：Keep the existing test suite green）。
- 不為了湊覆蓋率數字而寫斷言薄弱的測試。

---

## 七、既有測試套件必須維持綠燈

本單元改動 `schema_rbac.sql`，而既有測試走 in-memory SQLite、不讀那支 SQL，
理論上不受影響。但**必須實際驗證**：

```bash
python -m unittest discover -s tests -v
```

這條指令**只在 Build and Test 那一站跑一次**（驗證既有套件未被破壞），
不是本單元的執行指令——本單元的指令是 `§二` 那一條。
