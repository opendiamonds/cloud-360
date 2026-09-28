# 決策紀錄：C1 成本估算改版（上傳估價表）— Ideation

Ideation 四站所有經人工裁決的決定，依階段排列。每筆註明來源題號，供下游逐字複驗。

## Intent Capture（2026-09-16）

| # | 決定 | 來源 |
|---|---|---|
| IC-1 | 改版動機是現行自動取價太慢或太常失敗 | Q1＝B |
| IC-2 | 上傳式估價**完全取代**自動估價，不保留雙軌 | Q2＝A |
| IC-3 | 架構師、FinOps／分析、管理層三種角色共用同一畫面，不做角色差異化 | Q3＝D／Q10＝D |
| IC-4 | agent 輸出三類建議：省錢、跨雲比較、估價品質檢查 | Q4＝D／Q11＝D |
| IC-5 | 六個 agent 模組最終全部遷至 LangGraph，不保留兩套框架 | Q5＝B |
| IC-6 | 成功指標為「從上傳到看到建議的時間」 | Q6＝A |
| IC-7 | 關鍵關係人只有「維運這個 repo 的人」 | Q7＝C |
| IC-8 | 回報機制為各階段的核可關卡，不另外產出報告 | Q8＝B |
| IC-9 | 沿用 `c1-estimate-upload-rework` 範圍（20 階段、17 道關卡） | Q9＝A |
| IC-10 | 本 intent 只遷成本 agent，其餘五個模組另開 intent | Q12＝C |

## Feasibility（2026-09-16）

| # | 決定 | 來源 |
|---|---|---|
| FE-1 | 各雲只支援一種主格式：AWS CSV、Azure XLSX、GCP CSV | Q1＝A |
| FE-2 | 原始檔不留存，解析完即丟，只存結構化資料 | Q2＝A |
| FE-3 | 送 LLM 的是完整解析結果，不裁切、不遮罩 | Q3＝A |
| FE-4 | 解析失敗採寬鬆策略：能解析的照用，其餘標「無法辨識」，不得整批拒絕 | Q4＝B |
| FE-5 | 既有 9 端點、4 張表、Playwright runner 全數移除，不留歷史資料 | Q5＝A |
| FE-6 | 上傳的估價表為獨立資源，可選擇性綁定架構圖，不得設為必要關聯 | Q6＝B |
| FE-7 | 跨雲比較門檻為至少一朵雲；不足時必須明示「資料不足」 | Q7＝B |
| FE-8 | LangGraph 經 OpenRouter 的 OpenAI 相容端點存取模型 | Q8＝A |
| FE-9 | 目標 3 分鐘內，需進度指示 | Q9＝B |
| FE-10 | 解析正確性交由 agent 的品質檢查建議把關 | Q10＝C |
| FE-11 | 可行性判定 GO，附兩項前提 | feasibility-assessment |

## Scope Definition（2026-09-16）

| # | 決定 | 來源 |
|---|---|---|
| SD-1 | 三類建議不再等權：省錢為核心 Must，跨雲比較與品質檢查降為 Should | Q1＝B |
| SD-2 | 畫面顯示逐項明細（品項、規格、數量、金額）＋ 總額 ＋ 建議 | Q2＝C |
| SD-3 | 舊端點／資料表／頁面的移除與新功能上線**同一批部署** | Q3＝A |
| SD-4 | M2 規則衝突的 ADR 在 scope-definition 結束後立刻處理 | Q4＝A |
| SD-5 | Won't Have 只有「定期重新估價／排程重跑」一項；匯出、歷史版本比較、回寫架構圖三項記為**未承諾** | Q5＝D |
| SD-6 | 3 分鐘為目標值，實測 5 分鐘內可接受 | Q6＝B |
| SD-7 | 交付排序偏好 value-first | Q7＝B |
| SD-8 | 不指名代表，由 Danniel 一人代表三種角色驗收 | Q8＝A |

**SD-1 的性質**：它修改了 IC-4 已核可的「三類全必備、不分先後」。這是 intent-capture 審查 R-01 明確指派 scope-definition 處理的收斂（required action 逐字要求「若存有任何優先順序共識，應在 scope-definition 明確登錄」），不是下游擅自縮小範圍。依團隊規則，上游 `intent-statement.md` 不回改，以 scope-definition 問題檔的確認紀錄向下游傳遞。

## ADR（2026-09-16，scope-definition 與 approval-handoff 之間）

| # | 決定 | 來源 |
|---|---|---|
| ADR-0017-1 | `pricing_client` 的存在強制要求**廢止** | ADR-0017 §1 |
| ADR-0017-2 | 三層形狀（router → service → 純函式核心）**保留**；純函式層由 `cost_calculator` 改錨至估價表解析器，ADR-0006 的 PBT hard constraint 原樣移轉 | §2 |
| ADR-0017-3 | 計價 API 禁令**保留並升格為無條件**：不得有任何自動取價路徑，不論該端點是否需要憑證 | §3 |
| ADR-0017-4 | `project.md` 三處、`team.md` 兩處就地加註限定，原文保留不刪 | §7 |

## Approval & Handoff（2026-09-16）

| # | 決定 | 來源 |
|---|---|---|
| AH-1 | 接受 RISK-02、RISK-03、RISK-04；RISK-01 額外要求 inception 補上不依賴 LLM 的機械檢查設計 | Q1＝B |
| AH-2 | 兩人以上可平行，第一梯次三項技術工作可同時起跑 | Q2＝B |
| AH-3 | `deploy/render-env.sh` 的 repo contract 紅燈在進 inception 之前清掉 | Q3＝A |
| AH-4 | 不重跑 scope-definition，記明漂移來源與判定理由 | Q4＝A |
| AH-5 | **保留三朵雲的官網查價功能**，作為 agent 產生建議時的按需工具 | 追問（自由作答）|
| AH-6 | 查得的價格**只寫進建議文字**，不回寫明細、不新增現價欄位 | 追問＝A |
| AH-7 | AH-1 的機械檢查**維持獨立義務**，另加一層不需 SKU 對應的確定性檢查 | 追問＝A |
| AH-8 | 以修訂 ADR-0017（新增 §8）並就地更新受影響產出的方式收斂，不重跑 feasibility／scope-definition | 追問＝A |
| AH-9 | `deploy/render-env.sh` 的修法採「移除 AWS 帳號憑證傳遞」，非迴避字串、非放寬檢查 | Q3＝A ＋ 事實查證 |
| AH-10 | Ideation → Inception，建議 GO | initiative-brief |

### AH-5 的性質與代價

AH-5 推翻了 IC-2（完全取代）、FE-5（`pricing_client` 全數移除）與 ADR-0017 §1／§3 的前提。使用者原始說法為「三朵雲想保留查詢官網 API 的功能」，經兩輪追問界定為：**agent 產生建議時按需查價**，不是系統例行核對、不是雙軌估價、不含 Playwright。

反轉的範圍已被壓到最小，但代價是實在的：

1. **ADR-0017 在建立後 25 分鐘內自我修訂。** §8 撤回了 §1 的 `pricing_client` 廢止與 §3 的「不得新增任何自動取價路徑」。§1 與 §3 已加註「不得單獨引用」。
2. **SKU 對應回到範圍內**（RISK-07）。這是舊自動估價最常失敗的環節。關鍵差異是新架構下查價失敗非阻塞——對不到就是該筆「無法查證」，明細與建議照常產出。
3. **新增一類系統性誤判**（RISK-08）。官方目錄價是未折扣定價，上傳的估價表可能含 CUD／RI／Savings Plan。兩者本就不該相等，把它們當同一種東西比較會把對的報成錯的。AH-6 禁止回寫明細，擋掉了最壞後果，但 agent 的建議文字仍可能誤述。

### AH-7 為什麼是獨立義務而不是被 AH-5 取代

查價看起來像是更強的正確性防線，但它由 LLM 決定查什麼——同一份估價表跑兩次可能查不同品項。機械檢查的價值恰恰在於「每次都跑、結果可複現」。兩者互補，下游不得合併處理。

### AH-9 的查證過程

原本判定為「與本 intent 無關的既有違規」，查證後修正：`deploy/render-env.sh` 把 AWS 帳號憑證寫進 `deploy/.env` 是 commit `7de3068`（C1 功能）加入的，而 ADR-0001 明列 production credentials 與 environment-specific secrets 不在本 repo 範圍、`project.md` 2026-08-19 的 C1 規則也只准公開免帳號端點。**這從一開始就違規**，舊版 validator 只掃 diff 所以沒抓到，升級後掃全部追蹤檔才暴露。

因此處置不是迴避字串或放寬檢查，而是移除整條憑證管線：`render-env.sh` 不再寫出、`docker-compose.deploy.yml` 不再傳遞、`.github/workflows/deploy.yml` 不再從 GitHub Secrets 讀取、`COST_PRICING_USE_SDK` 由 `auto` 釘為 `0`。AWS 查價改走公開 Bulk Price List（較慢，不需憑證）。`DEPLOY.md` 與 `LOCAL-DEV.md` 已同步（`CLAUDE.md` 的 blocking 規則）。兩支 contract 腳本現為綠燈。

順帶發現但**未處理**：`DEPLOY.md` 曾含 `AWS_SECRET_ACCESS_KEY=...` 的範例行，比 `render-env.sh` 危險得多，卻不在 validator 的掃描範圍內（`DEPLOY.md` 不在 `REQUIRED_FILES`）。該範例行已於本次一併移除，但**掃描範圍的漏洞仍在**——`validate_no_obvious_secrets()` 只掃 contract files，不掃全部追蹤檔。這是獨立於本 intent 的既有缺陷。

**AH-1 的性質**：它在 SD-1 之上加回一層保護。SD-1 把品質檢查降為 Should（可以不交付），AH-1 要求另外設計一套機械檢查。兩者不衝突——前者是 agent 用自然語言指出可疑數字，後者是程式判定總額對帳、幣別一致性、數量合理範圍。這是 ideation 產生的**新設計義務**，已列入 initiative-brief 的「帶進 Inception 的義務」表並指派 functional-design。

## 完整性檢查的兩項標記與處置

**`scope-definition` 標記為 drifted。** 引擎於 approval-handoff 進入時回報：`Completed stage results have drifted; routing is continuing in advisory mode. Suggested redo: /aidlc --stage scope-definition.`

漂移來源可精確指出：ADR-0017 完成後，回頭把「已解決」狀態標進 `scope-document.md` 的前置依賴表與 `intent-backlog.md` 的 PU-10 列。這兩處編輯**只改狀態註記，未動任何決策、答案或範圍**。引擎比對的是產出指紋，不分辨語意，因此判定為漂移。

處置為不重跑（AH-4）。重跑會把八題重問一次，換來一組相同的答案，並在稽核紀錄上多出一輪與決策無關的往返。此判定由人工裁決，非 conductor 自行決定。

**四站標記為 untracked**：`workspace-scaffold`、`workspace-detection`、`state-init`、`feasibility`。原因是這四站完成時未經 `orchestrate report` 留下完成收據——前三站由 `intent-create` 直接建立，`feasibility` 則是由 conductor 手動編輯 `aidlc-state.md` 推進的操作失誤。`scope-definition` 起已改走正規 `report` 路徑。標記為 advisory，不擋路由，但代表這四站在稽核紀錄上缺一張完成收據。

## Assumptions & Open Questions

- [assumption] 本紀錄的每一筆都可回溯到對應問題檔的 `[Answer]` 行。若下游發現某筆引用不到具體選項，該筆即應視為未定案而非已決定。
- [open] IC-4 與 SD-1 在字面上並存於不同 artifact（前者說三類全必備，後者說有優先序）。已在 SD-1 註明性質，但下游若只讀 `intent-statement.md` 仍會讀到舊版表述。這是「上游不回改」規則的已知代價。
