# TCMS 同步報告 — 261116-brain-create-diagram

> 狀態：**預覽完成，尚未寫入**。實際寫入須待本站核可關卡的使用者核可（寫入 `tcms.danniel.cc` 屬對外寫入）。
> `~/.tcms.conf` 存在（內容未讀取、未輸出）。

## 1. 驗證關卡（`/tcms-verify`）

### 第 1 層：機械檢查

| 指令 | 結果 |
|---|---|
| `python3 scripts/tcms_validate.py --file .../manual-test-cases.md` | 通過 3/3，ERROR 0，WARN 0 |
| `python3 scripts/tcms_validate.py --spec frontend/tests/e2e/diagram-drafts.spec.ts` | 首次：通過 5/5，**WARN 1**（`POST /api/architecture/reviews` 的 OpenAPI 未宣告 409）。判讀為真實文件落差，已在五個拒收草稿的端點補 `responses=` 並加測試（見 `automation-test-plan.md` §2）；重跑：ERROR 0，WARN 0 |
| `python3 scripts/tcms_validate.py --all` | 通過 27/27，ERROR 0，WARN 0 |

### 第 2 層：語意審查（三個手動案例，逐案七點）

| 檢查點 | 案例 1（主路徑） | 案例 2（新建／修改／反問） | 案例 3（升級補欄） |
|---|---|---|---|
| 1. 目的指向真會失敗的行為 | 通過：模型給低 p 時會反問而非建圖；存回不帶 `finalize` 時不會轉正式 | 通過：模型對修改句給高 p 會多建一張 | 通過：補丁未掛或吞例外時讀圖 500 |
| 2. 背景說得出既有自動化層為何沒抓到 | 通過：替身路由＋替身工作編排、e2e 攔截 WS | 通過：性質測試與替身都不碰真實模型給的 p | 通過：SQLite 與本機只跑 SQL 敘述的 PostgreSQL 驗證 |
| 3. 外人可執行 | 通過：前置條件逐步，引用 `LOCAL-DEV.md` 第 0 節 | 通過：依賴案例 1 的結果，已寫明 | 通過：`psql` 指令可複製貼上 |
| 4. 受測介面涵蓋實際碰到的面 | 通過：入口頁、專案頁、建圖、存圖、最近變更；WS `/api/brain/ws` 不在 OpenAPI，以入口頁 UI 表達 | 通過 | 通過：工作區與專案頁兩個讀圖面、列表與明細端點 |
| 5. 通過條件二元可判 | 通過：三個條件皆可觀察 | 通過：張數 1／2／2 與是否出現反問 | 通過：啟動成功、全為 ready、200 |
| 6. 與自動化層重複 | 不重複：自動化層不碰真實模型 | 不重複：同上 | 不重複：自動化層不碰真實 PostgreSQL 的舊 volume |
| 7. 與需求一致 | 通過：FR1.1、FR1.5、FR6.2、FR6.4、FR7.1 逐條對應步驟 3、5、6 | 通過：FR2.1 的三種句意 | 通過：FR6.5「既有的圖一律視為正式」 |

撰寫中依程式核對了案例引用的每一段畫面文字與日誌文字（反問句、按鈕標籤、啟動 log、圖名），修正了八處與實作不符的引用（例如反問句實為「要新建一張架構圖，還是修改目前的圖？」、主路徑的圖名實為「電商網站的 AWS 架構圖」）。

## 2. 手動案例同步（預覽）

指令：`python3 scripts/tcms_sync.py --file aidlc/spaces/default/intents/261116-brain-create-diagram/construction/tcms-test-cases/manual-test-cases.md --dry-run`

```
[dry-run] plan     將建立 261116 大腦建立架構圖：真實模型路徑（手動）
[dry-run] plan     將建立 261116 大腦建立架構圖：部署與升級（手動）
[dry-run] case     將建立 [P1] 真實模型下對沒有圖的系統說要畫圖，大腦建立草稿並產圖後轉為正式
[dry-run] case     將建立 [P1] 真實模型下已有圖時依句意分辨新建、修改與反問
[dry-run] case     將建立 [P1] 既有資料庫升級後 backend 自行補上草稿狀態欄位且既有圖皆為正式

[dry-run] 完成：新增 3 筆，更新 0 筆，共 3 筆
```

| 計畫 | P1 | P2 | P3 |
|---|---|---|---|
| 261116 大腦建立架構圖：真實模型路徑（手動） | 2 | 0 | 0 |
| 261116 大腦建立架構圖：部署與升級（手動） | 1 | 0 | 0 |

## 3. 自動化案例描述同步（預覽）

指令：`python3 scripts/tcms_sync.py --spec frontend/tests/e2e/diagram-drafts.spec.ts --dry-run` → 更新 0 筆。

TCMS 上找不到對應案例的 5 筆（這些測試還沒在 CI 的 `ui-regression` 跑過，案例由 junit plugin 在第一次執行時建立，本工具不建立）：

- Diagram drafts › marks drafts on the project page and leaves them out of the count
- Diagram drafts › only the save button turns a draft into a finished diagram
- Diagram drafts › lets the user pick a system from the brain clarify
- Diagram drafts › marks drafts in the attach-diagram dropdown
- Diagram drafts › marks drafts on the assessment page and shows a readable rejection

**待辦**：PR 的 `ui-regression` 第一次跑完後，重跑 `python3 scripts/tcms_sync.py --spec frontend/tests/e2e/diagram-drafts.spec.ts` 補上描述。後端 `unittest` 的案例不經 junit plugin 進 TCMS，不在同步範圍。

## 4. 實際寫入

**未完成（open item）。** 使用者核可後執行
`python3 scripts/tcms_sync.py --file aidlc/spaces/default/intents/261116-brain-create-diagram/construction/tcms-test-cases/manual-test-cases.md`，
兩次皆在第一個 RPC（`Product.filter`）失敗：

```
xmlrpc.client.ProtocolError: <ProtocolError for tcms.danniel.cc/xml-rpc/: 530 <none>>
```

`curl https://tcms.danniel.cc/` 同樣回 `530`（Cloudflare 連不到後端主機）。失敗發生在任何寫入之前，**TCMS 上沒有建立任何計畫或案例**，重跑不會產生重複（工具以標題為同步鍵）。

處置：TCMS 主機恢復後重跑上述指令（不帶 `--dry-run`），並把建立的計畫與案例 id 補記於此。
