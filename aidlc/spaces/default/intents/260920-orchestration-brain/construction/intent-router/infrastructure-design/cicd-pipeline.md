# CI/CD Pipeline — `U11 intent-router`

> **本檔是本站的 review artifact。** 本單元對交付管線的影響有三項，而**其中一項
> 是本站實地查證後才浮現的**：`NFR1` 的量測在 CI 裡**跑不起來**，因為 `ci.yml`
> 全檔沒有 `OPENROUTER_API_KEY`。

## 一、既有管線（不變的部分）

`ci.yml` 有七個 job：`gate`、`repo-contract`、`frontend`、`backend`、
`memory-schema`、`concurrency`、`docker-build`。**六者彼此並行，僅共同依賴
`gate`**（修訂 1，審查 `R-03`：原文寫「依序」並畫成箭頭鏈，而 `ci.yml:422`
自己的註解逐字「wall-clock 增量約為 0……故全部並行」——箭頭鏈會讓下一個要在
這張清單上插入 job 的人誤以為必須排在某處，實際只需 `needs: gate`）。
本單元**不新增任何 job**，
它的測試全部落在既有的 `backend` job 內：

| 測試類別 | 落點 | 依賴 |
|---|---|---|
| L5 述詞的 property-based（`ADR-0006` 的落點） | `backend/tests/test_*.py`，`hypothesis` | **零新增**（`hypothesis` 已在 `requirements.txt`） |
| L4 parser 的 V-1～V-5 畸形輸入 | 同上，example-based | 零新增 |
| L2 context-builder 的「不含完整歷程」斷言 | 同上，**無需 mock**（它是純函式） | 零新增 |
| L3 model-port 的四種失敗（逾時／5xx／429／連線失敗） | 同上，`unittest.mock` 替身 | 零新增 |
| 結構斷言（禁 import 清單、`kinds` 引數、模組層無可變綁定） | 同上 | 零新增 |

**`backend` job 用 `python -m unittest discover -s tests -v`**（`team.md` 既成事實），
新測試檔放進 `backend/tests/` 即被撿到。

## 二、新增的第八條路徑：`workflow_dispatch` 的量測 job（`[I1]`=A）

### 為什麼需要它，以及為什麼它不在 `ci.yml` 裡

| # | 查證 | 後果 |
|---|---|---|
| V1 | **`ci.yml` 全檔 `OPENROUTER` 零命中** | `NFR1`／`NFR10`／`OQ-10` 的量測在 CI 裡**拿不到金鑰**，無法執行 |
| V2 | 現有 LLM 測試**全部用替身**（`test_a3_langgraph_migration.py:6` 檔頭逐字「no real `OPENROUTER_API_KEY`」） | CI 套件今天**刻意**不需要真金鑰——這是既有設計，不是疏漏 |
| V5 | `ci.yml` 觸發是**裸 `pull_request`** | 同 repo 分支的 PR **會**拿到 secrets（fork 的不會）。任何 PR 作者能在自己的 workflow 改動裡 echo 它 |
| V6 | **本 repo 為 public**，`project.md` 逐字「一次意外 echo 即等同公開發布」 | 把付費金鑰放進 `pull_request` 路徑是一個實質的暴露風險 |

**`[I1]`=A 定案**：量測改由**手動觸發**的獨立 job 承載。

### 設計

```yaml
# 片段，非完整 workflow（設計階段限制 ≤15 行）
on:
  workflow_dispatch:
    inputs:
      annotation_set: { description: 標註集路徑, required: true }
jobs:
  routing-accuracy:
    runs-on: ubuntu-latest
    env:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}   # 僅此 job
      BRAIN_ROUTER_MODEL: typesafe/jev-1.13
```

| 面向 | 決定 | 理由 |
|---|---|---|
| **觸發** | 只有 `workflow_dispatch` | `pull_request` 觸發的 run **完全不碰金鑰** |
| **金鑰** | `secrets.OPENROUTER_API_KEY`，**只在這一個 job 的 `env`** | 不放 workflow 層級 `env`，縮小暴露面 |
| **Runner** | `ubuntu-latest`，**不是自架 runner** | 自架那台的 `concurrency: deploy-10-10` ＋ `cancel-in-progress: false` 會讓量測與部署互卡（`[I1]` 選項 C 的代價） |
| **輸出** | 準確率、`classify` 延遲 P50／P95、槽位數分佈 | 對應 `NFR1`／`NFR3.60`／`NFR3.73`；後者同時是 `D-7`（上界 4）的覆核依據 |
| **它不是閘門** | 不擋 PR、不擋 merge | **這是 `[I1]`=A 的已知代價**，處置見下 |

### 「它不是自動閘門」的處置——這一點不能只寫在這裡

**觸發義務寫進 `build-and-test`（3.6，`ALWAYS`）的核可關卡**：該站本來就要裁決
`0.7` 與 `80%` 的校正（`NFR1` 的校正程序），而裁決需要實測數字。
**沒有這個數字，該站的 Target Verification Matrix 會把 `NFR1`／`NFR10` 標
`Unverified`**（`build-and-test.md:144-146` 逐字：未被更下游站擁有的目標是
「`Unverified`，不是 deferred 成功」），觸發失敗升級梯。

亦即：**不跑這個 job，`build-and-test` 會自己紅燈**——這是比任何提醒都可靠的
強制機制，而它是既有的，不需要新發明。

### `TS-6` 的修正（本站實地查證後）

`nfr-requirements` 的 `TS-6` 原文把前置條件寫成「使用者把金鑰寫進 `backend/.env`」。
**V1 證明那對 CI 完全無效**——本機 `.env` 不會進 CI。修正後的前置條件是：

| 原描述 | **修正後** |
|---|---|
| 使用者把 `OPENROUTER_API_KEY` 寫進 `backend/.env` | **`OPENROUTER_API_KEY` 必須是一個 GitHub repository secret**（`deploy.yml:109`／`:577` 已在用它，故**很可能已存在**——但本站無法查證，`gh` 不可用），且本檔 §二 的 `workflow_dispatch` job 必須已落地並被跑過一次 |
| 落點：`backend/.env`（本機） | 落點：**GitHub secrets ＋ 一個手動 job** |

**`backend/.env` 仍然有它的用途**——本機開發與手動驗證——但它**不是**
`build-and-test` 的前置條件。兩者混為一談正是原 `TS-6` 的錯誤。

## 三、部署（不變，但有一處新的失敗模式）

`deploy.yml` 於 PR closed（merge）到 `ut` 觸發，跑自架 runner，30 分鐘逾時，
`concurrency: deploy-10-10`、`cancel-in-progress: false`。**本單元不改動它**。

**新的失敗模式**：`BRAIN_ROUTER_CONFIDENCE_THRESHOLD` 是 required-no-default
（`BR3.4`）。若 `render-env.sh` 沒有寫它，`docker compose up` 會**成功**、
backend 容器會起來然後 **crash-loop**。

**`[I2]`=A 的處置**：`render-env.sh` 寫字面值 `0.7`，比照
`BRAIN_SESSION_HISTORY_MAX=200`（`render-env.sh:130`）的既有先例。
**不加進那兩道「不得取預設」的守衛**（`deploy.yml:71-85` ＋ `render-env.sh:57-69`）
——它們的三個成員都是憑證，守衛訊息逐字在講 `JWT_SECRET` 被偽造的後果，
混進一個調校參數會讓那段訊息對不上。

**這個失敗模式仍有一道既有的網**：`deploy.yml:130` 的
`curl -fsS ... http://127.0.0.1:8090/` 健康檢查——crash-loop 的容器過不了它，
部署會失敗並觸發既有的 rollback job（還原 last-good、開 revert PR、
dispatch Deploy Doctor）。**所以後果是「部署失敗並自動回滾」，不是「靜默壞掉」。**

| Stage | Gate | 本單元的影響 |
|---|---|---|
| `repo-contract` | `validate_repo_contract.py` ＋ **`validate_env_contract.py`** | **會擋**：五個新變數若三處沒同步即紅燈（`NFR8.61`） |
| `frontend` | lint ＋ `tsc -b` ＋ build | 無影響（本單元無前端） |
| OpenAPI drift | `dump_openapi.py --check` | **無影響**——本單元不新增任何 HTTP 端點（`SEC-2`），`openapi.json` 不會變 |
| `backend` | import smoke ＋ `unittest` | **會擋**：本單元的全部測試在此 |
| `memory-schema` | 真實 PostgreSQL job | 無影響（本單元不改 schema） |
| `concurrency` | 併發測試 | 無影響（本單元無狀態） |
| `docker-build` | buildx 兩個 image | 無影響（無新依賴，`TS-5`） |
| **（新）`routing-accuracy`** | **手動，非閘門** | `NFR1`／`NFR10`／`OQ-10` 的唯一量測路徑 |

## 四、Rollback

**沿用既有路徑，零增量。** `deploy.yml` 的 `rollback` job 在部署失敗時還原
last-good、開 revert PR、dispatch Deploy Doctor。

**本單元讓 rollback 更簡單的一點值得記**：它**無狀態、不寫任何持久層、
不改 schema**（`NFR4.70`）。所以回滾本單元**沒有資料面的善後**——不需要
反向 migration、不需要清理半寫入的狀態。對照組是 `U10`（Redis session）與
`U8`（memory schema），兩者的回滾都要考慮資料。

## 五、Secrets management in CI/CD

| Secret | 在哪裡 | 本單元的變更 |
|---|---|---|
| `OPENROUTER_API_KEY` | GitHub secret → `deploy.yml:109`／`:577` → `render-env.sh:104`（`${...:-}`，**optional**）→ `compose:91` | **部署路徑零變更**。新增的是 §二 的 `workflow_dispatch` job 也要用它 |
| `BRAIN_ROUTER_*`（五個） | **不是 secret**，字面值寫在 `render-env.sh` | 新增五處，三檔同步（`NFR8.61`） |

**一處必須寫明的既有落差（非本單元造成，但本單元讓它更要緊）**：
`render-env.sh:21` 逐字把 `OPENROUTER_API_KEY` 標為 **optional**，`:104` 為
`${OPENROUTER_API_KEY:-}`——缺值即空字串、不中斷。該註解的理由是
「A1 design agent; **empty disables generation**」。

**但本單元的路由層一旦上線，空金鑰的後果就不只是「A1 不能產圖」**：
**入口頁的每一次輸入都會失敗**（`BR8.2` 大聲失敗，不降級猜測），因為分類是
每一輪的第一步、沒有快路徑（`BR2.1`／`K-10` 的 `hard_rules` 第一條）。

**本站不自行把它改成 required**——那會影響既有的 A1／A3／C1 部署行為
（現在它們在無金鑰時只是功能降級，改成 required 會讓整個 stack 起不來），
而那是一個跨單元的決定。**處置**：列為交接事項 `I-1`，承接
`U13 brain-gateway` 的 `infrastructure-design`（它擁有入口頁的 WS 端點，
是「入口頁完全不能用」這個後果的真正擁有者）。

> **`I-1` 的 CONDITIONAL-skip 風險（修訂 1，審查 `R-02`，Major）**：
> `infrastructure-design` 的 `execution` 是 **`CONDITIONAL`**，其 `condition` 逐字
> 「Infrastructure services need mapping, deployment architecture required, or
> cloud resources needed. **Skip if no infrastructure changes** and infrastructure
> already defined.」——而 `U13` 很可能正好符合那個 skip 條件（WS 端點已存在、
> 不需新 infra）。**若該站被 skip，`I-1` 會隨它一起無聲消失。**
>
> **判定 skip 的那個執行者（conductor 或人工）必須在判定的當下，把 `I-1`
> 重新提交使用者裁決，不得讓它隨 skip 靜默消失。**
>
> 比照本 intent 內的既有正確先例：`brain-infra` 的 `AUDIT-CORRELATION-ID` 交接項
> 逐字寫「該站是 CONDITIONAL、condition 為連言，`brain-infra` 跑過不保證
> `U12`／`U13` 會跑，屆時判定 skip 的執行者須重新提交使用者裁決」。
> **本站原本漏了這一句，而 `project.md` 已有明文規則要求它**——
> 這是本 intent 第四次踩同一個「指派給 CONDITIONAL 站而未註明 skip 風險」的洞。
>
> **`I-1` 承載的不是假設性風險**：空 `OPENROUTER_API_KEY` 會讓入口頁**每一輪**
> 輸入失敗（`BR2.1` 無快路徑 ＋ `BR8.2` 大聲失敗），而審查已獨立核實這條鏈成立。

## 六、審查處置表（`review-01.md`，三項，`VERDICT: READY`）

**三項全部接受並已修正。** 這是本單元四站以來第一個 `READY`，而它仍帶三項發現。

| ID | 嚴重度 | 判定 | 處置 |
|---|---|---|---|
| `R-01` | Major | **接受** | `traceability.json` 的 `NFR1.60`／`SEC-4` 由 `N/A` 改為 **`Deferred`**，`target` 寫具名承接站 `observability-setup（4.x）`。`N/A` 的語意是「無基礎設施落點」（對 `NFR3.65`／`NFR9.61`／`SEC-1` 等純應用層項是正確用法），而這兩列**有具名承接站**——那是 `Deferred`。**同一個 intent 內的對照組早就示範了這個區分**（`brain-infra` 的 `AUDIT-CORRELATION-ID`、`session-store` 的 `NFR4.41`），我沒去比對 |
| `R-02` | Major | **接受** | `I-1` 補上 CONDITIONAL-skip 風險註記（§五末）。`infrastructure-design` 對 `U13` 是 `CONDITIONAL` 且 `U13` **很可能正好符合 skip 條件**（WS 端點已存在、不需新 infra），而 `I-1` 承載的是一條已被審查獨立核實的生產風險（空金鑰 → 入口頁每輪失敗）。同樣地，**`brain-infra` 的 `AUDIT-CORRELATION-ID` 已有正確先例**，而 `project.md` 本就有明文規則 |
| `R-03` | Minor | **接受** | 「七個 job **依序**」改為「六者彼此並行，僅共同依賴 `gate`」。`ci.yml:422` 自己的註解逐字「wall-clock 增量約為 0……故全部並行」 |

### 三項的共同形狀，以及為什麼它值得單獨記

**兩個 Major 都在同一個 intent 內有現成的正確寫法，而我沒有去看。** `R-01` 的
`Deferred` vs `N/A` 區分、`R-02` 的 CONDITIONAL-skip 註記，**`brain-infra` 與
`session-store` 的同站產出都已經做對了**——它們就在隔壁目錄。

這與本 session 前三站的失誤**類別不同**：那些是查證範圍不足、引用過期事實、
同一份檔內自相矛盾。**這一次是沒有看對照組**——而 `project.md` 的六項自檢裡
**第 4 項就是「檔案集合一致性：同類單元之間 diff 產出檔清單」**。我跑了那一項，
但我跑的是**檔案是否齊備**，不是**同類產出的狀態語意是否一致**。

**可執行補強**：自檢 4 擴充為兩層——①`ls` 比對產出檔清單是否齊備（既有）；
②對 `traceability.json` 這類**有狀態欄位**的產出，抽樣比對同類單元**相同形狀的
項目用了哪個狀態值**，不一致就要能說出理由。成本是讀兩個檔，而它這次會抓到兩個 Major。

### 修正時機的如實記載

**上述三項修正發生在 `REVIEW_COMPLETED`（`VERDICT: READY`）記錄之後。**
本站 `gate: false`，沒有可以登記 disposition 的關卡，所以「接受但不修」會讓這兩個
Major 永久留在產出裡——而 `R-02` 的後果是一條真實的生產風險無聲消失。
故選擇修正；審查收據所綁定的是修正**前**的位元組，這一點在此記明，
不以「審查通過」掩蓋產出已變更的事實。
