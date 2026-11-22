# Observability Design — u1-iac-api

> Q4=A／Q6 NFR · 暫無 metrics／OTel。

## request_id（Q4=A）

1. 讀取入站 `X-Request-ID`（若專案已有慣例頭則對齊既有名稱）。  
2. 缺省 → 生成 UUID。  
3. 綁定 logging contextvar／middleware；錯誤回應可回顯同 id（無密文）。

## 日誌模式

| 事件 | 必填欄位 |
|---|---|
| request_end | request_id, user_id, diagram_id, route, status, error.code?, duration_ms |
| generate_end | 同上＋model?, llm_ms?, token_est? |
| checkov_end | 同上＋exit_code?, checkov_ms? |

## 關聯到 UI

- U2 顯示 `error.code`；支援人員用 request_id 對 log。
- **不做** Prometheus／OTel（NFR Q6=A）。

<!-- confirmed: Looks correct -->
