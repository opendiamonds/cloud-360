# Initiative Brief — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: approval-handoff（Ideation 1.7）· 本文件彙整 IDEATION 三站的已核可產出。
     來源標籤：[intent:*]／[feas:*]／[scope:*] 指各站問題檔的已答題號或 artifact 內的編號；
     [Q<n>] 指本站問題檔。 -->

## 上游輸入

本簡報彙整下列已核可的 IDEATION 產出：

- **intent-statement** 與 **stakeholder-map**（`../intent-capture/`）
- **feasibility-assessment**、**constraint-register**、raid-log（`../feasibility/`）
- **scope-document** 與 **intent-backlog**（`../scope-definition/`），均為 **Revision 1** 版本
- **ADR-0013**（`../../inception/decisions/0013-aidlc-projects-sync-scoping.md`）與其修訂對象 **ADR-0012**

依 scope 設計不存在、故未納入：**competitive-analysis**（market-research 跳過）、**team-assessment**（team-formation 跳過）、**wireframes**（rough-mockups 跳過）。此三項缺席為設計決定而非缺漏。

## 意圖與問題陳述

讓 AI-DLC 的流程進展與 GitHub Projects 看板之間維持自動一致：需求清單的正本放在 opendiamonds 組織的 Project #16，AI-DLC 各 stage 的進展反映到對應項目的 Status。四個問題同時成立——狀態失真、重複記帳、需求來源分散、對外可視性不足；其中狀態失真已是既成事實而非預測（看板上有項目標記為 In review 但對應 issue 已關閉）。

## 受益者

| 受益者 | 痛點 |
| --- | --- |
| 唯一開發者（本人） | 每跑完一個 stage 還要記得回去手動改看板狀態 |
| 其他 repo 協作者 | 看板狀態不準，看不出別人在做什麼 |
| 不參與開發的觀看者 | 只看看板，看不到 AI-DLC 內部進度 |
| 未來的自己 | 事後無法回溯某功能走過哪些 stage |

決策模型為單一決策者；其他協作者為受影響方，告知即可。觀看者為正式服務對象，未被賦予決策權。

## 市場驗證

不適用。`market-research` 依 scope 設計跳過——這是單一團隊在單一組織看板上的內部開發流程整合，不存在可研究的市場。

## 可行性與風險摘要

**判定：Conditional GO** [Q2]。技術路徑存在且有官方支援（框架對看板更新提供受管的安全輸出型別，可依欄位名稱設定單選欄位），但建立在五個前提上，其中三項尚未滿足；Revision 1 另引入兩項新的未解事項（U-6、U-7）。

進入 INCEPTION 時仍未解的七項。**U-1～U-5 已由 [Q1] 人工確認接受；U-6、U-7 為 Revision 1 新增，其確認見 [Q4]**：

| # | 未解項 | 指派落點 |
| --- | --- | --- |
| U-1 | 憑證權限未驗證：框架以 job 權限欄位鑄造憑證，該欄位無組織層看板的鍵。**整條路徑的單點失敗**，且同時承擔「App 是否真的安裝到組織」的驗證責任 | application-design 展開前實測 |
| U-2 | 看板自訂欄位的建立可行性未知：框架安全輸出清單有建立看板與建立檢視，無建立欄位 | application-design；不可行則退回人工建立 |
| U-3 | 首次建立追蹤項目時無既有對象可回讀，寫入前比對的防護在該時刻不成立 | application-design 補首建專屬檢查 |
| U-4 | 代理式工作流程的產出檔不受任何 CI 閘門驗證 | ci-pipeline |
| U-5 | 十一項全 Must 且宣告一次做完，與短生命週期分支實務在 deploy-on-merge 下相交 | delivery-planning |
| U-6 | **CAP-11 反向同步未經本 intent 的 feasibility 評估** —— 該站的技術可行性表、風險分析與 ADR-0006 四面向判定均不涵蓋 GitHub → repo 的路徑；目前的依據是 ADR-0012 已完成的推理，而非本 intent 自己的評估 | application-design 補齊，含 IAM 面重新判定 |
| U-7 | **PU-10 的驗證落點未定** —— PU-8 的驗證層為正向路徑設計，反向路徑的正確性判準與正向不同型 | application-design |

**ADR-0006 security baseline 四面向**已於 feasibility 逐項判定：IAM 適用（新增本 repo 第一個 GitHub API 身分）、Encryption 部分適用、Network exposure 不適用（不新增對外服務或端點）、Audit logging 適用。

## 範圍邊界

**In Scope**：十一項能力 CAP-1～CAP-11，全部列為 Must——綁定建立、推送觸發同步、PR 觸發同步（優先）、排程對帳、失敗通報、寫入前回讀、細粒度進展外置、README 指路文字、憑證可行性實測、驗證層，以及 **CAP-11 反向同步**（Revision 1 新增）。

**Won't Have**：跨 repo 支援、自動關閉 issue、既有 71 個項目的一次性對正。（原列入的「反向同步」已由 ADR-0013 移出排除清單，改為 CAP-11。）

**未承諾**：無。

交付意向為一次做完不分批，但此為**範圍層宣告，不決定 Bolt 切分**；批次屬 delivery-planning。排序偏好 risk-first，其中憑證實測為 Must 但不構成交付批次。

## 概念視覺

不適用。`rough-mockups` 依 scope 設計跳過——本 intent 沒有自建的使用者介面，唯一的視覺呈現是 GitHub 看板本身，而看板的版面不由本專案設計。

## 團隊計畫

不適用。`team-formation` 依 scope 設計跳過——單一決策者、單一團隊，`project.md` 已將此記載為既定事實。

## 上線前置依賴

| # | 前置 | 狀態 |
| --- | --- | --- |
| P-1 | 應用程式已安裝至組織並勾選本 repo | **未驗證** — 查詢需 `admin:org` scope；使用者選擇由 U-1 的實測一併證明（呼叫失敗即代表未安裝或無權限） |
| P-2 | 憑證存入 repo | ✅ **已完成** — 本站實測確認 secret 存在（2026-08-23T06:11:48Z）、變數僅存識別碼，且私鑰已重新產生 |
| P-3 | 憑證權限實測結果 | 未完成，等同 U-1 |
| P-4 | 看板自訂欄位存在 | 未完成，等同 U-2 |
| P-5 | 反向同步的權限與 PR 化路徑 | 未完成 —— Revision 1 新增，等同 U-6 |

P-2 的處理過程中修復了一項憑證缺陷：私鑰原被存為 Actions 變數（明文、UI 可回讀、workflow log 不遮罩）而非 secret，而本 repo 為 PUBLIC 且有 5 名協作者。實測確認未對匿名者外洩（未認證讀取回 HTTP 401），使用者已重新產生私鑰並改存 secret、刪除變數——風險結案而非僅搬移位置。

## Go/No-Go 建議

**建議 Conditional GO，進入 INCEPTION** [Q2]。此建議在 Revision 1 後維持不變——新增的 CAP-11 同樣不需要憑證即可在 INCEPTION 完成設計。

理由：INCEPTION 的全部工作是設計與規劃（reverse-engineering、requirements-analysis、user-stories、application-design、units-generation、delivery-planning），**沒有任何一站需要憑證即可進行**。未完成的四項前置依賴（P-1、P-3、P-4、P-5）阻擋的是 CONSTRUCTION 的實際寫入，不是設計。在 phase 邊界停等會讓不需要憑證的工作停擺。

保留 conditional 字樣的理由：P-1／P-3／P-4／P-5 確實仍未完成，宣告 Full GO 會與事實不符。

**下一站範圍已定** [Q3]：reverse-engineering 限定掃描兩塊——AI-DLC 的狀態表徵（state 檔欄位、逐 stage 表、intents.json 的 status）與既有 12 組代理式工作流程的形狀與慣例。這兩塊正是本機制要讀的與要仿的。

## Assumptions & Open Questions

- U-1～U-5 已由 [Q1] 人工確認接受，U-6～U-7 由 [Q4] 確認；接受不等於解決，各自的落點見上表。 [assumption]
- P-1 的驗證被併入 U-1 的實測。若該實測因其他原因失敗（例如欄位識別碼錯誤），將無法區分「未安裝」與「有權限但呼叫寫錯」，屆時需要拆開驗證。 [assumption]
- 承接自上游且仍成立的假設：框架的看板更新行為未經本 repo 實測、框架承載應用程式識別碼的變數名稱與其文件描述不一致、看板狀態欄位定義在實作期間保持穩定、細粒度進展的落點細節與排程對帳頻率尚未決定。 [assumption]

## Revision 1（2026-08-23）

**觸發**：reverse-engineering 開始前發現 ADR-0012（Accepted 2026-08-16）涵蓋本 intent 主題卻未被任何 IDEATION 站點引用。經使用者裁決開立 ADR-0013 修訂之，並回跳 scope-definition 以 Modify 模式擴充範圍。本交接包隨之重製。

**改動**：

- 上游輸入新增 ADR-0013 與 ADR-0012；scope-definition 的兩份 artifact 標明為 Revision 1 版本。
- 未解項由五項增為七項：新增 U-6（CAP-11 未經本 intent 的 feasibility 評估）與 U-7（PU-10 的驗證落點未定），兩者皆指派 application-design。
- 範圍邊界：In Scope 由十項增為十一項（新增 CAP-11 反向同步）；Won't Have 由四項減為三項（反向同步移出）。
- 前置依賴新增 P-5（反向同步的權限與 PR 化路徑）。
- 相關衍生數字（前提數、未完成前置依賴數）已同步。

**未改動**：Go/No-Go 判定維持 Conditional GO——CAP-11 同樣不需要憑證即可在 INCEPTION 完成設計；[Q3] 的 reverse-engineering 掃描範圍不受影響。

**確認狀態的區分**：[Q1] 的人工確認只涵蓋 U-1～U-5，那是它作答當下存在的清單。U-6 與 U-7 為本次新增，需另行確認（[Q4]），不得以 [Q1] 的既有作答代替。
