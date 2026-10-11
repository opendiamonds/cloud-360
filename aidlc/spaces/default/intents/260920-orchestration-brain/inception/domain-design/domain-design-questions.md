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
| `[E<n>]`（**無** `DD:` 前綴） | **修訂輪**的 domain-design 作答，與上一列是**兩套不同的編號空間**：原輪用到 `E9` 為止，修訂 1 自 **`E11`** 起（`E10` 保留不用，避免與原輪最後一號相鄰造成誤讀）。**下一次修訂請從 `E16` 起**——本表是唯一要查的地方，不必回去數標題 |
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

---

> **編號空間的更正（2026-10-02T23:26:55Z，`review-02` 的 `R-04`）**：修訂 1 原本把五個新問題編為
> `E6`–`E10`，而 `E6`–`E9` 在原輪**已被用於完全不同的問題**（原 `E6`＝Redis session
> 存活期、`E7`＝語意記憶檢索、`E8`＝「需求」實體承載、`E9`＝本機 embedding 切換），
> 當時只靠「有無 `DD:` 前綴」區分——而那個區分**未寫進慣例表**，一旦有人誤加或誤刪
> 前綴，追溯就會指向錯誤的問題。已改為 **`E11`–`E15`**（原輪用到 `E9` 為止，故
> `E11` 起無碰撞），`components.md`／`decisions.md` 的裸 `[E#]` 引用同步更新。

# 修訂 1（2026-10-02T22:47:42Z）— 能力 11／12／13 的元件邊界

## 為什麼有修訂 1

本站三份產出於 2026-09-25 完成並通過審查，但那一輪早於 `scope-document.md` 修訂
3／4（能力 11／12）與 user-stories 修訂 1（US11／US12／US13）。機械實測：
`能力 11`／`能力 12`／`project_members`／`成員`／`需求欄位`／`MCP`／`自動改選`／
`併發`／`FR11`–`FR13`／`US11`–`US13`／`_progress_queue`／`邀請` **16 個關鍵詞在三份
產出合計 0 命中**；追溯表只有 **20 筆**上游 id，而 `requirements.md` 現有 **76 個**
FR／NFR 識別字。既有六個元件與九則 ADR **全部有效、不回改**。

## 上游的狀態標記（本站消費的兩份都不乾淨，如實記載）

| 上游 | 狀態 | 具體影響 |
|---|---|---|
| `requirements.md` | **`directly stale`** | 本 session 把 `FR12.4c` 的橫幅落點由「入口頁」就地更正為「使用者的落地頁」（審查 `R-04` 要求），該更正**尚未經 requirements-analysis 的關卡重新核可**。本站的設計以更正後的版本為準，並在此標明 |
| `stories.md` | **`Revalidate`** | 因上述 `requirements.md` 的更正而被標記；內容本身已於 2026-10-02 核可（31 則／106 條 AC） |

**不假裝上游是乾淨的**：若 requirements-analysis 之後重跑並改變 `FR12.4c` 的落點，
本站與 `ReselectionEvent` 相關的設計須一併重審。

## 本站查出的一個直接衝突（**必須先解，否則下游拿到兩個互斥的模型**）

**`ADR-009` 與能力 11 直接牴觸。** `ADR-009` 的 Decision 逐字為「**不建
`Requirement` 實體**、不建需求↔系統的多對多關聯表」，改以 `DiagramChangeRecord`
的 `requirementSummary`（**自由文字摘要**）與 `requirementLabel`（**輕量標籤**）承載。

而能力 11 要求的是**結構化的固定欄位**：`[R12]`＝D 逐字否決了自由鍵值對
（理由是「自由欄位會讓同一個概念出現多個名字，而畫面無從分辨」），`FR11.2` 要求
按 agent 分組的固定欄位、`FR11.3` 要求未填計數、線框 §17 畫出 SLA／尖峰 TPS／
使用客群／月預算上限／計費區域五個具名欄位。

**兩者對「需求」這個詞指的不是同一件事**：`ADR-009` 的「需求」是**溯源概念**
（哪個需求驅動了這次架構圖變更），能力 11 的「需求欄位」是**agent 需要的架構假設**
（SLA、TPS、預算）。這是 `ddd-patterns.md` 點名的同名不同義（bounded context 的
命名碰撞），也正是 `project.md` 記著的「會議結論點名的識別字先查證是否已被佔用」。
**怎麼收是 E12 的問題。**

## 已由上游定案、本站不重問

| 已定案項 | 定案內容 | 來源 |
|---|---|---|
| 三層階層 | 專案 → 系統 → 架構圖 | `[RA:FR9.1]`、`AC9.1.1`、`ADR-002`／`ADR-003` |
| 需求欄位的形狀 | **按 agent 分組的固定欄位**，非自由鍵值對 | `[R12]`＝D、`FR11.2`、線框 §17 |
| MCP 的進程形狀 | **獨立進程**，對外帶使用者 token 呼叫既有 API | `[F16]`＝B（取代 `[S13]`＝A） |
| MCP 的暴露範圍 | **不得對外暴露**，僅供同主機的大腦進程連接 | `requirements.md:614` |
| token 不得當工具引數 | 工具 schema 的 properties 不含憑證名稱 | `FR11.5`、`C-T11` |
| 兩層授權串聯 | 全域功能權限 ＋ 專案成員資格，任一層不過即拒 | `FR12.6` |
| 自動改選的挑選規則 | **最早加入的成員**，且挑選結果須排列不變 | `[RA-1]`＝A、`FR12.4`／`FR12.4a` |
| 併發修復的鍵 | **per-request**，不得用 `thread_id`（per-user）或不存在的「session」 | `[V-01]`、US13 的 DoD |
| 成員頁的可見性 | 一般成員看得到、清單唯讀；控件**不在 DOM 內** | `[DM:D9]`＝A、不變量 I-5 |

## E11. 專案成員管理要新建元件，還是擴充既有的 `ProjectHierarchy`？

`ProjectHierarchy` 已擁有 `Project`／`System`／`DiagramChangeRecord` 三個實體，
而能力 12 新增的是成員關係與角色。

- **A. 新建 `ProjectMembership` 元件**，擁有 `ProjectMember` 實體，`depends_on`
  `ProjectHierarchy`（讀專案是否存在）。理由：成員關係的**變更率與生命週期**與
  階層不同（階層是建立後少動，成員是持續進出），且它承載**授權判定**這個與
  階層無關的職責。`architecture-guide.md` 的邊界判準：單一可命名的職責、擁有自己
  的資料、可獨立測試。代價：多一個元件邊界、多一條 `depends_on` 邊。
- **B. 擴充 `ProjectHierarchy`**，把 `ProjectMember` 加為它的第四個實體。理由：
  成員**附屬於**專案，沒有專案就沒有成員；併在一起可避免一個「只有一張表」的元件。
  代價：`ddd-patterns.md` 逐字「若兩個概念因**不同理由**而改變，它們屬於不同的
  bounded context」——成員變更的理由（人員進出、授權調整）與階層變更的理由
  （新系統、新架構圖）無關；且 `ProjectHierarchy.behaviour` 已在上一輪因「不得有
  任何繞過 `require_story_action` 的路徑」與它自己的 `sync` 入邊自相矛盾而被審查打回
  （見 `project.md` 的該條教訓），再加一個職責會讓那段 behaviour 更難寫對。
- **C. 新建 `ProjectMembership` 且**不**依賴 `ProjectHierarchy`**（只持有
  `projectId` 而不驗證它存在）。代價：孤兒成員列無人擋，而 `AC12.1.3`（非成員看不到
  專案）需要兩者一起判——把關聯完整性推給資料庫外鍵等於讓它在應用層不可測。

`[Answer]`: A — 新建 ProjectMembership 元件，depends_on ProjectHierarchy
<!-- 作答時間 2026-10-02T23:06:33Z（以 `date -u` 取值）。選項本文已於提問前寫入本檔，選單內容與本檔逐字一致。 -->

## E12. `ADR-009` 與能力 11 的「需求」衝突怎麼收？

見上方「本站查出的一個直接衝突」。三個選項的**可逆性差異很大**。

- **A. 兩者並存且改名**：能力 11 的東西叫 **`SystemRequirementField`**（掛在系統之下、
  按 agent 分組的固定欄位），`ADR-009` 的 `requirementSummary`／`requirementLabel`
  **原樣保留**於 `DiagramChangeRecord`。新增一則 ADR 明寫兩者是不同概念、各自的
  讀寫端，並在兩處都標註「**不要把這兩個『需求』當成同一件事**」。代價：產品裡有
  兩個都叫「需求」的東西，使用者介面上必須用不同措辭（線框 §17 用「需求籤」，
  `DiagramChangeRecord` 用「最近變更」——實際上**線框已經這樣區分了**）。
- **B. 取代 `ADR-009`**：把 `DiagramChangeRecord` 的自由文字摘要改為指向
  `SystemRequirementField`。代價：`ADR-009` 是**使用者自己在 `[DD:E2]` 重新框定後
  定案的**（逐字「需求不用被完整紀錄，只要讓架構圖在被異動時被紀錄……紀錄內容只要
  是摘要即可」），取代它等於推翻使用者的定案，依 `project.md` 的規則必須先界定
  反轉範圍並由使用者裁決——而本題就是那個裁決點。且兩者的**基數不同**：一次架構圖
  變更可能由多個需求驅動，而需求欄位是每個系統一組固定欄位，硬接會製造一個
  多對多關聯表，正是 `ADR-009` 明文拒絕的東西。
- **C. 把需求欄位掛在 `System` 實體上**（`ProjectHierarchy` 擁有，不新建實體）。
  代價：`FR11.3` 的未填計數、`FR11.4`–`FR11.6` 的 MCP 讀寫、`FR12.4b` 式的「誰寫」
  稽核都要掛在 `ProjectHierarchy` 上，使它同時擁有階層、變更紀錄與 agent 契約三種
  職責；且欄位集合會隨新 agent 上線而變（線框 §17 明寫「新 agent 上線要同步加一組
  定義」），那個變更率與 `System` 完全不同。

`[Answer]`: A — 兩者並存且改名：能力 11 的叫 SystemRequirementField，ADR-009 的 requirementSummary／requirementLabel 原樣保留
<!-- 作答時間 2026-10-02T23:06:33Z（以 `date -u` 取值）。選項本文已於提問前寫入本檔，選單內容與本檔逐字一致。 -->

## E13. per-project 授權判定（`H-12`）要落在哪一層？

`[DM:D9]`＝A 要求畫面依「我在這個專案的角色」決定控件可見性，而既有的
`CapabilityRoute` 管的是**能力層**（story id）。不變量 `I-5` 另要求一般成員視角的
變更控件**不在 DOM 內**，所以前端必須收到一個明確的結論而不是自己推導。

- **A. `ProjectMembership` 提供判定方法**，每個需要它的元件 `depends_on` 它。
  理由：授權判定與成員資料同屬一個 bounded context，資料與規則不分離；
  `architecture-guide.md` 的「擁有自己的資料」判準成立。代價：每個消費端都多一條
  `depends_on` 邊，且**必須**在設計上禁止繞過（上一輪 `ProjectHierarchy` 正是在這裡
  自相矛盾——behaviour 寫「不得同進程直呼」而機讀目錄自己宣告了 `sync` 入邊）。
- **B. 新建獨立的 `ProjectAuthorization` 元件**，只做判定、不擁有資料（讀
  `ProjectMembership`）。理由：判定邏輯有自己的變更率（將來可能加入繼承、群組）。
  代價：一個不擁有資料的元件正是 `architecture-guide.md` 列為**紅旗**的
  「pass-through proxy」；且它與 `ProjectMembership` 會永遠一起改。
- **C. 每個元件自己判**（各自讀成員資料並比對角色）。代價：授權規則出現 N 份副本，
  而 `team.md` 的「單一真實來源」逐字要求「同一份事實已存在於程式中時，新增第二份
  物化前必須先確認是否有既有常數或 API 可直接使用」；更實際的問題是 `FR12.6` 的
  兩層串聯會在每個元件裡被重寫一次，而其中任一處寫錯就是一個授權繞過。

`[Answer]`: A — ProjectMembership 提供 per-project 授權判定方法
<!-- 作答時間 2026-10-02T23:06:33Z（以 `date -u` 取值）。選項本文已於提問前寫入本檔，選單內容與本檔逐字一致。 -->

## E14. MCP 橋接是獨立元件，還是 `BrainGateway` 的一部分？

`[F16]`＝B 已定案它跑**獨立進程**，對外帶使用者 token 呼叫既有 API；
`requirements.md:614` 已定案它**不得對外暴露、僅供同主機**。本題只問**元件身分**
（domain-design 的元件是「你寫的程式」，不是部署拓樸——拓樸屬 units-generation）。

- **A. 新建 `McpBridge` 元件**：擁有工具 schema 的宣告與 token 轉遞路徑，
  `depends_on` 既有 API（以 `external_dependencies` 記 HTTP 呼叫）。理由：它的
  **消費者不是人而是 agent**，介面形狀（MCP 工具宣告）與 `BrainGateway` 的
  WebSocket 完全不同；且 `C-T11` 的「token 不得當工具引數」是**它專屬**的硬約束，
  掛在獨立元件上才有明確的斷言落點（`AC11.4.2` 的白名單斷言）。
- **B. 併入 `BrainGateway`**：兩者都是「對外的入口」。代價：`BrainGateway` 的
  behaviour 會同時描述 WebSocket 的使用者連線與 MCP 的 agent 連線，而兩者的認證
  主體（使用者 JWT vs 代使用者的 token）、暴露範圍（對外 vs 僅同主機）與失敗模式
  都不同——`architecture-guide.md` 的紅旗之一正是「兩個元件總是一起部署」的反面：
  **一個元件承擔兩種不該一起變的理由**。
- **C. 不建元件，記為 `external_dependencies`**。代價：MCP server 是**我們要寫的
  程式**，不是我們使用的第三方服務；stage 檔逐字「Infrastructure, databases, caches,
  queues, and third-party services are `external_dependencies` — never components」，
  反過來說**我們寫的程式必須是元件**。

`[Answer]`: A — 新建 McpBridge 元件
<!-- 作答時間 2026-10-02T23:06:33Z（以 `date -u` 取值）。選項本文已於提問前寫入本檔，選單內容與本檔逐字一致。 -->

## E15. `FR13` 的 per-request 進度通道要不要成為元件？

`FR13.1` 要求把 `design_agent.py` 的模組層全域 `_progress_queue` 改為 per-key
（鍵為 per-request），`FR13.2`／`FR13.3` 是它的可觀察面，US13 的 DoD 另要求一併
清理該檔的三個模組層可變狀態、以及 `wa_collab_orchestrator.py:79` 補傳鍵。
`H-13` 層級的提醒：既有 agent 模組（`design_agent`／`wa_collab_orchestrator`）在
本站的機讀目錄裡是「既有」而**不是元件**。

- **A. 新建 `ProgressChannel` 元件**：擁有 per-request 的進度佇列與其清除端，
  既有 agent 模組與 `BrainGateway` 都 `depends_on` 它。理由：它是**本 intent 要寫的
  新程式**，且「誰清」這一腿目前無人負責（US13 的 DoD 只要求鍵是 per-request、
  **沒有要求清除**，而只寫不刪會把跨使用者錯送換成無上界記憶體成長——這是我在
  refined-mockups 自檢 2 查出的）。獨立元件讓清除端有明確的擁有者。
- **B. 修在既有 agent 模組內，不成為元件**：它是一個 bug fix，不是新建構塊。
  代價：「誰清」仍然無人負責，且 `BrainGateway` 要消費這些事件卻沒有任何契約——
  `FR13.2` 的「A 的事件集合與 B 的事件集合互斥」會變成一條沒有元件可掛的斷言。
- **C. 併入 `WorkOrchestrator`**（它已負責交辦與狀態事件轉譯）。理由：進度事件
  本就是它轉譯的那些事件的來源。代價：`WorkOrchestrator` 的 `behaviour` 會同時
  描述「交辦給哪個 agent」與「agent 的進度怎麼隔離」，而後者是**既有 agent 的
  內部狀態**；更實際的問題是 `FR13` 的修復範圍橫跨兩支既有檔案
  （`design_agent.py`、`wa_collab_orchestrator.py`），把它併進一個新元件的
  responsibilities 會讓「這個元件完成了嗎」同時指涉新程式與既有程式的改動。

`[Answer]`: A — 新建 ProgressChannel 元件，擁有 per-request 進度佇列與其清除端
<!-- 作答時間 2026-10-02T23:06:33Z（以 `date -u` 取值）。選項本文已於提問前寫入本檔，選單內容與本檔逐字一致。 -->
