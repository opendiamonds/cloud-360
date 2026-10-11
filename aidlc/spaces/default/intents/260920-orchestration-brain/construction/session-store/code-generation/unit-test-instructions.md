# Unit Test Instructions — `U10 session-store`

> 本檔與 `code-generation-plan.md` 一同受 Plan Approval 綁定。
> 核可後**逐位元**不得更動——任何一個位元的改動都會讓收據失效並重開核可。

## 一、測試框架（既成事實，不引入新框架）

| 項目 | 值 | 出處 |
|---|---|---|
| 框架 | Python 內建 **`unittest`** ＋ `hypothesis` ＋ `unittest.mock` | `team.md` 逐字；**未使用 pytest** |
| CI 執行 | `python -m unittest discover -s tests -v`（`ci.yml` 的 `backend` job） | 同上 |
| 工作目錄 | **`backend/`** | 既有測試的慣例 |
| DB 替身 | `backend/tests/helpers.py` 在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`，改走 in-memory SQLite | 同上 |
| **Redis 替身** | **手寫 in-memory 物件**，置於 `backend/tests/` 內 | **本單元新增**；見 §四 |

**不新增任何測試依賴。** `fakeredis` 之類的套件會是第二個新依賴，而
`NFR8.41` 只授權**一個**（生產用的 Redis 客戶端）。手寫替身的範圍受限於本單元
實際用到的指令集（見 §四），這是刻意的取捨，不是省事。

## 二、本單元的精確執行指令（**三個，全部限定本單元**）

自 `backend/` 目錄執行：

```bash
python -m unittest tests.test_session_types -v
python -m unittest tests.test_session_contract -v
python -m unittest tests.test_session_store_behaviour -v
```

**三個指令都以模組名限定，不得改成 `python -m unittest` 或 `discover`。**
`build-and-test` 會逐單元執行每個單元的指令；未限定的指令會讓整套測試被重跑
一次 ×（單元數）。

**全套回歸**（只在 Step 12.4 的收尾跑一次，不屬本單元的日常指令）：

```bash
python -m unittest discover -s tests -v
```

## 三、三個測試檔的職責切分

| 檔案 | 驗什麼 | 不驗什麼 |
|---|---|---|
| `tests/test_session_types.py` | 純函式與資料形狀：`BR3.4` 修剪的三條 PBT property、`EC4` 段識別封閉集合、序列化往返 | 不碰 Redis、不碰授權 |
| `tests/test_session_contract.py` | **靜態**契約：模組不 import request／websocket 型別、`require_story_action` 零命中、無 router 註冊、日誌建構函式不接受任意 `kwargs`、Lua 是修剪的唯一生產載體 | 不執行任何方法 |
| `tests/test_session_store_behaviour.py` | 五個方法的行為、授權委派、段隔離、重入、長度上限、原因碼分類 | 不驗 Lua 的真實原子性（見 §六） |

**靜態檔獨立存在的理由**：`NFR4.46` 的三項禁令（不判權／不取身分／不對外）
是**形狀**而非行為——用執行期測試驗它，等於去證明某件事不會發生，
而那在測試裡永遠只能驗到你想到的那幾條路徑。讀原始碼比對是二元可判的。

## 四、Redis 替身的範圍（明寫它支援什麼、不支援什麼）

**支援**（本單元實際用到的指令）：

| 指令 | 用途 |
|---|---|
| `HGET` / `HSET` / `HGETALL` / `HDEL` | 段、作業對象、meta 的讀寫 |
| `EXPIRE` / `TTL` | `BR1.3` 的續期與 `NFR4.57` 的剩餘期 |
| `EXISTS` / `DEL` | `BR1.6` 的不存在判定 |
| `EVAL` / `EVALSHA` / `SCRIPT LOAD` | Lua；替身以**呼叫 `session_types` 的參考實作**模擬腳本效果 |

**不支援、也不假裝支援**：

- **真正的原子性**。替身是單執行緒 Python 物件，「原子」在它身上是免費的，
  所以它**證明不了** Lua 在真實 Redis 上的原子性。
- **`noeviction` 的 OOM 行為**。替身無記憶體上限。原因碼 `REDIS_OOM` 的測試
  以「替身被設定為對下一次寫入回覆 `OOM ...` 字串」驅動，驗的是**分類邏輯**，
  不是 Redis 的真實行為。
- **AOF 與重啟還原**。替身沒有持久化概念。

**這三項的真實驗證點是 `[I1]`=B 的部署後步驟**，不是 CI。
這段話寫在這裡，是為了讓「三個指令全綠」不被讀成「Redis 行為已驗證」。

## 五、預期的測試條數與覆蓋目標

| 檔案 | 條數 | 依據 |
|---|---|---|
| `test_session_types.py` | 約 **5**（含 3 個 `@given` property） | Testing Contract 的 `standard`：每元件 5–8 |
| `test_session_contract.py` | 約 **5** | 同上 |
| `test_session_store_behaviour.py` | 約 **8** | 同上。它涵蓋兩個元件（`redis_gateway` ＋ `session_store`），故取上緣 |

**覆蓋率**：`org.md` 宣告 80% line coverage，而本 repo **無覆蓋率量測機制**
（`team.md` 逐字「既無法量測也無法強制，是宣告而非閘門」）。
**本檔不宣稱滿足該數字、也不弱化它**；實際門檻是上表的條數 ＋ 計畫 §五 的
六項突變驗證。

## 六、Mock／Stub 指引

| 對象 | 做法 | 理由 |
|---|---|---|
| Redis | **手寫 in-memory 替身**（§四），由建構子注入 `redis_gateway` | 不新增依賴；注入點明確 |
| `K-07` 的 `HierarchyFacade` | `unittest.mock.Mock`，分別設定回傳解析結果 / raise `HierarchyForbidden` / raise `HierarchyNotFound` | 授權委派是本單元的 IAM 面，必須能驅動三種結果 |
| `principal` | 簡單的具名物件，帶 `user_id` | 不需要真實的 `get_current_user` |
| 時間與 TTL | 注入可控的 clock，不用 `time.sleep` | `NFR4.57` 的區間斷言需要可預測的時間 |
| **不 mock** 的 | `session_types` 的純函式 | mock 純函式等於不測它 |

**`psycopg2` stub 的既有慣例仍適用**：任何會間接 import DB 的測試檔，
第一行必須是

```python
import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import
```

`test_session_types.py` 若完全不觸及 DB，可省略；觸及 `K-07` 型別的兩個檔**必須**有。

## 七、測試資料

- **固定 fixture，不用隨機資料**（PBT 除外——那正是它的用途）。
- 訊息文字一律 `fixture-msg-<n>` 形式的無意義字串。**不得**使用看起來像真實
  對話的內容：本 repo 為 public，測試檔也在版控內。
- 段識別只用 `EC4` 的三個合法值；非法值的測試明確使用 `"nope"` 這類顯然無效的字串。
- 每個測試自備資料，**不共用可變狀態**；替身在 `setUp` 重建。
- `BRAIN_SESSION_HISTORY_MAX` 在測試中以**顯式注入**提供（例如 5），
  不讀環境變數——讓「超限丟最舊」的測試不需要 200 則資料。

## 八、每一條測試對應哪一條規則（寫測試前先對照）

| 測試 | 規則 |
|---|---|
| 修剪三條 property | `BR3.4` |
| 段識別封閉集合 | `EC4`／`BR2.1` |
| 序列化往返 | `EC7`（允許部分三元組，含 `null`） |
| 不 import request／websocket | `BR5.2`／`NFR4.46` |
| `require_story_action` 零命中 | `BR5.1`／`NFR4.46` |
| 無 router 註冊 | `BR5.3`／`NFR4.46` |
| 日誌建構函式不收任意 `kwargs` | `NFR4.63`／`BR3.6` |
| Lua 為修剪唯一生產載體 | `performance-design.md` 的唯一載體原則 |
| `load` 不存在回 `None` | `BR1.6` |
| 五個方法皆續期 TTL | `BR1.3` |
| `append_message` 需段識別 | `BR3.1` |
| 段隔離 | `BR3.2`／`AC3.1.2`／`AC6.1.3` |
| 切回不刪段、再切回到同一段 | `BR2.5`／`BR2.4`／`[S2]`=A |
| 入口頁不得切換 | `BR2.2` |
| `K-07` 例外原樣上傳且不落地 | `BR4.6` |
| **第二段也跑 allow/deny** | `BR4.7`（`[S3]`=A 新引入的授權面） |
| 超長訊息 raise `SessionMessageTooLong` | `OPEN-N10-6` |
| 三種原因碼分類 | `NFR4.62` |
| 上限缺值時啟動失敗 | `BR3.5` |

**這張表是寫測試前的 checklist，不是寫完後的整理。** 少掉其中一列，
對應的規則就沒有自動化承載——而本 repo 的教訓反覆是：沒有斷言的規則，
在 CI 全綠時依然會被違反。
