# Infrastructure Design 問題檔 — `U19 membership-service`

> Depth 為 `Minimal`。本單元**零新基礎設施**（零新進程、零新監聽埠、零新環境變數、
> 零新外部服務、零新資料庫物件），故本站只有**一個**實質決定：
> **併發測試的 CI 載體**。
>
> 這一題是上一站自己交接下來的（`logical-components.md §四` 逐字：
> 「新 CI job — **本站不預選**」），不是本站新造的。

## 〇、不重問的事（上游已定案，可引用原文）

| 事項 | 定案處 |
|---|---|
| 零新進程／埠／環境變數／外部服務／資料庫物件 | `logical-components.md §四` 的五列表 |
| 鎖的機制與對象（父 `projects` 列 `FOR UPDATE`） | `[N1]`=A；`NFR12.1`–`NFR12.5` |
| 鎖的取得順序（`projects.id` 遞增） | `security-design.md §一之二`（本 intent 自己的設計，非待決） |
| 不設快取、不加索引、不設鎖等待逾時 | `performance-design.md §一`／§二之二／§三 |
| 四類 log 的級別與欄位、事件名前綴 | `observability-design.md §一` |
| 四項觀測面刻意不設（追蹤／metrics／告警／SLO） | `observability-design.md §二`；承接 `OPEN-ND19-7` |
| 回填的承載形式（獨立腳本、大聲失敗、`DEPLOY.md` 記步驟） | `reliability-design.md §三`（沿用 `U18` 的 `[P1]`=A 先例） |
| 回填是否與 `U18` 的腳本合併成一支 | **`OPEN-N19-4`，已指派 `code-generation`**——不在本站 |
| 鎖等待的 WARN 門檻值 | **`OPEN-ND19-6`，已指派 `code-generation`**——不在本站 |

---

## 一、`[ID1]` 併發測試要掛在哪個 CI 載體上？

### 為什麼這是一題：`[N1]`=A 選的機制在既有測試路徑上**靜默消失**

本站實測（`sqlalchemy 2.1.1`，執行時間 2026-10-07T00:10Z 前後）：

```
db.query(P).filter(P.id == 1).with_for_update()
```

在 SQLite dialect 下編譯出來的 SQL 是

```
SELECT p.id, p.name FROM p WHERE p.id = ?
```

**`FOR UPDATE` 整段不見了，而且沒有錯誤、沒有警告。**
故一個跑在既有測試路徑（`backend/tests/helpers.py` 的 in-memory SQLite）上的
「併發守門」測試，會在**完全沒有鎖**的情況下通過——它驗證的是空氣。
這比「測試失敗」嚴重，因為綠燈會被當成證據。

### 既有 CI 的機械事實（本站以腳本解析 `ci.yml` 的 `needs:` 邊，非憑印象）

| 事實 | 值 |
|---|---|
| job 總數 | **6**：`gate`／`repo-contract`／`frontend`／`backend`／`memory-schema`／`docker-build` |
| 依賴邊 | `gate` 無 needs；**其餘五個全部且僅 `needs: gate`** → 彼此**並行** |
| 唯一有真實 PostgreSQL 的 job | `memory-schema`（`pgvector/pgvector:pg18` service container），但它**只跑 `psql`，沒有 setup-python、沒有 pip install** |
| 既有單元測試的執行方式 | `backend` job 的 `python -m unittest discover -s tests -v`，**無 PostgreSQL service** |
| `backend/tests/` 內需要真實 PostgreSQL 的測試 | **0 個**（51 個測試檔全部走 SQLite 或 mock）——本單元是第一個 |
<!-- 提問時此格寫「52 個測試檔」，為估值而非實算。送審前自檢 6 以
     `ls backend/tests/test_*.py | wc -l` 實算為 **51**，就地更正。
     該數字不影響本題的答案（兩個值之下「需要真實 PG 的既有測試」都是 0）。
     **但它確實出現在呈現給使用者的選項 D 描述裡**（「52 個檔走 SQLite、
     1 個走真實 PG」），故如實記載：使用者看到的那段文字帶了一個差 1 的估值。
     使用者選的是 A 而非 D，故該誤差未影響決定；選項 D 的本文亦就地更正為 51。 -->

| `skipUnless`／`skipIf` 的既有先例 | **0 個**（全樹 grep） |

**所以放在 `backend/tests/` 的真實 PG 測試會被 `discover` 撿到並在該 job 連線失敗**
（該 job 的測試步驟只設 `JWT_SECRET`，沒有 PostgreSQL 可連）。
位置與閘門不是風格問題，是「會不會紅燈」與「會不會靜默跳過」的問題。

### 選項

| 選項 | 做法 | 代價與風險 |
|---|---|---|
| **A（建議）** | **新增一個 job（如 `concurrency`，`needs: gate`）＋ 新測試根目錄 `backend/tests_pg/`**，該 job 自帶 postgres service container、`setup-python` ＋ `pip install`，執行 `python -m unittest discover -s tests_pg` | **覆蓋面不可能靜默消失**：新目錄不被 `discover -s tests` 看到（結構性隔離，不是條件式跳過），而 job 自己是一個 check，缺了看得出來。並行執行故**wall-clock 成本 ≈ 0**（五個 job 已全部並行）；`cache-dependency-path` 同為 `backend/requirements.txt`，共用 `backend` job 已填的 pip cache。check name 是**新增**而非改名，branch protection 不受影響（`memory-schema` 的註解逐字記載：改名才危險）。代價：第二座 postgres container 的 runner 分鐘數；兩個測試根目錄要被知道 |
| **B** | **擴充既有 `memory-schema` job**：加 `setup-python` ＋ `pip install` ＋ 執行測試；測試仍放新目錄 `backend/tests_pg/` | 重用已經在跑的 container，不多一座。代價：① pip install 是**串行**加進該 job 的 wall-clock（目前它只跑 `psql`，不需要 Python）；② 該 job 的 name 已經「比內容窄」（它的註解自承 `U18` 的 `P1`–`P12` 也掛在這裡，刻意不改名以保護 check name），再掛第三類東西會讓「Memory schema」這個名字第三次失真 |
| **C** | **測試留在 `backend/tests/`，用 env guard 跳過**（`@unittest.skipUnless(os.environ.get("CLOUD360_PG_TESTS") == "1", ...)`），在有 PG 的 job 裡設該變數 | 單一測試根目錄，`discover` 不會炸。**但 `unittest` 的跳過與通過在輸出上無法分辨**（`OK (skipped=1)`）：哪天那個環境變數從 job 裡掉了，覆蓋面會**靜默消失而 CI 全綠**——這正是 `project.md` 反覆記載的失敗類別（無聲降級），也正是 `tcms-test-cases` 規則存在的理由。另：全樹零 `skipUnless` 先例，本選項同時引入一個新慣例 |
| **D** | **給既有 `backend` job 加一個 postgres service container**，單一測試根目錄、不需 guard | 最小 diff、一個測試根。代價：把 container 啟動時間加到**最常紅燈、最該快**的那個 job 的關鍵路徑上；且該 job 會同時存在兩種 DB 策略（51 個檔走 SQLite、1 個走真實 PG），下一個人讀 `helpers.py` 時要先分辨自己在哪一種裡 |

[Answer]: A 新 job ＋ 新測試根目錄
<!-- 作答時間 2026-10-07T00:55:02Z，以 `date -u` 取值 -->

**後果（本站據此寫成設計）**：

1. **新 job**（名稱在產出內定為 `concurrency`，`needs: gate`），自帶
   `pgvector/pgvector:pg18` service container ＋ `setup-python` ＋
   `pip install -r backend/requirements.txt`，執行
   `python -m unittest discover -s tests_pg`。
2. **新測試根目錄 `backend/tests_pg/`**。隔離是**結構性**的：既有
   `discover -s tests` 看不到它，故不需要任何 env guard，也不會在
   `backend` job 連線失敗。
3. **check name 只新增、不改名。** `memory-schema` 的註解逐字記載改名會讓
   branch protection 的必要檢查變成「缺少必要檢查」；新增不觸發該風險。
4. **`memory-schema` 維持只跑 `psql`**，不加 Python 步驟——它的 name 已經
   比內容窄兩次，第三次失真的成本高於一座 container 的 runner 分鐘數。
5. 兩個測試根目錄的存在本身是一項需要被寫下的事實，否則下一個人新增
   真實 PG 測試時會放回 `backend/tests/` 並踩同一個洞。寫進
   `cicd-pipeline.md` 的判準表。

