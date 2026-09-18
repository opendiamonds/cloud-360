# Business Logic Model — U1 `backend-activity-policy`

> Stage: functional-design（Construction 3.1）· Unit: `backend-activity-policy`（kind: service）
> 上游來源：`../../../inception/units-generation/unit-of-work.md`、`unit-of-work-story-map.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/application-design/components.md`（下稱 components）、`component-methods.md`、`services.md`。
> 規則定義見 `business-rules.md`，實體定義見 `domain-entities.md`。

## 本單元交付的一件事

讓「任何以有效憑證發出的請求都更新該帳號的最後活動時間，且同一帳號每 5 分鐘至多寫一次」成立。

## 觸發點

既有的認證依賴 —— **所有帶憑證的 HTTP 請求的必經點**（跨五支 router 窮舉確認，不存在「已認證但不經此點」的 HTTP 路徑）。

**位置精度**：觸發點在該依賴的**尾端**，即**停用檢查之後**（`component-methods.md` C-2 逐字要求）。差一行就改變輸出，理由見 `business-rules.md` 的 **R0**。

### 範圍限制：純 WebSocket 共編活動不計入（非驗證缺口）

共編的 WebSocket 端點**不經認證依賴、不解析憑證**，因此純共編活動不會更新最後活動時間。

- **性質**：AC-1.1 的**已知範圍限制**，不是本站的驗證缺口，也不是可補的疏漏 —— 該端點目前完全沒有認證，要納入就得先為它加上認證，那是另一件事。
- **來源**：stories 的 reviewer Finding D，上游未關閉，經 `unit-of-work-story-map.md` 明確指派給**本單元**承接。
- **實務後果**：一位使用者若整天只在共編畫布上操作、從不觸發任何 HTTP 請求，其最後活動時間不會更新。實務上前端載入頁面即發 HTTP 請求，此情境極罕見，但**不是不可能**，故如實記載而非略過。

該處在觸發時**已經取得**完整的使用者物件與可用的資料庫工作階段，因此判定所需的值**已在手，不需要任何額外查詢**。這是本設計相對於「先讀再判斷」方案的關鍵成本差異。

## 主流程

```
認證依賴驗證憑證、查出使用者物件**並通過停用檢查**之後
        │
        ├─ 取得當下時刻（帶時區 UTC）
        │
        ├─ 以使用者物件既有的欄位值呼叫 R1（節流判定）
        │      ↑ 零查詢 —— 值已隨認證流程在手
        │
        ├─ R1 = 不允許 ──→ 直接返回，不觸碰資料庫  ← 絕大多數請求走這條
        │
        └─ R1 = 允許
               │
               ├─ 更新欄位為當下時刻
               ├─ 提交
               │
               ├─ 成功 ──→ 返回「已寫入」
               │
               └─ 例外 ──→ 先復原工作階段
                            └─ 記錄警告（含使用者識別、例外型別與訊息）
                                 └─ 返回「未寫入」
        │
原始請求接續既有的權限檢查與端點邏輯
```

**文字說明**：認證依賴確立使用者後，取得帶時區的當下時刻，以使用者物件既有的欄位值呼叫節流判定。判定為否時直接返回、完全不觸碰資料庫（絕大多數請求走這條）。判定為是時更新欄位並提交；成功則返回已寫入，發生例外則**先復原工作階段**、記錄警告、返回未寫入。無論哪條路徑，原始請求都照常繼續。

## 交易語意 —— 本單元最關鍵的契約

既有的工作階段供應器**既不提交、也不在例外路徑復原**，只在結束時關閉；工作階段設定為不自動提交。因此兩件事都必須由本單元負責：

### 必須自行提交

絕大多數認證端點是**唯讀**的（使用者清單、個人資訊，以及協作、審查、透鏡各模組的全部讀取端點），它們本身從不提交。

**若不提交，待決的更新會在工作階段關閉時被整個丟棄** —— requirements FR-1.1 對這些端點永遠不成立，而回傳值還會宣稱寫入成功。

**在依賴階段提交是安全的**：本單元執行於認證依賴內，此時端點自身的業務邏輯尚未開始，工作階段中不存在端點的待決變更。窮舉全 repo 的依賴可呼叫者確認**無一對工作階段寫入**，故這次提交只會提交本單元自己的更新。

### 失敗時必須先復原再記錄

若只吞下例外而不復原，工作階段會進入待復原狀態。**緊接著執行的權限檢查會查詢權限表，該查詢會直接拋出例外** —— 使用者的原始請求照樣失敗，直接推翻本單元「不得讓原始請求失敗」的承諾。

復原之後工作階段恢復可用，後續的依賴與端點邏輯不受影響。

### 工作階段的所有權

**借用不獨佔** —— 本單元提交，但**不關閉**工作階段（生命週期仍屬供應器）。

## 失敗處置（Q2=A 定案）

| 面向 | 定義 |
|---|---|
| 傳播 | **不傳播** —— 活動時間的寫入是輔助性副作用，不是請求的目的。一次記錄失敗導致整個 API 呼叫掛掉是不成比例的後果 |
| 記錄層級 | **警告**（沿用既有補欄函式的形狀） |
| 記錄內容 | 使用者識別、例外型別、例外訊息 |
| **不記錄** | 完整堆疊 —— 輔助性副作用的堆疊會淹沒日誌，且呼叫路徑固定、堆疊的診斷價值有限 |

**為何內容是這三項**：使用者識別讓人能分辨「全面性失敗」與「特定帳號問題」；例外型別與訊息讓人能分辨「連線問題」與「約束衝突」。少了任一項，這條日誌就失去它唯一的診斷價值。

### 來源誠實聲明

「寫入失敗不得讓原始請求失敗」這條約束**在 requirements 與 stories 中都沒有對應條文**。它是 application-design 的設計判斷，唯一的上游依據是 construction 階段護欄的「silent failures are not acceptable」—— 而該護欄要求的是失敗必須被記錄，並未規定失敗的傳播方式。

本站沿用該判斷並具體化記錄內容，**不重新論證它**。

## 成本

| 分支 | 成本 |
|---|---|
| 判定為否（絕大多數） | 一次記憶體內的時間比較。對請求延遲**無可測量的影響** |
| 判定為是 | ①一次以主鍵定位的單列更新與提交（次毫秒級）；②**一次因工作階段過期而產生的使用者重讀** —— 既有的工作階段設定在提交後會使已載入物件過期，後續的權限檢查讀取該使用者時會觸發重新查詢 |

兩項合計仍是次毫秒級，且**每帳號每 5 分鐘至多發生一次**。requirements NFR-1 的效能約束有明顯餘裕。

若日後量測顯示第二項值得消除，可調整工作階段設定 —— 但那是最佳化，不是本設計的前提。

## 擴展特性

節流判定**不依賴任何程序內狀態** —— 判定基準是資料庫中的欄位值本身。因此加上多個 worker 程序或多個後端實例時，**行為不變、節流仍然正確**，不需要回頭改設計。

（目前為單一實例、單一 worker，但本設計刻意不依賴這個事實。）

## 本單元的驗證缺口（如實記載）

`services.md` 的測試義務對照表共**六列**：五項落在 C-7（授權雙向）／C-4（端點測試）／C-6（前端 e2e）／C-8（規格檔漂移、型別檔漂移），第六項（NFR-7 既有功能不退化）由該檔自陳**不承載具體驗證設計**。**無一落在本單元**。具體兩處：

| 缺口 | 為何自動化測試抓不到 |
|---|---|
| C-2 的交易契約（提交／復原） | 純函式測試不碰資料庫；U2 的端點測試只斷言回應欄位集合 |
| C-3 的既有環境補欄（含其**自行提交的交易邊界** —— 既有三處補欄先例皆以自行提交的連線區塊包覆，非沿用外部 session；此細節須明寫，`unit-of-work.md` 已記載同型遺漏在 C-7 造成的後果） | 測試**直接由模型建表**（不經啟動流程的補欄路徑），故補欄補丁**從未被任何測試執行過** |

**承接方式**：部署後重啟 + 人工核對。上游已實測記載此失敗模式 —— 只改模型而不補啟動補丁，staging 上每個已認證請求都會失敗，**而 CI 全綠**。

規則層（R1／R2）則有完整的純函式與 property-based 涵蓋。**本單元的驗證強度是不齊的**，這來自 repo 既有的測試涵蓋現況，非本站可解決。

## 與其他單元的介面

| 對象 | 形式 | 方向 |
|---|---|---|
| U2（序列化） | 呼叫 R2 判定逾期；讀取本單元建立的欄位 | U2 依賴本單元 |
| U2（序列化） | **呼叫本單元的時區正規化函式** —— 這是 `component-methods.md` C-4「序列化前亦須套用同一正規化」的承載處。本單元的正規化 helper 因此為**公開介面**而非私有（理由見 `business-rules.md`），避免 U2 自寫第二份可漂移的副本 | 單一真實來源（`team.md ## Code Style`） |
| 既有認證依賴 | 在其尾端觸發本單元 | 觸發點 |
| 既有權限檢查 | 無直接關係，但**本單元的失敗復原是它能正常運作的前提** | 隱含 |

---

## Review — Iteration 2

**Reviewer**: aidlc-architecture-reviewer-agent · Unit: backend-activity-policy · Iteration 2
**Date**: 2026-08-09T14:50:12Z
**Verdict**: READY

本輪不採信「已修正」的宣稱，逐項回 repo 實測八項修正是否真正關閉 iteration 1 的三項 Major、五項 Minor，並主動尋找修正過程本身新引入的缺陷。

### 八項修正驗收

| # | 原嚴重度 | 判定 | 說明 |
|---|---|---|---|
| 1 | Major（時區正規化私有／公開） | **達成** | 實測結論：`business-rules.md` L87、L103-109 已把正規化 helper 改為「本單元對外的公開介面」，理由段落逐字對上 `component-methods.md` C-4 第 193 行「序列化前亦須套用同一正規化」（已逐字核對相符）；`business-logic-model.md` L129 的介面表已新增對應列，指向 U2。iteration 1 明確要求「L71-73 的理由段須改寫，不得繼續宣稱『呼叫端不需要知道時區問題的存在』」——`grep` 全檔確認該句已不存在，僅剩範圍已收斂、僅指涉 R1／R2 自身呼叫端的「呼叫端不需要在每次呼叫前自己處理時區」（L101），不再對 U2 過度宣稱。**但此修正本身引入一個新問題，見新發現 F1** |
| 2 | Major（R0 遺失，帳號停用斷言無依據） | **達成** | `business-rules.md` 新增 R0（L10-32），三態表逐項回 repo 驗證：已停用＝`backend/services/auth.py:60-64` 的 `get_current_user` 在 `is_active=False` 時於 `return user` 之前直接 403，**確認觸發點之後**；待授權＝`backend/services/rbac.py` 的 `require_story_action._dep`／`require_arch_action._dep` 才檢查 `authorization_status`，時機確實在認證依賴之外、更後面；「待授權帳號會出現在清單裡」的主張經讀 `backend/services/user_router.py:442-458 list_users`（`db.query(User).order_by(User.id).all()`，無任何 `is_active`／`authorization_status` 過濾）證實無誤。`business-logic-model.md` L30 主流程首格已改為「並通過停用檢查之後」；`domain-entities.md` L49「帳號停用｜不變」已改為指向 R0 並附理由，不再是無依據斷言。R0 對「待授權帳號可能同時逾期」的可接受性主張（引用 refined-mockups 已畫出最壞情境）經讀 `aidlc/.../refined-mockups/mockups.md` 第 34-52 行確認：dave 列即為此最壞情境，且已附三項可核實依據（含直接引用 `login()`／`register()` 原始碼）。**完全達成，無殘留** |
| 3 | Major（WebSocket 範圍限制遺失） | **達成** | `business-logic-model.md` L13 已加限定語「所有**帶憑證的 HTTP 請求**的必經點」，並新增「範圍限制：純 WebSocket 共編活動不計入」小節（L17-25）。實測 `backend/services/collab_router.py:221-232` 的 `@router.websocket("/ws/{workspace_id}")` 確認零依賴、不解析憑證；同檔的 `/collab/users`、`/collab/diagrams`、`/collab/workspace/bootstrap` 等 REST 端點皆掛 `require_arch_action`（內含 `get_current_user`），與「純 WS 訊息才不計入、頁面載入的 HTTP 請求仍計入」的敘述一致。「實務上前端載入頁面即發 HTTP 請求」一句經讀 `frontend/src/pages/WorkspacePage.tsx` 確認：頁面掛載即呼叫 `fetchDiagrams()` 與 `${API_COLLAB}/workspace/bootstrap`，並非未經查證的樂觀推測。來源歸屬「stories 的 reviewer Finding D…經 unit-of-work-story-map.md 明確指派給 U1」與 `unit-of-work-story-map.md` 第 140 行逐字相符。**完全達成，無殘留** |
| 4 | Minor（「四項」應為「六列」） | **達成** | `business-logic-model.md` L113 已改為「六列…五項落在 C-7／C-4／C-6／C-8，第六項（NFR-7…）由該檔自陳不承載…無一落在本單元」，逐格核對 `services.md` L149-156 的測試義務對照表（授權雙向→C-7、端點測試→C-4、e2e→C-6、規格檔漂移→C-8、型別檔漂移→C-8、NFR-7→不承載）完全相符 |
| 5 | Minor（「強制模式直接建表」措辭錯誤） | **達成** | `business-logic-model.md` L118 已改為「測試**直接由模型建表**（不經啟動流程的補欄路徑）」，與 `domain-entities.md` L73「直接由模型建表」的措辭一致，兩檔不再矛盾。實測 `backend/tests/helpers.py:29` 確認建表語句為 `Base.metadata.create_all(bind=engine)`，與「強制模式」（`force=True`，屬權限矩陣種子的引數）無關，修正後的措辭準確 |
| 6 | Minor（AD-4 引用錯誤） | **達成** | `business-rules.md` L36 已改為「`decisions.md` **AD-4**，經 `components.md` C-1 承載」。核對 `decisions.md` AD-4 標題「兩個時間門檻規則集中為單一純函式元件」與 `components.md` L17「這是本站的設計推論…依據見 `decisions.md` AD-4」，引用方向正確 |
| 7 | Minor（補欄先例的自行提交交易邊界遺漏） | **部分達成（內容存在，但原標的列未修）** | 相關內容確實已補上，但**落在與原建議不同的位置**：`business-logic-model.md` L118 的「本單元的驗證缺口」表新增了「含其自行提交的交易邊界——既有三處補欄先例皆以自行提交的連線區塊包覆」（經 `grep backend/database.py` 核實 `_ensure_a4/j5/a3_schema` 三者皆為 `with engine.begin() as conn:`，逐字相符），但 iteration 1 建議修正的標的——`domain-entities.md` L62「失敗處置」列——**原文一字未動**，仍只寫「沿用既有補欄函式的形狀（逐句 try、記錄警告後續行）」，未提及自行提交的交易邊界。`domain-entities.md`「既有環境的欄位建立」表本身是本單元描述「補欄怎麼做」的主要落點，而該表仍不完整；讀者若只讀該表、不連讀 `business-logic-model.md` 的驗證缺口段，仍會漏掉這個細節。見新發現 F2 |
| 8 | Minor（C-5 偏離未標註） | **達成** | `domain-entities.md` L18「資料庫層預設值」列已加註「此處刻意偏離 requirements C-5…此偏離為刻意且已標明，非疏漏」，逐字滿足 iteration 1 的建議修正 |

### 主動尋找修正過程新引入的缺陷

| 編號 | 檢查對象 | 結果 |
|---|---|---|
| — | R0 新增是否與既有 R1／R2 編號、交叉引用衝突 | 無衝突。「本單元擁有三條規則」（L6-8）正確納入 R0；「兩條時間門檻規則」（L34）標題刻意只指 R1／R2（R0 非時間門檻判斷，是活動定義），層次正確、非矛盾 |
| — | 介面表新增列是否讓「本單元的公開介面」清單在三檔間不一致 | 未發現不一致。`business-rules.md` L109 自陳「這項交接已列入 `business-logic-model.md` 的介面表」，實測介面表（L129）確有對應列；`domain-entities.md` 不涉及介面、未提及屬合理（不在其職責範圍） |
| F1 | Q3=A 的字面選項與最終設計是否一致 | **不一致，見下方 Finding 1** |
| F2 | Finding 7 的修正落點是否覆蓋原標的 | **未覆蓋，見下方 Finding 2** |
| — | 三份 artifact 是否仍無實際程式碼、未越界做 3.5 的事 | 確認無越界。三檔僅 `business-logic-model.md` 一處 fenced block，內容為 ASCII 流程圖（非程式碼）；全檔 `grep` 無 `def `／`class `／TS 語法殘留 |

### Findings

| # | 嚴重度 | 位置 | 問題 | 建議修正 |
|---|---|---|---|---|
| 1 | Minor | `functional-design-questions.md` Q3（L49-62）vs `business-rules.md` L78-109、`domain-entities.md` L5 | **時區正規化 helper 由「私有」改為「公開」，是對已作答的 Q3 的實質推翻，但問題檔與前言引用皆未同步標註。** Q3 的選項 A 文字逐字為「C-1 內部的共用**私有** helper，兩個判定各自呼叫」，`[Answer]: A` 已鎖定此形狀；`business-rules.md` 現以「為何是公開而非私有」整節（L103-109）推翻這個字面選擇，理由紮實（承接 iteration 1 Finding 1），但 `functional-design-questions.md` 本身未加任何修訂註記，`domain-entities.md` L5 的前言仍寫「Q3=A（時區正規化置於規則層內部）」——這個措辭技術上不算錯（正規化的**位置**確實仍在 C-1 內部，Q3=A 的這部分未變），但刻意迴避了「私有」這個被推翻的字眼，讓只看問題檔或前言的讀者無法察覺這項反轉。本專案在 `application-design` 的先例（AD-1〜AD-3 對應人工作答的 Q1〜Q3，三輪 iteration 均未被推翻；唯有標註「本站設計判斷（未經問答）」的 AD-4〜AD-9 才在 iteration 間被 reviewer 觸發修訂）顯示：本專案的既定作法是人工作答的題目一經鎖定即不再由 reviewer 迭代推翻，若要推翻則走 Revision 流程（如 `decisions.md` AD-9 的「由 units-generation Q2=B 觸發回跳」模式）。此處未經該流程、亦未在問題檔留下痕跡。實際風險有限——下游（U2 的 functional design、code-generation）預期消費的是 `business-rules.md`／`business-logic-model.md` 本身而非問題檔的字面選項，因此不構成執行期或責任交接的破口，純屬審計軌跡的精確度問題 | 於 `functional-design-questions.md` Q3 下方補一則簡短修訂註（例如「iteration 2 依 reviewer Finding 1 由私有改為公開，理由見 `business-rules.md`」），並將 `domain-entities.md` L5 的「Q3=A（時區正規化置於規則層內部）」改為明確承認此反轉（例如「Q3=A 定其位置為 C-1 內部；公開性其後依 reviewer Finding 1 由私有改為公開，見 `business-rules.md`」） |
| 2 | Minor | `domain-entities.md` L62 | **iteration 1 Finding 7 的建議修正標的（此列）本身仍未修改；修正內容改落在 `business-logic-model.md` 的驗證缺口表。** 「失敗處置」列仍只寫「沿用既有補欄函式的形狀（逐句 try、記錄警告後續行）」，未提及三個既有先例皆以 `with engine.begin() as conn:` 的自行提交交易邊界包覆（已於 `backend/database.py:142/189/259` 逐一核實）。該細節確實已寫入 `business-logic-model.md` L118 的「本單元的驗證缺口」表，內容正確、引用 `unit-of-work.md` 對 C-7 同型遺漏的記載也準確，但 `domain-entities.md`「既有環境的欄位建立」表才是本單元描述「補欄怎麼做」的主要落點——只讀該表（不連讀驗證缺口段）的讀者仍會漏接這個影響 PostgreSQL 生效與否的細節。風險程度與 iteration 1 原評的 Minor 相同，未升級，因為內容確實存在於同一份 artifact 集合內、且引用正確，只是分散在兩處 | 於 `domain-entities.md` L62「失敗處置」列補上第三項（或加註「詳見 `business-logic-model.md` §本單元的驗證缺口」的互指），使該表本身完整，不需連讀他檔才能補全實作所需的關鍵細節 |

### Summary

三項 Major 全部**完全且正確地關閉**，且逐項回 repo 實測驗證（`auth.py` 的 403 位置、`rbac.py` 的授權檢查時機、`user_router.py` 的 `list_users` 無過濾、`collab_router.py` 的 WebSocket 零依賴、`WorkspacePage.tsx` 的頁面載入 HTTP 請求、`refined-mockups/mockups.md` 的 dave 列最壞情境、`database.py` 三個既有補欄先例的 `engine.begin()` 交易邊界）——沒有一項是「加字但未關閉」。五項 Minor 中四項完全達成，第五項（Finding 7）內容存在但落錯位置，原標的列仍不完整，降格重列為本輪 Finding 2（同為 Minor，不升級，因內容確實存在於本 artifact 集合內）。

本輪主動排查修正過程本身，找到一項新問題（Finding 1）：Finding 1 的修正（私有→公開）在技術實質上正確且論證紮實，但推翻了已用 A/B/C 選項鎖定的人工作答 Q3，而問題檔與前言引用都未同步標註這項反轉，形成一個與本專案在 `application-design` 階段展現的既定作法（人工作答的題目不由 reviewer 迭代直接推翻，要推翻須走 Revision 流程）不一致的先例。因下游實際消費的是 `business-rules.md`／`business-logic-model.md` 本身而非問題檔字面，此為審計軌跡精確度問題，不構成執行期風險，故列 Minor 而非 Major。

兩項 Minor（Q3 反轉未標註、Finding 7 標的列未修）皆為低成本可補的措辭與互指問題，不影響任何規則、交易契約或實體定義的正確性。`required-sections` sensor 三檔仍全 `pass:true`（H2 數 11／9／7），全檔仍無實際程式碼、未越界進入 code-generation 的職責範圍，`python3 scripts/validate_repo_contract.py` 通過。**判定 READY**（0 Critical、0 Major、2 Minor）。

---

## Review

**Reviewer**: aidlc-architecture-reviewer-agent · Unit: backend-activity-policy · Iteration 1
**Date**: 2026-08-09T14:32:36Z
**Verdict**: NOT-READY

### 事實查證

本輪不採信本站的宣稱，逐項回 repo 實測（`backend/` 為應用程式碼，非其他單元的 construction 產出）。

| 主張 | 查證結果 | 判定 |
|---|---|---|
| 「窮舉全 repo 的依賴可呼叫者確認無一對工作階段寫入」（本檔 L55） | `grep -rho "Depends([a-zA-Z_0-9]*" backend/` 得**全 repo 僅 5 個**依賴可呼叫者：`get_db`(40)、`require_story_action`(24)、`require_arch_action`(14)、`get_current_user`(6)、`security_bearer`(1)。逐一讀原始碼：`get_db`（`database.py:31-36`）只 `yield`／`close`；`security_bearer` 為 `HTTPBearer` 不碰 DB；`get_current_user`（`auth.py:39-65`）只有一次 `db.query(User)...first()`；`require_arch_action._dep`（`rbac.py:161-181`）與 `require_story_action._dep`（`rbac.py:228-248`）只走 `user_can → get_permission_row → db.query(RolePermission)`。**五者皆為唯讀，無一 `add`／`commit`／`flush`**。另查 `main.py` 無 router 級 `dependencies=`、無自訂 middleware（只有 CORS），故依賴集合確實封閉 | **成立** |
| 「既有工作階段供應器既不提交、也不在例外路徑復原，只在結束時關閉；設定為不自動提交」 | `database.py:24` `sessionmaker(autocommit=False, autoflush=False, bind=engine)`；`database.py:31-36` `try: yield db finally: db.close()` —— 逐字相符 | **成立** |
| 「不復原則緊接著的權限檢查查詢會拋例外」 | `require_story_action._dep`／`require_arch_action._dep` 於 `get_current_user` 之後執行且皆查 `RolePermission`，待復原狀態下必然拋錯。**惟三個端點（`user_router.py:381 get_me`、`:410 patch_my_authorization_request`、`:431 list_canonical_roles`）只掛 `get_current_user` 而無後續權限檢查**，該情形下改由端點自身的查詢拋錯 —— 結論（必須復原）不變，但「權限檢查」不是唯一受害者 | 成立（措辭略窄） |
| 「所有認證請求的必經點，不存在『已認證但不經此點』的路徑」 | 逐支列舉五支 router 的路由裝飾器與其依賴：僅 `user_router.py:283 /roles/catalog`、`:290 /register`、`:352 /login`、`collab_router.py:221 websocket`、`main.py:53 /` 五處無認證依賴，**全部為公開端點（不帶憑證）**；其餘每一個端點皆經 `get_current_user`（直接或經 `require_*_action`） | **字面成立**（但見 Finding 3） |
| 「補欄函式獨立 vs 擴充：既有三個補欄函式各對應一個功能批次，其中兩個往使用者表加欄位」 | `database.py:123 _ensure_a4_schema`（A4：`ALTER TABLE users ADD COLUMN last_opened_diagram_id` ＋ 建 `user_diagram_chats`）、`:151 _ensure_j5_schema`（J5：`ALTER TABLE users ADD COLUMN authorization_status` 等 ＋ 建 `role_authorization_requests`）、`:198 _ensure_a3_schema`（A3：建 `architecture_reviews`／`wa_lenses`）。**三個各對應一個功能批次為真；其中兩個確實往 `users` 加欄位** | **成立** |
| 「失敗處置沿用既有補欄函式的 `logger.warning` 形狀」（Q2=A） | `database.py:144-147`／`192-194`／`262-264` 三處皆為 `try: conn.execute(...) except Exception as e: logger.warning("<批次> schema 補丁略過/失敗: %s — %s", sql[:60], e)` —— 警告層級、單行、不含堆疊，**形狀相符**。惟既有形狀只帶「例外物件」（等同訊息），**不含例外型別**，本站列的三項內容是加強而非沿用 | 成立（沿用為層級與樣式，非內容） |
| 「repo 同時存在兩種互不相容的時間慣例」 | `auth.py:32,34` 為 `datetime.utcnow()`（naive）；`user_router.py:424,511,549` 為 `datetime.now(timezone.utc)`（aware）。實測 naive − aware 相減拋 `TypeError: can't subtract offset-naive and offset-aware datetimes` | **成立** |
| 「SQLite 不保存時區，帶時區欄位讀回為不帶時區」 | 以 SQLAlchemy 2.0.51 實測：`DateTime(timezone=True)` 欄位寫入 `datetime.now(timezone.utc)`、`expunge_all()` 後重讀，取得 `tzinfo=None` 的 naive 值 | **成立** |
| 「測試從不呼叫啟動流程」 | `backend/tests/helpers.py:29` `Base.metadata.create_all(bind=engine)` 直接由模型建表，全檔無 `init_db()`／`_ensure_*_schema()` 呼叫 | **成立**（惟本檔 L108 的措辭有誤，見 Finding 5） |
| 「提交後工作階段過期導致使用者重讀」（成本第二項） | `database.py:24` 未設 `expire_on_commit`，SQLAlchemy 預設為 `True`。實測 `commit()` 後 `inspect(obj).unloaded` 由 `set()` 變為全部欄位 → 後續 `require_*_action._dep` 讀 `current_user.role`／`authorization_status` 必觸發一次重新查詢 | **成立** |
| `required-sections` sensor（三檔） | 全 `pass:true`，H2 數 9／7／7，`findings_count:0` | 通過 |
| `upstream-coverage` sensor（三檔） | 全回 `{"pass":true,"consumes":[],"reason":"no upstream"}` —— 未解析到 consumes 清單的**空跑**，不構成證據。改以人工核對：三檔檔頭皆完整列出六份 consumes（`unit-of-work`、`unit-of-work-story-map`、`requirements`、`components`、`component-methods`、`services`） | 無效力；人工核對通過 |
| `linter`／`type-check` sensor | 三檔無任何 TS／JS／TSX 程式碼區塊（唯一 fenced block 為 ASCII 流程圖），且**全檔無實際程式碼** —— 未越界做 3.5 的事 | N/A（正確） |
| 上游契約一致性（門檻與邊界） | R1「含等於」逐字對上 requirements FR-1.3（第 34 行「距上次寫入滿 5 分鐘（含）之後的下一個請求觸發第 2 次寫入」）；R2「不含等於」逐字對上 requirements FR-3.1（第 55 行「早於當下起算 90 天」）與 component-methods C-1 docstring；FR-3.3「不提供設定介面」對上 requirements 第 57 行 | 通過 |
| 上游契約一致性（交易語意） | 本檔「必須自行提交／失敗先復原／不關閉」逐項對上 `component-methods.md` C-2 的三條契約與 `components.md` C-2 | 通過 |

### Findings

| # | 嚴重度 | 檔案 | 問題 | 建議修正 |
|---|---|---|---|---|
| 1 | **Major** | `business-rules.md` L59、L71-73；`business-logic-model.md` L118 | **時區正規化定為「私有」，與 `component-methods.md` C-4 要求的「序列化前亦須套用同一正規化」在結構上互斥，且介面表未揭露。** `business-rules.md` L59 定「正規化的實作位置＝**規則層內部的共用私有 helper**」，L71-73 的理由是「呼叫端不需要知道時區問題的存在……C-4（序列化，屬 U2）要用同一個判定，若由呼叫端負責就是兩個可能漏掉的地方」。但 `component-methods.md` C-4 第 193 行（iteration 2 Finding N7）逐字要求：「`last_activity_at` 從資料庫直通序列化時，在 SQLite 測試路徑下讀回為不帶時區的值……**因此序列化前亦須套用同一正規化**」。C-1 的兩個判定**回傳 bool，不回傳正規化後的值**，且 helper 為私有 → U2 結構上取不到「同一正規化」，只能自寫第二份。這使 L71-73 的理由只對「逾期判定」成立、對「值的序列化」不成立，而本檔 L118 的介面表只寫「呼叫 R2 判定逾期；讀取本單元建立的欄位」，完全沒有把這項義務交出去。後果具體：U2 會產生一份可獨立漂移的正規化副本，且違反 `team.md ## Code Style` 的「單一真實來源」（「新增副本的同一個 PR 必須一併新增鎖住兩者一致的測試；無法寫測試的副本不新增」） | 二擇一並明寫：①把正規化 helper 由**私有改為本單元對外的公開介面**（C-1 多一個公開的正規化函式），並在 L118 的介面表新增一列「U2：呼叫本單元的時區正規化函式（`component-methods.md` C-4 序列化前正規化的承載）」；或②維持私有，但在 `business-rules.md` 明記「C-4 的序列化前正規化**不由本單元承載**，U2 需自行實作」，並依 `team.md` 單一真實來源規則載明副本的一致性測試義務。無論哪一種，L71-73 的理由段須改寫，不得繼續宣稱「呼叫端不需要知道時區問題的存在」 |
| 2 | **Major** | `business-rules.md`（全檔）、`domain-entities.md` L49、`business-logic-model.md` L20 主流程 | **「哪些認證請求算活動」這條規則沒有被寫下來，而 `domain-entities.md` 的生命週期表已先行斷言了結論。** 實測 `auth.py:60-64`：`get_current_user` 在查出 user 之後、`return user` 之前，對 `is_active=False` 直接拋 403；`rbac.py:232-237`：`authorization_status != "approved"` 的 403 則在**更後面**的權限檢查中。本檔主流程只寫「認證依賴驗證憑證、查出使用者物件**並通過停用檢查**之後 → 取得當下時刻 → 呼叫 R1」，**丟失了 `component-methods.md` C-2「既有認證依賴的**尾端**」的位置精度**，而位置差一行即改變可稽核的輸出：(a) 置於停用檢查**之前** → 已停用帳號只要客戶端仍持舊 token 輪詢，`last_activity_at` 就持續更新、永遠不會被 R2 標為逾期；(b) 置於**之後** → 停用當下凍結，才與 `domain-entities.md` L49「帳號停用｜不變」相符 —— 但該斷言在三份 artifact 中**沒有任何依據**，它只在 (b) 成立。(c) `authorization_status='pending'` 帳號在任何擺法下都會被記為活動，而三份 artifact 完全未提。此非空談：`user_router.py:437-460 list_users` 回傳**全部**使用者（含 `is_active=False` 與 `pending`），兩類帳號都會出現在新欄位裡 | 於 `business-rules.md` 新增第三條規則（例如 R0「活動的定義」），明訂：①觸發點為認證依賴中**停用檢查之後**（逐字保留 `component-methods.md` C-2 的「尾端」）；②`is_active=False` 的請求**不記為活動**並說明其稽核理由；③`authorization_status` 非 approved 的請求**是否**記為活動，給出判定與理由。同時把 `business-logic-model.md` 主流程首格改為「認證依賴驗證憑證、查出使用者物件**並通過停用檢查**之後」，並讓 `domain-entities.md` L49 指向該規則 |
| 3 | **Major** | `business-logic-model.md` L13、L101-112 | **上游明確指派給本單元的已知缺口在本站消失。** `unit-of-work-story-map.md` 第 140 行「帶進 Construction 的已知缺口」表逐字列有：「**共編 WebSocket 端點不經認證中介層｜U1｜**stories 的 reviewer Finding D，上游未關閉。純共編活動不會更新最後活動時間，**屬 AC-1.1 的範圍限制**」，該表表頭自陳其存在目的正是「在此明列以免它們在單元切分後失蹤」。實測 `collab_router.py:221-232` `@router.websocket("/ws/{workspace_id}")` 確實**零依賴、零 token 解析**。本站的「本單元的驗證缺口」段落忠實承接了另外兩項 U1 缺口（C-2 交易契約、C-3 補欄），`business-rules.md` 亦承接了殘留項 m3，**唯獨這一項整段遺失**；且 L13 以無限定語寫「所有認證請求的必經點（跨五支 router 窮舉確認，不存在『已認證但不經此點』的路徑）」，字面雖真（WS 端點不帶憑證，非「已認證」），卻讓讀者無從得知 FR-1.1／AC-1.1 存在這個涵蓋洞 | 於 L13 的觸發點段落或「本單元的驗證缺口」段落補一列**範圍限制**（非驗證缺口）：純 WebSocket 共編活動不經認證依賴，故不更新最後活動時間，屬 AC-1.1 的已知範圍限制，來源為 stories reviewer Finding D 經 `unit-of-work-story-map.md` 指派給 U1；並把 L13 的斷言加上限定語（「所有**帶憑證的 HTTP 請求**的必經點」） |
| 4 | Minor | `business-logic-model.md` L103 | 「`services.md` 的測試義務對照**四項**全部落在其他單元」與來源不符：`services.md` 第 149-156 行的「測試義務對照」表實為**六列**（授權雙向→C-7、端點測試→C-4、前端 e2e→C-6、規格檔漂移→C-8、型別檔漂移→C-8、NFR-7 既有功能不退化→「**本站不承載具體驗證設計**」）。其中第六列並非「落在其他單元」而是無承載。結論（無一落在本單元）仍成立，但依據不可核對 | 改為「六項義務中五項落在 C-7／C-4／C-6／C-8，第六項（NFR-7）由 `services.md` 自陳不承載，**無一落在本單元**」 |
| 5 | Minor | `business-logic-model.md` L108 | 「C-3 的既有環境補欄｜測試以**強制模式直接建表**、從不呼叫啟動流程」—— 實測 `backend/tests/helpers.py`：建表是第 29 行的 `Base.metadata.create_all(bind=engine)`，**與強制模式無關**；`force=True` 出現在第 32 行的 `ensure_role_permissions_seeded(db, force=True)`，那是**權限矩陣種子**（屬 U4 的脈絡）。同一份 artifact 集合中 `domain-entities.md` L73 的表述（「直接由模型建表」）才是正確的，兩檔互相矛盾 | 改為「測試直接由模型建表（`Base.metadata.create_all`）、從不呼叫啟動流程」，與 `domain-entities.md` L73 對齊 |
| 6 | Minor | `business-rules.md` L8 | 「同置於一個零 I/O 的純函式模組（**components AD-4**）」引用錯檔：AD-4 是 `decisions.md` 的條目，`components.md` 第 17 行自身即寫明「依據見 `decisions.md` AD-4」。本站把它記成 components 的條目 | 改為「（`decisions.md` AD-4，經 `components.md` C-1 承載）」 |
| 7 | Minor | `domain-entities.md` L62 | 「失敗處置｜沿用既有補欄函式的形狀（**逐句 try、記錄警告後續行**）」只列了既有形狀的兩個面向，漏了三個先例共有的第三個面向：**`with engine.begin() as conn:` 的自行提交交易邊界**（`database.py:142`／`189`／`259`）。這不是可有可無的細節 —— `unit-of-work.md` 第 131 行對 U4／C-7 記載的正是同型遺漏的後果（「若改用啟動流程的既有 session 而未自行提交，寫入會被靜默丟棄」），而本 intent 的補欄同樣是 DDL，在 PostgreSQL 中需要提交才生效 | 在該列補上第三項：語句於 `with engine.begin()` 的自行提交交易中執行（與既有三個先例同形），不得沿用啟動流程中不提交的 session |
| 8 | Minor | `domain-entities.md` L16、L19 | 型別列以「requirements C-5（既有時間戳慣例）」為來源，但 requirements C-5 原文為「既有時間戳慣例為帶時區的**資料庫層預設值**」，而下兩列本站明定「資料庫層預設值｜**無**」。此偏離是正確且必要的（`components.md` C-3 已完整論證），但本檔未標明「本欄位**刻意偏離** C-5 的預設值部分」，純比對兩份文件會誤判為與已核可需求牴觸 | 於「資料庫層預設值」列的來源欄加註：刻意偏離 requirements C-5 的「資料庫層預設值」部分，理由見 `components.md` C-3；C-5 在此僅作為**帶時區型別**的來源 |

### Summary

事實面極為紮實：本輪逐項回 repo 實測的**六大主張全部成立**，且多項是靠自己跑出來的證據確認的 —— 依賴可呼叫者確為 5 個且五者皆唯讀（故「在依賴階段提交是安全的」這個論證站得住）、`get_db` 不提交不復原、`expire_on_commit` 預設為 `True` 使成本第二項成立（實測 `commit()` 後全欄位進入 `unloaded`）、SQLite 實測把 tz-aware 值讀回為 `tzinfo=None`、naive 與 aware 相減實測拋 `TypeError`、三個既有補欄函式確為三個功能批次且其中兩個往 `users` 加欄位。三檔 `required-sections` 全過，全檔無實際程式碼、無 3.2／3.3 的新 NFR 決策（成本與擴展特性兩節皆為 `services.md` 已核可分析的轉述，非本站新創），**未越界**。

擋下的三項都不是論證品質問題，而是**責任交接的破口**：①時區正規化定為私有，使 `component-methods.md` C-4「序列化前亦須套用同一正規化」在結構上無法共用，而介面表沒有把這項義務交給 U2 —— 依 `team.md` 的單一真實來源規則，這是一份會漂移且未被鎖住的副本；②「哪些認證請求算活動」這條規則從未被寫下，而 `auth.py:60-64` 的停用 403 就落在觸發點前後一行之間，主流程又丟失了上游「尾端」的位置精度，使 `domain-entities.md`「帳號停用｜不變」成為無依據的斷言，且停用與 pending 帳號都真的會出現在新欄位裡（`list_users` 回傳全部使用者）；③上游 story map 第 140 行明確指派給 U1、且該表存在的唯一理由就是「以免它們在單元切分後失蹤」的 WebSocket 範圍限制，在本站整段消失 —— 而本站對另外兩項 U1 缺口的承接是完整的，可見這是漏接而非決定。

三項皆為低成本可補（各為一個段落或一列），補完後兩條規則、交易契約與實體定義完全不需重畫。**判定 NOT-READY**（0 Critical、3 Major）。

---

## Review — Revision 1（未受影響性查核）

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-11T02:32:34Z
**Iteration:** 1

**查核範圍**：本輪不重新裁決 U1（`backend-activity-policy`）與 U4（`security-reviewer-permission`）既有已核可（iteration 2）的功能設計內容本身，只驗證「Revision 1（PU-6 使用者清單分頁）對兩單元零影響、其功能設計文件不需修改」這一項主張是否成立。依 `unit-of-work.md`／`unit-of-work-story-map.md`／`decisions.md`（AD-10／AD-11／AD-12）／`bolt-plan.md` 的 Revision 1 段落，以及工作樹中已存在的實作程式碼逐項對抗式核對，未讀取任何 sibling unit 的 `construction/<other-unit>/` 內容——涉及 U2／U3 的比對一律經共享的 inception 產物（`unit-of-work-story-map.md`、`decisions.md`）或應用程式碼本身核對，非讀取 U2／U3 的 construction 產出。

### 查核表

| # | 項目 | 方法 | 結果 |
|---|---|---|---|
| 1 | US-5 的 11 條 AC 是否有任一條落在 U1 或 U4 | 逐條讀 `stories.md` AC-5.1〜AC-5.11 原文；核對 `unit-of-work-story-map.md` Revision 1 的 AC→單元對應表（第 178〜188 行） | **AC 層級表：無一落在 U1 或 U4**，11 條全數落在 U2／U3。AC-5.8（「分頁回應中的欄位值與資料庫一致」）明確落在 U2——其「落點理由」逐字寫明「分頁 envelope 是**新的回應構造點**」，是序列化構造點問題，不是 R1／R2 判定邏輯問題。**但發現一項跨表不一致，見 Findings #3** |
| 2 | B2 拆分後，U1 單獨成 Bolt 的信心假說與預期展示，是否與 U1 四份文件相符 | 讀 `bolt-plan.md` Revision 1 §B2（信心假說、DoD、預期展示：「展示在資料庫層，不在 UI」） | **相符**。U1 四份文件全文無一處提及 UI、管理頁或前端讀者；「已知的驗證缺口」段落原文就是「承接方式：部署後重啟 + 人工核對」，未預設任何 UI 驗證路徑。DoD 五項（C-1 property-based、C-2 自行提交、C-3 可為空/無預設值/可重跑、schema 同步）逐字與 Revision 1 前的 B2 DoD 相同，未被拆分動過 |
| 3 | 清單端點分頁後由一次查詢變兩次查詢（`count()` + 分頁 `all()`），是否觸及 C-2 的交易契約 | 讀 `backend/services/user_router.py::list_users`、`backend/services/auth.py::get_current_user` | **不觸及**。兩個查詢皆為唯讀（`count()`／`.offset().limit().all()`），皆在 `get_current_user`（含 `record_activity` 的自行提交）已執行完畢**之後**才發生，不開新交易、不提交、不復原。`domain-entities.md`／`business-logic-model.md` 已記載的「提交後 `expire_on_commit` 觸發使用者重讀」成本不因兩次查詢而放大——重讀是既有身分物件被自動刷新，與清單查詢的次數無關 |
| 4 | Revision 1 是否觸及權限矩陣、`role_permissions`、或啟動補丁 `_apply_security_reviewer_j3a_view`（U4 範圍） | `git diff` `backend/database.py`、`backend/services/rbac_seed_data.py`、`schema_rbac.sql` 三檔 | **未觸及**。三檔目前的未提交變更**只有** U4 既有的 PU-4 內容（`Security_Reviewer`／`J3a` 兩處預設值翻轉為 `can_view=True`、啟動補丁 `_apply_security_reviewer_j3a_view`），無一行與分頁相關。`list_users` 的新查詢參數與 envelope 完全長在 `user_router.py` 內，掛的仍是 U4 既有開通的**同一個** `require_story_action("J3a", "view")` 依賴，分頁未新增、移除或調換任何權限檢查 |
| 5 | 四份文件的既有主張是否被目前工作樹中已寫成的實作推翻 | 逐行比對 `business-rules.md`／`business-logic-model.md`／`domain-entities.md`（兩單元）against `backend/services/activity.py`、`backend/database.py`、`backend/services/user_router.py`、`backend/tests/test_activity.py`、`backend/tests/test_j3a_view_permission.py`、`backend/tests/test_user_list_endpoint.py` | R0 觸發點位置（`is_active` 檢查之後、`return user` 之前）、R1／R2 邊界、C-2 自行提交／先復原、C-3 可為空無預設值可重跑、U4 的只更新不插入／條件式套用，**逐項與程式碼相符**。**但發現兩項與分頁無關、獨立存在的實作落差，見 Findings #1、#2**——這兩項不是本輪 Revision 1 引入的缺口，是先於且獨立於 PU-6 的既有落差，本查核依 hunt 第 5 項的明確要求一併如實記載 |

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Major（**與 Revision 1 無關**，獨立既有落差） | `backend/database.py:299-349`（`_apply_security_reviewer_j3a_view`）vs `business-rules.md` R4（L74-88） | **U4 兩輪 reviewer 反覆強調的「後兩態同級、需人工處置」四態記錄契約，在實作中未被遵守。** R4 明文要求「未套用：該列已被管理員異動」須與「未命中目標列」**同級**標示為需人工處置（「這是本規則相對上游最重要的一項強化」）。實作中「未命中目標列」用 `logger.warning(...)`；但「該列已由 %s 人工調整，不覆寫」這一分支用的是 `logger.info(...)`，且訊息措辭沿用了 M1-a 明確要求打掉的「已跳過」字眼——兩態在啟動日誌上並不同級可見。另外，`domain-entities.md` 明文要求本補丁套用成功時寫入「補丁專屬識別字」（第三種 `updated_by` 取值），但實作的成功分支只有 `row.can_view = True; db.commit()`，**從未寫入任何識別字**——冪等改靠直接檢查 `can_view` 現值達成，與設計描述的判定順序（先看 `updated_by`）不同。`test_j3a_view_permission.py` 檔頭自陳不涵蓋這支函式，故此落差目前無任何測試會抓到。**此發現與 PU-6 分頁改動完全無關**——U4 的功能設計文件本身仍然正確（已通過兩輪對抗式審查），落差在**實作**，不在設計 | 不建議回改 U4 的功能設計文件（設計正確）；建議在 code-generation／build-and-test 階段修正實作：①把「已被管理員異動」分支改為與「未命中目標列」同級（`logger.warning` 或等級更高），且不再沿用「已跳過」措辭；②成功套用時依 `domain-entities.md` 寫入一個不可能與帳號衝突的補丁識別字到 `updated_by` |
| 2 | Major（**與 Revision 1 無關**，獨立既有落差） | `backend/services/activity.py`（`_as_aware_utc` 前綴底線、全 repo零匯入）vs `backend/services/user_router.py::_to_user_schema`（`last_activity_at=user.last_activity_at` 未正規化直傳）vs `business-rules.md` L103-109 | **U1 iteration 1 Major Finding 1 的解法（把正規化 helper 由私有改公開，供 U2 呼叫）在實作中未落地。** `business-rules.md` 明文：「正規化 helper 是本單元對外的公開介面，U2 直接呼叫它——這項交接已列入 `business-logic-model.md` 的介面表」。但 `activity.py` 中的正規化函式仍叫 `_as_aware_utc`（前綴底線，全 repo `grep` 零其他匯入），`user_router.py::_to_user_schema` 把 `user.last_activity_at` 原樣傳進 `UserSchema`，未呼叫任何正規化。目前無任何測試會抓到——`test_user_list_endpoint.py`／`test_activity.py` 對時間欄位的斷言止於「非 None」／值相等，未檢查序列化後的 ISO 字串是否帶時區位移。生產環境（PostgreSQL 保存時區）現況下無已知外顯影響（設計本身也預期正規化在生產路徑是 no-op），但**這正是 reviewer 當初要求補上的那道防線本身沒有被接上**——一旦讀回值在任何環境下變成 naive（例如既有測試路徑），該值會不帶時區位移直接進入回應 JSON，與 AC-1.6「不因寫入端與顯示端的時區處理差異而偏移」的精神相悖。**此發現與 PU-6 分頁改動完全無關**——它是 U1／U2 邊界既有的落差，早於且獨立於本輪 Revision 1 | 不建議回改 U1 的功能設計文件（設計正確，已通過兩輪審查）；建議在 code-generation／build-and-test 階段修正：將正規化函式改為公開（去底線前綴或另提供公開包裝），並在 `_to_user_schema` 序列化 `last_activity_at` 前呼叫它 |
| 3 | Minor | `unit-of-work-story-map.md` Revision 1（AC→單元表第 185 行 vs 需求層對應表「FR-6.6」列） | **同一份文件的兩張表對「AC-5.8／FR-6.6 是否落在 U1」互相矛盾。** AC 層級表明寫「AC-5.8｜**U2**」；但「需求層的對應」表把 FR-6.6 記為「**U1**（判定不變）、U2（值一致）」。經查證：FR-6.6 要求「分頁不改變逾期標示與無紀錄態的判定規則」，這項不變量由 R2 是純函式（只吃 `last_activity_at`／`now`，不吃頁次）**自動滿足**（`backend/services/activity.py::is_overdue` 的簽章確認無頁次相關輸入），**U1 的四份功能設計文件不需要為此新增任何內容**——這與本查核項目 1／5 的結論一致。但兩張表本身的矛盾是上游 `unit-of-work-story-map.md`（units-generation 階段產出）的文件缺陷，不在本次查核的四份文件範圍內，本站不逕自修改 | 建議下次接觸 `unit-of-work-story-map.md` 時於 AC 層級表 AC-5.8 列加註「FR-6.6 的判定不變子句由 U1 既有 R2 之純函式性質自動滿足，非新增義務」，消除與需求層表的表面矛盾；不需要、也不建議變更 U1／U4 任一份 construction 產出 |

### Summary

**兩單元皆為「真正未受影響」，「不需修改功能設計文件」的結論成立**，理由逐項有據：US-5 的 11 條 AC 在 `unit-of-work-story-map.md` 的 AC 層級對應表中無一落在 U1 或 U4；`unit-of-work.md` Revision 1 逐字記載 U1、U4 複雜度「M（不變）」，且拆分 C-9 後的四條 DAG 邊未新增，只強化既有的 U2→U1 邊（該邊由 C-4→C-1／C-3 早已建立，非本輪新生）；`bolt-plan.md` Revision 1 把 U2 移出 B2、讓 U1 單獨成 Bolt 的理由（envelope 是破壞性契約變更、須與消費端同批部署）完全不涉及 U1 本身的介面或行為，U1 的 DoD 逐字未變，只是展示層級改為純資料庫層並如實記載；分頁端點的兩次查詢皆為唯讀且晚於 C-2 的提交，不放大也不改變既有的交易契約與其成本分析；U4 涉及的 `role_permissions`／啟動補丁在工作樹的實際 diff 中只含 U4 自身既有內容，分頁完全未觸碰，且分頁端點沿用的正是 U4 已開通的同一個權限依賴。

**唯一需要留意的落差與 Revision 1 無關**：查核第 5 項（依任務明確要求的「文件主張 vs 已寫成的實作」比對）發現兩項獨立、與分頁無涉的既有落差——U4 的 R4 四態記錄在實作中的日誌等級未達成「後兩態同級」的設計要求，且成功套用時未依設計寫入補丁識別字（Finding 1）；U1 的時區正規化 helper 未如設計所述被公開並被 U2 序列化路徑呼叫（Finding 2）。兩者皆判 Major，但**均為實作與設計的落差，不是功能設計文件本身的缺陷**——兩份設計都已通過兩輪對抗式審查且維持正確，問題出在後續（尚未經 review 的）code-generation／實作階段沒有完全落實已核可的契約，應在 build-and-test 或下一輪 code review 時處理，不構成回改 U1／U4 這四份 construction 文件的理由，也不影響「Revision 1 對兩單元零影響」本身的判定。另有一項 Minor（Finding 3）純屬上游 `unit-of-work-story-map.md` 內部兩張表的措辭不一致，同樣不影響本查核結論。

**判定 READY**：U1（`backend-activity-policy`）與 U4（`security-reviewer-permission`）的功能設計文件在 Revision 1（PU-6 分頁）之後**確實不需要任何修改**。

### 未受影響性查核的兩項附帶發現 —— 處置（2026-08-11）

該輪 reviewer 在做 doc-vs-code 比對時，另外查出兩項**與分頁無關**的實作忠實度缺口（設計本身正確，實作沒跟上）。兩項**皆已修正並補上測試**：

| # | 缺口 | 修正 | 新增的測試 |
|---|---|---|---|
| 1 | U1 的時區正規化函式 `_as_aware_utc` 是私有的、全 repo 零匯入；U2 的序列化 `_to_user_schema` 把 `last_activity_at` **原樣直傳**，而 `business-rules.md` 明文把這個整合點記為已解決 | 改為公開的 `as_aware_utc` 並接進序列化。**後果比看起來嚴重**：不帶位移的時間字串會被瀏覽器的 `new Date()` 當成本地時間解讀，顯示時間整體偏移一個時區位移量 —— AC-1.6 失敗，而畫面上完全看不出來 | `test_user_list_endpoint.py::test_serialised_timestamp_carries_a_utc_offset` —— 在 SQLite 上跑（正是最會露餡的環境），斷言回應帶位移且往返後仍是同一時點 |
| 2 | U4 的 `_apply_security_reviewer_j3a_view` 未遵守 `business-rules.md` R4 的**四態**契約：把「已被管理員異動」當常態跳過（`info`）而非與「未命中目標列」同級的需人工處置（`warning`），且從不寫入補丁識別字 | 第三態改為 `warning` 並帶出該欄實際值；套用成功時寫入 `system_patch.j3a_view` | `test_j3a_view_permission.py::J3aStartupPatchTest` 四個 case，涵蓋四個分支。**這填補了先前明文記載為「無自動化驗證」的既有環境套用路徑**（真實啟動流程仍需部署後人工核對日誌） |

第 2 項另有一個先前未被任何文件預見的分支：`schema_rbac.sql` 的 `INSERT` 不含 `updated_by`，故真實 staging 的該欄為 **NULL**。原實作只認 `"system_seed"`，會把 NULL 誤判為人工調整而**在最需要它的環境靜默失敗**。已把 NULL／空字串一併視為「尚未被人工調整」，並以 `test_applies_when_row_came_from_the_sql_seed` 釘住。此分支是在**真實 docker stack 上實跑**時發現的，不是讀程式碼看出來的。
