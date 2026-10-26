# Reverse Engineering 時間戳

> **新鮮度標記（全 codekb 適用）｜repo `cloud`｜mode Focused merge（STALE）＋ 跨 store 合併**
>
> 本輪把兩份既有 store 合併成一份。**正本自本輪起為 `aidlc/spaces/default/codekb/cloud/`**，
> `codekb/cloud-360/` 降為歷史副本（**不刪除，但不再更新**）。
> `codekb/chiton` symlink 已由 `cloud-360` 改指 `cloud`，使本 worktree 的
> `basename(projectDir)` 推導路徑落在正本上。

## 掃描元資料

| 欄位 | 值 |
|---|---|
| 執行時刻（UTC） | `2026-10-01T23:24:20Z`（`date -u`，**實跑**） |
| Commit（full） | `34aeef38350b0f2865b025446528bd32143804bf`（`git rev-parse HEAD`，**實跑**） |
| Commit（short） | `34aeef3` |
| **本輪進行中 HEAD 曾前進** | **是 → `c3d9ef8`**（見下方「基準 commit 在本輪中途前進」） |
| 分支 | `danniel/docs/orchestration-brain-ideation` |
| Worktree | `/Users/jiangzhengdao/orca/workspaces/cloud-360/chiton` |
| Intent | `260920-orchestration-brain` |
| 模式 | **Focused merge（STALE）**＋**跨 store 合併**（以 `cloud-360/` 為底、疊 `cloud/` 較新區塊、加本輪新發現） |
| Active space | `default` |
| Codekb 目錄 | `aidlc/spaces/default/codekb/cloud/`（引擎 `workspace codekb` 解析為 `codekb/chiton/` → symlink → `cloud/`） |
| 專案類型 | brownfield |
| Pipeline | reverse-engineering link 2／FINAL（architect synthesis） |
| 上游輸入 | `<record>/inception/reverse-engineering/developer-scan.md`（link 1，66 KB／13 節） |
| Depth | Standard（`kind: partial`，見下方深度分佈） |

### 基準 commit 在本輪中途前進（已複驗，結論不變）〔A〕

本輪**開始時** HEAD 為 `34aeef3`，**寫完 9 份檔時**已前進到
`c3d9ef8`（`文件(local-dev): 補完 cli 模式退役的同步，並修掉一個會誤判新舊碼的排錯判準`）
——由他人在本輪進行中 commit，不是我寫的。

`[跑]` `git diff --stat 34aeef3..c3d9ef8` 的完整內容為**三個檔**：

```
 LOCAL-DEV.md                                                    |   26 +-
 .../inception/reverse-engineering/developer-scan.md             | 1352 ++++++---
 .../inception/reverse-engineering/memory.md                     |   15 +
```

**處置與複驗結果**：

1. **零應用程式碼變動**——`backend/`、`frontend/`、`deploy/`、`schema_rbac.sql`、
   `openapi.json`、`ws-contract.json`、`.github/` 全部未動。
   故本 codekb 對程式的所有事實在 `c3d9ef8` 上**同樣成立**。
2. **`LOCAL-DEV.md` 的 11 處引用已逐行重驗**（`:23`／`:38`／`:39`／`:78`／`:81`／
   `:219`–`:223`／`:237`）`[跑]`——該 commit 改的 26 行不在這些位置，
   **11 個行號在 `c3d9ef8` 上全部仍指向本檔引用的同一句話**。
3. **`developer-scan.md` 我讀到的就是最終版**：本輪讀取時它是未 commit 的工作樹版本，
   而 `c3d9ef8` 正是把那些修改收進版控，位元組數（65,940）一致。

**本檔其餘各處一律以 `34aeef3` 為基準標示**，因為那是絕大多數事實被查證的時點；
上述三項是唯一需要跨到 `c3d9ef8` 的差異，且都已複驗。

---

## 新鮮度等級（每份 artifact 逐節標註，不得整份視為同一新鮮度）

本 codekb 的每一節都帶下列五個等級之一。**沒有標記的段落視為 C 級**。

| 等級 | 意義 | 可信賴程度 |
|---|---|---|
| **A** | 本輪（`34aeef3`，2026-10-02）實證：開檔讀過／實際執行過／以程式計算過 | 可直接引用 |
| **B** | 本輪部分實證：該節的部分行是本輪實讀，其餘沿用 | 逐句看標記，不可整節引用 |
| **C** | 承 `codekb/cloud-360@2026-09-22`（commit `dc4b687`），**本輪未複驗** | 引用前自行複驗 |
| **D** | 承 `codekb/cloud@2026-10-01`（commit `5fd8f14`），**本輪未複驗** | 引用前自行複驗 |
| **E** | **未掃**：本輪完全沒碰，且兩份 store 的記載也未複驗 | 不可當事實使用 |

### 證據標記（句級，與等級並用）

| 標記 | 意義 |
|---|---|
| `[讀]` | 本輪開檔讀內容，行號為本輪複驗值 |
| `[算]` | 本輪只做 grep／計數／程式解析，未讀全文 |
| `[跑]` | 本輪實際執行指令，結論即其輸出 |
| `[承:cloud-360@2026-09-22]` | 沿用歷史副本記載，本輪未複驗 |
| `[承:cloud@2026-10-01]` | 沿用本 store 前一輪記載，本輪未複驗 |
| `[未掃]` | 本輪完全未碰 |

---

## 深度分佈（誠實紀錄）

### Deep（本輪**整檔**讀過，寫進 `analyzed.paths`）

共 **7 條**。判準是「整個檔案的內容本輪都被讀過」，不是「這個檔案本輪被提到過」：

| 路徑 | 行數 | 本輪做了什麼 |
|---|---|---|
| `backend/main.py` | 67 | link 1 全 67 行 `[讀]`；本輪另 `[算]` 複驗 `include_router` 8 條與 import 清單 |
| `backend/services/llm_provider.py` | 178 | link 1 全 178 行逐行 `[讀]` |
| `backend/services/design_agent.py` | 218 | link 1 逐行 `[讀]`，`_progress_queue` 13 處命中逐段複驗 |
| `backend/requirements.txt` | 18 項宣告 | link 1 全檔 `[讀]`；本輪以程式重新解析釘選分佈 `[跑]` |
| `backend/Dockerfile` | 31 | 本輪全檔 `[讀]` |
| `frontend/package.json` | — | link 1 全檔 `[讀]` |
| `openapi.json` | — | 本輪以 Python 完整解析全部 path／operation／schema `[跑]` |

### 刻意**不**寫進 `analyzed.paths` 的（深度切分落在檔案內部）

依 `project.md` 的既有規則（「`analyzed.paths` 的粒度是檔案或目錄、表達不了行區間，
處置是把該元件留在淺掃區……寧可低報覆蓋」）：

| 路徑 | 本輪實讀的範圍 | 未讀的部分 |
|---|---|---|
| `backend/database.py` | `init_db()`（`:85–96`）、7 支 `_ensure_*` 定義行、12 處 `except Exception` 行號、`:199–231` 的 `_ensure_vector_extension` docstring | 其餘 656 行 |
| `backend/services/brain_router.py` | docstring `:1–31` ＋ 函式骨架 | **455 行的本體** |
| `backend/services/user_router.py` | `:80–92` | 892 行的本體 |
| `backend/services/agent_router.py` | `:115–135` | 其餘 |
| `backend/services/wa_collab_orchestrator.py` | `:70–90` | 其餘 |
| `backend/services/review_agent.py` | `:1–12`（docstring ＋ imports） | 其餘 193 行 |
| `backend/services/langgraph_runtime.py` | `:1–25` | 其餘 140 行 |
| `backend/cost/advice_orchestrator.py` | `:1–82` | `:83–358` |
| `backend/cost/advice_stream_router.py` | `:5–9`、`:83`、`:173` | 其餘 |
| `backend/tests/helpers.py` | `:1–25`（psycopg mock 段） | 其餘 |
| `backend/.env.example` | `LLM_PROVIDER`／`OPENROUTER`／`REDIS_*`／`OLLAMA_*` 段 | 其餘 |
| `deploy/docker-compose.deploy.yml` | 以程式解析 service／network／volume 區塊結構 ＋ image 行 ＋ redis 相關註解 | 其餘（384 行） |
| `deploy/.env.example`、`deploy/render-env.sh` | `REDIS_*`／`OLLAMA_*` 段 | 其餘 |
| `schema_rbac.sql` | `CREATE TABLE` 20 處的行號、`projects` 區塊 `:327–334`、`user_diagrams.system_id` 的 7 處、`DELETE FROM role_permissions`（`:443`） | 其餘（>770 行） |
| `.github/workflows/ci.yml` | 5 個 job 的標題行 ＋ 14 條 `run:` 步驟 | 每個 step 的實作本體 |
| `frontend/src/App.tsx` | 路由表（13 條，附行號） | `RouteGuard`／`Layout` 包裹細節；160 行中約 100 行 |
| `DEPLOY.md`、`LOCAL-DEV.md` | 階層三表段（`DEPLOY.md:224,303–419`）、`LLM_PROVIDER`／Redis 段（`LOCAL-DEV.md:23,34–52,78,219–237`） | 其餘 |

### 完全未掃（E 級）

`backend/prompts/`、`backend/lenses/`、`backend/services/brain_ws_contract.py` 的契約本體（783 行）、
`frontend/src/pages/` 的任何元件內容（含 `BrainPage.tsx` 403 行）、`frontend/src/components/`、
`frontend/src/utils/`、`frontend/src/hooks/`、`frontend/tests/e2e/` 的 spec 內容、
`.github/workflows/deploy.yml`、11 支 gh-aw workflow 的 `.md` 內容、`ws-contract.json` 的內容
（只取頂層 key 與位元數）、`backend/tests/` 46 支測試檔的**內容**（只取檔名、`@given`／`TestClient` 計數，
以及 `test_llm_provider.py` 的類別／測試名稱列）。

### 為什麼是 `kind: partial` 而不是 `full`

`kind: full` 要求 `analyzed.paths` 含 `./` 且該次真的逐一深讀。本輪：前端零元件內容、
`backend/tests/` 零測試檔內容、多支模組只取 docstring 或片段、兩個目錄完全未開啟
——**任一條成立即為 partial**。使用者本輪選的是「把 `cloud/` 當正本並整份重寫」，
那是**廣度**（輸出被取代的範圍）的選擇，不是深度的宣稱；兩者分開判。

---

## 本輪實際執行過的指令（`[跑]` 的完整清單）

**只有下列項目是本輪的執行結果**，其餘任何「通過／全綠」字樣都不是本輪驗證的：

| 指令 | 結果 |
|---|---|
| `date -u`、`git rev-parse HEAD` | 見上表 |
| `git log --oneline -1 -- <path>`（6 次） | 各新檔的落地 commit 與日期 |
| `wc -l` / `wc -c`（多次） | 全部 LOC 與位元數 |
| Python 解析 `openapi.json` | 42 path／55 operation／39 schema／3.1.0 |
| Python 解析 `backend/requirements.txt` | 18 項宣告＝3 精確 pin ＋ 1 下限 ＋ 14 未 pin |
| Python 解析 `deploy/docker-compose.deploy.yml` 區塊結構 | **6 個 service**、2 個 network、3 個 volume |
| Python 解析 `backend/models.py` | 13 個 `__tablename__` ＋ 1 個 association table |
| Python import `services.rbac_seed_data` / `services.rbac` | seed **308 列**、`CANONICAL_ROLES` **11** |
| `grep -c` / `grep -rl`（多次） | `@given` 48 處／16 檔、`TestClient` 6 檔＋helpers、`fetch(` 62 處／15 檔、`Authorization: Bearer` 36 處 |
| `bun … engine workspace codekb` | `aidlc/spaces/default/codekb/chiton/` |
| `bun … engine workspace codekb-scope-diff --repo cloud` | **STALE**（22 條 analyzed path 全部變動） |
| `bun … engine workspace codekb-scope-diff --repo cloud --mint --paths <7 條>` | `4b4780442de22b80d7b850f24fd18cedf53edcef` |
| `ln -sfn cloud chiton` | symlink 已改指 |

link 1 另實跑了（本輪未重跑，但其輸出逐字可引用，標 `[跑:link1]`）：
`python3 -m unittest discover -s tests`（**419 tests, OK**）、
`npm run lint`（**0 errors, 2 warnings**）、
`python3 scripts/validate_cost_calculator_boundary.py`（exit 0）、
`python3 scripts/validate_pricing_lookup_boundary.py`（exit 0）。

### 本輪與 link 1 都**未**執行的檢查（不得記為通過）

`validate_repo_contract.py`、`validate_env_contract.py`、`npm run build`（`tsc -b`）、
`npm run check:types`、`npm run check:ws-types`、`dump_openapi.py --check`、
`dump_ws_contract.py --check`、Playwright e2e、`docker-build`、任何 compose stack。

---

## Coverage backstop — `codekb-scope-diff` 的結果（誠實陳述）

| 執行 | 輸出 |
|---|---|
| `codekb-scope-diff --repo cloud`（新鮮度） | **`STALE`** —— `cloud/` 於 `5fd8f14` 建立時的 22 條 `analyzed.paths` **全部 22 條**的內容都已變動 |
| `codekb-scope-diff --repo cloud-360`（新鮮度，參考） | **`STALE`** —— 其 33 條 analyzed path 全部變動 |
| `codekb-scope-diff --repo cloud --mint --paths <本輪 7 條>` | `4b4780442de22b80d7b850f24fd18cedf53edcef`（已填入下方 `fingerprint:`） |
| `codekb-scope-diff --repo cloud --compare <scope-draft>` | **`NARROWER`**（逐字輸出見下） |

### compare 的實際結果：`NARROWER`

**逐字輸出**（store intent `261001-a2-langgraph`；incoming intent `260920-orchestration-brain`）：

```
NARROWER: the incoming scope no longer claims verified deep coverage for:
  - backend/services/agent_router.py
  - backend/services/langgraph_runtime.py
  - backend/services/review_agent.py
  - backend/services/review_orchestrator.py
  - backend/services/review_router.py
  - backend/services/wa_score_service.py
  - backend/services/wa_collab_orchestrator.py
  - backend/services/wa_lens_engine.py
  - backend/services/wa_rule_engine.py
  - backend/services/llm_limits.py
  - backend/tests/test_langgraph_runtime.py
  - backend/tests/test_langgraph_migration.py
  - backend/test_agent.py
  - frontend/src/App.tsx
  - frontend/src/pages/AssessmentPage.tsx
  - scripts/smoke_langgraph_openrouter.py
  components: architecture-generation, langgraph-runtime, wa-review, lens-management,
              llm-gateway, frontend-routing, assessment-page
```

即 **16 條路徑 ＋ 7 個元件**由「已驗證的 deep 覆蓋」降級。這是**預期且正確**的結果
——本輪的 deep 集合刻意低報（見「深度分佈」），而降級的那些路徑**本輪確實沒有重新讀過**。
**下游不得再把上列 16 條當成已驗證。**

### ⚠️ 第一次 compare 的輸出無效，必須揭露

**我第一次跑 compare 時回的是 `COVERS`，而那個結果是假的。**
原因：stage 檔逐字要求「**Coverage backstop - run BEFORE writing**（the compare needs the
prior store unchanged）」，而我**先把新的 9 份檔寫進 `codekb/cloud/`，才跑 compare**。
於是工具讀到的「store」已經是我自己剛寫的版本，而 `--compare` 的對象是它的逐字副本
——**它比較的是同一份檔案的兩個副本，必然回 `COVERS`**。

**修復方式（已執行）**：以 `git show HEAD:<timestamp 路徑>` 取回 `b4f0cdc` 當時的
prior store，暫時還原到 codekb 目錄，重跑 compare 取得上方的 `NARROWER`，
再把本輪版本放回（以 `diff -q` 確認位元相同）。
**上方的 `NARROWER` 是對真正的 prior store 跑出來的。**

> **為什麼要把這件事寫進 codekb 而不是修掉就算了**：`COVERS` 與
> 「真的保留了前一輪的覆蓋」在輸出上長得一模一樣。若我只留下第一次的輸出，
> 下一輪的人會以為 22 條 deep 路徑都還有效，而實際上有 16 條本輪沒人讀過。
> 這與 `project.md` 已記的那條教訓同型（`UNKNOWN_SCOPE` 在輸出上跟通過檢查長得一樣），
> 只是這次的假陽性是**我自己的執行順序**造成的，不是工具的歧義。

> **附帶更正**：第一版草稿把 demote 數寫成「18 條、維持 deep 只有 3（共 4）條」，
> 那是我手數的，**錯了**。工具實算為 **22 條中保留 6 條（`backend/main.py`、
> `backend/services/design_agent.py`、`backend/services/llm_provider.py`、
> `backend/requirements.txt`、`backend/Dockerfile`、`openapi.json`）、降級 16 條**。
> 現以工具輸出為準。

### 元件命名的一處刻意對齊

本輪原本把五個深讀元件改成中文名，結果 compare 把**全部 9 個**前一輪元件報成已降級
——包括 `backend-app-shell` 與 `openapi-contract` 這兩個**本輪確實深讀過、範圍也相同**的。
原因是 rerun guard 對 `analyzed.components` 做**字面比對**，改名等於宣告放棄。

處置：把這兩個改回 `cloud/` 既有的 kebab-case 英文名，使 linkage 保留；
其餘三個因**範圍確實比前一輪窄**而使用新名，如實呈現為降級：

| 本輪元件名 | 前一輪對應 | 關係 |
|---|---|---|
| `backend-app-shell` | `backend-app-shell` | **範圍相同**（`main.py` 整檔），沿用原名 |
| `openapi-contract` | `openapi-contract` | **範圍相同**（`openapi.json` 完整解析），沿用原名 |
| `design-agent-core` | `architecture-generation` | **本輪較窄**（前一輪含 `agent_router` ＋ `design_agent`，本輪只有 `design_agent`） |
| `llm-provider-gateway` | `llm-gateway` | **本輪較窄**（前一輪含 `llm_provider` ＋ `llm_limits`，本輪只有 `llm_provider`） |
| `backend-container-image` | （前一輪無此元件） | 新增 |

`component-inventory.md` 的五個深讀 H3 標題與上表第一欄**逐字一致**。

`cloud-360/` 前一輪的 33 條 deep（含 `models.py`、`database.py`、`rbac.py`、`auth.py`、
`activity.py`、`prompt_guard.py`、全部 cost 入口、deploy 五檔、`ci.yml`、
`frontend/src/config/api.ts`、`context/`、`cost/slotRegistry.tsx`）**一律以 C 級承接**，
本輪未複驗。

---

## 合併完成度（逐檔誠實申報）

| Artifact | 合併程度 | 未承接的內容 |
|---|---|---|
| `reverse-engineering-timestamp.md` | **完全重寫** | — |
| `architecture.md` | **完整合併** | — |
| `component-inventory.md` | **完整合併** | — |
| `code-quality-assessment.md` | **完整合併** | — |
| `business-overview.md` | **完整合併** | `cloud/` 的 C1 舊實作敘述（`cost_router`／`sku_mapper`／Calculator runner）**刻意不承接**，理由見該檔 |
| `api-documentation.md` | **完整合併** | `cloud/` 的「`/api/cost` 9 個 operation」**刻意不承接**（已被 HEAD 的 10 個取代） |
| `code-structure.md` | **完整合併** | — |
| `technology-stack.md` | **完整合併** | — |
| `dependencies.md` | **完整合併** | `cloud/` 的「`backend/cost/` 內部與八類掛鉤」僅以指標保留（原文在歷史副本與更早的 record 內，本輪未複製逐表內容） |

### 仍只存在於 `codekb/cloud-360/`、本輪**未**逐字搬過來的內容

歷史副本不刪除，下列內容若要引用請直接開 `codekb/cloud-360/`：

1. `business-overview.md` 的「主線一～五」散文**已整段承接**，但其中「`design_agent` 以子行程驅動
   `claude` CLI」一句**本輪已證實為假**（見本 codekb 的更正），故搬過來的版本已改寫。
2. `component-inventory.md` 淺掃區的「資料資產」「部署工作流程與 gh-aw」兩節的
   **逐支 workflow 名稱清單**已承接，但 11 支 gh-aw 的內容兩輪皆未讀（E 級）。
3. `code-quality-assessment.md` 的 T-1～T-13 **全部承接並重新編號／更新**；
   新增 T-14～T-18。無技術債項目被丟棄。
4. `cloud-360/` 各檔檔頭的「本輪未以任何測試、lint 或 CI validator 的執行結果作為事實來源」
   這段**自我限制聲明不適用於本輪**——本輪確實有 `[跑]` 的結果（見上表），
   故改為逐項列出跑了什麼、沒跑什麼。

---

## 本輪重點發現索引（含它推翻了哪一份 store 的哪一句）

| # | 發現 | 等級 | 所在 artifact | 推翻了什麼 |
|---|---|---|---|---|
| 1 | **MCP 零基礎設施**，且 `MCP` 這個字已被 RBAC story `H3` 佔用（`user_router.py:85`） | A | `architecture.md`、`dependencies.md`、`technology-stack.md` | 兩個 store 皆**未記載**（新增，非更正） |
| 2 | **`design_agent._progress_queue` 模組級全域，併發不安全**；危害是**跨使用者送錯架構圖 XML** | A | `code-quality-assessment.md` T-14、`architecture.md` 約束四 | `cloud/` 只寫「非 thread-safe」未寫後果；`cloud-360/` 的 T-3 是另一件事（多 worker），**兩者並立不合併** |
| 3 | **`llm_provider.py` 已重寫（237→178 行）**，`LLM_PROVIDER=cli` **退役** | A | `technology-stack.md`、`code-quality-assessment.md` | `cloud/`「`LLM_PROVIDER`：`openrouter`｜`cli`」、`cloud-360/`「兩種 provider 的非對稱互斥」皆過時 |
| 4 | **brain demo-scope gateway 存在且已掛載**（`/api/brain/ws`、`BrainPage.tsx`、`/brain` 路由） | A | `architecture.md`、`component-inventory.md`、`business-overview.md` | 兩個 store 皆**未記載**。**本輪最重要的一項** |
| 5 | **WS 契約鏈與兩道 CI 漂移閘門已存在**（`brain_ws_contract.py` → `ws-contract.json` → `ws-contract.d.ts`） | A | `api-documentation.md`、`dependencies.md` | **直接推翻** `cloud-360/architecture.md` 約束二「新 WebSocket 契約沒有任何機械閘門」 |
| 6 | **階層三表已在 `schema_rbac.sql` ＋ migration，但不在 ORM／router／service** | A | `architecture.md`、`component-inventory.md` | 推翻 `project.md` 記載的「`system_id` 命中 0 次」 |
| 7 | **Redis ＋ Ollama 兩個服務已進部署堆疊，`db` 已升 `pgvector/pgvector:pg18`**；deploy stack 由 4 → **6 個 service** | A | `architecture.md` 約束八、`technology-stack.md`、`dependencies.md` | **推翻兩個 store**：`cloud-360/`「4 個服務／無 Redis／零基礎設施用途」、「Redis 是全新的第 5 個服務」。**link 1 也沒發現這一項** |
| 8 | **`backend/Dockerfile` 已無 Node 22 ＋ `claude` CLI** | A | `technology-stack.md`、`dependencies.md`、`component-inventory.md` | **推翻兩個 store**的「image 內含 Node／CLI」與「CLI 缺席會在請求時失敗」 |
| 9 | **LLM 棧已全數收斂到 LangGraph ＋ OpenRouter**；`claude_agent_sdk` 全樹零 import 且有兩個 `assertNotIn` 鎖住 | A | `architecture.md`、`business-overview.md`、`dependencies.md` | 推翻 `cloud/`「Review／Lens＝Claude Agent SDK」與「缺 `claude-agent-sdk` pin」 |
| 10 | **psycopg v3**；`tests/helpers.py` 已改 mock `psycopg`（條件式）而非 `psycopg2` | A | `technology-stack.md`、`code-quality-assessment.md` | 推翻 `cloud-360/`「`psycopg2-binary`」與 `team.md` 的 Testing Posture 原文 |
| 11 | `openapi.json` 為 42 path／55 op／**39 schema** | A | `api-documentation.md` | `cloud-360/` 記 32 schema，過時 |
| 12 | `requirements.txt` **18 項＝3 精確 pin ＋ 1 下限 ＋ 14 未 pin**；`fastapi==0.111.0`（**無 `[standard]` extra**） | A | `technology-stack.md` | 推翻 `cloud-360/`「17 項／5 精確 pin／`fastapi[standard]==0.141.1`」、`team.md` 同句，**以及 link 1 自己的「2 精確 pin」** |
| 13 | **`DEPLOY.md` 與 `LOCAL-DEV.md` 的 blocking 同步規則本輪都已被遵守** | A | `code-quality-assessment.md` | link 1 列為待查，本輪已查證 |
| 14 | `database.py` 的 `_ensure_*` 補丁由 6 增為 **7**，且第 7 支（`_ensure_vector_extension`）**順序在 `create_all` 之前**，方向與其餘六支相反 | A | `architecture.md` 約束六、`component-inventory.md` | `cloud-360/`「6 支」已過時 |
| 15 | **PBT hard constraint 的一處實際缺口**：純函式三支中 `estimate_readers.py` **沒有專屬測試檔**，`@given` 覆蓋為零 | A | `code-quality-assessment.md` T-18 | link 1 列為待查，本輪已查證 |

---

## 本輪未解、建議列為待查

| 項 | 為什麼重要 | 本輪狀態 |
|---|---|---|
| `brain_ws_contract.py` 783 行的完整契約（九種伺服器訊息、六種客戶端訊息的全部 payload 欄位） | `U2`／`U13` 的直接輸入；本輪只從 `brain_router.py` docstring 得知其子集 | E 級 |
| Redis／Ollama 的**應用端客戶端**要落在哪個模組 | 基礎設施已就緒但 `requirements.txt` 無 `redis` 套件、backend 應用程式碼零 import——`U10` 的起點是「接線」而非「建服務」 | A 級已查證缺口，落點未定 |
| `_last_xml`（`design_agent.py:32`）的讀取端在哪 | 判斷它的外部可觀察後果；結構與 `_progress_queue` 同型 | 未查 |
| `diagram_change_records` 的 90 天清除機制 | `DEPLOY.md:310` 逐字寫「清除機制本輪尚未落地——這張表實際上不會被清除」；`project.md` 禁止 repo 內無人值守排程 | A 級已查證缺口 |
| `main.py:62` 註解寫「下面兩行」但只有一行 `include_router` | 第二處是 `main.py:7` 的 import。移除 brain demo 時別漏 | A 級，已記載 |
| `deploy.yml`、11 支 gh-aw、Playwright e2e 的現況 | 兩輪皆未掃 | E 級 |
| `test_render_env_redis.py` 的契約內容（`K-01` 等） | 它是 Redis／Ollama 環境契約的唯一自動化承載 | 只讀了 5 行 |

---

## Scope of Analysis

```yaml
scope_version: 1
kind: partial
intent: 260920-orchestration-brain
fingerprint: 4b4780442de22b80d7b850f24fd18cedf53edcef
analyzed:
  paths:
    - backend/main.py
    - backend/services/design_agent.py
    - backend/services/llm_provider.py
    - backend/requirements.txt
    - backend/Dockerfile
    - frontend/package.json
    - openapi.json
  components:
    - backend-app-shell
    - openapi-contract
    - design-agent-core
    - llm-provider-gateway
    - backend-container-image
shallow:
  paths:
    - ./
    - backend/
    - backend/models.py
    - backend/database.py
    - backend/env_bootstrap.py
    - backend/.env.example
    - backend/services/
    - backend/services/brain_router.py
    - backend/services/brain_ws_contract.py
    - backend/services/hierarchy_migration.py
    - backend/services/user_router.py
    - backend/services/collab_router.py
    - backend/services/agent_router.py
    - backend/services/review_router.py
    - backend/services/review_agent.py
    - backend/services/review_orchestrator.py
    - backend/services/wa_collab_orchestrator.py
    - backend/services/wa_rule_engine.py
    - backend/services/wa_lens_engine.py
    - backend/services/wa_score_service.py
    - backend/services/lens_router.py
    - backend/services/lens_service.py
    - backend/services/diagram_builder.py
    - backend/services/langgraph_runtime.py
    - backend/services/llm_limits.py
    - backend/services/rbac.py
    - backend/services/rbac_seed_data.py
    - backend/services/auth.py
    - backend/services/activity.py
    - backend/services/prompt_guard.py
    - backend/services/collab_suggestions.py
    - backend/cost/
    - backend/cost/advice_orchestrator.py
    - backend/cost/advice_stream_router.py
    - backend/cost/estimate_intake_router.py
    - backend/cost/cost_advice_agent.py
    - backend/cost/pricing_client.py
    - backend/tests/
    - backend/tests/helpers.py
    - backend/scripts/
    - backend/prompts/
    - backend/lenses/
    - frontend/src/
    - frontend/src/App.tsx
    - frontend/src/pages/
    - frontend/src/components/
    - frontend/src/config/api.ts
    - frontend/src/context/
    - frontend/src/cost/
    - frontend/src/hooks/
    - frontend/src/utils/
    - frontend/src/types/
    - frontend/tests/e2e/
    - frontend/nginx.conf
    - frontend/Dockerfile
    - scripts/
    - deploy/
    - deploy/docker-compose.deploy.yml
    - deploy/docker-compose.test.yml
    - deploy/render-env.sh
    - deploy/.env.example
    - deploy/cloudflared/config.yml
    - docker-compose.yml
    - .github/workflows/
    - .github/workflows/ci.yml
    - schema.sql
    - schema_rbac.sql
    - ws-contract.json
    - README.md
    - CLAUDE.md
    - AGENTS.md
    - DEPLOY.md
    - LOCAL-DEV.md
    - TESTING.md
    - .claude/
    - aidlc/
```
