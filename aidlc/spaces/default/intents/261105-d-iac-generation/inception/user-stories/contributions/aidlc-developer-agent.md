**Collaborator:** aidlc-developer-agent

## Contribution

盲評範圍：`stories.md`／`personas.md`／`user-stories-questions.md`／`requirements.md`／`team-practices.md`／codekb architecture 與 `rbac_seed_data.py` 對照。焦點：可實作性、故事粒度、`backend/iac` 對齊、OpenAPI／RBAC 掛鉤、R-01（D2 先於 D3）API 形狀、切圖清空狀態機。未讀 sibling contributions；未改 lead 產出。

### 總評（實作視角）

工作流程切法（Q1=A）與標準粒度（Q2=A）對齊既有 `backend/cost/` 領域套件與步驟式 UI，便於下游切 Bolt。R-01 在故事層已用 US4.1／AC4.1.1 釘死「無 D2 成功報告 → UI disabled＋執行 API 4xx」，可直接做成 service 前置條件與 TestClient 負向案例。切圖清空（US1.3／Q4=A）與 D1 失敗保留（US2.3）語意可並存，但狀態機尚缺「進行中請求／伺服器側產物鍵」邊界。最大阻擋項是 **persona 主路徑與現行 D 柱種子編輯權不相容**：Alex（`Project_Architect`）僅有 D1 `edit`，D2／D3 只有 `view`；且**沒有任何角色同時具備 D1＋D2＋D3 `edit`**，US6.2「Alex 一人走完」在現有 RBAC 下無法落地。

### 可實作性與 backend／iac 對齊

- 故事維持產品語彙、未鎖檔名／路徑——正確；與 `team-practices` 的 `backend/iac/`、三層、禁 `d1_*` 前綴、`langgraph_runtime`＋OpenRouter、禁代 apply **無衝突**。
- US2.1／US3.1／US4.1 可映射為 `iac_generate_*`／`iac_scan_*`／`iac_secret_*` 路由＋純函式核心＋agent；PBT／負向突變義務落在 AC4.1.3／US6.2，與 practices Q4／Q5 一致。
- FR8.3 OpenAPI 延至 contract-design（traceability Deferred）可接受；實作時 `/api/iac/...` 獨立掛載、勿塞 `agent_router`／`user_router` 仍須由設計釘死。
- **缺口**：故事未區分 `view`（可檢視步驟／報告）與 `edit`（執行產生／掃描／改寫）。`require_story_action("D1"|"D2"|"D3", …)` 的 action 字面若不在 AC 出現，HTTP 層容易誤用 `view` 放行執行，或反過來用 `edit` 擋住 Fiona 只讀報告。

### R-01：D2-before-D3 API 形狀

- **AGREE 核心契約**：AC4.1.1＋AC4.1.2 已可翻譯為：`POST …/secrets/rewrite`（或等價）必須驗證「同工作階段／同草稿 revision 存在至少一次 D2 `status=succeeded` 報告（允許 zero findings）」；否則 **4xx**（建議設計凍結 409 或 422，並與「無 D1 草稿」的 4xx 區分 reason code）。
- 與 Advisory（US3.2）正交且正確：有 HIGH／CRITICAL **仍可開** Secrets **畫面**（AC4.2.1／AC3.2.1）；擋的是**執行**，不是導覽——API 不得把「進入步驟」做成同一支執行端點的副作用。
- **殘差風險**：`requirements.md` FR6.2 字面仍只寫「執行 D2／D3 需 D1 成功草稿」。故事已關閉 R-01，但若下游只讀 FR 表會實作出「有 D1 即可 D3」。建議 lead 在故事依賴或 US4.1 註明「執行 D3 前置＝D1 草稿 ∧ D2 成功報告；覆寫／補強 FR6.2 對 D3 的語意」，避免 contract-design 雙來源。

### 切圖清空狀態機（US1.3）

AC1.3.1 給出可測的目標態（清空 D1／D2／D3 產物、提示、下載／D2／D3 回 disabled、直到新 D1 成功）。實作仍缺：

| 事件 | 故事已釘 | 未釘（建議下游補） |
|---|---|---|
| 改選／上傳成功且脈絡圖 id 變更 | 清空＋提示 | 進行中的 generate／scan／rewrite 是否 cancel／ignore 結果 |
| D1 失敗（US2.3） | 保留上次成功草稿 | 與「切圖清空」的優先序：僅在 diagram_id 不變時保留 |
| 重新整理／多 tab | — | 產物若只在前端 state，刷新後可能「復活」錯圖草稿；須伺服器以 `(user|workspace, diagram_id)` 為鍵或明確宣告 session-only |
| 清空後殘留 D2 報告 id | 須失效 | API：舊 `report_id` 呼叫 D3 → 4xx（與 R-01 同一閘） |

未補齊前，e2e／TestClient 無法寫出穩定的「切圖後舊 artifact 不可再用」案例。

### 故事粒度

- 步驟密度大致符合「每 Must 步驟 2–4 則」：選圖 3、D1 3、D2 2、D3 2、下載 2、權限／演示 2——可接受。
- **US2.1 偏肥**：多檔樹＋預覽＋相容 HCL＋（經涵蓋）agent／決定性 generator 同則；失敗模式與驗證方式（UI 預覽 vs PBT 核心 vs HTTP）不全同類，delivery 時容易變成「一個 Bolt 塞不下或假完成」。建議拆「成功產出可預覽模組樹」與「決定性核心／agent 編排可離線／可 stub」——或至少在 DoD／units 分開，AC 保留產品面。
- **US4.1** 同時承載 R-01 閘、改寫清單、明文不得外洩——閘與改寫可同故事，但 AC4.1.3 屬跨層護欄，宜標 DoD／測試義務，避免與「改寫成功可見清單」混成同一驗證面。
- **US6.1**：AC 驗證「存在 TestClient」屬交付／測試義務（team correction：元層次 AC），不是使用者可觀察行為；內容正確，落點應改 DoD 或併入各執行故事的授權 AC。

### OpenAPI／RBAC 掛鉤

- 種子現況（`rbac_seed_data.py`）：`Project_Architect`＝D1 edit、D2／D3 view；`Platform_Engineer`＝D1／D2 edit、D3 view；`Security_Reviewer`＝D2／D3 edit、D1 view；`Developer`＝D1／D3 edit、D2 view。**無三角 edit 角色**。
- personas 寫 Alex 主路徑含「跑 D1…走完 D2／D3」、US6.2 要 Alex 依序完成——與種子衝突。若不改種子，演示必須多角色協作或改用非 Alex 帳號；若改種子讓 Architect 具 D2／D3 edit，則觸發 A 規則雙向測試＋`schema_rbac.sql`／`DEPLOY.md` 同步。
- 入口故事（AC1.1.1／1.1.2）未寫清：進入工作區要 D1 `view` 還是 `edit`；執行各步各自要哪個 story 的 `edit`。Fiona「無權限時入口行為」與「可檢視掃描」需要分開 AC，否則前端會用單一 `capabilities.D1` 開關整區。

### 與 requirements 覆蓋

- Must FR 大多有故事承接；FR8.3／NFR1／5／6／7 Deferred 合理。
- FR3.3 下載前 HIGH／CRITICAL 摘要掛在 US5.1 AC5.1.4——可實作。
- FR6.2「無 D1 時 D2／D3 執行 4xx」由 US3.1 AC3.1.2 與 US4.1 部分覆蓋；D3 的 D2 前置僅在故事層完整——見上。

---

## Positions

| # | 主張 | 立場 | 理由 |
|---|---|---|---|
| 1 | Q1 工作流程切法＋Q2 標準粒度適合作為 Construction 故事骨架 | **AGREE** | 對齊步驟 UI 與 `backend/iac/` 三能力邊界；故事數與步驟密度可交付。 |
| 2 | US4.1／AC4.1.1–2 足以作為 R-01「D2 成功報告後才可執行 D3」的 API／UI 契約 | **AGREE** | 明確 disabled＋API 4xx；與 Advisory「可看不可跳執行」可同時實作。 |
| 3 | 切圖清空（US1.3）目標態清楚，可當狀態機验收起點 | **AGREE** | 與 US2.3「失敗不整場清空」不矛盾（觸發條件不同）。 |
| 4 | 故事與 `backend/iac`／禁 apply／PBT 三核心／獨立 `/api/iac` 慣例無產品層衝突 | **AGREE** | 實作約束已在 practices／FR；故事未引入矛盾路徑。 |
| 5 | Alex 單獨走完 US6.2（含執行 D2／D3）在現行 RBAC 種子下可實作 | **OBJECT** | Architect 無 D2／D3 `edit`；全矩陣無三角 edit。須改種子、改主路徑角色、或改寫為多角色協作演示，並在 AC 寫明各步所需 `view`／`edit`。 |
| 6 | 僅依現行 FR6.2 字面實作 D3 前置即可 | **OBJECT** | FR6.2 仍只要求 D1；實作必須以 US4.1 為準並在契約層寫出 D2 報告前置，否則 R-01 會在 OpenAPI／handler 復發。 |
| 7 | US1.3 狀態機已完整到可直接開工無開放決策 | **OBJECT** | 缺 in-flight cancel、伺服器鍵／session 壽命、舊 report_id 作廢；不清會導致切圖後仍能打通 D3。 |
| 8 | US2.1 維持單則 Must 即可獨立完工驗證 | **OBJECT** | UI 預覽與決定性 generator／agent／PBT 失敗模式不同類；宜拆故事或強制 units／Bolt 拆分，避免假完成。 |
| 9 | US6.1 以「存在 allow／deny TestClient」作為使用者故事 AC 適當 | **OBJECT** | 屬 A／B 交叉交付義務；應移 DoD／各執行故事授權 AC，AC 改寫系統對無權呼叫回 403 的可觀察行為。 |
| 10 | 入口／執行權限用「有 D1／D2／D3 權限」概括即可開工 | **OBJECT** | 種子以 view／edit 分列；須在 US1.1／US3／US4／US6 釘死各操作對應 action，否則 OpenAPI `Depends(require_story_action)` 無法對 AC。 |
