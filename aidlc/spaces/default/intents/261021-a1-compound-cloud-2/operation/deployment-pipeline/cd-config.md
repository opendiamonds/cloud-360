# CD Configuration — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: deployment-pipeline (4.1) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 持續部署 (CD) 架構

依據專案架構決定（ADR-0007），持續部署設定如下：
- **觸發條件**: PR 通過測試審核後 Squash Merge 至整合主幹 `ut` 分支。
- **工作流檔案**: `.github/workflows/deploy.yml`。
- **目標環境**:
  - 自有主機 Staging (`192.168.10.10`)。
  - 經 Cloudflare Tunnel 對外安全暴露為 `cloud360.danniel.cc`。
  - 公有雲生產環境嚴格在 Out of Scope（ADR-0001, ADR-0002），無生產環境自動發布風險。

---

## 2. 部署流程矩陣

```yaml
name: Deploy to Staging
on:
  push:
    branches: [ ut ]

jobs:
  deploy:
    name: Build & Deploy Container
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and Push Docker Image
        run: |
          docker build -t cloud360-app:${{ github.sha }} .
      - name: Deploy to Staging Host
        run: |
          # 經由 SSH / Tunnel 部署至 192.168.10.10
          docker-compose pull && docker-compose up -d
```

