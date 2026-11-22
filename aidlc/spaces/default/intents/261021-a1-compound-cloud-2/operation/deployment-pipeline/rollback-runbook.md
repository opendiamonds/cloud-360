# Rollback Runbook — A1 混合雲繪圖功能 (Compound Cloud)

> Stage: deployment-pipeline (4.1) · Phase: Operation · Scope: feature · Depth: Standard
> Intent: `261021-a1-compound-cloud-2`

---

## 1. 回退觸發條件 (Rollback Triggers)

部署至 Staging 後，若發生以下任一情形，即刻啟動回退程序：
1. 前端畫布載入失敗或拋出全域 JavaScript 例外（HTTP 500 / Sentry Alert）。
2. 後端容器啟動健康檢查（Health Check `/health`）連續 3 次失敗。
3. 產生架構圖 XML 發生嚴重解析異常導致服務崩潰。

---

## 2. 逐步回退操作手冊 (Step-by-Step Rollback)

### 步驟 1: 容器版本即刻回滾
登入 Staging 部署主機，將 Docker 映像檔回滾至上一穩定 SHA：
```bash
# 取得前一個可用 image SHA
PREV_IMAGE=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep cloud360-app | sed -n '2p')

# 重新啟動上一個穩定版本
docker stop cloud360-app && docker run -d --name cloud360-app -p 8000:8000 $PREV_IMAGE
```

### 步驟 2: 分支回滾與重整
在本地與遠端 Git 儲存庫回退 Squash Commit：
```bash
git checkout ut
git revert <faulty-squash-commit-sha> -m "回退: 混合雲繪圖功能異常回滾"
git push origin ut
```

### 步驟 3: 健康狀態確認
訪問 `https://cloud360.danniel.cc/health` 確認回傳 `{"status": "ok"}`。

