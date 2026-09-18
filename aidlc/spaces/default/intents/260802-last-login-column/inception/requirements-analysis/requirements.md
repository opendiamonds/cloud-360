# Requirements — 帳號最後活動時間（稽核欄位）

<!-- Stage: requirements-analysis（Inception 2.3）· 來源標籤定義見 requirements-analysis-questions.md 的 ## Sources。
     [Q<n>] 指本 stage 問題檔的已選答案；[intent:*]／[scope:*]／[feas:*]／[rm:*] 指上游 ideation artifact 的已確認決定；
     [kb:*] 指 reverse-engineering 產出的 codekb；[tp] 指 practices-discovery 核可的 team-practices；
     [dr:*] 指 practices-discovery 的 discovered-rules（已 promote 進 project.md 的 ## Mandated）；
     [pd] 指 practices-discovery 的 evidence；[raid:*] 指 feasibility 的 raid-log 條目；
     [scope:r2] 指 scope-document Revision 2；[ah:r1] 指 initiative-brief Revision 1；[tp:cs] 指 team-practices 的 ## Code Style；
     [impl] 指本站對 repo 現行程式碼的直接實測（引用時附檔名與行號），不是任何上游 artifact 的轉述。 -->

## 上游輸入

- **intent-statement**（`../../ideation/intent-capture/intent-statement.md`）：問題陳述（存取稽核需要帳號活動證據）、兩類受益者、成功指標。
- **scope-document**（`../../ideation/scope-definition/scope-document.md`，**Revision 2**）：**六項** Must 能力 (a)–(f) 與排除清單，本文件逐項展開為可測試需求。(f) 分頁於本檔 **Revision 1** 補入。
- **business-overview**（`aidlc/spaces/default/codekb/cloud-360/business-overview.md`）：平台定位與服務角色，界定本功能的業務脈絡。
- **architecture**（`aidlc/spaces/default/codekb/cloud-360/architecture.md`）：modular monolith + SPA 的分層與 RBAC 橫切關注點，界定需求的落點。
- **code-structure**（`aidlc/spaces/default/codekb/cloud-360/code-structure.md`）：既有模組組織與程式碼模式，界定實作面的既有約束。
- **team-practices**（`../practices-discovery/team-practices.md`）：本輪生效的三項測試底線，直接構成本文件的驗收要求。

## 意圖分析

**目標（非功能清單）**：讓存取稽核能回答「這個帳號是否仍在使用」這個問題，且答案是**可抄錄、可比對的證據**，而非印象或推測 [intent]。

達成此目標需要三件事同時成立：系統要**產生**活動證據（今日完全沒有，見 `[kb:architecture]`）、管理介面要**呈現**該證據且讓逾期帳號可即讀辨識、稽核角色要**取用得到**該介面。第四件事（小螢幕可用）源自 rough-mockups 階段確認的無障礙底線並經 scope Revision 1 納入 [rm:Q5a]。第五件事（清單分頁）源自 Construction 3.2 實測發現清單端點無分頁、無上限，經 scope Revision 2 納入 [scope:r2] —— 它不是稽核目標本身的一部分，而是讓前四件事在真實資料量下仍然可用的前提。

本功能**不是**要建立完整的活動稽核系統：不留歷史、不做匯出、不做排序篩選 [scope]。它是一個以最小成本讓稽核問題可被回答的欄位。

## 功能需求

### FR-1 記錄帳號最後活動時間（對應 Must (a)／PU-1）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-1.1 | 任何以有效憑證發出的請求，都更新該帳號的最後活動時間 | 以測試帳號發出任一需認證的請求後，該帳號的最後活動時間等於該請求發生的時刻（誤差在 FR-1.3 的節流窗內）[feas:Q1] |
| FR-1.2 | 只保留最後一次的值，不保留歷史 | 連續兩次活動後，系統中僅存在後一次的時間值 [intent:Q9] |
| FR-1.3 | 同一帳號的活動時間更新，寫入頻率不得高於**每 5 分鐘一次**；計時基準為**上一次成功寫入的時刻**（滑動視窗，非固定時間桶） | 自上次寫入起 5 分鐘內對同一帳號連續發出多個請求，資料庫寫入次數為 1；距上次寫入滿 5 分鐘（含）之後的下一個請求觸發第 2 次寫入 [Q3] |
| FR-1.4 | 資料模型須保留未來擴充為歷史紀錄的路徑 | 欄位設計不阻擋日後新增歷史表；本需求不定義擴充的具體形式 [intent:Q9] |

**設計階段必答項**：達成 FR-1.3 的手段（節流／彙整／非同步）由 application-design 選定，本文件只給約束不指定手段 [Q3]（承 raid-log R1）。

### FR-2 管理介面顯示欄位（對應 Must (b)／PU-2）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-2.1 | 使用者管理頁為每個帳號顯示最後活動時間 | 表格出現「最後活動時間」欄，位置在「角色」之後、「操作」之前 [rm:Q1] |
| FR-2.2 | 時間以絕對格式 `YYYY-MM-DD HH:MM` 顯示 | 顯示值可直接抄錄比對，不需換算 [rm:Q2] |
| FR-2.3 | 無活動紀錄的帳號**不套用逾期標示** | 上線前既有帳號的該欄無 `(!)` 圖示、不變色（語意判定；呈現形式見 FR-2.4）[feas:Q2] |
| FR-2.4 | 無紀錄態呈現為可聚焦的破折號 `—`，聚焦或 hover 時顯示說明文字 | 該欄顯示 `—`；以鍵盤 Tab 可聚焦該元素並讀到說明文字（文案於 refined-mockups 定案）[rm:Q4] [rm:Q4a] |
| FR-2.5 | **所有回傳使用者物件的端點都必須包含此欄位** | Admin 頁執行角色調整或啟停用後，該列的最後活動時間**不得變為空白** [Q4] |

FR-2.5 是本文件明確新增的防禦性需求：既有實作在兩個端點的回應構造中漏傳欄位 [pd]，新欄位若比照辦理會產生使用者可見的錯誤。既有的 `requested_role` 漏傳問題不在本 intent 修復範圍 [Q4]。

### FR-3 逾期未活動視覺標示（對應 Must (c)／PU-3）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-3.1 | 超過 **90 天**未活動的帳號帶視覺標示 | 最後活動時間早於當下起算 90 天者顯示 `(!)` 圖示且時間值變色 [Q1] [rm:Q3] |
| FR-3.2 | 標示不得僅以顏色傳達 | 圖示與文字替代同時存在，符合 WCAG 2.1 AA 的非色彩傳達要求 [rm:Q3] [rm:Q5] |
| FR-3.3 | 門檻為固定值，不提供設定介面 | 系統中無任何調整 90 天門檻的使用者介面 [scope]（Won't Have） |

門檻 90 天的依據：對應季度稽核節奏；本平台為內部工具，一季無任何活動足以構成「帳號可能該停用」的訊號 [Q1]。此值自本階段起為具體驗收值，不再是 assumption。

### FR-4 `Security_Reviewer` 檢視權限開通（對應 Must (d)／PU-4）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-4.1 | `Security_Reviewer` 取得使用者管理介面的檢視權限 | 該角色登入後導覽出現入口，可進入頁面並看到完整使用者清單 [intent:Q10] |
| FR-4.2 | 權限粒度維持現狀，不做欄位級控制 | 四個管理類角色皆可見本欄位，無角色間的欄位差異 [intent:Q11/Q12] [scope]（Won't Have） |
| FR-4.3 | 權限變更須在兩處預設值來源同步 | 兩處來源的該角色權限值一致，任一處未同步即視為未完成 [feas:T5] [raid:D1] |

**已確認的範圍事實**：此權限旗標同時解鎖使用者清單與升權申請佇列兩個頁面，經人工確認為可接受範圍，不縮窄、不回改上游 artifact [pd]。

### FR-5 行動響應式卡片改造（對應 Must (e)／PU-5）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-5.1 | 小螢幕改為卡片式佈局，桌面維持表格 | 於斷點以下每個帳號呈現為一張卡片，欄位以「標籤: 值」逐行呈現 [rm:Q5] |
| FR-5.2 | 逾期與無紀錄的標示規則在兩種佈局下一致 | 卡片中的 `(!)` 圖示與可聚焦破折號 `—` 的語彙與桌面完全相同 [rm:Q3] [rm:Q4] |
| FR-5.3 | 既有頁面功能在卡片佈局下全數可用 | 角色調整、啟停用、授權操作在小螢幕皆可完成，觸控目標不小於 44x44 [rm:Q5] |

斷點的具體數值於 refined-mockups 定案，以既有內容破版處為準 [rm]。

### FR-6 使用者清單分頁（對應 Must (f)／PU-6）（**Revision 1 新增**）

| # | 需求 | 驗收標準 |
| --- | --- | --- |
| FR-6.1 | 使用者清單端點不再一次回傳全部帳號，改以**頁碼式**分頁回傳 | 帳號總數大於每頁筆數時，單次請求回傳的帳號筆數等於每頁筆數，且不等於總筆數 [scope:r2] [ah:r1] |
| FR-6.2 | 回應須同時帶出足以呈現分頁控制的資訊：**總筆數、目前頁次、每頁筆數** | 回應中三個值皆存在且為數值；總筆數等於系統中符合查詢條件的帳號總數（非本頁筆數）[scope:r2] |
| FR-6.3 | 兩種佈局（桌面表格、小螢幕卡片）皆提供分頁控制 | 於斷點以上與以下皆可切換頁次；兩種佈局的分頁語彙一致 [scope:r2] [rm:Q5] |
| FR-6.4 | 請求的頁次超出實際範圍時，回應為**成功**且資料清單為空，分頁資訊照常帶出；**「目前頁次」回顯請求值，不夾到最後一頁** | 總共 2 頁時請求第 5 頁：HTTP 狀態為 200、資料清單長度為 0、總筆數與每頁筆數仍為正確值、**目前頁次為 5**（即請求值，非 2）；前端顯示空態並提供回到第 1 頁的方式 [Q7] |
| FR-6.5 | 頁面內操作（角色調整、啟停用、刪除）成功後**維持目前頁次，並以就地更新呈現結果**（不整份重抓） | 於第 2 頁停用一個帳號後，畫面仍在第 2 頁，且該列的狀態已更新；角色調整與刪除同理（刪除為就地移除該列）[Q6] |
| FR-6.6 | 分頁不改變逾期標示（FR-3）與無紀錄態（FR-2.4）的判定規則 | 同一帳號在任何頁次上的標示結果相同；標示的判定不依賴它出現在第幾頁 [scope:r2] |
| FR-6.7 | 分頁**不**引入排序或篩選 | 系統中無任何依最後活動時間排序或篩選清單的使用者介面 [scope:r2]（Won't Have，Revision 2 明確保留） |

**上線前置依賴（本站不代決）**：**每頁筆數**與**回應 envelope 的具體形式**由 application-design 定案 [scope:r2]，見 OQ-6。依 `project.md ## Corrections`（Must 能力含未定參數時不降級該能力，把「參數於指定階段定案」升格為上線前置依賴），FR-6 仍為 Must、與其餘五項一起上線才算完成；參數未定案則 Must 集合不可完整交付。

**跨層影響（非僅顯示層）**：FR-6.1／FR-6.2 改變的是**API 回應契約**，同時波及後端序列化（FR-2.5 的三個構造點所在模組）、型別契約與前端三層。依 `project.md ## Corrections`（改變 API 回應契約的能力不得被歸類為顯示類能力的完成條件），FR-6 為獨立的能力與獨立的驗收面，不併入 FR-2 的 Definition of Done。

**FR-6.5 對前端是行為變更，不是既有形狀的延伸**（reviewer Revision 1 Finding 1 更正）：三個操作的既有成功路徑**並不相同**（`frontend/src/pages/AdminPage.tsx:89`／`:113`／`:129` [impl]）。角色調整（`:89`）為 `setUsers((prev) => prev.map(...))` 就地更新，維持頁次無須改動；**啟停用（`:113`）與刪除（`:129`）現行皆呼叫 `fetchUsers()` 整份重抓，重抓後回到未帶頁次的清單，頁次會跳走** —— 要滿足 FR-6.5 就**必須把這兩條路徑改為就地更新**（刪除為就地移除該列）。Q6 已在三個選項中選定 A（就地更新），**「以目前頁次重抓」是被排除的 Option B，不是可選的替代實作**。實作時不得默認「沿用既有形狀即可」，那正是會產出違反 FR-6.5 成品的路徑。

就地移除會使該頁暫時少一列（不自動遞補下一頁的第一筆），這是 Q6=A 的直接後果、非缺陷；下次切頁或重新載入即恢復滿頁。

## 非功能需求

| # | 類別 | 需求 | 驗收標準 |
| --- | --- | --- | --- |
| NFR-1 | 效能 | 活動時間記錄不得成為請求路徑上的顯著負擔 | 同一帳號 5 分鐘內至多一次寫入（同 FR-1.3）[Q3] |
| NFR-2 | 無障礙 | WCAG 2.1 AA，全裝置適用 | 對比 4.5:1、鍵盤可達、screen reader 可讀；標示非僅色彩傳達 [rm:Q5] |
| NFR-3 | 安全 | 權限變更須通過 ADR-0006 security baseline 的**四面向**檢查，四項缺一不可 | 四面向逐項判定見下方「ADR-0006 四面向檢查」表，每項皆有明列的影響與處置（或「不適用」判定與理由）[dr:ADR-0006] |
| NFR-4 | 可測試性 | 授權矩陣變更需 allow/deny 雙向測試 | 存在測試同時驗證 `Security_Reviewer` 可檢視、且未獲授權角色不可檢視 [tp] |
| NFR-5 | 可測試性 | 新增或修改的 HTTP 端點需 `TestClient` 測試 | 存在測試斷言回應的 status code 與欄位集合（涵蓋 FR-2.5）[tp] |
| NFR-6 | 可測試性 | 前端資料形狀變更需 e2e 斷言 | 存在 Playwright case 斷言表頭出現該欄位、且至少一列顯示時間值或無紀錄態的破折號 `—` [tp] |
| NFR-7 | 相容性 | 既有頁面功能不得因本變更退化 | 前端回歸驗證涵蓋角色調整、啟停用、授權操作 [scope] |
| NFR-8 | 安全 | **兩個**分頁查詢參數（頁次、每頁筆數）皆須在系統邊界驗證，非法值不得傳入資料查詢層 | **每頁筆數**：非數值、負數、零、超過上限者皆被拒絕或夾到合法範圍。**頁次**：非數值、負數、零者皆被拒絕或夾到合法範圍（**注意**：頁次「合法但超出實際範圍」不屬非法值，其行為由 FR-6.4 定義，兩者是不同判定）。兩者皆不得出現未處理例外 [scope:r2]（承 `phases/construction.md`「Validate and sanitize all inputs at system boundaries」） |
| NFR-9 | 無障礙 | 分頁控制符合 NFR-2 的同一底線 | 分頁控制鍵盤可達、目前頁次可被輔助技術讀出、非僅以顏色表達目前頁次 [rm:Q5] |
| NFR-10 | 可測試性 | 分頁行為需 `TestClient` 測試 | 存在測試斷言：分頁回應的欄位集合（FR-6.2 三個值）、以及超出範圍頁次回 200＋空清單（FR-6.4）[tp] |

NFR-4 至 NFR-6 直接承接 practices-discovery 核可的三項測試底線 [tp]，非本階段新創。NFR-8 至 NFR-10 為 **Revision 1 新增**，承接同一批底線在分頁能力上的落點（NFR-10 是 NFR-5「端點變更需 `TestClient` 測試」對 FR-6 的具體化，非新規則）。

### ADR-0006 四面向檢查（對應 NFR-3）

`project.md` 的 `## Mandated` 逐字要求：涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出中明列 security 影響與處置，不得僅以「已有 ADR-0006」帶過 [dr:ADR-0006]。本 intent 變更權限矩陣，四面向逐項判定如下：

| 面向 | 判定 | 影響與處置 |
| --- | --- | --- |
| **IAM** | **適用** | `Security_Reviewer` 取得 `J3a` 檢視權限（FR-4）。該旗標同時解鎖使用者清單與升權申請佇列兩個頁面，範圍經人工確認可接受 [pd]。風險接受已記於 raid-log R3；權限值須在兩處預設值來源同步（FR-4.3） |
| **Encryption** | **不適用** | 本 intent 新增的欄位為活動時間戳，非憑證、非個人敏感資料；傳輸加密沿用既有的 Cloudflare Tunnel 邊界，未變更；靜態儲存沿用既有資料庫設定，未引入新的儲存位置或加密決策 |
| **Network exposure** | **不適用** | 未新增任何對外端點、未變更既有的網路邊界。FR-4 開通的是**既有頁面**的檢視權限（應用層授權），不是新的網路暴露面；對外入口仍為既有的單一反向代理與 Tunnel [kb:architecture] |
| **Audit logging** | **適用（帶已知限制）** | 本次權限矩陣變更會產生一筆變更記錄，但該記錄為易失性（保存期約等於兩次部署間隔，見 C-7）。處置：記為已知限制並向下游傳遞，持久化另立 intent [Q5]。本 intent 不使該限制惡化 |

#### FR-6 分頁的四面向判定（**Revision 1 新增**）

`project.md ## Mandated` 的四面向檢查是**逐項變更**的義務，不是逐 intent 一次即可。FR-6 改變既有端點的回應契約與查詢輸入，故獨立判定；四項缺一不可，判為不適用者一律附理由：

| 面向 | 判定 | 影響與處置 |
| --- | --- | --- |
| **IAM** | **不適用** | FR-6 不新增、不移除、不修改任何角色或權限值；能看到使用者清單的角色集合在分頁前後完全相同。分頁只改變**同一批已授權資料**的回傳批次大小 [scope:r2]（(f) 的能力定義本身不涉及角色或權限）；清單端點的授權依賴鏈（`backend/services/user_router.py:439` 的 `require_story_action("J3a", "view")`）未變 [impl] |
| **Encryption** | **不適用** | 未新增資料項、未改變傳輸或靜態儲存的加密邊界；回應內容的欄位集合擴充（分頁資訊）不涉及憑證或個人敏感資料。傳輸邊界仍為既有的 Cloudflare Tunnel [kb:architecture] |
| **Network exposure** | **適用（改善）** | 未新增端點、未變更網路邊界，但**既有端點原本無分頁、無上限、回傳全部帳號**（[scope:r2] 的觸發事實）。導入分頁使單次回應的資料量與查詢成本有界，降低資源耗盡與大量資料一次外洩的暴露面。**新引入的攻擊面是查詢參數**，處置為 NFR-8 的邊界驗證（非法值不得傳入查詢層） |
| **Audit logging** | **不適用** | FR-6 為唯讀查詢行為的變更，不產生狀態異動、不需新增稽核記錄。系統既有的稽核寫入點（`backend/services/user_router.py` 的 `_audit_append` 共 7 個呼叫點 [impl]）**全部位於狀態異動路徑**，其中與本 intent 相關者為角色變更（`:699`，其易失性限制見 C-7）；`list_users`（`:438`）不在其中，FR-6 不觸及任何一個呼叫點 |

## 約束

| # | 約束 | 影響 | 來源 |
| --- | --- | --- | --- |
| C-1 | 系統無任何既有活動紀錄，且無可回填來源 | 上線時所有既有帳號的值為空，以無紀錄態呈現（可聚焦破折號，見 FR-2.4）；此空窗已被接受 | [feas:Q2] [rm:Q4] |
| C-2 | 專案無資料庫遷移框架；結構變更靠服務啟動時自動補齊 | 部署後服務必須完成一次重啟，變更才生效 | [feas:T3] |
| C-3 | 重跑整份資料庫初始化腳本會重置角色權限設定 | 部署程序必須排除「重跑整份腳本」作為本次變更的套用手段 | [feas:T4] |
| C-4 | 資料庫結構或 seed 變更須同步更新部署資產（blocking） | `schema_rbac.sql` 與 `DEPLOY.md` 未同步即不得標示相關階段完成 | [raid:D1] |
| C-5 | 既有時間戳慣例為帶時區的資料庫層預設值 | 新欄位循此慣例以維持一致性 | [kb:code-structure] |
| C-6 | 前端資料抓取形狀受 lint 規則約束 | Admin 頁新增欄位若需額外資料源，必須沿用既有的抓取／狀態更新拆分形狀，否則 CI 紅燈 | [pd] |
| C-7 | 權限變更的稽核記錄為易失性 | 該記錄的實際保存期約等於兩次部署間隔；本 intent 不修復，記為已知限制 | [Q5] [pd] |
| C-8 | 雲端供應商 production 環境不在本 repository 範圍 | 本功能僅及自有 staging | [intent] |
| C-9 | 既有使用者清單端點無分頁、無上限，一次回傳全部帳號 | FR-6 改的是**既有端點的回應契約**，不是新端點；所有既有消費端都會看到新形狀，型別契約與各消費端的呈現皆須同步 | [scope:r2]（**Revision 1 新增**） |
| C-10 | 前端三個頁面內操作的既有成功路徑**並不一致**（**Revision 1 修訂**，reviewer Finding 1；下列行號皆指 `frontend/src/pages/AdminPage.tsx`）：**角色調整**為就地 `map` 更新（`AdminPage.tsx:89`，不重抓）；**啟停用**（`AdminPage.tsx:113`）與**刪除**（`AdminPage.tsx:129`）皆呼叫 `fetchUsers()` **整份重抓** | FR-6.5 對角色調整為零改動；對**啟停用與刪除是行為變更**（重抓後頁次會跳走，**必須改為就地更新** —— Q6=A 已排除「以目前頁次重抓」的 Option B）。改法須遵循既有的抓取／狀態更新拆分與 `react-hooks/immutability`（回傳新物件），否則 CI 紅燈（同 C-6） | 行為事實：[impl]（`frontend/src/pages/AdminPage.tsx:89`／`:113`／`:129`）；lint 形狀約束：[tp:cs]（**Revision 1 新增**） |

## 假設

- [assumption] 90 天門檻適用於當前的團隊規模與使用型態；若帳號流動率明顯改變，此值需重新評估 [Q1]
- [assumption] 5 分鐘的節流間隔對「最後活動」的稽核語意足夠精確；若稽核方日後要求更高精度，需重新評估 FR-1.3 [Q3]
- [assumption] 本平台為內部工具，活動時間資料不受外部法規框架約束；此判斷未經法務獨立確認 [feas:Q4]
- [assumption] 單一欄位覆寫模式下不存在需要獨立保存政策的歷史資料；擴充為歷史紀錄時需重新評估 [Q2]
- [assumption] （開放問題）達成 FR-1.3 的具體手段未選定，屬 application-design 的必答項 [Q3]

## 範圍外

本章分三類，三者狀態不同，不可互相混同（承 scope-document 的分類）。

### 明確排除（Won't Have，承 scope-document）

- 登入／活動歷史紀錄 —— 僅預留資料模型擴充路徑，不實作
- 門檻 90 天的可設定介面 —— 固定值，不做管理介面
- 欄位級權限控制 —— 維持現行的角色 × 功能粒度
- 依最後活動時間排序／篩選 —— 顯示即可

### 另立項的既有缺陷（不是 Won't Have，是既有問題）

這兩項既非本 intent 的能力範圍，也非產品層級的排除決定；它們是本階段查得的既有缺陷，本 intent 不修復亦不使其惡化：

- 既有 `requested_role` 在兩個端點的漏傳 —— 另立項修復 [Q4]
- 權限變更稽核軌跡的持久化 —— 另立項處理 [Q5]

### 未承諾（沿自 scope-document，狀態不變）

- 稽核報表匯出 —— **不在範圍、亦不在排除清單**。此為 scope-document 刻意設立的第三類狀態，本階段不推定其未來去向，不得視為已排除或隱含在範圍內 [scope]

## 開放問題

| # | 問題 | 定案時點 |
| --- | --- | --- |
| OQ-1 | FR-1.3 的達成手段（節流／彙整／非同步） | application-design（raid-log R1 的必答項） |
| OQ-2 | 卡片式佈局的響應式斷點數值 | refined-mockups |
| OQ-3 | 無紀錄狀態的說明文案措辭 | refined-mockups |
| OQ-4 | PU-5 的前端回歸驗證涵蓋面 | 待 inception 後續階段界定 |
| OQ-5 | 既有頁面是否已有載入骨架的慣例 | refined-mockups 查證對齊 |
| OQ-6 | **每頁筆數與回應 envelope 的具體形式**（**Revision 1 新增**；為上線前置依賴，非可延後項） | application-design（[scope:r2] 指定） |
| OQ-7 | 分頁控制的視覺、版位與兩種佈局下的呈現（**Revision 1 新增**） | refined-mockups |

## Revision 1（2026-08-11）— PU-6 使用者清單分頁

**觸發來源**：`scope-document.md` Revision 2 新增 Must 能力 **(f) 使用者清單分頁**（PU-6）。本站以 Modify 模式疊加修訂。

| 變更 | 內容 |
| --- | --- |
| **新增** | FR-6.1〜FR-6.7（分頁能力的行為契約）、NFR-8（查詢參數邊界驗證）、NFR-9（分頁控制的無障礙）、NFR-10（分頁的 `TestClient` 測試）、C-9（既有端點無分頁無上限）、C-10（前端既有狀態更新形狀）、OQ-6（每頁筆數與 envelope，上線前置）、OQ-7（分頁控制的視覺）、ADR-0006 四面向對 FR-6 的獨立判定表 |
| **不變** | FR-1〜FR-5 全部條目與其驗收標準；NFR-1〜NFR-7；C-1〜C-8；既有假設；三類範圍外的分類與內容；Q1〜Q5 的答案 |
| **未於本站定案** | 每頁筆數、回應 envelope 形式 —— 由已核可的上游指定歸屬 application-design，本站不越權代決，改升格為上線前置依賴（OQ-6） |

### Revision 1 更正輪（2026-08-11，reviewer iteration 1 的 1 Critical + 1 Major + 3 Minor）

| # | 嚴重度 | 修正內容 |
| --- | --- | --- |
| 1 | Critical | C-10 原把「角色調整」與「啟停用」合併陳述為「皆不重抓清單」，回 repo 核對後不成立：只有角色調整（`AdminPage.tsx:89`）是就地更新，啟停用（`:113`）與刪除（`:129`）皆為 `fetchUsers()` 整份重抓。C-10 改為逐操作陳述並附行號；FR-6 新增「FR-6.5 對前端是行為變更」段，明寫啟停用與刪除**必須修改**；誤引的 `[tp:cs]` 改標新註冊的 `[impl]`（行為事實由實測承載，lint 形狀約束仍引 `[tp:cs]`）。問題檔 Q6 依「只修理由不改決定」的既有規則就地標註並加 R1 段。**決定未變。** |
| 2 | Major | NFR-8 的文字說「分頁查詢參數」（複數）但驗收標準只涵蓋每頁筆數，頁次的非法值無任何條目涵蓋。已補齊頁次的型別／範圍驗證，並明寫其與 FR-6.4「合法但超出範圍」的分界。 |
| 3 | Minor | FR-6 四面向判定表的 IAM／Encryption／Audit logging 三列補上來源標籤，與本文件既有的逐句可溯源慣例一致。 |
| 4 | Minor | FR-6.4 補定義「目前頁次」在超出範圍情境下的值：**回顯請求值，不夾到最後一頁**，使該欄位在邊界情境下可測。 |
| 5 | Minor | 第三條新增假設加註「本區分為本站的綜合判斷，非逐字承自 Q7 選項原文」，並於問題檔的 Consolidated Summary Confirmation 逐條列出三條新增假設後重新取得確認。 |

**Iteration 2 驗證輪後的收尾修正（三項 Minor，READY 後補）**：

| # | 修正內容 |
| --- | --- |
| A | `[impl]` 標籤原有 4／5 處未依其自訂定義附檔名行號。已全部補上（`AdminPage.tsx:89`／`:113`／`:129`、`user_router.py:439`、`user_router.py` 的 `_audit_append` 呼叫點與 `:699`／`:438`）。 |
| B | FR-6 四面向表 Audit logging 列原句脫離語境讀，會與 repo 內 7 個 `_audit_append` 呼叫點字面衝突。已改為明寫「7 個呼叫點全部位於狀態異動路徑、`list_users` 不在其中」，使該列自身即可核對。 |
| C | FR-6.5 補充段原寫「改為就地更新，**或以目前頁次重抓**」，等於重新開放 Q6 已排除的 Option B。已移除該替代方案並明寫其為被排除選項；FR-6.5 的需求本文同步恢復 Q6=A 的完整表述（維持頁次**且就地更新**），C-10 第三欄一併對齊。另補記就地移除會使該頁暫時少一列，屬 Q6=A 的直接後果而非缺陷。 |

**本次修訂新增的假設**（依 `project.md ## Corrections`，Assumptions 有增刪即須重新取得人工確認；本節對應的確認為問題檔 Revision 1 的 Consolidated Summary Confirmation，已作答 A）：

- [assumption] FR-6.5 的「就地更新不會與重抓結果不同」成立於「清單無互動排序／篩選、排序準則固定」這個前提 [Q6]；若日後解除排序／篩選的排除，此假設須重新評估
- [assumption] FR-6.4 選擇以 200＋空清單表達超出範圍的頁次，前提是「超出範圍」屬合法查詢而非不合法輸入 [Q7]
- [assumption] **（本區分為本站的綜合判斷，非逐字承自 Q7 選項原文）** FR-6.4（合法但超出範圍的頁次）與 NFR-8（型別／範圍非法的參數）是兩個不同的判定，不可互相取代；此區分已於 Revision 1 的更正輪一併寫入 NFR-8 的驗收標準與問題檔 Q7 的 Revision 註，並隨 Consolidated Summary Confirmation 重新取得確認

## Review — Revision 1（Iteration 2 驗證輪）

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-10T23:53:26Z
**Iteration:** 2

本輪為對抗式**驗證輪**：不採信「Revision 1 更正輪」表格（第 209-215 行）的自陳修正，逐項回頭核對 `requirements.md`、`requirements-analysis-questions.md`、`frontend/src/pages/AdminPage.tsx`、`backend/services/user_router.py`、`scope-document.md` Revision 2 的原文與行號，並另行搜尋修正動作本身可能引入的新問題。

### 逐項核對（iteration 1 的 5 項 findings）

| # | 原嚴重度 | 判定 | 查證方法與結果 |
| --- | --- | --- | --- |
| 1 | Critical | **達成** | 讀 `AdminPage.tsx` 第 77-133 行逐行核對：`handleRoleChange`（77-95）成功後 `setUsers((prev) => prev.map(...))`（第 89 行），不重抓；`handleToggleActive`（97-117）成功後呼叫 `fetchUsers()`（第 113 行），整份重抓；`handleDelete`（119-133）成功後亦呼叫 `fetchUsers()`（第 129 行），整份重抓。C-10（第 153 行）與 FR-6.5 補充段（第 99 行）引用的三個行號 `:89`／`:113`／`:129` **與實際檔案逐行相符**。`requirements-analysis-questions.md` Q6 前言（152 行）以 `~~刪除線~~` 標記原誤述並改標 `[impl]`，選項 A 本文（160 行）以同樣手法就地標註「此理由只對角色調整成立」，`[Answer]` 本身（166 行）**逐字未改寫**，並新增 R1 附加段落（168-176 行）完整記錄落差來源、對決定的影響（無）與對實作的影響（有）；R1 段落並逐字引用 `project.md ## Corrections`「下游查證推翻的是選項的理由而非決定本身時，只修理由不改決定」的原文，做法與該規則的措辭一致。`[tp:cs]` 重新核對 `team-practices.md ## Code Style`「資料抓取拆兩層」段，確認該段落確實只規範三層拆分與 `react-hooks/immutability`，不涉及「操作後是否重抓」——改標 `[impl]` 於事實層、保留 `[tp:cs]` 於 lint 形狀約束層（C-10 第三欄「行為事實：[impl]；lint 形狀約束：[tp:cs]」），兩者用途已正確區分，不再混用同一標籤支撐兩種不同主張。**Critical 真正關閉**。 |
| 2 | Major | **達成** | NFR-8（第 112 行）驗收標準現同時列出「每頁筆數」（非數值／負數／零／超過上限）與「頁次」（非數值／負數／零）兩組邊界條件，且明文以括號註記「頁次『合法但超出實際範圍』不屬非法值，其行為由 FR-6.4 定義，兩者是不同判定」，與 FR-6.4（第 90 行）「請求的頁次超出實際範圍時…回應為成功」互不重疊、互不矛盾，QA 可依此分別寫出「頁次＝0」（NFR-8）與「頁次＝5（總共 2 頁）」（FR-6.4）兩條不同測試。問題檔 Q7 R2 段（194-195 行）與此逐字對應。**Major 真正關閉**，需求文字「兩個分頁查詢參數」與驗收標準涵蓋範圍已一致。 |
| 3 | Minor | **達成** | 「FR-6 分頁的四面向判定」表（130-138 行）IAM 列現有 `[scope:r2]`＋`[impl]`，Encryption 列有 `[kb:architecture]`，Audit logging 列有 `[impl]`。逐一核對支持力：IAM 列「(f) 的能力定義本身不涉及角色或權限」——讀 `scope-document.md` 第 24 行「(f) 使用者清單分頁｜使用者清單不再一次回傳全部帳號…」，確認 (f) 定義全文未提角色或權限，`[scope:r2]` 支持成立；「清單端點的授權依賴鏈未變」——讀 `user_router.py` 第 439 行 `list_users` 仍為 `Depends(require_story_action("J3a", "view"))`，未變，`[impl]` 支持成立。Encryption 列「傳輸邊界仍為既有的 Cloudflare Tunnel」——與 iteration 2（原始輪）已核實的 `architecture.md` 網路邊界描述一致，`[kb:architecture]` 支持成立。Audit logging 列細節見下方「新發現 B」。**三列缺標籤的表面問題已解決**，但發現一項新的內容精確度問題（見新發現 B），不足以推翻本項判定為「達成」。 |
| 4 | Minor | **達成** | FR-6.4（第 90 行）驗收標準已明文「**目前頁次為 5**（即請求值，非 2）」，補上原本留白的邊界值定義；問題檔 Q7 R2 段第 1 點（194 行）逐字對應「回顯請求值，不夾到最後一頁」。可測性缺口已補齊。 |
| 5 | Minor | **達成** | 第三條新增假設（第 221 行）保留「（本區分為本站的綜合判斷，非逐字承自 Q7 選項原文）」annotation；問題檔 Consolidated Summary Confirmation — Revision 1（199-224 行）的「新增假設的確認」清單第 3 項（217 行）同步帶有相同 annotation，且確認關卡 `[Answer]: A`（224 行）明文「涵蓋 R1、R2 與上列三條新增假設」，晚於三條假設全部列出之後作答，確認範圍與假設集合一致。 |

### 迴歸檢查

- **FR-6.5 對前端是行為變更」段落是否與 FR-6.5 本身 AC、C-10、FR-1〜FR-5 矛盾**：無矛盾。FR-6.5 的 AC 列（第 91 行）只斷言可觀察行為（「畫面仍在第 2 頁」），未綁定實作機制；補充段落（第 99 行）與 C-10（第 153 行）彼此措辭一致（皆為「必須修改這兩條路徑（改為就地更新，或以目前頁次重抓）」）。FR-1〜FR-5 未被觸及。
- **「維持目前頁次，就地更新該列」舊措辭是否仍殘留造成內部矛盾**：`requirements.md` 全文已無此完整片語（僅有「維持目前頁次」，見 FR-6.5 第 91 行與 Revision 1 摘要表第 205 行）。`requirements-analysis-questions.md` 中仍可見於 Q6 前言（152 行，`~~刪除線~~`）與選項 A 本文（160 行）、`[Answer]`（166 行）——前二者依協定以刪除線就地標註為「不成立」但保留原文可讀，`[Answer]` 本身依協定不改寫。三處共同閱讀不構成矛盾：`[Answer]` 選的是「維持目前頁次」這個決定（機制上以就地更新為主），R1 附加段落已明文承認對啟停用/刪除是行為變更。**未見矛盾**。
- **Consolidated Summary 表是否仍與實際答案、FR 文字相符**：`requirements-analysis-questions.md` 第 203-207 行的 Q6／Q7／R2-2 三列與 `requirements.md` 對應的 FR-6.5、FR-6.4、NFR-8 逐項核對後**內容相符**。
- **是否有衍生數字、交叉引用因本輪修正而未同步**：核對「Revision 1 更正輪」表頭「1 Critical + 1 Major + 3 Minor」與表格實際 5 列（1+1+3）相符；「本次修訂新增的假設」段落與 Confirmation 段落皆一致宣稱「三條」且確實各列 3 項；C-10／FR-6 四面向表對 C-6、C-7 的交叉引用經核對內容仍準確。**未發現衍生數字或交叉引用的同步失誤**（與過往同型失誤模式相比，本輪未重蹈覆轍）。
- **`[impl]` 標籤是否已在檔頭正確註冊且用法一致**：已於第 9 行註冊，定義明文「引用時附檔名與行號」。全文 5 處使用中，僅 C-10（第 153 行）的用法在**同一表格列**內同時帶有具體行號（`AdminPage.tsx:89`／`:113`／`:129`），其餘 4 處（第 99、135、138 行）**標籤旁未附檔名或行號**，屬用法不完全一致——詳見新發現 A。

### 新發現

| # | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| A | Minor | `[impl]` 標籤使用處（第 99、135、138 行） | 檔頭（第 9 行）明訂 `[impl]`「引用時附檔名與行號」，但 FR-6.5 補充段（99 行「三個操作的既有成功路徑並不相同 [impl]」）、FR-6 四面向表 IAM 列（135 行「授權依賴鏈未變 [impl]」）、Audit logging 列（138 行「該路徑不被 FR-6 觸及 [impl]」）三處標籤旁均未附檔名或行號，僅 C-10 一處符合定義。內容經查證均為真（見上方逐項核對），非誤引，但標籤格式本身未依其自訂定義一致套用 | 三處補上具體檔名行號（如 IAM 列補 `user_router.py:439`），或將定義放寬為「至少一處鄰近引用即可」並在檔頭註明，兩者擇一以消除定義與用法的落差 |
| B | Minor | FR-6 四面向判定表·Audit logging 列（第 138 行） | 「本 intent 唯一寫入稽核記錄的路徑是角色變更」一句，若脫離「本 intent 涉及的能力範圍」這個限定語境逐字理解，與 repo 事實不符：`grep _audit_append` 顯示 `user_router.py` 實際有 7 個呼叫點，分屬 `register`（335）、`approve_authorization_request`（514）、`reject_authorization_request`（553）、`delete_user`（649）、`update_user_role`（699）、`put_role_permissions`（800）、`reset_role_permissions_defaults`（825）——並非只有角色變更一條路徑。在「本 intent 的六項 Must 能力中，唯一觸及稽核記錄的是 FR-4」這個限定讀法下句子成立，但字面未明寫此限定，容易被下游讀者誤解為「全 repo 唯一路徑」。判定本身（FR-6 不適用 Audit logging，因為 FR-6 未觸及任何 `_audit_append` 呼叫點，含 `delete_user` 在內）不受影響，因為 FR-6 定義本身確實不修改任何後端寫入邏輯 | 改「本 intent 唯一寫入稽核記錄的路徑是角色變更」為「本 intent 六項 Must 能力中，唯一觸及稽核記錄寫入的是 FR-4 的權限矩陣變更」，明確限定語境範圍，避免與 repo 實際的多個 `_audit_append` 呼叫點產生字面衝突 |
| C | Minor | FR-6.5 補充段（第 99 行）、C-10（第 153 行） | 本輪修正新增「必須修改這兩條路徑（改為就地更新，或以目前頁次重抓）」，把 Q6 決策原文明確以「複雜度高於本 feature 其餘部分」為由排除的 Option B（重抓當前頁）重新列為對啟停用／刪除的合法實作路徑之一，但文件未說明該代價為何不再成立。Assumption 1（第 219 行，「就地更新不會與重抓結果不同」）與 FR-6.4（超出範圍頁次回 200＋空清單）合起來或可解釋此代價已被吸收，但這條推論鏈未明文銜接；iteration 1 reviewer 的原始建議（第 248 行 recommendation (3)）僅要求「改為就地更新」單一路徑，未要求納入第二個選項。這不影響 FR-6.5 本身的可測試性（AC 只斷言可觀察行為），但屬本輪修正動作新引入、且未登錄為 OQ 的隱性實作分歧，與本文件既有的「開放實作決策一律登錄 OQ」慣例（如 OQ-1 對應 FR-1.3）不一致 | 二擇一：(1) 依原 reviewer 建議收斂回單一路徑「改為就地更新」，刪除「或以目前頁次重抓」；或 (2) 保留兩個選項但比照 OQ-1 新增一條 OQ，註明「啟停用／刪除的頁次維持機制：就地更新 vs 重抓當前頁，兩者擇一」及定案時點（application-design） |

### Summary

iteration 1 的 5 項 findings（1 Critical、1 Major、3 Minor）逐項回頭核對 repo 與問題檔原文後**全數真正關閉，無一項僅為表面修飾**：Critical 的行號引用（`AdminPage.tsx:89`／`:113`／`:129`）逐行核對與程式碼相符，`[tp:cs]` 誤引已正確改標並與 `[impl]` 分工清楚；Major 的 NFR-8 現同時涵蓋頁次與每頁筆數兩個參數且與 FR-6.4 分界清楚；三項 Minor（四面向表標籤、FR-6.4 邊界值、新增假設 annotation）均已補齊且與問題檔逐字對應。Q6 的更正流程本身也符合 `project.md ## Corrections` 的「只修理由不改決定」協定：答案未改寫、理由以刪除線就地標註、落差來源記入獨立的 R1 附加段落。本輪對抗式覆查另發現三項新 Minor（`[impl]` 標籤用法不完全一致；Audit logging 列一句話脫離語境讀可能與 repo 事實衝突；FR-6.5 補充段新增的「重抓當前頁」選項重新開放 Q6 已排除的 Option B、且未登錄為 OQ），三者均為精確度與一致性瑕疵，不影響任何驗收標準的可測試性、不推翻任何已核可的決定、不構成需回跳確認的範圍變更。判定：**READY**——五項原始 findings 真正解決，未發現會阻擋工程展開的迴歸。

## Review — Revision 1

**Verdict:** NOT-READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-10T23:40:22Z
**Iteration:** 1

本輪僅覆查 Revision 1 新增內容（FR-6.1〜FR-6.7、NFR-8〜NFR-10、C-9〜C-10、OQ-6〜OQ-7、「FR-6 分頁的四面向判定」表、Revision 1 段落），FR-1〜FR-5、NFR-1〜NFR-7、C-1〜C-8、Q1〜Q5 已於 iteration 2（2026-08-09）核可為 READY，不重新裁決；本輪對抗式核對每一條新增主張的來源標籤與上游原文，並回 repo 對照程式碼實況。

### 事實查證

| # | 查證項目 | 查證方法 | 結果 |
| --- | --- | --- | --- |
| 1 | C-9「既有使用者清單端點無分頁、無上限，一次回傳全部帳號」是否屬實 | 讀 `backend/services/user_router.py` L438-461 `list_users()` | **屬實**：`db.query(User).order_by(User.id).all()`，無 `.limit()`／`.offset()`／`Query` 分頁參數，回應型別為 `List[UserSchema]` 全量陣列 |
| 2 | C-10 與問題檔 Q6 前言「既有實作在（角色調整、啟停用）兩個操作成功後**不重抓清單**，而是以 `setUsers((prev) => prev.map(...))` 就地更新」是否屬實 | 讀 `frontend/src/pages/AdminPage.tsx` L77-117：`handleRoleChange`（角色調整）與 `handleToggleActive`（啟停用） | **部分不實**：角色調整（L89）成功後確為 `setUsers((prev) => prev.map(...))`，不重抓，與宣稱相符；**啟停用成功後（L113）呼叫 `fetchUsers()`，即整份重新請求清單，並非就地更新**，與宣稱直接矛盾。兩個操作的既有行為並不相同，宣稱把它們合併陳述為同一種行為 |
| 3 | `[tp:cs]`（`team-practices.md` `## Code Style`）是否支持「不重抓清單」這個具體主張 | 讀 `team-practices.md` `## Code Style`「前端：lint 規則造成的結構約束」段（L157「資料抓取拆兩層」條） | **不支持**：該段只規範「抓取函式／呼叫端 state 更新／`useEffect` cancelled flag」三層拆分與 `react-hooks/immutability`（回傳新物件），全文未提及「操作成功後應否重抓清單」這個行為選擇；`[tp:cs]` 對 C-10／FR-6.5 這條主張而言是誤引 |
| 4 | 「FR-6 分頁的四面向判定」表 Network exposure 列「只有 nginx 對外曝露，未新增端點」是否屬實 | 讀 `codekb/cloud-360/architecture.md` L36-42（系統脈絡文字 fallback） | **屬實**：「使用者瀏覽器經 Cloudflare Tunnel 進入 nginx…只有 nginx 對外曝露，後端與資料庫都不直接對外」，逐字支持判定 |
| 5 | FR-6.7／Won't Have「排序／篩選」排除是否仍完整保留、未被 FR-6 鬆動 | 對照 `scope-document.md` Revision 2 L35、L45、L75 | **一致**：三處皆明文「(f) 分頁是本次唯一新增的清單互動，不連帶解除排序與篩選」，requirements.md 的表述未超出或窄化此範圍 |
| 6 | OQ-6「每頁筆數與回應 envelope 形式留 application-design 定案」是否被 FR-6 本身逾越代決 | 通篇檢視 FR-6.1〜FR-6.7 | **未逾越**：FR-6.2 只規定回應「須帶出哪三個值」（總筆數／目前頁次／每頁筆數），未指定 envelope 的容器結構或每頁筆數的具體數字，與 `scope-document.md` Revision 2 assumption（「每頁筆數、回應是否包 envelope 屬設計決定」）分工一致 |
| 7 | 「意圖分析」段主張「分頁源自 Construction 3.2 實測」的來源歸因是否準確 | 對照 `scope-document.md` Revision 2「Revision 2 摘要」段（L69） | **逐字相符**：「Construction 3.2…實測發現使用者清單端點無分頁、無上限」與 requirements.md 原文一致，且明確標註「它不是稽核目標本身的一部分」——正確歸因，未重蹈 `project.md` correction `rough-mockups:rev1-c1` 記載的「把現行實作副作用誤認為產品需求」覆轍 |

### Findings

| # | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| 1 | Critical | C-10（約第 150 行）、FR-6.5（約第 90 行）、`requirements-analysis-questions.md` Revision 1 Q6 前言與選項 A（約第 152、156、162 行） | C-10 與 Q6 前言把「角色調整」與「啟停用」兩個操作合併陳述為「既有實作皆不重抓清單」，並據此把 FR-6.5（維持頁次、就地更新）定性為「與既有行為一致、改動最小」。經回 repo 核對，這對「啟停用」不成立：`handleToggleActive` 現行成功路徑是 `fetchUsers()`（整份重抓），不是就地更新。FR-6.5 的驗收標準恰以「停用」為例句（「於第 2 頁停用一個帳號後，畫面仍在第 2 頁」），若依「改動最小、既有行為一致」的錯誤前提去實作，等於默認 `handleToggleActive` 不需修改，會直接產出違反 FR-6.5 的成品（停用後被重抓拉回未分頁前的整份清單、頁次跳走）。這與 `project.md ## Corrections` 明確記載的同一 intent 既有失誤同型（`cid:rough-mockups:rev1-c1`：把實作副作用誤植為既定事實、並讓錯誤前提支撐後續整條論證鏈），且 `[tp:cs]` 本身也未涵蓋「是否重抓」這個主張（見事實查證 #3），屬誤引來源 | 決定本身（就地更新、維持頁次）依既有三選項比較仍站得住腳，不需改動；但須：(1) 更正 C-10 與 Q6 前言為逐操作陳述——角色調整既有為就地更新，啟停用既有為整份重抓；(2) 移除「改動最小、與既有行為一致」對啟停用的適用性，或明確界定僅適用於角色調整；(3) 在「跨層影響」段落加一句：FR-6.5 要求把 `handleToggleActive` 的更新策略從整份重抓改為就地更新，屬行為變更而非既有形狀的延伸；(4) 移除或改標 `[tp:cs]`，改引實測所得的具體行數或新增一個查證來源標籤 |
| 2 | Major | NFR-8（約第 109 行） | 需求文字寫「**分頁查詢參數**須在系統邊界驗證」（複數，理應涵蓋頁次與每頁筆數兩者），但驗收標準只列舉「每頁筆數」的邊界情形（非數值／負數／零／超過上限）。**頁次本身的非法值完全未被任何 FR 或 NFR 涵蓋**：FR-6.4 只定義「合法但超出範圍」的頁次（如總共 2 頁請求第 5 頁）該如何回應，NFR-8 的 AC 未列頁次的型別／範圍驗證（如頁次為負數、零、非數值時應如何處置）。QA 無法僅憑本文件寫出「非法頁次」這條測試，是需求陳述範圍與驗收標準範圍不一致造成的真實覆蓋缺口 | 於 NFR-8 的驗收標準明確加入頁次的驗證項（例如「非數值、負數、零的頁次皆被拒絕或夾到合法範圍，不得出現未處理例外」），使「分頁查詢參數」的措辭與 AC 涵蓋範圍一致；或拆出獨立一條需求專責頁次驗證 |
| 3 | Minor | 「FR-6 分頁的四面向判定」表（約第 130-135 行） | IAM／Encryption／Audit logging 三列皆無任何來源標籤，僅 Network exposure 一列標 `[scope:r2]`。與本文件既有的逐句可溯源慣例（原「ADR-0006 四面向檢查」表已建立的標準，iteration 2 review 曾對其 Encryption 列缺標籤開立 Minor Finding B）不一致，且是本輪新增內容中的新發生例，非沿用既有缺口 | IAM／Encryption／Audit logging 三列各補上可佐證的標籤，例如 IAM 可引 `[scope:r2]`（(f) 定義本身未提及角色變更）、Encryption 可引 `[kb:architecture]`、Audit logging 可交叉引用 C-7 或既有稽核機制描述 |
| 4 | Minor | FR-6.4（約第 89 行） | 驗收標準只斷言「HTTP 狀態為 200、資料清單長度為 0、總筆數與每頁筆數仍為正確值」，未定義回應中「目前頁次」（FR-6.2 規定每次回應必帶的三值之一）在超出範圍情境下應為何值——回顯請求值（如 5）、還是夾到最後一頁（如 2）？兩者對前端「回到第 1 頁」的實作方式不同，AC 本身留了一個可測項空白 | FR-6.4 補一句明確定義「目前頁次」欄位在此情境下的值（例如「目前頁次回顯請求值，不夾到最後一頁」），使該欄位在邊界情境下也可測 |
| 5 | Minor | Revision 1 新增假設第二條（約第 207 行） | 「FR-6.4 選擇以 200＋空清單…NFR-8 的邊界驗證處理的是型別與範圍非法的參數…兩者是不同的判定，不可互相取代」——後半句的區分推論未逐字出現於已作答的 `requirements-analysis-questions.md` Q7 選項 A 原文（該選項只到「以 200 表達『查詢合法但該頁無資料』」），屬本站產出 artifact 時新增的綜合判斷，非逐字承自已確認的選項文字。`project.md ## Corrections`（`cid:intent-capture:c12`）要求 Assumptions 增刪須同步重新取得人工確認；本條與其他四項新增假設不同，未經逐字對應的確認文字支撐 | 若此區分句為必要內容，於下次確認迴圈中以逐字或近逐字方式呈現於問題檔（例如追加子選項或於 Consolidated Summary 內明列），或在假設旁註明「本區分為本站綜合判斷，非逐字承自 Q7」，避免與其餘四項確有逐字對應的假設混為一談 |

### Summary

本輪對抗式覆查發現一項 Critical：C-10 與問題檔 Q6 前言把「角色調整」「啟停用」兩個操作的既有行為混為一談，宣稱兩者皆「不重抓清單」，但回 repo 核對 `AdminPage.tsx` 後，「啟停用」的既有成功路徑實為整份重抓（`fetchUsers()`），並非就地更新——這與 FR-6.5 恰以「停用」為例句的驗收標準直接相關：若依「改動最小」的錯誤前提實作，會漏改 `handleToggleActive`、產出違反 FR-6.5 的成品，且引用的 `[tp:cs]` 來源本身也不支持這個主張。此失誤與 `project.md` 明文記載的同一 intent 過往失誤同型（誤植實作副作用為既定事實、支撐後續整條論證鏈），值得注意的是同一份文件在「意圖分析」段對分頁起源的歸因（Construction 3.2 實測，而非核心價值）反而做對了，顯示問題不是不理解這條校正規則，而是逐項核對時的疏漏。另有一項 Major（NFR-8 的驗收標準未涵蓋其自身文字宣稱的「頁次」驗證，僅涵蓋「每頁筆數」）與三項 Minor（四面向判定表三列缺來源標籤、FR-6.4 未定義邊界情境下「目前頁次」的值、新增假設之一未逐字對應到已確認文字）。決定本身（FR-6.5 選就地更新、FR-6.4 選 200＋空清單）在核對後仍站得住腳，不需推翻，但 Critical 與 Major 兩項須先修正才能判定 READY。

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-09T02:05:51Z
**Iteration:** 2

本輪為對抗式覆查：不採信 builder 的修正宣稱，逐項回頭核對本檔、`requirements-analysis-questions.md`、以及上游 `wireframes.md`（已 READY，iteration 3）、`raid-log.md`、`constraint-register.md`、`discovered-rules.md`、`evidence.md`、`scope-document.md`、`feasibility-questions.md`、`project.md`、`architecture.md` 的原文。

### 逐項核對（iteration 1 的六項 findings）

| # | Severity | Iteration 1 finding | 修正宣稱 | 核對方法與結果 |
| --- | --- | --- | --- | --- |
| 1 | Critical | FR-2.3／NFR-6 要求顯示文字「無紀錄」，與已核可 wireframes（可聚焦破折號 `—`）矛盾 | FR-2.3 改為只定義語意判定，呈現形式交給 FR-2.4；五處統一為破折號 | `grep "無紀錄"` 全文複查：所有殘留的「無紀錄」均為**狀態名**（「無紀錄態」），無一處作為**顯示文字**出現。FR-2.4（第 46 行）明訂 `—` 並標 `[rm:Q4][rm:Q4a]`；FR-5.2（76）、NFR-6（90）、C-1（110）均以 `—` 表述；逐字核對已 READY 的 `wireframes.md` 第 87 行「無紀錄（空值）｜可聚焦 `—` ＋說明 tooltip；不套逾期標示｜[Q4][Q4a][feas:Q2]」，完全對齊。`requirements-analysis-questions.md` 前言另有明確修訂註（第 9 行）記載更正緣由，符合 `team.md` correction（下游具體決策不被更早措辭覆蓋）。**已解決，五處一致，無迴歸**（FR-2.3 的「不套逾期標示」語意本身未被弱化，仍是獨立驗收項）。 |
| 2 | Major | NFR-3 的 `[tp]` 標籤查無實據，真正來源在 `discovered-rules.md`／`project.md ## Mandated` | 改標 `[dr:ADR-0006]`，檔頭註冊該標籤定義 | 檔頭第 6 行已註冊「`[dr:*]` 指 practices-discovery 的 discovered-rules（已 promote 進 `project.md` 的 `## Mandated`）」。NFR-3（87）與新增的「ADR-0006 四面向檢查」表頭（97）皆用 `[dr:ADR-0006]`。逐字比對 `project.md ## Mandated`（affirmed 2026-08-09）原文：「涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出（feasibility、scope、user-stories 等）中明列 security 影響與處置，不得僅以『已有 ADR-0006』帶過」——requirements.md 第 97 行的轉述逐字相符。**已解決**。 |
| 3 | Major | 「範圍外」把「未承諾」的匯出項放進標題為「排除」的清單，語意漂移 | 拆為三個獨立小節：明確排除／另立項的既有缺陷／未承諾 | 核對 `scope-document.md` 第 27–38 行：其「Won't Have」四項與本檔「明確排除」四項逐字對應；其「未承諾」段（第 36–38 行，稽核報表匯出）與本檔「未承諾」小節狀態描述（「不在範圍、亦不在排除清單」）逐字對應，未被誤植入排除清單。**核心漂移已消除**。附帶發現一項新的次要精確度問題，見下方新 Finding C。 |
| 4 | Major | ADR-0006 四面向只做了 IAM 與 audit logging 兩項 | 新增四面向表，encryption／network exposure 判「不適用」並附理由 | 逐項核實：IAM＝適用（cites `[pd]`、raid-log R3、FR-4.3 cross-ref，均可溯源）；Encryption＝不適用（理由：新欄位非憑證/PII，傳輸/靜態儲存邊界未變）；Network exposure＝不適用（理由：FR-4 只對既有頁面翻轉授權旗標，未新增端點/邊界，cites `[kb:architecture]`）；Audit logging＝適用（帶已知限制，cross-ref C-7／`[Q5]`）。**對抗式複核 network exposure 判定**：讀 `architecture.md` 第 51–55 行「使用者瀏覽器經 Cloudflare Tunnel 進入 nginx…只有 nginx 對外曝露，後端與資料庫都不直接對外」，確認本 intent 未新增端點、未變更對外邊界，僅是既有已可達端點的應用層授權翻轉——判「不適用」站得住腳，未見過度寬鬆。**已解決**，但 Encryption 列本身缺引用標籤，見新 Finding B。 |
| 5 | Minor | `[memory:M1]` 未在本 stage 的 Sources register 定義 | 改用 `[raid:D1]`，檔頭註冊 `[raid:*]`、`[dr:*]`、`[pd]` | 檔頭第 6–7 行已註冊 `[raid:*]`／`[pd]`。C-4（113）改標 `[raid:D1]`，核對 `raid-log.md` D1（「`schema_rbac.sql` 與 `DEPLOY.md` 的同步更新（blocking）是相關 Construction／部署階段標示完成的前置」）與 C-4 主張（「`schema_rbac.sql` 與 `DEPLOY.md` 未同步即不得標示相關階段完成」）逐字語意相符。**已解決**，但同一標籤在別處被挪用支撐另一個不同主張，見新 Finding A。 |
| 6 | Minor | FR-1.3 的 5 分鐘節流未指明滑動視窗 vs 固定時間桶 | 明訂以「上一次成功寫入的時刻」為基準的滑動視窗，修改驗收標準措辭 | FR-1.3（34）：「計時基準為上一次成功寫入的時刻（滑動視窗，非固定時間桶）」，AC 具體到「距上次寫入滿 5 分鐘（含）之後的下一個請求觸發第 2 次寫入」，可直接測試，消除原本的歧義。**對抗式檢查是否逾越「手段留設計階段」的既定分工**：FR-1.4 下方「設計階段必答項」注記（37）仍完整保留「達成 FR-1.3 的手段（節流／彙整／非同步）由 application-design 選定」，OQ-1（153）也仍列為 application-design 必答項。滑動視窗定義的是**可觀察行為契約**（what：如何界定「5 分鐘內一次」），不是**實作機制**（how：用記憶體節流／批次彙整／非同步佇列哪一種手段達成），兩者不矛盾。**已解決，無迴歸**。 |

### 新 Finding（本輪覆查中發現，非原六項之列）

| # | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| A | Minor | FR-4.3（第 67 行） | `[raid:D1]` 與該行主張不對應。FR-4.3 主張「兩處**預設值來源**同步」（`rbac_seed_data.py` 與 `schema_rbac.sql` 的權限預設值一致），精確對應 `[feas:T5]`（`constraint-register.md` T5：「角色權限預設值存在兩處來源（資料庫腳本與後端種子資料），必須同步修改」）。但同時疊加的 `[raid:D1]` 實際指向另一組完全不同的檔案配對——`schema_rbac.sql` 與 `DEPLOY.md` 的**文件同步義務**（已在 C-4 正確使用），與「兩處預設值來源」無關 | 移除 FR-4.3 的 `[raid:D1]`，只保留 `[feas:T5]`（已充分支撐該行全部主張） |
| B | Minor | ADR-0006 四面向檢查表·Encryption 列（第 102 行） | IAM 列有 `[pd]`／raid R3／FR-4.3 cross-ref，Network exposure 列有 `[kb:architecture]`，Audit logging 列有 C-7／`[Q5]` cross-ref，唯獨 Encryption 列（「本 intent 新增的欄位為活動時間戳…傳輸加密沿用既有的 Cloudflare Tunnel 邊界…靜態儲存沿用既有資料庫設定」）沒有任何標籤，與本文件自訂的逐句可溯源慣例不一致（內容本身合理，可由 `architecture.md` 佐證，純屬掛漏） | 補 `[kb:architecture]`，與其餘三列的可溯源標準一致 |
| C | Minor | 「範圍外」章節首段（第 129 行） | 「本章分三類，三者狀態不同，不可互相混同（承 scope-document 的分類）」對第三類略有超 claim：`scope-document.md` 本身只劃出兩類（Won't Have／未承諾），「另立項的既有缺陷」是本階段透過 Q4／Q5 新識別的分類，並非承自 scope-document | 改為「其中前兩類承 scope-document 的既有分類，第三類為本階段新識別的既有缺陷」一類措辭，避免對來源的過度歸因 |

### Summary

六項 iteration 1 findings（1 Critical、3 Major、2 Minor）逐字核實全數落地，且未發現迴歸：破折號表述在五個位置（FR-2.3 語意／FR-2.4／FR-5.2／NFR-6／C-1）一致，並與已 READY 的 `wireframes.md` 完全對齊；`[dr:ADR-0006]` 已註冊且與 `project.md ## Mandated` 逐字相符；「範圍外」三分類的語意漂移已消除；ADR-0006 四面向補齊，其中 network exposure「不適用」判定經對抗式檢驗（比對 `architecture.md` 的網路邊界事實）站得住腳；`[raid:D1]` 已註冊且在 C-4 用法正確；FR-1.3 的滑動視窗定義經檢查屬「可觀察行為契約」而非「實作手段」，未逾越 application-design 的既定分工。本輪另發現三項 Minor 級新問題（FR-4.3 的 `[raid:D1]` 引用範圍不符、四面向表 Encryption 列缺引用、「範圍外」首段對第三分類的來源歸因略為超 claim），均屬引用精確度瑕疵，不影響任何驗收標準的可測試性、不改變已核可的決策內容，不阻擋 READY。判定：**READY**——工程可依此文件直接展開，不需回頭確認。
