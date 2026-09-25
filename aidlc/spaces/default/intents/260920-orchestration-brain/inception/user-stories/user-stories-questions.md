# User Stories — 故事計畫與問題

<!-- Stage: user-stories（Inception 2.4，mode: mob）· Record: 260920-orchestration-brain
     本檔是 PART 1 的故事計畫，含嵌入式問題。
     來源標籤慣例沿用 requirements.md 的定義；本站的作答以 [US:U<n>] 引用，
     以避開 rough-mockups 的 [R<n>] 與 requirements-analysis 的 [RA:R<n>]。 -->

## 來源標籤（本站新增一種，避開既有兩處撞號）

| 標籤 | 指向 |
|---|---|
| `[US:U<n>]` | **本站**的作答（U1–U5） |
| `[RA:R<n>]` | requirements-analysis 的作答 |
| `[R<n>]` | rough-mockups 的作答 |
| 其餘 | 沿用 `requirements.md` 的慣例表 |

前兩站已因 `R1`–`R8` 撞號各自加了前綴。本站改用 `U` 而非再開一個 `R`，
理由見 requirements-analysis 的日記：**題號前綴應由 stage 決定、不要用單一字母**。

## 故事計畫

### Persona 發展取向

`stakeholder-map.md` 已確認 4 類關係人，本站**不重新發明 persona**，只把它們
補成 `personas.md` 所需的完整形狀（角色、目標、痛點、技術熟練度、使用頻率）。
`product-guide.md` 要求每則故事都引用一個已定義的 persona——若某則故事對不上
任何 persona，不是故事錯就是 persona 少了一個。

| Persona | 第一版定位 | 來源 |
|---|---|---|
| 架構設計者 | 直接服務 | [Q2] |
| 評估／稽核者 | 直接服務 | [Q2] |
| 成本／FinOps 關注者 | 直接服務 | [Q2][Q12][Q14] |
| 管理者／平台維運者 | **間接**服務 | [Q2][Q10] |

### 故事格式

標準格式 `As a [persona], I want [goal], so that [benefit]`，逐則檢查 INVEST。
故事 id 為 `US{group}.{seq}`、驗收標準 id 為 `AC{group}.{seq}.{n}`，皆為永久
追溯鍵。AC 採 Given/When/Then。

**AC 的硬性要求（沿用 `project.md` 的既有教訓）**：AC 描述**系統行為**，
必須能真的失敗；「須有某某測試」屬交付條件、寫進 Definition of Done，不寫成 AC
——元層次的 AC 驗的是有沒有寫測試，不是功能對不對。

### 優先度

沿用 `scope-document.md` 的分級，不重新分級：9 項 Must、1 項 Should（能力 7
主動通知推播）。`Could`／`Won't Have` 兩類在 scope 層為空（`[S5]`＝A），故
故事層也不會有——若出現，即代表本站擅自擴大或排除了範圍。

MVP 邊界由 `delivery-planning`（2.9）正式決定，本站的優先度只是它的輸入。

### 待決的切分取向

見下方 U1–U5。

---

## U1. 管理者／平台維運者要不要有故事？

`[Q10]`＝C 定案他是**間接**服務對象：其需求由長期記憶或既有稽核紀錄承載，
**不經由**跨頁面的共享工作階段。但 requirements.md 的 FR4 給了記憶層完整的
授權、保存、刪除與稽核要求（FR4.3a／FR4.3b／FR4.5a／FR4.7），其中稽核那一面
正是為他而存在。

- A. **給他故事，但只限「取得紀錄」這一面**：例如「身為管理者，我想查出某個
  對象最近被誰改過，以便追溯」。不含任何共享工作階段的互動。這讓 FR4.7
  （刪除稽核）與 FR4.3b（可見範圍變更稽核）有故事承載。（建議）
- B. **不給他故事**：間接服務對象在本 intent 沒有可驗收的使用者行為，
  FR4 的稽核面以 NFR 與約束承載即足。代價：一組 Must 級的 FR 沒有任何
  persona 視角的驗收描述。
- C. **給他完整故事**，含「檢視所有使用者的記憶」這類管理操作。代價：這會
  擴大 `[Q10]`＝C 的邊界——該作答明確把他排除在共享工作階段之外，
  而管理介面屬新增的使用者可見面，scope 未涵蓋。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:05:29Z | Mode: guided -->

## U2. 故事的切分軸要用哪一種？

`user-story-patterns.md` 列了五種切分法。本 intent 的 10 項能力與 4 個 persona
是交叉的——同一個 persona 會用到多項能力，同一項能力也服務多個 persona。

- A. **按能力切（Capability-first）**：10 項能力各自成一個故事群（`US1.*`
  對應能力 1……），群內按 persona 或流程分故事。好處是與 `requirements.md` 的
  FR 群組一對一，traceability 最直接；`intent-backlog.md` 的交付序也是按能力排的。（建議）
- B. **按 persona 切**：四個 persona 各自成群。好處是每群讀起來是一條完整的
  使用者旅程。代價：同一項能力會散在多群，FR → US 的追溯變成多對多。
- C. **按工作流程切**：依 `user-flow.md` 的 5 條流程成群。好處是與已核可的
  流程圖一對一。代價：能力 4（記憶）、能力 9（階層）不在任何一條流程的主線上，
  會沒有歸屬。
- D. **混合**：Must 能力按能力切，Should 與基礎設施類按流程切。
  代價：兩套切分軸並存，讀者需先判斷某則故事屬哪一套。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:05:29Z | Mode: guided -->

## U3. 三項量測資料交付物要不要寫成故事？

requirements-analysis 把三項交付物指派給本站：≥ 50 筆標註測試集（NFR1）、
N 個切換情境清單（NFR2）、跨功能任務情境集合 ＋ 現行 UI 基準（NFR11）。
它們**不是使用者可見行為**，但如果不成為故事就沒有 `US` id，
`traceability.json` 也無法把對應的 NFR 指向任何承載者。

- A. **不寫成故事，改在 `stories.md` 設一個獨立的「量測交付物」段落**，各給一個
  非 `US` 的 id（如 `M-1`／`M-2`／`M-3`），並在 `traceability.json` 把三條 NFR
  記為 `Deferred` 指向 `build-and-test`（3.6）。理由：它們沒有 persona，
  硬套 `As a [persona]` 會產生 `product-guide.md` 明文禁止的「開發者視角故事」。（建議）
- B. **寫成故事，persona 用「開發者／QA」**。好處是有 `US` id、能被
  `delivery-planning` 當成一般工作估算。代價：`user-story-patterns.md` 逐字把
  「As a developer, I want to migrate the database」列為反樣式（Too Technical），
  且本站的 persona 清單沒有開發者。
- C. **本站只產出情境清單本身**（三份資料檔），不在 `stories.md` 提及。
  代價：`delivery-planning` 看不到它們，工作量會被漏估——而它們正是
  requirements-analysis 列為需回補的 N-3。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:05:29Z | Mode: guided -->

## U4. 能力 1 要切成幾則故事？

能力 1 是最大的 Must：`requirements.md` 給了它 **8 條子需求**（FR1.1 意圖識別
與交辦、FR1.2 工作項狀態、FR1.3 信心不足不交辦、FR1.4 逐項更正、FR1.5
prompt_guard、FR1.6 信心值輸出、FR1.7 門檻 0.7、FR1.8 入口頁授權）。
`user-story-patterns.md` 要求每則故事 3–6 條 AC；8 條子需求塞一則必然超標。

依 `project.md` 的既有教訓（`user-stories:c32`）：入口故事過大時應拆，
且拆後 AC 前綴跟故事號走以免撞號。

- A. **拆四則**：(1) 說出需求並被交辦（FR1.1／FR1.2／FR1.5）、(2) 信心不足時
  被反問（FR1.3／FR1.6／FR1.7）、(3) 交辦錯了可逐項導回（FR1.4）、
  (4) 入口頁的權限落點（FR1.8）。每則 3–5 條 AC，四則各自對應線框的不同節。（建議）
- B. **拆三則**：把 (3) 逐項更正併入 (1)，因為兩者都在「交辦」這條主線上。
  代價：(1) 會有 6–7 條 AC，逼近上限。
- C. **拆兩則**：成功面一則、失敗面一則（含反問與更正）。
  代價：每則 4 條以上 AC 且失敗面那則同時涵蓋兩種不同的失敗（判不出來 vs 判錯）。
- D. **拆五則以上**：FR1.8 的授權再拆成「有權限者的落地」與「無權限者的落地」。
  代價：後者是不可達狀態（`[R8]` 明寫「不存在無權限的入口頁」），拆出來會是
  一則無法驗收的故事。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:05:29Z | Mode: guided -->

## U5. 11 條 NFR 在 `traceability.json` 裡怎麼覆蓋？

`traceability` sensor 會驗每個 `FR`／`NFR` id 都被宣告且有覆蓋，且 `OK` 的
target 必須是 `stories.md` 內真的存在的 `US` id。11 條 NFR 中有些天然對得上
故事（NFR4 重啟還原、NFR7 保存與刪除稽核），有些是純量測或純機制
（NFR1／2／3／11 的門檻、NFR5 的 WS 契約閘門、NFR6 的 PG CI job）。

- A. **逐條判定，三種狀態並用**：對得上使用者可見行為的記 `OK` 並指向故事；
  門檻類記 `Deferred` 指向 `build-and-test`（3.6，ALWAYS）；純機制類記
  `Deferred` 指向其在 requirements.md 已指定的落點（NFR5 → `contract-design`、
  NFR6 → CI job）。每一條都附理由。（建議）
- B. **全部記 `Deferred`**：NFR 本質上由後續站承載，本站不強行對應故事。
  代價：NFR4（重啟後脈絡可還原）明顯是使用者可感知的行為，記 Deferred 會讓
  它在故事層沒有任何驗收描述。
- C. **全部想辦法對到故事**：為每條 NFR 找或造一個故事承載。
  代價：會為了湊覆蓋而造出「身為使用者，我想要系統在 2 秒內回應」這類
  把 NFR 包裝成故事的產物，那不是故事而是需求的複寫。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:14:33Z | Mode: guided -->

---

## Mob 整合期間加開的判斷題（U6–U9）

依 `stage-protocol-ensemble.md` §5 的分流規則：三位參與者提出的未解反對意見中，
**判斷性的爭議（兩邊立場都合理）當場交給使用者**，不由 lead 整合吸收。
以下四題即屬此類。知識性的爭議與純覆蓋缺口由 lead 直接處理，不成題。

## U6. `US4.3`（管理者追溯變更）要怎麼處置？

設計師與品質工程師**各自獨立**證明那三條 AC 今天就判定不可滿足，證據不重疊
且皆經 lead 複驗：`openapi.json` 42 條 path 零稽核查詢端點；`grep -rn "audit"
frontend/src` 零命中；`AdminPage.tsx:327–332` 表頭是帳號名冊（無變更歷程）；
唯一還活著的 `estimate_audit_events` **只寫不讀**（`estimate_audit.py` 只有
`db.add`，全樹無 query、無端點、無 UI）；已核可的 13 格線框中零管理／稽核畫面。

草稿原本把它寫成「界線提醒：若實作時發現需要新畫面就回補」。那個寫法現在站不住
——**這件事現在就查得出來**。

- A. **升為已查證的回補項 N-8，故事保留**：明確宣告本 intent 多一個新的使用者
  可見面（稽核查詢面），與 N-7（專案／系統建立路徑）同級，列入回補清單交
  `delivery-planning` 估算。代價：本 intent 的範圍再擴一項。（建議）
- B. **降為 `M-*` 資料交付物**：不寫成故事，只要求「稽核事件被寫下來且可被
  取得」這個資料層義務，讀取面留給後續 intent。代價：`[Q2]` 確認的四個關係人中，
  管理者在第一版完全沒有可驗收的使用者行為。
- C. **整則刪除，管理者的稽核需求推到後續 intent**：`[Q10]`＝C 已把他定為間接
  服務對象，第一版不服務他。代價：FR4.7 與 FR4.3b（兩條 Must 級 FR 的稽核要求）
  在故事層沒有任何 persona 視角的驗收描述。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:51:18Z | Mode: guided | mob 整合期間加開 -->

## U7. `US4.1` 是不是 epic——FR4 要不要拆更細？

開發者主張切分軸不一致：**FR4 的 10 條子需求只拆 3 則，而 FR1 的 8 條拆了 4 則**。
`US4.1` 一則獨佔獨立 schema（零前例、SQLite 測不到）、grant 邊界與整套檢索。
設計師另指出線框第 9 節「我的記憶」只被覆蓋三分之一，且該畫面**在已核可線框中
沒有入口**（Sidebar／脈絡列／路由三處皆無）。

- A. **拆成三則**（`US4.1` 脈絡取得／`US4.4` 寫入端與擁有者／`US4.5` 可見範圍
  與 grant 邊界），故事總數由 18 增為 20。代價：本站的故事數與已確認摘要不符，
  須重取一次摘要確認。（建議）
- B. **維持 3 則不拆**：`US4.1` 的四條 AC 已在 3–6 範圍內，切分軸不一致不等於
  切錯。代價：一則故事同時涵蓋零前例的 schema 隔離與整套檢索，INVEST 的
  「Small」（1–5 天）明顯不成立。
- C. **拆兩則**（脈絡取得／寫入端與授權），故事總數 19。折衷。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:51:18Z | Mode: guided | mob 整合期間加開 -->

## U8. `FR1.8` 的「置於瀑布之首」與 `isPending` 相牴觸，怎麼處置？

品質工程師查出、lead 已複驗：`App.tsx:21` 的**第一道**是
`if (isPending) return <Navigate to="/waiting-approval" />`，而已核可的
`FR1.8`（源自 `[R8]`＝A 的「置於瀑布之首」）照**字面**實作，會把入口頁的判斷
插在 `isPending` **之前**——**未核准的帳號會落進入口頁**，繞過等待授權頁。

`[R8]`＝A 的作答當時沒有考慮到 `isPending` 這個分支（該題的衝突描述只列了
五個權限判斷與 `/403`）。

- A. **修正 `FR1.8` 的措辭為「置於權限判斷之首，但在 `isPending` 之後」**，
  並在 `US1.4` 新增一條 AC 守住「未核准帳號仍落在 `/waiting-approval`」。
  這是對已核可需求的**澄清**而非推翻——沒有人會要未核准帳號進入口頁，且
  `require_story_action` 本來就對 `authorization_status != approved` 直接 403。（建議）
- B. **照字面實作，另在入口頁內自行處理未核准狀態**：入口頁自己檢查並導向。
  代價：既有的集中式落地判斷被繞過，同一個判斷出現在兩處。
- C. **回跳 `rough-mockups` 以 Modify 模式修訂 `[R8]`**，因為這是該站定案的
  措辭有缺漏。代價：回跳一站並重走其核可關卡。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:51:18Z | Mode: guided | mob 整合期間加開 -->

## U9. 12 條 AC 目前沒有任何自動化承載層，怎麼處置？

品質工程師查出：唯一能碰前端的 e2e 跑在 `OPENROUTER_API_KEY: ""` 的 stack 上
（`deploy/docker-compose.test.yml:36–38`，註解逐字寫「LLM path stays untouched」），
`ui-regression.md` 與 `ci.yml` 也都沒有金鑰。因此所有「大腦實際回覆了什麼」
類的 AC 在 CI 裡無法被驗證。

- A. **以既有的注入接縫把 LLM 打樁**（`advice_orchestrator._run_agent` 是既有
  先例），讓 e2e 在不需要真實金鑰的情況下驗證意圖識別與交辦的**行為**。
  代價：樁不驗證真實模型的判斷品質——那由 NFR1 的標註集在另一條路徑量測。（建議）
- B. **把金鑰放進 CI**：`ui-regression` 與 `ci.yml` 取得 `OPENROUTER_API_KEY`。
  代價：本 repo 為 public、Actions log 公開可讀，`project.md` 已記載「一次意外
  echo 即等同公開發布」；且每個 PR 都會產生真實的 LLM 花費。
- C. **接受這 12 條為手動測案**，在 `tcms-test-cases`（3.8，blocking）分桶時
  列為「只能手動」。代價：`project.md` 明文警告「預設丟手動等於把問題藏進一份
  沒人會跑的文件」。
- D. 尚未定義。
- X. Other (please specify)

[Answer]: A  <!-- 2026-09-25T02:51:18Z | Mode: guided | mob 整合期間加開 -->

---

## Consolidated Summary Confirmation

<!-- 本區塊於 mob 整合後重寫（修訂 2）。首次確認的收據因 U6–U9 加題而失效，
     且整合結果與當時的計畫已有實質差異，故整份重取，不沿用舊確認。 -->

**九題的定案摘要**（U1–U5 為出題時取得，U6–U9 為 mob 整合期間加開）：

- **U1** 管理者／平台維運者**有故事，但只限「取得紀錄」這一面**，不含任何共享
  工作階段的互動
- **U2** 故事按**能力**切：10 項能力各自成一個故事群（`US1.*` 對應能力 1……），
  與 `requirements.md` 的 FR 群組一對一
- **U3** 三項量測資料交付物**不寫成故事**，改在 `stories.md` 設獨立段落並給
  `M-1`／`M-2`／`M-3` 非 `US` id；對應的 NFR 在 traceability 記 `Deferred`
  指向 `build-and-test`（3.6）
- **U4** 能力 1 **拆四則**：被交辦（FR1.1／1.2／1.5）、被反問（FR1.3／1.6／1.7）、
  逐項導回（FR1.4）、入口頁權限（FR1.8）
- **U5** 11 條 NFR **逐條判定、三種狀態並用**：可見行為記 `OK` 指向故事、
  門檻類 `Deferred` 指向 `build-and-test`、純機制類 `Deferred` 指向已定落點，
  每條附理由
- **U6** `US4.3` 新增一個使用者可見面（稽核查詢面），列為回補項 **N-8**
- **U7** `US4.1` 是 epic，FR4 由 3 則拆為 **5 則**
- **U8** `FR1.8` 與 `isPending` 的牴觸：改寫 `AC1.4.3` 為 `isPending` 期間的守衛，
  並以新的 `AC1.4.4` 取代原本不可達的 Given。**不回改** `requirements.md`
- **U9** 12 條無自動化承載層的 AC：以**替身**（stub）讓其中可自動化的部分落地，
  不把 `OPENROUTER_API_KEY` 放進 CI（本 repo 為 public、Actions log 公開可讀）

**U1 那條界線已從假設變成已查證的事實**（首次確認時寫的是「若實際上需要新畫面
就回補」）：設計師與開發者以互不重疊的證據各自查證，`US4.3` 的三條 AC **無法**
由既有介面滿足——42 條 openapi path 零稽核查詢端點、前端 `audit` 零命中、
`AdminPage` 表頭無變更歷程、唯一活稽核表只寫不讀、13 格線框零管理畫面。
依 U6＝A 的裁決，回補項 **N-8** 成立。`[Q10]`＝C（P-4 不經共享工作階段）未被推翻。

**各故事群的最終則數**（首次確認時為 18 則，U7 使 US4 由 3 則增為 5 則）：

| 群組 | 則數 | 變動 |
|---|---|---|
| US1 意圖識別與交辦 | 4 | — |
| US2 跨功能共享脈絡 | 2 | — |
| US3 子頁面另開新對話 | 1 | — |
| US4 長短期記憶 | **5** | U7：由 3 則拆出 2 則 |
| US5 多意圖識別 | 1 | — |
| US6 多輪對話 | 1 | — |
| US7 主動通知推播 | 1 | 唯一的 Should |
| US8 串流式互動 | 1 | — |
| US9 專案→系統→架構圖 階層 | 2 | — |
| US10 成本能力編排 | 2 | — |

合計 **20 則**故事、**71 條 AC**（每則 3–5 條，皆在 3–6 條範圍內；機械實算），
外加 `M-1`／`M-2`／`M-3` 三項量測交付物。

**兩項我自行判定、未經提問的機械修正**（請一併過目）：

1. **群組 4 的編號改了**。拆分當下寫成 `US4.1a`／`4.1b`／`4.1c`，但框架的 id 文法
   是 `US\d+\.\d+` 與 `AC\d+\.\d+\.\d+`，帶字母後綴的**一個都比對不到**；
   而 `units-generation` 與 `domain-design` 也用同一組 pattern 從 `stories.md`
   解析上游，那三則故事與 9 條 AC 會對下游全部隱形。已改為 `US4.1`／`US4.4`／
   `US4.5`——接在群組尾端而不是重排 `US4.2`／`US4.3`，因為後兩者已被三份
   contribution 檔引用 11 處，重排會讓那些引用靜默指向另一則故事。故群組 4 的
   文件順序為 `US4.1 → US4.4 → US4.5 → US4.2 → US4.3`。
2. **順帶查出上游同型問題，但沒有回改**：`requirements.md` 的 `FR4.3a`／`FR4.3b`／
   `FR4.5a` 也落在 id 文法外（會被解析成 `FR4`），其個別追溯在機械層不可見。
   追溯表以群組 `FR4` 承接，並列為交接事項——依 `project.md` 的 `refined-mockups:c3`，
   不回改已核可的上游。

四份產出（`stories.md`／`personas.md`／`user-stories-assessment.md`／
`traceability.json`）皆已通過本站的三個檢查（required-sections、upstream-coverage、
traceability：70 筆上游 id、70 列覆蓋、0 findings）。

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
<!-- 作答時間 2026-09-25T03:33:15Z（以 `date -u` 取值，非估計）。確認範圍：U1–U9
     九題定案、20 則故事／71 條 AC 的最終規模、兩項機械修正（群組 4 id 重編、
     上游 FR 後綴問題不回改）。首次確認的收據已因 U6–U9 加題失效，本次為整份重取。 -->

