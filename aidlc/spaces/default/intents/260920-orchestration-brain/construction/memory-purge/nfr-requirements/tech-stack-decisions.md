# 技術選擇 — `U9 memory-purge`

> 本單元**不引入任何新技術**。本檔的用途是把「為什麼不引入」寫成可查證的決定，
> 以及把 `[N1]`=A 選定的執行環境固定下來——否則下游會以為這些仍是開放選擇。

## 一、選擇表（全部沿用既有，零新依賴）

| 層 | 選擇 | 理由 | 被排除的替代方案 |
|---|---|---|---|
| **承載形式** | **GitHub Actions workflow**（純 Actions 步驟，非 gh-aw） | `FR4.5a` ＋ `project.md ## Forbidden`：排程觸發、無人在迴圈內的流程自動化**必須**以 gh-aw 或 Actions 承載，不得以 `backend/` 內新增的排程程式承載 | ① `backend/` 內的 APScheduler／cron——**被 `project.md` 明文禁止**；② gh-aw（LLM 驅動）——`FR4.5a` 附註要求決定性映射邏輯放純 Actions 步驟，而 LLM 路徑是本 repo 三塊結構性盲區之一 |
| **執行環境** | **既有自架 runner** `[self-hosted, linux, x64, cloud360]` | `[N1]`=A。`deploy.yml` 的兩個 job（`:27`／`:402`）已在用它；它與資料庫在同一主機，故連線不跨信任邊界 | GitHub 託管 runner——需要暴露資料庫或新開 tunnel ＋ 把 DB 憑證放進 secret，與 ADR-0006 的 network exposure 面衝突（詳見問題檔 `[N1]` 選項 B 的代價欄） |
| **資料庫存取** | **`docker compose exec -T db psql`** | 沿用 `deploy.yml` 已驗證的形狀。`db` **沒有 host port**（`deploy.yml:146-148` 逐字：只有 `frontend` 有），故這是 runner 唯一的到達方式。`-T` 為**必要**（該 runner 無 TTY） | ① 直連 `psql -h <host>`——需要 host port，等於新增暴露面；② 透過後端 HTTP 端點——新增一個能刪除資料的攻擊面，且會把決定性邏輯移出純 Actions 步驟 |
| **資料庫身分** | **`POSTGRES_USER`**（應用程式角色） | `NFR6.10`：grant 邊界只開放記憶 schema，而它是資料庫層的唯一防線。以 superuser 連線會讓該邊界對本單元失效 | `-U postgres` 或任何 superuser 覆寫 |
| **刪除邏輯的語言** | **SQL**（字面存在於 workflow 或版控的 `.sql` 檔） | 兩條 DELETE 都是單一 WHERE 條件且已有索引支援（`ix_memory_records_expires_at`、`ix_memory_audit_events_occurred_at`），不需要任何程序式邏輯 | Python 腳本——會把邏輯移出純 Actions 步驟，且本 repo 已有「以 repo 內實作程式承載無人值守流程自動化」的禁令 |
| **排程觸發** | **`on: schedule`** | `FR4.5` 逐字要求「逾期**自動**刪除」 | 只有 `workflow_dispatch`——不滿足「自動」（問題檔 `[N1]` 選項 D） |
| **新依賴** | **零** | `psql` 已在 `db` 容器內；`docker compose` 已在 runner 上 | — |

## 一之二、「零新技術」是對照 codekb 的既有盤點得出的，不是推測

`aidlc/spaces/default/codekb/chiton/technology-stack.md` 是 brownfield 的技術棧盤點
（`consumes` 的第三項）。本站逐項對照它，確認上表的每一個選擇都已存在於該盤點內：

| 本單元用到的東西 | `technology-stack.md` 的對應記載 |
|---|---|
| PostgreSQL（`psql` 在容器內） | `:17` `pgvector/pgvector:pg18`（deploy stack） |
| GitHub Actions | `:170` 「CI｜GitHub Actions `ci.yml`，**5 job／14 條可讓 CI 紅燈的步驟**」 |
| `psycopg`（v3）驅動 | `:47` `psycopg[binary]`——**本單元不直接用它**（走 `psql` CLI），列出是為了說明 `+psycopg` 的 URL 形式從何而來 |

而該檔 `:200` 的「本 intent 會引入的新技術面」一節**沒有**任何屬於本單元的列
——`:211` 的「獨立 PostgreSQL schema（零前例）」屬 `U5`，不是本單元。
**故「本單元零新技術」是對照既有盤點後的結論。**

> 附帶一項與 `NFR6.10` 相關的記載：該檔 `:211` 逐字寫「測試走 in-memory SQLite
> （**無 schema 概念**），跨 schema 行為在現有測試基礎設施上**不可驗證**」——
> 這與 `K-05` 的 `why_not_existing_tests` 是同一件事，也是 `NFR6.10` 無機械強制的根因。

## 二、本單元的技術增量實測為零（逐項列出，避免被讀成未評估）

| 類別 | 增量 |
|---|---|
| 新語言／執行環境 | **無** |
| 新套件（Python／npm） | **無** |
| 新容器／服務 | **無** |
| 新監聽埠 | **無** |
| 新環境變數 | **無**（`NFR8.10`） |
| 新 GitHub secret | **無**（`NFR7.12` 的判準④） |
| 新資料庫物件 | **無**（兩張表與兩個索引皆由 `U5` 交付） |
| 新 CI job | **一個 workflow**，但它不是 `ci.yml` 的 job——它是獨立的排程 workflow，不進 PR 閘門 |

## 三、一項與既有實務的落差，本站如實記載

`deploy.yml` 用自架 runner 的既有 job 都是**由事件觸發**（PR closed、
`workflow_dispatch`），而本單元是**第一個在自架 runner 上以 `on: schedule`
觸發的 workflow**。

| 差別 | 後果 |
|---|---|
| 事件觸發的 job：runner 離線時，**觸發者在等結果**（PR 合併了但沒部署，有人會發現） | 失敗是**有人在看**的 |
| 排程觸發的 job：runner 離線時，**沒有人在等** | 失敗是**沒有人在看**的——Actions 清單上只是少一列 |

這正是 `NFR7.13` 存在的理由，而它在本 repo**沒有先例可照抄**。
**本站以兩條指令雙向查證，不是憑印象**：

| 查證 | 指令 | 結果 |
|---|---|---|
| 哪些 workflow 有 `schedule:`，各自跑在哪種 runner | 對 `.github/workflows/*.yml` 逐檔 `grep -q "schedule:"` 後取其 `runs-on` | **7 個**：`agentics-maintenance`、`aidlc-sync-pull`、`aidlc-sync-reconcile`、`aidlc-sync-reverse`、`aidlc-sync-selftest`、`daily-digest.lock`、`release-watch.lock`——`runs-on` 全部是 `ubuntu-slim` 或 `ubuntu-latest`，即 **GitHub 託管** |
| 反向：哪些 workflow 用自架 runner，它們有沒有排程 | `grep -rln "self-hosted" .github/workflows/*.yml` 後逐檔 `grep -c 'schedule:'` | **只有兩個**（`ci.yml`、`deploy.yml`），且**兩者的 `schedule:` 命中數皆為 0** |

兩個方向都成立，故「本 repo 沒有任何在自架 runner 上排程觸發的 workflow」
是實測結論而非推測。**反向查證是必要的**：只做第一條會漏掉「某個用自架 runner
的檔案其實也有排程」這種可能。

**故 `NFR7.13` 的偵測機制是本單元唯一需要新設計的東西**，而本站刻意不預選它
（屬 `infrastructure-design`），只固定它的判準：**必須不依賴該 runner**。
記為 `OPEN-N9-1`。
