# Operations Runbooks — Cloud-360

- Status: Living document（隨故障累積更新）
- Scope: 自有 staging 環境 `192.168.10.10` / `cloud360.danniel.cc`（見 ADR-0007）
- Related: [[0008-continuous-construction-operations]]、`aidlc/spaces/default/memory/project.md` 的 `## Deployment`

補齊 ADR-0008 點名的 Operations 待辦：本文件涵蓋 **SLO**、**observability 現況**、**incident playbooks**。每一則 playbook 都對應本專案實際發生過或明確可能的故障。

### 1. Service Level Objectives（staging 等級）

| 指標 | 目標 | 量測方式 |
|---|---|---|
| `cloud360.danniel.cc` 可用性 | 週內 ≥ 99%（staging，非 production SLA） | 外部探測 `GET /`（見第 2 節） |
| Deploy 成功率 | ≥ 90% 的 merge-to-ut 部署綠燈 | `Deploy` workflow 成功率 |
| Deploy 失敗復原 | 失敗後 self-heal（rollback + revert PR + Deploy Doctor）自動觸發 | 見 playbook C |
| UI 回歸 | PR 上 6/6 通過才可 merge | UI Regression workflow |

> 這是 staging 目標，非對外承諾。production SLA 不在範圍（ADR-0007）。

### 2. Observability 現況

**現有（不需額外工具）**：
- **容器健康檢查**：`db` / `backend` / `frontend` 皆有 compose healthcheck；`docker compose ps` 一眼看 healthy。
- **部署健康檢查**：`deploy.yml` 內建兩段（內網 8090 + 公開網址），失敗即擋 + 觸發 self-heal。
- **CI 關卡**：每 PR 的 contract / lint / build / docker / UI 回歸。
- **每日彙整**：Daily Digest agentic workflow 彙整 CI/deploy/agent 狀態（進 main 後啟用）。

**指標與儀表板（已建，於 dc-infra 維運）**：Prometheus + Grafana + blackbox + cAdvisor + node-exporter，中心在 192.168.10.10，儀表板在 `https://grafana.danniel.cc`（見 dc-infra `services/monitoring/`）。
- 主機指標：10.10 與 20.8（複用 20.8 現有 node-exporter）
- 容器指標：cAdvisor
- **主動外部探測**：blackbox 定時探 `cloud360.danniel.cc` / `tcms.danniel.cc` 的存活、延遲、TLS 到期 —— 這就是第 1 節可用性 SLO 的量測來源。

**尚缺**：主動告警（服務掛掉主動 push 通知）。Grafana 已備妥 Telegram 告警管道的接線，只差一把 bot token；設定後在第 4 節補上實際告警規則與路由。

### 3. Incident Playbooks

每則格式：**症狀 → 判斷 → 處置 → 驗證**。所有指令在 `192.168.10.10`（`~/deploy/cloud-360` 為 compose 目錄）。

#### A. 網站回 Cloudflare Error 1033

- **症狀**：瀏覽器顯示 `Error 1033 Cloudflare Tunnel error`。
- **判斷**：tunnel 沒連上。cloud360 的 cloudflared 是 **compose 容器**（`cloud360-cloudflared-1`），非 systemd。
- **處置**：
  ```bash
  docker ps -a --filter name=cloud360-cloudflared   # 看是否 Restarting
  docker logs cloud360-cloudflared-1 --tail 30       # 找 "permission denied" 等
  # 憑證權限問題（歷史故障）：compose 已設 user: "1000:1000"，確認憑證檔存在且可讀
  ls -l ~/.cloudflared/b460a579-9e0d-42f1-a31d-c84d35bef065.json
  docker compose -f deploy/docker-compose.deploy.yml --env-file deploy/.env up -d cloudflared
  ```
- **驗證**：`curl -fsS -o /dev/null -w "%{http_code}" https://cloud360.danniel.cc/` → 200。

#### B. 網站回 502（tunnel 通但 origin 連不到）

- **症狀**：HTTP 502。
- **判斷**：tunnel 連上了，但打不到後面的服務。歷史故障：port 對映錯（服務內部聽的 port 與對映不符）。
- **處置**：
  ```bash
  docker compose -f deploy/docker-compose.deploy.yml ps        # frontend 是否 healthy
  curl -sk -o /dev/null -w "%{http_code}" http://127.0.0.1:8090/  # 本機直打 nginx
  docker compose -f deploy/docker-compose.deploy.yml logs frontend --tail 40
  ```
- **驗證**：本機 8090 回 200 後，公開網址即恢復。

#### C. Deploy 失敗

- **症狀**：`Deploy (ut → 192.168.10.10)` workflow 紅。
- **判斷 + 處置**：**多半不需手動** —— rollback job 會自動把服務滾回 last-good、開 revert PR、並叫 Deploy Doctor 開 issue 分析根因。先看那張 issue。
- **人工介入時機**：last-good 不存在（首次部署就失敗）→ 讀 Deploy Doctor issue，修 root cause 後重推。
- **驗證**：`https://cloud360.danniel.cc/` 回 200，且 `docker compose ps` 全 healthy。

#### D. 憑證外洩 / 預設密碼可登入

- **症狀**：可用已知/預設帳密登入（歷史故障：`admin/admin123`）。
- **處置**：立即改密碼（bcrypt，與 auth.py 同套）：
  ```bash
  NEW=$(openssl rand -base64 15 | tr -d '/+=' | head -c 20)
  H=$(docker exec cloud360-backend-1 python -c "import bcrypt;print(bcrypt.hashpw('$NEW'.encode(),bcrypt.gensalt()).decode())")
  docker exec cloud360-db-1 psql -U postgres -d cloud360 -c "UPDATE users SET password_hash='$H' WHERE username='admin';"
  ```
- **根治**：見 issue #425（schema 不應內建明文預設密碼）。
- **驗證**：舊密碼登入回 401、新密碼回 200。

#### E. 資料庫容器 unhealthy

- **症狀**：`cloud360-db-1` 非 healthy；backend 起不來。
- **處置**：
  ```bash
  docker compose -f deploy/docker-compose.deploy.yml logs db --tail 50
  docker compose -f deploy/docker-compose.deploy.yml restart db
  ```
- **注意**：`schema_rbac.sql` 只在**空 volume** 首次初始化跑；既有資料不會被重播。切勿刪 `cloud360_db` volume（會清空資料且 admin 回到預設密碼）。

#### F. Self-hosted runner 離線

- **症狀**：CI/deploy 卡在 queued；`cloud360-10-10` 顯示 offline。
- **處置**：
  ```bash
  sudo systemctl status actions.runner.opendiamonds-cloud-360.cloud360-10-10.service
  sudo systemctl restart actions.runner.opendiamonds-cloud-360.cloud360-10-10.service
  ```
- **注意**：10.10 上另有 `dev-platform` 的 runner，勿誤動。

#### G. 磁碟接近滿

- **症狀**：部署/build 失敗於 no space。10.10 跑多個服務。
- **處置**：`docker system df` 看用量 →  `docker image prune -f` / `docker builder prune -f`（勿 `-a --volumes`，會誤刪其他服務資料）。

### 4. 告警去向

**一律送 Slack `#nemoclaw`**（channel ID `C0B5XEQDVR7`，bot `NeMoClaw`）。取代原先「優先送 Telegram」的規劃，理由是部署通知已於 2026-07-25 落地於同一頻道，告警與部署事件集中在同一處才看得到完整時序。

| 告警來源 | 現況 | 觸發條件 |
|---|---|---|
| 部署成功／失敗／回滾 | ✅ 已上線（`deploy.yml` 的 `notify` job） | deploy job 實際執行後 |
| 站台可用性 | ⏳ 待建（見 issue #467） | 外部 blackbox 探測連續失敗 |
| Self-hosted runner 離線 | ⏳ 待建（見 issue #467） | runner `status=offline` |

**關鍵限制**：`notify` job 掛在 `deploy` 之後，job 卡在 `queued`（runner 離線）時整條 workflow 不執行，因此**無法**回報「部署未開始」或「站台不可用」。這兩類必須由 192.168.10.10 **之外**的探測發出 —— 該機失效時發不出自己失效的警報（2026-07-26 事件已驗證，見 `audit.md`）。

站台可用性與 runner 探測實作於 dc-infra repo（見 ADR-0007 的 repo 邊界）。
