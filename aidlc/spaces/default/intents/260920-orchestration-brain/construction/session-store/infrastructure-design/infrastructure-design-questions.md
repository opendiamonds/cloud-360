# Infrastructure Design 問題檔 — `U10 session-store`

> depth 為 **Minimal**。本站只問一題——其餘的基礎設施決定要嘛已由 `U1 brain-infra`
> 完成、要嘛已在本單元的 `nfr-design` 定案、要嘛可由實讀檔案直接確認。
> 下方逐項列出「已確認、不出成題目」的內容與其證據。

## 一、實讀確認的四件事（原本可能要問，查了就不用問）

| 問題 | 實讀結果 | 結論 |
|---|---|---|
| `[N3]`=A 的 `noeviction` 要不要同步到 CI 測試 stack？（`nfr-requirements` 審查 `R-04` 指派本站確認） | `deploy/docker-compose.test.yml:120-121` 逐字「**NO `--appendonly`, NO `--maxmemory`**: this stack has no persistence by design」 | **不需要**。`maxmemory-policy` 只在觸及 `maxmemory` 時生效，而該 stack 根本沒設 `maxmemory`。**這是確認，不是假設**——`R-04` 的指派就此關閉 |
| CI 測試 stack 的 ACL 允不允許 `EVAL`（`[D1]`=A 的 Lua 需要它）？ | `docker-compose.test.yml:146-150` 的 app 使用者為 `+@all -@admin -@dangerous`，**與 deploy stack 逐字相同** | **允許**。且 `nfr-design` 的審查已實地裝 Redis 8.8.0 跑過這條規則，`EVAL`／`EVALSHA`／`SCRIPT LOAD` 三者皆通過 |
| `NFR8.40` 的新環境變數會不會與「無預設值」牴觸？（測試 stack 的慣例是 `${VAR:-default}`） | `project.md ## Mandated` 的三環境契約逐字把 CI 測試列為「值**全內嵌且有預設**」 | **不牴觸**。`BR3.5` 要求的是**應用程式**不得有預設值；CI 由環境供值正是該契約要的形狀。兩者是不同層的「預設」 |
| Redis 服務本身要不要本單元做什麼？ | `codekb/chiton/technology-stack.md:206` 逐字「**服務已佈建**（`redis:8-alpine`、AOF volume、ACL、healthcheck）…**env contract 的 blocking 工作已完成**」 | **不需要**。本單元的基礎設施增量只有三項：`noeviction`、新環境變數、新 Python 依賴 |

## 二、本站可自行決定、不出成題目的兩項（附依據）

1. **`NFR4.60` 的 `MEMORY STATS` 採集點放在 backend 行程內的低頻取樣。**
   不放 Actions workflow 的理由是它要的是**連續**訊號而非單次快照；而
   `project.md` 禁止以 repo 內程式承載「**無人值守的**流程自動化與外部系統同步」，
   該條的判準逐字是「由事件或排程觸發、無人在迴圈內」且標的是**外部系統同步**——
   行程內的自身記憶體取樣不是外部同步，不落在該禁令內。此判定寫進產出，不憑直覺。
2. **本單元不新增任何 CI job。** `[I1]` 的選項 A 若被選中會推翻這一點，故它在該選項的
   代價裡逐字列出。

---

## [I1] `NFR4.64` 的重啟還原驗證要跑在哪裡——在 CI 的測試 stack 跑它是**沒有意義的**

**`NFR4.64` 逐字**要求重啟還原（`NFR4.53`–`NFR4.57` 五項）有「**可重複執行**的驗證
程序」，而 `observability-design.md` §六 已定**重啟的對象是 Redis 而不是 backend**
（backend 無狀態，重啟它什麼都不會掉）。

**但 CI 的測試 stack 跑這個驗證會是空的**，三項實讀證據：

| 證據 | 內容 |
|---|---|
| `deploy/docker-compose.test.yml:120-121` | 逐字「**NO `--appendonly`**, NO `--maxmemory`: this stack has no persistence by design」 |
| 同檔全文 | **沒有任何 top-level `volumes:` 區段**（實測 `grep -c "^volumes:"` 回 `0`）——redis 沒有 named volume |
| `deploy/docker-compose.deploy.yml:250-253` | deploy stack **有** `redis_aof:/data` |

無 AOF ＋ 無 volume ⇒ 在 CI 重啟 redis 會**全失**。於是那個測試要嘛必然紅燈、
要嘛被寫成「斷言資料消失」——兩種都不是 `NFR4` 要驗的東西。

**既有先例**：`deploy.yml:195` 已有一個 Redis 專屬的部署後檢查步驟
（`Verify the Redis ACL actually took effect`），所以「部署後對 staging 驗 Redis」
在本 repo 是既成形狀而非新發明。

### 選項

- **A — 給 CI 測試 stack 加上 AOF ＋ named volume，讓驗證在 CI 真的有意義。**
  - **好處**：`NFR4.64` 成為**每個 PR 都會跑的閘門**，`NFR4.53`–`NFR4.57` 五項在合併前就被驗。
  - **代價**：① 推翻 `docker-compose.test.yml` 檔頭逐字的「this stack has no persistence
    **by design**」與「rebuilt every run」的設計意圖；② **需要一個新的 CI job 或擴充既有的**
    ——現有 backend 測試跑 in-memory SQLite、**完全沒有 Redis**，而 `ui-regression` 是
    Playwright，在它中間重啟 redis 會讓整套 e2e 不穩（`team.md` 逐字記載它是真閘門、
    `stats.unexpected` 非 0 即紅）；③ 與本單元「不新增 CI job」的立場衝突。
- **B（建議）— 作為部署後的驗證步驟，對 staging 執行。**
  在 `deploy.yml` 既有的部署後檢查之後加一步：寫入一個涵蓋五項的 fixture session →
  重啟 redis 容器 → 逐項讀回比對（含剩餘 TTL 落在預期區間）。
  - **好處**：① 驗的是**真的那一套設定**（AOF ＋ named volume ＋ `noeviction`），
    而 CI 無論怎麼配都只是近似；② 零新 CI job、不碰 `ui-regression`；
    ③ `deploy.yml:195` 已有同類步驟，形狀是現成的。
  - **代價**：① **不是 PR 閘門**——壞掉要等合併後才知道。但本專案是 deploy-on-merge，
    延遲是分鐘級，且 `deploy.yml` 已有 rollback job（還原 last-good、開 revert PR）；
    ② 重啟 redis 會讓當下在用 staging 的人掉 session——**這一點必須寫進產出**，
    不能當作沒有。
- **C — 在 CI 內以「不重啟」的替代驗證**：`BGREWRITEAOF` 之後檢查 AOF 有被寫入。
  - **代價**：**那不是還原驗證**。它驗「有寫出去」，而 `NFR4` 的不變量是「**讀得回來**」。
    兩者的差別正是 `U1` 註解裡那個「healthcheck 通過但 session 全失」的失敗模式。
- **D — 如實記為不可在 CI 驗證，列為具名缺口，不設驗證。**
  - **代價**：`NFR4.64` 逐字要求「可重複執行的驗證程序」，記為缺口等於那一條不成立；
    而 `NFR4` 是本單元最重的一條 NFR。

[Answer]: B（作為部署後的驗證步驟，對 staging 執行）
<!-- answered 2026-10-09T14:46:34Z via AskUserQuestion；選項原文已於提問前逐字寫入本檔 -->

---

## 上游已定案、不重問

| 事項 | 定案出處 |
|---|---|
| Redis 服務、ACL、AOF volume、healthcheck | `U1 brain-infra`（已完成）；`codekb/chiton/technology-stack.md:206` |
| `maxmemory 256mb` 與容器上限的關係 | `U1` 的 compose 註解逐字 `container memory limit >= maxmemory × 1.5 + 256MB` |
| 淘汰策略改 `noeviction` | `[N3]`=A；`NFR4.50`／`NFR8.42` |
| 儲存結構 Hash ＋ Lua、並發安全 | `[D1]`=A；`performance-design.md`／`reliability-design.md` |
| 逾時／重試／不加熔斷 | `[D2]`=A；`reliability-design.md` §一 |
| 不設 SLO、不做備份、單點可接受 | `reliability-requirements.md`（附理由） |
| 無 metrics／tracing／告警管道 | `observability-design.md` §五；`OPEN-N10-4` 記為無自然承接站 |
| 部署模型（deploy-on-merge 至 `192.168.10.10`） | `ADR-0007`／`ADR-0008`；`org.md ## Deployment` |
