# Observability Setup — 問題檔

> stage 檔要求產出 CloudWatch dashboard、SNS 告警、X-Ray 等設定；本 repo 部署在單台自架 staging（`deploy/docker-compose.deploy.yml`，經 Cloudflare Tunnel 為 `cloud360.danniel.cc`），**沒有** CloudWatch、Grafana、Prometheus 或任何 tracing 套件。依 `project.md`「repo 沒有可掛的監控平台時，不要產出 dashboard 規格」與上游 17 份 `monitoring-design.md` 的一致定調，本站不假裝有那些平台。
> 上游 17 份監控設計把「告警通道」一律記為**無通道**（`U10` 的 `OPEN-N10-4`），並把 dashboard、告警與 SLO 的落點指派給本站（例：`construction/intent-router/infrastructure-design/monitoring-design.md` §五「承接：`observability-setup`」；`construction/brain-infra/infrastructure-design/monitoring-design.md:203-204`「若被 skip，本 intent 完全沒有 metrics 與告警」）。本站要回答的核心是：**告警是否要從「無通道」變成會通知人的機制**。

## 已由上游或規則層定案、不重問

### Q1 — dashboard 怎麼呈現？

- A. 不產出 dashboard 規格；指標定義照上游，消費方式為以 `log-queries.md` 的查詢在主機或排程工作上算出
- B. 引入 Grafana／Prometheus 並畫 dashboard
- C. 改用 CloudWatch

[Answer]: A <!-- 來源：`project.md` `## Corrections`「repo 沒有可掛的監控平台（無 Grafana／CloudWatch 等）時，不要產出 dashboard 規格」；`construction/intent-router/infrastructure-design/monitoring-design.md` §五；B／C 屬新增基礎設施，依 `project.md` `## Scope Overrides` 需新 ADR -->

### Q2 — 分散式 tracing？

- A. 不引入 tracing 套件；以 `turn_id` 串接同一行程內的大腦 → 路由 → 編排 → 能力 agent 日誌
- B. 引入 OpenTelemetry
- C. X-Ray

[Answer]: A <!-- 來源：`construction/intent-router/infrastructure-design/monitoring-design.md` §四「Tracing：不引入任何套件……該鏈四跳全部同進程」及其重審觸發條件（鏈路變成跨進程時重做） -->

### Q3 — 日誌聚合與保留？

- A. 沿用容器 stdout → Docker `json-file`，每容器 `max-size: 50m`、`max-file: 5` 輪替；不另訂保留天數
- B. 引入集中式日誌（ELK／Loki）
- C. 另訂固定保留天數

[Answer]: A <!-- 來源：`deploy/docker-compose.deploy.yml:69-75`（`&json_file_bounded`）；`construction/brain-infra/infrastructure-design/monitoring-design.md` §五；`construction/intent-router/infrastructure-design/monitoring-design.md` §四「訂一個沒有機制執行的保留期是宣告而非控制」 -->

## 需要使用者決定

### Q4 — 告警要送到哪裡？

背景：上游五個單元的告警（例：路由層 `LlmUnavailable` 率 5 分鐘 > 5%、`MalformedRouting` 任何一次、記憶持續降級）全部寫「無通道」。2026-11-15 staging 大腦**每一句都失敗**（Jev 1.13 改為決策模型），就是在沒有任何告警的情況下由使用者自己發現的。repo 內可沿用的先例有兩個：`memory-retention-watchdog.yml`（排程 Actions，異常時開 GitHub issue）與 `deploy.yml` 的 Slack 通知（`SLACK_BOT_TOKEN`）。依 `project.md` `## Forbidden`，無人值守的自動化一律以 GitHub Actions／gh-aw 承載，不得放在 repo 內的腳本。本 repo 為 public、Actions log 公開，排程工作只能印計數與錯誤類別，不得印對話內容。

- A. 維持無通道：只寫 `log-queries.md`，由人在需要時登入主機查
- B. 新增排程 Actions 工作（self-hosted runner，每小時），掃描後端日誌算出計數，超過門檻時開或更新一則 GitHub issue（比照 `memory-retention-watchdog`）
- C. 同 B，另外以既有的 `SLACK_BOT_TOKEN` 送一則 Slack 訊息
- D. 引入監控平台（Prometheus＋Alertmanager 等）；需新 ADR

[Answer]: C <!-- 2026-11-16T13:40:41Z 使用者以選單選定「排程掃 log＋開 issue＋Slack」 -->

### Q5 — 若 Q4 選 B 或 C，要在本站就實作嗎？

- A. 本站就寫出 workflow 與測試、開 PR，合併部署後以一次手動觸發驗證
- B. 本站只產出規格（門檻、查詢、issue 格式），實作開成後續工作
- C. 不適用（Q4 選 A 或 D）

[Answer]: A <!-- 2026-11-16T13:40:41Z 使用者以選單選定「這一站就實作」 -->

### Q6 — SLO 怎麼訂？

背景：`phases/operation.md` 要求 SLO 以具體百分比與時間窗量化，且告警門檻要低於 SLO 違反點。上游刻意只訂兩個：路由層 `classify` P50 ≤ 800 ms（`NFR3.60`）、意圖識別準確率 ≥ 80%（`NFR1`，離線、無實證基礎的初版值）；分類成功率標為「無 SLO，只觀測」，理由是失敗多在供應商側（`construction/intent-router/infrastructure-design/monitoring-design.md` §三）。

- A. 照上游：只有這兩個 SLO，分類成功率只觀測
- B. 照上游，另加一個使用者感受的可用性 SLO：大腦對話輪次「非錯誤結束」比率 ≥ 99%，7 天滾動，由 Q4 的排程工作量測；告警門檻設在 1 小時內錯誤率 > 5%
- C. 先不訂任何 SLO，等有監控平台再訂

[Answer]: B <!-- 2026-11-16T13:40:41Z 使用者以選單選定「照上游＋加可用性 SLO」 -->
