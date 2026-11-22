# Reliability Requirements — U3: u3-design-agent-compound

> Stage: nfr-requirements (3.2) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 可靠度 (Reliability Targets)
- **JSON 解析自動重試**: 格式錯誤自動觸發 1 次自我修正重試。
- **優雅降級**: 超出重試上限回傳清楚錯誤訊息，不造成服務 process 崩潰。

