# Intent Backlog — A1 混合雲架構繪圖

<!-- Stage: scope-definition（Ideation 1.4）· 來源標籤定義見 scope-definition-questions.md 的 ## Sources。
     Proto-Units 為 inception units-generation 的前身：以能力為單位，依 Dependency-first 交付順序排列。 -->

## 上游輸入

- 能力集與範圍邊界承襲本階段之 `scope-document.md`，其上游為 **intent-statement**、**feasibility-assessment** 與 **constraint-register** [intent:Q1] [feas:Q1] [feas:Q2]。
- market-research 已依條件判定跳過，無市場面待辦。

## Proto-Units（依 Dependency-first 順位排列 [Q2]）

### PU-1 後端 Prompt 與 Tool 參數擴充 — Must

- **價值**：使 LangGraph 架構設計 Agent 具備混合雲之領域知識與呼叫介面，為後續幾何產圖之唯一輸入源頭 [code:C3]。
- **內容**：
  1. 擴充 `backend/services/design_agent.py` 中的 `draw_architecture_diagram` tool，將 `provider` 參數容許範圍納入 `"compound"`。
  2. 更新 `backend/prompts/cloud_architecture_system_prompt.md`，增加混合雲 3-Cloud 拓樸指引與 JSON 範例，明確規範 AWS、Azure、GCP 三個獨立頂層容器之輸出格式。
- **依賴**：無（技術依賴鏈頭）。
- **DoD 要點**：LLM 能夠正確辨識多雲需求並輸出帶有 `provider = "compound"` 及三雲 groups 的結構化 tool call。
- **順位理由**：Dependency-first 第 1 順位 [Q2]。

### PU-2 diagram_builder Hub-and-Spoke 幾何與三雲群組組裝 — Must

- **價值**：核心幾何引擎，使單一 mxGraphModel XML 能同時容納三個頂層雲端容器，且空間互不衝突 [feas:Q1] [code:C1]。
- **內容**：
  1. 在 `backend/services/diagram_builder.py` 實作 Hub-and-Spoke 空間佈局演算法，以核心雲居中、另外兩雲分列兩翼，動態計算 X/Y 偏移量與群組邊界。
  2. 確保 `GROUP_STYLES` 既有之 AWS、Azure、GCP 群組樣式能同時寫入單一 XML 之 root 節點中。
- **依賴**：PU-1（需依賴 tool 產出的 groups 結構）。
- **DoD 要點**：產出的 XML 經解析後包含三個合法頂層雲端容器，子網路與各雲內部元件階層正確。
- **順位理由**：Dependency-first 第 2 順位 [Q2]。

### PU-3 n8n Webhook Compound 上行整合與圖示查詢 — Must

- **價值**：打通 n8n 外部服務契約，確保向 n8n 發送之上行精確符合 `provider = "compound"` 要求，並穩定取得圖示 [desc] [feas:Q2] [code:C2]。
- **內容**：
  1. 修改 `fetch_icon_from_n8n` 呼叫點，在混合雲情境下向 n8n 發送 `json={"service": search_name, "provider": "compound"}`。
  2. 維持並驗證非 200 或圖示缺失時的灰底 SVG fallback 保護機制，避免單一圖示缺漏中斷整張架構圖渲染。
- **依賴**：PU-2（節點圖示組裝入 XML）。
- **DoD 要點**：httpx POST 請求之 JSON payload 驗證包含 `provider: "compound"`；圖示回傳後正確 base64 編碼嵌入 mxCell。
- **順位理由**：Dependency-first 第 3 順位 [Q2]。

### PU-4 跨雲連線避障與協議標籤渲染 — Must

- **價值**：清晰呈現跨雲服務之間的互動網路拓樸與通訊管道（如 DirectConnect、VPN、HTTPS）[feas:Q3]。
- **內容**：
  1. 強化連線路徑計算，確保跨越不同 Cloud 頂層邊界的連線不會被相鄰容器 AABB 誤判為無效障礙物。
  2. 支援在 mxCell edge 上渲染連線標籤文字（label），顯示如 "HTTPS / VPN / REST API" 等通訊協定。
- **依賴**：PU-2（需有三雲節點座標方可計算跨雲連線）。
- **DoD 要點**：跨雲連線端點正確錨定兩側不同雲之 node id，連線平順無折線破圖。
- **順位理由**：Dependency-first 第 4 順位 [Q2]。

### PU-5 前端選單新增與對話模式串接 — Must

- **價值**：提供直覺之使用者操作介面與對話體驗，使架構師可主動點選或對話觸發混合雲繪圖 [feas:Q4]。
- **內容**：
  1. 於前端畫布頁面（如 `WorkspacePage`）之 Provider 選單中新增「混合雲 (Compound)」選項。
  2. 點選後向後端傳遞 compound 參數；同時在對話中支援多雲意圖識別提示。
- **依賴**：PU-1、PU-2（後端支援 compound 接收與生成）。
- **DoD 要點**：使用者點選選單或對話後，畫布能順暢載入並展示混合雲架構圖。
- **順位理由**：Dependency-first 第 5 順位 [Q2]。

### PU-6 專屬單元測試集 test_diagram_builder_compound.py — Must

- **價值**：遵循專案護欄，為混合雲核心幾何與通訊提供可持續回歸之自動化防護網 [feas:Q5] [memory:M2]。
- **內容**：
  1. 建立 `backend/tests/test_diagram_builder_compound.py`。
  2. 測試案例包含：(a) Hub-and-Spoke 三雲群組座標計算、(b) 跨雲 edges 與協議標籤組裝、(c) mock n8n 通訊 payload 驗證、(d) 混合雲 XML 語法驗證。
- **依賴**：PU-2、PU-3、PU-4。
- **DoD 要點**：測試全數通過 `python -m unittest discover -s tests`，零 warning、零失敗。
- **順位理由**：Dependency-first 第 6 順位 [Q2]。

### PU-7 畫布 Fit to Window 最佳縮放體驗 — Could

- **價值**：混合雲畫布較單一雲為寬，自動縮放可提升架構師首屏瀏覽體驗 [Q4]。
- **內容**：畫布繪製完成後，前端呼叫 mxGraph 之 `fitWindow()` 或自動計算縮放比率，讓三雲全景完整呈現在螢幕可視區內。
- **依賴**：PU-5。
- **DoD 要點**：載入後自動置中並適度縮放，不裁切邊界。
- **順位理由**：Could Have 優先級，列為體驗優化。

## Assumptions & Open Questions

None.
