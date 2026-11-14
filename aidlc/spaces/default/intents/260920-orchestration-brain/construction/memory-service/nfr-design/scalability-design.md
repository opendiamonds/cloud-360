# 擴充性設計 — `U8 memory-service`

> 本單元不新增進程或容器，故本檔設計的是**資料成長的邊界**與
> **沒有上界的讀取路徑**這兩件它真的擁有的事。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `nfr-requirements/scalability-requirements.md` | `NFR7.27`（成長上界）、`NFR7.28`（分頁）、`NFR7.29`（`limit` 上限）與 `N8-8` |
| `functional-design/rules.md` | `BR7.1`／`BR7.2`／`BR7.3` 三個寫入端 |
| `inception/contract-design/contract-summary.md` | `K-08` 的 OpenAPI 半邊（`GET /records` 無分頁宣告） |
| repo 既有先例 | `/api/auth/list` 的 offset／limit ＋ `total` |

## 一、分頁設計（`NFR7.28`）：照既有先例，不自創

`K-08` 的 `GET /api/memory/records` **沒有任何分頁宣告**，而 `BR7.1` 讓
`U13` 每輪對話寫一筆 episodic，故該路徑的回應大小隨使用量線性成長
（而 `content` 是 `TEXT`）。

| 項目 | 設計 | 依據 |
|---|---|---|
| 形式 | **offset／limit**，回應含 `total` | repo 既有先例 `/api/auth/list`；`U19` 的 `test_user_list_endpoint.py` 即測它的分頁欄位 |
| 為什麼不用 cursor | cursor 對大資料集更好，但本表有 90 天上界、且既有先例是 offset。**新增第二種分頁語彙的成本高於收益** | `team.md` 的「沿用現有形狀，不要單點自創抽象」 |
| 預設上限 | 必須有；不得「未指定即回全部」 | `NFR7.28` |
| 三區的處理 | 三個 `kind` **各自分頁**，不是三區共用一個 offset | 否則一區的筆數會推移其他兩區的視窗，使分頁語意不可理解 |

**這處偏離 `K-08`**：新增分頁參數會讓 `openapi.json` 與 `K-08` 的 OpenAPI
半邊產生落差。記為 `D8-4`（與 `N8-8` 同一件事，本檔給出具體形式）。

## 二、`limit` 上限（`NFR7.29`）

`K-08` 的 `search` 簽名含 `limit: int`，而契約未定上限。

| 設計 | 呼叫端指定超過伺服器上限時，**收斂到上限**而非照辦或報錯 |
|---|---|
| 為什麼收斂而非 422 | `search` 是同進程 facade（`U11` 消費），一個過大的 `limit` 是呼叫端的疏失而非使用者輸入；收斂使它降級而非失敗 |
| 為什麼需要上限 | 無上限的 `limit` 是一條 DoS 路徑（STRIDE 的 D），且 HNSW 的檢索成本隨 `limit` 成長 |

## 三、成長上界（`NFR7.27`）：依賴 `U9`，不重建

| 事實 | 說明 |
|---|---|
| 唯一的上界機制 | `U9 memory-purge` 的 90 天清除（**已交付**） |
| 本單元的增量 | **零**——不新增機制 |
| 漏跑偵測 | `U9` 的 `NFR7.13` watchdog（已交付） |
| 誠實限定 | 只有 `episodic` 受清除約束（只有它有 `expiresAt`）。`semantic`／`procedure` **無上界**——它們只能由使用者刪除 |

**最後一列是本站新寫下的**：`BR7.3` 讓使用者手動建立 `semantic`，
而沒有任何機制會清它。在本輪的使用量下不是問題（手動建立量小），
但「三種記憶中有兩種沒有保存期」這件事應該被看到。

**`D8-5` 的承接（承審查 `R-02`）**：**無自然承接站。**
理由：它不是設計缺口而是**產品決定**——`FR4.5` 逐字只把 90 天保存期
約束在 episodic，故「semantic／procedure 要不要有保存期」需要一個新的
已核可需求，而本 intent 的 24 個單元**沒有一個擁有保存期政策**
（`U9 memory-purge` 擁有的是**執行機制**，它依 `expiresAt` 選列，
而 semantic／procedure 的 `expiresAt` 依 `EC1` 恆為空）。

依 `project.md` 的規則（`approval-handoff:5d0af04b`：找不到誠實的轉移目標時
寫「無自然承接站」並指定屆時判定 skip 的 conductor 重新提交給使用者，
不得填一個看起來合理的假目標），本項**不指派任何站**，
並要求本單元 `code-generation` 的核可關卡把它重新提交給使用者裁決。

## 四、不適用的面向（逐項附理由）

| 面向 | 判定 |
|---|---|
| 水平擴充／auto-scaling | **N/A**：既有單一 FastAPI 進程，單主機 compose（ADR-0007） |
| 資料分割／分片 | **N/A**：90 天上界使 `episodic` 有界；分割屬 `U5` 的 schema 範圍 |
| 連線池調整 | **N/A 且刻意不動**：沿用既有 engine。本單元新增查詢而非連線來源 |
| 負載分散 | **N/A**：無多實例 |
