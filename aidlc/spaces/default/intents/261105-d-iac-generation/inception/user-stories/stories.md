# User Stories — Story D IaC 生成與安全交付

<!-- Stage: user-stories（mob）· Q1–Q5=A。
     切法＝工作流程；粒度＝標準；R-01＝D3 需 D2 報告；切圖＝清空；Alex 主路徑（選圖／D1／下載）。
     Round 1 已折入 design／developer／quality 事實類 OBJECT；RBAC 三角 edit 採多角色演示（見 US6.2）。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）
- **personas**（`./personas.md`）
- **questions**（`./user-stories-questions.md`）
- **contributions/**：Round 1 三份盲審
- **review R-01** 已於 Q3=A 關閉（故事層）；**R-02** 於 US1.3；**R-03** 於 US1.4

## Round 1 整合摘要

| 修正 | 依據 |
|---|---|
| 掃描步驟補自由檢視空態（對稱 US4.2） | design OBJECT／quality §2.6 |
| D1／D2／D3 進行中態；D2／D3 失敗＋重試 | design／quality／FR7.3 |
| US2.1 主角改 Elena；UI AC 與 generator DoD 分層 | design persona／developer US2.1／quality PBT |
| 執行 D3 前置＝D1 ∧ D2 成功報告（覆寫 FR6.2 對 D3） | developer OBJECT 6 |
| 切圖：提示可感知；進行中請求不得寫回舊圖產物；舊 report_id→4xx | design／developer US1.3 |
| 入口／執行釘死 view／edit；無權入口採 disabled＋說明 | developer OBJECT 5／10；quality AC1.1.2 |
| US6.1 產品雙向 403 AC＋DoD TestClient；US6.2 多角色演示＋可觀察態 | developer／quality 元層次 |
| Advisory 下載：摘要內容、確認／取消、無 HIGH 對照 | quality §6 |
| 複製回饋可判；未選檔 disabled；HIGH 文字標籤 | quality AC 可測性 |
| 上傳失敗升 Must（US1.4）關閉 R-03 | quality US7.2 |
| NFR5 鍵盤操作一條 Must；對比閾值仍 Deferred→refined-mockups | design NFR5 |
| PBT／禁 SM 寫入／禁 apply 工具進各核心故事 DoD | quality §3 |

**Lead 判斷（未再問使用者）**：現行種子無三角 `edit` → US6.2 改為 **多角色協作演示**（不改種子）；Alex 仍為選圖／D1／下載主路徑（Q5=A）。

## 優先序與依賴

皆為本輪 **Must Have**（除非標 Should）。依賴：

```
US1.* (選圖／入口) --> US2.* (D1)
US2.* --> US3.* (D2)
US3.* --> US4.* (D3)   # Q3=A：執行 D3 需 D2 成功報告（補強 FR6.2）
US2.* --> US5.* (下載；另受 D2 摘要／D3 改寫影響)
US1.* --> US6.* (權限／演示)
```

**Won't**：代 apply、寫入雲端 SM、自研掃描引擎、本輪 CI IaC scan job。

**權限語意（全故事共用）**

| 操作 | 所需 story action |
|---|---|
| 進入 IaC 工作區／檢視各步驟 UI | 對應故事之 `view`（至少 D1 `view` 進入口） |
| 執行 D1／D2／D3 | 該故事之 `edit` |
| 下載／複製 | D1 成功草稿＋呼叫端授權（設計凍結；不得以 `view` 放行執行 API） |

---

## US1.1 從 Workspace 進入 IaC 工作區

> **As a** Alex，**I want** 點「生成 IaC」進入步驟式工作區（草稿為主），**so that** 我不再卡在 Coming Soon。

**優先序**：Must Have · **涵蓋**：FR1.1、FR1.6、NFR5（操作面）

### 驗收標準

- **AC1.1.1** Given 我有 D1 `view`（或更高），When 我在 Workspace 看工具列，Then 「生成 IaC」可點且進入 IaC 工作區（可見生成／掃描／Secrets 步驟與草稿主區）。
- **AC1.1.2** Given 我沒有 D1 `view`，When 我檢視入口，Then 入口為 **disabled**（非隱藏）並說明缺少的故事權限（點出 D1／D2／D3 與 view／edit 缺口之一）。
- **AC1.1.3** Given 有權使用者只使用鍵盤，When 操作步驟切換、執行／disabled 控制、findings 列、下載與複製，Then 每一項可聚焦並啟動（disabled 者可聚焦或具名說明且不可啟動）；焦點可見；嚴重度與切圖提示不單靠顏色。

---

## US1.2 選圖：活躍圖、改選與上傳

> **As a** Alex，**I want** 進入時帶入活躍架構圖，並能改選或上傳 `.drawio`／`.xml`，**so that** D1 輸入圖正確（R-01／F1=C）。

**優先序**：Must Have · **涵蓋**：FR1.2–FR1.5

### 驗收標準

- **AC1.2.1** Given Workspace 有當前活躍圖，When 我進入 IaC 工作區，Then 脈絡自動顯示該圖。
- **AC1.2.2** Given 同專案有其他圖，When 我從下拉改選，Then 脈絡更新為新圖。
- **AC1.2.3** Given 我上傳合法 `.drawio`／`.xml`，When 上傳成功，Then 脈絡指向新建／匯入圖。
- **AC1.2.4** Given 無活躍圖、無可選圖且未上傳，When 我嘗試產生，Then 全頁／主區阻擋並提供回 Workspace 的 CTA；不可成功呼叫 D1。

---

## US1.3 切換架構圖後清空產物

> **As a** Elena，**I want** 換圖時清空當次 IaC 產物並被提示，**so that** 不會下載錯圖的草稿（Q4=A）。

**優先序**：Must Have · **涵蓋**：FR1.3＋Q4 · **關閉** requirements R-02（故事層）

### 驗收標準

- **AC1.3.1** Given 目前已有 D1（或 D2／D3）產物，When 我改選或上傳導致脈絡圖變更，Then 系統清空當次 D1／D2／D3 工作產物、顯示**可見文字**提示（輔助技術可得知已清空），且下載／執行 D2／D3 回到「無草稿」disabled 態，直到新 D1 成功。
- **AC1.3.2** Given 切圖當下仍有進行中的 D1／D2／D3 請求，When 脈絡圖 id 已變更，Then 該請求結果不得寫入目前工作區為可下載草稿；對舊 `report_id` 呼叫 D3 → 4xx。

**DoD（實作／測試義務）**：產物以 `(session|user, diagram_id)` 為鍵（或明確 session-only 並在刷新後失效）；e2e／TestClient 覆蓋「切圖後舊 artifact 不可再用」。

---

## US1.4 上傳失敗時脈絡不變

> **As a** Alex，**I want** 上傳失敗時看到錯誤且選圖脈絡不變，**so that** 不會誤切到空圖（R-03）。

**優先序**：Must Have · **涵蓋**：FR1.4 負向 · **關閉** R-03

### 驗收標準

- **AC1.4.1** Given 脈絡已指向圖 A，When 上傳非 `.drawio`／`.xml`（或設計凍結之非法類型），Then 可見錯誤提示，且脈絡仍為圖 A。
- **AC1.4.2** Given 同上，When 上傳觸發伺服器／大小錯誤（stub 5xx／413），Then 錯誤可見且脈絡仍為圖 A。

---

## US2.1 產生多檔 HCL 模組樹並預覽

> **As a** Elena，**I want** 對脈絡圖執行 D1 得到多檔模組樹與預覽，**so that** 我能檢視可帶走的模組化草稿（Q2=A）。

**優先序**：Must Have · **涵蓋**：FR2.1–FR2.3、FR2.5

### 驗收標準

- **AC2.1.1** Given 脈絡圖有效且我有 D1 `edit`，When D1 成功，Then UI 檔案樹至少含 `main.tf`／`variables.tf`／`outputs.tf`（或設計核准等價拆分），且選檔可預覽 HCL 全文。
- **AC2.1.2** Given D1 成功，When 我檢視產出檔名與產品文案，Then 檔案副檔名為 `.tf`，且 UI／說明**不**宣稱僅支援單一商業 Terraform 發行版。
- **AC2.1.3** Given 我已觸發 D1 且請求尚未結束，When 我檢視生成步驟，Then 顯示進行中狀態（對齊 Workspace agent 語彙），且執行控制不可再送出第二個成功態請求。

**DoD**：決定性 generator 核心具名 Hypothesis／unittest（模組樹約定檔名、序列化往返、非法圖輸入不靜默空樹）；agent 編排可 stub／離線；路徑落 `backend/iac/`，不經 `agent_router`／`user_router`。

---

## US2.2 多雲資源不靜默丟棄

> **As a** Alex，**I want** 圖含 GCP／Azure 時仍看到產出或實驗性標記，**so that** 資源不會被默默省略。

**優先序**：Must Have · **涵蓋**：FR2.4

### 驗收標準

- **AC2.2.1** Given 測試圖含非 AWS 資源，When D1 成功，Then 產出中可見對應內容或明確「實驗性」區塊；不得無提示省略。

---

## US2.3 D1 失敗可重試且保留策略

> **As a** Alex，**I want** D1 失敗時看到錯誤並重試，**so that** 我不失去可恢復的工作狀態。

**優先序**：Must Have · **涵蓋**：FR2.6、FR7.3

### 驗收標準

- **AC2.3.1** Given D1 失敗且脈絡 `diagram_id` 未變，When 我看該步驟，Then 有錯誤訊息與重試；若先前已有成功草稿則仍可預覽；不採「失敗即清空整次工作階段」。

---

## US3.1 執行掃描並看到報告

> **As a** Fiona，**I want** 對 D1 成功草稿執行 D2 並看到嚴重度文字化的報告，**so that** 我能評估風險（FR3）。

**優先序**：Must Have · **涵蓋**：FR3.1、FR3.4–FR3.5

### 驗收標準

- **AC3.1.1** Given 存在 D1 成功草稿且我有 D2 `edit`，When 我執行 D2 成功，Then 顯示報告（≥1 finding 或明確「無 finding」文案），每則 finding 含可讀嚴重度文字。
- **AC3.1.2** Given 無 D1 成功草稿，When 我嘗試執行 D2，Then 控制項 disabled＋說明，且執行 API → 4xx。
- **AC3.1.3** Given 無 D1 成功草稿，When 我切到掃描步驟，Then 畫面可開並顯示空狀態／說明，執行掃描控制項 disabled＋說明（不可進入成功 loading）。
- **AC3.1.4** Given 我已觸發 D2 且請求尚未結束，When 我檢視掃描步驟，Then 顯示進行中狀態，且不可重複送出成功態請求。
- **AC3.1.5** Given D2 失敗，When 我看該步驟，Then 有錯誤訊息與重試；既有 D1 草稿仍可預覽，不整段清空工作階段。

**DoD**：報告形狀 unittest（CLI stub）＋Hypothesis 不變量；本 intent **不**新增 CI IaC scan job（workflow 靜態可查）。

---

## US3.2 Advisory：不擋進入 Secrets；HIGH／CRITICAL 文字可見

> **As a** Fiona，**I want** 即使有 HIGH／CRITICAL 仍能進入 Secrets 步驟，但風險必須可見，**so that** 流程不被硬擋且風險可讀（Q4=A）。

**優先序**：Must Have · **涵蓋**：FR3.2–FR3.3（列表面）

### 驗收標準

- **AC3.2.1** Given D2 報告含 HIGH 或 CRITICAL，When 我導向 Secrets 步驟，Then 仍可進入該步驟 UI。
- **AC3.2.2** Given 同上，When 我檢視掃描區，Then 每則 HIGH／CRITICAL finding **同時**可見嚴重度文字標籤（字面含 `HIGH`／`CRITICAL` 或產品凍結之繁中等價）與 finding 識別／標題；不得僅靠色票／圖示。

---

## US4.1 僅在 D2 成功後執行 D3 改寫

> **As a** Alex（執行需 D3 `edit`；演示可由 Fiona 代執行），**I want** 只有在已有 D2 成功報告後才能執行 secrets 改寫，**so that** 我不能繞過掃描（Q3=A／R-01）。

**優先序**：Must Have · **涵蓋**：FR4、FR6.2（D3 補強）· **關閉** R-01

> **契約註記（覆寫／補強 FR6.2 對 D3）**：執行 D3 前置＝同工作階段存在 D1 成功草稿 **∧** 至少一次 D2 `status=succeeded` 報告（允許 zero findings）。僅有 D1 不足。建議 API 以 reason code 區分「無 D1」與「無 D2 成功報告」（409 或 422，設計凍結）。

### 驗收標準

- **AC4.1.1** Given 有 D1 草稿但**從未**成功完成 D2，When 我嘗試執行 D3，Then 控制項 disabled＋說明，且執行 API → 4xx。
- **AC4.1.2** Given 已有至少一次 D2 成功報告（可為零 finding）且有 D1 草稿，且我有 D3 `edit`，When 我執行 D3 成功，Then 疑似密文賦值改寫為 SM 參考語法，UI 列出已改寫項目（或「無可改寫項」）。
- **AC4.1.3** Given D3 完成（曾注入可辨識明文樣式），When 我檢查回應／log sink／後續下載物抽樣，Then 不得出現該明文樣式。
- **AC4.1.4** Given 我已觸發 D3 且請求尚未結束，When 我檢視 Secrets 步驟，Then 顯示進行中狀態，且不可重複送出成功態請求。
- **AC4.1.5** Given D3 失敗且先前已有 D2 成功報告與 D1 草稿，When 我看該步驟，Then 有錯誤訊息與重試；D1 草稿與既有 D2 報告仍可檢視，不整段清空。

**DoD**：Redactor Hypothesis＋負向突變（注入明文 → sink 零命中；拿掉遮罩 → 測試紅 → 還原綠）；靜態／架構檢核：**無**雲端 SM Create／Put 整合（FR4.3）。

---

## US4.2 可檢視 Secrets 步驟但不代表可執行

> **As a** Alex，**I want** 自由打開 Secrets 步驟畫面，**so that** 我能預覽說明；執行仍受 US4.1 約束（Q6=C／F2=A）。

**優先序**：Must Have · **涵蓋**：FR6.1

### 驗收標準

- **AC4.2.1** Given 無 D2 報告（或無 D1 草稿），When 我切到 Secrets 步驟，Then 畫面可開（空狀態／說明），但執行控制項仍 disabled。

---

## US5.1 下載 zip 與複製目前檔

> **As a** Alex，**I want** 下載模組 zip 並複製目前預覽檔，**so that** 我能在平台外 apply（FR5）。

**優先序**：Must Have · **涵蓋**：FR5.1–FR5.4、FR8.1、FR3.3（下載摘要）

### 驗收標準

- **AC5.1.1** Given D1 成功，When 我下載 zip，Then 檔案含模組樹；平台 UI／API **無** apply／destroy 動作。
- **AC5.1.2** Given 我選中某檔，When 我按複製，Then 剪貼簿內容等於該檔預覽全文（或設計凍結之截斷規則），且可見「已複製」類文案。
- **AC5.1.3** Given 無 D1 成功草稿，When 我看下載，Then disabled＋說明。
- **AC5.1.4** Given 未選中任何檔，When 我看複製控制，Then 控制項 disabled 或點擊後可見錯誤且不覆寫剪貼簿為空白成功態。
- **AC5.1.5** Given 當前工作階段之 D2 成功報告含 ≥1 則 HIGH 或 CRITICAL，When 我發起 zip 下載，Then **先**出現摘要（可見 HIGH／CRITICAL 計數或條目清單），且在確認前**不**完成檔案下載。
- **AC5.1.6** Given 摘要已顯示，When 我確認，Then 下載完成且 zip 含模組樹；When 我取消／關閉，Then 不完成下載，工作區草稿狀態不變。
- **AC5.1.7** Given D2 成功且報告無 HIGH／CRITICAL（或無 finding），When 我下載，Then **不**出現 HIGH／CRITICAL 摘要閘即可完成下載。

**DoD**：OpenAPI／agent 工具清單靜態斷言無 apply／destroy。

---

## US5.2 D3 後下載反映改寫結果

> **As a** Fiona，**I want** D3 完成後的 zip 含改寫後 HCL，**so that** 帶走的檔案不明文留密。

**優先序**：Must Have · **涵蓋**：FR5.3、FR4.4

### 驗收標準

- **AC5.2.1** Given D3 已改寫成功，When 我下載 zip，Then 內容為改寫後草稿，抽樣不得含已改寫前的明文賦值。
- **AC5.2.2** Given D3 已完成且歷史 D2 報告仍含 HIGH／CRITICAL，When 我再次下載，Then 仍須通過與 AC5.1.5–5.1.6 相同之摘要確認（不得因已改寫而跳過）。

---

## US6.1 第一個 D HTTP 的授權雙向行為

> **As a** Fiona（與系統品質利害），**I want** 第一個落地的 D 柱 HTTP 對無權呼叫回 403、有權回契約成功態，**so that** 種子領先不會漏授權（FR7.2）。

**優先序**：Must Have · **涵蓋**：FR7.1–FR7.2、NFR4

### 驗收標準

- **AC6.1.1** Given 角色對該故事僅有不足之 action（或缺權），When 呼叫本 intent **第一個**落地的 D1／D2／D3 執行 HTTP，Then 回應 **403**。
- **AC6.1.2** Given 角色具該故事所需 `edit`，When 呼叫同一路徑（合法前置滿足或 stub），Then 回應 **2xx** 且含契約欄位集（設計凍結於 OpenAPI）。

**DoD**：同 PR 以 TestClient **成對**寫出 AC6.1.1／AC6.1.2；標明測的是 D1 或 D2 或 D3 哪一支；不得只測 happy path。

---

## US6.2 可演示端到端路徑（多角色）

> **As a** 專案利害關係人，**I want** 本機／staging 能以符合現行 RBAC 種子的帳號組合走完選圖→D1→D2→D3→下載，**so that** MVP「三者可演示」成立（Q7=A）。

**優先序**：Must Have · **涵蓋**：FR8.2

### 驗收標準

- **AC6.2.1** Given 具備 D1 `edit` 的帳號（如 Architect）與一張可用圖，When 完成選圖與 D1（LLM 可 stub），Then 檔案樹可見約定模組檔且可預覽。
- **AC6.2.2** Given 同上工作階段草稿，When 具備 D2 `edit` 的帳號（如 Security_Reviewer 或 Platform_Engineer）執行 D2，Then 報告區出現 finding 列或「無 finding」文案。
- **AC6.2.3** Given D2 已成功，When 具備 D3 `edit` 的帳號執行 D3 後由有權者下載，Then UI 可見改寫清單或「無可改寫項」，且 zip 非空。

**DoD**：引用 US2.1／US3.1／US4.1 之 PBT／突變護欄為演示前置；本故事不重複定義性質。**不**要求單一角色同時擁有 D1＋D2＋D3 `edit`（現行種子無三角 edit）。若未來改種子使 Architect 三角 edit，須走 A 規則雙向測試並同步 `schema_rbac.sql`／`DEPLOY.md`。

---

## Should Have（本輪可排後但不丟）

| ID | 故事摘要 | 來源 |
|---|---|---|
| US7.1 | 掃描引擎可配置（不預填品牌） | scope Should |

（原 US7.2 上傳失敗已升為 **US1.4** Must。）

## INVEST 備註

- Independent：步驟依賴真實存在；以「可檢視 vs 可執行」與 view／edit 分離降低假 Independent。
- Testable：產品 AC 皆 Given／When／Then 且可二元失敗；PBT／403／靜態禁令掛各故事 **DoD**，不混進元層次 Then。
- Small：標準粒度；US2.1 UI 與 generator DoD 分層避免假完成。
