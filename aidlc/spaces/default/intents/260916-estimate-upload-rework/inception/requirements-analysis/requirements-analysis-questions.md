# Requirements Analysis 問題：C1 成本估算改版（上傳估價表）

本檔為 inception requirements-analysis 的提問與作答紀錄。問題全部紮在 reverse-engineering 的實測事實上，不重問 ideation 已定案的產品邊界（清單見 [S9]）。

## Sources

- **[S1]** `codekb/cloud/dependencies.md`：`backend/cost/` 只有一條進入邊（`backend/main.py:13`）；`backend/services/` 無任何模組反向 import `cost.*`；套件內無循環引用。
- **[S2]** `codekb/cloud/dependencies.md` 第 69-79 行：`cost_service.py:43` **跨模組引用私有函式** `services.collab_router._user_can_access_diagram` 與 `_visible_diagrams`，破壞封裝。既有成本資源的可見性完全依附架構圖的可見性。
- **[S3]** `codekb/cloud/dependencies.md` 第 89 行：RBAC seed（`backend/services/rbac_seed_data.py`）有 5 組 C1 story id——`C1`、`C1h`（每日時數）、`C1r`（估價區域）、`C1b`、`C1o`（SKU 與單價覆寫），各 11 列。程式實際使用 `C1.view` 與 `C1h`／`C1r`／`C1o` 的 `edit`；**`C1b` 已在 seed 裡但無任何程式引用**（B2 budget 遺留）。
- **[S4]** `codekb/cloud/business-overview.md`：`frontend/src/App.tsx:24` 的根路徑導向第一順位是 `if (can('C1','view')) → /cost`；`Sidebar.tsx:201` 有 `NavLink to="/cost"`。成本頁是所有具 C1 檢視權角色登入後的落地頁。
- **[S5]** `codekb/cloud/code-structure.md`：全 repo **沒有任何檔案上傳端點**；`backend/` 無 `python-multipart` 以外的上傳處理慣例可沿用（見 `technology-stack.md`）。本功能是本 repo 第一個未受信任的檔案輸入面。
- **[S6]** `codekb/cloud/dependencies.md` 第 88 行：DDL 雙軌——`backend/database.py::_ensure_cost_schema()`（329-395 行）與 `schema_rbac.sql:169-212`，加上 `DEPLOY.md:219-238` 的資料表對照表。`project.md` 的 schema↔deploy 同步是 **blocking** 規則。
- **[S7]** `codekb/cloud/dependencies.md` 第 91 行：既有 e2e 回歸 `frontend/tests/e2e/regression.spec.ts:492` 起依賴 test stack 內嵌的 `COST_PRICING_STUB=1` 與硬編碼期望值 `$86.40 / 月`。
- **[S8]** 上游未決事項：`constraint-register.md` 記「4 張表全部移除後，新功能仍需符合 ADR-0006 的稽核記錄要求，但原始檔不留存使事後回溯無據可依。稽核記錄的粒度未定。」`scope-document.md` 記「可選綁定架構圖的綁定語意仍未定義」。
- **[S9]** 已由 ideation 定案、本 stage 不重問：上傳取代自動估價（IC-2，經 AH-5 限定為「取代產生估價」）；三雲各一種主格式（FE-1）；原始檔不留存（FE-2）；完整解析結果送 LLM（FE-3）；寬鬆解析、無法辨識列仍呈現（FE-4）；估價表為獨立資源可選綁架構圖（FE-6）；至少一朵雲、不足時明示資料不足（FE-7）；LangGraph 經 OpenRouter（FE-8）；3 分鐘目標／5 分鐘上限（FE-9、SD-6）；逐項明細＋總額（SD-2）；省錢建議為核心 Must（SD-1）；agent 按需查價且不回寫明細（AH-5、AH-6）；確定性機械檢查為獨立 Must（AH-7）。

---

## Q1 — 上傳估價表的可見性

估價表是全新的獨立資源 [FE-6]，沒有既有的可見性模型可直接沿用。既有成本資料的可見性是**依附架構圖**的——`cost_service` 跨模組借用 `collab_router` 的私有函式判斷「這張圖你看不看得到」[S2]。上傳的估價表可以不綁架構圖，所以那條路徑不再必然成立。

- **A.** 只有上傳者本人看得到自己上傳的估價表
- **B.** 具 C1 檢視權的人都看得到所有人上傳的估價表
- **C.** 預設只有上傳者可見，但可明確分享給特定人（沿用架構圖的分享模型）
- **D.** 綁了架構圖的估價表沿用該圖的可見性；沒綁的只有上傳者可見
- **X.** Other (please specify)

[Answer]: C — 預設只有上傳者可見，但可明確分享給特定人（沿用架構圖的分享模型）

## Q2 — 既有五組 C1 RBAC story id 的處置

RBAC seed 有 `C1`、`C1h`、`C1r`、`C1b`、`C1o` 五組 [S3]。其中 `C1h`（每日時數）、`C1r`（估價區域）、`C1o`（SKU 與單價覆寫）對應的都是「調整自動估價參數」的能力，新架構下這三種調整都不存在了；`C1b` 本來就沒有程式引用。

- **A.** 保留 `C1`（改為上傳與檢視權），移除 `C1h`／`C1r`／`C1o`／`C1b` 四組
- **B.** 保留 `C1`，另新增一組「上傳」權限與「檢視」分開（例如管理層只能看不能傳）
- **C.** 五組全部保留不動，只是 `C1h`／`C1r`／`C1o` 變成無作用的殘留
- **D.** 保留 `C1`，移除 `C1h`／`C1r`／`C1o`，但 `C1b` 留著（未來 budget 用）
- **X.** Other (please specify)

[Answer]: A — 保留 `C1`（改為上傳與檢視權），移除 `C1h`／`C1r`／`C1o`／`C1b` 四組

## Q3 — 上傳檔案的限制

這是本 repo 第一個未受信任的檔案輸入面 [S5]，ADR-0006 的安全基線是 hard constraint。需要定義拒絕的界線——這些是會寫進需求並被測試驗證的數字。

- **A.** 單檔 5 MB、單次最多 3 檔（三朵雲各一），只接受 `.csv`／`.xlsx` 副檔名且驗證檔案內容魔數
- **B.** 單檔 10 MB、單次最多 3 檔，同上驗證
- **C.** 單檔 1 MB、單次最多 3 檔，同上驗證（官方估價表通常很小）
- **D.** 不設明確上限，交給設計階段依實測樣本決定
- **X.** Other (please specify)

[Answer]: A — 單檔 5 MB、單次最多 3 檔，只接受 `.csv`／`.xlsx` 副檔名且驗證檔案內容魔數

## Q4 — 雲別的判定方式

上傳一份 CSV，系統要知道它是 AWS 還是 GCP 的（兩者都是 CSV）。

- **A.** 使用者上傳時明確指定是哪朵雲
- **B.** 系統依檔案標頭欄位自動判定，判不出來才問使用者
- **C.** 系統自動判定，判不出來就拒絕該檔並說明原因
- **D.** 使用者指定，但系統偵測到與指定不符時提出警示
- **X.** Other (please specify)

[Answer]: B — 系統依檔案標頭欄位自動判定，判不出來才問使用者

## Q5 — 估價表的生命週期

原始檔不留存 [FE-2]，但解析後的結構化資料會存在資料庫。需要定義它活多久、能不能被取代。注意「歷史版本比較」在 scope 中列為**未承諾**（不在範圍也不在排除清單），所以這題的答案不得實質實作版本比較。

- **A.** 同一朵雲再次上傳即**覆蓋**前一次，永遠只保留最新一份；使用者可手動刪除
- **B.** 每次上傳都是新的一筆，舊的保留但預設不顯示；使用者可手動刪除
- **C.** 覆蓋式，且結構化資料設保存期限（例如 90 天後自動清除）
- **D.** 每次上傳都是新的一筆且全部保留，不提供刪除
- **X.** Other (please specify)

[Answer]: B — 每次上傳都是新的一筆，舊的保留但預設不顯示；使用者可手動刪除

## Q6 — 稽核記錄的粒度

ADR-0006 要求稽核記錄，但原始檔不留存使事後回溯無據 [S8]。既有的 `cost_audit_event` 表在退場清單中，新的記錄要記什麼是未決事項。

- **A.** 只記事件層級：誰在何時上傳了哪朵雲的估價表、解析出幾列、幾列無法辨識、何時產生了建議
- **B.** 事件層級加上解析結果的摘要（各雲總額、品項數），不記逐項明細
- **C.** 事件層級加上原始檔的雜湊值（不存檔案本身，但能證明「同一份檔案」）
- **D.** A 加 C：事件層級＋原始檔雜湊，不記金額
- **X.** Other (please specify)

[Answer]: A — 只記事件層級：誰在何時上傳了哪朵雲的估價表、解析出幾列、幾列無法辨識、何時產生了建議

## Q7 — 確定性機械檢查（CAP-9）的判準

AH-7 定案要做不依賴 LLM 的機械檢查，但判準未定。這些是會被 property-based test 驗證的規則（ADR-0006 hard constraint，解析器為純函式）。

- **A.** 三項：逐列加總 vs 表上總額（容差 1%）、單一估價表內幣別須一致、數量須為正數
- **B.** 同 A，但容差改為 0.5%
- **C.** 同 A，另加「單價 × 數量 = 小計」的逐列驗算
- **D.** 只做幣別一致與數量為正，總額對帳交給設計階段判斷可行性
- **X.** Other (please specify)

[Answer]: B — 逐列加總 vs 表上總額（容差 0.5%）、單一估價表內幣別須一致、數量須為正數

## Q8 — `/cost` 路徑與登入落地頁

`App.tsx:24` 的根導向第一順位是 `can('C1','view') → /cost` [S4]。新頁面取代舊頁面在同一批部署完成 [SD-3]，所以路徑可以沿用，但這是一個需要明確決定而非預設的事。

- **A.** 新頁面沿用 `/cost` 路徑與現有落地頁邏輯，使用者無感
- **B.** 新頁面用新路徑（例如 `/estimates`），`/cost` 導向過去，落地頁改指新路徑
- **C.** 新頁面用新路徑，且落地頁順位改為不再優先導向成本頁
- **D.** 沿用 `/cost`，但落地頁順位改為不再優先導向成本頁
- **X.** Other (please specify)

[Answer]: A — 新頁面沿用 `/cost` 路徑與現有落地頁邏輯，使用者無感

---

## 後續澄清（Step 8 矛盾偵測產物）

Step 7 對八題答案做矛盾與模糊掃描，發現三處在寫成需求前必須解決。

## F1 — Q7 的 0.5% 容差與 FE-4 的寬鬆解析互相衝突

FE-4 定案「無法辨識的列仍列出並標示」，代表部分解析是預期行為。但只要有一列沒解析出金額，逐列加總就會與表上總額差得遠超過 0.5%——總額對帳在部分解析的檔案上會**必然失敗**。這不是容差調整能解決的，是判準本身需要條件化。

- **A.** 有無法辨識列時跳過總額對帳，只報告「因 N 列無法辨識，總額無法核對」；全部解析成功時才套用 0.5% 容差
- **B.** 一律對帳，但把無法辨識列的金額視為未知並計入誤差說明，不判定為失敗
- **C.** 一律對帳且一律以 0.5% 判定，部分解析的檔案就是會顯示對帳失敗（如實反映）
- **D.** 有無法辨識列時改用寬鬆容差（例如 5%），全部解析成功時用 0.5%
- **X.** Other (please specify)

[Answer]: A — 有無法辨識列時跳過總額對帳，只報告「因 N 列無法辨識，總額無法核對」；全部解析成功時才套用 0.5% 容差

## F2 — Q5 的「舊的保留但預設不顯示」語意未定

若舊紀錄永遠無法取用，保留它就只是資料庫成長；若可以取用，那實質上就是歷史版本功能，而 scope 把「歷史版本比較」列為**未承諾**。需要一條不越界的明確界線。

- **A.** 舊紀錄僅存於資料庫供稽核，UI 完全不提供任何存取入口（本期不做任何列表或切換）
- **B.** UI 提供「顯示歷史上傳」的展開清單，可檢視單一舊版明細，但**不提供並排比較**
- **C.** 改為 Q5-A 的覆蓋式，不保留舊紀錄（撤回原答案）
- **D.** 舊紀錄保留且可檢視，並接受這實質上把歷史版本納入本期範圍（需回頭修 scope）
- **X.** Other (please specify)

[Answer]: B — UI 提供「顯示歷史上傳」的展開清單，可檢視單一舊版明細，但不提供並排比較

## F3 — Q1 的「沿用架構圖的分享模型」是新增能力

scope-document 的 CAP-1 至 CAP-9 裡**沒有分享能力**。選 C 等於在 requirements 階段新增一項 ideation 未承諾的功能。需要確認它的優先度，否則它會以 Must 的身分混進來。

- **A.** 分享列為 Should：先做「只有上傳者可見」，分享在核心流程完成後才做
- **B.** 分享列為 Must：沒有分享就不算完成，接受它擴大本期範圍
- **C.** 本期不做分享，改為 Q1-A「只有上傳者本人看得到」（撤回原答案）
- **D.** 本期不做分享，改為 Q1-B「具 C1 檢視權者皆可見」（撤回原答案）
- **X.** Other (please specify)

[Answer]: B — 分享列為 Must：沒有分享就不算完成，接受它擴大本期範圍

## F4 — 查價來源解禁（Other-escape，使用者於摘要確認時提出）

使用者於摘要確認環節提出「我想改成要呼叫三朵雲各自的 api，可以是需要帳號的」。此要求與四層既有約束衝突：`project.md` `## Never`、`team.md` Q2、ADR-0017 §3 與 §8（本 session 稍早才再次確認）、以及 `scripts/validate_repo_contract.py:226` 對 `AWS_SECRET_ACCESS_KEY` 字串的無差別攔截。經釐清後裁定如下。

**F4a 端點類別**：A — 只要**目錄價**類：AWS Price List Query API（IAM）、GCP Cloud Billing Catalog API（API key）、Azure 沿用公開 Retail Prices。實際帳單與用量類（Cost Explorer、Cost Management、Billing Export）**維持禁止**。

[Answer]: A — 只要目錄價類端點；帳單與用量類維持禁止

**F4b 憑證歸屬**：A — 平台統一一組憑證，經 GitHub Secrets → `deploy/render-env.sh` → `deploy/.env` 的既有管線注入，不採每使用者自帶。

[Answer]: A — 平台統一一組，沿用既有 GitHub Secrets 管線

---

## Consolidated Summary Confirmation

**原始八題**

- Q1 可見性：預設只有上傳者可見，可明確分享給特定人（沿用架構圖的分享模型）
- Q2 RBAC：保留 `C1` 改為上傳與檢視權，移除 `C1h`／`C1r`／`C1o`／`C1b` 四組
- Q3 上傳限制：單檔 5 MB、單次最多 3 檔，限 `.csv`／`.xlsx` 且驗證檔案內容魔數
- Q4 雲別判定：依標頭欄位自動判定，判不出來才問使用者
- Q5 生命週期：每次上傳都是新的一筆，舊的保留，可手動刪除
- Q6 稽核粒度：只記事件層級（誰、何時、哪朵雲、解析幾列、幾列無法辨識、何時產生建議），不記金額
- Q7 機械檢查：逐列加總 vs 表上總額（容差 0.5%）、單一表內幣別一致、數量為正
- Q8 路徑：新頁面沿用 `/cost`，落地頁邏輯不變，使用者無感

**後續澄清三題**

- F1 對帳條件化：有無法辨識列時**跳過**總額對帳並報告「因 N 列無法辨識，總額無法核對」；全部解析成功時才套用 0.5% 容差
- F2 歷史語意：UI 提供「顯示歷史上傳」展開清單，可檢視單一舊版明細，**不提供並排比較**
- F3 分享優先度：分享列為 **Must**，接受它擴大本期範圍

**按下確認前需要知道的後果**

- F2 與 F3 都超出 ideation 已核可的 `scope-document`。CAP-1 至 CAP-9 裡沒有分享能力，也沒有歷史清單檢視。requirements 會把它們寫成 FR 並標記為「requirements 階段新增、scope-document 尚未涵蓋」，`scope-document.md` 與 `intent-backlog.md` 需要同步補上。
- F3 選 Must 表示分享做不出來就不算交付完成。它與 SD-7 的 value-first 排序如何並存，留給 delivery-planning（OQ2）。
- **F4 推翻了四層既有約束，影響面最大。** 它使 `pricing_sdk.py` 與 `boto3` 由「刪除」改為「保留」（FR9.4 反轉）、新增整節 FR11 憑證管線重建、並要求修改 `validate_repo_contract.py` 的禁用字串比對（FR11.2）——該腳本正是本 session 稍早促使我們拆掉憑證管線的原因。需要一份新 ADR（暫編 ADR-0018）推翻 `project.md`、`team.md` 與 ADR-0017 §3／§8 三處規則，並判定是否連帶修訂 ADR-0001（OQ6、OQ7、OQ8）。


Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
