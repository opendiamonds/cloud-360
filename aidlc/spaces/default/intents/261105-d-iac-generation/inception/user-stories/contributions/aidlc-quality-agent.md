**Collaborator:** aidlc-quality-agent

## Contribution

<!-- 視角：AC Given/When/Then 可測性、負向路徑、PBT／403 掛點、追溯缺口、
     US7.2 上傳失敗、Advisory 下載摘要確認可測性。
     Stance: refute。本檔不改 stories.md／personas.md／traceability.json。 -->

### 0. 範圍與計數

`stories.md` 現有 **Must 故事 12 則、AC 共 23 條**（US1：7、US2：4、US3：4、US4：4、US5：5、US6：2）；**Should 僅表列 US7.1／US7.2，零條 G／W／T**。幾乎所有 Must AC 已採 Given／When／Then 形狀——這點可沿用。阻擋「QA 能寫出會失敗的測試」的是：(1) 若干 Then 是元層次／空洞；(2) 關鍵負向路徑未成 AC；(3) PBT／403 掛在錯誤層或只掛一邊；(4) `traceability.json` 標 OK 但故事本文接不住對應 FR。

判定基準：能否寫出一支**實作做錯就紅**的斷言（`unittest`＋Hypothesis、`TestClient`、Playwright，或標明人工／靜態）。`TESTING.md` 禁止預期結果用「正常／成功」；`team.md` Corrections `user-stories:c3`：元層次「Then 存在某測試」屬 DoD，不是系統行為 AC。

---

### 1. AC 可測性（Given／When／Then）

**可沿用**：AC1.2.4、AC3.1.2、AC4.1.1、AC4.2.1、AC5.1.3 等前置／disabled／4xx 形狀清楚，可直接轉 TestClient／Playwright。

**須改寫或拆層**：

| AC | 問題 | 建議 |
|---|---|---|
| **AC6.1.1** | Then「存在…TestClient」——純元層次；驗的是有沒有寫測試，不是授權行為會不會失敗（違 `user-stories:c3`） | 產品 AC：Given 無權角色，When 呼叫該 D HTTP，Then **403**；Given 有權，When 同路徑，Then **2xx＋契約欄位集**。TestClient 成對寫進 **US6.1 DoD**（或 US2／US3／US4 第一個 HTTP 故事的 DoD） |
| **AC6.2.1** | Then「每步有可觀察**成功態**」＋「有自動化測試護欄」——「成功」違 `TESTING.md`；後半又是元層次 | 拆成：(a) 每步可觀察態寫死（例：D1 後檔案樹含三檔名；D2 後報告區有 finding 列或「無 finding」文案；D3 後改寫清單或「無可改寫項」；下載後 zip 非空）；(b) generator／scanner／redactor 護欄進 **DoD**，勿混進 Then |
| **AC2.1.2** | 「目標為…相容 HCL」難二元失敗 | 可觀測：產出副檔名 `.tf`；UI／文件字串**不**宣稱僅支援單一商業發行版（靜態／e2e 字串斷言）。「語意相容」留設計＋離線 generator 性質，不假裝是 UI AC |
| **AC3.2.2** | 「醒目可見」主觀 | 改為：每則 HIGH／CRITICAL finding **同時**可見嚴重度**文字標籤**（字面含 `HIGH`／`CRITICAL` 或產品凍結之繁中等價）與 finding 識別／標題；不得僅靠色票／圖示（對齊 NFR5） |
| **AC4.1.3** | 產品負向（不得出現明文）OK，但括號「由測試護欄覆蓋」把 DoD 寫進 AC | Then 只留「回應／log sink／下載物抽樣不得含注入明文」；Hypothesis＋突變列 **US4.1 DoD** |
| **AC1.1.2** | 「隱藏**或** disabled」二選一，QA 不知布置哪種 | 本 stage 定一種為 Must 預期，或拆兩條 AC（產品選 A→只驗 A）；否則 e2e 無法寫唯一預期 |
| **AC5.1.2** | 「有成功回饋」偏空洞 | Then：剪貼簿／UI 回饋內容**等於**當前預覽檔全文（或設計凍結之截斷規則＋可見「已複製」類文案） |

---

### 2. 缺失的負向路徑

下列失敗面在 FR／審查已出現，但 Must AC **未覆蓋**或僅暗示：

1. **上傳失敗（requirements R-03 → 現掛 US7.2）**——見 §5；目前零 G／W／T。
2. **D2／D3 執行失敗＋重試**——FR7.3／FR2.6 要求三故事皆「步驟內錯誤＋重試、不整場清空」；僅 **AC2.3.1** 覆蓋 D1。缺：Given D2（或 D3）失敗，When 檢視該步，Then 錯誤可見＋可重試，且既有 D1 草稿（與已成功之 D2 報告，若有）仍可預覽。
3. **Advisory 下載：取消確認**——AC5.1.4 只寫「完成前須通過摘要」；缺 Given 摘要已開，When 使用者**取消／關閉**，Then **不**完成下載（無新 zip／下載事件未觸發）。沒有取消支，確認閘等於恆真。
4. **無 HIGH／CRITICAL 之下載**——缺正向對照：Given D2 成功且最高嚴重度低於 HIGH（或無 finding），When 下載，Then **不**出現 HIGH／CRITICAL 摘要確認即可完成（否則實作可能對所有下載都彈窗，AC5.1.4 仍綠）。
5. **未選檔就複製**——AC5.1.2 只涵蓋已選檔；缺 disabled／錯誤態。
6. **無 D1 時檢視 D2 步驟空狀態**——FR6.1 要求可自由檢視各步；US4.2 只覆蓋 Secrets。缺：無 D1 時打開**掃描**步驟 → 空狀態／說明可見，執行仍 disabled（與 AC3.1.2 執行面分離）。
7. **FR4.3 不寫入雲端 SM**——`traceability` 掛 US4.1，但無 AC／DoD 可靜態或契約斷言「無 SM Create／Put 整合」。應進 US4.1 DoD（靜態／架構檢核），勿只靠「涵蓋 FR4」。

---

### 3. PBT／403 掛點

`stories.md` INVEST 註「PBT／403 掛 US4／US6」——方向對，**落點不足**：

| 護欄（來源） | 現況 | 缺口 |
|---|---|---|
| **403 allow／deny**（FR7.2、NFR4、team Q2） | 僅 AC6.1.1 元層次「存在 TestClient」 | 缺產品雙向 AC；且「第一個 D HTTP」可能是 D1／D2／D3 任一——DoD 須寫明：**落地那一個**故事同 PR 齊備有權 2xx＋無權 403，不得只測 happy path |
| **Generator PBT**（FR2.5、NFR2、ADR-0006） | US2.1 無 DoD；AC 只談 UI 檔案樹 | US2.1（或 US6.2）須 **DoD** 具名性質（例：模組樹必含約定檔名；序列化往返；非法圖輸入不靜默產出空樹）。僅 example「有三個檔」不夠 |
| **Scanner／報告形狀 PBT**（FR3.4–3.5） | US3.1 只有 UI 報告 | 缺 DoD：報告形狀 unittest（CLI stub）＋Hypothesis 不變量；以及「本 intent **不**新增 CI IaC scan job」的可查證項（workflow 靜態） |
| **Redactor PBT＋負向突變**（FR4.4–4.5、team Q4） | AC4.1.3 混在產品 Then | 產品負向保留；DoD 明列：注入明文 → sink 零命中；拿掉遮罩 → 測試紅 → 還原綠；另加 Hypothesis 性質（非只 example） |

NFR2 在 `traceability.json` 掛 US4.1、US6.2——可接受為覆蓋宣稱，但 **US2.1／US3.1 才是 generator／scanner 的自然掛點**；只掛 US6.2 會讓「先交 D1 UI、後補 PBT」逃過故事簽核。建議：各核心純函式的 PBT DoD 掛在**引入該核心的第一個 Must 故事**上，US6.2 只保留端到端演示＋彙總引用。

---

### 4. 追溯缺口（`traceability.json` vs 故事本文）

JSON 幾乎全標 `OK`，但多處是**標籤覆蓋、AC 未承接**（sensor 認 ID 映射，不認可測性）：

| 上游 | JSON target | 故事缺口 |
|---|---|---|
| FR2.5 | US2.1 | 無 agent／`langgraph_runtime`／純函式 generator 路徑之 AC 或 DoD |
| FR3.4、FR3.5 | US3.1 | 無「報告形狀可 unittest／PBT」「不新增 CI scan job」 |
| FR4.3、FR4.5 | US4.1 | 無「禁 SM 寫入」；PBT 未進 DoD |
| FR6.1 | US4.2 | 只覆蓋 Secrets 可開；D2 步驟無 D1 時的可檢視未寫 |
| FR7.3 | US2.3 | 只覆蓋 D1 失敗；D2／D3 失敗未承接 |
| FR8.1 | US5.1 | AC5.1.1 有「無 apply／destroy」——可接受；建議 DoD 加「OpenAPI／agent 工具清單無 apply／destroy」靜態項 |
| US7.1、US7.2 | **不在 coverage** | Should 無 ID 映射；R-03 若仍開放，追溯靜默消失 |
| NFR5 | Deferred → refined-mockups | OK；但 AC3.2.2「不單靠顏色」已部分承接——Deferred 註解宜寫「對比閾值／鍵盤」以免以為整包 NFR5 已由 US3.2 消化 |

另：`upstream_ids` 含完整 FR／NFR 子項，與 coverage 列一致——機械面尚可。問題在 **OK 的語意過寬**。Lead 應在修 AC／DoD 後，對上表改為真實可測 target，或把僅設計可驗者改 `Deferred`＋具體 stage。

---

### 5. US7.2 上傳失敗（R-03）

requirements 審查 **R-03（Minor）**：FR1.4 只有上傳成功；失敗時（格式不符、過大、伺服器錯誤）未定——「錯誤提示且脈絡不變」。

現況：`stories.md` Should 表一行摘要，**無故事正文、無 AC**。後果：

- QA 無法寫 TC（無 Given／When／Then、無通過條件）。
- 宣稱「關閉／承接 R-03」不成立——表列 ≠ 覆蓋。
- 若維持 Should 且本輪不實作，須在故事層**顯式**寫「R-03 仍 Open／Deferred 至某 stage」，避免下游以為已關。

**最低可測補法**（建議升 Must 掛 US1.2，或給 US7.2 完整正文）：

- **AC7.2.1** Given 脈絡已指向圖 A，When 上傳**非** `.drawio`／`.xml`（或設計凍結之非法類型），Then 可見錯誤提示，且脈絡**仍為圖 A**（不切到空／新圖）。
- **AC7.2.2**（可 Should）Given 同上，When 上傳觸發伺服器／大小錯誤（stub 5xx／413），Then 錯誤可見且脈絡不變。

不要求本 stage 定錯誤字串原文（留給設計），但「有錯誤＋脈絡不變」必須二元可判。

---

### 6. Advisory 下載摘要確認可測性（AC5.1.4／FR3.3）

AC5.1.4 現文：

> Given D2 曾報告 HIGH／CRITICAL，When 我下載，Then 完成前須通過摘要確認（FR3.3）。

對 QA 的問題：

1. **「通過確認」是程序，不是觀察結果**——未寫確認 UI 必含什麼（HIGH／CRITICAL **計數或清單**，FR3.3 原文），也未寫確認後的可觀察完成態（開始下載／取得 zip）。
2. **缺取消支**（見 §2.3）——沒有「不通過則不完成」，閘門不可證偽。
3. **與 US5.2 交織未定**：D3 改寫後再下載且仍有歷史 HIGH／CRITICAL 報告時，是否仍要摘要？缺一條 AC 會讓實作只在「純 D2 後首次下載」做確認。
4. **AC3.2.1／AC3.2.2** 管「進 Secrets」與「列表醒目」；下載確認只在 AC5.1.4——拆分正確，但 5.1.4 強度不足，FR3.3 後半會漏測。

建議改寫為至少兩條（產品行為，非元測試）：

- **AC5.1.4a** Given 當前工作階段之 D2 成功報告含 ≥1 則 HIGH 或 CRITICAL，When 我發起 zip 下載，Then **先**出現摘要（可見 HIGH／CRITICAL 計數或條目清單），且在確認前**不**完成檔案下載。
- **AC5.1.4b** Given 摘要已顯示，When 我確認，Then 下載完成且 zip 含模組樹；When 我取消，Then 不完成下載，工作區草稿狀態不變。
- （建議）**AC5.1.4c** Given 報告無 HIGH／CRITICAL，When 下載，Then 無該摘要閘即可完成（對照 §2.4）。

Playwright：規則 C 在「真 UI 取代 Coming Soon」時觸發——下載確認屬資料／流程形狀，應有 e2e：攔截 download 事件或斷言 button 在確認前不觸發；後端若另有下載 API，TestClient 不替代 UI 閘（閘在瀏覽器）。

---

### 7. 其餘同意點（精簡）

- 依賴圖 US1→US2→US3→US4 與 Q3=A（D3 需 D2 成功報告）一致；**AC4.1.1** 同時要求 UI disabled＋API 4xx——可測性佳，關閉 R-01 的故事層處置正確。
- **AC1.3.1** 切圖清空產物＋控制項回 disabled——可測，關閉 R-02 方向正確（細節文案留設計）。
- Personas：Alex 主路徑、Elena（US1.3）、Fiona（US3／權限）符合 Q5=A。
- Won't（代 apply、CI scan job、自研引擎）與 FR／team 一致；勿在 Must AC 再夾帶。

---

## Positions

| # | 主題 | Position | 理由 |
|---|---|---|---|
| 1 | AC 整體 G／W／T 形狀 | **AGREE** | Must AC 多數已是 Given／When／Then，可作為 TCMS／自動化原文基礎 |
| 2 | AC6.1.1／AC6.2.1 元層次與「成功態」 | **OBJECT** | 違反 `user-stories:c3` 與 `TESTING.md`；403／PBT／演示護欄應拆成產品 AC＋DoD |
| 3 | AC3.2.2「醒目」／AC5.1.2「成功回饋」／AC1.1.2 雙可選 | **OBJECT** | 非二元可判或預期不唯一，e2e 無法寫死 |
| 4 | 負向：D2／D3 失敗重試、複製未選檔、無 D1 檢視 D2 | **OBJECT** | FR6.1／FR7.3 未完整落到 AC；僅 D1 失敗不夠 |
| 5 | PBT 掛 US2.1／US3.1／US4.1 DoD；403 雙向產品 AC | **OBJECT**（現況） | INVEST 有宣告但故事未具名性質、未成對 allow／deny；JSON OK 不能代替 |
| 6 | `traceability.json` 全面 OK | **OBJECT** | FR2.5／3.4／3.5／4.3／4.5／6.1／7.3 等為標籤覆蓋；US7.* 無列 |
| 7 | US7.2 上傳失敗承接 R-03 | **OBJECT** | 僅 Should 一行、無 AC＝未覆蓋；須完整 AC 或顯式 Deferred |
| 8 | Advisory 下載確認 AC5.1.4 | **OBJECT** | 缺摘要內容、確認後完成態、取消支、無 HIGH 對照；FR3.3 下載半段目前不可證偽 |
| 9 | R-01／R-02 故事層關閉（AC4.1.1、AC1.3.1） | **AGREE** | 邊界可測；與 Q3／Q4 定案一致 |
| 10 | 平台不代 apply（AC5.1.1）與三 persona 分配 | **AGREE** | 與 scope／personas／Forbidden 一致 |

**總結 stance：** 結構與依賴可前進，但在修掉元層次 AC、補上 US7.2／下載確認／D2·D3 失敗等負向、以及把 PBT／403 寫進正確故事的 DoD＋產品雙向 AC 之前，**不建議**以目前正文簽核為對 QA／TCMS 就緒。
