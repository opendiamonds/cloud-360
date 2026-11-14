# CI／CD 管線 — `U22` `progress-channel`

> 單元：`U22` `progress-channel`（`library`，M）　Stage：`infrastructure-design`（3.4）　Depth：`Minimal`
> 本站產出 2 項（`cicd-pipeline.md`、`traceability.json`）。`produces_kinds` 把
> `infrastructure-specification` 與 `monitoring-design` 過濾掉——它們的 kind 清單為
> `[service, ui, packaging]`，本單元是 `library`；而 `cicd-pipeline` 與 `traceability`
> 的清單含 `library`，`cicd-pipeline` 更是本 stage 的 `review_artifact`。

---

## §〇 CONDITIONAL 適用性判定（執行，不 skip）

condition 逐字：「Infrastructure services need mapping, deployment architecture
required, or cloud resources needed. **Skip if no infrastructure changes and
infrastructure already defined.**」

| 條款 | 判定 | 依據 |
|---|---|---|
| Infrastructure services need mapping | **不成立** | `library`，無進程、無 socket、無 port、無容器 |
| Deployment architecture required | **不成立** | 零新環境變數；compose 維持 **6** 個服務 |
| Cloud resources needed | **不成立** | 無任何雲端資源 |
| CI pipeline 的內容 | **成立** | 本單元引入三道目前**不存在**的閘門 |

**執行的理由不是前三款成立**（它們都不成立），而是 **kind 過濾本身界定了工作範圍**：
infra 兩份被濾掉、CI 一份留下。引擎回的 `produces` 實測為 2 項，與此一致。

> **更正一個已凍結的假宣告**：`nfr-design` 的三處產出逐字寫本 stage 對 `library`
> 「kind-vacuous」。那是把一個四條的 map 只讀了前兩條（該輪審查 `R-01`，Critical）。
> **本站的存在即為該更正的證據**，連同 `S-9` 具名帶進閘門。

---

## §一 本單元對 CI 的實際改動：**零設定變更**

| 面向 | 改動 |
|---|---|
| `ci.yml` | **不動**（`[Q1]`=A 的全部價值） |
| 新 job | 無 |
| 新步驟 | 無 |
| 新 CI 依賴 | 無（`U22-D3`：`collections.deque` ＋ `dict` 皆標準庫，`requirements.txt` 不變） |
| Docker image | 不變（`docker-build` job 不受影響——本單元不改 `Dockerfile`、不加依賴） |
| `deploy.yml` | **不動**（零環境變數、零服務、`render-env.sh` 與三個 `.env.example` 皆不變） |
| compose | 維持 6 個服務 |

**三道閘門全部寄生在既有的步 7 上。** `ci.yml` 的 `backend` job 第 7 步逐字為
`python -m unittest discover -s tests -v`，它會自動撿到 `backend/tests/` 下的任何
新檔——所以把閘門寫成測試即等於進了 CI，不需要任何設定變更。

**先例已查證**：`backend/tests/test_hierarchy_migration.py:454` 的
`test_schema_rbac_sql_matches_migration_ddl` 正是「用測試解析另一個檔的原始文字」
這個形狀，由 `U4` 交付、現在就在跑。

### 為什麼不走 `scripts/*.py --check` 那條（`[Q1]` 選項 B 被否決的理由）

步 5／6（`dump_openapi.py --check`、`dump_ws_contract.py --check`）是很自然的樣板，
但選它需要先裁決一條規則：`project.md` 的 `## Forbidden` 逐字禁止「以 repo 內新增的
實作程式承載**無人值守的**流程自動化」，而判準是觸發來源——由 `on: push`／
`pull_request` 觸發、無人在迴圈內者**落在禁止範圍內**。該條的既有例外是 `tcms`
plugin 的兩支腳本，它們只被 stage 檔呼叫、`.github/` 下無 workflow 呼叫它們。
`[Q1]`=A 繞開了這個裁決，而且附帶拿到兩個好處：**失敗訊息是標準 unittest 輸出**
（會說明哪一個條件不成立，而非只有 `grep` 的 exit code），且**本機與 CI 行為一致**
（開發者自己跑 `python -m unittest` 就看得到）。

---

## §二 三道閘門

全部放在一支新檔 `backend/tests/test_progress_channel_contract.py`。

### 閘門 1 — `U22-V3`：退場符號與三個呼叫點

| 檢查 | 條件 |
|---|---|
| 1a | `design_agent.py` 內 `_progress_queue` 零命中 |
| 1b | `design_agent.py` 內 `_last_xml` 零命中 |
| 1c | `design_agent.py` 內無「把全域設為 `None`」那一行 |
| 1d | `_drain_progress` 已改寫為呼叫 `ProgressChannel.drain` |
| **1e** | **`run_design_agent` 的三個呼叫點全部傳入新鍵**：`agent_router.py:125`、`wa_collab_orchestrator.py:79`、`backend/test_agent.py:41` |

**1e 是這道閘門的實質內容，也是最容易寫成恆真的一條。** 寫法必須是
「**先數出呼叫點總數，再斷言每一個都帶新參數**」，不是「grep 新參數有沒有出現」
——後者在只改一處時也會過。承接 `functional-design` 審查 `R-01`（Critical）與
`nfr-requirements` 的 `S-2`。

### 閘門 2 — `U22-V5`：本模組不含鍵鑄造函式

`progress_channel.py` 內無 `uuid`／`secrets`／`random` 的 import，且無任何回傳新鍵
的函式。承接 `SEC-1` 在本單元側唯一可驗的部分。

> **本閘門有一個已知的射程限制**（承 `nfr-design` 的 `S-5`，狀態 `GAP`）：它只能
> 證明「本模組不鑄造」，**證不了「入口端鑄造得正確」**。`nfr-design §五` 已寫明
> `code-generation` 實作本閘門時應一併斷言 `agent_router.py` 與
> `wa_collab_orchestrator.py` 以 `uuid4`／`secrets` 鑄造——那是把 `S-5` 的缺口收起來
> 的最便宜路徑（與閘門 1 的 1e 讀同樣兩支檔，可併在同一支測試檔內）。
> **本站把它寫成 `U22-V7` 使它有 id**，見 §四。

### 閘門 3 — `S-7`：形狀級的例外原文檢查

`design_agent.py` 內對 `{e}`／`{exc}`／`str(e)`／`repr(e)` 的命中為零。

**這是形狀級而非字面級的檢查**，取代 `SEC-2` 原本只 grep
`f"發生未預期錯誤：{e}"` 一個句型的寫法——那個 grep 抓不到 `:103`，於是漏掉的
那一半會在閘門上長得像已經修好（`nfr-requirements` 審查 `R-01`，Critical）。

> **如實記載射程限制**（`nfr-design` 審查 `R-04`）：這組 pattern 對**未來**的覆蓋
> 宣稱不成立——`"...".format(e)`、`% e`、`{e.args}`、或把變數改名為 `exc` 以外的
> 名字都會逃掉。本站實測現狀：全檔恰兩個 `except ... as e`、兩者都命名為 `e`，
> `.format(`／`% e`／`e.args`／`traceback` 全部零命中，**所以這組 pattern 對當下
> 是完整的**；它不保證的是日後新增的第三個 `except`。要真正完整需要 AST 層檢查，
> 成本遠高於本單元的規模，故不在本站做，但這個限制必須被寫下來而不是被宣稱為完整。

---

## §三 突變驗證（`[Q2]`=A，本站的交付條件）

三道閘門檢查的都是「某個字串**不存在**」，而這類檢查最容易寫成恆真——pattern 寫錯
就永遠找不到，於是永遠綠。`[Q2]`=A 把突變驗證列為本站的交付條件並指定內容，使
「這道閘門不是恆真」成為一個**做過就有紀錄**的動作。

| # | 突變 | 必須的結果 | 對應閘門 |
|---|---|---|---|
| 1 | 把 `_progress_queue: asyncio.Queue[...] \| None = None` 一行加回 `design_agent.py` | 閘門 1 **紅** | `U22-V3` |
| 2 | 在 `progress_channel.py` 加一行 `import uuid` | 閘門 2 **紅** | `U22-V5` |
| 3 | 把 `:216` 的固定字串改回 `f"發生未預期錯誤：{e}"` | 閘門 3 **紅** | `S-7` |
| 4 | **只**把 `wa_collab_orchestrator.py:79` 改回不傳新鍵（另兩處保持正確） | 閘門 1 的 **1e 紅** | `U22-V3`／`S-2` |

**突變 4 是四個裡最重要的一個**，因為它驗的正是 1e 那條「最容易寫成恆真」的斷言：
若 1e 被寫成「grep 新參數有沒有出現」，突變 4 **會過**（另兩處仍有該參數），而那正是
`functional-design` 的 `BR5.1` 只列一個呼叫點所造成的缺口。驗不出突變 4 的 1e 等於
沒有 1e。

每一次突變都須：改回錯的行為 → 跑 `python -m unittest discover -s tests` → 確認紅燈
→ 還原 → 複驗綠燈。結果（含突變內容與紅燈訊息）寫進 `code-generation` 的產出。

> 本站**不**把突變驗證推給 `tcms-test-cases`（`[Q2]` 選項 B）：那一站的
> `execution: ALWAYS` 且有 `/tcms-verify` 關卡，職責上接得住，但本站已經知道突變該
> 是什麼（上表四項），交出去等於讓下一站重新推導同一件事。`tcms-test-cases` 仍會
> 依其規則做它自己的覆蓋盤點，兩者不衝突。

---

## §四 交接與開放項

| id | 項目 | 落點 | `execution`（已查 `stage-graph.json`） | 風險 |
|---|---|---|---|---|
| `U22-V7` | **新增**：閘門 2 的擴充——一併斷言 `agent_router.py` 與 `wa_collab_orchestrator.py` 以 `uuid4`／`secrets` 鑄造新鍵。這是把 `nfr-design` 的 `S-5`（狀態 `GAP`）收起來的最便宜路徑，且與閘門 1 的 1e 讀同樣兩支檔，可併在同一支測試檔。 | `code-generation`（3.5） | **ALWAYS** | **中→低**。`S-5` 原本沒有有保證的落點（`U13`／`U12` 的 `nfr-requirements` 皆 `CONDITIONAL`，而 `code-generation` 是 per-unit 所以到不了它們）；本項把它收進**本單元自己的**閘門，因此不再依賴那兩個單元是否被 skip。 |
| `S-9` | **更正**：`nfr-design` 三處產出宣告本 stage 對 `library` kind-vacuous，實為非 vacuous（`produces_kinds` 四條中後兩條含 `library`）。本站的存在即為證據，但凍結的產出仍帶著假宣告。 | 閘門上揭露 | — | **低**（方向是「多了一站」而非少了一站），但若有人只讀 `nfr-design` 會以為本站不存在。 |
| `S-10` | **閘門 3 的射程限制**：形狀級 pattern 對當下完整、對未來不完整（`.format(e)`、`% e`、`{e.args}`、改名變數皆可逃掉）。要完整需 AST 層檢查，成本遠高於本單元規模。 | `code-generation` 的程式註解 ＋ 閘門上揭露 | **ALWAYS** | **中**。這是一個**已知會隨時間腐化**的閘門，而腐化是安靜的。 |
| `S-1`（承上游） | buffer 上界數值 ＋ 定值前須先量 | `code-generation` | **ALWAYS** | 低 |
| `S-2`（承上游） | 三個呼叫點 → 已成為閘門 1 的 1e ＋ 突變 4 | `code-generation` | **ALWAYS** | **由高降為中**：本站把它變成一條有突變驗證的機械閘門 |
| `S-7`（承上游） | `SEC-2` 的範圍更正（兩處而非一處）→ 已成為閘門 3 | `code-generation` | **ALWAYS** | 由中降為低 |
| `S-4`（承上游，**本站不另設閘門**） | `U22-V4` 的 `await` 禁令。`nfr-design` 的 `[Q1]`=A 已把它變成語法層保證，本站**刻意不加閘門**——`await` 在 `def` 內是 `SyntaxError`，連 import 都會失敗，而 `ci.yml` 的 `backend` job 步 4（Import FastAPI app）會先撞到它。再加 grep 是為一個已由語言排除的問題加機制。 | 已由 `nfr-design` 的設計承擔 | — | **低** |
| `R-02`（承 `nfr-design` 審查，Critical，**本站無法收**） | `DuplicateChannelKey` 在哪裡被接住從未被設計。`agent_router.py:124-128` 的 `event_generator()` 無 `try/except` 且包在 `StreamingResponse` 內，故該例外**不經** `design_agent.py:214`——使用者得到無聲中止的 SSE 串流。 | **閘門裁決**，之後落 `code-generation` | **ALWAYS** | **高**。本站是 CI 閘門的站，**擋不住一個沒有設計的出口**——沒有任何 grep 能斷言「這個例外有被接住且轉成 `error` 事件」。它需要一個設計決定（誰接、轉成什麼），而本單元的三個設計站都已凍結。 |

### 本階段新增、已核可 scope 尚未涵蓋

**`U22-V7` 是本站新增的驗證項**（上表第一列），但它不是新能力——它是把 `S-5` 這個
已存在的缺口收進一個**有保證落點**的閘門。`scope` 仍為 12 項能力。

其餘皆為承接或更正，無範圍擴充。
