# Constraint Register — 統一入口大腦

本文件登記本 intent 必須在其中運作的既有邊界。約束不是風險——風險可能不
發生，約束一定成立。每一列都標註來源；來源定義見 `feasibility-questions.md`
的 `## Sources`（S1–S13）與各題作答。

本登記表以 `<record>/ideation/intent-capture/intent-statement.md` 的
Initial Scope Signal 為範圍前提：本 intent 不改動該段已確認的產品邊界。

## 技術約束

| ID | 約束 | 影響 | 來源 |
|---|---|---|---|
| C-T1 | 部署拓樸現為 4 個服務（`db`、`backend`、`frontend`、`cloudflared`）＋ 具名 volume `cloud360_db`。新增 Redis 使其成為 5 個 | 任何新增元件都改變部署拓樸，並連帶觸發 C-O1 的環境變數規則 | [S1][F2] |
| C-T2 | `fastapi[standard]` 與 `pydantic` 為精確釘選版本（`==0.141.1`、`==2.13.4`），理由是 OpenAPI 規格輸出跨版本會飄 | 升這兩支必須在同一個 PR 內重新 dump `openapi.json` 並重產前端型別 | [S2] |
| C-T3 | 新增或變更端點會連動兩道機械檢查：CI 的 `openapi.json` 漂移檢查，與前端 `npm run gen:types` 產生的 `src/types/api.d.ts` | 端點變更必須在同一個 PR 內重產兩者，否則 CI 紅燈 | [S5] |
| C-T4 | 既有串流契約為 SSE（`text/event-stream`，`{type, content}`），共存於 3 個端點；架構圖共編另有 WebSocket | 本 intent 改用 WebSocket 後，系統內將有兩種串流機制並存；既有 SSE 端點不在本次變更範圍內 | [S3][S4][F4] |
| C-T5 | 現用資料庫映像為官方 `postgres:16-alpine`，**不含 pgvector**，且 repo 內無任何 `CREATE EXTENSION` | 語意記憶若採向量檢索，須換映像或自建映像——屬拓樸層變更，不是加一張表 | [S9] |
| C-T6 | `schema_rbac.sql` 為 init script，**只在空的 data volume 上執行** | 既有 staging 的 volume 非空，故新增 extension 與資料表在既有環境上需要明確的手動遷移步驟 | [S10] |
| C-T7 | CI 的 Python 版本為 3.12 | 新引入的套件必須相容此版本。**修訂 1 更正**：LangGraph 已非「新引入」——`langgraph==1.2.11` 與 `langchain-openai==1.6.2` 已釘選並隨既有成本 agent 通過 CI 與部署 [V8]。本條對本 intent 的剩餘適用對象為 Redis 客戶端等尚未引入的套件 | [S7][V8] |
| C-T8 | PostgreSQL 不支援跨 database 查詢（需 `postgres_fdw` / `dblink`） | 記憶層落點因此定為「同一 database、獨立 schema」，以保留原生 join 能力 | [F3] |
| C-T9 | 既有 `llm_limits.py` 管的是**單次請求的 token 上限**（來自環境變數），非花費上限；repo 內不存在任何設定類端點 | 本系統目前沒有、本 intent 也不建立**自身 LLM 花費**的計量或 admin 設定機制。注意這與 `backend/cost/` 無關——後者計的是使用者雲端架構的估價，不是本平台自身的花費 | [S11][S12][F13][V-F3] |
| C-T10 | 成本 agent 的回覆為非同步 job（`ThreadPoolExecutor`），其 SSE 每秒輪詢 DB 送出狀態事件，**非 token 級串流** | 大腦不需要實作 token 級的巢狀串流轉送；上游 `intent-statement.md` 假設第 5 條所列的三種處置（逐字轉送／彙整後再送／並存）預設 token 流，該框架不成立。依 `team.md ## Corrections` 不回改上游，以 C-S6 向下游傳遞 | [V-F1][F15] |

<!-- 修訂 1：C-T9 的「repo 內不存在任何設定類端點」原寫於成本能力不存在
     時。本輪重新查證 `/api/cost/v1` 的 10 條端點，確認其中無設定類端點
     （settings／config／budget 在 backend/cost/ 的 router 層 0 命中），
     故主張仍成立，但依據已更新為 V-F3 而非沿用舊句。C-T10 為本輪新增。

     修訂 1 存檔於 2026-09-21，對應 feasibility 的 Consolidated Summary
     Confirmation 收據。本檔的修訂範圍：C-S2 改寫、新增 C-S5／C-S6／C-S7、
     C-T7 更正、C-T9 重新查證、新增 C-T10。 -->

## 組織與流程約束

| ID | 約束 | 影響 | 來源 |
|---|---|---|---|
| C-O1 | **blocking**：新增 compose 消費的變數時，同一個 PR 必須讓 `deploy/render-env.sh` 寫它、`deploy/.env.example` 列它。失敗模式無聲——缺值變空字串，服務照常啟動但功能降級 | Redis 的連線設定必須與其容器在同一個 PR 內落地 | [S8][F2] |
| C-O2 | **blocking**：資料庫結構變更時 `schema_rbac.sql` 與 `DEPLOY.md` 必須同步 | 專案／系統階層與記憶層 schema 都會觸發此規則 | [S8] |
| C-O3 | 單一決策者，無其他關係人，不需對外回報節奏 | 範圍、優先順序與驗收皆由同一人決定；無跨團隊協調成本，亦無 change freeze 之類的組織阻礙 | [Q8] |
| C-O4 | 成本上限由 OpenRouter 後台承載，本專案不掌握其數值；本 intent 內以「盡量省」為設計原則 | 編排層優先選便宜快速的模型，昂貴模型只用在真正需要處；此為設計原則，非可量測的門檻 | [F11][F13] |

## 範圍約束（承自上游，不在本站重新開放）

| ID | 約束 | 來源 |
|---|---|---|
| C-S1 | 作業對象採「專案 → 系統 → 架構圖」三層，本 intent 一併建立該階層 | [Q5] |
| C-S2 | 大腦編排**既有的**成本／FinOps 能力（`backend/cost/`，`/api/cost/v1` 下 10 條端點），本 intent 不新建成本計量；答案就地在入口頁呈現，`/cost` 頁不加入共享工作階段範圍 | [Q12][Q14] |
| C-S5 | 大腦呼叫成本能力一律走 HTTP 並帶使用者的 token，使既有的 `require_story_action("C1",…)` dependency 照常執行；不得以同進程呼叫 service 層繞過該授權，稽核的行為主體為使用者本人 | [F14] |
| C-S6 | 大腦把成本 job 的狀態事件（`progress`／`completed`／`timeout`／`failed`／`heartbeat`）轉譯進自己的訊息流；不得等 job 完成才開始回覆（與已核可的「首字回應時間」指標矛盾） | [F15] |
| C-S7 | 大腦自建獨立的 LangGraph 執行層，不改造既有已上線的 `services/langgraph_runtime.py`，兩者並行。**附帶義務**：系統內將並存兩份 OpenRouter 客戶端與兩套串流事件語意，依 `team.md ## Code Style` 的單一真實來源規則，必須有鎖住兩者一致性的驗證；具體手段不在本站預選 | [Q13] |

<!-- 修訂 1：C-S2 原文為「成本／FinOps 只做交接介面與明確的『尚未提供』
     回覆，不實作成本計算 [Q6][Q11]」，其前提已被推翻（成本能力已存在），
     Q6／Q11 已由 Q12 取代。C-S5／C-S6／C-S7 為本輪新增。 -->
| C-S3 | 共享工作階段涵蓋統一入口、架構圖工作區、評估頁三處，不含管理功能頁面 | [Q7] |
| C-S4 | 雲端供應商 production 環境、production credentials、environment-specific secrets、direct production IaC、destructive cloud operations、native iOS/Android app 皆在範圍之外 | [memory:M2] |

## 法規與隱私約束

| ID | 約束 | 影響 | 來源 |
|---|---|---|---|
| C-R1 | 本 repo 只部署至自有 staging，無外部法規框架（PCI／HIPAA／SOC2／GDPR）適用 | 本 intent 不需要做法規對應或稽核證據包 | [memory:M2]、ADR-0007 |
| C-R2 | episodic memory 保存 by-user 的對話歷程，須設保存期限且使用者可自行刪除自己的記憶 | 記憶層必須具備刪除介面與期限機制；刪除本身亦須留下稽核紀錄（見 ADR-0006 audit logging 面向） | [F5] |

## Assumptions & Open Questions

- C-R2 的**保存期限值**未定，留待後續階段。[assumption]
- C-O4 的成本上限**實際數值**不為本專案所掌握，故無法據以驗證「盡量省」
  是否足夠。[assumption]
- C-T5 是否成立，取決於語意記憶是否確定採向量檢索——該決定尚未做出。
  [assumption]
