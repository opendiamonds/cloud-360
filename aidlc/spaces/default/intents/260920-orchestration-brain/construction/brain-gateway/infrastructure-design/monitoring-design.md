# 監控設計 — `U13 brain-gateway`

> 實作 `../nfr-design/observability-design.md` 的觀測策略。**只用既有 log，不新建管線**：本 repo 沒有指標、告警或集中化 log 管線
> （`project.md ## Deployment` 第 4 點：observability 仍是真實待辦；`brain-infra` 的 `[I3]`=D 不新增 metrics／告警）。
> 以下的「指標」都是**從 log 事件數出來的量**，由維運者以指令查詢，不是常駐的時間序列。
> log 載體：`backend` 容器 stdout（`main.py:25` 的 `logging.basicConfig(level=logging.INFO)`）→ Docker json-file，
> 每容器 50m × 5 檔（`docker-compose.deploy.yml:62-68`）。保存的是**容量**不是**期間**，期間＝容量 ÷ 寫入速率（未量測）。

## 一、Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| 分類前段耗時 `preClassifyMs` | `turn_end` INFO（`NFR13.35`） | P50 ≤ 400 ms（`NFR13.1` (a)） | 記憶預取、認證、Redis `load` 是否吃掉預算 |
| 第一則內容耗時 `toFirstContentMs` | 同上 | P50 ≤ 300 ms（`NFR13.1` (b)） | `U12` 交辦到第一則回覆的膠水時間 |
| `classifyMs` | 同上 | 無本單元門檻（`U11` 的 `NFR3` 擁有） | 歸因：端到端慢時區分是分類還是本單元 |
| 輪次結果分佈 `outcome` | 同上 | `error:INTERNAL_ERROR` 佔比 > 0 即需查原因 | 空 `OPENROUTER_API_KEY`（`OPEN-GW13-7`）與 Redis 故障都表現為此值 |
| 預取結果分佈 `prefetch` | 同上 | `failed`＋`breaker_open`＋`busy_skipped` 持續出現即需查 Ollama | 記憶降級不影響回覆但影響品質，使用者看不出來 |
| 拒絕升級次數（依 `reason`） | `ws_refused` INFO | `global_limit` 出現即表示達每行程上限 200（`NFR13.17`） | 容量訊號；`no_protocol` 偏高通常是舊客戶端（DEMO 殘留）或子協定被代理剝除（`OPEN-GW13-6`） |
| 訊框拒絕次數（依 `reason`） | `frame_rejected` INFO | 單一連線 `count` 持續增加 | 濫用或客戶端錯誤迴圈 |
| 連線生命週期 | `ws_accepted`／`ws_ready`／`ws_closed`（含 `closeCode`） | `ws_accepted` 數遠大於 `ws_ready` 數 → 握手載入失敗（多為 1011） | 區分「進得來但載不起」與「進不來」 |
| 記憶熔斷 | `memory_breaker_open` WARNING／`memory_breaker_close` INFO（`skipped`） | 任何一次開啟 | Ollama 不可用的最早訊號 |
| 記憶執行器滿 | `memory_busy` INFO（每 100 次一筆） | 出現即表示 4 條執行緒長期飽和（`NFR13.5`） | 容量訊號 |

## 二、Alerts

本 repo **沒有告警通道**（`deploy.yml` 的 Slack 通知只針對部署結果，`deploy.yml:734` 起）。下表的「Routes to」如實記載為人工；
建立告警通道是獨立的基礎設施決定，承接站為 Operations 的 `observability-setup`。

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| 入口頁全面失敗 | 連續 N 個 `turn_end` 皆 `outcome=error:INTERNAL_ERROR`（N 由 `observability-setup` 定） | 高 | 人工查 log；第一個要查的是 `OPENROUTER_API_KEY` 與 Redis |
| 子協定透傳失效 | 部署後 `ws_refused reason=no_protocol` 突增、`ws_accepted` 歸零 | 高 | 人工；依 `infrastructure-specification.md` 第 4.4 節三層實測定位 |
| 記憶熔斷開啟 | 出現 `memory_breaker_open` | 中 | 人工；查 `ollama` 容器與模型是否在 volume（`deploy.yml:245` 起的 pull 步驟） |
| 連線上限 | 出現 `ws_refused reason=global_limit` | 中 | 人工；單一行程假設下無法水平擴展（`NFR13.33`），需重新評估架構 |
| 後端啟動失敗 | 容器重啟迴圈且 log 含 `REDIS_` 相關 `KeyError`／`ValueError` | 高 | 部署 job 的資料面探測（`deploy.yml:308` 起）會紅燈並觸發既有 rollback |

## 三、SLIs / SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| `preClassifyMs` P50 | ≤ 400 ms（`NFR13.1` (a)） | `build-and-test` 的一次量測執行（本站無常駐量測；`NFR13.1` 的判定落點即 build-and-test） |
| `toFirstContentMs` P50 | ≤ 300 ms（`NFR13.1` (b)） | 同上 |
| 握手成功率（`ws_ready` ÷ 非 `ws_refused` 的握手） | **本站不設數值**——沒有基線，訂一個沒有人量過的數字等於讓它由猜測決定 | 由 `observability-setup` 在取得部署後基線後設定 |

## 四、Logs & Tracing

- **logger**：`cloud360.brain_gateway`（`NFR13.34`），事件名在前、`key=value` 在後，欄位只限 `observability-design.md` §一的 `_ALLOWED`；
  **不含** token、query string、使用者文字、回覆文字（`NFR13.15`）。
- **關聯**：`turnId` 是一次交辦的關聯鍵，出現在本單元該輪每一筆 log，並傳入 `classify`／`dispatch`（`NFR13.38`）。`U8` 的 `search` log
  不帶 `turnId`（`OPEN-GW13-8` 已結案為接受的殘留）。無分散式追蹤。
- **維運者查詢**（主機上；`deploy.yml:523` 部署後會刪除 `deploy/.env`，故用 `docker logs` 而非需要 `--env-file` 的 `docker compose logs`）：

```text
docker logs --since 1h cloud360-backend-1 2>&1 | grep -E 'cloud360\.brain_gateway:(turn_end|ws_refused|ws_accepted|ws_ready|ws_closed|frame_rejected|memory_breaker_open|memory_breaker_close|episodic_write_failed|memory_busy)( |$)'
docker logs --since 1h cloud360-backend-1 2>&1 | grep 'cloud360.brain_gateway:turn_end ' | grep -o 'outcome=[^ ]*' | sort | uniq -c
docker logs --since 1h cloud360-backend-1 2>&1 | grep 'cloud360.brain_gateway:ws_refused ' | grep -o 'reason=[^ ]*' | sort | uniq -c
```

- **行格式（推論）**：`main.py:25` 的 `basicConfig` 未指定 `format`，Python 預設為 `%(levelname)s:%(name)s:%(message)s`，故一行形如 `INFO:cloud360.brain_gateway:turn_end turnId=… outcome=done …`；上列 grep 依此形狀。若日後改了全域 log 格式，這三條指令要一起改。
- **本機預期的雜訊**：`EMBEDDING_PROVIDER=fulltext` 下每個有交辦的輪次一筆 `episodic_write_failed` WARNING（`observability-design.md` §三揭露）。
- **Dashboard**：不建（無指標後端）。

## 五、上線後第一次要人工確認的事

1. `infrastructure-specification.md` 第 4.4 節的三層實測全部通過，結果記入 `build-and-test`。
2. 以測試帳號在入口頁送一則訊息後，`docker logs` 恰見一筆該 `turnId` 的 `turn_end`，且該行不含所送文字。
3. 握手時 `ws_accepted` → `ws_ready` 成對出現；關閉分頁後出現 `ws_closed`。
4. `docker top cloud360-backend-1` 只有一個 uvicorn 行程（`infrastructure-specification.md` 第七節）。
