# Security Design — `U24 member-pages-ui`

> 本檔是本站的 **review artifact**。單元類型 `ui`：零新端點、零持久層、
> 零新進程邊界，故本檔設計的是**瀏覽器端的安全姿態**，不是伺服器端架構。

## 零、上游來源

| 來源 | 用到什麼 |
|---|---|
| `construction/member-pages-ui/nfr-requirements/security-requirements.md` | `NFR4.80`／`NFR8.80`、`SEC-U24-1`–`SEC-U24-6`、ADR-0006 四面向判定、STRIDE |
| `construction/member-pages-ui/functional-design/functional-spec.md` | §二之一／§二之二 的 `role="status"` 硬約束、§四 六個端點（含 422 兩種語意） |
| `construction/member-pages-ui/functional-design/rules.md` | `BR21.3`（失敗兩分支）、`BR22.3`（`canManage` 推導）、`BR23.1`（422 分流） |
| `inception/contract-design/contract-summary.md` | `K-16` 的 `residual_gap`（沒有機制擋住前端自己猜） |

## 一、授權架構（本單元唯一的實質安全面）

**設計原則：前端不是授權決策點，而是授權結論的渲染點。**
這是一條**紀律**，由 e2e 守住——**不是**由欄位集合提供的結構保證。
（審查 `R-02`／Critical 更正：初版逐字寫「`MemberView` 刻意不含任何全域角色或
授權結論……故前端在結構上**沒有第二個授權資料來源可取用**……不是靠紀律，
是靠欄位集合」。**那句話是假的**，見 §一之一。）

| 層 | 誰決定（伺服器） | 前端可讀的對應來源 | 本單元的角色 |
|---|---|---|---|
| 能力層 `K3 view` | `require_story_action("K3","view")`——實測掛在 `membership_router.py:171`（`list_members`）、`:311`（`reselections/pending`）、`:335`（`acknowledge`） | `can("K3","view")` | 沿用既有 `CapabilityRoute`（`RouteGuard.tsx:35`）做路由把關；**另**以 `can("K3","view")` 作為橫幅查詢的**發出前置條件**（`frontend-components.md:157` 已逐字定案，見 §一之二） |
| **能力層 `K3 edit`（審查 `R-01`／Critical 補）** | `require_story_action("K3","edit")`——實測掛在 `membership_router.py:210`（邀請）、`:246`（移出）、`:283`（改角色），即本單元**全部三個寫入操作**。與 `"view"` 是**不同的 action** | `can("K3","edit")` | **併入 `canManage` 的前置條件**（見 §一之三） |
| 專案層角色 | `MemberView.role`（`project_owner`／`project_admin`／一般成員） | 無全域對應——只能由 `list_members` 回應取得 | `BR22.3`：以自身 `user_id` 在結果中查出自己的 `role` |
| 寫入操作的最終把關 | 伺服器（403／409／422） | — | 不預判；收到 403 的處置見 §一之三（**不是**重抓清單） |

### 一之一、前端確實有一個全域授權來源（審查 `R-02`）

| 查證 | 結果 |
|---|---|
| `useAuth().can(storyId, action)` | **存在**：`frontend/src/context/AuthContext.tsx:113-125`。`:119` 逐字 `const hasEdit = !!(p.edit \|\| p.can_edit);` |
| 資料來源 | 伺服器下發的 `user.permissions`（`AuthContext.tsx:116` 的 `user?.permissions?.[key]`） |
| 型別 | `StoryPermission` 含 `view`／`edit`／`review`（`frontend/src/context/auth-context.ts:12-18`）；`can` 的簽章在 `:49` |
| 既有消費者 | `CapabilityRoute`（`RouteGuard.tsx:35`，其 `:39` destructure `can`）——**初版表格的上一列自己就引用了它** |

所以 `K-16` 的 `residual_gap`（「沒有機制擋住前端自己猜」）之所以無法關閉，
**不是**因為沒有來源可猜，而正是因為**有一個全域來源，且它不得被用來推導
per-project 結論**。禁令的正確措辭是：

> **可以**用 `can("K3", …)` 判定全域能力；**不得**用任何全域能力推導
> per-project 角色（`project_owner`／`project_admin`／一般成員）。
> per-project 結論的唯一來源是 `list_members` 回應中自己那一列的 `role`（`BR22.3`）。

守住它的是 `BR22.3` 的 observable 與 `SEC-U24-5`（四個控件在一般成員身分下
全部不存在）兩條 e2e——**是紀律，不是結構**。本檔不再宣稱後者。

### 一之二、橫幅查詢的發出前置條件（審查 `R-03`）

`frontend-components.md:157` 逐字：「`ReselectionBannerHost` 以 `can('K3','view')`
作為發出請求的前置條件」。本站初版把 `UIP-2` 的「缺 `K3 view` 者 **0** 次」歸因於
`BR21.3`，**那是錯的**——`BR21.3` 是**重試**規則（`logical-components.md` §二 自己
寫出它的語意是「403 永久失敗本工作階段**不再**發請求」），要先發一次請求並收到
403 才知道，實際計數是 **1**，`UIP-2` 的 e2e 會紅。正確設計是沿用上游已定的前置判定：
掛載時先 `can("K3","view")`，為 false 則**不發請求**（計數 0）。`BR21.3` 處理的是
「有權限但失敗」與「發出後才發現 403」兩種殘餘情形，兩條規則並存不衝突。

### 一之三、`canManage` 的兩段式前置（審查 `R-01`）

**已證實可達的壞狀態**：「per-project 為 `project_admin`，但缺全域 `K3.edit`」。
兩條獨立路徑都到得了：

| 路徑 | 證據 |
|---|---|
| 被直接邀為 `project_admin` | 受邀者把關只要求 view——`membership_service.py:72` 逐字 `REQUIRED_INVITEE_ACTION = "view"`。而 `rbac_seed_data.py:342`／`:346`／`:348` 逐字給 `FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner` 的 `K3` 為 `True, False, False`（view 有、edit 無） |
| 被自動改選升為 `project_admin` | `reselect_for_project` → `select_successor(candidates)`（`membership_service.py:722`）後直接 `set_member_role(..., role=ROLE_PROJECT_ADMIN)`，**無任何 `K3.edit` 過濾** |

初版的後果可構造：`canManage` 僅由 per-project `role` 推得 → 四個控件全部渲染 →
每次寫入永久 403 → 而初版對 403 的處方逐字是「關閉進行中的 modal 並重抓一次清單
（**權限可能剛被改**）」→ 重抓回來的 `role` 不變、`canManage` 仍為 true →
**無上界的死循環，且對使用者沒有任何說明**。

**本站的設計決定**：

> `canManage` ＝（自己那一列的 `role` ∈ {`project_owner`, `project_admin`}）
> **AND** `can("K3","edit")`

- 這**不違反** `BR22.3`：`BR22.3` 規定 per-project 結論的**取得方式**，本條是在它
  之外再 AND 一個**獨立的全域閘**——與伺服器實際的兩段式檢查
  （`require_story_action("K3","edit")` ＋ per-project 角色）同形，不是用全域能力
  推導 per-project 結論（§一之一 的禁令）。
- **不增加請求數**：`can()` 讀的是已載入的 `user.permissions`，故 `UIP-4`
  （首次可互動前恰 1 次請求）不變。
- `SEC-U24-5`（四個控件在一般成員身分下全部不存在）仍成立且更強。
- **403 的處方同步改為終態**：不再重抓清單。收到 403 時關閉 modal、以 live region
  播報一段可理解的文字、**並停止該操作的重試**——重抓無法改變 `role`，重抓就是死循環。

**本決定擴充了一條已核可規則的效果**（`BR22.3` 的渲染條件多一個 AND），
故於核可關卡明白揭露，而非當成細化吸收。被排除的替代方案是「渲染控件但以 403
為終態」——它讓使用者看得到四個永遠失敗的控件，而本單元是管理成員的唯一入口。

### 一之四、殘留缺口（如實記載，不美化）

`K-16` 的 `residual_gap` 逐字「沒有機制擋住前端自己猜」。本站**無法**關閉它——
`useAuth().can` 是既有且可取用的全域來源，而「不得用它推導 per-project 角色」
只能靠 e2e 守住。本單元能做到的是 §一之三 的兩段式前置（讓壞狀態下控件不渲染）
＋ `BR22.3` 與 `SEC-U24-5` 兩條會紅的 e2e。**這是防護而非強制。**

## 二、輸入驗證設計

| 輸入面 | 設計 | 依據 |
|---|---|---|
| 邀請對話框的角色值 | 前端只提供列舉內的選項；不接受自由輸入 | 列舉外值會由 Pydantic 回 422（物件陣列型 `detail`），該路徑仍須可處理 |
| 422 的**兩種**語意 | 以 `detail` 的**型別**分流：字串＝缺全域權限（`AC12.5.1`）、物件陣列＝驗證錯誤（`BR23.1`） | `functional-spec.md` §四 第 2 列；`SEC-U24-4` 禁止把非字串 `detail` 當文案渲染 |
| 使用者顯示名稱等伺服器文字 | 以 React 的預設轉義渲染，**不使用** `dangerouslySetInnerHTML` | 本單元無富文字需求；此為 XSS 面的結構性關閉 |
| URL 參數 `project_id`／`user_id` | 僅轉送，不做本地權限推論 | 伺服器對每個端點各自把關 |

## 三、加密與機密

| 面向 | 設計 |
|---|---|
| 傳輸 | 沿用既有同源 `fetch` ＋ 既有 TLS 終結（Cloudflare Tunnel → nginx），本單元不新增通道 |
| 靜態 | **零瀏覽器儲存**（`NFR4.80`）：橫幅已讀狀態必須在伺服器，否則 `AC12.4.4` 的跨裝置一致無法成立 |
| 機密 | 本單元**零新環境變數**（`NFR8.80`／`TS-U24-7`），故 `render-env.sh` 與 `deploy/.env.example` 的同步義務為**空集合** |
| token | 沿用既有 `Authorization: Bearer` 手寫標頭形狀（`team.md` 記載的既成慣例，40 處）；**不**把 token 放進 query string 或任何可被 log 的位置 |

## 四、稽核與記錄設計

| 面 | 設計 |
|---|---|
| 使用者可見稽核 | 變更紀錄（`AC12.2.2`）由本單元**渲染**、不記錄；資料存在於 `reselection_events`，但**無任何端點可取**（`OPEN-MP24-7`），故此面目前在前端不可達 |
| 前端訊號 | `SEC-U24-6` 的兜底規則：**每一條對使用者無聲的失敗路徑**都須輸出一筆 console 訊號，內容限於型別名稱與端點標識 |
| 禁止內容 | `SEC-U24-1`：console **不得**含使用者文字或識別字。本 repo 為 public、Actions log 公開可讀 |
| 不做的 | 不送任何記錄到後端（會新增端點依賴，推翻「零新端點」的結構宣稱——`[N3]`=C 被排除的理由） |

**設計上的張力與處置**：`SEC-U24-6`（要記）與 `SEC-U24-1`（不得記什麼）同時成立，
故訊號的**形狀**必須先被設計，而不是留給實作各自發明：

```ts
// 介面層形狀（≤15 行）：兩個欄位都是**字面值聯集**，不是開放的 string
type SignalKind = 'members-fetch-failed' | 'banner-fetch-failed'
  | 'banner-forbidden' | 'invite-validation-failed' | 'write-forbidden';
type SignalEndpoint =                                  // 六個端點，method ＋ 路徑樣板
  | 'GET /projects/:id/members'   | 'POST /projects/:id/members'
  | 'DELETE /projects/:id/members/:uid' | 'PATCH /projects/:id/members/:uid'
  | 'GET /reselections/pending'   | 'POST /reselections/:eid/acknowledge';
type FailureSignal = { kind: SignalKind; endpoint: SignalEndpoint };
```

**審查 `R-04`（Major）更正**：初版把兩欄寫成開放的 `string`，並宣稱「讓
`SEC-U24-1` 成為型別層的結構保證，而非撰寫時的紀律」——**那是高估**。
`kind: \`invite-failed:${displayName}\`` 與
`endpoint: '/api/membership/projects/7/members/42'` 都會通過型別檢查，
移除 `message`／`detail`／`displayName` 三個欄位只是關掉了最方便的那條通道。
改為**字面值聯集**之後它才真的是型別層保證：任何非列舉值無法編譯。
封閉列舉可構造這件事也已查證——六個端點全部可僅以 method ＋ 路徑樣板區分
（`GET`／`POST` 共用 `/projects/{id}/members`、`DELETE`／`PATCH` 共用
`/projects/{id}/members/{user_id}`，另兩個路徑各自唯一）。

端點標識用**路徑樣板**而非實際值：實際 `project_id`／`user_id` 是識別字，
落在 `SEC-U24-1` 的禁止範圍內——而字面值聯集使「填入實際 id」同樣無法編譯。

## 五、ADR-0006 security baseline 四面向（逐項判定，**不留空白**）

**逐格比對上游**：本表與本單元 `nfr-requirements/security-requirements.md` §一
的判定**相同**；差異處為零。上游 `inception/requirements-analysis/requirements.md`
的同名表（`:598`／`:618` 兩列 Encryption 皆判「適用」）與本單元判定不同，
理由是**範圍**：那兩列的依據分別是 `NFR7`（episodic memory 的靜態與傳輸加密）與
`FR11.5` 的 `C-T11`（MCP 傳輸層承載使用者 token），兩者都落在伺服器側與 `U11`／
記憶層；本單元零新儲存、零新通道。

| 面向 | 判定 | 本站的設計 |
|---|---|---|
| **IAM** | **適用** | §一 的三層授權架構；`I-5` 的欄位集合是其結構前提；`K-16` 的 `residual_gap` 本站無法關閉，已如實記載 |
| **Encryption** | **不適用** | §三：零新通道、零新儲存、**零瀏覽器儲存** |
| **Network exposure** | **不適用** | 零新端點、零新進程邊界；六個消費點全屬 `U19` 既有端點 |
| **Audit logging** | **適用** | §四：使用者可見稽核面目前不可達（`OPEN-MP24-7`）；前端訊號以型別層關閉 `SEC-U24-1` 的禁止內容 |
| **PBT hard constraint** | **不適用** | ADR-0006 點名的三個落點（IaC generator／cost calculator／agent routing）皆非本單元；前端無 PBT 框架（`team.md` 既成事實），唯一自動化層是 Playwright e2e |

## 六、STRIDE（與 `nfr-requirements` 的差異處逐項說明）

| 威脅 | 判定 | 本站的設計層補充 |
|---|---|---|
| Spoofing | 否 | 身分由既有 JWT 決定，本單元不新增身分來源 |
| Tampering | **是（唯一新面）** | 瀏覽器端可改 DOM 使隱藏控件出現——但**不構成權限提升**：伺服器對每個寫入端點各自把關（403／409）。本單元的設計是「不渲染」而非「不可呼叫」，兩者的差別已寫明 |
| Repudiation | 否 | 本單元不產生稽核事件；寫入端的稽核由 `U19` 承載 |
| Information disclosure | 否 | 回應欄位集合由 `MemberView` 決定（四欄）；`SEC-U24-1` 另關閉 console 洩漏面 |
| Denial of service | **否（但有一項已揭露、未設界的負載）** | `UIP-2` 每次掛載一次、刻意不快取；上界由人的換頁速度決定（`performance-design.md` §三）。本站**不新增節流**：節流與 `[N2]`=B 的快取在本單元後果同形（跨分頁不一致） |
| Elevation of privilege | 否 | 見 Tampering 列——前端無授權決策權 |

## 七、送審前自檢（七項，**逐項報告結果**）

| # | 自檢項 | 本站結果 |
|---|---|---|
| 1 | **可達性** | 本站新增一項設計約束（`FailureSignal` 的兩欄形狀），其違反面可達且可驗：多寫一個欄位即可構造違反，而 `SEC-U24-6` 的 e2e 斷言「訊號不含受測帳號的 `display_name` 與 email」會紅。**另如實記載一項不可達**：`UIP-5` 的渲染閘設計目前不可量測（取得變更紀錄的端點不存在，`OPEN-MP24-7`），已在 `performance-design.md` §一 標為「待命設計」而非已可驗 |
| 2 | **契約端點三問**（整站全部產出） | 本站新增的狀態只有一處：`<LiveRegion />` 的 `message`。**誰寫**＝兩個頁面各自的播報呼叫點；**誰讀**＝元件自身渲染；**誰清**＝呼叫端在下一次播報或操作完成時覆寫為空字串（`[ND1]`=A 的無狀態 props 形狀使「清」只能由呼叫端做，不會有元件內殘留）。✅ 三腿俱全。`FailureSignal` 無持久狀態，無三問標的 |
| 3 | **引用逐字核對**（事實與定位分開驗） | **查出一處跨站殘留並單獨記節**：`unit-of-work.md:426` 是**空行**，`U24` 的依賴在 `:427`、被依賴在 `:428`；該誤引存在於本單元 `nfr-requirements` 的三份檔與**兩輪審查記錄**（兩輪都「複驗」過它並判 accurate——驗了事實沒驗定位）。詳見 `logical-components.md` §五。本站其餘引用逐一開檔驗過：`membership_router.py:311` = `Depends(require_story_action("K3", "view"))` ✅、`RouteGuard.tsx:35` ✅、`rbac_seed_data.py:343-345` ✅、`functional-spec.md:202` = 「（`role="status"`，**此時為空**，見 §二之一）」✅、`unit-of-work.md:53` = `U17` 的 `packaging`／`standalone` 登記 ✅、`EstimateAdvicePanel.tsx:278`／`:291` ✅、`Layout.tsx:16`／`:17` ✅ |
| 4 | **檔案集合一致性** | 本站四份（performance／security／logical-components／traceability）是 `produces_kinds` 對 `ui` 的字面結果；同 intent 的 `service` 類單元各七份。**附帶一項與上一站相反的觀察**：引擎自己的 `consumes` 解析**只**交付五份輸入、未要求那三份 `[service]` 專屬需求檔（儘管 stage 檔標 `required: true`），與 `produces_kinds` 一致——這與 `OPEN-MP24-4` 記載的 `functional-design` 矛盾方向相反，本站無矛盾 |
| 5 | **跨檔傳播**（掃查範圍須含 `consumes`，不只本站 `produces`） | **本項初版報得不實，由審查 `R-06` 抓到**：我把「live region 的建造者」這個事實的落點只掃到本站三份產出並判「與上一站一致（不矛盾）」，**漏了同時被消費的 functional-design**——`rules.md:303-304` 的 `BR27.1` `logic` 與 `frontend-components.md:41`／`:46`／`:53` 共四處字面仍寫「由 `U23` 提供」。已補對齊註記於 `logical-components.md` §一之一（依 `refined-mockups:c3` 不回改上游）。本輪的三個事實：① live region 的建造者與形狀（落點：本檔 §一、`logical-components.md` §一／§一之一／§三／§四）；② `unit-of-work.md` 行號更正（落點：`logical-components.md` §四／§五）；③ `canManage` 的兩段式前置（落點：本檔 §一／§一之三、`traceability.json` 的 `SEC-U24-5` 與 `canManage-two-stage`、`logical-components.md` §二 的 403 列） |
| 6 | **可算的數字先算再寫** | 全部由指令輸出且在最後一次內容改動之後重跑，見 §八 |
| 7 | **逐一對照 hard constraint** | §五 的五列表格即為此項，四面向無空白、PBT 另列；與上一站**逐格相同**，與 inception 上游的差異已寫出範圍理由。**審查判為 PARTIAL 且判得對**：表格存在、判定正確，但 **IAM 列的內容不完整**——它指向 §一 的三層架構與 `I-5`，而初版的 §一 缺 `K3.edit` 這一層（`R-01`）且其結構前提為假（`R-02`）。**表格存在不等於內容涵蓋了實際的 IAM 面**，這是本項第二次教我同一件事（上一站是「判定與上游相反卻沒寫理由」）。修訂後 §一 有四個子節，IAM 列現已涵蓋兩個能力層 ＋ 專案層 ＋ 寫入把關 |

## 八、本檔引用的可算數字（由指令輸出）

| 數字 | 指令 | 值 |
|---|---|---|
| `/api/membership` 端點數 | `grep -cE '^@router\.(get\|post\|patch\|delete\|put)' backend/services/membership_router.py` | **6**（`K3 view` 三個：`:171`／`:311`／`:335`；**`K3 edit` 三個**：`:210`／`:246`／`:283`） |
| 前端 `aria-live` 命中 | `grep -rc 'aria-live' frontend/src/` 非零檔 | **1 檔 2 處**（`EstimateAdvicePanel.tsx`） |
| 前端 `role="status"`／`role="alert"` 命中 | 同上 pattern | **0**／**0** |
| `Layout.tsx` 行數 | `wc -l` | **22**（唯一 `data-slot` 在 `:16`、`{children}` 在 `:17`） |
| `K3.edit` 在本單元產出的命中 | `grep -rc` 於三站 16 檔 | 修訂前 **0**（`R-01` 的實質內容）；修訂後見本檔 §一 |
| 本站 h2 數 | `grep -c '^## '` | performance **4**、security **9**、logical-components **6** |
| `traceability.json` | `upstream_ids` ／ `coverage` ／ `reverse` | **23** ／ **23**（OK **20**、Deferred **1**、N/A **2**）／ **3** |
