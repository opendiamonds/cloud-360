# Integration & E2E Test Instructions


### 目的

驗證 backend（FastAPI + PostgreSQL）與 frontend 跨單元互動。目前**無自動化整合測試**，以下為手動 E2E 場景（來源：各 unit code summary 的手動驗收章節）；自動化列入缺口。

### 環境準備

```bash
docker compose up -d db adminer
cd backend && uvicorn main:app --reload --port 8000
cd frontend && npm run dev
# 首啟空庫會自動 seed：role_permissions 矩陣 + admin/admin123
```

### 場景

#### 場景 1：U-J → U-A1／A2（登入與權限閘門）

1. `admin/admin123` 登入 → Sidebar 顯示 Admin 兩頁  
2. Admin 把某使用者改為只讀角色 → 該使用者 Sidebar 隱藏「架構圖生成」、直連 403  
3. J4 矩陣改動 → `/me` 權限即時反映

#### 場景 2：U-A2 → U-A4（畫布編輯與持久化）

1. 開圖、手動編輯、儲存 → 重整後自動開同圖（bootstrap）  
2. 對既有圖請 AI「只新增 WAF」→ 原節點連線保留  
3. 清空對話 → 聊天清空、XML 仍在

#### 場景 3：U-A5（分享與即時共編）

1. Alex 分享給 Hannah（編輯）＋ Ian（檢視）  
2. 兩瀏覽器同開一圖：Hannah 改圖 → Alex 即時看到；Ian 唯讀＋檢視歡迎詞  
3. 關閉 backend → 前端標籤轉「單機模式」

#### 場景 4：U-A1（AI 生成，需 `OPENROUTER_API_KEY`）

1. 聊天輸入需求 → SSE 逐步回覆 → 畫布出現 mxGraph 圖

#### 場景 5：U-A3（Well-Architected 評核）

1. 具 A3.edit 帳號（如 alex／hannah）登入 → Sidebar「評估儀表板」  
2. 選有權限圖 → 執行評核 → 見支柱分數與 findings；有 key 時見建議串流  
3. Workspace：產圖成功 CTA「Well-Architected」或頂列按鈕 → `/assessment?diagramId=`  
4. 無 key：規則完成後 `rules_only`，可之後重試建議  
5. 分享圖給 Fiona（A3.view）→ 可開啟同一歷史報告  

### 清理

```bash
docker compose down          # 保留資料
docker compose down -v       # 連 volume 一併清除
```

### 缺口

- pytest + httpx TestClient 的 API 整合測試、Playwright E2E → 待後續 plan
