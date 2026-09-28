# Business Overview — Cloud-360

> 逆向工程產出。**基準 commit `9307dbc`（2026-08-23）**；前一基準為 `c3de2c8`（2026-08-17）。
> **本輪為兩區定向掃描 ＋ 差異標註，不是完整重掃**。節標題後的新鮮度標記：
> **［本輪重寫］**｜**［本輪機械複驗］**｜**［差異標註］**｜**［沿用 `c3de2c8`］**。
> 讀法與跨分支限制見 `reverse-engineering-timestamp.md`。
>
> **用詞提醒**：在標記為［沿用 `c3de2c8`］或［差異標註］的段落內，「本輪／本次」指的是
> **`c3de2c8` 那一輪掃描**；在［本輪重寫］／［本輪機械複驗］段落內，以及任何加 **★** 的
> 條目，指的才是本輪（`9307dbc`，2026-08-23）。
>
> 本檔描述系統「在做什麼、服務誰、產生什麼價值」，不描述實作。實作見
> `architecture.md`、`code-structure.md`、`api-documentation.md`。

## 系統定位 ［沿用 `c3de2c8`］

Cloud-360 是 **AI-native multi-cloud architecture & operations platform**，方法論基礎為
Spec-Driven Development（SRS、user stories、architecture、ADRs）。定位來源為 ADR-0001，
記載於 `aidlc/spaces/default/memory/project.md` 的 `## Decided`。

用一句話描述目前**已實作**的系統：使用者用自然語言描述一套雲端架構，系統產生可編輯的
draw.io 架構圖；接著用一套離線的 Well-Architected 規則引擎對該圖評分、指出風險，並由
AI agent 產生改善建議；圖與評核結果都掛在一個以角色為基礎的權限模型下管理。

「AI-native」在本系統有兩層具體意義，兩層都能在程式碼中找到落點：

1. **產品面**：核心價值鏈（產圖、評核、改善建議）由 LLM agent 驅動，不是表單填寫工具。
2. **開發面**：repo 自身以 agentic workflow 維護（**11 組** gh-aw workflow，涵蓋 contract
   驗證、PR review、UI 回歸測試、部署自癒、spec 與 code 一致性、本機開發文件漂移），
   開發流程本身也是 AI-native。

「multi-cloud」目前的落地程度是**評核與圖形層支援三雲，佈建層尚未實作**：`backend/lenses/`
下有 AWS／GCP／Azure 三份 lens 定義，評核可切換 provider；但基礎設施產出（Terraform／IaC）
對應的業務能力（見下方能力表 D 群）尚無實作模組。

## 服務對象與角色 ［沿用 `c3de2c8`］

系統有 **11 個正式角色**（canonical roles，定義於 `backend/services/rbac.py:23`）。角色不是
單純的權限桶，而是對應到不同的雲端工作職能：

| 角色 handle | 中文顯示名 | 職能定位 |
|---|---|---|
| `Project_Architect` | 專案架構師 | 設計與評核架構的主要使用者 |
| `Developer` | 開發者 | 消費架構設計成果，權限最窄的一般使用者 |
| `Project_Editor` | 專案編輯者 | 可編輯專案資產，不涉管理 |
| `Project_Admin` | 專案管理員 | 專案層級的使用者與權限管理 |
| `FinOps_Analyst` | FinOps 分析師 | 成本相關能力的目標使用者 |
| `SRE` | 網站可靠性工程師 | 維運相關能力的目標使用者 |
| `Ops_Lead` | 維運主管 | 變更審批與維運決策 |
| `Platform_Engineer` | 平台工程師 | IaC 與平台能力的目標使用者 |
| `Security_Reviewer` | 資安審查員 | 合規與資安檢查 |
| `Platform_Admin` | 平台管理員 | 平台層級最高管理權（可核准任何角色） |
| `Platform_Owner` | 平台擁有者 | 平台擁有者 |

另有兩個**歷史別名**會在執行期被正規化，代表文件與程式碼曾用過不同 handle：
`Security_Admin` → `Security_Reviewer`，`Engineering_Manager` → `Project_Editor`。

角色的中文顯示名來源為 `backend/services/user_router.py` 的 `ROLE_DISPLAY_NAMES`；正規化規則
來源為 `rbac.py` 的 `ROLE_ALIASES`。

## 核心業務能力 ［沿用 `c3de2c8`］

系統以 **story id** 為業務能力的單位。權限矩陣涵蓋 **28 個 story**，其顯示名定義於
`backend/services/user_router.py` 的 `STORY_FEATURE_LABELS`（該對照表同時餵給註冊頁的
「可使用功能」目錄）。這是理解產品範圍最直接的一張表：

| 群組 | Story | 業務能力 | 執行期實作狀態 |
|---|---|---|---|
| A 架構設計 | `A1`／`A2`／`A4` | 架構圖生成（三個 story 在執行期視為同一功能） | **已實作** |
| A 架構設計 | `A3` | Well-Architected 評核 | **已實作** |
| B 雲端評選 | `B1` | 單一雲端評選 | 僅存在於權限矩陣 |
| B 雲端評選 | `B2` | 生態相容掃描 | 僅存在於權限矩陣 |
| B 雲端評選 | `B3` | 地緣合規與延遲 | 僅存在於權限矩陣 |
| C 成本 | `C1` | TCO 與流量預算 | 僅存在於權限矩陣 |
| C 成本 | `C2` | 資源優化定價 | 僅存在於權限矩陣 |
| C 成本 | `C3` | Egress 隱性成本 | 僅存在於權限矩陣 |
| D IaC | `D1` | Terraform 產出 | 僅存在於權限矩陣 |
| D IaC | `D2` | IaC 安全掃描 | 僅存在於權限矩陣 |
| D IaC | `D3` | Secret 與敏感值管理 | 僅存在於權限矩陣 |
| E 優化 | `E1` | Right-sizing | 僅存在於權限矩陣 |
| E 優化 | `E2` | 架構現代化 | 僅存在於權限矩陣 |
| E 優化 | `E3` | Runbooks 生成 | 僅存在於權限矩陣 |
| F 維運 | `F1` | 跨雲健康查詢 | 僅存在於權限矩陣 |
| F 維運 | `F2` | 變更與回滾 | 僅存在於權限矩陣 |
| F 維運 | `F3` | 高風險審批閘門 | 僅存在於權限矩陣 |
| G 合規 | `G1` | CSPM 持續合規 | 僅存在於權限矩陣 |
| G 合規 | `G2` | IAM 最小權限 | 僅存在於權限矩陣 |
| G 合規 | `G3` | Policy-as-Code | 僅存在於權限矩陣 |
| H 平台整合 | `H1` | 內部 API 註冊 | 僅存在於權限矩陣 |
| H 平台整合 | `H2` | Agent 存取邊界 | 僅存在於權限矩陣 |
| H 平台整合 | `H3` | MCP 與 Skill 生命週期 | 僅存在於權限矩陣 |
| J 系統管理 | `J1` | 登入能力（不列入註冊功能摘要） | **已實作**（無獨立 guard） |
| J 系統管理 | `J3a` | 使用者設定 | **已實作** |
| J 系統管理 | `J3b` | 細項設定（權限矩陣維護） | **已實作** |

**實作狀態的判定依據（本次重新實測）**：對 28 個 story id 在 `backend/services/`
（排除 `rbac_seed_data.py`）與 `frontend/src/`（排除產生的 `api.d.ts`）全庫計數引用。結果：

- `A3`（23 處，7 檔）、`J3a`（24 處，8 檔）、`J3b`（10 處，4 檔）、`A1`（8 處，5 檔）、
  `A2`／`A4`（各 4 處）—— 有 guard、路由、導覽等多處引用。
- `B1`–`H3` 與 `J1` 共 22 個 story **各只出現 1 次**，且該次都在 `user_router.py` 的
  `STORY_FEATURE_LABELS` 顯示名對照表內，沒有任何端點或頁面掛在它們上面。

這代表一個對下游 stage 重要的事實：**權限矩陣的廣度（28 story）遠大於實作的廣度（6 story）**。
矩陣先行描述了完整產品願景，實作目前落在 A 群與 J 群。新增功能時 story id 已預留，
不需要擴充矩陣維度；但也代表矩陣的 308 列中有大部分目前不影響任何執行期行為。

### J5 授權審核的定位

`J5` 是「使用者註冊後需管理員授權」這條流程的**功能代號**，出現在
`backend/database.py::_ensure_j5_schema()` 與 `backend/tests/test_j5_authz.py`，
但**不在 28 個 story id 之列**，也沒有專屬權限旗標。它的權限實際掛在 `J3a`
（授權申請的核准／駁回端點 guard 為 `J3a.edit`）。

## 業務流程主線 ［差異標註］

### 主線一：帳號取得與授權

1. 新使用者在註冊頁選一個角色送出申請。註冊頁的角色功能目錄由
   `GET /api/auth/roles/catalog` 動態產生，讓申請者在送出前看得到該角色能用哪些功能。
2. 帳號建立時 `authorization_status = 'pending'`，同時建立一筆授權申請。
3. **pending 狀態的使用者無法使用任何業務功能** —— 權限判定的第一道閘門即檢查此狀態，
   未核准時所有 story 權限一律為否。
4. 管理員在授權申請頁核准或駁回。核准權受 BR-04 限制：`Platform_Admin` 可核准任何角色；
   `Project_Admin` 不可核准 `Platform_Admin` 與 `Platform_Owner`。
5. 核准後 `authorization_status = 'approved'`，角色寫入，使用者取得該角色的能力集合。

### 主線二：對話產圖（A1）

使用者在工作區以自然語言描述需求，AI Design Agent 逐步回覆並產出 draw.io 架構圖 XML，
過程即時串流到畫布。圖可存檔、可分享給其他使用者、可多人即時共編，並附帶一段對話紀錄（A4）。

**平台自我竄改預檢**：進入 agent 之前有一道 `prompt_guard` 前置檢查（`prompt_guard.py`，
63 LOC，純函式）。命中時**不呼叫 LLM**，直接回固定的拒絕訊息。這道檢查的存在對應
`project.md ## Mandated` 的既有規則。

### 主線三：架構評核與改善（A3）

對一張架構圖（既有圖或上傳的 XML）執行 Well-Architected 評核：

1. **規則階段**：離線規則引擎解析圖形結構，產出支柱分數與風險發現（findings）。這一階段
   **不呼叫任何雲端 API、不需要雲端憑證**，完全依賴圖形本身的語意。
2. **Lens 階段**：套用可自訂的 Lens（相容 AWS Well-Architected Custom Lens 格式，
   支援 AWS／GCP／Azure 三份預設 lens）計算風險規則。
3. **建議階段**：Review Agent 依 findings 串流產出改善建議。此階段有逾時保護；
   逾時或失敗時評核仍以「僅規則結果」的狀態完成，**不會整體失敗**。

另有一條**雙 agent 協作**路徑：Design Agent 與 Review Agent 互相對話，最多 2 輪，
目標是產出「lens 總分 ≥ 80 且無 HIGH_RISK」的架構圖。

### 主線四：權限治理與帳號稽核（J3a／J3b）

管理員可在 Admin 區維護三件事：使用者清單與角色指派、授權申請審核、以及
**11 角色 × 28 story 的權限矩陣本身**。矩陣是執行期的權限真實來源 —— 改矩陣即刻改變
所有使用者能做什麼，不需要改程式碼或重新部署。

矩陣的三個旗標語意（來源 `rbac.py`）：

- **檢視（view）**：實際判定為「勾了 view **或** edit **或** review 任一即可檢視」。
- **編輯（edit）**：可做除審核外的一切；勾選時自動開啟 view。
- **審核（review）**：可檢視加審核，不可編輯。

**帳號活動稽核（本輪已落地）**：使用者清單現在額外提供每個帳號的**最後活動時間**與
**逾期標示**，並支援分頁瀏覽。業務語意（來源 `backend/services/activity.py` 與
`models.py` 的欄位註解）：

| 概念 | 語意 | 政策值 |
|---|---|---|
| 最後活動時間 | 任何以有效憑證發出的請求都更新它（**不是只有登入**） | 同一帳號至多每 **5 分鐘**寫一次（`ACTIVITY_WRITE_THROTTLE`） |
| 從未活動 | 欄位為空。上線前的既有帳號皆為此態 | 刻意不設 `server_default` —— 有預設值會讓「從未活動」與「剛建立」無法區分 |
| 逾期 | 距今超過門檻即標示 | **90 天**（`OVERDUE_THRESHOLD`） |
| 逾期標示的例外 | 「從未活動」的帳號**不套用**逾期標示 | — |

節流機制是刻意的取捨：以「最後活動時間的精度」換「每個請求不都變成一次資料庫寫入」。
下游若需要更高精度的稽核（例如逐次登入紀錄），那是**新的能力**，不是現有欄位的調參。

## 業務邊界與非目標 ［沿用 `c3de2c8`］

依 `project.md` 的 `## Scope Overrides`：

- **在範圍內**：SRS、architecture diagrams、user stories、ADRs、IaC generator 設計、
  agent routing 設計、MCP 與 skill 管理規格、驗證腳本、baseline CI、自有 staging 的部署與維運。
- **在範圍外（除非新 ADR 核可）**：雲端供應商 production 環境、production 憑證、
  環境相依的機密、直接對 production 套用 IaC、破壞性雲端操作、原生 iOS／Android app。

程式碼層面可觀察到的邊界一致性：Well-Architected 評核**不呼叫 AWS API**
（`wa_rule_engine.py` 與 `wa_lens_engine.py` 都是純函式，不連外、不讀 DB），
因此不需要任何雲端憑證即可運作。這是刻意的設計，與「production 憑證在範圍外」一致。

## 開發流程層的業務資產 ［本輪重寫］

這些不是產品功能，但是本專案業務價值的一部分（「開發面的 AI-native」），
且已有可執行的實作。**這一層是本輪 reverse-engineering 唯二實掃的範圍**，
架構細節見 `architecture.md` 的三節「開發流程層架構」。

### 驗證與同步腳本（本基準 `9307dbc` 上為 4 支）

| 資產 | 落點 | 說明 |
|---|---|---|
| Repo contract 驗證 | `scripts/validate_repo_contract.py`（405 LOC） | 必要文件、必要文字、文件語言、禁止路徑與內容；CI 第一關 |
| 三環境設定契約 | `scripts/validate_env_contract.py`（315 LOC） | dev／CI 測試／部署三者不得互相滲透，亦不得互相漏接；同屬 CI 第一關 |
| 測案管理同步 | `scripts/tcms_sync.py`（515 LOC） | 手動案例（建立＋更新）與自動化案例（只更新）分開同步進自架 Kiwi TCMS |
| 測案機械驗證 | `scripts/tcms_validate.py`（360 LOC） | 必填欄位、空洞預期結果、追溯目標存在、API/UI 比對 `openapi.json` 與 `App.tsx` |
| 測案撰寫標準 | `TESTING.md`（242 LOC） | 測試案例格式的唯一真實來源 |

> **`origin/ut` 上已是 7 支。** 前一版 codekb 記載「ADR-0012 的同步實作在 PR #508 尚未進
> `ut`」——**該記載已過期**：本輪以 `gh pr view 508` 實測為 `MERGED`（2026-08-22），
> `git ls-tree origin/ut scripts/` 確認 `aidlc_sync_push.py`／`aidlc_sync_pull.py`／
> `aidlc_sync_buglist.py` 三支已在 `ut` 上。**但它們與 ADR-0013 及
> `project.md ## Forbidden` 的新規則構成待解衝突**（見 `architecture.md` 的
> 「一項待解衝突」）——這三支的去留尚未定案，因此本節不把它們列為既定資產。

### 11 組 gh-aw agentic workflow

開發流程本身由 11 組 LLM 驅動的 agentic workflow 維護（`engine: copilot`，
gh-aw 編譯器 `v0.81.6`；`origin/ut` 已升至 `v0.86.2`）。
**只有 `ui-regression` 是真閘門**，其餘 10 組是提問／自動修／開 issue 型：

| 型態 | workflow | 業務作用 |
|---|---|---|
| **阻擋型（1）** | `ui-regression` | 對短生命週期 stack 跑 Playwright、回報 Kiwi TCMS；`.stats.unexpected` 非 0 即擋 |
| PR 上提問（4） | `pr-reviewer`／`code-drift-alert`／`local-dev-drift`／`contract-guard` | 分別審 PR 慣例、契約性程式改了 spec 沒跟、`LOCAL-DEV.md` 前置條件漂移、repo contract |
| PR 上自動修（1） | `lint-fix` | 只修機械性、零判斷的 lint error |
| 開 issue（4） | `spec-sync`／`daily-digest`／`release-watch`／`deploy-doctor` | spec 漂移、每日匯總、上游 release 追蹤、部署失敗自癒 |
| issue 上分類（1） | `issue-triage` | 分類、貼標、追問缺漏 |

**分界原則與 repo 既有實務一致**（ADR-0012 引為判準）：`deploy-doctor` 只診斷不修
（明文寫「so a human can fix」）、`lint-fix` 自動修但僅限機械性問題。

### AI-DLC 自身的狀態，是一份可被消費的資產（也是一份有坑的資產）

AI-DLC 把每個 intent 的進度寫在 `<record>/aidlc-state.md`、註冊在 `intents.json`、
把事件流寫進 `<record>/audit/` 的 per-clone shard。這讓「做到哪、卡在哪」成為可程式化
消費的資料——**ADR-0012／ADR-0013 的 GitHub 同步構想正是建立在這上面。**

但本輪實掃揭露四件消費者必須先知道的事（細節見 `architecture.md`）：

1. `intents.json` 的 `status` 只有 `in-flight`／`complete` 兩值，**沒有 parked／failed**，
   且與狀態檔的 `Status` **實測已分岔 1/6**——兩者不是同一事實的兩份拷貝。
2. `Status` 只有 `Running`／`Completed`，**沒有「等待核准」這個值**。
   看板若要有 "In review"，來源只能是 stage checkbox。
3. `[ ] — SKIP`（不適用）、`[S] — EXECUTE`（被跳過的欠債）、`[ ] — EXECUTE`（待辦）
   **是三種語意，但都長得像「沒打勾」**。
4. **作用中 intent 的 record 目前完全未進版控**，而 `active-intent` 游標永遠被 gitignore。
   任何只看已提交內容的機制，**更新頻率由人什麼時候 commit 並合併 record 決定**，不由排程決定。

## 詞彙表 ［本輪擴充］

| 詞 | 意義 |
|---|---|
| **story** | 業務能力的最小權限單位，以 `A1`、`J3a` 等 id 標示。權限矩陣的一個維度 |
| **canonical role** | 11 個正式角色 handle。非正式別名會在執行期被正規化 |
| **permission matrix** | 11 角色 × 28 story = 308 列的 view／edit／review 旗標表，執行期權限真實來源 |
| **authorization status** | 帳號的授權狀態，`pending`／`approved`／`rejected`。非 `approved` 時所有業務權限為否 |
| **最後活動時間** | 帳號最近一次以有效憑證發出請求的時刻；節流 5 分鐘。空值代表「從未活動」 |
| **逾期** | 最後活動距今超過 90 天。「從未活動」不套用此標示 |
| **lens** | Well-Architected 評核準則集合，相容 AWS Custom Lens 格式，per-cloud 各一份 |
| **finding** | 評核產出的單一風險發現，可帶 `HIGH_RISK` 等風險等級 |
| **pillar score** | 依 Well-Architected 支柱切分的分數 |
| **A1／A3 pipeline** | 兩條 LLM agent 串流管線，前者產圖、後者評核與建議 |
| **Design Agent／Review Agent** | 兩個 LLM agent 角色；協作模式下互相對話最多 2 輪 |
| **BR-04** | 核准權限限制規則：`Project_Admin` 不可核准平台級角色 |
| **prompt guard** | 進 agent 前的平台自我竄改預檢；命中即不呼叫 LLM |
| **LLM provider** | LLM 存取模式，`openrouter`（部署預設）或 `cli`（本機已登入的 claude CLI） |

### 開發流程層詞彙（本輪新增）

| 詞 | 意義 |
|---|---|
| **intent** | AI-DLC 的一個需求生命週期。在 `intents.json` 有一列、在 `aidlc/spaces/<space>/intents/<record>/` 有一個 record 目錄 |
| **record** | 某個 intent 的產出目錄，含 `aidlc-state.md`、各 stage artifact 與 `audit/` shard |
| **stage checkbox** | `aidlc-state.md` 的逐 stage 進度標記，六值：`[ ]`／`[-]`／`[?]`／`[R]`／`[x]`／`[S]` |
| **EXECUTE／SKIP 後綴** | 與 checkbox **正交**的一維：`SKIP` = 該 scope 不含此 stage；`EXECUTE` = 在 scope 內 |
| **audit shard** | `<record>/audit/<host>-<clone8>.md`，append-only 的事件流。唯一帶時間戳、唯一說得出 gate 被拒過幾次的來源 |
| **gh-aw** | GitHub Agentic Workflows。作者寫 `.md`，`gh aw compile` 產出 `.lock.yml`；**Actions 只執行後者** |
| **safe-outputs** | gh-aw 的受管輸出機制。agent 本身不持有寫入權限，寫入由框架以受限形狀代理 |
| **受管區塊** | issue 內文中 `<!-- aidlc:managed -->` 夾住的部分，由 repo 覆寫；標記外的人寫內容永不觸碰（ADR-0012） |
