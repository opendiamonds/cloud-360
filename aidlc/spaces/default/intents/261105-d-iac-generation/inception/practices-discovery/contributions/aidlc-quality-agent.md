**Collaborator:** aidlc-quality-agent

## Contribution

盲評範圍：測試姿勢、覆蓋率工具、CI 品質閘門、測試／程式形狀，以及訪談必須解開的缺口。未讀 sibling `contributions/`。本輪複驗 HEAD `0bffc82`：`backend/tests/test_*.py` **41** 檔、`@given` **12** 檔／**19** 處、`test_rbac.py` 對 D1／D2／D3 **0** 命中、無 `test_*iac*`／`test_*terraform*`、`.github/workflows/` 對 checkov／tfsec／gitleaks／trivy **0** 命中、無 `.coveragerc`／coverage 依賴、前端僅 `frontend/tests/e2e/`（Playwright；無 Story D／IaC case）。

### 已定案、訪談不得重問

| 項目 | 為何已定案 | Story D 的正確用法 |
|---|---|---|
| 規則 A／B／C（與「不採前端 unit 框架」） | `team.md` Q4；本輪草稿正確標為一般效力 | 改 D 種子 → A；新／改 `/api/iac*`（或等價）→ B；真 UI 取代 Coming Soon → C。**不**另造平行「必須有 D 測試」條款 |
| ADR-0006 PBT → **IaC generator** | `project.md ## Testing Posture` hard constraint | 模組 ABSENT ⇒ N/A（非豁免）。**第一個 generator 純函式核心落地的同一 PR 必須有 Hypothesis `@given`，不得只交 example-based**。工具鏈（Hypothesis）與「要不要 PBT」皆不進訪談 |
| `tcms-test-cases`＋結構性盲區 | `project.md ## Mandated`；`TESTING.md`／`test-case-authoring.md` | Construction blocking。三個 LangGraph agents 的 **LLM 對話路徑**進「只能手動」；可決定性核心（generator／scanner 報告形狀／redactor）進自動化並做突變驗證 |
| 80% line coverage | `org.md` 宣告；`team.md` 拒絕在本層弱化 | 仍無法量測、無法強制。增量門檻維持 A／B／C；本輪**不**導入 coverage gate、不重開承載機制題 |
| backend `unittest`＋`hypothesis`（非 pytest）；`ui-regression` 真閘門 | 既成事實 | 新測檔放 `backend/tests/test_*.py`；e2e 寫進 `frontend/tests/e2e/` 才會擋 PR。不得把付費 LLM 打進 `ui-regression` |
| 平台不 apply／high-risk gate | `org.md`／`project.md`／草稿 Deployment | 產碼／掃描 ≠ apply。測試不得假設 staging 會對雲端執行 apply |
| 矩陣領先實作 ≠ 已有能力 | `project.md` Corrections `reverse-engineering:c9`；草稿 Mandated | 測試／測案／文件不得把 D 種子或 Coming Soon stub 當成已有 router／頁／掃描能力 |

### 草稿寫對的現況（品質視角核可）

- **Story D 測試是 ABSENT，不是覆蓋率不足**：無 IaC router／OpenAPI 條目可掛 TestClient；無 D 柱 e2e；`test_rbac.py` 未覆蓋 D 故事 id。應記 greenfield 缺口，不可寫成「補幾個 case 就好」。
- **A／B／C 一般效力已寫清、且與 C1 先例對齊**：草稿未把「要不要 A／B／C」當新規則——正確。
- **I2（第一個 D HTTP 消費者 × 種子未改）是真缺口**：D 種子已在 `rbac_seed_data.py`，與當年 C1 同形。規則 A 只在「預設值變更」觸發；規則 B 字母只要求 status＋欄位集——可只測 happy path 而漏 403。C1 已用 Q3 補洞；D 柱尚無對等定案。**這是本輪 Testing Posture 訪談的第一優先。**
- **I3／I4 不預選工具**：CI 無 IaC／secret scan job；contract secret 掃描仍只看 `contract_files()`——與 D3 交叉會放大風險面。工具名（checkov／tfsec／gitleaks）不得未訪談就寫進 Mandated。
- **I6 分桶方向正確**：三 agents ≠ 三條全手動；必須先釘「非 LLM 可測核心」再把剩餘丟 TCMS。
- **`discovered-rules.md` 克制**：未發明 Story D 專屬 ALWAYS／NEVER；PBT／三層／A／B／C 皆引用既有規則——promote 友善。
- **CI 對未來 D 端點的實際閘門**：`unittest discover`＋OpenAPI drift＋（有寫才擋的）`ui-regression`。`tsc -b` 仍不保護手寫 interface；不能當成 D schema 護欄。

### 對草稿的挑戰

**1. 測試檔數寫「約 43」會在 promote 時污染基線。**

本輪 `ls backend/tests/test_*.py`＝**41**（與 `code-quality-assessment.md` 一致）。「約 43」多半把 `helpers.py`／`__init__.py` 算進去。`@given`「12 檔／約 19 處」與複驗一致，應保留精確數字。Final Integration 寫入 `team.md` 時必須用 **41**，不得帶約數。

**2. `Methodology: custom`＋Ordering 是 Lead 草稿標註，不可無訪談 promote。**

`evidence.md` 已自承非訪談定案。若整合時原樣進 `team.md`，會把未 Affirm 的方法論標籤變成團隊規則。處置：訪談明示採用／改標 `test-after`／刪除該標註三選一；**不得 silently promote。** Ordering 正文（同 PR 齊備 A／B／C 與 generator PBT、不得留到後續 PR）與 ADR-0006 相容，可在核可後保留為執行說明。

**3. I5 不得把「D2／D3 也要 PBT」當成與 ADR-0006 等價的選項。**

ADR-0006 點名落點是 **IaC generator**（另加 cost calculator、agent routing），**不含** scanner／secret-handler。訪談應框成：A＝僅 generator 強制 PBT（執行既有 ADR）；B＝另以新 ADR／本輪 Affirm 把 scanner 或 redactor 升格為 PBT 核心。把「三核心皆 PBT」寫成好像已有 ADR 撐腰，會在未改 `project.md` 的情況下擴大 hard constraint。

**4. codekb 第 7 點過度宣稱必須在 evidence 打叉。**

`code-quality-assessment.md` 寫「首個 D 端點的測試義務：allow／deny 雙向 TestClient（team.md Q3 定案）」——**錯誤**。Q3 原文鎖定 C1／`/api/cost*`。Lead 草稿的 I2 正確保留待訪談，但 `evidence.md` 應明示「codekb 此句不可當已定案」，否則訪談者會略過 I2。

**5. I2 選項 B（僅 D1）低估 D2／D3 的同形風險。**

D2／D3 同樣矩陣領先、角色集合不同（含 `Security_Reviewer`）。若第一個落地的是 D2 掃描 API 而選 B，403 路徑仍可缺席。建議選項改寫為：A＝D1／D2／D3 任一故事的第一個 HTTP 消費者皆比照 C1 Q3；B＝維持一般 A／B／C、不另立交叉規則。不要保留「只有產碼入口才要」的中間項當預設吸引力選項——除非訪談明確接受不對稱風險。

**6. I7 若進 practices 訪談，不得重問「C 要不要適用」。**

真 UI／資料形狀變更觸發規則 C 已定案。本站最多問入口落點是否本輪就要測（或留給設計）；**不可**出現「先做 stub CTA、暫緩 e2e」當合法選項——那等於局部廢掉 C。

### 訪談必須問（品質透鏡）

Brownfield re-run：只問草稿＋盲評建不成的判斷。建議四題；其餘不要。

1. **第一個 D HTTP 消費者的授權測試（種子多半不變）**  
   A：D1／D2／D3 **任一**故事的第一個 HTTP 消費者落地時，即使 seed 未改，仍強制 allow／deny 雙向 TestClient（有權 → 2xx、無權 → 403），比照 C1 Q3。  
   B：不另立交叉規則；僅在改 `role_permissions` 預設時走 A，新端點只滿足 B 字母（status＋欄位集）。  
   （解的是 A／B 交叉空洞，不是重問 A／B／C 存廢。）

2. **D2 靜態掃描的自動化落點**  
   A：本 intent 只要求 unittest 內測「編排＋報告形狀」（example-based；工具／CLI 可 stub）；不新增 CI scan job。  
   B：另增 CI job（blocking 或 report-only 於同題子選），工具名由訪談／後續 ADR 點名——**本站不得預填 checkov／tfsec**。  
   Scanner 是否 PBT：預設否（見挑戰 3）；若選升格，必須明說是新 Affirm／新 ADR。

3. **D3 Secret 測試義務與 contract 掃描缺口**  
   A：D3 落地時強制負向測試——回應／log／artifact 不得出現明文 secret；redaction 路徑須突變驗證；contract secret 掃描作用域擴大另排（不阻塞 D3 負向測試）。  
   B：D3 僅 example-based happy path；掃描作用域擴大與負向測試皆留待補清單。  
   品質建議偏向 A：既有「宣稱＞機制」落差在 D3 會從文件債變成可洩漏路徑。

4. **三 agents 的測案分桶下限（非 LLM）**  
   A：每個故事必須先有可離線斷言的純函式／決定性核心（D1 generator 含 PBT；D2 報告形狀；D3 redactor），LLM 編排僅手動／TCMS。  
   B：允許首個 Bolt 以 agent 編排為主、純函式核心延後——**品質反對**：與 ADR-0006（D1）及「結構性盲區不得假裝已覆蓋」衝突。  
   若選 A，不必再問「要不要 Hypothesis」。

**條件題（scope／設計未釘則刪）：** Walking Skeleton 本輪若開 `on`，完成定義仍須可測（至少一條非 LLM 的 `TestClient` 或純函式斷言）——屬 skeleton 題的附帶約束，不另造測試規則。`Methodology`／Ordering 標籤確認可併入綜合確認，不單獨佔一題。

### 明確不要問

- 要不要對 IaC generator 做 PBT／用不用 Hypothesis／`@given` 長什麼樣子  
- A／B／C／前端 unit 框架要不要重採  
- 本輪要不要引入 `coverage.py` 或把 80% 寫成 CI 閘門  
- 平台要不要 apply（已禁）  
- 預選 checkov／tfsec／gitleaks 品牌（無證據、無決策）  
- 把 D 種子／Coming Soon 當已交付能力（已 Forbidden 同形）  
- calculator／C1 計價 Forbidden 全文（非本 intent；memory 仍生效即可）

### 殘餘風險（記 evidence，不升級為規則）

- 前端繼續只有 Playwright：D 真 UI 會加重冰淇凌甜筒，但 unit 框架已否決，本輪接受。  
- SSE／agent 串流若沿用既有契約空 schema，OpenAPI drift 對事件形狀幾乎無護欄——屬設計／契約債，不是本站新測試規則。  
- `hypothesis` 未 pin：與 backend lockfile 待補同桶，非 Testing Posture 題。  
- CTA 與 D1 權限脫鉤：產品缺陷候選；修復後才有穩定的 e2e 授權前置，不在 practices 新造 NEVER。

## Positions

- AGREE: A／B／C 直接適用 Story D、不另造平行測試規則 — Q4 已定案；D 只是觸發條件（改種子／新端點／真 UI）
- AGREE: ADR-0006 對 IaC generator 現況 N/A、落地即 blocking 且須 Hypothesis — 與 `project.md` 一致；「要不要 PBT」不進訪談
- AGREE: Story D／IaC 自動化覆蓋為 ABSENT — 41 檔中無 D 業務測、無 e2e、CI 無 IaC scan；屬有無問題
- AGREE: I2／I3／I4／I6 為本輪必問缺口 — 種子領先、掃描工具未定、secret 掃描作用域缺口、LLM 盲區分桶皆無法由證據代答
- AGREE: `discovered-rules` 不發明 D 專屬 ALWAYS／NEVER — 避免未 Affirm 內容經 promote 進 memory
- AGREE: 80% 維持宣告、本輪不上 coverage 閘門 — 避免 `team.md` 弱化 `org.md`；增量門檻仍是 A／B／C＋D1 PBT
- OBJECT: 「約 43 個測試檔」寫進將 promote 的基線 — 精確值為 41 個 `test_*.py`；約數會覆蓋 codekb／實測
- OBJECT: `Methodology: custom`／Ordering 無訪談即可能被 promote — evidence 已標草稿；必須 Affirm、改標或刪除
- OBJECT: I5 把 D2／D3 PBT 寫成與 ADR-0006 等價選項 — ADR 只點名 generator；擴大必須新 Affirm／新 ADR
- OBJECT: codekb「team.md Q3 已定首個 D 端點 allow／deny」未在 evidence 打叉 — 會讓訪談誤跳 I2
- OBJECT: I2 保留「僅 D1 強制」作為中間項 — D2／D3 同屬矩陣領先，不對稱預設會重演 C1 空洞
- OBJECT: I7 若問成「可否暫緩規則 C」 — C 已定案；真 UI 必須 e2e，本站只可談入口時程而非廢止觸發
