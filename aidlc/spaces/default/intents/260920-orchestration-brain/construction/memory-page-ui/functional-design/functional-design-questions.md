# Functional Design 問題檔 — `U15 memory-page-ui`

> 單元類型 **`ui`**（`unit-of-work.md:51`），故 `produces_kinds` 只要求
> `functional-spec.md`、`frontend-components.md`、`traceability.json` 三份
> （`entities: [service, spec, library]`、`rules: [service, spec, library]` 皆不含
> `ui`）。依 stage 檔：UI-only 單元的 `functional-spec.md` 為**自足**。
>
> **但 `rules.md` 仍會產出，而且是機制要求、不是加碼**：`traceability` sensor 的
> `functional-design` 分支（`.claude/tools/aidlc-sensor-traceability.ts:493-502`）
> 逐字要求每個 `OK` 覆蓋項的 target「must name at least one BRx.y ID」且該 id
> 必須存在於 `rules.md`。先例 `U24 member-pages-ui` 同為 `ui` 且同樣產出 `rules.md`。
>
> Depth **Minimal**，故只問「預設錯了會造成真實重工」的題目。本站四題。

## 一、上游已定案、本站不重問

| 事項 | 定案 | 出處（逐字核對過） |
|---|---|---|
| 記憶的使用者可見面必須存在 | 獨立頁 `/memory`，三區 ＋ 逐則刪除 | `[F5]`=C、`[DM:D1]`=C；`wireframes.md` §9、`mockups.md` M6 |
| 路由守衛 | `ProtectedRoute`，**不包** `CapabilityRoute`；**不需新 story id** | `K-14` `provides.guard`、`mockups.md` M0 的查證 |
| 頁內授權由誰承擔 | `K-08` 的 `MemoryFacade` 以擁有者欄位承擔，**前端不自行過濾** | `K-14` `behaviour_semantics.authorization_responsibility` |
| 三區的條目形狀 | 語意／程序＝一句可判斷對錯的陳述；情節＝日期 ＋ 主題 | `interaction-spec.md:509-511`、`mockups.md` M6 的三區表 |
| 語意／程序**不分頁**、情節**分頁** | 已定案 | `interaction-spec.md:509-511` |
| 刪除用**確認**而非 undo | undo 會讓稽核出現兩筆需互相抵銷的紀錄 | `mockups.md` M6「刪除的確認」、`[RA:FR4.7]` |
| **不得用 `window.confirm`** | 用就地確認列（該則原地展開「確定刪除？」） | `interaction-spec.md`「刪除的確認」 |
| `empty` 與 `error` **必須可區分** | 共用畫面會讓讀取失敗被誤認為記憶被清空 | `interaction-spec.md:502-503`（本檔明文定案） |
| 每區 5 個狀態 | `default`／`empty`／`loading`／`error`／`deleting` | `interaction-spec.md` States 表 |
| 無障礙規格 | 每區 `region` ＋ `aria-labelledby`；`[刪除]` 的 `aria-label` 須含內容摘要；`h1` ＋ 三個 `h2` 不跳級；刪除完成以 live region 播報 | `interaction-spec.md` Accessibility 表 |
| `data-testid` 命名 | `memory-page`、`memory-zone-{semantic,procedural,episodic}`、`memory-item-{id}`、`memory-item-{id}-delete`、`memory-item-{id}-delete-confirm`、`memory-pagination` | `interaction-spec.md` Test ids |
| 兩個入口一個顯示條件 | **INV-3**：Sidebar 項與入口頁捷徑必須解析到同一個判定（目前為「已登入」） | `interaction-spec.md:33` |
| 驗證方式 | **Playwright e2e**（前端無 unit／component 測試框架） | `unit-of-work.md:191`、`team.md ## Testing Posture` |
| 前端資料抓取形狀 | 兩層抓取（純抓取函式／呼叫端 `.then.catch.finally` 更新 state／`useEffect` 內 `cancelled` flag）；`react-hooks/set-state-in-effect` 為 **error** 級 | `team.md ## Code Style`、`K-14` `data_fetch_shape` |
| URL 組裝 | 沿用 `apiUrl()`，不自造 | `K-14` `url_building` |
| 90 天只約束 `episodic` | `semantic`／`procedure` 的 `expires_at` 為 `None` | `FR4.5`；`memory_service.py:181-191` 實讀 |
| `OQ-N3`（記憶無寫入端）**已由上游解決、本站不重開** | `U8` 的 `[FD4]`=A 新增 `POST /api/memory/records`，為 `semantic` 的唯一來源 | `memory_router.py` 的 `create_memory` docstring；實讀磁碟 |

## 二、本單元承載的故事與其 AC

`unit-of-work-story-map.md:120` 指派 **`US4.2`、`US4.4`** 兩則給 `U15`。
逐條判定哪些 AC 真的落在本單元：

| AC | 落在 `U15`？ | 理由（逐字核對上游） |
|---|---|---|
| `AC4.2.1` | **是** | 「要求刪除」的使用者操作面在本頁；「不再出現在脈絡組裝中」那一半在 `U8`／`U11` |
| `AC4.2.2` | 否 | 稽核紀錄的**寫入**在 `U8` 的 `delete`，**查詢面**是回補項 `N-8`（不在任何已列單元） |
| `AC4.2.3` | 否 | 90 天清除是 `U9 memory-purge`（GitHub Actions workflow） |
| `AC4.4.1` | **是** | 「我**檢視**它的擁有者欄位」——檢視面在本頁；寫入端在 `U8` |
| `AC4.4.2` | 否 | 酬載自行指定擁有者會被忽略，純伺服器端行為，e2e 碰不到 |
| `AC4.4.3` | **是** | 「我**檢視**它的可見範圍」——同 `AC4.4.1` |

→ 本單元的 `upstream_ids` 為 **6 條**（兩則故事的全部 AC），其中 **3 條** `OK`、
**3 條** 由 `reverse`／`N/A` 說明落點。

## 三、本站查出的契約缺口（提問的前提，先寫在這裡）

**`GET /api/memory/records` 不回傳總筆數。** 實讀磁碟：
`memory_router.py` 的 `list_memories` 宣告 `response_model=List[MemoryView]`，
`memory_facade.py:299-318` 的 `list_records` 回 `List[MemoryView]`,
`memory_service.py` 的查詢是 `.offset(...).limit(size).all()` ——**整條路徑沒有
任何 `count()`**。

而已核可的 `mockups.md` M6 線框逐字畫了 `情節記憶 2 則 / 共 34 則`，並逐字寫
「沿用既有 `PaginationControl` 元件（`src/components/PaginationControl.tsx`）」；
該元件的 props 逐字要求 `total: number`（`PaginationControl.tsx:8-11`，註解寫
「總筆數，取自回應」）。

**兩者不能同時成立。** 這是下游查出的上游契約缺口，依
`project.md` 的 `units-generation:260822-ug-L2`：標出缺口、寫明它讓哪一條 AC
不可滿足、指派具體落點與修法，**不逕自修改已通過審查的上游產出**。
修法本身是本站 `M1` 要問的。

附帶的同型事實：`DEFAULT_LIST_PAGE_SIZE = 50`、`MAX_LIST_PAGE_SIZE = 200`
（`memory_service.py:72-73`）。所以**語意與程序記憶的「N 則」在超過上限時也
數不準**——這不另立一題，而是由 `M1` 的原則一致套用（見該題的後果段）。

## 四、問題

## M1. 情節記憶的分頁怎麼做？（總筆數不存在）

§三的缺口。四條路各自的代價都是真的：

- **A. 改用「上一頁／下一頁」兩鍵 ＋「顯示第 N–M 則」，不顯示總數**：以
  `limit = pageSize + 1` 探測是否還有下一頁（多拿一筆、不渲染它）。零後端改動、
  零假數字。代價是**偏離已核可線框兩處**——沒有「共 34 則」、沒有沿用
  `PaginationControl`（它的 `total` 無從餵）。偏離須在產出內明記為對齊修正。
- **B. 保留 `PaginationControl`，`total` 以「目前 offset ＋ 本頁筆數」近似**：
  畫面與線框一致。代價是**那個數字是錯的且會隨翻頁變大**——使用者第 1 頁看到
  「共 50 筆」、第 2 頁看到「共 100 筆」。顯示一個查不到來源的數字，正是
  `project.md` 一再記下的那類缺陷。
- **C. 擴充 `GET /api/memory/records` 回 `{items, total}`**：線框與元件都能照用，
  且是契約上「對」的修法。代價是它改的是 `U8` 的已核可契約，而 `U8` 已完成且
  在游標之前（與 `OPEN-MP24-6` 同形，本 intent 內**無自然承接站**）；同時動到
  `openapi.json` 與 `frontend/src/types/api.d.ts`，牽動 CI 的 OpenAPI drift 閘門。
- **D. 情節記憶改為不分頁，一次抓 `limit=200`，超過則顯示「僅顯示最近 200 則」**：
  最簡單。代價是與已核可的「情節記憶**分頁**」（`interaction-spec.md:511`）
  直接衝突，且 90 天內超過 200 則的使用者會有看不到的記憶卻無法翻頁取得。

**選 A 的後果會一致套用到另外兩區**：語意與程序記憶的區標題也不宣稱精確數，
而是在回傳筆數等於請求上限時顯示「N+ 則」。

`[Answer]`: A
<!-- 作答時間 2026-10-11T10:23:51Z（以 `date -u` 取值，非估計）。選項本文已於提問前
     逐字寫入本檔，選單內容與本檔一致；提問前已執行 `aidlc-log.ts decision`。
     選項順序未重排，故選單的 A 即本檔的 A。 -->

## M2. 三區的資料怎麼抓？

`GET /api/memory/records` 吃 `kind` 多值參數（`memory_router.py` 的
`kind: Optional[List[str]]`），所以「一個請求」與「三個請求」都做得到。
而 `interaction-spec.md` 的 States 表要求**每個 Zone 各有** `loading`／`error`／
`empty` 三態——這個要求會壓住答案。

- **A. 三個請求，每區一個（`?kind=semantic` 等），情節記憶那個帶 `offset`／`limit`**：
  三區各自有獨立的 loading／error／empty，直接滿足 States 表。情節記憶翻頁只重抓
  自己那一區。代價是首次載入 3 次請求。
- **B. 一個請求抓全部（不帶 `kind`），前端分組**：首次載入 1 次請求。代價有兩個且
  都是硬的——① 三區**不可能**有獨立的 `error` 態（一次失敗就是三區全失敗），直接
  違反 States 表；② 情節記憶的 `offset`／`limit` 會把另外兩區一起截斷，因為分頁是
  施加在**混合三種 kind 的單一結果集**上。
- **C. 兩個請求（語意＋程序合一個、情節一個）**：2 次請求，情節的分頁乾淨。代價是
  語意與程序共享 error 態，仍違反 States 表，只是程度較輕。

`[Answer]`: A
<!-- 作答時間 2026-10-11T10:23:51Z。順序未重排。 -->

## M3. 刪除成功後清單怎麼更新？

- **A. 就地移除該列，不重抓**：沿用 `U24` 已落地的形狀（`MembersListPage.tsx` 的
  `setMembers((prev) => [...prev, member])` 與 `AdminPage.tsx` 的就地更新先例）。
  零額外請求、無整頁閃動。情節記憶若刪到該頁變空且非第一頁，自動退回前一頁。
  代價是前端持有的集合與伺服器可能短暫不一致（例如 90 天清除剛好同時發生）。
- **B. 刪除成功後重抓該區**：資料一定與伺服器一致。代價是每刪一則多一次請求，
  且重抓期間該區進入 `loading`——`interaction-spec.md` 的 `deleting` 態逐字是
  「**該條目**淡化並停用，**其餘可用**」，整區 loading 與它衝突。
- **C. 刪除成功後重抓整頁三區**：最一致。代價同 B 且放大三倍，並且會讓另外兩區
  無故閃動。

`[Answer]`: A
<!-- 作答時間 2026-10-11T10:23:51Z。順序未重排。 -->

## M4. INV-3 的「入口頁捷徑」這一半怎麼處理？

`interaction-spec.md:33` 的 **INV-3** 要求 Sidebar 項與入口頁捷徑用**同一個**
顯示條件。但入口頁是 `U14 entry-page-ui`，**尚未施工**；目前 `/brain` 是
`Sidebar.tsx:209` 註解逐字標明的 `DEMO SCOPE`，而該註解同時寫「大腦入口的正式
落點是 `U14`（含權限掛載與分層），**屆時整段取代**」。

- **A. 本單元做 Sidebar 項 ＋ `/memory` 路由，並把顯示條件抽成一個共用判定
  （單一函式／常數），捷徑本身的渲染留給 `U14` 匯入**：INV-3 有了可被滿足的
  承載者（一個判定、兩個呼叫點），而本單元不去碰一段註解說會被整段取代的程式。
  代價是 INV-3 的第二個呼叫點在 `U14` 落地前不存在，故該不變量在本單元的 e2e
  只能驗到一半（Sidebar 那一半）。
- **B. 本單元直接在 `/brain` 的 demo 頁掛上捷徑**：INV-3 兩個呼叫點都在，e2e 驗得完整。
  代價是 `U14` 會「整段取代」那一段，捷徑會連帶被刪掉——而刪掉時沒有任何機制會
  提醒 INV-3 少了一半。
- **C. 本單元完全不處理第二個入口，整條 INV-3 留給 `U14`**：職責最乾淨。代價是
  INV-3 在本單元**沒有任何落點**，而 `U15` 是記憶頁的擁有者——把自己頁面的入口
  不變量整條推給別的單元，是 `project.md` 一再記下的那種死指派。

`[Answer]`: A
<!-- 作答時間 2026-10-11T10:23:51Z。順序未重排。 -->

## 五、歧義分析（Step 3 的 MANDATORY 檢查，逐項）

| 檢查 | 結果 |
|---|---|
| 含糊答案（「大概」「看情況」「混用」） | **無**。四題皆為單一字母且各自指向一個可實作的形狀 |
| 跨題矛盾 | **無**。M1=A 的「不要總數」與 M2=A 的「每區一個請求」互相增強（每區各自分頁即不需跨 kind 的總數）；M3=A 的「就地移除」與 M1=A 的「以 `limit+1` 探測」在刪除後需重算「是否還有下一頁」——此為**推論後果而非矛盾**，已寫進 `functional-spec.md` 的 `W4` 第 5 步 |
| 產出所缺的細節 | **一項**：M1=A 之下「每頁幾則」未由任何上游定案（線框畫 2 則、伺服器預設 50）。本站取 **20**，理由寫在 `functional-spec.md §四之一`，並列為 `OPEN-MP15-3` 交給 `nfr-requirements` 覆核，不假裝它有上游來源 |

**本節在 `M5` 加開之後的更正（如實記載順序）**：上表寫完時我的結論是「無需追問」。
隨後起草 `rules.md` 時實讀 `memory_service.py:270-283` 的 `_visible_to`，查出一個
**上表三項檢查都碰不到**的缺口——它不是答案含糊、不是跨題矛盾、也不是答案缺細節，
而是**四題的前提**（「這頁只有我的記憶」）本身不成立。故加開 `M5`。
不回頭把「無需追問」改寫成別的樣子：那句話在當時是我真實的判斷，而它錯了。

## 六、追問（起草產出時查出、`M1`–`M4` 已作答之後加開）

## M5. 清單裡會出現別人的記憶，而線框說「你可以刪掉任何一則」

**實讀磁碟的事實**（`backend/services/memory_service.py:270-283`）：

```
return query.filter(
    (MemoryRecord.owner_user_id == principal_user_id)
    | (MemoryRecord.visibility_scope == VISIBILITY_SCOPE_PLATFORM)
)
```

`GET /api/memory/records` 的可見範圍過濾是 **OR**：自己的列，**或**任何
`visibility_scope == 'platform'` 的列——**包含別人擁有的**。

**這個狀態今天就可達，不是理論風險**：`PUT /api/memory/records/{id}/scope`
已上線（`memory_router.py` 的 `widen_memory_scope`），`Platform_Admin` 與
`Platform_Owner` 得把任何一則放寬為 `platform`（`memory_types.py:100` 的
`SCOPE_WIDENING_ROLES`）。放寬後，**所有**已登入使用者的記憶頁都會看到那一則。

**它同時打到三處已核可的敘述**：

1. 線框 §9 與 `mockups.md` M6 的說明文字逐字：「這裡是大腦記住的**關於你**的事。
   **你可以刪掉任何一則**。」——第二句對非自己擁有的列為**假**。
2. `DELETE /api/memory/records/{id}` 對非擁有者回 **404**（`[D1]`=A 把「非擁有者」
   收斂進 404，`memory_facade.py:322-339`）。所以照線框渲染 `[刪除]` 會給出一個
   **永遠失敗**的按鈕，而它的 404 與「這則已被別人刪掉」**不可分辨**。
3. `AC4.4.1` 要求「我檢視它的**擁有者欄位**」——線框三區的條目形狀
   （`interaction-spec.md:509-511`）**沒有擁有者欄位**，只有內容與日期。

- **A. 非擁有者的列照顯示，但不渲染 `[刪除]`，改顯示「平台可見（他人的記憶）」**：
  `[刪除]` 的判定式為 `record.owner_user_id === user.id`。沿用 `U24` 兩段式
  `canManage` 的同一條理由——**永不渲染一個寫入必然被拒的控件**。同時為每一則補
  擁有者欄位（自己的列顯示「你」，他人的顯示「其他使用者」，並把數值 id 放進
  `data-owner-user-id` 供 e2e 精確斷言），`AC4.4.1` 因此有落點。代價：已核可線框的
  「你可以刪掉任何一則」為假，須在本站記為**對齊修正**（依 `refined-mockups:c3`
  不回改上游）。
- **B. 非擁有者的列前端過濾掉不顯示**：畫面與「我的記憶」這個標題一致。代價：
  直接違反 `K-14` 的 `authorization_responsibility` 逐字「**前端不自行過濾**」，
  且 `BR2.2` 的過濾刻意在 SQL 的 `WHERE` 內完成（`memory_service.py:271-274`
  逐字「不可見的列從未離開資料庫」），前端再濾一次就有**第二份可見範圍實作**。
- **C. 照線框渲染 `[刪除]`，404 視為終態並顯示錯誤**：畫面與線框完全一致。代價：
  使用者看到一個永遠失敗的按鈕，而 404 與「已被刪除」不可分辨——這正是
  `U24` 的兩段式 `canManage` 剛剛才消除掉的那個形狀。
- **D. 本輪只做「只有自己的記憶」的前提，平台可見列的呈現整條指派給下游**：
  本站最省。代價：平台可見是**今天就可達**的狀態，指派等於讓一個可達狀態沒有
  定義的畫面；而唯一的下游 ui 承接站是 `U17 a11y-gate`（只做 axe 掃描）。

`[Answer]`: A
<!-- 作答時間 2026-10-11T10:37:52Z（以 `date -u` 取值，非估計）。選項本文已於提問前
     逐字寫入本檔，選單內容與本檔一致；提問前已執行 `aidlc-log.ts decision`。
     選項順序未重排，故選單的 A 即本檔的 A。 -->
