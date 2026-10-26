## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/security-requirements.md > 三、STRIDE 的 I 列；四、ADR-0006 IAM 列；二、SEC-U15-1 | 「他人的 platform 列出現在我的頁面」被判為「設計上的可見、已核可行為」，並宣稱頁內授權全在 U8，但沒有處理「登入即可」包含哪些帳號。實查：自助註冊的帳號 `authorization_status="pending"` 仍會拿到 token（`backend/services/user_router.py:361`、`:392`）；`get_current_user` 只驗 token 與 `is_active`，沒有檢查 authorization_status（`backend/services/auth.py:87-91`）；`MemoryFacade.list_records` 的 docstring 逐字「不拋任何授權例外，只回較小的集合」（`backend/services/memory_facade.py:299-310`）。所以 pending 帳號直接 `GET /api/memory/records` 就能讀到所有被放寬為 platform 的記憶，唯一的攔阻是前端 `ProtectedRoute` 的 `isPending` 轉址（`frontend/src/components/RouteGuard.tsx`）。這正是本檔 §開頭與 SEC-U15-1 自己說「畫面不是存取控制」的那一類防線。此外放寬不限 kind（`memory_service.py:498-523` 的 `widen_scope_with_audit` 無 kind 檢查），episodic（NFR7 稱之為個人可識別的使用歷程）被放寬後也會顯示給所有帳號。「已核可」的出處只有 `functional-spec.md §四之三` 對該行為的描述，沒有任何一處核可「未核可帳號亦可讀」。這是 ADR-0006 IAM 面（hard constraint）的曝險面描述不足。 | New |
| R-02 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/nfr-requirements-questions.md > 三、`OPEN-MP15-3` 的覆核 | 「不出題、以證據收斂」本身可以接受（常數可逆、Minimal depth），但證據比文中宣稱的弱。①「取 20 使兩個前端分頁清單每頁筆數一致」不成立：`AdminPage.tsx:34`、`:83` 的 `pageSize` 取自後端回應，檔內註解逐字「不寫死前端常數（後端是真相來源）」，20 只是 `useState(20)` 的初始值；`user_router.py:146-147` 的 20 是伺服器預設，與記憶端點的伺服器預設 50（`memory_service.py:72`）是對稱的「某端點的預設」，故「選 50 沒有比 20 多出證據」的反向論述同樣適用於 20。②功能設計的第二個理由（三區並存時不推離首屏）是未量測的版面主張。真正站得住的只有 `limit+1=21 ≤ 200`（`memory_service.py:151-155`）。結論（20）無害，但「以證據收斂」的措辭過度。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/security-requirements.md > 一、`NFR4.90`、`NFR8.90`；traceability.json > coverage NFR4／NFR8 | 兩條標為「可繼承」並在 coverage 記為 `OK`，但本檔與 performance-requirements 的開頭規則是「無法誠實繼承者以 `SEC-U15-n` 宣告」。NFR4 的可測不變量是「重啟 backend 後既有對話脈絡仍可還原」（`requirements.md` NFR4 節），針對 Redis 內的大腦 session／工作狀態，本單元不持有；NFR8 的觸發是「新增元件引入新環境變數」，本單元零新增，是「前提不成立」而非「已滿足」。把「瀏覽器儲存零命中」掛在 NFR4 之下，會讓 NFR4 在追溯上看似被本單元覆蓋。另外 ADR-0006 表把 Encryption 判「不適用」，而 coverage 把加密要求的父條 NFR7 判 `OK`，兩處語意需一句話對齊（本單元的答案是「不產生用戶端靜態儲存」）。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/security-requirements.md > `NFR4.90`／`NFR7.90`／`SEC-U15-4`／`SEC-U15-5` 的可測不變量；performance-requirements.md > `UIP-1` | 數個不變量的可測性比宣稱弱。①儲存掃描只列 `localStorage`／`sessionStorage`／`IndexedDB`，漏掉 `document.cookie`、Cache API（`caches`）、路由 `state`／`history.state`（會跨重新整理保留）、service worker。②`NFR7.90` 的 e2e「回到該頁重新發出 3 個 GET」只能證明沒有跨頁 fetch 快取，無法證明內容被釋放（模組層快取＋重抓同樣會通過）。③`SEC-U15-5` 的前半「console.* 引數不含 content／record 變數（code review 可判）」不是機械檢查；後半的 `page.on('console')` 才是。④`UIP-1` 的「三者發出時間皆早於任一者回應完成」若不指定以延遲路由攔截拉長回應，在本機毫秒級回應下的時序斷言容易變成 flaky，而 e2e 設定是 `retries: 1` 且容忍 flaky，會被吞掉。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/security-requirements.md > 四之一 交接表第 4 列；二、`SEC-U15-2` | 「`SEC-U15-2` 的後端測試是否存在」被列為待確認的交接項，但現在就可查證：`backend/tests/test_memory_authz.py` 的 `test_A5_other_user_deletes_...`（`:249-280`）斷言非擁有者刪除回 404、記憶仍存在、無稽核列，`test_A7`（`:319`）斷言 `Platform_Admin` 刪他人記憶也是 404，與 `SEC-U15-2` 的不變量逐字相符。應改寫為「已存在，引用 A5／A7」，而不是留一個會被下游重複驗證的開放項。 | New |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/security-requirements.md > 四、ADR-0006 四面向表 | 表頭宣稱「沿用其判定」並逐列標「一致」，但與 `functional-spec.md §九之二`（`:341-348`）逐字比對有兩處遺漏：Network exposure 列的判定失效條件（「若 INV-3 的第二個入口日後需要跨來源請求，本列轉為適用」）未帶入，而 Encryption 列有帶；IAM 列的「不新增 story id」理由未帶入。落點欄 `NFR8.90`「零新設定即零新暴露面」也是不嚴謹的推論（沒有新設定不等於沒有新暴露面，真正的依據是沒有新進程、新埠、新路徑）。 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/security-requirements.md > 二、`SEC-U15-4` | 以「他人的 user id 屬內部識別字，可見文字不需要它」為安全要求，卻同時要求把同一個數值寫入 `data-owner-user-id`（`rules.md` `BR35.1`），且 `owner_user_id` 本來就在 API 回應與瀏覽器網路面板裡。可見文字不含數字沒有降低任何曝險，只是顯示文案選擇。建議改列為 UX 要求，或改寫為真正的安全論述；現狀會讓下游誤以為移除屬性是安全改進。 | New |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/memory-page-ui/nfr-requirements/performance-requirements.md > `UIP-3`／`UIP-5` | `UIP-5` 規定滿 200 筆時標題顯示「200+ 則」，但 `UIP-3` 與交接表只處理情節記憶的 offset 補償。語意／程序區以 `limit=200` 一次取得，使用者刪除其中一則後就地移除，剩 199 筆，標題依 `zoneCountLabel(n, limit)` 會變成「199 則」（不再帶 `+`），而伺服器端仍有未取得的列，這等於宣稱完整的計數（違反功能設計 §二之一的硬約束）。兩條都只在初始載入驗證。需補一個二元可判的要求：刪除後若該區原本是「N+」，標題維持「+」或觸發該 kind 的補抓（`UIP-3` 的「至多 1 次 GET」預算已容許）。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 引用逐項核對（`memory_service.py:72-73`、`:151-155`；`memory_types.py:41`、`:100`；`user_router.py:146-147`；`AdminPage.tsx:198-203`；`api.ts:25`；`api.d.ts` 的 `MemoryView`；`test_memory_authz.py` A5／A7） | 全部行號與內容相符 | 事實與定位皆正確；唯一的引用問題是 R-02 的推論，不是行號 |
| NFR1–NFR11 判定與 `requirements.md` 原文逐條比對 | N/A（NFR1、2、3、5、6、9、10、11）判定皆忠於原文；NFR2 的母體確實限定三處、NFR11 的母體確實是跨功能情境（`stories.md` `M-3` 存在）；NFR4／NFR7／NFR8 的「OK」見 R-03 | 無錯判；僅有繼承措辭過度（R-03） |
| `functional-spec.md §九之二` 與 ADR-0006 表比對 | 四面向判定一致，漏帶兩處附屬內容 | 見 R-06 |
| 上游 R-01／R-02／R-03 的處置 | 交接表如實列出且標明 R-03 非使用者裁決範圍 | 未誤處理，不重提 |

### Summary

零 Critical、一個 Major、其餘為 Minor，依判定規則為 READY。最需要在核可前權衡的是 R-01：本檔把「他人 platform 列可見」當成已核可的設計行為，卻沒有看見後端對 pending 帳號與 episodic 放寬沒有任何攔阻，而本單元的安全論述全部押在「U8 承擔授權」上。其餘發現多屬繼承措辭、可測性與一處標題計數缺口（R-08）。
