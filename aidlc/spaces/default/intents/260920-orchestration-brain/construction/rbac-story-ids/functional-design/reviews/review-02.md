## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-04T11:32:53Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `construction/rbac-story-ids/functional-design/rules.md` > 修訂 1 `BR7.3`／`BR7.4`，交叉比對 `inception/user-stories/stories.md` `AC12.4.1` | `AC12.4.1`（已核可，逐字：「**Then** 被選中者為該專案**最早加入的成員**」）對自動改選的候選範圍沒有任何限定詞——它適用於「該專案另有成員」這個 Given 下的**任何**成員。`BR7.3` 卻把候選集合窄化為 `{m ∈ members \| user_can(m.role,'K3','edit')}`，即只在持有全域 `K3.edit` 的成員裡選最早加入者；`K3.edit` 只給 4／11 個角色（`BR5.2`），其餘 7 個角色（含 `Developer`／`FinOps_Analyst`／`Security_Reviewer`／`Platform_Owner`，皆持有 `K3.view`）可以合法成為一般成員。可構造的反例：若某專案最早加入的非 owner 成員是一位 `Developer`（只有 `K3.view`），依 `AC12.4.1` 的字面應選中他，但 `BR7.3` 會跳過他、改選下一位持有 `K3.edit` 者，或在無人持有時直接擋下停用——這是 `AC12.4.1` 字面從未涵蓋的第三種結果。本單元用來處理這個張力的機制（`修訂 1 Q7`）只向使用者揭露了「挑選純函式要多一個輸入、不得讀 DB」這項**實作**代價，未揭露它會**窄化已核可 AC 的選取範圍**這項**語意**代價；也沒有比照同檔 `BR6.3` 的做法（明寫「這是對齊修正，依 `refined-mockups:c3` 不回改上游，在此記明」）去標註、交接給 `AC12.4.1` 的所有者。按現狀，`U19` 實作者若以 `AC12.4.1` 字面為準寫測試，會與 `BR7.3` 矛盾；若以 `BR7.3` 為準，`AC12.4.1` 在一般成員比任何 `K3.edit` 持有者更早加入的資料狀態下即為假，而沒有任何上游文件被告知這件事。 | 在 `rules.md` 比照 `BR6.3` 的既有格式，於 `BR7.3`／`BR7.4` 加一條「對齊修正」說明，明寫它把 `AC12.4.1` 的「最早加入的成員」窄化為「最早加入、且持有全域 `K3.edit` 的成員」，並把這項窄化登記為交接給 `AC12.4.1` 擁有者（`user-stories`／`U19`）的事項，供下一次觸達該站時收斂或更正驗收標準原文。 | New |
| R-02 | Minor | `construction/rbac-story-ids/functional-design/traceability.json` > `coverage[4]`（`AC9.2.1`）、`coverage[5]`（`AC9.2.2`）、`reverse` 中 `BR4.4` | 三個條目的 `target` 欄位內文都把「【修訂 1 增補】……」那句話逐字重複貼了兩遍（例如 `AC9.2.1` 的 target 從「本單元讓四個角色持有 K2.edit」一路到「同時保證該角色建立後管得動自己的專案（AC12.1.2）」整句再重複一次）。內容本身不衝突也不誤導，但這是一個編輯時的複製貼上殘留，會讓下一個開這份 JSON 做機械比對或人工核對的人誤以為兩句話在描述不同的事。 | 去除三處重複的句子，各保留一份。 | New |
| R-03 | Minor | `construction/rbac-story-ids/functional-design/functional-spec.md` > `§六′` 網路暴露列、`§六′-b` 契約端點三問表 | 兩處都把 `_build_role_catalog` 的定義行號寫成 `:250`，但 `backend/services/user_router.py` 實際是 `def _build_role_catalog(db: Session) -> List[dict]:` 在第 **249** 行（已用 `grep -n` 核對）。這是本 record 已反覆記載過的「事實對、定位差一行」形狀；本檔同一節另外五處行號引用（`:242`、`:310`、`:313`、`:885`、`database.py:171`／`:184`）本次逐一核對皆精準命中，只有這一處差一行。 | 把兩處 `:250` 改為 `:249`。 | New |
| R-04 | Minor | `construction/rbac-story-ids/functional-design/rules.md` > `BR4.5` 的 `note`；`functional-spec.md` `§六′` network exposure 列 | 兩處都寫「揭露內容是四個中文功能名，不含任何資料或人與角色的對應」。但實讀 `user_router.py:249` 的 `_build_role_catalog`，`/roles/catalog` 的回應**正是**逐角色（`CANONICAL_ROLES`）列出其 `features`（持有能力的中文標籤）——即公開回應確實包含「角色 → 功能」的對應，只是不含「使用者（人）→ 角色」的對應。現有措辭把這兩種不同的「對應關係」合併成一句話帶過，容易讓人讀成「完全不含角色資訊」，與同一段上面自己承認的「逐角色列出」自相矛盾。 | 把「不含任何資料或人與角色的對應」改寫為更精確的說法，例如「不含使用者與角色的對應（即不洩漏『誰是什麼角色』），但本就會逐角色揭露『哪個角色能做什麼』——這是 `/roles/catalog` 既有設計目的，K1–K4 不改變揭露的類別」。 | New |
| R-05 | Minor | 送審 brief 的「deviation #5」自述 vs `.claude/tools/aidlc-sensor-traceability.ts:460,503` | 本輪 brief 把加 `status: Deferred` 的 `reverse` 列描述為繞過「sensor 只承認 `status: OK` 引用」的限制。實讀 sensor 原始碼：`okEntries`（只收 `status==="OK"`）只用來從 **coverage** 推導 `targeted` 集合；`derivedOrphans` 的豁免條件 `explained` 是 `new Set(data.reverse.map(e => e.id))`——對 **reverse** 陣列**不篩 status**，任何狀態的 `reverse` 項目都能讓同名規則免於被判為 orphan。所以本輪在 `reverse` 補上 `BR1.1`／`BR1.3`／`BR1.4`／`BR2.2`／`BR2.3` 五筆 `Deferred` 項，其所以能消除 orphan，不是因為用了「Deferred 也算數」這個特例，而是因為 sensor 對 `reverse` 本來就不檢查 status。補的內容本身誠實（確實說明了這五條規則經由哪些 `coverage` Deferred 列被引用），不構成灌水，但本輪對「這是不是在鑽 sensor 漏洞」這個自我提問給出的理由是錯的——回答「不是鑽漏洞」是對的，但給錯了理由。 | 若要在產出或交接記錄中保留這個自我檢查的結論，理由改寫為「`derivedOrphans` 的 `explained` 集合不篩 `reverse` 的 status，故補 `Deferred` 項本就是 sensor 設計內的合法用法，不是鑽漏洞」，而非「sensor 只認 `status: OK`」。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 手動腳本：解析 `backend/services/rbac_seed_data.py` 的 308 列，統計角色數／story id 數 | 11 角色、28 story id、308 列，組合完整無缺漏 | 確認 `entities.md`／`rules.md`／`functional-spec.md` 反覆引用的「既有 308 ＝ 11×28」「352 ＝ 308＋11×4」等算式成立，非憑印象 |
| 手動腳本：統計 `Platform_Owner` 在既有 28 個 story id 上的 `can_edit`／`can_review` | edit=1（`J1`）、review=2（`F3`、`H2`） | 證實 `entities.md`「修訂 1 更正一處既有事實陳述」段的自我更正（`Platform_Owner` 並非全為 `v--`）屬實，且決定（`K2`/`K3`/`K4` 皆不給其 `edit`）依 `functional-design:c22` 保留不變，處置得當 |
| `grep` 核對：`schema_rbac.sql` 第 12、761 行；`DEPLOY.md` 第 577/591/596/1259/1270 行 | 全部精準命中（`761` 行確為 `-- 352`，與 `INSERT` 區塊實算 308 列不一致，屬既存漂移） | 證實本輪對原文「第 759 行」「`DEPLOY.md` 第 594／613 行」兩處行號更正（改為 761、577/591/596/1259/1270）是本輪真正重新核對過的結果，非沿用舊引用 |
| `grep` 核對：`user_router.py` 的 `STORY_FEATURE_LABELS`（27 鍵）、`CATALOG_EXCLUDED_STORIES`（`{J1}`）、`_feature_label`/`_build_role_catalog`/`/roles/catalog`/`force=True` 端點的行號 | `:60`、`:90`、`:242`、`:249`（artifact 誤植為 `:250`，見 R-03）、`:310`、`:313`、`:885` 全部核對；`roles_catalog` 確認無 `Depends(get_current_user)`、docstring 逐字「公開」 | 證實 `BR4.5`／`N-2`／§六′-b 的契約端點三問查核基本準確，僅一處行號誤植（R-03） |
| `database.py` 行號核對：`ensure_role_permissions_seeded(db, force=False)`、`ensure_missing_role_permissions(db)` | 分別在 `:171`、`:184` | 證實本輪「原文 `171–175` 的行號錯誤，兩函式分別在 `171`／`184`」這項自我更正準確 |
| `grep` 核對：`contract-summary.md` 的 `K-16` `public_interface`（7 個方法）、`K-19`/`K-20` 的 `authorization_responsibility` 逐字 | `K-16` 無 `review` 動作；`K-19` 逐字「頁面自身的可見性把關由 `K-03` 的 `K4` story id 承擔」；`K-20` 逐字「可見性把關由 `K-03` 的 `K3` story id ＋ `K-16` 的 per-project 判定承擔」 | 證實 `EC-4`（`can_review` 恆 false 的理由）與 `BR6.3`（`K4` 窄化為僅需求籤、依 Q6=A 對齊修正）兩項查證屬實、引用精準 |
| 讀 `.claude/tools/aidlc-sensor-traceability.ts` 的 orphan 推導邏輯 | `explained` 集合來自 `data.reverse` 全部 id，不篩 status；`targeted` 才篩 `status==="OK"`（僅用於 coverage 的 target 校驗） | 推翻本輪 brief 對 deviation #5 的自我描述（見 R-05）；但本輪實際採取的補救動作（在 `reverse` 補 `Deferred` 項）本身合法、非灌水 |
| 交叉比對 `stories.md` `AC12.4.1`／`FR12.4` 與 `rules.md` `BR7.3`／`BR7.4` | `AC12.4.1` 字面「最早加入的成員」無任何資格限定；`BR7.3` 把候選窄化為持有全域 `K3.edit` 者 | 發現 R-01：一項未經對齊修正標註、可能使已核可 AC 字面失真的語意窄化 |

### Summary

本輪修訂在數字、行號與跨檔引用上的查證紀律明顯優於本 record 先前幾站的平均水準——11 處我獨立重新核對的 `file:line` 引用裡，10 處精準命中（唯一的例外是 R-03 的 `:250`/`:249` 差一行），且多項「本站自檢查出」的缺口（`schema_rbac.sql:761` 既存漂移、`DEPLOY.md` 五處行號、`ensure_role_permissions_seeded` 的第三個呼叫點、`Platform_Owner` 的事實更正）經我實地重新計算或 `grep` 後確認屬實，不是憑印象宣稱。阻擋 READY 的唯一 Critical/Major 級問題（R-01）是一個真實但範圍有限、修法明確（比照本檔自己已用過的 `BR6.3` 對齊修正格式補一條說明＋交接事項）的語意窄化：`BR7.3` 把自動改選的候選範圍限制在全域持有 `K3.edit` 的成員，而這與已核可的 `AC12.4.1`（「最早加入的成員」不限資格）在特定資料狀態下會給出不同結果，且這項窄化只以「Q7 的實作代價」揭露給使用者，未以本記錄慣用的「對齊修正」格式登記為對上游 AC 的修改。其餘四項（R-02～R-05）均為 Minor：兩處純文字重複、一處行號差一、一處措辭精確度、一處 brief 自述與 sensor 原始碼不符（但實際動作合法）。

**分類計數**：newly introduced by this revision = 5（R-01、R-02、R-03、R-04、R-05 全部源自本輪修訂的新內容）；pre-existing and unreviewed = 0；new design problem = 1（R-01，其餘四項屬流程／措辭缺陷而非設計問題）。

依驗證規則（零 Critical、≤2 Major 任何數量 Minor 即 READY）：本輪 0 Critical、1 Major、4 Minor，**READY**。R-01 建議在下一次觸達 `user-stories`／`U19` 時收斂，但不構成本單元本身不可實作的架構缺陷。
