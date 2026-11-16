# 安全設計 — `U8 memory-service`

> 本單元持有本 repo **第二套授權模型**，且是個人對話歷程的唯一讀寫端。
> 本檔把 `nfr-requirements` 的九條安全需求轉成具體機制，並記錄
> `[D1]`=A 對已核可契約 `K-08` 的一處刻意偏離。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `nfr-requirements/security-requirements.md` | `NFR7.20`–`NFR7.26`、`NFR6.20`、`NFR6.21` 與其二元判準 |
| `nfr-requirements/tech-stack-decisions.md` | 四層形狀與 facade 為 `sole_entry` |
| `functional-design/rules.md` | `BR1`／`BR2`／`BR4`／`BR5`／`BR6` 共 15 條授權或稽核規則 |
| `functional-design/functional-spec.md` | §1.4–§1.6 的流程順序（本檔 §二的對象） |
| `inception/contract-design/contract-summary.md` | `K-08` 的 `authorization_model`、`on_denied`、`hard_rule`、`public_interface` |
| `schema_rbac.sql`（版控） | `id SERIAL PRIMARY KEY`（`:453`）、grant 區塊、`ck_memory_audit_events_action` |
| 本站 `[D1]`=A | 刪除路徑的回應收斂 |

## 一、兩套授權模型的實作設計

`K-08` 的 `sole_entry` 是 `MemoryFacade`。**全部授權判定只在該層，且各只有一份。**

```
memory_router.py   ── 轉譯 HTTP ↔ 例外；**不做任何授權判定**
      │
MemoryFacade       ── 唯一入口：擁有者判定 ＋ 角色判定，各一份
      │
memory_service.py  ── 業務協調，讀寫 DB；**假設授權已通過**
      │
memory_ranking.py  ── 純函式；不讀 DB、不拋 HTTPException
```

| 判定 | 依據 | 承載的規則 | 拒絕時 |
|---|---|---|---|
| **擁有者模型** | 列的 `ownerUserId` 與呼叫者是否相同 | `BR2.2`（讀的過濾）、`BR4.1`（刪） | `MemoryForbidden(reason="owner")` |
| **角色模型** | 呼叫者是否為 `Platform_Admin`／`Platform_Owner` | `BR5.1`（放寬）、`BR6.1`（稽核查詢） | `MemoryForbidden(reason="scope")` |

**兩者不可互換。** 最容易出的錯是用角色模型判讀寫：`Platform_Admin`
**不因其角色而能讀或刪**他人的記憶（`BR4.1` 的 note）。
它被授予的只有兩件事——放寬可見範圍與查稽核。

**角色判定只實作一份**，由 `BR5.1` 與 `BR6.1` 共用；兩者的角色集合相同
（`[FD2]`=A 刻意與 `widen_scope` 對齊），故第二份實作沒有存在理由。

### 1.1 `BR2.2` 的過濾位置

可見範圍過濾**在 SQL 的 `WHERE` 內**，不在應用層事後篩：

| 做法 | 後果 |
|---|---|
| **SQL 內過濾（採用）** | 不可見的列從未離開資料庫；`LIMIT` 作用在已過濾的集合上，故回傳筆數正確 |
| 應用層事後篩 | 不可見的列會先被讀進進程（洩漏面擴大），且 `LIMIT n` 會在過濾後剩不足 n 筆——分頁與檢索筆數都錯 |

`K-08` 的 `authorization_responsibility` 逐字「可見範圍的過濾在 facade 內完成，
呼叫端不得自行過濾」——**facade 內完成**指的是責任歸屬，
而實作上該條件下推到 SQL 是更強的形式，不是違反。

## 二、`[D1]`=A：刪除路徑的回應收斂（**對 `K-08` 的刻意偏離**）

### 2.1 查出的問題

`functional-spec.md §1.4` 先取記憶、後判擁有者，於是：

| 情境 | 原設計的回應 |
|---|---|
| 不存在的 id | **404** |
| 存在但屬他人 | **403** |

而 `schema_rbac.sql:453` 的主鍵是 `id SERIAL PRIMARY KEY`——**連續整數**。
故任何已認證使用者可對 `DELETE /api/memory/records/{id}` 走訪 `1..N`，
以 403／404 的差異取得**全表哪些 id 存在**。

**這是整張表的枚舉，不是單點存在性洩漏**（我在 `nfr-requirements §二之一`
當時的描述偏輕）。STRIDE 分類為 Information Disclosure。
洩漏的是後設資料（其他使用者的記憶總量與分布），**不會刪到別人的資料**
——`BR4.1` 的擁有者判定仍然有效。

**而本單元的另一條路徑做了相反的事**：§1.5（放寬）刻意先判角色再取記憶，
並寫明理由就是避免這個 oracle。同一個威脅、兩種處置，
該不一致已由 `functional-design` 的審查以 `R-03`（Major）指出。

### 2.2 設計：對外收斂，內部保留

**使用者裁決 `[D1]`=A**：刪除路徑把兩種失敗收斂為**同一個對外回應（404）**。

| 層 | 行為 |
|---|---|
| `memory_service` | 照實回報：找不到，或找到但擁有者不符 |
| `MemoryFacade` | **兩者皆拋 `MemoryNotFound`**；但在拋出前以 `reason="owner"` 寫入日誌（`NFR7.30`），使稽核與診斷仍可區分 |
| `memory_router` | `MemoryNotFound` → **404**。刪除路徑**不回 403** |

**內部保留區分是這個設計的關鍵**：若連日誌也收斂，營運端就無法分辨
「使用者誤刪已刪除的記憶」與「有人在枚舉」——而後者是需要被看到的。

### 2.3 這處偏離的完整代價（逐項，不美化）

| # | 代價 | 處置 |
|---|---|---|
| 1 | **偏離 `K-08`**：其 `delete` 宣告 `raises: [MemoryForbidden, MemoryNotFound]`，HTTP 半邊宣告 `403` 與 `404`。收斂後刪除路徑的 403 不再可達 | 記為 `D8-1`，須在下一輪契約修訂追認。**本站不改已核可的契約** |
| 2 | **`NFR7.24` 的判準必須改**：原為「② 他人（含 `Platform_Admin`）→ 403」，改為「→ **404**」 | 本檔 §二之四 給出改後判準；`nfr-requirements` 的原文不回改（`refined-mockups:c3` 的形狀），以本檔為下游依據 |
| 3 | `openapi.json` 的 `DELETE` 回應集合會少一個 403 | 觸發 OpenAPI drift 閘門，須重 dump。記為 `D8-2` |
| 4 | 擁有者誤刪已刪除的記憶仍得 404 | **行為不變**，非新代價 |

### 2.4 改後的 `NFR7.24` 判準（三個案例）

| # | 情境 | 期望 |
|---|---|---|
| ① | 擁有者刪自己的記憶 | **204** |
| ② | 他人（含 `Platform_Admin`）刪該記憶 | **404**（原為 403） ＋ 日誌含 `reason="owner"` |
| ③ | 任何人刪不存在的 id | **404** ＋ 日誌不含 `reason="owner"` |

**② 與 ③ 的對外回應刻意相同，差異只在日誌**——這正是 oracle 被關閉的證據，
故判準必須同時斷言「狀態碼相同」與「日誌可區分」，缺一不可。

## 三、`NFR7.22` 的順序設計（放寬路徑，無偏離）

§1.5 的順序**維持原樣**：先判角色、後取記憶。

| 步 | 動作 | 拒絕時 |
|---|---|---|
| 1 | 角色不是 `Platform_Admin`／`Platform_Owner` | `MemoryForbidden(reason="scope")` → **403** |
| 2 | 取記憶；不存在 | `MemoryNotFound` → 404 |

**為什麼這條不需要收斂**：角色判定在取記憶**之前**，故無權者在任何 id 上
都得到同一個 403，無法區分存在與否——oracle 本來就不存在。
稽核查詢（§1.6）同形。

**設計上的對稱性**：放寬與稽核查詢用「**先判角色**」關閉 oracle；
刪除無法這樣做（要知道擁有者必須先取列），故改用「**收斂回應**」。
兩種手法不同但目的相同，寫下來以免被讀成不一致。

## 四、輸入驗證與日誌衛生

### 4.1 輸入驗證（寫入端）

| 項目 | 設計 |
|---|---|
| `kind` | 封閉集合比對（`EC3`）；不在集合內 → 422 |
| `content` | 去除前後空白後長度 > 0（`EC2`）；否則 422 |
| `visibilityScope` | **不接受為輸入**（`BR2.1`／`NFR7.21`）——不是驗證，是不存在該參數 |
| `ownerUserId` | **不接受為輸入**（`BR1.2`／`NFR7.20`）；酬載若帶則**靜默忽略**，不回 422 |

**`ownerUserId` 刻意靜默忽略而非拒絕**：回 422 會讓呼叫端以為
「換個欄位名就能指定」，而忽略使該能力不存在。這是 `BR1.2` 的原設計。

### 4.2 日誌衛生（`NFR6.21`／`NFR7.31`）

**設計為欄位白名單，而非黑名單。**

| 允許 | principal 識別字、`memoryId`、`kind`、`reason`、過濾後筆數 |
|---|---|
| **禁止** | `content`、`embedding`、以及**整個模型物件** |

**禁止整個模型物件是這一條的關鍵**：`logger.warning(f"denied: {memory}")`
會把 `content` 帶進日誌，而它在功能上完全正常、測試也會綠。
本 repo 為 public 且 Actions log 公開可讀（`project.md` 逐字
「一次意外 echo 即等同公開發布」），而本單元處理的是個人對話歷程。

**驗證方式**：`NFR7.31` 的判準是**字串比對**——測試拿 fixture 的 `content`
去比對日誌輸出，確認不命中。不是人工審查。

## 五、STRIDE（本單元的攻擊面）

| 類別 | 本單元的威脅 | 處置 |
|---|---|---|
| **S** Spoofing | 偽造身分以取得他人記憶 | 沿用既有認證層；`BR1.1` 使擁有者不可由酬載指定 |
| **T** Tampering | 竄改他人記憶的可見範圍 | `BR5.1` 角色判定 ＋ `BR5.3` 稽核（前後值） |
| **R** Repudiation | 否認刪除過某筆記憶 | `BR4.2` 稽核（`deleted_by_user` ＋ actor ＋ 時間），且與刪除同交易（`NFR4.21`） |
| **I** Information Disclosure | **① 記憶枚舉 oracle**（§二）；**② 日誌洩漏內容**（§四之二）；③ 跨使用者讀取 | ① `[D1]`=A 收斂回應；② 欄位白名單；③ `BR2.2` 在 SQL 內過濾 |
| **D** Denial of Service | 無上界的列出或檢索耗盡資源 | `NFR7.28` 分頁 ＋ `NFR7.29` 伺服器端 `limit` 上限 |
| **E** Elevation of Privilege | 以角色繞過擁有者判定 | **兩套模型刻意分離**（§一）；`Platform_Admin` 不得讀或刪他人記憶 |

**風險最高的一格是 I**，而它有三個來源——其中兩個是本站新查出或新收斂的。

## 六、`NFR6.20`：不新增連線身分（繼承，無增量）

| 項目 | 設計 |
|---|---|
| 連線來源 | 沿用既有 `database.py` 的 engine；**不建立第二個 engine、不帶 `-U`、不組連線字串** |
| grant 邊界 | 沿用 `U5` 的 `DO` 區塊；本單元不改 grant |
| 誠實限定 | 該邊界**目前不構成真實邊界**——`U9` 的 `[ND2]`=A 已實測 `POSTGRES_USER` 建立的角色本身即 superuser。`NFR6.20` 保留的是「不要變得更糟」 |

**本單元讓 `OPEN-CG5-1` 更值得補**：它是一個有 DELETE 權的新消費者，
而 grant 邊界是資料庫層的唯一防線且未被 CI 驗證。承接 `OPEN-ND9-2`。

## 七、加密設計：無增量

| 面向 | 承載者 | 本單元 |
|---|---|---|
| 靜態 | 主機層 LUKS（`U5` 的 `NFR6.1`） | 不新增儲存體 |
| 傳輸 | compose 內部 ＋ 既有 nginx／Cloudflare Tunnel（`U5` 的 `NFR6.2`） | 新增的 `POST` 走與既有端點同一條路徑 |

**不寫「不適用」**：該面向成立，由上游承載且本單元未改變其前提。

## 八、ADR-0006 四面向

**填表前已逐格比對上游同名表格**（`nfr-requirements/security-requirements.md §五`、
`U5`、`U9`），差異處明列。

| 面向 | 判定（與上游一致） | 本站的設計增量 |
|---|---|---|
| **IAM** | 適用（本單元最寬的一格） | §一的兩套模型實作分離 ＋ 角色判定只一份。**本站新增**：`[D1]`=A 的回應收斂屬 IAM 面的設計決定（它改變拒絕路徑的可觀察結果） |
| **Encryption** | 適用，無增量 | §七。不寫「不適用」 |
| **Network exposure** | 適用，有增量 | 新增的 `POST` 是第四條對外端點，走既有認證層與既有 nginx 路徑；零新監聽埠、零新 tunnel |
| **Audit logging** | 適用（核心之一） | `BR4.2`／`BR5.3` 與資料變更**同交易**（`NFR4.21`）；**`[D1]`=A 之後，稽核與日誌是區分枚舉與誤刪的唯一手段**，故 §二之二 要求內部保留 `reason` |

### PBT：hard constraint 為 **N/A（非豁免）**，但有一個落點

ADR-0006 點名三個落點（IaC generator、cost calculator、agent routing）——
`agent routing` 指 `U11 intent-router`，本單元不是其中任何一個。

**但 `NFR3.24` 的次級排序鍵是純函式**（`memory_ranking.py`，§一的第四層），
它是本單元唯一適合 property-based 測試的對象：
性質為「同一輸入集合的任意排列，排序結果相同」。
repo 既有先例 `backend/cost/estimate_readers.py:247-251`。記為 `D8-3`。

## 九、殘餘風險

| id | 內容 | 承接 |
|---|---|---|
| `D8-1` | `[D1]`=A 偏離 `K-08`（刪除路徑的 403 不再可達） | 下一輪契約修訂追認 |
| `D8-2` | `openapi.json` 的 `DELETE` 回應集合變更，觸發 drift 閘門 | `code-generation`（3.5，**ALWAYS**） |
| `D8-3` | `NFR3.24` 純函式的 PBT 落點 | `code-generation`（3.5） |
| `OPEN-CG5-1`（承接） | grant 邊界未被 CI 驗證 | 與 `OPEN-ND9-2` 同一決定 |
| `FD8-5`（承接） | `BR5.1` 無 AC；本檔以 `NFR7.22` 的雙向判準補可驗性 | `code-generation` 的測試 |
| `N8-6`（關閉） | 刪除路徑的 oracle——**本站以 `[D1]`=A 關閉** | 已處置 |
