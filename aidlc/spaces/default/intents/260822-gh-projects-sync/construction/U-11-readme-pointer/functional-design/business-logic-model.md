# Business Logic Model — U-11 README 指路段落

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-11-readme-pointer
     本單元的 `kind` 依 [ug:unit-of-work.md] 刻意留空（「五類皆不合，收完整設計矩陣」），
     故 `produces_kinds` 解析出**全部四份**產出。本檔是其中之一。 -->

## 適用性判定

**本單元沒有商業邏輯。** 這是判定，不是漏寫。

[ug:unit-of-work.md] 的 U-11 條目：擁有 [req:FR-H1]（在 `README.md` 增加一段含 Project #16 連結的文字）、交付「`README.md` 的一段新增文字」、驗證方式「文字比對」、複雜度 **XS**。

逐項對照 stage 的 condition（「New data models, complex business logic, or business rules need design. Skip if simple logic changes with no new business logic.」）：

| 條款 | 判定 | 理由 |
| --- | --- | --- |
| New data models | ❌ | 交付物是 markdown 文字，無任何型別、無結構化資料 |
| Complex business logic | ❌ | 無演算法、無分支、無資料轉換。整個單元是一次靜態的文字新增 |
| Business rules need design | ❌ | 唯二的約束（含 Project #16 連結、刪除行數為 0）已在 [US:S-11] 的 AC 1／AC 2 定死，且兩者都是二元可判的文字比對 |

**若這個 stage 可以逐單元 skip，本單元應該被 skip。** 引擎的 per-unit 迭代沒有這個能力——`report --result skipped` 作用於整個 stage（會連帶跳過 U-2～U-9），所以本檔以「判定 ＋ 理由」的形式存在，而不是被略過或被填入捏造的內容。

## 唯一的處理序列

```
在 README.md 既有內容之後 ──► 附加一段文字（含 Project #16 連結）
                              └─► 不修改、不刪除任何既有行
```

文字 fallback：只有一個步驟——附加。沒有讀取、沒有判斷、沒有轉換。

「只增不動」不是實作技巧而是**驗收條件**：[US:S-11 AC 2] 要求 `git diff --numstat` 對 `README.md` 的刪除行數為 0。這是 user-stories 站對原措辭「既有結構與總覽敘述未被改動」的改寫，理由是原句不可判（什麼算結構？改一個標點算不算？）。

> **引用來源已更正（2026-08-29T15:24:44Z，reviewer iteration 1 Major）。** 本單元先前把逐字引文「FR-H1（README 指路）為單段文字，無元件」的出處標為 `[ad:components.md]`，實測 `grep -in "FR-H1\|README" components.md` **零命中**——該句只存在於 `component-dependency.md`。這與 application-design 自己在其 reviewer iteration 2 已修過的同型混淆是同一個形狀，如今以「引錯檔名」在下游重現，違反 `project.md` 多次強調的「掛來源標籤前必須逐字核對原文」。

## 與上游的對應

單元定義引自 [ug:unit-of-work.md] 的 U-11 條目；AC 引自 `stories.md` 的 S-11（並見 [ug:unit-of-work-story-map.md] 的對應）；需求編號 FR-H1 引自 `requirements.md`。[ad:component-dependency.md] 明記「**FR-H1（README 指路）為單段文字，無元件**」，故本單元在 [ad:component-methods.md] 與 [ad:services.md] 中**沒有對應的方法或服務**——這是上游的明確判定，不是查不到。

<!-- 更正紀錄：本節原引用 [ad:components.md]，經 reviewer iteration 1 Finding #1 核對為誤植——該逐字原句實際出自 component-dependency.md:98。已於 2026-08-29T16:14:22Z 改為 [ad:component-dependency.md]。（此註記本身曾被一次整批字串替換連帶改成反義，同批更正。） -->

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T15:10:14Z
**Iteration**: 1

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
|---|---|---|---|---|
| 1 | Major | `business-logic-model.md:36`、`business-rules.md:28`、`domain-entities.md:11,23`、`frontend-components.md:11,27` | 六處把「**FR-H1（README 指路）為單段文字，無元件**」這句**逐字引號**的出處標成 `[ad:components.md]`。實測：`components.md` 全文（檔頭、C-1～C-7 七個元件清單、承載形式決定）**不含 "FR-H1" 或 "README" 字串**（`grep -in "FR-H1\|README" components.md` 零命中）；該逐字句只出現在 `component-dependency.md:98`（並在 `:103` 有更正註記、`decisions.md:240` 有修復紀錄）。這正是同一份 application-design 產出**自己在 reviewer iteration 2 抓到並標為 Major 修復過的同型混淆**（`decisions.md` iter2-#11：`FR-H1` 在 `components.md`／`component-dependency.md` 間的歸屬曾經自相矛盾，修復後定案落在 `component-dependency.md`）——如今在下游 functional-design 的四份產出裡，以「整批引用到錯檔名」的形式重新出現。這四份文件的核心論證（本單元無元件、無方法、無服務）幾乎全部建立在對上游的引用上，引用出處錯誤直接削弱這個論證鏈的可查證性，且逐字違反 `project.md ## Corrections` 已多次強調的規則：「在 artifact 掛來源標籤前，必須回頭逐字核對該題的已選選項原文，不得憑印象引用」（`intent-capture:c11`，精神同樣適用於 `[ad:*]` 標籤）。**注意**：`component-dependency.md` 本身不在本 stage frontmatter 的 `consumes:` 清單內（只列 `components`／`component-methods`／`services`），這也是為何 `upstream-coverage` sensor 不會抓到這個錯誤——它只驗證文字裡出現了字串 "components"，不驗證引用內容是否真的在那份檔案裡。 | 六處引用改為 `[ad:component-dependency.md]`（對照 `:98`／`:103` 原文與 `decisions.md:240` 的修復紀錄）。若堅持要引用 `components.md` 本身，改寫成弱化語氣的推定句（例如「`components.md` 的 7 元件清單 C-1～C-7 未列 FR-H1，屬省略推定，非明文聲明」），不要用「已明記」這種宣稱逐字引號存在的措辭。修正時一併確認 `component-dependency.md` 未列入本 stage 的 `consumes:`，若要長期依賴它作為引用來源，應在四份文件中就近說明這是「同一份 application-design 產出下的姊妹檔」，而非讓讀者誤以為它是本 stage 的正式輸入。 |
| 2 | Minor | `business-rules.md:22-24`；引自 `unit-of-work.md` U-11 實作註記 | 「與全域 DoD 的 `validate_repo_contract.py` 有部分重疊——該腳本的 `REQUIRED_TEXT` 已鎖住 README 的關鍵字」的推論以現況核對：`scripts/validate_repo_contract.py` 目前 `REQUIRED_TEXT["README.md"]` 的兩個 tuple 分別是 `("Cloud-360","AWS","GCP","Azure","draw.io","Mobile Web",...)` 與 `("AI-DLC",)`（實測 `grep -n "README" scripts/validate_repo_contract.py` 並讀取兩處 tuple），**不含任何與「Project #16」或本單元新增段落相關的關鍵字**。現況的「重疊」只保障 README.md 既有內容不被整檔清空，並不保障 FR-H1 這段新文字未來被靜默刪除或改寫而不觸發 CI 紅燈——「已鎖住」這個宣稱對這段新文字而言尚未成立，是超前於現況的用詞。 | 建議在 U-11 的實作中，把一個穩定關鍵字（如 Project #16 的連結網址片段，或「Project #16」字面）併入既有 `REQUIRED_TEXT["README.md"]` 的其中一個 tuple——這仍是沿用同一機制、非「另設檢查」，「下游不需為此另設檢查」這句話在補上這一步之後才完全成立。 |

### Validation Tool Results

本 stage 未在 frontmatter 列出可執行的 validation script（`sensors:` 為 `required-sections`／`upstream-coverage`／`linter`／`type-check`，皆為 PostToolUse 階段自動觸發的 sensor，非本輪人工可另行呼叫的獨立工具）。以下為本輪人工逐項核對的結果，取代機械工具輸出：

| 檢查項 | 方式 | 結果 | 解讀 |
|---|---|---|---|
| CONDITIONAL 條件逐款比對 | 對照 stage frontmatter 的 `condition` 三分句與 `business-logic-model.md` 的判定表 | 三款皆為 ❌（無新資料模型／無複雜商業邏輯／規則已於 stories.md 定死為二元可判） | 判定成立，「應 skip」的結論站得住腳 |
| `report --result skipped` 的作用範圍 | 讀 `.claude/tools/aidlc-orchestrate.ts:4237-4302`，並核對 `aidlc-state.md` 中 `functional-design` 只有單一 checkbox（非逐單元） | 確認：`skip` 要求 `--stage` 精確等於 `Current Stage`（單一 slug），且 `for_each: unit-of-work` 的完成判準是跨全部單元彙總（`aidlc-state.ts` 的 `perUnit` 邏輯），無逐單元 skip 通道 | 「引擎無法逐單元 skip」的技術主張為真 |
| `unit-of-work.md` U-11 條目逐字核對 | 直接讀取 `unit-of-work.md:174-184` | `kind` 留空、理由「五類皆不合，收完整設計矩陣」、`複雜度 XS`、交付與驗證方式描述，皆與四份 functional-design 產出的引用逐字相符 | 「kind 留空是上游已知並接受的選擇」屬實 |
| `[US:S-11] AC 1／AC 2` 逐字核對 | 直接讀取 `stories.md:300-313` | AC 1／AC 2 文字、改寫理由段、persona P3→P2 修正段，皆與 `business-logic-model.md`／`business-rules.md`／`frontend-components.md` 的引用逐字相符 | 通過 |
| `[ad:components.md]` 引用核對 | `grep -in "FR-H1\|README" components.md` | 零命中；同一句逐字出現在 `component-dependency.md:98` | 對應 Finding #1 |
| `component-methods.md`／`services.md` 無對應項 | `grep -n "FR-H1\|README\|U-11" component-methods.md services.md` | 零命中，兩檔確實均無 U-11 相關條目 | 「無對應方法或服務」屬實 |
| 可算數字重算 | 逐條核對 AC 數（2）與產出檔數（現為 5：四份設計文件＋本輪的 `functional-design-questions.md`） | 相符 | 通過 |

### Summary

判定本身（應 skip、引擎無法逐單元 skip、四份產出非空洞佔位、`kind` 留空是上游已知選擇）逐項查證皆成立，且對 `aidlc-orchestrate.ts` 的技術主張經直接讀碼證實無誤。唯一但重複出現的問題是：四份設計文件用來支撐「本單元無元件／無方法／無服務」這個核心結論的引用，六處全部把出處標成 `[ad:components.md]`，但該逐字引號實際只存在於 `component-dependency.md`——而且這正是同一份上游 artifact 自己在 reviewer iteration 2 修復過的同型混淆，如今以「引錯檔名」的形式在下游重現。這是可機械核對、有明確修法的引用錯誤，不是架構判斷錯誤；但它是本單元全部四份文件共同的、唯一的實質內容支柱，且直接觸犯 `project.md` 已多次記載的「引用前必須逐字核對來源」規則，故列 Major 並依此判 NOT-READY。修法為六處改指向 `component-dependency.md` 並視需要在文中補一句說明其非本 stage 正式 `consumes` 對象；連同 Finding #2 的 `REQUIRED_TEXT` 措辭一併修正後，應可一輪過關。

## Review (Iteration 2)

**Verdict**: READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T16:11:20Z
**Iteration**: 2

### 逐項查證表

| # | Iteration 1 發現 | 處置 | 查證方式 | 結論 |
| --- | --- | --- | --- | --- |
| 1 | Major：四檔六處把逐字引文「FR-H1（README 指路）為單段文字，無元件」的出處標成 `[ad:components.md]`，實際只存在於 `component-dependency.md` | 四檔改為引用 `[ad:component-dependency.md]` | (a) 開 `component-dependency.md` 核對逐字引文是否確實在其中；(b) 逐檔（`business-logic-model.md`／`business-rules.md`／`domain-entities.md`／`frontend-components.md`）全文搜尋，確認不再殘留 `[ad:components.md]` 這個錯誤引用 | (a) **核對成立**：`component-dependency.md:98` 逐字為「**FR-H1**（README 指路）為單段文字，無元件。」，與四檔引文完全相符。(b) **四檔皆已改正**，未見殘留的 `[ad:components.md]` 誤引；其中 `frontend-components.md` 由原本兩處（`:11,27`）收斂為「與上游的對應」一處，`:11` 的「適用性判定」段落原本掛出處的句子改為純內部推理（無 props／無 state／無 API 整合點），追溯責任集中到檔尾一處——這是合理的重構而非漏改，唯一可查證的來源仍指向正確的 `component-dependency.md`。**判定：已修正**。但修正過程在 `business-logic-model.md` 留下一則措辭自相矛盾的殘留註記，見下方新發現 #1（Minor） |
| 2 | Minor：`business-rules.md:22-24` 稱 `validate_repo_contract.py` 的 `REQUIRED_TEXT` 「已鎖住 README 的關鍵字」，但實測該腳本對 `README.md` 要求的關鍵字與 Project #16／本次新增段落無關 | — | 重讀現行 `scripts/validate_repo_contract.py:88-98` 的 `REQUIRED_TEXT["README.md"]` 九個 tuple 元素（`Cloud-360`／`AWS`／`GCP`／`Azure`／`draw.io`／`Mobile Web`／`Cloud Security Posture`／`human approval gate`／`MCP & Skill Management`），並重讀 `business-rules.md:20-24` 現況 | **未修正**。`business-rules.md:20-24` 逐字仍是：「本單元與全域 DoD 的 `validate_repo_contract.py` 有部分重疊——該腳本的 `REQUIRED_TEXT` **已鎖住** README 的關鍵字。」與 iteration 1 引用完全相同。且核對結果確認：九個既有關鍵字確實不含任何與 Project #16 或 FR-H1 新增段落相關的字串，原判斷（「已鎖住」對這段新文字尚未成立）依然有效。**附帶說明**：此句字面上與 `unit-of-work.md:184` 的 U-11 實作註記逐字相同（「其 `REQUIRED_TEXT` 已鎖住 README 關鍵字」），即這個不準確的措辭**源自上游、已核可的 units-generation 產出**，本站是逐字沿用而非自創；依 `project.md` 的「標出不逕改已通過 reviewer 的上游產出」紀律，逐字沿用本身不算失分，但「未加註」使這個不準確措辭在本站原樣延續，仍是可歸屬本站的殘留缺口。Minor 不阻擋 READY，如實記載 |

### 新引入的問題

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
| --- | --- | --- | --- | --- |
| 1 | Minor | `business-logic-model.md`（「與上游的對應」段落末尾的 HTML 註記） | 修正 Major #1 時，在「與上游的對應」段落（已正確改為 `[ad:component-dependency.md]`）之後，多留了一則 HTML 註記：「更正標記見下方 Review 區塊 Finding #1：本節的 `[ad:component-dependency.md]` 引用經核對為誤植，逐字原句實際出自 `component-dependency.md:98`。本行原文維持，不回改，理由見 Review。」——此句字面自相矛盾：先說本節「`[ad:component-dependency.md]` 引用經核對為**誤植**」，緊接著卻說「逐字原句實際出自 `component-dependency.md:98`」，即該引用其實**正確**（本 Review 表列 #1 已重新核對確認）。緊鄰上方另有一段完整且措辭正確的更正說明（「> **引用來源已更正……** 本單元先前把……出處標為 `[ad:components.md]`，實測……零命中……」），這則 HTML 註記疑似是修正過程中的中間草稿殘留，把「原本錯誤的 `[ad:components.md]`」誤打成「現在正確的 `[ad:component-dependency.md]`」，內容與上方說明重複且方向相反，可能誤導之後的讀者以為現行引用仍有疑慮。不影響本檔正文的實際引用內容（已核對正確），故列 Minor。 | 移除該則 HTML 註記，或改寫為與上方藍字說明一致的措辭（例如：「（先前誤植為 `[ad:components.md]`，已於 reviewer iteration 1 Major 後更正為本行的 `[ad:component-dependency.md]`）」），避免同一事實在同一檔案內出現方向相反的兩種表述。 |

### Summary

Major #1（六處引用出處錯誤）本輪已確實修正：實地核對 `component-dependency.md:98` 逐字含該引文，四檔搜尋未見殘留的 `[ad:components.md]` 誤引，`frontend-components.md` 的收斂（兩處併為一處＋一處改寫為內部推理）為合理重構。Minor #2（`REQUIRED_TEXT` 「已鎖住」的用詞）本輪未修正，且查明其措辭實際承襲自已核可的 `unit-of-work.md` 上游文字，不阻擋 READY。本輪唯一新增的問題是 `business-logic-model.md` 修正 Major #1 時遺留的一則自相矛盾 HTML 註記，內容與其正上方措辭正確的更正說明方向相反，屬編輯殘留而非設計缺陷，列 Minor。零 Critical、零 Major、2 Minor，判 READY。
