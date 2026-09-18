# Constraint Register — 帳號最後活動時間（稽核欄位）

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。 -->

## 上游輸入

- 約束的業務脈絡承襲 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`），其「適用的既有約束」段為本登錄的起點。
- market-research 已依 scope 跳過，其可選產出 **competitive-analysis**、**market-trends**、**build-vs-buy** 不存在（scope 設計使然），本登錄無市場面約束來源。

## 技術約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| T1 | 系統沒有任何既有的登入／活動紀錄，也沒有可回填的資料來源 | 歷史空窗無法消除；上線時所有既有帳號的值為空，顯示「無紀錄」 | [code:C1] [Q2] |
| T2 | 認證為無狀態短期憑證（8 小時效期、無更新機制） | 「登入時刻」與「實際活動」最多差 8 小時；已以「記錄任何有效活動」定錨迴避 | [code:C2] [Q1] |
| T3 | 專案無資料庫遷移框架；既有環境的結構變更靠服務啟動時自動補齊，或重跑整份初始化腳本 | 本功能採「啟動時補齊＋最小範圍權限更新」路徑；不得依賴重跑整份腳本 | [code:C4] [Q3] |
| T4 | 重跑整份資料庫初始化腳本會重置角色權限設定，覆寫線上手動調整 | 部署程序必須明確排除「重跑整份腳本」作為本次變更的套用手段 | [code:C5] [Q3] |
| T5 | 角色權限預設值存在兩處來源（資料庫腳本與後端種子資料），必須同步修改 | 權限值翻轉屬 seed 語意變更，觸發 M1 的部署資產同步義務 | [code:C6] [memory:M1] |

## 組織與流程約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| O1 | 資料庫結構或 seed 行為變更時，`schema_rbac.sql` 與 `DEPLOY.md` 必須同步更新（blocking） | 未完成不得標示相關 Construction／部署階段為完成 | [memory:M1] |
| O2 | 合併進 `ut` 即自動部署至自有 staging；build 與 deploy 之間無 phase gate | 變更一旦合併立即生效於 staging，部署考量須與實作同步規劃 | [intent:Q10/Q12 所處的既有管線脈絡；`org.md#Deployment`] |
| O3 | 無時程、預算或組織性阻塞；隨開發能量排入 | 無外部期限壓力，品質優先於速度 | [Q5] |

## 法規與政策約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| R1 | 活動時間資料有保存上限（值未定） | 保存期限的具體值與清除語意留待 requirements-analysis | [Q4] |
| R2 | security baseline 為常設 hard constraint（涵蓋 IAM、audit logging 等面向） | 權限擴張的風險處置須留下證據；已記入 raid-log R3 | [memory:M4] [Q7] |
| R3 | 雲端供應商 production 環境、production credentials 不在本 repository 範圍內 | 本功能僅及自有 staging，不觸及雲端供應商環境 | [intent-statement 適用的既有約束] |
| R4 | 無外部法規框架（PCI、HIPAA、GDPR 等）被指認為適用 | 屬假設而非確認，見 Assumptions | [Q4] |

## Assumptions & Open Questions

- [assumption] 本平台為內部工具，無外部法規框架適用於活動時間資料；此判斷未經法務或合規方獨立確認 [Q4]
- [assumption] 保存上限的值與「單一欄位覆寫」模式下的清除語意未定義，留待 requirements-analysis [Q4]
- [assumption] （開放問題）O2 的自動部署管線之下，資料庫變更與程式碼變更的生效順序（啟動時補齊發生在服務重啟時）是否需要額外的部署順序約束，留待 Construction 的部署規劃檢驗 [Q3]
