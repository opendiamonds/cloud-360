# NFR Requirements 問題檔 — `U9 memory-purge`

> Depth 為 `Minimal`；本單元是 `packaging`、size `S`，故 `produces_kinds` 只給三份
> 產出（`security-requirements`／`tech-stack-decisions`／`traceability`），
> performance／scalability／reliability／observability 四份**對本 kind 不適用**。
>
> 本站只問**一題**：它是 `OQ-13` 裡唯一有安全後果、且不能由本站自行決定的那一半。

## 〇、不重問的事（上游已定案，可引用原文）

| 事項 | 定案處 |
|---|---|
| 保存 90 天、逾期自動刪除 | `FR4.5`（`[RA:R2]`） |
| **承載形式必須是 gh-aw 或 GitHub Actions workflow**，不得以 `backend/` 內的排程程式承載 | `FR4.5a` ＋ `project.md ## Forbidden`（觸發判準逐字為「由事件或排程觸發、無人在迴圈內」） |
| 決定性的映射邏輯放**純 Actions 步驟**，不交給 gh-aw 的 LLM 路徑 | `FR4.5a` 附註（本 repo 三塊結構性盲區之一是「所有 LLM 路徑」） |
| 清除動作本身須留稽核 | `FR4.7` ＋ `NFR7` |
| 稽核保存期亦為 90 天，以**自身** `occurred_at` 為鍵（不是 join 記憶的時間） | `NFR7.2`；`schema_rbac.sql` 的 `ix_memory_audit_events_occurred_at` 即為此查詢而建 |
| **`DG-1` 已由 `U5` 解決** | 見 §一之二 |
| 資料庫層邊界為「grant 只開放記憶 schema」 | `FR4.4`／`NFR6`；`schema_rbac.sql` 的 `BR1.2` 區塊 |

### 〇之一、`unit-of-work.md` 對本單元的一項記載已過期（本站查證）

`unit-of-work.md:221` 逐字寫「`U9`：**`DG-1` 尚未解決**……稽核事件一併刪除則
『刪除留稽核』失去意義，保留則成為懸空參照」，並把落點指向
`functional-design`（**CONDITIONAL**，而本單元因 kind 為 `packaging` 確實**未執行**該站）。

**本站開檔核對 `schema_rbac.sql`，`DG-1` 已由 `U5 memory-data` 在 DDL 層定案**：

| 事實 | 依據（逐字） |
|---|---|
| `memory_audit_events` **刻意不對 `memory_records` 設外鍵** | 表 COMMENT：「Deliberately holds NO foreign key to memory_records so the trail OUTLIVES the memory it describes. With an FK both options break an approved requirement: CASCADE makes FR4.7 vacuous after 90 days, RESTRICT makes FR4.5 impossible」 |
| 代價已明寫 | 同上：「Cost, stated plainly: memory_id has NO referential integrity」 |
| 清除動作有**專屬的** action 值 | `ck_memory_audit_events_action` 的 `purged_by_retention`，且 COMMENT 逐字說明它與 `deleted_by_user` **刻意分開**（前者是 `FR4.5`、後者是 `FR4.6`，合併會讓兩者在稽核上無法區分） |
| 清除的 actor 問題已定案 | `actor_user_id` 的 COMMENT：`purged_by_retention` 沒有自然使用者，故用**保留的系統 actor**；填記憶擁有者會讓稽核「對誰刪的」說謊 |
| 稽核表不含記憶內容 | `BR2.2` 註解：若含內容，「保留稽核」等於「保留被刪除的使用者資料」，`FR4.5` 形同虛設 |

**故本站不重開 `DG-1`**，只如實記載該筆上游記載已過期，並把它寫進
`security-requirements.md`。這是「指派落在已被 skip 的 CONDITIONAL 站」那個
失敗模式的一次**良性**結果：被指派的站沒跑，但問題已在更上游被解決。

### 〇之二、本單元的清除動作有**兩個**目標，不是一個

| # | 目標 | 條件 | 索引支援 |
|---|---|---|---|
| 1 | `memory.memory_records` | `expires_at < now()`（`expires_at` 在 `kind = episodic` 時必填，由 `ck_memory_records_episodic_has_expiry` 強制——**NULL 的 episodic 列永遠選不到，即永久保留且無痕跡**） | `ix_memory_records_expires_at` |
| 2 | `memory.memory_audit_events` | `occurred_at < now() - 90 days`（**自身**時鐘，`NFR7.2`） | `ix_memory_audit_events_occurred_at` |

兩者都已有索引，且索引註解逐字寫明是為清除查詢而建。**只做第 1 項會讓稽核表
無上界成長**，而該表本輪沒有任何讀取端（`US4.3` 的查詢面是回補項 `N-8`，屬 `U8`）。

---

## 一、`[N1]` 清除 workflow 用哪一條路徑連到資料庫？

### 為什麼只問這一題

`OQ-13` 逐字問的是「90 天清除 workflow 的**落點與其取得資料庫連線的方式**
——它跑在 GitHub Actions 上，而資料庫在自架 staging 主機後面」，指派
`infrastructure-design`（CONDITIONAL，skip 轉 `deployment-pipeline`，**亦** CONDITIONAL，
兩者皆 skip 須重新提交使用者）。

**落點**（哪個 workflow 檔、排程時間）屬 `infrastructure-design`；
**連線方式**有直接的安全後果，且 `NFR7` 逐字要求 episodic memory 的
「靜態儲存與傳輸的加密要求須於設計階段明確」——那是本站的 security 面。
故本站只固定連線路徑這一半，不預先決定落點。

### 本站查證到的機械事實

| 查證項 | 結果 |
|---|---|
| 自架 runner 是否存在 | **是**：`[self-hosted, linux, x64, cloud360]`，`deploy.yml` 的兩個 job（`:27`、`:402`）都用它 |
| 資料庫有沒有對主機發布連接埠 | **沒有**。`deploy.yml:146-148` 逐字：「the only service with a host port is **frontend**, so the runner cannot reach ollama over HTTP」——`db` 同樣沒有 host port |
| 既有 workflow 怎麼碰容器內的服務 | `docker compose exec -T`（`-T` 為必要：「this runner has no TTY」） |
| 本 repo 是否 public | **是**，而 `project.md` 逐字記載「Actions log 公開可讀……一次意外 echo 即等同公開發布」 |
| 記憶 schema 的 grant 邊界是否已被 CI 驗證 | **否**（`OPEN-CG5-1`）：驗它需要第二個資料庫角色，而 `memory-schema` job 的 service container 只有 superuser |

### 選項

| 選項 | 做法 | 安全後果與代價 |
|---|---|---|
| **A（建議）** | **跑在既有自架 runner 上，以 `docker compose exec -T db psql` 執行刪除**。排程由 `on: schedule` 觸發，決定性的 SQL 放純 Actions 步驟 | **零憑證離開主機、零新暴露面、零新 GitHub secret**：連線完全在 compose 內部網路，`db` 維持沒有 host port。直接沿用 `deploy.yml` 已驗證過的存取形狀。代價：清除依賴自架 runner 在線（runner 離線時排程靜默不執行——**這是本選項唯一的真實風險**，須有對應的 NFR 與可觀測性要求） |
| **B** | **GitHub 託管 runner ＋ 把資料庫憑證放 GitHub secret ＋ 對外發布資料庫連接埠**（或另開一條 tunnel） | 不依賴自架 runner 在線。代價極高：① 必須把 PostgreSQL 暴露到主機或網際網路，**那是一個全新的對外暴露面**，而本單元原本零暴露增量；② 資料庫憑證跨越信任邊界進入 GitHub；③ 本 repo 為 public，`project.md` 已記載「憑證誤存為 variable 僅搬移到 secret 不足以結案，必須重新產生金鑰」的實例。**本站認為此選項與 ADR-0006 的 network exposure 面直接衝突** |
| **C** | **後端新增一個帶認證的清除端點**，workflow 以 token 透過既有 Cloudflare Tunnel 呼叫它 | 不暴露資料庫、不需 DB 憑證。代價：① 新增一個**能刪除資料**的 HTTP 端點，是新的攻擊面，且它必須能被無人值守的呼叫者使用（故不能只靠互動式登入）；② 決定性的映射邏輯會落在 `backend/` 而非純 Actions 步驟，與 `FR4.5a` 附註的意圖相左；③ 又一個需要輪替的 token |
| **D** | **只做 `workflow_dispatch` 手動觸發**，不設排程 | 零自動化風險。代價：`FR4.5` 逐字要求「逾期**自動**刪除」，手動觸發不滿足它；且 90 天保存期的合規意義建立在「它真的會到期」之上 |

[Answer]: A 自架 runner ＋ docker compose exec -T psql
<!-- 作答時間 2026-10-07T23:19:40Z，以 `date -u` 取值 -->

**後果（本站據此寫成 NFR）**：

1. **連線路徑**：清除 workflow 跑在既有自架 runner（`[self-hosted, linux, x64, cloud360]`）
   上，以 `docker compose exec -T db psql` 執行刪除。**`-T` 是必要的**——該 runner 無 TTY
   （`deploy.yml:148` 逐字記載）。
2. **零暴露增量**：`db` 維持**沒有 host port**；不新增 tunnel、不新增對外監聽埠。
   ADR-0006 的 network exposure 面因此為「本單元零增量」，而非「有落點」。
3. **零新憑證**：資料庫憑證不離開主機、不進入 GitHub secret，故
   `project.md` 的「新增憑證型 secret 後須查證它落在 secrets 而非 variables」
   **不觸發**。
4. **本選項唯一的真實風險必須寫成 NFR**：自架 runner 離線時 `on: schedule`
   **靜默不執行**——沒有錯誤、沒有紅燈，而 90 天保存期的合規意義建立在
   「它真的會到期」之上。這是本單元的核心靜默失敗面，須有可觀測的對策
   （見 `security-requirements.md` 的 **`NFR7.13`**）。
   <!-- 初稿此處寫 `NFR7.6`。送審前自檢發現 `NFR7.1`／`NFR7.2`／`NFR7.3`／`NFR7.4`
        已分別被 U5／embedding-port／brain-infra／hierarchy-data 等單元使用，
        其中 U5 的 `NFR7.2` 更已被 `schema_rbac.sql` 的註解逐字引用。
        本單元的編號因此改由 `NFR7.10` 起算，理由見 security-requirements.md §一。 -->
5. **決定性的 SQL 放純 Actions 步驟**，不交給 gh-aw 的 LLM 路徑（`FR4.5a` 附註）。
