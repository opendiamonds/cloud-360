# 告警設定（Alarms）

> 決定來源：`observability-setup-questions.md` [Q4]=C（排程掃日誌＋開 issue＋Slack）、[Q5]=A（本站實作）、[Q6]=B（照上游＋可用性 SLO）。
> 實作：`.github/workflows/brain-health-watch.yml`（判斷）與 `.github/actions/brain-health-alert/action.yml`（通知），測試 `backend/tests/test_brain_health_watch.py`。
> 撰寫時間：2026-11-16T13:46:07Z

## 一、為什麼現在才有通道

上游 17 份 `monitoring-design.md` 的告警 `Routes to` 全部是「無通道」（`U10` 的 `OPEN-N10-4`），而 `construction/brain-infra/infrastructure-design/monitoring-design.md:203-204` 寫明：本站若被 skip，本 intent 完全沒有 metrics 與告警。2026-11-15 staging 大腦每一句都失敗（ADR-0024 記載的 Jev 1.13 400），是使用者自己發現的——本檔關閉 `OPEN-N10-4`。

## 二、告警清單

兩個 job 互不依賴（`scan` 在被監看的主機上讀日誌；`site-probe` 在 GitHub 代管 runner 上從外部打網站），各自管理一則 issue。

| ID | 來源 job | 條件（每小時一次） | 嚴重度 | Routes to | 對應的上游定義 |
|---|---|---|---|---|---|
| `BACKEND_DOWN` | scan | backend 容器狀態不是 `running/healthy`、`running/none`、`running/starting` | P1 | GitHub issue「[brain-health] 大腦服務告警」＋ Slack `C0B5XEQDVR7` | `brain-infra` monitoring-design §六（healthcheck） |
| `TURN_ERRORS` | scan | 1 小時內 `turn_end … outcome=error:*` > 5% 且 ≥ 2 次 | P2 | 同上 | [Q6]=B 的告警門檻（低於 SLO 違反點） |
| `LLM_UNAVAILABLE` | scan | 1 小時內 `error_kind=LlmUnavailable` > 5% 且 ≥ 2 次 | P2 | 同上 | `intent-router` monitoring-design §二 |
| `MALFORMED_ROUTING` | scan | `error_kind=MalformedRouting` ≥ 1 | P2 | 同上 | `intent-router` monitoring-design §二 |
| `MEMORY_DEGRADED` | scan | 1 小時內 `memory_degraded=True` ≥ 3 輪 | P3 | 同上 | `intent-router` monitoring-design §二（記憶持續降級） |
| `PROMPT_GUARD_SURGE` | scan | 1 小時內 `error_kind=PROMPT_GUARD_HIT` ≥ 5 次 | P2 | 同上 | `intent-router` monitoring-design §二 |
| `SLO_7D_BREACH` | scan | 7 天可用性 < 99% 且樣本 ≥ 50 輪 | P2 | 同上 | `slo-config.md` S1 |
| `SITE_DOWN` | site-probe | 重試 3 次後首頁仍非 200 | P1 | GitHub issue「[brain-health] 網站從外部無法使用」＋ Slack | `deploy.yml` 的外部可達檢查 |
| `DATA_PLANE_DOWN` | site-probe | 重試 3 次後 `POST /api/auth/login`（不存在帳號）仍非 401 | P1 | 同上 | `deploy.yml` 的資料面探測（同一個探測帳號） |

**嚴重度只是標註**：本 repo 沒有 on-call 輪值，P1／P2／P3 不對應不同通道。

## 三、通知行為

- **開**：沒有開著的同標題 issue 時開一則，發 Slack。
- **變**：告警組合（排序後的 id，記在 `<!-- brain-health-sig: … -->`）改變時在既有 issue 留言，發 Slack。
- **不變**：組合相同時什麼都不做——不留言、不發 Slack。每小時洗版會讓讀者學會忽略告警。
- **恢復**：告警全部解除時留言「已恢復」並關閉 issue，發 Slack。
- 告警觸發中的 run 以紅燈結束，讓掃 Actions 列表的人也看得到。
- Slack 失敗（`errors: false`）不改變 job 結果，只留 warning；issue 是主要通道。

## 四、與上游定義的偏差（如實記載）

| 偏差 | 上游 | 本站 | 理由 |
|---|---|---|---|
| 時間窗 | `LlmUnavailable` 率「5 分鐘內」 | 1 小時 | 排程最小粒度取每小時；更密的排程會在 self-hosted runner 上每 5 分鐘起一次 job。代價：最長約 1 小時才被通知（11/15 的事故是整天沒人發現，相比仍是大幅改善） |
| `prompt_guard` 按人計 | 「單一 principal 短時間多次」 | 全體 1 小時 ≥ 5 次 | 日誌白名單刻意不含 principal（`SEC-3`／`SEC-5`）；為了告警把 principal 加回日誌會違反安全設計 |
| 反問率異常 | 偏離基準 ±50% 持續 15 分鐘 | **未實作** | 沒有基準值可比；先以 `log-queries.md` Q3 人工觀測，累積兩週資料後再定門檻 |
| 記憶持續降級 | 「連續 N 輪」 | 1 小時內 ≥ 3 輪 | 日誌沒有輪次順序以外的連續性標記，以時間窗內次數近似 |

## 五、ADR-0006 四面向

| 面向 | 判定 | 說明 |
|---|---|---|
| IAM | 適用 | workflow 權限只有 `contents: read`＋`issues: write`（先例 `memory-retention-watchdog.yml`）；`issues: write` 不能改程式碼。Slack 沿用既有 `SLACK_BOT_TOKEN`，**零新增 secret** |
| Encryption | 不適用 | 不新增任何儲存或傳輸路徑；探測走既有 HTTPS |
| Network exposure | 適用 | 外部探測打的是已公開的首頁與登入端點，不新增暴露面；探測帳號不存在，不會登入成功 |
| Audit logging | 適用 | 本 repo 為 public、Actions log 與 issue 公開：日誌只寫進 `RUNNER_TEMP`、從不印出；issue 與 Slack 只含計數、錯誤類別與門檻（`test_minimal_permissions_and_logs_never_printed` 鎖住） |

## 六、測試與突變驗證

`backend/tests/test_brain_health_watch.py`：14 案全綠（含以 11/15 事故形狀的日誌斷言兩條告警會觸發）。

| 突變 | 改動 | 結果 |
|---|---|---|
| H1 | 錯誤率門檻 `>` 改 `>=` | 紅：`test_error_rate_at_exactly_five_percent_does_not_fire` |
| H2 | 拿掉 `MALFORMED_ROUTING` | 紅：`test_one_malformed_routing_fires` |
| H3 | 「至少 2 次」改「至少 1 次」 | 紅：`test_single_error_in_a_quiet_hour_does_not_fire` |
| H4 | 去重失效（永遠留言） | 紅：`test_same_alert_set_does_not_comment_again` |

還原後兩檔 sha256 與基線相同（workflow `ba8f4259e9c7f55b…`、action `f99e71daa9ebe0f9…`），14 案重跑全綠。

## 七、仍未覆蓋（殘餘風險）

- **沒人看守看守者**：GitHub Actions 長時間故障或本 workflow 被停用時兩條路徑同時沉默——與 `memory-retention-watchdog` 的 `OPEN-ID9-1` 同形，接受為殘餘風險。
- **self-hosted runner 離線但網站正常**：`scan` 不會產生 run、`site-probe` 也是綠的。此時不會告警，只能由 Actions 列表缺少 `scan` 的 run 看出。
- **真實執行驗證**：本站合併部署後以一次 `workflow_dispatch` 驗證（[Q5]=A），結果補記於本節。
