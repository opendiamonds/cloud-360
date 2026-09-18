# Build and Test Summary — 260816-production-path-check

- Intent：`260816-production-path-check`（issue #509）
- Test Strategy：**Minimal**、Depth：**Minimal**、Scope：**bugfix**
- 上游：`<record>/construction/production-path-check/code-generation/code-generation-plan.md`、
  同目錄 `code-summary.md`
- 實際執行結果：`build-test-results.md`

## 建置狀態與前置條件

**建置就緒、測試就緒、可部署。** CI 的四個 job 中三個已在本機以其實際指令驗證通過
（`repo-contract`、`frontend`、`backend`），第四個（`docker-build`）未執行 ——
本次不觸及 Dockerfile 或建置上下文，留給 CI。

本次變更**新增一個環境面依賴**（非套件依賴）：`validate_no_production_config_added()`
改用 `git ls-files`，因此該檢查必須在 git 工作樹內執行。無 git 時
`subprocess.run(..., check=True)` 會拋例外而非靜默通過 —— 刻意的 fail-fast，
不讓檢查在拿不到檔案清單時假裝通過。CI 是 `actions/checkout` 產生的 git 工作樹，
條件滿足；淺 clone（`fetch-depth: 1`，CI 的預設）亦不影響 `git ls-files`。

套件依賴零新增（NFR-2）。

## 產出的測試類型清單

| 類型 | 狀態 | 依據 |
|---|---|---|
| `unit-test-instructions.md` | **已產出** | Minimal 策略要求 |
| `integration-test-instructions.md` | **跳過** | 見下 |
| `performance-test-instructions.md` | **跳過** | 見下 |
| `security-test-instructions.md` | **跳過** | 見下 |

### 跳過的測試類型（逐項理由，非省略）

stage 檔的 Step 4-8 對 Minimal 策略明示「generate ONLY `unit-test-instructions.md`，
Skip all other test types」，並註明這是 soft guideline，context 需要時仍可加開。
本 intent 逐項判定為不需要：

- **Integration**：受測對象是一支無外部邊界的獨立腳本。它只呼叫 `git ls-files`
  並比對路徑字串 —— 不連 DB、不呼叫 HTTP、不跨模組。既有的 10 個測試已在
  真實 git 子行程上執行（不是 mock），該有的整合面已被單元測試涵蓋。
- **Performance**：NFR-3 有量化門檻（< 1 秒），但已在單元執行中直接量測完成
  （實測 0.015s，門檻的 1/60，見 `build-test-results.md`）。為一個 15 毫秒的
  函式建立獨立的效能測試基礎設施，成本遠高於收益。
- **Security**：本變更的安全面是**加強既有控制**而非引入新攻擊面（逐項判定見下節）。
  不新增端點、不處理使用者輸入、不碰認證授權。

## ADR-0006 Security Baseline 逐項判定（hard constraint，缺一不可）

依 `project.md` 的 Mandated 條款，每項變更須對四個面向逐一判定並附理由，不得留空白。

| 面向 | 判定 | 理由 |
|---|---|---|
| **IAM** | N/A | 不觸及角色、權限矩陣、`role_permissions` seed、認證或授權路徑。受測腳本無任何身分概念。 |
| **Encryption** | N/A | 不處理金鑰、憑證、雜湊或任何加密路徑。 |
| **Network exposure** | N/A | 不新增或修改端點、不改 `nginx.conf`、不改 compose 的埠對應。受測腳本不連網。 |
| **Audit logging** | **相關 —— 本變更是淨強化** | 這道 contract 檢查本身就是「防止 production 設定與 secrets 路徑進入版控」的**控制**。修正前它在 CI 恆為 no-op（規則宣稱有擋、機制實際沒擋）；修正後涵蓋全部版控檔案，控制真正生效。**這是恢復一道原本失效的控制，不是新增風險面。** |

**測試本身的安全性**（FR-9）：回歸測試不在真實 repo 建立任何違規路徑，
所有情境限於 `tempfile` 暫存目錄，且 fixture 的 git 設定逐次以 `-c` 傳入，
既不讀也不寫使用者的全域 git 設定。

### 未解決的安全落差（如實記載，不在本 intent 範圍）

`validate_no_obvious_secrets()` 只掃 `contract_files()`（12 個 repo 層必要檔 +
baseline record 必要檔 + audit shard），**結構上看不到 `backend/`、`frontend/`、
`deploy/`、`schema_rbac.sql` 與任何 `.env.example`** —— 本 repo 唯一的 secret 掃描器
看不到應用程式碼。這在 `team.md` 有記載並於本次保留（FR-7 只移除了已解決的那一條）。

成因與修法都與本 intent 不同（一個是掃描**範圍**過窄，一個是比對**基準**錯誤），
`requirements.md` 的範圍邊界明列它為獨立問題。**這裡重申它仍然存在**，
避免「production 路徑檢查修好了」被誤讀成「contract 的安全掃描都修好了」。

## 覆蓋預期

Minimal 策略的門檻是「1 test per requirement + happy-path floor」。本次 10 個測試
涵蓋 FR-1～FR-4 與 AC-1／AC-2，符合並略高於門檻。

**本 repo 無覆蓋率量測機制**（無 `.coveragerc`、無 `coverage`／`pytest-cov`、
CI 無對應 step），故 `org.md` 宣告的 80% line coverage **無法量測也無法強制**。
這是既有狀況（`team.md` 已如實記載），不是本次的遺漏。實際可執行的門檻是
`team.md` 本輪新增的 A／B／C 三項變更範圍內、二元可判的規則。

## 就緒評估

| 面向 | 狀態 |
|---|---|
| Build-ready | ✅ 三個 job 本機驗證通過，`docker-build` 留給 CI |
| Test-ready | ✅ 222/222 綠燈；新測試會被 `ci.yml:135` 自動探索（AC-6） |
| Deployment-ready | ✅ 不涉及 schema、部署設定或環境變數，`validate_env_contract.py` exit 0 |

## 已知限制與待辦

1. **`docker-build` 未在本機執行** —— 明列為未執行項，不是通過。
2. **`team.md` 的 lint 行號已漂移**（`WorkspacePage.tsx:279` → 實測 `301`）。
   本次未觸及前端，且該段落受 practices-discovery gate 治理，故不修改，留待覆核。
3. **`discovered-rules.md` 第 4 項**（`260802-last-login-column` record）仍描述這道檢查為
   no-op。屬另一個 intent 的 record，不逕行修改；`team.md` 已加指標。
4. **新測試尚無 TCMS spec 註解** —— `test-case-authoring.md` §4.4 要求至少一個
   `@api` 或 `@ui`，而這支測試兩者皆無。屬格式契約對「非 HTTP、非 UI 測試」的真實缺口，
   交由下一站 `tcms-test-cases` 判定。
5. **引擎的 `{unit-name}` placeholder 未解析** —— 本 stage 的 consumes 收到字面路徑，
   已手動解析。交接說明見 `<record>/construction/code-generation/memory.md`。
