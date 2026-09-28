---
name: agent-orchestration-brain
depth: Standard
keywords: []
description: Composed scope - LangGraph 統一入口大腦，編排功能 agent，含 Redis session 層、Postgres 三種記憶、跨頁共享 context 與串流回覆
skeleton: off
---

# agent-orchestration-brain scope

由 adaptive-workflows composer 合成的 scope（ARS 74 / Standard），用於建造
Cloud-360 的**統一入口大腦**：以 LangGraph 為框架的編排層，把使用者意圖分派給
既有與新增的功能 agent（架構設計 agent、成本／FinOps agent 等），並帶一個以
Redis 承載的 session 層（記錄識別意圖後鎖定的專案／系統／架構圖 id，用來判斷
當下正在改動的對象是誰）、一個以 PostgreSQL 承載的長短期記憶層
（semantic / procedure / episodic），入口頁與各功能頁共享同一個 session 且可
在子頁面另開新 session，並以串流架構支撐多意圖識別、多輪對話與主動通知推播。

這個 scope 是**合成的，不是推論出來的**。`keywords: []` 是刻意的：它只能用
`--scope agent-orchestration-brain` 明確叫出，永遠不參與 scope 自動偵測。

## Entropy profile

| Component | Score | Band |
|-----------|-------|------|
| Intent Ambiguity (IAE) | 0.70 | HIGH |
| Codebase Structural Uncertainty (CSU) | 0.80 | HIGH |
| Verification Entropy (VE) | 0.75 | HIGH |
| Risk / Blast Radius (R) | 0.65 | MED |
| Unresolved Assumptions (UA) | 0.75 | HIGH |
| **Composite (advisory)** | **74 / 100** | **Comprehensive** |

以 fallback 路徑評分：CodeKB MCP server 未曝露，因此結構類分數來自 workspace
scan 加上對受影響子圖的有界閱讀（`backend/services/` 的模組清單、
`llm_provider.py`、`collab_router.py` 的 WebSocket 段、`deploy/`，以及一次確認
repo 內 Redis 與 LangGraph 引用為零的 grep），另讀了本地 reverse-engineering
產物 `aidlc/spaces/default/codekb/cloud-360/`。**無 call-graph 證據。**

CSU 最高。這層要同時碰後端既有的 agent 路徑（`agent_router`、`design_agent`、
`review_orchestrator`、`wa_collab_orchestrator`）、全新的 Redis session 層、
Postgres 記憶層，以及前端每一頁的共享 context。既有的本地 RE 產物基準為
`9307dbc`，自述為兩區定向掃描、約七成內容新鮮度停在更早的基準且已落後
`origin/ut`；它自己列出的「觸發完整重跑」條件中，「引入訊息佇列或快取層」與
「部署拓撲變更（新容器）」被本任務**同時命中**。

VE 次高。本 repo 無覆蓋率量測機制、前端無 unit／component 測試框架（唯一自動化
層是 Playwright e2e）、HTTP 層覆蓋極低，而 `project.md` 已明文把「所有 LLM 路徑」
列為自動化層的結構性盲區——那正是這個大腦的主體。

UA 高。session TTL、Redis 失效時的降級行為、三種記憶的保存期與隱私邊界、多意圖
衝突如何收斂、是否取代既有的 agent 端點，目前都沒有答案。

R 落在 MED 上緣：影響每一個頁面、新增對外模型憑證與網路暴露面（觸發 ADR-0006
security baseline 的四個面向）、且會把使用者層級的 episodic memory 寫進資料庫；
但部署目標僅限自有 staging，且已有自動 rollback 與 revert PR 機制。

## Membership

28 stages EXECUTE，6 stages SKIP。

**Ideation** 保留 intent-capture、feasibility、scope-definition、rough-mockups
與 approval-handoff。feasibility 的 condition 條款在這裡真的命中——LangGraph
採用、模型路由、Redis 引入與串流傳輸都是顯著技術不確定性。rough-mockups 不
折疊進 refined-mockups，因為跨頁共享 session 的呈現形狀（獨立入口頁／常駐側欄／
命令面板）存在真正分歧的 UX 方向，值得先用低成本線框比較再投入高保真。

- **market-research → SKIP**：產品定位已由 ADR-0001／0002 與既有 SRS 定案，
  這是既有產品的內部平台能力，沒有未知市場要研究。它名義上要降的 IAE 屬規格層
  而非市場層，由 intent-capture 與 requirements-analysis 收斂。
  *翻回 EXECUTE 的觸發*：這個大腦要獨立對外銷售或定位為另一個產品。
- **team-formation → SKIP**：單一決策者、無跨團隊協調，`project.md` 已把這點
  記為既成事實（也是不做 WSJF／RICE 數值評分的理由）。沒有團隊拓撲要決定。
  *翻回 EXECUTE 的觸發*：功能 agent 由第二個團隊擁有。

**Inception** 全開，只砍 practices-discovery。reverse-engineering 是這一段的
承重站：CodeKB 不可用，只有它會寫下游 design 與 generation 階段實際讀取的本地
RE artifact store，而既有那一份對本次受影響區域全部標為「未重新推導」。
units-generation、contract-design、delivery-planning 三站都逆機械篩選的預設
un-SKIP：工作明顯拆成多個單元（orchestrator graph、session store、memory store、
意圖路由、功能 agent adapter、串流傳輸、推播、前端共享 context、模型路由）；
brain ↔ 功能 agent 的工作契約與 brain ↔ 前端的 session／串流 API 都是正式契約，
且本 repo 已由 `openapi.json` 產生 `api.d.ts` 卻存在已知的前後端型別斷點；
delivery-planning 則要處理非平凡的依賴圖，以及 deploy-on-merge 之下
「破壞性契約變更與其消費端必須同批次」這條本 repo 學到的隱含約束。
user-stories 逆折疊保留，因為 blocking 的 `tcms-test-cases` 會逐字比對
`stories.md` 的 AC。

- **practices-discovery → SKIP**：`team.md` 與 `project.md` 的實踐層已於
  2026-08-09 與 08-16 affirmed 且內容厚實（測試 A／B／C 規則、code style、
  部署、branch／commit 慣例），會隨每個 stage 載入規則鏈。重跑此站會整段替換
  `team.md` 的五個 section，而這個刪除風險本 repo 已親身記載過。真正新的驗證
  問題（LangGraph 圖、Redis session 狀態、串流）落在 nfr-requirements 與
  `tcms-test-cases`。
  *翻回 EXECUTE 的觸發*：團隊希望在動工前先把 LangGraph／Redis 的慣例正式
  寫進 `team.md`。**這是本 grid 中最值得重新考慮的一格**——LangGraph 與 Redis
  確實構成「從零選一套新工具鏈」，正好命中此站的 un-SKIP 條件。

**Construction** 全開。nfr-design 不折疊進 nfr-requirements，因為這裡不是單一
可量測目標，而是多個互相牽動的 NFR：串流首字延遲、Redis 失效時的降級路徑、
記憶保存期與隱私、模型成本控制、推播送達保證，再加上 ADR-0006 的四個面向。
infrastructure-design 承擔新的 Redis 容器與 Postgres 記憶 schema，兩者都會觸發
`project.md` 的 blocking 同步規則（`schema_rbac.sql` ＋ `DEPLOY.md`、
`render-env.sh` ＋ `.env.example` 環境契約）。ci-pipeline 保留，因為
`docker-compose.test.yml` 起的短生命週期 stack 需要納入新服務。
`tcms-test-cases` 在本 repo 是每個 intent 的 construction 必經且 blocking 的
階段（`project.md ## Mandated`，編譯圖中 `execution: ALWAYS`）；機械篩選漏掉它
只是因為 priors 表沒有它的成本項。

**Operation** 保留 deployment-pipeline、deployment-execution、
observability-setup 與 performance-validation。「利用 streaming 架構做到快速
回覆」是明寫的效能 NFR，由 nfr-requirements 釘住目標、performance-validation
收斂。observability-setup 保留的理由是這層是一個新的常駐執行期面，其失效模式
（Redis 斷線、模型閘道限流、串流停滯）全屬靜默失敗，而本 repo 已被同型的靜默
失敗咬過。

- **environment-provisioning → SKIP**：沒有新環境要開。staging 是唯一部署
  目標，雲端 production 環境由 ADR-0001／0002 排除在範圍外。Redis／Postgres 的
  拓撲決定落在 infrastructure-design，compose 與 env 接線落在
  deployment-pipeline。
  **已知 advisory**：deployment-execution 的 `environment-inventory` 輸入因此
  無產出者。在 brownfield 這是 advisory 而非缺陷——實際的環境盤點是
  `DEPLOY.md` ＋ `deploy/docker-compose.deploy.yml` ＋ `deploy/.env.example`，
  由 `project.md` 的 blocking 規則保證與變更同步。此折疊已在核可閘門揭露。
- **incident-response → SKIP**：staging 已有自動 rollback（還原 last-good、
  開 revert PR）與 Deploy Doctor 自癒 workflow，新失效模式的告警由
  observability-setup 承擔。獨立 runbook 只會多一份文件而沒有新的 on-call 面。
  *翻回 EXECUTE 的觸發*：這個大腦取得正式 on-call 輪值或 SLO 承諾。
- **feedback-optimization → SKIP**：本 intent 沒有承諾上線後的量測迭代迴圈；
  repo 持續部署到 staging，改善由 AI-DLC 的 learning loop 與下一個 intent 承接。
  *翻回 EXECUTE 的觸發*：本 intent 要自己擁有一輪有量測的使用回饋循環。

## Depth

`depth: Standard` 而非 Comprehensive。28 個階段本身已經承載了覆蓋面，
Comprehensive 會再把每個階段的產出量乘上去。若個別設計站需要更深，
以 `/aidlc --depth` 逐案覆寫，不改這個 scope 的預設值。

## Skeleton

`skeleton: off`，沿用 `aidlc/spaces/default/memory/team.md` 記載的團隊定案。
本專案自 baseline 起已有可運行的 backend／frontend、四道 CI 關卡與自動部署，
管線成熟度已超過「需要走 skeleton 驗證端到端管線是否打通」的階段。這份工作
疊的是新的應用層，不是打通新的交付管線。
