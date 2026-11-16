# Infrastructure Design 問題檔 — `U6 embedding-port`

> Stage：`infrastructure-design`（3.4）　Unit：`U6 embedding-port`（`library`，M）
> Depth：**Minimal**　Review：advisory（1 輪）　建立時間：2026-10-05　作答完成：2026-10-05T01:11:37Z（`date -u` 取值）
>
> `produces_kinds` 對 `library` 只開放 `cicd-pipeline` 與 `traceability`
> ——`infrastructure-specification` 與 `monitoring-design` 是
> `[service, ui, packaging]`，本單元不產出。
> **本單元零容器、零服務、零端點**，所以本站談的不是「要開什麼資源」，
> 而是**它對既有 CI／CD 管線造成什麼**。

---

## 〇、已定案、**不重問**

| 已定案 | 出處 |
|---|---|
| 四個提供者、`fulltext` ⇒ 無 Port、大聲失敗 | ADR-008；`functional-design [Q1]`／`[Q3]` |
| 啟動驗證落在與 `configure_provider_env()` 並列的函式，由 startup hook 呼叫 | `nfr-design [Q1]`=A（`D-1`） |
| `fastembed` 選用、不進 `requirements.txt`、lazy import | `functional-design [Q4]`=A |
| timeout 具名常數、預設 10 秒、可由環境變數覆寫；**名稱未定**，具名交接 `code-generation`（`H-N4`） | `nfr-requirements [Q3]`=A；`nfr-design` 審查 `R-02` |
| 可觀測性只用 `logging`，零 metrics 依賴、零新端點 | `nfr-design [Q4]`=A（修訂） |
| `requirements.txt` 淨變更：零 | `nfr-requirements` 的 `tech-stack-decisions.md §二` |

## 〇·二、出題前的唯讀查證（**非來源**）

- `deploy/docker-compose.deploy.yml:120-123` 以**無 fallback** 的形式傳四個 embedding 變數
  （`${EMBEDDING_PROVIDER}` 而非 `${EMBEDDING_PROVIDER:-x}`）；
  `deploy/render-env.sh:124-127` 把四者當**字面值**寫出。
- `deploy/docker-compose.test.yml:102` 為 `EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER:-stub}`
  ——**有** fallback，故 `ui-regression` 的短生命週期 stack 會以 `stub` 啟動。
- `scripts/validate_env_contract.py` 的 `validate_local_dev_template_is_complete()`
  掃描 `backend/**/*.py`（排除 tests）的所有環境變數讀取，**要求每一個都被
  `backend/.env.example` 記載**，否則 CI 的 `repo-contract` job 紅燈。
  其 `validate_deploy_stack_is_fully_supplied()` 只要求**無 fallback** 的變數被寫入。
- CI（`ci.yml`）順序：`repo-contract` → `frontend` → OpenAPI drift → `backend`
  （import smoke ＋ `unittest`）→ `docker-build`。
- `backend/requirements.txt` **無** `fastembed`；`docker-compose.test.yml:18` 逐字
  「NO ollama」。**故本單元三個實作中，CI 實際執行到的只有 `stub`。**

---

## Q1 兩個真實提供者在 CI 的執行覆蓋是**零**

`ollama` 需要第 6 個容器（test stack 逐字沒有），`fastembed` 不在 `requirements.txt`
（CI 根本不會安裝）。於是本單元交付三個實作，**CI 只跑得到 `stub` 一個**。
`P1`–`P4`／`P6` 六個 PBT 性質裡有五個只對 `stub` 成立——這在
`functional-design/functional-spec.md` 的 `OQ-E2` 已記為「無自然承接站」。
本站是基礎設施站，是最後一個能把它變成 CI 設定的地方。

- **A（建議）— 不加 CI job，把它寫成具名缺口並指定可用的替代覆蓋。**
  以 mock／monkeypatch 覆蓋**可測的那幾段**：lazy import 失敗（`BR4.3`）、
  逾時路徑（`NFR3.2`）、`userinfo` 遮罩（`SEC-2`）、截斷（`D-4`）——這些都不需要
  真的 ollama 或 fastembed。**真正不測的是「該提供者回傳的向量是否真的 1024 維」**，
  而那在首次真實呼叫時會由 `BR2.2` 的執行期斷言攔下。缺口照 `OQ-E2` 的形狀維持具名。
  代價：部署後第一次用記憶才會發現模型維度不對——但那是大聲失敗，不是靜默。
- **B — 在 `ci.yml` 加一個 optional job，裝 `fastembed` 並跑其 PBT。**
  能真正覆蓋一個實作。代價：CI 多一個會下載約 1GB 模型的 job（每次 PR 或每日），
  而 `fastembed` 依 `[Q4]`=A 是**本機限定**的路徑——為一條本機路徑付 CI 時間與頻寬。
- **C — 在 test stack 加 ollama 服務。** 覆蓋面最大。代價：直接推翻
  `docker-compose.test.yml:18` 逐字「NO ollama」的既有決定，且 `ui-regression`
  每個 PR 都要拉模型；該檔的註解寫明它刻意是四服務的短生命週期 stack。
- **D — 把 `fastembed` 加進 `requirements.txt` 讓 CI 自然涵蓋。**
  代價：推翻 `[Q4]`=A，且 `tech-stack-decisions.md` 已核可「`requirements.txt`
  淨變更：零」。

[Answer]: A

## Q2 timeout 變數要不要進部署 compose，以及用哪一種形式

`nfr-design` 的 `H-N4` 把變數**名稱**交給 `code-generation`，但**它要不要出現在
部署 stack**是基礎設施決定，屬本站。三種形式對 `validate_env_contract.py` 的
觸發完全不同：

- **A（建議）— 進 `backend/.env.example`，但**不**進部署 compose。**
  即：部署環境一律用程式預設的 10 秒，不提供部署期覆寫。
  `validate_local_dev_template_is_complete()` 的要求**仍然成立**（backend 會讀它，
  所以 `backend/.env.example` 必須記載）——這一條無論如何都要做。
  但因為部署 compose 不引用它，`render-env.sh` 與 `deploy/.env.example`
  **不需**變動，`validate_deploy_stack_is_fully_supplied()` 不觸發。
  理由：10 秒是「服務掛了」的判準，不是需要逐環境調校的效能參數；
  真要調整時再加，成本一樣。代價：staging 上要改 timeout 必須改 code 重新部署。
- **B — 進部署 compose，用**有** fallback 的形式（`${X:-10}`）。**
  可在部署期覆寫，且因為有 fallback，`validate_deploy_stack_is_fully_supplied()`
  不要求 `render-env.sh` 寫它。代價：`deploy/.env.example` 要列它（否則文件與
  實際可設定項脫節），而那又觸發 `LOCAL-DEV.md` 的 blocking 同步。
- **C — 進部署 compose，用**無** fallback 的形式（`${X}`），比照既有四個變數。**
  形式最一致（`:120-123` 四個都是無 fallback）。代價：`render-env.sh` **必須**
  寫它（機械強制），`deploy/.env.example` 必須列它，`LOCAL-DEV.md` 必須同步
  ——三處 blocking，而這個變數有程式預設值、缺值不會造成無聲降級，
  不具備那四個變數需要強制的理由。
- **D — 連 `backend/.env.example` 都不加，只留程式常數。**
  代價：**CI 會紅**——`validate_local_dev_template_is_complete()` 掃到
  `backend/` 讀了一個未記載的變數就失敗，訊息逐字「An undocumented variable is one
  a developer cannot set without reading the source」。

[Answer]: A

## Q3 `D-1` 的啟動驗證會在部署時第一次真正執行，而部署失敗會自動 revert

`D-1` 讓設定錯誤**終止啟動**。這在部署路徑上有具體後果：`deploy.yml` 啟動失敗
→ `rollback` job 還原 last-good → **自動開 revert PR** → dispatch Deploy Doctor。
也就是說，一個打錯的 `EMBEDDING_PROVIDER` 不只是部署紅燈，是**一次自動回退**。
而 `render-env.sh:124-127` 把那四個值寫成字面值，所以實際風險不是「值錯」
而是「**有人改了那四行**」。

- **A（建議）— 不加部署前檢查，但把這條失敗路徑寫進 `cicd-pipeline.md` 的
  rollback 說明，並指出既有的 `validate_env_contract.py` 已在 `repo-contract`
  job（**部署之前**）擋下一部分。**
  具體：改動 `render-env.sh` 的 PR 會先過 `repo-contract`；該檢查驗的是
  「compose 要的變數有沒有被寫入」，不驗「值是否在允許集合內」。
  **那個缺口是真的**，但補它需要在 CI 裡複製一份允許值清單——第二份會過期的副本，
  正是 `team.md`「單一真實來源」要防的。故接受，並寫明它。
  代價：`EMBEDDING_PROVIDER` 被改成非法值時，第一個發現的是部署而不是 CI。
- **B — 在 `repo-contract` job 加一條檢查：`render-env.sh` 寫出的
  `EMBEDDING_PROVIDER` 值必須在四個合法值內。**
  部署前就擋下。代價：允許值清單出現第二份（一份在 Python 的 Port、一份在
  檢查腳本），且本單元才剛為「兩份清單」寫了一條雙向一致性測試（`BR3.3`）
  ——再製造一組同形的問題。
- **C — 讓啟動驗證改為只記 WARN，避免自動 revert。**
  代價：直接推翻已核可的 `BR1.6` 與 ADR-008「不得靜默降級」。
- **D — 在 `deploy.yml` 加一個 smoke step，部署後確認那條啟動 INFO 出現。**
  能確認驗證真的跑了。代價：那是部署**後**，revert 已經不需要被避免（啟動失敗
  本來就會讓部署紅）；它能抓的是「驗證沒跑」而非「值錯」，價值較低。

[Answer]: A


---

## 修訂 1 — 兩題的作答經審查後反轉（2026-10-05）

審查 iteration 1 判 **NOT-READY**（1 Critical、4 Major）。其中兩項直接推翻本檔的
已作答內容。**原選項本文與原 `[Answer]` 皆不改寫**（依 `scope-definition:21af5820`：
保留「A 曾被選過」的可追溯性）；反轉以本節記錄。

### Q2：`A` → **反轉為遵守 `NFR8.1` 逐字**（審查 `R-01`，**Critical**）

**壞在哪**：`NFR8.1` 是上一站**已核可且通過審查**的需求，逐字寫 timeout 變數
「必須在同一個 PR 內讓 `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它、
`backend/.env.example` 列它」——而 `[Q2]`=A 說前兩者「**不需**變動」。
更糟的是 `traceability.json` 仍把 `NFR8.1` 標為 `OK`：**設計文字與追溯表各說各話，
而下游只會讀到其中一份。**

**我的錯在出題時**：Q2 的四個選項沒有一個提到它們與 `NFR8.1` 的關係。
我在上一站自己寫下那條需求，隔一站出題時沒有回去核對——
使用者是在不知道選項 A 會推翻一條已核可需求的情況下作答的。

**反轉後**：timeout 變數進部署 compose（無 fallback，比照 `:120-123` 的既有四個）、
`render-env.sh` 寫它、`deploy/.env.example` 列它、`backend/.env.example` 列它、
`LOCAL-DEV.md` 同步。設定檔改動面由**一個**變**四個**，外加 `LOCAL-DEV.md`。
不選「修訂 `NFR8.1`」的理由：合規成本只有四個檔各加一到兩行，而那四個檔
已經各有四行同形內容；順帶讓 staging 調 timeout 不必改 code 重新部署。

### Q3：`A` → **反轉為「呼叫既有驗證函式」**（審查 `R-04`，Major）

**壞在哪**：我把「補那個 CI 缺口」框成**只有兩條路**——接受缺口，或在 CI 複製
一份允許值清單。審查指出第三條路，而實測證明它便宜：`repo-contract` job
**已經有 `actions/setup-python@v5` 並已跑四支 Python validator**，所以 CI 可以
直接 import 並呼叫 `D-1` 的驗證函式（允許值清單的唯一真實來源）去驗
`render-env.sh` 會寫出的值——**零第二份清單**。既有前例就在隔壁：
`dump_openapi.py --check` 正是在 `backend` job 裡 import 應用程式碼做漂移檢查。

**我的錯是用一條正確的規則（`team.md` 的「單一真實來源」）去迴避一個真實的
安全缺口，而沒有去找「同時滿足該規則又關上缺口」的選項。**

**反轉後**：加該 CI step，缺口關閉；具體 YAML 與 step 名稱交接 `code-generation`
（`H-I3`），並明文禁止在該 step 內自行列舉允許值。
