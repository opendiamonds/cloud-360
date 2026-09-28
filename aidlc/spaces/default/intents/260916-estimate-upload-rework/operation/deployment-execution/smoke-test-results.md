# Smoke Test Results — C1 staging（基線）

> 範圍：對**已部署** staging 的連通性煙霧，非 C1 功能完整驗收（程式尚未經本 stage redeploy）。

| # | 煙霧項 | 結果 |
|---|---|---|
| S-1 | 前端根路徑 200 | **通過** |
| S-2 | `/api/auth/login` 路由可達（OPTIONS→405） | **通過** |
| S-3 | C1 上傳→建議 E2E（真實資料） | **未跑** — 待合併＋redeploy 後以 TCMS 手動 M-1／Playwright 複驗 |

## 總結

基線連通 **通過**。C1 功能煙霧列為合併後待辦。

<!-- Post-confirmation save -->
