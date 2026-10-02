## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| R-01 | Major | `accessibility-checklist.md` 修訂 1「`/admin/*` 為什麼重審後仍然不掃」，選項 D 之後的更正段落（約第 171 行） | 已逐字核對更正文字：「只掃該元件技術上做不到」已改寫為「可行，但 `include` 只縮小**報告範圍**，不代表該子樹內的既存違規會被排除……選 A 的理由不變，但支撐它的那句話本來是假的」。此表述與 `@axe-core/playwright` 的 `AxeBuilder.include(selector)` 的實際行為（只縮範圍、不排除子樹內既存違規）一致，且 D11＝A 的最終決定未被動搖。本輪未發現殘留的「技術上做不到」措辭。 | 無需再改。 | Resolved |
| R-02 | Major | `mockups.md` M0（Sidebar.tsx 行號引用，第 78–83 行）、`accessibility-checklist.md` 修訂 1 範圍表（第 156 行）、`refined-mockups-questions.md`（第 295 行） | 已實地讀 `frontend/src/components/Sidebar.tsx`：三個既有群組的 `<nav>` 確實在 144／200／242 行（不是 233），`mockups.md:81-83` 已加就地更正並保留原句（依 `refined-mockups:c3` 不回改已核可內容）。可見列數已重算為 **7**（3 群組標題 ＋ `大腦（示範）` ＋ 入口 ＋ 我的記憶 ＋ 專案），我獨立核對 `.claude/knowledge/aidlc-design-agent/ux-guide.md:61` 的「max 7 items」上限，7 恰好踩在上限上，與更正後的敘述（「已經踩在上限上」而非「再加一項就到」）一致。新增交接 **H-13**（`mockups.md:883`）指派給 `code-generation`（3.5，execution=`ALWAYS`，已以 `.claude/tools/data/stage-graph.json` 核對），且該站在目前游標（`Current Stage: refined-mockups`）之後，承接站有效。三份文件的更正已互相一致（`accessibility-checklist.md:156`、`refined-mockups-questions.md:295` 皆同步更正為 7 與交接 H-13）。 | 無需再改。另見 R-09（本輪新查出的次要殘留：行號範圍本身仍有一個小誤差）。 | Resolved |
| R-03 | Minor | `mockups.md` 修訂 1「七項自檢逐項結果」第 6 項（第 946 行） | review-02 指名的這一個落點已正確更正：「①axe 掃描點原寫『由 2 增為 9』——兩種計數方式都得不出 9：依表格列數是 2→7（新增 5），依實際掃描次數是 2→12」，與 `accessibility-checklist.md:183-186` 的計數基準說明逐字一致，我獨立依兩種基準重算（表格列數 7＝2 不變＋5 新增；實際掃描次數 1+1+1+3+2+2+2=12）皆相符。**但同一份 `accessibility-checklist.md` 檔案的另一處（第 222 行「修訂 1 擴大了 `[axe]` 的覆蓋面（掃描點由 2 個增為 9 個）」）仍是原始的錯誤數字，未被本輪修正動作觸及** — 見新發現 R-08。 | R-03 指名的落點本身已修正，判 Resolved；R-08 另記同檔案內的殘留傳播。 | Resolved |
| R-04 | Minor | `mockups.md` 修訂 1「七項自檢逐項結果」第 6 項 | 已獨立以腳本重新解析 `mockups.md` 的 M10／M11／M13／M14／M15／M16 六節，逐一數出 code fence 數：M10=3、M11=1、M13=2、M14=2、M15=3、M16=1，合計 **12**，與更正後文字「實為 12 個（M10×3＋M11×1＋M13×2＋M14×2＋M15×3＋M16×1）」完全一致。並對這 12 個框內的每一行以 `len()`（非顯示寬度，符合本專案 CJK 計數慣例）重新量測，**0 行偏離 72 字元**。 | 無需再改。 | Resolved |
| R-05 | Minor | `design-system-mapping.md` §1（第 28–31 行）、`mockups.md` M8（第 442 行） | review-02 的這一項**明確點名兩個落點**（`design-system-mapping.md` §1 與 `mockups.md` M8）。重新用 `grep -ro 'md:' frontend/src \| wc -l` 複算為 **22**，與要求一致。**`design-system-mapping.md:31` 已補上就地更正**（「`md:` 的實際用量為 22 處」），**但 `mockups.md:442` 的 M8 段落仍原封不動寫「`md:` **19** 處」，附近完全沒有任何更正附註**——兩個被指名的落點只修了一個。此處是 `mockups.md` 自己在產出時引用的斷點數字，不是單純轉述上游，理當同步。 | 在 `mockups.md:442` 附近補一句就地更正（仿 `design-system-mapping.md:31` 的格式），把「19 處」更正為「22 處」並附查證指令，使兩個落點一致。 | Unresolved |
| R-06 | Minor | `interaction-spec.md:15` | 已更正為「既有 34 個」並附更正說明與 `review-02` 的 `R-06` 出處，與 `design-system-mapping.md` §13（`grep -roh 'data-testid="[^"]*"' frontend/src \| sort -u \| wc -l` = 34，複算一致）同步。全檔（`mockups.md`／`accessibility-checklist.md`／`refined-mockups-questions.md`／`design-system-mapping.md`）掃描「24 個」「24 處」字樣，0 命中殘留。 | 無需再改。 | Resolved |
| R-07 | Minor | `refined-mockups-questions.md`（新增「修訂 1 的彙整摘要」一節，第 436–473 行） | 已補上彙整摘要，逐項列出五份產出修訂 1 的實際內容、使用者應特別注意的三件事、以及七項發現的處置狀態。未新增「Looks correct」式的彙整確認，但給出的理由可查證為真：`aidlc-state.md:21` 逐字為「`Summary Confirmation`: off (set by you)」，故引擎本輪確實不要求也不記錄該收據；本站選擇不替使用者重新開啟他自己關掉的儀式，同時仍把後果寫在核可關卡會看到的文件裡，滿足了 `R-07` 真正要防的事（使用者只看到選項、沒看到後果）。此判斷合理。但該節末段寫「七項逐一處置，無一項留為 Accepted risk」——這句話與本輪查出的 R-05（部分未修）、R-08（殘留傳播）不符，屬於過度宣稱完成度，見 R-10。 | 處置機制的判斷本身成立，判 Resolved；但其完成度宣稱的準確性另記 R-10。 | Resolved |

| R-08 | Minor | `accessibility-checklist.md:222`（「修訂 1 對『部分改善』這句話的更新」一節） | **新發現（本輪修正造成的殘留）**：`review-02` 的 `R-03` 指出「掃描點由 2 增為 9」是錯的數字（應為 2→7 列或 2→12 次掃描），作者已在「axe 掃描點的修訂」一節（第 183–186 行）正確更正並說明計數基準。但同一份檔案往下約 40 行的另一處——「修訂 1 擴大了 `[axe]` 的覆蓋面（掃描點由 **2 個增為 9 個**），但沒有改變那個結構」——仍是修正前的錯誤數字，一字未改。這正是 `project.md` 已記過的「跨檔傳播」失誤的同檔內版本：同一個事實在同一份檔案內以兩種形式表達，修正只命中了其中一種。 | 把第 222 行的「2 個增為 9 個」更正為「2 列增為 7 列（實際掃描 12 次）」，與上文的計數基準說明一致。 | New |
| R-09 | Minor | `mockups.md:81-83`／`888`／`:883`、`accessibility-checklist.md:156`、`refined-mockups-questions.md:295`（五處皆引用 `Sidebar.tsx:209-213`） | **新發現**：五處對 `大腦（示範）` 區塊的行號引用皆為「209-213」。實地讀 `frontend/src/components/Sidebar.tsx:209-216`：209 為 DEMO SCOPE 註解，210 `<div>`，211 `<nav>`，212 `<NavLink>`，213 文字「大腦（示範）」，214 `</NavLink>`，215 `</nav>`，216 `</div>`——完整區塊是 209-216，「209-213」只到可見文字那一行、未含收尾標籤。此引用源自 `review-02` 自己的原始措辭（我的上一輪審查），本輪的修正動作原樣沿用、未發現也未糾正這個次要的行號範圍誤差。不影響任何結論（`U14` 移除範圍、可見列計數皆不受影響），純粹是引用定位的精確度問題。 | 五處引用統一更正為 `Sidebar.tsx:209-216`（或註明「209 起、至 216 的 `</div>` 止」），下次编辑這些段落時一併處理即可，不必為此單獨開一輪。 | New |
| R-10 | Minor | `refined-mockups-questions.md:471-473`（「審查的七項發現全部已修」一節） | **新發現**：該節逐字寫「`review-02` 判 READY（0 Critical／2 Major／5 Minor）。……七項逐一處置，無一項留為 Accepted risk。」這句完成度宣稱與本輪查證結果不符：`R-05` 的兩個被指名落點只修了一個（見上表，判 Unresolved），且 `R-08` 查出 `accessibility-checklist.md:222` 仍殘留 `R-03` 要修正的錯誤數字。這不是嚴重的事實錯誤（兩處殘留皆為低影響的計數/傳播問題），但「全部已修、無一項留為風險」這句話本身是過度宣稱，會讓核可關卡的人誤判完成度。 | 把該句改寫為「六項半已處置；`R-05` 的 `mockups.md` 落點與一處同檔傳播殘留（`accessibility-checklist.md:222`）留待下次編輯這些檔案時一併修正」，如實反映範圍。 | New |

### Summary

**七項原始發現的狀態**：R-01、R-02、R-04、R-06、R-07 五項已完整核實為 Resolved——我逐一重新查證了支撐這些修正的事實（`AxeBuilder.include()` 的真實行為、`Sidebar.tsx` 的實際行號與 `ux-guide.md` 的 7 項上限、12 個 ASCII 框的逐行 72 字元複算、`data-testid` 相異值 34、`Summary Confirmation: off` 的機制事實），全部與作者的更正一致。R-03 在它被指名的那一個落點（`mockups.md` 自檢報告）已正確修正，判 Resolved，但同一份 `accessibility-checklist.md` 另一處（第 222 行）仍殘留修正前的錯誤數字，另記為新發現 R-08。R-05 的兩個被指名落點（`design-system-mapping.md` §1、`mockups.md` M8）只修了前者，`mockups.md:442` 仍寫著原本的「19 處」，判 Unresolved。

**本輪修正是否引入新缺陷**：沒有引入會動搖任何設計決定的新缺陷。查出的三項新發現（R-08／R-09／R-10）全部屬於同一種形狀——**跨檔或同檔內的傳播殘留與完成度宣稱過頭**——而不是新的設計錯誤：R-08 是 R-03 的修正只打到一個落點、沒有掃到同檔另一處的同一個數字；R-09 是沿用了我自己上一輪審查文字裡的一個次要行號誤差，沒人在這輪的更正動作中重新核對它；R-10 是彙整摘要的完成度宣稱沒有對照本輪實際的修正範圍去核實。三者皆為 Minor、皆不影響任何既定設計決定（D11=A、`大腦（示範）` 的移除與交接 H-13、單一斷點、34 個 test-id 前綴）。

**我的獨立複算（與作者的自檢對照）**：
- axe 掃描點：表格列數 7（2 不變 + 5 新增）、實際掃描次數 12（1+1+1+3+2+2+2）——與更正後的 `accessibility-checklist.md:183-186` 一致。
- ASCII 框：12 個（M10×3／M11×1／M13×2／M14×2／M15×3／M16×1），12 個框的全部內容行皆為 72 字元（`len()`）。
- `md:` 斷點用量：22 處（`grep -ro 'md:' frontend/src | wc -l`）。
- `data-testid` 相異值：34 個（`grep -roh 'data-testid="[^"]*"' frontend/src | sort -u | wc -l`）。
- Sidebar 可見列數：7（3 群組標題 + `大腦（示範）` + 入口 + 我的記憶 + 專案），對照 `ux-guide.md:61` 的 max 7 — 恰好踩在上限。
- `Sidebar.tsx` 的三個既有 `<nav>` 行號：144／200／242（非原寫的 233）。
- `大腦（示範）` 區塊的實際行號範圍：209-216（五處引用寫的「209-213」略短，見 R-09）。
- `mockups.md` 等五份產出的目前實際行數：947／767／279／229／473——與 `mockups.md:944` 自檢表宣稱的「914／767／272／214／434」已不一致（因為該表寫於本輪 R-01–R-07 修正之前，修正本身又新增了內容，但沒有回頭更新這張表）。這本身不是誤導性的錯誤（該行有時間戳註明是「本節寫入後」的值，而不是「本輪修正後」的值），但連同 R-10 一起看，顯示這一輪修正的收尾動作沒有把「自檢已完成」的描述延伸覆蓋到修正本身。

**建議給人工關卡**：本輪驗證確認 7 項原始發現中 6 項已妥善處置（R-03 在其被指名的落點內完整修正），1 項（R-05）只完成一半。另查出 3 項新的 Minor 殘留（R-08／R-09／R-10），全部是同類的「傳播掃描不夠徹底」或「完成度宣稱沒有對照實況」，不涉及任何需要重新裁決的產品或設計決定。依團隊的裁決規則（0 Critical、0 Major 未解決、Minor 不論數量不擋），判定 **READY**。這是本站最後一次審查，R-05／R-08／R-09／R-10 四項未解決的 Minor 殘留將以 Accepted risk 形式進入核可關卡紀錄——它們都是檢查清單層面的小尾巴（兩處孤立數字、一個行號範圍、一句過度宣稱），不影響 D8–D12 五項定案、交接 H-9～H-13 或任何畫面規格本身，但建議在下一次編輯這些檔案時（例如 `units-generation` 落地或 `domain-design` 處理 H-12 時）順手補上，不需要為此單獨重開一輪審查。
