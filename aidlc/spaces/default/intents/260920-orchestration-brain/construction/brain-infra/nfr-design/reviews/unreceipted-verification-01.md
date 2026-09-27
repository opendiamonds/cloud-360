# 未收據驗證 — R-18…R-23 的修法

> 本輪不是正式審查迭代：`nfr-design` 的 `reviewer_max_iterations: 2` 已用完，
> 引擎拒絕第三輪，故本檔**不是收據**、不進 `.aidlc-engine/reviews/`。
> 使用者在知情下要求執行，目的是抓缺陷而非取得收據。

**Reviewer:** aidlc-architecture-reviewer-agent
**判定:** 有發現
**Date:** 2026-09-27T02:49:44Z
**範圍:** 只驗 `R-18`…`R-23` 六項的修法；R-01…R-17 不重審。新發現自 `R-24` 起編。

## 發現

| ID | Severity | Location | Finding | Required action |
|---|---|---|---|---|
| R-24 | Major | `security-design.md` > 一 > D-3 > 「探測必須有有界重試」的 `bash` 片段（line 441–453） | **那段片段在本 repo 的既有 shell 慣例下會在第一次 `curl` 層級失敗時整步中止，重試迴圈形同不存在。** `deploy.yml` 的三個同類步驟逐字都以 `set -euo pipefail` 開頭（`:114`、`:129`、`:208`），而片段第 443 行是 `code=$(curl …)`——**賦值語句的結束狀態就是命令替換的結束狀態**，`curl` 因 `--max-time 15` 逾時（28）或連線被拒（7）時，`set -e` 立即終止該步驟：不重試、不執行第 451 行的 `last code` 診斷輸出、步驟結束碼是 28 而非 1。我以等價腳本實跑複驗（見「查證結果」§1），輸出為零次迭代訊息、`exit 28`。既有兩道檢查之所以沒有這個問題，是因為它們把 `curl` 放在 `if curl …; then` 的**條件位置**（`:116`、`:130`），那個位置被 `set -e` 豁免——所以「與既有兩道檢查同形」這句話在最關鍵的一點上不成立。後果正是 R-18 要防的那一個：一次短暫的連線層失敗 → 步驟紅燈 → `rollback` job → 對沒問題的合併開 revert PR | 在片段中把取值改為不讓 `set -e` 觸發的形式（`code=$(curl … || true)`，或整段改成 `if`／`case` 判定），並在片段旁寫明理由：「`set -euo pipefail` 下 `code=$(curl …)` 會讓 `curl` 的非零結束碼直接終止步驟，故必須 `|| true`」。同時修掉「30 × 5s 與既有兩道檢查同形」這句——形狀差異正在取值位置 |
| R-25 | Minor | `security-design.md` line 397、line 456–457；`traceability.json` > `PROBE-API-DB`／`SCOPE-DEPLOY-YML-PROBE` 的「30 × 5s」 | **窗口長度寫成「30 × 5s」，但實際上界是 30 ×（15 ＋ 5）＝ 600 秒**：每次迭代的 `--max-time 15` 也算在牆鐘時間裡。這使同一份檔的兩句話互相拉扯——line 397 拿「單次探測可能耗十分鐘」當逾時參數的存在理由，而加了迴圈之後**整步**的上界又回到十分鐘（修掉 R-24 之後才會真的跑滿）。這一點有預算意義：`deploy` job `timeout-minutes: 30`（`:28`）、`rollback` job `timeout-minutes: 20`（`:177`），而該 job 內還有 `up -d --build`＋8090 迴圈（≤150s）＋tunnel 迴圈（≤120s） | 把窗口寫成「最多 30 次、每次至多 15 秒請求 ＋ 5 秒間隔，牆鐘上界 ≈ 10 分鐘；成功路徑通常在數秒內結束」，並就地寫明它與兩個 job 的 `timeout-minutes` 的關係（真斷線時紅燈延遲上界即 10 分鐘） |
| R-26 | Minor | `security-design.md` line 457 | 「**`init_db()` 每新增一個 `_ensure_*_schema` 補丁，這個窗口就要重新評估**」是一條**沒有承載者**的要求——沒有指名誰會被提醒、也沒有任何機械觸發。這正是本 repo 已記載的「規則宣稱強度高於機制」形狀。而承載者其實現成：`local-dev-drift` 的觸發路徑已含 `backend/database.py`（`.github/workflows/local-dev-drift.md:8`、`local-dev-drift.lock.yml:57`），且 `project.md ## Mandated` 對 `backend/database.py` 的 schema 補丁已有 blocking 同步條款 | 指名承載者：在該句補上「本條的提醒機制掛在 `local-dev-drift` 既有的 `backend/database.py` 觸發路徑上（非阻擋），且屬 `project.md` 對該檔 schema 補丁的既有 blocking 同步範圍」；若判定不掛任何機制，改寫為「本條目前無承載機制，屬已知落差」 |
| R-27 | Minor | `security-design.md` line 473–482（失敗分類表與其前言） | **在 D-3 最主要的失敗模式下，觀察到的代碼是 `502` 而不是 `504`，而分類表會把診斷指向 `backend` 容器本身、離開真正的原因（網段歸屬）。** 逐項證據：`backend/database.py:76` 的 `Base.metadata.create_all(bind=engine)` 與 `:78–83` 的六個補丁**都在 `:86` 的 `try:` 之外**（`try` 只包住 `:85` 之後的 session 工作），故 `backend`→`db` 被網段規則丟包時 `create_all` 會在 TCP SYN 逾時後拋出 → `@app.on_event("startup")`（`backend/main.py:46–50`）失敗 → uvicorn 不進入服務狀態 → `restart: unless-stopped`（`docker-compose.deploy.yml:32`）反覆重啟 → nginx 取不到上游 → **整個探測窗口都是 502**。所以 line 474 的「網段打錯的最常見表現正好是 504」對 `backend`→`db` 這一段不成立（對 `backend`→`redis`／`ollama` 才成立，因為那兩段不在 startup 路徑上）。與 R-20 同一形狀：閘門照樣紅燈，錯的是診斷方向 | 把 `502` 那一列改為「`backend` 容器不可達或未監聽——**含 `backend`→`db` 在 startup 期間就斷掉的情形**（`database.py:76` 的 `create_all` 在 `:86` 的 try 之外，例外會讓 startup 失敗並進入重啟迴圈）」，並把 line 474 的「最常見表現是 504」收窄為「`backend`→`redis`／`ollama` 的斷線表現為 504；`backend`→`db` 的斷線表現為 502」 |
| R-28 | Major | `security-design.md` line 416（`rollback` 落點列）；`traceability.json` > `SCOPE-DEPLOY-YML-PROBE` 的「兩處皆須有界重試（30 × 5s，出現 401 即通過），失敗讓 job 紅燈」 | **`[G7]`=A 的落點只寫了「加進 `:229–236` 的健康檢查迴圈」，沒寫要改成什麼形狀——而該迴圈與 `deploy` job 的 `exit 0`／`exit 1` 形狀不相容，照字面實作會壞掉既有輸出契約。** 逐項證據：(1) `:229–236` 位於 `Restore the last-good deployment` **同一個步驟內**（該步驟 `:208` 亦為 `set -euo pipefail`），迴圈是 `RESTORED=unhealthy` → 成功則 `RESTORED=healthy; break` → **迴圈之後**在 `:237` 寫 `echo "restored=${RESTORED}" >> "$GITHUB_OUTPUT"`；(2) 該步驟今天**永遠不會因健康檢查失敗而紅燈**——它把結果放在 output 裡而不是結束碼裡，所以「失敗讓 job 紅燈」這條指示在 `rollback` 這一半改變了既有行為，而設計沒有說要不要改；(3) 若照 `deploy` 那段片段的寫法把 `code=$(curl …)` 放進去，在 `set -e` 下第一次 `curl` 層級失敗即中止該步驟，**`:237` 永遠不會執行** → `restored` 為空 → `notify` 的 `case "${RESTORED}"`（`:381–386`，只認 `healthy`／`unhealthy`／`none`）落到 wildcard，Slack 印「回滾: 結果未知」，探測的真實結論就此遺失；(4) 若改為新增第三種狀態（例如資料面不健康），則 `:381–386` 的 `case` 必須同步加分支，否則同樣落到「結果未知」。整段是一個實作者必然要猜的空白，而四種猜法的可觀察後果各不相同 | 在該落點列明寫 rollback 那一半的形狀，二擇一並寫明後果：(a) **併入既有迴圈的成功條件**——`/` 與 `/api/auth/login` 兩者皆通才 `RESTORED=healthy; break`，不使用 `exit`，`:237` 照舊唯一寫入，`notify` 的 `case` 不需改動（資料面壞掉時報「已嘗試還原，但服務仍未恢復」，granularity 較粗）；或 (b) **新增第三種狀態**（如 `unhealthy-dataplane`），則同一個 PR 必須一併補 `deploy.yml:381–386` 的 `case` 分支。兩種寫法都必須註明「此步驟以 `$GITHUB_OUTPUT` 而非結束碼表達結果，故 `deploy` job 那段的 `exit 0`／`exit 1` 不可原樣搬過來」，並套用 R-24 的 `|| true` |

## 逐項驗證

### R-18（Major，唯一的真設計問題）— 修法方向正確，片段本身有 bug

**已修對的部分**，逐字引用：

- line 415 落點列首欄逐字為「`deploy.yml` 的**獨立新步驟**（在 `Wait for the frontend to answer locally` 步驟**之後**，**不是**加進該步驟的迴圈內）」，且 line 435–437 把上一版的錯誤就地記載：「初版寫『……即 `:116` 那一段之下』，而 `:116` 在迴圈內、`:118` 就 `exit 0`——照字面加在那裡是**永不執行的死碼**」。**指向 `:116` 的落點字樣已不存在於落點表**（全檔 `:116` 的三處命中皆為引用該行內容的舉證，非落點指示）。
- line 424–429 的四列時序舉證我逐一開檔複驗**全部成立**：`deploy/docker-compose.deploy.yml:77–78` 逐字為 `depends_on:` ／ `- backend`（無 `condition:`）✅；`.github/workflows/deploy.yml:112–125` 為 30 × 5s 迴圈、`:116` 是 `curl -fsS -o /dev/null http://127.0.0.1:8090/`、`:118` 是 `exit 0` ✅；`backend/main.py:46–50` 為 `@app.on_event("startup")` 同步呼叫 `configure_provider_env()` 與 `init_db()` ✅；`backend/database.py:74–83` 為 `def init_db():` ＋ `Base.metadata.create_all(bind=engine)` ＋ 六個 `_ensure_*_schema()`（`a4`／`j5`／`a3`／`cost`／`estimate_intake`／`last_activity`）✅。
- `deploy.yml:169–175` 的 rollback 觸發條件逐字為 `failure() && needs.deploy.result == 'failure' && github.event_name == 'pull_request' && github.event.pull_request.merged == true` ✅，`:229–236`、`:249–282`、`:284–295` 皆如上一輪所述 ✅。

**(a) 片段自身的獨立分析** — 三個子問題分開回答：

1. **`code` 在迴圈外的 `echo` 是否一定有值**：只要迴圈體完成過一次賦值就有值，`$(seq 1 30)` 非空故正常路徑下不會是未定義（`set -u` 亦安全）。**真正的問題不是未定義，是那一行在 `curl` 層級失敗時根本到不了**——見下一點。
2. **`curl` 逾時回 `000` 時的行為**：`[ "$code" = "401" ]` 不會被執行到。`code=$(curl …)` 這個賦值的結束狀態即 `curl` 的 28，`set -e` 當場終止步驟。**這是 R-24，Major**。
3. **`&& { …; exit 0; }` 在 `set -e` 下的行為**：**沒有問題**，實跑複驗 `set -euo pipefail; [ a = b ] && { echo yes; exit 0; }; echo survived-and-list` 輸出 `survived-and-list`、`exit=0`——`&&` 的左運算元被 `set -e` 豁免。此處不構成發現。

**(b) 30 × 5s 是否足夠涵蓋 `init_db()`** — **足夠，且相當寬裕**。六個補丁的實際內容我逐一讀過（`database.py:185`／`:213`／`:260`／`:330`／`:386`／`:504`）：清一色 `ALTER TABLE users ADD COLUMN IF NOT EXISTS`、`CREATE TABLE IF NOT EXISTS`、四組 `RENAME`（C1 退場）與一條對 `users` 的 `UPDATE`——全部是目錄層級操作，在 `users` 這種數十列的表上是毫秒級；`create_all` 是 metadata 反射。唯一有實質成本的是**首次開機**：`:88–120` 的 11 位 persona ＋ bootstrap admin 各跑一次 `bcrypt.gensalt()`（預設 12 rounds，約 0.2–0.4 秒）≈ 數秒，再加 `ensure_role_permissions_seeded`（`:157`）的一次性 seed。另外 `backend.depends_on: db.condition: service_healthy`（`docker-compose.deploy.yml:63–65`）保證 backend 根本不會在 `pg_isready` 之前啟動。**150 秒對這個窗口是數十倍餘裕**；真正該修的是窗口長度的**表述**（R-25），不是次數。

**(c) 重試會不會掩蓋真斷線** — 會延遲，但仍在預算內；問題是設計沒把這個代價寫出來。修掉 R-24 之後，一次「網段打錯」的部署要到 ≈10 分鐘後才紅燈（每次迭代 15 秒逾時 ＋ 5 秒間隔）。`deploy` job 的 `timeout-minutes: 30` 尚可容納（`up -d --build` ＋ 150s ＋ 120s ＋ 600s），`rollback` 的 `timeout-minutes: 20` 亦可，但兩者都變窄。歸入 R-25。

**(d) 「每新增一個補丁就重評窗口」的承載者** — **沒有**。見 R-26；而現成的承載者（`local-dev-drift` 對 `backend/database.py` 的既有觸發）設計未指名。

### R-19（Major）— Resolved

`traceability.json` 的 `NFR4.1` 現逐字為「D-3 把可連到 Redis 的容器**由 5 個縮到 3 個（backend／db／ollama）**……**但 internal 內部不隔離（user-defined bridge 預設 enable_icc 為 true），故暴露面縮小而未縮到單一容器**」，並就地記載「初版寫『由 4 個縮到 1 個（backend）』，與同檔 NFR8.7 直接對撞」。與 `NFR8.7` 的「真實變化 5 → 3」一致 ✅。

### R-20（Minor）— Resolved

`PROBE-API-DB` 現逐字為「**失敗分類以 security-design.md 的分類表為準**（500／504／curl 逾時 000 同屬資料面不可達；502 為 backend 容器不可達或未監聽；回 HTML 為 /api/ 路由或 frontend→backend 斷）」，被自己指名為錯的舊括號已不存在於依據句中（僅以「初版此處的括號原樣留著……本輪更正」的歷史敘述形式出現）✅。
殘留 grep（兩檔）：`4 個縮到 1`／`由 4 個`／`縮到 1 個`／`只有 backend`／`502／504 = backend` 的命中**全部落在明示為「初版……本輪更正」的歷史敘述內**，無一處是現行主張；唯一的例外是 `security-design.md:261` 的 compose 註解「`internal:   # 資料面：只有 backend 與它依賴的後端服務」——語意正確（描述網段成員的組成原則），非計數殘留 ✅。

### R-21（Minor）— Resolved

`security-design.md:31` 的新措辭逐字為「而那指的是**兩個 job 的 `env:` 對照表**（該條的表格逐字列出 `deploy` → `:90–104`、`rollback` → `Restore the last-good deployment` 步驟的 `env:`，並明寫「兩個 job 的改動不對稱」、`rollback` **沒有**等價的 required-secrets 守門）」。回 `nfr-requirements/security-requirements.md` 逐字核對：`:475` 標題為「`NFR8.1` — 七個變數由 `render-env.sh` 寫入，且 `deploy.yml` 兩處同步」；`:489` 逐字為「**兩個 job 的改動不對稱（本輪更正初版的「兩個 job 都要改兩項」）**」；`:491–494` 的表格逐字列 `deploy` → `env:` 對照表「要加（`:90–104`）」、`rollback` → 「要加（`Restore the last-good deployment` 步驟，`env:` 在 `:193`、條目到 `:206`）」、`rollback` 的 required-secrets 欄逐字為「**不存在**——該 job 沒有等價的缺值守門」。**四項引用逐字成立** ✅。並已就地記明「初版把 `NFR8.1` 轉述為『兩個 job 都要呼叫 `render-env.sh`』——那是 `project.md ## Mandated` 的另一條規則」✅。

### R-22（Minor，`[G7]`=A）— **未完全 Resolved**

落點已加入（line 416、`SCOPE-DEPLOY-YML-PROBE`、`§四` line 620–624 三處一致），**方向正確**；但**形狀留白，而該迴圈的形狀與 `deploy` job 不相容**，見 R-28。另附一項已查證、不另立發現的事實：`restored` 的下游消費者只有兩處（`deploy.yml:183` 的 job output 與 `:333` 的 `notify` env），而 `notify` 的 `case`（`:381–386`）只認三個值；`Capture the failing deploy log`（`:240`）、`Open a revert PR`（`:251`）、`Hand the failure to the Deploy Doctor agent`（`:285`）皆為 `if: always()`，故即使 restore 步驟中止，自癒鏈本身不會斷——只有 Slack 的回滾結論會變成「結果未知」。

### R-23（Minor）— Resolved（技術主張成立）

line 358–361 的兩列表把兩者分開：`internal` 內部再分段判「**可行，但不在本站範圍**」並保留「2 → 4 個網段」的成本；關閉 ICC 判「**不可行——不是『未採用』**」，理由逐字為「它對 user-defined bridge 的語意是**該網段內全部容器間流量一律 DROP**，沒有 per-pair 例外（`--link` 的放行只存在於舊的 default bridge）……**不是把數字壓到 1，是壓到 0 並讓整個 stack 失能**」，並註明「『2 → 4 個網段』那個成本說明也只對上一列成立」。

**我對這個技術主張的判定：成立，敘述強度恰當，不過強也不過弱。** `com.docker.network.bridge.enable_icc` 是 bridge driver option，設為 `false` 時該網段上的容器間流量一律被丟棄，且 user-defined bridge **沒有** per-pair 放行機制（`--link` 的 ICC 例外是 legacy default bridge 專屬）；DNS 解析與出向 NAT 不受影響，這正好使它的失敗模式是「名字解得到、連不上」——與本檔對 DROP 型失敗的描述一致。`backend` 需要連 `db`／`redis`／`ollama` 三者，故該網段一旦關閉 ICC 即全斷，「壓到 0 並讓 stack 失能」為真。**未實測**：本環境無執行中的 Docker daemon，此判定依 Docker 的 bridge driver 語意推導，與上一輪相同（如實記載）。

## 查證結果

### 1. `bash` 片段的獨立分析（實跑，非推導）

以與片段同形、把 `curl` 換成「印 `000` 並回 28」的替身，在 `set -euo pipefail` 下實跑：

- 結果：**零次迭代訊息、零次 `last code` 診斷輸出、步驟結束碼 28**——迴圈在第一次賦值就死。
- 對照組一：`set -euo pipefail; [ a = b ] && { echo yes; exit 0; }; echo survived-and-list` → 輸出 `survived-and-list`、`exit=0`（`&&` 左運算元豁免，**不是** bug）。
- 對照：`deploy.yml` 既有兩道檢查把 `curl` 放在 `if` 條件位置（`:116`、`:130`），因此不受影響——**形狀差異就在這裡**。

### 2. 行號引用逐字核對（本輪新增者全查）

| 引用 | 逐字內容 | 判定 |
|---|---|---|
| `deploy/docker-compose.deploy.yml:77–78` | `depends_on:` ／ `- backend`（frontend 之下，無 `condition:`） | ✅ |
| `.github/workflows/deploy.yml:112–125` | `Wait for the frontend to answer locally` 步驟；`:114` `set -euo pipefail`、`:115` `for _ in $(seq 1 30)`、`:116` `if curl -fsS -o /dev/null http://127.0.0.1:8090/; then`、`:118` `exit 0`、`:120` `sleep 5`、`:125` `exit 1` | ✅ |
| `deploy.yml:118` | `exit 0`（在迴圈內） | ✅ |
| `deploy.yml:169–175` | `rollback:` ／ `needs: deploy` ／ `if: failure() && needs.deploy.result == 'failure' && github.event_name == 'pull_request' && github.event.pull_request.merged == true` | ✅ |
| `deploy.yml:229–236` | `for _ in $(seq 1 30)` → `if curl -fsS -o /dev/null http://127.0.0.1:8090/` → `RESTORED=healthy` ＋ `break`；`:237` 才寫 `$GITHUB_OUTPUT` | ✅（形狀與 deploy job 不同，見 R-28） |
| `backend/main.py:46–50` | `@app.on_event("startup")` ／ `def on_startup():` ／ `configure_provider_env()` ／ `init_db()` | ✅ |
| `backend/database.py:74–83` | `def init_db():`、`:76` `create_all`、`:78–83` 六個 `_ensure_*_schema()` | ✅ |
| `contract-summary.md:1424`（在 `inception/contract-design/` 之下） | `K-05` ／ `OQ-3`：episodic memory 的加密手段 ／ `U5` ／ `nfr-design`（CONDITIONAL…） | ✅ |
| `nfr-requirements/security-requirements.md` `NFR8.1`（`:475`、`:489`、`:491–494`） | 見上「R-21」逐字 | ✅ |
| `local-dev-drift`（R-26 的承載者候選） | `local-dev-drift.md:8` 與 `local-dev-drift.lock.yml:57` 皆列 `backend/database.py` | ✅（設計未引用，見 R-26） |

**位移影響**：本檔的行號引用全部指向 repo 檔案或上游 artifact，無任何指向本檔自身行號者，故本輪的內容增補對引用零影響（逐一開檔比對）。

### 3. 計數實算（`python3` / `grep` 實跑）

- `traceability.json`：`json.load` 成功；`upstream_ids` **20**、`coverage` **20**、**集合相等**、兩側皆無重複 ✅。
- status 分佈：`Counter({'OK': 10, 'N/A': 10})` ✅。
- `reverse` **10** 項：`D-1`／`D-2`／`D-3`／`D-4`／`IAM-PG-SUPERUSER`／`AUDIT-CORRELATION-ID`／`PROBE-API-DB`／`SCOPE-DEPLOY-YML-PROBE`／`SCOPE-DEPLOY-MD-FDE`／`TENSION-DISK-UNLOCK` ✅。
- 三落點表（line 413–417）**3 列** ✅；ICC 可行性表（line 358–361）**2 列** ✅；FDE 掛載點表（line 116–121）**4 列** ✅ 且 line 125 逐字寫「必須**逐一列出**這四個檢查對象」，數字與表一致 ✅；`§〇` **2 列**（`S-6`／`S-7`）且與 `reverse` 的兩個 `SCOPE-*` 一一對應 ✅；`§四` 的「剩下真的沒有閘門的」清單 **5 項**，全檔無指向它的舊計數 ✅。

### 4. sensor 自行重跑（三支）

| Sensor | fire_id | 結果 |
|---|---|---|
| `required-sections`（`security-design.md`） | `a95938fe` | `passed` |
| `upstream-coverage`（`security-design.md`） | `a7b6659b` | `passed` |
| `traceability`（`traceability.json`） | `727dd58a` | `passed` |

三支皆通過。但它們只驗結構：R-24…R-28 全部在語意層，sensor 抓不到。

### 5. 同一份檔內是否自相矛盾

- **`§四`（「一項本輪由無閘門變成有閘門」）vs `§〇`（`S-6` 是新增工作量）**：**不矛盾**。前者陳述「照本設計實作之後的閘門狀態」，後者陳述「誰承擔這份工作、範圍誰回補」，且兩節互相指引（`§四` line 620 註明來源為 R-16 ＋ R-22、`S-6` 的後果段指回 `§〇`）。`§四` line 620–624 並逐字記載了三個版本的演進（只放 `DEPLOY.md` → 只加 deploy job → 加上 rollback），與 `§〇` 的由來欄（「rollback 那一半為審查 R-22 ＋ `[G7]`=A」）一致。
- **ICC 可行性表 vs D-3 的 blast radius 引言**：**不矛盾**。引言（line 337–341）以 `enable_icc` 預設 true 為前提說明「不隔離 `internal` 內部」，ICC 表說明把它關掉不可行——同一個事實的兩面。
- **新查出的一處矛盾**：line 474 的「網段打錯的最常見表現正好是 504」與 `backend`→`db` 在 startup 期間斷線的實際表現（502）相牴觸 → R-27。
- **一項不列為發現的措辭觀察**：`§四` 用「現由 `deploy.yml` 的探測把關」的現在式描述一個尚未寫進 repo 的步驟。整份檔都是設計、讀者不會誤以為 repo 已有，故不列為發現；但若下游只摘這一句，會讀成既有閘門。

### 6. 硬規則逐項

| 規則 | 判定 | 依據 |
|---|---|---|
| 不得 commit 私鑰／三雲 credential 字串 | **compliant** | 兩份產出無任何憑證字面值；探測刻意使用不存在的帳號 `__deploy_probe__`，line 485 逐字「**它不需要憑證**，所以可以放進 workflow 而不新增任何 secret」 |
| 版控中不得存在 path parts 含 `prod`／`production`／`secrets` | **compliant** | 本輪兩份產出與新增路徑皆不含該 path part |
| 部署憑證不得含 `$` | **N/A（本輪）** | 本輪六項修法不新增任何變數；`NFR4.1(a)` 的 `$` 禁令已在上游與既有段落記載 |
| 無人值守自動化須以 gh-aw／Actions workflow 承載 | **compliant** | 探測的兩個落點都是 `.github/workflows/deploy.yml` 的純 Actions 步驟（非 repo 內實作程式、非 LLM 路徑），符合該條以觸發來源判定的界線；第三個落點 `DEPLOY.md` 是人手動路徑，不在該條範圍 |
| ADR-0006 hard constraint 四面向 | **判定表仍在且誠實** | IAM／Audit 維持「部分處置」、Encryption 由 D-1 承接、Network exposure 由 D-3 承接；本輪六項修法未改變任何面向的判定，故不需重判。PBT 判 N/A 的理由（本單元無純函式、落點釘在 `K-10`／`K-06`）未被本輪修法觸動 |
| 文件語言繁體中文 | **compliant** | 兩份產出全繁中；`grep` `## English Version` 命中 0 |
| 設計階段 `bash` 片段 ≤ 15 行示意 | **compliant，但有一個可讀性風險** | 第一段（line 389–394）**6 行**、第二段（line 442–452）**11 行**，逐段都在上限內。風險是兩段並存且**第一段（單發版）在原地沒有任何「不可直接採用、見下方修法」的前向指引**，修正段在 45 行之後——考慮本 record 已有「實作者照字面抄」的實例（R-18 的 `:116`），建議在 line 386 的「具體做法——」處加一句指向 line 439 的修法。此點併入 R-24 的 Required action，不另立發現 |

## 結論

**六項不是都修好了：四項 Resolved（R-19／R-20／R-21／R-23），一項方向對但留了實作者必然猜錯的空白（R-22 → R-28），一項方向對但修正動作本身帶進新 bug（R-18 → R-24）。** 另查出三項（R-25／R-26／R-27），其中 R-27 屬既存漏審（分類表在上一輪被判 Resolved，當時未推導 startup 路徑）。

**三類切分**：修正動作新引入 **2 項**（R-24、R-28——都落在 R-18／R-22 的修法本身）；既存漏審 **1 項**（R-27）；真正的新設計問題 **0 項**（R-25／R-26 是表述與承載者缺口，不需要新的設計選擇）。**自我製造佔比 2／5 ＝ 40%**，較上一輪的 4／6 ＝ 67% 下降——但兩個 Major 都是自我製造，且其中 R-24 是一段**會在第一次真實失敗時就讓閘門行為與設計描述不符**的程式碼。

依本站 verdict 規則（0 Critical、2 Major）這相當於 **READY**；但 R-24 與 R-28 都必須在進實作前折入，理由與上一輪相同且更急：R-24 會讓探測在連線層失敗時無重試、無診斷輸出地紅燈，而一次誤報就會讓人把這個閘門拿掉，等於 R-01 又回來；R-28 會讓實作者在四種互不相同的 rollback 形狀之間猜，其中一種會讓 `restored` 這個既有輸出契約靜默失效。R-25／R-26／R-27 各為一到兩句就地補寫。

**深度**：deep，限於指定範圍。未實測者如實記載——Docker daemon 在本環境未執行（ICC 語意與 DROP 行為為依 Docker bridge driver 語意推導）；`192.168.10.10` 上 backend 冷啟動的實際秒數未實測（R-18(b) 的結論不依賴具體秒數，只依賴六個補丁皆為目錄層級操作這個已讀證據）。R-01…R-17 未重新質疑。
