# Bolt 計畫：C1 估價表上傳

Bolt＝一次 Construction 建置切片（可含一個或多個 Unit），結束時要有可跑、可驗的完成定義。本計畫採 **value-first**：儘早讓使用者看到上傳與明細；建議路徑緊接其後。因最擔心 LangGraph／OpenRouter，**B2 與價值路徑根集合平行**去風險——不是改成全盤 risk-first。

Scope 宣告 `skeleton: off`，不做獨立 walking-skeleton 閘門。B1→B4→B5 仍形成「解析→API→可見頁」的實質薄切片。

## 序列總覽

| 順序 | Bolt ID | Units | 可與誰平行 | 預估複雜度 |
|---|---|---|---|---|
| 1 | B1 | U1 `estimate-parser` | B2、B3 | M |
| 1 | B2 | U6 `langgraph-runtime` | B1、B3 | M |
| 1 | B3 | U4 `credential-pipeline` | B1、B2 | M |
| 2 | B4 | U2 `estimate-intake-api` | —（需 B1） | L |
| 3 | B5 | **U3＋U8** | B6（若 B2 已完成） | L |
| 3 | B6 | U7 `cost-advice-agent` | B5（需 B4＋B2） | L |
| 4 | B7 | U9 `advice-presentation-ui` | —（需 B5＋B6） | M |
| 5 | B8 | U5 `pricing-lookup-port` | —（需 B3；建議 B6 後） | M |

合併目標：`ut`（squash-merge）。Deploy-on-merge：B5 是唯一允許「退場＋新頁」同時上線的邊界。

---

## B1 — 解析器

**Units:** U1 `estimate-parser`　**Walking skeleton:** 否

**Definition of Done**

- AWS CSV／Azure XLSX／GCP CSV 各至少一份樣本解析出預期品項集合
- `validate_cost_calculator_boundary.py` 指向新模組且 CI 綠
- Property-based tests 覆蓋正規化與無法辨識列標記
- `EstimateValidator` 三項檢查可單測（含「有無法辨識列則跳過對帳」）

**Confidence hypothesis:** 三雲官方匯出可穩定解析，靜默錯欄可被機械檢查抓住一部分。

**Demo:** 命令列或測試報告展示三份樣本的 `ParseResult` 與檢查結論。

---

## B2 — LangGraph 執行骨架

**Units:** U6 `langgraph-runtime`　**Walking skeleton:** 否

**Definition of Done**

- LangGraph 相依可安裝；經 OpenRouter OpenAI 相容端點完成一次成功推論
- 不移除 `claude-agent-sdk`（其他 agent 仍用）
- 可重用的圖執行／串流輔助可供 B6 接上

**Confidence hypothesis:** 新框架＋OpenRouter 在本部署拓樸下可用（回應 Q5 最大擔心）。

**Demo:** 最小腳本印出一次模型回覆。

---

## B3 — 憑證管線

**Units:** U4 `credential-pipeline`　**Walking skeleton:** 否

**Definition of Done**

- `deploy.yml`／`render-env.sh`／`docker-compose.deploy.yml` 傳遞目錄價憑證變數
- `validate_repo_contract.py` 放行變數名、仍擋真實金鑰；兩支 contract 腳本綠
- `DEPLOY.md`／`LOCAL-DEV.md` 已同步；無憑證時服務可啟動（FR11.4）

**Confidence hypothesis:** FR11.2 的 CI 閘門調整可安全完成，不擋後續查價。

**Demo:** 本機無憑證啟動成功；CI contract job 綠。

**約束:** 必須在 B5（含 U3）合併前完成，避免 FR9.8 環境變數中間態紅燈。

---

## B4 — 上傳 API

**Units:** U2 `estimate-intake-api`　**Walking skeleton:** 否

**Definition of Done**

- `POST/GET/DELETE /api/cost/v1/sets*` 與分享 `PUT .../shares` 依 contract-summary C2
- 上傳限制 5MB×3、魔數驗證、原始檔即棄
- RBAC `C1` 語意更新；移除 C1h／C1r／C1o／C1b seed
- 事件稽核（不含金額）；可觸發建議掛點（即使 B6 尚未合入也可 no-op／佇列）
- **分享 API 為 Must，本 Bolt DoD 必含**（Q4=A）

**Confidence hypothesis:** 全 repo 第一個檔案上傳面在授權與限制下可用。

**Demo:** 用 curl／httpie 上傳樣本、列出、分享給第二使用者、刪除。

---

## B5 — 退場＋明細頁（同批）

**Units:** U3 `legacy-cost-retirement` ＋ U8 `estimate-workspace-ui`　**Walking skeleton:** 否（實質端到端可見切片）

**Definition of Done**

- 舊 `/api/cost/diagrams...` 九 operations、四表、Playwright、相關測試／OpenAPI／e2e 已清或改寫
- `/cost` 可上傳、看明細、機械檢查、歷史抽屜、分享 UI、隱私徽章（refined-mockups）
- **U3 與 U8 同一合併進 `ut`**——中間不得有「只有刪沒有頁」的部署
- WCAG 2.1 AA 關鍵路徑可鍵盤操作

**Confidence hypothesis:** 使用者看得到新 C1；`/cost` 無死窗。

**Demo:** 瀏覽器走完上傳→三雲卡片→歷史→分享；舊估價 API 404。

---

## B6 — 成本建議 agent

**Units:** U7 `cost-advice-agent`　**Walking skeleton:** 否

**Definition of Done**

- LangGraph 成本建議圖；省錢建議必產出；跨雲／品質依 Should 規則處理
- Advice 持久化與狀態；SSE（heartbeat／progress／completed／timeout）符合 C3
- 斷線不取消背景工作；5 分鐘逾時後明細仍可用
- 查價未接上時不得假裝有現價

**Confidence hypothesis:** 上傳後 5 分鐘內可看到至少省錢建議（或明確失敗原因）。

**Demo:** 訂閱 SSE 看到進度與完成；`GET .../advice` 快照一致。

**平行:** 可與 B5 同時進行（需 B4＋B2 已完成）。

---

## B7 — 建議呈現 UI

**Units:** U9 `advice-presentation-ui`　**Walking skeleton:** 否

**Definition of Done**

- 建議區骨架／進度／三態；標註「由 AI 產生，請自行核對」
- 與檢查結果區視覺可分；「本期未提供」≠「產生中」

**Confidence hypothesis:** 「有明細沒建議」窗口期結束。

**Demo:** 上傳後同一頁看到建議載入至完成。

---

## B8 — 查價 Port

**Units:** U5 `pricing-lookup-port`　**Walking skeleton:** 否

**Definition of Done**

- 三雲目錄價查詢；失敗降級；輸出不進入明細寫入路徑
- 至少一筆建議文字可引用查得現價（經 B6 接上）

**Confidence hypothesis:** Should 查價可掛上且不破壞 Must 建議路徑。

**Demo:** 開啟查價後建議中出現標明「目錄價／未含折扣」的現價引用。

---

## 合併與衝突備註

- B4 與 B5 的 U2／U3 可能同改 `cost_router`：B4 先合入，B5 的 U3 再刪舊 handler（units 審閱 R-03）
- B5 與 B7 的 U8／U9 前端衝突：B7 盡量新增檔；接受必要合併
- Contract-design 四項 Minor（privacy required、advice_status none/null、SSE 時間戳、SSE 是否進 openapi）在 B4／B6／B7 functional-design 消化
