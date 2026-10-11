# 安全需求 — `U9 memory-purge`

> 本單元是 `packaging`、size `S`：交付「90 天逾期清除」的 GitHub Actions workflow。
> `produces_kinds` 使 performance／scalability／reliability／observability 四份產出
> **對本 kind 不適用**，故本檔是本站唯一的需求文件，可觀測性的要求一併寫在這裡
> （`NFR7.13`）——不另立一份不在 `produces` 內的檔案。
>
> **本單元零端點、零進程、零監聽埠、零前端面。** 它的全部安全面是
> 「一個排程觸發的刪除動作如何取得資料庫連線、刪對了什麼、以及漏跑時看不看得出來」。

## 〇、上游依據（逐一指名檔案，便於複驗）

| 上游 | 本站用到它的什麼 |
|---|---|
| `inception/requirements-analysis/requirements.md` | `FR4.5`（保存 90 天、逾期自動刪除）、`FR4.5a`（承載形式必須是 gh-aw 或 Actions，決定性邏輯放純 Actions 步驟）、`FR4.7`（刪除動作留稽核）、`NFR6`（schema 隔離與其 CI 驗證）、`NFR7`（保存與刪除稽核；逐字要求加密要求「須於設計階段明確」）、`NFR8`（新元件的部署設定完整性）、`NFR9`（成本原則）、以及 `OQ-13`（本站 `[N1]` 的來源） |
| `inception/contract-design/contract-summary.md` | `K-05`（本單元消費的 schema 契約）＋ 本單元為無消費端的葉節點這一事實。詳見 §一之二 |
| `codekb/chiton/technology-stack.md` | brownfield 技術棧盤點，用於佐證「本單元零新技術」。詳見 `tech-stack-decisions.md §一之二` |
| `schema_rbac.sql`（版控，非 record） | 兩張表與兩個索引的實際 DDL 與 COMMENT——`DG-1` 於 §三 關閉的依據 |
| `.github/workflows/deploy.yml`（版控） | 自架 runner 與 `docker compose exec -T` 的既有存取形狀（`:27`／`:402`／`:146-148`） |

## 一、編號從 `NFR7.10` 起算的理由（先說，以免被讀成跳號錯誤）

`NFRx.y` 的命名空間在本框架是**per-unit** 的（stage 檔逐字：「Every detailed
requirement inherits its inception NFR ID and appends a sub-number」），
但本站實查發現**低位號已被佔用且其中一個已外溢到版控的 SQL 裡**：

| id | 佔用者 | 本站為何不重用 |
|---|---|---|
| `NFR6.1`／`NFR6.2` | `U5 memory-data`（靜態加密→主機層；傳輸→compose 內部） | 本單元與 `U5` 共用同一組表與同一個 inception 父項，重用會讓兩份文件的同一個 id 指不同需求 |
| `NFR7.2` | `U5 memory-data`（稽核保存 90 天，以自身 `occurredAt` 為鍵） | **它已被 `schema_rbac.sql` 的索引註解逐字引用**，是本 intent 中唯一外溢到版控 SQL 的 `NFRx.y`，實質已成全域識別字 |
| `NFR7.1`／`NFR7.3`／`NFR7.4` | `embedding-port`／`brain-infra`／`hierarchy-data`／`hierarchy-service` 各自的衍生需求 | 同一父項下已有多個不同語意的佔用 |

故本單元的衍生需求自 `NFR7.10` 起算，`NFR6` 與 `NFR8` 的衍生項亦分別自
`NFR6.10`／`NFR8.10` 起算。**這不是跳號，是為了讓 id 在本 intent 內可唯一定位。**

> **本檔的 id 排版約定**（讓「哪一行宣告它」可機械判定）：**只有 §二 的宣告列
> 使用 `**`+backtick 的粗體形式**，其餘位置一律用單純 backtick 引用。
> 送審前自檢 6 以 `grep -coE '\*\*`NFR[0-9]+\.[0-9]+`\*\*'` 實算得 10 個粗體命中、
> 9 個不同 id，逐行檢視後發現 `NFR7.10` 在本節與 §二 各粗體一次——
> 那不是重複宣告，但它讓「宣告站」在機械計數下不唯一，故本節改為非粗體。
> 現在粗體命中數應**恰等於 8**（本單元宣告的八條）。

## 一之二、本單元的契約位置：只消費 `K-05`，不擁有任何契約

`contract-summary.md:27` 逐字把 `U9 memory-purge` 列為**三個沒有消費端的葉節點**之一
（另兩個是 `U16 object-picker-ui`、`U17 a11y-gate`），而它**消費** `K-05`
（`contract-summary.md:389`，`U5 memory-data` → `U8`、`U9`，形式 `schema`）。

本站用到 `K-05` 的四件事：

| `K-05` 的宣告（逐字或摘） | 本站據此定下的需求 |
|---|---|
| `schema_isolation.boundary`：「grant 只開放記憶 schema」 | `NFR6.10`（清除須以 `POSTGRES_USER` 連線，不得以 superuser 繞過該邊界） |
| `tables`：`memory_records` 含 `expiresAt`、`memory_audit_events` 含 `occurredAt` | `NFR7.10` 的兩條 DELETE 各自以這兩欄為 WHERE 條件 |
| `known_gap.id: DG-1`，`landing: functional-design（CONDITIONAL；skip 轉 code-generation）` | 本站查證該 gap 已由 `U5` 的 DDL 定案並於 §三 關閉 |
| `verification.why_not_existing_tests`：既有測試走 in-memory SQLite，而「**SQLite 沒有 schema 概念**」 | `NFR6.10` 無機械強制的根因——驗 grant 邊界需要真實 PostgreSQL ＋ 第二個資料庫角色 |

**本單元不新增、不修改任何契約**：它沒有消費端，故沒有對外的契約面。

## 二、本站定案的需求（八條，全部二元可判）

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR7.10`** | 清除動作必須涵蓋**兩個**目標：逾期的 episodic 記憶列，**以及**逾期的稽核事件列 | workflow 內存在兩條 DELETE：`memory.memory_records WHERE expires_at < now()` 與 `memory.memory_audit_events WHERE occurred_at < now() - interval '90 days'` | `FR4.5` ＋ `NFR7.2`；`U5` 的 `OPEN-N5-2` 逐字指出「上游只寫了前者」 |
| **`NFR7.11`** | 每一列被清除的記憶都必須產生一筆 `purged_by_retention` 稽核事件，actor 為**保留的系統 actor** | 清除 N 列記憶後，`action = 'purged_by_retention'` 的新列數為 N；且其 `actor_user_id` 不是記憶擁有者 | `FR4.7`；`schema_rbac.sql` 的 `ck_memory_audit_events_action` 與 `actor_user_id` COMMENT（逐字：填記憶擁有者會讓稽核「對誰刪的」說謊） |
| **`NFR7.12`** | 連線路徑為**自架 runner ＋ `docker compose exec -T db psql`**；`db` **不得**取得 host port；**不得**新增任何 GitHub secret 或對外 tunnel | ① workflow 的 `runs-on` 為 `[self-hosted, linux, x64, cloud360]`；② 刪除步驟以 `docker compose exec -T` 執行；③ 本單元 diff 不含對 `db` 服務新增 `ports:`；④ `gh api repos/<owner>/<repo>/actions/secrets` 的名稱集合不變 | 使用者裁決 `[N1]`=A（2026-10-07） |
| **`NFR7.13`** | 自架 runner 離線導致排程**未執行**必須是**可偵測的**，不得靜默 | 存在一個不依賴該 runner 的檢查，能回答「最近一次成功清除距今多久」；逾一定天數即可見地失敗或告警 | `[N1]`=A 的後果 4（本選項唯一的真實風險） |
| **`NFR7.14`** | 決定性的映射與刪除邏輯必須在**純 Actions 步驟**內，不得交給 gh-aw 的 LLM 路徑 | 清除步驟所在的 job 不含 `engine: copilot` 或任何 gh-aw agent 呼叫；SQL 以字面形式存在於 workflow 或版控的 `.sql` 檔 | `FR4.5a` 附註；`project.md` 的「本 repo 三塊結構性盲區之一是所有 LLM 路徑」 |
| **`NFR7.15`** | 「清除稽核事件」這個動作本身**不留**稽核紀錄 | 稽核清除步驟執行後，`memory_audit_events` 的列數**只減不增** | 承 `U5` 的衍生決定 1（理由是無終止遞迴；`FR4.7` 約束的對象是**記憶**的刪除，不是稽核本身） |
| **`NFR6.10`** | 清除必須以**應用程式角色**（`POSTGRES_USER`）連線，不得以 superuser 繞過 grant 邊界 | 連線不帶 `-U postgres` 之類的 superuser 覆寫；`docker compose exec -T db psql` 的預設身分即 `POSTGRES_USER` | `FR4.4`／`NFR6`；`schema_rbac.sql` 的 `BR1.2` grant 區塊 |
| **`NFR8.10`** | 本單元**零新部署設定** | ① `python3 scripts/validate_env_contract.py` 綠燈；② 本單元 diff 不含 `deploy/`、`deploy/render-env.sh`、任一 `.env.example`、`deploy/docker-compose.*.yml` | `NFR8`；`[N1]`=A 使此條**自然成立**（而非需要額外努力） |

### 2.1 `NFR7.13` 是本單元唯一需要新機制的一條

其餘七條在 `[N1]`=A 之下**全部是「維持現況」或「照既有形狀做」**：連線形狀沿用
`deploy.yml` 已驗證的 `docker compose exec -T`，身分沿用 `POSTGRES_USER`，
零新設定、零新 secret、零新暴露面。

`NFR7.13` 不同：**它要防的是「什麼都沒發生」**。

| 情境 | 現況會發生什麼 |
|---|---|
| runner 在線、排程正常 | 清除執行，Actions 有一筆綠色 run |
| **runner 離線** | **`on: schedule` 不會排入、不會失敗、不會有任何 run**——Actions 的清單上就是少一列，而少一列沒有顏色 |

後果不是「晚一天清」，是**保存期的合規意義失效**：`FR4.5` 的 90 天建立在
「它真的會到期」之上，而逾期未刪的 episodic memory 是使用者以為已消失的個人對話歷程。

**本站不預選偵測機制**（候選包含：以 GitHub 託管 runner 跑一個只讀的新鮮度檢查、
把「最後一次成功清除時間」寫進資料庫並由既有的 daily-digest 讀、或在
`deploy.yml` 的部署後探測中附帶檢查）——機制選擇屬
`infrastructure-design`（3.4）。**但本站固定它的判準**：必須有一個
**不依賴該 runner** 的檢查。依賴它的檢查在 runner 離線時與被偵測的失敗同時消失。

記為 `OPEN-N9-1`（`blocking-downstream`）。

## 三、`unit-of-work.md` 對本單元的一項記載已過期（本站查證並關閉）

`unit-of-work.md:221` 逐字寫「`U9`：**`DG-1` 尚未解決**……兩條已核可需求在此交會
且互相拉扯：稽核事件一併刪除則『刪除留稽核』失去意義，保留則成為懸空參照」，
落點指向 `functional-design`（**CONDITIONAL**，而本單元因 kind 為 `packaging`
確實**未執行**該站）。

**`DG-1` 已由 `U5 memory-data` 在 DDL 層定案**，本站開檔核對 `schema_rbac.sql`：

| 事實 | 逐字依據 |
|---|---|
| `memory_audit_events` **刻意不對 `memory_records` 設外鍵** | 表 COMMENT：「Deliberately holds NO foreign key to memory_records so the trail OUTLIVES the memory it describes. With an FK both options break an approved requirement: CASCADE makes FR4.7 vacuous after 90 days, RESTRICT makes FR4.5 impossible」 |
| 代價已明寫、未被美化 | 同上：「Cost, stated plainly: memory_id has NO referential integrity」 |
| 清除有專屬的 action 值，且**刻意**與使用者刪除分開 | `purged_by_retention` vs `deleted_by_user`；COMMENT 逐字：合併會讓 `FR4.5` 與 `FR4.6` 在稽核上無法區分，「their compliance meaning differs」 |
| 清除的 actor 問題已定案 | `actor_user_id` COMMENT：清除無自然使用者（排程觸發、無人在迴圈內），故用保留的系統 actor |
| 稽核表不含記憶內容 | `BR2.2` 註解：若含內容，「保留稽核」等於「保留被刪除的使用者資料」 |

**`FR4.7` 的實際滿足窗口因此是明確的**（承 `U5` 的推論）：記憶在建立後 90 天被清除，
該清除事件再活 90 天。即「刪除留稽核」在刪除後**有 90 天**成立，而非零秒。

**本站的處置**：`DG-1` 於本檔**關閉**，並如實記載該筆上游記載已過期。
這是「指派落在已被 skip 的 CONDITIONAL 站」那個失敗模式的一次**良性**結果
——被指派的站沒跑，但問題已在更上游被解決。記為 `OPEN-N9-2`（`process`，
建議下一輪 practices-discovery 或 units-generation 修訂時更新那一行）。

## 四、ADR-0006 四面向：本站的增量

逐格對照 `U5` 的同名表（`memory-data/nfr-requirements/security-requirements.md §五`），
**不與它矛盾**；本單元是它的清除端。

| 面向 | 判定 | 本站的增量 |
|---|---|---|
| **IAM** | **適用** | `NFR6.10`：清除必須以 `POSTGRES_USER` 連線，**不得以 superuser 繞過** grant 邊界。這是本單元唯一的 IAM 面——它是一個有刪除權的身分，而 `U5` 的 grant 邊界是資料庫層的唯一防線。**殘留缺口**：該 grant 邊界**本輪未被 CI 驗證**（`U5` 的 `OPEN-CG5-1`，逐字理由是「驗它需要第二個資料庫角色，而 service container 只有 superuser」），故 `NFR6.10` 目前**無機械強制**，只能以 workflow 的連線寫法審查 |
| **Encryption** | **本單元無增量**（承 `U5` 的 `NFR6.1`／`NFR6.2`） | **不寫「不適用」**——那會讀成該面向對本修訂不成立。靜態由主機層（LUKS）承載、傳輸為 compose 內部流量；而 `[N1]`=A 使清除流量**同樣留在 compose 內部**，故 `NFR6.2` 的前提在本單元**繼續成立**（選 B 會打破它：資料庫憑證與查詢會跨越主機邊界） |
| **Network exposure** | **本單元零增量** | `[N1]`=A 的直接後果：`db` 維持沒有 host port、不新增 tunnel、不新增對外監聽埠（`NFR7.12`）。**這一格原本可能是「有落點」**——選項 B 會把 PostgreSQL 暴露出來，而那是本單元原本不存在的對外暴露面 |
| **Audit logging** | **適用（本單元的核心之一）** | `NFR7.11`（清除須留 `purged_by_retention` 稽核、actor 為系統 actor）＋ `NFR7.15`（清除稽核本身不留稽核，承 `U5` 的衍生決定）。兩者合起來使 `FR4.7` 在本單元可被二元判定 |

### PBT 判定：**N/A（非豁免）**

本單元交付的是一個 workflow 與其中的 SQL，**沒有任何本單元擁有的純函式**。
ADR-0006 的 property-based hard constraint 點名的三個落點（IaC generator、
cost calculator、agent routing）皆不在本單元。

**這與 `U19` 的「適用且 blocking」形成對照**，寫下來以免被讀成漏判：
`U19` 有 `select_successor` 這個被上游點名的純函式，本單元沒有對應物。

## 五、殘餘風險（三項，逐項附承接）

1. **`NFR7.13` 的偵測機制未定**（`OPEN-N9-1`，`blocking-downstream`）。
   承接 `infrastructure-design`（3.4，**CONDITIONAL**）→ 轉移目標
   `deployment-pipeline`（4.1，**亦 CONDITIONAL**）。**兩者皆 skip 時須重新提交使用者**
   ——這與 `OQ-13` 共用同一條轉移鏈，而該鏈的風險已由上游逐字揭露。
2. **`NFR6.10` 無機械強制**（承 `U5` 的 `OPEN-CG5-1`）。grant 邊界是資料庫層的
   唯一防線，而它未被 CI 驗證；本單元是一個**有刪除權**的新消費者，
   故這個缺口在本單元之後比之前更值得補。
3. **`OQ-13` 的「落點」那一半仍未定**（workflow 檔名、排程時間）。本站只固定
   連線路徑（有安全後果的那一半），落點屬 `infrastructure-design`。
   記為 `OPEN-N9-3`（`carried`）。
