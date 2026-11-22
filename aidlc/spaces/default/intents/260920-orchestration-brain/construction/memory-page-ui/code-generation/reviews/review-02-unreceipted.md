# Review 02（審查有效、收據缺失）— `code-generation` / `memory-page-ui`

> **本檔不是引擎寫的審查紀錄，而是如實保存一份記不進 audit 的審查。**
>
> | 項目 | 狀態 |
> |---|---|
> | `REVIEW_REQUESTED` iteration 2（`Recovery: stale-receipt`） | 已記錄，requestId `review:d0b2e7d7dae8e7fb90c82592c3bc1892` |
> | 審查員執行 | 已完成，判定 **READY**（R-01～R-04、R-06 Resolved；R-05 Unresolved；R-07 New Minor） |
> | `REVIEW_COMPLETED` | **被拒**：「workspace source changed after REVIEW_REQUESTED iteration 2」 |
>
> **根因**：與 `project.md ## Mandated` 的 `code-generation:source-fingerprint-includes-caches` 記載相同——引擎的 workspace 指紋不尊重 gitignore。審查員為獨立查證實跑了後端 `unittest` 與前端 `npm run build`，這兩個動作本身會更新 `backend/.hypothesis/`、各目錄的 `__pycache__/` 與建置產物；`git status --ignored` 顯示變動全落在被忽略的路徑，`git status` 的追蹤／未追蹤原始碼與請求當下一致（13 個 manifest 路徑）。
>
> **為什麼不重送審查**：這是本單元唯一一次 stale-receipt 復驗額度，已用掉；且重送會把「請求時間」記在審查實際執行之後，等於偽造順序。真正的修法在 upstream（指紋應尊重 gitignore），不得改 `.claude/` 下的框架檔。
>
> 以下為審查員寫入 `.aidlc-engine/reviews/code-generation/units/memory-page-ui/1c50192fc194e910/2.review.md` 的原文，未改一字。

---

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 2

本次為復驗輪（advisory），發現將原樣呈現給核可關卡的人。已實跑：後端 `python3 -m unittest tests.test_memory_pending_authz tests.test_memory_authz tests.test_memory_contract`（43 個，OK）、`npm run lint`（0 error、2 warning，皆在本單元未碰的檔案）、`npm run build`（通過）；另以 `vite preview` 服務建置產物，對 `tests/e2e/memory-page.spec.ts` 實跑 Playwright（15/15 通過，含新增的 E11–E15）。第 1 輪三項 Major 已修正並經驗證，無 Critical、無 Major，故為 READY；殘留一項已知交接事項（R-05）與一項新的 Minor（R-07）。

### Findings

| ID | Severity | Location | Finding | Status |
|---|---|---|---|---|
| R-01 | Major | frontend/src/components/memory/MemoryZone.tsx `handleRemoved`、`loadPage`、`resyncInBackground`、`applyLoaded`；frontend/tests/e2e/memory-page.spec.ts E11、E12 | 已修正並驗證。逐一代入 {刪除在途、翻頁在途、背景重抓在途、失敗} 的交錯：(1) 刪除完成時有翻頁／重試在途（`pendingLoadPageRef` 非 null）→ 以 `loadPage` 重送同一目標頁，`loadPage` 遞增序號使原在途回應失效，失敗落入 `error` 且有「重試」，不會停在 `loading`；(2) 翻頁已完成且穩定 → `resyncInBackground(shownPageRef.current)`，重抓的是使用者現在所在的頁，且只在 `rowPage === currentPage` 才搬焦點；(3) 該區停在 `error`（`settledRef` 為 false）→ 不重抓，使用者已有「重試」；(4) 背景重抓在途時翻頁 → `loadPage` 遞增序號丟棄重抓回應（E7）；(5) 重抓回應為空而退頁 → 經 `loadPage` 設定 `pendingLoadPageRef`，之後完成的刪除走 (1)。三個 ref 皆只在 `applyLoaded`、effect、事件處理器與 `.then/.catch` 內寫入，沒有在 render 期間寫入或讀取，`npm run lint` 的 `react-hooks/refs`、`set-state-in-effect` 無違規。E11 在舊程式（以按下確認時的頁次重抓）下必紅：第 2 頁已顯示後刪除完成，舊碼重抓 offset=0 把畫面拉回第 1–20 則，`item 41` 不會出現；E12 在舊程式下必紅：舊碼重抓第 1 頁、失敗分支只設 `syncFailed` 而不離開 `loading`，且第 2 頁回應已被序號丟棄，`-retry` 永不出現。兩案的斷言都綁在會因還原而改變的畫面與 GET 序列上。 | Resolved |
| R-02 | Major | backend/tests/test_memory_pending_authz.py `PendingSearchInProcessTest.test_B8_...`；backend/services/memory_facade.py `search` | 已修正並驗證。B8 注入的是 `resolve_embedding_port()` 解析出的真正 `StubAdapter`（並以 `assertIsInstance` 鎖住），以 `mock.patch.object(port, "embed", wraps=port.embed)` 觀察 `embed` 的呼叫次數；pending principal 的 `search` 斷言 `MemoryForbidden(reason=pending)`、`embed.call_count == 0` 且被替換的 SQL 步驟 `call_count == 0`；allow 側用同一個 spy 斷言 approved 帳號 `embed.call_count == 1`、SQL 步驟 `== 1`。allow 側這一半證明 spy 確實接在 facade 實際使用的 Port 上（`MemoryFacade(self.db, port=port)` 走 `self._port or resolve_embedding_port()`），故 deny 側的 `call_count == 0` 不是恆真。只替換「取向量之後」的 pgvector SQL，使「守衛被拿掉」的突變在 `assertRaises` 這一行變紅，而不是在 SQLite 語法錯誤上變紅。 | Resolved |
| R-03 | Major | R/construction/memory-page-ui/code-generation/traceability.json `UIP-1`～`UIP-6`；frontend/tests/e2e/memory-page.spec.ts E13、E14、E15 | 已修正並驗證。六列各自對應不同案例與斷言，不再共用 note：UIP-1→E13（三個 GET 在任何回應之前即送達，語意區在情節區未回應時已渲染）、UIP-2／UIP-5→E2、UIP-3→E6／E11／E12、UIP-6→E15（兩則刪除各自被閘門延遲，先放行第 1 則再放行第 2 則，以 `prev` 過濾才不會讓第 1 則回來）。UIP-4 改標 Deferred 並如實說明。「UIP-4 無法經由介面構造」這項主張成立：`EpisodicPager` 的「上一頁」「下一頁」在 `isBusy`（`status === 'loading'`）時皆停用，且 `onPageChange(page ± 1)` 取的是 `page` state，而 `page` 只在 `applyLoaded` 時前進；因此第二次點擊在載入期間要嘛被 `disabled` 擋下，要嘛（若在重新渲染之前發出）請求的仍是同一個 `page + 1`，不可能發出第 3 頁的請求。E14 驗證的正是這道保護（移除 `isBusy` 停用會讓 `toBeDisabled` 與 GET 數量斷言變紅）。 | Resolved |
| R-04 | Minor | backend/tests/test_memory_pending_authz.py `test_B9_missing_authorization_status_mints_approved`；backend/services/hierarchy_facade.py `Principal.is_approved` | 已依第 1 輪所列的第二條路處理：維持預設值，並以 B9 鎖住「`authorization_status` 為 None 或物件缺該欄位 → `is_approved=True`」是刻意行為（含 `SimpleNamespace` 輕量物件），B7 另鎖住 pending／rejected → False。授權欄位預設放行的 fail-open 形狀本身仍在，但已有測試使任何改動都必須先處理 `tests_pg` 的輕量物件，這符合第 1 輪建議的處置。 | Resolved |
| R-05 | Minor | backend/services/hierarchy_facade.py `HierarchyFacade._authorize`（`user_can(db, role, "K2", action)` 未傳帳號核准狀態）；R/construction/memory-page-ui/code-generation/code-summary.md §六 第一列 | 依人的裁決保留為交接事項，不重新論證：持有角色的 pending 帳號在 hierarchy 與 membership 兩條 facade 路徑上仍通過授權（ADR-0006 IAM 面向），承接者仍寫「於核可關卡提交使用者決定」，未指派單元，也未寫入對應的 allow/deny 測試義務。需由核可關卡的人指定承接單元（`U7`／`U19` 或獨立 intent）。 | Unresolved |
| R-06 | Minor | R/construction/memory-page-ui/code-generation/code-summary.md §三 偏離 #11、#12、§六 第二列 | 已修正並驗證。偏離表新增 #11（已核准檢查落點由 router dependency 改為 facade 六個方法第一行，連帶改動 `U8` 的 `memory_facade.py`、`memory_errors.py` 與 `memory_router.py` 的 OpenAPI 回應集合，並標明需與 `D8-1`／`D8-2` 一併追認），§六 交接表新增 `K-08` 契約追認一列；#12 如實說明新案例未寫入已核可的 `unit-test-instructions.md` 而記於 §七。 | Resolved |
| R-07 | Minor | frontend/tests/e2e/memory-page.spec.ts E12（`a failing refetch after a delete during paging ends in a retryable error`，約第 717–731 行） | 新發現，僅影響測試對「晚到回應被丟棄」的突變敏感度，不影響現況行為。`staleFinished` 以 `waitForEvent('requestfinished', 謂詞)` 在 `expect.poll(...).toBe(3)` 之後才註冊，謂詞只比對 `GET`、`kind=episodic`、`offset=20`，而那時還有第二個符合謂詞的請求（放行 DELETE 後重送、回 500 的 offset=20）。該請求的 `requestfinished` 若在註冊之後才觸發，`settleAfter` 會在「被延遲的舊回應」尚未處理前就返回；之後的 `toBeVisible`／`toHaveCount(0)` 是自動等待斷言，在「舊回應被錯誤地套用」的突變下，錯誤態可能已先被斷言通過而舊回應稍後才覆蓋它。現況程式下案例仍必綠（15/15），只是這一步對「序號防線被拿掉」的突變不一定紅。 | New |

### 核查摘要

- **R-01 修法的全交錯檢驗**：刪除在途 × {翻頁在途、翻頁已完成、重抓在途、區處於 `error`、退頁在途}，以及兩次刪除先後完成的組合，`handleRemoved` 都落在上述五條分支之一，沒有留下「區停在 `loading` 且無重試」的路徑。已知且為既有行為（非本輪引入）：翻頁失敗進入 `error` 後，「重試」載入的是最後一次成功顯示的頁（`page` state），不是使用者原本要去的頁；E12 的 note 已誠實記載。
- **E11／E12 對舊程式必紅**：以閱讀程式推演兩個案例的步驟序列對照舊 `handleRemoved`，皆在 code-summary §七 所稱的步驟變紅；未獨立還原舊程式重跑（為避免改動受審的原始碼）。
- **B8 的 embed spy**：已確認接線（allow 側 `embed.call_count == 1`），deny 側斷言不是恆真。
- **lint／hook 規則**：0 error；2 個 warning 在 `AssessmentPage.tsx`、`WorkspacePage.tsx`，非本單元檔案。新增程式沒有就地修改物件、沒有在 effect 內同步 setState、沒有在 render 期間存取 ref。
- **範圍**：本輪只讀本單元的原始碼、測試與紀錄，沒有開啟其他單元的 construction 目錄。
