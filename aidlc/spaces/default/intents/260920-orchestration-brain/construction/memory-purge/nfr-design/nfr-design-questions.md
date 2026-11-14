# NFR Design 問題檔 — `U9 memory-purge`

> Depth 為 `Minimal`；kind 為 `packaging`，故 `produces_kinds` 只給兩份產出
> （`security-design`／`traceability`）——performance／scalability／reliability／
> observability／logical-components 五份對本 kind 不適用。
>
> **本站的兩題都來自上一站的審查發現**，不是新造的題目。兩者都是上一站寫錯或漏寫
> 的東西，而兩者的修法都有安全後果且不能由本站自行決定。

## 〇、不重問的事（上游已定案）

| 事項 | 定案處 |
|---|---|
| 連線路徑：自架 runner ＋ `docker compose exec -T db psql` | `[N1]`=A；`NFR7.12` |
| 清除涵蓋兩個目標（逾期記憶 ＋ 逾期稽核） | `NFR7.10` |
| 清除稽核本身不留稽核（無終止遞迴） | `NFR7.15`，承 `U5` 的衍生決定 |
| 決定性邏輯放純 Actions 步驟，不走 LLM 路徑 | `NFR7.14`；`FR4.5a` 附註 |
| 零新部署設定 | `NFR8.10` |
| `NFR7.13` 的**偵測機制**（runner 離線） | **刻意不在本站**——屬 `infrastructure-design`（`OPEN-N9-1`）。本站只設計它的 security 面（若有） |
| `DG-1` | 已由 `U5` 在 DDL 層定案，上一站已關閉 |

---

## 一、`[ND1]` `purged_by_retention` 的 `actor_user_id` 要填什麼？（審查 `R-02`，Major）

### 這是一個會讓 SQL 直接失敗的缺口，不是文件瑕疵

`NFR7.11` 要求每筆清除稽核的 actor 為「保留的系統 actor」，而本站複驗了審查的發現：

| 查證 | 結果 |
|---|---|
| `memory_audit_events.actor_user_id` 的 DDL | `schema_rbac.sql:484` 逐字 `actor_user_id INTEGER NOT NULL REFERENCES public.users (id)` |
| 是否有任何地方 seed 這個系統 actor | **沒有**。`schema_rbac.sql` 全檔**無任何 `INSERT INTO users`**；`:15` 逐字「不建立固定密碼管理員；bootstrap admin 由後端依環境變數建立」 |
| `U5` 有沒有定過它的具體值 | **沒有**。`U5` 的 COMMENT（`:509`）只在概念層寫「a reserved system actor is used」，並說明為何不能填記憶擁有者（「would make the audit LIE about who deleted it」）與為何不能留 NULL（「would weaken 'who did this'」） |

**後果**：清除 workflow 的 `INSERT INTO memory.memory_audit_events (...)` **在語法層就會失敗**
（違反 NOT NULL 外鍵）。故 `NFR7.11` 目前不是「未強制」，是**沒有任何 SQL 能滿足它**。
**這個缺口同樣適用於 `U5` 自己**——它定義了概念但沒有提供值。

### `users` 表的既有約束（決定了可行的形狀）

```
id SERIAL PRIMARY KEY, username VARCHAR NOT NULL（UNIQUE index）,
password_hash VARCHAR NOT NULL, role VARCHAR NOT NULL,
is_active BOOLEAN DEFAULT TRUE, ...
```

故任何「系統 actor 列」都必須有 username、`password_hash`、`role` 三個非空值。

### 選項

| 選項 | 做法 | 後果與代價 |
|---|---|---|
| **A（建議）** | **在 `schema_rbac.sql` seed 一列不可登入的系統 actor**：固定 `username`（如 `system.retention-purge`）、`password_hash` 設為**結構上不可能比對成功**的哨符值、`role` 設為**非** canonical role、`is_active = FALSE`。清除 SQL 以 `SELECT id FROM users WHERE username = '<哨符>'` 取 id，**不寫死整數** | 給了 `NFR7.11` 一個真實的 FK 目標，且三道鎖使它不可被用來登入：① `is_active = FALSE` 會被 `auth.py` 的既有檢查拒絕；② `password_hash` 為哨符值，無任何密碼可比對成功；③ `role` 非 canonical 使 `rbac.py` 的 `is_canonical_role` 回 False、全部權限判定為拒。以 username 查 id 而非寫死整數，使它在 `SERIAL` 值不同的環境間仍正確。**代價**：`users` 表多一列不是人的列（Admin 使用者清單會看到它——須確認是否要排除）；且這是對 `U5`／baseline 表的 seed 變更，觸發 `schema_rbac.sql` ＋ `DEPLOY.md` 的 blocking 同步 |
| **B** | **把 `actor_user_id` 改為可為 NULL**，系統動作留 NULL | 不需要假使用者。**但 `U5` 的 COMMENT 逐字反對**：「leaving it NULL would weaken 'who did this' on every event」——它是為**每一筆**事件而非只為清除事件設的 NOT NULL。且這是對 `U5` 已交付表的 DDL 變更，等於推翻一條已核可的決定 |
| **C** | **用被停用的記憶擁有者的 id** | 零 schema 變更。**但 `U5` 的 COMMENT 逐字反對**：「Filling in the memory owner would make the audit LIE about who deleted it」——稽核會說是使用者自己刪的，而 `action` 欄的 `deleted_by_user` 與 `purged_by_retention` 刻意分開正是為了區分這兩者 |
| **D** | **本站不決定，推給 `code-generation`** | 零現在的成本。**但 `code-generation` 會撞上一個硬失敗且沒有決定可依**——而本站是 `packaging` 單元鏈上最後一個有 security 設計職責的站（`infrastructure-design` 管的是落點與排程）。推下去等於讓實作者自己發明一個身分語意 |

[Answer]: A seed 一列不可登入的系統 actor
<!-- 作答時間 2026-10-07T23:55:51Z，以 `date -u` 取值 -->

**後果（本站據此設計）**：三道鎖的承載位置已逐一開檔核對，不是推測：

| 鎖 | 承載 | 實測 |
|---|---|---|
| `is_active = FALSE` 使登入被拒 | 既有 `auth.py` 的檢查 | `backend/services/auth.py:75` 逐字 `if not user.is_active:` |
| 非 canonical role 使全部權限判為拒 | 既有 `rbac.py` 的 `is_canonical_role` | `backend/services/rbac.py:54-55`：`return normalize_role(role) in CANONICAL_ROLES` |
| 哨符 `password_hash` 使無密碼可比對成功 | `bcrypt` 無法對非 bcrypt 格式字串回 True | 設計要求（見 `security-design.md §二`） |

**以 username 查 id、不寫死整數**：`users.id` 是 `SERIAL`，值因環境而異。

---

## 二、`[ND2]` 要不要為清除建立一個真正受限的資料庫角色？（審查 `R-01`，Major）

### 上一站的 `NFR6.10` 目前是恆真的，而我寫成了「未驗證」

`NFR6.10` 要求「以 `POSTGRES_USER` 連線，不得以 superuser 繞過 grant 邊界」，
並把缺口記為「無機械強制」。本站複驗審查的發現，**那個敘述比實情樂觀**：

| 查證 | 結果 |
|---|---|
| 部署的 `db` 服務設了哪些環境變數 | `deploy/docker-compose.deploy.yml:43-45` 只有 `POSTGRES_USER`／`POSTGRES_PASSWORD`／`POSTGRES_DB` 三個 |
| 官方 `postgres`／`pgvector` image 對 `POSTGRES_USER` 的行為 | 由它建立的角色**本身即 superuser** |
| grant 授予誰 | `schema_rbac.sql:524` 逐字 `GRANT USAGE ON SCHEMA memory TO %I', current_user`——授予**執行初始化腳本的那個身分**，也就是那個已是 superuser 的 `POSTGRES_USER` 自己 |

**所以本系統目前不存在任何非 superuser 的資料庫連線身分。**
「以 `POSTGRES_USER` 而非 superuser」不是兩個可區分的連線——它們是同一個。
`NFR6.10` 因此**恆真（永遠通過）**，而不是「未驗證但可能失敗」。
這比「缺 CI 驗證」嚴重：它看起來在守護一道 IAM 邊界，實際上沒有。

### 選項

| 選項 | 做法 | 後果與代價 |
|---|---|---|
| **A（建議）** | **接受現況並把 `NFR6.10` 的敘述改寫成誠實的版本**：明寫「本系統現狀是 `POSTGRES_USER` 即 superuser，`NFR6.10` 無法區分兩者，故它目前不構成 IAM 邊界」，並把「是否要為清除新增受限角色」列為**具名的開放項**交給 `infrastructure-design`／後續 intent | 零成本、零新憑證、不破壞 `[N1]`=A 換來的「零新部署設定」（`NFR8.10`）。**它修的是誠實度而非邊界**——一條恆真的需求被誤讀成已有防護，比明寫「目前沒有防護」危險得多。代價：IAM 邊界確實仍不存在，只是不再假裝存在 |
| **B** | **在 `schema_rbac.sql` 新增一個受限角色**（只有 `memory` schema 的 DELETE／INSERT／SELECT），清除以該角色連線 | 真正建立 IAM 邊界，且**順便讓 `U5` 的 `OPEN-CG5-1` 變得可驗證**（有了第二個角色才能測越界）。代價明確且不小：① 新角色需要密碼 → **新憑證** → `render-env.sh` ＋ `deploy/.env.example` ＋ compose 三處同步（`project.md` 的 blocking 規則），**直接打破 `NFR8.10` 的「零新部署設定」**；② `docker compose exec -T db psql` 的預設身分是 `POSTGRES_USER`，改用新角色需顯式 `-U` 並提供密碼，而密碼不能出現在 Actions log（本 repo 為 public）；③ 既有環境需要一次 role 建立的遷移步驟 |
| **C** | **B 的縮小版**：建立受限角色但**不**給清除用，只用來讓 `OPEN-CG5-1` 的越界測試可執行 | 補上驗證能力而不改清除路徑，`NFR8.10` 不破（測試用角色只在 CI service container 內建立，不進部署設定）。代價：清除本身仍以 superuser 連線，`NFR6.10` 仍恆真——它修的是**驗證**，不是邊界 |

[Answer]: A 接受現況，改寫成誠實的敘述
<!-- 作答時間 2026-10-07T23:55:51Z，以 `date -u` 取值 -->

**後果（本站據此設計）**：

1. **`NFR6.10` 的敘述在本站被改寫**（不是回改上一站的凍結檔，而是在
   `security-design.md` 以「上游敘述的更正」形式記載）：本系統現狀下
   `POSTGRES_USER` 即 superuser，該需求**無法區分**「以 `POSTGRES_USER`」與
   「以 superuser」，故它**目前不構成 IAM 邊界**。
2. **仍保留的實質要求**：清除**不得顯式以其他身分覆寫**（例如不得在 workflow 內
   硬塞一組更高權限的連線字串）。這一條仍是可審查的，只是它守的是
   「不要變得更糟」，不是「已經有邊界」。
3. **「是否新增受限角色」列為具名開放項**（`OPEN-ND9-2`），指派
   `infrastructure-design` 或後續 intent。附上它的真實代價：新憑證會打破
   `[N1]`=A 換來的 `NFR8.10`。
4. **`NFR8.10` 因此維持成立**——這是選 A 的附帶好處，寫明以免被讀成巧合。
