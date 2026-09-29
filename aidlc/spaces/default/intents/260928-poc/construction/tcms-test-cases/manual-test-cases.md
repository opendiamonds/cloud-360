## TC: 驗證 LangGraph Agent 的對話記憶機制

- plan: POC-LangGraph-Migration
- priority: P1

### 目的
確保 Design Agent 改寫為 LangGraph 框架後，能在同一個使用者的繪圖連線中，將歷史上下文保留在 checkpointer (MemorySaver) 中。

### 受測介面
- API: `POST /api/architecture/generate`

### 前置條件
1. 啟動後端伺服器與前端。
2. 準備一組測試使用者帳號，並具有架構圖修改權限（`edit`）。

### 測試步驟
| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 從 UI 發送對話「我要建立一個 AWS 網路環境」 | 系統回傳「收到，請問是否需要包含 Public/Private Subnet？」或其他 AWS 相關詢問。不得拋出 500 錯誤。 |
| 2 | 發送另一句對話「幫我畫出來，並且補上一個 EC2」 | Agent 產出的 XML 必須同時包含 VPC 框架（來自第一句對話的記憶）以及 EC2 節點（來自第二句對話）。 |
| 3 | 發送「幫我把 EC2 換成 RDS」 | Agent 產出的 XML 必須更新為包含 VPC 與 RDS，不得遺漏一開始的 AWS 與 VPC 脈絡。 |

### 通過條件
- 連續發送多句話語後，產生的架構圖符合所有對話堆疊的要求，且不會忘記先前的需求。

### 追溯
- 實作：`backend/services/design_agent.py`
- 自動化對應：`backend/tests/test_langgraph_migration.py::TestLangGraphMigration::test_langgraph_memory`
- PR／commit：e97f0b4
- User story：POC
