# TCMS 同步報告 — AI-DLC ↔ GitHub Projects 同步機制

<!-- Stage: tcms-test-cases（Construction）· intent 260822-gh-projects-sync -->

## 第 1 層：機械檢查（`scripts/tcms_validate.py`）

```
python3 scripts/tcms_validate.py --file <record>/construction/tcms-test-cases/manual-test-cases.md
→ 驗證 5 個案例……　通過 5/5　ERROR 0　WARN 0
```

四類檢查全過：必填六段落齊備、無空洞預期結果、追溯路徑與測試名稱回 repo 核對存在、
受測介面比對實作。

### 本輪為了通過機械層而擴充的格式契約（不是繞過它）

本 intent 的交付物是 **10 個 composite action ＋ 7 支 workflow**，完全不在 web app 內
——**既無 HTTP 端點也無前端路由**。原本的「受測介面」只認 `- API:`（比對
`openapi.json`）與 `- UI:`（比對 `App.tsx`），於是五個案例逐案報
`ERROR 「受測介面」沒有列出任何 API 端點或 UI 路徑`。

處置經人工裁決（Q1=A）為**擴充契約**，而不是填一個假端點讓機械層過關——後者正是這道
檢查存在的理由所要防的事（`project.md` 的 `tcms-test-cases:c20`：假端點會通過機械比對
而無人察覺）。

| 檔案 | 改了什麼 |
| --- | --- |
| `TESTING.md` | 「受測介面」新增第三種行別 `- Workflow: \`路徑\` → <event>`，附三行別對照表與這次新增的理由 |
| `scripts/tcms_validate.py` | 新增 `WORKFLOW_LINE` 解析；比對 `.github/` 下檔案存在**且**宣告的事件真的在該檔的 `on:` 裡；「三者皆無」維持 **ERROR**；`TRACE_PATH` 加入 `.github`（原本 `.github/...` 的追溯會被靜默忽略） |

**「三者皆無」刻意維持 ERROR** ——放寬成 WARN 會讓這道檢查就此失效，那是選項 C 被否決
的理由。

## 第 2 層：語意審查（逐案七點）

每案逐點給出通過或具體理由。七點取自撰寫標準 §6。

| # | 案例 | ①目的指向真會失敗的行為 | ②回歸案例說得出既有自動化為何沒抓到 | ③外人可執行 | ④受測介面涵蓋實際碰到的面 | ⑤通過條件二元 | ⑥不與自動化層重複 | ⑦與 AC 一致 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `[aidlc-sync]` commit ⇒ 四個 job 跳過 | ✅ 失敗面是「平台不照 `if:` 動作」 | ✅ 逐字寫明兩支自動化驗的是判定邏輯與檔案形狀，不是平台行為 | ✅ 前置條件給了完整可貼上的 git 指令與清理步驟 | ✅ `ci.yml` ＋ 產生標記的 composite action | ✅ 「四個全部 skipped 且 gate 為 success」 | ✅ 自動化層只到判定邏輯 | ✅ [US:S-1 AC 7] 逐字要求「既有 run 不被取消，且不新增一輪四個 job」 |
| 2 | 反向 PR ⇒ 只有釘住的幾支建立 run | ✅ 失敗面是「靜態模型與平台語意有落差」 | ✅ 寫明 `IGNORE:` 驗的是「這五個被排除」而非「沒有別的跑起來」 | ✅ 給了 `gh workflow run` / `gh pr checks` 指令 | ✅ 三支 workflow（產生端、應被排除端、closed 端） | ✅ 「四支 gh-aw 一個都沒建立 run」＋「靜態與實際一致」 | ✅ 靜態面由本 stage 的 `PR-TRIGGER-1` 涵蓋，本案例驗的是平台實際行為 | ✅ [US:S-6 AC 7] |
| 3 | selftest 第二段端到端 | ✅ 失敗面是整條寫入鏈在真實 API 下走不完 | ✅ 寫明它就是自動化層本身、且為何不能改成自動執行（會觸發 `issue-triage` LLM 路徑） | ✅ 前置條件含 secrets/variables 兩邊各查一次的指令 | ✅ selftest workflow ＋ board action ＋ 外部相依逐項 | ✅ 「寫入值＝讀回值」「#16 未被寫入」「清理完成」 | ✅ stub 層驗的是假 `gh` 之下的分支 | ✅ [US:S-10 AC 2] |
| 4 | `AI-DLC Stage` 欄位自動建立 | ✅ 失敗面是「名字寫錯 ⇒ 正式看板多一個永久欄位」 | — 非回歸案例（背景寫的是設計上的未定案，非既往缺陷） | ✅ 給了 `gh project field-list` 指令與前後比對 | ✅ forward workflow ＋ board action | ✅ 「只新增一個」「名稱逐字相同」「第二次不新增」 | ✅ 自動化驗得到「建立了」，驗不到「名字對」 | ✅ [US:S-5 AC 1／AC 2] |
| 5 | README 連結對匿名讀者可開 | ✅ 失敗面已實測發生（404） | ✅ 寫明 `REQUIRED_TEXT` 驗的是字串在不在，CI 的 token 永遠是登入狀態 | ✅ 給了 curl 與無痕視窗兩條路 | ✅ `ci.yml` 的 `repo-contract` ＋ 外部相依（看板公開性） | ⚠️ **見下方說明** | ✅ 字串層由 `REQUIRED_TEXT` 涵蓋，可達性無任何自動化 | ✅ [US:S-11 AC 1] 的實質意圖 |

### 第 5 案通過條件的判定（⚠️ 的理由，不是漏寫）

案例 5 的通過條件是「HTTP 200」——**二元可判**。但案例本文明寫「**本案例目前預期為
失敗**」：#16 為 `public: false`（本 intent 以 `gh api` 實測），所以今天執行它必然紅。

這**不是**一個寫壞的案例，而是一個**如實記載未關閉缺口**的案例。它的存在是為了讓
「README 宣告需求正本在一個外部讀者打不開的看板」這件事有一個會定期紅的落點，而不是
只寫在某份報告的一行裡。收斂路徑有二（把看板轉公開／在 README 註明需授權），屬產品
決定；選後者時本案例的通過條件要跟著改寫。**在那之前，它是一個誠實的紅燈。**

## 第 2 層的結論

**五案全部通過語意審查**（第 5 案的 ⚠️ 是刻意的預期失敗，已在案例本文與此處說明）。
依撰寫標準「不通過就停，不要先同步再修」——本輪不需要停。

## 同步：手動案例

### 預覽（`--dry-run`，實際輸出）

```
解析到 5 個案例：
  [P1] 帶 [aidlc-sync] 標記的 commit 推送後，ci.yml 四個 job 全部跳過且既有 run 不被取消
        plan=AI-DLC ↔ GitHub Projects 同步（手動）  text=2727 字元
  [P1] 反向同步 PR 開啟後，只有釘住的那幾支 workflow 建立 run
        plan=AI-DLC ↔ GitHub Projects 同步（手動）  text=2405 字元
  [P1] 自我測試第二段對測試看板的端到端往返
        plan=AI-DLC ↔ GitHub Projects 同步（手動）  text=2570 字元
  [P1] AI-DLC Stage 自訂欄位在正式看板 #16 上被自動建立且名稱正確
        plan=AI-DLC ↔ GitHub Projects 同步（手動）  text=1914 字元
  [P2] README 的看板連結對未登入的讀者打得開
        plan=AI-DLC ↔ GitHub Projects 同步（手動）  text=1466 字元

缺少 tcms-api 套件。安裝：pip install tcms-api
```

### 結果：**已寫入**（gate 裁決後執行）

`tcms-api` 客戶端套件原本未安裝（`~/.tcms.conf` 存在，缺的是套件），故 gate 之前的
dry-run 停在 `缺少 tcms-api 套件`。安裝一個套件到使用者的 Python 環境是環境變更，
未逕自執行——gate 裁決為「安裝並實際同步」，`python3 -m pip install --user tcms-api`
之後重跑。

**安裝後的 dry-run 預覽**（連得上 TCMS 之後的完整輸出）：

```
[dry-run] plan     將建立 AI-DLC ↔ GitHub Projects 同步（手動）
[dry-run] case     將建立 [P1] 帶 [aidlc-sync] 標記的 commit 推送後，ci.yml 四個 job 全部跳過且既有 run 
[dry-run] case     將建立 [P1] 反向同步 PR 開啟後，只有釘住的那幾支 workflow 建立 run
[dry-run] case     將建立 [P1] 自我測試第二段對測試看板的端到端往返
[dry-run] case     將建立 [P1] AI-DLC Stage 自訂欄位在正式看板 #16 上被自動建立且名稱正確
[dry-run] case     將建立 [P2] README 的看板連結對未登入的讀者打得開

[dry-run] 完成：新增 5 筆，更新 0 筆，共 5 筆
```

**實際寫入結果**：

```
plan     已建立 AI-DLC ↔ GitHub Projects 同步（手動） (id=26)
case     已建立 id=40 帶 [aidlc-sync] 標記的 commit 推送後，ci.yml 四個 job 全部跳過且既
case     已建立 id=41 反向同步 PR 開啟後，只有釘住的那幾支 workflow 建立 run
case     已建立 id=42 自我測試第二段對測試看板的端到端往返
case     已建立 id=43 AI-DLC Stage 自訂欄位在正式看板 #16 上被自動建立且名稱正確
case     已建立 id=44 README 的看板連結對未登入的讀者打得開

完成：新增 5 筆，更新 0 筆，共 5 筆
```

| 項目 | 值 |
| --- | --- |
| `~/.tcms.conf` | 存在 |
| `tcms-api` Python 套件 | **已安裝**（`--user`，gate 核可後） |
| 建立的 TestPlan | `AI-DLC ↔ GitHub Projects 同步（手動）`，**id=26** |
| 建立的案例 | **5**（id 40〜44） |
| 更新的案例 | 0（本輪為首次同步，無既有案例可更新） |
| 未同步的 | 無 |

**同步鍵是案例標題**，工具以標題 upsert。日後改標題等於在 TCMS 建出第二個案例、舊的
變孤兒——要改標題先在 TCMS 處理舊案例。

## 同步：自動化案例

**本 intent 沒有可同步的對象。**

`scripts/tcms_sync.py --spec` 的對象是 Playwright spec（`frontend/tests/e2e/*.spec.ts`）
——TCMS 上的自動化案例由 `kiwitcms-junit.xml-plugin` 從測試結果建立，而本 repo 只有
Playwright 的結果會經 `ui-regression` 回寫 TCMS。

本 intent **未新增也未改動任何 Playwright spec**（`frontend/` 零改動）。它新增的自動化
全部是 `.github/actions/aidlc-sync-*/` 下的 Python 檢查器與 harness，由
`aidlc-sync-selftest.yml` 執行，**不產生 junit XML、不經 junit plugin、在 TCMS 上沒有
對應案例**。

工具**不建立**自動化案例（建的會是永遠沒有執行結果的孤兒），所以這裡不是「同步失敗」
而是「沒有同步對象」。

> **值得登錄的落差**：本 intent 交付了 312 tests／1844 checks 的自動化，而**其中沒有
> 任何一項會出現在 TCMS 上**。`operation/test-case-management-plan.md` 的分工假設自動化
> 案例經 junit plugin 進入 TCMS，該假設對 Playwright 成立、對本 intent 的 Python 層
> 不成立。要不要讓這一層也回寫 TCMS 是獨立決定（需要產出 junit XML 並接進 workflow），
> 登錄給 gate。

## 未完成項與登錄事項

| # | 項目 | 處置 |
| --- | --- | --- |
| 1 | ~~`tcms-api` 未安裝 ⇒ 手動案例未寫入 TCMS~~ | **已關閉**：gate 裁決為安裝並實跑，5 個案例已寫入 TestPlan id=26（案例 id 40〜44） |
| 2 | `tcms_validate.py` 的 `DEFAULT_MANUAL` 硬編碼指向 **`260802-last-login-column`** | `--all`（stage 檔指定的形式）驗的是**前一個 intent** 的檔案，不是作用中 intent 的。本輪改以 `--file` 明確指定而通過。修法（改為解析 `active-intent`）未逕自執行——它會改變前一個 intent 的覆蓋範圍，屬獨立決定 |
| 3 | 本 intent 的 Python 自動化層在 TCMS 上完全不可見 | 見上一節的落差說明 |
| 4 | 案例 5 目前預期為紅 | 如實記載的未關閉缺口，非案例缺陷 |
| 5 | 未分類項 U-1（[US:S-10 AC 5] 的 403 前提不可達） | 指派回 user-stories 改寫落點或於 ADR 記明失效，見 `manual-test-cases.md` 的分桶表 |

## 與上游的對應

分桶與案例內容引自 `manual-test-cases.md`；自動化落點與突變驗證引自
`automation-test-plan.md`；`build-and-test-summary.md` 與各單元 `code-summary.md` 提供
「哪些行為已被自動化斷言」的依據；格式契約引自 `TESTING.md` 與撰寫標準
`aidlc/spaces/default/knowledge/aidlc-quality-agent/test-case-authoring.md`。
