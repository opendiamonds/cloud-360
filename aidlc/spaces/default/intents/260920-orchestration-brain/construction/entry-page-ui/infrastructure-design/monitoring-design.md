# Monitoring Design — `U14 entry-page-ui`

> 撰寫時間 2026-10-17T04:41:16Z（`date -u` 取值）。
>
> 本單元**不交付任何 metrics 收集、告警規則或 SLI／SLO**。本 repo 沒有指標後端、告警通道或集中化 log（`U10` 登記的 `OPEN-N10-4`；
> `U13` 的 `monitoring-design.md` 開頭同一事實），本站沿用、不另立同義缺口。把「有 log」寫成「有監控」是本 repo 已記過的失敗形狀，
> 本檔只列**今天實際存在**的可觀測面，以及本單元在其上新增或改變的部分。後端大腦連線的事件（`ws_accepted`、`ws_ready`、`ws_closed`、`ws_refused`、`turn_end`）
> 屬 `U13`，正本在 `../../brain-gateway/infrastructure-design/monitoring-design.md`，本檔只引用、不重抄。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `../nfr-design/security-design.md` | §二之二（`work_target_names_failed` 只記 `connId`、例外類別名；被拒的查詢不記）、§六之五（前端 `console.*` 欄位限制） |
| `../nfr-design/performance-design.md` | §三（名稱查詢的語句數上界）、§一之三（握手預算） |
| `../nfr-requirements/security-requirements.md` | `EPN-14`、`EPN-16` |
| `../../brain-gateway/infrastructure-design/monitoring-design.md` | 後端 log 的行格式與查詢指令、`ws_refused` 的 `reason` 值 |

## 一、今日的可觀測面（本單元相關的完整清單）

| # | 訊號 | 產生點 | 去向與保留 | 本單元的變化 |
|---|---|---|---|---|
| 1 | `U13` 的連線與輪次事件（`ws_accepted`／`ws_ready`／`ws_closed closeCode=…`／`ws_refused reason=…`／`turn_end outcome=…`） | logger `cloud360.brain_gateway` | backend stdout → docker `json-file`，每服務 50m × 5 依**容量**輪替（`deploy/docker-compose.deploy.yml:62-68`） | 本單元上線後才有真實瀏覽器流量；在此之前這些事件只來自實測腳本 |
| 2 | **新增**：`work_target_names_failed`（WARNING，欄位只有 `connId`、`exc`） | `BrainGateway._names_for` 吞下任何例外時（`EPN-07`、`EPN-14`） | 同第 1 項 | 名稱查詢失敗**不**影響握手、扇出與交辦，畫面只是顯示「（無法顯示名稱）」——所以這筆 WARNING 是該故障唯一的伺服器端痕跡。`HierarchyForbidden` 是否記 log 由 code-generation 依 nfr-design 帶入項 `R-04`（建議不記）定案 |
| 3 | nginx 與 uvicorn 的 access log | nginx 映像預設 access log；uvicorn 預設開啟（`backend/Dockerfile:30` 未加 `--no-access-log`） | frontend／backend 各自的 `json-file` | WS 升級在 access log 只留路徑 `/api/brain/ws`：token 在子協定標頭、不在網址（`EPN-16`），故**不落地**。nginx 預設格式不記請求標頭（`frontend/nginx.conf` 無自訂 `log_format`，`grep -c access_log` 為 0） |
| 4 | 前端 `console.*` | 新增的連線 hook 與元件 | 不保留（瀏覽器 session） | 只帶 `type`、`code`、關閉碼、turnId；不含使用者文字、名稱、token（`EPN-14`，e2e 以 `page.on('console')` 斷言） |
| 5 | CI 結果 | `ci.yml`、`ui-regression` → Kiwi TCMS | GitHub Actions log；Kiwi 保留每次執行的結果 | 新 e2e 進 Kiwi；既有 14 個測試的處置見 `cicd-pipeline.md` §三之二 |
| 6 | 部署步驟 6a 的結果（`[EPI1]`=A，失敗即擋部署） | `deploy.yml` | Actions log（公開）；失敗時另見 `rollback` 與 Slack 通知 | 輸出只含狀態列與協定名，不含 token；每次部署在 backend log 留下一筆 `ws_closed` 的 `closeCode=4401`、`connId` 為空——**這是預期的雜訊**，查 4401 時要扣掉部署時間點那一筆 |

## 二、Metrics & KPIs — **本單元不交付 metrics 收集**；下列為可由 log 人工數出的量

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| 名稱查詢失敗次數 | 第 2 項 | 部署環境**任何一次**出現即需查原因 | 正常情況下不該發生；持續出現代表 DB 或授權異常，而畫面上只是靜靜地顯示「（無法顯示名稱）」 |
| 終止性關閉碼分佈 | 第 1 項的 `ws_closed closeCode=` | `4403` 持續出現 → 有人 `K1` 被撤銷但前端仍嘗試（應為每頁至多一次 `refreshMe()` 後停止，`EPN-03`） | 驗證 4403 不再形成重連迴圈（`security-design.md` §六之二） |
| 握手限流 | 第 1 項的 `ws_refused reason=handshake_rate` | 部署重啟後短暫出現可接受；平時出現代表某使用者開了超過宣告支援的 3 個分頁或前端退避失效 | `performance-design.md` §一之三 的預算是否被打穿 |
| 協定名缺漏 | 第 1 項的 `ws_refused reason=no_protocol` | 部署後突增且 `ws_accepted` 歸零 → 子協定在某一跳被剝除（`OPEN-EP14-13`） | 入口頁全面不可用的最早伺服器端訊號 |
| 首字回應 P50（`NFR3`，≤ 2 秒） | `U13` 的 `turn_end`（`toFirstContentMs` 等欄位） | 由 `build-and-test` 的一次量測判定 | 本單元在交辦關鍵路徑上新增的名稱查詢成本為常數（`NFR3.141`，語句數由 unittest 鎖住） |

## 三、Alerts — **本單元不交付告警規則**

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| （無） | — | — | 通道不存在（`OPEN-N10-4`） |

值得告警但目前無處可送的訊號（登記供 `OPEN-N10-4` 關閉時一併接上，不新開缺口編號）：① 部署後 `no_protocol` 突增；② `work_target_names_failed` 出現；
③ `4403` 在同一 `connId` 以外的大量新連線上反覆出現。第 ① 項的「部署當下」那一半已由步驟 6a 以擋部署的形式承接（`[EPI1]`=A）。

## 四、Logs & Tracing

- **logger 與欄位**：沿用 `cloud360.brain_gateway` 與既有欄位白名單 `_ALLOWED`（`backend/services/brain_gateway.py:130`）；本單元**不新增欄位**，只新增事件名 `work_target_names_failed`（`EPN-14`）。
- **維運者查詢**（在 `192.168.10.10`；部署後 `deploy/.env` 已被刪除，故用 `docker logs` 而非需要 `--env-file` 的 `docker compose logs`，與 `U13` 相同）：

```text
docker logs --since 1h cloud360-backend-1 2>&1 | grep -c 'cloud360.brain_gateway:work_target_names_failed '
docker logs --since 1h cloud360-backend-1 2>&1 | grep 'cloud360.brain_gateway:work_target_names_failed ' | grep -o 'exc=[^ ]*' | sort | uniq -c
docker logs --since 1h cloud360-backend-1 2>&1 | grep 'cloud360.brain_gateway:ws_closed ' | grep -o 'closeCode=[^ ]*' | sort | uniq -c
```

  行格式依 `U13` 的推論（`main.py:25` 的 `basicConfig` 未指定 `format`，預設 `%(levelname)s:%(name)s:%(message)s`）；若全域 log 格式改變，這三條要一起改。
- **關聯**：本單元不引入 request id。前端 `console` 的 turnId 與後端 `turn_end` 的 `turnId` 是同一個值，可人工對齊；無分散式追蹤。
- **Dashboard**：不建（無指標後端）。

## 五、SLIs／SLOs — **本單元不交付**

| SLI | SLO target | Measurement window |
|---|---|---|
| （無） | — | — |

`phases/operation.md` 要求 SLO 量化到百分比與時間窗，而本單元既無常駐量測也無告警通道；寫一個量不到的 SLO 只會製造「已定義」的假象。
`NFR2`（跨頁面上下文保留率）與 `NFR3`（首字回應）的判定落點是 `build-and-test` 的量測，不是本站。握手成功率的 SLO 由 `U13` 交 `observability-setup` 在取得基線後設定，本單元不另訂。

## 六、可量測與不可量測（照實）

| 事項 | 可量測？ | 方式／原因 |
|---|---|---|
| Cloudflare 兩跳的協定名透傳 | **每次部署自動**（`[EPI1]`=A，失敗即擋部署） | `cicd-pipeline.md` §二之一、§五之二 第 3 步 |
| Cloudflare 兩跳的 `bearer.` 項透傳 | **只能人工** | 需要有效 token（`cicd-pipeline.md` §五之二 第 1 步） |
| 瀏覽器實際能連上入口頁 | **只能人工** | `cicd-pipeline.md` §五之二 第 4 步 |
| 部署重啟期間使用者的重連表現 | **只能人工** | `cicd-pipeline.md` §五之二 第 7 步；後端不可用時長無量測來源 |
| 名稱查詢故障 | 可（人工查 log） | 第 2 項；前端無從區分「不可見」與「查詢失敗」（刻意逐位元相同，`EPN-12`） |
| 每分頁連線數 ≤ 1 | 只在 CI | e2e 以 `page.on('websocket')` 計數（`EPN-01`）；正式環境無收集 |
| 對話紀錄是否外洩到瀏覽器儲存 | 只在 CI | e2e 比對鍵集合（`EPN-13`） |
