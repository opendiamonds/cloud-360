# Approval & Handoff Questions — 統一入口大腦

<!-- Stage: approval-handoff（Ideation 1.7）· Record: 260920-orchestration-brain
     本站為彙整站：把 Ideation 四站的產出壓成一份 initiative brief 與決議紀錄，
     並執行 Ideation → Inception 的階段邊界驗證。
     依 `project.md` 的 `approval-handoff:c1`，本站**只問未被上游定案的事項**；
     已由各站 gate 核可、scope 跳過或上游問題檔確認的內容不重問，省略清單見下。 -->

## 消費的上游輸入

| 產出 | 站 | 狀態 |
|---|---|---|
| `intent-statement.md`、`stakeholder-map.md` | intent-capture（1.1） | 已核可（含修訂 1） |
| `feasibility-assessment.md`、`constraint-register.md`、`raid-log.md` | feasibility（1.3） | 已核可（含修訂 1） |
| `scope-document.md`、`intent-backlog.md` | scope-definition（1.4） | 已核可（含修訂 1） |
| `wireframes.md`、`user-flow.md` | rough-mockups（1.6） | 已核可（2026-09-24，R-06 以已接受風險放行） |

`market-research`（1.2）與 `team-formation`（1.5）在本 scope 為 SKIP，故其
對應產出不存在，本站不以缺席視為缺口。

## 不重問的事項（已由上游定案，附可引用的依據）

依 `scope-definition:260822-c5`，宣稱「已由上游定案」必須能引用具體選項或
原文；引用不出來就代表它未被定案，應補問而非推論。逐項如下：

| 本站的範例題 | 不問的依據（逐字可引用） |
|---|---|
| 所有關係人是否同意 intent 與 scope？ | `[Q8]`＝單一決策者、無其他關係人、不需對外回報節奏；且 1.1／1.3／1.4／1.6 四站的核可關卡皆已由同一位決策者通過 |
| 市場研究是否支持這筆投資？ | `market-research`（1.2）在本 scope 為 SKIP，無產出可據 |
| mob 是否已編成並排期？ | `team-formation`（1.5）為 SKIP；`[Q8]` 已確認單一決策者、無跨團隊協調 |
| 線框是否反映共同願景？ | rough-mockups（1.6）核可關卡已於 2026-09-24 通過（Approve），R-06 以已接受風險帶進 refined-mockups |
| 是否有預算／資源承諾？ | `[S7]`＝A「沒有硬性時程」；`[F8]`＝C 有成本上限但 `[F13]`＝A 該上限改由 OpenRouter 後台承載、`[F11]`＝B 無硬數字、原則為「盡量省」 |
| 遷移風險要不要加做第三個試探？ | `[F10]`＝A「遷移風險交給設計階段處理，不做試探」——已明確否決加做試探 |
| Must 佔比 90% 要不要重新分級？ | `[S8]`→`[S9]`＝G,J 已降級一次、`[S11]`＝A 修訂 1 又升回一項；`scope-document.md` 逐字記「兩次皆為決策者在知悉佔比事實後的定案，本文件如實記載，不再質疑」 |
| 三個成功指標的門檻值？ | `[F7]`＝B「留到 requirements-analysis」 |
| 交付排序？ | `[S10]`＝A「風險優先 ＋ 不可覆寫的技術依賴序」 |

## 本站新問的事項（5 題）

共通背景：上游留下四處「指派目標不明確或不存在」的缺口。依
`units-generation:260822-ug-L2`，指派若指向一個可能被 skip 或根本不存在的
站，會無聲落空——本站把它們逐一釘死，是這一站的工作，不是重開上游。

**查證事實（非來源，供題幹引用）**：本工作流程編譯後的 34 站中**不存在
`application-design`**。Inception 的設計站為 `domain-design`（2.6）、
`units-generation`（2.7）、`contract-design`（2.8）、`delivery-planning`（2.9）；
Construction 的設計站為 `functional-design`（3.1）、`nfr-requirements`（3.2）、
`nfr-design`（3.3）、`infrastructure-design`（3.4）。

---

## H1. 兩個技術試探（P-1、P-2）要在哪裡執行？

`[F6]`＝A,B 定案「要做這兩個試探」，`intent-backlog.md` 把它們列為排在所有
proto-Unit 之前的先行項，但**沒有任何一站被指名執行它們**。P-2（記憶層資料
模型）要回答的「三種記憶各自的形狀與查詢方式」正是 `domain-design`（2.6）
要設計的東西；P-1（收窄後：多意圖分支結構、session 如何注入圖、自建 runtime
與既有 `services/langgraph_runtime.py` 的一致性）同樣餵給設計。

- A. **併入 `domain-design`（2.6）**：該站一邊試跑一邊定記憶資料模型與編排
  模型，不另立時段。試探結論與設計在同一站產出，不會脫節。（建議）
- B. **現在做，進 Inception 之前**：先拿到兩個結論，讓整個 Inception 建立在
  已驗證的前提上。代價是現在要多花半天到兩天（`A-1` 假設，未驗證）。
- C. **`delivery-planning`（2.9）排成 Construction 的第 0 個 Bolt**：代價是
  `domain-design` 會在沒有試探結論的情況下先定資料模型。
- D. **不特別指派**，讓 `reverse-engineering`（2.1）掃完 repo 後再判斷還需不
  需要試探。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-23T23:13:53Z | Mode: guided -->

## H2. 兩項「定案階段＝待指定」的上線前置依賴要交給哪一站？

`scope-document.md` 的「上線前置依賴」表有兩列的定案階段寫著**待指定**：
(1) 主動通知推播的**觸發情境與接收對象**（綁能力 7，唯一的 Should）；
(2) episodic memory 的**保存期限值**（綁能力 4，`[F5]`＝C 已定「保存期限 ＋
使用者可自行刪除」，只差期限數字）。兩者都是上線前必須有值的參數。

- A. **兩項都在 `requirements-analysis`（2.3）定案**：該站本來就在寫可驗收
  的需求，三個成功指標的門檻值（`[F7]`＝B）也在那裡，集中在同一站處理。（建議）
- B. **拆開**：推播的觸發情境與接收對象 → `requirements-analysis`（2.3）；
  保存期限值 → `nfr-requirements`（3.2），因為保存期限偏資料治理／NFR。
- C. **兩項都在 `nfr-requirements`（3.2）**。
- D. **推播那項留到 `delivery-planning`（2.9）**（它是唯一的 Should，可能不
  進第一版，先確定要不要做再談參數）；保存期限值在 `requirements-analysis`。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-23T23:13:53Z | Mode: guided -->

## H3. R-1（既有架構圖遷入新階層）的設計要交給哪一站？

`[F10]`＝A 已定案「交給設計階段處理，要求產出遷移步驟與回復方式」，指派對象
寫的是「`application-design` 或 `functional-design`」——但**本工作流程沒有
`application-design` 這一站**（見上方查證事實）。R-1 是本 intent 影響最大且
無試探涵蓋的風險（`raid-log.md` 可能性中／影響高），指派必須落在真的會執行
的站上。

- A. **`domain-design`（2.6）**：新階層的資料模型就在該站定，遷移的歸屬規則
  與回復方式一併在那裡產出，時間上最早、與資料模型同一份產出。（建議）
- B. **`functional-design`（3.1）**：feasibility 原文點名的另一半；在序 1 那個
  工作單元內產出。代價是要等到 Construction。
- C. **`infrastructure-design`（3.4）**：`C-T6`（`schema_rbac.sql` 只在空
  volume 執行）使手動遷移程序偏部署作業，放在基礎設施設計站。
- D. **拆成兩半**：資料歸屬規則與回復方式 → `domain-design`（2.6）；實際遷移
  腳本與執行程序 → `infrastructure-design`（3.4）。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-23T23:13:53Z | Mode: guided -->

## H4. R-8（兩份 runtime 漂移）的一致性驗證要交給哪一站？

`[Q13]`＝自建編排層，系統內將並存**兩份 OpenRouter 客戶端與兩套串流事件
語意**；`team.md` `## Code Style` 的單一真實來源規則要求「新增副本的同一個
PR 必須一併新增鎖住兩者一致的測試」。`raid-log.md` R-8 與 `D-6` 目前只寫
「設計階段」，而設計站有四個，籠統指派同樣會落空。

- A. **`contract-design`（2.8）**：把兩套串流事件語意收斂成一份共用契約，從
  結構上避免漂移；測試再鎖住它。只有這個選項是「預防」而非「偵測」。（建議）
- B. **`nfr-design`（3.3）**：一致性屬品質屬性的設計，該站處理跨元件的非功能
  設計。
- C. **`tcms-test-cases`（3.8）**：以 blocking 測案承載，保證不會被漏掉；
  但它只偵測漂移，不阻止兩份實作一開始就分歧。
- D. **`functional-design`（3.1）**：在大腦那個工作單元內處理。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-23T23:14:54Z | Mode: guided -->

## H5. Go / No-Go：殘留風險的接受範圍

本站對 Ideation 的整體判定是 **GO**（承自 feasibility 的 GO，且修訂 1 後
信心上調）。但有三項風險進 Inception 時**沒有任何早期訊號機制**，需要你明確
表態是接受、還是要求先收斂：

- **R-1**（既有架構圖遷移）：`[F10]`＝A 已否決試探，只有設計階段的指派（本站
  H3 釘落點）。在實作前沒有執行期證據。
- **A-4**（「盡量省」是否足以守住 OpenRouter 後台的成本上限）：`raid-log.md`
  逐字記為**唯一無法驗證的假設**——本專案不掌握該上限數值。
- **R-8**（兩份 runtime 漂移）：可能性高／影響中；`[Q13]` 作答時已逐項揭露，
  屬知情選擇，非疏漏。

- A. **GO，三項全部以已知殘留風險帶進 Inception**：各自已有指派（H3／H4）或
  已知情（R-8），不額外設前置條件。（建議）
- B. **GO，但加一個前置**：R-8 的一致性驗證落點必須在 `domain-design`（2.6）
  開始前就定下來，否則兩份實作會在設計階段就分歧。
- C. **GO，但加一個前置**：R-1 的遷移必須在 Inception 內先產出可重跑的遷移
  腳本與回復方式，才繼續往 Construction 走。
- D. **不 GO**：有項目必須先解決才進 Inception（請在 X 指名是哪一項）。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-23T23:14:54Z | Mode: guided -->

---

## 作答後的查證與後果（本站於答案收齊後補記，非新問題）

依 `project.md` 的 `units-generation:260822-ug-L2`：指派若落在 `CONDITIONAL`
的站上，必須額外註明「該站可能被 skip」的風險並指出誰要確認。收齊 H1–H5 後
本站逐一查編譯後的 stage graph，結果如下：

| 指派 | 目標站 | execution | 後果 |
|---|---|---|---|
| H1 兩個技術試探 | `domain-design`（2.6） | **CONDITIONAL** | 條件為「需要新元件或新邏輯建構塊時執行」。本 intent 要建新階層、記憶層與編排層，條件成立的可能性極高，但仍非保證 |
| H3 R-1 遷移設計 | `domain-design`（2.6） | **CONDITIONAL** | 同上 |
| H4 R-8 一致性驗證 | `contract-design`（2.8） | **CONDITIONAL** | 條件為「系統有正式契約要釘死——跨單元邊界或對外 API」。本 intent 有多個單元與新 WebSocket 介面，條件成立的可能性高，但仍非保證 |
| H2 兩項前置依賴 | `requirements-analysis`（2.3） | **ALWAYS** | 無 skip 風險 |

**兩項必須被記入 initiative brief 的後果**：

1. **轉移規則（本站訂定，寫入 brief 與 decision log）**：若 `domain-design`
   在其執行時被判定為不適用而 skip，H1 與 H3 的義務**自動轉移**至
   `units-generation`（2.7，本 scope 內、且 domain-design 的下一站）；若
   `contract-design` 被 skip，H4 的義務自動轉移至 `tcms-test-cases`（3.8，
   `execution: ALWAYS`，本 repo 唯一不會被 skip 的驗證站）。確認者是屆時執行
   該站的 conductor。沒有這條規則，三項指派會在 skip 當下無聲落空。

2. **H4 的取捨如實記載**：選項 C（`tcms-test-cases`）是四個選項中**唯一
   `execution: ALWAYS`、不可能被 skip** 的落點，但它只偵測漂移、不預防；
   選項 A（`contract-design`）是唯一能從結構上預防漂移的落點，代價是它為
   CONDITIONAL。決策者選 A，即以「可預防」換「可能被 skip」，並以上述轉移
   規則補回後者。

3. **`domain-design`（2.6）的負載集中**：H1＋H3 定案後，該站將同時承載五件
   事——(a) 專案→系統→架構圖 階層的資料模型、(b) 記憶層資料模型、(c) 編排層
   模型、(d) P-1 與 P-2 兩個技術試探的實際執行、(e) R-1 既有資料遷移的歸屬
   規則與回復方式。這是 H1=A 與 H3=A 的直接後果，不是缺陷；如實記入 brief，
   使下游在該站規劃工作量時看得到。

---

## 修訂 2 —— 上游修訂後新增的兩題（H6、H7）

<!-- 修訂 2 的觸發：2026-09-29 的會議結論使 scope-definition 以 Modify 模式
     新增能力 11（專案系統資訊需求頁），rough-mockups 隨之重做（21 個畫面），
     RAID 於 2026-09-30 新增 D-8／D-9／R-10。本站於 2026-09-23 完成的三份
     產出對「能力 11」零命中，故需修訂。
     依 `approval-handoff:260823-rev1-c1`：既有的 H1–H5 作答只涵蓋它作答當下
     存在的清單，修訂新增的項目必須另行取得確認，不得沿用舊確認寫成「已接受」。
     H1–H5 與其 `[Answer]` 一律不動。 -->

**修訂 2 仍不重問的事項**（延續 `approval-handoff:c1`，附可引用依據）：

| 事項 | 不問的依據 |
|---|---|
| 能力 11 要不要做 | `[S12]`＝A 已定案為 Must；`scope-document.md` 修訂 2 逐字記載其四項責任 |
| 能力 11 與能力 10 之間要不要列依賴 | scope-definition 修訂 2 逐字寫「本站不主張的一項：不列依賴」，理由已記入 `project.md` 的 Forbidden |
| 能力 11 的三籤是否為同一個驗證面 | rough-mockups 的 Assumptions 已明寫「導覽上的分組、非同一驗證面」並指名 `units-generation:c6` 要求逐籤評估 |
| D-8／D-9 由誰修 | 使用者於 2026-09-30 明確指出由 tina 承接，非 doreen、非本 intent |

---

## H6. 成員管理的範圍決定 —— 指派已落空，要在哪裡收

**背景（本站查證，非推論）**：rough-mockups 修訂 2 發現 §16–§18 畫了 `[成員]`
按鈕卻無對應範圍，處置是**移除按鈕**並把範圍決定**回送 `scope-definition`**
（併入能力 11／另立能力 12／明確排除，三選一）。

**但那個指派不會自己執行。** 本站實查 `.claude/tools/data/stage-graph.json`：
`scope-definition` 的 `execution` 為 `ALWAYS`，然而 `aidlc-state.md` 顯示
`Last Completed Stage: rough-mockups`、`Completed: 7`——它**在游標之前、已完成**。
`ALWAYS` 只保證它在工作流程中會被執行一次，不保證會被再執行一次。也就是說，
這是 `units-generation:260822-ug-L2` 警告的那種**死指派**：交接表上看起來完整，
實際上沒有任何一站會接。

**會議結論描述的範圍有多大**（逐字）：專案創建者為 `project_owner` 即
`project_admin`、可指定其他加入專案的成員角色給予權限、`project_admin` 可多人、
`project_owner` 帳號被移除時自動改選其他人。這是一整層授權模型，不是一個按鈕。

**約束**：`phases/ideation.md` 的 Scope Discipline 逐字禁止「carry forward scope
decisions that have not been explicitly approved」；`scope-definition:rev1-c4`
禁止下游 stage 擅自擴大已核可範圍——所以本站**不能**自行把它併進能力 11。

- **A**：**明確排除本 intent**，寫進 `scope-document.md` 的 Won't Have（本次），
  並記明它是會議結論的一部分、留給後續 intent。本 intent 的範圍就此收斂。
  代價：`[S14]=A`（專案成員角色不進 `CANONICAL_ROLES`）這句話會暫時失去對象——
  它預設成員角色存在，而本 intent 不做它；需在 scope 文件就地註記此事。
- **B**：**回跳 `scope-definition` 以 Modify 模式定為能力 12**，正式擴充範圍並
  重走該站核可關卡。代價：本 intent 從 11 項變 12 項，且新增的是一整層授權模型
  （per-project 角色、多 admin、自動繼任），會再一次觸發 `schema_rbac.sql` ＋
  `DEPLOY.md` 的 blocking 同步；`rough-mockups` 與本站都要再修訂一輪。
- **C**：**帶進 Inception 當明確的開放範圍項**，由 `requirements-analysis`（2.3，
  `ALWAYS`）承接決定。代價：**這一條牴觸 `phases/ideation.md` 的 Scope Discipline**
  ——未經核可的範圍決定不得帶過階段邊界。本站如實列出它是為了不隱藏這個選項，
  但它需要你明知該牴觸而仍選擇它。

[Answer]: B  <!-- 2026-09-30T15:39:25Z | Mode: guided | 修訂 2 新增 -->

---

<!-- H6 的成本揭露確認（2026-09-30T15:43:22Z）：H6=B 作答之後，本站以
     `aidlc-jump.ts resolve --stage scope-definition` 實測回跳成本並回報使用者
     ——`affected_stages` 共 23 站，但其中只有 `scope-definition` 與
     `rough-mockups` 為 `[x]` 已完成而真的失去核可，`approval-handoff` 為 `[-]`
     進行中，其餘 20 站本就是 `[ ]` PENDING、重設對它們是 no-op；需重過的核可
     閘門為 3 個。另揭露一項原選項說明未涵蓋的新工作：rough-mockups 修訂 2
     刻意移除了 `[成員]` 按鈕（理由逐字為「不為一個沒有範圍的東西畫
     affordance」），成員管理成為能力 12 之後該站必須**新畫**成員清單／邀請／
     角色指定／自動繼任等畫面，不只是重新核可。使用者在看到這份實測成本後
     選擇「執行回跳（我已選 B）」，H6=B 維持不變。依
     `intent-capture:c6`（不揭露成本的確認不是知情確認）記錄此輪。 -->

## H7. Go / No-Go 重審 —— D-8／D-9 要不要成為進入下一階段的前置條件

**背景**：修訂 1 的判定是 **GO 且不附帶任何前置條件** [H5]。修訂 2 之後有兩項
新事實：

1. **範圍變大**：新增能力 11（新頁面 ＋ 新資料模型的管理面）。
2. **新增兩項外部相依**（RAID D-8／D-9，本站於 2026-09-30 合併 `ut` 時查出）：
   `#678` 從 `requirements.txt` 移除 `langchain-openai` 與 `claude-agent-sdk`，
   而程式仍在活路徑上 import 它們，乾淨 venv 實測皆為 `ModuleNotFoundError`。
   影響**能力 10 路由的 `/api/cost/v1` 建議流程**與 **Assessment 路由目標**。
   修復方為 tina，不在本 intent 範圍。

**逐項對照可行性面向**（依 `approval-handoff:rev1-c2`，不因範圍變大就自動下修；
依 `feasibility:3966ea4`，重審也可能上調）：

| 面向 | 能力 11 是否引入 | 判定 |
|---|---|---|
| 新服務 | 否——沿用既有 FastAPI／React | 不下修 |
| 新依賴 | 否——無新套件 | 不下修 |
| 新基礎設施 | 否——`projects`／`systems` 兩表已在能力 9 的範圍內 | 不下修 |
| 新技術層 | 否——CRUD 表單 ＋ 唯讀彙總，本 repo 有大量前例 | 不下修 |
| 可無障礙存取的籤元件 | **是**——本 repo 零前例（`AssessmentPage` 的兩籤為純 `useState`，無 `role="tablist"`／`aria-selected`／方向鍵），rough-mockups 已如實記載此揭露落差 | 小幅新工作，非可行性風險 |

- **A**：**維持 GO，不附帶進入 Inception 的前置條件**。D-8／D-9 列為**能力 10 與
  Assessment 路由的端到端驗收前置**，寫進交接表並指名 tina；它們不阻擋任何設計
  工作。依據：三處缺口皆與本分支零耦合（47 個改動檔中 0 個、10 個識別字 grep 全
  0 命中、設計刻意自建 runtime 而非重用 `langgraph_runtime`）。
- **B**：維持 GO，但把 D-8／D-9 升為**進入 Construction 的前置條件**——設計可以
  做，但不得開始寫能力 10 的程式直到 tina 修完。代價：能力 10 的施工被一個
  本 intent 無法控制的外部項擋住，而它其實可以先寫完再驗。
- **C**：改為 **CONDITIONAL GO**——tina 修完才進 Inception。代價：整個 intent 停在
  別人的修復上，而那兩處缺口不影響任何設計工作，這個代價與風險不成比例。

[Answer]: A  <!-- 2026-09-30T15:39:25Z | Mode: guided | 修訂 2 新增 -->

---

# 修訂 3（2026-10-01）—— 能力 12 落地後的收尾

<!-- 觸發：修訂 2 的 [H6]=B 使範圍決定回跳 scope-definition。該站修訂 3 以
     [S16]=A 新增能力 12（專案成員管理，Must），rough-mockups 修訂 3 補完其
     畫面並通過兩輪審查（皆 READY）。本站第三次執行的工作是把 initiative-brief
     與 decision-log 補到現況——兩者仍是 2026-09-29 的版本，不只早於 H6／H7，
     更早於能力 11 與能力 12，比現況落後兩個修訂。 -->

**修訂 3 不重問的事項**（附可引用依據，依 `scope-definition:260822-c5` 須能引用具體選項字母）：

| 不重問的事項 | 可引用依據 |
|---|---|
| 兩個技術試探的執行位置 | [H1]=A |
| 兩項上線前置依賴的承接站 | [H2]=A |
| R-1（架構圖遷入新階層）的設計落點 | [H3]=A |
| R-8（兩份 runtime 漂移）的驗證落點 | [H4]=A |
| 殘留風險的接受範圍（H5 當時的集合） | [H5]=A |
| 成員管理的範圍決定收在哪 | [H6]=B（已執行：回跳 scope-definition，產出能力 12） |
| D-8／D-9 是否為進入下一階段的前置 | [H7]=A（且兩者已於 2026-10-01 由 `ut` 解決，條件自然滿足） |
| 自動改選的挑選規則 | scope-definition 修訂 3 已指派 `requirements-analysis` |
| 兩層串聯的診斷畫面缺口 | rough-mockups 修訂 3 已指派 `requirements-analysis` |

**本輪 Go / No-Go 逐項重審（分析，非提問）**：依 `approval-handoff:rev1-c2`，範圍
擴充後不得自動下修信心，須逐項對照可行性面向。能力 12 不引入新服務、不新增對外
暴露面、不新增依賴、不引入新技術層——它是既有 FastAPI／React／PostgreSQL 之上
的一張新表與一組既有形狀的頁面，且 `[M3]=A` 經查證不需改 schema 約束。故 **GO
維持不變**。反方向同樣逐項檢查（依同一條規則的反面）：D-8／D-9 由 `ut` 解決，使
[H7]=A 所列的兩項外部驗收前置**由待辦轉為已滿足**，信心面為上調而非下調。

---

## H8. R-11（`LLM_PROVIDER=cli` 已失效且為靜默失敗）要怎麼處置？

<!-- 本題為新增風險，不在 [H5]=A 確認當下的集合內，依
     `approval-handoff:260823-rev1-c1` 必須另行取得確認，不得沿用舊確認。
     發現經過：解 `LOCAL-DEV.md` 的 `ut` 合併衝突時，看到該檔第 219 行
     （cli 模式用已登入的 claude CLI、不需金鑰）與 `ut` 新寫的 H1（不再需要
     claude CLI）自相矛盾。實測：設 `LLM_PROVIDER=cli` 並給定兩個變數後呼叫
     `configure_provider_env()`，`api_key` 為空字串、`base_url` 為 None、
     `llm_auth_ready()` 仍回 True。全樹已無子行程呼叫。 -->

- **A**：**接受為殘留風險，指派 `requirements-analysis`（已查證為 `ALWAYS`，不需
  轉移目標）判定是否要求 `ut` 側修**。本 intent 不改 `llm_provider.py`——它是
  A1／A3 共用、屬 `ut` 側維護範圍，且修法二擇一（移除 cli 模式／讓它不再刪變數）
  屬該模組擁有者的決定。本 intent 的處置僅限 `LOCAL-DEV.md` 已標明該模式目前是壞
  的並指向 RAID R-11。代價：cli 模式在被修好之前都不能用，而預設是 openrouter，
  須手動改設才會踩到。
- **B**：比照 [H7] 對 D-8／D-9 的處置，升為**進入下一階段的前置條件**。代價：R-11
  的可能性為低（須手動改設）、且與本 intent 的任何設計工作零關係，用前置條件擋
  整個階段與風險不成比例。
- **C**：不列入本 intent 的 RAID，移除 R-11，改以 issue 交給 `ut` 側。代價：RAID
  是本 intent 唯一會被下游讀到的風險清單，移出等於讓這個靜默失敗在本 intent 的
  紀錄裡消失；而它是在本 intent 的合併動作中查出來的。
- **D**：本 intent 直接修 `llm_provider.py`。代價：改別人正在改的模組，且修法涉及
  「cli 模式該不該存在」這個不屬本 intent 的設計決定。

[Answer]: D  <!-- 2026-10-01T14:48:45Z | Mode: guided | 修訂 3 新增 -->

**D 的落實方式（三種修法逐一評估後選定）**：

| 修法 | 判定 |
|---|---|
| ①**移除 `cli` 模式** | **選定**。全樹已無子行程呼叫（`create_subprocess_exec`／`Popen` 皆 0 命中），cli 模式已無可認證的對象——它不是壞了，是它要服務的東西不存在了。移除是唯一讓程式與事實一致的修法 |
| ②讓 cli 模式不再刪那兩個變數 | 不選。這樣它會與 `openrouter` 模式行為完全相同，變成一個無作用的別名——把一個會靜默失敗的選項換成一個會誤導人的選項 |
| ③只讓 `llm_auth_ready()` 在 cli 模式回 `False` | 不選。那只是把靜默失敗改成大聲失敗，使用者仍然得到一個永遠不能用的設定值 |

**相容性處置**：`LLM_PROVIDER=cli` 已是公開設定值，不能靜默消失。處置為**保留該值的辨識但拒絕啟動**，並在訊息中指出 A3 已遷移至 LangGraph／OpenRouter、該模式已無子行程可認證——大聲失敗優於無聲降級（與 `construction.md` 的「Errors must be surfaced」一致）。`LOCAL-DEV.md` 第 219 行與 RAID R-11 同步更新為已解決。


<!-- 本題我推薦 A，使用者選 D（本 intent 直接修 llm_provider.py）。依
     `project.md` 的規則，選項會製造新的正確性問題時須請其重選——本輪判定
     **不構成**：D 的代價是協調成本（改 tina 正在改的模組，下次她碰同一支
     時可能衝突），不是正確性問題，且該代價已在選項原文逐字揭露。使用者對
     自己 repo 的協調有權決定，故照辦。
     修法選擇見下方「D 的落實方式」。 -->

---

## H9. rough-mockups 的兩個殘留 Minor（R-05／R-06）要在哪裡收？

<!-- R-05：`user-flow.md` 的 Flow 6（建立專案）未提建立者的預設角色，使能力 12
     第 (1) 項在流程檔無落點（wireframes 已補引用）。R-06：§23 的文字 fallback
     仍寫「這一格的存在理由是 M3」，比該節新標題的雙重引用窄。
     注意：rough-mockups 已核可，其審查收據已消耗。 -->

- **A**：**在本站的 `initiative-brief.md` 明記這兩項對齊修正，上游檔不回改**。依
  `refined-mockups:c3` 的既有慣例——下游修正上游已核可 artifact 的內部瑕疵時，在
  本站 artifact 明記「這是對齊修正、非本站新定案」並說明原瑕疵，上游檔案本身仍不
  回改（否則純比對兩份文件會誤判為迴歸）。代價：讀 `user-flow.md` 的人看不到這則
  修正，必須讀到交接文件才知道。
- **B**：指派 `requirements-analysis`（`ALWAYS`）在寫 FR 時吸收這兩項。代價：它們
  是畫面層的敘述瑕疵而非需求缺口，交給需求站會把一件小事放大成一條 FR。
- **C**：回改 `user-flow.md` 與 `wireframes.md`。代價：直接違反「上游檔案本身仍不
  回改」，且該站已核可、收據已消耗，回改會讓已核可版本與現況分歧。
- **D**：保留為已知殘留，兩份文件都不記。代價：R-05／R-06 在審查紀錄裡存在但在交接
  文件裡消失，下游不會知道。

[Answer]: A  <!-- 2026-10-01T14:48:45Z | Mode: guided | 修訂 3 新增 -->

---

## H10. 新角色命名與 RBAC story id 的落點 —— 候選承接站是 CONDITIONAL

<!-- 能力 11 與能力 12 都需要新的 RBAC story id（K1／K2 已被入口頁與階層用掉），
     且能力 12 的非管理者那一層叫什麼尚未定案（[S14]=A 只定了 project_admin 不進
     CANONICAL_ROLES）。兩者必須一起定才不會再撞名。
     已查證 stage-graph.json：domain-design 為 CONDITIONAL（可能被 skip），
     requirements-analysis 與 units-generation 為 ALWAYS。
     依 `approval-handoff` 的既有規則，指派 CONDITIONAL 站必須附轉移目標，
     否則指派會無聲落空（本 intent 的 [H6] 就是一次死指派）。 -->

- **A**：**指派 `domain-design`，並附轉移目標 `requirements-analysis`（`ALWAYS`）**；
  若 `domain-design` 被判定 skip，由當時的 conductor 轉交。理由：角色模型與
  story id 本質是 domain 決定；但本 intent 已經吃過一次死指派，所以必須附轉移目標。
- **B**：直接指派 `requirements-analysis`（`ALWAYS`），不經 `domain-design`。
  代價：角色命名與權限矩陣的設計在需求站做會偏早，可能在 domain-design 又被改一次。
- **C**：指派 `units-generation`（`ALWAYS`）。代價：那站的工作是切分單元，不是定
  命名與 story id；塞進去等於把一個設計決定藏在切分裡。

[Answer]: A  <!-- 2026-10-01T14:48:45Z | Mode: guided | 修訂 3 新增 -->

---

## H11. 能力 11 的 MCP 封裝完全沒有可行性評估，要怎麼處置？（階段邊界檢查加開）

<!-- 本題由本站 Step 4 的階段邊界檢查重驗觸發，非上游遺留。
     實測：以八個關鍵詞（需求頁、需求欄位、成員管理、project_admin、
     project_owner、MCP、能力 11、能力 12）對 feasibility 的三份產出合併搜尋，
     全部 0 命中。原因是結構性的——兩項能力都在 feasibility 跑完之後才新增
     （能力 11 於 scope 修訂 2、能力 12 於修訂 3），而 feasibility 從未重跑；
     引擎自己也標 `Directly stale: feasibility`。
     兩項的風險型態不同：能力 12 的缺口是形式缺口（其可行性已由本站 Go/No-Go
     的逐項表以查證過的事實覆蓋）；能力 11 的 [S13]=A 定案「agent 經大腦端
     MCP 封裝取用欄位，底下走 HTTP 帶使用者 token」是 repo 內無前例的全新整合
     機制，缺口是實質缺口。 -->

- **A**（AI 推薦）：接受為殘留風險，列為交接第 19 列，指派 `domain-design`
  （CONDITIONAL）並附轉移目標 `requirements-analysis`（`ALWAYS`），且在該站先做
  技術試探（比照 P-1／P-2）。代價：若該機制實際不可行，會到 `domain-design` 才
  發現，而那時能力 11 的兩頁線框與 `[R10]`／`[R12]` 已經核可。
- **B**：**重跑 `feasibility`**（引擎已建議 `/aidlc --stage feasibility`）。讓能力
  11／12 與新增的 R-11 都正式被評估一次。代價：多一輪完整的 stage（提問、產出、
  審查、關卡），而其中大部分內容（能力 1–10）本輪已驗過且未變；且往回跳會使
  下游已核可的站失去核可狀態。
- **C**：只對 MCP 封裝做一次小範圍技術試探，現在做。代價：ideation 階段本不該做
  實作性試探，且會拖延進入 Inception。
- **D**：不記為缺口，視為已被能力 9 的評估隱含。代價：隱含不等於背書——這正是
  檢查 2 對能力 3／5／6 已經記過的語句；MCP 封裝是 repo 內無前例的新整合機制，
  與能力 9 的資料模型不是同一類風險。

[Answer]: B  <!-- 2026-10-01T15:02:47Z | Mode: guided | 修訂 3、階段邊界檢查加開 -->

<!-- AI 推薦 A，使用者選 B。依 `project.md` 的規則，選項會製造新正確性問題時須
     請其重選——本輪判定**不構成**：B 是把一個實質缺口補起來的正確做法，代價純
     為流程成本（多一輪 stage ＋ 下游重新核可），不是正確性問題。且使用者的選擇
     與引擎自己的 stale 判定一致。
     後果：本站**不核可**，改為往回跳至 feasibility。影響範圍於執行前以
     `jump resolve` 查明並向使用者揭露。 -->

---

## Consolidated Summary Confirmation

- Looks correct
- Request changes

[Answer]: Looks correct
