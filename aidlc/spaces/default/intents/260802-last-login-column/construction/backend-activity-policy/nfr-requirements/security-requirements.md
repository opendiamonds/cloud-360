# Security Requirements — U1 `backend-activity-policy`

> Stage: nfr-requirements（Construction 3.2）· Unit: `backend-activity-policy`（kind: service）
> 上游來源：`../functional-design/business-logic-model.md`、`business-rules.md`、`../../../inception/requirements-analysis/requirements.md`（下稱 requirements）、`../../../inception/application-design/component-methods.md`、`decisions.md`。
> 問答定案：Q1=A（設計上界）、Q2=A（不額外加密，寫明理由）、Q3=A（**僅「不要求告警」部分生效**；級別沿用 3.1 Q2=A 的警告級，見 R-1 的更正說明）。事實查證 S1〜S5 見 `nfr-requirements-questions.md`。

## ADR-0006 四面向逐項判定（hard constraint，缺一不可）

`project.md ## Mandated` 明文要求：涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出中**明列 security 影響與處置**，**不得僅以「已有 ADR-0006」帶過**。判定為不適用者一律附理由，不留空白。

| 面向 | 判定 | 影響與處置 |
|---|---|---|
| **IAM／授權** | **不適用（本單元）** | 本單元**不改變任何權限機制或權限資料**。誰能讀取最後活動時間，由既有的端點層檢查決定（requirements FR-4.2 已定案不做欄位級控制）；權限**資料**的變更屬 U4。本單元的寫入路徑不涉及授權判斷 |
| **Encryption** | **不額外保護**（Q2=A 定案） | 沿用資料庫現有的傳輸與靜存保護層級，**不加欄位級加密**。理由見下方 §encryption 的判定理由 |
| **Network exposure** | **不適用** | 本單元**不新增任何端點、不改變任何路由、不對外開放新的介面**。它是既有認證依賴內的一段邏輯，暴露面與變更前完全相同 |
| **Audit logging** | **分兩層判定**（見下方同名小節） | ①**本單元的寫入動作是否需要稽核軌跡** → 不需要；②**requirements 層級的 audit logging 關切（C-7／FR-4 的易失性）與本單元的關係** → **不適用（本單元），該關切屬 U4** |

## Encryption 的判定理由（不得省略）

| 論點 | 內容 |
|---|---|
| **同表敏感度對照** | 最後活動時間與同表已有的帳號名稱、角色、啟用狀態、授權狀態屬**同一敏感度層級**，而後者**現在就沒有欄位級加密** |
| **單獨加密不提升實際安全性** | 能讀到該表的攻擊者同時能讀到帳號與角色；單獨保護時間欄位不改變攻擊者的獲益 |
| **明確的功能代價** | 加密後逾期判定的比較必須搬到應用層逐列解密 —— 與 U2 的清單端點（一次回傳全部使用者）直接衝突，且會使排序與查詢失效 |
| **範圍** | 全表或全庫的靜存加密是基礎設施層決策，屬 AD-5 明確排除的範圍 |

**結論**：不加欄位級加密。這是**經判定的決定**，不是未考慮。

## Audit logging 面向（兩層判定，比照 IAM 列的處理深度）

> **本節於 reviewer iteration 1 後更正。** 初版以「本單元就是 audit logging 的實作」這個關於**存在理由**的陳述，取代了兩個真正該回答的問題，且處理深度不及同表的 IAM 列（IAM 列正確判定「屬 U4」）。此處分開回答。

### 層次一：本單元的寫入動作本身是否需要稽核軌跡？

**判定：不需要。**

| 論點 | 內容 |
|---|---|
| **性質差異** | 本單元的寫入**產生**稽核資料，它不是一個需要被另外稽核的「變更」。為「記錄活動」這個動作再記錄一次，會產生無限遞迴的稽核需求 |
| **與同表其他欄位的對照** | 啟用狀態與授權狀態的變更**有**既有的稽核記錄機制，因為那些是**人為決策**；本欄位的寫入是**系統對事實的觀測**，無決策者可歸屬 |
| **可否事後追溯** | 欄位值本身即為結果；寫入失敗有 R-1 的日誌。兩者合計已足以回答「這個值為何是這樣」 |

### 層次二：requirements 層級的 audit logging 關切與本單元的關係

**判定：不適用（本單元）。該關切屬 U4。**

requirements 的 ADR-0006 四面向表對 Audit logging 的判定，針對的是 **FR-4 的權限矩陣變更**及其記錄的易失性（保存期約等於兩次部署間隔，requirements C-7），處置為「記為已知限制並向下游傳遞，持久化另立 intent」。

**那整組關切落在 U4，不落在本單元** —— 與同表 IAM 列的判定一致（權限資料的變更屬 U4）。

### 產品定位說明（不取代上述兩項判定）

| 面向 | 內容 |
|---|---|
| **本單元的定位** | 最後活動時間**本身就是稽核資料** —— 這個 intent 的存在理由就是讓稽核者看得到帳號的活動狀況。**這是產品定位說明，不是 ADR-0006 的判定** |
| **記錄的內容** | 僅時間戳，**不記錄請求路徑、來源位址或請求內容** —— 那會擴大資料的敏感度並超出上游定案的範圍 |
| **保留期** | 只保留最後一次，無歷史（上游已定案） |
| **已知限制** | 權限變更稽核記錄的易失性（requirements C-7）**屬 U4**，見上方層次二的判定 —— 此處僅為交叉引用，非本單元的待辦 |

## SEC-1 不得記錄超出時間戳的資料

**需求**：活動記錄**只寫入時間戳**。不得順帶記錄來源位址、使用者代理、請求路徑或任何請求內容。

**理由**：那會把一個「最後活動時間」欄位變成行為追蹤記錄，敏感度層級隨之改變，而上游的資料保護判定（見上）是建立在「僅時間戳」這個前提上的。

## SEC-2 失敗不得洩漏敏感資料

**需求**：寫入失敗的記錄（見 `reliability-requirements.md` R-1）**不得包含**憑證、權杖或完整的請求內容。記錄例外型別與訊息即可。

**依據**：`team.md ## Forbidden` 明文禁止把敏感資料寫進任何 log。

## SEC-3 不改變認證流程的判定結果

**需求**：本單元的觸發**不得**改變任何請求的認證或授權結果。無論寫入成功或失敗，請求的後續處理完全不受影響。

**依據**：C-2 的交易契約（失敗先復原再記錄）已保證此點；本條把它明列為 security 需求，因為「在認證流程中插入一段可能失敗的邏輯」若處理不當，就是一個可用來干擾認證的面向。

**相關的既有判定**：觸發點在**停用檢查之後**（3.1 的 R0），故已停用帳號的請求走不到記錄邏輯 —— 這既是稽核正確性的要求，也讓本單元的執行完全落在「已通過完整認證檢查」的範圍內。

---

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-09T23:23:09Z
**Iteration:** 1

本輪不採信本站「訂需求、不訂實作」與「Q1〜Q3 定案有效」的宣稱，逐項回 repo 實測 S1〜S5，並把五份 artifact 互相比對、再比對 3.1（`business-logic-model.md`／`business-rules.md`，已 reviewed READY 兩輪）與 `inception/requirements-analysis/requirements.md`（已 reviewed READY 兩輪）的逐字內容。

### S1〜S5 逐項實測

| # | 查證 | 本站宣稱 | 實測結果 | 判定 |
|---|---|---|---|---|
| S1 | 觀測性依賴 | `backend/requirements.txt` 無 prometheus／opentelemetry／statsd／psutil | `grep -iE` 全 `requirements.txt` 無匹配 | **成立** |
| S2 | 連線池設定 | `database.py:23` 為 `create_engine(DATABASE_URL)`，未帶連線池參數 | 逐字核對 `database.py:23`：`engine = create_engine(DATABASE_URL)`，`sessionmaker` 亦僅 `autocommit=False, autoflush=False` | **成立** |
| S3 | 部署資源限制 | `deploy/docker-compose.deploy.yml` 無 replicas／cpus／mem_limit | 檔案存在，`grep` 全檔無匹配 | **成立** |
| S4 | 帳號規模 | 啟動流程種入 11 個預設帳號 | `database.py` 的 `default_personas` 清單逐一核對，含 `fiona`(Security_Reviewer) 等，人工計數為 11 | **成立** |
| S5 | CI 效能測試 | `ci.yml` 四道關卡無效能測試步驟 | `grep -inE "perf|benchmark|load test|locust"` 全檔無匹配 | **成立** |

S1〜S5 全部成立，Q1=A（以設計上界取代延遲預算）的事實依據站得住腳；且進一步查證發現 requirements NFR-1 自身的驗收標準本就是「同一帳號 5 分鐘內至多一次寫入（同 FR-1.3）」而非延遲數字（`requirements.md` L85），故 P-1 的上界表述**逐字命中**上游 AC，並非把問題換簡單。P-2「絕大多數請求只做一次記憶體內時間比較」的機制性主張，經回頭核對 `backend/services/auth.py:39-64` 的 `get_current_user`（單一 `db.query(User).filter(...).first()`，`User` 無任何 `deferred()` 欄位）確認成立：判定輸入確為隨查詢一併載入的欄位值，不觸發額外查詢。P-3「沿用既有工作階段、自行提交」與 3.1 的 C-2 契約（借用不獨佔）不衝突，兩者針對的是「開不開新連線」與「提不提交」兩件不同的事，如實站得住腳。ADR-0006 四面向表結構完整（四項皆有判定與理由，無空白），`Encryption` 判定的「同表既有欄位同等敏感度且現在就沒加密」一句經核對 `schema.sql` L8-13（`password_hash`／`role`／`is_active` 均為明碼欄位、`schema_rbac.sql` 全檔無 `pgcrypto`／`ENCRYPT`）確認屬實。`python3 scripts/validate_repo_contract.py` 通過；五檔均無程式碼區塊、無 `def`／`class`／SQL 語句，未越界做 3.3／3.5 的事。

### Findings

| # | 嚴重度 | 位置 | 問題 | 建議修正 |
|---|---|---|---|---|
| 1 | **Critical** | `reliability-requirements.md` R-1（「級別｜錯誤級（非警告級）」）vs `functional-design/business-logic-model.md`「失敗處置（Q2=A 定案）」表（「記錄層級｜警告」） | **本站 R-1 把「同一個寫入失敗事件」的記錄層級由 3.1 已核可（reviewer READY，iteration 2）的『警告』悄悄改為『錯誤級』，且未依本專案已示範過的 Revision 協定揭露。** 兩份文件描述的是同一件事：業務邏輯模型的「主流程」明寫「例外 → 先復原工作階段 → **記錄警告**（含使用者識別、例外型別與訊息）→ 返回未寫入」，其「失敗處置（Q2=A 定案）」表逐格定義「記錄層級｜**警告**（沿用既有補欄函式的形狀）」——這是 3.1 `functional-design-questions.md` Q2 的人工定案（選項 A 明確拒絕選項 B「錯誤層級，含完整堆疊」，理由是「把輔助性副作用的失敗提升到與請求失敗同級，會稀釋錯誤層級的訊號價值」），且該站已通過 reviewer 兩輪 READY，Q2 本身**沒有任何 Revision 註記**（同檔的 Q3 有明確的 Revision 段可對照，顯示本專案已有揭露反轉的既定作法，Q2 未走這條路徑代表它從未被標記為可異動）。本站 `nfr-requirements-questions.md` Q3 的選項 C 提到「沿用既有補丁的警告單行形狀」時只把它當成「既有補欄補丁」（schema migration 的舊有樣式）的代稱，完全未點名這正是 3.1 Q2=A 已鎖定、且用於**同一個寫入失敗事件**的決定；`reliability-requirements.md` R-1 的理由段（「既有補欄補丁的失敗處置是警告級單行，且不含例外型別」）同樣只拿「補欄補丁」的原始樣式做對照，未提及 Q2=A 早已在此基礎上加強為『警告＋使用者識別＋例外型別＋例外訊息』並鎖定為警告層級。後果是**兩份同屬本單元、同時餵給 code-generation 的 artifact 對同一行為給出互斥指示**：依 `business-logic-model.md` 實作會寫 `logger.warning(...)`，依 `reliability-requirements.md` 實作會寫 `logger.error(...)`，兩者不可能同時成立，構成典型的「需求錯誤會導致實作出錯」 | 二擇一並依 `team.md` 的既定 Revision 協定明寫：①在 `reliability-requirements.md` R-1 加 Revision 段，逐字指出這是對 `business-logic-model.md`「失敗處置（Q2=A 定案）」記錄層級的推翻，附推翻理由（持續發生於請求路徑、對使用者不可見 vs 補欄補丁為啟動期一次性事件），並回 `business-logic-model.md`／`functional-design-questions.md` Q2 補一則同型 Revision 註記（比照該檔 Q3 的既有範例）；或②撤回 R-1 的層級改動，維持 `警告` 並在 R-1 中改寫理由段為「沿用並強化 Q2=A 已鎖定的警告層級（已含使用者識別、例外型別、例外訊息），不再重新提升層級」。無論哪一種，兩份文件的記錄層級最終必須逐字一致 |
| 2 | Major | `security-requirements.md` ADR-0006 四面向表「Audit logging」列（「適用，且本單元是它的實作」）及其後同名小節 | **Audit logging 面向的判定回答了一個自我指涉的替代問題，而非 ADR-0006 該面向原本要問的問題，且與同一張表的 IAM 列處理方式不一致。** `inception/requirements-analysis/requirements.md` 的意圖層 ADR-0006 四面向表（已 reviewed READY）對 Audit logging 的判定明確針對**FR-4 的權限矩陣變更**：「本次權限矩陣變更會產生一筆變更記錄，但該記錄為易失性（保存期約等於兩次部署間隔，見 C-7）。處置：記為已知限制並向下游傳遞，持久化另立 intent」——這與本單元完全無關，本檔 IAM 列自己也正確判定「權限**資料**的變更屬 U4」而非本單元。但輪到 Audit logging 列時，本檔不是比照 IAM 列給出「不適用（本單元），該關切（C-7）屬 U4」的平行判定，而是把問題換成「最後活動時間本身就是稽核資料」——這是一個關於**本單元存在理由**的陳述，不是關於**本單元的變更是否需要被稽核**的判定，兩者是不同層次的問題。實質後果：本檔從未評估「本單元在每個已認證請求上寫入一個與 `is_active`／`authorization_status` 同表、同敏感度欄位的動作，是否需要任何形式的稽核軌跡」這個真正落在本單元範圍內的問題；文中唯一觸及 C-7 的地方（「已知限制（繼承自上游）」小節）被放在 Audit logging 判定**之後**、作為附註而非判定本身，讀者若只看判定列會誤以為本單元已完整承接 requirements 層級的 audit logging 關切，但實際上該關切（C-7／FR-4）仍懸而未決地屬於 U4，本檔只是換了個容易回答的問題來自我肯定 | 把 Audit logging 列拆成兩層判定，比照 IAM 列的處理深度：①**本單元是否需對自己的寫入動作提供稽核軌跡**——給出明確判定與理由（例如：不需要，因為寫入本身即是稽核資料的產生，不是需要另外稽核的「變更」；或需要，理由為何）；②**requirements 層級 Audit logging 判定（C-7／FR-4 的易失性稽核記錄）與本單元的關係**——比照 IAM 列，明寫「不適用（本單元），該關切屬 U4」而非放在判定之後的附註。「最後活動時間本身就是稽核資料」這句可以保留，但須明確標示為「本單元的產品定位說明」，不得取代①②兩項判定 |
| 3 | Minor | `reliability-requirements.md` R-1「內容」列（「必須包含例外型別」） | 與 3.1 `business-logic-model.md` 已鎖定的記錄內容（「使用者識別、例外型別、例外訊息」三項，且逐項附「少了任一項即失去診斷價值」的理由）相比，R-1 只重申其中一項，未言明是**取代**（只需型別即可）還是**沿用並強調**（三項都要，型別是其中最關鍵者）。與 Finding 1 同源（Q3 未意識到自己在改動 Q2=A 已定的內容），但內容缺口比層級缺口更容易被讀者以「R-1 更新」的字面意思誤讀為只需一項 | R-1 內容列明寫「使用者識別、例外型別、例外訊息（沿用 `business-logic-model.md` Q2=A 已定的三項，本列僅強調其中對可搜尋性最關鍵的例外型別）」，消除取代／沿用的歧義 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `python3 scripts/validate_repo_contract.py` | PASS | Repo contract 通過，五檔語言、必要文字、禁止路徑／內容均無違反 |
| `required-sections`（人工核對，sensor 未在本次會話執行） | 五檔 H2 數為 6／6／5／6／3，均 ≥2 | 通過 |
| `upstream-coverage`（人工核對） | 五檔檔頭均列出 `business-logic-model.md`／`business-rules.md`／`requirements.md`（本站 consumes 的三項 required 上游） | 通過 |
| `linter`／`type-check` | 五檔無任何 TS／JS／TSX 程式碼區塊 | N/A（正確 —— 本站不應有程式碼） |
| 程式碼越界檢查（人工，`grep '```'`／`def `／`class `／SQL 語句） | 五檔零匹配 | 未越界做 3.3／3.5 的事 |

### Summary

事實面（S1〜S5、ADR-0006 四面向的技術主張、P-1〜P-3 的機制性宣稱）逐項回 repo 實測全部成立，`Q1=A` 以設計上界取代延遲預算的論證紮實且直接命中 requirements NFR-1 自身以節流頻率為驗收標準的字面要求，並非規避。但本輪找到一個**不可與上游共存的直接矛盾**：`reliability-requirements.md` R-1 把 3.1 已核可（reviewer 兩輪 READY）的寫入失敗記錄層級從「警告」悄悄改為「錯誤級」，未依本專案已示範過的 Revision 揭露協定標註，形成兩份同時餵給 code-generation 的 artifact 對同一失敗事件互斥的記錄層級指示——這不是論證品質問題，是會讓實作者無所適從的責任交接破口，判 Critical。另一項 Major 出在 ADR-0006 四面向表的 Audit logging 判定：它用「本單元就是稽核資料的實作」這個自我指涉的產品定位陳述，取代了「本單元的變更本身是否需要稽核」與「requirements 層級的 audit logging 關切（C-7／FR-4）與本單元的關係」這兩個真正該回答的問題，且未比照同表 IAM 列的處理深度，讓一個 hard constraint 面向看似已判定，實則答非所問。兩項合計（1 Critical、1 Major）已超過 READY 的門檻。**判定 NOT-READY**（1 Critical、1 Major、1 Minor）。
