# Deployment

> Operations — deployment artifacts index.
> Operations — 部署產出索引。


### 範圍

本目錄記錄 Cloud-360 **self-hosted staging** 部署相關的 AIDLC 產出索引。實作檔案位於：

- `deploy/docker-compose.deploy.yml`
- `deploy/cloudflared/config.yml`
- `deploy/.env.example`
- `.github/workflows/deploy.yml`

決策依據：[`ADR-0007`](../../inception/decisions/0007-self-hosted-deployment-pipeline.md)。  
人工環境變數與 DB seed 說明：[`DEPLOY.md`](../../../../../../../DEPLOY.md)。  
**A3 上線**：[`a3-go-live-checklist.md`](a3-go-live-checklist.md)。

### 待補 artifacts

- 通用部署驗收清單（非 A3）與 rollback 步驟擴寫
- 與 `aidlc-state.md` Operations 區塊同步的 stage-completion summary
