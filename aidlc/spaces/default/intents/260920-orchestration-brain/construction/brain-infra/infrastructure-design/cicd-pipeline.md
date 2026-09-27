# CI/CD Pipeline — `brain-infra`（U1）

## 這份檔在做什麼

本檔描述**本單元對既有 CI/CD 的改動**，不重新設計管線——`ci.yml` 與 `deploy.yml` 的既有
形狀由 ADR-0007／ADR-0008 定案，本單元只增不改結構。

**探測的設計不在本檔重做**：`PROBE-CONTRACT` 七條（P-1…P-7）、三個落點與 `rollback` 那一半
的形狀全部在 `nfr-design` 的 `security-design.md` 定案，本檔只承接並說明它在管線裡的位置。
那一站的教訓已套用於此：**設計文件裡的可執行程式碼會成為缺陷來源**，所以本檔不給 YAML 或
shell，只給契約與位置。

---

## 一、既有管線的形狀（本單元不改）

| Workflow | 觸發 | Job 序列 | 本單元是否改動 |
|---|---|---|---|
| `ci.yml` | PR 與 push 到 `main`／`ut`／`danniel/**`／`chore/**` | `repo-contract` → `frontend`（lint ＋ `tsc -b` ＋ build）→ OpenAPI drift 檢查 → `backend`（import smoke ＋ `unittest`）→ `docker-build`（buildx 建兩個 image，`push: false`） | **完全不改**（已實地查證）。`docker-build` 只有兩個步驟：`context: ./backend` 與 `context: ./frontend`，皆 `push: false` 的純建置驗證。新增的 `redis`／`ollama` 用**官方映像、不經 Dockerfile**，不在它的作用域內 |
| `deploy.yml` | PR closed（merge）到 `ut`，或手動 `workflow_dispatch` | `deploy`（自架 runner，`timeout-minutes: 30`）→ 失敗時 `rollback`（`timeout-minutes: 20`）→ `notify`（GitHub-hosted，`timeout-minutes: 5`） | **改兩個 job 的步驟**，見 §二 |
| `ui-regression`（gh-aw） | 每個 PR | 起 `docker-compose.test.yml` 的短生命週期 stack、跑 Playwright、回報 Kiwi TCMS；`post-steps` 讀 `pw-report.json` 的 `.stats.unexpected`，非 0 即 `exit 1` | **改它消費的 compose**，見 §三 |

---

## 二、`deploy.yml` 的改動（承接 `nfr-design` 的 `S-6`）

### 兩處新增步驟

| Job | 位置 | 承載什麼 |
|---|---|---|
| `deploy` | **獨立新步驟**，在 `Wait for the frontend to answer locally` 步驟**之後**（**不在**該步驟的迴圈內——那個迴圈第一次成功即 `exit 0`，加在裡面是永不執行的死碼） | `PROBE-CONTRACT` 全部七條；失敗**讓 job 紅燈**（進而觸發既有 `rollback`） |
| `rollback` | **併入** `Restore the last-good deployment` 步驟裡既有的健康檢查迴圈 | 同一個探測，但**結果以 `$GITHUB_OUTPUT` 的 `restored` 表達、不使用 `exit`**——該步驟今天不因健康檢查紅燈，且 `notify` 的 `case` 只認三個值 |

**兩個 job 的形狀不可互抄**，理由與具體約束見 `security-design.md` 的
「`rollback` 那一半的形狀」專節（`P-6`／`P-7`）。本檔只重申結論：**`deploy` 用結束碼，
`rollback` 用 output；後者採「`/` 與 `/api/auth/login` **兩者皆通**才 `RESTORED=healthy`」，
不新增第四種狀態值。**

**⚠ 「通」對兩個端點不是同一個意思，必須寫明否則實作者會寫出永不通過的檢查**（本輪補查自審：
原句只寫「兩者皆通」）：`/` 的通是 **HTTP 2xx**（`try_files` 回靜態檔）；`/api/auth/login` 的通是
**HTTP 401**——依 `P-3`，探測刻意用一個**不存在**的固定使用者名稱，所以 401 才是「backend 起來了
且它查得到資料庫」的證據，2xx 反而代表探測寫錯了（真的登入成功）。**`P-2` 是這件事成立的前提**：
受測端點的處理必須**在任何憑證比對之前查資料庫**，目前滿足此性質的是 `POST /api/auth/login`
（`security-design.md` 的 `P-2` 已逐字指名並附 `backend/services/user_router.py` 的行號）——換成
任何不先查庫的端點，401 就不再證明 `backend`→`db` 連通，整個探測失去意義。

### 為什麼這兩處是必要的，而既有四道機制不夠

`nfr-design` 的審查 R-01（Critical）已逐項查證：`deploy.yml` 的兩個 `curl` 都打 `/`（由
`try_files` 回靜態檔）、`db` 的 `pg_isready` 在**容器內部**執行、`depends_on:
service_healthy` 只管啟動順序，而 `deploy.yml` 全檔對 `/api` 的命中數是 **0**。所以
`backend`→`db` 斷掉時，部署會**綠燈通過**，站台首頁正常而所有需要資料庫的功能全壞。

**而本單元正是那個會弄斷它的變更**——`nfr-design` D-3 把既有的 `db` 服務移進 `internal`
網段。

### 探測的重試窗口與 job 逾時的關係（必須實測）

| 項目 | 值 | 來源 |
|---|---|---|
| 重試次數 × 間隔 | 30 × 5 秒 | 與既有兩道檢查同形 |
| 牆鐘上界 | **不是一個可以在設計階段算出的常數**——見右欄的不等式與指派 | `nfr-design` 的 `P-4` 只要求「必須有連線逾時與總逾時上限」，**沒有給值**（複驗 `security-design.md:398` 逐字），所以初版的 `≈ 10 分鐘` 算不出來（自檢第 6 項查出）。**第二版的「取 job 逾時的一半」也不成立（審查 R-43）**：「一半」是一個沒有來源的係數，而且**預算裡沒有扣掉同一個 job 的其餘消費**。實讀 `rollback` job（`deploy.yml:169–301`，`timeout-minutes: 20` ＝ 1200s），探測併入 `Restore the last-good deployment` 步驟，而同一個 20 分鐘之內還有：checkout ＋ `render-env.sh`、**無界的 `up -d --build`**、既有的 150s 8090 迴圈，以及該步驟**之後**三個 `if: always()` 步驟（`Capture the failing deploy log` `:239`、`Open a revert PR` `:249`、`Hand the failure to the Deploy Doctor` `:284`）。**約束式**：設探測為 `N` 次重試、間隔 5 秒、單次總逾時 `T`，則牆鐘 `W = N × (T + 5)`，要求 `W ≤ 1200 − (up -d --build 實測) − 150 − (三個 if: always() 步驟實測) − (checkout ＋ render 實測) − 安全餘裕`。**代入 `N = 30`、`T = 15` 的反例**：兩個迴圈合計就是 `150 + 600 = 750s`，只剩 450s 給一個**無界**的 `up -d --build` 加三個後續步驟——逼近或超過 1200s 是可達的，而超時的後果是 **rollback 本身被砍掉**：站台留在壞版本、revert PR 沒開。**指派（`code-generation`，三件都要）**：(1) 在自架 runner 上**實測**上式右側的每一項（`up -d --build` 必須實測，不可從 1200s 直接分配）；(2) 由**重試次數 `N`** 吸收差額（rollback 側用較少次數即可，`T` 不必因此被壓到失去區分「還在啟動」與「真的斷了」的能力），並寫下所選 `N`／`T` 滿足上式；(3) 實測值與所選值記入 `DEPLOY.md`（第 13 項第 (9) 條已涵蓋此欄位）。**`deploy` 側**（`timeout-minutes: 30`，`deploy.yml:28`）較寬鬆，由較緊的 rollback 側反推出的 `N`／`T` 對它是保守的，方向正確（審查 R-43 複驗此點無誤）。**不回改 `security-design.md`**——已核可產出，`P-4` 的「必須有上限」本身成立，缺的是值 |
| `deploy` job 逾時 | 30 分鐘 | `deploy.yml:28` |
| `rollback` job 逾時 | **20 分鐘** | `deploy.yml:177` |

**`rollback` job 的餘裕不大**：它內含 `up -d --build` ＋ **單一** 8090 迴圈（≤150s），再加一個上界
10 分鐘的探測。**本輪更正（審查 R-42）**：初版另列了一個「tunnel 迴圈（≤120s）」，而實讀 `deploy.yml`
的 `rollback` job（`:169–301`）——該 job 內的 `curl` 只有**一處**（`Restore the last-good deployment`
步驟內，`for _ in $(seq 1 30)` ＋ `sleep 5` ＝ 150s，打 `http://127.0.0.1:8090/`），全 job 對
`cloud360.danniel.cc` 的命中數為 **0**；tunnel 迴圈（`seq 1 24`，120s）只存在於 `deploy` job
（`:127–139`）。這段是「餘裕夠不夠」判斷的唯一依據，而初版把 rollback 的既有消費**多算了 120 秒**。**實作時必須實測實際耗時並記入 `DEPLOY.md`**；
若逼近 20 分鐘，要嘛縮短探測窗口（但那會犧牲它區分「還在啟動」與「真的斷了」的能力），
要嘛提高 `timeout-minutes`——**兩者都是需要決定的事，不是實作者可以順手挑的**。

### 探測不需要任何 secret

`PROBE-CONTRACT` 的 `P-3` 要求使用者名稱是一個**不存在的固定值**，所以探測不需要憑證、
不產生任何狀態（不建帳號、不留稽核列）。**這使它可以放進 workflow 而不新增任何 secret**，
所以**探測本身**不因它而觸及「憑證必須落在 secrets 而非 variables」那條規則。**但本單元整體確實觸及它**（審查 R-41）：第 3 項要把 `REDIS_PASSWORD` 加進 `deploy.yml` 的 `env:`（`${{ secrets.… }}`），那是一個**新的憑證型 secret**，複查義務與其二元判準寫在第 4d 項。這一句只限定探測的範圍，不得被讀成整站的結論。

### 這符合「無人值守的流程自動化一律以 workflow 承載」

`project.md ## Forbidden` 禁止以 repo 內的實作程式承載無人值守的流程自動化。探測落在
**純 GitHub Actions 步驟**（不是 `scripts/` 下的 Python，也不是 gh-aw 的 LLM 路徑），
**符合**該條。且它是決定性的映射邏輯而非判斷性工作，依同一條規則的後半段，正該放在純
Actions 步驟而不交給 gh-aw。

---

## 三、CI test stack 的改動（`[I5]`=A）

### `EMBEDDING_PROVIDER=stub`，**不在 CI 起 Ollama**

| 決定 | 內容 |
|---|---|
| **做什麼** | `deploy/docker-compose.test.yml` 的 `backend.environment:` 加 `EMBEDDING_PROVIDER: stub`（依 `NFR8.1b`，該 stack 的慣例是自帶測試用預設值） |
| **不做什麼** | **不在 CI test stack 加 `ollama` 服務** |
| **既有先例** | 同檔 `:35–37` 逐字：`# A1 generation is out of scope for these tests; leave the key empty so` ／ `# the app boots but the LLM path stays untouched.` ＋ `OPENROUTER_API_KEY: ""` |
| **enum 支援** | `contract-summary.md` `K-01` 的 `EMBEDDING_PROVIDER` 逐字 `allowed: [ollama, fastembed, fulltext, stub]` |

**為什麼不起 Ollama**：`ui-regression` 是每個 PR 都跑的**真閘門**（`post-steps` 讀
`.stats.unexpected`，非 0 即 `exit 1`）。在它裡面拉約 1.2GB 的模型會把每次 PR 的成本與
失敗面都拉大，而模型快取本身又是一個新的維護面與新的失敗模式。

**為什麼不能留空**：`K-01` 對 `EMBEDDING_PROVIDER` 的 `validation` 逐字是「值不在 `allowed`
內即啟動失敗並列出可選值」、`required: true`、**無預設值**（「偵測不到選定提供者時須大聲
失敗」）。所以留空會讓 backend 啟動失敗，`ui-regression` 全紅。

**為什麼選 `stub` 而不是 `fulltext`**：`fulltext` 的語意與向量檢索不同，e2e 斷言若依賴
相似度排序會得到不同結果——那比 `stub` 更容易寫出**假綠燈**（測試通過但它測的不是產品的
實際行為）。embedding 的真實行為由 **`U6 embedding-port` 的單元測試**覆蓋，該契約的
`verification` 已含 property-based 測試。

**為什麼也不選 `fastembed`（`components.md` 明確指出它不需要新服務）**：該檔的 External
Dependencies 表逐字寫 `MemoryStore` → fastembed「本機無 Ollama 時的行程內 embedding；
**ONNX、不拉 torch、不加服務**」。所以它確實是「不起容器」的另一個選項，且比 `stub` 更接近
真實行為。**不選它的理由是 CI 的成本結構**：它雖不加服務，但會在 backend 映像裡引入 ONNX
執行期並在首次使用時**下載 `multilingual-e5-large` 模型**——對每個 PR 都跑的
`ui-regression` 而言，那和拉 Ollama 模型是同一類成本，只是換了個位置。`stub` 是唯一
**零下載**的選項。

**這一項的邊界要說清楚**：選 `stub` 意味著 **CI 完全不驗證任何 embedding 路徑**。
`components.md` 的 `MemoryStore` 依賴四種 provider（`ollama`／`fastembed`／`fulltext`／
`stub`），而 `EmbeddingPort` 的四個實作與其切換邏輯**只由 `U6` 的單元測試覆蓋**——e2e 層
沒有任何一條會碰到它。這是刻意的分工，但如果 `U6` 的測試被削弱，**沒有第二道防線**。

#### ⚠ 本決定使 `U6 → brain-infra` 依賴邊的上游理由不再成立（審查 R-09）

`inception/units-generation/unit-of-work.md:268` **逐字**記載：

> `U6` 的 `depends_on: [brain-infra]` 取的是「**ollama 與 fastembed 兩個實作要能被驗證**」

而本站把 `ollama` 排除在 CI test stack 之外（`[I5]`=A）、又以成本理由排除 `fastembed`——
**於是那兩個實作在本 intent 的任何自動化層都沒有可執行的環境**：e2e 走 `stub`，`U6` 的單元
測試只能以 mock 覆蓋 HTTP（ollama）與 ONNX（fastembed）邊界。

**`verification` 含 property-based 不補這個缺口**：property-based 測試約束的是**純函式**，
它不會驗證 `ollama` provider 真的接得上一個在跑的 Ollama。

**本站不自行定案，指名承接者與該回答的問題**：

| 誰 | 要確認什麼 |
|---|---|
| **`U6` 的 functional-design** | `ollama`／`fastembed` 兩個實作的驗證手段——mock 邊界測試夠不夠？還是需要一次性的手動驗證並記入 `DEPLOY.md`？ |
| **`U6`／`U1` 的 delivery 順序** | 若 `U6 → brain-infra` 的依賴邊理由已不成立，那條邊還需要嗎？**本站不擅自移除已核可的依賴邊**，但必須指出它的理由變了 |

**為何不由本站解決**：`[I5]`=A 是為了不讓 `ui-regression` 每個 PR 拉 1.2GB 模型，那個理由
仍然成立；而「`ollama` 實作怎麼被驗證」是 `U6` 的測試策略問題，不是部署打包的問題。**但把
它留在這裡不說，就會變成一個沒人知道自己繼承了的缺口。**

### CI test stack 的其他改動

| 改動 | 依據 |
|---|---|
| `db` 映像改為 PG 18 ＋ pgvector | `NFR6.1` 落點 2（「`ui-regression` 每個 PR 自動起」，所以它走的是空 volume 初始化路徑） |
| 加 `redis` 服務 ＋ `backend.environment:` 的 Redis 三者（自帶測試預設值） | `NFR8.1b` |
| 加 `networks:` 分段（`edge`／`internal`） | `nfr-design` D-3。**理由與 deploy stack 不同**——test stack 沒有 `cloudflared`，所以沒有現存威脅要擋；加它的唯一理由是**避免兩份 compose 的形狀漂移** |
| 加 `logging:` 到全部服務 | `[I4]`=A／`S-9`。效果上不需要（stack 每次重建），理由同上——避免漂移 |
| 加記憶體上限到全部服務 | `[I2]`=C／`S-8`。**注意：CI runner 的可用記憶體與 `192.168.10.10` 不同**，所以兩份 compose 的上限值**不應相同**——這一點必須寫進 `code-generation` 的輸入 |
| 加 `redis` 的 `healthcheck` | `[I3]`=D。（**不加 `ollama` 的**——該 stack 沒有那個服務） |

### 本 intent 還會有另一個 workflow，本單元的改動不得與它相撞

`components.md` 的 External Dependencies 表逐字記載 `MemoryStore` →
**gh-aw／GitHub Actions workflow**：「**90 天逾期清除的承載形式**」。

那是 **`U9 memory-purge`（`kind: packaging`）的交付**，不是本單元的。記在此處的理由：

- 本單元對 `.github/workflows/` 的改動集中在 `deploy.yml`（見 §五 的第 1–3 項），
  **不新增任何 workflow 檔**；`U9` 會新增一個。兩者不衝突，但做一致性比對的人需要知道
  「本 intent 的 workflow 改動不只 `deploy.yml`」。
- `project.md ## Forbidden` 的判準（無人值守的自動化一律以 gh-aw 或 Actions workflow
  承載，**不得**以 repo 內的實作程式承載）對兩者同樣適用。本單元的探測落在純 Actions 步驟、
  符合；`U9` 的清除機制屆時也必須是 workflow 而非 `scripts/` 下的程式。

### 一項仍然 Deferred 的上游衝突（本站不解）

`NFR6.1` **落點 3** 的上游逐字衝突：`requirements.md` 的 NFR6 與 `contract-summary.md` 的
`K-05` `verification.carrier` 兩處把某個 CI job 的 service container 釘成
`postgres:16-alpine`，而 `K-05` 自己的 `embedding vector(1024)` 欄位在該映像上**必然失敗**。

**該 job 是 `U5 memory-data` 的交付**，不是本單元的。本站不回改已核可的上游，只在此重申
它仍未解，並指名承接單元——`U5` 的迭代須就地確認。

---

## 四、Build stages／artifact 管理（本單元不改）

| 面向 | 現況 | 本單元 |
|---|---|---|
| Build | `ci.yml` 的 `docker-build` 以 buildx 建兩個 image、`push: false`；`deploy.yml` 在自架 runner 上 `up -d --build`（就地建） | 不改。**沒有 image registry**——每次部署在主機上重建 |
| Artifact 管理 | 無 registry、無版本標籤。`~/.cloud360/last-good-sha` 是唯一的「已知良好版本」紀錄 | 不改。但 `NFR6.3(b)` 的排序不變量已記載：**回滾取出的 commit 其映像主版本須與當前 PGDATA 相容**——升版窗口內這個假設不成立 |
| 環境晉升 | 沒有晉升鏈。`ut` 合併即部署 staging；**production 不在範圍** | 不改（ADR-0001／ADR-0002／ADR-0008） |
| Feature flags | 無 | 不引入 |
| Rollback | `deploy.yml` 的 `rollback` job：還原 last-good、開 revert PR、dispatch Deploy Doctor | **改它的健康檢查**（見 §二），不改其餘 |

**一項既有的權限現況，如實記載不美化**：`rollback` job 的權限為 `contents: write` ＋
`pull-requests: write` ＋ `actions: write`。`team.md` 已逐字記載這是「刻意放寬（功能需要），
但可否進一步縮窄尚未被評估過」。**本單元新增一個觸發 `rollback` 的條件**（探測失敗），
所以它讓那組權限被觸發的頻率**可能上升**——這一點值得記下，但縮窄該權限不在本單元範圍。

---

## 五、本單元對 CI/CD 的改動清單（給 `code-generation` 的完整輸入）

| # | 檔案 | 改動 | 依據 |
|---|---|---|---|
| 1 | `.github/workflows/deploy.yml` | `deploy` job 新增獨立探測步驟（結束碼表達結果） | `S-6`／`PROBE-CONTRACT` |
| 2 | `.github/workflows/deploy.yml` | `rollback` job 的健康檢查迴圈併入探測（output 表達結果、不用 `exit`） | `S-6`／`[G7]`=A |
| 3 | `.github/workflows/deploy.yml` | `deploy` 與 `rollback` 兩個 job 的 `env:` 對照表**只新增 `REDIS_PASSWORD` 一項**。**其餘六者不進 `env:`**——依 `NFR4.1(c)` 的 `REDIS_USER` 契約（`security-requirements.md:111` 逐字「`render-env.sh` 內的字面值，不進 `deploy.yml` 的 `env:` 對照表……**`NFR8.1` 的 `deploy.yml` 兩處同步因此只涉及 `REDIS_PASSWORD`，不涉及 `REDIS_USER`**」），以及 `render-env.sh:73–90` 的既有形狀（非機敏值一律寫字面量，只有機敏值走 `${NAME}` 由 `env:` 傳入）。**本輪更正（審查 R-40，Critical）**：初版寫「新增七個變數」，照字面實作會讓六個沒有對應 secret 的名字解析為**空字串**並寫進 `deploy/.env`；其中 `EMBEDDING_PROVIDER` 依 `K-01` 是 `required: true`、無預設、偵測不到提供者時**須大聲失敗**，於是 backend 啟動失敗 → deploy 紅燈 → 觸發既有自動 `rollback` ＋ revert PR。同一份清單的第 15 項才剛以「一次短暫不可用會製造一次不必要的回滾」為理由拒絕一律紅燈，這一項卻自己造了一條 | `NFR8.1` ＋ `NFR4.1(c)` |
| 4a | `deploy/render-env.sh:44–49` | 把 `REDIS_PASSWORD` 加入**必填值檢查**。實讀 `:45–46`，現有硬編碼只有 `POSTGRES_PASSWORD` 與 `JWT_SECRET` 兩個名字 | `NFR4.1(a)`。**可測判準**：對空的 `REDIS_PASSWORD` 執行 `render-env.sh` 須**非零退出** |
| 4b | `deploy/render-env.sh:59` | 把 `REDIS_PASSWORD` 加入 **`$` 擋阻名單**。實讀 `:59` 的 `for name in` 固定名單為 `POSTGRES_PASSWORD JWT_SECRET N8N_PASSWORD GCP_BILLING_API_KEY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY`——**六個名字，不含 `REDIS_PASSWORD`** | **`project.md ## Forbidden` 的硬規則**（憑證不得含 `$`：docker compose 會對 `--env-file` 的值做內插，`ab$cd` 被**無聲截斷**成 `ab`，Redis 以遠弱於預期的密碼運行且無任何錯誤——`render-env.sh:52–56` 的註解就是這件事的正文）。**可測判準**：對一個含 `$` 的 `REDIS_PASSWORD` 執行 `render-env.sh` 須**非零退出** |
| 4c | `deploy/render-env.sh` 的 heredoc | 寫出**七個**變數。**其中六個是字面值**（`REDIS_USER`／`EMBEDDING_PROVIDER`／`REDIS_URL`／`OLLAMA_BASE_URL`／`OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL`，比照 `:73–90` 既有的 `POSTGRES_USER=postgres`／`LLM_PROVIDER=openrouter` 形狀），**只有 `REDIS_PASSWORD` 走 `${REDIS_PASSWORD}` 由第 3 項的 `env:` 傳入** | `NFR8.1`／`NFR8.2` |
| 4d | **新增 secret 後的複查義務**（不是檔案改動，是必做步驟） | `REDIS_PASSWORD` 是本單元新增的**憑證型 secret**，故 `project.md ## Mandated` 的複查義務生效：以 `gh api repos/<owner>/<repo>/actions/secrets` 與同路徑的 `/variables` **各查一次**、比對名稱，確認它落在 secrets 而非 variables。本 repo 為 **public**、Actions log 公開可讀，一次意外 echo 即等同公開發布；**若曾誤存為 variable，僅搬移不足以結案，必須重新產生金鑰**（「應該沒人看過」是沒有證據的假設）。判準二元：兩次查詢的結果中，`REDIS_PASSWORD` 須出現在 secrets 清單、且**不得**出現在 variables 清單 | `project.md ## Mandated` ＋ 上游 `security-requirements.md:128–134`。**本輪新增（審查 R-41）** |
| 5 | `deploy/.env.example` | 列出七個新變數 | `NFR8.2` |
| 6 | `deploy/docker-compose.deploy.yml` | `backend.environment:` 七個變數（**不得帶 `:-` fallback**） | `NFR8.1a` |
| 7 | `deploy/docker-compose.deploy.yml` | 新增 `redis`／`ollama` 服務、`networks:` 分段、三個 volume（含 PG volume 改名）、全部服務的 `logging:` 與記憶體上限、兩個新 `healthcheck` | `NFR4.x`／D-3／`S-8`／`S-9`／`[I3]`=D |
| 8 | `deploy/docker-compose.test.yml`（**本 stack 的權威清單：本項 ＋ 第 16b 項，二者合起來即全部**） | `backend.environment:` Redis 三者 ＋ `EMBEDDING_PROVIDER: stub`、新增 `redis`、`networks:` 分段、全部服務的 `logging:` 與記憶體上限（**值與 deploy 不同**）、`redis` 的 `healthcheck`、db 映像改 PG 18 ＋ pgvector、**`redis` 的 ACL 設定資產**（見第 17b 項——`NFR4.1(c)` 的範圍表逐字要求 test stack「**必須有，但不會是同一份檔**」） | `NFR8.1b`／**`NFR4.1(c)`**／`[I5]`=A／D-3／`S-8`／`S-9` |
| 9 | repo 根 `docker-compose.yml` | **只改 db 映像**為 PG 18 ＋ pgvector。**現值為 `postgres:15-alpine`（`:3`），不是 16**（審查 R-45 實測更正）——所以這是 **15 → 18** 跨三個大版本，而該檔 `:13` 掛的是具名 volume `postgres_data`、`:5` 為 `restart: always`：既有 volume 與 PG 18 的資料目錄不相容，容器會進**重啟迴圈**。本 intent 的升版程序（`NFR6.3` 七步）**只涵蓋 deploy stack**，此路徑無任何 CI 閘門，處置寫在第 14 項 | `NFR6.1` 落點 4。**D-3／`S-8`／`S-9` 刻意不適用於它**（它 publish 端口是為了讓開發者直連，那是它存在的目的） |
| 10 | `backend/.env.example` | 列出 backend 讀得到的新變數 | `NFR8.3` |
| 11 | `schema_rbac.sql` | 加 `CREATE EXTENSION IF NOT EXISTS vector;` | `NFR6.2`（**blocking**） |
| 12 | `backend/database.py` | 新增一支 `_ensure_vector_extension()`，**呼叫點在 `create_all()` 之前**。**這是對既有形狀的唯一例外，必須明寫否則實作者會照既有形狀放錯位置**（本輪補查自審）：實讀 `init_db()`（`:74`），`Base.metadata.create_all()` 在 `:76`，而既有**六支** `_ensure_*_schema()` 全在 `:78–83`——即**全部都在 `create_all()` 之後**（該檔 `:507` 的註解逐字說明了那個順序的理由：「`create_all` 不會 ALTER 既有表，因此新欄位在既有環境需要這支補丁」）。新的這一支方向相反：**`vector` 型別必須在任何宣告 `vector` 欄位的表被建立之前存在**，否則 `create_all()` 自己就會以 `type "vector" does not exist` 失敗——而 `init_db()` 由 `backend/main.py` 的 startup 事件同步呼叫，所以那是**啟動失敗**，不是延後修復。**判準二元**：`_ensure_vector_extension()` 的呼叫必須出現在 `create_all()` 那一行之前，不得與其餘六支並列在它之後 | `NFR6.2`／`NFR6.2a` |
| 13 | `DEPLOY.md` | **十一項必寫內容**：(1) 全碟加密前置條件與四個掛載點的檢查方式（祖先鏈含 `crypto_LUKS`／ZFS 替代判準）、(2) 解鎖方式（passphrase vs TPM）與其對斷電自動回復的後果、(3) dump 檔三條要求、(4) 探測（手動升版路徑那一份）、(5) 回退窗口結束時刪舊 volume 並記錄、(6) **磁碟空間的逐掛載點門檻** ＋ `DBSIZE`／`DUMPSIZE` 的量測指令、(7) 記憶體上限的**暫定值與複量期限**（`[I2b]` 本輪已鬆開為「先以公開基準設值、限期複量」，所以記的是暫定值＋期限，複量完成後再補數字與日期）、(8) `max-size`／`max-file` 的值**與總量不超過 2GB 的上界**、(9) `rollback` job 加上探測後的實際耗時、(10) **升版期間暫時提高或移除 `db` 記憶體上限、還原驗證後恢復並記錄「已恢復」**（審查 R-07）、(11) `maxmemory` 的值與其與容器上限的關係式檢查結果 | `NFR8.5` ＋ `S-7`／`S-10`／`[I2b]` ＋ 審查 R-05／R-06／R-07 |
| 14 | `LOCAL-DEV.md` | 依 `NFR8.4`，因 `backend/database.py` 的 schema 補丁與 `.env.example` 改動而必須同步。**另加兩項必寫內容（審查 R-45，本輪新增）**：(1) **本機 PostgreSQL 必須先安裝 pgvector**——`LOCAL-DEV.md:101–102`／`:119–120` 逐字是 `createdb -U postgres -h localhost cloud360` ＋ `psql "postgresql://postgres:postgres@localhost:5432/cloud360" -f schema_rbac.sql`，**本機走的是主機安裝的 PostgreSQL 而非 compose**（該檔對根 `docker-compose.yml` 零命中），而第 11 項要在 `schema_rbac.sql` 加 `CREATE EXTENSION IF NOT EXISTS vector;`，stock 主機 PostgreSQL 無 pgvector 時會以 `extension "vector" is not available` **硬失敗**，本機 bootstrap 第 3 節當場斷掉。須給可執行的前置檢查（例：`psql -c "SELECT * FROM pg_available_extensions WHERE name='vector'"` 須有一列），或改以根 compose 提供 db；(2) **既有 `postgres_data` volume 在 PG 15 → 18 之下不相容**（見第 9 項），寫明處置——移除該 volume 重建，或本機亦走 dump/restore | `NFR8.4`（**blocking**） |

#### ⚠ `DEPLOY.md` 是雙語分段文件，而第 13 項與第 11 項的 blocking 同步都要寫進它（本輪補查自審）

前四輪都沒有對照 `DEPLOY.md` 的**現況**，只驗了第 13 項自身的計數。實讀該檔：它有
**`## 中文版`（`:9`）與 `## English Version`（`:500`）兩個半部**，而英文半部是 **39 行的縮寫版**
（中文半部 490 行），已經不是翻譯而是精簡摘要——換言之**它已經漂移**。

**這製造一個第 13 項沒有回答的問題：十一項必寫內容要寫進哪一半？** 三條路各有代價，
而它們不是實作者可以順手挑的：

| 路 | 代價 |
|---|---|
| (a) 兩半都寫 | 雙份維護。`project.md` 在 TCMS 條款裡逐字寫過這件事的結果——「**雙份維護必有一份悄悄過期**」，而英文半部已經證明了這一點 |
| (b) 只寫中文半部 | 與 `team.md ## Forbidden`（不得保留或新增雙語分段）的方向一致，但**第 11 項觸發的 blocking 同步在字面上涵蓋英文半部**：`project.md ## Mandated` 要求更新「這支 SQL 會建立的表／欄位」表，而英文 `### Database`（`:524` 起）**正是在列那份清單** |
| (c) 移除英文半部 | 方向最乾淨，但 `DEPLOY.md` 是 **repo 根目錄文件**，不在 ADR-0009 列舉的強制範圍內（該條列舉的是 `aidlc/spaces/*/intents/**/*.md`、`CLAUDE.md`、`team.md`、`project.md`），且 `validate_repo_contract.py` 的語言檢查**刻意只掃 record 內**——所以移除它是一個 repo 級的文件決定，**不是本單元的範圍** |

**本單元的處置**：採 **(b)**，並把缺口顯性化而非吸收掉——

1. 十一項**運維必寫內容**只寫進**中文半部**（它們是操作細節，英文縮寫版從未涵蓋同級細節）。
2. **第 11 項的 blocking 同步例外處理**：`CREATE EXTENSION IF NOT EXISTS vector;` 屬「這支 SQL
   會建立的物件」，故**中文 `### 2.` 與英文 `### Database` 兩處都要補一行**——這一項是
   blocking 規則的字面要求，不適用 (b) 的簡化。這是唯一要寫兩半的項目。
3. **英文半部的既存漏洞不由本單元擴大、也不由本單元修補**，並記為 open item：它今天就已經
   缺了中文半部 490 行裡的大部分內容，本單元不製造新的落差，但也**不宣稱它是同步的**。
4. **指派**：「`DEPLOY.md` 要不要移除英文半部」需一個 repo 級決定（ADR 或使用者裁決），
   落點不在本 stage。**本站不代它決定**，只記錄這個決定尚未做、以及在它做出之前第 2 點是
   唯一的 blocking 例外。

**第 12 與第 11 項是 blocking 規則的落點**（`project.md ## Mandated` 的 schema／deploy
同步條款），第 14 項同樣是 blocking。

### 漏列的三項，本輪補入（審查 R-08 的清單完整性檢查）

| # | 檔案 | 改動 | 依據 |
|---|---|---|---|
| 15 | `.github/workflows/deploy.yml` | **部署後執行一次 `ollama pull bge-m3`**，三項規格如下（審查 R-19）：**(a) 執行方式**——在 `ollama` 容器內執行（`docker compose exec` 型（**該步驟跑在自架 runner 上、無 TTY，所以必須以非互動形式執行**：`docker compose exec -T`；少了 `-T` 會以 `the input device is not a TTY` 失敗——審查 R-30 的第二半）），**不得**用 host 端 HTTP，因為 `infrastructure-specification.md` `§五` 的 ADR-0006 Network exposure 列逐字「唯一有 host port 的服務仍是 `frontend`」，host 打不到 `ollama`；**(b) 位置**——在 `up -d` 之後、**在 `S-6` 的探測步驟之前**（兩者無資料相依，探測打 `/api/auth/login` 不碰 embedding，但寫死一個順序以消除歧義，並讓「模型沒有就緒」比「資料面不通」更早被發現）；**(c) registry 不可達的語意**——若模型**已在 volume** 而 registry 短暫不可達，**不得讓部署紅燈** | **審查 R-02（Critical）**——官方 `ollama/ollama` 映像啟動**不會**自動拉模型，缺這一步則 `/api/tags` 永久回空清單、healthcheck 恆為健康且恆無模型、`NFR9.1` 執行期靜默失守。機制的選擇理由見 `infrastructure-specification.md` `§二`；(c) 的理由見下方專節 |
| 16a | `deploy/docker-compose.deploy.yml` | `redis` 與 `ollama` **兩者**的 `restart: unless-stopped` ＋ **兩條 `depends_on`**（`backend` → `redis` 用 `service_healthy`、`backend` → `ollama` 用 `service_started`） | **審查 R-13b／R-04** |
| 16b | `deploy/docker-compose.test.yml` | **只有 `redis`** 的 `restart: unless-stopped` ＋ **只有一條** `depends_on`（`backend` → `redis`，`service_healthy`）。**`backend` → `ollama` 不適用**——依 `[I5]`=A 該 stack 沒有 `ollama` 服務（同檔 `§三` 的表格逐字「該 stack 沒有那個服務」） | **審查 R-16（Critical）**——初版第 16 項把兩個 stack 併成一列、逐字寫「兩個新服務」與兩條邊，**照字面對 test.yml 寫 `backend depends_on ollama` 會是 compose 的 undefined-service config error，`ui-regression` 每個 PR 全紅**。與 R-03 同形：兩份 compose 的服務集合不同 |
| 17a | `deploy/docker-compose.deploy.yml` | `redis` 的 **`command:` 覆寫**承載 **`appendonly yes`** ＋ `maxmemory` ＋ `maxmemory-policy allkeys-lru`（一條 `command:`，三個旗標）。`appendonly` 是**送審前自檢第 2 項**查出的無寫者項：映像預設 `appendonly no`，不明寫則 `NFR4.2` 靜默失守而 healthcheck 照樣過 | **審查 R-05** ＋ **自檢第 2 項**——`[I1]`=A 與 `[I2b]` 對「值住哪裡」指向相反方向，本輪定案為 `command:`，使它與容器上限在同一個服務區塊內可對照 |
| 17b | **兩份 compose 各自的 `redis` ACL 設定資產** | **`NFR4.1(c)` 的 ACL 使用者必須被建立，而 Redis 容器預設不讀任何專案設定。**承載形式二擇一（上游 `security-requirements.md:80` 逐字）：**掛載的 Redis 設定資產**（`redis.conf`／`users.acl`，**兩份 compose 各自一份**），或 **compose 的 `command:` 覆寫**（`ACL SETUSER`，由 compose 逐 stack 內插）。**兩份 compose 都必須有**。**兩份不得共用同一份檔**——上游 `:95` 的理由是 `redis.conf`／`aclfile` **不內插環境變數**而 ACL 把密碼綁在 user 那一行，共用只有兩種收法：把部署憑證寫成 repo 內字面值（**等於把部署憑證放進 public repo**，牴觸 `NFR4.1(a)` 與 `project.md ## Forbidden`），或讓 test 用 deploy 的真憑證——**兩者都不可接受**。test stack 的值依該 stack 既有慣例**內嵌自帶測試用預設值**（與 `JWT_SECRET` 同形）。**若 test stack 沒有 ACL 使用者，兩條路都死**：用非 `default` 使用者會 `WRONGPASS`、用 `default` 被 `NFR4.1(c)` 擋下，結果是**每個 PR 的 `ui-regression` 都紅**（上游 `:95` 逐字） | `NFR4.1(c)`（**本輪新增，審查 R-38，Critical**——前四輪四份產出對 `users.acl`／`REDIS_USER`／`ACL SETUSER`／`--user` 的命中數皆為 **0**） |

**清單總數：原始十四項 → 本輪為 22 列**（編號 `1, 2, 3, 4a, 4b, 4c, 4d, 5–15, 16a, 16b, 17a, 17b`；實算而非估計）。三次拆分的由來：第 16 項拆為 **16a／16b**（審查 R-16，兩份 compose 的 `depends_on` 不同，併成一列會讓 test stack 落地即紅燈）；第 4 項拆為 **4a／4b／4c ＋ 新增 4d**（審查 R-39／R-41，上游 `security-requirements.md:118–123` 的 `render-env.sh` 擴充表有**三列**而初版只承接了 heredoc 那一列，4d 是新增 secret 的 `gh api` 複查義務）；第 17 項拆為 **17a／17b**（審查 R-38，ACL 設定資產是兩份 compose 都必須有的獨立承載，不能混在 deploy 的 `command:` 那一列裡）。

#### `ollama pull` 的「冪等」宣稱過寬，以及 registry 不可達該不該紅燈（審查 R-19(c)）

**初版寫「冪等——模型已存在時是 no-op」，那不準確**：`ollama pull` 在模型已存在時**仍會連
registry 比對 manifest**，registry 不可達即失敗。配合本項自訂的「失敗讓部署紅燈」與既有的
自動 `rollback` ＋ revert PR，**上游 registry 一次短暫不可用，會把一次正常合併變成自動回滾
加一個 revert PR**——即使模型早就在 volume 裡、服務其實完全可用。

**定案：分兩種情形，不可一律紅燈。**

| 情形 | 判定 | 理由 |
|---|---|---|
| **模型不在 volume**，且 pull 失敗 | **紅燈** | 服務真的不可用——`/api/tags` 會是空清單，embedding 整條壞掉。這正是 R-02 要防的 |
| **模型已在 volume**，但 pull 因 registry 不可達而失敗 | **不紅燈，記 warning** | 服務可用，紅燈只會製造一次不必要的回滾與 revert PR。**而這一次例外是安全的**，因為「模型在不在」有一個獨立可查的事實來源：`/api/tags` 的回應內容（非空即代表模型在） |

**所以該步驟的形狀是**：先查 `/api/tags` 是否已含 `bge-m3` → 若有，pull 失敗只記 warning；
若無，pull 失敗即紅燈。**這也讓 `/api/tags` 第一次有了一個它真正適合的用途**——它不適合當
healthcheck（無模型時回空清單而非錯誤，`monitoring-design.md` `§六` 已記載），但**正適合當
「模型在不在」的判定**，因為那正是它回報的東西。

#### ⚠ 這個分支在本 repo 的 shell 慣例下寫不出來，除非明寫容錯（審查 R-30）

**`.github/workflows/deploy.yml` 的多行 `run:` 區塊一律以 `set -euo pipefail` 開頭**（實數 16 個 `run:` 中 **13 個**帶它；三個例外 `:105` `bash deploy/render-env.sh`、`:152` `rm -f deploy/.env`、`:156` 的 Summary 皆為單行或非判定指令——審查 R-46 更正初版的全稱句「每一個」），而上述
判定**要求兩個命令的非零結束碼被容忍**：

| 命令 | 為何會非零 | 在 `set -e` 下的後果 |
|---|---|---|
| 查 `/api/tags` 的那一次呼叫 | 模型不在時它**不會**非零（回 200 ＋ 空清單），但**容器還沒起來或網段打錯時會**非零 | 步驟當場中止，**判定分支永遠不會被執行**，所以「分兩種情形」的設計語意被反轉成「任何異常都紅燈」 |
| `ollama pull` | registry 不可達時非零——**而那正是我們決定不一定要紅燈的情形** | 步驟當場中止並以 pull 的結束碼失敗，warning 分支永遠走不到 |

**這是 `nfr-design` 的審查 R-24 原樣重現**（那裡是 `code=$(curl …)` 在 `set -e` 下中止整步，
實測 `exit=7`、零迭代訊息）。**同一個陷阱在本 stage 第二次出現，所以必須寫成契約而不是
寄望實作者想到。**

**契約（比照 `PROBE-CONTRACT` 的 `P-5`）**：本步驟的兩個判定命令**都必須以不觸發 `set -e`
的形式取值**（條件位置判定，或顯式容錯取值），且步驟的最終結束碼**必須由判定邏輯決定**，
不得由任一中間命令的結束碼直接決定。**具體寫法留 `code-generation`**——本檔不給 shell，
理由同本檔開頭「這份檔在做什麼」段（`:10–11`）；但**這條約束不寫下來，實作者必然踩**。

**給 `code-generation` 的輸入（`[I2b]` 本輪已鬆開，見 `infrastructure-specification.md`
`§二`）**：記憶體上限**不再阻塞** `code-generation`。它依公開基準產出可部署的值，並在
compose 註解與 `DEPLOY.md` 標記為**暫定、未量測**。**CI test stack 的值另循一條路**——由
`ubuntu-latest` 的公開規格推導，不適用主機量測程序（實測起 test compose 的是
`ui-regression.lock.yml:384` 的 job，`runs-on: ubuntu-latest`）。

---

## Assumptions & Open Questions

- **`rollback` job 加上探測後的實際耗時未知**，而它的 `timeout-minutes` 是 20 且內含另外
  兩個迴圈。實作時須實測；若逼近上限，縮短窗口或提高逾時**都是需要決定的事** [assumption]
- **記憶體上限以公開基準設暫定值，尚未量測**。`[I2b]` 已反轉，**它不再是 `code-generation`
  的前置條件**（初版此處逐字寫「是前置條件」，與同檔 `§五` 的「不再阻塞」相隔十一行直接
  對撞——審查 R-15）。剩餘不確定性是暫定值的準確度與複量期限的擁有者 [assumption]
- **首次 `ollama pull` 的耗時未實測**。它影響的是**部署步驟的耗時**（含 `deploy` job 的
  30 分鐘逾時餘裕），**不是** `healthcheck` 的 `start_period`——後者在本輪已確認與下載無關
  [assumption]
- **兩份 compose 的記憶體上限值必然不同**（CI runner 與 `192.168.10.10` 的可用記憶體不同），
  所以「兩份 compose 保持一致」這個原則在**這一項上例外**——必須明寫，否則下一個做一致性
  比對的人會把它當成漂移 [assumption]
- **`NFR6.1` 落點 3 的上游逐字衝突仍未解**，承接單元為 `U5 memory-data` [assumption]
（**原本留在此處的一項假設已實地查證，結論移入 §一 的表格**：`ci.yml` 的 `docker-build`
確定**不需改動**——它只有兩個步驟，`context: ./backend` 與 `context: ./frontend`，都是
`push: false` 的純建置驗證；新增的 `redis`／`ollama` 用官方映像、不經 Dockerfile，所以
不在它的作用域內。該 job 的註解逐字說明了它的目的：「Build only — the deploy job on the
self-hosted runner is what actually ships. This exists so a broken Dockerfile fails the
PR, not the deploy.」）
