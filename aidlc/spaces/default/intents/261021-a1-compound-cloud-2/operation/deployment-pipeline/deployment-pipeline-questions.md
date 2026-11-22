# Deployment Pipeline Questions & Clarifications

> Stage: deployment-pipeline (4.1) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 部署管線確認事項

- **Staging 部署邊界**: 維持透過 `deploy.yml` 部署至自有 Staging 主機 `192.168.10.10`（Cloudflare Tunnel `cloud360.danniel.cc`）。
- **無生產發布風險**: 公有雲 Production 維持 Out-of-Scope。

---

## Consolidated Summary Confirmation

在依據上述內容產出部署管線設定產物前，請確認以下彙整摘要正確無誤：

- **CD 管線架構**: PR 合併至 `ut` 觸發 Staging 自動建置與部署。
- **發布與回退策略**: 零 Schema 變更之滾動部署，具備即時映像檔回滾與 Git revert 手冊。

Does this all look correct before I generate the deployment pipeline artifacts?
- Looks correct
- Request changes

[Answer]: Looks correct

