# Unit Test Instructions — `U2 brain-ws-contract`

<!-- Stage: code-generation（Construction 3.5）· Unit: brain-ws-contract · kind: spec -->

## 測試框架（既成事實，不新增）

| 層 | 框架 | 依據 |
|---|---|---|
| Backend | Python 內建 **`unittest`**（**非 pytest**）＋ `hypothesis` ＋ `unittest.mock` | `team.md ## Testing Posture` |
| Frontend | **`@playwright/test` 是唯一的前端測試框架**；無 vitest／jest／`@testing-library` | 同上，本站複查 `devDependencies` 屬實 |
| 本單元新增 | **零新測試框架** | 本單元的驗證面是 CI 閘門與 lint，不是 UI 行為 |

本單元**不新增任何前端測試**：它交付的是型別、兩道閘門與一條 lint 規則，
沒有可由 Playwright 觀察的使用者行為。前端側的驗證由 `eslint` 與 `tsc -b` 承擔，
兩者都是既有的 CI 步驟。

## 本單元的測試落點

| 檔 | 涵蓋 |
|---|---|
| `backend/tests/test_ws_contract.py` | 契約模型本身：`BR1.5` validator、`BR1.6` turnId 二分、`BR2.12`／`BR2.13` 的欄位不可構造、`WsSubprotocol` 的字面型別 |
| `backend/tests/test_dump_ws_contract.py` | dump 腳本：`--check` 的 fail-closed 語意、`BR1.4` 集合等勢斷言、`NFR5.7` 白名單斷言、序列化決定性 |

## 執行指令（**本單元專用，不得用全專案指令**）

```bash
cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ws_contract tests.test_dump_ws_contract -v
```

- **必須帶 `PYTHONDONTWRITEBYTECODE=1`**：`__pycache__` 不在引擎的來源指紋排除清單內
  （`aidlc-lib.ts:14117` 只排除 `.pytest_cache`），在審查窗口內產生 `.pyc` 會讓議決記不進去。
  本 session 已為此吃過兩次虧。
- **不得**寫成 `python -m unittest discover -s tests`——那是全專案指令。
  `build-and-test` 會逐單元執行這裡的指令，未 scope 的指令會讓整套測試被重跑 N 次。

### 執行前提（brownfield，本站已驗）

1. 測試 runner 已存在，無需 bootstrap：CI 以 `python -m unittest discover -s tests -v` 執行。
2. 新測試檔放進 `backend/tests/` 即被自動撿到。
3. 測試檔**首行**必須是：
   ```python
   import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import
   ```
   `tests/helpers.py` 在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`。
   **本單元的契約模組不 import 任何 DB**，但 `backend/tests/` 的既有慣例如此，沿用以免例外。

## 測試量（Standard strategy：每元件 5–8 個）

| 元件 | 目標測試數 | 內容 |
|---|---|---|
| `brain_ws_contract.py` | **7** | (1) `BR1.5` 兩份 `turnId` 相等 → 通過；(2) 不相等 → `ValidationError`；(3) `payload.turnId` 缺失 → `ValidationError`；(4) `BR1.6` 輪次型別缺 `turnId` → 拒；(5) `BR1.6` 非輪次型別帶 `turnId` → 拒；(6) `WsClientEnvelope` 不接受 `turnId` 欄位（`BR2.13`，型別層不可構造）；(7) `WsSubprotocol` 的兩個欄位為字面值、不接受其他值 |
| `dump_ws_contract.py` | **6** | (1) `--check` 在規格檔不存在時 exit 1 且訊息指向 dump；(2) 規格檔與模型一致時 exit 0；(3) 手改規格檔後 exit 1；(4) `BR1.4` 集合等勢：注入一個沒有 payload 的 type → 斷言失敗；(5) `NFR5.7` 白名單：注入一個未宣告的客戶端欄位 → 斷言失敗；(6) 序列化決定性：連跑兩次輸出位元相同 |

合計 **13** 個測試。

## 突變驗證（`test-case-authoring.md §5`，**每一條斷言都要看它紅過一次**）

不是選項。對下列五項各做一次「改回錯的行為 → 確認紅燈 → 還原 → 複驗綠」，
並把突變內容與紅燈的斷言編號寫進 `code-summary.md`：

| # | 突變 | 預期轉紅 |
|---|---|---|
| M1 | 把 `BR1.5` 的 validator 改成恆真（`return self`） | `test_ws_contract` 的 (2)(3) |
| M2 | 把 `BR1.6` 的輪次型別集合改成空集合 | (4)(5) |
| M3 | 拿掉 `BR1.4` 的集合等勢斷言 | `test_dump_ws_contract` 的 (4) |
| M4 | 把白名單的預期集合改成「只要是子集就通過」 | (5) |
| M5 | 把 `sort_keys=True` 拿掉 | (6) |

**突變本身也要確認生效**：改完先開檔確認內容真的變了。
本 repo 踩過一次 `_SERVICE_ABBREVIATIONS = {} or {...}`——`or` 回傳右側，突變根本沒作用，
測試當然綠，差點被讀成「測試沒抓到」。

## 覆蓋率目標

`org.md` 宣告最低 80% line coverage。**本 repo 目前無覆蓋率量測機制**
（無 `.coveragerc`、無 `coverage`／`pytest-cov`、CI 無 coverage step——`team.md` 逐字記載
「既無法量測也無法強制，是宣告而非閘門」）。

**本單元不引入覆蓋率工具**（那是獨立的工具鏈決策，不由本單元夾帶），
改以 `team.md` 本輪生效的三項二元可判規則作為實際門檻：

| 規則 | 對本單元是否適用 | 處置 |
|---|---|---|
| **A** `role_permissions` 變更需 allow/deny 雙向測試 | **不適用** | 本單元不動 RBAC seed |
| **B** 新增／修改 HTTP 端點需 `TestClient` 測試 | **不適用** | 本單元不新增任何端點（WebSocket 端點是 `U13`） |
| **C** 前端資料形狀變更需 e2e 斷言 | **不適用** | 本單元不改任何使用者可見的資料形狀 |

三項皆不適用，故本單元的實際門檻是**上表 13 個測試 ＋ 五項突變驗證全部做到**。
這一點必須在 `code-summary.md` 逐項回報，不得以「測試都綠了」帶過。

## Mocking／Stubbing 指引

- **契約模組不需要任何 mock**：它是純 Pydantic 模型，無 I/O、無 DB、無網路。
- **dump 腳本的測試需要一個暫存目錄**：用 `tempfile.TemporaryDirectory()` 產生假的規格檔路徑，
  **不得**讓測試寫到 repo 根的真實 `ws-contract.json`（那會讓 CI 的第一道閘門看到被測試改過的檔）。
- **`BR1.4`／白名單的突變測試不得改動真實模組**：以 monkeypatch 或傳入替身 schema 字典進行，
  用完還原。

## 測試資料管理

本單元無資料庫、無 fixture 檔。全部測試資料在測試檔內以字面值構造。
`WsSubprotocol` 的兩個值（`bearer`／`.`）在測試中**必須從模型取值**而非寫死字串——
否則測試會與被測物件同時錯，那正是 `NFR5.4` 在防的形狀。

## ADR-0006 PBT hard constraint

**不適用，附理由。** 該約束點名 IaC generator、cost calculator、agent routing 三類純計算模組，
本單元不含其中任何一個；`rules.md` 的 `calculation` category 實算為 **0**。
唯一的執行期程式碼（`BR1.5` validator）是兩值相等比較，無值域可供性質測試。
PBT 在本 intent 的落點是 `U11` 的 IntentRouter 門檻純函式與 `U6` 的 EmbeddingPort。
