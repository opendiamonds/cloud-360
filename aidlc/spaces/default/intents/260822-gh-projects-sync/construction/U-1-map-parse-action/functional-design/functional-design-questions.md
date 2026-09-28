# Functional Design — U-1 映射與解析 composite action

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-1-map-parse-action
     來源標籤：[ad:*] application-design；[req:*]／[US:*] requirements／stories；
     [ug:*] units-generation。本檔只問**尚未被上游定案**的事。 -->

## CONDITIONAL 適用性判定

stage 的 condition 為「New data models, complex business logic, or business rules need design. Skip if simple logic changes with no new business logic.」逐項對照 U-1：

| 條款 | U-1 判定 | 依據 |
| --- | --- | --- |
| New data models | ✅ | `Decision`／`ParsedRecord`／`Unparseable` 三個新型別，[ad:component-methods.md] 已給欄位但未給語意細節 |
| Complex business logic | ✅ | 七條**有序**判定，且對照表須為**總函式**（[US:S-2 AC 15]） |
| Business rules need design | ✅ | `get_field` 四條行為、50 字元截斷、`[S]` 與 `— SKIP` 的區分 |
| Skip if simple logic changes | ❌ 不適用 | `.github/actions/` 在本 repo 不存在，此為首例，非修改既有邏輯 |

**判定：EXECUTE。** `produces_kinds` 對 `kind: library` 解析出三份產出，`frontend-components` 限 `ui`，不適用。

## 已由上游定案、本站不重問

| 事項 | 出處（可引用的具體落點） |
| --- | --- |
| 七條判定的**優先順序**與各自的 `reason_code` | [ad:component-methods.md] §C-1「判定順序」1–7 |
| 第 3 條先於第 4／5 條（`Completed` 不因殘留 `[?]` 回退） | 同上，附註逐字 |
| 第 1 與第 3 條互斥（`handlePark` 在 `Status == "Completed"` 時拒絕，實測 `aidlc-state.ts:830-832`） | 同上 |
| 自訂欄位格式 `<短前綴><stage-slug> (<編號>)`、四個前綴 | [ad:component-methods.md] §自訂欄位格式（[US-OQ-4] 定案、[Q3=C] 收斂） |
| `get_field` 四條行為的**內容** | [ad:component-methods.md] §C-2，[US:S-2 AC 7–10] |
| 兩處不一致時以受管區塊為準 | [ad:decisions.md] ADR-A4 |
| 承載形式為 composite action、且 Project 編號／組織名／record 根目錄／自訂欄位名一律為 input | [ad:application-design-questions.md] `[Answer]: A（經 F1 收斂）` |
| fixture record 不註冊進 `intents.json`，兩條選取路徑都不會選中它 | [ad:component-methods.md] §C-2「intent 選取的邊界」 |
> **`上限 50 字元` 已從本表移除**（reviewer iteration 1 Major）：Q4 正是在問要不要在特定邊界超過它，把它同時列為「已定案、本站不重問」是同一份檔內的自相矛盾。改列為缺口 F-3，見下。


## 本站發現的上游契約缺口

**四項**（reviewer iteration 2 Major 後更正——先前寫「兩項」，是 F-3 加入後未同步的計數；F-4 為本輪新增）。依 `project.md`（`units-generation:260822-ug-L2`）標出、寫明它擋住哪一條、指派落點；不逕自改寫上游。

**兩種性質不可混同**：F-1／F-2／F-4 是上游的**缺漏**（該寫而沒寫）；**F-3 是對已核可約束的鬆綁**（上游寫了，本站要改它）。先前的前言把四項一律稱為「缺漏」，與 F-3 自身的內文直接矛盾。

### 缺口 F-1：`Config` 從未被定義

`Config` 出現在六個方法簽章（`map`、`field_value_for`、`read_item`、`create_item`、`ensure_field`、`reconcile`），但 [ad:component-methods.md] §共用型別的型別區塊**沒有它**。至少三件事必須由它承載：白名單集合（[req:FR-J5] 的 `whitelisted` 判定）、Project 編號／組織名／record 根目錄／自訂欄位名（[F1=A] 要求全部參數化）。

**擋住**：`map()` 無法判定 `whitelisted`，[US:S-3 AC 6] 的白名單前後半都不可實作。
**落點**：本站的 `domain-entities.md`（U-1 這一輪即可定義，因為 `map` 是 U-1 的方法）。

### 缺口 F-2：`map()` 算不出第 2 條判定

第 2 條「有未處理反向紀錄 → `suppressed`」需要反向同步狀態，但 `map()` 的宣告輸入只有 `ParsedRecord | Unparseable` 與 `Config`，而 `ParsedRecord` 由 `parse(state_md_text, intents_json_text, record_path)` 產生——**三個來源都不含反向同步狀態**。

> **本段先前的後半句已更正（reviewer iteration 2 Critical）**：原文寫「那份狀態在 `<record>/sync-state.json`，是 C-4 `read_sync_state` 才讀得到的」——**那是錯的**，且與本檔 Revision 1 表中「來源更正」那一列直接矛盾（同一份文件同時主張與否定同一件事）。[ug:unit-of-work.md] 的 U-8 實作註記明文記載已核可的偵測機制是**讀開啟中的反向同步 PR 的 diff 是否含該 intent 的 record 路徑**。此處不是「作答當下的紀錄」——它是本站自己的缺口描述，寫錯就該改，不受「不改寫題幹與選項」那條保護。

**擋住**：[req:FR-G3] 與 [US:S-6 AC 3]（逐 intent 暫停覆寫）在 U-1 這一層無法實作。
**落點**：本站 Q2 裁定。三個候選都不需要改動已核可的**判定順序**，差別在資料怎麼進來。

### 缺口 F-3：本站的 Q4 會鬆綁一條已核可的上游約束

[ad:component-methods.md] §自訂欄位格式定的「**長度上限 50 字元**」是 [US-OQ-4] 的定案、經 [Q3=C] 收斂、並通過三輪 reviewer。Q4 問的是「前綴＋編號本身就塔滿時怎麼辦」，而它的三個選項中有一個（A）**會讓值超過該上限**。

**這不是缺漏，是鬆綁**——與 F-1／F-2（上游沒寫的東西）性質不同，必須分開記載。依 `project.md`（`units-generation:260822-ug-L2`）標出並指派落點：

- **擋住**：無。上游的上限在「前綴＋編號 ≤ 50」的情形下仍完全適用，被鬆綁的只有上游未涵蓋的邊界。
- **落點**：**上游 application-design 的 `component-methods.md` §自訂欄位格式**，需補一句「前綴與編號本身超過上限時照寫」。本站**不逕自改寫上游**；已把該句寫進本單元的 `business-rules.md` R-5.4 並明記它是刻意鬆綁，供上游下次修訂時採納。
- **人工授權**：Q4 的答案由使用者裁定（見下方 `[Answer]`），故此鬆綁**非本站單方面決定**。但「有人授權」不等於「上游已更新」，兩者不可混同。

### 缺口 F-4：誰負責算出 `reverse_pending`？

[Q2=A] 定案由 workflow 層在逐 record 迴圈**之前**組出 `Config.reverse_pending`，來源是開啟中的反向同步 PR 的變更路徑（U-8 的偵測機制）。

**但沒有任何上游 artifact 指派這件事給任何單元。** U-8（[ug:unit-of-work.md]）擁有的是**產生**反向 PR；**讀取**開啟中的反向 PR 並映射為 intent id 集合，是**正向同步 workflow**（U-6）在每一輪開始時要做的事，而 U-6 的擁有清單裡沒有它。

- **擋住**：[req:FR-G3] 與 [US:S-6 AC 3] 的實作在 U-6 這一層沒有落點。U-1 已經備好接口（`Config.reverse_pending`），但沒有人被指派去填它。
- **落點**：**U-6 的 functional-design**，需明確擁有「讀開啟中的反向 PR → intent id 集合」這個步驟，並定義 PR 不存在時的行為（空集合）與 API 失敗時的行為（**不得**靜默視為空集合——那會讓暫停覆寫失效而無人察覺）。
- **本站不逕自指派給 U-6 的擁有清單**（那是 units-generation 的產出），只標出缺口與建議落點。

> **⚠ 目標 stage 是 CONDITIONAL，指派可能無聲落空**（reviewer iteration 3 Major）：`functional-design` 的 `execution` 為 `CONDITIONAL`（stage 檔 frontmatter），且 `for_each: unit-of-work`。**U-6 那一輪若被判為「無新資料模型、無複雜商業邏輯」而 skip，本指派會連帶消失，而沒有任何機制會報錯。** 依 `project.md`（`units-generation:260822-ug-L2`）此風險必須明寫並指出誰要確認：
>
> - **確認人與時機**：**Bolt 1 的 gate**（U-6 落在 Bolt 1，見 `bolt-plan.md`）。核可該 Bolt 前必須確認 `construction/U-6-forward-workflow/functional-design/` 存在且其中定義了 `reverse_pending` 的取得步驟。
> - **若 U-6 的 functional-design 被 skip**：本缺口改由 **Bolt 1 的 Definition of Done** 直接承接——[req:FR-G3] 與 [US:S-6 AC 3] 不得在無人負責計算 `reverse_pending` 的情況下被標為通過。
>
> **先前寫「本項與 F-3 的處置形狀相同」是不準確的**（同輪 Major）：F-3 的目標 `component-methods.md` 是**已執行完畢**的上游 artifact，指派它只是登記待修訂；F-4 的目標是**尚未執行且可能被 skip** 的 stage。兩者的落空風險不同級，不該用同一句話帶過。
>
> 至於 iteration 2 指出的原始問題（iteration 1 把更正後的機制寫成既定事實、沒像 F-3 那樣標成缺口）：那是同一輪內對兩個同型問題採不同標準，已由本節的存在修正。

---

## 問題

### Q1. composite action 怎麼把 `Decision` 交給呼叫端？

composite action 的 `outputs` **只能是字串**，而 `map()` 回傳的 `Decision` 有四個欄位（`status`、`field_value`、`reason_code`、`traceable_row`），其中 `status` 還可能是 `null`。本 repo 無 composite action 先例（`.github/actions/` 不存在），沒有既有形狀可沿用。

A. **四個獨立 output**：`status`、`field_value`、`reason_code`、`traceable_row` 各一個。看得到的效果：呼叫端 `${{ steps.map.outputs.reason_code }}` 直接可用，不需 `fromJSON`；YAML 層一眼看得出這個 action 產出什麼。`null` 以空字串表達，而 `reason_code` 一律非空，故「`status` 空字串」與「決定不寫」是同一件事，不引入歧義。代價：`Decision` 未來加欄位時要同步改 `action.yml` 的 outputs 區塊與每一個呼叫端。

B. **單一 JSON 字串 output**：`decision`，呼叫端用 `fromJSON()` 取欄位。看得到的效果：加欄位不需改 `action.yml`；`null` 可如實表達而不需與空字串合流。代價：呼叫端每次取值都是 `${{ fromJSON(steps.map.outputs.decision).reason_code }}`，較難讀；且 JSON 字串經過 `$GITHUB_OUTPUT` 時多行與特殊字元需 heredoc 分隔符處理，是本 repo 沒踩過的坑。

C. **寫檔到 `$RUNNER_TEMP` 並 output 檔案路徑**：看得到的效果：完全不受 `$GITHUB_OUTPUT` 的大小與跳脫限制；對帳路徑一次處理多個 intent 時可累積成一份檔案。代價：引入檔案 I/O，而 [ad:components.md] 明記 C-1「**不擁有任何 I/O**」——雖然寫的是 runner 暫存區不是 record，但它讓「純函式、可用純文字 fixture 驅動」這個 [US:S-10 AC 1] 的前提變得需要額外解釋。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T05:40:13Z（讀自 date -u）· 四個獨立 output -->

### Q2. 第 2 條判定（`suppressed`）的輸入怎麼進 `map()`？（缺口 F-2）

三個候選都**不改動已核可的判定順序**，也都不改 `map()` 回傳型別；差別在資料從哪個參數進來，以及誰負責算「這個 intent 有沒有未處理的反向紀錄」。

A. **`Config` 承載，由呼叫端在進迴圈前算好**：把 `Config` 定義為含 `reverse_pending: [intent_id]`（一份 id 集合），workflow 層在逐 record 迴圈**之前**呼叫一次 C-4 讀 `sync-state.json` 組出它。看得到的效果：`map()` 維持已核可簽章一字不改；仍是純函式（同樣的 `Config` 與 `ParsedRecord` 必得同樣的 `Decision`），fixture 驅動不受影響；逐 intent 判定（[US:S-6 AC 3]）自然成立。代價：`Config` 同時裝「設定」（Project 編號、欄位名）與「本輪狀態」（哪些 intent 待處理），名字與內容不完全相稱——需在 `domain-entities.md` 明寫這是刻意的兩用。

B. **`map()` 加第三個參數 `sync_state`**：改為 `(ParsedRecord | Unparseable, Config, SyncState) -> Decision`。看得到的效果：語意最乾淨——設定與狀態分開，讀簽章就知道這個函式吃什麼。代價：**更動已通過三輪 reviewer 的 [ad:component-methods.md] 簽章**，屬對已核可上游的修改，依 `project.md` 的紀律應回上游走 Modify 而非在本站就地改。

C. **第 2 條移出 `map()`，由 workflow 層在呼叫前短路**：workflow 發現該 intent 有未處理反向紀錄時，根本不呼叫 `map()`，直接記 `suppressed`。看得到的效果：`map()` 的輸入完全不變，純函式性最強。代價：**判定順序被拆到兩個地方**——第 1、3～7 條在 composite action 內、第 2 條在 workflow YAML 內，而 [US:S-10 AC 1] 的 fixture 驅動測試只碰得到 composite action，第 2 條會落在自我測試的涵蓋範圍**之外**。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T05:40:13Z（讀自 date -u）· Config 承載 reverse_pending，呼叫端在迴圈前算好 -->

### Q3. `in_scope` 從哪裡判定？非 stage 行怎麼處理？

`list_stages` 回傳 `[{slug, checkbox, in_scope}]`，但 `in_scope` 的來源上游未定。實際的 `aidlc-state.md` 每一行形如 `- [x] intent-capture — EXECUTE` 或 `- [ ] market-research — SKIP`；`## Stage Progress` 區塊內另有 `### INITIALIZATION PHASE` 這類標題行、一行 HTML 註解，以及 `Per unit: [TBD]` 這種**不是 stage 的行**。

A. **後綴即判定，不match 的行一律忽略**：只有形如 `- [<c>] <slug> — <EXECUTE|SKIP>` 的行算 stage 行，`in_scope = (後綴 == "EXECUTE")`；其餘行（phase 標題、註解、`Per unit: [TBD]`）靜默略過。看得到的效果：規則單純、可用純文字 fixture 窮舉；新增 phase 或新增說明文字不會誤判。代價：若引擎未來改變後綴寫法（例如加入第三種標記），本機制會把整批 stage 讀成非 stage 行而使該 record 變成「無任何 in-scope stage 動過」→ 誤判為 `Ready`，**且不會報錯**。

B. **同 A，但無法 match 的非空行使該 record 回 `Unparseable`**：看得到的效果：上述靜默誤判變成明確的「跳過並列入無法解析清單」，符合 [req:FR-J3] 的精神。代價：`Per unit: [TBD]` 這種**現在就存在**的行會讓每個 Construction 階段的 record 全部變成 `Unparseable`——除非把它列為已知例外，而例外清單本身又是一個要維護的寫死清單，與 [req:FR-J4]「不得寫死」的精神相衝。

C. **A ＋ 一條下限檢查**：規則同 A，但若 `## Stage Progress` 區塊內**一行 stage 行都沒 match 到**，回 `Unparseable{missing: ["stage-lines"]}`。看得到的效果：保留 A 的單純與寬容，同時把 A 的那個靜默誤判（後綴寫法改變 ⇒ 全部讀不到 ⇒ 誤判 `Ready`）變成可觀察的失敗。代價：仍抓不到「只有部分行的寫法改變」這種局部漂移。

X. Other（請說明）

[Answer]: C  <!-- 2026-08-29T05:40:13Z（讀自 date -u）· 後綴判定 ＋ 區塊內零 match 時回 Unparseable -->

### Q4. 自訂欄位值超過 50 字元時，截斷規則的邊界怎麼定？

上游定案：格式 `<短前綴><stage-slug> (<編號>)`、上限 50、「超出時截斷 stage-slug 尾端並保留前綴與編號（前綴是狀態訊號，不可被截斷）」。但**前綴與編號本身就佔掉 50 字元**時上游未定——`parked @ ` 是 9 字元，編號部分 ` (260822-gh-projects-sync)` 是 26 字元，兩者相加 35，留給 slug 的只剩 15；若 intent id 更長則可能為負。

A. **slug 可被截到零長度，前綴與編號永遠完整**：不足時 `field_value` 就是 `parked @  (<很長的編號>)`，即使整體超過 50 也照寫。看得到的效果：狀態訊號與可追溯的編號永不遺失，這兩者正是這個欄位存在的理由；`traceable_row` 與受管區塊仍有完整敘述（ADR-A4）。代價：**上限 50 在此情形下被違反**，需在 `business-rules.md` 明記這是刻意的優先序而非漏判，並在 U-3 寫入前不做二次截斷。

B. **編號改為可截斷，slug 保底 N 字元**：看得到的效果：整體嚴格不超過 50。代價：**被截斷的編號無法追溯**——[US:S-5] 這個欄位的用途正是讓人看到「這是哪一個 intent 走到哪一站」，半個編號兩者皆失。

C. **超限時整個值退化為固定短字串**（例如 `parked @ …`）：看得到的效果：規則極簡、必不超限。代價：直接放棄該欄位在這些 record 上的資訊價值，而觸發條件（intent id 長）與內容價值無關。

X. Other（請說明）

[Answer]: A  <!-- 2026-08-29T05:40:13Z（讀自 date -u）· slug 可截到零，前綴與編號永遠完整 -->

---

## Step 4 歧義分析（stage 檔要求的強制步驟）

- **模糊answer**：無。四題皆為明確選項，無「mix of」「不確定」「看情況」類措辭。
- **答案間矛盾**：無。逐對檢查：Q1=A 的「`null` 以空字串表達」與 Q3=C 的「回 `Unparseable`」不衝突（後者透過 `reason_code = "unparseable"` 表達，`status` 為空字串）；Q4=A 允許 `field_value` 超過 50 字元，而 Q1=A 的 output 為字串無長度限制，相容。
- **合起來產生的新細節（非矛盾，但必須定死）**：Q2=A 讓 `Config` 含**變長集合**（`reverse_pending`、白名單），而 Q1=A 選的是「具名、可讀」的介面風格；composite action 的 `inputs` 是固定名稱的字串。序列化形式因此必須明確，否則實作者會各自發明。**本站裁定**（記入 `domain-entities.md` §Config 的承載形式，並在 diary 記為 Interpretation）：純量設定走具名 input，集合型設定走**換行分隔的單一字串 input**。理由是它與 Q1=A 的「YAML 層一眼看得出」一致，且換行分隔在 `$GITHUB_OUTPUT`／`inputs` 兩側都不需跳脫處理（相對於 JSON，正是 Q1=B 被放棄的理由）。此為設計裁定而非另一題——三種候選（JSON 字串／換行分隔／逗號分隔）之間沒有會改變工作內容的差異，依 `project.md`（`requirements-analysis:260822-ra-c5`）不出成單一可行解的假選擇。

---

## Revision 1（2026-08-29T06:10:32Z）— reviewer iteration 1 的修正

verdict **NOT-READY**（2 Critical、1 Major、1 Minor）。**Q1～Q4 的題幹、選項與答案一律不改寫**，它們是作答當下的紀錄；下列是對選項**理由**的更正與缺口重新分類。

| 發現 | 判定 | 處置 |
| --- | --- | --- |
| Critical #1 — Q2=A 選項本文寫的「呼叫一次 C-4 `read_sync_state` 讀 `sync-state.json`」與 [ug:unit-of-work.md] U-8 的已核可偵測機制（讀反向 PR 的 diff 是否含該 intent 的 record 路徑）矛盾，且 `read_sync_state` 的簽章是逐 `record_path`，「呼叫一次」不成立 | **成立** | **決定不變、理由更正**（`functional-design:c22`）：`Config` 承載、迴圈前算好、`map` 維持已核可簽章且仍是純函式——這些都不受影響；改的只是那個集合的來源。更正寫入 `business-rules.md` R-3.2 與 `domain-entities.md` 的 `Config` 表 |
| Critical #2 — R-3.6 把 `[S]` 定為「動過」，使 `[S]` 與 `— SKIP` 的孿生 record 產出不同 Status，違反 [req:FR-B3] 與 [US:S-2 AC 5] | **成立，且是本站自己引入的錯誤**（非上游轉錄） | 定義反轉為「in-scope checkbox ∈ {`" "`, `"S"`} 即命中 R-3.6」。差別的可見性由 `skipped ` 前綴與 S-4 承接，FR-B3 的兩個要求同時滿足 |
| Major — 「不重問」表把 50 字元上限列為已定案，Q4 卻在鬆綁它 | **成立** | 從該表移除，改列為缺口 **F-3** 並指派上游落點 |
| Minor — `domain-entities.md` 的溯源清單漏列兩條 partial AC（S-2 AC 4、S-3 AC 6） | **成立** | 已補，並指向缺口 G-1 |

**未被推翻的攻擊**（reviewer 自述查證後不成立）：Q1 的 `null` → 空字串合流無歧義；R-5.3 的雙空格範例正確；`linter`／`type-check` 的 no-op 宣稱誠實（grep 確認零 TS/JS 圍欄）；F-1／F-2 確為真實的上游缺口而非捏造。
