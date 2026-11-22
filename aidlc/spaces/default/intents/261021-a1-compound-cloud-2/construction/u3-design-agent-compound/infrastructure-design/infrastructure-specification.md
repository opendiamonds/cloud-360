# Infrastructure Specification — U3: u3-design-agent-compound

> Stage: infrastructure-design (3.4) · Phase: Construction · Scope: feature · Depth: Standard
> 建構單元: `u3-design-agent-compound` (kind: `service`)

## 1. 運行規格與資源配置 (Runtime Specifications)
- **環境**: 既有後端 FastAPI 容器 (Docker / Python 3.11-slim)
- **CPU / 記憶體配置**: 預設 1 vCPU, 1GB RAM，足以應對多雲意圖解析與非同步 SSE 串流。
- **網路通訊**: 監聽內部 8000 埠，透過既有反向代理或 Tunnel 暴露。

