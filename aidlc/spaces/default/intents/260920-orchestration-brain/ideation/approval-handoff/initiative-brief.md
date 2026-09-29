# Initiative Brief — 統一入口大腦

<!-- Stage: approval-handoff（Ideation 1.7）· Record: 260920-orchestration-brain
     本文件把 Ideation 五個執行站的產出壓成一份可決策的摘要，並交接給 Inception。
     引用的上游決定一律標註其來源（[Q<n>] intent-capture、[F<n>] feasibility、
     [S<n>] scope-definition、[R<n>] rough-mockups、[H<n>] 本站）。 -->

## 一句話摘要

在 Cloud-360 建一個統一入口的大腦：使用者說出需求，由它判斷要做什麼、交給
哪一個既有功能做，並在頁面之間維持同一段對話脈絡與同一個作業對象。10 項
能力中 9 項為 Must、1 項為 Should，判定為 **GO**。

## 問題與意圖

承自 `intent-statement.md`（`intent-capture/`）。要收斂的是三個同時存在的
痛點 [Q1]：沒有統一入口、上下文在頁面之間斷掉、AI 能力無法組合。為了讓
「上下文不斷掉」成立，系統必須能指出使用者當下正在處理哪一個對象，本次
確認以「專案 → 系統 → 架構圖」三層識別並記錄 [Q5]。

服務對象與其關係承自 `stakeholder-map.md`：架構設計者、評估／稽核者、
成本／FinOps 關注者為**直接服務**；管理者／平台維運者為**間接服務**（其需求
由長期記憶或既有稽核紀錄承載，不經由跨頁面的共享工作階段）[Q2][Q10][Q12]
[Q14]。決策結構為**單一決策者、無其他關係人、不需對外回報節奏** [Q8]。

成功以三項可量測結果判定 [Q3]：意圖識別準確率、跨頁面上下文保留率、首字
回應時間。**三項門檻值皆未定**，已指派 `requirements-analysis`（2.3）定案
[F7]。

## 市場驗證

**本 initiative 未做市場研究**：`market-research`（1.2）在 `agent-orchestration-brain`
這個 scope 為 SKIP，因此 `competitive-analysis.md` 不存在，本 brief 無市場
資料可引用。做這件事的理由不是市場訊號，而是**既有 AI 功能路徑已達極限**
——目前兩個生成入口彼此獨立，再加任何功能都會變成第三、第四個孤島 [Q4]。
此為內部技術債驅動的 initiative，非市場驅動；如實記載，不以「無資料」充當
「已驗證」。

## 可行性與風險重點

承自 `feasibility-assessment.md`、`constraint-register.md`、`raid-log.md`。

**GO，信心中等偏高**，理由分三層：

1. **最重的部分已經存在**：串流不是從零做（既有 3 個 SSE 端點有明文契約、
   架構圖共編另有 WebSocket）；LLM 供應商切換層已可用。
2. **新引入的元件各自成熟，且 LangGraph 已非新引入**：`langgraph==1.2.11`
   已釘選並隨既有成本 agent 通過 CI 與部署；Redis 仍為零引用，是本 intent
   真正新增的元件。修訂 1 的三項新決定（編排既有成本能力、自建編排層、
   就地呈現）未引入任何新服務、新依賴或新技術層，故此層信心**上調**。
3. **最大的不確定性不是新技術，而是既有資料**：既有架構圖直接掛在使用者
   底下，而 `schema_rbac.sql` 只在空的 data volume 執行（`C-T6`），既有
   staging 的遷移必須手動。

**進 Inception 時沒有任何早期訊號機制的三項風險**（決策者已於 [H5] 明確
接受，全部以已知殘留風險帶進去）：

| 風險 | 狀態 | 本 brief 的處置 |
|---|---|---|
| **R-1** 既有架構圖遷入新階層 | 可能性中／影響高；[F10] 已否決做試探 | 指派 `domain-design`（2.6）產出歸屬規則與回復方式 [H3] |
| **A-4** 「盡量省」是否守得住 OpenRouter 後台的成本上限 | `raid-log.md` 逐字記為**唯一無法驗證的假設**——本專案不掌握該數值 | 無法消除。以設計原則承載 [F11]，並在 `[F13]` 確認上限改由 OpenRouter 後台設定 |
| **R-8** 兩份 OpenRouter 客戶端／兩套串流事件語意漂移 | 可能性高／影響中；[Q13] 作答時已逐項揭露，屬知情選擇 | 指派 `contract-design`（2.8）把兩套事件語意收斂成一份共用契約 [H4] |

其餘六項風險（R-2 至 R-7、R-9）各有緩解方向，依 `feasibility:c6` 本階段
**只記方向不預選手段**；選定手段是設計階段的必答項。

**約束**（`constraint-register.md`，共 10 技術 ＋ 4 組織 ＋ 7 範圍 ＋ 2 法規）
中對 Inception 最有約束力的三條：`C-O1`（新增 compose 變數必須同 PR 寫入
`render-env.sh` 與 `.env.example`，失敗模式無聲）、`C-O2`（schema 變更時
`schema_rbac.sql` 與 `DEPLOY.md` 必須同步）、`C-S5`（大腦呼叫成本能力一律走
HTTP 並帶使用者 token，不得以同進程呼叫繞過既有授權）。

**ADR-0006 security baseline 四面向**在 feasibility 已逐項判定，**四項全部
適用、無不適用項**（IAM、encryption、network exposure、audit logging）。

## 範圍邊界

承自 `scope-document.md` 與 `intent-backlog.md`。

**在範圍內：10 項能力，無任何項目列入 Won't Have** [S5]。

| 分級 | 項數 | 能力 |
|---|---|---|
| **Must** | 9 | 意圖識別與工作交辦、跨功能共享脈絡與自動切換、子功能各自開新對話、長短期記憶（語意／程序／情節）、多意圖識別、多輪對話、串流式互動、專案→系統→架構圖階層、成本／FinOps 能力的編排 |
| **Should** | 1 | 主動通知推播 |
| Could／Won't | 0 | 皆為空，是分級結果而非疏漏 |

**Must 佔 90%**，高於 `prioritization-frameworks.md` 建議的 60% 上限。本站
**不再質疑**：`scope-definition` 已就此 push back 一次（[S8]），決策者據以
降級兩項；修訂 1 因上游前提變動又升回一項（[S11]）。兩次皆為決策者在知悉
佔比事實後的定案。

**在範圍外**（全數承自上游，本站未新增亦未移除）：雲端供應商 production
環境與其 credentials、environment-specific secrets、direct production IaC、
destructive cloud operations、native iOS/Android app [memory:M2]；成本計算
本身與「跨雲分析（by 專案）」[Q12]；本平台自身 LLM 花費的計量與 admin 設定
機制 [F13]；管理功能頁面不納入共享工作階段 [Q7]。

**交付排序**：風險優先 ＋ 不可覆寫的技術依賴序 [S10]。`intent-backlog.md`
的 10 個 proto-Unit 依序為：階層 → 意圖識別 → 串流 → 記憶 → 共享脈絡 →
多輪對話 → 多意圖 → 子頁面新對話 → 成本編排 → 主動推播。兩條**技術依賴
不可覆寫**：成本編排 → 意圖識別、主動推播 → 串流。

## 概念視覺

承自 `wireframes.md` 與 `user-flow.md`（`rough-mockups/`）。共 13 格線框，
涵蓋 10 項能力的逐項對照表 ＋ 5 條使用者流程（含錯誤路徑）。

版面骨架與落點已定案：入口頁進 Sidebar [R1]、採指定骨架 [R2]、作業對象在
子頁面以脈絡列呈現 [R3]、成本答案以結構化卡片就地呈現 [R4]、`progress`
事件以單一則就地更新的訊息呈現 [R5]、子頁面「另開新對話」入口由脈絡元件
統一承載 [R6]、無障礙底線 [R7]、入口頁權限走 `DefaultRedirect` 瀑布 [R8]。

第 12、13 節為**意圖識別的失敗面**（信心不足時列候選並反問、不交辦；交辦
錯了使用者可逐項導回），是 1.6 核可關卡上人工退回後補上的。

**一項已接受的殘留發現**：rough-mockups 審查的 R-06（Minor）——第 13 節
ASCII 框內「這件沒有產生任何變更，不需要你回頭清理」是無條件語氣，其限定
（這是該情境的文案、非普遍承諾）寫在 30 行外的本文。核可時以**已接受風險**
放行，帶進 `refined-mockups`（2.5）處理。

## 團隊計畫

**無團隊計畫可交付**：`team-formation`（1.5）在本 scope 為 SKIP，故
`team-assessment.md` 不存在。[Q8] 已確認單一決策者、無其他關係人、無跨團隊
協調成本（`C-O3`）。`team.md` 的 Q3 定案 `skeleton: off`，故**不走
walking-skeleton 儀式**，第一個 Bolt 照常跑。

Bolt 編組與序列由 `delivery-planning`（2.9）承接；本站只交付能力層級的
交付序（見上方範圍邊界）。

## Go / No-Go 建議

### **GO**

依據：feasibility 的三層理由全部成立且修訂 1 後信心上調；三項無早期訊號的
風險（R-1、A-4、R-8）已由決策者於 [H5] 明確接受為已知殘留風險，其中兩項
（R-1、R-8）在本站已釘到具體的執行站，第三項（A-4）本質上不可驗證且其成因
在專案之外。

**本 GO 不附帶任何進入 Inception 的前置條件** [H5]。

## 進入 Inception 的交接事項

本站的核心工作是把上游「指派目標不明確或不存在」的缺口逐一釘死。依
`units-generation:260822-ug-L2`，指派落在 `CONDITIONAL` 的站上必須註明
skip 風險並指出誰確認——故每一列都附 execution 欄與轉移目標。

| # | 交接事項 | 指派給 | execution | skip 時轉移至 | 來源 |
|---|---|---|---|---|---|
| 1 | P-1（LangGraph 編排模型）與 P-2（記憶層資料模型）兩個技術試探的**實際執行** | `domain-design`（2.6） | CONDITIONAL | `units-generation`（2.7） | [H1]、[F6] |
| 2 | 主動通知推播的**觸發情境與接收對象** | `requirements-analysis`（2.3） | **ALWAYS** | 不適用 | [H2] |
| 3 | episodic memory 的**保存期限值** | `requirements-analysis`（2.3） | **ALWAYS** | 不適用 | [H2]、[F5] |
| 4 | 三個成功指標的**門檻值** | `requirements-analysis`（2.3） | **ALWAYS** | 不適用 | [F7]、[Q3] |
| 5 | R-1 既有架構圖遷入新階層的**歸屬規則、遷移步驟與回復方式** | `domain-design`（2.6） | CONDITIONAL | `units-generation`（2.7） | [H3]、[F10] |
| 6 | R-8 兩份 runtime 的**一致性驗證**（把兩套串流事件語意收斂成共用契約） | `contract-design`（2.8） | CONDITIONAL | `tcms-test-cases`（3.8） | [H4]、[Q13] |
| 7 | 外部成本上限觸發時的**系統行為**（R-4，方向為明確降級而非靜默失敗） | 設計階段 | — | — | [F13] |
| 8 | 兩種串流機制並存的**邊界**（哪些路徑走 WebSocket、哪些維持 SSE） | 設計階段 | — | — | [F4] |
| 9 | 語意記憶**是否採向量檢索**（決定 pgvector 與換映像的前置是否成立） | 設計階段 | — | — | feasibility A-2、`C-T5` |
| 10 | rough-mockups 審查 R-06（第 13 節框內文案的無條件語氣） | `refined-mockups`（2.5） | CONDITIONAL | `functional-design`（3.1） | 1.6 核可時列為已接受風險 |
| 11 | 路由層模型候選 `typesafe/jev-1.13` 的採用與否 | `nfr-requirements`（3.2） | CONDITIONAL | **無自然承接站**（見下） | 1.6 核可關卡上使用者指定列入正式待辦 |
| 12 | 能力 3（子功能各自開新對話）、5（多意圖識別）、6（多輪對話）各自的**可測不變量** | `requirements-analysis`（2.3） | **ALWAYS** | 不適用 | 本站的階段邊界檢查（見下） |

**轉移規則（本站訂定）**：第 1、5、6、10 列的目標站為 `CONDITIONAL`。若該站
在其執行時被判定為不適用而 skip，其義務**自動轉移**至上表指定的站；確認者是
屆時執行該站的 conductor。沒有這條規則，這些指派會在 skip 當下無聲落空。

**第 11 列（Jev）沒有轉移目標，如實記載**：它的目標 `nfr-requirements`（3.2）
為 CONDITIONAL，而唯一在主題上相鄰的 `nfr-design`（3.3）的執行條件是「NFR
Requirements 已執行」——前者被 skip，後者必然一併被 skip。也就是說，若
`nfr-requirements` 被判定不適用，**本工作流程沒有任何一站會自然接下這件事**。
處置不是發明一個假的承接站，而是：屆時判定 skip 的 conductor 必須在該 skip
的當下把這一項重新提交給使用者裁決，不得讓它隨 skip 一起消失。

第 7、8、9 列承自 feasibility，其指派對象為概括的「設計階段」。本站未再細分
——它們與第 1、5、6 列不同，不綁定單一站的產出形式，且 `domain-design` 與
`contract-design` 之外仍有 `nfr-design`、`infrastructure-design` 可承接。

**第 11 列（Jev）的補充**：`typesafe/jev-1.13` 在 OpenRouter 上可取得，其
`output_modalities` 為 `["decisions"]`（型別化決策＋信心分數），適用面為
能力 1（意圖識別與工作交辦）與能力 5（多意圖識別），不適用能力 8（大腦自身
回覆的串流，它不產生文字）。採用與否**不需推翻任何已核可決定**——[F1] 逐字
已允許「編排層與功能 agent 可以用不同模型」。應在能力 1 有實測準確率與延遲
基準後再與 `gemini-3.7-flash` 比較定案。保留：`decisions` 輸出保證回傳是
合法的型別化選擇，不保證該選擇正確，而「意圖識別準確率」量的是後者。

### 階段邊界檢查的結果（`<record>/verification/phase-check-ideation.md`）

四項檢查中三項 PASS、一項 **PASS WITH WARNINGS**：

- **檢查 1（Intent → Scope → Backlog 一致性）PASS**：三份文件的能力集合為
  同一組 10 項，無孤兒能力、無孤兒 proto-Unit。
- **檢查 2（scope 項目的 feasibility 背書）PASS WITH WARNINGS**：**能力 3
  （子功能各自開新對話）、5（多意圖識別）、6（多輪對話）三項 Must 在三份
  feasibility 產出中的關鍵詞計數分別為 0、1、0**——它們很可能被隱含在能力 1
  與 2 的評估裡，但隱含不等於背書。三項都不引入新服務或新技術層，風險型態
  是「需求寫不清楚」而非「做不出來」，故不阻擋；已列為上表第 12 列。
- **檢查 3（產出完整性）PASS**：兩項缺席（`competitive-analysis.md`、
  `team-assessment.md`）為 scope 設計的結果，非遺漏。
- **檢查 4（跨階段矛盾）PASS**：查出的兩項不一致（`application-design` 不
  存在、指派落在 CONDITIONAL 站）皆已在本站處置。

### `domain-design`（2.6）的負載集中

[H1] 與 [H3] 的直接後果：該站將同時承載五件事——(a) 專案→系統→架構圖 階層
的資料模型、(b) 記憶層資料模型、(c) 編排層模型、(d) P-1 與 P-2 兩個試探的
實際執行、(e) R-1 既有資料遷移的歸屬規則與回復方式。這不是缺陷，是兩個
決定的後果；如實記載，使下游在規劃該站工作量時看得到。

## Assumptions & Open Questions

- 三項成功指標的門檻值、episodic memory 的保存期限值、主動通知推播的觸發
  情境與接收對象，在本 brief 產出時**皆無數值**；本文件不對任何數值做出
  承諾，僅記載其定案落點 [assumption]
- 兩個技術試探的**時間盒**未定（`A-1` 假設半天到兩天，未經驗證）；[H1] 定案
  它們併入 `domain-design` 執行，但該站要為它們保留多少時間本站未確認 [assumption]
- 語意記憶是否採向量檢索未定，故 `C-T5`（換映像取得 pgvector）是否成立
  無法判定 [assumption]
- 「盡量省」的設計原則是否足以守住 OpenRouter 後台的成本上限，**在本 intent
  內沒有判定依據**——本專案不掌握該上限數值 [assumption]
- 本站訂定的轉移規則（CONDITIONAL 站 skip 時義務自動轉移）尚未被任何機械
  檢查承載，其生效仰賴屆時執行該站的 conductor 讀到本表 [assumption]
- `competitive-analysis.md` 與 `team-assessment.md` 因對應站 SKIP 而不存在，
  故本 brief 的「市場驗證」與「團隊計畫」兩節無上游資料可引用；這是 scope
  的結果而非產出缺漏 [assumption]
