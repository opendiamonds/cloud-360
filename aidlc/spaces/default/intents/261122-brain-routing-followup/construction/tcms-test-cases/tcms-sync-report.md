# 驗證關卡與 TCMS 同步報告 — 大腦路由延續回答與架構設計提問狀態

> Intent：`261122-brain-routing-followup`
> **狀態：已同步。** 驗證關卡與 `--dry-run` 預覽於核可關卡呈現，使用者核可後於 2026-11-24T01:10Z 實際寫入 TCMS，結果見 §5。

## 結論

| 項目 | 結果 |
|---|---|
| 第 1 層 機械檢查 | **通過**：本 intent 3／3，ERROR 0、WARN 0；`--all` 27／27，ERROR 0、WARN 0 |
| 第 2 層 語意審查 | **通過**：3 案 × 7 點，無不通過項；4 點附執行注意事項（§2） |
| 手動案例同步預覽 | **完成**：TCMS 恢復後重跑，判定為新增 plan 1 個、新增案例 3 筆、更新 0 筆（§4.1） |
| 自動化案例同步預覽 | **不適用**：工具不支援 Python 測試檔，且後端測試在 TCMS 上沒有案例（§3） |
| 實際同步 | **完成**：新增 plan 1 個（id=56）、案例 3 筆（TC-281～283），更新 0 筆（§5） |

---

## 1. 第 1 層：機械檢查

`--all` 驗的是 `tcms_validate.py` 內建的預設路徑（`260802-last-login-column` 的手動案例與 `frontend/tests/e2e/regression.spec.ts`），**不含本 intent 的檔案**，所以另以 `--file` 驗本檔。兩者都跑：

```
python3 scripts/tcms_validate.py --all
```

```
驗證 27 個案例……
通過 27/27　ERROR 0　WARN 0
機械檢查全數通過。語意正確性仍需 /tcms-verify 的人工審查關卡。
```

```
python3 scripts/tcms_validate.py --file aidlc/spaces/default/intents/261122-brain-routing-followup/construction/tcms-test-cases/manual-test-cases.md
```

```
驗證 3 個案例……
通過 3/3　ERROR 0　WARN 0
機械檢查全數通過。語意正確性仍需 /tcms-verify 的人工審查關卡。
```

兩者 exit 0。沒有 WARN 需要判讀。

機械層管不到、但需要說明的兩點：

- **WebSocket 不在受測介面的機械比對範圍內。** 大腦全部互動走 `/api/brain/ws`，它不在 `openapi.json`（現有 68 個 path，沒有任何一個含 `brain`），寫成 `- API:` 行會被判 ERROR。三案都以一行 `- WebSocket：` 列出它——解析器不認這個行別、不比對，但它讓下一個改 WebSocket 契約的人看得到這三案會受影響。機械層實際比對到的是 `POST /api/auth/login`、`GET /api/auth/me` 與 UI `/`、`/workspace`、`/projects`，全部存在。
- **追溯的 user story 以需求編號代替。** 本 intent 沒有 user-stories 站；驗證器以 `User story[：:]\s*([A-Za-z0-9]+)` 取值，實際取到 `FR2`／`FR1`／`NFR1`，所以沒有「未標註 User story」的 WARN。完整的需求編號（如 `FR2.1、FR2.2、FR2.3`）寫在追溯段落內。

## 2. 第 2 層：語意審查（`/tcms-verify` 七點）

本 intent 沒有 `stories.md`；第 7 點改對照 `inception/requirements-analysis/requirements.md` 的 FR／NFR 驗收條件。

### TC-1：架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖

| # | 檢查 | 判定 | 理由 |
|---|---|---|---|
| 1 | 目的指向會失敗的行為 | 通過 | 指向「徽章為失敗、原因為沒有產出圖」與「圖被改寫」兩個具體失敗；修正前的 staging 真實發生過 |
| 2 | 背景說出症狀、逐字訊息、自動化為何沒抓到 | 通過 | 逐字 `失敗：架構設計：架構圖 #1 架構設計沒有產出圖`；自動化漏抓的理由有兩層且已查證：舊單元測試把「只有提問文字」寫成 `a1_no_xml` 的期望值（`git diff` 可見修正前的斷言），以及真實 A1 何時只回提問由 LLM 決定、e2e 不觸及 LLM |
| 3 | 外人可執行 | 通過，附注意 | 步驟只需瀏覽器。前置條件 1（確認新碼已部署）需 staging 主機 shell；沒有主機權限的執行者須請維運者代跑這一行。A1 是否只回提問不可控，已明定「直接產圖＝前置未達成、換句重跑」，不會被誤判為通過 |
| 4 | 受測介面涵蓋實際碰到的面 | 通過 | 登入 API、入口頁、`/workspace`、WebSocket、OpenRouter 都已列。`/workspace` 載圖會打的圖檔 API 未列——該 API 不是本 intent 改動、只用於比對，判定不影響 |
| 5 | 通過條件二元 | 通過 | 三項同時成立才通過；「前置未達成」明定為重跑而非第三種結論 |
| 6 | 與自動化重複 | 通過 | A-8／A-9 以替身 A1 驗判定與送出的文字；本案驗真實 A1 ＋ 真實閘道 ＋ 真實畫面，自動化層碰不到這一段 |
| 7 | 與需求一致 | 通過 | FR2 驗收第 1 條：完成、無失敗原因、畫面含提問與提示、不含「沒有產出圖」——逐項有步驟；「沒有 PUT」以步驟 7 圖面未變觀察；`sideEffect`、變更紀錄、procedure 記憶在畫面上看不到，由 A-9 承擔 |

### TC-2：回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡

| # | 檢查 | 判定 | 理由 |
|---|---|---|---|
| 1 | 目的指向會失敗的行為 | 通過 | 反問卡出現即失敗；修正前 staging 每一輪都發生 |
| 2 | 背景三件事 | 通過 | 逐字反問卡標題與三個候選文字；自動化漏抓的理由：路由測試全是假 HTTP（LLM 結構性盲區），且本機 `claude-code` 走工具呼叫路徑本來就帶歷程，開發機重現不了 |
| 3 | 外人可執行 | 通過，附注意 | 步驟 1–3 只需瀏覽器；步驟 4 讀 log 需 staging 主機 shell。log 行沒有使用者欄位，已寫明以 `docker compose logs -t` 的時間戳對齊 |
| 4 | 受測介面 | 通過 | 登入 API、入口頁、WebSocket、Decisions API、主機 shell |
| 5 | 通過條件二元 | 通過 | 反問卡有無、交辦對象、log 三欄位與 `caps` 首項，全為可比對的字面 |
| 6 | 與自動化重複 | 通過 | A-1／A-2 只驗請求形狀；本案驗真實模型對該形狀的判讀，另含 R-01（最後一則系統訊息是提示而非提問）這個替身測不到的形狀 |
| 7 | 與需求一致 | 通過 | NFR1 的第七句：「primary 選中 architecture-design，且不觸發反問」——以 `slots=1`、`can_single_out=True`、`caps` 首項 `('architecture-design', 1)` 判定；單槽位時 `caps` 依 `primary` 機率排序、選中者恆第一（ADR-0024 D-5），所以首項即 `primary` 的選擇 |

### TC-3：NFR1 延續規則上線後 ADR-0024 實測六句的路由結果不變

| # | 檢查 | 判定 | 理由 |
|---|---|---|---|
| 1 | 目的指向會失敗的行為 | 通過 | 延續規則可能讓模型把獨立新需求讀成延續（該交辦的變反問）或在空歷程下偏向某能力（該反問的被交辦），兩者都有對應的列 |
| 2 | 背景 | 通過（非回歸案例） | 不是修既有缺陷，是驗證新指示文字的副作用；背景說明了為何替身測不到，以及為何刻意在空歷程下量（隔離單一變因） |
| 3 | 外人可執行 | 通過，附注意 | 需要 staging 主機 shell 與 Redis 存取（清空測試帳號 session）。清空程序只刪 `brain:session:<id>` 這一個 key、以應用程式自己的 ACL 帳號執行，不影響其他使用者；仍屬對 staging 的寫入，須由有權限的維運者執行。前置條件 2 要求測試帳號的可見目錄恰為三個名稱，共用帳號做不到，須用專用帳號 |
| 4 | 受測介面 | 通過 | 含 `GET /api/auth/me`（取 `id`）、`/projects`（核對目錄）、入口頁、WebSocket、Redis |
| 5 | 通過條件二元 | 通過 | 撰寫時抓到並修正一處：第 5 列原寫「成本分析顯示『在等：』架構設計」，那取決於架構設計跑多快，與路由無關；改為以 `data-capability` 判定兩列的能力，狀態不列入判定 |
| 6 | 與自動化重複 | 通過 | 自動化層沒有任何一支會打真實 Decisions API |
| 7 | 與需求一致 | 通過 | NFR1：「六句的路由結果（交辦哪個能力、是否反問、是否指名）與 ADR-0024 實測表一致」——每列都檢查這三項：交辦能力（`caps` 首項或 `data-capability`）、反問（`brain-clarify` 有無、`can_single_out`）、指名（脈絡列是否變動）。第 5 句 `primary` 0.68 低於門檻，但 `wants_design` .81 與 `wants_cost` .98 都過門檻，依 ADR-0024 D-5 走多槽位、不反問，預期值依此寫 |

**語意審查結論：通過。** 三案都需要 staging 主機權限才能完整執行，這是 LLM 路徑與 staging 專屬缺陷的本質，已在各案前置條件寫明，不構成不通過。

## 3. 自動化案例的同步：不適用

依 stage 指示對五支改動的後端測試檔各跑一次 `--spec … --dry-run`：

```
python3 scripts/tcms_sync.py --spec backend/tests/test_intent_routing_decisions.py --dry-run
backend/tests/test_intent_routing_decisions.py 沒有解析到任何規格註解。每個 test 前需要一個含 @purpose／@step 等標記的 /** */ 區塊。
```

其餘四支（`test_intent_routing_context.py`、`test_work_orchestrator_capabilities.py`、`test_work_orchestrator_flow.py`、`test_work_orchestrator_rules.py`）輸出相同，皆在連線 TCMS 之前就以 `SystemExit` 結束。

原因有兩層，任一層都足以讓同步不成立：

1. **工具只認 Playwright 形狀。** `tcms_sync.parse_spec` 只解析 `/** */` 註解區塊、`test.describe('…')` 與 `test('…')`；Python 的 docstring 與 `def test_…` 都不認。
2. **TCMS 上沒有可更新的案例。** `--spec` 只更新、不建立；自動化案例由 `kiwitcms-junit.xml-plugin` 從 CI 的 junit 結果建立。全 repo 只有 `.github/workflows/ui-regression.lock.yml` 會跑這個 plugin，而它上傳的是 Playwright 的 `junit.xml`；CI 的 `backend` job 跑的 `unittest` 結果從未進 Kiwi。

所以本 intent 的 15 個自動化測試**不會出現在 TCMS**，這不是本輪漏做，是既有工具鏈的邊界。規格註解已照撰寫標準補齊（`automation-test-plan.md` §3），日後後端 junit 接上 Kiwi、工具支援 Python 時可直接同步。是否要補上這條管線屬工具鏈決策，不在本 stage 範圍，列為 §6 的觀察項。

## 4. 手動案例的同步預覽（dry-run）

```
python3 scripts/tcms_sync.py --file aidlc/spaces/default/intents/261122-brain-routing-followup/construction/tcms-test-cases/manual-test-cases.md --dry-run
```

執行時間：2026-11-23T16:54Z（`date -u` 取值）。輸出：

```
解析到 3 個案例：
  [P1] 架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖
        plan=Cloud-360 大腦路由延續回答（手動）  text=3591 字元
  [P1] 回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡
        plan=Cloud-360 大腦路由延續回答（手動）  text=3580 字元
  [P1] NFR1 延續規則上線後 ADR-0024 實測六句的路由結果不變
        plan=Cloud-360 大腦路由延續回答（手動）  text=5083 字元

...
xmlrpc.client.ProtocolError: <ProtocolError for tcms.danniel.cc/xml-rpc/: 530 <none>>
```

exit 1。`~/.tcms.conf` 存在；失敗點在登入（`Auth.login`）。另以 `curl` 確認 `https://tcms.danniel.cc/` 與 `/xml-rpc/` 都回 HTTP `530`——這是 Cloudflare 回的「無法連到來源」，表示 TCMS 主機或其 Tunnel 目前不在線，不是憑證或案例檔的問題。

**解析層的預覽已取得**（3 案、plan 名稱、priority、內容長度）；**判定層的預覽未取得**——`--dry-run` 也要先登入，才能比對 TCMS 上既有的 plan 與案例標題，所以目前無法列出「將新增／將更新」。

依案例標題推斷（**非工具輸出**，TCMS 恢復後須以真正的 dry-run 確認）：三個標題都是本 intent 新寫的，預期為**新增 3 筆、更新 0 筆**；plan「Cloud-360 大腦路由延續回答（手動）」預期不存在、會由工具建立，Product 為 `Cloud-360`。

### 4.1 TCMS 恢復後重跑（判定層預覽）

執行時間：2026-11-24T00:22Z（`date -u` 取值）。同一指令，exit 0：

```
[dry-run] plan     將建立 Cloud-360 大腦路由延續回答（手動）
[dry-run] case     將建立 [P1] 架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖
[dry-run] case     將建立 [P1] 回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡
[dry-run] case     將建立 [P1] NFR1 延續規則上線後 ADR-0024 實測六句的路由結果不變

[dry-run] 完成：新增 3 筆，更新 0 筆，共 3 筆
```

解析段（3 案、plan、priority、字元數）與上方第一次輸出逐字相同。判定結果與先前依標題的推斷一致：新增 3 筆、更新 0 筆、plan 由工具建立。

## 5. 實際同步（佔位——核可後填寫）

前置：TCMS 恢復可達（`curl -s -o /dev/null -w "%{http_code}\n" https://tcms.danniel.cc/` 回 `200` 或 `302`），且已重跑 §4 的 dry-run、把真正的「將新增／將更新」輸出貼進本節並在關卡呈現過。

```
python3 scripts/tcms_sync.py --file aidlc/spaces/default/intents/261122-brain-routing-followup/construction/tcms-test-cases/manual-test-cases.md
```

| 項目 | 結果 |
|---|---|
| dry-run 判定層輸出（TCMS 恢復後重跑） | 新增 3 筆、更新 0 筆、建立 plan 1 個（§4.1） |
| 實際執行時間（`date -u`） | 2026-11-24T01:10:28Z（使用者於關卡核可後執行，exit 0） |
| 新增案例數 | 3 |
| 更新案例數 | 0 |
| 落入的 TestPlan（名稱與 id） | Cloud-360 大腦路由延續回答（手動），id=56（本次新建） |
| 各案 TC id | TC-281（只回提問時顯示完成與等你回覆）、TC-282（只打 A 時直接交給架構設計）、TC-283（NFR1 六句路由結果不變） |
| 未同步項目與原因 | 手動案例無。自動化案例不適用，見 §3 |

工具輸出：

```
plan     已建立 Cloud-360 大腦路由延續回答（手動） (id=56)
case     已建立 id=281 架構設計只回提問時工作項顯示完成與等你回覆提示，不標為沒有產出圖
case     已建立 id=282 回答架構設計的選擇題只打 A 時直接交給架構設計，不出現反問卡
case     已建立 id=283 NFR1 延續規則上線後 ADR-0024 實測六句的路由結果不變

完成：新增 3 筆，更新 0 筆，共 3 筆
```

## 6. 未完成項與觀察

| # | 項目 | 狀態 |
|---|---|---|
| 1 | 手動案例同步進 TCMS | **完成**：plan 56、TC-281～283（§5） |
| 2 | 手動案例的判定層 dry-run | **完成**：見 §4.1 |
| 3 | 三個手動案例的實際執行 | 須待本修正部署到 staging 後執行（本分支尚未 commit／合併）；TC-2 與 TC-3 的結果即 requirements NFR1 的量測結果，須寫進本 intent 的紀錄，是 ADR-0025 轉 Accepted 的依據 |
| 4 | O-1（平台竄改預檢被判為等你回覆） | open item，未寫腳本，理由見 `automation-test-plan.md` §5 |
| 5 | 後端 `unittest` 結果不進 TCMS | 觀察項，非本 intent 缺陷：本 intent 的 15 個自動化測試因此在 TCMS 上不可見。補上需同時改 CI（產出 junit 並跑 plugin）與 `tcms_sync.py`（解析 Python docstring），屬工具鏈決策 |
