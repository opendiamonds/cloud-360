<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-09T06:00:00Z — 出題前先實測架構事實而非依賴 codekb 轉述：確認無背景 worker／無快取層／無排程（`BackgroundTasks`、`celery`、`apscheduler`、`redis` 於 backend 皆零實際依賴，僅 `wa_rule_engine` 的關鍵字清單命中）、deploy stack 僅單一 backend 服務、`uvicorn main:app` 未指定 `--workers`（單一 process）。這三項直接決定節流手段的可行集合。
- 2026-08-09T06:00:00Z — 關鍵設計事實：`get_current_user` 已對每個認證請求查出完整 User 物件，故「距上次寫入是否滿 5 分鐘」的判斷**資料已在手**，不需額外查詢。此事實使「條件式寫入」的成本降到只有真正需要寫入時的一次 UPDATE，改變了三個候選手段的成本排序。
- 2026-08-09T06:20:00Z — 「不新增服務／不引入新依賴」在本站被當成需要明確論證與替代方案的**設計決定**（AD-5），而非省略。後續 iteration 3 的 M1 證明這個立場有實際作用：它讓「新增一張標記表」的成本被看見，並促成改用既有欄位。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-09T08:30:00Z — 全站共跑 7 輪審查（iteration 1〜4 + Revision 1 三輪），遠超 `reviewer_max_iterations: 2`。輪數本身不是目標：**其中兩個 Critical 是修正前一輪時新引入的**（iteration 2 的 C-7 執行順序會清空 308 列權限矩陣；Revision 1 的型別產生放進 `npm run build` 會讓 docker-build 與 staging 部署同時失敗）。這個比率值得記下來：修正引入缺陷不是偶發，而審查是唯一抓到它們的機制。
- 2026-08-09T07:30:00Z — reviewer 跑了 4 輪，超過 stage 宣告的 `reviewer_max_iterations: 2`。理由：iteration 2 的 Critical（C-7 順序會清空權限矩陣）是**我在 iteration 1 修正時新引入的**，不是原始 findings 的殘留；若依「iterations 用罄即 proceed」放行，等於把一個自己製造的災難性缺陷交給下游。iteration 3、4 屬驗證輪（每輪都因修訂動了 `produces[]` 而使 review receipt 失效，需重新取得）。判斷依據是缺陷來源與嚴重度，不是輪次計數。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T06:10:00Z — 把節流判定（5 分鐘）與逾期判定（90 天）收斂為單一純函式元件（C-1），而非各自留在寫入路徑與序列化路徑。代價是兩個本無耦合的規則被放在一起；收益是兩個門檻數值有單一定義處、C-1 成為依賴圖的葉節點、當下時刻可參數化因而邊界條件可直接斷言。以本 intent 規模判斷收益大於代價，並在 AD-4 標明為本站推論、gate 上可挑戰。
- 2026-08-09T07:10:00Z — C-7 的套用標記由「新增一張標記表」改為使用既有的 `role_permissions.updated_by`（iteration 3 M1）。新表方案會觸發 requirements C-4 對「新增表」的 blocking 同步義務、需要另一個建表補丁、且無元件擁有它 —— 三項成本在初版都沒被承載。既有欄位的三條寫入路徑（種子固定字串／SQL 腳本留空／管理員帳號）互斥且已實測，零新 DDL。
- 2026-08-09T08:20:00Z — Q6=A（commit 產生的型別檔、型別產生不進 `npm run build`）同時解掉三件事：Critical 1 的 Docker build context 問題、Major 3 的公網暴露風險、以及讓首版寫錯的「docker-build：無」變成事實。選項的優劣不是靠比較條列出來的優缺點得出，而是靠**實測既有 CI 與 Dockerfile 的結構**才看得出來 —— 沒查 build context 的話 B 與 A 看起來差不多。
- 2026-08-09T08:25:00Z — 委派審查時明說自己的懷疑方向（「我懷疑漂移檢查會 flaky」），reviewer 實測後**推翻了懷疑的機制但確認了問題存在**：輸出對 hash 種子是位元決定性的，但跟著未釘住的依賴版本飄。明說懷疑讓它去實測，比不說更有價值 —— 但必須接受它可能證明我錯，且它的結論優先。
- 2026-08-09T07:40:00Z — M1-a 的修法選擇「拆日誌態並收緊契約句」而非「放寬謂詞去覆蓋管理員已異動的情況」。放寬謂詞會覆寫管理員的既有調整，那正是 AD-7 否決「重跑種子強制模式」的理由 —— 修一個缺陷不得以違反同一份文件已否決的原則為手段。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T08:35:00Z — Revision 1 帶入 Construction 的殘留（承 iteration 4 的六項）：⑦型別檔時效性的 gate 已定案為 frontend job 的漂移檢查，實作時須確認該 job 能經 `../` 讀到 repo 根的規格檔；⑧釘選須為精確等值形式，升版兩支依賴時須在同一 PR 內重新 dump 規格檔；⑨型別檔是否納入 `npm run lint` 作用域須於採用時定案；⑩規格檔的檔名與確切路徑本站未定，須不觸犯 repo contract 的禁止路徑規則且不落在 `frontend/public/`。
- 2026-08-09T07:45:00Z — M1-a（Major，READY 後殘留）：C-7 的更新謂詞「`updated_by` 為 NULL 或種子識別字」實際涵蓋「從未被人動過」，比契約句「尚未被本補丁套用過」窄一格。目標列若在部署前已被管理員動過（整列賦值，連調 `can_edit` 都算），C-7 永不套用且三態日誌會報「已跳過」—— 唯一的執行期訊號在這條失敗路徑上讀起來正常。修法：跳過態拆兩態，「未套用：該列已被管理員異動」與「未命中目標列」同級告警。
- 2026-08-09T07:45:00Z — m4（Minor）：M2 的涵蓋邊界註記與三態要求已進 `services.md` 與 `component-methods.md`，但未同步到 primary artifact `components.md` 的 C-7 組成段落。
- 2026-08-09T07:45:00Z — m5（Minor）：標記方案不可組合（第二支同形狀補丁會被 C-7 的標記擋住），且補丁識別字與使用者帳號共用同一欄位而 `username` 無格式約束，唯一性未被結構保證。
- 2026-08-09T07:45:00Z — m3（Minor，自 iteration 2 起未處置）：時區正規化吸收不帶時區的值時無 warning，與本站對 C-2 反覆援引的「silent failures are not acceptable」立場不一致。
- 2026-08-09T07:45:00Z — C-7 的交易語意未寫進契約（reviewer 列為實作提醒，不計 finding）：既有 `_ensure_*` 先例走 `with engine.begin()` 自動提交，沿用即正確；但若 Construction 改用 `init_db()` 的既有 session 而未自行提交，寫入會被丟棄 —— 與 C-2 同型的風險，C-2 已明訂而 C-7 未訂。
- 2026-08-09T07:45:00Z — FR-4.3 一致性檢查測試（比對兩處預設值來源）若判定超出本 intent 範圍，須明寫以人工核對承接，不得留白。
- 2026-08-09T07:45:00Z — NFR-7 既有功能回歸的驗證設計仍無落點，自 refined-mockups 起持續追蹤。
- 2026-08-11T00:00:00Z — AD-12（跨頁一致性）**未出選擇題**：Q8〜Q10 定案後只剩一個不違反任何已核可 AC 的解（就地移除＋當前頁重抓），其餘候選各自與某條已核可決定牴觸。對只有一個可行解的事出選擇題是假的選擇，理由直接記入 AD-12。
- 2026-08-11T00:00:00Z — envelope 的四個欄位定為「皆必填、皆無預設值」，與 C-4 對兩個新欄位的既有約束同一個理由：`UserListPage` 是本 intent 的**第四個**回應構造點，帶預設值會讓「完全沒讀查詢參數的實作」也輸出正確形狀的 key，而 AC-5.2 被改寫為值斷言正是為了分辨這種自我回報式實作。
- 2026-08-11T00:00:00Z — `total` 明訂為獨立計數查詢、不得由 `len(items)` 導出。這條看似多餘，但它正是 AC-5.2 第一個 Then 要抓的東西 —— 由 `len(items)` 導出的實作在「總數少於一頁」時完全正確，只在多頁時錯，而多頁情境在目前的 12 個帳號下不會自然出現。
- 2026-08-11T00:00:00Z — C-9 橫跨前後端，與 C-8 同為跨層元件。已在 `component-dependency.md` 明記 units-generation 須依「驗證方式與失敗模式是否同類」判斷要不要拆（端點測試 vs e2e 是兩種判準），不由本站代決。
- 2026-08-11T00:10:00Z — reviewer 以 repo **自身已編譯的 `dist/assets/index-*.css`** 反推列高，推翻本站「57px／12 列」的估算（實為 66〜81px／8〜10 列，且兩個 actor 的列高不同）。教訓不是「估錯了」，是**估算方式錯**：我從 className 心算，而編譯產物就在 repo 裡、可以直接讀。決定（每頁 20）不變，理由整段換掉。
- 2026-08-11T00:10:00Z — 本站原本把「刪除後重抓」寫成一句話就過了，reviewer 指出它與 `isLoading`／`isBusy` 的互動完全未定義，而 Construction 手上最順手的既有工具（`fetchUsers()`）會讓每刪一列閃一次整頁載入 —— 字面通過 AC-5.6、實質打斷工作流。補定「三種抓取路徑對應三種畫面行為、互不共用旗標」。這類缺口的共同形狀是：**新行為與既有機制的交界沒被寫下來，於是預設會沿用既有機制，而既有機制的副作用正好破壞新需求的意圖。**
