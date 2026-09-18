<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-08-09T08:00:00Z — 切分的天然接縫直接來自 application-design 的依賴矩陣，不需另行推導：C-1（政策）與 C-3（資料模型）是葉節點；C-2（寫入）與 C-4（讀取）互不依賴、只經 C-1／C-3 間接關聯；C-7（權限）與其他元件零程式碼耦合（不同資料表）。矩陣的「四列全空 + 單向 C-6→C-4」性質使 DAG 幾乎是照抄。
- 2026-08-09T08:00:00Z — 部署模型不出題：AD-5 已定案不新增服務、不新增執行單元，且部署是既有的單一 stack（deploy-on-merge 至自有 staging）。所有單元共用同一次部署，這是上游定案的結果而非本站的選項。

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-08-09T09:00:00Z — Q1〜Q3 作答後，因上游 application-design 的 Revision 1 新增元件 C-8，追加 Q1a 處理其歸屬。**原答案不動、以 Revision 段疊加**，與上游修訂採同一形狀（歸檔／不改寫既有答案／修訂來源記入問題檔）。
- 2026-08-09T09:05:00Z — stage 檔的覆蓋驗證要求「every unit has stories」，本站有一個單元（U5）不滿足。選擇如實記載並附完整追溯鏈，而非捏造故事以形式滿足該要求。
- 2026-08-09T08:00:00Z — stage 步驟 3 的範例題目清單中，「deployment model（monolithic / independent / hybrid）」與「unit granularity 的抽象偏好」兩題省略。前者已由 AD-5 與既有部署架構定案（見上）；後者以具體的切分方案並列取代抽象的粗細偏好 —— 對一個七元件的加欄 feature，「粗或細」的抽象問法無法讓使用者評估實際後果，直接給出候選切分的單元清單才是可判斷的。省略理由記於問題檔前言。

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-08-09T09:00:00Z — C-8 獨立為 U5 而非併入 U2（Q1a=A）。判準不是「元件數量該怎麼分配」，而是**驗證方式與失敗模式是否同類**：U2 是執行期契約（端點測試、回應欄位集合），C-8 是建置期資產（CI 漂移檢查、CI 紅燈）。併在一起會讓「U2 完成了嗎」同時指涉兩種不可互相替代的判準。
- 2026-08-09T09:05:00Z — U5 沒有對應的使用者故事，選擇**如實記載**而非為它捏造一則。stage 檔要求「every unit has stories」，但為一個開發期保護機制編造使用者價值主張會製造假故事；改以完整的追溯鏈（ug:Q2=B → AD-9 → C-8 → U5）交代其來源。

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-08-09T09:40:00Z — 三輪審查揭露的自身錯誤，兩類：**引用誤植**（把上游殘留項「C-7 交易語意」記成「C-2」，而 C-2 早已由 AD-8 明訂 —— 一字之差讓真正有風險的 U4 收不到警告）與**數字未隨修訂傳播**（AC 數表三列與 story map 不符，其中一列正是前一輪修訂加了 U3 進 AC-1.6 後未回頭更新的舊值）。兩者都不是判斷錯誤，是機械性同步失敗，而它們會流進 2.8 的 Bolt 分割。
- 2026-08-09T09:10:00Z — 本站承接自上游、尚未關閉的缺口共五類（NFR-7 桌面回歸無 AC 落點、AC-3.1a 無可執行驗收路徑、U4 既有環境套用無自動化驗證、AC-2.2 對比度須人工驗證、application-design 的 11 項殘留），已在 story map 明列並標出各自落在哪個單元，避免它們在切分後失蹤。
- 2026-08-11T00:00:00Z — C-9 橫跨前後端，依 `cid:units-generation:c6` 的既有判準（驗證方式與失敗模式是否同類）拆兩半併入 U2／U3，而非獨立成 U6。關鍵觀察：拆分後「C-9 前端依賴 C-9 後端」這條關係**變成 U3 → U2 的既有邊**，不需要新邊；獨立成 U6 反而會產生 U3→U6 與 U6→U2 兩條新邊，外加 U6 內部兩種不可互相替代的完成判準。拓樸上拆分嚴格較優。
- 2026-08-11T00:00:00Z — AC 數以腳本重算為 36（舊值 25 已作廢），US-5 的 11 條逐條指定落點，其中 AC-5.3／5.4／5.11 跨兩個單元、兩邊都算（與既有跨單元 AC 的處理一致）。跨單元 AC 由三條增為六條。
- 2026-08-11T00:00:00Z — U3 由 L 上修為 **XL**：它是本 intent 唯一需要新增**互動**元件（六個狀態）的單元，且 application-design 定死的「三種抓取路徑對應三種畫面行為、互不共用旗標」在既有程式碼中不存在（現行只有單一 `isLoading`）。這不是 AC 數多寡的問題，是結構上要引入既有程式碼沒有的東西。
- 2026-08-11T00:20:00Z — 又一次在「衍生數字」上失手：把跨單元 AC 的既有基準數寫成三條（實為四條，漏計 AC-2.1／AC-2.3）。`project.md` 的 `cid:units-generation:c6b` 就是上一輪為同型失誤學到的規則，而我這次仍是**憑既有敘述引用基準數、沒有逐格重數**。規則已經在那裡，缺的是執行 —— 引用任何「既有為 N 條」的基準時，那個 N 也要重數，不能只重數新增的部分。
- 2026-08-11T00:20:00Z — 2.7 的「不得建議實作順序」界線比想像中容易越過：我只是想說明合併約束的規模變大，卻順手寫成 `US-1 → US-2 → US-4 → US-5` 的箭頭鏈，而 `stories.md` 對 US-5 根本沒建立這個順序（它只有集合層級的「須序列合併」與方向相反的「須在 US-4 之前定案」）。箭頭是順序的語法，用它就等於在排序。
