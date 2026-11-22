# Requirements Analysis — 釐清問題

> Stage: requirements-analysis（Inception）· Depth: Standard · Scope: feature
> Intent: `261105-d-iac-generation`（Story D：D1＋D2＋D3）
> 作答：在每題 `[Answer]:` 後填選項字母。X 為自由填答。

## 已由上游定案、不重問

| 決策 | 來源 |
|---|---|
| 一次交付 D1＋D2＋D3；三 agent；LangGraph＋對齊 A／C Workspace | intent／scope／market |
| 平台不代 apply；使用者下載後自行 apply | intent／scope／practices Forbidden |
| 依賴序 D1 → D2 → D3；dependency-first；無硬性 deadline | scope |
| 不做：代 apply、production 憑證、商業 IaC 平台嵌入、自研掃描引擎 | scope／feasibility |
| 入口＝Workspace「生成 IaC」；步驟式工作區；草稿為主畫面 | rough-mockups |
| `backend/iac/` 領域套件；檔名用領域語彙（禁 `d1_*` 前綴） | practices Q5 |
| PBT：generator **及** scanner／redactor；決定性核心先於 LLM | practices Q5／Q6 |
| 第一個 D HTTP 消費者必測 allow／deny（2xx／403） | practices Q2 |
| D3：負向＋redaction 突變；本 intent 不新增 CI IaC scan job | practices Q4／Q3 |
| Agents 一律 `langgraph_runtime`＋OpenRouter | practices Q6 |
| 選圖互動（R-01）曾標 refined 前凍結；本輪 requirements 須釘可測行為 | rough review／approval-handoff |

## Sources

- [intent] `ideation/intent-capture/intent-statement.md`
- [scope] `ideation/scope-definition/scope-document.md`
- [feas] `ideation/feasibility/`、`approval-handoff/initiative-brief.md`
- [ux] `ideation/rough-mockups/wireframes.md`、`user-flow.md`
- [codekb] `aidlc/spaces/default/codekb/cloud/`（Story D＝Coming Soon＋種子）
- [practices] `inception/practices-discovery/team-practices.md`、`discovered-rules.md`

## Q1. 進入 IaC 工作區時，架構圖怎麼選？（凍結 R-01）

> 線框有「所選架構圖」脈絡，但沒有選圖畫面。沒有可測規則就無法寫 FR／e2e。

A. 自動帶入 Workspace **當前活躍**架構圖；若無活躍圖 → 阻擋並提示先在 Workspace 開啟／確認一張圖。多圖時仍以當前活躍為準，工作區內提供下拉可改選同專案其他已確認圖。
B. 一律跳出選圖模態（列出同專案可用圖）；即使已有活躍圖也要確認一次。
C. 僅支援「當前活躍圖」、無下拉改選；要換圖須回到 Workspace 切換後再進 IaC。
D. Not yet defined
X. Other (please specify)

[Answer]:X可以跟A3一樣選擇下構圖或上傳架構圖

## Q2. D1 產出的「可下載／可檢視草稿」最低交付形狀？

> 成功指標要求可下載或可檢視 Terraform／OpenTofu。檔案集合與格式不定，無法寫驗收。

A. 多檔模組樹（至少 `main.tf`／`variables.tf`／`outputs.tf` 或等價）＋ UI 檔案樹／HCL 預覽；下載為 **zip**；另提供「複製目前檔」；語法目標預設 **OpenTofu／Terraform 相容 HCL**（不強制二選一品牌鎖死）。
B. 單一合併 `.tf` 檔＋預覽；下載為單一檔；不強制模組拆分。
C. 只做 UI 預覽與複製，本輪不做 zip 下載。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q3. 本輪雲端供應商覆蓋？

> Brownfield「從架構圖產出」。圖可能含多雲符號；全雲支援與品質風險差很大。

A. **本輪 Must**：依圖上資源推斷供應商，優先完整支援 **AWS**；圖含 GCP／Azure 資源時仍產出對應草稿（品質可標實驗性），不得靜默丟棄。
B. **本輪 Must 僅 AWS**；圖含非 AWS 資源 → 明確列出「本輪未支援」區塊，不產出假資源。
C. 本輪 Must 等權支援 AWS＋GCP＋Azure（同一驗收深度）。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q4. D2 掃描結果如何影響「下一步／下載」？

> 不做自研引擎；本 intent 不新增 CI scan job。產品內掃描是諮詢還是閘門需定案。

A. **Advisory**：任何嚴重度都不阻擋進入 D3 或下載；HIGH／CRITICAL 必須在 UI 醒目列出，下載前顯示摘要確認。
B. **Soft gate**：存在未處理的 HIGH／CRITICAL 時，預設禁用下載，使用者可明示「仍要下載」覆寫（需記一筆稽核／日誌理由欄）。
C. **Hard gate**：有 HIGH／CRITICAL 就不可下載、不可完成流程（只能回到草稿修正後重掃）。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q5. D3「Secret Manager 整合」本輪成功形狀？

> Intent 要求不內嵌 production secrets；具體成功形狀一直留到 requirements。

A. 偵測草稿中疑似密文／密鑰賦值 → **改寫為供應商 Secret Manager 資料來源／參考語法**（依 Q3 供應商）＋ UI 列出「已改寫項目」；**不**代建立雲端 secret、**不**呼叫需帳號的 SM 寫入 API；明文不得出現在回應／log／下載物。
B. 只做偵測＋警告清單，**不改寫** HCL；使用者自行改。
C. 除改寫參考語法外，還要能對接帳號憑證把 secret **寫入**雲端 SM（建立資源）——與「不代 apply／無 production 憑證」衝突風險高，選此项須另開 ADR。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q6. 步驟狀態機：何時能進下一步／下載？

> 線框有「執行 D1」「下一步：掃描」並列，啟用條件未寫（R-02）。

A. 僅 **D1 成功完成**後可進 D2；僅 **D2 成功完成**（有報告，即使有 finding）後可進 D3；**下載**在 D1 成功後即可（zip 為當下草稿快照），D2／D3 完成後下載含掃描摘要／secrets 改寫結果。失敗步驟顯示錯誤＋重試，不得跳步。
B. 三步都必須成功後才能下載；中間不可下載。
C. 各步可自由跳轉；下載隨時可按（以當下緩衝為準）。
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q7. 「可演示路徑」的驗收深度（對齊一次交付三者）？

> Intent 未要求三者皆可演示的端到端，但 scope 將 MVP 定為三者皆有可演示路徑——需消歧。

A. Staging／本機可走完：選圖 → D1 產出可預覽／下載 → D2 顯示至少一則真實或 stub 掃描報告 → D3 完成改寫或明確「無可改寫項」→ 下載；LLM 可用 stub／錄製回應，但 **決定性核心**（generator／scanner 報告形狀／redactor）必須有自動化測試護欄。
B. 只要 UI 步驟與 API 契約在，D2／D3 可用純 mock 畫面演示，核心純函式可延後（與 practices Q6=A 衝突，不建議）。
C. 僅 D1 必須可演示；D2／D3 有 API 契約即可算交付。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q8. 無權限／無圖／D1 失敗時的產品行為？

> Edge paths 有文字無畫面（R-03）。需可測期望，不重開 RBAC 種子題。

A. **無權限**：入口隱藏或 disabled＋說明缺哪一故事權限（D1／D2／D3）。**無可用圖**：進入後全頁阻擋，CTA 回 Workspace。**D1／D2／D3 失敗**：步驟內錯誤訊息＋重試；保留上一步產物不清除；沿用 A／C Workspace 既有錯誤樣式語彙。
B. 無權限時入口仍可見，點了才 403 toast；其餘同 A。
C. 失敗時自動清空該次工作階段所有草稿。
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Follow-up — Q1 Other 與 Q6=C 消歧

> 偵測到歧義後必問。Q1 選了 Other（對齊 A3：可選既有圖或上傳）；Q6 選了自由跳步／隨時下載，需釘可測邊界，避免與 D1→D2→D3 依賴及 Q4 Advisory 下載確認打架。

### F1. Q1 Other：來源模型定案

> 你的原文：「可以跟 A3 一樣選擇架構圖或上傳架構圖」。Workspace 現況已有歷史圖下拉＋上傳 `.drawio`／`.xml`。請選最接近的可測形狀。

A. IaC 工作區提供與 Workspace／A3 **同一套**圖來源：①下拉／列表選同專案既有架構圖；②上傳／匯入 `.drawio`／`.xml`（建成 diagram 後當脈絡）。無圖可選且未上傳 → 阻擋。
B. 僅「選既有圖＋上傳」；**不**自動帶入當前活躍圖（一定要明示選或上傳）。
C. 自動帶入活躍圖 **加上** 可改選既有圖 **加上** 上傳。
D. Not yet defined
X. Other (please specify)

[Answer]: C

### F2. Q6=C：自由跳步時，空草稿能不能跑 D2／D3／下載？

> 你選「各步可自由跳轉；下載隨時可按」。若 D1 尚未成功，行為必須可測。

A. 可自由**檢視**各步驟 UI，但 **執行 D2／D3** 與 **下載 zip** 仍要求至少一份 D1 成功草稿；否則按鈕 disabled＋說明。
B. 無 D1 草稿也可按 D2／D3／下載：空狀態或 400／空 zip（另定錯誤契約）。
C. 改回近似原 Q6-A：執行路徑維持 D1→D2→D3 解鎖；下載仍可在 D1 成功後。
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

依你的回答整理如下：

- **選圖（R-01／Q1 Other＋F1）**：自動帶入活躍圖＋可改選既有圖＋上傳 `.drawio`／`.xml`；無來源則阻擋。[Q1]=X，[F1]=C
- **D1 草稿形狀**：多檔模組樹＋預覽；zip 下載＋複製目前檔；OpenTofu／Terraform 相容 HCL。[Q2]=A
- **雲端覆蓋**：Must 優先完整 AWS；GCP／Azure 仍產出（可標實驗性），不得靜默丟棄。[Q3]=A
- **D2 對下載／下一步**：Advisory；HIGH／CRITICAL 醒目列出，下載前摘要確認，不硬擋。[Q4]=A
- **D3 成功形狀**：偵測後改寫為 SM 資料來源／參考語法＋已改寫清單；不寫入雲端 SM、不代建 secret。[Q5]=A
- **步驟導覽**：可自由檢視各步；**執行 D2／D3** 與 **下載 zip** 須有 D1 成功草稿，否則 disabled。[Q6]=C，[F2]=A
- **演示深度**：端到端可走完；LLM 可 stub，決定性核心須自動化測試。[Q7]=A
- **錯誤／權限**：無權限隱藏或 disabled；無圖全頁阻擋；失敗可重試且保留上一步產物。[Q8]=A

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
