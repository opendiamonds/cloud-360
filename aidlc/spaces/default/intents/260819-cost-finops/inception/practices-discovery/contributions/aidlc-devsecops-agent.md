**Collaborator:** aidlc-devsecops-agent

## Contribution

本輪以 DevSecOps 透鏡（lint／format、SAST／DAST、secret 與 dependency scanning、supply-chain）盲審 lead 草稿。查閱範圍：`team-practices.md`、`discovered-rules.md`、`evidence.md`、`team.md` 的 Deployment／Forbidden、`project.md` 的 Scope Overrides／Forbidden、`codekb/cloud/dependencies.md`。不修改四份 lead 產物。

### 1. C1 查價憑證禁令：草稿不夠硬（本輪主要異議）

Ideation 已定案（constraint-register T1／R1／O4）：查報價只能走**公開、免帳號**的官方價目 HTTP 端點；不得使用 production credentials；不得讀客戶帳單或 Cost Explorer；合併進 `ut` 即部署至自有 staging，沒有「先在 production 再處理」的緩衝。`project.md ## Scope Overrides` 亦將雲端供應商 production 環境與 production credentials 列為 out of scope。

草稿 `discovered-rules.md` 的 C1 Forbidden 目前只有：

> NEVER 用 `httpx` 或 `requests` 直接呼叫雲端 Pricing API 而不新建獨立 pricing port

這條是**模組隔離**規則，不是**憑證與 API 類別**規則。依字面，只要新建獨立 port，即可呼叫需帳號的 AWS Pricing API、Cost Explorer、CUR／Billing，甚至把 staging 雲端憑證寫進 GitHub Actions secrets 或 `deploy/.env`。既有繼承規則也補不上這個洞：

| 既有規則 | 實際擋得到什麼 | C1 仍可繞過的路徑 |
|---|---|---|
| NEVER commit 三雲 credential 字串 | git 內的 PEM／環境變數字樣 | runtime 使用 GitHub secrets 或 runner 上的 staging IAM |
| NEVER production write／IaC apply／IAM 變更無 human approval | 寫入與權限變更 | Cost Explorer **讀取**、帳單 API **讀取** |
| Scope Overrides：production credentials 不在範圍 | 政策聲明，無 CI 閘門 | 「staging 查價憑證」可被合理化為非 production |
| Secret 掃描 `validate_no_obvious_secrets()` | 12 個 contract 檔的明顯樣式 | `backend/`、`deploy/`、`.env.example` 完全看不見（見下節） |

`dependencies.md` 已載明：無 `pricing.amazonaws`、無 `cloudbilling`、無 `retailprices`、**無 boto3**；C1 若要查價必須新寫 client 或靜態表。這正是最容易把需帳號 SDK 夾帶進來的時刻。

**建議 lead 在訪談後，將下列升格為 `discovered-rules.md` 的 C1 Forbidden／Mandated（目前應標 `[proposed — 待訪談]`，不得當成已核可 hard constraint）：**

- **NEVER** 為 C1 查價呼叫 Cost Explorer、Cost and Usage Report、Billing／Invoice、Account 管理面，或任何需 SigV4／IAM／訂閱金鑰的雲端 API。
- **NEVER** 為 C1 查價配置或使用 staging／production 雲端帳號憑證（GitHub secrets、`deploy/.env`、`backend/.env`、runner instance profile 皆禁止）。
- **NEVER** 為 C1 查價路徑引入 `boto3`、`azure-identity`／`azure-mgmt-consumption`、`google-cloud-billing` 等預設走帳號認證的 SDK。
- **ALWAYS** C1 pricing port 僅允許呼叫公開免帳號價目端點（例如 AWS Price List bulk offer files、Azure Retail Prices、GCP 公開價目 catalog）；請求不得帶 `Authorization`、不得做 SigV4、不得帶 API key。host 必須 allowlist，禁止呼叫端可配置任意 URL（SSRF）。
- **ALWAYS** 價目回應與估價數字寫入 log 時不得夾帶雲端帳號識別或憑證殘值（呼應 `team.md ## Forbidden` 的 log 遮罩）。

現有「獨立 pricing port」規則應**保留**（隔離仍正確），但必須加上上述「只准公開免帳號端點」的上限，否則隔離等於授權錯誤 API 類別。

### 2. Secret 掃描與 production 路徑檢查：草稿記載正確，C1 使其從「待補」變成「本輪風險放大器」

同意 `team-practices.md ## Deployment` 與 `discovered-rules.md` 待補表對兩項機制落差的如實記載：

- `validate_no_obvious_secrets()` 只掃 contract 檔，看不到 `backend/`、`frontend/`、`deploy/`、`.env.example`。
- `validate_no_production_config_added()` 在 CI 乾淨 checkout 恆為 no-op。

異議在於**處置時程**，不是事實。C1 會新增 outbound HTTP client、可能新增 env 變數與 `.env.example` 列。在掃描器看不見應用程式碼、production 路徑檢查在 CI 無效的現況下，把「擴大掃描／修正 diff 基準」繼續標成「非本輪阻擋」等於：本 intent 最可能引入雲端憑證的 PR，會通過現有六道 CI 閘門。建議訪談二選一（不得兩頭空）：

- **A（本輪阻擋）**：C1 相關 PR 在合併前，secret 掃描至少覆蓋 `backend/`、`deploy/`、所有 `.env.example`；或
- **B（本輪政策阻擋、工具後補）**：先核可上一節的 NEVER 憑證規則，並在 code review／`pr-reviewer` 明確把「C1 新增雲端憑證 env」列為必擋 finding；工具擴大仍列待補。

不得維持「規則宣稱 NEVER commit credentials、機制卻掃不到即將落地的 pricing client」。

### 3. Lint／format：前端有閘門、後端無；SAST／DAST 在草稿中整段缺席

同意草稿 Code Style：前端 ESLint 10 + `tsc -b` 為真實閘門（只擋 error、未 `--max-warnings 0`）；backend 無 Ruff／Black／mypy；根目錄無 Prettier。待補表列 `ruff check` + `black --check` 合理。

草稿五個 H2 與 `discovered-rules.md` **完全沒有命名 SAST 或 DAST**。現況推論（與 CI 描述一致）：無 Bandit／Semgrep／CodeQL、無 OWASP ZAP／等效 DAST、ESLint 未載 security plugin。這不是「沒寫進 Code Style 的小遺漏」，而是安全左移在本 repo 沒有任何自動化落點。

C1 會新增：對外 HTTP 取值、金額運算、RBAC 守衛的 cost router、可能的 budget 寫入。這正是 SAST 該抓的 injection／SSRF／hardcoded secret 形狀，也是 DAST 該打的授權邊界。建議：

- 將「無 SAST／無 DAST」寫進 `evidence.md` 與待補表，避免被誤讀成「ESLint 已覆蓋安全」。
- `[proposed — 待訪談]`：C1 construction 是否以 Bandit（或 Semgrep）作為 backend 新模組的 PR 警告（本輪可不擋 merge），DAST 維持對 staging 的既有 ui-regression 之外、不另開 ZAP（與 `skeleton: off`、無 production 範圍一致）。不建議把完整 SAST 閘門假裝成既成實踐。

### 4. Dependency 與 supply-chain

同意草稿：FastAPI／Pydantic 精確釘選，其餘 pip 未 pin、無 lockfile；frontend 有 `package-lock.json` + `npm ci`。`dependencies.md` 確認 frontend 生產相依極少、無成本／圖表專用庫。

缺口未寫入草稿的部分：

- CI 無 `pip-audit`／`npm audit --omit=dev`／Dependabot 安全性 PR 作為閘門（Dependabot 分支命名已豁免，但不等於有 CVE 掃描）。
- `docker-build` 為 `push: false`、無映像 CVE 掃描（Trivy／Inspector）。對 C1 不是立即阻擋，但新 HTTP client 依賴一旦未 pin，CI／Docker／staging 三處可能解析到不同且含 CVE 的版本。
- **C1 具體風險**：若查價被實作成「加一個 SDK」，supply-chain 會從 `httpx` 擴大到整套雲端 SDK。這與第 1 節的 NEVER-SDK 規則同一條防線。

建議 `[proposed — 待訪談]`：C1 新增的 pip 套件必須有版本約束（`==` 或相容範圍），不得再以未 pin 的一行加入 `requirements.txt`。全檔 lockfile 仍可留待補；**本 intent 新增列不得比現況更鬆**。

### 5. 可直接整合進草稿的文字（供 lead 選用，非已核可）

**`team-practices.md ## Deployment` 建議增補（標 `[proposed — 待訪談]`）：**

C1 查價為出站連線，不是入站曝露。允許的唯一來源是公開免帳號官方價目端點。不得為了「讓估價更準」而把 Cost Explorer、帳單 API、或任何雲端帳號憑證接進 staging。ADR-0006 的 IAM 面向在此的正確處置是**不新增查價用 IAM**，不是「最小權限的 Cost Explorer role」。

**`evidence.md` 建議增補 Gap：**

Gap（安全管線）：secret 掃描看不到即將新增的 pricing client；無 SAST／DAST；無 dependency CVE 閘門。C1 的 credential 禁令目前只存在 ideation constraint-register，尚未進入 practices Forbidden 的可執行形狀。

## Positions

- AGREE: 草稿如實記載 secret 掃描只覆蓋 contract 檔、production 路徑檢查在 CI 恆為 no-op — 這是機制落差而非缺工具，不應美化成已有 secret scanning。
- AGREE: 前端 ESLint 為真實閘門、backend 無 linter／formatter、pip 多數未 pin — 與 supply-chain 現況一致，待補表方向正確。
- AGREE: C1 查價必須新建獨立 pricing port、不得混入 n8n／PNG 既有 `httpx` 呼叫點 — 隔離邊界正確，應保留。
- AGREE: 繼承的 NEVER commit 三雲 credential、NEVER 無核准的 production write／IAM 變更、Scope Overrides 排除 production credentials — 作為基線正確，但不足以涵蓋 C1 查價。
- OBJECT: C1 Forbidden 只禁止「不經獨立 port 呼叫 Pricing API」，未禁止 Cost Explorer、帳單 API、staging／production 查價憑證與帳號認證 SDK — 與 ideation T1／R1 及 Scope Overrides 相比過弱，隔離規則在字面上授權了錯誤的 API 類別。
- OBJECT: 將 secret 掃描擴大與 production 路徑 CI 修復標為「非本輪阻擋」，卻同時讓 C1 落地第一個雲端出站 client — 在掃描器看不見 `backend/` 時，本輪是風險最高而非可延期的時刻。
- OBJECT: 草稿未記載「無 SAST、無 DAST、無 dependency CVE 閘門」— ESLint／unittest／repo-contract 不能被推論為安全掃描；C1 新模組會放大此盲區。
- OBJECT: 未禁止為 C1 引入 `boto3` 等帳號認證 SDK，亦未要求本 intent 新增 pip 列必須 pin — 與「公開免帳號價目 + 無 lockfile」的組合不相容。
