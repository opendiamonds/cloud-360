# 安全設計 — `U9 memory-purge`

> kind 為 `packaging`，故 `produces_kinds` 只給 `security-design` ＋ `traceability`
> 兩份產出；performance／scalability／reliability／observability／logical-components
> 五份對本 kind 不適用。
>
> **本站的實質內容是上一站兩條需求的修補**：`NFR7.11` 原本沒有任何 SQL 能滿足，
> `NFR6.10` 原本是恆真的。兩者都由審查查出，兩者的修法都由使用者裁決
> （`[ND1]`=A／`[ND2]`=A）。

## 〇、上游依據

| 上游 | 本站用到它的什麼 |
|---|---|
| `nfr-requirements/security-requirements.md` | 八條需求（`NFR7.10`–`NFR7.15`、`NFR6.10`、`NFR8.10`）與其二元判準；`[N1]`=A 的連線路徑 |
| `nfr-requirements/tech-stack-decisions.md` | 零新技術的選擇表；`db` 無 host port 與 `exec -T` 的既有形狀 |
| `inception/contract-design/contract-summary.md` | `K-05`（本單元消費的 schema 契約）；本單元為無消費端的葉節點 |
| `nfr-requirements/reviews/review-01.md` | `R-01`／`R-02`／`R-03` 三項發現——**本站的兩個設計決定都源自它** |
| `schema_rbac.sql`（版控） | `users` 與 `memory_audit_events` 的實際 DDL 與約束 |
| `backend/services/auth.py`、`backend/services/rbac.py` | `[ND1]`=A 的三道鎖實際由哪幾行承載 |

## 一、`NFR7.11` 的設計：系統 actor 的形狀（`[ND1]`=A）

### 1.1 它修的是一個會讓 SQL 直接失敗的缺口

`memory_audit_events.actor_user_id` 是 `NOT NULL REFERENCES public.users (id)`
（`schema_rbac.sql:484`），而全檔**沒有任何 `INSERT INTO users``（`:15` 逐字
「不建立固定密碼管理員；bootstrap admin 由後端依環境變數建立」）。
`U5` 的 COMMENT（`:509`）只在概念層寫「a reserved system actor is used」。

**故在本站之前，`NFR7.11` 不是「未強制」，是沒有任何 SQL 能滿足它。**

### 1.2 系統 actor 列的設計

| 欄位 | 值 | 為什麼是它 |
|---|---|---|
| `username` | 固定哨符，如 `system.retention-purge` | 它是**查詢鍵**（見 §1.4），且 `ix_users_username` 是 UNIQUE，故哨符天然唯一 |
| `password_hash` | **結構上不可能比對成功**的哨符字串（非 bcrypt 格式） | `NOT NULL` 使它不能留空；給一個非 bcrypt 格式的值使 `bcrypt.checkpw` 不可能回 True |
| `role` | **非** canonical role（如 `system`） | 使 `rbac.py:54-55` 的 `is_canonical_role` 回 False，全部權限判定為拒 |
| `is_active` | **`FALSE`** | 使 `auth.py:75` 的 `if not user.is_active:` 拒絕任何登入 |

### 1.3 三道鎖，而且三道都落在**既有**程式上

| # | 鎖 | 承載位置（實測） |
|---|---|---|
| 1 | 登入被拒 | `backend/services/auth.py:75` 逐字 `if not user.is_active:` |
| 2 | 全部權限判為拒 | `backend/services/rbac.py:54-55` 逐字 `return normalize_role(role) in CANONICAL_ROLES` |
| 3 | 無密碼可比對成功 | `password_hash` 為非 bcrypt 格式；本設計要求 |

**三道鎖都不是本單元新寫的程式**——這是這個設計的主要優點：它不新增任何
需要被信任的驗證路徑，只利用既有的三道。**任何一道被繞過都不是本單元的回歸**。

### 1.4 以 `username` 查 id，不寫死整數

```sql
-- 設計意圖示例（非實作）
INSERT INTO memory.memory_audit_events (memory_id, actor_user_id, action)
SELECT r.id, (SELECT id FROM users WHERE username = 'system.retention-purge'),
       'purged_by_retention'
FROM memory.memory_records r WHERE r.expires_at < now();
```

`users.id` 是 `SERIAL`，值因環境而異（本機、CI service container、staging 各不相同）。
**寫死整數會在某個環境指到另一個人**——那是一個靜默且嚴重的錯誤：稽核會說某個
真實使用者刪了記憶。以 username 查則在任何環境都正確，或者**查不到時大聲失敗**
（子查詢回 NULL → `NOT NULL` 違反 → 整個交易中止），而大聲失敗是這裡要的行為。

### 1.5 兩項衍生後果，本站寫明而非留給下游發現

1. **Admin 使用者清單會看到這一列。** `users` 多了一個不是人的列，而既有的
   `/api/auth/list` 不會知道要排除它。**本站不預選處置**（排除它需要改既有端點的
   查詢，屬 `U19`／既有端點的範圍，不是本 `packaging` 單元）；
   記為 `OPEN-ND9-1`，並指出它的可見後果是**管理者會在清單上看到一個無法登入、
   無任何權限的帳號**——不是安全問題，是可能被誤認為髒資料而被刪掉的風險。
   **若它被刪掉，清除的稽核 INSERT 會從那一刻起全部失敗**（外鍵違反）。
2. **這是對 baseline 表的 seed 變更**，故觸發 `project.md` 的 blocking 同步：
   `schema_rbac.sql` ＋ `DEPLOY.md` 必須同一個 PR 更新。
   `U5` 的 `memory_audit_events` 也依賴這一列，故**它同時補上了 `U5` 的同一個缺口**。

## 二、`NFR6.10` 的更正：它目前不構成 IAM 邊界（`[ND2]`=A）

### 2.1 上一站的敘述比實情樂觀，本站據審查 `R-01` 更正

| 查證 | 結果 |
|---|---|
| 部署 `db` 服務的環境變數 | `deploy/docker-compose.deploy.yml` 只設 `POSTGRES_USER`／`POSTGRES_PASSWORD`／`POSTGRES_DB` |
| 官方 `postgres`／`pgvector` image 的行為 | 由 `POSTGRES_USER` 建立的角色**本身即 superuser** |
| grant 授予誰 | `schema_rbac.sql:524` 逐字 `GRANT USAGE ON SCHEMA memory TO %I', current_user`——授予執行初始化腳本的那個身分，即那個已是 superuser 的 `POSTGRES_USER` 自己 |

**結論**：本系統目前**不存在任何非 superuser 的資料庫連線身分**。
「以 `POSTGRES_USER` 而非 superuser」不是兩個可區分的連線，它們是同一個。

| `NFR6.10` 的狀態 | 上一站寫的 | 實情 |
|---|---|---|
| | 「無機械強制」（聽起來像缺 CI 驗證） | **恆真**：不管清除怎麼連都是 superuser，該需求永遠通過 |

**為什麼這個差別要緊**：一條恆真的需求**看起來在守護一道 IAM 邊界而實際沒有**。
`project.md` 記過「不可達的規則是死碼，卻在文件上長得像已解決」——恆真的需求是
同一個形狀的鏡像：它不是不可達，是永遠可達，而兩者都讓讀者以為有防護。

### 2.2 本站保留的實質要求（它守的是「不要變得更糟」）

`NFR6.10` 改述後仍有一條可審查的內容：**清除不得顯式以其他身分覆寫**
——例如不得在 workflow 內硬塞一組更高權限的連線字串、不得以 `-U` 指定別的角色。

| 判準 | 二元可判 |
|---|---|
| workflow 的 `psql` 呼叫不含 `-U` 覆寫，也不含任何額外的連線字串 | 是（讀 workflow 即可判） |

**這一條不宣稱建立了邊界**，它宣稱的是「維持現況、不新增更高權限的路徑」。

### 2.3 「是否新增受限角色」列為具名開放項，附真實代價

記為 `OPEN-ND9-2`，指派 `infrastructure-design` 或後續 intent。代價必須一併帶走，
否則下游會把它當成純粹的改善：

| 代價 | 內容 |
|---|---|
| 新憑證 | 受限角色需要密碼 → `render-env.sh` ＋ `deploy/.env.example` ＋ compose 三處同步（`project.md` 的 blocking 規則），**直接打破 `[N1]`=A 換來的 `NFR8.10`（零新部署設定）** |
| 公開 log 風險 | `exec -T db psql` 的預設身分是 `POSTGRES_USER`；改用新角色需顯式 `-U` ＋ 密碼，而本 repo 為 public、Actions log 公開可讀 |
| 既有環境遷移 | 需要一次 role 建立步驟 |
| **附帶好處** | 有了第二個角色，`U5` 的 `OPEN-CG5-1`（grant 邊界未被 CI 驗證）才**變得可驗證** |

**`NFR8.10` 因此在本輪維持成立**——這是 `[ND2]`=A 的附帶好處，寫明以免被讀成巧合。

## 三、交易邊界與順序（承審查 `R-03`，Minor）

審查指出上一站對「兩次 DELETE ＋ 一次 INSERT」的交易邊界、順序與部分失敗
完全沒有涉及，**連「須交給下一站決定」都沒寫**，是無聲缺口而非已承接的缺口。
本站就地定下設計，不再往下推：

### 3.1 順序：先寫稽核，再刪記憶

| # | 動作 | 為什麼是這個順序 |
|---|---|---|
| 1 | 對所有逾期記憶寫 `purged_by_retention` 稽核列 | **稽核必須先於它描述的對象消失落地**。反過來（先刪再寫）若在中間失敗，記憶已消失而稽核不存在——`FR4.7`（刪除留稽核）在那一刻被破壞，且**無法事後補救**（已經不知道刪了什麼） |
| 2 | 刪除逾期記憶列 | — |
| 3 | 刪除逾期稽核列（`occurred_at < now() - 90 days`） | **必須在步 1 之後**：步 1 剛寫的列 `occurred_at = now()`，不可能落在逾期範圍內，故順序本身不會自我刪除。但若把步 3 放在步 1 之前，效果相同——寫下來是因為「清除會不會刪掉自己剛寫的稽核」是讀者會問的問題，答案是**不會，且與順序無關**（90 天的時間差保證它） |

### 3.2 交易邊界：步 1＋2 同一交易；步 3 獨立交易

| 設計 | 理由 |
|---|---|
| **步 1 與步 2 同一交易** | 兩者是同一個事實的兩面（「這些記憶被清除了」＋「留下紀錄」）。分開會產生「有稽核但記憶還在」或「記憶沒了但沒稽核」兩種半套狀態，後者直接違反 `FR4.7` |
| **步 3 獨立交易** | 它與步 1／2 沒有資料依賴（刪的是 90 天前的舊稽核）。綁在同一交易只會讓一個無關的失敗把整次清除回滾 |
| **部分失敗的語意** | 任一交易失敗則該交易整個回滾，workflow **以非零碼結束**（大聲失敗）。下一次排程會重新處理同一批逾期列——**因為選取條件是 `expires_at < now()`，它天然冪等**：已刪除的列不會再被選到，未刪除的仍會 |

### 3.3 為什麼這不需要重試機制

清除是**冪等且自我收斂**的：失敗後不做任何補償，下一次排程自然重試。
故本站**不設計** retry／backoff／circuit breaker——`nfr-design-guide.md` 的那些
pattern 是為「呼叫會失敗的外部依賴」而設，而本單元的唯一依賴是同一主機上的資料庫，
且失敗的正確反應是大聲結束而非重試。

**唯一真正需要被偵測的失敗是「根本沒跑」**（`NFR7.13`），而那不是重試能解的。

## 四、ADR-0006 四面向：本站的增量

逐格對照上一站的同名表（`nfr-requirements/security-requirements.md §四`）。
**本站改動其中一格的判定，並寫明理由**——`project.md` 記過「與上游相反的判定
比沒跑這道檢查更糟」，故差異在此明列而非靜默覆蓋。

| 面向 | 上一站的判定 | **本站的判定** | 增量／差異 |
|---|---|---|---|
| **IAM** | 適用（`NFR6.10` 守 grant 邊界，缺口為「無機械強制」） | **適用，但本站更正其強度**：`NFR6.10` **目前不構成 IAM 邊界**（恆真），保留的是「不得顯式以更高權限覆寫」 | §二。**這是與上游不一致的那一格**，差異來自審查 `R-01` 的實測（`POSTGRES_USER` 即 superuser），不是重新判斷 |
| **Encryption** | 本單元無增量（承 `U5` 的 `NFR6.1`／`NFR6.2`） | **一致，無增量** | `[N1]`=A 使清除流量留在 compose 內部，`NFR6.2` 的前提繼續成立。系統 actor 列的 `password_hash` 是哨符值而非真實憑證，**不構成新的機密** |
| **Network exposure** | 本單元零增量 | **一致，零增量** | `[ND2]`=A 使這一格**維持**零增量——選 B 會引入新憑證與顯式連線字串 |
| **Audit logging** | 適用（`NFR7.11` ＋ `NFR7.15`） | **一致，且本站補上它缺的那一塊** | `NFR7.11` 原本無任何 SQL 能滿足（審查 `R-02`）；§一 的系統 actor 設計是它第一次變得可實作。另 §三 定下稽核**先於**記憶消失落地的順序——那是 `FR4.7` 在部分失敗下仍成立的前提 |

### PBT：**N/A（非豁免）**，與上一站一致

本單元交付一個 workflow 與其中的 SQL，無本單元擁有的純函式。
ADR-0006 點名的三個落點（IaC generator、cost calculator、agent routing）皆不在此。

## 五、殘餘風險

| id | 內容 | 承接 |
|---|---|---|
| `OPEN-ND9-1` | **系統 actor 列會出現在 Admin 使用者清單上**，而它可能被誤認為髒資料而刪除——刪掉之後清除的稽核 INSERT 會全部失敗（外鍵違反）。是否要在 `/api/auth/list` 排除它屬既有端點的範圍 | `U19`／既有端點，或後續 intent |
| `OPEN-ND9-2` | **是否為清除新增真正受限的資料庫角色**。代價含新憑證（打破 `NFR8.10`）與公開 Actions log 的風險；附帶好處是讓 `U5` 的 `OPEN-CG5-1` 變得可驗證 | `infrastructure-design` 或後續 intent |
| `OPEN-N9-1`（承接） | `NFR7.13` 的偵測機制（runner 離線導致排程靜默不執行）。本站確認它**不是重試能解的問題**（§三之三），故 `infrastructure-design` 仍是正確落點 | `infrastructure-design` → `deployment-pipeline`（兩者皆 `CONDITIONAL`，皆 skip 須重新提交使用者） |
| `OPEN-CG5-1`（承接） | grant 邊界未被 CI 驗證。本站的 `[ND2]`=A **不改善它**，只停止假裝它已被守護 | 與 `OPEN-ND9-2` 同一個決定 |
