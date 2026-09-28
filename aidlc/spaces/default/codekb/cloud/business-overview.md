# 業務總覽（Business Overview）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan（整組取代）**
> 本次為全 repo 重掃，9 份 artifacts 整批取代 2026-08-19（`c3de2c8`）的舊版本。深度分佈見 `reverse-engineering-timestamp.md` 的 `## Scope of Analysis`。

## 產品定位與價值主張

Cloud-360 是 AI-native 的多雲（AWS／GCP／Azure）架構設計與運維平台。核心價值鏈為「以自然語言描述需求 → 產生可編輯的 draw.io 架構圖 → 以 Well-Architected（WA）lens 審核 → 由同一份架構圖推導成本」，並以故事級 RBAC 控制誰可檢視、編輯、審核與改價。

執行環境限於自有 staging（`cloud360.danniel.cc`，ADR-0007）；雲端供應商 production 仍在範圍外（ADR-0001／ADR-0002）。方法論基礎為 Spec-Driven Development 與 AI-DLC v2（ADR-0011）。

**與 2026-08-19 舊 codekb 的最大差異：C1 成本估算已由「僅有 RBAC 種子」變成完整可運行的功能域。** 現況為 `backend/cost/`（18 支 Python、9 份 YAML、2 份 fixture）、`/api/cost` 9 個 HTTP operations、4 張資料表、`/cost` 前端頁面、17 支後端測試與一段 Playwright 回歸皆已存在。舊 codekb 中「cost calculator ABSENT」「pricing client ABSENT」「無 `/cost` 路由」等敘述**全部失效**。

## 主要使用者旅程

| 故事／領域 | 主角 | 目標 | 入口 | 現況 |
|---|---|---|---|---|
| A1 架構圖生成 | 架構師／工程師 | 以聊天提示產生與迭代架構圖，於 embed.diagrams.net 畫布編輯並持久化 | `/workspace` | 可運行 |
| A3 評估與審核 | 審核者／架構師 | 對已存架構圖執行 WA review、檢視 findings 與分數、管理 lens | `/assessment` | 可運行 |
| **C1 成本估算** | **FinOps 分析師／架構師** | **由架構圖推導逐項成本、調整區域與每日時數、覆寫 SKU 與單價、匯出 Calculator 估價檔** | **`/cost`** | **可運行（本次重掃的主要新事實）** |
| J 管理（權限） | 管理員 | 使用者管理、角色授權請求、角色–故事權限矩陣、最後活動與分頁 | `/admin/*` | 可運行 |
| 協作 | 協作者 | 架構圖 CRUD、聊天歷史、分享、WebSocket 同步 | `/api/collab` + WS | 可運行 |

導覽與落地頁由故事權限驅動。**`frontend/src/App.tsx:24` 的根路徑導向第一順位是 `if (can('C1','view'))` → `/cost`**：成本頁不只是側欄的一個項目，它同時是所有具 C1 檢視權角色登入後的落地頁。此事實對任何調整成本頁存廢的變更都是直接影響面。

## C1 成本估算的業務行為（現況）

1. **估價來源為自動取價**：`pricing_client` 依雲別分派至 AWS Bulk／Azure Retail／GCP Catalog 的公開價目端點，另有 `pricing_sdk`（boto3 Pricing Query API，需 IAM 憑證，預設關閉）。
2. **SKU 對應**：`sku_mapper`（YAML 規則，`sku_map.yaml` 263 行）優先，未命中改走 `sku_ai_resolver`（LLM 推論）。
3. **Agent 產生建議**：`cost_pricing_agent` 以 `claude_agent_sdk` 建立 in-process MCP server `cloud360-cost`，暴露 3 個 tool 供 agent 按需查價與試算。
4. **Calculator 自動化**：`azure_calculator_runner`／`gcp_calculator_runner` 以 Playwright 驅動官方 Calculator 網頁產生可匯出的估價檔（xlsx／csv）。
5. **可調參數**：估價區域（`C1r`）、每日時數（`C1h`）、SKU 與單價覆寫（`C1o`），每次調整寫入 `cost_audit_event` 稽核表。

上述 1～4 的每一項都是本 intent 的退役或改寫目標；**能力盤點與逐條掛鉤清單見 `component-inventory.md` 與 `dependencies.md`，不在本檔重複。**

## 範圍與邊界

**In scope（目前可運行）**：FastAPI 後端（6 組 router 掛載於 5 個前綴）、React SPA（9 頁）、PostgreSQL（11 張 ORM 表）、staging Docker 部署與 Cloudflare Tunnel、CI 契約／lint／build／drift／unittest／Docker、11 支 gh-aw agentic workflow、Kiwi TCMS 測案管理。

**Out of scope（除非新 ADR）**：雲端供應商 production 環境與 credentials、direct production IaC、destructive cloud operations、native iOS／Android app。

## 與本 intent 的業務關聯

Intent `260916-estimate-upload-rework` 要把 C1 由「系統自動取價」改為「使用者上傳三朵雲的官方估價表，由 agent 解析後給成本建議」。從業務面看，這是一次**估價真實來源的反轉**：

- 現行路徑的價格來自公開目錄價，**不含** CUD／RI／Savings Plan 等客戶專屬折扣；上傳的官方估價表則已含折扣，因此上傳值是更接近帳單的真相，不得被目錄價覆蓋（`project.md` `## Mandated` 已就此立過規則）。
- 現行 Calculator 自動化路徑（Azure／GCP）**在部署環境中結構性不可用**：`backend/Dockerfile` 未執行 `playwright install chromium`，容器內沒有瀏覽器二進位。任何以「現行 Calculator 路徑的線上表現」為依據的退役論證都缺乏事實基礎。詳見 `code-quality-assessment.md`。
- 退役面的實際邊界比「9 個端點 + 4 張表」大得多：有 8 類套件外掛鉤，其中 3 類會直接讓 CI 紅燈。清單見 `dependencies.md`。
