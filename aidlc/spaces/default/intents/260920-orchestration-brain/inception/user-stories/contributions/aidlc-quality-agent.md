**Collaborator:** aidlc-quality-agent

## Contribution

我的視角只有一個問題：**這 62 條 AC，每一條由哪一層自動化承載，哪些條在今天的
repo 裡根本沒有任何層能碰到。** 下面的每一項都回過 repo 實測或實算，附檔名行號供
機械複驗。

---

### 0. 先回答被指名的三個問題

**Q1 — AC1.2.4 今天可測嗎？若模型無法輸出信心值，AC1.2.1 會不會變成不可否證？**

**AC1.2.4 今天可測，而且它必須可測**，但理由與 OQ-10 無關。AC1.2.4 斷言的是
**路由層的輸出契約**（「它帶有一個定義域 0–1 的信心值可與門檻比較」），不是
「模型原生具備校準過的信心」。任何實作都能滿足它——包含自陳值、候選分數正規化、
或分數差距映射——因為 AC 只要求「可與門檻比較」，沒有要求「校準」。所以它不是
一條主體不存在的 AC，它是一條**型別與定義域的斷言**。

更重要的是：`project.md ## Testing Posture` 把 **agent routing** 逐字列為 ADR-0006
PBT hard constraint 的三個落點之一。因此 AC1.2.4 ＋ AC1.2.1 的判定邏輯**必須**被
拆成一個純函式（形如 `decide(confidence, threshold) -> 交辦 | 反問`），才能讓
Hypothesis 在 [0,1] 上驅動它。這不是建議，是既有 hard constraint 的直接後果。
既有先例現成可抄：`backend/services/activity.py` 的 `should_record_activity` 就是
「兩個時間門檻的純函式判定」，`backend/tests/test_activity.py` 已用 `@given` 覆蓋它，
且它的 docstring 逐條寫出邊界（含「恰為 90 天者不逾期」這種嚴格大於的宣告）。
`cost_calculator`／估價表解析器的純函式禁令（禁 `httpx`、DB session、`HTTPException`）
是同一個形狀，甚至已經有 CI validator 在擋（`scripts/validate_cost_calculator_boundary.py`）。

**AC1.2.1 不會變成不可否證，但會變成可能永不觸發**，這兩件事不同，而後者更危險：

- 在**純函式層**，AC1.2.1 永遠可否證：餵 `confidence=0.5` 就必須走反問分支。
- 在**整合層**，只要正規化器回傳常數（例如模型不吐分數就一律填 1.0），`< 0.7`
  永不成立，AC1.2.1 就是死碼——而文件上長得像已解決。這正是
  `project.md` 的 `functional-design:c10`（「新增偵測 X 狀態的規則前先推導 X 是否
  可達」）所警告的形狀，且該教訓已經在本 repo 付出過代價。

**因此請在 US1 的 Definition of Done 加一條**：`M-1` 的 ≥ 50 筆標註集中，
**至少 K 筆必須是路由層實測信心 < 0.7 的輸入**（K 值由 `build-and-test` 實測後定），
否則「AC1.2.1 綠燈」只代表單元測試裡那條分支存在、生產環境永不進入。
這讓 M-1 同時承載 NFR1 的準確率母體與 AC1.2.1 的可達性證據，不需要新增交付物。

**另外一個 AC1.2.4／FR1.7 都沒講的第三態**：「信心值取不到」（模型回傳格式錯誤、
呼叫失敗、解析不出數值）。FR1.7 只定義了 `< 0.7` 與否，AC1.2.4 只定義了 0–1；
`None`／`NaN` 走哪一條分支沒有任何一份已核可產出說過。PBT 會在第一次跑就找到它。
建議在 AC1.2.4 的 Then 補一句把定義域收成 **「0–1 的實數，或明確的『取不到』值；
後者一律走 FR1.3 的反問路徑」**——不補的話，實作者的自然選擇是預設交辦（fail-open），
而那是本 intent 最不該 fail-open 的地方。

---

**Q2 — AC4.1.1 的「反映出它取得了那項先前資訊」能不能變成二元可判，而不變成實作斷言？**

能，而且**本檔自己已經示範過答案**：AC4.1.2 就是同一件事的可判版本——
「**When** 系統為我組裝脈絡，**Then** 它只取得我依可見範圍有權讀取的部分」。
AC4.1.2 斷言的對象是**脈絡組裝的結果**，不是 LLM 的散文。AC4.1.1 卻把斷言對象放在
回覆文字上。同一則故事的兩條 AC 用了兩種不同強度的斷言對象，而可判的那一種已經被
接受了——所以把 AC4.1.1 改成 AC4.1.2 的形狀，不會引入任何新的 AC 紀律妥協。

建議改寫（保留原意圖，把斷言對象換掉）：

> **AC4.1.1** **Given** 我在先前的對話中留下了一筆關於某系統的記憶（記憶列 id 已知），
> **When** 我在新的對話中討論**同一個作業對象**、系統為該輪組裝脈絡，
> **Then** 組裝結果**包含該筆記憶列**（以 id 比對），且**不包含**與該對象無關的記憶列

這是二元可判的（集合成員判定），落點是 backend `unittest`，零新依賴。
「回覆讀起來有沒有反映出來」則不可能二元化——那需要人對 LLM 散文下判斷，屬
`tcms-test-cases` 的「只能手動」桶，且依 `project.md` 的必做 2，它的預期結果必須寫出
**可觀察的**判準（例如「回覆中出現該筆記憶所記的偏好，且未要求使用者重新交代背景」），
不能寫「正確反映」。**我不建議為它造一個 UI 可觀察面**（例如在回覆旁列出「本次用到的記憶」）
——那是新增的使用者可見面、`scope-document.md` 未涵蓋，性質同 N-7，不該由測試可觀察性
的需要夾帶進來。要做就明列為回補項讓使用者裁決，不要偷偷加。

**但 AC4.1.1 還有第二個、更硬的問題：它的 Given 目前無法構造。** 我對記憶列跑了
契約端點三問（誰寫、誰讀、誰清）：

| 端 | 狀態 |
|---|---|
| 誰讀 | FR4.3（讀取一律經最小權限模型）＋ AC4.1.2 — **已指名** |
| 誰清 | FR4.5／FR4.5a（90 天、gh-aw 承載）＋ FR4.6（使用者自刪）— **已指名**；Redis session 那端由 OQ-9 承接 |
| **誰寫** | FR4.3a／FR4.3b 指名了寫入時**擁有者與可見範圍怎麼填**，但**沒有任何一條需求說什麼事件會產生一筆語意記憶或程序記憶** |

所以測試作者無法把 AC4.1.1 的 Given（「我在先前的對話中提過某個系統的設計取向」）
變成一段 setup code——他不知道要做什麼才會產生那一列。episodic 還可以推測是對話落地，
semantic／procedure（線框 §9 逐字列出「偏好用繁體中文回覆」「改完架構圖後通常會接著看成本」）
則完全沒有寫入觸發條件。這是**寫入端懸空**，而 `project.md` 的既有教訓
（`260920-orchestration-brain:requirements-analysis` 那條）逐字說「寫入端是三問中最容易漏的一問」
——本 intent 已經在 `projects`／`systems` 上踩過一次。建議在 US4.1 旁標出這個缺口、
指派 `domain-design`（2.6，**CONDITIONAL**）定義三種記憶各自的寫入觸發條件，
轉移目標 `units-generation`（2.7，**ALWAYS**）。

---

**Q3 — AC8.1.1 的「整段產生完之前就出現第一個字」由哪一層觀察？Playwright 的計時斷言
夠穩到當閘門嗎？**

**不夠穩，而且它在這個 repo 的閘門上是會漏的**，三個機械理由：

1. **flaky 被容忍。** `.github/workflows/ui-regression.md:284–289` 讀
   `.stats.unexpected`、非 0 才 `exit 1`，並逐字允許 `.stats.flaky`
   （註解原文：「a retried-then-passed test is stats.flaky, which we allow」），
   而 `frontend/playwright.config.ts:17` 是 `retries: process.env.CI ? 1 : 0`。
   一條時間敏感的測試「第一次紅、重試綠」會被判為 flaky 而**放行**。
   時間敏感斷言在這道閘門上等於半個閘門。
2. **一次 run 只有一個樣本。** AC8.1.1 若寫成計時，它量的是單次；NFR3 要的是 P50。
   單樣本推不出 P50，P50 也不該由一條 AC 承載。兩者要分開。
3. **它其實不需要時鐘。** AC8.1.1 的實質是「增量交付」，那是**順序與筆數**的性質，
   不是秒數的性質：「訊息串中在終止事件之前，至少存在一則帶內容的增量事件」。
   順序斷言是決定性的，計時斷言不是。

**建議落點：backend `unittest` ＋ `TestClient.websocket_connect`。** 我實測了這條路
可行且零新依賴：安裝的是 `starlette 1.6.0`，`TestClient.websocket_connect` 存在，
`WebSocketTestSession` 提供 `receive_text`／`receive_json`／`send_json`／`close`
（`backend/requirements.txt` 已有 `fastapi[standard]==0.141.1` 與 `httpx`）。
**但本 repo 目前 `websocket_connect` 全樹零命中**——WS 從來沒有被任何自動化測過，
包含既有的 `/api/collab/ws/{workspace_id}`。所以這是新做法，但成本是零。

AC8.1.1 的可判形式建議：

> **Then** 該次互動的 WebSocket 訊息序列中，**在終止事件之前至少有一則帶內容的
> 增量事件**（即訊息數 > 1，且第一則帶內容的事件早於終止事件）

秒數則整條移進 NFR3 的量測機制（伺服器端在送出時刻與第一個 content token 時刻之間
計時、多樣本取 P50，`requirements.md` 已把落點定在 `build-and-test`）。這與
`requirements.md` NFR3 的既有寫法一致，本建議不改它，只是把 AC 與 NFR 的分工講清楚。

---

### 1. 一條橫跨全檔的阻塞事實：唯一的前端自動化層沒有 LLM 憑證

這是我這一輪最重要的發現，它影響 12 條 AC。

- `deploy/docker-compose.test.yml:36–38` 逐字：`OPENROUTER_API_KEY: ""`，
  註解原文「A1 generation is out of scope for these tests; leave the key empty so
  the app boots but the LLM path stays untouched.」
- `.github/workflows/ui-regression.md:114–115` 只傳 `POSTGRES_PASSWORD` 與
  `JWT_SECRET`（另有 TCMS 三個），**沒有任何 LLM 金鑰**。
- `.github/workflows/ci.yml` 全檔無 `OPENROUTER`／`ANTHROPIC` 環境變數（grep 零命中）。

**後果**：凡 Then 依賴一次真實模型回應的 AC，在今天的 repo 裡**沒有任何自動化層**
能承載——不是「覆蓋不足」，是有無問題。共 **12 條**：
AC1.1.1、AC1.1.4、AC1.3.2、AC1.3.3、AC2.2.2、AC3.1.3、AC5.1.1、AC5.1.3、
AC6.1.1、AC6.1.2、AC6.1.3、AC10.1.1。

**建議的處置（既有先例現成）**：要求路由層與大腦執行層提供**模組層注入接縫**，
形狀直接抄 `backend/cost/advice_orchestrator.py:29–30`：

```
# Injected by tests
_run_agent: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None
_session_factory: Optional[Callable[[], Session]] = None
```

`backend/tests/test_cost_advice_agent.py:35,42,45,46` 就是它的使用與還原樣板。
有了接縫，上述 12 條的**行為面**可以在 backend `unittest` 決定性地測（意圖→交辦目標、
一句話→N 個工作項、指涉詞→作用對象），真實模型的**準確率面**留給 NFR1 的量測機制。
沒有接縫，這 12 條會全部落到手動桶，而 `project.md` 的 tcms 必做 1 明文禁止
「預設丟給手動」。

**同時要指出 `requirements.md` N-3 的一個缺口**：NFR1（準確率 ≥ 80%）與 NFR3
（首字 P50 ≤ 2s）的量測**必然需要真實模型呼叫**，而落點 `build-and-test`（3.6）
跑的是 `ci.yml` 的 backend job，那裡沒有金鑰。所以 N-3 除了「標註集 ＋ 量測機制」
之外，還隱含一項**沒有被寫下來的前提**：這兩條 NFR 的量測跑在哪裡、金鑰從哪來、
它是不是 PR 閘門（若是，每個 PR 都要付 LLM 費用；若否，它就不是閘門而是定期量測）。
建議把這一句補進 M-1／M-3 的說明，交給 `delivery-planning`（2.9，ALWAYS）估算。

---

### 2. 可達性：兩條 AC 的 Given 在現況下不成立

**QA-1（Critical）— AC1.4.3 的 Given 在預設 seed 下不可達。**

我對 `backend/services/rbac_seed_data.py` 的 `DEFAULT_ROLE_PERMISSIONS` 實算了
11 個正式角色對瀑布五個 story 的 view 權限：

| 角色 | 具備 view 的瀑布 story |
|---|---|
| Developer | A1, A3 |
| FinOps_Analyst | A1, C1 |
| Ops_Lead | A1, A3, C1 |
| Platform_Admin | A1, A3, C1, J3a, J3b |
| Platform_Engineer | A1, A3 |
| Platform_Owner | A1, A3, C1, J3a, J3b |
| Project_Admin | A1, A3, C1, J3a, J3b |
| Project_Architect | A1, A3, C1 |
| Project_Editor | A1, A3, C1 |
| SRE | A1, A3, C1 |
| Security_Reviewer | A1, A3, J3a |

**11 個角色全部具備 A1 view**，而 `frontend/src/App.tsx:22` 的第一道是
`if (canArch('view')) return <Navigate to="/workspace" />`。因此
「不持有上述任何一項權限」這個狀態**沒有任何預設角色能達到**，`/403` 這個終點在
seed 之下不可達。它不是完全不可達——可以用既有的 `PUT /api/auth/role-permissions`
（openapi 42 個 path 中確實有 `['get','put']`）先把某角色的五格關掉再登入——
但那是一個目前沒有任何測試做過的 setup 步驟，必須在 AC 的 Given 裡寫明，
否則測試作者會以為挑一個低權限角色登入就能重現。

**QA-2（Critical）— 第四個落地結果沒有任何 AC 守住，而它是授權面。**

`App.tsx:21` 在瀑布之前還有一道：`if (isPending) return <Navigate to="/waiting-approval" />`
（`isPending` = `authorization_status === 'pending'`，`AuthContext.tsx:111`）。
FR1.8 逐字引用了瀑布的五道，**沒有提到這一道**；AC1.4.1／1.4.2／1.4.3 也沒有。
而 FR1.8 要求入口頁權限「置於既有 `DefaultRedirect` 權限瀑布之**首**」——照字面
實作有可能把它插在 `isPending` **之前**，於是一個**尚未通過授權**的帳號只要角色
帶有入口頁權限就會進入入口頁，繞過 `/waiting-approval`。這條迴歸**不會有任何 AC 紅燈**。

建議新增（我建議的唯一一條新 AC）：

> **AC1.4.4** **Given** 我的帳號 `authorization_status` 為 `pending` 且我的角色持有
> 入口頁權限，**When** 我登入並造訪 `/`，**Then** 我落在 `/waiting-approval`，
> **不**落在入口頁——入口頁權限**不得**置於 pending 判定之前

落點 Playwright e2e（需要一個 pending 帳號；`backend/database.py:95–103` 的 demo
persona 全部 `authorization_status="approved"`，所以這個帳號要在測試內建立或以
既有的 `PATCH /api/auth/me/authorization-request` 造出來——請在 DoD 寫明）。

**QA-3（Major）— AC1.4.2 的可達性是 OQ-11 的隱性約束，現在要寫下來。**

AC1.4.2 需要一個「無入口權限、有架構圖權限」的角色；AC1.4.3 需要一個「五格全無」
的狀態。兩者都取決於 OQ-11（入口頁 story id 的 seed 要給哪些角色）。若 OQ-11 決定
11 個角色全給，AC1.4.2 立刻變成不可達。建議在 US1 的 DoD 寫一條可執行約束：
**入口頁權限的預設 seed 必須至少留一個正式角色不持有它**，否則 AC1.4.2 是死碼。
這條要在 OQ-11 定案時被看到，不能等實作。

**QA-4（Major）— AC5.1.2 的 Given 不可構造，連帶使 AC1.1.2 的五值宣稱只驗到三值。**

AC5.1.2 的 Given 是「兩個工作項中第二項依賴第一項的結果」。但線框 §8 的依據段逐字
寫著：「拆解後的**交辦順序**與其判定方式未定，見 `user-flow.md` 的 Assumptions」。
**沒有任何已核可產出定義「什麼情況算依賴」**，所以測試作者無法構造這個 Given，
`等待中` 這個狀態也就無從產生。連帶後果：AC1.1.2 斷言狀態 ∈ 五值集合，
但若 `等待中` 永不產生、`已停掉` 只在更正路徑產生，一次測試實際只會觸及
`處理中`／`完成`／`失敗`；「∈ 五值」這種集合成員斷言**在只產生一個值時照樣綠燈**。
建議：AC1.1.2 的驗收要求改為「五個狀態值**各自**都有一條產生它的路徑可被觸發」，
並把依賴判定規則指派 `domain-design`（2.6，CONDITIONAL）／轉移
`units-generation`（2.7，ALWAYS）。

---

### 3. 二元可判性：三條 AC 的 Then 需要人的判斷

**QA-5（Major）— AC1.3.1 的「明講它有沒有留下東西」沒有可判準的觀察集合。**

線框 §13 的「兩個本站定案的行為」逐字聲明：「框中的『這件沒有產生任何變更』是
**該情境下**的訊息文案，**不是對所有情境的承諾**」。也就是說，上游刻意不列舉訊息集合。
於是 QA 無法判定任何一段文字算不算「明講」。可判形式：

> **Then** 該工作項的狀態徽章為 `已停掉`，**且**其下存在一個固定 `data-testid` 的
> 殘留說明元素，其文字**非空**且屬於已定案的訊息集合之一

訊息集合由 `refined-mockups`（2.5，**CONDITIONAL**）列舉；轉移目標
`tcms-test-cases`（3.8，**ALWAYS**）——後者本來就必須把每個外部可觀察行為分桶，
是誠實的承接站。徽章那半部（`已停掉`）現在就可判，字串已由線框釘死。

**QA-6（Major）— AC4.2.1 的「後續任何對話」是無界全稱量化。**

「不再出現在**後續任何對話**的脈絡組裝中」——「任何」的量詞範圍無界，有限次測試
無法證實。可判形式：「(a) 該記憶列不再出現在同一使用者、同一作業對象的脈絡組裝
結果中（以 id 比對）；(b) 『我的記憶』頁不再列出它」。兩條都是有界的集合斷言。

**QA-7（Minor）— 三處「經由既有授權路徑被拒」需要一個可比對的觀察值。**

AC9.2.3（「拒絕經由既有的 `require_story_action` 路徑」）、AC10.1.5、AC4.3.3 都要求
「被拒」且「走既有路徑」。單看 403 無法區分是哪一道擋的。可判形式：斷言
**403 ＋ `detail` 以 `權限不足：需要 <story>.<action>` 開頭**——這個字串是
`backend/services/rbac.py:271–276` 的 f-string 逐字產出，而未授權帳號那一道的訊息
是不同的（`:263–266`「帳號尚未通過管理員授權，無法使用業務功能」）。兩者可機械區分，
所以這條建議是零成本的，只是把觀察值寫進 AC 的 Then。

---

### 4. 只有「不存在」的斷言會在功能壞掉時照樣綠燈

六條 AC 的 Then 只斷言某事**不發生**：AC1.2.1（不建立工作項）、AC2.1.3（不顯示脈絡列）、
AC3.1.2（不含共享訊息）、AC6.1.3（無法解析）、AC7.1.3（不收到通知）、
AC8.1.3（token 不在 query string）。這類斷言在「功能整個沒做／連線根本沒建立」時
一樣通過。其中四條已經被同故事內的正向 AC 配對保護（AC1.2.1 有「列出候選判讀」、
AC2.1.3 有 AC2.1.1／2.1.2、AC3.1.2 有 AC3.1.3、AC7.1.3 有 AC7.1.1），**兩條沒有**：

**QA-8（Major）— AC8.1.3 需要配對的正向斷言。**
「檢視該連線的網址，認證 token 不出現在 query string 內」在「WS 根本連不上」時通過。
建議 Then 補成兩半：「(a) 以 token 僅置於 `Sec-WebSocket-Protocol`（或握手後首則訊息）
的握手**成功並通過認證**；(b) 以 token 置於 query string 的握手**被拒絕**」。
(b) 這半是把 FR8.5 從「我們不會那樣寫」升成「伺服器不接受那樣寫」，這才擋得住
未來有人照抄 `collab_router.py:257` 的既有前例。兩半都落在
`TestClient.websocket_connect`。

**QA-9（Minor）— AC6.1.3 的「系統無法解析它」需要指名可觀察的結果。**
「無法解析」在畫面上長什麼樣沒有定義：是走 US1.2 的反問？回一則錯誤？沉默？
建議指向已存在的失敗路徑（反問），與 AC6.1.2 一致，否則它是一條沒有預期結果的 AC。

---

### 5. 需要目前不存在的機制的 7 條 AC

這一節是「AC 要的機制還不存在」，不是覆蓋不足。

| AC | 卡在哪 | 機械證據 |
|---|---|---|
| AC2.1.4（重啟後還原） | 測試 stack 沒有 Redis，也沒有重啟步驟 | `deploy/docker-compose.test.yml` 只有 `db`／`backend`／`frontend` 三個服務；`backend/requirements.txt` **沒有任何 redis 客戶端**；backend `unittest` 以 `sys.modules.setdefault("psycopg2", MagicMock())` 改走 in-memory SQLite（`tests/helpers.py`） |
| AC4.2.2（刪除留稽核，管理者查得到） | 無讀取介面 | 見下方 QA-10 |
| AC4.2.3（90 天清除） | 承載者是 GitHub Actions workflow（FR4.5a／N-6），**沒有任何測試層能觸發一次 workflow** | — |
| AC4.3.1／4.3.2／4.3.3 | 無稽核表、無讀取介面 | 見下方 QA-10 |
| AC9.1.2（既有圖遷入新階層） | 測試 DB 每次全新，構造不出「遷移前就存在的圖」 | `docker-compose.test.yml` 檔頭逐字「The database is created fresh every run (no volume)」；且 `schema_rbac.sql` 只在空 volume 執行（`architecture.md` 約束六），既有環境的唯一演進路徑是 `database.py` 的 6 支 `_ensure_*`，而它們**全部 `except Exception: logger.warning`** 吞掉失敗（`database.py:204–209`、`:251–256`、`:321–326`、`:493–500`、`:519–526`） |

**QA-10（Major）— US4.3 三條 AC 今天沒有任何介面可滿足，這件事現在就能定案，不必等實作。**

故事旁的界線說明寫「本站不預判它需不需要（新查詢畫面）」。我對 42 個 openapi path
做了機械檢查，答案現在就有：

- 42 個 path 中，路徑含 `audit`／`activity`／`history`／`memor` 者**零命中**。
- `backend/models.py` 的 13 個模型中唯一的稽核表是 `EstimateAuditEvent`
  （`:305`，`estimate_audit_events`），而它**只有寫入端**
  （`backend/cost/estimate_audit.py:38,41`），**沒有任何讀取端點**。
- `schema_rbac.sql:196` 的 `archive_cost_audit_event` 是**已退役**的：
  `COMMENT ON TABLE` 逐字「C1 retired: archived cost audit; app must not read/write;
  drop after >=90d」。
- `/api/auth/list` 回的是 `last_activity_at`（**何時活動過**），不是**改了什麼**；
  `/api/auth/authorization-requests` 回的是角色申請，與記憶可見範圍變更無關。

所以「可見範圍被誰在何時由什麼改成什麼」這件事，**既沒有表、也沒有端點**。
US4.3 的三條 AC 不是「可能需要新畫面」，是**確定需要一個新的稽核讀取面**
（表 ＋ 端點 ＋ 授權，畫面則取決於是否要給人看）。建議把故事旁的條件句改成定案，
納入 `requirements.md` 的回補清單（性質同 N-7），交由 `delivery-planning`（2.9，ALWAYS）估算。
若使用者選擇不做，那麼 P-4 在本 intent 就沒有任何使用者可觀察行為，`[US:U1]`＝A
的前提（「給他故事，但只限取得紀錄這一面」）就不成立——這個後果要在關卡上讓使用者看到，
不要靠下游發現。

**QA-11（Major）— 由測試可觀察性推出的一項回補：真 Redis 的 CI job。**

`requirements.md` 的 NFR6 已經為 FR4.2 的獨立 schema 要了一個**對真實 PostgreSQL 執行的
CI job**（N-2）。AC2.1.4 ＋ NFR4（session 一律放 Redis、重啟可還原）有**完全同型**的
驗證缺口——現行測試基礎設施沒有 Redis，也沒有第二個載體——但七項回補清單裡**沒有它**。
建議補為一項（暫稱 N-8）：**一個帶 `redis` service container 的 CI job，或一個
`fakeredis` 層級的替身**，範圍限於「狀態寫入 Redis、以新行程讀回、脈絡與作業對象一致」。
不補的話 AC2.1.4 只能手動，而它是 NFR4 唯一的使用者可感知面。

---

### 6. 兩條 AC 可能在**正確實作**上失敗（false-fail）

**QA-12（Major）— AC8.1.2 沒有帶上節流前提，因此正確實作也會紅燈。**

`backend/services/activity.py:26` 是 `ACTIVITY_WRITE_THROTTLE = timedelta(minutes=5)`，
且 `should_record_activity` 的 docstring 逐字：「距上次寫入**未滿** throttle → 不寫入」，
計時基準是「上一次成功寫入的時刻」（滑動視窗）。而任何測試流程都會先登入，
登入後的 `GET /api/auth/me` 走 `get_user_from_token(record=True)` →
`record_activity` 寫入一次（`architecture.md` 資料流第 3 點、`auth.py:80–83`）。
於是幾秒後的 WS 互動**在正確實作下也不會更新時間戳**，AC8.1.2 照字面會失敗。
FR8.4 有寫「節流仍為既有的 5 分鐘」，AC 把它漏掉了——這正是
`project.md` 的 `functional-design:c2`（「AC 的 Then 子句必須逐字拆解，不得以概括語轉述」）
所指的形狀。建議 Given 補成「**Given** 我的 `last_activity_at` 為空或距上次寫入已滿
5 分鐘」。我**不建議**把 Then 改成「WS 認證路徑以 `record=True` 呼叫活動記錄器」——
那是實作斷言。

**QA-13（Minor）— 登入後有一個短暫的 `/403` 視窗，會讓 US1.4 的斷言不穩。**

`frontend/src/context/AuthContext.tsx:86` 在 `login()` 中先同步
`setUser({ username, role, permissions: {}, authorization_status: 'approved' })`，
之後才 `await fetchMe(...)`。在那個空隙裡 `can()` 對所有 story 回 false
（`:114–126`），`DefaultRedirect` 會走到 `:27` 的 `/403`。`expect(page).toHaveURL()`
會重試所以最終值會穩，但任何「**不**落在 `/403`」型的斷言（含我上面提的 AC1.4.4）
可能捕捉到那個瞬間。建議 US1.4 的 DoD 註明：落地斷言一律對**最終**路徑斷言、
不對過程斷言。這一項偏實作，我只放在這裡供 lead 判斷是否值得寫進 DoD。

---

### 7. NFR2 的量測形狀還有一個會讓門檻回到 100% 的洞

`requirements.md` NFR2 的「同一個 `test()` 內、自行計數、只斷言一次比率」是對的，
`expect.soft` 不適用的分析也是對的（soft 不中止但仍判 fail → `.stats.unexpected` 非 0）。
我同意整段，但要補一個它沒涵蓋的入口：

**`frontend/playwright.config.ts:15` 是 `timeout: 30_000`（單一 test 的上限），
`expect: { timeout: 10_000 }`。** 把 N 個跨頁面切換情境**全部塞進同一個 `test()`**，
每個情境都含登入與多次導航、且跑在冷啟動的 compose stack 上——**極可能超過 30 秒**。
而 test 層級的 timeout 是 `unexpected`，**不是**比率失敗；於是比率斷言根本不會執行，
門檻又回到 100%，正是 R-14／R-20 要消除的形狀。同理，逐情境的 `try`／布林捕捉必須
連 Playwright 的 `TimeoutError` 一起捕捉（它是可捕捉的例外），否則單一情境的等待逾時
會把整個 test 打掉。

建議在 NFR2 的量測機制補兩句可執行條款：(a) 該 test 內以
`test.setTimeout(<N 情境的合計預算>)` 覆寫 30 秒預設；(b) 逐情境的捕捉範圍必須
包含逾時例外。另外 `fullyParallel: false`、`workers: 1`（`:16`、`:19`）意味著整個
e2e 套件是序列跑的，而 `ui-regression.md:191` 是 `timeout 15m npx playwright test`
——NFR2 的 N 個情境 ＋ NFR11 的逐情境 `test()` 會一起吃這 15 分鐘預算，
請在 `build-and-test` 的規劃裡把它當成一個真實上限，不是無限。

---

### 8. 全 62 條 AC 的承載層分派（分桶計數為實算）

| 桶 | 定義 | 條數 |
|---|---|---|
| **B1** | backend `unittest`／`TestClient`（含 `websocket_connect`）／Hypothesis，零新依賴 | **26** |
| **B2** | Playwright e2e，現有 stack 即可（不需模型回應） | **14** |
| **B3** | 需要真實模型回應 → **目前無任何層**，需注入接縫 | **12** |
| **B4** | 需要目前不存在的機制（Redis／真 PG／重啟／遷移入口／workflow 執行／稽核讀取面） | **7** |
| **B5** | 目前非二元可判或 Given 不可構造 | **3** |
| | | **62** |

- **B3（12）**：AC1.1.1、AC1.1.4、AC1.3.2、AC1.3.3、AC2.2.2、AC3.1.3、AC5.1.1、
  AC5.1.3、AC6.1.1、AC6.1.2、AC6.1.3、AC10.1.1
- **B4（7）**：AC2.1.4、AC4.2.2、AC4.2.3、AC4.3.1、AC4.3.2、AC4.3.3、AC9.1.2
- **B5（3）**：AC1.3.1（QA-5）、AC4.1.1（Q2）、AC5.1.2（QA-4）
- **B1 的一項前提**：其中 5 條的可行性建立在注入接縫上——AC1.1.2、AC1.2.2 需要
  大腦自己的接縫；AC10.1.2、AC10.1.3、AC10.2.3 可直接用既有的
  `advice_orchestrator._run_agent`。沒有接縫，前兩條會滑進 B3。
- **B1 內兩條值得點名的好 AC**：AC8.1.4（既有 5 個 SSE 端點不在變更範圍）是一條
  **清單回歸斷言**，可對 `openapi.json` 的 path 集合與路由清單機械比對，是全檔最容易
  自動化且最有防護價值的一條；AC10.2.1（逾時）雖然
  `backend/cost/advice_orchestrator.py:19` 的 `TIMEOUT = timedelta(minutes=5)`
  遠超任何測試上限，但它是**模組層常數**，`unittest.mock.patch` 可直接覆寫 → B1 成立。
  相對地 AC10.2.2（失敗）在**現有 stack 上會因為 `OPENROUTER_API_KEY: ""` 而自然發生**
  ——這是唯一因缺金鑰而**變容易**的一條，但請在測試裡斷言「可與逾時區分的具體訊息」，
  不要只斷言「出現某段失敗文字」，否則它會因為基礎設施設定錯誤而綠燈，理由是錯的。

---

### 9. 建議補進各群 Definition of Done 的測試可觀察性條款（全部是交付條件，不是 AC）

| 群 | 條款 |
|---|---|
| US1 | (1) 路由層的門檻判定必須是可被 Hypothesis 驅動的純函式（ADR-0006 PBT hard constraint 的 agent routing 落點）；(2) 入口頁權限 seed 至少留一個正式角色不持有；(3) `M-1` 含 ≥ K 筆信心 < 0.7 的輸入以證明 AC1.2.1 可達；(4) 五個狀態值各有可觸發路徑 |
| US4 | (1) 三種記憶各自的**寫入觸發條件**須被指名（否則 AC4.1.1 的 Given 無法構造）；(2) 90 天逾期判定須是純函式並與既有的 `OVERDUE_THRESHOLD`（`activity.py:31`，**帳號**逾期，同為 90 天）**命名區分**，避免兩個同值不同義的常數互相污染；(3) 稽核讀取面（表 ＋ 端點 ＋ 授權）列為回補項 |
| US8 | (1) WS 訊息契約須有可被 `TestClient.websocket_connect` 驅動的型別來源（與 NFR5 的契約閘門同源）；(2) 以 token 置於 query string 的握手須被**拒絕**，不只是「我們不那樣寫」 |
| US9 | 遷移須有**可被 `unittest` 匯入並呼叫的入口**（不得只存在於 `init_db()` 的副作用或只在空 volume 執行的 SQL 檔中），否則 AC9.1.2 只能手動 |
| US10 | 沿用既有 `_run_agent`／`_session_factory` 接縫；逾時測試以 `patch` 覆寫 `TIMEOUT` |
| 全群 | 「被拒」類 AC 一律斷言 403 ＋ `detail` 前綴，以區分是哪一道授權擋的 |

### 10. 指派與轉移目標（CONDITIONAL 一律附 ALWAYS 轉移；已回查 `.claude/tools/data/stage-graph.json` 的 34 站）

| 事項 | 落點 | execution | 轉移目標 |
|---|---|---|---|
| 三種記憶的寫入觸發條件（Q2／QA-10 前半） | `domain-design`（2.6） | CONDITIONAL | `units-generation`（2.7，ALWAYS） |
| 多意圖的依賴判定規則（QA-4） | `domain-design`（2.6） | CONDITIONAL | `units-generation`（2.7，ALWAYS） |
| 「有沒有留下東西」的訊息集合列舉（QA-5） | `refined-mockups`（2.5） | CONDITIONAL | `tcms-test-cases`（3.8，ALWAYS） |
| 注入接縫與 12 條 B3 的落點（§1） | `contract-design`（2.8） | CONDITIONAL | `tcms-test-cases`（3.8，ALWAYS） |
| NFR1／NFR3 的金鑰來源與是否為 PR 閘門（§1 末） | `build-and-test`（3.6） | **ALWAYS** | 不需 |
| NFR2 的 `test.setTimeout` 與逾時捕捉（§7） | `build-and-test`（3.6） | **ALWAYS** | 不需 |
| 真 Redis 的 CI job（QA-11，建議列為 N-8） | `infrastructure-design`（3.4） | CONDITIONAL | `ci-pipeline`（4.x）亦 CONDITIONAL → **兩者皆 skip 時須重新提交使用者**（同 `requirements.md` OQ-13 的處置形狀） |
| 稽核讀取面（QA-10） | 回補清單 ＋ `delivery-planning`（2.9） | **ALWAYS** | 不需 |

## Positions

- AGREE: **AC 一律描述系統行為、「須有某某測試」歸 Definition of Done** — 我把
  第 9 節的每一條都寫成交付條件而非 AC，正是因為元層次 AC 驗的是有沒有寫測試，
  而本 repo 已有實證顯示照做也抓不到要防的缺陷。
- AGREE: **US1.4 刻意不為「無權限者看到的入口頁」寫 AC，並把理由寫在故事旁** —
  這是正確的可達性判斷，也是全檔最該被保留的紀律；我在 QA-1／QA-2 做的就是把同一把尺
  用在剩下三條 AC 上。
- AGREE: **AC6.1.3 與 AC1.2.4 刻意寫成獨立 AC 而非藏在前提裡** — 前者把能力 3 與
  能力 6 的交界從實作手上收回來，後者讓「路由層不吐信心值」不能靜默通過。
  這兩條是本檔品質最高的設計。
- AGREE: **`requirements.md` NFR2 對 `expect.soft` 的分析** — 「不中止但仍判 fail」
  的區分是對的，且它精準指出了 `.stats.unexpected` 會讓門檻回到 100%。我只補了它
  沒涵蓋的第二個入口（單一 test 的 30 秒上限與逾時例外，見第 7 節）。
- AGREE: **三項量測交付物不寫成故事（`[US:U3]`＝A）** — 沒有 persona 的東西硬套
  `As a [persona]` 會產出反樣式；`M-*` id 讓 `delivery-planning` 看得到它們，足夠了。
- OBJECT: **12 條 AC（B3）在今天的 repo 裡沒有任何自動化層能承載，而本檔沒有記載
  這件事** — 唯一的前端自動化層跑在 `OPENROUTER_API_KEY: ""` 的 stack 上
  （`deploy/docker-compose.test.yml:36–38` 連註解都寫明「LLM path stays untouched」），
  `ui-regression.md:114–115` 與 `ci.yml` 也都沒有金鑰。不在故事層記下這件事，
  它會在 `tcms-test-cases` 的分桶時被整批丟進「只能手動」，而那正是
  `project.md` 必做 1 明文禁止的預設行為。
- OBJECT: **AC1.4.3 的 Given 在預設 seed 下不可達，而本檔把它當成可驗收的 AC** —
  11 個正式角色**全部**具備 A1 view（實算 `rbac_seed_data.py`），而 `App.tsx:22`
  的第一道就是 `canArch('view')`，所以 `/403` 終點沒有任何角色能到達。它可以用
  既有的 `PUT /api/auth/role-permissions` 造出來，但那個 setup 步驟必須寫在 Given 裡。
- OBJECT: **`isPending → /waiting-approval` 這第四個落地結果沒有任何 AC 守住，
  而 FR1.8 的「置於瀑布之首」照字面實作可以繞過它** — 這是授權面的無聲迴歸，
  建議新增 AC1.4.4（第 2 節有完整措辭）。這是我唯一主張新增的 AC。
- OBJECT: **AC4.1.1 目前不可二元判定，且它的 Given 不可構造** — 前者有零成本的修法
  （改成 AC4.1.2 的斷言對象形狀），後者是真缺口：沒有任何需求說什麼事件會產生一筆
  語意或程序記憶。寫入端懸空，而本 intent 已在 `projects`／`systems` 上犯過同型的錯。
- OBJECT: **US4.3 的「若實作時發現需要新查詢畫面才列回補」應改為現在就定案** —
  42 個 openapi path 中稽核／歷史／記憶類端點**零命中**，唯一的活稽核表
  `estimate_audit_events` 只有寫入端，`archive_cost_audit_event` 的 `COMMENT` 逐字是
  `app must not read/write`。答案已經可以機械判定，不必留給實作；留著會讓 P-4 的
  唯一一組 AC 在下游靜默落空。
- OBJECT: **AC8.1.1 不該由 Playwright 的計時斷言當閘門** — `retries: 1` ＋
  `ui-regression.md:284–289` 明文容忍 `.stats.flaky`，時間敏感測試「紅了重試變綠」
  會被放行；且單樣本推不出 P50。它的實質是順序性質，應改為 WS 訊息序列的順序斷言
  並落在 `TestClient.websocket_connect`（starlette 1.6.0 已支援、零新依賴、
  但本 repo 全樹零使用）。秒數整條交給 NFR3 的量測機制。
- OBJECT: **AC8.1.2 在正確實作下也會失敗** — 5 分鐘滑動節流
  （`activity.py:26` ＋ `should_record_activity` 的 docstring）遇上「測試必先登入、
  登入即寫入一次」，使幾秒後的 WS 互動合法地不更新時間戳。FR8.4 寫了節流、AC 漏了，
  Given 須補上節流前提。
- OBJECT: **七項回補清單漏了一項由驗證需求逼出來的機制：真 Redis 的 CI job** —
  NFR6 已為獨立 schema 要了真 PG 的 job（N-2），AC2.1.4／NFR4 有完全同型的缺口
  （測試 stack 無 Redis、`requirements.txt` 連 redis 客戶端都沒有、backend 測試走
  in-memory SQLite），卻沒有對應項。建議列為 N-8。
