## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-09-25T00:05:41Z
**Iteration:** 1

本輪為 ADVISORY 單次審查，findings 直接交人工在核可關卡裁決，其後無修正—重審迴圈。

### 先講站得住的部分

本站引用的機械事實我實測複驗，**全部成立**：`openapi.json` 為 42 個 path
且 `/api/collab/ws/...` 不在其中（NFR5 的立論基礎）；既有 SSE 端點實數為
**5**（`agent_router.py` 3、`review_router.py` 1、`advice_stream_router.py` 1），
本站更正 `team.md` 的「3 個」是對的；`collab_router.py:257` 確為
`get_user_from_token(..., record=False)`；`backend/Dockerfile` 的 `CMD` 無
`--workers`；全樹 `CREATE SCHEMA`／`search_path` 命中數為 **0**；
`tests/helpers.py` 確以 `MagicMock` 換掉 `psycopg2` 並走 `sqlite:///:memory:`；
成本 job 的事件型別確為 `progress`／`completed`／`failed`／`timeout`／`heartbeat`，
且 `cost_advice_agent.py` 的 LLM 呼叫確為同步 `invoke_graph`。
ADR-0006 四面向以逐項判定表呈現、10 項能力各有對應 FR、codekb 證據強度標記
（`[讀]`／`[簽]`／`[算]`／`[未驗]`）帶進需求並以 A-6 收束，都符合規則層要求。

以下是我認為人工在按下核可前必須先看的缺口。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements.md` > FR1 與「ADR-0006 Security Baseline 四面向逐項判定」表 IAM 列 | 已核可的 rough-mockups `[R8]`＝A **整條未進需求**。該作答逐字定案「給入口頁自己的 story id，置於瀑布之首」，並在作答後的後果段明寫「需新增 RBAC story id 與權限矩陣項目」，會觸發 `team.md` 的 allow/deny 雙向測試與 `project.md` 的 `schema_rbac.sql`＋`DEPLOY.md` blocking 同步。我對 requirements.md 全檔 grep `story id`／`role_permissions`／`導向`／`DefaultRedirect`／`瀑布`／`403`：**零命中**。入口頁是能力 1（Must）的唯一載體，它自己的授權落點目前沒有任何需求承載，而 IAM 列只列了記憶層、成本代呼叫與 Redis 憑證，宣稱「四面向皆適用，無不適用項」時漏掉了本 intent 新增的唯一使用者入口 | 新增一條 FR，寫明入口頁有自己的 story id、置於既有權限瀑布之首、無該權限者沿用現行落地順序（不得繞過 `/403`），並把它列進 IAM 列；同時明標此為 `role_permissions` seed 變更，觸發 allow/deny 雙向測試與兩份部署資產的 blocking 同步 | New |
| R-02 | Critical | 同上 > FR1.3 | FR1.3 以「信心未達門檻」為觸發條件，全檔無該門檻的數值，Open Questions 也沒有為它設一項。而 rough-mockups 第 12 節的「刻意不在本站定案的」段逐字寫著：「觸發本畫面的**判定門檻**（信心低於多少才改為詢問）屬數值參數，與三個成功指標的門檻同屬 requirements-analysis 的工作，本站不預選」——這是上游明確交給本站的義務，R1 只收了三個成功指標的門檻，沒有收這一個。結果是一條 Must 級 FR 沒有 pass/fail：QA 無法判定「未達門檻」何時成立。（附帶：你自問的 FR1.3「可達性」處理我判為**適當**——把信心訊號的前提寫出來並掛 OQ-10 是誠實的；真正的缺陷是門檻值缺席，不是那段 caveat） | 為 FR1.3 定出可二元判定的門檻（數值，或「由路由層輸出的信心值與設定值比較，設定值初版為 N、於首次實測後校正」），並把「路由層必須輸出可比較的信心值」升為一條獨立 FR 而非前提句——否則實作者可能做出一個不輸出信心值的路由層，FR1.3 靜默永不觸發 | New |
| R-03 | Major | 同上 > FR9（FR9.1–FR9.4）與 ADR-0006 表 IAM 列 | `projects`／`systems` 是本 intent 新建的核心資料模型，但沒有任何需求指名**誰建立它、誰能讀改刪、以什麼權限**。FR9.1 只定資料模型、FR9.2 定遷移、FR9.3 把歸屬規則交 `domain-design`；已核可線框第 3 節有「[切換對象]」控件（選取），卻沒有建立路徑。在一個所有存取都走 `require_story_action` 的 repo 裡，新核心模型沒有存取控制需求是契約的寫入端與授權端同時懸空，且與 R-01 同屬 IAM 列的漏項 | 新增 FR 指名專案／系統列的建立者與可存取角色（或明確寫成 OQ 並指派落點與 execution），並補進 IAM 列 | New |
| R-04 | Major | 同上 > NFR1、NFR2、NFR3 | 三條門檻中只有 NFR1 有量測母體（≥50 筆標註輸入）與資料集承接站（N-3＋`[RA:R9]`）。**NFR2 的 ≥95% 沒有母體定義、沒有量測工具、沒有承接站**——「切換功能後仍正確指向同一對象的比例」的分母是什麼、誰量、在哪一站建立量測，全部未寫；其附帶子句「一併涵蓋『完成一個跨功能任務所需的頁面切換次數下降』」更沒有基準值也沒有門檻，字面上不可驗證。另 NFR1 自己寫「第一版以建立量測機制為先」，但 N-3 只涵蓋**資料集**，那個**量測機制**沒有任何一站被指派。你問「沒有依據的門檻算不算可測」——80% 這個數字由 A-3 誠實標為工程判斷，我認為可接受；不可接受的是 NFR2 連量測方式都沒有 | 為 NFR2 定義量測母體與判定方式，或明標其為量測機制未定並指派落點；把「頁面切換次數下降」拆出獨立門檻或刪除該子句；為 NFR1／NFR3 的量測機制指名承接站（N-3 應同時涵蓋量測機制，不只資料集） | New |
| R-05 | Major | 同上 > FR4.5、NFR7 | 「逾期自動刪除」的執行機制無落點：沒有 FR 說它由什麼承載，Open Questions 也沒有（OQ-9 只管 Redis session，FR4.5 自己指明 90 天只管 PostgreSQL 的 episodic memory）。這不只是缺一個設計決定——`project.md` `## Forbidden` 禁止以 repo 內新增的實作程式承載**無人值守**的流程自動化（排程觸發、無人在迴圈內者一律以 gh-aw／GitHub Actions workflow 承載）。一個 90 天排程清除正好落在該禁令的範圍內，而需求沒有提到，實作者很可能寫成 backend 的排程程式並直接違規 | 新增一條 FR 或 OQ 指名 90 天清除的承載形式（須為 workflow 而非 repo 內排程程式）與其落點，並在文中引用該 Forbidden 條款 | New |
| R-06 | Major | 同上 > FR1.2 | 來源標籤誤掛。FR1.2 主張「每個工作項帶一個狀態（處理中／完成／失敗／已停掉）」並掛 `[R3][R5]`，但逐字核對：rough-mockups R3＝A 是「子頁面沿用與入口頁相同的脈絡呈現」，R5＝A 是「成本 job 的 progress 用單一則就地更新的訊息」——**兩題都沒有一個字談工作項或其狀態集合**。真正的來源是線框第 8／13 節（本站在 FR1.3、FR1.4 就是這樣引的）。同時，線框第 8 節顯示的狀態含「**等待中**」（依賴前一項的工作項），FR1.2 的四個狀態把它漏掉——QA 依 FR1.2 寫測試會把已核可線框上的「等待中」判為違規 | 把 `[R3][R5]` 改為線框第 8／13 節的引用；狀態集合補上「等待中」或明寫為何排除 | New |
| R-07 | Major | 同上 > FR4.3、ADR-0006 表 IAM 列 | 記憶列的「擁有者與可見範圍」欄位只定了**讀取**一律經最小權限模型，沒有指名**誰寫這兩個欄位、可見範圍由誰設定或變更**。A-5 談的是介接系統如何映射自身角色去讀。寫入端未指名的後果是安全相關的：任何介接系統都能自行把一列記憶標成較寬的可見範圍 | 為 FR4.3 補上寫入端：誰得設定與變更記憶列的擁有者與可見範圍、變更是否留稽核（或明列為 OQ 並指派落點） | New |
| R-08 | Minor | 同上 > NFR1 的校正條款 | 「門檻得於首次實測後校正」沒有授權者、沒有判準、沒有時點。首版實測 62% 時，這條 NFR 是驗收失敗還是自動改寫門檻，文件上無法判定 | 寫明由誰在哪一站依什麼判準校正，以及校正前首版的驗收立場 | New |
| R-09 | Minor | 同上 > 「來源標籤慣例（含一處必須避開的撞號）」表 | 慣例表只列 6 種標籤，但全檔實際使用的還有 `[desc]`（FR9.1、FR9.4）、`[memory:M2]`、`[C-R2]`／`[C-S5]` 等約束 id、`[raid-log R-7]`、`[rough-mockups 第 13 節]`、`[kb:api-documentation]`（該檔在 codekb 存在，但慣例表只寫 `[kb:<檔>]` 指向本站宣告消費的三份）。表本身的目的是防撞號誤讀，不完整會削弱這個保護 | 補齊慣例表至涵蓋全檔實際使用的每種標籤形式 | New |

### Summary

不建議在現況下直接核可。兩項 Critical 都是**上游已核可決定在本站落空**，不是
判斷分歧：`[R8]`＝A 定案的入口頁 story id 與權限瀑布位置整條不見（R-01），
rough-mockups 第 12 節逐字指派給本站的信心判定門檻沒有被收（R-02）——後者讓一
條 Must 級 FR 沒有 pass/fail。五項 Major 中有三項是同一個失敗形狀：契約只寫了
一端（`projects`／`systems` 的建立者與授權、記憶列可見範圍的寫入者、90 天清除
的執行機制）。至於你自己最擔心的三處，我的判定是：80% 門檻的誠實標註（A-3）與
FR1.3 的可達性 caveat**都站得住**，真正該修的是 NFR2 連量測母體都沒有、以及
FR1.3 缺門檻值；N-1 至 N-4 的「新增 scope 需回補」分類我逐項核對後**皆成立**，
但清單漏了 R-01 與 R-05 兩項本站實際新增的義務（新 RBAC story id、90 天清除
機制），建議一併補入回補請求。
