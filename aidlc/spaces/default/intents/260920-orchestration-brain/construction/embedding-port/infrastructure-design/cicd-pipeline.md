# CI/CD Pipeline — `U6 embedding-port`（`library`）

<!-- Stage: infrastructure-design（Construction 3.4）· Unit: embedding-port · kind: library -->

## 〇、本單元在管線裡的位置

**本單元零容器、零服務、零端點、零新依賴。** `produces_kinds` 因此只開放
`cicd-pipeline` 與 `traceability`——`infrastructure-specification` 與
`monitoring-design` 是 `[service, ui, packaging]`，本單元**不產出**，
而那不是省略：沒有要佈的東西。

所以本檔談的不是「要開什麼資源」，而是**它對既有管線造成什麼**。

**本檔消費的上游（逐一開檔核對）**：`../nfr-design/security-design.md`
（`D-1`–`D-10`、§五 的 `H-N1`–`H-N4`）、`../nfr-design/logical-components.md`
（§二 失敗域、§五 隔離策略）、`../functional-design/functional-spec.md`
（§一 W1／W2）、`inception/domain-design/components.md`、
`inception/contract-design/contract-summary.md`（`K-01`／`K-06`）。

**本單元不需要的上游**：`performance-design`／`scalability-design`／
`reliability-design`／`observability-design` 四份對 `library` 從未產出
（`nfr-design` 的 `produces_kinds` 限定 `[service]`）。其內容的落點見
`../nfr-design/security-design.md §〇·二` 的八列狀態表。

## 一、既有管線（**修訂 1：原表是錯的，見下方更正說明**）

### 實際的 job 圖（`.github/workflows/ci.yml`，逐一核對）

```
gate （:55）
  ├─→ repo-contract （:141，needs: gate）
  ├─→ frontend      （:169，needs: gate）
  ├─→ backend       （:233，needs: gate）
  └─→ docker-build  （:299，needs: gate）
```

**四者各自 `needs: gate`，彼此平行，不是序列。**

| Job | 內含步驟 | 本單元的影響 |
|---|---|---|
| `gate` | sync write-back 閘門 | **無影響** |
| `repo-contract` | `validate_repo_contract.py`、`validate_env_contract.py`、`validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py`（皆經 `actions/setup-python@v5`） | **會被觸發，見第二節** |
| `frontend` | lint ＋ `tsc -b` ＋ build | **無影響**（零前端改動） |
| `backend` | ① import smoke → ② **OpenAPI 漂移**（`dump_openapi.py --check`，`:280`）→ ③ **WS 契約漂移**（`dump_ws_contract.py --check`，`:291`）→ ④ `python -m unittest discover -s tests` | ②**無影響**（零 HTTP 端點，`openapi.json` 不變）；③**無影響**（零 WebSocket 改動，本單元是行程內 library）；④ 新測試檔被自動撿到，見第三節 |
| `docker-build` | buildx 建兩個 image，`push: false` | **無影響**：`requirements.txt` 淨變更為零，image 內容不變；且本單元**不碰任何 compose 的服務定義**——`deploy/docker-compose.deploy.yml` 的 `ollama` 服務仍然沒有 `ports:`（實測：整個 deploy stack 只有 `frontend` 有 `ports:`），本單元零新增暴露面 |

> **修訂 1 的更正（審查 `R-02`，Major）。** 本節原本的五列表格標著「實測，非引述」，
> 而它**憑空多出一個不存在的 job**（把 OpenAPI 漂移寫成獨立 job #3，實際是
> `backend` job 內的一個 step，`:280`）、**漏掉同一個 job 裡的第二道漂移閘門**
> （`dump_ws_contract.py --check`，`:291`）、**漏掉 `gate` job**，並把四個平行的 job
> 畫成 1→5 的序列。一個宣稱「實測」卻發明了 job 的表，比沒有表更糟——
> 它正是本站存在的理由（給下游一份可信的管線事實）所要防的東西。已整節重寫。

## 二、`repo-contract` 的七道環境檢查，逐條判定

`scripts/validate_env_contract.py` 的 `main()` 依序跑**七**道檢查（不是四道
——審查 `R-03`，Major：本節原文把四道框成完整集合，而那個「完整」是假的）。
`[Q2]` 於**修訂 1 反轉為遵守 `NFR8.1` 逐字**（審查 `R-01`，Critical），
所以會觸發的是**三道**：

| # | 檢查 | 是否觸發 | 為什麼 |
|---|---|---|---|
| 1 | `validate_workflow_uses_the_renderer` | **否** | 管的是 `deploy.yml` 不得繞過 `render-env.sh` 自行寫 `deploy/.env`；本單元不改 `deploy.yml` |
| 2 | `validate_deploy_stack_is_fully_supplied` | **會** | timeout 變數以**無 fallback** 形式進部署 compose（比照既有四個），故 `render-env.sh` **必須**寫它。失敗訊息逐字：「requires … with no fallback, but … never writes them. GitHub Actions deploys would start the stack with those values empty — a silently degraded service, not a failed deploy」 |
| 3 | `validate_deploy_template_is_complete` | **會** | 同一組 `required` 集合也必須出現在 `deploy/.env.example`（手動 host-copy 路徑要能填齊）。失敗訊息逐字：「an incomplete template is an undeployable stack」 |
| 4 | `validate_deploy_template_sets_nothing_derived` | **否** | `DEPLOY_DERIVED` 只含 `DATABASE_URL` 與 `VITE_API_BASE_URL`；timeout 變數不是 compose 推導值 |
| 5 | `validate_scopes_are_separated` | **否** | 本單元不把本機來源（`localhost`／`127.0.0.1`）寫進部署範本，也不把部署專屬 key 寫進 dev 範本 |
| 6 | `validate_local_dev_template_is_complete` | **會** | 它掃 `backend/**/*.py`（排除 tests）的所有環境變數讀取，要求每一個都被 `backend/.env.example` 記載。失敗訊息逐字：「An undocumented variable is one a developer cannot set without reading the source」 |
| 7 | `validate_templates_ship_no_placeholder_values` | **否** | 範本要寫真實值 `10`，不是 `<fill-me>` 這類佔位符。**但這是一條要遵守的約束**，不是不相干 |

### `[Q2]` 的反轉（審查 `R-01`，Critical）

**原決定（`[Q2]`=A）與上一站已核可且通過審查的 `NFR8.1` 直接矛盾。**
`NFR8.1` 逐字：timeout 變數「**必須在同一個 PR 內**讓 `deploy/render-env.sh` 寫它、
`deploy/.env.example` 列它、`backend/.env.example` 列它，並同步更新 `LOCAL-DEV.md`」，
而原 `[Q2]`=A 說前兩者「**不需**變動」。更糟的是 `traceability.json` 仍把 `NFR8.1`
標為 `OK`——**設計文字與追溯表各說各話，而下游只會讀到其中一份**。

修訂 1 的處置：**反轉 `[Q2]`，遵守 `NFR8.1` 逐字**（使用者裁決）。
不選「修訂 `NFR8.1`」是因為合規成本只有四個檔各加一到兩行，
而那四個檔已經各有四行同形內容；且順帶讓 staging 調 timeout 不必改 code 重新部署。

**因此本單元要改的設定檔是四個**（原為一個）：

| 檔 | 改動 | 被哪道檢查強制 |
|---|---|---|
| `deploy/docker-compose.deploy.yml` | 加一行，無 fallback 形式，比照 `:120-123` | —（它是 #2／#3 的輸入） |
| `deploy/render-env.sh` | 加一行字面值，比照 `:124-127` | #2 |
| `deploy/.env.example` | 加一行 ＋ 註解 | #3、#7 |
| `backend/.env.example` | 加一行 ＋ 註解 | #6、#7 |

**加上 `LOCAL-DEV.md` 的 blocking 同步**（`project.md ## Mandated`），且它有**兩項**
要寫：timeout 變數，以及 `fastembed` 的帶版本安裝指令與 HuggingFace 下載說明
（`[Q4]`=A 讓隱性硬依賴由 2 個變 3 個）。

## 三、測試在 CI 的實際覆蓋（**三個實作只跑得到一個**）

這是本檔最重要的一節，因為它記的是一個**不會被任何紅燈揭露的事實**。

| 實作 | CI 是否執行 | 依據 |
|---|---|---|
| `stub` | **是** | `docker-compose.test.yml:102` 為 `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-stub}`；單元測試亦直接建它 |
| `ollama` | **否** | `docker-compose.test.yml:18` 逐字「NO ollama. `EMBEDDING_PROVIDER` is `stub` instead」——test stack 沒有該服務 |
| `fastembed` | **否** | 不在 `backend/requirements.txt`（`[Q4]`=A），CI 根本不會安裝它 |

### `[Q1]`=A 的處置：分成「可 mock 的」與「真的測不到的」

**可以在 CI 覆蓋的（用 mock／monkeypatch，不需要真服務）**：

| 行為 | 承載 | 怎麼測 |
|---|---|---|
| `fastembed` 未安裝 → 拋 `EmbeddingProviderUnavailable` 且訊息含安裝指令 | `BR4.3` | monkeypatch 讓 import 失敗 |
| 逾時 → 拋 `EmbeddingProviderUnavailable` | `NFR3.2`、`D-6` | 以不可達位址或 mock transport 構造 |
| 例外訊息剝除 `userinfo` | `SEC-2`、`D-7` | 以含 `user:pass@` 的 `OLLAMA_BASE_URL` 構造 |
| 超長輸入截斷 ＋ WARN | `D-4` | mock 提供者，斷言送出前已截斷且 `assertLogs` 捕捉到 WARN |
| 啟動驗證的四類失敗 | `BR1.1`／`BR1.3`／`NFR7.1` | 直接呼叫驗證函式，不經 startup hook |
| 批次語意、決定性、1024 維、空輸入 | `P1`–`P4`、`P6` | 對 `stub` 執行 |
| 雙向一致性 | `P5`、`BR3.3` | 純設定推導，三個實作都驗得到 |

**真的測不到的，只有一件事**：`ollama` 與 `fastembed` **實際回傳的向量是否真為
1024 維**。這一項在首次真實呼叫時會由 `BR2.2` 的執行期斷言攔下——**大聲失敗，
不是靜默**。缺口照 `../functional-design/functional-spec.md` 的 `OQ-E2` 形狀維持具名。

**為什麼不加 CI job**（`[Q1]` 的 B／C／D 各自的代價）：B 要每次 PR 下載約 1GB 模型，
為一條**本機限定**的路徑付 CI 時間；C 直接推翻 `docker-compose.test.yml:18` 的既有
決定，且該檔註解寫明它刻意是四服務的短生命週期 stack；D 推翻 `[Q4]`=A 與已核可的
「`requirements.txt` 淨變更：零」。

## 四、部署與 rollback

### 本單元在部署路徑上的新失敗模式（**修訂 1 後已被 CI 擋在部署之前**）

`D-1` 讓設定錯誤**終止啟動**（`BR1.6`、ADR-008「不得靜默降級」）。
在 deploy-on-merge 之下，這條路徑是：

```
PR 合併進 ut
   → deploy.yml 在自架 runner 上 up -d
   → backend 啟動 → startup hook → 驗證 EMBEDDING_PROVIDER 等四個變數
   → 不通過 → 行程終止 → 部署失敗
   → rollback job：還原 last-good ＋ 開 revert PR ＋ dispatch Deploy Doctor
```

**也就是說，一個非法的 `EMBEDDING_PROVIDER` 不只是部署紅燈，是一次自動回退。**

但實際風險比它聽起來小：`deploy/render-env.sh:124-127` 把那四個值寫成**字面值**
（`EMBEDDING_PROVIDER=ollama` 等），不是從 GitHub secrets 解析。所以風險不是
「secret 沒設」，而是「**有人改了那四行**」。

### 這個缺口**被關上了**，而原本的理由是個假兩難（審查 `R-04`，Major）

**缺口**：`repo-contract` 在部署之前跑，但 `validate_env_contract.py` 驗的是
**「compose 要的變數有沒有被寫入」**，**不驗「值是否在允許集合內」**。
所以把 `render-env.sh:124` 改成 `EMBEDDING_PROVIDER=ollamaa` 的 PR
**會通過 CI**，然後在部署時炸並觸發自動 rollback ＋ revert PR。

**原本我寫的理由是**：補它需要在 CI 複製一份允許值清單，而第二份清單會漂移
——那正是 `team.md`「單一真實來源」要防的，且本單元才剛為此寫了 `BR3.3`。

**那是個假兩難。** 審查指出還有第三條路，而實測證明它便宜：
`repo-contract` job **已經有 `actions/setup-python@v5`，並已經跑四支 Python
validator**（`validate_repo_contract.py`、`validate_env_contract.py`、
`validate_cost_calculator_boundary.py`、`validate_pricing_lookup_boundary.py`）。
所以 CI 可以**直接 import 並呼叫 `D-1` 的那個驗證函式**
（允許值清單的唯一真實來源），拿它去驗 `render-env.sh` 會寫出的值
——**零第二份清單、零漂移風險**。既有前例就在隔壁：`dump_openapi.py --check`
正是在 `backend` job 裡 import 應用程式碼來做漂移檢查。

**修訂 1 的決定（使用者裁決）：加這個檢查，缺口關閉。**

| | 修訂前 | 修訂後 |
|---|---|---|
| 誰先發現值錯 | 部署（自動 rollback ＋ revert PR） | **`repo-contract`，部署之前** |
| 允許值清單份數 | 1（但缺口開著） | **1**（CI 呼叫同一份） |
| 新增成本 | — | `repo-contract` 多一個 step；無新依賴、無新環境 |

**設計決定在本站，具體的 YAML 與 step 名稱交給 `code-generation`**
（與本站對 `H-N4` 的做法一致）——見第六節 `H-I3`。

**我把原本的錯誤理由留在上面而不是刪掉**，因為「用一條風格規則去迴避一個
真實的安全缺口」是這一輪最值得記住的失誤形狀：規則本身是對的，
但我沒有去找「同時滿足該規則又關上缺口」的第三個選項。

### 回滾

本單元**沒有自己的回滾程序**——它沒有 schema 變更、沒有資料遷移、沒有外部狀態。
`git revert` 即完整回滾；既有的 `rollback` job 不需要任何本單元專屬的步驟。

## 五、Secrets

**本單元引入零個 secret。** 四個既有變數全部是非機敏字面值
（提供者名、服務內部 URL、模型名），`render-env.sh` 註解逐字說明它們
「**不經 GitHub secrets**」。新增的 timeout 變數同樣非機敏。

唯一與 secret 相關的要求是 `SEC-2`／`D-7`：例外與 log 不得含 `userinfo`
——那是**防範**（目前 `OLLAMA_BASE_URL` 無 userinfo），不是修補。

## 六、交給後續站的事

| # | 事項 | 落點 |
|---|---|---|
| `H-N4`（承 `nfr-design`） | timeout 環境變數的**確切名稱**（建議 `EMBEDDING_TIMEOUT_SEC`）與 `backend/.env.example` 的記載 | `code-generation`（3.5，`ALWAYS`） |
| `H-I1` | `LOCAL-DEV.md` 的**兩項**更新：timeout 變數 ＋ `fastembed` 的帶版本安裝指令與 HuggingFace 下載說明 | `code-generation`（3.5，`ALWAYS`）——`project.md` 的 blocking 規則 |
| `H-I2` | ollama 容器的 CPU／RAM 配額與 staging 主機餘裕的**實測**（`K-01` 標明那兩個數字未實測） | 不屬本單元；`U1 brain-infra` 與 `operation` 階段 |
| `H-N1`（承 `nfr-design`） | `embed` 延遲的自動化斷言 | `build-and-test`（3.6） |
| `H-N2`（承 `nfr-design`） | telemetry 基礎設施（`/metrics`） | `observability-setup`（4.4，**CONDITIONAL**——被 skip 時判定者須重新提交使用者） |
| `H-I3` | **`repo-contract` 的新 step**：import 並呼叫 `D-1` 的驗證函式，驗 `render-env.sh` 寫出的 `EMBEDDING_PROVIDER` 值在允許集合內。**設計決定已在本站定案（審查 `R-04` 後反轉）**，交出的只有具體 YAML 與 step 名稱。**禁止在該 step 內自行列舉允許值**——那會重新製造被否決的第二份清單 | `code-generation`（3.5，`ALWAYS`） |
