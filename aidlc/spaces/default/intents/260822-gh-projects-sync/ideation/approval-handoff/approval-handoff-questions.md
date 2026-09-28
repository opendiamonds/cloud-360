# Initiative Approval & Handoff — 釐清問題

> Stage: approval-handoff（Ideation 1.7）· Depth: Standard · Scope: aidlc-github-projects-sync
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。

## 省略的範例題與理由

本站為彙整型 stage，依 `project.md ## Corrections` 只問未被上游定案的事項。stage 檔的六個範例題中，四題省略：

| 範例題 | 省略理由 |
| --- | --- |
| Do all stakeholders agree on the intent and scope? | 單一決策者 [intent:Q5]，且 intent-capture、feasibility、scope-definition 三站的 gate 皆已由該決策者核可。重問等於重開已核可的閘。 |
| Is there budget/resource commitment? | 本 intent 不新增雲端資源、不產生授權費用，唯一成本是實作工時；且已確認無硬時程 [scope:Q6]。預算問題對本 intent 無實質內容。 |
| Do the rough mockups reflect the shared vision? | `rough-mockups` 依 scope 設計跳過，無 wireframes 產出可供比對。 |
| Does the market research support the investment? | `market-research` 依 scope 設計跳過，無 competitive-analysis／market-trends／build-vs-buy 產出。 |
| Are mobs staffed and scheduled? | `team-formation` 依 scope 設計跳過；單一決策者，無 team-assessment 產出。 |

保留並改寫的一題為「critical risks 是否已被確認並有緩解」（下方 Q1），另新增兩題（Q2 Go/No-Go 判定、Q3 下一站範圍）。

## 上游輸入

- `../intent-capture/intent-statement.md`（**intent-statement**）與 `../intent-capture/stakeholder-map.md`（**stakeholder-map**）
- `../feasibility/feasibility-assessment.md`（**feasibility-assessment**）、`../feasibility/constraint-register.md`（**constraint-register**）、`../feasibility/raid-log.md`
- `../scope-definition/scope-document.md`（**scope-document**）與 `../scope-definition/intent-backlog.md`（**intent-backlog**）
- 依 scope 設計不存在：**competitive-analysis**、**team-assessment**、**wireframes**

---

## Q1. 下列五項在進入 INCEPTION 時仍未解，確認知悉並接受帶著它們往下走嗎？

> 依 `project.md ## Corrections`，本題的已答清單即構成人工確認，不另設重複的 Assumption Confirmation 關卡。

| # | 未解項 | 目前處置 |
| --- | --- | --- |
| U-1 | **RSK-7 憑證權限未驗證** — 框架以 job 權限欄位鑄造憑證，但該欄位無組織層看板的鍵。此為整條路徑的單點失敗，且現已同時承擔 P-1（App 是否真的安裝到 org）的驗證責任 | 指派 application-design 展開前實測 [scope:Q3] |
| U-2 | **CAP-7 建立欄位可行性未知** — 框架的安全輸出清單有建立看板與建立檢視，無建立欄位 | 不可行時退回人工建立 [scope:Q9] |
| U-3 | **RSK-1 首次建立無回讀保護** — 自動建立追蹤項目的那一刻尚無既有對象可比對，CAP-6 的防護在該時刻不成立 | 未解，指派 application-design 補首建專屬檢查 |
| U-4 | **RSK-4 產出檔無閘門** — 代理式工作流程的 `.lock.yml` 不受任何 CI 檢查，定義與產出漂移不會被發現 | 未解，指派 ci-pipeline |
| U-5 | **交付批次張力** — 十項全 Must 且宣告一次做完 [scope:Q1]，與 `org.md` 短生命週期分支（1–2 天）在 deploy-on-merge 下正面相交 | 未解，指派 delivery-planning |

A. 全部確認並接受 — 帶著這五項進入 INCEPTION，各自依上表指派的落點處理
B. 大致接受，但有一項要先處理 — 請在答案中說明是哪一項、以及要在什麼時點處理
C. 不接受 — 其中有項目應該先解決才進 INCEPTION（請說明）
X. Other (please specify)

[Answer]:A. 全部確認並接受 — 帶著這五項進入 INCEPTION，各自依上表指派的落點處理

## Q2. Go/No-Go 判定確認

> feasibility 的判定是 **conditional GO**，條件之一（P-2 憑證存入）已於本站查證完成，另有 P-1／P-3／P-4 未完成。本題確認以什麼姿態跨越 phase 邊界。

A. Conditional GO — 進入 INCEPTION，未完成的前置依賴由 U-1 的實測與各指派落點處理。INCEPTION 全是設計與規劃工作，不需要憑證即可進行。
B. Full GO — 視為無條件通過，不保留 conditional 字樣（此選項需你確認前置依賴確實已不構成條件）。
C. Hold — 暫停在 phase 邊界，等 P-1／P-3／P-4 全部完成再進 INCEPTION。
D. Reject Initiative — 終止本 intent。
X. Other (please specify)

[Answer]:A. Conditional GO — 進入 INCEPTION，未完成的前置依賴由 U-1 的實測與各指派落點處理

## Q3. INCEPTION 第一站 reverse-engineering（2.1）的掃描範圍

> composer 把這站從 SKIP 改為 EXECUTE 的理由是：本機制的資料來源是 AI-DLC 自身的狀態表徵，而該表徵在各 record 之間並不一致（有的 record 機器欄位為空、有的已填；逐 stage 表用 Pending／Active／Verified／Skipped，頂層卻用 Completed）。掃描範圍若不限定，會變成無目的的全 repo 巡覽。

A. 限定在兩塊 — ①AI-DLC 狀態表徵（state 檔的欄位、逐 stage 表、intents.json 的 status）；②既有 12 組 gh-aw workflow 的形狀與慣例。這兩塊正是本機制要讀的與要仿的。
B. 加上第三塊 — 另掃既有 CI workflow（`ci.yml`／`deploy.yml`）以了解新 workflow 要與什麼並存。
C. 不限定 — 全 repo 掃描，讓 RE 自行判斷什麼相關。
D. Not yet defined — 留給該站自行決定範圍。
X. Other (please specify)

[Answer]:A. 限定在兩塊 — ①AI-DLC 狀態表徵 ②既有 12 組 gh-aw workflow 的形狀與慣例

---

## Consolidated Summary Confirmation

本站三題均以結構化選單單選作答，選項全文於作答當下完整呈現，答案即為其字面內容（Q1=A、Q2=A、Q3=A）。依 `project.md ## Corrections`（彙整 artifact 的清單若與問題檔某題的已答內容逐字對應，該題作答即為人工確認），不另設重複的彙整確認關卡。Q1 的已答清單同時構成 U-1～U-5 的假設確認。

[Answer]: A. Looks correct（由 Q1／Q2／Q3 的選單作答直接構成，未另設重複關卡）

---

## Revision 1（2026-08-23）

**觸發**：ADR-0012 未被引用的缺口被發現 → 開立 ADR-0013 → 回跳 scope-definition 擴充範圍（CAP-11 反向同步）→ 本交接包重製。

**既有答案不動**：Q1、Q2、Q3 的作答維持有效。Q2（Conditional GO）與 Q3（RE 掃描範圍）不受本次修訂影響。Q1 的確認範圍**只涵蓋其作答當下的 U-1～U-5**，不延伸到新增項。

## Q4. Revision 1 新增兩項未解事項，確認知悉並接受嗎？

> Q1 的人工確認只涵蓋 U-1～U-5，那是它作答當下的清單。以下兩項為本次新增，需另行確認。

| # | 未解項 | 指派落點 |
| --- | --- | --- |
| U-6 | **CAP-11 反向同步未經本 intent 的 feasibility 評估** —— feasibility 的技術可行性表、風險分析與 ADR-0006 四面向判定均不涵蓋 GitHub → repo 路徑。目前依據是 ADR-0012 已完成的推理（防迴圈三道防線、狀態欄位單向、反向一律開 PR），那是他人已做過的推理，不是本 intent 自己的評估 | application-design 補齊，含 IAM 面重新判定——回寫 repo 的權限面比目前大 |
| U-7 | **PU-10 的驗證落點未定** —— PU-8 的驗證層（dry-run ＋ 真實測試項目端到端）為正向路徑設計；反向路徑的正確性判準（「該不該把這個看板變更寫回 record」）與正向不同型 | application-design |

A. 兩項都確認並接受 — 帶著它們進入 INCEPTION，依上表落點處理
B. 接受 U-7，但 U-6 要先補 feasibility — 回跳 feasibility 以 Modify 模式補評估反向同步後再往下
C. 都不接受 — 應先解決才進 INCEPTION（請說明）
X. Other (please specify)

[Answer]: A. 兩項都確認並接受 — 帶著它們進入 INCEPTION，依上表落點處理