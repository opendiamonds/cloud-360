# Discovered Rules — Cloud-360（Lead Integration，practices-discovery re-run）

> 本檔只收錄**人類已明述**的硬約束（`ALWAYS` / `NEVER` 形式），以及依訪談 Q1（分層寫）
> 定案、需要「補上承載機制」的明確待辦。`project.md` 既有的 `## Mandated` /
> `## Forbidden`（repo contract、schema↔deploy 同步、production 禁令等）已生效，
> 不在此重複列出。

## Mandated

- **ALWAYS 對每一項變更檢查 ADR-0006 security baseline 的四個面向（IAM、encryption、network exposure、audit logging）**；此為 hard constraint（`CLAUDE.md` 第 3 章「Standing Constraints」逐字列為 `Hard constraint（IAM、encryption、network exposure、audit logging）`）。原承載該約束的 v1 路徑 `extensions/security/baseline/` 已隨 v2 遷移（ADR-0011）從 repo 移除（全樹搜尋僅 `project.md` 的 `## Decided` 一行與兩份 ideation 文件引用它，無任何實體檔案），使這條 hard constraint 一度失去可執行形式。本條為其在 v2 規則層的重新落點（訪談 Q5 定案 A：補進本檔）。實務上：涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出（feasibility、scope、user-stories 等）中明列 security 影響與處置，不得僅以「已有 ADR-0006」帶過。

## Forbidden

（本次無新發現。）

## 待補承載機制（訪談 Q1=C 分層寫，明確待辦）

> 以下項目是「規則宣稱大於實際承載機制」的已知落差（見 `team-practices.md`／`evidence.md`
> 逐項查證），依 Q1 決議不寫進 `team.md` 的現況段落，改列為待辦，交由後續 stage
> （technical-debt 處理、design、或另開 intent）排入。

1. **`org.md` 80% line coverage 門檻無法量測**：導入 `coverage.py`／`pytest-cov` 等量測工具，取得真實基線後再談是否調整門檻語氣。目前實際生效的替代門檻是 `team-practices.md ## Testing Posture` 新增的 A/B/C 三項規則（訪談 Q4 定案）。
2. **schema↔deploy 同步（`project.md` 既有 blocking 規則）沒有自動化執行者**：`validate_repo_contract.py` 的 `REQUIRED_TEXT` 只做純子字串比對，驗的是 `project.md` 這份檔案裡有沒有 `schema_rbac.sql`／`DEPLOY.md` 這兩個字串，與本次變更是否真的同步了完全無關。待補一個真正比對 schema 變更與 `schema_rbac.sql`／`DEPLOY.md` 內容的檢查。
3. **`validate_no_obvious_secrets()` 的作用域小於 `project.md ## Forbidden` 的宣稱**：只掃 `contract_files()`（12 個 repo 層必要檔 + baseline record 必要檔 + audit shard），結構上看不到 `backend/`、`frontend/`、`deploy/`、任何 `.env.example`。待擴大掃描器作用域至全 repo（排除 `node_modules`／`dist`／`.git`），或改用 GitHub secret scanning／`gitleaks`。
4. **`validate_no_production_config_added()` 在 CI 恆為 no-op**：以 `git diff --name-only`（unstaged ∪ staged）為輸入，CI 乾淨 checkout 上兩者皆為空集合。待修正 diff 基準（PR 情境對 base ref，push 情境對 `HEAD~1`），讓它在 CI 真的會擋。

上述 4 項本輪皆**未經訪談逐項定案**（訪談僅涵蓋 Q1–Q6，devsecops／developer 兩位 support agent 提出的 Q9–Q13、Q-dev-1/2/3 追加題目未進入本輪正式訪談）；此處列為待辦本身即是本輪的產出，具體導入方案（優先序、範圍、是否分階段）留待下一輪 practices-discovery 或獨立技術債任務決定，不在本檔逕自寫成規則。

## 檢視範圍與判定理由

檢視了以下來源，尋找「人類已明確表述、但尚未寫進 `project.md` / `team.md` 既有 `## Mandated` /
`## Forbidden`」的硬約束：

1. **`CLAUDE.md`（repo 根目錄）**：第 3 章「Standing Constraints」的三項中，security baseline、property-based testing、文件語言已收錄於 `project.md` 的 `## Decided`；但 security baseline 一項經 devsecops agent 查證，其承載路徑 `extensions/security/baseline/` 已隨 v2 遷移消失，屬於「已明述但失去可執行形式」的情況，經訪談 Q5 定案補進本檔（見上）。第 4 章「Repository Contract」的內容已收錄於 `project.md` 的 `## Mandated`。
2. **`AGENTS.md`**：僅重述 AI-DLC 規則層結構與繁中回應要求，兩者皆已存在於既有規則層，無新內容。
3. **`code-quality-assessment.md` 的技術債登記簿（T1–T20）**：這些是**尚未被任何人明述為規則的觀察**——例如「`schema_rbac.sql` 第 178 行的 `DELETE FROM role_permissions;` 會破壞既有環境資料」（T4）、依賴未 pin（T5）、JWT 預設值（T6/T7）、WebSocket 無授權（T8）等，都是**事實發現**，不是團隊已經決議的規範。依 stage 指示，推斷不應寫成規則；已改記入 `evidence.md`，交由訪談決定是否要正式定為規則。本輪訪談（Q1–Q6）未涵蓋這些項目，故均未升格為本檔規則，仍留在 `evidence.md` 作為向下游傳遞的事實與開放問題。
4. **`.github/workflows/ci.yml`、`deploy.yml`**：CI／CD 的既有行為（四道 gate、rollback 自動化、`concurrency` 控制）是**已落地的機制**，但機制本身不等於「人類明述的規則」；其中已被人類明述為規則的部分（如 deploy-on-merge、production 範圍外）已在 `org.md` / `project.md` 收錄。三位 support agent 進一步查證發現機制的**實際作用域小於 `project.md` 既有規則的宣稱**（見上方待補承載機制第 3、4 項）——這類落差性質上是「已有規則、機制不符」，不是「新規則遺漏」，故不歸入 `## Mandated`／`## Forbidden`，而是待補承載機制。

**結論**：本輪新增一項需補登的硬約束（ADR-0006 security baseline 的可執行形式，訪談 Q5 定案），另有 4 項「規則宣稱大於機制承載」的落差列為明確待辦（訪談 Q1=C 決議的分層寫產出）。`team-practices.md` 中的實務規則（Testing Posture 的 A/B/C 三項、PR 合併分流、Walking Skeleton off）皆已由訪談 Q2–Q4 定案，屬於「已affirm 的實務」而非「人類明述的硬約束」，故收錄於 `team-practices.md` 而非本檔。
