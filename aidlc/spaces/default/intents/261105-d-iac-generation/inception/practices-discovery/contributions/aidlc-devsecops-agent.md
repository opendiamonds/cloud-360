**Collaborator:** aidlc-devsecops-agent

## Contribution

> Blind support review｜intent `261105-d-iac-generation`｜practices-discovery｜HEAD `0bffc82`｜2026-11-05T15:28:20Z  
> 範圍：lint／format、SAST／DAST、secret／dependency scanning、supply-chain；焦點 Story D2／D3 與「平台不 apply IaC」。未讀其他 support contribution。

### 實測摘要（repo 現況）

| 控制面 | 現況（本輪抽查） | 對 Story D 的含義 |
|---|---|---|
| Lint／format | Frontend：ESLint（CI 擋 error）＋`tsc -b`；無 Prettier。Backend：無 Ruff／Black／mypy | D 柱新 Python 模組仍無靜態風格閘；不得把「有 CI」誤讀成後端已有 SAST |
| SAST | `.github/workflows/` 對 CodeQL／Semgrep／Bandit／Sonar **0 命中** | 應用層漏洞靠人工＋unittest；D2「靜態 IaC 掃描」是**產物掃描**，不是現有 app SAST 的延伸 |
| DAST | 無 OWASP ZAP／同類 staging 動態掃描 job | 本 intent 不依賴 DAST 當 D2 閘門；D2 應鎖在生成物靜態分析 |
| IaC scan（D2） | `ci.yml`／workflows 對 checkov／tfsec／trivy／gitleaks **0 命中**；codekb `technology-stack`／`dependencies` 亦無對應相依 | 與 lead I3 一致：工具未定案前**不得**寫進 Mandated／workflow；定案後才可談 CI blocking vs 報告-only |
| Secret 掃描 | 見下方「機制校正」 | D3 落地會放大剩餘盲區；負向測試＋遮罩突變仍須訪談（I4） |
| Dependency／SBOM | Frontend：`package-lock.json`＋`npm ci`。Backend：多數未 pin、**無 lockfile**；**無** `.github/dependabot.yml`；CI 無 `npm audit`／`pip-audit`／Snyk／Trivy image gate（`docker-build` 為 `push: false`、無 scan） | 若 D2 整合外部掃描 CLI，供應鏈風險上升——工具版本／二進位來源須一併定案，不可只選品牌名 |
| Apply 邊界 | `org.md`／`project.md` Forbidden＋Scope；ideation T5／R2；`discovered-rules` 已重申 | **產品能力＝產碼＋掃描＋SM 引用；永不代 apply** |

### 機制校正（相對 lead／team 既有敘述）

Lead／`team-practices` Deployment 仍寫：`validate_no_obvious_secrets()`「結構上看不到應用程式碼」。本輪讀 `scripts/validate_repo_contract.py` 現況為**雙軌**：

1. **字面 `FORBIDDEN_CONTENT_PATTERNS`**（PEM 標頭、`AZURE_CLIENT_SECRET=`、`GOOGLE_APPLICATION_CREDENTIALS=`）——仍只掃 `REQUIRED_FILES`（contract 必要檔）。
2. **`SECRET_VALUE_REGEXES`**（`AWS_SECRET_ACCESS_KEY`／`GCP_BILLING_API_KEY` 的**賦值形狀**）——已對 `git ls-files` **全域**掃追蹤文字檔（ADR-0018 §6）。

因此「宣稱＞機制」仍成立，但已**部分收窄**，不是「完全看不到應用程式碼」。剩餘真實缺口：

- 無 gitleaks／truffleHog／GitHub secret scanning 類**通用**高熵／多供應商規則；
- PEM 等字面樣式仍限 contract 檔；
- 日誌／API 回應／生成 artifact 的**執行期**明文洩漏不在 contract 掃描範圍——這正是 D3 必須用產品測試鎖住的面。

另：`FORBIDDEN_NEW_PATH_PARTS` 含精確 path-part `secrets`——D3 產物／模組路徑**不得**使用完整 path part 名為 `secrets` 的目錄或檔名（子字串檔名如 `secrets-policy.md` 不受影響；見 `project.md`）。

### Lint／format 立場

- **追認** lead：前端 lint 結構約束（Context 拆檔、資料抓取兩層、immutability）對未來 D UI 仍強制；後端無 formatter／linter 為待補承載，**不**由本 intent 夾帶 Ruff／Black 決策。
- D1／D2／D3 純函式核心若落地，ESLint 管不到 Python——安全不變量必須靠 **unittest／Hypothesis＋契約測試**，不能指望 lint。

### D2 — 靜態 IaC 掃描姿態（建議訪談定錨）

1. **產品 D2 ≠ 平台 apply**：掃描對象是 D1 產出的 Terraform／OpenTofu **草稿／報告**；結果給使用者下載／檢視。任何 `terraform apply`／雲端部署 API／狀態後端寫入屬 **out of scope**（ideation 已定「使用者自行 apply」）。
2. **整合不重寫引擎**（feasibility／build-vs-buy）：Checkov／tfsec／Trivy 等為候選；lead 不預選——**同意**。訪談 I3 應同時問清：
   - A＝僅產品內編排＋報告形狀（unittest 鎖契約；掃描 CLI 為執行期相依）；  
   - B＝另加本 repo CI job，對**範例／fixture IaC**跑同一掃描器（回歸護欄）；  
   - C＝CI blocking 對產品生成物（通常不可行／成本高，需明確否決理由）。
3. **嚴重級閘門**：工具一旦選定，High／Critical 發現在產品面必須可觀測（不得靜默丟棄）；是否「阻擋下載」屬產品 AC，是否「阻擋 PR」屬 CI 決策——兩者分開問，避免混成一條 ALWAYS。
4. **不得**把 D2 實作成「對使用者雲帳號只讀探測／漂移」——那會滑向代管 apply／雲憑證邊界。

### D3 — Secret Manager／明文禁令

1. **Hard**：生成 IaC、API 回應、應用 log、TCMS／audit／decisions 產物皆**不得**含 production／environment secret 明文；遮罩 `[REDACTED]`（既有 `team.md` Forbidden）。成功形狀＝雲端 SM **引用**（ARN／resource id／data source），非內嵌值（ideation Rsk-3／Dep-5）。
2. **測試義務（建議 I4 採納方向）**：至少一組負向 TestClient／純函式測試——人為注入明文樣式時，輸出／log sink **不得**出現該明文；redaction 路徑做突變驗證（改回未遮罩→測試紅→還原）。這補的是 contract 掃描碰不到的執行期面。
3. **與擴大 contract 掃描的關係**：擴大 gitleaks 類 CI 與 D3 產品測試**互補、不可互相替代**；訪談可並列，但不要用「擴大 validate_repo_contract」單獨結案 D3。
4. **平台呼叫雲端 SM API**（若 requirements 採整合）：憑證只進 GitHub Secrets／環境變數，經 `render-env.sh`；**禁止**寫進生成檔或 `.env.example` 真值；IAM／API key 最小權限；日誌只記變數名不記值（`DEPLOY.md` 已有同形先例）。

### 平台不 apply IaC（硬規則）

- **同意** lead：`discovered-rules` 保留「high-risk IaC apply 須 plan＋impact＋rollback＋human gate」與「NEVER 未核准即 apply／direct production IaC」——與 `org.md` Deployment／Forbidden、`project.md` Scope Overrides 一致。
- **補強表述（建議整合進 Forbidden 候選，訪談確認後再 ALWAYS／NEVER）**：Story D 代理人／API／workflow **不得**提供一鍵 apply／對使用者雲帳號寫入；產碼與掃描成功**不**構成 apply 授權。平台 staging 部署（`deploy.yml`→`192.168.10.10`）與此規則正交，不得被誤讀為「已有 IaC apply 管線」。

### Supply-chain（若導入掃描 CLI）

- 無 Dependabot、backend 無 lockfile：導入 checkov／tfsec／trivy 時，須在同一決策裡定 pin／鎖版／更新節奏，避免「掃描器自身帶 CVE 卻無人看」。
- Docker image 建置現無漏洞掃描閘——非本 intent Must，但若 D2 以 container 包 CLI，應在 I3 一併揭露此缺口。

### 對 lead 草稿的整合建議（不改 memory，僅供 Final Integration）

1. 修正 Deployment「secret 掃描作用域」敘述為雙軌現況（字面樣式＝REQUIRED_FILES；AWS／GCP 值形＝全域 `git ls-files`），並列剩餘通用掃描缺口。  
2. I3／I4 維持待訪談；整合時把「產品掃描 vs repo CI 掃描」與「契約掃描 vs 執行期 redaction 測試」拆成可勾選選項。  
3. 不在未訪談前把特定掃描工具名寫進 `discovered-rules` Mandated（lead 已遵守——維持）。  
4. Path-part `secrets` 禁令在 D3 設計／命名 checklist 明示，避免 construction 踩 contract 紅燈。

## Positions

- AGREE: 平台產碼／掃描 ≠ apply，apply／direct production IaC 維持 out-of-scope＋human gate — 與 org／project Forbidden 及 ideation T5 一致，不得在 practices 層弱化。
- AGREE: D2 工具（checkov／tfsec／trivy 等）與 CI 閘門姿態留待訪談、不預寫 Mandated — 現況 workflows 0 命中，預選工具會把未定案寫成假護欄。
- AGREE: D3 明文 secret 不得進生成物／log；I4 應涵蓋負向測試與 redaction 突變 — 補 contract 掃描碰不到的執行期洩漏面。
- AGREE: 不發明新的 ALWAYS／NEVER；僅重申已 affirmed 邊界 — 符合本 stage「human-stated hard constraints only」紀律。
- OBJECT: 「secret 掃描結構上看不到應用程式碼」敘述已過時 — `SECRET_VALUE_REGEXES` 已全域掃追蹤檔；應改寫為雙軌＋剩餘通用／PEM／執行期缺口，以免 I4 建立在錯誤現況上。
- OBJECT: Supply-chain 缺口（無 Dependabot、backend 無 lockfile、image 無 scan）在 D2 引入外部 CLI 前必須進訪談選項 — lead 證據偏產品掃描，未把「掃描器相依本身」當成風險面。
- OBJECT: 建議在 Forbidden 候選加一條產品級「D 代理人／API 不得代 apply」與既有「未核准不得 apply」並列 — 後者管人工高風險操作，前者管產品能力邊界，混用會讓下游以為人工核准即可做平台代 apply。
