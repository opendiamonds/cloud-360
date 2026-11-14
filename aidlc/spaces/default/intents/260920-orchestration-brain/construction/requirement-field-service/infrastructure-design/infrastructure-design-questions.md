# Infrastructure Design 問題檔 — `U20 requirement-field-service`

> **本站問 0 題。** 與 `U15`／`U24` 不同，本單元的基礎設施面**不是空的**：資料表收斂
> 帶來 CI 驗證步驟與部署順序兩件事。但兩者的做法都由上游審查與 repo 現況決定，沒有需要
> 使用者在多個可行方案間選擇的地方，故不出題；本站依 2026-10-06 核可的精簡形狀產出，
> 並**仍派審查員**——因為這一站有真實內容（CI 變更），不屬「無標的、by-reference」的情形。

## 一、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據（本站實測） |
|---|---|---|
| 部署策略 | **有標的：部署順序** | `deploy.yml` 與 `deploy/*.sh` 對 `run_meta_schema_migration.py` 零命中——遷移是**手動**步驟，後端則合併即自動部署。見 `infrastructure-specification.md` 第二節 |
| 運算／儲存／網路 | **無新資源** | 新 router 掛在既有 `/api`；`frontend/nginx.conf` 的 `location /api/` 已涵蓋；表由 `U18` 交付 |
| 監控 | **無新管線** | 只有應用 log（`observability-design.md`）；repo 無指標或告警管線 |
| CI/CD | **有標的：收斂驗證** | 既有 `memory-schema` job（`ci.yml:308`）擴充步驟，執行 `run_meta_schema_migration.py` 走「舊定義 → 收斂 → 重跑」。見 `cicd-pipeline.md` |
| Secrets | **無標的** | 零新環境變數（`NFR8.120`） |
| 擴縮 | **無標的** | embedded，隨既有後端（`scalability-design.md`） |

## 二、問題

（無）
