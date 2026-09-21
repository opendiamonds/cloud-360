# Deployment Log — C1 估價上傳改版

> 時間：2026-09-19T20:30:00Z · 決定：Q1=A（不在本 stage 強制 redeploy）

## 目標環境

| 項目 | 值 |
|---|---|
| Staging URL | `https://cloud360.danniel.cc` |
| 管線 | `.github/workflows/deploy.yml`（`workflow_dispatch`／合併觸發） |
| Compose | `deploy/docker-compose.deploy.yml` + `deploy/render-env.sh` → `deploy/.env` |
| 主機 | 私網 `192.168.10.10`（Cloudflare Tunnel，ADR-0007） |

## 本輪執行

1. 確認 `deployment-pipeline`／`environment-provisioning` 為 SKIP → 使用 workspace 既有 CD。  
2. **未**執行 `gh workflow run`：construction 產物仍在本機 worktree，未經 `ut` 合併；強制部署會上線過期／不完整映像。  
3. 對現行 staging 做 HTTP 健康探測（見 `health-check-report.md`／`smoke-test-results.md`）。  

## 後續部署步驟（人工）

```bash
# 合併本 intent 變更至 ut 後
gh workflow run deploy.yml
# 或依 repo 慣例推送觸發
```

## Rollback

既有 `deploy.yml` 失敗自癒／手動 `workflow_dispatch` 回上一綠 commit；細節見 `DEPLOY.md`。

<!-- Post-confirmation save -->
