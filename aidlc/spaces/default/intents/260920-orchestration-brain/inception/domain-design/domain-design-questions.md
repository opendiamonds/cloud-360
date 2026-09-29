# Domain Design Questions — 統一入口大腦

<!-- Stage: domain-design（Inception 2.6）· Record: 260920-orchestration-brain
     lead: aidlc-architect-agent · support: aidlc-aws-platform-agent, aidlc-design-agent
     mode: inline · summary_confirmation: required · review_class: advisory -->

## 來源標籤慣例

| 標籤 | 指向 |
|---|---|
| `[Q<n>]`／`[F<n>]`／`[S<n>]` | intent-capture／feasibility／scope-definition 的作答 |
| `[R<n>]` | rough-mockups 的作答 |
| `[RA:...]` | requirements-analysis（`[RA:R<n>]` 作答、`[RA:FRx.y]`／`[RA:NFRn]` 需求） |
| `[US:U<n>]` | user-stories 的作答 |
| `[DM:D<n>]` | refined-mockups 的作答 |
| `[DD:E<n>]` | **本站新增**——domain-design 的作答（用 `E` 避開既有 D／DM 撞號） |
| `[kb:<檔>]` | codekb 的事實，附其證據標記 |
| `[實測]` | 本站對 repo 現況的唯讀查證 |

## 出題前的查證（**非**來源登錄，僅供題幹與選項引用）

| # | 查證項 | 結果 |
|---|---|---|
| V-1 | story id 的命名慣例與規模 | `(role, story_id, view, edit, review)` 五元組，**308 列＝11 角色 × 28 個 story id**（實算）。id 形狀為「大寫字母＋數字（＋可選小寫尾綴）」；已用字首 **A、B、C、D、E、F、G、H、J**；**K 起全部未用** |
| V-2 | `UserDiagram` 的擁有關係 | `user_id = Column(Integer, ForeignKey("users.id"), nullable=False)`——**NOT NULL**。另有 `diagram_shares` association table（`user_id` ＋ `diagram_id` 皆為 primary key）做多對多分享 |
| V-3 | 向量檢索前例 | **零**。全 `backend/` 對 `pgvector`／`embedding`／`vector(` 命中 0 |
| V-4 | Redis 現況 | **零基礎設施用途**。`[kb:architecture]` 記載全樹 13 個 `redis` 命中全部是領域內容（WA 建議文字、lens JSON、drawio 模板、AWS 服務清單 prompt）。加 Redis 是第 5 個服務，觸發 env contract 的 blocking 規則（`[kb:architecture]` 約束八） |
| V-5 | 獨立 schema 的前例與可測性 | **兩者皆無**。全樹無 `CREATE SCHEMA`、無 `search_path`；測試走 in-memory SQLite（`tests/helpers.py` 換掉 `psycopg2`），**SQLite 沒有 schema 概念**（`[kb:architecture]` 約束七） |
| V-6 | 既有環境的 schema 演進路徑 | 只有 `database.py` 的 6 支 `_ensure_*` 補丁，且**全部以 `except Exception: logger.warning` 吞掉失敗**。`schema_rbac.sql` 只在空 volume 執行、且含裸的 `DELETE FROM role_permissions;`（`[kb:architecture]` 約束六） |
| V-7 | LangGraph 串流能力 | `langgraph_runtime.py:133–149` 已有 `astream_graph`，但**全樹零消費者**。「既有 runtime 不能串流」是錯的說法，不可拿來當自建第二個 runtime 的理由（`[kb:architecture]` 約束五） |

## 已由上游定案、本站不重問

| 已定案項 | 內容 | 來源 |
|---|---|---|
| 三種記憶落在同一 DB 的獨立 schema | semantic／procedure／episodic | `[F3]`、`[RA:FR4.1]`／`[RA:FR4.2]` |
| 記憶的最小權限模型 | 記憶列帶擁有者與可見範圍；擁有者由記憶層依已驗證身分設定、可見範圍預設最窄 | `[F9]`、`[RA:FR4.3]`／`[RA:FR4.3a]`／`[RA:FR4.3b]` |
| session 狀態放 Redis | 不得放行程記憶體；重啟後脈絡可還原 | `[RA:R7]`、`[RA:NFR4]` |
| 串流機制為 WebSocket | 既有 5 個 SSE 端點不在變更範圍 | `[F4]`、`[RA:FR8.2]` |
| 成本能力一律走 HTTP 帶 token | 不得同進程繞過 `require_story_action` | `[F14]`、`[RA:FR10.2]` |
| 入口頁有自己的 story id | 置於 `DefaultRedirect` 瀑布之首 | `[R8]`、`[RA:FR1.8]` |
| `/memory` **不需要**新 story id | 走 `ProtectedRoute`，由擁有者欄位把關 | `[DM:D1]`＝C 的查證 |
| 建立路徑有兩個入口、共用一條寫入路徑 | 脈絡列選單 ＋ 對話式，皆經 `require_story_action` | `[DM:D2]`＝D、`[RA:FR9.5]` |
| 90 天清除由 gh-aw／Actions workflow 承載 | 不得是 `backend/` 內的排程程式 | `[RA:FR4.5a]` |

---

## E1. 大腦要切成幾個元件？

這是本站的核心題。`[RA]` 的 10 個 FR 群組都要落到元件上，而切分方式有多種可行解。
下列選項的元件皆為**我們要寫的程式**，不含基礎設施（Redis／PostgreSQL 是
`external_dependencies`，不是元件）。

- **A. 六個元件**（建議）：
  `IntentRouter`（意圖識別、信心值、多意圖拆解）、
  `SessionContext`（作業對象、共享↔獨立、Redis 讀寫）、
  `WorkOrchestrator`（工作項狀態機、逐項導回、交辦給能力轉接層）、
  `MemoryStore`（三種記憶、擁有者與可見範圍、稽核）、
  `ProjectHierarchy`（`projects`／`systems`、遷移、建立路徑）、
  `BrainGateway`（WebSocket 端點、訊息封包、串流）。
- **B. 三個粗粒度元件**：`BrainCore`（路由＋編排＋session＋gateway 全包）、
  `MemoryStore`、`ProjectHierarchy`。
- **C. 八個細粒度元件**：A 的六個，再從 `WorkOrchestrator` 拆出
  `CapabilityAdapter`（呼叫既有 A1／A3／C1 的 port），從 `IntentRouter` 拆出
  `ClarifyResolver`（反問候選的產生與收束）。
- **D. 兩個元件**：`Brain`（除階層外全部）、`ProjectHierarchy`。

[Answer]: A
<!-- A = 六個元件：IntentRouter／SessionContext／WorkOrchestrator／MemoryStore／ProjectHierarchy／BrainGateway｜作答時間 2026-09-25T06:14:55Z（date -u 取值）。依選項內容比對回寫。 -->

## E2. `user_diagrams.user_id` 的 NOT NULL 怎麼處理？

`[實測 V-2]`：該欄是 **NOT NULL** FK 指向 `users.id`，且 `[kb:component-inventory]`
明文指出這是全 repo 唯一的擁有關係。插入「專案 → 系統 → 架構圖」中介層時，
這個欄位的去向是一個不可迴避的決定——`[RA:FR9.2]` 只說「應能遷入新階層」，沒說怎麼接。

- **A. 保留 `user_id`，新增 nullable 的 `system_id`**（建議）：`user_id` 仍是
  「誰建的」，`system_id` 是「屬於哪個系統」。兩者並存，舊程式碼零改動，可回復。
  代價：擁有語意有兩個來源，需明訂誰是權威。
- **B. 改指**：移除 `user_id`，架構圖改由 `System` 擁有，擁有者經
  `systems → projects` 上溯。語意最乾淨，但需 backfill 全部既有列，且
  `[實測 V-6]` 顯示既有環境的唯一演進路徑是會吞掉失敗的 `_ensure_*` 補丁——
  **失敗會靜默**。不可逆。
- **C. 保留 `user_id` 但標記 deprecated**：新圖只寫 `system_id`，舊圖維持只有
  `user_id`，讀取端兩種都要處理。

[Answer]: A（於加開 E8 後取得）
<!-- A = 保留 user_id、新增 nullable system_id｜作答時間 2026-09-25T06:26:08Z。首次作答為重新框定（原文保留於下方註解），經 E8 界定範圍後回頭補答本題。 -->
<!-- 作答時間 2026-09-25T06:14:55Z（date -u 取值）。使用者的回覆原文：

「一個專案，多個需求。一個需求有可能影響多個系統，一個系統一份drawio架構圖，
一份drawio架構圖會有多個架構圖tab，需求不用被完整紀錄，只要讓架構圖在被異動時
被紀錄，因為什麼需求被異動，紀錄內容只要是摘要即可」

此回覆**不是 A／B／C 任一項**，而是對階層本身的重新框定：它引入一個已核可需求中
不存在的實體（需求／Requirement）與一組新關係（專案 1:N 需求、需求 N:M 系統），
並要求架構圖異動時記錄「因為哪個需求」的摘要。依 project.md 的
`application-design:260822-ad-L3`（重新框定須先查證再決定採納或追問）與
`approval-handoff:e2923632`（推翻上游定案時須先界定反轉範圍、再把「就地修訂 vs
重跑」交由使用者裁決），本站不逕自吸收，加開 E8 界定範圍。
**原 E2 的問題（`user_id` NOT NULL 的去向）仍未被回答**，併入 E8。 -->

## E3. 既有架構圖的遷移歸屬規則（`[RA:FR9.3]`）

`[RA:FR9.3]` 把「遷移的歸屬規則、遷移步驟與回復方式」指派給本站。

- **A. 每個使用者一個預設專案 ＋ 預設系統**（建議）：遷移時為每個持有架構圖的
  使用者建立「<使用者>的專案／預設系統」，其現有圖全部掛進去。使用者之後可改名、
  可搬移。回復方式：刪除新建的 `projects`／`systems` 列並清空 `system_id`。
- **B. 單一全域「未分類」專案**：所有既有圖掛進同一個專案。遷移最簡單，但
  `diagram_shares` 的多對多分享會讓不同使用者的圖混在同一個專案下，可見性語意衝突。
- **C. 不自動遷移**：既有圖維持無階層（`system_id` 為 `NULL`），只有新建的圖有階層。
  代價：`stories.md` 的 `AC9.1.4` 逐字要求遷移後 `system_id IS NULL` 的計數為 **0**
  且**必須大聲失敗**——選 C 會讓那條已核可的 AC 永遠不可滿足。

[Answer]: A
<!-- A = 每個使用者一個預設專案 ＋ 預設系統｜作答時間 2026-09-25T06:14:55Z（date -u 取值）。依選項內容比對回寫。 -->

## E4. 新增哪些 story id（`OQ-11` ＋ `OQ-14`）

`[實測 V-1]`：現有 28 個 story id，字首 A–H、J 已用，**K 起未用**。
`[RA:FR1.8]` 要求入口頁有自己的 story id；`[RA:FR9.5]` 要求 `projects`／`systems`
的讀寫刪一律經 `require_story_action`。`[DM:D1]`＝C 已定案 `/memory`
**不需要** story id。新增 story id 會觸發 `schema_rbac.sql` ＋ `DEPLOY.md`
的 blocking 同步（回補項 N-5 已登記此事）。

- **A. 新字首 `K`，兩個 id**（建議）：`K1` 統一入口頁、`K2` 專案／系統階層。
  `K` 是全新功能域，與既有 A（架構）／C（成本）／J（管理）語意不重疊。
- **B. 併入既有字首**：`A5` 入口頁、`A6` 專案／系統（都算「架構」域）。
  不新增字首，但把「統一入口」塞進 A 域會讓 `canArch()` 這類既有 helper 的語意變模糊。
- **C. 單一 id `K1` 涵蓋全部**：入口頁與階層共用一個權限格。最省，但「能進入口頁」
  與「能刪別人的專案」會變成同一個開關。
- **D. 三個 id**：`K1` 入口頁、`K2` 專案、`K3` 系統（專案與系統分開授權）。

[Answer]: A
<!-- A = 新字首 `K`，兩個 id：K1 統一入口頁、K2 專案／系統階層｜作答時間 2026-09-25T06:14:55Z（date -u 取值）。依選項內容比對回寫。 -->

## E5. 誰可以放寬記憶列的可見範圍（`OQ-12`）

`[RA:FR4.3b]` 定案：可見範圍預設最窄（僅擁有者可見），**放寬是一個獨立的、需授權的
操作，且每次變更須留稽核紀錄**。上游把「哪些角色」指派給本站。
`[實測 V-1]`：現有 11 個角色，action 欄位為 `(view, edit, review)` 三個。

- **A. 只有 `Platform_Admin` 與 `Platform_Owner`**（建議）：最窄。記憶是個人資料，
  放寬它等於讓別人看見某使用者的偏好與對話歷程，屬平台治理層的動作。
- **B. 擁有者自己 ＋ 上述兩者**：使用者得主動分享自己的記憶（例如讓同組看見
  「這個專案的慣用命名」）。較實用，但使用者可能在不理解後果時放寬。
- **C. 擁有者自己**：完全由個人決定，平台不介入。
- **D. 目前誰都不能**：第一版只實作「可見範圍欄位 ＋ 預設最窄 ＋ 稽核機制」，
  放寬操作留給後續 intent。

[Answer]: A
<!-- A = 只有 `Platform_Admin` 與 `Platform_Owner` 得放寬記憶列的可見範圍｜作答時間 2026-09-25T10:17:29Z（date -u 取值）。 -->

## E6. Redis 中 session 的存活期與清除條件（`OQ-9`，並解 `G-1`／`G-2`）

`[RA:NFR4]` 定案 session 放 Redis、重啟後脈絡可還原，但**誰清、何時清沒有定義**
——這是 requirements-analysis 自己的契約端點自檢查出的缺口。refined-mockups
又查出兩個同源缺口：工作項集合無人清除（**G-1**）、作業對象無人清回
`no-object`（**G-2**，使該狀態只在首次使用可達）。三者是同一個問題的三個面。

- **A. 單一 session key ＋ TTL 續期**（建議）：作業對象、共享／獨立狀態、工作項集合
  全部放在**同一個** Redis key 之下，TTL 24 小時、每次互動續期。TTL 到期即三者
  一起消失，下次進入就是全新 session（作業對象回 `no-object`）。**一個機制同時解掉
  OQ-9、G-1、G-2**。代價：使用者隔天回來會失去脈絡——但那正是「還原」的邊界。
- **B. 顯式清除，無 TTL**：登出時刪除 key。脈絡可以跨很多天存在。代價：從不登出
  的使用者其 key 無限成長；且 `no-object` 仍然不可達（沒有事件會清作業對象）。
- **C. TTL ＋ 顯式清除並存**：TTL 作為兜底，登出與「切換對象」時另有顯式清除路徑。
- **D. 分成兩個 key**：作業對象一個（長 TTL）、工作項一個（短 TTL）。工作項會先
  消失而作業對象留著。

[Answer]: A
<!-- A = 單一 session key ＋ TTL 24 小時、每次互動續期；一個機制同時解 OQ-9／G-1／G-2｜作答時間 2026-09-25T10:17:29Z（date -u 取值）。 -->

## E7. 語意記憶的檢索方式（`OQ-2`）

`[RA]` 的 `A-2` 假設與 `C-T5` 約束都掛在這一題上。`[實測 V-3]`：本 repo
**零向量檢索前例**（`pgvector`／`embedding`／`vector(` 全 `backend/` 命中 0）。

- **A. 不用向量：PostgreSQL 全文檢索 ＋ 標籤**（建議）：語意記憶是短句陳述
  （線框 §9 的三區各是「一句可判斷對錯的話」），量級小。零新擴充、零新運維面，
  且 `[實測 V-5]` 已顯示獨立 schema 本身就是零前例——同時引入向量會讓驗證缺口疊加。
- **B. `pgvector`**：新增 PostgreSQL 擴充。檢索品質最好，但這是第 6 個
  基礎設施決定（Redis 已是第 5 個服務），且既有測試走 SQLite，**向量檢索在測試
  路徑上完全無法驗證**。
- **C. 第一版不做檢索**：把該使用者的全部語意記憶一次取出交給 LLM 判斷相關性。
  最簡單，但脈絡窗成本隨記憶量線性成長，且 `[RA:NFR3]` 的首字 P50 ≤ 2 秒預算
  幾乎全被路由層 LLM 吃掉，再加負擔有風險。

[Answer]: B（pgvector）＋ Ollama 容器 ＋ bge-m3 作為向量來源
<!-- 作答時間 2026-09-25T10:17:29Z（date -u 取值）。**本題經三輪收斂，如實記載過程**：

 1. 初答 B（pgvector）。我依 project.md 的「使用者選項會製造新正確性問題時須具名
    指出」提出兩項具體後果（兩個 compose 的 image 都要換、embedding 是一條新的
    LLM 路徑且落在 repo 已知盲區又無花費計量）。
 2. 使用者先答「接受並寫成顯性要求」，隨即改為「那 E7 改選你建議的」（＝A 全文檢索），
    再改為「還是用 pgvector，但幫我找不用錢的方案」。
 3. 使用者追問「openrouter 沒有免費的模型嗎」。**查證結果：OpenRouter 沒有
    embeddings 端點**——其 API reference 只有 `POST /api/v1/chat/completions` 與
    `GET /api/v1/generation`，該頁與 FAQ 兩處對 "embedding" 零提及。故 OpenRouter 的
    `:free` 模型是對話模型，產不出 pgvector 要存的向量；這是技術上不通，不是價格問題。
 4. 在「本機算 / 別家免費額度 / 改回全文檢索」三條路中，使用者選 **Ollama 容器 ＋ bge-m3**。

 定案後果（全部列入回補項 N-11）：
 - DB image 由 `postgres:16-alpine` 換為 `pgvector/pgvector:pg16`（Debian 基底），
   **deploy 與 test 兩個 compose 都要改**；PG 大版本相同故 `cloud360_db` volume 相容。
 - Ollama 是**第 6 個服務**（Redis 第 5），觸發 env contract 的 blocking 規則：
   新變數必須在同一個 PR 內由 `render-env.sh` 寫入並列於 `deploy/.env.example`。
 - 新增模型快取 volume（bge-m3 約 1.2GB）；Ollama RAM 約 2GB，而
   **staging 主機的 RAM／CPU 餘裕在 DEPLOY.md 與 LOCAL-DEV.md 皆無記載、本站未查證**。
 - embedding 改為本機運算，故 `[F13]`=A 的「不做花費計量」不再構成問題（零 API 費用）；
   但它仍是一條 LLM 路徑，落在 repo 三塊結構性盲區之一。
 - **衍生的硬約束**：`ui-regression` 每個 PR 起的短生命週期 stack 不可能跑 1.2GB 模型，
   故 `MemoryStore` 必須以 `EmbeddingPort` 對外，並提供決定性替身供測試使用。
   這不是選配——沒有它，測試 stack 要嘛跑不起來、要嘛每個 PR 拉一次模型。 -->

## E8.（加開）「需求」這個實體要怎麼承載，以及它動到哪些已核可產出

**加開理由**：E2 的回覆不是選項之一，而是對階層的重新框定。依 `project.md` 的
`application-design:260822-ad-L3`（重新框定須先查證是否等價，再決定採納或追問）與
`approval-handoff:e2923632`（推翻上游定案時須先界定反轉的確切範圍，不得由 AI
逕自吸收），本站先查證再出題。

**查證結果——反轉範圍比表面小**：

| 使用者原文的成分 | 是否為新東西 | 逐字證據 |
|---|---|---|
| 一個系統一份 drawio 架構圖，一份架構圖多個 tab | **不是新的** | `[RA:FR9.1]` 逐字：「一個專案有多個系統、一個系統對應**一份架構圖檔與其中多張圖**」——tab 就是「多張圖」 |
| 一個專案多個需求；一個需求影響多個系統 | **是新的** | `scope-document.md:60` 能力 9 逐字只有「專案 → 系統 → 架構圖 階層」；`stories.md` `AC9.1.1` 逐字「脈絡列顯示完整的**三層**路徑」；`backend/models.py` 對 `Requirement` 命中 **0** |
| 架構圖異動時記錄「因為什麼需求」，摘要即可 | **是新的**，且需要新表 | `[實測]`：`models.py` 的 13 個模型**沒有任何變更歷程表**，`UserDiagram` 只有會被覆寫的 `updated_at`——一次異動一列的紀錄放不進既有結構 |

**定案 C** — 摘要 ＋ 輕量標籤：不建 Requirement 表、不建多對多關聯表，
但變更紀錄帶一個需求名稱／編號欄位，可用同一標籤搜尋它影響過哪些圖。

[Answer]: C

<!-- C｜作答時間 2026-09-25T06:26:08Z（date -u 取值）。
     後果：三層階層維持不變，`[RA:FR9.1]`、`AC9.1.1`、線框 §3、mockups M4 全部
     仍然成立，**不需要修訂任何已核可產出**。但它新增一張架構圖變更紀錄表
     （含來源需求摘要與輕量標籤），那是 `scope-document.md` 的 10 項能力之外多出來的
     工作量——依 `project.md` 的 requirements 規則列為回補項 **N-10**（N-9 為 axe）。
     代價已在選項說明中揭露：輕量標籤可溯源但不保證一致（打錯字即另一個需求）。 -->

## E9.（加開）本機開發沒有 Ollama 時，embedding 怎麼切換

**加開理由**：E7 定案 Ollama ＋ bge-m3 之後，使用者指出本機開發需要因應。這是
定案的直接後果而非新範圍，故加開本題釘住切換機制。

**查證結果（兩項都會決定答案的形狀）**：

| # | 查證項 | 結果 |
|---|---|---|
| V-8 | fastembed 支不支援 bge-m3 | **不支援**。其支援清單無 `BAAI/bge-m3`；但有 `intfloat/multilingual-e5-large`（**1024** 維、多語）與 `paraphrase-multilingual-MiniLM-L12-v2`（384 維） |
| V-9 | bge-m3 的 dense 維度 | **1024** 維，多語（100+ 語言）。與 `multilingual-e5-large` **同維度**，故 pgvector 欄位可共用 `vector(1024)` |

**關鍵風險**：同維度**不等於**同向量空間。兩個模型各自產生的向量不可互相比較——
若本機寫 e5-large 的向量、staging 寫 bge-m3 的向量到同一個 schema，相似度檢索會
回垃圾**而且不會報錯**。

[Answer]: D（使用者重新框定：三個提供者並存，由設定選擇）
<!-- 作答時間 2026-09-25T10:28:55Z（date -u 取值）。使用者原文：「本機有Ollama走Ollama，沒有走
     fastembed或退回PostgreSQL全文檢索，讓使用者自己選」。

     定案內容：`EmbeddingPort` 有三個實作＋CI 的決定性替身，由設定切換
     （`ollama` | `fastembed` | `fulltext` | `stub`）。每列記憶存 `embeddingModel`，
     檢索只比對同一 model id 的列，使跨模型不相容在結構上不可能靜默出錯。
     `fulltext` 模式下建立的列其向量欄位為 NULL，之後不會被向量檢索看到，
     除非重新 embed——此事必須寫進 LOCAL-DEV.md。

     **本站自行加上的一條約束（非使用者定案，理由在此）**：偵測不到選定的提供者時
     必須**大聲失敗並列出三個可選值**，不得靜默降級為全文檢索。理由是向量與全文的
     檢索結果差異大，靜默切換會讓「為什麼找不到我的記憶」變成無法除錯的問題；而
     `phases/construction.md` 明文要求「Errors must be surfaced」，`project.md` 亦
     反覆記載靜默失敗是本 repo 的主要受害形式（實例：N8N 憑證從未寫入導致架構圖
     icons 靜默退回灰底佔位圖）。

     連帶觸發 blocking 規則：新增 `.env.example` 變數 → 必須同步更新 `LOCAL-DEV.md`
     （`project.md ## Mandated`）。三個提供者的本機設定方式亦須寫入該檔。 -->

## Consolidated Summary Confirmation

**九題定案**（`[DD:E1]`–`[DD:E9]`，其中 E8／E9 為過程中加開）：

| 題 | 定案 | 一句話後果 |
|---|---|---|
| E1 | A — 六個元件 | `BrainGateway`／`IntentRouter`／`SessionContext`／`WorkOrchestrator`／`MemoryStore`／`ProjectHierarchy`；依賴圖無環，後兩者為可平行開工的葉節點 |
| E2 | A — 保留 `user_id`，新增 nullable `system_id` | 舊程式零改動、可回復；`system_id` 為歸屬的權威來源 |
| E3 | A — 每人一個預設專案 ＋ 預設系統 | 歸屬與現行擁有者一致，不改既有可見性 |
| E4 | A — 新字首 `K`：`K1` 入口頁、`K2` 階層 | 矩陣由 308 列增為 **330** 列（實算 308 + 11×2） |
| E5 | A — 僅 `Platform_Admin`／`Platform_Owner` 得放寬記憶可見範圍 | 最窄；擁有者本人不能自行放寬 |
| E6 | A — 單一 session key ＋ TTL 24 小時續期 | **一個機制同時關掉 `OQ-9`、`G-1`、`G-2` 三個缺口** |
| E7 | pgvector ＋ **本機 Ollama（bge-m3）** | 零 API 費用；但 DB image 換、第 6 個服務、模型 volume——全列入 **N-11** |
| E8 | C — 「需求」只做變更摘要 ＋ 輕量標籤 | **不需修訂任何已核可產出**；新增一張變更紀錄表，列為 **N-10** |
| E9 | D — `EmbeddingPort` 四實作由設定切換 | 每列記憶存 `embeddingModel`，跨模型不相容無法靜默發生 |

**三份產出**：`components.md`（6 元件／7 實體／8 依賴邊／13 外部依賴，8 條
well-formedness 規則以腳本逐條驗過）、`decisions.md`（**9 個 ADR**，四段皆完整）、
`traceability.json`（20 則故事全數 `OK`）。四個 sensor 帶齊參數後全綠。

**六項送審前自檢的結果（blocking，逐項報告）**

| # | 自檢項 | 結果 |
|---|---|---|
| 1 | **可達性** | 通過。兩條「偵測 X」規則皆可達——「遷移後 `system_id IS NULL` 不為 0」可達（部分失敗）、「偵測不到 embedding 提供者」可達（Ollama 未啟動） |
| 2 | **契約端點三問** | **查出 3 處，全在「誰清」與「誰讀」**（與 requirements-analysis 那輪「寫入端最易漏」相反）：**DG-1** 稽核事件在其記憶被 90 天清除後的去向（`[RA:FR4.5]` 與 `[RA:FR4.7]` 在此互相拉扯）、**DG-2** `Project`／`System` 刪除的 cascade（會讓 `[US:AC9.1.4]` 的不變量在**執行期**被打破，而遷移當下是滿足的）、**DG-3** `DiagramChangeRecord` 無讀取端。三項皆不自行定案，指派 `functional-design`（H-7） |
| 3 | **引用逐字核對** | 通過。`[RA:FR9.1]`、`AC9.1.1`、`scope-document.md:60`、`rbac_seed_data.py` 的五元組、`user_diagrams.user_id` 的 `nullable=False`、`App.tsx:38–41` 皆開檔逐字核對 |
| 4 | **檔案集合一致性** | 通過。stage 宣告的 3 個 produces 與實際檔案相符 |
| 5 | **跨檔傳播** | 通過。六個元件名、`K1`／`K2`、`N-10`／`N-11`、1024 維、四個 Port 實作、24 小時 TTL 皆出現在 3 份產出中。`DG-1`–`DG-3` 原只在 `components.md`，已在 ADR-002／003／009 補上交叉引用 |
| 6 | **可算的數字先算再寫** | 通過。7 個數字實算全部相符（元件 6、實體 7、依賴邊 8、外部依賴 13、ADR 9、upstream 20、現有矩陣 308 列），且 308 + 11×2 = 330 |

**三件我要你特別看過的事**

**1. E8 的反轉範圍比表面小，而我是查證後才知道的。** 你那句「一個系統一份 drawio
架構圖，一份架構圖多個 tab」**已經是 `[RA:FR9.1]` 的逐字原文**（「一個系統對應一份
架構圖檔與其中多張圖」）——完全不是新東西。真正新的只有「需求」。而你自己說
「不用被完整紀錄、摘要即可」正是在避開建完整實體，所以選 C 之後**不需要修訂任何
已核可產出**（三層階層、`AC9.1.1` 的「三層」、線框 §3、`mockups.md` M4 全部仍成立）。

**2. OpenRouter 那條路是技術上不存在，不是不夠好。** 查了它的 API reference 與 FAQ
兩處：只有 `chat/completions` 與 `generation`，對 embedding 零提及。所以 `:free`
模型是對話模型，產不出向量。

**3. `OQ-1` 被指派給本站但我沒定案。** 它是「切回共享時獨立那段的處置」，屬對話
歷程的保留語意而非元件邊界；`[DD:E6]`=A 已決定外框（兩段都在同一 key 下、一起到期），
剩下的保留／捨棄／可回溯需與歷程 schema 一併決定，轉移至 `units-generation`（ALWAYS）。
**這是本站未完成的指派，我如實記為未解決而不是已處理。**

**另外兩件如實記載**：Ollama 的 2GB RAM 與 bge-m3 的 1.2GB 取自一般認知、
**未在 staging 主機實測**，而 `DEPLOY.md`／`LOCAL-DEV.md` **完全沒有記載該主機的
RAM／CPU**——本 intent 要往那台機器加第 5（Redis）與第 6（Ollama）個服務，
而沒有任何文件能回答「加得下嗎」。七項交接事項 H-1…H-7 皆已查 `stage-graph.json`
確認 slug 與 `execution`；落在 CONDITIONAL 者全部附轉移目標。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- 作答時間 2026-09-25T11:38:56Z（以 `date -u` 取值，非估計）。確認範圍：E1–E9 九題定案、
     三份產出、六項送審前自檢的逐項結果（3 處契約缺口 DG-1／DG-2／DG-3 已指派
     functional-design）、三件特別揭露事項（E8 反轉範圍比表面小、OpenRouter 無
     embeddings 端點、OQ-1 本站未定案並轉移 units-generation）、以及 Ollama 主機
     資源未實測且文件無記載一事、七項交接事項 H-1…H-7。 -->

