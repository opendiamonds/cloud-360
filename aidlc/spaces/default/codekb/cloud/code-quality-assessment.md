# 程式品質評估（Code Quality Assessment）

> Reverse Engineering 合成產物｜repo `cloud`｜工作樹掃描日 2026-09-16｜intent `260916-estimate-upload-rework`｜mode **Full rescan**
> 本檔的每項發現都標註**證據強度**：`實讀`＝逐行或逐檔讀過、`靜態計數`＝以工具統計、`推得`＝由結構推論未實測。本次**未執行**測試套件，故無任何「測試通過」類主張。

## 測試

| 項目 | 現況 | 證據強度 |
|---|---|---|
| 測試目錄 | `backend/tests/`（43 檔、5,277 行）、`frontend/tests/e2e/`（1 檔、667 行） | 靜態計數 |
| 框架 | `unittest`（全部 backend）＋ `hypothesis`（7 檔）；前端 `@playwright/test` | 靜態計數 |
| 執行方式 | CI：`python -m unittest discover -s tests -v`；`npx playwright test`（`ui-regression` workflow，對短生命週期 test stack） | 實讀 `ci.yml` |
| 覆蓋率設定 | **absent**——無 `.coveragerc`、`pytest.ini`、`pyproject.toml` 或任何門檻設定 | 靜態計數 |
| C1 相關測試 | 17 檔 | 靜態計數 |
| Property-based | 7 檔用 `hypothesis`（含 `test_cost_calculator`），符合 ADR-0006 對 cost calculator 的 hard constraint | 靜態計數 |

### 三個結構性的測試盲區

1. **後端單元測試從未跑過真正的 PostgreSQL DDL**。`backend/tests/helpers.py` 以 `MagicMock` 取代 `psycopg2`，改用 SQLite in-memory + `StaticPool`。因此 `database.py` 的 5 支 `_ensure_*_schema()` 的 raw SQL **不在任何自動化覆蓋內**——而它正是既有環境唯一的 schema 升級路徑。
2. **測試以字串路徑 patch 模組**。`@patch("cost.pricing_client.fetch_hourly_via_sdk")` 這類寫法在重構搬檔或改名時會**靜默失效**（測試照樣綠燈，但已不再測到目標）。C1 的 17 支測試多屬此形，對本 intent 的重構風險最高。
3. **無覆蓋率量化把關**。43 支測試沒有任何數字門檻，`org.md` 宣告的 80% line coverage 目前既無法量測也無法強制。

## Lint、格式與型別檢查

| 面向 | 前端 | 後端 |
|---|---|---|
| Linter | ESLint 10 flat config（`npm run lint`，CI 只擋 **error**，未加 `--max-warnings 0`） | **無** |
| Formatter | 無 Prettier（根目錄無 `.prettierrc`） | **無** |
| 型別檢查 | `tsc -b`（隨 build 觸發）＋ `npm run check:types` drift 閘門 | **無** |
| 唯一機械把關 | 三道（lint、typecheck、build） | import smoke test ＋三支自製契約腳本 |

抑制標記全 repo 僅 23 處（`noqa`／`eslint-disable`／`type: ignore`／`@ts-*`），多為測試檔調整 `sys.path` 所需的 `# noqa: E402`——這是應該保護的既有紀律。

## CI／CD

`.github/workflows/` 共 33 檔。核心為 `ci.yml`（5 jobs：`gate`、`repo-contract`、`frontend`、`backend`、`docker-build`）與 `deploy.yml`（自架 runner 部署至 `192.168.10.10`，含自動 rollback）；其餘為 11 支 gh-aw agentic workflow 與 7 支 `aidlc-sync-*`。

**`repo-contract` job 的三連發**與**兩道 drift 閘門**的內容記在 `component-inventory.md` 的 `contract-validators` 與 `dependencies.md`，此處不重複。

### CI 覆蓋不到的三塊結構性盲區

`project.md` 已據實測認定：六道閘門全綠時仍會放行三類缺陷——**所有 LLM 路徑**、**n8n 圖示取得**、**本機環境殘值**。這是 `tcms-test-cases` stage 成為 blocking 規則的理由，本次重掃未發現任何改變此判斷的新機制。

## 文件品質

README、`CLAUDE.md`、`AGENTS.md`、`DEPLOY.md`（含 6 群資料表對照）、`LOCAL-DEV.md`、`TESTING.md` 齊備且維護良好。程式內註解密度高且多寫「為什麼」而非「做什麼」——`ci.yml`、`requirements.txt`、`docker-compose.deploy.yml` 的註解已達規格等級。模組級 docstring 覆蓋率良好，`agent_router.py` 的「契約（前端依賴，請勿變更）」段落是最完整的樣板。

## 技術債清單

以結構形式存在而非以註解形式存在——**全 repo `TODO`／`FIXME`／`HACK` 僅 1 處**，且那是 `validate_env_contract.py` 內的 placeholder 字串清單，不是真的待辦。

### 1. 部署映像缺 Playwright 瀏覽器（對本 intent 最重要的一項）

`backend/Dockerfile` 安裝了 Node 與 `@anthropic-ai/claude-code`，但**沒有** `playwright install chromium`；`requirements.txt` 卻裝了 `playwright` 套件。執行期因此沒有瀏覽器二進位。

**後果**：Azure／GCP Calculator runner 在 staging 容器內**結構性不可用**，這條路徑實際上只在本機可跑。`frontend/src/pages/CostPage.tsx:705` 甚至在 UI 上要求使用者自行執行 `playwright install chromium`，等於把部署缺陷轉嫁為使用者指示。

**對決策的影響**：任何以「現行 Calculator 路徑的線上表現」為依據的退役或保留論證，其依據並不存在——該前提從未成立。（證據強度：實讀 `Dockerfile` 與 `requirements.txt`；未在容器內實際執行驗證。）

### 2. God modules

| 檔案 | 行數 |
|---|---|
| `frontend/src/pages/AssessmentPage.tsx` | 1,861 |
| `backend/services/diagram_builder.py` | 1,818 |
| `frontend/src/pages/WorkspacePage.tsx` | 1,194 |
| `backend/cost/gcp_calculator_runner.py` | 979 |
| `backend/services/wa_rule_engine.py` | 973 |
| `frontend/src/pages/CostPage.tsx` | 964 |
| `backend/services/user_router.py` | 896 |
| `backend/cost/azure_calculator_runner.py` | 803 |

另 `cost_service.build_snapshot` 的 280-410 行區段亦屬同級。

### 3. 跨模組引用私有函式

`cost_service.py:43` 的 `from services.collab_router import _user_can_access_diagram, _visible_diagrams`——底線開頭的符號被另一個套件依賴。任何 C1 改寫都必須重新決定授權判斷的來源。

### 4. schema 雙軌且不對稱

`schema.sql` **完全沒有**成本 DDL；4 張 C1 表只存在於 `schema_rbac.sql:169-212` 與 `_ensure_cost_schema()`（`database.py:329-395`，含一段把 `pricing_cache.hourly` 改成 `NUMERIC(12,6)` 的補丁）。同一份 DDL 兩個真實來源，且 `schema_rbac.sql` 只在空 volume 生效。

### 5. 雙層快取重疊

`pricing_client` 在 `backend/cost/.pricing_offer_cache/` 寫 24 小時磁碟快取，`price_cache` 又在 `pricing_cache` 表寫 24 小時快取——兩套 TTL 各自為政，無共同失效機制。

### 6. 依賴大多未釘版本

`requirements.txt` 14 項只有 2 項精確釘選，無 lockfile；`boto3`、`playwright`、`claude-agent-sdk` 皆浮動。CI、Docker build 與 staging 三處各自解析。

### 7. 死碼：`cost-overspend` 與 `cost-banner` slot

`frontend/src/cost/slotRegistry.tsx` 的兩個 slot 名稱對應 B2 功能，而 E2E 明確斷言這些 testid 命中數為 0（ADR-C1-08 規定 B1 不得渲染）。已存在但刻意未啟用。

### 8. `C1b` 權限種子無程式引用

`rbac_seed_data.py` 的 `C1b`（11 列）沒有任何程式使用，是 B2 budget 的遺留。

### 9. 設定文件自相矛盾

`deploy/.env.example:94-95` 仍保留註解掉的 `AWS_ACCESS_KEY_ID`／`AWS_SECRET_ACCESS_KEY`，與 `DEPLOY.md:126` 明文宣告「不要加、也不會進容器」互相矛盾。雖僅為註解，仍是誤導來源。

### 10. rollback job 的權限未經評估

`deploy.yml` 的 rollback job 權限為 `contents: write` + `pull-requests: write` + `actions: write`。這是功能需要的刻意放寬，但**可否縮窄（改用 GitHub App token，或把「開 revert PR」拆成最小權限獨立 job）尚未被評估過**，不記為已評估無虞。

## 安全基線對照（ADR-0006 四面向）

| 面向 | 現況觀察 | 判定 |
|---|---|---|
| IAM | `pricing_sdk` 是唯一需要雲端帳號憑證的路徑（boto3 Pricing Query API），由 `COST_PRICING_USE_SDK` 控制，工作樹現況預設 `0`；AWS 帳號憑證傳遞已自部署鏈移除（見下方未提交變更） | 現況收斂中，本 intent 應確認是否徹底移除 |
| Encryption | 對外流量經 Cloudflare Tunnel；DB 位於內網 compose 網路 | 未在本次深度驗證 |
| Network exposure | 僅 cloudflared 對外；compose 其餘服務不直接暴露 | 實讀 compose |
| Audit logging | C1 的四種寫入操作皆寫 `cost_audit_event`（誰、何時、舊值、新值），與資料更新同交易 | 實讀 `cost_router`／推得 service 行為 |

## 未提交的工作樹變更（讀者必看）

下列五個檔案在掃描當下是**未提交的工作樹修改**（`git status` 為 ` M`），本 codekb 描述的是**工作樹狀態**而非版控歷史：

`deploy/render-env.sh`、`deploy/docker-compose.deploy.yml`、`.github/workflows/deploy.yml`、`DEPLOY.md`、`LOCAL-DEV.md`。

變更內容為移除 AWS 帳號憑證的部署傳遞，並把 `COST_PRICING_USE_SDK` 預設改為 `0`。**查閱 git 歷史的讀者不會看到這些改動**——這點在 `reverse-engineering-timestamp.md` 亦有記載。
