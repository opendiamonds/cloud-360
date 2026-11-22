# ADR 0022：`work_target` 帶三層名稱（C-8），與大腦讀取路徑的專案可見性守門

- Status: Accepted（2026-10-17 隨 `U14` Plan Approval 核可）
- Date: 2026-10-17
- 編號依據：`inception/decisions/` 現有 `0019`–`0021`；全 repo 各 intent 的 `decisions/` 最大號為 `0021`（`261001-a2-langgraph` 另有一份 `0019`，為既存撞號，與本 ADR 無關）。
- Amends:
  - `U2` 的契約模組 `brain_ws_contract.py` 的 `WorkTargetPayload`（現行 `:282-302`），連同 `ws-contract.json`／`frontend/src/types/ws-contract.d.ts`。
  - `U7` 的 `HierarchyFacade`：新增 `describe_work_target`；`list_projects`／`list_systems`／`resolve_work_target` 加必填參數 `project_visible`。
  - `U13` 的 `brain_gateway.py`：`BrainGateway`／`build_brain_gateway`／`_HierarchyResolver` 加必填 `membership_facade_factory`；新增 `_names_for`；四個 `work_target` 推送點帶名稱。
  - `U19`／`U23` 的 `MembershipFacade.project_visibility`：回傳的閉包改為「每個 facade 實例、每位使用者只查一次可見集合」的批次形狀（判定定義不變）。
  - `U23` 的靜態鎖 `tests/test_project_visibility_static.py`：`S2`／`S3` 的方法集合擴及四個讀取方法，`S3` 新增一筆精確例外。
  - `contract-summary.md` K-13 對 `work_target` 欄位的描述（以本 ADR 為準，已凍結的上游檔不回改）。
- 觸發來源：
  - `U14` functional-design 的 `[EP2]`=A 與其修訂 1（使用者 2026-10-17 裁決：孤兒圖名稱以 `U7` 新唯讀方法取得）。
  - functional-design 帶入項 `R-01`（使用者 2026-10-17T02:06:14Z 裁決：名稱查詢套用 `U23` 可見性）、`R-07`（同批論證）。
  - nfr-requirements 帶入項 `R-01`（2026-10-17T03:58:59Z 裁決：目錄、反問標籤、唯一命中同樣套可見性）、`R-02`（每組 ≤ 5、快照 ≤ 15 條 SQL）。
  - nfr-design `[EPD1]`=A（2026-10-17T04:22:24Z：直接設定作業對象的守門）；nfr-design 帶入項 `R-01`（2026-10-17T04:30:21Z：由圖推導出的專案不可見時保留圖名）、`R-02`（同時刻：可見性改為一次批次查詢）。
- 依據全文：`construction/entry-page-ui/functional-design/functional-spec.md` §二之一；`nfr-requirements/security-requirements.md` §二；`nfr-design/security-design.md` §一–§五；`nfr-design/performance-design.md` §三；`nfr-design/logical-components.md` §一、§五；`../carried-review-items.md`。

## Context

1. **畫面要顯示名稱，契約只有識別碼。** `U14` 的入口頁與兩個子頁面的脈絡列要顯示「專案 / 系統 / 圖」三層名稱（`AC1.1.5`、`AC2.1.1`、`AC9.1.1`），而 `WorkTargetPayload` 只有三個識別碼與 `segment`。`U14` 的唯一後端通道是大腦 WS（`contract-summary.md:916-917`），前端不得另走 HTTP 查名稱（`BR98.5`）。
2. **孤兒圖沒有既有讀法。** 系統歸屬為 null 的圖（`OPEN-H11`），用既有的 `list_projects`／`list_systems`／`list_diagrams_of_system` 組合查不到名稱；且 `U13` 既有測試以假 facade 斷言 `list_systems` 的呼叫次數（`tests/test_brain_gateway_turn.py:356`），走列舉會改變那些計數。
3. **擁有者範圍不等於可見範圍。** `U23` 已把專案可見性定為「成員 ∪（擁有者且零成員列）」（`membership_service.py:337-356`）。被移出的建立者（`owner_user_id` 仍是他、已不是成員）在 `U23` 的專案頁得到 404，但大腦有三條路仍以擁有者範圍讀到或設定他的前專案：名稱推送、對象目錄（`_build_catalog`，經反問標籤與唯一命中）、頁面直接送出的 `set_work_target`（經 `_HierarchyResolver` → `resolve_work_target`）。
4. **`U13` 不得 import 成員關係符號**（`tests/test_brain_gateway_limits.py:380-382`），`_HierarchyResolver` 與 `_build_catalog` 每次自開 DB session（`brain_gateway.py:564-577`、`:1226-1243`），可見性判定的閉包必須綁同一個 session。
5. **協定版本。** `U13`（`fa8ce42`）與 `U14` 同在本分支、皆未進 `origin/ut`；示範後端已移除（`backend/services/brain_router.py` 不存在）。在 `U14` 之前，前端沒有任何大腦 WS 消費者。

## Decision

| 代號 | 對象 | 決定 |
|---|---|---|
| D-1 | `U2` `WorkTargetPayload` | 新增 `projectName`、`systemName`、`diagramName`，型別 `Optional[str]`，**必存在、無預設**（給預設會使產生的 TS 欄位變為可選）。語意：對應識別碼為 null、查不到、不屬請求者、不可見或查詢失敗時為 null；名稱為空字串時原樣送出（前端顯示「（未命名）」）。重 dump `ws-contract.json`、重產 `ws-contract.d.ts`，三檔同一個 commit |
| D-2 | `U7` `HierarchyFacade.describe_work_target(principal, *, project_visible, project_id=None, system_id=None, diagram_id=None)` | 唯讀、冪等、不寫稽核、**不拋查不到**。順序：① `_authorize(principal, "view")`（`HierarchyForbidden` 不在本方法內捕捉）；② 服務層新純查詢 `hierarchy_service.describe_work_target` 以擁有者範圍逐層查（專案層主鍵＋擁有者；系統層 `systems` join `projects` 一條；圖層 `user_diagrams` left join `systems` 一條，同時取得圖所屬系統的 `project_id`）；③ **明確指定路徑**（`project_id` 或 `system_id` 非 null）：三元組中出現的每個相異專案 id（`project_id` 參數、系統所屬專案、圖所屬系統的專案）皆須 `project_visible(pid)` 為真，任一為假 → **三個名稱皆 null**（視同查不到，`[EPD1]`=A 的同義延伸）；**只有圖的路徑**（`project_id`、`system_id` 皆 null）：**不判可見性、不推導上層**，回 `{projectName: null, systemName: null, diagramName: <圖名或 null>}`——圖屬請求者本人（nfr-design `R-01` 使用者裁決）。語句數：每組 ≤ 5（授權 1 ＋ 三層各 ≤ 1 ＋ 可見性 ≤ 1），快照三組 ≤ 15 |
| D-3 | `U7` `list_projects(principal, *, project_visible)`、`list_systems(principal, *, project_id, project_visible)` | `project_visible` **必填、無預設、keyword-only**。`list_projects`：擁有者範圍列舉後只保留可見者；`list_systems`：擁有者檢查後 `project_visible(project_id)` 為假 → `HierarchyNotFound(PROJECT_NOT_FOUND_DETAIL)`（與不屬請求者同一句）。兩者唯一的應用程式呼叫端是 `_build_catalog` |
| D-4 | `U7` `resolve_work_target(principal, *, project_visible, project_id=None, system_id=None, diagram_id=None)`（`[EPD1]`=A） | 服務層解析不變；解析出的 `projectId` 非 null 且不可見時：明確指定了 `project_id` 或 `system_id` → `HierarchyNotFound`（專案句或系統句，與今天指定別人的專案逐字相同，經 `rules.error_for` 轉為固定句 `target_not_found`）；只由圖推導 → 回 `{projectId: null, systemId: null, diagramId: <圖>}`、無錯誤 |
| D-5 | `U19`／`U23` `MembershipFacade.project_visibility(principal)` | 判定定義不變（仍只由 `_visible_project_ids_select` 組出）。回傳的閉包改為：同一個 `MembershipFacade` 實例內、同一位使用者**第一次**被呼叫時以 `membership_service.visible_project_ids` 取得可見集合（**一條 SQL**），存在實例的私有欄位，之後的每一次判定（含同一實例再呼叫 `project_visibility(principal)` 產生的新閉包）都以集合成員判斷、**零 SQL**。實例的其他方法（`list_visible_*`、成員寫入）不讀這份暫存。這是 nfr-design `R-02` 裁決「一條 SQL 判定整批專案 id」的落點：`list_projects` 的語句數與擁有專案數無關（固定 3）、目錄的可見性成本為常數（＋1） |
| D-6 | `U13` 組裝 | `BrainGateway.__init__`、`build_brain_gateway(app, *, membership_facade_factory)`、`_HierarchyResolver.__init__` 新增**必填、無預設**的 `membership_facade_factory: Callable[[Any], Any]`；唯一組裝點 `main.py:84` 傳入 `membership_facade.MembershipFacade`（`main.py` 是唯一對 `services.membership_facade` 的靜態邊）。每個受守門的呼叫點寫成 `project_visible=vis.project_visibility(principal)`，`vis = self.membership_facade_factory(db)`、`db` 與 facade 同一個 session |
| D-7 | `U13` 名稱推送 | 新增 `async _names_for(conn, triples)`：去重、一次 `asyncio.to_thread`、一個 DB session、每組呼叫一次 `describe_work_target`。`HierarchyForbidden` → 該組三名稱 null、**不記 log**（被拒絕是正常結果，nfr-design `R-04`）；其他任何例外 → 該組三名稱 null、記一筆 WARNING `work_target_names_failed`（只帶 `connId`、`exc`＝例外類別名，皆在既有 `_ALLOWED` 內，白名單不新增欄位）、`rollback`（再失敗則吞下）、繼續下一組；thread 外層失敗 → 全部 null ＋ 一筆 log。**絕不往外拋**。四個推送點：握手（第一個 try 之後、送 `ready` 之前）、`_set_target_confirmed`、`_on_set_work_target`、`_on_set_sharing_mode`；`_work_target_envelope`／`_snapshot_envelopes` 仍為同步，改收 `names`／`names_by_segment` 參數。名稱不儲存、每次推送重查 |
| D-8 | `U23` 靜態鎖 | `S2`、`S3` 的方法集合由 `WRITE_METHODS` 擴為 `WRITE_METHODS ∪ GUARDED_READS`（`describe_work_target`、`list_projects`、`list_systems`、`resolve_work_target`），以 `ast.Attribute.attr` 判定（不以字串 grep，`intent_routing.py:155` 的 `_describe_work_target` 是 `ast.Name` 呼叫、名稱不同）。`S3` 對讀取方法的呼叫點下限 5（`_names_for` 1、`_build_catalog` 3、`_HierarchyResolver` 1）。`S3` 新增**唯一**例外 `("services/session_store.py", "resolve_work_target")`：接收者是建構時注入的轉接器（`_HierarchyResolver`），由轉接器注入判定；以 `(檔案, 方法名)` 精確比對。`S1`、`S4`、`S5` 與 `test_brain_gateway_limits.py` 的禁止清單一條都不放寬 |
| D-9 | 協定版本與同批 | 維持 `v: 1`。論證：`U14` 之前前端沒有任何大腦 WS 消費者，後端與前端在同一個映像建置與同一次 `up -d --build` 上線，三個「必存在、可為 null」的欄位增量對 `v: 1` 安全、不需升版（取代 functional-spec §二之一第 5 點不可滿足的「若 `U13` 先於 `U14` 進 `ut`」分支，帶入項 functional-design `R-07`）。**`U14` 上線之後**，任何不相容的增量都必須升版。合併前於分支（squash 之前）執行三項檢查：`git log --oneline origin/ut..HEAD` 同時含 `U13` 與 `U14` 的 commit；`grep -c projectName ws-contract.json` ≥ 1；`test -e backend/services/brain_router.py` 為假——任一不成立即停止合併 |

## Consequences

- **重開三個已交付單元**（`U2`、`U7`、`U13`）並改動 `U19`／`U23` 的一個方法與一支靜態鎖檔。既有斷言只因新增必填關鍵字而補參數，期望值一律不動；唯一的例外是 `tests/test_brain_gateway_startup.py:60` 的 `side_effect=lambda app: …` 必須改為 `lambda app, **kw: …`（否則新的必填關鍵字使它 `TypeError`），並加一條斷言 `kw["membership_facade_factory"] is MembershipFacade`。
- **fail-closed**：漏傳 `project_visible` 即呼叫當下 `TypeError`；漏傳 `membership_facade_factory` 即**啟動**失敗（組裝在 startup hook，CI 的 import smoke 抓不到；會發現的是 `test_brain_gateway_startup.py`、`ui-regression` 的 stack 起不來、部署資料面探測持續 502 而回滾）。
- **語句數**：每次推送多一組名稱查詢，每組 ≤ 5、快照 ≤ 15（以 SQLAlchemy `before_cursor_execute` 計數測試鎖住，1 個與 50 個專案語句數相同）。`list_projects` 固定 3 條。目錄：可見性成本為常數 ＋1，`_build_catalog` 的總數為 3 ＋ 3N（N ≤ 50，未截斷時逐專案 `list_systems` 的三條為**既有**成本，本 ADR 不改它的階；截斷時為 3 或 6）。
- **名稱陳舊**（`OPEN-EP14-16`）：改名或刪除不觸發推送，畫面顯示舊名直到下一次推送（換頁、重新整理、對象變更）。
- **工作項標籤不受影響**（`OPEN-EP14-10`）：仍為「架構設計：架構圖 #12」形狀。
- **殘留（如實記載）**：
  1. 移出**之前**已設好的作業對象不被追溯清除；交辦仍帶前專案，直到改選或 session 閒置 24 小時（每次互動續期，`redis_gateway.py:102-103`）。名稱已為 null。
  2. 「成員看得到專案、大腦目錄看不到」（擁有者範圍 ∩ 可見性，`OPEN-EP14-9` 與 `U23` 已知限制第 ③ 項的「成員」那一半）不在本次範圍。
  3. `U12` 的 `list_diagrams_of_system` 仍只做擁有者範圍（以已存的作業對象為輸入，與殘留 1 同源）。
  4. `MembershipFacade` 實例內的可見集合暫存在該實例存活期間不更新；實例的存活範圍為一次 HTTP 請求或一次 `to_thread` 呼叫，期間不會發生成員異動後再判定的流程（實例的成員寫入方法不讀暫存）。
- **回滾**：`git revert` 合併 commit 即可，無 DDL、無資料遷移、名稱不儲存；回滾使三處可見性守門一併消失，但 `/api/brain/ws` 本身也不存在，故不重開被移出者經大腦取得名稱的路徑。

## Security（ADR-0006 四面向）

| 面向 | 判定 | 內容 |
|---|---|---|
| IAM | **適用（擴充）** | 名稱、目錄（反問標籤與唯一命中）、直接設定三條讀取／設定路徑由「擁有者範圍」收緊為「擁有者範圍 ∩ `U23` 可見性」；判定只有一份（`_visible_project_ids_select`），非測試程式的唯一合法來源是 `MembershipFacade.project_visibility`；`HierarchyFacade` 與 `brain_gateway` 不 import 任何成員關係符號；靜態鎖 `S2`／`S3` 機械強制。「不存在」「不屬請求者」「不可見」「查詢失敗」對前端逐位元相同（名稱為 null、不另送 `error`），不新增探測面 |
| Encryption | **適用（相同）** | 零新傳輸、零新持久化（名稱不儲存） |
| Network exposure | **適用（相同）** | 零新端點、零新路由、零新埠；`describe_work_target` 只在進程內被 `U13` 呼叫 |
| Audit logging | **適用（相同）** | 不新增稽核事件；新增一筆白名單內的 WARNING `work_target_names_failed`（只帶 `connId`、例外類別名，不含名稱或識別碼）；被拒絕的查詢不記 |

**PBT**：不適用——`describe_work_target`、`list_*` 的守門與 `_names_for` 皆非 IaC generator、cost calculator、agent routing；以窮舉身分（被移出的建立者、零成員列建立者、非擁有者成員、另一專案的成員、孤兒圖、`K2 view` 撤銷）的 example-based 測試驗證。

## Alternatives Rejected

| 代號 | 未採方案 | 理由 |
|---|---|---|
| D-1 | 前端以 HTTP 查名稱 | 推翻 `contract-summary.md:916-917` 的唯一通道條款，並新增 `U14 → U7` 的 HTTP 邊 |
| D-1 | 脈絡列只顯示識別碼 | `AC1.1.5`／`AC9.1.1` 要求名稱 |
| D-1 | 只從前端已有的選單或清單取名 | 入口頁沒有清單；子頁面清單不含專案與系統名；孤兒圖之外的層取不到 |
| D-1 | 名稱欄位給 `None` 預設 | 產生的 TS 欄位變可選，前端多一個 `undefined` 分支，且漏送無法被契約測試抓到 |
| D-2 | 組合既有 `list_projects`／`list_systems`／`list_diagrams_of_system` | 全量列舉再過濾，語句數隨資料量成長；孤兒圖查不到；改變 `U13` 既有呼叫次數斷言 |
| D-2 | 由圖推導上層再判可見性、不可見時三名稱皆 null（nfr-design 初稿 ④'） | 被移出的建立者開**自己的**圖時脈絡列顯示「（無法顯示名稱）」，與 `[EPD1]` 選項 A 告訴使用者的「只顯示圖名」相反（nfr-design `R-01`，使用者裁決採此 ADR 的形狀） |
| D-2 | 系統層沿用 `assert_system_owned_by`（兩條 SQL） | 上界變 6，超過裁決的 5 |
| D-2／D-7 | 把授權 ① 提到 `_names_for` 只做一次 | 需要一個「已授權」的 facade 入口，等於開一條不授權的讀取路徑 |
| D-3 | 在 `U13` 內自行過濾目錄 | 任何新呼叫端都會靜默繞過；放在 facade 才能進 `S2`／`S3` 機械鎖並 fail-closed |
| D-4 | `[EPD1]` 選項 B：由圖推導也視同查不到 | 被移出者每開一次自己的圖就看到與畫面矛盾的「查不到」 |
| D-4 | `[EPD1]` 選項 C：本次不關 | 裁決逐字涵蓋「不能經大腦指定」 |
| D-5 | 另開一個批次判定方法（例如 `visible_project_ids` 注入） | 使 `U13` 需要第二個注入點，非測試程式的合法來源由一個變兩個，違反 `EPN-11a`「判定只有一份」 |
| D-5 | 維持逐專案一條 SQL（2 ＋ 5N） | nfr-design `R-02` 使用者裁決要求一次批次查詢 |
| D-6 | 注入現成閉包 | 閉包綁建立它的 session，而 `_HierarchyResolver`／`_build_catalog` 每次自開 session |
| D-6 | `membership_facade_factory` 給預設值 | 預設只能是恆可見（靜默繞過）或恆不可見（大腦對所有人失效） |
| D-9 | 升版為 `v: 2` | 沒有相容對象，只增加協商成本 |
