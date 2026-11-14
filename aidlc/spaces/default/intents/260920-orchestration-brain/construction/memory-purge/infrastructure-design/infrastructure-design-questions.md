# Infrastructure Design 問題檔 — `U9 memory-purge`

> 本單元是 `packaging`，而它的交付物**就是**基礎設施（一個 GitHub Actions
> workflow），故本站是這個單元的實質站——與 `U7`／`U19` 那種「零基礎設施變更」的
> `service` 單元相反。四份產出全部適用。
>
> 本站只問**一題**：`NFR7.13` 的偵測機制。它是上游標為
> `blocking-downstream` 的 `OPEN-N9-1`，且**本站是它指定的落點**。

## 〇、不重問的事（上游已定案）

| 事項 | 定案處 |
|---|---|
| 連線路徑：自架 runner ＋ `docker compose exec -T db psql` | `[N1]`=A；`NFR7.12` |
| 清除兩個目標、順序（稽核先於記憶）、交易邊界（步1+2 同交易、步3 獨立） | `nfr-design/security-design.md §三` |
| 不需要 retry／circuit breaker（清除冪等且自我收斂） | `nfr-design/security-design.md §三之三` |
| 系統 actor 的形狀（哨符 username、非 canonical role、`is_active = FALSE`） | `[ND1]`=A |
| `NFR6.10` 不構成 IAM 邊界，接受現況 | `[ND2]`=A |
| 決定性邏輯放純 Actions 步驟，不走 LLM 路徑 | `NFR7.14`；`FR4.5a` 附註 |
| 零新部署設定、零新 GitHub secret | `NFR8.10`；`NFR7.12` |

### 〇之一、本站自行定案的兩項（低風險，附理由，不出成題目）

`OQ-13` 的「落點」那一半（`OPEN-N9-3`）：

| 項目 | 本站定案 | 理由 |
|---|---|---|
| workflow 檔名 | `.github/workflows/memory-retention-purge.yml` | 與既有命名慣例一致（`deploy.yml`／`ci.yml` 為功能名）；**不以 `.md` 結尾**，因為那是 gh-aw 的慣例而本單元刻意不走 LLM 路徑（`NFR7.14`） |
| 排程頻率 | **每日一次**（`on: schedule`，UTC 離峰時段） | 90 天保存期之下，每日執行使任何列的逾期時間**至多 1 天**。成本是每日一次兩條 SQL——可忽略。更長的週期（如每週）會讓逾期窗口達 7 天，而那是使用者以為已刪除的個人對話歷程 |

**為什麼這兩項不出成題目**：它們沒有安全後果、沒有互斥的替代方案、
且上游已把判準寫死（`FR4.5` 要求「自動」、`NFR7.14` 要求純 Actions）。
`project.md` 記過「單一可行解的假選擇」不該出成題目。

---

## 一、`[ID1]` `NFR7.13` 的偵測機制：怎麼發現「排程根本沒跑」？

### 問題的形狀

`[N1]`=A 讓清除跑在自架 runner 上。其代價已由上游定案並記為 `NFR7.13`：
**runner 離線時 `on: schedule` 不會排入、不會失敗、不會有任何 run**
——Actions 清單上只是少一列，而少一列沒有顏色。

上游已固定判準：**偵測機制必須不依賴那個 runner**
（依賴它的檢查會在 runner 離線時與被偵測的失敗同時消失）。本站選機制。

### 本站查證到的機械事實

| 查證項 | 結果 |
|---|---|
| 既有的排程 workflow 跑在哪 | **7 個全部**在 GitHub 託管 runner（`ubuntu-slim`／`ubuntu-latest`）——雙向查證見 `nfr-requirements/tech-stack-decisions.md §三` |
| 既有排程 workflow 怎麼通知 | `daily-digest.md` 與 `release-watch.md` **都用 `safe-outputs: create-issue:`**——開 GitHub issue 是本 repo 既有的通知管道 |
| 那兩個是不是 LLM 驅動 | **是**，它們是 gh-aw（`.md` ＋ `engine`），而 `project.md` 把「所有 LLM 路徑」列為本 repo 三塊結構性盲區之一 |
| 有沒有不需要資料庫就能判斷新鮮度的資料來源 | **有**：GitHub Actions API 知道任一 workflow 最後一次成功執行的時間（`gh api`），完全不需要碰資料庫 |

**關鍵洞察**：偵測「有沒有跑」**不需要資料庫**。問「資料庫裡最舊的逾期列有多舊」
需要資料庫（而資料庫在那個可能離線的主機後面）；問「那個 workflow 上次成功是什麼時候」
只需要 GitHub 自己的 API。後者是同一個問題的可達版本。

### 選項

| 選項 | 做法 | 後果與代價 |
|---|---|---|
| **A（建議）** | **新增一個 GitHub 託管的純 Actions 排程 workflow**：以 `gh api` 查清除 workflow 最後一次成功執行的時間，超過門檻（如 3 天）即 `gh issue create` 開 issue | **完全不依賴自架 runner**（跑在 GitHub 託管上）、**完全不碰資料庫**、**零新 secret**（用內建 `GITHUB_TOKEN`）、**零新部署設定**（`NFR8.10` 不破）。通知管道沿用 repo 既有慣例（開 issue）。且它是**純 Actions**，不走 LLM 路徑——合 `NFR7.14` 的同一個理由（一個二元的新鮮度比較不需要 LLM，交給 LLM 只會讓它落在那塊結構性盲區裡）。代價：多一個 workflow 檔；需要 `issues: write` 權限（既有兩個排程 workflow 已有 `issues` 權限的先例） |
| **B** | **把檢查併入既有的 `daily-digest`**（gh-aw） | 零新 workflow 檔。代價：`daily-digest` 是 **LLM 驅動**（`engine: copilot`），而一個「比較兩個時間戳」的決定性檢查交給 LLM，正是 `project.md` 與 `FR4.5a` 附註都反對的形狀——它會讓這道守門落在本 repo 三塊結構性盲區的「所有 LLM 路徑」那一塊。且 digest 的性質是摘要而非告警，漏報不會有人察覺 |
| **C** | **讓清除 workflow 自己在失敗時大聲叫** | 零新機制。**但它對本問題無效**：要偵測的狀況正是「它根本沒有執行」，而沒執行的 workflow 不會失敗、不會通知。這是 `project.md` 記過的「不可達的規則」形狀——一個永遠不會觸發的檢查 |
| **D** | **以資料庫新鮮度為判準**：查「最舊的逾期未刪列有多舊」 | 它直接量測真正關心的事（資料有沒有被清掉），而非代理指標（workflow 有沒有跑）。**但它需要連資料庫**，而資料庫在那個可能離線的主機後面——若主機整體不可用，這個檢查與被偵測的失敗**同時消失**，正是上游判準要排除的形狀。（若改由 GitHub 託管 runner 連資料庫，則需要暴露資料庫，那已在 `[N1]` 被否決） |

[Answer]: A GitHub 託管的純 Actions 監看排程
<!-- 作答時間 2026-10-08T09:38:09Z，以 `date -u` 取值 -->

**後果（本站據此設計，見 `monitoring-design.md`）**，以及**一處選項描述的更正**：

### 作答後的更正：`issues` 權限的先例比我寫的窄

提問時我寫「需要 `issues: write`（既有兩個排程 workflow 已有 `issues` 權限的先例）」。
**作答後開檔核對，這句話不準確**：

| 查證 | 結果 |
|---|---|
| `daily-digest.md` 的 `permissions` | `contents: read`／**`issues: read`**／`pull-requests: read`／**`actions: read`** |
| 它怎麼開 issue | 透過 gh-aw 的 `safe-outputs: create-issue:`——那是一條**經過消毒的獨立寫入路徑**，不是把 `issues: write` 授給 agent |

**故本 repo 目前沒有任何排程 workflow 持有 `issues: write`。** 本設計要的那個權限
**比任何既有排程 workflow 都寬**，這一點必須如實記載而非以「有先例」帶過。

**真正有先例的是 `actions: read`**（`daily-digest.md:13`）——而那恰好是監看者查詢
workflow 執行紀錄所需的權限。

**結論不變（A 仍是正解）**，但代價欄要改寫：它不是「沿用既有權限先例」，
而是「新增一個本 repo 尚無先例的寫入權限，範圍限於開 issue」。
處置與替代方案見 `monitoring-design.md §二之三`。
