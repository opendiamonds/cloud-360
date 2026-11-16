# NFR Design 問題檔 — `U19 membership-service`

> Depth 為 `Minimal`。本站**只問一題**——它是上一站審查的 Critical（`R-01`），
> 而該發現的修法是**跨單元**的，不是我可以自行選定的。
>
> 其餘設計決定本站自行定案（鎖的取得順序、聚合查詢形狀、log 事件形狀、
> 元件失效域），理由是它們都有唯一正解或既有先例，見各設計檔。

## 〇、不重問的事（上游已定案）

| 事項 | 定案處 |
|---|---|
| 鎖父 `projects` 列、`assertCanDeactivate` 不取鎖、不改 `SessionLocal` | `[N1]`=A；`NFR12.1`–`NFR12.5` |
| 拒絕以 WARN 級結構化 log 記錄、不新增表 | `[N2]`=A；`NFR12.6`／`NFR12.7`／`NFR12.26` |
| 聚合查詢 ＋ 等價測試 | `[N3]`=C；`NFR12.10`–`NFR12.12` |
| 守門不變量為「至少一位管理者」、單一謂詞 | `[FD1]`=A；`BR2.1`／`BR2.2` |
| 稽核同表以 `cause` 區分 | `[FD3]`=A；`BR5.3`–`BR5.5` |
| 四項觀測目標刻意不設（追蹤／metrics／告警／SLO） | `observability-requirements.md` §四 |
| 既有專案回填為必要（`NFR12.24`／`NFR12.25`）；**承載形式**未定 | `OPEN-N19-4` |

---

## 一、`[ND1]` 「新建專案不再零成員」的修法——它跨越 `U19` 與已交付的 `U7`

### 審查 `R-01`（Critical）查出的事實，本站已獨立複驗

`NFR12.18` 要求「建立專案與其建立者成員列在同一交易內」，但**建立專案的寫入端不在本單元**：

| 層 | 位置 | 現況 |
|---|---|---|
| HTTP | `hierarchy_router.py:165` `create_project` | 既有端點 |
| facade | `hierarchy_facade.py:157` `create_project` | 既有，契約 `K-07`（`U7` 擁有） |
| service | `hierarchy_service.py:98` `create_project` | **只 `db.add(project)` ＋ `db.commit()`，完全沒有寫 `project_members`** |

`project_members` 在 `backend/` 的命中數為 **0**（唯一例外是本 intent 新增的 SQL 斷言檔）。

**而本單元上一站引用的理由本身是錯的**：`functional-spec.md` §九 風險 7 寫
「唯一寫 `projects.owner_user_id` 的是 `hierarchy_migration.py`（一次性遷移）」
——那句話在 `U7` 交付**之前**是對的，現在不是。`create_project` 是現行、持續運作的建立路徑。

**後果**：即使 `NFR12.24`／`NFR12.25` 的回填把既有專案全部補上，
**上線後透過既有路徑新建的每一個專案仍然是零成員**，而 `BR1.6`（查無列即拒絕）
會讓這些新專案的擁有者被判定為非成員。這不是一次性缺口，是**無上界持續發生**的缺口。

### 為什麼這題必須問

`BR1.1` 要求成員關係的寫入**只能經 `U19` 的 facade**；
而 `components.md:558-561` 的依賴方向是 **`ProjectMembership` → `ProjectHierarchy`**
（`U19` 依賴 `U7`，不是反向）。這兩條合起來讓三個看似自然的修法各自違反一條，
**不是偏好問題**。

### 選項

| 選項 | 修法 | 違反什麼／代價 |
|---|---|---|
| **A（建議）** | **`U19` 的 facade 包一層**：新增 `MembershipFacade.create_project_with_owner`，它先呼叫 `U7` 的 facade 建專案、再寫建立者成員列，兩者同一交易；建立專案的 HTTP 入口改走 `U19` 的 router（或 `U7` 的 router 退化為薄委派） | **兩條規則都不違反**：成員寫入留在 `U19`（合 `BR1.1`），依賴方向仍是 `U19 → U7`（合 `components.md`）。代價：**既有 HTTP 端點的擁有者改變**，而那是既有端點的契約變更，故與 `BR6.4` 同樣觸發「不可分批部署」；另需確認 `hierarchy_router.py:165` 的現有消費端（前端建立專案的呼叫點） |
| **B** | **直接改 `U7` 的 `hierarchy_service.create_project`（`:98`）**，在 `db.commit()` 之前加一列 `project_members` | 改動最小、單一 chokepoint、涵蓋全部呼叫端（含測試直呼 service 的那幾處）。**但它違反 `BR1.1`**：`U7` 會直接寫一張由 `U18` 擁有、`U19` 的 facade 治理的表，而 `BR1.1` 逐字禁止「跳過 facade 直接讀寫 `project_members`」 |
| **C** | **`U7` 的 `create_project` 改呼叫 `U19` 的 facade** 寫成員列 | 合 `BR1.1`。**但它製造依賴環**：`U7` → `U19` → `U7`，而 `components.md:558-561` 的宣告是單向 |
| **D** | **事件／callback**：`U7` 建完專案發一個領域事件，`U19` 訂閱後寫成員列 | 無環、合 `BR1.1`。代價：**repo 沒有任何領域事件機制**（零前例），要為一處需求引入一整套；且事件是非同步的，而 `NFR12.18` 要求**同一交易**——非同步訂閱者無法參與發布者的交易 |

[Answer]: A U19 的 facade 包一層
<!-- 作答時間 2026-10-06T23:44:08Z，取自 audit shard 的 QUESTION_ANSWERED 列而非估計 -->

### 作答後的更正：我把 A 的代價說大了

提問時我寫 A 的代價包含「既有 HTTP 端點的擁有者改變，故與 `BR6.4` 同樣觸發
不可分批部署，且須確認前端建立專案的呼叫點」。**作答後實地查證，這段有一半是錯的**：

| 查證 | 結果 |
|---|---|
| `frontend/src` 對 `projects` 的命中數 | **0**（寬鬆比對整個目錄，不只 API 路徑形狀） |
| 對照組：`AdminPage.tsx` 是否消費停用端點 | **是**，`frontend/src/pages/AdminPage.tsx:163` 呼叫 `fetch(apiUrl(...))`，路徑為 `/api/auth/<id>/active` |
| `openapi.json` 是否已宣告該端點 | **是**：`/api/hierarchy/projects` 有 `get` 與 `post` |

**所以 `BR6.4` 的「不可分批」對本變更不成立**——它的依據是「既有端點的回應形狀變更
**且有既有消費端**」，而建立專案端點**今天沒有任何前端消費端**。
`BR6.4` 真正適用的是停用端點那一條（`AdminPage.tsx:163` 確實在用）。

**但有一項我沒提到的後果，而它是好消息**：移動該端點會改到 `openapi.json` 的
path／operation，而 **OpenAPI 漂移閘門對 path 變更是有效的**
（它對 `BR6.2` 的「新增 409 狀態碼」無效，是因為該檔的 55 個 operation
宣告的狀態碼只有 `{200, 422, 201, 204}`——那是**狀態碼**層級的盲區，不是 path 層級）。
故本變更會被 CI 機械抓到。

**結論不變（A 仍是正解），但它比我描述的便宜。** 兩項更正都寫進
`security-design.md` §三與 `logical-components.md`，並記為 `OPEN-ND19-1`。

