# 單元測試指示 — `U3 rbac-story-ids`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: rbac-story-ids · kind: spec -->

> Methodology **`test-after`**、Test strategy **`standard`**（每元件 5–8 測試
> ＋ 關鍵邊界的整合測試），兩者皆由 `aidlc-testing-posture.ts render` 的
> Testing Contract 決定，完整 JSON 逐字貼於 `code-generation-plan.md`。

---

## 一 Runner 就緒（第一個可執行測試步驟之前必須完成）

**本單元是 brownfield，runner 已存在，故本節是「驗證」而非「建置」。**

**精確的 unit-scoped 指令**（寫進本檔是 Testing Contract 的要求）：

```bash
cd backend && python -m unittest tests.test_rbac_story_ids_seed -v
```

**全套指令**（CI 跑的那個，`ci.yml` 的 `backend` job）：

```bash
cd backend && python -m unittest discover -s tests -v
```

**驗證要點**（寫第一個測試之前確認）：

1. `backend/tests/` 下的新檔會被 `discover` 自動撿到——**無需任何 CI 設定變更**。
2. 框架是 Python 內建 **`unittest`**，**不是 pytest**
   （`team.md ## Testing Posture` 的既成事實）。
3. 新測試檔第一行 import 必須是：
   ```python
   import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import
   ```
   `backend/tests/helpers.py` 在任何 DB import 前
   `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite。
4. **零新依賴**：`ast`、`re`、`unittest`、`logging` 皆標準庫；
   `backend/requirements.txt` 不變。
5. 讀原始碼／SQL 文字的契約測試前例：`backend/tests/test_hierarchy_migration.py`
   的 `test_schema_rbac_sql_matches_migration_ddl`（由 `U4` 交付、現在就在跑）。
   其 `@note` 逐字說明它**不比對型別與約束**（那需要真的 PostgreSQL）
   ——本單元的比對對象是 seed **資料**而非 DDL，故同樣不需要資料庫。

---

## 二 測試檔與測試清單

**一支新檔**：`backend/tests/test_rbac_story_ids_seed.py`

**為什麼是一支而不是三支**（`nfr-design` 的 `D-10`）：下列七個測試都只需要
「解析 `DEFAULT_ROLE_PERMISSIONS`」這一份邏輯。分檔會把同一份解析寫三次
——而 `team.md` 的「單一真實來源」正是本單元在防的東西，在它自己的測試裡
製造三份副本是自相矛盾。

| # | 測試 | 斷言 | 承載 |
|---|---|---|---|
| 1 | `test_the_matrix_has_exactly_352_rows_and_no_missing_combination` | 長度 == 352 **且**每個 `(role, story_id)` 組合恰一列 | `U3-V4`、`BR3.4`′ |
| 2 | `test_a_role_with_a1_view_does_not_hold_k3` | 存在角色持有 `A1` view 但 `K3` 三旗標皆 false | `U3-V1`、`BR5.3` |
| 3 | `test_at_least_one_role_does_not_hold_k4` | 存在角色 `K4` 三旗標皆 false | `U3-V2`、`BR6.5` |
| 4 | `test_every_k2_editor_also_holds_k3_edit` | 對每個 `K2.edit` 持有者，`K3.edit` 為 true | `U3-V3`、`BR5.4` |
| 5 | `test_the_four_new_story_ids_never_grant_review` | 四個新 id 的 `can_review` 在 44 列皆 false | `U3-V5`、`EC-4` |
| 6 | `test_the_seed_write_logs_which_rows_it_inserted` | `assertLogs` 捕捉後，`K1`／`K2`／`K3`／`K4` 四個字串都在訊息中 | `SEC-4`、`D-7` |
| 7 | `test_the_sql_seed_block_matches_the_python_default_row_for_row` | 兩份 tuple 集合相等；失敗時輸出三段 diff | `SEC-5`、`BR4.4`′、`D-5` |

數量 **7**，落在 `standard` 策略的「每元件 5–8 測試」區間內。

### 測試 1 的兩個子斷言不可合併

長度與組合完整性是**兩個獨立的失敗模式**：把一列的 `story_id` 由 `K4` 改成 `K3`
會讓長度仍是 352 而組合有缺漏。`BR3.4`′ 逐字要求「同時驗總數**與**組合完整性」，
而突變 `M2` 正是為此而設。

### 測試 6 的斷言粒度

**只綁四個 story id 的字串，不綁整句措辭**（`nfr-design` 的 `D-8`）。
理由：綁整句會讓任何文案修訂紅燈；綁零內容（只驗「有一行 log」）則回到
`SEC-4` 要防的那個缺口。這是最寬鬆而仍有效的綁法。

**但 log 的文字格式自此成為受測契約**——下一個改 log 文案的人若讓四個 story id
不再出現在同一行，這條會紅。那是刻意的，不是測試壞了。

### 測試 7 的失敗輸出設計

三段 diff：只在 SQL 的列／只在 Python 的列／兩邊都有但旗標不同的列，
各最多列前 **10** 筆並附該段總數。

**第三段不可省**：只比列數與 story id 集合會讓「列在、但旗標不同」整類漏掉
——那正是「同一個角色在不同環境有不同權限」的形狀，`SEC-5` 存在的全部理由。

**解析範圍以區塊邊界定位，不得寫死行號**：以
「`INSERT INTO role_permissions` 之後、下一個裸 `;` 之前」界定。
本單元自己的 44 列插入就會讓行號位移。

---

## 三 突變驗證（本計畫的交付條件）

七個測試裡有五個檢查「某個狀態**存在**」或「某個字串**不存在**」，
而這類檢查最容易寫成恆真。**每一項都必須做突變驗證**：
改回錯的行為 → 跑測試 → 確認紅燈 → 還原 → 複驗綠燈，
並把突變內容與紅燈訊息寫進 `code-summary.md`。

| # | 突變 | 必須紅的測試 |
|---|---|---|
| `M1` | 從 `DEFAULT_ROLE_PERMISSIONS` 刪掉任一列 | 測試 1（長度子斷言） |
| `M2` | 把一列的 `story_id` 由 `K4` 改成 `K3` | 測試 1（**組合子斷言**；長度仍 352） |
| `M3` | 把 `SRE` 的 `K3` 列改為 `(True, False, False)` | 測試 2 |
| `M4` | 把 `SRE` 的 `K4` 列改為 `(True, False, False)` | 測試 3 |
| `M5` | 把 `Project_Architect` 的 `K3` 改為 `(True, False, False)` | 測試 4 |
| `M6` | 把任一新列的第三個旗標改為 `True` | 測試 5 |
| `M7` | 把 `rbac.py` 的 log 改回只記列數 | 測試 6 |
| `M8` | **只**改 Python 那份的一列旗標（不動 SQL） | 測試 7（三段 diff 的**第三段**） |

**`M2` 與 `M8` 是最重要的兩個**：

- **`M2`** 驗的是測試 1 那條「最容易被合併掉」的子斷言。若測試 1 只驗長度，
  `M2` 會過——而那正是 `BR3.4`′ 要防的「列數對但組合有缺漏」。
- **`M8`** 驗的是測試 7 第三段的存在理由。若比對只看列數與 story id 集合，
  `M8` 會過——而那是本單元最危險的失敗模式（環境相依且無聲）。

**每次突變後先 `grep` 確認檔案真的變了，再跑測試。**
`test-case-authoring.md §5` 記過一次突變沒生效（`{} or {...}` 的 Python `or`
回傳右側）而被誤讀為「測試沒抓到」。

---

## 四 既有測試必須保持綠燈

Testing Contract 的 `scope_floor` 逐字：「Keep the existing test suite green.」

本單元改動 `rbac_seed_data.py`、`rbac.py`、`user_router.py`、`schema_rbac.sql`
四支既有檔，故 `backend/tests/` 全套必須在改動**前後各跑一次並比對**：

- **新增數** == 本單元新增的 7 個測試
- **既有項零失敗**
- **特別注意兩支**：
  - `backend/tests/test_rbac.py`——直接測授權矩陣
  - `backend/tests/test_collab.py`——`import DEFAULT_ROLE_PERMISSIONS`（用途無關，
    但 import 的是本單元改動的那個物件）

### 覆蓋率

`org.md` 宣告「最低 80% line coverage」，而 `team.md` 如實記載**本 repo 完全沒有
覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage
step）——該門檻目前既無法量測也無法強制。

**本計畫不宣稱達成它，亦不以「已達成」記錄。** 實際門檻是 `team.md` 的
A／B／C 三項規則，而本單元：

| 規則 | 判定 | 理由 |
|---|---|---|
| **A**（`role_permissions` 變更需 allow/deny 雙向測試） | **適用，但本單元只能做一半** | 本單元**就是** `role_permissions` 的 seed 變更。然而 allow/deny 雙向需要一個端點，而本單元零端點（`SEC-1`／`SEC-6`）。本單元交付的是**授權資料的結構前提**（測試 2–5）；allow/deny 雙向已具名交接 `U19`（`U3-A1`–`U3-A3`）。**這是真實的覆蓋缺口，不是豁免** |
| **B**（HTTP 端點需 `TestClient`） | **不適用** | 零端點 |
| **C**（前端資料形狀變更需 e2e） | **不適用** | 零畫面；`STORY_FEATURE_LABELS` 是後端字典 |

---

## 五 PBT 判定

**對本單元 N/A。** `rules.md` 修訂 1 實算 `calculation` 類規則為 **0**；
本單元的七個測試全部是對固定資料集合的斷言，沒有值域可探索。

**但這個 N/A 不等於整個 intent 沒有 PBT 標的**：`BR7.4` 點名的挑選純函式
（真正可失敗的性質是**排列不變性**——`ORDER BY joined_at` 在時間戳相同時
沒有穩定順序）是 `U19` 的交付物，已由 `U3-A3` 具名交接。
ADR-0006 點名的三個落點（IaC generator、cost calculator、agent routing）
皆不在本單元。
