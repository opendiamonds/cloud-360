# 外部依賴對照：C1 估價表上傳

本 intent 主要在自有 staging 與既有 SaaS 帳號內完成；下列為會卡住某個 Bolt 的外部項。

| 依賴 | 擁有者 | 預估前置 | 卡住的 Bolt | 滑移時怎麼辦 |
|---|---|---|---|---|
| OpenRouter API（金鑰、額度、模型可用性） | 平台／Danniel | 已有既有 LLM 路徑；確認 OpenAI 相容端點可用 | B2、B6 | B2 失敗則暫停 B6／B7；B5 明細路徑仍可交付 |
| AWS IAM（`pricing:GetProducts` 等最小權限）＋ GitHub Secrets | 平台 | B3 需要 Secrets 已建立 | B3、B8 | 無憑證仍可啟動（FR11.4）；B8 降級略過查價 |
| GCP Cloud Billing Catalog API key | 平台 | 同 B3 | B3、B8 | 同上，僅略過 GCP 查價 |
| Azure Retail Prices | 無帳號 | 無 | B8 | 公開端點；失敗則略過 |
| 三雲官方估價表**樣本檔**（測試用） | 團隊自備 | B1 前 | B1、B4、B5 | 用合成 CSV／XLSX 先跑通；正式樣本後補回歸 |
| Cloudflare Tunnel／反向代理 idle 行為 | 既有部署 | 已驗證 A1／A3 SSE | B6、B7 | 契約已要求 heartbeat；若仍斷線調間隔 |
| Kiwi TCMS（`tcms.danniel.cc`） | dc-infra | construction 末 | `tcms-test-cases` stage | 文件案例可先寫在 repo；同步延後 |

**非依賴（刻意不列）:** 雲端供應商 Cost Explorer／Billing 類 API（ADR-0018 禁止）；物件儲存（原始檔不留存）。
