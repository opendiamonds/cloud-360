# Scope Definition 問題：C1 成本估算改版（上傳估價表）

本檔為 scope-definition 階段的提問與作答紀錄。上游 intent-capture 與 feasibility 已定案的事項不重問，清單見 [S7]。

## Sources

出題前的唯讀查證結果，供題幹與選項引用。

- **[S1]** `backend/cost/cost_router.py`：9 個端點全部掛在 `/diagrams` 之下（`GET /diagrams`、`GET /diagrams/{id}`、`GET /diagrams/{id}/calculator-export/xlsx`、`GET /diagrams/{id}/calculator-export/csv`、`PUT /diagrams/{id}/region`、`PUT /diagrams/{id}/lines/{mxcell_id}/hours`、`PUT .../sku`、`PUT .../override`、`GET /diagrams/{id}/audit`）。
- **[S2]** `backend/models.py`：4 張成本相關資料表——`diagram_cost`（191）、`diagram_cost_line`（208）、`pricing_cache`（227）、`cost_audit_event`（239）。
- **[S3]** `backend/cost/` 目錄現有 30 個檔案，含兩支 Playwright runner（`azure_calculator_runner.py`、`gcp_calculator_runner.py`）、`pricing_client.py`、`sku_mapper.py`、`price_cache.py` 與 8 份 YAML 對照表。
- **[S4]** `frontend/src/pages/CostPage.tsx` 為 964 行；`frontend/src/App.tsx` 的路由表有 `/cost`（第 73 行）；`frontend/src/components/Sidebar.tsx` 的「成本 → 預估成本」入口由 `can('C1','view')` 控制（第 19、184、202 行）。
- **[S5]** `aidlc/spaces/default/memory/org.md` `## Deployment`：deploy-on-merge，合併進 `ut` 即部署至 staging。因此每個 Bolt 邊界都是一次真實部署，破壞性契約變更與其消費端之間存在「同批次」約束。
- **[S6]** intent-capture 審查留下三項待人工處置：R-01（三類建議全必備、無優先序的執行風險）、R-03（成功指標缺量級錨點）、R-04（三種使用者角色未指名驗收代表）。feasibility 的 RAID log 留下 ISSUE-01（`project.md` 規則 M2 與「完全取代」衝突，需 ADR，阻擋 construction）。
- **[S7]** 已由上游定案、本階段不重問：完全取代自動估價（intent-capture Q2=A）；三類建議皆必備、無優先序（Q4=D／Q11=D）；三角色共用同一畫面（Q3=D／Q10=D）；本 intent 只遷成本 agent 到 LangGraph（Q5=B／Q12=C）；成功指標為時間（Q6=A）；沿用 `c1-estimate-upload-rework` 範圍（Q9=A）；各雲一種主格式（feasibility Q1=A）；原始檔不留存（Q2=A）；完整解析結果送 LLM（Q3=A）；解析失敗寬鬆處理並標記「無法辨識」（Q4=B）；9 端點／4 表／Playwright runner 全數移除（Q5=A）；估價表為獨立資源、可選綁架構圖（Q6=B）；至少一朵雲即可、不足時標示資料不足（Q7=B）；LangGraph 走 OpenRouter 的 OpenAI 相容端點（Q8=A）；3 分鐘目標值加進度指示（Q9=B）；解析正確性交由 agent 品質檢查（Q10=C）。

---

## Q1 — 三類建議的退讓順序

三類建議（省錢、跨雲比較、品質檢查）目前全部是 Must 且無優先序 [S7]。審查指出這在執行面沒有備援：若其中一類在實作時明顯拖累交付，沒有預先定義的取捨依據 [S6]。

- **A.** 維持三類全 Must，不設退讓——任一類做不到，整個功能就不上線
- **B.** 省錢建議為核心 Must，跨雲比較與品質檢查可降為 Should
- **C.** 品質檢查為核心 Must（它是解析正確性的唯一防線），另兩類可降為 Should
- **D.** 三類都維持 Must，但允許降級呈現：先顯示已產生的建議，其餘標示「產生中」

[Answer]: B <!-- 2026-09-16T06:01Z -->

## Q2 — 畫面要顯示到什麼粒度

決定 UI 工作量與後端要持久化的結構化資料深度。無論選哪一個，「無法辨識」的列都必須在畫面上可見（已由 feasibility Q4 定案）。

- **A.** 只顯示三朵雲各自的總額，加上建議
- **B.** 總額 ＋ 依服務類別彙總（如運算／儲存／網路），加上建議
- **C.** 逐項明細（品項、規格、數量、金額）＋ 總額，加上建議

[Answer]: C <!-- 2026-09-16T06:01Z -->

## Q3 — 退場與新功能的交付批次

既有 9 個端點、4 張表、`/cost` 頁面要整組移除 [S1][S2][S4]，而本專案是 deploy-on-merge：每個 Bolt 邊界都是一次真實部署 [S5]。

- **A.** 同一批：移除舊端點與頁面、上線新功能在同一次部署完成
- **B.** 先上線新功能（新舊並存一段時間），確認可用後再移除舊的
- **C.** 先移除舊的（`/cost` 暫時下架或顯示維護中），再分批上線新的

[Answer]: A <!-- 2026-09-16T06:01Z -->

## Q4 — M2 規則衝突的 ADR 產出時點

`project.md` 規則 M2 要求成本功能域保留 `pricing_client` 三層架構，而本改版要移除的正是那條路徑。需要一份 ADR 才能解除，否則 construction 會被擋 [S6]。

- **A.** 現在就開——scope-definition 結束後立刻處理，不拖到 inception
- **B.** inception 早期（requirements-analysis 之前）
- **C.** delivery-planning（inception 末端、進 construction 之前）
- **D.** 另開一個獨立的小 intent 專門收斂規則層，不佔用本 intent 的階段

[Answer]: A <!-- 2026-09-16T06:01Z -->

## Q5 — 明確排除（Won't Have）

可複選。選中者寫進 scope 文件的排除清單；未選中者記為「未承諾」，不推定未來去向。

- **A.** 建議結果匯出（PDF／CSV）
- **B.** 歷史估價的版本比較（這次 vs 上次）
- **C.** 建議的自動套用（依建議回寫架構圖）
- **D.** 定期重新估價／排程重跑

[Answer]: D（僅此一項；A／B／C 未選中，記為未承諾） <!-- 2026-09-16T06:33Z -->

## Q6 — 時間指標的量級錨點

feasibility 定了 3 分鐘為目標值，但未經實測，瓶頸完全在 LLM 推論 [S7]。審查建議在本階段取得一個方向性量級，避免 nfr-requirements 無錨點可用 [S6]。

- **A.** 3 分鐘是硬上限——做不到就要改設計（例如分批出建議、串流回傳）
- **B.** 3 分鐘是目標，實測 5 分鐘內可接受
- **C.** 只要有進度指示，10 分鐘內都可接受
- **D.** 不設上限，以「比舊的自動估價快」為準

[Answer]: B <!-- 2026-09-16T06:33Z -->

## Q7 — 交付排序偏好

決定 intent-backlog 的排序依據，以及下游 delivery-planning 的 Bolt 序列起點。

- **A.** risk-first：先做 LangGraph ＋ LLM 建議這段最不確定的
- **B.** value-first：先做上傳與明細顯示，建議功能後補
- **C.** dependency-first：依技術相依順序，不額外加權
- **D.** 先清場：先移除舊的整套，再從零建新的

[Answer]: B <!-- 2026-09-16T06:33Z -->

## Q8 — 驗收代表

三種使用者角色（架構師、FinOps／分析、管理層）目前都不在關鍵關係人清單內 [S6]，inception 的使用者故事會缺驗收人。

- **A.** 不指名，由 Danniel 一人代表三種角色驗收
- **B.** 三種角色各指名一位代表
- **C.** 只指名 FinOps／分析角色代表（對數字最敏感的那一個）
- **D.** 留到 inception 的 user-stories 階段再決定

[Answer]: A <!-- 2026-09-16T06:33Z -->

---

## Consolidated Summary Confirmation

- **Q1**：三類建議不再等權。省錢建議為核心 Must；跨雲比較與估價品質檢查降為 Should。
- **Q2**：畫面顯示逐項明細（品項、規格、數量、金額）＋ 總額 ＋ 建議。
- **Q3**：舊的 9 端點／4 張表／`/cost` 頁面移除與新功能上線在同一次部署完成。
- **Q4**：M2 規則衝突的 ADR 在本 stage 結束後立刻處理，不拖到 inception。
- **Q5**：Won't Have 只有一項——定期重新估價／排程重跑。匯出、歷史版本比較、建議自動套用回寫架構圖三項**未選中**，依規則記為「未承諾」：不在本次範圍、不在排除清單、不推定未來去向。
- **Q6**：3 分鐘為目標值，實測 5 分鐘內可接受。
- **Q7**：value-first——先做上傳與明細顯示，建議功能後補。
- **Q8**：不指名代表，由 Danniel 一人代表三種角色驗收。

**需要在按下確認前看到的兩個後果：**

1. **Q1 改變了上游已核可的產品邊界。** intent-capture 的 Q4／Q11 定案是「三類建議全必備、不分先後」，本題答案把它改成有優先序。這是 intent-capture 審查 R-01 明確指派本 stage 處理的事項，屬於審查要求的收斂而非擅自縮小範圍。依團隊規則，上游 `intent-statement.md` 不回改，以本檔的確認紀錄為準向下游傳遞。

2. **Q3 ＋ Q7 合起來會產生一段「比現在更差」的期間。** Q3 要求舊估價路徑與新功能同批部署，Q7 要求先做上傳與明細、建議後補。兩者合起來的結果是：第一次部署之後，自動估價已經移除、上傳與明細已經可用，但**還沒有任何建議**——而「讓 agent 給建議」正是這次改版的目的。這個窗口期有多長取決於第二批的交付速度。兩個答案本身都成立，是組合起來才浮現的後果，故不另開題，在此揭露。

[Answer]: Looks correct <!-- 2026-09-16T06:49Z -->
