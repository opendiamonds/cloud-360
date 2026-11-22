# 日誌查詢（Log Queries）

> 本 repo 沒有 CloudWatch Logs Insights 或任何日誌平台（[Q1]=A、[Q3]=A）。以下是在 staging 主機（`192.168.10.10`）上直接對容器日誌執行的查詢，也是 `brain-health-watch.yml` 計數所用的同一組 pattern。
> **公開紀律**：這些指令的輸出可能含 `turnId`、錯誤碼，但不含對話內容（日誌欄位白名單）。仍**不得**把原始輸出貼進 public repo 的 issue、PR 或 Actions log；只貼計數。

前置：`B=cloud360-backend-1`、`W=1h`（可改 `24h`、`168h`）

### Q1 — 對話輪次依結果分組（S1、`TURN_ERRORS`、`SLO_7D_BREACH`）

```bash
docker logs "$B" --since "$W" 2>&1 | grep -oE 'turn_end turnId=.* outcome=[^ ]+' \
  | grep -oE 'outcome=[^ ]+' | sort | uniq -c | sort -rn
```

### Q2 — 路由層錯誤類別（`LLM_UNAVAILABLE`、`MALFORMED_ROUTING`）

```bash
docker logs "$B" --since "$W" 2>&1 | grep -oE 'intent routing turn=.*' \
  | grep -oE 'error_kind=[A-Za-z_]+' | sort | uniq -c | sort -rn
```

對照 OpenRouter 狀態與 `docker exec "$B" printenv BRAIN_ROUTER_MODEL`（應為 `typesafe/jev-1.14`，ADR-0024）。

### Q3 — 反問率與槽位數分佈（`intent-router` 指標，人工觀測）

```bash
docker logs "$B" --since "$W" 2>&1 | grep -oE 'intent routing turn=.*' \
  | awk '{for(i=1;i<=NF;i++){split($i,a,"="); if(a[1]=="can_single_out") c[a[2]]++; if(a[1]=="slots") s[a[2]]++}}
         END{for(k in c) print "can_single_out="k, c[k]; for(k in s) print "slots="k, s[k]}'
```

`slots` 長期恆為 1 是異常訊號：代表多意圖路徑在線上是死碼（`intent-router` monitoring-design §一）。

### Q4 — 路由耗時分位數（S2）

```bash
docker logs "$B" --since "$W" 2>&1 | grep -oE 'intent routing turn=.* elapsed_ms=[0-9]+' \
  | grep -oE 'elapsed_ms=[0-9]+' | cut -d= -f2 | sort -n \
  | awk '{a[NR]=$1} END{if(NR) printf "n=%d P50=%d P95=%d\n", NR, a[int(NR*0.5)+1], a[int(NR*0.95)+ (NR*0.95==int(NR*0.95)?0:1)]}'
```

### Q5 — 安全事件（`PROMPT_GUARD_SURGE`、握手與重驗）

```bash
docker logs "$B" --since "$W" 2>&1 \
  | grep -oE 'error_kind=PROMPT_GUARD_HIT|handshake_auth_failed|ws_revoked [^ ]+ closeCode=[0-9]+|revalidate_failed' \
  | sed -E 's/connId=[^ ]+ //' | sort | uniq -c
```

### Q6 — 記憶與工作項的降級訊號（`MEMORY_DEGRADED`）

```bash
docker logs "$B" --since "$W" 2>&1 \
  | grep -oE 'memory_degraded=True|memory_breaker_(open|close)|persist_put_timeout|semantic_write_failed' \
  | sort | uniq -c
```

事件發出位置：`memory_breaker_open`（`backend/services/brain_gateway.py:482`）、`persist_put_timeout`（`backend/services/work_orchestrator.py:798`）、`turn_end`（`brain_gateway.py:1330-1339`）、`intent routing turn=`（`backend/services/intent_routing.py:310`）。
