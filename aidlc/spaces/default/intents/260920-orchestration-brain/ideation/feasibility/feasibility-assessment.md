# Feasibility Assessment — 統一入口大腦

本文件評估 `intent-statement.md` 所述能力的技術可行性與風險。依
`phases/ideation.md`，可行性估計採保守立場、假設一律明確標示，且不下沉到
實作設計。來源標籤定義見 `feasibility-questions.md` 的 `## Sources`（S1–S13）
與各題 `[F<n>]` 作答。

## 消費的上游輸入

本 stage 消費 `<record>/ideation/intent-capture/intent-statement.md`：其
Problem Statement、Target Customer、Success Metrics、Initiative Trigger 與
Initial Scope Signal 五段皆為本評估的前提，其中作業對象採「專案 → 系統 →
架構圖」三層 [Q5]、**編排既有的真實成本能力** [Q12]、共享工作階段涵蓋統一
入口與兩個功能頁 [Q7]、成本答案就地在入口頁呈現 [Q14]，本評估不改動這些
已核可的決定。

（修訂 1：本段原寫「成本能力只做交接介面 [Q6][Q11]」，其前提「成本能力
不存在」已被上游推翻，Q6／Q11 已由 Q12 取代，改以 [Q12][Q14] 為準。）

## Go / No-Go 判定

**GO，信心為中等偏高。**

理由分三層，每層都對照實測事實而非印象：

**第一層：最重的部分已經存在。** 「串流快速回覆」不是從零做——既有
`agent_router.py` 已有三處 SSE 回應且有明文契約 [S3]，架構圖共編另有
WebSocket [S4]；LLM 供應商切換亦已可用 [S5 之外的 intent-capture 查證]。
本 intent 在這兩件事上是「選用哪一種」而非「能不能做」。

**第二層：新引入的元件各自成熟；其中 LangGraph 在本 repo 已有可運行前例，
Redis 仍無。** 修訂 1 重新查證後，這一層的事實與原評估不同，且方向是**信心
上調**而非下調：

- **LangGraph 已非新引入**。`backend/requirements.txt` 已釘選
  `langgraph==1.2.11` 與 `langchain-openai==1.6.2`，`services/langgraph_runtime.py`
  已提供 OpenRouter 版的 invoke/stream/astream，`cost/cost_advice_agent.py`
  已以它建 `StateGraph` 並在部署環境運行 [V8]。原評估所依據的「引用為 0」
  [S6] 對 LangGraph 已不成立。
- **Redis 仍為 0** [V9]。`backend/`／`deploy/` 的 `redis` 命中皆為
  Well-Architected 規則引擎中的雲端服務名稱字串與定價表資料，非實際依賴。
  這一半的原評估維持成立。

逐項對照可行性面向後，修訂 1 的三項新決定（[Q12] 編排既有成本能力、
[Q13] 自建編排層、[Q14] 就地呈現）**未引入任何新服務、新依賴、新基礎設施
或新技術層**：成本能力已存在且以 HTTP 呼叫 [F14]，LangGraph 已是釘選依賴，
狀態事件轉譯不需要新機制 [F15]。故 GO 維持，且本層的信心較原評估**提高**。

<!-- 修訂 1 存檔於 2026-09-21，對應 feasibility 的 Consolidated Summary
     Confirmation 收據。本檔的修訂範圍：前提段的成本能力引用、能力表的
     成本／串流／自建 runtime 三列、Go/No-Go 第二層、驗證計畫的 LangGraph
     試探收窄。 -->

**第三層：最大的不確定性不是新技術，而是既有資料。** 上游 [Q5] 已把
「建立專案 → 系統 → 架構圖 階層」定為第一級範圍項，而既有架構圖直接掛在
使用者底下。`schema_rbac.sql` 是 init script、只在空的 data volume 上執行
[S10]，既有 staging 的 volume 非空，故遷移必須手動。本站未以試探消除此風險，
改為對設計階段的明確指派 [F10]——見下方「對下游的指派」。

判定為 GO 而非 Conditional GO：三層之中沒有任何一項指向「做不到」，最重的
未知（遷移）有明確歸屬而非懸空。

## 技術可行性逐項

| 能力 | 判定 | 依據 |
|---|---|---|
| 統一入口的意圖識別與工作交辦 | 可行 | 編排框架為 LangGraph [desc]；模型路由沿用既有切換層並允許大腦獨立指定模型 [F1]。既有 agent 能力已模組化（`design_agent`、`review_agent`、`wa_collab_orchestrator`），有可被編排的對象 |
| 跨功能共享的對話脈絡 | 可行 | session 層以新增的 Redis 容器承載 [F2]；涵蓋範圍限於統一入口與兩個功能頁 [Q7] |
| 三種長短期記憶 | 可行，但有一項前置 | 落點為同一 database、獨立 schema [F3]，跨 schema join 為原生能力，可支撐「只搜這個專案的記憶」這類混合查詢。**前置**：語意記憶若採向量檢索，現用的官方 `postgres:16-alpine` 不含 pgvector [S9]，須換映像或自建映像——屬拓樸層變更 |
| 記憶層的授權 | 可行 | 記憶層內建最小權限模型（擁有者與可見範圍欄位），介接的應用系統以自身角色對應映射到這組欄位 [F9]。DB 層邊界則由「grant 只鎖到記憶 schema」承載 [F3] |
| 串流回覆與主動推播 | 可行 | 改用 WebSocket [F4]，既有共編 WebSocket 為可參照的前例 [S4]。代價：既有 3 個 SSE 端點維持不動，系統內將有兩種串流機制並存 |
| 專案 → 系統 → 架構圖 階層 | 可行，風險集中在遷移 | 新資料模型本身無技術障礙；困難在既有資料的歸屬與既有頁面的相容（見上方第三層與 RAID R-1） |
| 編排既有的成本／FinOps 能力 | 可行 | 該能力已存在（`backend/cost/`，`/api/cost/v1` 下 10 條端點）[Q12]。大腦以 HTTP 帶使用者 token 呼叫，既有的 `require_story_action("C1",…)` dependency 照常執行，授權不可被繞過、稽核主體為使用者本人 [F14][V-F2]。本 intent 不新建成本計量 |
| 成本回覆的串流交接 | 可行，且比預期簡單 | 成本端的「串流」實為 job 狀態輪詢（每秒查 DB，送 `progress`／`completed`／`timeout`／`failed`／`heartbeat`），非 token 級串流 [V-F1]。大腦把狀態事件轉譯進自己的訊息流即可，不需要逐 token 轉送 [F15]。代價：進度文字與 `timeout`／`failed` 兩種終態的訊息設計屬下游 |
| 大腦自建獨立的編排執行層 | 可行，但引入一致性負債 | 既有 `services/langgraph_runtime.py` 已提供 OpenRouter 版 invoke/stream/astream 並為成本 agent 所用 [V8]；使用者知情選擇自建而非沿用 [Q13]。後果是系統內並存兩份 OpenRouter 客戶端與兩套串流事件語意，正是 `team.md` `## Code Style` 單一真實來源規則管制的形狀。緩解方向為「鎖住兩者一致性的驗證」，具體手段不在本站預選（見 RAID） |

## 驗證計畫（技術試探）

本站決定以兩個用完即丟的技術試探降低最高的兩項不確定性 [F6]：

| 試探 | 要回答的問題 | 不做的話會怎樣 |
|---|---|---|
| LangGraph 編排模型（**修訂 1 已收窄**） | 原問題為「LangGraph 能否乾淨地包住既有那些以 SSE 回應的 agent 端點」。該問題**已由 repo 內的可運行前例回答**：`cost/cost_advice_agent.py` 正是「LangGraph 圖 ＋ 以 SSE 對外」的形狀且已在部署環境運行 [V8][V-F1]。收窄後要回答的是本 intent 獨有的部分：**多意圖識別的分支結構、session 資訊如何注入圖、以及大腦自建的 runtime [Q13] 與既有那份要如何維持一致** | 收窄前的版本會重複驗證一件 repo 已經證明的事；收窄後未做的話，R-8 的一致性負債沒有任何早期訊號 |
| 記憶層資料模型 | 三種記憶各自的形狀與查詢方式，以及換映像取得向量檢索的代價 [S9] | 資料模型錯誤會同時波及 schema、查詢與部署拓樸三處 |

試探不進正式程式碼、不求品質，只為回答上述問題；答案取得後即丟棄。

**未被試探涵蓋者**：既有資料遷移。此為本站經覆蓋檢查主動指出的缺口
[F10]，處置見下。

## 對下游的指派

以下為本站識別、但本站不處置的事項。若下游未接到，該風險即無聲落空。

| 指派對象 | 事項 | 來源 |
|---|---|---|
| application-design 或 functional-design | **既有架構圖遷入新階層的具體步驟與回復方式**，須涵蓋：既有資料的歸屬規則、既有頁面在遷移前後的相容、以及 `schema_rbac.sql` 只在空 volume 執行 [S10] 所導致的手動遷移程序 | [F10] |
| requirements-analysis | **三個成功指標的門檻值定案**（意圖識別準確率、跨頁面上下文保留率、首字回應時間） | [F7]、[Q3] |
| 設計階段 | **外部成本上限觸發時的系統行為**（緩解方向見 RAID R-4，本站不預選手段） | [F13] |
| 設計階段 | **兩種串流機制並存的邊界**（哪些路徑走 WebSocket、哪些維持 SSE） | [F4] |

## ADR-0006 Security Baseline 四面向逐項判定

依 `project.md ## Mandated`，此為 hard constraint，四面向缺一不可，判定為
不適用者亦須附理由。

| 面向 | 判定 | 說明 |
|---|---|---|
| IAM | **適用** | 記憶層採兩層授權：DB 層以 grant 只開放記憶 schema [F3]；應用層由記憶層內建的最小權限模型（擁有者、可見範圍）承載，介接系統映射自身角色 [F9]。新增的 Redis 容器亦需其連線憑證的最小權限設定 |
| Encryption | **適用** | episodic memory 為 by-user 的對話紀錄，屬個人可識別的使用歷程；其靜態儲存與傳輸的加密要求須於設計階段明確。本站不預選手段 |
| Network exposure | **適用** | 新增 Redis 容器改變部署拓樸 [F2]；其對外暴露面必須為零（僅限 compose 內部網路）。WebSocket 端點 [F4] 為新的對外介面，須沿用既有的認證方式 |
| Audit logging | **適用** | 管理者／平台維運者的需求即由長期記憶或既有稽核紀錄承載 [Q10]，故記憶層的寫入與刪除事件本身構成稽核來源；F5 的「使用者可自行刪除」亦須留下刪除紀錄，否則稽核與刪除權互相抵消 |

四面向皆判定為適用，無不適用項。

## Assumptions & Open Questions

- 兩個技術試探的**時間盒**未定（半天或兩天）。本站僅確認要做，未確認各自
  的時間上限。[assumption]
- 語意記憶是否確定採**向量檢索**未經確認。若不採向量檢索，pgvector 與換
  映像的前置即不成立；若採用，該前置為必經步驟 [S9]。[assumption]
- 成本上限由 OpenRouter 後台承載 [F13]，**本專案不掌握其實際數值** [F11]。
  因此本評估無法判斷「盡量省」的設計原則是否足以守住該上限。[assumption]
- episodic memory 的**保存期限值**未定 [F5]，故無法估算記憶層的資料量成長
  與其對查詢效能的影響。[assumption]
- LangGraph 的**版本與其對 Python 3.12 [S7] 的相容性**未經實測；本站的
  可行性判定假設其相容。[assumption]
