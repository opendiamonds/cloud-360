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

## Consolidated Summary Confirmation

- Looks correct
- Request changes

[Answer]: Looks correct
