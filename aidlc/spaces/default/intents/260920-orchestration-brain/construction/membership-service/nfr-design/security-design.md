# 安全設計 — `U19 membership-service`

> 本站設計上游 `nfr-requirements` 的 **29 條 `NFR12.x`** 的承載形式。
> 本站**不複寫** `functional-design` 的 29 條 `BR` 規則（`team.md` 的單一真實來源）。
>
> `U19` 是 `service`，故六份設計產出全部適用（`U5`／`U18` 只有 `security-design`）。

## 〇、上游依據

| 上游產出 | 本站用到它的什麼 |
|---|---|
| `security-requirements.md` | `NFR12.1`–`NFR12.5`（鎖）；ADR-0006 四面向的增量 |
| `observability-requirements.md` | `NFR12.6`／`NFR12.7`／`NFR12.26`（拒絕的 log） |
| `reliability-requirements.md` | `NFR12.15`–`NFR12.25`（交易邊界、冪等、回填） |
| `performance-requirements.md` | `NFR12.8`–`NFR12.12`（查詢形狀） |
| `scalability-requirements.md` | `NFR12.13`（鎖的範圍限單一專案）——本站 §一之二 的排序設計以它為前提：鎖的粒度是專案，故多專案操作才會需要排序 |
| `tech-stack-decisions.md` | 三項：① `with_for_update()` 是本單元**唯一**的技術增量且 repo 零前例；② **SQLAlchemy 的 SQLite dialect 會靜默丟掉 `with_for_update()`**，故併發驗證不能走既有測試路徑（本站 §五第 2 項的風險陳述以它為依據）；③ 兩種新測試形狀（真實 PG ＋ barrier 的併發測試、`hypothesis` 的 PBT） |
| `functional-spec.md`（本單元） | §2.1–§2.9 九條工作流程；§三 狀態機；§八 ADR-0006 三欄表 |
| `rules.md`（本單元） | `BR1.1`（唯一入口）、`BR2.1`（守門）、`BR6.1`–`BR6.4`（既有端點） |
| `contract-summary.md` | `K-16`（本單元）、`K-07`（`U7` 的專案階層）、`K-15`（兩張表） |

## 一、鎖的設計：取得順序是本節的實質產出

`NFR12.1`–`NFR12.3` 定下「鎖父 `projects` 列、`assertCanDeactivate` 不取鎖」。
**上游沒有定取得順序，而不定會產生死鎖。** 這是本站的設計。

### 1.1 死鎖軌跡（本站推導，上游未涵蓋）

自動改選對**一位**被停用的 owner 可能涉及**多個**專案（他可能是數個專案的 owner）。
若兩個操作以相反順序取鎖：

| 時間 | T1（停用 `X`，改選專案 7、9） | T2（停用 `Y`，改選專案 9、7） |
|---|---|---|
| 1 | 鎖專案 **7** | |
| 2 | | 鎖專案 **9** |
| 3 | 等專案 **9** | |
| 4 | | 等專案 **7** → **死鎖** |

PostgreSQL 會偵測並中止其中一個交易（`deadlock detected`），
故後果不是永久卡住而是**一個停用請求失敗**——但它是**不可重現的間歇失敗**，
而這類失敗在本 repo 的驗證層（容忍 flaky 的 CI）會被當成雜訊。

### 1.2 設計決定：一律以 `projects.id` 遞增順序取鎖

| 設計 | 內容 |
|---|---|
| **取得順序** | 任何一次操作若需鎖多個專案，**一律按 `projects.id` 遞增**取鎖 |
| **單專案操作** | `inviteMember`／`removeMember`／`changeRole` 只鎖一列，順序問題不存在 |
| **多專案操作** | 只有自動改選（一位 owner 多個專案）。它先把專案 id 排序，再逐一取鎖 |
| **為什麼不用「一次鎖全部」** | `SELECT ... WHERE id IN (...) FOR UPDATE` 的取鎖順序由執行計畫決定、**不保證**；明確的排序迴圈才是決定性的 |

**這不是我發明的手法**，是防死鎖的標準做法（全域一致的資源排序）。
本站的工作是**指名那個排序鍵**並寫明它為什麼不能靠 `IN (...)` 達成。

### 1.3 鎖的範圍不含 `assertCanDeactivate`，而這留下一個已知窗口

`NFR12.3` 明文它不取鎖。設計後果：它回「通過」之後、既有端點寫入 `is_active`
之前，另一個交易可能改變該使用者的管理者身分。**本站不關閉這個窗口**，
理由與 `NFR12.3` 相同（取鎖會把一個管理者動作變成廣域鎖），並承接 `OPEN-N19-2`。

## 二、拒絕 log 的設計形狀（`NFR12.6`／`NFR12.26`）

| 欄位 | 值 | 為什麼是它 |
|---|---|---|
| `story_id` | `K3`（成員）／`K4`（需求欄位） | 與 `BR1.5` 的 `MembershipForbidden(story_id=...)` 同一個值，使 log 與例外可對照 |
| `action` | 方法名（`invite_member` 等） | 可分辨是哪一種越權嘗試 |
| `project_id` | 具名參數的值 | `BR1.4` 已要求它是具名參數，故一定取得到 |
| `principal` | 使用者識別 | **只有識別，不含任何憑證**（`NFR12.26`） |

**不含的欄位與理由**：不含 token／session／授權標頭（`NFR12.26`）；
不含被拒的具體原因字串（避免把授權矩陣的內部結構寫進 log）。

## 三、`[ND1]`=A 的設計：`U19` 包一層，而本站更正了它的代價

### 3.1 設計形狀

```
U19.MembershipFacade.create_project_with_owner(principal, name)
  ├─ 鎖？ 無——此時專案還不存在，沒有可鎖的父列
  ├─ 呼叫 U7 的 HierarchyFacade.create_project(principal, name=name)   # 合 components.md 的依賴方向
  ├─ 寫一列 ProjectMember(project_id=新專案, user_id=principal, role='project_admin')
  └─ 兩者同一交易（NFR12.18）
```

**成員寫入留在 `U19`**（合 `BR1.1`），**依賴方向仍是 `U19 → U7`**（合 `components.md:558-561`）。

**一個需要寫明的設計細節**：建立路徑**不需要取鎖**——`NFR12.1` 的鎖保護的是
「對既有專案的成員變更」，而建立時該專案尚不存在，沒有併發對手。
（這一點若不寫明，實作者會以為 `NFR12.1` 的「任何成員關係變更」涵蓋它而去鎖一個還沒有的列。）

### 3.2 本站對 `[ND1]`=A 代價描述的更正

提問時我寫 A 的代價含「與 `BR6.4` 同樣觸發不可分批部署，且須確認前端呼叫點」。
**作答後實地查證，這段有一半是錯的**：

| 查證 | 結果 |
|---|---|
| `frontend/src` 對 `projects` 的命中數 | **0**（寬鬆比對整個目錄） |
| 對照組：`AdminPage.tsx:163` 是否消費停用端點 | **是**（路徑 `/api/auth/<id>/active`） |
| `openapi.json` 是否已宣告建立端點 | **是**：`/api/hierarchy/projects` 有 `get` 與 `post` |

**`BR6.4` 的「不可分批」對本變更不成立**——它的依據是「既有端點的回應形狀變更
**且有既有消費端**」，而建立專案端點**今天沒有任何前端消費端**。
`BR6.4` 真正適用的是停用端點那一條。

**而有一項我沒提到的後果，它是好消息**：移動該端點會改到 `openapi.json` 的
path／operation，而**漂移閘門對 path 變更有效**（它對 `BR6.2` 的「新增 409 狀態碼」
無效，是因為那是**狀態碼**層級的盲區，不是 path 層級）。故本變更會被 CI 機械抓到。

記為 `OPEN-ND19-1`（更正記錄，非新缺口）。

## 四、ADR-0006 四面向：本站的增量

逐格對照 `functional-spec.md` §八 與 `security-requirements.md` §三 的同名表。
**上一站在 Network exposure 一格與 `functional-spec.md` §八 不一致而未揭露
（審查 `R-02`，Major）；本站以 §八 的判定為準並寫出落點。**

| 面向 | 判定（與 `functional-spec.md` §八 一致） | 本站的設計增量 |
|---|---|---|
| **IAM** | **適用（本單元的核心）** | 鎖的取得順序（§一之二）——它是 `BR2.1` 在併發下成立的前提；拒絕 log 的欄位集合（§二） |
| **Encryption** | **本單元無落點**（上游為此面點名的落點是 `McpBridge`／`U21`） | 無 pattern。§二的 `NFR12.26` 是**不得寫入**憑證的禁令，不是加密設計 |
| **Network exposure** | **適用，有落點**（新 HTTP 端點供 `U24`；擴充一處既有端點的回應契約；**`[ND1]`=A 再加一項：建立專案端點的擁有者改變**） | 三項落點逐一寫明；`BR6.1` 的三道檢查次序；`BR6.2` 的顯式 409；§三之二 查出 `BR6.4` 對建立端點**不適用**而對停用端點適用 |
| **Audit logging** | **適用** | 稽核列與 log **兩個載體**的界線（§二）；拒絕不進稽核表（`NFR12.7`） |

**PBT：適用且 blocking**，作用對象 `selectSuccessor`，性質為**排列不變性**。
本站的設計增量是指出**鎖與 PBT 互不相干**：`selectSuccessor` 不讀 DB，
故它完全在鎖的範圍之外——這是 `BR4.1`（純函式）的附帶好處。

## 五、殘餘風險

1. **`assertCanDeactivate` 的 TOCTOU 窗口**（`OPEN-N19-2`，承接）。
2. **鎖的取得順序無機械強制**：沒有任何工具會檢查「多專案操作是否按 id 遞增取鎖」。
   違反它的後果是間歇性死鎖，而間歇失敗在容忍 flaky 的 CI 中會被當成雜訊。
   記為 `OPEN-ND19-2`。
3. **`BR1.1`（facade 是唯一入口）仍無機械強制**（承接 `OPEN-FD19-3`）。
   `[ND1]`=A 讓建立路徑合規，但沒有任何機制擋住下一個人直接寫表。
