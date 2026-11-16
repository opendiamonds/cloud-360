## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T13:20:01Z
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `infrastructure-specification.md` §二「記憶體上限的值怎麼來」 | 初版 `[I2]`＋`[I2b]`＋硬寫 compose 三者並存的死結。 | 已由使用者裁決鬆開 `[I2b]`，改公開基準＋限期複量。 | Resolved |
| R-02 | Critical | `infrastructure-specification.md` §二 | 官方 `ollama/ollama` 映像不會自動拉模型。 | 已定案部署後 `ollama pull` 步驟並已上線（`deploy.yml:274` 一帶）。 | Resolved |
| R-03 | Critical | `cicd-pipeline.md` §六「差集」 | 初版「差異只有 `cloudflared`」與 `[I5]`=A 矛盾。 | 已更正為差集 `{cloudflared, ollama}` 並實測服務數。 | Resolved |
| R-04 | Major | `infrastructure-specification.md` §二 | 兩個新服務的 `depends_on` 拓樸從未設計。 | 已定案 `backend→redis` `service_healthy`、`backend→ollama` `service_started`。 | Resolved |
| R-05 | Major | `infrastructure-specification.md` §二 | `maxmemory` 承載與容器上限關係式不可判定。 | 已給出可判定關係式與 `command:` 承載。 | Resolved |
| R-06 | Major | `infrastructure-specification.md` §四 | 磁碟空間公式套用單一掛載點，算不出來。 | 已拆為逐掛載點門檻並給出日誌預算上界。 | Resolved |
| R-07 | Major | `infrastructure-specification.md` §二 | 升版窗口內 `db` 記憶體上限未另行處置。 | 已定案升版期暫時提高、驗證後恢復。 | Resolved |
| R-08 | Minor | `cicd-pipeline.md` §五 | 改動清單完整性缺口（漏列三項）。 | 已補入第 15–17 項。 | Resolved |
| R-09 | Major | `cicd-pipeline.md` §三 | `[I5]`=A 使 `U6→brain-infra` 依賴邊的上游理由不成立。 | 已指名承接站（`U6` functional-design／delivery 順序），不擅自移除依賴邊。 | Resolved |
| R-10 | Minor | `infrastructure-specification.md` Assumptions | `pg16` 陳舊引用清單不完整、複驗指令本身有誤。 | 已補完逐處行號並更正複驗 pattern。 | Resolved |
| R-11 | Minor | `infrastructure-specification.md` §五 | Audit logging 方向措辭需更精確（無界改有界的淨效果）。 | 已更正為「移除摧毀全部證據的路徑，代價落在長回溯」。 | Resolved |
| R-12 | Minor | `security-design.md`（nfr-design，非本單元產出） | 審查者未重開問題檔逐字核對 Redis 淘汰策略決定的字面修正。 | 承接者為下一次觸及該節者；本站不代為處理。 | Unresolved |
| R-13 | Minor | `infrastructure-specification.md` §〇 | 多處編號／措辭的小幅不精確（如 S-8 標題初版漏報 CI 側服務數）。 | 已逐項更正。 | Resolved |
| R-14 | Major | `cicd-pipeline.md` §六 6.1 第 23 項 | **本輪撤回被要求的修法，改為撤回順序約束本身。經覆驗：撤回成立。** 實讀 `.github/workflows/ci.yml`：`repo-contract`(`:143`)／`frontend`(`:171`)／`backend`(`:235`)／`docker-build`(`:301`) 四個 job 確認**全部且僅**以 `needs: gate` 為前置，彼此無邊，`push`／`pull_request` 兩種觸發下皆無路徑過濾會讓其中一個 job 跳過而另一個照跑（`ci.yml:7-24` 的 `paths-ignore` 僅排除 `sync-state.json`，不影響這四個 job）。本 repo 既有的 `check:types`（`ci.yml:197`）與 `dump_openapi.py --check`（`:280`）兩道既有 drift gate 確實互相獨立、各自只比對「已 commit 的位元組」，彼此跑的順序從不影響對方的判定正確性——這正是第 22 項新閘門要沿用的同一個形狀。排除的失敗路徑逐一覆驗：(a) 假紅——若 `openapi.json` 被改壞，`dump_openapi.py --check` 與第 22 項各自獨立偵測，不會因為其中一個先跑而讓結論不一致；(b) `workflow_dispatch`／單一 job 重跑——GitHub Actions 的「re-run failed jobs」是對**同一個 commit SHA**重跑，所有 job 檢出的檔案位元組恆一致，不存在「一個 job 看到舊位元組、另一個看到新位元組」的情形；(c) 若產生器實作需要跨步驟的前置產物（如已安裝的 node_modules），那是**同一 job 內的步驟序**（天然循序執行），不需要跨 job `needs:`，文件已正確指出「落在哪個 job 由 runtime 決定」並留給 `code-generation` 回寫。初版原本要求的「必須排在 `dump_openapi.py --check` 之後」這部分論證**不成立且不需要**：它建立在「『隱含於 job 順序』」這句假話上，而四個 job 本來就平行跑，沒有任何隱含順序可言；撤回後也沒有遺留任何未覆蓋的錯誤路徑。 | 無——結論成立，予以採納。 | Resolved |
| R-15 | Minor | `infrastructure-specification.md` §七 7.3 ＋ §〇 S-15 | PBT 適用標的新增（`openapi.json`＋allowlist→工具宣告的產生器）是否與 `unit-of-work.md` 修訂 4 判定表「`U21` 工具 schema 白名單＝不適用」矛盾。逐字核對兩者的受測對象：上游判不適用的是「對既有 schema 的結構斷言」（無輸入空間，不需隨機輸入）；本站新增的是「輸入為任意 OpenAPI 文件 × 任意 allowlist 的轉換函式」（有輸入空間）。兩者是不同的函式/斷言對象，本站的推理站得住，不是把判定硬凹成自己要的結論——它給出了具體的輸入空間差異作為區分依據，而非僅憑斷言。 | 無。 | Resolved |
| R-16 | Major | `infrastructure-specification.md` §〇 | `S-11` 編號被本輪新增的兩列重複使用（與既有「收窄 `nfr-requirements` 指派範圍」那條 `S-11` 撞號），且摘要句「四項」與實際列數不符。覆驗：現行表格已將新兩列改為 `S-13`／`S-14`，另增 `S-15`，既有 `S-11` 原樣保留且未被覆蓋；`grep -c '^\| \*\*S-'` 確認為 7 列，摘要句「七項」逐一列出全部 7 個編號，兩者相符。 | 無。 | Resolved |
| R-17 | Minor | `cicd-pipeline.md` §六 6.1 | 先例引用偏弱（只引「產物進版控」）。覆驗：現行引用改為 `ci.yml:197`「API type contract drift」步驟（內容逐字核對 `run: npm run check:types` 與其上方 6 行註解，位置與內容皆準確）及 `ci.yml:280` 的 `dump_openapi.py --check`（位置與內容皆準確），並正確點名本 repo 既有的「drift gate N of 2」慣例與分置理由（node vs python）。 | 無。 | Resolved |
| R-18 | Minor | `cicd-pipeline.md` §六 6.2 第 27 項 | 「`validate_env_contract.py` 禁止寫入範本」的歸因有誤導性。覆驗：實讀 `scripts/validate_env_contract.py:50-53`，`DEPLOY_DERIVED = {"DATABASE_URL", "VITE_API_BASE_URL"}`，逐字只含兩個具名鍵，確非通用規則。現行文字已改寫為兩條真正理由（無自有 secret；對外目標為同網段服務名可硬寫），並加上「若 `U21` 需要可配置值則 blocking env-contract 規則完整適用」的條件句。 | 無。 | Resolved |
| R-19 | Major | `cicd-pipeline.md` §二「探測的重試窗口與 job 逾時的關係」表（第二列說明欄）與 `infrastructure-specification.md` §四「`DBSIZE`」列 | **大量 `.github/workflows/deploy.yml` 與 `deploy/docker-compose.deploy.yml` 的 `:行號` 引用已過期，幅度與 `nfr-design` review-04 的 `R-29`（已指出該類漂移最多達 227 行）同形，且本輪（已過該次審查之後）仍未修正。** 逐一實測：(1) `rollback` job 的範圍引為 `deploy.yml:169–301`，實際 `rollback:` job 起於 `:395`、止於 `:584`（`notify:` 起於 `:586`）——整段引用偏移約 **190–230 行**；(2) `rollback` job `timeout-minutes: 20` 引為 `:177`，實際在 `:403`；(3) 三個 `if: always()` 步驟引為 `:239`（`Capture the failing deploy log`）／`:249`（`Open a revert PR`）／`:284`（`Hand the failure to the Deploy Doctor`），實際分別在 `:523`／`:533`／`:568`；(4) `deploy` job 的 tunnel 等待迴圈（`seq 1 24`，120s）引為 `:127–139`，實際 `seq 1 24` 在 `:356`。這四組引用與 `nfr-requirements:260822-ra-c2` 系列教訓中反覆記過的「內容對而行號錯」同形——本例連**內容的落點範圍本身**（哪個 job、涵蓋哪些步驟）也因為偏移過大而指向完全不相關的程式碼區段，不只是行號偏差幾行。影響：`§二` 的牆鐘上界不等式（`W = N×(T+5) ≤ 1200 − …`）與其後對 `N=18, T=5/10` 的實測值交叉核對，都需要讀者先找到正確的 job 邊界與既有步驟清單，而文件給的座標會先把讀者帶到 `notify` job 或 `backend.environment` 設定區塊；`infrastructure-specification.md` §四的 `DBSIZE` 列引 `deploy/docker-compose.deploy.yml:20`／`:96` 作為「其現名為 `cloud360_db`」的依據，而該兩行實際內容分別是記憶體上限注釋與 `LLM_MODEL` 環境變數，與 volume 命名無關；真正的命名與改名說明落在 `:47–51`（且該處註解顯示**改名已經落地**：`db_pg18` 宣告名、實際 Docker volume 為 `cloud360_db_pg18`，舊名為 `cloud360_cloud360_db`——不是「本輪將要改名」的未來式）。此外 `infrastructure-specification.md` §二「`ollama pull`」一節引用的機制已可在 `deploy.yml:274` 一帶找到**已上線且逐字相符**的實作（含 R-19(c) 的「模型已在 volume 時 registry 不可達只記 warning」分支），代表本單元此前的設計判斷本身正確、也已被下游忠實實作；問題僅在於本次送審的文件**沒有在交付前重新核對自己引用的座標**，而這正是上游姊妹站（`nfr-design`）審查已明確示警過、要求「下一個依行號操作的人」之前重新核對的同一類風險，本站在繼承這些文字時未重做那一步。 | 在交給 `code-generation` 或任何人依行號操作 `deploy.yml`／`docker-compose.deploy.yml` 之前，重新核對並更新本檔與 `infrastructure-specification.md` 內全部對這兩份檔案的 `<file>:<line>` 引用（含把 `cloud360_db` 的敘述改為「舊名；現已更名為 `cloud360_db_pg18`」而非「即將更名」），或至少在檔首加一句等同於 `nfr-design` `R-29` 的免責聲明，指出行號已知漂移、核對時請先用內容關鍵字定位。 | New |
| R-20 | Minor | `infrastructure-specification.md` §七 7.3「Encryption」列 | 本站第七個服務的 ADR-0006 Encryption 判定只談 in-transit／at-rest 姿態，未在同一列重申 `unit-of-work.md` 修訂 4 對 `U21` 的 Encryption 判定逐字要求的「工具 schema 不得出現任何 `token`／`key`／`secret`／`authorization` 欄位」這一條。**非矛盾**——該要求實質已在同檔 §7.2「認證欄位處置：產生時剝除 `HTTPBearer`」一列被處理，方向正確，只是沒有在 §7.3 的 ADR-0006 判定表內重複指名，造成單獨讀這張判定表的人看不到這一條已被處理。 | 在 §7.3 的 Encryption 列補一句交叉引用 §7.2 的欄位剝除規則，使該判定表自身完整可讀，不需要跳到另一節才能確認這一面已覆蓋。 | New |

### Validation Tool Results

本 stage（`infrastructure-design`，`kind: packaging`）未列出 stage 專屬驗證工具；本輪驗證以直接讀取 repo 現況與結構化檢查 `traceability.json` 取代機械 sensor。

| 工具／檢查 | 結果 | 解讀 |
|---|---|---|
| `traceability.json` 結構完整性 | `upstream_ids` 29 項、`coverage` 29 項、id 完全一一對應、無重複 id、無 `GAP`／`ORPHAN`、狀態僅 `OK`／`N/A`／`Deferred` | 通過，無結構性缺口 |
| `.github/workflows/ci.yml` 四個 job 的 `needs:` 邊（R-14 覆驗） | `repo-contract`／`frontend`／`backend`／`docker-build` 全部且僅 `needs: gate`，無跨 job 邊 | 支持本輪撤回「隱含於 job 順序」此一不成立的宣稱 |
| `.github/workflows/deploy.yml` 行號核對（R-19） | `rollback:` 實際 `:395-584`；`timeout-minutes: 20` 在 `:403`；三個 `if: always()` 步驟在 `:523/:533/:568`；`seq 1 24` 在 `:356` | 文件引用的對應座標（`:169-301`／`:177`／`:239,:249,:284`／`:127-139`）全部與實際不符，偏移約 190–230 行 |
| `deploy/docker-compose.deploy.yml` 現況對照文件描述（S-8／S-9 等） | 服務集合（`db`／`backend`／`redis`／`ollama`／`frontend`／`cloudflared`，6 個，尚無 `mcp-bridge`）、`deploy.resources.limits.memory`、`logging: &json_file_bounded`、`networks: [edge]/[internal]` 均已上線，且實作註解明確引用本單元的 `infrastructure-specification.md §六` 與既有審查編號（R-02 等） | **設計已被忠實實作**，且實作內容與文件敘述的決策（ollama pull 的 warning/紅燈分流、redis `service_healthy` 拓樸等）逐字相符，強化文件可信度 |
| `openapi.json` 結構核對（§7.2） | 42 個 path、55 個 operation、51 個宣告 `security`、`securitySchemes` 僅 `HTTPBearer` | 與文件逐字宣稱一致 |
| `backend/requirements.txt` 對 `mcp` 套件（§6.3） | 零命中 | 與文件「`mcp` 套件不在 `backend/requirements.txt`」的宣稱一致 |
| `scripts/validate_env_contract.py:50-53` 的 `DEPLOY_DERIVED`（R-18 覆驗） | 僅含 `DATABASE_URL`、`VITE_API_BASE_URL` 兩個具名鍵 | 支持本輪對 R-18 歸因更正的覆驗 |

### Summary

本輪覆驗的核心動作——R-14 的刻意撤回——經獨立覆驗成立：`ci.yml` 的四個 job 確實平行、互不依賴，兩道既有 drift gate 本就各自獨立充分，撤回順序約束不會留下任何未覆蓋的假紅或假綠路徑；R-15／R-16／R-17／R-18 的修法逐一開檔核對後也都準確落地。本輪新查出一項 Major（`R-19`）：`cicd-pipeline.md` 與 `infrastructure-specification.md` 對 `.github/workflows/deploy.yml`／`deploy/docker-compose.deploy.yml` 的多處行號引用已大幅漂移（190–230 行），且與姊妹站 `nfr-design` review-04 剛指出過的同一類風險（`R-29`）同形——本站在繼承相關描述時沒有重新核對座標。這不改變任何已核可的架構決定（內容層面的結論，包括已上線的 `ollama pull`、網段分段、探測拓樸，實測皆與文件一致），純屬可快速修正的引用維護問題，不構成架構缺陷；另有一項 Minor（`R-20`）為 ADR-0006 判定表的自身完整性小缺口。全部 Critical／Major 發現（除 R-19 外）均已 Resolved，僅 1 項新 Major 與 1 項既有 Minor（R-12）未解——未達 NOT-READY 門檻，建議在 `code-generation` 前花一次通次修正 R-19 指出的座標。
