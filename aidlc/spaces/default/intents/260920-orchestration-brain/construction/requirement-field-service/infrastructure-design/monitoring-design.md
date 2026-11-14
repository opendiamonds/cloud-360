# 監控設計 — `U20 requirement-field-service`

## 一、本單元的訊號

| 訊號 | 來源 | 怎麼看 |
|---|---|---|
| 授權拒絕 | WARNING `requirement_field.denied`（`observability-design.md`） | 後端容器 log（`docker compose logs backend`） |
| 寫入／清空 | INFO `requirement_field.written`／`cleared` | 同上 |
| 遷移收斂結果 | `run_meta_schema_migration.py` 的輸出與結束碼 | 人工執行時的終端輸出 |
| 收斂驗證 | CI `memory-schema` job 的新步驟 | GitHub Actions |

## 二、刻意不建的東西

| 不建 | 理由 |
|---|---|
| dashboard、告警通道 | repo 沒有指標或告警管線（`project.md ## Deployment`：observability 仍是真實待辦）；為一個 router 單獨引入是獨立的基礎設施決定 |
| log 集中化或保存期限設定 | 沿用既有容器 log；本單元的 log 不含值（`NFR20.28`），沒有需要特別保護或延長保存的內容 |

## 三、上線後第一次要人工確認的事

1. 遷移腳本在 staging 結束碼為 0，且輸出包含此欄的型別檢查通過。
2. 以一個有 `K4.edit` 的成員帳號在需求籤儲存一次，後端 log 出現一行 `requirement_field.written`，
   且該行不含輸入的值。
