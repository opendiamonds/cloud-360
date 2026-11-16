# 安全需求 — `U8 memory-service`

> 本單元是本 repo **第二套授權模型**的持有者（擁有者 ＋ 可見範圍，非
> story-action），且是記憶這批**個人可識別使用歷程**的唯一讀寫端。
> 它的安全面是本 intent 最寬的之一：四條 HTTP 端點（含本輪新增的建立端點）、
> 兩套授權判定、一個有刪除權的身分、以及一個公開可讀風險為零但洩漏後果最重的
> 資料集。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `requirements.md` | `NFR6`（schema 隔離與其 CI 驗證）、`NFR7`（90 天保存 ＋ 刪除稽核 ＋ 加密要求須於設計階段明確）、`FR4.3`／`FR4.3a`／`FR4.3b`／`FR4.4`／`FR4.6`／`FR4.7` |
| `functional-design/rules.md` | 22 條規則，其中 `BR1`／`BR2`／`BR4`／`BR5`／`BR6` 全部是授權或稽核 |
| `functional-design/functional-spec.md` | §1.4–§1.6 的流程順序（本檔 `NFR7.22` 的依據） |
| `inception/contract-design/contract-summary.md` | `K-08` 的 `authorization_model`、`on_denied`、`hard_rule` |
| `memory-data/nfr-requirements/security-requirements.md`（`U5`） | `NFR6.1`／`NFR6.2`（靜態與傳輸加密）；`OPEN-CG5-1`（grant 邊界未被 CI 驗證） |
| `memory-purge/`（`U9`，已交付） | `NFR7.10`–`NFR7.15`、`NFR6.10`、`NFR8.10` 與其裁決 |
| `schema_rbac.sql`（版控） | 兩張表的實際 DDL、grant 區塊、`ck_memory_audit_events_action` |

## 一、編號從 `.20` 起算的理由（先說，以免被讀成跳號）

`NFRx.y` 在本框架是 per-unit 的，但本 intent 的低位號已被大量佔用。
本站以腳本實算全 record 已用的 sub-number：

| 父項 | 已被佔用 |
|---|---|
| `NFR3` | 1, 2 |
| `NFR4` | 1–4 |
| `NFR6` | 1–5, 10 |
| `NFR7` | 1–4, 6, 10–15 |
| `NFR8` | 1–10 |
| `NFR9` | 1, 2 |

故本單元一律自 **`.20`** 起算。**這不是跳號，是為了讓 id 在本 intent 內可唯一定位**
——`U9` 的經驗證明重用會讓同一個 id 在兩份文件指不同需求，而其中 `NFR7.2`
已外溢到版控 SQL 的索引註解、實質成為全域識別字。

## 二、本站定案的安全需求（九條，全部二元可判）

| id | 需求 | 二元判準 | 來源 |
|---|---|---|---|
| **`NFR7.20`** | 記憶的擁有者一律為寫入時呼叫者的已驗證身分；酬載中任何意圖指定擁有者的欄位**被忽略**且不回報錯誤 | 兩個測試：① 寫入後 `ownerUserId` 等於已驗證身分；② 酬載帶他人身分時仍為已驗證身分、且回應為成功而非 422 | `FR4.3a`；`BR1.1`／`BR1.2`；`AC4.4.1`／`AC4.4.2` |
| **`NFR7.21`** | 新記憶的可見範圍一律為最窄（`owner`）；寫入端**不接受** `visibilityScope` 作為輸入 | 寫入後該欄為 `owner`；酬載帶 `platform` 時仍為 `owner` | `FR4.3b`；`BR2.1`；`AC4.4.3` |
| **`NFR7.22`** | 放寬可見範圍僅 `Platform_Admin`／`Platform_Owner`，且**授權判定須先於記憶存在性判定** | allow/deny 雙向：① 具該角色 → 2xx；② 不具 → **403**；③ **不具該角色 ＋ 不存在的 memoryId → 403（不是 404）** | `FR4.3b`；`K-08` 的 `scope_widening`；`BR5.1`；`functional-spec.md §1.5` 步 2 |
| **`NFR7.23`** | 稽核事件的讀取僅 `Platform_Admin`／`Platform_Owner` | allow/deny 雙向：具該角色 → 2xx；不具 → 403 | `[FD2]`=A；`BR6.1`；`AC4.3.3` |
| **`NFR7.24`** | 刪除僅限擁有者本人；**角色不授予跨使用者的刪除權** | 三個案例：① 擁有者 → 204；② 他人（含 `Platform_Admin`）→ 403；③ 不存在 → 404 | `FR4.6`；`BR4.1` |
| **`NFR7.25`** | 刪除與可見範圍放寬各留一筆稽核事件，且稽核寫入與資料變更**在同一交易邊界內** | 刪除 N 列後 `deleted_by_user` 新增 N 筆；放寬後 `scope_changed` 帶正確的前後值；交易中止時兩者皆不生效 | `FR4.7`；`BR4.2`／`BR5.3`；`AC4.2.2`／`AC4.3.1` |
| **`NFR7.26`** | 記憶的**建立不產生**稽核事件 | 寫入後 `memory_audit_events` 列數不變 | `BR7.4`（由 `ck_memory_audit_events_action` 無建立值裁決） |
| **`NFR6.20`** | 本單元**不新增**任何資料庫連線身分，亦不以 `-U` 或連線字串覆寫既有身分 | 本單元 diff 不含新的資料庫憑證、不含 `-U`；連線沿用既有 `database.py` 的 engine | `FR4.4`；`NFR6`；承 `U9` 的 `NFR6.10` 同形 |
| **`NFR6.21`** | 記憶內容、`embedding`、以及任何可識別的使用歷程**不得出現在應用程式日誌中** | 授權拒絕的 log 只含 principal 識別字、`memoryId`、`reason`；**不含 `content`** | ADR-0006 audit logging；承 `U5` 的 `BR2.2`（稽核表刻意不含內容）同一理由 |

### 2.1 `NFR7.22` 的第三個案例是這一條的全部重點

`functional-spec.md §1.5` 步 2 把**角色判定排在記憶取得之前**，理由是：
若先查記憶，無權者會從 404 與 403 的差異得知**某個 memoryId 是否存在**，
而那是一個跨使用者的記憶存在性 oracle。

**判準因此必須包含第三個案例**（無權 ＋ 不存在 → 403）。
只測前兩個的話，一個把順序寫反的實作也會通過。

**本站同時記載一個已知的不一致**：`functional-spec.md §1.4`（刪除）的順序
是**先取記憶、後判擁有者**，於是刪除路徑上存在同樣的 oracle
（非擁有者對存在的 id 得 403、對不存在的 id 得 404）。
這一點已由本單元 `functional-design` 的審查以 `R-03`（Major）指出並帶進關卡，
**本站不自行修改已核可的上游產出**，但 `NFR7.24` 的三個案例如實反映了
目前的設計（② 403、③ 404），故它與 `NFR7.22` 的形狀**刻意不同**。
處置見 `N8-6`。

## 三、`NFR6`（schema 隔離）在本單元的狀態：繼承，且缺口比之前更值得補

| 查證項 | 結果 |
|---|---|
| grant 邊界的載體 | `schema_rbac.sql` 的 `DO` 區塊，授予 `current_user` 對 `memory` schema 的 USAGE ＋ 表的 CRUD |
| 它被 CI 驗證了嗎 | **沒有**——`U5` 的 `OPEN-CG5-1` 逐字：「驗它需要第二個資料庫角色並以該角色嘗試越界，而 service container 只有 superuser」 |
| 連線身分是不是真的受限 | **不是**——`U9` 的 `[ND2]`=A 已查證：`POSTGRES_USER` 建立的角色**本身即 superuser**，故本系統目前不存在任何非 superuser 的連線身分 |
| 本單元讓這個缺口更嚴重嗎 | **是**：本單元是一個有 **DELETE** 權的新消費者（`BR4.1`），而 grant 邊界是資料庫層的唯一防線 |

**本站不宣稱 `NFR6` 在本單元已被強化**，也不假裝邊界存在。
`NFR6.20` 保留的是「不要變得更糟」（不新增更高權限的路徑），
與 `U9` 的 `NFR6.10` 同形。

是否新增真正受限的資料庫角色，承接 `OPEN-ND9-2`（後續 intent）——
其代價已由 `U9` 寫明：新憑證會打破 `NFR8.10` 的零新部署設定，
並在公開可讀的 Actions log 中引入風險。

## 四、加密：`NFR7` 的指派已由 `U5` 回答，本單元無增量

`NFR7` 逐字要求 episodic memory 的「靜態儲存與傳輸的加密要求**須於設計階段明確**」。

| 面向 | `U5` 的回答 | 本單元的增量 |
|---|---|---|
| 靜態 | 主機層（LUKS），`NFR6.1` | **無**——不新增儲存體 |
| 傳輸 | compose 內部流量，`NFR6.2` | **無**——本單元的 HTTP 端點走既有的 nginx ＋ Cloudflare Tunnel 路徑，與既有端點同一條 |

**不寫「不適用」**：該面向對本單元成立，只是由上游承載且本單元未改變其前提。

## 五、ADR-0006 四面向逐格判定（hard constraint）

`project.md ## Mandated` 逐字要求「對每一項變更檢查 ADR-0006 security baseline
的四個面向」，且「涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage
產出中明列 security 影響與處置，不得僅以『已有 ADR-0006』帶過」。

**填表前已逐格 grep 上游同名表格並比對判定**（`U5`、`U9`、
本單元 `functional-design §八`），差異處明列。

| 面向 | 判定 | 本單元的落點與增量 |
|---|---|---|
| **IAM** | **適用（本單元最寬的一格）** | **兩套授權模型**：擁有者模型（`NFR7.20`／`NFR7.24`）與角色模型（`NFR7.22`／`NFR7.23`）。**本輪新增的 IAM 面**是 `[FD2]`=A 定下的稽核讀取授權——在它之前 `K-08` 只寫 `raises: [MemoryForbidden]` 而未定誰可通過，`AC4.3.3` 不可實作。**與上游不同的一格**：`U5` 把 IAM 的落點記為 grant 邊界，本單元的 IAM 主要落在**應用層的兩套模型**，因為 grant 邊界目前不構成真實邊界（§三）。此差異來自 `U9` `[ND2]`=A 的實測，非重新判斷 |
| **Encryption** | **適用，本單元無增量** | 見 §四。**不寫「不適用」** |
| **Network exposure** | **適用，有增量** | 本輪新增 `POST /api/memory/records`（`[FD4]`=A），是本單元的第四條對外端點。它走既有的認證層與既有的 nginx 路徑，**不新增監聽埠、不新增 tunnel**；但它是一個**新的對外寫入面**，故這一格不是零增量。`/memory` 走 `ProtectedRoute` 但不包 `CapabilityRoute`（`K-08` 已查證不需新 story id） |
| **Audit logging** | **適用（本單元的核心之一）** | `NFR7.25`（刪除與放寬各留稽核、同交易邊界）＋ `NFR7.26`（建立不留稽核，由封閉集合裁決）＋ `NFR6.21`（日誌不得含記憶內容）。**本站新增 `NFR6.21`**：上游談的是稽核**表**不含內容，沒有人談應用程式**日誌**——而授權拒絕的 log 是最容易順手把 `content` 帶進去的位置 |

### PBT 判定：**N/A（非豁免）**，但附一條本站新增的決定性要求

ADR-0006 的 property-based hard constraint 點名三個落點
（IaC generator、cost calculator、agent routing）。**本單元不是其中任何一個**
——`agent routing` 指 `U11 intent-router`。故該 hard constraint 對本單元 N/A。

**但本站新增一條與之相鄰的要求**，記為 `NFR3.24`（列於效能面但本質是正確性）：

> 相似度排序在**分數相同**時必須有決定性的次級排序鍵，否則同一組輸入在
> 兩次呼叫之間可能回不同順序，而這在畫面上與「功能壞了」無法區分。

repo 內已有正解可抄：`backend/cost/estimate_readers.py:247-251` 的
`key=lambda item: (-item[1], item[0])`（先分數遞減、再以識別字遞增）。
若 `code-generation` 把該次級排序鍵實作為純函式，它就是本單元
**唯一**適合 property-based 測試的落點（`team.md` 已記載 repo 有 13 個 `@given`
的自發良好實踐，皆落在純函式模組）。記為 `N8-7`。

## 六、殘餘風險（逐項附承接）

| id | 內容 | 承接 |
|---|---|---|
| `N8-6` | **刪除路徑（`functional-spec.md §1.4`）存在記憶存在性 oracle**，與 §1.5 刻意避免的那一個同形。已由 `functional-design` 的審查 `R-03`（Major）指出並帶進關卡 | `code-generation`（3.5，**ALWAYS**）——實作時可就地把擁有者判定提到記憶取得之前，不需改上游文件 |
| `N8-7` | 相似度排序的決定性次級鍵（`NFR3.24`），含其 PBT 落點 | `code-generation`（3.5，**ALWAYS**） |
| `OPEN-CG5-1`（承接） | grant 邊界未被 CI 驗證；本單元是有刪除權的新消費者，故此缺口比之前更值得補 | 與 `OPEN-ND9-2` 同一個決定（後續 intent） |
| `OPEN-ND9-2`（承接） | 是否新增真正受限的資料庫角色 | 後續 intent |
| `FD8-5`（承接） | `BR5.1`（僅管理員得放寬）**沒有任何 AC**；本檔以 `NFR7.22` 的 allow/deny 雙向判準補上可驗性，但上游的 AC 缺口仍在 | `code-generation`（3.5）的測試 ＋ 下一輪 user-stories 修訂 |
