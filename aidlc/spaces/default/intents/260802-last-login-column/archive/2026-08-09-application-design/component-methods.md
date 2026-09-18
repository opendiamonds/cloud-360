# Component Methods — 公開介面簽章

> Stage: application-design（Inception 2.6）· Intent: 260802-last-login-column
> 上游來源：`../requirements-analysis/requirements.md`（下稱 requirements）、`../user-stories/stories.md`（下稱 stories）、`../practices-discovery/team-practices.md`（下稱 team-practices）、`../refined-mockups/interaction-spec.md`。
> 元件邊界見 `components.md`；本檔只定**公開介面的形狀**與錯誤處置方式。詳細業務規則屬 Functional Design 階段，不在此展開。
> **本文件為 iteration 3**，依 iteration 1、2 的 reviewer findings 修訂。

## 閱讀方式

簽章以 Python 型別標註與 TypeScript 型別表達，**是介面契約而非實作**。參數命名可在 Construction 調整，但下列三項**是契約，改動即破壞設計論據**：

1. 「當下時刻」一律為顯式參數（見 §為何當下時刻是參數）
2. 所有時間值一律為**帶時區的 UTC**（見 §時區契約）
3. C-2 自行負責交易的提交與復原（見 C-2）

---

## 時區契約（全域，iteration 1 Finding 8）

**本 intent 的所有 `datetime` 值，無論流經哪個元件，一律為帶時區的 UTC（`tzinfo` 不為 `None`）。**

這條契約不是風格偏好，而是因為 repo 目前**同時存在兩種互不相容的慣例**：既有的認證模組使用不帶時區的寫法，既有的使用者路由使用帶時區的寫法。Python 對帶時區與不帶時區的值做比較或相減會直接拋 `TypeError`。

**取得當下時刻的唯一許可寫法**：`datetime.now(timezone.utc)`（與使用者路由的既有慣例一致）。**不得**使用 `datetime.utcnow()` —— 它回傳不帶時區的值，會在第一次比較就炸掉。

**測試環境的落差**：測試使用 in-memory SQLite，而 **SQLite 不保存時區資訊**，因此帶時區的欄位讀回來會是不帶時區的值。若不處理，requirements NFR-5 所要求的第一支端點測試會在第一次比較時失敗。**收斂方式**：C-1 的兩個判定在收到不帶時區的值時，**一律視為 UTC 並補上時區**後再比較（正規化，而非拒絕）。選擇正規化而非拋錯，是因為拒絕會讓整個測試路徑無法運作，而正規化在生產環境（PostgreSQL 保存時區）不會被觸發。

此契約同時是 stories AC-1.6 交辦本站的「儲存與顯示時區策略」的設計期落點。

---

## C-1 活動時間政策

零 I/O、零框架依賴的純函式模組。這是唯一持有兩個門檻數值的地方。

```python
# 門檻常數 —— 全系統唯一定義處
ACTIVITY_WRITE_MIN_INTERVAL: timedelta   # 5 分鐘（requirements FR-1.3）
ACTIVITY_OVERDUE_THRESHOLD: timedelta    # 90 天（requirements FR-3.1）


def should_record_activity(
    last_recorded_at: datetime | None,
    now: datetime,
    min_interval: timedelta = ACTIVITY_WRITE_MIN_INTERVAL,
) -> bool:
    """距上次成功寫入是否已達最小間隔。

    時區：兩個 datetime 皆應為 tz-aware UTC；收到 naive 值時
    視為 UTC 並補上時區後再比較（見全域時區契約）。

    last_recorded_at 為 None（從未記錄）時回傳 True —— 第一次活動必須被記下。
    邊界：恰好等於 min_interval 時回傳 True（已達即可寫）。
    """


def is_activity_overdue(
    last_activity_at: datetime | None,
    now: datetime,
    threshold: timedelta = ACTIVITY_OVERDUE_THRESHOLD,
) -> bool:
    """距最後活動是否已超過逾期門檻。

    時區：同上。

    last_activity_at 為 None（無紀錄）時回傳 False —— 無紀錄不等於逾期
    （requirements FR-2.3、stories AC-2.3 已確立此語意）。
    邊界：恰好等於 threshold 時回傳 False —— requirements FR-3.1 為
    「嚴格大於」，恰好 90 天尚未逾期。
    """
```

**兩個邊界方向相反，是刻意的**：節流是「已達即可寫」（含等於），逾期是「須超過才算」（不含等於）。兩者各自對應上游已核可的措辭 —— requirements FR-1.3 的驗收條件逐字寫「距上次寫入滿 5 分鐘（**含**）之後的下一個請求觸發第 2 次寫入」，stories AC-2.1 則逐字排除「恰為 90 天者」。iteration 1 的審查已逐字核對兩者，確認各自正確、非筆誤。

**錯誤處理**：兩者皆為全函式（total function）—— 對任何合法型別的輸入都有回傳值，不拋出例外。`None` 是有意義的輸入而非錯誤。

**測試落點**：requirements 的品質約束（ADR-0006 property-based 為 hard constraint）在本 intent 的落點就是這裡。可直接表達的性質包含：兩函式對 `now` 皆單調（時間越晚，判定只會從否轉是，不會反覆）、`None` 輸入的回傳為常數、門檻兩側的判定互斥、**帶時區與不帶時區的等值輸入產生相同結果**（時區正規化的性質）。team-practices 記載既有的 8 個 property-based 測試全部落在純函式模組，本元件與該實務同形狀。

### 為何當下時刻是參數

若在函式內部取用系統時鐘，這兩個判定就無法在不操縱系統時間或不打補丁的前提下測試邊界。把它提為參數後，「恰好 90 天」「89 天 23 小時 59 分」這類斷言是一行直述。這是本設計刻意付出的介面代價（每個呼叫端都要傳 `now`），換取規則層的完全確定性。

---

## C-2 活動時間記錄器

```python
def record_activity_if_due(
    user: User,
    db: Session,
    now: datetime,
) -> bool:
    """依 C-1 判定，必要時寫入一次活動時間。

    回傳是否實際寫入並成功提交（供測試與觀測使用，呼叫端可忽略）。

    行為：
      1. 以 user 既有的欄位值呼叫 should_record_activity —— 不做額外查詢，
         該值已隨認證流程取得的 user 物件在手。
      2. 判定為否 → 直接回傳 False，不觸碰資料庫。
      3. 判定為是 → 更新欄位並 **db.commit()**。
      4. 任何例外 → **先 db.rollback()**，再記錄失敗（含使用者識別與例外
         內容），回傳 False。

    交易語意（契約，非實作細節）：
      - 必須自行 commit（理由見下）
      - 失敗時必須先 rollback 才記錄（理由見下）
      - 借用呼叫端的 session，不擁有其生命週期：不得 close
    """
```

### 交易語意為何是契約（iteration 1 Finding 3）

實測既有的 session 供應器為 `try: yield db finally: db.close()` —— **既不 commit，也不在例外路徑 rollback**，且 session 設定為不自動提交。因此兩件事都必須由本元件負責，否則設計本身不成立：

**為何必須自行 commit**：絕大多數認證端點是唯讀的（使用者清單、個人資訊，以及協作、審查、透鏡各模組的全部讀取端點），它們本身從不 commit。若本元件不 commit，待決的更新會在 session 關閉時**被整個丟棄** —— requirements FR-1.1「任何以有效憑證發出的請求都更新該帳號的最後活動時間」對這些端點永遠不成立，而函式回傳 `True` 還會謊稱寫入成功。

**在依賴階段 commit 是安全的**：本元件執行於認證依賴內，此時端點自身的業務邏輯尚未開始，session 中不存在端點的待決變更。因此這次 commit 只會提交本元件自己的更新，不會誤提交他人的未完成交易。

**為何失敗時必須先 rollback**：若只吞下例外而不 rollback，session 會進入待復原狀態。緊接著執行的權限檢查會查詢權限表，該查詢會直接拋出 `PendingRollbackError`，**使用者的原始請求照樣失敗** —— 那會直接推翻本元件「不得讓原始請求失敗」的核心承諾。rollback 之後 session 恢復可用，後續的依賴與端點邏輯不受影響。

### 失敗處置的來源聲明（iteration 1 Finding 4）

「活動時間寫入失敗不得讓使用者的原始請求失敗」這條約束**在 requirements 與 stories 中都沒有對應條文**。它是本站的設計判斷，唯一的上游依據是 construction 階段護欄的「silent failures are not acceptable」—— 而該護欄要求的是失敗必須被記錄，並未規定失敗的傳播方式。初版誤將此約束標為 requirements NFR-4（NFR-4 的實際內容是授權矩陣的雙向測試要求）。此判斷在核可 gate 上開放挑戰。

**呼叫點**：既有認證依賴的尾端，在使用者物件確立之後。該處已持有 `db` session，無需額外取得。`now` 由呼叫點以 `datetime.now(timezone.utc)` 產生。

---

## C-3 使用者資料模型與既有庫補欄

```python
# 使用者模型新增欄位
last_activity_at = Column(DateTime(timezone=True), nullable=True)
```

**可為空是必要的**，不是寬鬆設計：功能上線時既有帳號全部無值（requirements C-1），這正是 requirements FR-2.3 與 stories AC-2.3 所描述的無紀錄態的來源。若設為非空並給預設值，會讓「從未活動」與「剛剛活動」在資料上無法區分 —— 直接摧毀本 intent 的核心語意。

**帶時區**與既有慣例一致（requirements C-5；iteration 1 實測確認既有 9 個 datetime 欄位全部採此形式）。**不設資料庫層預設值**，理由同上。

```python
def _ensure_<id>_schema() -> None:
    """為既有資料庫補上本 intent 的欄位。

    形狀沿用既有的兩個同類先例（皆為往使用者表加欄位）：
      ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at
        TIMESTAMP WITH TIME ZONE

    以 IF NOT EXISTS 保證可重複執行；由既有的啟動流程呼叫。
    """
```

**同步義務**（requirements **C-4**，blocking）：本欄位的 DDL 必須同步寫入 repo 根目錄的 schema 檔與部署文件。未同步即不得標示相關階段完成。
（iteration 1 Finding 6：初版將此義務誤標為 requirements C-2／C-3；那兩條的實際內容分別是「無遷移框架、須重啟生效」與「禁止重跑整份腳本」。）

**部署後須重啟**（requirements C-2、stories AC-1.7）：補欄在服務啟動時執行，因此部署後必須完成一次重啟，欄位才會存在。

**測試環境不受影響**：iteration 1 實測確認測試從不呼叫啟動流程，而是直接由模型建表，因此 PostgreSQL 專屬的 `ADD COLUMN IF NOT EXISTS` 語法（SQLite 不支援）在現行測試路徑上不會執行。

---

## C-4 使用者物件序列化

既有的使用者回應結構新增兩欄：

```python
last_activity_at: datetime | None   # UTC；None 表示無紀錄
is_overdue: bool                    # 由 C-1 計算，非儲存欄位
```

`is_overdue` 是**衍生值不是儲存值** —— 不進資料庫，每次序列化時以當下時刻呼叫 C-1 計算。這保證它永遠反映請求當下的判定，不會因為資料陳舊而失準。

### 三個構造點的一致性約束（iteration 1 Finding 1）

requirements FR-2.5 要求**所有回傳使用者物件的端點**都包含此欄位（「使用者物件」的邊界定義見 `components.md` C-4）。實測既有程式碼，回應模型在三處被構造，**三處全部都是手寫具名引數**（全 repo `from_orm` 使用數為 0）：

| 構造點 | 形式 |
|---|---|
| 使用者清單端點 | 手寫具名引數 —— 本 intent 的主要顯示路徑 |
| 啟停用端點 | 手寫具名引數 —— 已知會漏欄位 |
| 角色調整端點 | 手寫具名引數 —— 已知會漏欄位 |

（iteration 2 Finding N2：初版把清單端點記為「隨查詢結果序列化」，與程式碼不符。三處形式相同、風險相同。）

**契約（二擇一，Construction 定實作）**：

- **選項一** —— 兩個新欄位在回應模型上**不設可靜默通過的預設值**。缺漏時立即失敗，讓問題在測試而非生產暴露。
- **選項二** —— 三個構造點改走**單一的共用工廠函式**（接受使用者物件與當下時刻，回傳回應物件），使分歧在結構上不可能發生。
  （iteration 2 Finding N8：初版並列了「ORM 自動轉換」分支，但該分支不可行 —— `is_overdue` 是衍生值不是儲存欄位，ORM 物件上不存在該屬性。要讓自動轉換成立就得在模型層加一個自行取用系統時鐘的 property，那會把 C-1 刻意參數化的「當下時刻」在邊界處重新藏回去，與其可測性設計直接衝突。）

**不可接受的做法**：給欄位一個預設值然後只改清單端點 —— 那會讓兩個 PUT 端點回傳空值與否，**完整複製既有缺陷**，而 stories AC-1.5 逐字要求「而非因構造遺漏而缺失」，該驗收條件直接失敗，且**所有現有測試都會是綠的**。

**序列化前的時區正規化**（iteration 2 Finding N7）：`last_activity_at` 從資料庫直通序列化時，在 SQLite 測試路徑下讀回為不帶時區的值，序列化後不帶偏移量 —— 若 requirements NFR-5 的端點測試斷言 UTC 形式會失敗，而那正是 team-practices 規則 B 的第一支測試。**因此序列化前亦須套用同一正規化**（不帶時區者補為 UTC），使「回應一律為 UTC」在測試與生產兩條路徑上都成立。

**空值語意**：`last_activity_at` 為 `None` 時 `is_overdue` 必為 `False`（C-1 的契約已保證）。這兩欄不會出現「無紀錄卻標記逾期」的組合，前端不需防禦此情形。

**授權**：可見性由既有的端點層權限檢查決定（requirements FR-4.2 已定不做欄位級控制）。序列化層不自行判斷誰看得到。權限**資料**的變更屬 C-7。

**測試義務**：requirements NFR-5 與 team-practices 規則 B —— 新增或修改的端點需以測試客戶端斷言 status code 與回應欄位集合。此斷言正好覆蓋 FR-2.5 的三個構造點，是本 intent 中唯一能自動抓到「某個端點漏了欄位」的機制。

---

## C-5 最後活動時間儲存格

```typescript
interface LastActivityCellProps {
  lastActivityAt: string | null;   // ISO 8601 UTC；null 表示無紀錄
  isOverdue: boolean;              // 由呼叫端傳入，元件不自行計算
}
```

兩者皆為必填，型別**不含 `undefined`** —— 正規化責任在 C-6（見下）。

**`isOverdue` 為傳入值**：refined-mockups `interaction-spec.md` 已定此形狀（避免在算繪過程讀取當下時刻所觸發的 lint 規則違反）。本站 Q2 的定案讓這個值有了明確來源 —— 來自 API 回應，而非前端計算。

五種狀態的視覺規格、色階與可及性屬性全部已定於 refined-mockups 的 `interaction-spec.md` 與 `design-system-mapping.md`，本檔不重述。

---

## C-6 管理頁資料傳遞

無新增公開介面 —— 既有頁面元件的內部擴充。契約層面有四點：

1. 表頭新增一欄，位置為角色之後、操作之前（refined-mockups 已定）
2. 每列將 API 回應的兩個欄位傳給 C-5，**傳遞前完成正規化**（見下）
3. 小螢幕斷點以下改用卡片佈局（refined-mockups 已定斷點值）
4. 不需要額外資料源，故 requirements C-6 的抓取形狀約束自動滿足

**正規化契約**（iteration 1 Finding 10）：C-5 的兩個 props 皆為必填且不含 `undefined`，但實測前端的使用者型別是手寫介面、資料抓取未做欄位驗證或白名單，因此**後端尚未部署時這兩個欄位會是 `undefined`**。本元件必須在傳遞點收斂：

```typescript
lastActivityAt={u.last_activity_at ?? null}
isOverdue={u.is_overdue ?? false}
```

這使「部署順序無硬性約束」的論證真正成立，而不只是因為執行期碰巧不會爆。

**明確不變更**：載入態與錯誤態沿用既有整塊替換模式（stories AC-1.9）；既有的角色欄空值呈現不動（stories AC-2.5 定案為僅以可及性區分新欄位）。

---

## C-7 權限預設值變更與既有環境套用

**本元件為 iteration 2 新增**（iteration 1 Finding 2）。

### 兩處預設值來源

requirements FR-4.3 要求該角色的權限值在**兩處來源**同步，任一處未同步即視為未完成：

| 來源 | 角色 |
|---|---|
| 種子資料模組 | 新建環境由程式碼路徑初始化時使用 |
| 資料庫初始化腳本 | 新建環境由 SQL 路徑初始化時使用 |

兩處皆須將該角色對使用者管理功能的檢視權限由關閉改為開啟。

### 既有環境的套用機制

```python
def _ensure_<id>_permissions() -> None:
    """為既有資料庫套用本 intent 的權限變更。

    契約（三項皆為契約，非實作細節）：
      1. **執行順序** —— 必須在既有的權限種子函式**之後**呼叫。
         不得與 C-3 的補欄補丁並列於建表之後的位置（理由見下）。
      2. **只更新、不插入** —— 權限表為空時不做任何事，
         由既有種子函式負責建立完整矩陣。
      3. **條件式更新** —— 僅在該列尚未被本補丁套用過時才更新，
         以既有的「最後異動者」欄位作為套用標記（見下）。
      4. **可觀察性** —— 記錄三態之一：已套用／已跳過（已套用過或
         已被管理員調整）／**未命中目標列**。第三態不是例外，
         沒有明確記錄就無法在啟動日誌上發現（見下）。
    """
```

### 為何執行順序是契約（iteration 2 Finding N1）

實測既有初始化流程的順序為：建表 → 三個補欄補丁 → 使用者種子 → **權限種子**。而既有的權限種子函式**僅在權限表為空時寫入**。

若本元件放在補欄補丁的位置（即權限種子之前）並具備插入能力，在空表環境會發生：本元件先插入一列 → 權限表不再為空 → 種子函式判定「表非空」直接返回 → **308 列預設矩陣一列都不寫入** → 全系統 RBAC 端點盡數拒絕存取。

此情境可達（repo 根目錄的本機開發編排檔未掛載初始化腳本，該路徑完全依賴 Python 種子），且**無任何測試會發現**（測試輔助模組以強制模式直接建矩陣，不經初始化流程）。

因此「不存在時插入」的分支明確排除 —— 既有種子已涵蓋該列，該分支只有製造上述故障的能力。

### 為何是條件式而非無條件更新（iteration 2 Finding N4）

無條件更新等於**每次服務重啟都把該權限強制設回開啟**。管理員若日後刻意撤銷，下一次部署會靜默復原，而權限變更的稽核記錄是易失性的（requirements C-7），撤銷會消失且無跡可循。這與 AD-7 否決「重跑種子強制模式」的理由自相矛盾。

**契約**：以權限表**既有的「最後異動者」欄位**作為套用標記（iteration 3 Finding M1）。單看權限值無法區分「從未套用」與「已套用後被管理員撤銷」（兩者都是關閉），但該欄位可以 —— 其取值在三條路徑上互斥：種子寫入為固定系統識別字、初始化腳本寫入為空、**管理員經管理介面調整時為管理員帳號**。

- **更新條件**：該欄位為空或等於種子的系統識別字
- **更新後**：把該欄位標記為本補丁的專屬識別字
- **管理員撤銷後**：該欄位為管理員帳號，不符更新條件，撤銷得以保留

**零新表、零新 DDL、零額外的部署資產同步義務。** 初版要求「新增一張標記表」會觸發 requirements C-4 對新增表的 blocking 同步義務並需要另一個建表補丁 —— 在既有欄位已足夠的前提下屬不必要的成本。

### 為何需要三態記錄（iteration 3 Finding M2）

目標式更新影響 0 列**不是例外**，沿用既有補丁的例外捕捉形狀看不到它。本元件的存在理由正是「這件事會靜默落空」，若它自己的套用結果沒有可觀察的訊號，就等於在剛封死的缺口旁邊留一個新的。因此三態（已套用／已跳過／未命中）必須各自記錄，使「未命中目標列」成為能在啟動日誌上發現的事實。

這也是本元件在既有測試路徑上唯一的驗證手段 —— 見下方 §驗證缺口。

### 驗證缺口（iteration 3 Finding M2）

**requirements NFR-4 的雙向測試涵蓋不到本元件。** 實測測試輔助模組以強制模式直接由預設矩陣建表、**從不呼叫啟動流程**，因此該測試驗證的是種子預設值是否已改（FR-4.3 的一半），與本元件是否存在、順序是否正確、是否真的更新到既有庫**完全無關** —— 把本元件整個刪掉，該測試照樣通過。

因此本元件在既有測試路徑上**沒有自動化驗證**，須以「部署後人工核對 + 啟動日誌的三態記錄」承接，並登錄為已知限制（處理方式比照 §FR-4.3 的第③項）。

### FR-4.3 的一致性檢查落點（iteration 2 Finding N5）

**須揭露的既有事實**：種子資料模組的檔頭寫著「由初始化腳本產生（勿手改）」，但**該產生腳本不存在於 repo**（codekb 已登錄為風險項，緩解欄為「無」）。因此「兩處同步」目前既無工具也無驗證。

**處置**：①本 intent 以手動修改同步兩處，並在 PR 說明記載該檔頭契約已失效；②新增一支比對兩處預設值的測試（至少涵蓋本次變更的那一列），放進既有後端測試目錄即被現有測試指令撿到，零新依賴；③若②超出範圍，須明寫 FR-4.3 以人工核對承接並登錄為已知限制，不得留白。

**為何必須是目標式而非重跑種子**：實測既有的種子函式**僅在權限表為空時寫入**（表中已有資料就直接返回 0），因此改了預設值對既有環境完全無效。而它的強制模式會**刪光整張權限表再重寫**，那正是 requirements C-3 要避免的重置 —— 會覆寫管理員在管理介面上對其他角色所做的全部調整。

**若不做這個元件會怎樣**：兩處預設值改了、所有測試綠燈、CI 通過、部署成功，而既有 staging 上該角色的權限**依然是關閉的**。stories AC-3.4 正是為了防止這件事而寫的驗收條件。這是本 intent 中最容易靜默落空的一項。

**同步義務**（requirements C-4，blocking）：權限 seed 的語意變更屬部署資產同步的觸發條件，schema 檔與部署文件須同步更新。

**測試義務**（requirements NFR-4、team-practices 規則 A）：需有測試**同時**驗證該角色可檢視、且未獲授權角色不可檢視 —— 雙向，缺一不可。

---

## 介面契約摘要

| 元件 | 對外承諾 | 對內依賴 |
|---|---|---|
| C-1 | 兩個全函式，確定性，不拋例外；時區正規化 | 無 |
| C-2 | 自行 commit；失敗先 rollback 再記錄；不 close session | C-1、C-3 |
| C-3 | 欄位可為空、帶時區、無預設值；補欄可重複執行 | 無 |
| C-4 | 兩欄在**所有**使用者物件端點必達；無紀錄時逾期必為否 | C-1、C-3 |
| C-5 | 五狀態呈現；不自算逾期 | 無 |
| C-6 | 傳遞前正規化為 C-5 的宣告型別 | C-4（HTTP）、C-5 |
| C-7 | 只更新不插入；在權限種子之後執行；條件式套用 | 無（與 C-3 分屬不同資料表） |
