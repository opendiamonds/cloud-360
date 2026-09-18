# Components — 元件邊界與職責

> Stage: application-design（Inception 2.6）· Intent: 260802-last-login-column
> 上游來源：`../requirements-analysis/requirements.md`（下稱 requirements）、`../user-stories/stories.md`（下稱 stories）、`../practices-discovery/team-practices.md`（下稱 team-practices）、`../refined-mockups/interaction-spec.md`、codekb `architecture.md` 與 `component-inventory.md`。
> 本站問答定案：`application-design-questions.md` Q1／Q2／Q3 皆選 A。
> **本文件為 iteration 3**，依 iteration 1 與 iteration 2 的 reviewer findings 修訂（兩輪審查紀錄保留於文末）。

## 設計立場

本 intent 是在**既有的 FastAPI 模組化單體**上加一個欄位並顯示它，不是引入新架構。因此本設計的第一個決定是**不新增服務、不改變架構風格、不引入新依賴**（理由與替代方案見 `decisions.md` AD-5）。所有變更落在既有模組邊界內，元件劃分的目的是讓**業務規則與 I/O 分離**，使規則層可被既有測試實務直接覆蓋。

依 requirements 的功能需求，本 intent 有兩條**時間門檻規則**：

- 寫入節流門檻 —— 同一帳號兩次寫入至少相隔 5 分鐘（requirements FR-1.3，滑動視窗、基準為上次成功寫入）
- 逾期判定門檻 —— 距今超過 90 天視為逾期（requirements FR-3.1，嚴格大於）

兩者形狀相同：拿一個時間戳、跟當下比、對一個門檻做判斷。**本站把它們收斂為同一個純函式元件**（C-1），而不是各自散落在寫入路徑與序列化路徑裡。這是本站的設計推論，非問答直接定案 —— 依據見 `decisions.md` AD-4。

除了「加欄位、顯示欄位」之外，本 intent 還有**兩件容易被漏掉的必辦事項**，iteration 1 的審查證實初版確實漏了它們，現各有專屬元件：

- **欄位必須出現在所有回傳使用者物件的端點**（requirements FR-2.5）—— 不只清單端點。承載於 C-4。
- **權限預設值的變更必須在既有環境真的生效**（requirements FR-4.3、stories AC-3.4）—— 這在現行機制下沒有生效路徑。承載於 C-7。

> **元件編號與需求編號是兩套命名空間**：本檔的 `C-n` 指元件；requirements 的 `C-n` 指約束條件。引用需求約束時一律寫成「requirements C-n」。

## 元件清單

| ID | 元件 | 所在層 | 新增／既有 | 核心職責 |
|---|---|---|---|---|
| C-1 | 活動時間政策 | 後端 · 純邏輯 | 新增 | 擁有全部時間門檻規則；零 I/O、零框架依賴 |
| C-2 | 活動時間記錄器 | 後端 · 請求路徑 | 新增 | 依 C-1 判定，在需要時執行單筆條件式寫入 |
| C-3 | 使用者資料模型與既有庫補欄 | 後端 · 資料 | 既有擴充 | 新欄位的模型定義、新建環境 DDL、既有環境補欄 |
| C-4 | 使用者物件序列化 | 後端 · API | 既有擴充 | **所有**回傳使用者物件的端點都帶出時間值與逾期旗標 |
| C-5 | 最後活動時間儲存格 | 前端 · 呈現 | 新增 | 單一儲存格的五種狀態呈現 |
| C-6 | 管理頁資料傳遞 | 前端 · 頁面 | 既有擴充 | 取得 API 欄位並正規化後傳給 C-5；表頭與卡片佈局 |
| C-7 | 權限預設值變更與既有環境套用 | 後端 · 資料 | 新增 | 兩處預設值來源同步；既有環境的目標式套用 |

---

## C-1 活動時間政策

**職責**：擁有本 intent 全部與「時間門檻」有關的業務規則。這是唯一知道「5 分鐘」與「90 天」這兩個數字的地方。

**公開介面**（簽章見 `component-methods.md`）：
- 判斷「距上次成功寫入是否已達最小間隔」
- 判斷「距最後活動是否已超過逾期門檻」

**邊界與所有權**：
- **擁有**：兩個門檻常數、兩個判定規則、邊界語意（requirements FR-3.1 的「嚴格大於」、FR-1.3 的滑動視窗基準）、**時間參數的時區契約**
- **不擁有**：任何資料庫存取、任何 HTTP 概念、任何「現在幾點」的取得方式 —— 當下時刻一律由呼叫端傳入

**時區契約**（iteration 1 Finding 8）：兩個判定的所有時間參數**一律為帶時區的 UTC**。這不是實作細節而是介面契約，因為 repo 目前**同時存在兩種慣例** —— 既有的認證模組用不帶時區的寫法，既有的使用者路由用帶時區的寫法。Python 對這兩種值做比較會直接拋型別錯誤。更關鍵的是測試環境使用 in-memory SQLite，而 **SQLite 不保存時區**，讀回的值不帶時區；若呼叫端傳入帶時區的當下時刻，requirements NFR-5 所要求的第一支端點測試會在第一次比較就失敗。契約的具體形狀（含違反時的行為）見 `component-methods.md`。

此契約同時是 stories AC-1.6 交辦本站的「儲存與顯示時區策略」的設計期落點。

**為何是獨立元件**：把當下時刻設計成參數而非在內部取用，使這兩個規則成為**完全確定性的純函式**。team-practices 記載的既有實務是「團隊為可直接呼叫的純函式寫測試的比例，遠高於需要組裝請求的路由層」，且既有的 8 個 property-based 測試全部落在純函式模組。把規則放在這個形狀，等於把它放進團隊已經證明會被測到的位置；邊界條件（恰好 5 分鐘、恰好 90 天、無紀錄）因此可被直接斷言，不需要架設資料庫或發 HTTP 請求。

**無紀錄的處理**：從未有活動紀錄時，兩個判定都必須有明確答案 —— 「該寫入」為真（第一次活動要記下來），「逾期」為否（沒有紀錄不等於逾期，這是 requirements FR-2.3 與 stories AC-2.3 已確立的語意：無紀錄態不掛逾期標示）。

---

## C-2 活動時間記錄器

**職責**：在認證後的請求路徑上，依 C-1 的判定決定是否寫入，並在需要時執行單筆更新。

**觸發位置**：既有的認證依賴（codekb `architecture.md` 記載其為所有認證請求的必經點；iteration 1 已跨 5 支 router 窮舉確認**不存在「已認證但不經此點」的路徑**）。該處**已經取得完整的使用者物件與可用的資料庫工作階段**，因此判定所需的資料在此刻已在手，不需要任何額外查詢。

**公開介面**：單一進入點 —— 接受使用者物件、資料庫工作階段與當下時刻，回傳是否實際寫入。

**邊界與所有權**：
- **擁有**：寫入時機的執行、**交易的提交與復原**、寫入失敗的處置
- **不擁有**：門檻規則本身（屬 C-1）、欄位的資料型別（屬 C-3）、工作階段的生命週期（借用不獨佔，不關閉）

**交易語意**（iteration 1 Finding 3 —— 這是本元件最關鍵的契約）：實測既有的工作階段供應器**既不提交也不在例外路徑復原**，只在結束時關閉。因此本元件的兩個分支都必須自行負責：

- **必須自行提交**。絕大多數認證端點是唯讀的（使用者清單、個人資訊，以及協作、審查、透鏡各模組的全部讀取端點），它們本身從不提交。若本元件不提交，待決的更新會在工作階段關閉時被整個丟棄 —— requirements FR-1.1 對這些端點**永遠不會成立**，而回傳值還會宣稱寫入成功。
- **失敗時必須先復原再記錄**。若只吞下例外而不復原，工作階段會進入待復原狀態；緊接著執行的權限檢查會查詢權限表，直接拋出例外，**使用者的原始請求照樣失敗** —— 那會直接推翻本元件「不得讓原始請求失敗」的核心承諾。

**失敗處置**：活動時間的寫入是**輔助性副作用，不是請求的目的**。因此寫入失敗不得讓使用者的原始請求失敗 —— 一次記錄失敗導致整個 API 呼叫掛掉，是明顯不成比例的後果。但「不讓請求失敗」不等於「靜默吞掉」：失敗必須記錄下來，使其可被觀察。

> **來源誠實聲明**（iteration 1 Finding 4）：「寫入失敗不得讓原始請求失敗」這條約束**在 requirements 與 stories 中都沒有對應條文**，是本站的設計判斷，唯一的上游依據是 construction 階段護欄的「silent failures are not acceptable」（它要求失敗必須被記錄，但沒有規定失敗的傳播方式）。初版誤將其標為 requirements NFR-4；NFR-4 的實際內容是授權矩陣的雙向測試要求。此判斷在核可 gate 上開放挑戰。

**併發**（iteration 1 Finding 9 修正）：兩個請求同時判定為「該寫入」時，兩者都會發出更新。各自持有自己算出的當下時刻，資料庫的列鎖保證更新序列化，但**不保證後提交者的時刻較大** —— 最終值是後提交者的時刻，與兩者的較大值可能有次毫秒級的偏差。在 5 分鐘的節流語意下這個偏差沒有實務影響，因此不需要鎖。（初版寫成「單調前進」是錯的，該論據不成立，但結論不變。）

---

## C-3 使用者資料模型與既有庫補欄

**職責**：新欄位在三個地方的一致定義 —— 應用層模型、新建環境的 DDL、既有環境的補欄。

**組成**：
1. **模型欄位** —— 使用者模型新增一個可為空的時間戳欄位（可為空是必要的：既有帳號在功能上線時全部沒有值，這正是 requirements C-1、FR-2.3 與 stories AC-2.3 的無紀錄態來源）
2. **新建環境 DDL** —— 依 requirements C-4 同步至 repo 根目錄的 schema 檔與部署文件（blocking）
3. **既有環境補欄** —— 沿用既有的啟動補丁機制（本站 Q3 定案）

**為何補欄走啟動補丁**：codekb `component-inventory.md` 記載的既有機制中，**已有兩個同形狀先例都是往使用者表加欄位**，且都採用可重複執行的寫法（iteration 1 實測確認兩者形狀逐字相同）。本 intent 要做的事與它們形狀完全相同，沿用即可；且此路徑**不需要重跑會重置權限矩陣的初始化腳本** —— requirements C-3 已明文禁止以重跑整份腳本作為本次變更的套用手段。詳見 `decisions.md` AD-3。

**部署後必須重啟**（requirements C-2、stories AC-1.7）：專案無資料庫遷移框架，結構變更靠服務啟動時自動補齊。因此**部署後服務必須完成一次重啟，欄位才會存在**。這不是可選的維運建議，而是本設計成立的前提，須寫入部署程序。

**時區型別**：欄位採帶時區的時間戳，與既有慣例一致（requirements C-5；iteration 1 實測確認既有 9 個時間欄位全部採此形式）。**不設資料庫層預設值** —— 若給預設值，「從未活動」與「剛建立帳號」在資料上就無法區分，會摧毀本 intent 的核心語意。

**欄位命名**：本站依既有慣例決定（snake_case），**未經問答定案**，屬本站設計判斷，見 `decisions.md` AD-6。

**FR-1.4 的設計期判定**（stories 明文交辦本站）：requirements FR-1.4 要求「資料模型須保留未來擴充為歷史紀錄的路徑」，且該需求無行為驗收條件，其落點就是本站的設計審查。**判定：符合**。理由是本設計採用使用者表上的單一可為空欄位、每次覆寫，這個形狀對日後新增獨立歷史表沒有任何阻擋 —— 歷史表可用外鍵指向使用者，而現有欄位可保留為「最後一次」的快取或逕行移除。本設計**未**引入會妨礙擴充的結構（例如把多筆活動塞進單一欄位的序列化字串、或以欄位語意承載時序假設）。

---

## C-4 使用者物件序列化

**職責**：**所有回傳使用者物件的端點**都帶出時間值與逾期旗標兩個欄位。

> **iteration 1 Finding 1 的修正**：初版把本元件限定為「使用者**清單**序列化」，導致 requirements FR-2.5 與 stories AC-1.5 完全沒有承載元件。FR-2.5 的原文是「**所有**回傳使用者物件的端點都必須包含此欄位」，而 stories US-1 的完成定義逐字點名了高風險落點。

**「使用者物件」的邊界定義**（iteration 2 Finding N3）：本元件所稱的「使用者物件」**專指 Admin 使用者管理清單的列模型**（`UserSchema`）。requirements FR-2.5 的驗收條件把範圍收斂到 Admin 頁的角色調整與啟停用操作，故以該模型為界。

被明確**排除**的端點（皆回傳使用者資料但非 Admin 列模型，且非 Admin 頁的消費對象）：

| 排除的端點 | 回傳模型 | 排除理由 |
|---|---|---|
| 個人資訊端點 | 自有的個人資訊模型 | 呈現當前登入者自己的資料，非 Admin 稽核清單 |
| 協作使用者清單 | 精簡欄位的字典 | 協作功能的參與者選單，refined-mockups 的消費端不含它 |
| 登入／註冊回應 | 自有的登入回應模型 | 認證流程的回應，不是使用者管理資料 |
| 授權申請核准回應 | 精簡字典 | 操作結果回執，非完整使用者列 |

**若日後要把欄位擴及這些端點，屬新的範圍決定，不由本設計隱含涵蓋。**

**邊界 —— 三個構造點**：實測既有程式碼，`UserSchema` 在三處被構造，**三處全部都是手寫具名引數**（全 repo `from_orm` 使用數為 0，該模型雖啟用了 ORM 轉換但無任何呼叫端使用）：

| 構造點 | 形式 | 現況風險 |
|---|---|---|
| 使用者清單端點 | 手寫具名引數構造 | **高** |
| 啟停用端點 | 手寫具名引數構造 | **高** |
| 角色調整端點 | 手寫具名引數構造 | **高** |

> iteration 2 Finding N2：初版把清單端點記為「隨查詢結果序列化／風險低」，與程式碼不符，也與已核可的 stories US-1 完成定義矛盾 —— 該定義逐字把**使用者清單端點**與兩個更新端點並列為高風險落點。三處形式與風險完全相同，不存在「一個自動、兩個手寫」的分佈。清單端點更是本 intent 的**主要顯示路徑**（requirements FR-2.1、FR-2.2、NFR-6 皆依賴它），標為低風險會把注意力從它身上移開。

後兩者**現行就已經漏傳既有的一個欄位**（請求中的角色欄位），這證明「手寫構造點會漏欄位」不是假設性風險，而是這個 repo 已經發生過的事實。新欄位若只加進回應模型而不處理這三個構造點：

- 若欄位有可靜默通過的預設值 → 兩個端點回傳空值或否，**完整複製既有缺陷**，而 stories AC-1.5 逐字要求「而非因構造遺漏而缺失」，該驗收條件直接失敗
- 若欄位無預設值 → 兩個端點在執行期直接錯誤

**因此本元件的設計約束是**：兩個新欄位在回應模型上**不得設置可靜默通過的預設值**，或改以**單一的共用工廠函式**（接受使用者物件與當下時刻）使三個構造點不可能分歧。ORM 自動轉換不是可行選項 —— `is_overdue` 是衍生值而非儲存欄位，ORM 物件上不存在該屬性（iteration 2 Finding N8）。具體形狀見 `component-methods.md`。

**輸出的兩個欄位**：
- 最後活動時間（可為空的時間戳，UTC）
- 是否逾期（布林；本站 Q2 定案為後端計算）

**邊界與所有權**：
- **擁有**：回應欄位的形狀、空值表達、三個構造點的一致性
- **不擁有**：逾期的判定規則（呼叫 C-1）、顯示格式（屬 C-5／C-6）、誰看得到（屬既有權限機制與 C-7）

**為何逾期由後端算**：90 天是業務規則，與稽核對「什麼算逾期」的定義同源；放在定義它的那一端只有一個真相來源。更關鍵的是**客戶端時鐘不可信** —— 前端計算會讓判定結果取決於使用者裝置的系統時間，裝置時鐘偏移或時區設定錯誤會使同一份資料在不同機器上顯示不同的逾期狀態。在稽核用途下，由客戶端時鐘決定合規標示不可接受。詳見 `decisions.md` AD-2。

**授權**：本欄位的可見性由既有的端點層權限檢查決定（requirements FR-4.2 已明文定案「權限粒度維持現狀，不做欄位級控制」，且列於 Won't Have）。序列化元件**不做欄位級授權判斷**，這是正確的而非缺口。權限**資料**的變更屬 C-7。

**時區**：回應一律為 UTC 時間戳，顯示端負責在地化（requirements C-5）。

---

## C-5 最後活動時間儲存格

**職責**：單一儲存格的呈現，涵蓋 refined-mockups `interaction-spec.md` 已規格化的五種狀態。

**輸入**（皆為傳入值，元件不自行計算）：時間值（可為空）、是否逾期。兩者皆為必填，型別不含未定義 —— 正規化責任在 C-6。

**為何逾期是傳入而非自算**：`interaction-spec.md` 已定此形狀，理由是避免在算繪過程中讀取當下時刻所觸發的 lint 規則違反。本站 Q2 的定案讓這個傳入值有了明確來源 —— 來自後端回應，而非前端在資料處理階段計算。

**邊界**：只負責一格。表頭、欄位順序、卡片佈局、斷點皆屬 C-6。設計語彙（色階、字級、內距）全部沿用既有管理頁既有值，對應關係見 refined-mockups `design-system-mapping.md`。

---

## C-6 管理頁資料傳遞

**職責**：既有管理頁的擴充 —— 表頭新增一欄、把 API 欄位正規化後傳給 C-5、在小螢幕斷點以下改用卡片佈局。

**正規化責任**（iteration 1 Finding 10）：C-5 的兩個輸入皆為必填且型別不含未定義，但實測前端的使用者型別是手寫介面、資料抓取未做欄位驗證，因此**後端尚未部署時這兩個欄位會是未定義**。本元件必須在傳遞點把未定義收斂為 C-5 宣告的型別（空值與否）。這使「部署順序無硬性約束」的論證成立，而不只是因為執行期碰巧不會爆。

**資料抓取形狀**（requirements C-6）：若新欄位需要額外資料源，必須沿用既有的抓取與狀態更新拆分形狀，否則 CI 紅燈。本設計不需要額外資料源（兩個欄位隨既有的使用者清單回應一併取得），故此約束自動滿足。

**邊界與所有權**：
- **擁有**：欄位在表格中的位置、斷點切換、卡片內的欄位順序、傳給 C-5 前的正規化
- **不擁有**：單格呈現（屬 C-5）、逾期判定（屬 C-4／C-1）

**明確不做**：載入態與錯誤態沿用既有的整塊替換模式，不重新設計（stories AC-1.9 已依實測定案）。既有的角色欄空值呈現維持原樣不動 —— 那在本 intent 範圍外（stories AC-2.5 的區分手段定案為僅以可及性區分）。

---

## C-7 權限預設值變更與既有環境套用

> **本元件為 iteration 2 新增**（iteration 1 Finding 2）。初版把 requirements FR-4 整條映射到 C-4 並宣稱「本 intent 不改變權限機制」—— 這是錯的。本 intent 不改變權限**機制**，但確實要改權限**資料**，而那筆變更在現行機制下**沒有任何生效路徑**。

**職責**：讓 `Security_Reviewer` 取得使用者管理介面的檢視權限，並確保該變更在既有環境真的生效。

**問題的形狀**：實測確認三件事疊在一起，構成一個會靜默落空的缺口：

1. 該角色的權限預設值在**兩處來源**都是關閉的（種子資料模組與初始化腳本），requirements FR-4.3 要求兩處同步，任一處未同步即視為未完成
2. 種子函式**僅在權限表為空時寫入** —— 既有環境的表早已有資料，因此改了預設值也不會被套用
3. requirements C-3 **禁止**以重跑整份初始化腳本作為套用手段（那會重置管理員在介面上調整過的所有權限）

三者相加的結果是：**改了兩處預設值之後，既有 staging 上這筆權限依然是關閉的，而所有測試與 CI 都會是綠的**。stories AC-3.4 正是為了防止這件事而寫的驗收條件。

**組成**：
1. **兩處預設值同步** —— 種子資料與初始化腳本的該筆權限值必須一致（requirements FR-4.3）。一致性檢查的具體落點見下方「§FR-4.3 的一致性檢查落點」
2. **既有環境的套用機制** —— **只更新、不插入**的目標式更新，只動該角色與該功能的那一列
3. **雙向測試** —— requirements NFR-4 要求授權矩陣變更需有 allow/deny 雙向測試（team-practices 本輪新增規則 A 同此），即同時驗證該角色可檢視、且未獲授權角色不可檢視

### 執行順序與空表行為（iteration 2 Finding N1 —— 這是本元件最關鍵的契約）

> **初版把本元件寫成「形狀比照 C-3 的補欄補丁」＋「該列不存在時插入」，這個組合會造成災難性後果**，reviewer 實測後揭露，判定為 Critical。此處明確定死。

實測既有的初始化流程順序為：建表 → **三個補欄補丁** → 使用者種子 → **權限種子**。C-3 的三個先例全部位於補欄補丁的位置，也就是**在權限種子之前**。

若本元件依「形狀比照 C-3」放在同一處，且依「不存在時插入」執行，則在權限表為空的環境中會發生：

1. 本元件先插入該角色的那一列 → 權限表不再為空
2. 既有的權限種子函式判定「表非空」→ **直接返回，308 列預設矩陣一列都不寫入**
3. 所有角色的權限查詢皆查無資料 → 權限判定恆為否 → **全系統的 RBAC 端點盡數拒絕存取**

**這個情境確實可達**：repo 根目錄的本機開發用編排檔**沒有把初始化腳本掛載進資料庫初始化目錄**（只有部署與測試用的兩支有），該路徑的權限矩陣完全依賴 Python 種子。**且沒有任何測試會發現** —— 測試輔助模組以強制模式直接建矩陣，從不經過初始化流程。

**因此本元件的契約是**：

- **執行順序**：必須在**權限種子函式之後**執行，**不得**與 C-3 的補欄補丁並列於建表之後的位置
- **空表行為**：**只更新、不插入**。權限表為空時本元件不做任何事，由既有的種子函式負責建立完整矩陣

「不存在時插入」的分支在既有種子已涵蓋該列的前提下沒有任何正當用途，**只有製造上述故障的能力**，故明確排除。

### 冪等語意：條件式更新而非無條件回寫（iteration 2 Finding N4）

初版寫「可重複執行 —— 多次啟動的結果相同」，實際語意是**每次服務重啟都把該權限強制設回開啟**。這有一個未被揭露的後果：管理員若日後在管理介面上刻意撤銷此權限，**下一次部署重啟會靜默把它復原**，而 requirements C-7 已載明權限變更的稽核記錄是易失性的 —— 撤銷會消失且無跡可循。

這與 `decisions.md` AD-7 否決「重跑種子強制模式」的理由自相矛盾：那個方案被否決正是因為它會覆寫管理員的調整。與 C-3 的類比在此也失效 —— 補欄語句冪等且**永不覆寫使用者資料**，權限更新會。

**因此本元件採條件式更新**：**僅在該列尚未被本補丁套用過時才更新**。

判斷「是否已套用過」不能只看權限值本身 —— 「從未套用」與「已套用後被管理員撤銷」兩者的值都是關閉，無法區分。**但既有 schema 上已經有能區分它們的欄位**（iteration 3 Finding M1）：權限表的每一列都有一個記錄「最後由誰異動」的欄位，其取值在三條路徑上明確且互斥 —— 種子寫入時為固定的系統識別字、初始化腳本寫入時為空、**管理員經管理介面調整時為該管理員的帳號**。

**因此本元件的條件式更新以該欄位為套用標記**：

- **更新條件** —— 該欄位為空或等於種子的系統識別字（代表該列從未被人動過）
- **更新後** —— 把該欄位標記為本補丁的專屬識別字，使後續啟動可判定「已套用過」而跳過
- **管理員撤銷後** —— 該欄位為管理員帳號，不符更新條件，**撤銷得以保留**

這個做法**零新表、零新 DDL、零額外的部署資產同步義務**。初版要求的「新增一張標記表」會觸發 requirements C-4 對「新增表」的 blocking 同步義務（且本元件的同步義務原本只涵蓋權限 seed 的語意變更，未涵蓋新表），並需要另一個補丁負責建表 —— 在既有欄位已足夠的前提下，那是不必要的成本。

**已知限制**：既有的權限重置端點（管理員可呼叫）會刪光整張權限表並以種子重寫，該操作會一併抹除本補丁的標記與管理員的所有調整。這不是本元件引入的行為，但代表「管理員的撤銷得以保留」的保證只在不觸發該端點的前提下成立。

### 既有權限種子的三個呼叫端（iteration 3 Finding m2）

本元件的設計以「種子只在啟動期執行」為前提，但實測該種子函式有**三個**呼叫端，其中兩個在請求路徑上：

| 呼叫端 | 模式 | 對本元件的意義 |
|---|---|---|
| 啟動流程 | 非強制（空表才寫） | 本元件緊接其後執行 |
| 公開的角色目錄端點（未認證） | 非強制（空表才寫） | 空表的種子行為可在啟動後被外部觸發；本次不致出錯（種子預設值已改為開啟），但不在本設計描述的時序模型內 |
| 權限重置端點（管理員） | **強制**（刪光重寫） | 上述「已知限制」的來源 |

第三項同時說明了 `decisions.md` AD-7 否決的「重跑種子強制模式」**並非假想的替代方案，它已是線上既有的管理員端點** —— 否決的是「把它用作本次變更的套用手段」，不是它的存在。

### FR-4.3 的一致性檢查落點（iteration 2 Finding N5）

requirements FR-4.3 要求兩處預設值同步，「任一處未同步即視為未完成」。初版只寫「需有明確的一致性檢查落點」而未指定是什麼 —— 那是空指標。

**同時必須揭露一項既有事實**：種子資料模組的檔頭寫著「由初始化腳本產生（勿手改；改腳本後重跑產生腳本）」，但**該產生腳本不存在於 repo**（codekb 已將此登錄為風險項，緩解欄為「無」）。因此「兩處同步」既沒有工具，也沒有驗證方式。

**本設計的處置**：

1. **修改方式** —— 本 intent 以**手動修改**同步兩處，並在 PR 說明中記載「種子資料模組檔頭的『勿手改』契約已失效（產生腳本不存在）」，使後續維護者不被誤導
2. **一致性檢查落點** —— 新增一支測試，比對種子資料模組的預設矩陣與初始化腳本中的對應內容（至少涵蓋本次變更的那一列，能涵蓋全部 308 列更好）。放進既有的後端測試目錄即被現有測試指令撿到，零新依賴
3. 若 Construction 判定第 2 項超出本 intent 範圍，須明寫 FR-4.3 的驗收**以人工核對承接**，並登錄為已知限制 —— 不得留白

**為何是目標式更新而非重跑種子**：重跑種子（強制模式）會刪光整張權限表再重寫，那正是 requirements C-3 要避免的重置。目標式更新只影響一列，管理員在介面上對其他角色所做的調整完全不受影響。設計理由與替代方案見 `decisions.md` AD-7。

**邊界與所有權**：
- **擁有**：該筆權限預設值的兩處同步、既有環境的套用機制
- **不擁有**：權限**機制**本身（既有的端點層檢查，不改）、欄位級授權（requirements FR-4.2 已定不做）

**已知的授權範圍外溢**：該功能識別碼的檢視權限同時開啟使用者清單與授權申請清單兩個端點。此範圍已在 requirements FR-4 與 stories AC-3.5 經人工確認為可接受，**非缺陷**，本站不再處理。

**稽核記錄的易失性**（requirements C-7 約束）：權限變更的稽核記錄保存期約等於兩次部署間隔。本 intent 不修復，記為已知限制。

---

## 元件與需求的對應

> iteration 1 Finding 7：初版此表漏列 11 項需求且無缺口聲明。本表現為**全覆蓋**，包含刻意不由本站承載的項目與理由。

### 功能需求

| 需求 | 承載元件 | 說明 |
|---|---|---|
| FR-1.1 記錄活動時間 | C-2、C-3 | C-2 的提交契約是此需求成立的前提 |
| FR-1.2 只保留最後一次 | C-3 | 單一欄位覆寫 |
| FR-1.3 5 分鐘節流 | C-1（規則）、C-2（執行） | |
| FR-1.4 保留擴充歷史的路徑 | C-3 | **設計期判定：符合**（判定理由見 C-3） |
| FR-2.1 顯示欄位 | C-4、C-5、C-6 | |
| FR-2.2 絕對時間格式 | C-5 | 格式已由 refined-mockups 定案 |
| FR-2.3 無紀錄不套用逾期標示 | C-1（語意）、C-4（輸出保證） | C-1 保證無紀錄時逾期必為否 |
| FR-2.4 可聚焦破折號與說明 | C-5 | 呈現規格已由 refined-mockups 定案 |
| FR-2.5 **所有**回傳使用者物件的端點 | **C-4** | iteration 2 補；三個構造點皆為其邊界 |
| FR-3.1 90 天逾期標示 | C-1（規則）、C-4（輸出）、C-5（呈現） | |
| FR-3.2 非僅色彩傳達 | C-5 | 圖示與文字替代已由 refined-mockups 定案 |
| FR-3.3 門檻固定不可設定 | C-1 | 門檻為常數，無設定介面 —— 需求即為 Won't Have |
| FR-4.1 取得檢視權限 | **C-7** | iteration 2 補 |
| FR-4.2 不做欄位級控制 | C-4（明示不做） | Won't Have；C-4 不做欄位級判斷是正確的 |
| FR-4.3 兩處預設值同步 | **C-7** | iteration 2 補 |
| FR-5.1 小螢幕卡片佈局 | C-6 | 斷點值已由 refined-mockups 定案 |
| FR-5.2 兩種佈局標示一致 | C-5、C-6 | C-5 不分佈局，天然一致 |
| FR-5.3 既有功能在卡片下可用 | C-6 | 觸控目標尺寸已由 refined-mockups 定案 |

### 非功能需求

| 需求 | 承載元件 | 說明 |
|---|---|---|
| NFR-1 效能 | C-1、C-2 | 節流即為其驗收條件；成本分析見 `services.md` |
| NFR-2 無障礙 | C-5、C-6 | 已由 refined-mockups 的可及性檢核表承載，本站不重複設計 |
| NFR-3 安全（ADR-0006 四面向） | **C-7**（IAM 面向） | 四面向的逐項判定已在 requirements 完成；本站的落點是權限變更本身 |
| NFR-4 授權雙向測試 | **C-7** | iteration 2 補；team-practices 規則 A 同此 |
| NFR-5 端點需測試客戶端測試 | C-4 | 涵蓋 FR-2.5 的三個構造點；team-practices 規則 B |
| NFR-6 前端 e2e 斷言 | C-6 | team-practices 規則 C |
| NFR-7 既有功能不得退化 | C-6 | **本站不承載具體驗證**，屬測試策略／交付規劃階段（見下方缺口聲明） |

### 約束

| 約束 | 承載元件 |
|---|---|
| requirements C-1 系統無既有活動紀錄 | C-3（欄位可為空）、C-5（無紀錄態呈現） |
| requirements C-2 無遷移框架，須重啟生效 | C-3（明訂部署後須重啟） |
| requirements C-3 禁止重跑整份腳本 | C-3、C-7（兩者皆採目標式、不重跑） |
| requirements C-4 部署資產同步（blocking） | C-3、C-7 |
| requirements C-5 帶時區時間戳慣例 | C-1（時區契約）、C-3（欄位型別） |
| requirements C-6 前端抓取形狀受 lint 約束 | C-6（不需額外資料源，自動滿足） |
| requirements C-7 稽核記錄易失 | C-7（記為已知限制，不修復） |
| requirements C-8 production 不在範圍 | 全體（僅及自有 staging） |

### 使用者故事

| 故事 | 承載元件 |
|---|---|
| US-1 稽核者檢視最後活動時間 | C-2、C-3、C-4、C-5、C-6 |
| US-2 無紀錄與逾期的辨識 | C-1、C-4、C-5 |
| US-3 `Security_Reviewer` 權限開通 | **C-7** |
| US-4 活動時間的記錄行為 | C-1、C-2、C-3 |

> iteration 1 Finding 5：初版使用 `S-1`〜`S-4` 為不存在的識別碼，已全數更正為 `US-1`〜`US-4`。

### 本站刻意不承載的項目

| 項目 | 理由 |
|---|---|
| NFR-7 的具體回歸驗證設計 | 屬測試策略／Build and Test；本站只指出 C-6 為受影響面。此缺口自 refined-mockups 起即已知並持續追蹤 |
| NFR-2 的對比度實測 | refined-mockups 的可及性檢核表已列為上線前必驗項，非設計期可完成 |
| 各需求的測試案例設計 | team-practices 已定規則 A／B／C 三項底線，個案設計屬下游 |
| 詳細業務邏輯表述 | 屬 Functional Design；本站只定介面形狀 |

---

## Review — Iteration 4

**Reviewer**: aidlc-architecture-reviewer-agent · Iteration 4（最終驗證輪）
**Date**: 2026-08-09T05:01:55Z
**Verdict**: **READY**（0 Critical、1 Major、2 Minor）

本輪範圍限定兩件事：逐條驗收 iteration 3 的 M1／M2／m1／m2／m3，以及確認修訂未引入新問題。不重審 iteration 1、2 已驗收通過的項目，不對已定案的設計決策提替代方案。

**結論先行**：M1 選定的機制（以 `role_permissions.updated_by` 作為套用標記）經回 repo 逐條實測，**三條寫入路徑確實互斥、欄位長度充足、NULL 與 `system_seed` 的路徑差異不造成問題**。但這個機制有**一個死角**：它實際實作的謂詞比設計自己寫下的契約句窄，在一個可達的狀態上會靜默不套用，而 M2 新增的三態記錄恰好把該狀態歸進「正常」那一格。見新發現 M1-a。

### Iteration 3 findings 驗收

| # | 原嚴重度 | 判定 | 說明 |
|---|---|---|---|
| M1 | **Major** | **已修正（機制成立），但新謂詞有死角** | 「新增標記表」已全數移除，改採既有 `updated_by` 欄位（`components.md` L236-246、`component-methods.md` L286-296、`decisions.md` L263）。新表所觸發的三項未承載成本（requirements C-4 blocking 同步、建表路徑無擁有元件、`services.md`／`component-dependency.md` 清單未更新）因方案改變而全部消滅，不再是缺口。**機制的可行性經實測成立**（見下方逐條核對），但更新謂詞與契約句不等價 —— 見新發現 **M1-a** |
| M2 | **Major** | **已修正（實質），一處未同步** | 兩項建議皆落地：①`services.md` L97 的處置欄已改為「**在既有測試路徑上無自動化驗證**；以啟動日誌的三態記錄 + 部署後人工核對承接」，L129-131 另加涵蓋邊界段落，明寫「把 C-7 整個刪掉，該測試照樣通過」；②三態可觀察性已寫進契約（`component-methods.md` L270-272 契約第 4 項、L298-302 §為何需要三態記錄、L304-308 §驗證缺口），`decisions.md` L280 亦列為「必須揭露的後果」第 2 項。與 `decisions.md` L275「執行順序成為隱性契約」的自相矛盾已消除。**殘留**：本檔（primary artifact）的 C-7 組成第 3 項仍只寫「雙向測試」而無涵蓋邊界註記，三態要求亦未寫入本檔 —— 見新發現 **m4** |
| m1 | Minor | **已修正** | 本檔 L234 的粗體契約句已改為「僅在該列**尚未被本補丁套用過**時才更新」，與 `component-methods.md` L268 逐字同一個謂詞；「值等於舊預設」已降為 L236 的推演中間步驟。兩份檔案的規範句不再分歧。（附帶說明：這個對齊本身是 M1-a 得以被看見的原因 —— 對齊後的契約句與 L240 的實作謂詞落差變得可直接比對） |
| m2 | Minor | **已修正** | 本檔新增 §既有權限種子的三個呼叫端（L248-258），以表格列出三個呼叫端、模式與對本元件的意義；`decisions.md` L286 的替代方案 B 已加註「此模式**並非假想方案，它已是線上既有的管理員端點**；否決的是把它用作本次變更的套用手段，不是它的存在」。`component-dependency.md` L148 的共用資源列亦已載明重置端點會抹除標記。三個呼叫端經實測與文件描述一致：`database.py:106`（啟動，`force=False`）、`user_router.py:286`（`GET /roles/catalog`，**確認無任何認證 Depends，為公開端點**，`force=False`）、`user_router.py:824`（`POST /role-permissions/reset-defaults`，`force=True`） |
| m3 | Minor | **未處置，如實留存** | `component-methods.md` L26 的收斂方式仍是靜默補時區，無 warning。iteration 3 已判定「隨設計帶入 Construction」，本輪確認該狀態未變、亦未被錯誤宣稱為已修正。**但它目前只存在於本檔的 review 表中，未進入任何 artifact 的 Construction 承接清單** —— 已補列於本輪 Summary 的殘留事項，不另計為新 finding |

#### M1 機制的回 repo 實測（逐條核對）

| 設計主張 | 實測結果 | 判定 |
|---|---|---|
| `updated_by` 存在且可為空、長度 `String(128)` | `backend/models.py:171` `updated_by = Column(String(128), nullable=True)`；`schema_rbac.sql:168` `updated_by VARCHAR(128)` | **成立**。補丁識別字（如 `last_activity_patch`）遠低於 128，長度非瓶頸 |
| 路徑一：Python 種子寫入固定系統識別字 | `backend/services/rbac.py:76` `updated_by="system_seed"`（全 repo 僅此一處出現該字串） | **成立** |
| 路徑二：初始化腳本寫入為空 | `schema_rbac.sql:180` 的 INSERT 欄位清單為 `(role, story_id, can_view, can_edit, can_review)`，**未給 `updated_by`** → 該欄為 NULL | **成立** |
| 路徑三：管理員經管理介面調整寫入帳號 | `user_router.py:786`（新增分支）與 `:793`（更新分支）皆為 `updated_by=admin_user.username` | **成立** |
| 三條路徑互斥、無第四個寫入者 | 全 repo `RolePermission(...)` 構造僅 `rbac.py:70` 與 `user_router.py:780` 兩處；`backend/` 內對該欄的賦值僅上述三處（`user_router.py:727`／`:813` 為讀出至回應，`lens_*` 的同名欄位屬另一張表） | **成立**。無遺漏的寫入者 |
| NULL（SQL 路徑）與 `system_seed`（Python 路徑）的差異不造成問題 | 更新條件同時接受兩者，兩條新建路徑收斂到同一結果；且 **staging 級環境的基線正是 NULL** —— `deploy/docker-compose.deploy.yml:23` 與 `deploy/docker-compose.test.yml:21` 皆把 `schema_rbac.sql` 掛入 `/docker-entrypoint-initdb.d`，故該環境 308 列的 `updated_by` 全為 NULL，謂詞在目標環境上會命中 | **不造成問題**。此為對 M1 機制**有利**的實測結果 |
| 標記寫入不會污染既有的 `updated_by` 語意呈現 | 該欄雖經 `user_router.py:727`／`:813` 回傳至前端，但 `frontend/src/` 全樹無任何 `updated_by` 參照，`RolePermissionsPage.tsx` 不顯示該欄 | **無 UI 副作用**。可放心以補丁識別字覆寫 |
| 標記為單列而非整份矩陣 | `RolePermissionsPage.tsx` 的 `handleSave` 以 `Object.values(dirty)` 組 payload，**只送被改動的格子**，故 `updated_by` 是逐格的，不會因管理員改任一格而蓋滿 308 列 | **成立**。這正是 M1-a 未升為 Critical 的原因 |

### 新發現

| # | 嚴重度 | 檔案 | 問題 | 建議修正 |
|---|---|---|---|---|
| M1-a | **Major** | components.md L234 vs L240；component-methods.md L268 vs L292；L270-272 | **更新謂詞比契約句窄一格，而 M2 的三態記錄把落差歸進「正常」那一格。** 契約句（本檔 L234、`component-methods.md` L268）是「僅在該列**尚未被本補丁套用過**時才更新」；實作謂詞（本檔 L240、`component-methods.md` L292）是「`updated_by` 為空或等於 `system_seed`」，本檔 L240 的括號自己譯得很準確 ——「代表該列**從未被人動過**」。兩者只在一個狀態上分歧：**目標列在本次部署之前就已被管理員經 `PUT /role-permissions` 動過**（不必是撤銷 `can_view`；在同一格上調整 `can_edit`／`can_review`，或曾授予後又收回，都會把 `updated_by` 寫成管理員帳號 —— `user_router.py:793` 是整列賦值，不分欄位）。此時 `updated_by` 既非 NULL 也非 `system_seed` → C-7 **永不套用** → FR-4.1／US-3／AC-3.4 在**正是 C-7 為之而生的既有環境上**靜默落空。<br><br>這是本輪修訂**新引入**的失敗路徑：iteration 3 的「新增標記表」方案在標記缺席時會照常套用（只是會覆寫管理員的設定一次），不存在此死角。更關鍵的是它與 M2 的修正互相抵銷 —— `component-methods.md` L270-271 把跳過態定義為「已跳過（**已套用過或已被管理員調整**）」，兩者合為一格，因此設計新加的唯一執行期訊號，在這條失敗路徑上會如實報「已跳過」，讀日誌的人無從分辨「本來就不用做」與「該做卻做不成」。三態中被設計為警示的只有「未命中目標列」，而本情境**命中了目標列**，不會落進那一態。<br><br>可達性：`RolePermissionsPage` 是線上運作中的 J3b 管理頁，`Security_Reviewer × J3a` 是一個可被點選的格子；設計無從斷言 staging 上該格從未被點過。未升為 Critical 的理由有二：①標記是逐格的（見上表末列），影響面限於該格而非整份矩陣；②`services.md` L131 ②已要求「部署後人工核對該角色確實能進入管理頁」，那道人工關卡會攔下它 —— 但那使 C-7 的自動生效承諾（`decisions.md` L268「不依賴人工步驟」）在此路徑上不成立 | 兩處小改即可：①把跳過態**拆為兩態** —— 「已跳過（本補丁已套用）」與「**未套用：該列已被管理員異動（`updated_by`=<值>）**」，後者須與「未命中目標列」同等級地標示為需人工處置，並明確接上 `services.md` L131 ② 的部署後核對；②在本檔 L234 的契約句加一句限定，如實寫明本謂詞實際涵蓋的是「從未被人動過」，使契約句不再比實作寬。不建議改謂詞去覆蓋該情境（覆寫管理員的既有調整正是 AD-7 否決替代方案 B 的理由） |
| m4 | Minor | components.md L202-206（C-7 組成） | **M2 的修正未同步到 primary artifact。** `services.md` 與 `component-methods.md` 都已載明「NFR-4 雙向測試不涵蓋 C-7 在既有環境的套用」與三態可觀察性要求，但本檔的 C-7 組成第 3 項仍是「**雙向測試** —— requirements NFR-4 要求授權矩陣變更需有 allow/deny 雙向測試……」，無任何涵蓋邊界註記，本檔全文亦無「三態」二字。只讀本檔 C-7 段落的開發者，會得到「C-7 有測試涵蓋、無額外可觀察性義務」的結論 —— 那正是 M2 判定為錯的那個結論。iteration 3 的 M2 Location 欄已點名本檔 L205，本輪未落地 | C-7 組成第 3 項加一句涵蓋邊界（「此測試涵蓋的是種子預設值變更，**不涵蓋既有環境的套用**，後者見 `services.md`」），並把三態可觀察性列為 C-7 的第 4 項組成，與 `component-methods.md` 契約第 4 項對齊 |
| m5 | Minor | components.md L238-244；component-methods.md L292-294 | **標記方案不可組合，且識別字的唯一性未被任何約束保證。** ①C-7 套用後把 `updated_by` 寫成本補丁識別字，該值既非 NULL 也非 `system_seed`；日後若有第二支同形狀的啟動期補丁需要動到**同一列**，沿用同一謂詞會被 C-7 的標記擋住。`decisions.md` L273 自己已預期「啟動流程再多一個補丁函式，長期累積」，而本專案無 migration 框架，這種累積是既定路徑，不是假想。②識別字的取值空間與使用者帳號共用同一個欄位，而 `models.py:26` 的 `username` 是**無長度上限、無格式約束**的 `String`（`user_router.py:291` 僅做 `strip().lower()`），因此「帳號名稱恰為 `system_seed` 或恰為本補丁識別字」在結構上未被禁止；前者會使該管理員的調整被誤判為種子值而遭覆寫。實務機率極低，但這是設計選擇把兩種語意塞進同一欄位所換來的代價，應被記下而非默認 | 在 C-7 註明：①接受清單的正式定義為「NULL ∪ `system_seed` ∪ 既往補丁識別字集合」，或明訂本形狀為**每列單次使用**、後續補丁需另擇機制；②補丁識別字選用不可能成為帳號的字面值（例如含空白或冒號），並在 Construction 一併確認 |

### Summary

**iteration 3 的五條 findings 全部處理到位**：M1 換掉新表方案、M2 兩項建議皆落地、m1 的謂詞已對齊、m2 的三個呼叫端已揭露且 AD-7 替代方案 B 已加註「已是線上端點」、m3 如實維持未處置。M1 選定的 `updated_by` 機制**經回 repo 實測確認可行**：三條寫入路徑互斥無遺漏（`rbac.py:76` / `schema_rbac.sql:180` / `user_router.py:786`、`:793`），`String(128)` 長度充足，NULL 與 `system_seed` 的路徑差異不但不造成問題，實測還顯示 staging 級環境（`deploy/docker-compose.deploy.yml:23` 掛載初始化腳本）的基線正是 NULL，謂詞會在目標環境命中；標記逐格而非整份矩陣（前端只送 dirty 格）；該欄不被前端顯示，覆寫無 UI 副作用。**新表方案原本未被承載的三項成本（C-4 blocking 同步、建表路徑、兩份清單）隨方案改變一併消滅。**

**唯一的 Major 是這個機制的死角，而它恰好被 M2 的修正遮住。** 更新謂詞實際是「從未被人動過」，比契約句「尚未被本補丁套用過」窄一格；差在「該列在本次部署前已被管理員動過」這個可達狀態上 —— `user_router.py:793` 是整列賦值，所以連調整 `can_edit` 都會留下管理員帳號。落在該狀態時 C-7 永不套用，US-3 靜默落空，而三態日誌會報「已跳過」（設計把「已套用過」與「已被管理員調整」合為一格），設計新加的唯一執行期訊號在這條路徑上讀起來完全正常。修法很便宜：把跳過態拆成兩態，並讓「未套用：該列已被管理員異動」與「未命中目標列」同級告警。這不阻擋 READY —— `services.md` L131 ② 的部署後人工核對是既有的攔截點，且影響面限於單一格。

依 verdict 規則（0 Critical、1 Major）判定 **READY**。開發者依這五份文件可以實作出正確的東西，不需要回頭問架構師。

**帶入 Construction 的殘留事項**：

1. **M1-a（Major）** —— C-7 跳過態拆為「已套用過」與「未套用：該列已被管理員異動」，後者須觸發 `services.md` L131 ② 的人工核對動作項；本檔 L234 契約句補上謂詞的實際涵蓋範圍。
2. **m4（Minor）** —— 本檔 C-7 組成同步 M2 的涵蓋邊界註記與三態要求。
3. **m5（Minor）** —— 標記接受清單的正式定義（含既往補丁識別字）或明訂每列單次使用；補丁識別字選用不可能成為帳號的字面值。
4. **m3（Minor，自 iteration 2 起未處置）** —— 時區正規化吸收 naive 值時無 warning（`component-methods.md` L26）；可與 M1-a 的可觀察性一併以同一形狀處理。
5. **C-7 的交易語意未寫進契約**（本輪不計為 finding）—— 既有 `_ensure_*` 先例皆以 `with engine.begin() as conn:` 執行（自動提交），沿用即正確；但 `SessionLocal` 為 `autocommit=False`，若 Construction 改用 `init_db()` 的既有 session 而未自行提交，寫入會在 `finally: db.close()` 被丟棄 —— 與 C-2 同型的風險，C-2 已明訂為契約、C-7 未訂。實作時擇一並寫明。
6. **FR-4.3 一致性檢查測試**（本檔 L269 第②項）—— 若判定超出本 intent 範圍，須依 L270 第③項明寫以人工核對承接，不得留白。

---

## Review — Iteration 3

**Reviewer**: aidlc-architecture-reviewer-agent · Iteration 3（驗證輪）
**Date**: 2026-08-09T04:51:29Z
**Verdict**: **READY**（0 Critical、2 Major、3 Minor）

本輪為**驗證輪**，範圍限定兩件事：逐條驗收 iteration 2 的 N1〜N8，以及檢查本輪修正是否引入新問題。不重審 iteration 1 已驗收通過的項目，不對 AD-1〜AD-3 的問答定案提替代方案。

N1（Critical）的新契約經回 repo 實測（`backend/database.py`、`backend/services/rbac.py`、`backend/services/rbac_seed_data.py`、`backend/services/user_router.py`、`backend/models.py`、`backend/tests/helpers.py`、`schema_rbac.sql`、`docker-compose.yml`、`deploy/docker-compose.*.yml`）確認**在三種情境下皆正確**，且未發現新的死角。阻擋不了 READY，但下游必須帶走的是 N4 的修正方式本身 —— **套用標記的成本確實被低估，且設計未察覺既有 schema 上已有等價的區分手段**。

### Iteration 2 findings 驗收

| # | 原嚴重度 | 判定 | 說明 |
|---|---|---|---|
| N1 | **Critical** | **已修正（契約正確）** | 三項全部落地且五份 artifact 表述一致：①執行順序釘死為「權限種子之後」（`components.md` L223、`component-methods.md` L264、`component-dependency.md` L48／L91／L128、`services.md` L49／L53、`decisions.md` L261）；②「只更新、不插入」明確（同上六處）；③「不存在時插入／UPSERT」的規範性表述**已完全移除** —— 全文僅存於「為何排除該分支」的歷史敘述中（`components.md` L209／L213／L226、`component-methods.md` L277／L281）。**契約本身經實測驗證為正確**，見下方三情境逐項核對 |
| N2 | Major | **已修正** | `components.md` L127-135 與 `component-methods.md` L175-183 兩表同步更正為「三處全部手寫具名引數、風險皆為高」，並刪除「隨查詢結果序列化／低」的表述。與 `user_router.py:451`（`list_users` 同為手寫具名引數）及 stories US-1 DoD 的「使用者清單端點」點名一致 |
| N3 | Major | **已修正** | `components.md` L114-125 已定義「使用者物件」＝ Admin 使用者管理清單的列模型，並以表格逐一列出四個被排除的端點與排除理由，另加「若日後擴及這些端點屬新的範圍決定」的邊界宣告。NFR-5 的測試範圍因此二元可判（三個構造點，非七個端點） |
| N4 | Major | **已修正，但修正手段的成本被低估** | 「一次性／可重複執行」的互斥表述已刪除，改為「條件式更新 + 套用標記」，並把「改採無條件回寫 → 此權限無法經管理介面永久撤銷」列為 requirements NFR-3（IAM 面向）的必須揭露後果（`decisions.md` L277）。**機制可行性成立**（新表或等價機制皆可實作），但成本與必要性的論證不完整 —— 見新發現 M1 |
| N5 | Major | **已修正** | `components.md` §FR-4.3 一致性檢查落點與 `component-methods.md` L291-295 已給出三段式處置：①手動同步兩處並在 PR 說明記載「勿手改」檔頭契約已失效；②新增比對兩處預設值的測試（零新依賴）；③若②超出範圍須明寫以人工核對承接並登錄為已知限制。空指標已消除 |
| N6 | Minor | **已修正（三項全部）** | ①`component-dependency.md` L72-74 已改為可逐格核對的無循環證明（四個 sink＋單向 C-6→C-4），並記明原「上三角全空」論據無效；②`component-methods.md` L317 的 C-7 對內依賴已改為「無（與 C-3 分屬不同資料表）」，與矩陣一致；③`services.md` L28 已改為「三個新**後端**元件」並補註元件清單標為新增者共四個 |
| N7 | Minor | **部分修正** | ①**已修正**：`component-methods.md` L193 已補「序列化前亦須套用同一正規化」，使「回應一律為 UTC」在 SQLite 測試與 PostgreSQL 生產兩條路徑上都成立。②**未修正**：正規化發生時不記 warning 的問題未處置（`component-methods.md` L26 的收斂方式仍是靜默補時區）。屬 Minor，不阻擋，隨設計帶入 Construction |
| N8 | Minor | **已修正** | 「ORM 自動轉換」分支已從契約中刪除，`component-methods.md` L185-189 僅保留「選項一：不設可靜默通過的預設值」與「選項二：共用工廠函式」，並在括號內記明自動轉換不可行的理由（`is_overdue` 為衍生值、模型層 property 會與 C-1 的參數化設計衝突）。`components.md` L142 同步 |

#### N1 契約的三情境逐項核對（實測）

既有初始化流程順序經 `backend/database.py` 實測確認為：`create_all`（L40）→ 三個補欄補丁（L42-44）→ 使用者種子（L49-101）→ `ensure_role_permissions_seeded(db, force=False)`（L106）。C-7 置於 L106 之後、只更新不插入、條件式套用時：

| 情境 | 實際行為 | 判定 |
|---|---|---|
| （a）全新空庫（Python 種子路徑，repo 根目錄編排檔未掛載初始化腳本 —— 已核對 `docker-compose.yml` 無 initdb 掛載） | 種子先寫入 308 列（種子資料本次已改為開啟）→ C-7 見表非空且該列已為開啟 → 無實質變更 | **正確**。iteration 2 揭露的「308 列全滅」路徑已封死 |
| （b）既有庫（staging） | 種子函式因表非空直接返回 0 → C-7 對該列執行目標式更新 → 權限生效 | **正確**。這正是 stories AC-3.4 要求的生效路徑 |
| （c）測試（in-memory SQLite） | `backend/tests/helpers.py:32` 以 `force=True` 直接建矩陣、從不呼叫 `init_db()` → C-7 在測試路徑上不執行 | **行為正確**（不會誤觸），但衍生一個驗證缺口 —— 見新發現 M2 |

**未發現新的死角**：`Security_Reviewer × J3a` 這一列在任一已種子環境中必然存在（實測 `rbac_seed_data.py` 為 11 角色 × 28 story 的完整笛卡兒積 308 列，`schema_rbac.sql:467-477` 的 J3a 區塊同為 11 列），因此「只更新不插入」不會因該列缺席而落空。C-7 若以獨立連線執行，與 `init_db()` 的工作階段互不干擾；`ensure_role_permissions_seeded` 於返回前已提交（`rbac.py:78`），順序上可見。

### 新發現

| # | 嚴重度 | 檔案 | 問題 | 建議修正 |
|---|---|---|---|---|
| M1 | **Major** | components.md L240；component-methods.md L287-289；decisions.md L263、L277 | **「套用標記」被寫成二選一的昂貴分支，但既有 schema 上已存在等價且零成本的區分手段，設計未察覺；同時新表方案的實際成本未被承載。** 本檔的立論是「單看欄位值無法區分『從未套用』與『已套用後被管理員撤銷』，兩者都是關閉」—— 這對 `can_view` 單一欄位成立，但**該列不只有這個欄位**。實測 `models.py:171` 的 `role_permissions.updated_by`（`String(128)`，可為空）在三條路徑上有明確且互斥的取值：種子寫入為 `"system_seed"`（`rbac.py:76`）、`schema_rbac.sql:180` 的 INSERT 未給該欄故為 NULL、管理員經 `PUT /role-permissions` 調整時一律寫入管理員帳號（`user_router.py:786` 新增分支、`:793` 更新分支）。因此「該列是否曾被管理員動過」**已經是可判斷的事實**，條件式更新可寫成「僅當 `updated_by` 為 NULL 或 `system_seed` 時才更新，並於更新後標記為本補丁的識別字」—— 零新表、零新 DDL、零部署資產同步義務。<br><br>相對地，本檔選定的新表方案有三項未被任何元件承載的成本：①**新表觸發 requirements C-4 的 blocking 同步**（`project.md ## Mandated` 逐字把「新增表」列為觸發條件，且要求更新 `schema_rbac.sql` 檔頭涵蓋清單與 `DEPLOY.md` 的表格）—— 本檔的 C-7 同步義務只寫「權限 seed 的語意變更」，未涵蓋新表；②**新表自身的建立路徑無人承載** —— 既有庫需要另一個啟動補丁先建表才能讀取標記，`元件清單` 中無元件擁有它，`component-dependency.md` 的依賴矩陣與共用資源、`services.md` L23 的資料庫變更清單與「本 intent 不產生資料成長」的資料生命週期段落皆未提及；③本檔為「成本過高就改採無條件回寫」預留的退路，會把一個 ADR-0006 hard constraint 下的 IAM 後果（權限無法永久撤銷）變成 Construction 的預設落點 —— 而該取捨在有零成本第三選項的前提下並不成立 | 在 C-7 的條件式契約中補上第三個候選並要求 Construction 先評估它：以 `role_permissions` 既有的 `updated_by` 欄位作為套用標記（更新條件與更新後的標記值一併寫明）。若評估後仍選新表，必須同時補齊：新表的擁有元件、既有庫的建表路徑、requirements C-4 對「新增表」的 blocking 同步義務，以及 `services.md`／`component-dependency.md` 中受影響的三處清單 |
| M2 | **Major** | services.md L97；components.md L205（C-7 組成 3）；decisions.md L275 | **C-7 的套用結果既沒有能失敗的測試，也沒有執行期訊號 —— 而 `services.md` 宣稱它有。** `services.md` L97 把失敗模式「C-7 權限套用在啟動時失敗」的處置寫為「US-3 會靜默落空，**因此需有測試涵蓋（requirements NFR-4 的雙向測試）**」。實測該測試對此**恆真**：`backend/tests/helpers.py:32` 以 `ensure_role_permissions_seeded(db, force=True)` 直接由 `DEFAULT_ROLE_PERMISSIONS` 建矩陣，**從不呼叫 `init_db()`**，因此雙向測試驗證的是種子資料是否已改（FR-4.3 的一半），與 C-7 是否存在、順序是否正確、是否真的更新到既有庫**完全無關** —— C-7 整個刪掉，該測試照樣綠。這與 `decisions.md` L275 自己的誠實記載（「執行順序成為隱性契約 —— 它不會被型別系統或測試保護」）直接互相矛盾：一份說沒有保護，另一份說有測試涵蓋。<br><br>同一缺口的第二面是執行期無訊號：目標式 UPDATE 影響 0 列**不是例外**，沿用 C-3 先例的 `try/except` + `logger.warning` 形狀捕捉不到它。C-7 這個元件的存在理由就是「這件事會靜默落空」，而它自己的套用結果目前沒有任何可觀察的成功／跳過／未命中訊號，與本設計對 C-2 反覆援引的 construction 護欄「silent failures are not acceptable」不一致 | 兩處分別處理：①`services.md` L97 的處置欄如實改寫 —— 雙向測試涵蓋的是種子預設值變更，**不涵蓋既有環境的套用**；後者在現行測試路徑上無自動化驗證，須明寫以部署後人工核對承接並登錄為已知限制（比照 N5 第③項的處理方式）；②在 C-7 契約補一條可觀察性要求：套用時記錄「已套用／已跳過（已套用過或已被管理員調整）／**未命中目標列**」三態，使未命中成為可在啟動日誌上發現的事實 |
| m1 | Minor | components.md L234 | **條件式更新的規範句仍寫著被自己否決的謂詞。** L234 的粗體契約句為「僅在該列**仍等於舊的預設值（關閉）**時才更新為開啟」，緊接的三點推演正是為了證明這個謂詞不足，並在 L240 改要求套用標記；而 `component-methods.md` L268 的契約寫的是「僅在該列**尚未被本補丁套用過**時才更新」。兩份檔案的規範句是**不同的謂詞**，只讀 `components.md` L234 的開發者會實作被否決的那一個 | 把 L234 的粗體句改為最終謂詞（尚未被本補丁套用過），把「值等於舊預設」降為推演過程的中間步驟 |
| m2 | Minor | components.md L211、L216；decisions.md L281-282；component-dependency.md L124 | **設計把權限種子描述為只在啟動期執行的單一路徑，實際有三個呼叫端，其中兩個在請求路徑上。** 實測 `ensure_role_permissions_seeded` 的呼叫端為：`database.py:106`（啟動，`force=False`）、`user_router.py:286`（**公開未認證**的 `GET /roles/catalog`，`force=False`）、`user_router.py:824`（`POST /role-permissions/reset-defaults`，**`force=True`**，刪光整表重寫）。兩點影響：①空表的種子行為可在啟動之後、由一個公開端點觸發（本次不致出錯 —— 種子資料已改為開啟 —— 但它不在設計描述的時序模型內）；②`decisions.md` L281-282 把「重跑種子強制模式」寫成一個被否決的**假想替代方案**，未揭露它已是線上的管理員端點。這同時削弱 M1 中新表方案所買到的效益：管理員的撤銷本來就可被既有的重置端點抹除 | 在 C-7 的前提描述補上這三個呼叫端與各自的觸發條件；`decisions.md` AD-7 的替代方案 B 加註「該模式已存在於既有的重置端點」，使 gate 上的取捨基於完整事實 |
| m3 | Minor | component-methods.md L26 | N7 第②項未處置（正規化靜默吸收 naive 值，生產環境無訊號）。屬 iteration 2 未修的 Minor，如實記載，不重複論證 | 隨設計帶入 Construction；若採納 M2 的可觀察性建議，可一併以同一形狀處理 |

### Summary

**N1 這條 Critical 確實修好了，而且是修對的。** 新契約的三項（權限種子之後、只更新不插入、條件式套用）在五份 artifact 中表述一致，「不存在時插入」的規範性文字已完全移除；回 `backend/database.py` 與 `backend/services/rbac.py` 實測後，該契約在全新空庫、既有庫、SQLite 測試三種情境下行為皆正確，且目標列在任一已種子環境中必然存在（308 列為 11×28 的完整笛卡兒積），沒有「只更新不插入」會落空的新死角。N2／N3／N5／N6／N8 完全修正，N4 修正方向正確、N7 修一留一。

**兩項 Major 都不是「照做會壞」，而是「照做之後沒人知道成不成功」與「為此付了不必要的價」。** M2 是本輪最值得下游注意的一條：`services.md` 宣稱 C-7 的失敗有 NFR-4 雙向測試涵蓋，但測試輔助模組以 `force=True` 直接建矩陣、從不經過啟動流程，該測試對 C-7 恆真 —— 這與 `decisions.md` 自己承認「執行順序不會被測試保護」互相矛盾，等於在剛封死的靜默缺口旁邊留了一個宣稱有保護、實際沒有的標示。M1 則是本輪修正引入的成本：`role_permissions.updated_by` 已能區分「種子寫入」與「管理員調整」（`rbac.py:76` vs `user_router.py:786/793`），套用標記不必然要一張新表，而新表方案會觸發 requirements C-4 對「新增表」的 blocking 同步義務且目前無元件承載。

依 verdict 規則（0 Critical、2 Major）判定 **READY**：開發者依此文件實作不會做出錯誤的東西，剩下的是要帶著走的兩項 Major 與三項 Minor。建議在核可 gate 上先處理 M1 的第三選項評估 —— 它會直接影響「權限是否可被管理員永久撤銷」這個 ADR-0006 IAM 面向的結果。

---

## Review — Iteration 2

**Reviewer**: aidlc-architecture-reviewer-agent · Iteration 2（最終輪）
**Date**: 2026-08-09T04:37:02Z
**Verdict**: **NOT-READY**（1 Critical、4 Major、3 Minor）

本輪逐條驗收 iteration 1 的 12 個 findings，並回 repo 實測每一項修正宣稱（`backend/database.py`、`backend/main.py`、`backend/models.py`、`backend/services/rbac.py`、`backend/services/rbac_seed_data.py`、`backend/services/user_router.py`、`backend/services/auth.py`、`backend/services/collab_router.py`、`backend/tests/helpers.py`、`docker-compose.yml`、`deploy/docker-compose.deploy.yml`、`deploy/docker-compose.test.yml`、`schema_rbac.sql`、`frontend/src/pages/AdminPage.tsx`、`scripts/`），不採信文件的自我宣稱。

**12 條 findings 中 10 條完全修正、2 條部分修正**（Finding 1、2）。阻擋 READY 的不是舊 findings 的殘留，而是**修正本身引入的新問題** —— 集中在 iteration 2 新增的 C-7 上，其中一項會讓部分環境的整份 308 列權限矩陣消失。

### Iteration 1 findings 驗收

| # | 原嚴重度 | 判定 | 說明 |
|---|---|---|---|
| 1 | Critical | **部分修正** | C-4 職責已擴為「所有回傳使用者物件的端點」、三個構造點入表、`component-methods.md` 補上「不得設可靜默通過的預設值／改走單一轉換路徑」的二擇一契約 —— 這部分成立。但實測 `user_router.py:451` 的 `list_users` **同樣是手寫具名引數構造**（`UserSchema(id=…, username=…, role=…, is_active=…, authorization_status=…, requested_role=…)`），全 repo **零處使用 `from_orm`**；本檔卻把它記為「隨查詢結果序列化／風險低」（見新發現 N2）。另「所有回傳使用者物件的端點」未定義邊界，實際有第四、第五處（見 N3） |
| 2 | Critical | **部分修正** | C-7 已建立，問題形狀（兩處預設值皆為 `false`、`ensure_role_permissions_seeded` 僅空表寫入、requirements C-3 禁止重跑腳本）與 repo 實測**逐項相符**（`rbac_seed_data.py:299`、`schema_rbac.sql:475`、`rbac.py:58-66`）。UPSERT 機制在既有形狀下**可行** —— `models.py:163-164` 的 `role_permissions` 主鍵為複合鍵 `(role, story_id)`，`ON CONFLICT (role, story_id)` 或 ORM 讀改寫皆成立。但**啟動順序未定義**，而本檔指定的「形狀比照 C-3」會直接導向錯誤位置（見 N1 Critical）；FR-4.3 的一致性檢查落點仍是空指標（見 N5） |
| 3 | Critical | **已修正** | `component-methods.md` L102-120 已把 commit／rollback／不 close session 三點列為契約。**論證經實測驗證為真**：全 repo 的 `Depends()` 可呼叫者僅 5 種（`get_db` 40、`require_story_action` 24、`require_arch_action` 14、`get_current_user` 6、`security_bearer` 1），**無一對 session 寫入**；FastAPI 先解析 dependencies 再執行端點函式，故「在認證依賴階段 session 中無他人待決變更」成立。rollback 的必要性亦確認：`rbac.py:238` 的 `require_story_action._dep` → `user_can` → `get_permission_row` → `db.query()`，待復原狀態會直接拋錯。WebSocket 路徑（`collab_router.py:221`）確認完全無驗證，非「已認證但繞過」路徑 |
| 4 | Major | **已修正** | NFR-3 → C-7（IAM 面向）、NFR-4 → C-7（雙向測試），與 requirements L87-88 原文一致；「寫入失敗不影響原始請求」已在 `components.md` L81 與 `component-methods.md` L122-124 兩處如實標為本站設計判斷、無上游條文 |
| 5 | Major | **已修正** | 全域改為 US-1〜US-4；五份 artifact 中已無 `stories S-n` 殘留（僅 iteration 1 審查紀錄內留有歷史引用，屬正確保留）。US-1 的映射已補上寫入側（C-2、C-3） |
| 6 | Major | **已修正** | 同步義務（blocking）全部改引 requirements **C-4**；C-2（部署後須重啟）與 C-3（禁止重跑腳本）已在 `components.md` L98、`services.md` L51、`component-dependency.md` L125、`decisions.md` L121 獨立表述 |
| 7 | Major | **已修正** | 對應表覆蓋 FR-1.1〜FR-5.3、NFR-1〜NFR-7、requirements C-1〜C-8、US-1〜US-4，逐項比對無遺漏；FR-1.4 已有實質判定（單一可為空欄位覆寫不阻擋歷史表擴充）；另有「本站刻意不承載的項目」表 |
| 8 | Major | **已修正** | 時區契約已釘死為 tz-aware UTC、明令 `datetime.now(timezone.utc)`、禁用 `utcnow()`，並定義 naive 值一律視為 UTC 補時區。策略在兩種資料庫下皆正確：PostgreSQL（`deploy/docker-compose.deploy.yml` 未設 `TZ`，容器預設 UTC）回傳 aware，正規化為 no-op；SQLite 的 `DateTime(timezone=True)` 不保存 offset，而本設計所有寫入皆為 UTC，故「naive 即 UTC」的還原正確。殘留缺口見 N7（Minor） |
| 9 | Minor | **已修正** | `components.md` L83 與 `component-dependency.md` L146 已改為「最終值為後提交者的時刻，與較大值可能有次毫秒級偏差」，並明記初版「單調前進」為錯 |
| 10 | Minor | **已修正** | C-6 正規化契約已建立（`?? null` / `?? false`），與 `AdminPage.tsx:39-48` 的實況（手寫 `DbUser` interface、`await res.json()` 無驗證）相符 |
| 11 | Minor | **已修正** | AD-6 已補 `last_login_at`（語意錯誤）與 `last_seen_at`（無既有先例、與中文文件用語不對應）兩個具理由的替代方案 |
| 12 | Minor | **已修正** | `services.md` L71-78 已補上「提交後物件過期導致的一次使用者重讀」。`database.py:24` 的 `sessionmaker(autocommit=False, autoflush=False, bind=engine)` 確實未關閉 `expire_on_commit`（預設 True），論述成立 |

### 新發現

| # | 嚴重度 | 檔案 | 問題 | 建議修正 |
|---|---|---|---|---|
| N1 | **Critical** | component-methods.md L255-266（C-7 補丁契約）；components.md L189；component-dependency.md L52、L118-125；decisions.md L259 | **C-7 的啟動順序未定義，而本檔指定的「形狀比照 C-3 的補欄補丁」會直接導向會清空整份權限矩陣的位置。** 實測 `database.py` 的 `init_db()` 順序為：`create_all`（L40）→ `_ensure_a4_schema()`／`_ensure_j5_schema()`／`_ensure_a3_schema()`（L42-44）→ 使用者 seed → **`ensure_role_permissions_seeded(db, force=False)`（L106）**。C-3 的三個先例全部位於 L42-44，即**在權限 seed 之前**。若 C-7 依「形狀比照 C-3」置於同處，且依本檔契約「**該列不存在時插入**（UPSERT 語意）」執行，則在 `role_permissions` 為空的環境中：C-7 先插入 `(Security_Reviewer, J3a)` 一列 → `ensure_role_permissions_seeded` 的 `count > 0` 判定成立（`rbac.py:62-64`）→ **直接 return 0，308 列預設矩陣一列都不寫入** → 所有角色的 `get_permission_row` 皆回傳 `None` → `user_can` 恆為 False → **全系統 RBAC 端點盡數 403**。此情境**確實可達**：repo 根目錄的 `docker-compose.yml`（本機開發用）**沒有掛載 `schema_rbac.sql` 到 initdb**（只有 `deploy/docker-compose.deploy.yml:23` 與 `deploy/docker-compose.test.yml:21` 有），該路徑的權限矩陣完全依賴 Python seed。且**沒有任何測試會發現**：`backend/tests/helpers.py:32` 以 `ensure_role_permissions_seeded(db, force=True)` 直接建矩陣，從不經過 `init_db()` | 在 C-7 契約明訂兩件事：①**執行順序**：C-7 必須在 `ensure_role_permissions_seeded` **之後**執行（即 `init_db()` 的 L106 之後），不得與 C-3 的補欄補丁並列於 L42-44；②**空表行為**：C-7 為**只更新不插入**（或以「表非空」為前置守衛），空表時不動作、由既有 seed 負責。順帶刪除或改寫「該列不存在時插入（UPSERT 語意）」這句 —— 在既有 seed 已涵蓋該列的前提下，insert 分支沒有正當用途，只有製造上述故障的能力 |
| N2 | **Major** | components.md L114-120（C-4 三個構造點表）；component-methods.md L177-181 | **`list_users` 被記為「隨查詢結果序列化／風險低」，與程式碼及已核可上游同時矛盾。** 實測 `user_router.py:451-458`：`list_users` 同樣是**手寫具名引數**構造 `UserSchema(id=…, username=…, role=…, is_active=…, authorization_status=…, requested_role=…)`；`grep -rn "from_orm" backend/` 命中數為 **0**（`UserSchema` 雖有 `orm_mode = True`，但無任何呼叫端使用）。三個構造點的形式與風險**完全相同**，不存在「一個自動、兩個手寫」的分佈。同時，已核可的 `stories.md:121`（US-1 DoD）逐字寫「已知的高風險落點為**使用者清單端點**與兩個更新端點」—— 本檔把上游明列的高風險落點降級為「低」。實害：清單端點是 FR-2.1／FR-2.2／NFR-6 的**主要顯示路徑**，「低風險」標籤會把開發者的注意力從它身上移開 | 兩份檔案的表格同步更正：三個構造點皆標為「手寫具名引數」、風險皆為「高」，並刪除「隨查詢結果序列化」與「低」的表述。C-4 的二擇一契約本身不需改動（它已涵蓋三處），改的是事實陳述與風險標示 |
| N3 | **Major** | components.md L110、L114；component-methods.md L162、L175；services.md L116 | **「所有回傳使用者物件的端點」未定義邊界，而實際超出本檔列舉的三處。** 本檔宣稱「使用者物件的回應在三處被構造」，但實測至少還有四個端點回傳使用者物件：`GET /api/auth/me`（`user_router.py:380`，`MeResponse` 含 `id`／`username`／`role`／`is_active`／`authorization_status`）、`GET /api/collab/users`（`collab_router.py:242`，`[{"id","username","role"}]`）、`POST /register`／`POST /login`（`LoginResponse` 含 `username`／`role`／`authorization_status`）、`PUT /authorization-requests/{id}/approve`（`user_router.py:520`，`{"ok","username","role"}`）。requirements FR-2.5 的原文是「**所有**回傳使用者物件的端點」（其 AC 才收斂到 Admin 頁的兩個更新操作），stories US-1 DoD 亦寫「涵蓋**所有會回傳使用者物件的端點**」。本檔既宣稱涵蓋「所有」，又只列舉 `UserSchema` 的三處，且未給任何邊界判定 —— 下游無法判斷 NFR-5 的 `TestClient` 測試該涵蓋 3 個還是 7 個端點 | 在 C-4 明確定義「使用者物件」= `UserSchema`（Admin 使用者管理清單的列模型），並逐一列出被排除的端點（`/me`、`/collab/users`、`LoginResponse`、approve 回應）與排除理由（對照 FR-2.5 的 AC 與 refined-mockups 的消費端）。這是二元可判的邊界宣告，不是補充說明 |
| N4 | **Major** | component-methods.md L255-266、L268；components.md L189；decisions.md L266、L275-276 | **C-7 每次啟動都強制回寫該列，使管理員在 Admin UI 上的撤銷永久失效 —— 這與 AD-7 否決替代方案 B 的理由自相矛盾，且未被揭露。** C-7 契約寫「可重複執行 —— 多次啟動的結果相同」＋「存在時更新」，即**每次服務重啟都把 `Security_Reviewer × J3a` 的 `can_view` 強制設為 true**。實測 `user_router.py:733` 的 `PUT /role-permissions` 允許管理員調整任一列；若管理員日後刻意撤銷此權限，下一次部署重啟會**靜默回復**，且 requirements C-7 已載明該變更的稽核記錄為易失性 —— 撤銷會消失且無跡可循。AD-7 否決替代方案 B 的唯一理由正是「會覆寫管理員的全部調整…會靜默破壞既有設定」，而 C-7 對這一列做的正是同一件事。與 C-3 的類比在此失效：`ADD COLUMN IF NOT EXISTS` 冪等且**永不覆寫使用者資料**，權限 `UPDATE` 會。另契約同一句並存的「**一次性**、可重複執行」語意互斥，未定案 | 在 C-7 契約二擇一並寫明：①**一次性套用**（以標記表／條件式更新「僅在該列仍等於舊預設值 `false` 時才更新」實作），套用後管理員的撤銷得以保留；或②**每次啟動強制**，但必須把「此權限自此不可經 Admin UI 永久撤銷」列為 NFR-3（IAM 面向）的已知後果並在 gate 上明示。同時刪除「一次性、可重複執行」的並存表述，選定其一 |
| N5 | **Major** | components.md L188；component-methods.md L241-250；decisions.md L271 | **FR-4.3 的「一致性檢查落點」是空指標，且未揭露兩處來源的實際維護契約已失效。** 本檔寫「這是 requirements FR-4.3 的直接要求，**需有明確的一致性檢查落點**」，但五份 artifact 皆未指定該落點是什麼、由誰承載。更關鍵的是本檔未揭露一項本站上游 codekb 已記載的事實：`backend/services/rbac_seed_data.py` 的檔頭逐字寫「由 `schema_rbac.sql` 產生（**勿手改**；改 SQL 後重跑產生腳本）」，而 **`scripts/` 下只有 `validate_repo_contract.py`，該產生腳本不存在於 repo**（codekb `dependencies.md:185-186`／`component-inventory.md:39`／`code-quality-assessment.md` T3 皆已明載，並登錄為風險 R5「兩份 308 列可能漂移，無人察覺，緩解：無」）。結果：開發者被要求「兩處同步」，但其中一處的檔頭禁止手改並指向一支不存在的工具，而 FR-4.3 的 AC（「任一處未同步即視為未完成」）沒有任何可執行的驗證方式 | 在 C-7 明訂三件事：①兩處來源的修改程序（既然產生腳本不存在，就明寫「本 intent 以手改方式同步兩處，並在 PR 說明中記載 `rbac_seed_data.py` 檔頭的 `勿手改` 契約已失效」）；②FR-4.3 的一致性檢查落點 —— 建議為一支比對 `DEFAULT_ROLE_PERMISSIONS` 與 `schema_rbac.sql` 該列（或全 308 列）的測試，放進既有 `backend/tests/`；③若判定②超出本 intent 範圍，須明寫 FR-4.3 的 AC 在本設計下**以人工核對承接**，並登錄為已知限制 |
| N6 | Minor | component-dependency.md L73（依賴矩陣性質 2）；component-methods.md L288；services.md L28 | **三處跨檔／自我一致性瑕疵。** ①`component-dependency.md` L73 宣稱「矩陣的上三角（依 C-1→C-7 排序）全空，證明依賴關係是嚴格單向的」，但同頁矩陣的 **C-2 列 × C-3 欄為「寫入」**，正落在上三角 —— 結論（無循環）為真，但所引的證明**與自己印出的矩陣矛盾**。②`component-methods.md` L288 記 C-7 的對內依賴為「C-3（**同表不同欄位**，無程式碼依賴）」，與 `component-dependency.md` L75「操作同一個資料庫但**不同的表**」及「C-7 與其他元件零耦合」矛盾；事實上 C-3 動 `users`、C-7 動 `role_permissions`，是不同的表。③`services.md` L28 寫「本 intent 的**三個**新元件」，而 `components.md` 元件清單標為「新增」者有 **四個**（C-1、C-2、C-5、C-7），差在前端的 C-5 | ①改為正確的無循環證明：C-1／C-3／C-5／C-7 四列全空 ⇒ 皆為 sink；其餘 C-2／C-4／C-6 之間僅有 C-6→C-4 單向一條邊 ⇒ 無循環。②`component-methods.md` L288 改為「無依賴（與 C-3 分屬不同資料表）」，與矩陣一致。③`services.md` L28 補「後端」限定或改為四個 |
| N7 | Minor | component-methods.md L26（時區收斂方式）；components.md L141；component-methods.md L167、L202 | **時區正規化只落在 C-1 的兩個判定，未及序列化邊界；且正規化在生產環境會靜默誤解而非顯現。** ①C-4 宣告「回應一律為 UTC 時間戳」、C-5 的 prop 註為「ISO 8601 UTC」，但正規化契約只寫在 C-1 的兩個判定內；`last_activity_at` 從資料庫直通序列化，未經任何正規化。在 SQLite 測試路徑下讀回為 naive，序列化後**不帶 offset**（`"2026-08-09T04:00:00"`），若 NFR-5 的 `TestClient` 測試斷言 UTC 形式會失敗 —— 這正是 team-practices 規則 B 的首支測試。②「naive 一律視為 UTC」在生產若真的出現 naive 值（例如日後有人沿用 `auth.py:32` 的 `datetime.utcnow()` 寫入），會**靜默給出偏移的答案**，與 C-2 據以立論的 construction 護欄「silent failures are not acceptable」立場不一致 | ①在 C-4 補一句：序列化前 `last_activity_at` 亦套用同一正規化（naive → 補 UTC），使「回應一律為 UTC」在測試與生產兩條路徑上都成立；②在時區契約補一句：正規化發生時記錄一則 warning（沿用既有補丁的 `logger.warning` 形狀），使生產環境的 naive 值可被觀察而非靜默吸收 |
| N8 | Minor | component-methods.md L186（C-4 契約選項二） | **選項二的「自動轉換」分支對 `is_overdue` 不可行。** 契約寫「三個構造點改走單一的物件轉換路徑（**自動轉換**或共用工廠函式）」，但 `is_overdue` 依本設計是**衍生值不是儲存欄位**（同檔 L171），ORM 的 `User` 物件上不存在該屬性，`from_orm`／`from_attributes` 無從取值。要讓自動轉換成立，必須另在模型層加一個 property 並在其中自行取得當下時刻 —— 那會把「當下時刻由呼叫端傳入」這個 C-1 的核心測試性設計（同檔 L79-81）在邊界處重新藏回去。本檔未提及此附加條件，選項二的兩個分支被並列為等價可選 | 刪除「自動轉換」分支，只保留「共用工廠函式（接受 `user` 與 `now`，回傳回應物件）」；或保留但明寫其附加條件（需在模型層新增 property、且該 property 內部取用系統時鐘，與 C-1 的參數化設計相衝突） |

### Summary

**iteration 1 的 12 條 findings 有 10 條完全落地、2 條部分落地，且所有修正宣稱的事實基礎經回 repo 實測全部為真** —— 特別是 Finding 3 的交易論證（「在認證依賴階段 commit 是安全的」）經窮舉全 repo 五種 `Depends()` 可呼叫者後確認成立，Finding 8 的時區正規化策略在 PostgreSQL 與 SQLite 兩條路徑下亦皆正確。這一輪的修訂不是文字補丁，是實質的設計補強。

阻擋 READY 的是**修正本身引入的新問題**，集中在 iteration 2 新增的 C-7：

**N1（Critical）是唯一會讓下游實作出災難性錯誤的一條。** C-7 的契約同時要求「形狀比照 C-3 的補欄補丁」與「該列不存在時插入」，而 C-3 的三個先例全部位於 `init_db()` 的 L42-44 —— 在 `ensure_role_permissions_seeded`（L106）**之前**。照此實作，任何以 Python seed 初始化的環境（含 repo 根目錄 `docker-compose.yml` 起的本機開發庫）會因為 C-7 先插入一列而讓空表判定失效，**308 列預設權限矩陣一列都不會寫入，全系統 RBAC 端點盡數 403**，而 `backend/tests/helpers.py` 以 `force=True` 建矩陣，沒有任何測試會發現。修正成本極低（釘死執行順序 + 移除 insert 分支），但不修就是本 intent 從「權限沒生效」升級為「權限全毀」。

**N4／N5（Major）是 C-7 的另外兩個未定案處**：每次啟動強制回寫使該權限無法被管理員永久撤銷（與 AD-7 否決替代方案 B 的理由自相矛盾，且屬 NFR-3 的 IAM 面向後果）；FR-4.3 的一致性檢查落點仍是空指標，而 `rbac_seed_data.py` 檔頭指向的產生腳本經確認**不存在於 repo**（codekb 已登錄為風險 R5，緩解欄為「無」），使「兩處同步」既無工具也無驗證。**N2／N3（Major）** 則是 Finding 1 的殘留：清單端點被誤記為自動序列化且風險降級（與程式碼及 US-1 DoD 同時矛盾），以及「所有回傳使用者物件的端點」缺邊界定義（實際另有四個端點回傳使用者物件），使 NFR-5 的測試範圍無法判定。

三項 Minor（矩陣無循環的證明與自身矩陣矛盾、C-7 對內依賴的跨檔矛盾與事實錯誤、時區正規化未及序列化邊界）不影響設計判斷，但 N6 ① 值得注意：那是本檔宣稱「可驗證」的性質之一，卻經不起對照自己上方兩行的表格。

**修補路徑不需推翻任何已定案決策**：N1／N4 是在 C-7 契約內補兩句順序與冪等語意，N2／N3 是事實更正與邊界宣告，N5 是指定一個測試落點，三項 Minor 為文字對齊。建議在核可 gate 上優先處理 N1 —— 它是本輪唯一「照文件做就會壞、且 CI 全綠」的一條。

---

## Review — Iteration 1（歷史紀錄，findings 已於 iteration 2 修訂）

**Reviewer**: aidlc-architecture-reviewer-agent · Iteration 1
**Date**: 2026-08-09T04:07:19Z
**Verdict**: NOT-READY（3 Critical、5 Major、4 Minor）

本輪為對抗式審查：五份 artifact 逐份精讀後，回 repo 實測每一項事實主張（`backend/services/auth.py`、`backend/database.py`、`backend/models.py`、`backend/services/rbac.py`、`backend/services/rbac_seed_data.py`、`backend/services/user_router.py`、`backend/tests/helpers.py`、`backend/Dockerfile`、`deploy/docker-compose.deploy.yml`、`schema_rbac.sql`、`frontend/src/pages/AdminPage.tsx`），並逐條比對 requirements、stories、team-practices、interaction-spec 原文。**設計所引用的既有機制事實幾乎全部正確**（見末節），問題不在事實查證，而在**需求承載的缺口**與**引用編號的系統性錯置**。

### Findings

| # | 嚴重度 | 檔案 | 問題 | 建議修正 |
|---|---|---|---|---|
| 1 | **Critical** | components.md L84、L128-141；component-methods.md L118-131；services.md L23；component-dependency.md L128 | **FR-2.5／stories AC-1.5 完全無承載元件。** `FR-2.5`、`AC-1.5` 在五份 artifact 中出現次數為 **0**。C-4 被命名為「使用者清單序列化」，四份文件一致把它的範圍限定在**清單端點**（「既有的使用者清單回應」「使用者清單端點｜回應新增兩欄」）。但 FR-2.5 的原文是「**所有回傳使用者物件的端點**都必須包含此欄位」，stories US-1 DoD（L121）更逐字點名兩個高風險落點。實測 `user_router.py:603-609`（`update_user_active`）與 `:705-711`（`update_user_role`）皆以**手寫 `UserSchema(...)` 具名引數**構造回應、**未使用 `from_orm`**，且兩處**現行就已漏傳 `requested_role`**（`UserSchema` 有此欄位，兩處構造皆未給）。新欄位若只加進 `UserSchema` 而不改這兩個構造點：有預設值 → 回傳 `null`／`false`（複製既有缺陷，AC-1.5「而非因構造遺漏而缺失或為 `null`」直接失敗）；無預設值 → 兩個端點 500。FR-2.5 正是為了防止這件事而寫的需求，設計卻整條漏掉 | 將 C-4 的職責由「使用者清單序列化」擴為「使用者物件序列化」，明列三個構造點（`list_users:451`、`update_user_active:603`、`update_user_role:705`）為其邊界；在對應表補 FR-2.5 → C-4 一列；於 `component-methods.md` 註明兩欄在 `UserSchema` 上**不得**設可靜默通過的預設值，或改為單一 `from_orm`／工廠函式使三處不可能分歧 |
| 2 | **Critical** | components.md L96、L135、L140；component-dependency.md L94；services.md L88 | **FR-4／US-3（權限開通）無任何承載元件，且既有環境無套用路徑。** `FR-4.3`、`AC-3.3`、`AC-3.4` 在五份 artifact 中出現次數為 **0**。設計把 FR-4／S-3 映射到 C-4（序列化），並宣稱「既有的權限檢查決定該請求是否被允許 —— **本 intent 不改變此機制**」。但本 intent 確實要改權限**資料**：實測 `rbac_seed_data.py:299` 與 `schema_rbac.sql:475` 皆為 `('Security_Reviewer', 'J3a', false, false, false)`，兩處都必須翻轉（FR-4.3／AC-3.3）。更關鍵：`rbac.py:58-66` 的 `ensure_role_permissions_seeded(db, force=False)` **僅在 `role_permissions` 為空表時寫入**，而 requirements C-3 已禁止以重跑 `schema_rbac.sql` 作為套用手段 —— 因此**現行 staging 不存在任何能讓這筆權限變更生效的路徑**，這正是 AC-3.4 逐字要求的「不因種子資料僅在空表時寫入而落空」。此缺口與 C-3 的補欄機制同構卻完全未被設計覆蓋；依此文件實作，US-3 會整則落空而 CI 全綠 | 新增一個元件（例如 C-7「權限預設值變更與既有環境套用」），明訂：①兩處預設值來源的同步義務與一致性檢查落點；②既有環境的套用機制（比照 C-3 的啟動補丁：一次性、可重複執行的目標式 `UPDATE`／`UPSERT`，只動 `Security_Reviewer × J3a` 該列，不觸碰其他列，以免重蹈 C-3 所要避免的覆寫）；③在對應表補 FR-4.1〜FR-4.3、NFR-3、stories US-3 對應此元件 |
| 3 | **Critical** | component-methods.md L63-89（C-2 簽章與失敗處置）；components.md L61；component-dependency.md L86、L116 | **C-2 的交易語意未定義，其核心承諾在既有 session 管理下不可達。** `record_activity_if_due(user, db, now) -> bool` 的契約只寫「發出單筆更新」「失敗時吞下例外並回傳 False，但必須先記錄」，**未定義 commit，也未定義失敗後的 session 復原**。實測 `database.py:31-36` 的 `get_db()` 為 `try: yield db finally: db.close()` —— **既不 commit、也不在例外路徑 rollback**；`database.py:24` 的 `SessionLocal` 為 `autocommit=False`。兩個分支都壞：**(a) 不 commit** → 絕大多數認證端點是唯讀（`GET /api/auth/list`、`/me`、`/roles`、`collab`／`review`／`lens` 的所有 GET）本身從不 commit，pending 的 UPDATE 會在 `db.close()` 時被丟棄，FR-1.1／AC-1.1「發出任一需認證的請求後最後活動時間被記錄」對這些端點**永遠不成立**，且 `record_activity_if_due` 回傳 True 是假的。**(b) commit 但失敗時只吞例外不 rollback** → session 進入 pending-rollback；緊接著執行的 `require_story_action._dep`（`rbac.py:238`）會呼叫 `user_can` → `get_permission_row` → `db.query(RolePermission)`（`rbac.py:119`→`:89`），拋 `PendingRollbackError`，**使用者的原始請求照樣失敗** —— 直接推翻 C-2「不得讓使用者的原始請求失敗」這條全設計最核心的承諾 | 在 `component-methods.md` 的 C-2 契約明訂三件事：①寫入路徑必須自行 `commit`（並說明在依賴階段執行時 session 內無端點的待決變更，故 commit 不會誤提交他人交易）；②`except` 區塊必須先 `db.rollback()` 再記錄並回傳 False，使後續依賴與端點仍可使用同一 session；③明確聲明此元件對 session 的所有權邊界（借用不獨佔、不 close）。這三點是可驗證的介面契約，不是實作細節 |
| 4 | **Major** | components.md L61、L98、L136、L137；component-methods.md L79；component-dependency.md L70、L86；services.md L70；decisions.md L235 | **NFR-3／NFR-4 引用系統性錯置，且「寫入失敗不影響請求」無上游來源。** requirements 原文（L87-88）：**NFR-3 = 安全（ADR-0006 四面向，四項缺一不可）**、**NFR-4 = 可測試性（授權矩陣 allow/deny 雙向測試）**。設計卻在 8 處把 NFR-3 當作「時區」、把 NFR-4 當作「寫入失敗不影響請求」。附帶兩個後果：①`grep` 全文確認 requirements 與 stories **沒有任何一條**規定「活動時間寫入失敗不得讓原始請求失敗」——這是本站自創的約束卻掛了假來源（其真正依據只有 construction 護欄的 silent-failure 條款，設計已同時引用，足以獨立支撐）；②NFR-3（ADR-0006 四面向）是 `project.md ## Mandated` 的 hard constraint，**設計對它零覆蓋**，卻讓它的編號被一個不相干的主題佔用，使「是否漏項」在文件比對層面被遮蔽 | 三處分別修正：時區的來源改引 requirements **C-5**（既有時間戳慣例）與 stories **AC-1.6**；失敗隔離改以 construction 護欄為唯一來源，並如實標註「本站設計判斷、無上游需求條文」（比照 AD-4〜AD-6 的處理方式）；另補一列說明 NFR-3 的四面向在本站的落點（IAM 面向即 Finding 2 的權限元件） |
| 5 | **Major** | components.md L138-141；component-methods.md L131；component-dependency.md L94；services.md L88；decisions.md L235-236 | **`stories S-1`〜`S-4` 為不存在的識別碼。** `stories.md` 定義的是 **US-1〜US-4**（L55／L141／L205／L271），全文無任何 `S-1`〜`S-4`。設計在 5 份檔案共 7 處引用 `stories S-n`，全部無法解析。相對地設計引用的 AC 編號（AC-1.9、AC-2.1、AC-2.3、AC-2.5）皆正確存在，顯示這是純粹的編號誤植而非語意錯誤 | 全域改為 US-1〜US-4；並順帶核對映射語意：US-1 實際涵蓋 FR-1.1〜FR-1.4／FR-2.1／FR-2.2／**FR-2.5**／NFR-1／NFR-5，設計現行「S-1（稽核者檢視）→ C-4、C-5、C-6」漏了寫入側與 FR-2.5 |
| 6 | **Major** | decisions.md L98、L102、L108、L119、L237；component-methods.md L114；components.md L73 | **requirements C-2／C-3 被誤引為「schema 與部署資產同步（blocking）」。** requirements 原文（L111-113）：**C-2 = 專案無 migration 框架、結構變更靠啟動時補齊（→ 部署後須重啟）**；**C-3 = 重跑整份初始化腳本會重置權限（→ 部署程序必須排除重跑）**；真正要求「`schema_rbac.sql` 與 `DEPLOY.md` 未同步即不得標示階段完成」的是 **C-4**。設計共 10 處以 C-2／C-3 承載這項 blocking 義務。誤引的實害是：C-2／C-3 本身承載的兩個約束（**AC-1.7 部署後必須重啟才生效**、**部署程序須排除重跑腳本**）在設計中沒有被獨立表述，而 AC-1.7 是 stories 明列的驗收條件 | 同步義務改引 **C-4**；另在 `services.md` 的失敗模式或 `decisions.md` AD-3 的 Consequences 補上 C-2 的實際後果（部署後須完成一次重啟，變更才生效 —— 對應 stories AC-1.7 與 AC-3.4） |
| 7 | **Major** | components.md L126-141（元件與需求的對應） | **對應表宣稱是需求對應，實際遺漏 11 項需求且無缺口聲明。** 未出現於表中者：**FR-1.4、FR-2.5、FR-3.2、FR-3.3、FR-5.1〜FR-5.3、NFR-1、NFR-2、NFR-5、NFR-6、NFR-7**（FR-5 系列與 NFR-2 在 C-5／C-6 內文有觸及，但表上不可見）。其中 **FR-1.4 特別嚴重**：`stories.md:333` 逐字把它交辦給本站——「無行為 AC —— 屬設計期約束…**落點為 application-design 的設計審查：欄位設計不得使用會阻擋歷史表擴充的結構**」，而 `FR-1.4` 在五份 artifact 中出現次數為 **0**。上游 stories 已示範了「明確標示未涵蓋項而非假裝已涵蓋」的作法，本表未沿用 | 補齊各列（可標「由 refined-mockups 既定規格承載」「屬測試策略階段」等），並比照 `stories.md` 的覆蓋確認段落，明列本站**刻意不承載**的項目與理由；FR-1.4 須有實質判定（單一可為空欄位覆寫不阻擋日後新增歷史表，且不引入會妨礙擴充的結構），這是上游指定的設計審查項，不能留白 |
| 8 | **Major** | component-methods.md L23-46（C-1 簽章）、L64-68（C-2 簽章）、L97（C-3 欄位） | **時間戳的 tz-aware／naive 未在契約中釘死，是可直接觸發 TypeError 的落點。** C-1／C-2 的 `now: datetime` 與 `last_recorded_at: datetime \| None` 不約束時區屬性。實測 repo **同時存在兩種慣例**：`auth.py:32/34` 用 naive 的 `datetime.utcnow()`；`user_router.py:424/511/549` 用 aware 的 `datetime.now(timezone.utc)`。Python 對 naive 與 aware 做減法／比較會拋 `TypeError`。更關鍵的是測試環境：`tests/helpers.py:26-29` 用 in-memory SQLite，**SQLite 不保存時區**，`DateTime(timezone=True)` 讀回來是 naive；若呼叫端傳 aware 的 `now`，NFR-5／DoD 所要求的第一支 `TestClient` 測試會在第一次比較就炸掉。stories Assumptions（L359）已逐字把「具體的儲存與顯示時區策略」交辦給 application-design（承 AC-1.6），本站尚未定案 | 在 C-1 的簽章區明訂契約：兩個 `datetime` 參數**一律為 tz-aware UTC**，並定義違反時的行為（拒絕或正規化，二擇一寫死）；在 C-2 的呼叫點明訂 `now` 的取得方式為 `datetime.now(timezone.utc)`（與 `user_router` 的既有慣例一致，而非 `auth.py` 的 `utcnow()`）；在 C-3 註明 SQLite 測試環境讀回為 naive 的落差與收斂方式。這一項同時是 AC-1.6 的設計期落點 |
| 9 | Minor | components.md L63；component-dependency.md L119 | **併發論證的「單調前進」不成立。** 兩個並行請求各自持有自己算出的 `now`（T1 < T2）。列鎖只保證 UPDATE 序列化，不保證「後 commit 者的值較大」——若持 T1 的請求後 commit，最終值為 T1，比 T2 舊。實務差距為次毫秒、無實害，但「最後值仍然正確（**單調前進**）」這句是錯的，而全設計以它作為「不需要鎖」的依據 | 改寫為：兩者皆寫、最終值為後 commit 者的時刻，與最大值的偏差不超過兩請求的時間差（次毫秒級），在 5 分鐘節流語意下無實務影響 —— 保留同一結論但論據為真 |
| 10 | Minor | component-dependency.md L132；component-methods.md L138-141 | **部署順序論證與 C-5 的 props 型別不一致。** 「前端先上時新欄位為 `undefined`（顯示為無紀錄態）」——但 `LastActivityCellProps` 定義為 `lastActivityAt: string \| null`、`isOverdue: boolean`（皆 required），`undefined` 不符合任一者。實測 `AdminPage.tsx:6-13` 的 `DbUser` 為手寫 interface、`fetchUserList` 以 `await res.json()` 直接放行（team-practices 已記載此處無編譯期保護），因此執行期不會爆，但契約與論證對不上 | 在 C-6 的契約補一條：由頁面層以 `?? null` / `?? false` 收斂為 C-5 的宣告型別；或把 `DbUser` 的兩個新欄位標為選填並在傳遞點正規化 |
| 11 | Minor | decisions.md L221-223（AD-6 Alternatives Rejected） | AD-6 的替代方案為「無其他認真考慮的選項」。inception 階段護欄要求「架構決策須有 trade-off 分析——至少記錄兩個替代方案」。AD-1〜AD-5 皆符合，僅 AD-6 缺 | 補一個真實替代（例如沿用 `last_opened_diagram_id` 的 `last_*` 前綴 vs. 語意更明確的命名）與否決理由，或明示 AD-6 屬命名慣例確認而非架構決策、不適用該護欄 |
| 12 | Minor | services.md L47、L51-53；component-dependency.md L89 | **「判定不產生任何查詢」在寫入分支的成本論述不完整。** `database.py:24` 的 `sessionmaker` 未關閉 `expire_on_commit`（預設 True），因此 C-2 一旦 commit，`get_current_user` 回傳的 `user` 物件即過期，後續 `require_story_action` 讀 `current_user.authorization_status`／`.role`（`rbac.py:232`、`:239`）會觸發一次 refresh SELECT。頻率上限為每帳號每 5 分鐘一次、影響可忽略，但 services.md 的成本論述目前只寫「新增一次單列更新」 | 在「延遲影響」補一句：寫入分支另含一次因 session 過期而產生的 user 重讀（或明訂 C-2 以 `expire_on_commit=False`／`db.refresh` 以外的方式規避），使成本陳述完整 |

### 已查證但未發現問題的項目

以下主張經回 repo 實測，**確認為真**，後續 iteration 不需重查：

| 主張 | 查證結果 |
|---|---|
| 「既有認證依賴已取得完整使用者物件與可用 db session」 | **成立**。`auth.py:39-42` 簽章含 `db: Session = Depends(get_db)`；`:57` 執行 `db.query(User).filter(...).first()`；`:65` 回傳完整 `User`。判定所需值確實在手，零額外查詢的成本論證正確 |
| 「認證依賴是所有認證請求的必經點」（有無繞過路徑） | **成立，且已窮舉**。跨 5 支 router 清點：所有需認證端點皆經 `get_current_user`，直接（`user_router` 3 處）或間接（`RoleChecker`、`require_story_action`、`require_arch_action` 皆 `Depends(get_current_user)`）。未經此路徑者僅有**真正未認證**的端點：`main.py` 的 `/`、`/api/auth/login`、`/register`、`/roles/catalog`、以及 `collab_router.py:221` 的 WebSocket（該端點完全無驗證，非繞過認證）。**不存在「已認證但不經此點」的路徑** |
| 「有兩個同形狀的既有補欄先例」 | **成立，形狀逐字相同**。`_ensure_a4_schema`（`database.py:123-148`）與 `_ensure_j5_schema`（`:151-195`）皆為 `ALTER TABLE users ADD COLUMN IF NOT EXISTS ...`、皆採 statements 陣列 + `with engine.begin()` + 逐句 `try/except` + `logger.warning`，皆由 `init_db()`（`:42-43`）在 `main.py` 的 startup event 呼叫。C-3 沿用此形狀的主張正確 |
| 補欄在 SQLite 測試環境的行為 | **不構成風險**。測試從不呼叫 `init_db()`：`tests/helpers.py:25-35` 以 `Base.metadata.create_all` 在 in-memory SQLite 建表。因此 PostgreSQL 專屬的 `ADD COLUMN IF NOT EXISTS`（SQLite 不支援）在現行測試路徑上不會執行。（`TestClient(app)` 不以 context manager 使用時亦不觸發 startup event） |
| 「回應新增欄位向後相容、部署順序無硬性約束」 | **成立**（型別契約的小瑕疵見 Finding 10）。`AdminPage.tsx:39-48` 的 `fetchUserList` 以 `await res.json()` 回傳，未做欄位白名單或 schema 驗證；`DbUser` 為手寫本地 interface，與後端 `UserSchema` 無編譯期連結。多出的欄位確實被忽略 |
| 「既有權限檢查在路由層決定可見性，序列化層不自行判斷」 | **成立且無漏洞**。`list_users`（`user_router.py:439`）由 `require_story_action("J3a","view")` 做端點層 all-or-nothing 把關。「某些角色看得到清單但不該看到新欄位」的情境**不存在**——requirements FR-4.2 已明文定案「權限粒度維持現狀，不做欄位級控制…四個管理類角色皆可見本欄位，無角色間的欄位差異」，且列於 Won't Have。設計未處理欄位級授權是正確的，不是漏洞 |
| 授權旗標的爆炸半徑 | **已由上游承接，非本站缺口**。`J3a:view` 同時開啟 `list_users`（`:439`）與 `list_authorization_requests`（`:466`）。此範圍已在 requirements FR-4 註記（L69）與 stories AC-3.5 明文「經人工確認為可接受，非缺陷」。（本站仍缺的是**變更機制本身**，見 Finding 2） |
| `DateTime(timezone=True)` 的選擇 | **與既有慣例完全一致**。`models.py` 全部 9 個 datetime 欄位（`:65/67/70/83/104/132/134/149/151/168`）皆為 `DateTime(timezone=True)`。C-3 不加 `server_default=func.now()` 也正確——加了會讓「從未活動」與「剛建立」無法區分，設計對此的論證（L100）站得住腳 |
| 兩個門檻的邊界方向相反 | **各自正確，非筆誤**。FR-1.3 的 AC 逐字為「距上次寫入滿 5 分鐘（**含**）之後的下一個請求觸發第 2 次寫入」→ `should_record_activity` 含等於為真 ✓；FR-3.1＋stories AC-2.1 逐字為「**不含**恰為 90 天者」→ `is_activity_overdue` 恰好等於時為否 ✓。設計 L49 引用「stories 的追溯段落」亦屬實（`stories.md:354`「邊界語意對齊確認」） |
| AD-6「欄位命名未經問答定案」的誠實性 | **誠實，處理方式正確**。`application-design-questions.md:30`（Q1 選項 A）確實逐字出現 `last_activity_at`，Q3 選項 A 則只出現 `_ensure_*_schema()` 與泛用的 `ADD COLUMN IF NOT EXISTS ...`。AD-6 主動揭露「題幹與選項文字中出現的欄位名是為了讓題目具體，不構成命名的定案」並標為 gate 上開放挑戰 —— 這正是 `team.md` correction（掛來源標籤前須逐字核對選項原文）所要求的形狀，不宜視為隱瞞 |
| team-practices 引用的三項事實 | **全部屬實**。`grep -c "@given" backend/tests/` = **8**，分布於 5 支純函式測試檔；`grep -rn "TestClient" backend/tests/` = **0**（規則 B 確為首次引入）；規則 A／B／C 的內容與 `team.md ## Testing Posture` 逐字相符 |
| 單一 worker／單一實例／零背景任務（AD-1 的擴展論證前提） | **全部屬實**。`backend/Dockerfile:37` 為 `CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]`，**無 `--workers`**；`deploy/docker-compose.deploy.yml` 僅 4 個服務（`db`／`backend`／`frontend`／`cloudflared`），backend 無水平擴展；`grep BackgroundTasks\|celery\|apscheduler\|create_task` 於 `backend/**.py` **零命中**。AD-1 否決方案 B（記憶體節流表）的「加 worker 後靜默破壞 FR-1.3」論證因此成立且有價值 |
| C-5 的 props 與 refined-mockups 一致性 | **逐字一致**。`interaction-spec.md` 的 Props 表（`lastActivityAt: string \| null`、`isOverdue: boolean`，皆 required、`isOverdue` 由呼叫端傳入）與 `component-methods.md:138-141` 完全相同；五種狀態、可及性區分手段（僅可及性層面）、斷點行為亦一致 |
| 依賴矩陣的無循環主張 | **成立**。C-1 與 C-3 為葉節點（無射出邊），矩陣上三角全空，七條依賴邊與 Mermaid 圖及文字 fallback 三者一致，無循環、無孤兒節點 |

### Summary

**設計的事實基礎紮實，缺口在需求承載面。** 對既有機制的每一項成本論證（認證依賴已持有 User 物件、兩個同形狀補欄先例、單 worker／零背景任務、既有時間欄慣例）實測全數成立，C-1 作為零 I/O 葉節點的形狀與 AD-1／AD-2 的替代方案分析也經得起推敲。

阻擋 READY 的是三件會讓開發者依此文件實作後**功能真的壞掉、且 CI 全綠**的事：**(1)** FR-2.5／AC-1.5 無承載元件，兩個 PUT 端點會逐字複製既有的 `requested_role` 漏傳缺陷 —— 而 FR-2.5 正是為防這件事而存在；**(2)** FR-4／US-3 整則無元件，且 `ensure_role_permissions_seeded(force=False)` 只在空表寫入、requirements C-3 又禁止重跑腳本，導致權限變更在既有 staging **沒有任何生效路徑**（AC-3.4 逐字要求的缺口）；**(3)** C-2 未定義 commit 與失敗後的 `db.rollback()`，而 `get_db` 兩者都不做 —— 不 commit 則唯讀端點的活動時間永不落地，commit 後不 rollback 則下一個 `db.query` 拋 `PendingRollbackError`，使用者請求照樣失敗，直接推翻 C-2 自己的核心承諾。

另有五項 Major 屬引用層的系統性錯置（NFR-3／NFR-4 語意互換且「失敗不影響請求」無上游來源、`S-n` 識別碼不存在、C-2／C-3 誤代 C-4、對應表漏 11 項需求含上游指名交辦的 FR-1.4）與一項實作即炸的契約空白（時間戳 tz-aware 未釘死，在 SQLite 測試環境會直接 TypeError）。這些不影響設計的**判斷**，但會讓下游的可追溯性檢查與首支 `TestClient` 測試落空。

修補路徑明確且不需推翻任何已定案決策：Finding 1／2 各補一個元件邊界，Finding 3／8 各補一段介面契約，Finding 4〜7 為引用更正。建議 iteration 2 修正後重審。
