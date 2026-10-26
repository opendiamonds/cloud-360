# CI/CD 管線 — `U13 brain-gateway`

> **結論先講：不新增任何 job、不改 `ci.yml` 與 `deploy.yml`。** 本單元的測試全部可被既有 `backend` job 撿到；契約漂移由既有兩道
> 閘門把關；部署沿用 deploy-on-merge 與既有 rollback。本站的實質內容是：(1) 三個「會讓既有 job 無聲失效或誤紅」的實作約束，
> (2) 契約重產的順序，(3) 部署後的人工實測（CI 無法做的那一段），(4) 待 `IG1` 裁決的一處可能變更。

## 一、Stage → Gate 對照

| 管線階段 | 既有 job／step | 本單元在此被驗證的東西 | 本單元需要的變更 |
|---|---|---|---|
| repo contract | `ci.yml:142` 起（`validate_repo_contract.py`、`validate_env_contract.py`、embedding 值檢查） | 無新變數（`NFR13.44` ②）；record 內文件語言 | 無 |
| frontend | `ci.yml:206-207`（API 型別漂移）、`:218-219`（WS 型別漂移 `check:ws-types`）、`:222-223`（`npm run build` 含 `tsc -b`） | C-1～C-7 重產的 `ws-contract.d.ts` 與前端一致；DEMO 頁缺 `page` 時 `tsc -b` 紅燈（`functional-spec.md` §十一之二第 6 點） | 無（由 `U14`／DEMO 刪除同批滿足，見 `infrastructure-specification.md` 5.2） |
| backend import smoke | `ci.yml:264-272`（`python -c "import main"`，只設 `DATABASE_URL`／`JWT_SECRET`） | 刪除 `brain_router` 匯入後 app 仍可匯入 | 無；**約束 C-a**（下節） |
| OpenAPI 漂移 | `ci.yml:281-289`（`dump_openapi.py --check`，匯入 `main`） | WebSocket 路由不入 OpenAPI——`openapi.json` 內 `/api/brain` 出現 0 次（實查），故刪 DEMO、加閘道都**不改** `openapi.json` | 無；**約束 C-a** |
| WS 契約漂移 | `ci.yml:299-300`（`dump_ws_contract.py --check`，不匯入 `main`） | C-1～C-7 改模型後 `ws-contract.json` 已重產（`NFR13.41` ①④） | 無 |
| backend 單元測試 | `ci.yml:303-306`（`python -m unittest discover -s tests -v`，只設 `JWT_SECRET`） | `NFR13.7`–`NFR13.44` 中標為 `unittest`／`TestClient`／PBT 的全部驗證；`NFR13.33` 的部署檔文字檢查；`NFR13.42` 五個 PBT | 無；**約束 C-b、C-c** |
| 真實 PostgreSQL job | `ci.yml:321` 起、`:550` 起 | 本單元無 DDL、無列鎖語意 | 無 |
| Docker 建置 | `ci.yml:615` 起 | 映像可建 | 無 |
| `ui-regression`（gh-aw，每 PR） | `docker-compose.test.yml` stack，經 nginx（`localhost:8090`） | `U14` 的 e2e 若斷言到 `ready`，**每個 PR 都機械驗證了 nginx 這一跳的子協定透傳**（`infrastructure-specification.md` 4.2 的 L2）；Cloudflare 那一跳 CI 碰不到 | 無（屬 `U14` 的測試計畫）；**後果 C-d** |
| 部署 | `deploy.yml`（合併進 `ut` 觸發，`deploy.yml:10-15`） | 資料面探測（`:308` 起）抓得到「後端因 `REDIS_*` 拒絕啟動」（502 持續） | 無；依 `IG1` 的答案可能新增一步（第五節） |
| 部署後實測 | **人工**（`infrastructure-specification.md` 4.4） | Cloudflare 兩跳的子協定透傳、回應不含 token | 無 workflow 變更——需要有效 token，而 Actions log 公開 |

## 二、讓既有 job 保持有效的三個實作約束（code-generation 必須遵守）

- **C-a｜閘道元件只在 startup hook 建立，不得在匯入時讀環境變數。** `ci.yml:264-272` 與 `:281-289` 都會 `import main`，且只設
  `DATABASE_URL`／`JWT_SECRET`。若 `build_brain_gateway` 或任何模組層程式碼在匯入時讀 `REDIS_*`，兩步都會以 `KeyError` 紅燈——
  看起來像本單元壞了，實際是違反了 `main.py:55-77` 既有的「掛在 startup hook 而非 import 時」慣例（該處四段註解逐字說明此理由）。
- **C-b｜單元測試不得連真實 Redis、不得依賴 CI 環境的 `REDIS_*`。** `backend` job 沒有 Redis 服務、只設 `JWT_SECRET`。
  `NFR13.32` 的三個啟動測試以 `unittest.mock.patch.dict(os.environ, …)` 自備變數並以 `with TestClient(app)` 觸發 startup；
  「Redis 不可達 → 握手 1011」以不可達位址構造（`build_redis_client` 延遲連線，`F-29`）。其他測試沿用 `TestClient(app)`
  不進 `with`（不觸發 startup，`team.md` 規則 B 的既有形狀）。目前 `backend/tests/` 內沒有任何 `with TestClient`（實查 0 檔），
  故本單元新增的是第一批會觸發 startup 的測試——它們必須在測試內自備 startup 需要的**全部**變數（含既有的
  `EMBEDDING_PROVIDER`、`BRAIN_SESSION_HISTORY_MAX`、`BRAIN_ROUTER_CONFIDENCE_THRESHOLD`，`main.py:61-76`），否則會因別的單元的啟動檢查紅燈。
- **C-c｜`NFR13.44` ① 的環境變數集合檢查必須用 AST 並涵蓋下標形式。** `validate_env_contract.py:88` 的偵測式只認
  `os.environ.get(...)`／`os.getenv(...)`，看不到 `os.environ["REDIS_URL"]`；以 grep 呼叫引數實作 `NFR13.44` ① 會對本單元恆真。
- **新測試的落點**：`backend/tests/test_brain_gateway*.py`，`discover -s tests` 的預設樣式 `test*.py` 會撿到，不需改 `ci.yml`。
  單一行程守門（`NFR13.33`）的測試讀 `backend/Dockerfile` 與兩份 compose，路徑以 `Path(__file__).resolve().parents[2]` 推得 repo 根；
  CI checkout 為完整工作樹，檔案皆在。另依 `infrastructure-specification.md` 第七節補斷言「`backend` 服務無 `env_file`」，
  依 5.2 補「`/api/brain/ws` 的 WebSocket 路由恰為 1 條」。

## 三、契約增量的重產步驟（`NFR13.41`；順序不可換）

0. **前置關卡**：`ADR-0020` 取得使用者核可，且其核可紀錄早於含 C-1～C-7 的 commit（`NFR13.41` ③）。
1. 改 `backend/services/brain_ws_contract.py` 的六個模型（每個新欄位有 `description`）。
2. 改 `backend/scripts/dump_ws_contract.py:108-116` 的 `CLIENT_FIELD_WHITELIST`（三個客→伺模型）。
3. `cd backend && python scripts/dump_ws_contract.py` → 重產 repo 根的 `ws-contract.json`。
4. `cd frontend && npm run gen:ws-types` → 重產 `src/types/ws-contract.d.ts`。
5. 改 `backend/tests/test_ws_contract.py` 的五處並加 `protocolName` 負向案例（`functional-spec.md` §十一之二第 5 點）。
6. 同一個 commit 內刪除或改寫 DEMO 前端（否則步驟 4 之後 `tsc -b` 紅燈）。
7. 本機跑一次 CI 的三個對應指令確認綠：`python scripts/dump_ws_contract.py --check`、`npm run check:ws-types`、`npm run build`。
8. **突變驗證**（`NFR13.41` ④）：只改模型、不做步驟 3 → `--check` 必須紅燈；還原後複驗綠。結果寫進 code-generation 產出。

## 四、部署策略與環境推進

- **策略**：沿用 deploy-on-merge 的原地替換（`docker compose up -d --build`），單一 staging、無 blue-green／canary（ADR-0007；production 不在範圍）。
  替換時所有既有 WebSocket 連線中斷——`U14` 的重連退避（帶入項 10、17：至少持續 60 秒）承接這個中斷；行程內暫態（等待中的反問等）
  隨之消失，屬 `NFR13.31` 已揭露的行為。
- **同批**：見 `infrastructure-specification.md` 第五節（DEMO 前後端刪除、C-1～C-7、`U14` 與 `U13` 同一次合併；DEMO 不得先於 `U13` 進 `ut`）。
- **推進**：本機 → PR（CI 全綠＋`ui-regression`）→ 合併 `ut` → staging 自動部署 → 人工三層實測 → 宣告入口頁可用。
- **回滾**：部署 job 失敗 → 既有 `rollback` job（`deploy.yml:542` 起）自動還原 last-good；部署成功但實測失敗 → 人工開 revert PR
  （`infrastructure-specification.md` 5.4）。本單元無 DDL，程式回滾不需資料還原。

## 五、Secrets management

| Secret／值 | 位置 | 本單元的變化 |
|---|---|---|
| `REDIS_PASSWORD` | GitHub secret → `deploy.yml:71-91` 必要檢查 → `render-env.sh:71`／`:129` | 無；它已是必要值。語意上由「session 功能需要」升為「後端啟動需要」 |
| `REDIS_URL`／`REDIS_USER` | `render-env.sh:127-128` 字面值（**不是** secret） | 無 |
| `OPENROUTER_API_KEY` | GitHub secret → `deploy.yml:109`／`:577` → `render-env.sh:109`（optional） | **待 `IG1`**：若選 A（部署時必要），只在 `deploy.yml:71-91` 的必要檢查加一項、**不**加進 `render-env.sh` 的拒絕清單（rollback job 只經 `render-env.sh`，`deploy.yml:617`，不得因空金鑰而無法回滾）；若選 B（警告不擋），在 deploy job 加一步只檢查是否為空、**不得印出值**；若選 C，管線不變 |
| 實測用的使用者 token | 維運者 shell 變數，用完 `unset` | **不進任何 workflow、secret 或檔案**：本 repo 為 public、Actions log 公開；`project.md ## Mandated` 的 secrets／variables 查證規則同一理由 |

不新增任何 GitHub secret 或 variable，故 `project.md` 要求的「新增憑證型 secret 後以 `gh api` 查證落在 secrets」本單元不觸發（`IG1` 三個選項皆不新增 secret：A 只檢查既有 secret 是否為空）。

## 六、為何不新增 job

| 候選 | 不新增的理由 |
|---|---|
| 連真實 Redis 的 WebSocket 整合 job | `U10` 的 `[I1]` 已考慮並否決 Redis-connected CI job（`deploy.yml` 的 Redis 還原步驟註解逐字記載）；本單元的 Redis 行為由 `U10` 的介面測試替身承載，部署面由 `deploy.yml:393` 起的還原驗證承載 |
| 在 `deploy.yml` 自動化子協定透傳實測 | 正向實測需要有效 token，而 Actions log 公開；不帶 token 的負向探測（無子協定 → 403）分辨不出新閘道與 DEMO（兩者對無子協定的請求都拒絕），不構成證據 |
| 前端 unit 測試 job | `team.md` 的 D 不採用；`U14` 以 Playwright e2e 承載 |

## 七、後果 C-d：CI 測試 stack 的空金鑰

`docker-compose.test.yml:83` 把 `OPENROUTER_API_KEY` 設為空字串，故 `ui-regression` 中入口頁每個走到 `classify` 的輪次都是
`error(INTERNAL_ERROR)`（不論 `IG1` 怎麼答——`IG1` 只管 staging）。`U14` 的 e2e 能斷言握手、`ready`、狀態訊息、`prompt_guard` 攔截
（在 `classify` 之前，`NFR13.6`）與錯誤呈現；**不能**斷言交辦成功。這要寫進 `U14` 的測試計畫，而不是在 e2e 失敗後才發現。
