# User Stories — 故事計畫與釐清問題

> Stage: user-stories（Inception 2.4，mob）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> **每題均附建議選項**，建議理由與代價寫在選項描述內。
> **成本揭露**：本題組共 3 題。答完後我會起草 personas 與 stories，再平行派出三位 agent（design／developer／quality）做獨立盲審，整合後經 reviewer 與你的核可。三位盲審是本 stage 的固定成本，不因題數多寡改變。

## Sources

- [req] `../requirements-analysis/requirements.md` — 18 條 FR、7 條 NFR，本階段的故事完全承接於此
- [intent] `../../ideation/intent-capture/intent-statement.md`、`stakeholder-map.md` — 受益者與其利益的已確認狀態
- [flow] `../../ideation/rough-mockups/user-flow.md` — 三條已核可的使用者流程
- [tp] `../practices-discovery/team-practices.md` — 三項測試底線，構成 AC 的驗收要求
- [kb] `aidlc/spaces/default/codekb/cloud-360/business-overview.md`、`component-inventory.md`

## 故事計畫（供作答參考）

- **Persona 開發取向**：以 intent-capture 已確認的受益者為準，不新創 persona
- **故事格式**：標準 `As a [persona], I want [goal], so that [benefit]`，AC 採 Given/When/Then（inception 護欄要求）
- **優先序**：五項能力在 scope 皆為 Must、缺一不可；MVP 邊界正式決定於 delivery-planning
- **INVEST**：每則故事附合規註記；本 intent 的依賴鏈（PU-1→PU-2→PU-3→PU-5，PU-4 平行）使完全的 Independent 不可得，此為既定事實而非缺陷

---

## Q1. Persona 涵蓋範圍：只寫兩個確認受益者，還是四個可見角色都寫？

> `intent-statement` 確認的受益者只有兩個：`Platform_Admin`（日常管理效率）與 `Security_Reviewer`（稽核軌跡）。
>
> 但 `stakeholder-map` 有一條 assumption 明載：`Project_Admin` 與 `Platform_Owner` **具備使用者管理介面的可見性，但兩者在本工作中的利益均未被指認** —— 本階段不推定其利益內容，亦不將其列為受益者或排除。
>
> 也就是說：四個角色都會看到這個欄位，但只有兩個角色的「為什麼需要它」是確認過的。

A. **只寫兩個確認受益者，另兩個列為「可見但利益未指認」** — personas.md 詳寫 `Platform_Admin` 與 `Security_Reviewer`，並以一段明確記載另兩個角色的可見性事實與其未確認狀態。**（建議）** 忠於上游的確認狀態，不憑空發明使用者目標；同時不讓下游誤以為只有兩個角色看得到。代價：personas 的完整度看起來較「不圓滿」。
B. **四個角色都寫成完整 persona** — 為 `Project_Admin`、`Platform_Owner` 也編寫目標與痛點。代價：那兩個角色的目標會是**發明的**，違反 inception 護欄「不得引入無來源需求」，且 stakeholder-map 明確要求不推定其利益。
C. **只寫兩個，完全不提另兩個** — 最簡潔。代價：下游可能誤判可見範圍，而可見範圍是 FR-4.2 明訂的事實（四個管理類角色皆可見）。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q2. 故事拆分粒度：一則對應一項能力，還是依使用者價值再拆？

> requirements 的 FR-1～FR-5 對應 scope 的五項 Must 能力（PU-1～PU-5）。故事可以一對一對應，也可以依「使用者實際獲得什麼」再拆。
>
> 舉例說明差異：FR-1（記錄活動時間）本身**對使用者不可見** —— 它是 FR-2（顯示）的前提。一對一拆法會產出一則「作為系統，我要記錄活動時間」這種沒有 persona 的偽故事；依價值拆法則會把記錄能力併入「看得到時間」的故事，讓每則故事都有真實受益者。

A. **依使用者價值拆，容許一則故事橫跨多個 FR** — 每則故事都有真實 persona 與可感知的價值；FR 到故事的追溯以對照表表達（不是一對一）。**（建議）** 符合 INVEST 的 Valuable 與「垂直切片」原則，也避免產出無 persona 的偽故事。代價：故事與 FR 非一對一，追溯需靠對照表而非編號對齊。
B. **一則故事對應一項能力（FR-1～FR-5 各一則）** — 追溯最直觀。代價：FR-1 會變成沒有 persona 的技術任務偽裝成故事，違反 INVEST 的 Valuable。
C. **更細的拆分（每個 FR 子項一則，約 18 則）** — 粒度最細。代價：對一個「加一欄」的 feature 而言明顯過度切分，且多數子項無法獨立交付價值。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 依使用者價值拆，容許一則故事橫跨多個 FR（採納建議：避免產出無 persona 的偽故事；FR 追溯以對照表表達）

---

## Q3. 既有功能的回歸驗證要不要寫成故事？

> requirements NFR-7 要求「既有頁面功能不得因本變更退化」，PU-5 的卡片改造會動到既有表格架構，而回歸涵蓋面目前是開放問題（requirements OQ-4，留待 inception 後續階段界定）。
>
> 問題是：回歸驗證應該以**故事**形式表達（有 persona、有價值），還是留在 NFR 與測試計畫層？

A. **不寫成獨立故事，但把回歸要求寫進 PU-5 相關故事的 AC** — 卡片改造那則故事的驗收條件包含「既有操作在小螢幕全數可用」。**（建議）** 回歸不是使用者想要的新價值，是變更的品質條件，寫成故事會讓 backlog 出現沒有人「想要」的項目；放進 AC 則能確保它被驗收。代價：回歸涵蓋面的細節仍需在測試計畫階段展開。
B. **寫成獨立故事** — 例如「作為 Platform_Admin，我要在小螢幕仍能完成既有操作」。好處：回歸工作在 backlog 中可見、可排序。代價：它與 PU-5 的故事高度重疊，且「維持現狀」不是新價值。
C. **完全留給測試階段，故事與 AC 皆不提** — 代價：NFR-7 失去在故事層的落點，容易被遺漏。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

# Mob 中場提問（Round 1 後的判斷題）

> 三位協作者（design／developer／quality）各自盲審後提出 24 項 OBJECT。**事實性問題由 lead 直接整合修正**（如導覽文字錯誤、AC 恆真、邊界未定義），下列四題屬 stage-protocol.md §5 定義的 **judgment call —— 兩種立場都合理，需人類裁決**。
> 每題均附建議選項。

## Q4. US-3（管理者順帶掌握活躍度）要保留還是併入 US-1？

> 三位協作者獨立質疑同一件事：US-3 的三條 AC **無一可能失敗**。
> - AC-3.1「同一列視野內」—— 表格容器是 `overflow-auto`，加第 6 欄後該列會水平捲動，「同一視野」既不成立也無可量測門檻
> - AC-3.3 與 AC-1.5 自承重複
> - AC-3.2 與 NFR-7／AC-5.3 重疊，且「既有 e2e 回歸」目前是空集合（6 個 case 無一操作 Admin 頁）
>
> 加上 lead 自己註記它「不含獨立實作」。

A. **併入 US-1，不保留獨立故事** — `Platform_Admin` 的價值以 US-1 的第二個 persona 視角表述。**（建議）** 一則沒有可失敗 AC、沒有實作、沒有獨立驗收的故事，在 backlog 中會被標記完成而沒有人做過任何事。代價：次要 persona 的價值在 backlog 中不再有獨立項次。
B. **保留，但重寫三條 AC 使其可失敗** — 例如把 AC-3.1 改為可量測的欄位可見性條件。代價：需為一則零實作的故事發明驗收標準，容易變成為了存在而存在。
C. **保留原樣** — 代價：三位協作者的一致意見被忽略，且 backlog 出現無法驗收的項次。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 併入 US-1，不保留獨立故事（採納建議：無可失敗 AC、無實作的故事會被標記完成而無人做事）

## Q5. 三項測試底線的 AC 該怎麼寫？

> AC-1.6／AC-4.2／AC-5.5 目前寫成「**元層次**」形式：`Then 存在 TestClient 測試斷言…`。quality 指出這個形式的問題：它驗收的是「有沒有寫測試」，不是「功能對不對」。
>
> 更糟的是 quality 實測發現：**AC-1.6 與 AC-5.5 照做也抓不到要防的缺陷** —— 前者因欄位宣告為選填，漏傳仍輸出 `null`，集合檢查照樣通過；後者因 e2e 資料庫只有一個帳號且必為無紀錄態，後端零實作也會通過。
>
> 這題的答案會成為後續所有故事的 AC 慣例。

A. **改為具體行為 AC，把「要有測試」留給 Definition of Done** — 例如 AC-5.5 改成「Given 某帳號有活動紀錄，When 稽核者檢視清單，Then 該列顯示對應的時間值」，並在故事的 DoD 註明需以 e2e 覆蓋。**（建議）** AC 描述系統行為、DoD 描述交付條件，兩者分工清楚；且行為 AC 才可能真的失敗。代價：需為每條補上能真正失敗的資料前提（例如 e2e 需要有活動紀錄的帳號）。
B. **維持元層次形式，但補強斷言強度** — 保留「存在某測試」的寫法，但明確指定要斷言什麼（例如「欄位值不為 null」）。代價：AC 仍在描述測試而非行為，且 team-practices 的測試底線本來就已經要求要有測試，AC 重述一次是冗餘。
C. **兩者並存** — 行為 AC ＋ 元層次 AC 各一組。代價：AC 數量近乎倍增，對「加一欄」的 feature 明顯過重。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 改為具體行為 AC，「要有測試」留給 Definition of Done（採納建議：AC 描述行為、DoD 描述交付條件）

## Q6. 上線初期「所有帳號都是無紀錄」的處境要不要在故事層處理？

> 這是本 intent 的一個真實處境：功能上線當天，**每一列的最後活動時間都是破折號 `—`**，且沒有任何 `(!)` 標示。對稽核者而言，整欄空白加零標示，讀起來像「這功能沒上線」。
>
> design 另指出一個沒人發現的細節：**「角色」欄目前也用 `—` 表示空值且不可聚焦**。待審核的帳號會出現兩個外觀相同、語意不同、可及性不同的破折號並排。
>
> design 明確不建議設計頁面級空狀態（那是新 UI，屬 scope 擴充）。

A. **新增一條 AC 把上線日狀態釘為預期行為，不新增 UI** — 例如「Given 功能剛上線且無任何帳號產生過活動，When 稽核者檢視清單，Then 全部列顯示無紀錄態，此為預期行為而非缺陷」。**（建議）** 零成本、零新 UI，但讓這個處境變成被驗收過的已知狀態而非意外。另把「兩個破折號並存」列為 refined-mockups 的必答項（區分手段留設計階段）。代價：使用者第一次看到時仍需自行理解。
B. **不處理，維持現狀（僅記在 assumptions）** — 代價：assessment 當初justify 執行本 stage 的理由之一正是「這個處境需要以故事形式讓決策者看見，而非藏在約束條款裡」，只放 assumptions 與該理由自相矛盾。
C. **設計頁面級空狀態說明** — 例如在表格上方顯示「本功能於 YYYY-MM-DD 上線，此前的活動未被記錄」。代價：新增 UI 元素屬 scope 擴充，需回跳 scope-definition 修訂重審。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 新增 AC 把上線日狀態釘為預期行為，不新增 UI；兩個破折號並存列為 refined-mockups 必答項（採納建議）

## Q7. US-1 的粒度：本階段給出建議，還是原封留給 delivery-planning？

> lead 原本把「US-1 是否切分」列為 assumption 留給 delivery-planning。developer 反對這個處理：**本階段已握有全部判斷依據**（實測 US-1 涉及 6 個原始碼檔 ＋ 2 個 blocking 部署資產，序列化 3 處、schema 來源 3 處），把判斷原封往下推等於讓下一站重做一次同樣的分析。

A. **本階段給出「不切分」的帶理由建議，delivery-planning 仍可推翻** — 理由：US-1 的後端記錄與前端顯示若拆開，前半段無法獨立交付任何使用者價值（記錄了但看不到），拆分會製造一個違反 INVEST Valuable 的碎片。**（建議）** 尊重下游的決定權，但不浪費本階段已完成的分析。
B. **原封留給 delivery-planning，不表態** — 代價：下一站需重做相同分析。
C. **本階段直接定案不切分** — 代價：越權，粒度與 Bolt 切分是 delivery-planning 的職責。
D. Not yet defined
X. Other (please specify)

[Answer]: A. 本階段給出「不切分」的帶理由建議，delivery-planning 仍可推翻（採納建議：不浪費已完成的分析，也不越權）
