# 測試案例撰寫標準 — Cloud-360

> `tcms-test-cases` stage 的撰寫依據。stage 檔說**要產出什麼**，本檔說**怎麼寫才算數**。
> 由 `aidlc-quality-agent` 於該 stage 起始時載入。
>
> 本檔位於團隊知識層（`aidlc/spaces/<space>/knowledge/`），不隨 AI-DLC 升級被覆蓋。

---

## 0. 為什麼需要手動測案

本 repo 的自動化層有三塊**結構性**的盲區，不是覆蓋率不足的程度問題，是那條路徑上沒有任何自動化斷言存在：

| 盲區 | 原因 | 後果 |
|---|---|---|
| 所有 LLM 路徑（A1 產圖、A3 建議、Lens 填答） | `ui-regression` 刻意不觸及——會產生費用且外部不穩 | A1／A3 的端到端行為零自動化覆蓋 |
| n8n 圖示取得 | 依賴外部 webhook，CI 環境不保證可達 | 圖示錯誤、降級靜默都測不到 |
| 本機環境設定（`LLM_PROVIDER`、`.env` 殘值） | CI 是乾淨 checkout，永遠不會有殘值 | 「乾淨環境會過、開發者機器會壞」的整類缺陷 |

這三塊的缺陷實際發生過，而且是**六道 CI 閘門全綠的情況下**發生的。手動測案是這些路徑目前唯一的守門機制。

---

## 1. 分流：一個行為只能有一個真實來源

`operation/test-case-management-plan.md` 定下的原則，**不得違反**：

| 測案類型 | 真實來源 | 執行 | TCMS 的角色 |
|---|---|---|---|
| 自動化 | repo 內的 spec code | GitHub Actions | 只存中繼資料與歷史結果（junit plugin 回寫） |
| 手動 | TCMS | 人工執行 | 主檔 |

**自動化案例不搬進 TCMS 當主檔**——那會造成雙份維護，而且其中一份必定悄悄過期。

### 分流判準

先問：**這個行為能不能被自動化斷言？**

- **能，而且已經有腳本** → 記進自動化計畫，**不寫手動案例**。重複覆蓋沒有加分。
- **能，但腳本還不存在** → 這個 stage 就把腳本寫出來。不是列願望清單。
- **不能，或不該** → 寫手動案例。

「不能或不該」的具體情形（其餘一律歸「能」）：

1. **每跑一次都要花錢**：呼叫 LLM 的路徑。
2. **依賴 CI 無法保證的外部服務**：n8n webhook、需要登入的 `claude` CLI。
3. **需要人的判斷**：架構圖「可不可讀」、圖示「對不對」——像素比對在這裡不可靠。
4. **需要真實環境狀態**：`.env` 有殘值、資料庫已有歷史資料、瀏覽器已登入某帳號。

判不出來的，**不要預設丟給手動**。在 stage summary 裡列為未分類項並說明卡在哪。預設丟手動＝把問題藏進一份沒人會跑的文件。

---

## 2. 手動案例的格式（機器可解析）

> **格式契約的正式來源是 repo 根目錄的 [`TESTING.md`](../../../../../TESTING.md)**，
> 不是本檔。那份文件不限工具，Cursor／Antigravity 的使用者也讀得到；必要欄位清單
> 由它的 `required-sections` 標記定義，`scripts/tcms_validate.py` 直接讀取該標記，
> 所以文件與程式不會分歧。
>
> 本節重述模板是為了讓 agent 不必跳檔，**兩者若有出入以 `TESTING.md` 為準**。

`manual-test-cases.md` 由 `scripts/tcms_sync.py` 解析後寫入 TCMS，**結構是契約**：

````markdown
# 手動測試案例 — <intent 名稱>

## TC: <案例標題>

- plan: <TCMS 測試計畫名稱>
- priority: P1

### 目的

<一到兩句：這個案例在保護什麼>

### 背景

<為什麼有這個案例。回歸案例必須寫出缺陷原貌>

### 受測介面

- API: `POST /api/auth/login` → 200 — 帳密驗證，成功時回 access_token
- UI: `/admin/users` — 使用者角色指派頁：表格、分頁導覽區
- 外部相依: <非本系統的依賴，如 n8n webhook；沒有就省略這行>

### 前置條件

1. <可複製貼上的指令或設定>

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | <一個動作> | <一個可觀察的結果> |

### 通過條件

- <二元可判的條件>

### 追溯

- 實作：<檔案路徑>
- 自動化對應：<測試檔::類別::方法，或「無」>
- PR／commit：<編號>
- User story：<id>
````

**「受測介面」是必填段落**，而且會被機械比對：API 端點與 method 對照
`openapi.json`，UI 路徑對照 `frontend/src/App.tsx` 的路由表。寫錯或寫了不存在的
端點，`tcms_validate.py` 會擋下來。格式必須逐字照上面那三行的形狀（`- API: `、
`- UI: `、`- 外部相依: `），backtick 不可省略——解析器認的是它。

它要回答的是「這個案例碰到系統的哪些面」。只寫 UI 而漏了它實際會打的 API，
機械層看不出來（那是語意審查的職責），但下一個要改那支 API 的人也就不會知道
這個案例會受影響。

### 段落層級（踩過一次的坑）

案例內的小節一律 `###`；小節**之內**的再分層用 `####`。曾經把「共用前置」與
「情境一／二」寫成 `###`，結果它們與「前置條件」「測試步驟」同級——解析器看到
的「測試步驟」段落是空的，而「前置條件」這個段落根本不存在。驗證器抓得到，
但寫的時候就別犯。

### 解析規則（不可違反）

- `## TC: ` 起始一個新案例，其後文字即 TCMS 的 case summary。
- **標題是同步鍵**。改標題＝在 TCMS 建出第二個案例，而不是更新第一個。要改標題，先在 TCMS 處理舊案例。
- `- plan:` 與 `- priority:` 必須緊接在標題後，且在第一個 `###` 之前。
- 從第一個 `###` 到下一個 `## TC:` 之間的全部內容，原樣送進 TCMS 的 `text` 欄位（Markdown 保留）。
- `priority` 用 `P1` / `P2` / `P3`。

### 語言

繁體中文（ADR-0009）。程式碼、指令、識別字、錯誤訊息原文維持原樣——錯誤訊息**必須**逐字，那是執行者比對的依據。

---

## 3. 步驟怎麼寫才算數

### 一個步驟 = 一個動作 + 一個可觀察的結果

預期結果寫「正常」「成功」「無異常」的，**不算步驟**。要寫出「正常」長什麼樣子：畫面上出現什麼、log 裡出現哪一行、API 回什麼狀態碼。

| ❌ 不合格 | ✅ 合格 |
|---|---|
| 啟動後端，確認正常 | 啟動後端，log 出現 `LLM_PROVIDER=cli：已移除 ANTHROPIC_BASE_URL、ANTHROPIC_DEFAULT_SONNET_MODEL`，且 `/openapi.json` 回 200 |
| 檢查圖示正確 | SNS 節點顯示 Simple Notification Service 圖示，**不得**是 Auto Scaling group 圖示 |
| 測試錯誤處理 | 回應訊息包含 `尚未設定 OPENROUTER_API_KEY`，且**不是** `401 Missing Authentication header` |

### 寫出「不該出現什麼」

回歸案例的價值多半在否定句。「顯示正確圖示」會被一個看起來很正常的錯圖示矇混過去；「**不得**是 Auto Scaling group 圖示」不會。

### 前置條件要能複製貼上

執行的人不會知道你腦中的環境。指令、檔案內容、帳密（測試帳號 `admin` / `admin123`）都寫出來。改了 `backend/.env` 一定要提醒**重啟後端**——`--reload` 只監看 `.py`。

### 背景要寫出缺陷原貌

回歸案例的 **背景** 必須包含三件事，缺一則一年後沒人看得懂這個案例在防什麼：

1. **症狀**：使用者看到什麼。
2. **錯誤訊息逐字**：例如 `There's an issue with the selected model (anthropic/claude-sonnet-4.6)`。
3. **既有自動化層為何沒抓到**：這句最重要，它同時說明了為什麼這是手動案例。

---

## 4. 自動化腳本：三個落點

先確認落點，再動手。本 repo 的既成事實（見 `team.md`）決定了選擇範圍：

### 4.1 Backend 單元／行為 → `backend/tests/test_*.py`

- 框架是 Python 內建 **`unittest`**，**不是 pytest**。CI 跑 `python -m unittest discover -s tests -v`。
- 新檔放進 `backend/tests/` 即被自動撿到。
- 測試 DB：`backend/tests/helpers.py` 在任何 DB import 前 `sys.modules.setdefault("psycopg2", MagicMock())`，走 in-memory SQLite。新測試檔第一行 import 要是：
  ```python
  import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import
  ```
- 純函式且有值域性質的，用 `hypothesis` 的 `@given` 寫成 property——ADR-0006 對 IaC generator、cost calculator、agent routing 是 hard constraint。

### 4.2 Backend HTTP 契約 → `TestClient`

`team.md` 規則 B：**新增或修改 HTTP 端點，必須有 `TestClient` 測試**，斷言 status code 與 `response_model` 的欄位集合。

前置條件已滿足（`fastapi[standard]` 與 `httpx` 已在 `requirements.txt`）。要點：

- 用 `app.dependency_overrides` 覆寫 `get_db`（`database.py`）與 `get_current_user`（`services/auth.py`）。
- `require_story_action` closure 依賴上述兩者，所以**真實的 `user_can` 授權路徑仍會被執行**——這正是價值所在。
- `TestClient(app)` 直接使用不觸發 `@app.on_event("startup")` 的 `init_db()`，不需要真實 DB。

### 4.3 前端端到端 → `frontend/tests/e2e/*.spec.ts`

- Playwright，chromium 單一 project。**這是唯一碰得到 UI 的自動化層**——前端沒有 unit／component 測試框架（`devDependencies` 只有 `@playwright/test`），引入一個是獨立的工具鏈決策，不由測案 stage 夾帶。
- `ui-regression` workflow 每個 PR 對短生命週期 stack 執行，`stats.unexpected` 非 0 即紅燈。所以**寫進去的東西會擋 PR**，要確保穩定。
- 登入用既有 helper 形狀：
  ```ts
  await page.getByPlaceholder('請輸入您的帳號').fill(username);
  await page.getByPlaceholder('請輸入密碼').fill(password);
  await page.getByRole('button', { name: '登入系統' }).click();
  ```
- **不要**在 e2e 裡觸及任何 LLM 路徑。那是這套套件刻意的邊界，破壞它會讓每個 PR 都花錢且不穩。

### 4.4 自動化案例也要有規格 —— 但規格的來源是 code 旁的註解

TCMS 上的自動化案例由 `kiwitcms-junit.xml-plugin` 從測試結果建立，預設**沒有任何描述**——點進去只看得到 `Author: ci-bot` 和一片空白。這對要判讀測試涵蓋範圍的人沒有幫助。

但**不可以直接在 TCMS 手寫描述**：spec code 才是會被改的那份，手抄的描述必定過期，而且沒有任何機制會告訴你它過期了。

做法是讓描述也從 code 產生 —— 在每個 `test()` 前加結構化註解：

```ts
/**
 * @purpose 錯誤憑證必須被拒絕，且使用者留在登入頁看得到原因。
 * @given seed 帳號 admin 存在
 * @step 以 admin 與一組錯誤密碼送出登入 | 後端回 401「帳號或密碼錯誤」
 * @step 檢視頁面 | 出現「帳號或密碼錯誤」
 * @step 檢視當前路徑 | 未被導向 `/workspace`
 * @pass 錯誤訊息可見，且 URL 不含 `/workspace`
 * @story J1
 * @note 「不得導向 workspace」是關鍵斷言：只驗錯誤訊息無法排除
 *       「顯示了錯誤但仍然放行」這種更嚴重的實作。
 */
test('錯誤密碼被拒並停留在登入頁', async ({ page }) => {
```

標記說明：

| 標記 | 必填 | 說明 |
|---|---|---|
| `@purpose` | ✅ | 這個測試保護什麼 |
| `@given` | ✅ | 前置狀態（seed 資料、需先建立的帳號、視窗尺寸等） |
| `@step` | ✅ | `操作 \| 預期結果`，一行一步，順序即步驟編號 |
| `@pass` | ✅ | 通過條件 |
| `@api` | ✅* | `METHOD /path -> status \| 說明`，一行一個端點 |
| `@ui` | ✅* | `/path \| 關鍵元素`，一行一個頁面 |
| `@story` | ✅ | 對應的 user story id |
| `@note` | — | 這個斷言為何長這樣、它在防哪個具體的錯誤實作 |

\* `@api` 與 `@ui` 至少要有一個。兩者都會被機械比對（端點對 `openapi.json`、
路徑對 `App.tsx` 路由表），寫錯會被 `tcms_validate.py` 擋下。範例：

```
 * @api POST /api/auth/login -> 200 | 帳密驗證，成功時回 access_token
 * @api GET /api/auth/list -> 200 | 使用者清單，支援 page 參數分頁
 * @ui /admin/users | 使用者角色指派頁：表格、「最後活動時間」欄、分頁導覽區
```

每個標記都可跨行（續行不加 `@`，會被接到前一個標記上）。

同步（**只更新、不建立**）：

```bash
python3 scripts/tcms_sync.py --spec frontend/tests/e2e/regression.spec.ts --dry-run
python3 scripts/tcms_sync.py --spec frontend/tests/e2e/regression.spec.ts
```

三個必須知道的約束：

1. **TCMS 案例名稱是 `<describe> › <test>`**，與 junit plugin 的 `--summary-template '${name}'` 一致。改動 `describe` 或 `test` 的字串會讓既有案例變孤兒（新名稱建新案例，舊的留著沒有執行結果）。
2. 工具**不建立**自動化案例。案例是 plugin 從測試結果建的；本工具建的會是永遠沒有執行結果的孤兒。找不到對應案例通常表示該測試還沒在 CI 跑過一次。
3. 工具**只寫 `text`**，不碰 `is_automated` 與 `case_status`——那兩個由 plugin 維護，兩個寫入者搶同一個欄位遲早出事。

寫進 TCMS 的內容開頭會帶一段警語，說明它是自動產生、在 TCMS 改會被覆蓋。

### 4.5 `team.md` 的三條測試底線（本 stage 一併檢查）

- **A**：`role_permissions` 預設值變更 → 必須有 allow/deny **雙向**測試。
- **B**：新增或修改 HTTP 端點 → 必須有 `TestClient` 測試。
- **C**：前端資料形狀變更 → 必須有 e2e 斷言。

---

## 5. 突變驗證：沒看過它紅過，就不算寫完

`construction.md` 禁止「無論實作對錯都會通過」的測試。唯一的證明方式是**讓它失敗一次**：

1. 測試寫完、跑綠。
2. 把修正改回錯的行為（或直接讓被測條件失效）。
3. 重跑，**確認紅燈**，並確認紅的是你預期的那幾個斷言。
4. 還原，複驗綠燈。
5. 把突變內容與結果寫進自動化計畫。

實例（本 repo 真實發生）：`ANTHROPIC_DEFAULT_*_MODEL` 的修正，突變成「只刪認證三個變數」時紅 2 項、突變成「cli 也讀別名變數」時紅 1 項。沒有這一步，就無法區分「測試守住了行為」與「測試剛好也通過」。

**突變本身也要檢查有沒有生效**。曾經有一次把 `_SERVICE_ABBREVIATIONS = {}` 寫成 `{} or {...}`，Python 的 `or` 回傳右側，突變根本沒作用，測試當然是綠的——差點被誤讀成「測試沒抓到」。改完先 grep 確認檔案真的變了。

---

## 6. 驗證關卡：同步之前必須通過

案例寫完不等於可以進 TCMS。**一份填得不完整或規格寫錯的案例，比沒有案例更糟**
——它讓人以為某個行為被覆蓋了。所以同步前有一道 gate：

```bash
/tcms-verify
```

它分兩層，順序不可顛倒。

### 第 1 層：機械檢查（`scripts/tcms_validate.py`）

| 類別 | 內容 |
|---|---|
| 必填欄位與格式 | 六個必填段落都在；步驟表格每列都有操作與預期結果 |
| 空洞預期結果 | 不得是「正常」「成功」這類無法判定的詞；每個案例至少要有一個帶具體證據的預期 |
| 追溯目標存在 | 引用的檔案路徑與測試名稱回 repo 核對 |
| API/UI 比對實作 | 端點與 method 對 `openapi.json`，UI 路徑對 `App.tsx` 路由表 |

**ERROR 一律阻擋。** WARN 要逐項判讀不得無視——最常見的 WARN 是「OpenAPI 未宣告
此狀態碼」，那通常代表端點缺 `responses=` 宣告，是真實的文件落差。

有一類 ERROR 不是案例的缺陷：追溯指向的檔案在**另一支尚未合併的分支**上。那是
真實的跨分支依賴，處置是說明依賴與確認合併順序，**不是把追溯改掉讓檢查過關**。

### 第 2 層：語意審查

機械層全過後才做。工具能驗「欄位在不在、路徑存不存在」，驗不了「這個規格是不是
真的描述了需求」。逐案檢查七點，每點給出通過或具體理由：

1. 目的是否指向一個真的會失敗的行為（不是對任何實作都成立的空話）
2. 回歸案例的背景是否說得出症狀、錯誤訊息逐字、**以及既有自動化層為何沒抓到**
3. 步驟能不能被沒參與開發的人執行
4. 受測介面是否涵蓋案例實際會碰到的介面（機械層只驗「列出來的存在」，驗不了「該列的有沒有漏」）
5. 通過條件是否二元可判
6. 是否與自動化層重複覆蓋
7. 規格是否與 `stories.md` 的 AC 一致——AC 說的事有沒有真的被驗到

**不通過就停，不要「先同步再修」。**

## 7. TCMS 欄位對應

| 本檔欄位 | TCMS 欄位 | 備註 |
|---|---|---|
| `## TC:` 後的標題 | `summary` | 同步鍵，保持穩定 |
| `### 之後的全部內容` | `text` | Markdown 原樣 |
| `- priority:` | `priority` | P1／P2／P3 |
| `- plan:` | 加入對應的 `TestPlan` | 不存在則建立 |
| （固定） | `is_automated = False` | 手動案例必須為 False，才與 junit plugin 回寫的自動化案例區分得開 |
| （固定） | tag `Cloud-360` | 該 Kiwi 實例跨專案共用，Product 是結構分隔、tag 輔助跨專案檢視 |

同步指令：

```bash
# 一律先預覽
python3 scripts/tcms_sync.py --file <path> --dry-run
# 確認後寫入
python3 scripts/tcms_sync.py --file <path>
```

需要 `~/.tcms.conf`（`url` / `username` / `password`）。**沒有這個檔案時同步不得靜默跳過**——記為未完成項並在 gate 說明。

---

## 8. 完整範例

````markdown
## TC: backend/.env 殘留 OpenRouter 變數時，cli 模式仍可正常取得模型回應

- plan: 本機 LLM 供應商與架構圖圖示（手動）
- priority: P1

### 目的

回歸案例。驗證 `.env` 裡殘留的 OpenRouter 設定不會癱瘓 cli 模式。

### 背景

實測踩過的缺陷：模型名稱正規化與環境變數刪除**互相抵銷**。

`ANTHROPIC_DEFAULT_*_MODEL` 定義的是 CLI 的**別名**指向哪個實際模型，不是
「要用哪個模型」。即使程式已把殘留的 gateway slug 正規化成 `sonnet`，子行程
仍會照著這個變數把 `sonnet` 映射回原本的 slug：

```
404 There's an issue with the selected model (anthropic/claude-sonnet-4.6)
```

**既有自動化層為何沒抓到**：當時的 21 個單元測試只檢查認證那三個變數
（`ANTHROPIC_BASE_URL`／`AUTH_TOKEN`／`API_KEY`），別名這一族不在
「哪些變數會蓋掉 CLI 登入」的心智模型裡，全部繞過了它。

### 前置條件

1. PostgreSQL 已啟動：`pg_isready -h localhost -p 5432`
2. `claude` CLI 已登入：`claude -p "回一個字：好"` 有回應
3. `backend/.env` 刻意設成「從 OpenRouter 切回來、殘值未清」的狀態：
   ```
   LLM_PROVIDER=cli
   OPENROUTER_API_KEY=
   ANTHROPIC_BASE_URL=https://openrouter.ai/api
   ANTHROPIC_DEFAULT_SONNET_MODEL=anthropic/claude-sonnet-4.6
   LLM_MODEL=anthropic/claude-sonnet-4.6
   ```

### 測試步驟

| # | 操作 | 預期結果 |
|---|---|---|
| 1 | 依前置設定 `.env`，保留全部三個殘留變數 | 設定完成 |
| 2 | 重啟後端（`--reload` 不監看 `.env`，必須重啟） | 啟動成功 |
| 3 | 觀察啟動 log | 出現 `LLM_PROVIDER=cli：已移除 ANTHROPIC_BASE_URL、ANTHROPIC_DEFAULT_SONNET_MODEL，改用 claude CLI 自帶的登入認證` |
| 4 | 登入前端並在 A1 送出任一架構需求 | 取得真實模型回應 |
| 5 | 檢查後端 log | **不得**出現 `There's an issue with the selected model` |
| 6 | 檢查後端 log | **不得**出現 404 |

### 通過條件

- 步驟 3 的移除訊息**包含 `ANTHROPIC_DEFAULT_SONNET_MODEL`**，不只認證那三個。
- 步驟 4 取得回應而非錯誤。

### 追溯

- 實作：`backend/services/llm_provider.py` 的 `_CLI_ALIAS_MODEL_VARS`
- 自動化對應：`backend/tests/test_llm_provider.py::CliModeClearsConflictingVars::test_deletes_the_alias_model_family`
- PR #499 · commit 2511e3d
- User story：A1
````

---

## 9. 常見錯誤

| 錯誤 | 為什麼是錯的 |
|---|---|
| 把已自動化的行為再寫一份手動案例 | 兩個真實來源，其中一份會過期 |
| 預期結果寫「正常」 | 執行的人無法判定；紅綠都說得通 |
| 只寫「應該顯示 X」不寫「不得是 Y」 | 錯得很像對的結果會被放行——實測發生過（Auto Scaling 圖示） |
| 回歸案例的背景沒寫缺陷原貌 | 一年後沒人知道在防什麼，案例會被當成冗餘刪掉 |
| 自動化計畫只列清單、不寫腳本 | 願望清單不會擋任何缺陷 |
| 測試寫完沒看它紅過 | 無法區分「守住行為」與「剛好通過」 |
| 改了案例標題 | TCMS 會多出一個案例，舊的變孤兒 |
| `~/.tcms.conf` 不存在就跳過同步 | 靜默降級——正是這個 stage 要防的失敗模式 |
