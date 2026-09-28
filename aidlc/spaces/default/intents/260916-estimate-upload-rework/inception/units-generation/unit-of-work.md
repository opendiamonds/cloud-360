# 工作單元目錄：C1 估價表上傳

本檔定義九個 Unit 的邊界、職責、kind、複雜度與實作約束。**不規定實作順序**——那是 delivery-planning 的經濟判斷。相依拓樸見 `unit-of-work-dependency.md`。

| Unit ID | Directory | Name | Kind | Complexity | Deployment |
|---|---|---|---|---|---|
| U1 | `u1-estimate-parser` | `estimate-parser` | library | M | embedded |
| U2 | `u2-estimate-intake-api` | `estimate-intake-api` | service | L | shared（單一 FastAPI process） |
| U3 | `u3-legacy-cost-retirement` | `legacy-cost-retirement` | service | M | shared；**須與 U8 同批部署** |
| U4 | `u4-credential-pipeline` | `credential-pipeline` | packaging | M | shared（deploy 設定） |
| U5 | `u5-pricing-lookup-port` | `pricing-lookup-port` | library | M | embedded |
| U6 | `u6-langgraph-runtime` | `langgraph-runtime` | library | M | embedded |
| U7 | `u7-cost-advice-agent` | `cost-advice-agent` | service | L | shared |
| U8 | `u8-estimate-workspace-ui` | `estimate-workspace-ui` | ui | L | shared（單一 SPA）；**須與 U3 同批部署** |
| U9 | `u9-advice-presentation-ui` | `advice-presentation-ui` | ui | M | shared |

---

## U1 — `estimate-parser`

**Kind:** library　**Directory:** `u1-estimate-parser`　**Complexity:** M

**Boundaries**

- 擁有：`EstimateParser`、`EstimateValidator`（純函式層）
- 模組路徑：`backend/cost/estimate_parser.py`（及同套件下三格式讀取器檔案）；驗證器路徑由 functional-design 釘選（domain-design 審閱次要發現：須納入 CI 邊界腳本）
- 不含：HTTP、DB、檔案上傳協調、LLM

**Responsibilities**

- 雲別判定與三格式（AWS CSV／Azure XLSX／GCP CSV）正規化
- 無法辨識列標記與原始文字保留
- FR4 三項機械檢查；存在無法辨識列時跳過總額對帳
- 改寫 `scripts/validate_cost_calculator_boundary.py` 指向新模組（FR9.6）；PBT 覆蓋（FR2.4）

**Constraints**

- 模組內不得 import `httpx`／`requests`／`sqlalchemy`／`fastapi`（FR2.3）
- 輸出結構將由 contract-design 正式化（Q7=A）

**Components:** EstimateParser, EstimateValidator

---

## U2 — `estimate-intake-api`

**Kind:** service　**Directory:** `u2-estimate-intake-api`　**Complexity:** L

**Boundaries**

- 擁有：`EstimateIntakeService`、`EstimateAccessControl`、`EstimateAuditLog`
- 實體：`EstimateSet`、`Estimate`、`EstimateLineItem`、`EstimateShare`、`EstimateAuditEvent`
- HTTP 邊界：新上傳／讀取／分享／歷史／刪除端點（取代舊 `/api/cost` 的對外形狀，但舊端點的**刪除**屬 U3）

**Responsibilities**

- 上傳限制與魔數驗證；原始檔即用即棄（FR1.6）
- 協調 Parser／Validator；持久化批次與明細；機械檢查結果**不**持久化（每次重算）
- 自有授權判斷（擁有者＋分享名單）；RBAC story `C1` 語意更新與 `C1h`／`C1r`／`C1o`／`C1b` seed 移除（FR7.1–7.2）
- 事件層級稽核（不含金額／明細）
- 觸發 U7 的建議產生（async）

**Constraints**

- 維持 `cost_router → cost_service → 純函式` 三層形狀（NFR6）
- 不得跨模組引用 `collab_router` 私有授權函式（FR7.3）
- `Advice` 實體由 U7 擁有；本單元只觸發、不寫建議內容

**Components:** EstimateIntakeService, EstimateAccessControl, EstimateAuditLog

---

## U3 — `legacy-cost-retirement`

**Kind:** service　**Directory:** `u3-legacy-cost-retirement`　**Complexity:** M

**Boundaries**

- 純刪除與工具鏈修正；不交付新產品能力
- 涵蓋 FR9 退場面（見下），**不含** FR9.4／FR9.5／FR9.6（保留／改指向屬 U5／U1）

**Responsibilities**

- 移除舊 `/api/cost` 九個 operations 與自動估價路徑實作（FR9.1）
- 移除四張舊表（DDL 雙軌：`database.py::_ensure_cost_schema` 與 `schema_rbac.sql`）並同步 `DEPLOY.md`（FR9.2）
- 移除 Playwright Calculator 模組、spike、`playwright` 相依（FR9.3）
- 修正 `warm_aws_pricing_cache.py`（FR9.7）；清理舊 C1 環境變數讀取點中與退場相關者（與 U4 協調 FR9.8 的「減」側）
- 更新 e2e 成本頁段落（FR9.9）；同 PR 重產 `openapi.json`／型別（FR9.10）；處理孤兒 prompt（FR9.11）

**Constraints**

- **須與 U8 同批部署**（Q6=A）：deploy-on-merge 下分兩批會讓 `/cost` 中間一次是死的
- 不得刪除 `pricing_sdk`／`pricing_client` 最小存活集（屬 U5）

---

## U4 — `credential-pipeline`

**Kind:** packaging　**Directory:** `u4-credential-pipeline`　**Complexity:** M

**Boundaries**

- 部署與 CI 閘門設定，無執行期業務邏輯
- FR11 全條；FR5.8（平台統一憑證注入）；FR9.8 的「增」側（目錄價憑證變數）

**Responsibilities**

- 重建 AWS／GCP 目錄價憑證傳遞：`deploy.yml` → `render-env.sh` → `docker-compose.deploy.yml`（FR11.1）
- 調整 `validate_repo_contract.py` 的 `FORBIDDEN_CONTENT_PATTERNS`：放行變數名、仍擋實際金鑰值（FR11.2，高風險）
- 同步 `DEPLOY.md`／`LOCAL-DEV.md`（FR11.3）
- 憑證缺席時系統可啟動（FR11.4）

**Constraints**

- ADR-0018：僅目錄價類；帳單／用量類 API 仍禁
- IAM 最小權限（FR5.9）由 U5 消費端執行期強制；本單元負責注入範圍不超標

---

## U5 — `pricing-lookup-port`

**Kind:** library　**Directory:** `u5-pricing-lookup-port`　**Complexity:** M

**Boundaries**

- 擁有：`PricingLookup`（改造自 `pricing_client`）
- 保留 `pricing_sdk`、`pricing_query_parser`、YAML 設定等最小存活集（FR9.4、FR9.5）

**Responsibilities**

- 統一包裝三雲目錄價端點；憑證缺漏／失敗時降級（FR5.10）
- **唯讀**：輸出不得進入明細寫入路徑（AH-6）

**Constraints**

- 單元相依僅 U4（需要憑證管線才能測 IAM 路徑）；**不被 U7 列為單元相依**（Q3=A）——接上時機由 delivery-planning 決定
- httpx 不得在他處直打 Pricing API

**Components:** PricingLookup

---

## U6 — `langgraph-runtime`

**Kind:** library　**Directory:** `u6-langgraph-runtime`　**Complexity:** M

**Boundaries**

- LangGraph 執行骨架與 OpenRouter（OpenAI 相容）接入
- 不含具體成本建議圖節點（屬 U7）

**Responsibilities**

- 引入 LangGraph 相依與可重用的圖執行／串流輔助
- 驗證對 OpenRouter 的一次成功推論（可行性去風險）
- **不得移除** `claude-agent-sdk`（其他 agent 仍用）（FR10.3）

**Constraints**

- 模型存取走 OpenRouter（FR10.2）

---

## U7 — `cost-advice-agent`

**Kind:** service　**Directory:** `u7-cost-advice-agent`　**Complexity:** L

**Boundaries**

- 擁有：`CostAdviceAgent`、`AdviceOrchestrator`、實體 `Advice`
- 背景工作生命週期與 HTTP 解耦；SSE 為訂閱者

**Responsibilities**

- 三類建議：省錢（Must）、跨雲比較／品質檢查（Should，未交付須明示）（FR5.1–5.3）
- 完整解析結果送 LLM（FR5.4）；`Advice` 持久化與狀態（產生中／完成／失敗）
- SSE 進度與 heartbeat（防 idle timeout）；逾時 5 分鐘後明細仍可用
- 可選呼叫 U5 查價；未接上或失敗時建議流程不得失敗，且**不得假裝有現價**（Q3=A 行為約束）

**Constraints**

- 單元相依：U6、U2；**不含 U5**
- `UNIQUE(estimateSetId)` 與重複觸發去重（domain-design 審閱次要發現）由 functional-design 釘選
- 單一 process 重啟可能卡住「產生中」——逾時清理屬下游（OQ-DD3）

**Components:** CostAdviceAgent, AdviceOrchestrator

---

## U8 — `estimate-workspace-ui`

**Kind:** ui　**Directory:** `u8-estimate-workspace-ui`　**Complexity:** L

**Boundaries**

- `/cost` 頁的上傳、明細、機械檢查結果、歷史抽屜、分享、隱私徽章
- **不含** AI 建議區的 SSE 訂閱與建議呈現（屬 U9）
- 建議區可留骨架殼位或「尚未啟用」占位，但不實作訂閱邏輯

**Responsibilities**

- refined-mockups M1–M4、M6–M8 中與上傳／明細／歷史／分享相關的畫面
- 拖放上傳、雲別就地更正、摺疊卡片、無法辨識列呈現、檢查結果區
- WCAG 2.1 AA；`ShareModal` 無障礙補丁

**Constraints**

- **須與 U3 同批部署**
- 與 U9 的合併衝突面已接受（Q4=A）；U9 應盡量只新增檔案，但本站不強制檔案邊界（那是 Q4 落選的 C）

**Components:** EstimateWorkspacePage（本單元範圍內的子區塊）

---

## U9 — `advice-presentation-ui`

**Kind:** ui　**Directory:** `u9-advice-presentation-ui`　**Complexity:** M

**Boundaries**

- AI 建議區、SSE 訂閱、進度／骨架載入、三類建議呈現與「由 AI 產生，請自行核對」標註
- 不修改上傳／明細核心流程（盡量），但與 U8 共享頁面殼

**Responsibilities**

- refined-mockups 建議三態；NFR2 進度指示
- 區分「檢查結果」與「AI 建議」來源（FR4.5 的建議側）

**Constraints**

- 相依 U8、U7；不在 U3 同批約束內——可在明細頁已上線後再交付

**Components:** EstimateWorkspacePage（建議區子區塊）

---

## 既有元件（不設 Unit）

`IdentityAndRbac`、`Collaboration` 本期僅 seed／外鍵標籤層面的配合，由 U2  consum；不另開 Unit。

## Assumptions & Open Questions

- **A-UG1**：FR9.8 的「增／減」分屬 U4（增憑證變數）與 U3（減舊 C1 參數）；同一批合併前須對齊，否則 `validate_env_contract.py` 紅燈。協調屬 delivery-planning 的 Bolt 打包，非單元相依邊。
- **A-UG2**：FR9.1「移除舊端點」與 U2「新增端點」在同一 router 檔上會衝突——拓樸上 U3 與 U2 **無**相依邊（可平行開發），但合併時需同 PR 或緊鄰；與 U3+U8 同批部署是不同層次的約束。
- **OQ-UG1**：U8／U9 的檔案切分慣例（是否強制 U9 只新增檔）留給 construction 的 mob 約定；本站 Q4=A 未選 C。
- **OQ-UG2**：`EstimateValidator` 模組路徑與 CI 腳本是否擴充——functional-design 承接（domain-design 審閱發現一）。

## Review

**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1
**Date:** 2026-09-18T10:24:41Z
**Request Challenge:** review:f49b1f9d8b12b63e521a525c8c299467
**Verdict:** READY

九個單元邊界成立，有向無環圖無循環依賴。先前三項 Minor 發現（R-01 U7→U2 授權整合點、R-02 FR9.8 批次順序說明、R-03 U2/U3 路由衝突緩解）均已回寫進 `unit-of-work-dependency.md`，無新阻擋項。
