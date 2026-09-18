# A3 Lens Editor — Execution Plan（Workflow Planning）

> AIDLC Inception → Workflow Planning（A3 增量）  
> Requirements: `inception/requirements/a3-lens-editor-requirements.md`  
> Answers: `a3-lens-editor-questions.md` + `a3-lens-editor-clarification-questions.md`


### 1. 範圍與影響

| 面向 | 判定 |
|---|---|
| 架構變更 | 否（同 monolith；擴充 A3 模組） |
| 資料模型 | **是** — 新表（建議 `wa_lenses`：id、lens_id、is_active、body_json、updated_by、updated_at） |
| API | **是** — GET／PUT（或 PATCH）active lens；可選 POST add-question／delete helper |
| FE | **是** — `AssessmentPage`「Lens 標準」分頁 |
| 評核管線 | **是** — `load_lens()` DB 優先 |
| 部署契約 | **是** — `schema_rbac.sql` + `DEPLOY.md`（override 強制） |

### 2. 建議階段（核准後執行）

| 階段 | 執行？ | 理由 |
|---|---|---|
| Inception WD／RE | 跳過 | 已完成 |
| RA／US／WP／UG | ✅ 本輪完成 | Q7=B |
| Application Design（完整重寫） | **精簡** | 併入下方 Construction FD；不另開系統架構圖 |
| Construction FD | ✅ | 短 FD：實體、API、UI、驗證規則 |
| NFR Req／Design | **精簡合併 FD** | 沿用 A3 NFR；補 security／validation |
| Infrastructure Design | 跳過 | 無新 infra |
| Code Generation | ✅ | BE＋FE＋測＋schema／DEPLOY |
| Build and Test | ✅ | unit＋既有評核回歸 |
| Operations | PLACEHOLDER | 部署說明已含 DEPLOY |

### 3. Construction 工作包（建議順序）

1. **DDL + model + `_ensure_*_schema` + schema_rbac／DEPLOY**  
2. **`wa_lens_engine`：resolve_active_lens(db)**（fallback 檔案）  
3. **API + 角色閘（`Security_Reviewer`）+ 驗證（五柱、每柱≥1、禁止改支柱集合）**  
4. **題目模板 + improvementPlan 建議字串**  
5. **Assessment UI 分頁**  
6. **Tests**（權限、fallback、增刪限制、儲存後評核讀 DB）  

### 4. 風險

| 風險 | 緩解 |
|---|---|
| 非法 riskRules 導致評核炸 | 儲存前用引擎 list_questions／試 score 或 schema validate |
| 誤以為 A3.edit 即可改 Lens | 文件＋API 硬碼角色；UI 依 `user.role` |
| 容器唯讀與舊「改檔」假設 | 堅持 DB，檔案僅 seed／fallback |

### 5. 核准門檻

請確認本計畫後，進入 **Construction Functional Design（短）→ Code Gen**。

### 6. Extension Compliance

| Extension | Status |
|---|---|
| bilingual-docs | compliant |
| security/baseline | applicable → Code |
| property-based | applicable → Code／Build |
| resiliency | N/A |
