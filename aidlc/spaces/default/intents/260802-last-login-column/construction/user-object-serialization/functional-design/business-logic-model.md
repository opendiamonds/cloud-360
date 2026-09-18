# Business Logic Model — U2 `user-object-serialization`

> Stage: functional-design（Construction 3.1）· Unit: `user-object-serialization`（kind: service）
> 上游來源：`../../../inception/application-design/components.md` C-4（下稱 components C-4）、`component-methods.md` C-4、`services.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/user-stories/stories.md`（下稱 stories）、`../../../inception/units-generation/unit-of-work.md`、`unit-of-work-story-map.md`。
> 規則見 `business-rules.md`（R1〜R3），實體見 `domain-entities.md`。
> 問答定案：Q1=A、Q2=A、Q3=A。事實查證 S1〜S5 見 `functional-design-questions.md` 的 `## Sources`。

## 本單元做什麼

把 U1 記錄下來的最後活動時間，連同一個當場算出來的逾期旗標，帶進**所有**回傳使用者物件的 API 回應裡。

範圍極窄 —— 三個構造點各加兩個欄位、外加一次正規化與一次判定呼叫。**零資料庫變更**。但它是本 intent 中資料鏈的必經環節：U1 寫進去的值若不出現在 API 回應，U3 就沒有東西可顯示。

## 觸發點

**三個回傳使用者物件的 API 端點**，每次請求各觸發一次。這不是啟動期的一次性動作（U1 的補欄與 U4 的權限套用才是），而是**每個請求都會走的路徑**。

## 主流程（以使用者清單端點為例，另兩處為單列版本）

```
請求進入端點
 |
 +-- 取得「當下時刻」一次，**必須帶時區 (UTC)** (Q2=A；R2)
 |     取到 naive 值會讓三個端點的第一次比較全部拋型別錯誤
 |
 +-- 查出使用者列（既有邏輯，不動）
 |
 +-- 逐列序列化：
      |
      +-- 讀取最後活動時間（可能為空）
      |
      +-- 呼叫 U1 的時區正規化函式 (R3)
      |     |
      |     +-- 值為空 -----------> 維持空
      |     +-- 不帶時區 ---------> 補為 UTC
      |     +-- 已帶時區 ---------> 原樣
      |
      +-- 呼叫 U1 的逾期判定函式（傳入正規化後的值與那個共用時刻）(R2)
      |     |
      |     +-- 值為空 -----------> 否（U1 契約保證）
      |     +-- 否則 -------------> 依門檻判定
      |
      +-- 構造回應物件：既有欄位 + 最後活動時間 + 逾期旗標
            |
            +-- 任一新欄漏傳 -----> 構造當下失敗 (R1)
 |
 +-- 回傳
```

**文字 fallback**：端點進入時先取一個「當下時刻」（**必須帶時區**，取到 naive 值會讓所有比較拋型別錯誤），整次回應的所有列共用。逐列序列化時，先讀出最後活動時間並呼叫 U1 的公開正規化函式（空值維持空、不帶時區者補為 UTC、已帶時區者原樣），再把正規化後的值與那個共用時刻一起傳給 U1 的逾期判定函式（空值一律回傳否）。最後構造回應物件；兩個新欄位為必填，任一漏傳會在構造當下失敗而非靜默回傳空值。

## 本單元最關鍵的設計取捨：為何不做共用工廠函式

components C-4 把「不設預設值」與「共用工廠函式」並列為二擇一，交由 Construction 定案。**查證後兩者並不對稱**：

| 面向 | 選項一（採用） | 選項二（工廠函式） |
|---|---|---|
| C-4 寫的簽章可行嗎 | 不適用 | **需要繞道**（非結構上不可能 —— reviewer iteration 1 更正）。依 S4，清單端點的一個既有欄位需要**額外的 DB 查詢**且只在待授權時執行，另兩處完全不傳；該簽章要涵蓋此差異，得先把查詢結果掛到物件的動態屬性上再傳入 —— 可行，但那本身是異味，且把差異藏進呼叫端而非消除它 |
| 會碰到範圍外的東西嗎 | 否 —— 只加兩個新欄位 | **會** —— 必須就地決定那兩處要不要補上漏傳的既有欄位（補了超範圍，不補則工廠內部仍要分歧） |
| 與既有團隊規則 | 一致 | 與 `team.md ## Code Style`「修改此檔就地沿用既有形狀，不趁機夾帶抽取」方向相反 |
| 漏傳時的行為 | **構造當下失敗** | 結構上不可能漏 |

**誠實記載選項一的代價**：它保證的是「漏傳會失敗」，不是「不可能漏傳」。將來新增第四個構造點仍需人記得帶上兩欄。選項二在這一點上確實更強 —— 但它要付的代價（簽章需繞道或加寬、必須就地決定要不要碰範圍外的既有缺陷）都是具體且立即的，而選項一的代價是假設性的（將來可能有第四個構造點）。

**這個判斷不依賴「工廠函式不可能實作」這個更強的主張** —— 該主張經 reviewer 檢驗為過度延伸，已於上表更正為「需要繞道」。

## 本單元的驗證強度（分項評估，不做整體宣稱）

> **本表於 reviewer iteration 1 後整段更正。** 初版把「三個端點都帶出兩欄」的保護歸功於欄位集合斷言，**那是錯的** —— 實測三個端點皆宣告 `response_model`，回應的 key 集合由回應模型的欄位宣告決定，與構造點傳了什麼無關。詳見 `business-rules.md` R1 的「欄位集合斷言抓不到構造遺漏」。

| 項目 | 驗證方式 | 強度 |
|---|---|---|
| **構造點漏傳新欄位** | **R1 的必填宣告** —— 缺漏時在構造當下拋錯，端點回 500 | **強（結構性，非測試）** |
| **回應值與資料庫一致**（AC-1.5 的 Then 逐字要求） | 端點測試斷言**值**：有紀錄者為對應時間值、無紀錄者為明確空值 | **強** —— 這才是能抓到「值被靜默預設為 `null`」的機制 |
| 回應模型本身增刪欄位 | 端點測試斷言**欄位集合完全相等**（Q3=A），三端點各一支 | **強** —— 這是欄位集合斷言的真正用途 |
| 回應中的時間為 UTC 形式 | 端點測試斷言值的形式 | **強** —— 這正是 R3 存在的理由（SQLite 路徑讀回不帶時區） |
| 空值時逾期旗標為否 | 端點測試可直接構造此情境斷言 | **強** |
| 逾期判定本身正確 | **不在本單元** —— 屬 U1 的純函式測試（含 property-based） | 由 U1 承載 |
| 正規化邏輯正確 | **不在本單元** —— 屬 U1 | 由 U1 承載 |
| R1 的「漏傳會失敗」行為本身 | 無專屬測試（要驗證它得刻意寫一個漏傳的構造） | **無** —— 如實記載。它靠的是回應模型的必填宣告，而非測試 |

最後一列是本單元唯一的驗證缺口，且性質溫和：R1 的機制是宣告式的（必填即失敗），不是需要被測試守護的邏輯。

## Q3 的定案與其真正的作用範圍（reviewer iteration 1 後更正）

**定案不變**（欄位集合完全相等），但**它防的是什麼**必須更正。

初版寫「這三個端點已經真的發生過本規則要防的失敗模式」—— 該敘述不成立。依 S2 的既有缺陷（兩個 PUT 端點漏傳一個既有欄位）在 `response_model` 之下**根本不是「少了欄位」**，而是**值被靜默預設為 `null`**；欄位集合斷言對它完全無效。

| 斷言 | 防得到 | 防不到 |
|---|---|---|
| 欄位集合**完全相等** | 回應模型本身被增刪欄位（schema 層回歸） | 構造點漏傳（key 由 `response_model` 保證存在） |
| **值**斷言（AC-1.5 要求） | 值被靜默預設為 `null`、值與資料庫不一致 | — |
| R1 的**必填宣告** | 構造點漏傳必填欄位（構造當下硬失敗） | 有預設值的欄位 |

三者**互補而非替代**，本單元三者皆需。選完全相等而非包含式的理由仍成立（多抓一類 schema 層回歸），但它**不是**本 intent 防構造遺漏的機制。

代價是日後合理新增欄位時測試會紅、必須在同一個 PR 更新預期集合 —— 這是契約測試應有的行為，不是損失。

## 與其他單元的介面

| 對象 | 介面 | 方向 |
|---|---|---|
| **U1** | 取用其**公開時區正規化函式**（R3）與**逾期判定函式**（R2）；讀取其建立的資料庫欄位 | 本單元**依賴** U1 |
| **U5**（型別契約） | 本單元決定的回應欄位形狀是型別產生的**輸入** | U5 依賴本單元 |
| **U3**（前端呈現） | **兩條邊**：①執行期直接消費本單元的 HTTP 回應（`unit-of-work-dependency.md` 明畫的 U3→U2 邊）；②建置期經由 U5 的型別契約依賴本單元的回應形狀 | U3 依賴本單元 |
| **U4** | 無程式碼耦合。U4 決定誰進得了管理頁，本單元不做欄位級授權 | 無 |

## 本單元不做的事

| 事項 | 為何 |
|---|---|
| 判定逾期的門檻與邊界語意 | 屬 U1（C-1），本單元只呼叫 |
| 決定何時寫入最後活動時間 | 屬 U1（C-2） |
| 欄位級授權 | requirements FR-4.2 已定案不做，列於 Won't Have；可見性由既有端點層權限檢查決定 |
| 顯示格式、在地化、無紀錄態的呈現 | 屬 U3（C-5／C-6） |
| **修正那兩個端點漏傳既有欄位的缺陷** | `phase-check-inception.md` 明確劃為範圍外；`team.md` 亦規定修改此檔時不夾帶額外改動 |
| 改動任何既有欄位的預設值或型別 | 同上 |

## 事實查證（本站主張的依據）

| 主張 | 查證方式 | 結果 |
|---|---|---|
| 三個構造點全部手寫具名引數 | 全檔搜尋回應模型的構造處並逐一讀取 | **成立**（S1） |
| 兩個 PUT 端點漏傳一個既有欄位 | 逐一比對三處傳入的欄位清單 | **成立**（S2）—— 清單端點 6 個、另兩處各 5 個 |
| 該欄位有預設值，所以漏傳靜默通過 | 讀取回應模型定義 | **成立**（S3）—— 這是 R1 的直接依據 |
| 清單端點的該欄位需要額外 DB 查詢 | 讀取清單端點的構造前置邏輯 | **成立**（S4）—— 且只在該使用者為待授權時執行。這是否決工廠函式簽章的決定性依據 |
| 全 repo 自動轉換使用數為 0 | 依 components C-4 的實測記載，本站複核三處皆為手寫 | **成立**（S5） |
| **三個端點皆宣告 `response_model`，回應 key 集合由回應模型決定** | reviewer iteration 1 實測三處路由裝飾器，且無 `exclude_unset`／`exclude_none` 客製 | **成立** —— 這推翻了本站初版對欄位集合斷言效力的歸因，已整段更正 |

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-09T16:00:08Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Critical | `business-logic-model.md`「為何 Q3 選『欄位集合完全相等』而非『包含即可』」節（L77-83）與「本單元的驗證強度」表（L64-75）；`business-rules.md` R1 節「為何這條規則存在」（L16-20）；`functional-design-questions.md` Q3（L73-89） | Q3=A 的核心論證（「完全相等的斷言同時抓『少了欄位』與『多了沒預期的欄位』…這正是本 intent 中唯一能自動抓到『某個端點漏了欄位』的機制」）在 FastAPI + Pydantic 的實際行為下不成立。實測 `backend/services/user_router.py:437/562/658` 三個端點的 decorator 皆宣告 `response_model=UserSchema` 或 `List[UserSchema]`，且無任何 `exclude_unset`／`exclude_none` 客製化（全檔 grep 為 0 命中）。這代表**回應 JSON 的 key 集合完全由 `UserSchema` 這個類別的欄位宣告決定，與哪個構造點呼叫、構造時傳了哪些具名引數無關**——`requested_role` 因為有 `Optional[str] = None` 預設值，無論是否被明確傳入，序列化後**一定會出現在 key 集合中**，差別只在值是 `None` 還是實際角色字串。S2 記載的既有缺陷（兩個 PUT 端點漏傳 `requested_role`）因此**從未是「少了欄位」，而是「值被靜默預設為空」**——這正是 `domain-entities.md` L58 自己承認的：「測試斷言的是欄位存在，不是值正確。缺陷本身仍在」。三份文件在同一個決定上出現互相矛盾的自我描述：`business-logic-model.md`／`business-rules.md`／`functional-design-questions.md` 反覆宣稱完全相等的 key-set 斷言「這正是能抓到本規則要防的失敗模式」，`domain-entities.md` 卻明確記載同一個斷言抓不到它。對兩個新欄位（R1）而言同理：Q1=A 選擇不設預設值後，漏傳會在 `UserSchema(...)` 建構當下拋 `ValidationError`（500），根本不會產出一個「key 較少但仍是 200」的回應可供 key-set 比對——真正攔住 R1 違反的是「建構期失敗→非 200」，不是 key-set 相等本身。這也意味著「本單元的驗證強度」表把「三個端點都帶出兩欄」評為「強」，但整份文件**沒有任何一列**明確規劃「`last_activity_at` 有值時，回應值與資料庫值一致」的測試——而這正是 `stories.md` AC-1.5（L90-93：「帶有與資料庫一致的值…而非因構造遺漏而缺失」）與其 DoD（L121：「斷言回應中該欄位帶有與資料庫一致的值（**不只是 key 存在**）」）逐字要求、且明確預警了這個混淆的驗收條件。若 code-generation 階段照字面實作本文件描述的「key 集合完全相等」測試而不額外補值級斷言，會產生「CI 綠燈但 AC-1.5／NFR-5／DoD 實質未被滿足」的結果——這正是下游單元無法正確銜接已核可驗收條件的情形。（註：「回應欄位集合完全相等」這個框架本身承襲自已核可的 `unit-of-work.md` L87〔units-generation 階段〕，此處不要求回改該上游檔案；但本站身為對此做過 S1-S5 程式碼查證的階段，有責任把機制講精確，而不是原樣放大一個不成立的因果關係。） | 把「回應欄位集合完全相等」重新定位為**日後欄位新增／刪除的漂移防呆**（這個用途是真的成立的），而非「能抓到 S2 那個既有缺陷模式」的機制；在「本單元的驗證強度」表新增一列，明確規劃「`last_activity_at` 非空時，回應值與資料庫寫入值一致」的測試，並讓 R1／Q3 的敘述與 `domain-entities.md` L58 的誠實記載互相一致，不再自相矛盾。 |
| 2 | Major | `business-rules.md` R2 節（L32-46）；`business-logic-model.md`「主流程」（L20-23） | R2 規定「當下時刻在進入端點時取一次」，但全文從未明確要求這個取值**必須是帶時區的 UTC**（例如 `datetime.now(timezone.utc)`），不可用 naive 的 `datetime.utcnow()`。這不是無關緊要的實作細節：本單元明確授權可讀的唯一 U1 檔案 `construction/backend-activity-policy/functional-design/business-rules.md` L84-85 逐字寫明「取得當下時刻的唯一許可寫法｜帶時區的 UTC 取值」「禁止｜不帶時區的 UTC 取值——它會在第一次比較就拋型別錯誤」，且 `components.md` C-1 節（iteration 1 Finding 8）把這個契約標記為「不是實作細節而是介面契約」。U1 的正規化 helper（R3）只處理**讀自資料庫**的 naive 值，不處理呼叫端傳入的 naive「當下時刻」——若 U2 的實作用了 naive 的取值方式，R2 呼叫會在第一次比較就對三個端點全部拋 `TypeError`（500），且不會被 R3 的正規化救回來。`user_router.py` 內雖已有 `datetime.now(timezone.utc)` 的既有先例（L424、L549）可供沿用降低風險，但本單元作為這個值的**唯一取得者**，理應在自己的規則文字中明確重申這個約束，而非要求實作者自行回頭比對 C-1 的介面契約段落才能發現。 | 在 R2 或「主流程」段落明確加一句：「取得『當下時刻』必須使用帶時區的 UTC 寫法（如 `datetime.now(timezone.utc)`），不得使用 naive 的 `datetime.utcnow()`——與 `user_router.py` 既有的 `datetime.now(timezone.utc)` 用法一致；違反會在 R2 比較時對三個端點全部拋 `TypeError`」。 |
| 3 | Major | `business-logic-model.md`「本單元最關鍵的設計取捨」表（L57）；`business-rules.md`「為何不採共用工廠函式」表（L26）；`functional-design-questions.md` Q1 選項一第一個理由（L38） | 三份文件把「工廠拿不到 C-4 寫的簽章」表述為結構上的「否」（不可能），但這個結論過度延伸了 S4 這個事實查證本身。S4 只證明「清單端點的 `requested_role` 需要條件式的額外查詢，另兩處不傳」，這件事是真的；但由此推出「`(使用者物件, 當下時刻)` 這個簽章結構上重現不了這個差異」並不成立——呼叫端仍可在呼叫工廠**之前**先做既有的條件式查詢，再把結果以動態屬性掛到 ORM 的 `User` 物件上（例如 `u.requested_role = requested`，Python／SQLAlchemy 允許對映射物件掛未宣告的屬性），工廠函式再用 `getattr(user, "requested_role", None)` 讀出。這樣工廠的簽章文字上仍是 `(使用者物件, 當下時刻)`，且對兩個 PUT 端點（不掛屬性）行為與現況完全一致，不會觸碰範圍外的既有缺陷——即表中第二個理由（「會碰到範圍外的東西」）在這個變體下也不成立。這不代表 Option 2 應該被採用（把非持久化的檢視層資料掛到 ORM 物件上是常見的程式碼異味，且不會減少呼叫端原有的條件式查詢邏輯，Option 1 仍是合理選擇，也仍有 `team.md ## Code Style` 的獨立支持），但「否／不可能」這個斷言本身沒有查證支撐，屬於未被本站考慮到的反駁。 | 把「工廠拿不到 C-4 寫的簽章」的判定從「否／不可能」改寫為「技術上可透過在 ORM 物件掛動態屬性繞過，但這本身是把檢視層資料混進持久化物件的異味，且不會減少呼叫端既有的條件式查詢分支——故仍判定選項一較佳，但理由是『代價更低』而非『選項二結構上不可行』」。 |
| 4 | Minor | `business-logic-model.md`「與其他單元的介面」表（L91） | 該表把 U3 對本單元的關係描述為「經由 U5 的型別契約間接依賴」，但已核可的 `inception/units-generation/unit-of-work-dependency.md` 的 Mermaid 圖與 YAML 邊定義明確畫出兩條邊：`U3 --HTTP取得兩個欄位--> U2`（直接）與 `U3 --import產生的型別--> U5`（另一條，間接透過型別）。本表遺漏了 U3 對 U2 的**直接** HTTP 依賴，只保留了間接的型別依賴，與上游依賴圖的邊定義不完全一致。 | 把該列改為「U3 同時直接依賴本單元的 HTTP 回應形狀（經 HTTP 取得兩個欄位）、也經由 U5 的型別契約間接依賴（編譯期型別檢查）」，對齊 `unit-of-work-dependency.md` 的兩條邊。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | PASS（`Cloud-360 repository contract validation passed.`） | Repo 層與 record 層必要文件、必要文字、文件語言、禁止路徑／內容檢查均通過；本站三份 artifact 未產生 contract 違規 |
| 程式碼實測（S1-S5 逐項複核，非工具，手動查證） | S1、S2、S3、S4、S5 五項主張皆與 `backend/services/user_router.py` 現況逐字相符（構造點行號 451/603/705、欄位數 6/5/5、`requested_role` 預設值、清單端點的條件式查詢、`from_orm`/`model_validate` 使用數為 0） | 事實面查證紮實可信；問題不在查證本身失真，而在由查證事實推導出的**因果論證**（Finding 1、3）出現過度延伸 |

### Summary

三份 artifact 在事實查證（S1-S5）與跨單元交接（U1 公開正規化函式、範圍外缺陷的認定）上都紮實可信，`business-rules.md` 對 R1-R3 的職責切分也清楚。但本輪判定 NOT-READY：Finding 1 是 Critical——文件反覆宣稱的「欄位集合完全相等測試能抓到既有的漏欄位缺陷」在 FastAPI／Pydantic 的 `response_model` 語意下不成立（`domain-entities.md` 自己的footnote 其實已經承認這一點，但沒有回頭修正另外兩份文件的敘述），若 code-generation 依文件字面實作，會產生「CI 綠燈但 AC-1.5／DoD 的『值一致』要求未被滿足」的落差。另有兩項 Major：R2 遺漏了「當下時刻必須帶時區」這個會導致三端點全部 500 的關鍵約束（儘管 U1 的契約檔已明文警告）；以及 Q1 對工廠函式選項的「結構上不可能」斷言過度延伸了 S4，存在一個本站未考慮到的繞過方式（雖不影響最終選擇）。建議修正 Finding 1、2 後即可視為 READY——這兩項都是文件敘述與測試規劃的補強，不需要推翻 Q1／Q2／Q3 已定案的選項本身。

---

### Iteration 2

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-09T16:13:43Z
**Iteration:** 2

#### Iteration 1 Findings — 逐項覆核

| # | 原嚴重度 | 狀態 | 覆核依據 |
|---|---|---|---|
| 1 | Critical | **已解決** | `business-rules.md` R1 新增「欄位集合斷言抓不到構造遺漏」小節與三種失敗模式對照表；`business-logic-model.md` 的「本單元的驗證強度」表整段更正，新增「構造點漏傳新欄位→R1 必填宣告（結構性，非測試）」與「回應值與資料庫一致→值斷言」兩列，且逐字對齊 `stories.md` AC-1.5（L90-93）與其 DoD（L121：「不只是 key 存在」）；`domain-entities.md` L58 的「會不會被抓到｜不會」與 Q3 的更正說明現已三處一致，不再互相矛盾。實測確認 `user_router.py:437/562/658` 三端點確皆宣告 `response_model`，全 repo 無 `exclude_unset`／`exclude_none` 客製，支持這個更正後的因果論證成立。 |
| 2 | Major | **已解決** | `business-rules.md` R2 新增「『帶時區』是硬性約束，不是風格」小節，明確要求當下時刻必須帶時區 UTC；`business-logic-model.md` 主流程圖與文字 fallback 同步在最前面標出「必須帶時區 (UTC) (Q2=A；R2)」；問題檔 Q2 補充約束一致。經讀取本單元被授權的唯一 U1 檔（`construction/backend-activity-policy/functional-design/business-rules.md` L78-97）核對，「取得當下時刻的唯一許可寫法｜帶時區的 UTC 取值」「禁止｜不帶時區的 UTC 取值——它會在第一次比較就拋型別錯誤」與本單元的敘述逐字對應，未發現矛盾。 |
| 3 | Major | **已解決** | 三處「為何不採共用工廠函式」表格皆已把第一個理由由「否／不可能」改寫為「需要繞道（非結構上不可能）」，並說明繞道方式（動態屬性）與其代價（異味、把差異藏進呼叫端）。`business-logic-model.md` 結論段新增「這個判斷不依賴『工廠函式不可能實作』這個更強的主張」，Q1 問題檔以 Revision 區塊清楚交代「原答案不改寫；A 仍為正確選擇，但依據縮為……」，正文與 Revision 之間**一致**，無自我矛盾。 |
| 4 | Minor | **已解決** | 「與其他單元的介面」表 U3 列已改為「兩條邊：①執行期直接消費本單元的 HTTP 回應…；②建置期經由 U5 的型別契約依賴本單元的回應形狀」。經回讀 `unit-of-work-dependency.md`（`U3 -->|"HTTP 取得兩個欄位"| U2`、`U3 -->|"import 產生的型別"| U5`、`U5 -->|"規格內容來自 C-4 的回應模型"| U2`）核對，兩條邊（一條直接、一條經 U5 轉一手的建置期依賴）與圖上的邊定義完全對應，措辭也正確地把型別依賴描述為「經由 U5」而非杜撰一條圖上不存在的 U3→U2 型別邊。 |

四項 iteration 1 finding 皆已妥善關閉，且核對過程中未發現任何一項修正本身違反上游已核可契約（`unit-of-work-dependency.md`、U1 的 `business-rules.md`、`stories.md` AC-1.5／DoD）。

#### 本輪新發現（修正過程本身引入，非原 iteration 1 finding 之列）

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Major | `functional-design-questions.md` Q3（L76-99，尤其 L80-89） | Q3 的 Revision 區塊（reviewer iteration 1 新增）明白宣稱「題幹與選項描述對這個斷言能防什麼的認定是錯的，**已更正**」，並具體點名「選項 A、B 描述中『S2 已經真的發生過』的推論**皆不成立**」。但緊接在這段 Revision 之後的選項 A、B 本文**完全未被編輯**，仍逐字保留被 Revision 自己判定為不成立的敘述：選項 A L89「依 S2，這三個端點**已經真的發生過**『新增欄位時漏掉另一個欄位』的失敗模式，包含式斷言抓不到它」、選項 B L94「而那正是本檔 S2 記載的、這三個端點**已發生過**的事」。這使得同一份文件在同一題之內，前段（Revision）與後段（選項本文）對「S2 的既有缺陷是不是『少了欄位』」給出**互相矛盾**的斷言——這正是 iteration 1 finding 1 的修復建議明確要求消除的自我矛盾（「讓 R1／Q3 的敘述……互相一致，**不再自相矛盾**」），但在 Q3 這一處，矛盾換了個位置重新出現，而非被消除。與 Q1 的 Revision 處理方式對照即可看出差異：Q1 的 Revision 置於 `[Answer]: A` **之後**，且明文承認「**原答案不改寫**」，不宣稱本文已被修正，讀者不會被誤導；Q3 的 Revision 置於選項**之前**，卻宣稱「已更正」，這個宣稱本身即為未被兌現的斷言。本單元真正的操作依據（`business-rules.md`、`business-logic-model.md`）已正確且一致，此矛盾目前不影響那兩份文件驅動的實作正確性，故不判 Critical；但 `functional-design-questions.md` 本身也在本站的必讀清單內，若日後有人只讀 Q3 字面（例如查證决策脈絡時）會被這個「宣稱已修但實未修」的落差誤導。 | 把 Q3 的 Revision 改為與 Q1 一致的處理方式：要嘛移到選項列表**之後**並把「已更正」改為「原選項描述不改寫，但下列理由已被本站判定為過度延伸／不成立」（如實記載未編輯的事實）；要嘛直接編輯選項 A、B 本文，把「已經真的發生過『新增欄位時漏掉另一個欄位』」改寫為「S2 的既有缺陷實為『值被靜默預設為 null』而非『少了欄位』，完全相等斷言防的是回應模型本身的欄位增刪」，讓本文與 Revision 的結論一致。 |
| 2 | Minor | `business-rules.md` R1 節「必須釐清的一件事」表（L26-30） | 表格第二列「真正抓得到的是什麼」欄寫「**值斷言**（見 R4）」，但本文件開頭明言「本單元擁有三條規則」（R1、R2、R3），全篇不存在任何 R4 定義，本單元被授權可讀的 U1 契約檔（`construction/backend-activity-policy/functional-design/business-rules.md`）亦只有 R0、R1、R2。這是一個指向不存在規則 ID 的斷鏈引用，屬 iteration 1 新增的表格中新引入的筆誤（很可能是想寫「見 AC-1.5」或「見 `business-logic-model.md` 的驗證強度表」）。因為「值斷言」的具體要求已在 `business-logic-model.md` 的「本單元的驗證強度」表與 `domain-entities.md` 中被完整且正確地描述，此筆誤不造成需求遺漏，僅為引用錯誤。 | 把「見 R4」改為「見 `business-logic-model.md`「本單元的驗證強度」表『回應值與資料庫一致』一列」或「見 AC-1.5」，移除對不存在規則 ID 的指涉。 |

兩項新發現皆源自 iteration 1 修正本身新增的內容（Q3 的 Revision 區塊、R1 節的三種失敗模式對照表），而非殘留的原始問題——符合「修正引入的缺陷不受原始輪次上限拘束」的處理原則，本次據實記載並列入計數。

#### 額外查證：R1 必填宣告的行為主張（本輪要求的獨立實測）

三份 artifact 現在把「構造點漏傳必填欄位→構造當下拋錯→端點回 500」列為本單元**唯一**的結構性保護（R1）。本輪對此做了獨立實測，不採信文件自身的敘述：

- 依 `backend/requirements.txt`，`pydantic`／`fastapi[standard]` 皆未 pin 版本；以當前可解析到的最新版本（`pydantic==2.13.4`、`fastapi==0.141.1`）在隔離環境重建 `UserSchema` 的精簡版（沿用既有欄位 + 兩個依 R1 設計、無預設值的新欄位），呼叫 `UserSchema(id=1, username="a", is_active=True)`（刻意漏傳新欄位）：**確認拋出 `pydantic_core.ValidationError`**（`is_stale / Field required [type=missing]`），與文件主張一致。
- 確認 `class Config: orm_mode = True` 在 Pydantic 2.x 下觸發 `PydanticDeprecatedSince20` 警告但**不影響**上述行為（`orm_mode` 只是 `from_attributes` 的舊名，與必填欄位驗證無關）——文件與既有程式碼皆未受此既有技術債影響。
- 確認 `user_router.py` 全檔零 `try/except`（僅 3 處 `raise HTTPException`，皆與構造回應物件無關），`main.py` 的 `FastAPI(title=...)` 未設 `debug`、未註冊任何 `exception_handler`，`add_middleware` 僅掛 `CORSMiddleware`——因此 `ValidationError` 一旦在路由函式內被拋出，會不受攔截地往上傳播，交由 Starlette 預設的 `ServerErrorMiddleware` 處理，回應 500。

**結論：文件對 R1 行為的主張成立，非未經查證的信任。** 這也代表 Finding 1（Iteration 2 新發現）與 Finding 2（R4 筆誤）之外，R1 本身作為本單元唯一結構性保護的核心論證是可信的，不構成額外的 Critical 疑慮。

#### 程式碼查核（是否仍無真實程式碼）

四份 artifact（含本檔）逐一確認：僅 `business-logic-model.md` L20、L48 兩處 fenced code block，內容為 ASCII 流程圖與其文字 fallback，非任何語言的可執行程式碼；`business-rules.md`／`domain-entities.md`／`functional-design-questions.md` 全篇無 fenced code block。符合 functional-design 階段不下探到程式碼實作的要求。

#### Validation Tool Results

| Tool / 查證 | Result | Interpretation |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | PASS（`Cloud-360 repository contract validation passed.`） | Repo 層與 record 層必要文件、必要文字、文件語言、禁止路徑／內容檢查均通過 |
| 程式碼實測：R1 必填欄位缺漏時的拋錯行為 | `pydantic==2.13.4` 下 `ValidationError` 確實在構造當下拋出；`user_router.py` 無 try/except 攔截；`main.py` 無自訂 exception handler | 支持文件「構造當下失敗、端點回 500」的核心主張，本輪未發現理由推翻它 |
| 程式碼實測：三端點 `response_model` 宣告與 `exclude_unset`／`exclude_none` 使用數 | 三端點（L437/562/658）皆宣告 `response_model`；全 repo `exclude_unset`／`exclude_none`／`exclude_defaults`／`response_model_exclude` 使用數為 0 | 支持 iteration 1 修正後「key 集合由回應模型宣告決定，與構造點傳了什麼無關」的因果論證 |
| 對照 `unit-of-work-dependency.md`（U2/U3/U5 邊定義） | `U3→U2`（HTTP）、`U3→U5`（型別）、`U5→U2`（規格） 三條邊與本檔「介面表」的兩條邊敘述一致 | Finding 4（iteration 1）修正正確，無新增矛盾 |
| 對照 U1 `business-rules.md`（唯一授權讀取的跨單元檔） | 時區契約段落（L78-97）與本單元 R2／R3 的引用逐字對應 | Finding 2（iteration 1）修正正確，無新增矛盾 |
| 全篇 grep `R4`／`R0` | `R0` 兩處皆正確標明「U1 的 R0」；`R4` 僅一處，且本單元不存在 R4 定義 | 支持本輪 Finding 2（新發現）：`R4` 為斷鏈引用 |

#### Summary

Iteration 1 的四項 finding（1 Critical、2 Major、1 Minor）逐項覆核皆**已妥善解決**，且對其中最關鍵的 Critical 修正——「R1 必填宣告在構造當下拋錯、端點回 500」——本輪額外做了獨立的程式碼實測（重建 `UserSchema` 精簡版、確認零攔截路徑），結果與文件主張相符，不是文件自我背書。修正過程本身確實新引入兩項可歸責於 iteration 1 編輯動作本身的瑕疵：Q3 問題檔的 Revision 區塊宣稱「已更正」但選項本文實際未被編輯，留下與 Revision 直接矛盾的殘留敘述（Major，因為它是「宣稱已修但實未修」的無依據斷言，且與 iteration 1 finding 1 要求的「不再自相矛盾」目標正面相關）；`business-rules.md` R1 節新表格內一處指向不存在的「R4」（Minor，純引用錯誤，實質內容在別處已正確齊備）。兩項新發現總計 1 Major、1 Minor、0 Critical，未超過 READY 的門檻（zero Critical、≤2 Major）。三份主要 artifact（`business-rules.md`、`business-logic-model.md`、`domain-entities.md`）之間對「三種保護機制各防什麼」的敘述現已完全一致，且無任何一項修正推翻或弱化已核可的上游契約（`unit-of-work-dependency.md`、U1 契約、`stories.md` AC-1.5／DoD）。**判定 READY**——建議修正上述兩項新發現（皆為文件內部一致性的收尾動作），但不阻塞本站關閉。

---

## Revision 1（2026-08-11）— 分頁（C-9 後端半）

> reviewer Revision 1 Finding 1：本檔在 Revision 1 初稿中**完全未更新**，與同單元的
> `business-rules.md`／`domain-entities.md` 自相矛盾（那兩份已宣告 envelope 是第四個
> 構造點，本檔的「本單元做什麼」卻仍只提三個構造點）。本節補齊。

### 本單元做什麼（Revision 1 更新）

除了「三個 `UserSchema` 構造點各加兩個欄位」之外，本單元現在還擁有**清單端點的分頁契約**：

| 面向 | 內容 |
|---|---|
| 查詢參數 | `page`／`page_size`，以框架原生範圍約束宣告 |
| 查詢邏輯 | `ORDER BY id` → offset → limit，外加一次**獨立的計數查詢**取 `total` |
| 回應形狀 | 具名 envelope `UserListPage`（第四個回應構造點） |
| 錯誤路徑 | 非法參數回 **422**（框架產生，不進處理函式） |

**仍然零資料庫變更** —— 分頁不新增表、不新增欄位、不新增索引（既有的 `id` 主鍵索引已足以支撐 `ORDER BY id` ＋ offset）。本單元的 DDL 影響面與 Revision 1 之前相同。

### 觸發點（Revision 1 更新）

由「三個回傳使用者物件的 API 端點」擴為：**三個回傳使用者物件的端點 ＋ 清單端點的分頁查詢路徑**。後者是同一個端點的同一次請求，但構造的是不同的模型（`UserListPage` 而非 `List[UserSchema]`）。

### 本單元的驗證強度（Revision 1 更新）

| 行為 | 驗證方式 | 能否真的失敗 |
|---|---|---|
| 三個構造點的兩個新欄位 | `TestClient` 斷言欄位集合與**值** | ✅ |
| envelope 的四個分頁值 | `TestClient` **值**斷言（含「總數少於一頁」的分辨情境） | ✅ |
| `total` 非由 `len(items)` 導出 | `TestClient`（多頁情境下 `total != len(items)`） | ✅ |
| `ORDER BY id` 未被移除 | `TestClient`（同一頁請求兩次順序相同） | ⚠️ 弱 —— 不穩定排序未必每次都露餡 |
| 非法參數回 422 且不洩資料 | `TestClient` | ✅ |
| 超出範圍回 200＋空＋頁次回顯 | `TestClient` | ✅ |
| 非分頁參數不改變結果 | `TestClient` | ✅ |

### 與 Q1（拒絕共用工廠）的關係（reviewer Revision 1 Finding 2）

Q1 在 Revision 1 之前比較了「三處各自手寫」與「單一共用工廠」，並選了前者，理由是工廠會被迫決定要不要順帶修 `requested_role` 的既有漏傳缺陷。

**實作採用了工廠，這是刻意的偏離，理由如下**：

1. **application-design 的 C-4 明文允許** —— 其設計約束逐字為「兩個新欄位在回應模型上**不得設置可靜默通過的預設值**，**或**改以**單一的共用工廠函式**（接受使用者物件與當下時刻）使三個構造點不可能分歧」（reviewer Iteration 2 N1：初稿漏抄括號子句，已補回 —— 該子句正是實作採用的簽章形狀）。工廠是該站列出的兩個合法手段之一，本站的 Q1 是在更早、資訊較少的時點選了另一個。
2. **Q1 駁回的具體代價沒有發生** —— 兩個 PUT 端點呼叫工廠時單純不傳 `requested_role`，沿用參數預設值，行為與駁回前逐字相同，不需要任何「繞道」，也沒有被迫處理範圍外的既有缺陷。
3. **實際採用的是兩者兼具**：欄位無預設值（Q1 選項的核心保護）**且**走共用工廠（第四個構造點加入後，三處變四處，各自手寫的分歧風險隨構造點數量上升）。

依 `project.md` 的「下游查證推翻的是選項的理由而非決定本身」處置原則的鏡像情形：這裡被推翻的是**駁回理由**，而較晚、資訊較多的 application-design 已明文允許該手段，故不回改 Q1 的問答紀錄，改在此記明偏離與依據。
