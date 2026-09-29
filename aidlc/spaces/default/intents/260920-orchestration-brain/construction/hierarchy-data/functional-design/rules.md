# Business Rules — `U4 hierarchy-data`（`spec`）

<!-- Stage: functional-design（Construction 3.1）· Unit: hierarchy-data · kind: spec -->

## 〇、這個單元的「業務規則」是什麼

`U4` 交付資料模型與一次性遷移。它的規則分三類：

1. **結構不變量**（`BR1.*`）：刪除行為與參照完整性。違反者由**資料庫層**擋下——
   這一類的價值就在於它不依賴任何程式流程記得做檢查。
2. **遷移不變量**（`BR2.*`）：遷移必須達成什麼、重跑時必須維持什麼、違反時怎麼失敗。
3. **消費端義務**（`BR3.*`）：本單元交付的資料被別的單元讀取時，那些單元必須做的事。
   它們在本單元**無法強制**，逐條標明落點。

**本單元沒有 `authorization` 類規則**——`K-04` 逐字「授權責任：**無**」。

---

## 一、source of truth

```yaml
rules:
  # === BR1.* 結構不變量（資料庫層擋下）===
  - id: BR1.1
    statement: Project 底下仍有 System 時，刪除該 Project 必須被拒絕
    category: constraint
    applies_to: Project 的刪除
    trigger: 任何刪除 Project 的嘗試
    logic: >
      IF 存在任一 System.project_id 指向該 Project THEN 拒絕該刪除。
    violation_behaviour: >
      刪除被拒絕，資料未改變。**錯誤訊息的內容不屬本單元**——見 BR3.2。
    source: Q1=A 的上層對應（DG-2 的同型處置）

  - id: BR1.2
    statement: System 底下仍有架構圖時，刪除該 System 必須被拒絕
    category: constraint
    applies_to: System 的刪除；ArchitectureDiagram.system_id 的參照
    trigger: 任何刪除 System 的嘗試
    logic: >
      IF 存在任一 ArchitectureDiagram.system_id 指向該 System THEN 拒絕該刪除。
    violation_behaviour: >
      刪除被拒絕，資料未改變，**且沒有任何一張圖的 system_id 被設為空**。
    source: >
      **Q1=A，這是 DG-2 的解——就「刪除造成懸空」這一條路而言**（DG-2 原本的範圍正是刪除，見下方引文；遷移之後的另兩條路是 OQ-H2，本單元未關，見 functional-spec.md §八，iteration 2 審查 R-08）。 domain-design 的 decisions.md:134–137 逐字留下這個缺口：
      「該不變量在執行期可被打破：遷移後若有人刪掉一個 System，其下架構圖的 system_id
      會懸空，AC9.1.4 要求計數為 0 的條件即不再成立……本 ADR 只保證遷移程序本身，
      不保證遷移之後的維持」。本規則把「產生懸空」這個動作變成**不可執行**，
      使 BR2.1 的不變量在**刪除這條路上**由「遷移當下成立」升級為「執行期持續成立」。
      **不是全部的路**：本規則不禁止直接把已掛好的圖的 system_id 改回空，也不要求
      新插入的圖必須帶它（本欄永遠可為空）——那兩條是 OQ-H2（審查 R-08）。
      **為何不選 SET NULL**：那正是把 system_id 設為空，直接製造 BR2.1 的違反。
      **為何不選 CASCADE**：架構圖是使用者的核心資產，而 user_diagrams 對 users.id
      的既有 FK 連 ondelete 都沒有——CASCADE 會讓「刪系統」比「刪使用者」更具破壞性。

  - id: BR1.3
    statement: 每位使用者至多一個預設 Project；每個 Project 至多一個預設 System
    category: constraint
    applies_to: Project.is_default、System.is_default
    trigger: 遷移建立預設專案／系統時；任何寫入 is_default 為真的嘗試
    logic: >
      **兩層各自獨立的唯一性，各自只引用自己表內的欄位**：
      (1) IF 該使用者已有 is_default 為真的 Project THEN 不得再建立第二個
          （範圍：Project.owner_user_id）。
      (2) IF 該 Project 底下已有 is_default 為真的 System THEN 不得再建立第二個
          （範圍：System.project_id）。
      **「每位使用者至多一組預設專案／系統」是這兩層的遞移結果**，不是一條獨立約束：
      使用者至多一個預設 Project，而預設 System 建在該預設 Project 之下。
    violation_behaviour: >
      寫入被拒絕。**這正是遷移冪等的機制**：重跑時「存在就取用、不存在才建」
      在**各自的表內**由約束保證，不靠程式流程記得檢查。
      **但兩表之間的配對不是**——「同一位使用者的預設 System 落在他的預設 Project 底下」
      沒有任何約束擋，由 BR2.5 的流程供應（見 §三，審查 R-07）。
    source: >
      Q3=A。**審查 R-01（Critical）更正**：初版把 System 的唯一性寫成以**擁有者**為範圍，
      而 System 沒有 owner_user_id 欄位——唯一性約束**無法以另一張表 join 來的值為範圍**，
      照初版描述**做不出來**，而 BR2.2 的整個冪等論證正是建立在「由資料庫約束保證」之上。
      **本站不採審查建議的兩個選項**（(a) 在 System 反正規化一個 owner 欄位、
      (b) 改用 trigger），理由：(a) 新增一個上游 components.md 沒有的欄位，
      且製造「它與 Project.owner_user_id 如何保持一致」這個新的完整性問題；
      (b) trigger 是程式邏輯，會讓「不依賴程式流程記得檢查」這句話變成不實。
      改以 project_id 為 System 的唯一性範圍——**兩個約束都只引用自己表內的欄位、
      都是可建的**，零新增欄位、零 trigger。
      **但遞移得到的保證不完全等於原意**：複合性質「每位使用者至多一組預設」還需要
      「預設 System 總是建在預設 Project 底下」這個**沒有約束擋住**的前提，
      而那由 BR2.5 的流程供應——所以 (b) 那句對 trigger 的反對理由，
      在複合這一層其實也適用於現行做法（審查 R-07）。差別是現行做法把程式依賴
      收在單一寫入端（遷移）身上並已誠實記載於 §三，而不是散在 trigger 裡。

  # === BR2.* 遷移不變量 ===
  - id: BR2.1
    statement: 遷移完成後，system_id 為空的架構圖列數必須為 0
    category: validation
    applies_to: ArchitectureDiagram.system_id
    trigger: 遷移程序的終檢
    logic: >
      IF 計數不為 0 THEN 遷移程序**大聲失敗**。
    violation_behaviour: >
      **必須是失敗，不得是警告。** AC9.1.4 逐字「若不為 0，遷移程序必須大聲失敗，
      不得以警告帶過」，而 stories.md:426 明寫這條 AC 的目的就是
      「直接否掉照抄既有 logger.warning 形狀的實作」。
    source: AC9.1.4 逐字；K-04 on_violation

  - id: BR2.2
    statement: 遷移必須冪等——重跑時已掛好的圖不得被重新指派
    category: constraint
    applies_to: 遷移程序
    trigger: 遷移程序的每一次執行（含部分失敗後的重跑）
    logic: >
      IF 某張圖的 system_id 已非空 THEN 跳過它，不重新指派。
      IF 該使用者已有預設專案／系統 THEN 取用既有的，不建立第二組
      （第二個預設 Project 由 BR1.3 的約束保證；第二「組」的配對另需本規則自己的
      獨佔寫入紀律——先解析預設 Project、再以其 id 為範圍找 System，見 rules.md §三，審查 R-07）。
    violation_behaviour: >
      部分失敗後的重跑會產生第二組預設專案／系統，使用者的專案清單出現重複項，
      且第一組底下的圖與第二組底下的圖分屬不同系統——一個**看起來成功**的錯誤結果。
    source: >
      K-04 retry_and_idempotency 逐字要求冪等，但**未定義判準**；判準由 Q3=A 定為
      「system_id IS NOT NULL」。
      **為何不以「該使用者是否已有預設專案」為判準**：部分失敗時會漏——
      預設專案已建、圖只掛了一半就失敗的情形下，重跑會整個跳過該使用者，
      剩下那一半永遠為空，而 BR2.1 會在最後大聲失敗**且指不出是誰**。
      **為何不每次全表重算**：那會覆蓋掉遷移之後使用者自己做的歸屬調整——
      一個看起來冪等、實際會毀掉使用者資料的做法。

  - id: BR2.3
    statement: 遷移不得修改架構圖的任何既有欄位
    category: constraint
    applies_to: ArchitectureDiagram 的既有欄位（owner_user_id、title、xml_data、updated_at）
    trigger: 遷移程序寫入時
    logic: >
      遷移只寫 system_id。owner_user_id 保留其既有語意「誰建的」，
      **不因新階層而改指**。
    violation_behaviour: >
      AC9.1.2（遷移後圖仍能開啟並編輯）與 AC9.1.3（既有頁面行為不變）同時失守。
    source: >
      decisions.md ADR-002。該 ADR 的 Alternatives Rejected 逐字記載為何不改指：
      「需 backfill 全部既有列，而執行 backfill 的機制會**靜默吞掉失敗**……
      一個不可逆的改動 ＋ 一個會靜默失敗的執行路徑，是本 repo 反覆受害的組合」。

  - id: BR2.4
    statement: 遷移必須有可被測試程式匯入並呼叫的入口
    category: constraint
    applies_to: 遷移程序的形式
    trigger: 遷移程序的設計
    logic: >
      IF 遷移只存在於啟動路徑的副作用中，或只存在於僅在空資料庫執行的結構定義檔中
      THEN 違反。它必須是一個可被獨立呼叫的單元。
    violation_behaviour: >
      AC9.1.2 只能手動驗證。stories.md:413–419 逐字記載這個失敗模式：兩個環境走
      **不同的結構路徑**，CI 每次重建資料庫，而 AC9.1.2 的 Given（一張在本 intent
      之前建立的架構圖）在每個自動化環境裡**都不可達**。
    source: K-04 migration.entrypoint 逐字

  - id: BR2.5
    statement: 遷移為每位持有圖的使用者建立恰好一組預設專案與預設系統
    category: constraint
    applies_to: 遷移程序
    trigger: 遷移程序執行時
    logic: >
      FOR EACH 持有至少一張架構圖的使用者：取得或建立其預設 Project 與預設 System，
      把其全部 system_id 為空的圖掛入該 System。
      **不持有任何圖的使用者不建立預設專案**——那會產生一批沒有內容的空專案。
    violation_behaviour: >
      使用者的圖無處可掛，BR2.1 在終檢時失敗。
    source: K-04 migration.action 逐字；「不持有圖者不建立」為本站的收窄

  - id: BR2.6
    statement: 遷移的執行必須留下可據以判斷進度的計數紀錄
    category: constraint
    applies_to: 遷移程序
    trigger: 遷移程序的每一次執行
    logic: >
      遷移執行後必須記錄至少三個計數：處理了幾位使用者、建立了幾組預設專案／系統、
      改寫了幾張圖的 system_id。
    violation_behaviour: >
      部分失敗後**無從判斷做到哪**——BR2.1 的終檢會大聲失敗，但失敗訊息只說得出
      「還有 N 張圖為空」，說不出「已經處理過哪些使用者」，使重跑前的判斷失去依據。
      注意這與 BR2.1 的大聲失敗是兩件事：那條管**失敗時要不要出聲**，
      本條管**成功與失敗都要留下多少資訊**。
    source: >
      **審查 R-04（Minor）升格。** 初版只在 functional-spec.md §六 的 Audit logging 列
      寫成一句「必須留下紀錄」的旁述，既無 id、無落點，也不在回補表內——
      而本站其他每一項新增義務（S-1／S-2／S-3／BR3.2）都有。
      它比旁述更接近一條可測規則，故升為 BR2.6。**落點 code-generation**（遷移的實作者）。

  # === BR3.* 消費端義務（本單元無法強制，逐條標明落點）===
  - id: BR3.1
    statement: 讀取 DiagramChangeRecord 者必須先讀 source，不得把它當成完整的變更歷程
    category: policy
    applies_to: 未來任何 DiagramChangeRecord 的讀取端
    trigger: 讀取該表時
    logic: >
      IF 讀取端把全部列當成「這張圖的完整變更歷程」THEN 它的結論是錯的——
      本輪唯一的寫入端只涵蓋大腦交辦的異動，經既有頁面直接編輯的不在其中。
    violation_behaviour: >
      呈現出一份看起來完整、實際缺了一半的歷程。**這種誤解在資料上看不出來**
      （表裡有列，只是少了一半），所以只能靠這條規則在讀取端成立時被讀到。
    source: >
      Q4=A。落點：未來的讀取端（本 intent 內不存在，見 Q2=A）。
      **必須連帶讀到的取捨（審查 R-05）**：使用者在 Q4 選的是「讓表名說真話」，
      而本站以 source 欄位取代改名。那個取代是經揭露並重新確認的，但它**實質上比
      使用者要求的弱**——改名會讓誤解在**看到表名的當下**就不可能發生，
      而現在的保護完全落在本條規則上，而本條是 policy 類、本單元**無法強制**、
      且今天**零讀取端**。換句話說：一個未來的讀者若不知道要先看 source，
      他看到的仍是一張**看起來像完整變更歷程**的表。
      這是已接受的殘餘風險，在此與機制並列，使讀設計紀錄（而不只是問題檔）的人看得到。

  - id: BR3.2
    statement: 刪除被 BR1.1／BR1.2 拒絕時，必須回傳可理解的錯誤並指出下一步
    category: policy
    applies_to: U7 hierarchy-service（K-07 facade）
    trigger: 刪除 Project 或 System 被拒絕時
    logic: >
      IF 刪除被拒絕 THEN 回應必須說明**為什麼**（其下還有 N 個系統／N 張圖）
      與**下一步**（先把圖移出，或先刪除它們）。
    violation_behaviour: >
      使用者只看到一個不明所以的伺服器錯誤，而資料庫層的保護會被誤讀為系統壞掉。
      不變量保住了，但使用者沒有任何方法刪掉一個空不掉的系統。
    source: >
      **Q1=A 製造的新義務。** 本單元只定義約束，不定義錯誤訊息——
      US9.2（建立／修改／刪除）由 story map 指給 U7／U16／U3，不是 U4。
      落點 **U7**（介面面）與 **U16**（畫面面）。**屬本階段新增，需回補 scope（S-3）。**

  - id: BR3.3
    statement: 歸屬的權威來源是 system_id，不是 owner_user_id
    category: policy
    applies_to: 任何需要判斷「這張圖屬於誰／哪裡」的單元
    trigger: 查詢架構圖的歸屬時
    logic: >
      IF 需要知道圖屬於哪個系統 THEN 讀 system_id。
      owner_user_id 只回答「誰建的」，**不回答歸屬**。
    violation_behaviour: >
      兩個欄位在遷移後可能指向不同的人（A 建的圖被移到 B 的系統下），
      以 owner_user_id 判斷歸屬會得到錯誤答案。
    source: decisions.md ADR-002 逐字。落點：U7、U10、U14
```

---

## 二、規則摘要表（由上方 yaml 衍生）

| 類別 | 規則數 | 規則 id |
|---|---|---|
| 結構不變量（資料庫層擋下） | 3 | `BR1.1`–`BR1.3` |
| 遷移不變量 | 6 | `BR2.1`–`BR2.6` |
| 消費端義務（本單元無法強制） | 3 | `BR3.1`–`BR3.3` |
| **合計** | **12** | — |

依 category 分佈：

| category | 規則數 | 規則 id |
|---|---|---|
| `constraint` | 8 | `BR1.1`、`BR1.2`、`BR1.3`、`BR2.2`、`BR2.3`、`BR2.4`、`BR2.5`、`BR2.6` |
| `validation` | 1 | `BR2.1` |
| `policy` | 3 | `BR3.1`、`BR3.2`、`BR3.3` |
| `authorization` | **0** | 本單元無授權判定（`K-04` 逐字「授權責任：無」） |
| `calculation` | **0** | 本單元無運算 |
| **合計** | **12** | 與上表相符 |

---

## 三、哪些規則由資料庫層強制，哪些不是（誠實分界）

| 規則 | 強制層 | 本單元能否保證 |
|---|---|---|
| `BR1.1`／`BR1.2` | **資料庫層** | **能**——不依賴任何程式流程記得檢查 |
| `BR1.3` 的**兩個原子約束** | **資料庫層** | **能**——「每位使用者至多一個預設 Project」與「每個 Project 至多一個預設 System」各自只引用自己表內的欄位，兩者都不依賴程式流程 |
| `BR1.3` 遞移得出的**複合**性質（「每位使用者至多**一組**預設專案／系統」） | 資料庫層的兩個約束 ＋ **`BR2.5` 的獨佔寫入紀律** | **不能單靠約束**——遞移還需要第三個前提：`is_default` 為真的 System **總是**建在該使用者 `is_default` 為真的 Project 底下。沒有任何約束擋住「預設 System 掛在非預設 Project 底下」（`BR1.3` 的第二子句只禁止**同一個** `project_id` 內有兩個預設 System，不管它指向哪個 `project_id`）。那個耦合完全由 `BR2.5` 的流程供應（「取得或建立其預設 Project 與預設 System」——它總是先解析出預設 Project 再以該 id 為範圍找 System）。今天無害的唯一理由是**遷移是 `is_default` 的唯一寫入端**，而它自己的邏輯不破壞這個耦合；一旦出現第二個寫入端，這個複合性質就不再自動成立（iteration 2 審查 R-07，Major：本表初版把 `BR1.3` 整條歸在「能——不依賴任何程式流程記得檢查」，那對這個複合性質是過度宣稱，而且它把 `BR1.3` 當初要消除的那一類風險原封不動搬到了組合這一層） |
| `BR2.1` | 遷移程序的終檢 | **能**，但**只在遷移執行的那一刻**——`AC9.1.4` 的 Given 逐字是「遷移已執行」，問的正是那一刻的列數。遷移之後，`BR1.2` 只擋住「刪除 System」這一條路；它不禁止把一張已掛好的圖的 `system_id` 改回空，也不要求新插入的圖必須帶 `system_id`（本欄在本設計裡永遠可為空）。那兩條路的處置是 `OQ-H2`，**本站不定案**（見 `functional-spec.md §八`）——因為把欄位收成 `NOT NULL` 與 `AC9.1.3`（既有頁面行為不變）直接衝突（iteration 2 審查 R-08，Major） |
| `BR2.2`／`BR2.5` | 遷移程序的流程 ＋ `BR1.3` 的約束 | **部分**——「取得或建立」的流程由程式寫；「不會建出第二個預設 **Project**」由約束保證，而「不會建出第二**組**（Project ＋ System 的配對）」另需 `BR2.5` 的獨佔寫入紀律，**不是單靠約束**（與上方 `BR1.3` 複合性質那一列同一件事；本列初版逐字寫「『不會建出第二組』由約束保證」，與上方直接對撞——審查 R-07） |
| `BR2.3`／`BR2.4`／`BR2.6` | 遷移程序的形式 | **能**（由程式碼結構保證，可被審查與測試驗證） |
| `BR3.1`／`BR3.2`／`BR3.3` | **不在本單元** | **不能**——它們是別的單元的行為，逐條已標落點 |

**三條 `BR3.*` 是本單元無法強制的**，這一點不加掩飾：它們寫在這裡是為了讓
`U7`／`U16`／未來的讀取端有一份可引用的來源，不是為了宣稱本單元已經處理了它們。

**本表在 iteration 2 審查後拆過兩列**（R-07 與 R-08），拆的理由同一個：
初版有兩處把「資料庫層擋得住」寫得比機制實際做到的強一小步——`BR1.3` 那一列
對**複合**性質過度宣稱，`BR2.1` 那一列把「執行期持續成立」寫成無條件。
兩處都不影響今天的正確性（遷移是唯一寫入端），但這是三個後續單元要建在上面的
資料模型，所以差那一小步也要寫出來，而不是留給下一個人自己發現。
