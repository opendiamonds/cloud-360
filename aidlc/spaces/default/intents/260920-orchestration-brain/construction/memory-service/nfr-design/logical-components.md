# 邏輯元件 — `U8 memory-service`

> 本檔是 `nfr-design` 與 `infrastructure-design` 之間的橋：
> 它給出**元件層級**的視圖，指出每個 NFR pattern 落在哪裡、
> 失敗域在哪裡、以及哪些資源是共用的。
>
> **本單元零新進程、零新容器**，故「元件」指的是進程內的模組邊界，
> 不是部署單位。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `nfr-requirements/tech-stack-decisions.md` | §三 的四層形狀與各層的禁令 |
| 本站 `security-design.md` | §一 的 facade 為唯一授權入口；`[D1]`=A 的回應收斂落在 facade |
| 本站 `reliability-design.md` | §一 的交易邊界落在 service 層 |
| 本站 `performance-design.md` | §一 的單一 SQL 落在 service 層；純函式層承載 `NFR3.24` |
| `inception/contract-design/contract-summary.md` | `K-08`（本單元擁有）、`K-05`（消費）、`K-06`（消費）、`K-10`（`U11` 消費本單元） |

## 一、元件清單與邊界

| 元件 | 職責 | 可碰 DB | 可拋 `HTTPException` | NFR pattern 落點 |
|---|---|---|---|---|
| `memory_router` | HTTP ↔ 例外的轉譯；分頁參數解析 | **否** | **是**（唯一一層） | `NFR7.28` 分頁、`NFR7.29` `limit` 上限 |
| `MemoryFacade` | **唯一授權入口**（`K-08` 的 `sole_entry`）：擁有者判定 ＋ 角色判定各一份 | 否（經 service） | 否——拋 `MemoryForbidden`／`MemoryNotFound` | `NFR7.20`–`NFR7.24`、`[D1]`=A 的回應收斂、`NFR7.30` 的拒絕日誌 |
| `memory_service` | 業務協調；單一 SQL 的組裝；交易邊界 | **是** | 否 | `NFR3.20` 的查詢設計、`NFR4.21` 的交易、`NFR7.34` 的過濾筆數 |
| `memory_ranking` | **純函式**：同分時的決定性次級排序鍵 | **否** | **否** | `NFR3.24` ＋ 其 PBT 落點（`D8-3`） |

### 1.1 各層的禁令是結構前提，不是風格偏好

| 禁令 | 若違反會壞掉的是什麼 |
|---|---|
| `memory_router` 不做授權判定 | 授權就有了第二份實作，而 `K-08` 的 `sole_entry` 保證失效；兩份實作遲早分歧 |
| `MemoryFacade` 不拋 `HTTPException` | facade 同時被 HTTP（`U15`）與同進程（`U11`）消費；拋 HTTP 例外會讓 `U11` 收到一個它無法處理的型別 |
| `memory_service` 不拋 `HTTPException` | 同上，且它是交易邊界的持有者——HTTP 關注點混進來會讓交易範圍難以推理 |
| `memory_ranking` 不讀 DB、不拋 `HTTPException` | **property-based 測試就寫不下去**（`D8-3`）。這是 `NFR3.24` 可驗的結構前提 |

## 二、失敗域與影響範圍

| 失敗 | 影響範圍 | 是否擴散到其他單元 |
|---|---|---|
| `U6 EmbeddingPort` 不可用 | `write` 與 `search` **皆失敗**（兩者都需要向量） | **是**：`U11 intent-router` 的分類會失去記憶輔助（經 `K-10`）。但 `U11` 的 `classify` 是否因此失敗由 `U11` 決定，本單元只負責大聲失敗 |
| PostgreSQL 不可用 | 本單元全部操作失敗 | 全系統——非本單元特有 |
| HNSW 索引缺失或 opclass 不符 | **功能正確、效能退化**，無錯誤 | 否。但 `NFR3.20` 會失敗（若有在量） |
| 記憶列數成長超過 `U9` 的清除能力 | `search` 延遲上升 | 否 |
| **`U9` 的清除漏跑** | `episodic` 無上界成長 → 延遲上升 ＋ 保存期合規失效 | **是**：`U9` 的 `NFR7.13` watchdog 是唯一偵測面 |

### 2.1 本單元的影響範圍比它的程式碼大

`BR7.1`／`BR7.2` 讓 `U13` 與 `U12` 成為本單元的**寫入端**
（`[FD1]`=B 的兩條新邊）。故：

| 若本單元的 `write` 失敗 | 則 |
|---|---|
| `U13` 每輪對話的 episodic 寫入失敗 | 對話本身是否因此失敗由 `U13` 決定——**本單元不規定它** |
| `U12` 工作項完成時的 procedure 寫入失敗 | 同上，由 `U12` 決定 |

**這兩個「由上游決定」是真實的未定項**：`[FD1]`=B 指派了寫入端，
但**沒有定寫入失敗時那兩個單元該怎麼辦**。
記為 `D8-7`，承接 `U12`／`U13` 各自的 `functional-design`。

## 三、共用資源

| 資源 | 擁有者 | 本單元的使用方式 | 邊界 |
|---|---|---|---|
| `memory.memory_records` | `U5`（`K-05`） | 讀寫 | grant 只開放 `memory` schema；**該邊界目前不是真實邊界**（`U9` 的 `[ND2]`=A） |
| `memory.memory_audit_events` | `U5`（`K-05`） | 寫（`deleted_by_user`／`scope_changed`）＋ 讀（稽核查詢） | 同上。`U9` 是它唯一的 DELETE 端 |
| `public.users` | baseline | 唯讀（擁有者與 actor 的參照） | 不改 |
| 既有 `database.py` 的 engine | baseline | 沿用 | **不建立第二個 engine**（`NFR6.20`） |
| `U6 EmbeddingPort` | `U6`（`K-06`） | 呼叫 | 經 Port 介面；不直接碰提供者 |
| 既有 FastAPI 進程 | baseline | 新增四個模組 | 無隔離——本單元的例外若未被攔會影響同進程的其他 router |

### 3.1 最後一列的誠實記載

本單元與既有的全部 router **共用同一個進程**，沒有 bulkhead。
一個未被攔截的例外（例如 `memory_ranking` 拋出未預期的型別錯誤）
會變成 500 並由 FastAPI 的預設處理回報，不會讓進程崩潰——
但**若它發生在 `U11` 的同進程呼叫路徑上**，`U11` 的分類會一併失敗。

**本站不設計 bulkhead**（無多實例、無執行緒池可隔離），
但要求 `memory_ranking` 為純函式正是降低這個風險的手段：
純函式的失敗模式有限且可用 PBT 窮舉。

## 四、NFR pattern ↔ 元件 對照（給 `infrastructure-design` 的交接）

| NFR pattern | 落在哪個元件 | `infrastructure-design` 需要知道的 |
|---|---|---|
| HNSW 索引（`NFR3.22`） | **不在任何元件內**——在 `U5` 的 schema | 四項 blocking 連帶義務（`schema_rbac.sql`／`DEPLOY.md`／`EXPECTED_INDEXES`／`verify_memory_schema.sql`） |
| 分頁（`NFR7.28`） | `memory_router` | 觸發 OpenAPI drift（`D8-4`） |
| 回應收斂（`[D1]`=A） | `MemoryFacade` ＋ `memory_router` | 觸發 OpenAPI drift（`D8-2`）；偏離 `K-08`（`D8-1`） |
| 交易邊界（`NFR4.21`） | `memory_service` | 無基礎設施影響 |
| 日誌白名單（`NFR6.21`） | 全部四層 | 無新 logging 基礎設施；沿用既有容器日誌 |
| 零新部署設定（`NFR8.20`） | — | `requirements.txt` diff 為空；不動 `deploy/` |

**本單元對 `infrastructure-design` 的唯一實質輸入是第一列**
（HNSW 索引的四項連帶義務）。其餘皆為進程內變更。
