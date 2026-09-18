# Wireframes — 帳號最後活動時間（稽核欄位）

<!-- Stage: rough-mockups（Ideation 1.6）· 低保真線框 · 來源標籤定義見 rough-mockups-questions.md 的 ## Sources。
     ASCII 線框依 stage-protocol.md 標準：僅基本 ASCII 字元；box 內每行**字元數**一致（桌面 72、小螢幕 34）。CJK 為寬字元，視覺寬度無法保證對齊，以字元數為準。 -->

## 上游輸入

- **intent-statement**（`../intent-capture/intent-statement.md`）：受益者（`Platform_Admin`、`Security_Reviewer`）與稽核目的。
- **scope-document**（`../scope-definition/scope-document.md`，Revision 1）：五項 Must 能力 — 本線框涵蓋 (b) 顯示、(c) 逾期標示、(e) 行動響應式卡片改造的呈現層。
- **intent-backlog**（`../scope-definition/intent-backlog.md`）：PU-2／PU-3／PU-5 的呈現需求。

## 設計決策摘要

| 決策 | 內容 | Source |
| --- | --- | --- |
| 欄位位置 | 插在「角色」之後、「操作」之前（資訊欄集中在左，操作欄在右） | [Q1] |
| 時間格式 | 絕對時間 `YYYY-MM-DD HH:MM`，稽核可直接抄錄比對 | [Q2] |
| 逾期標示 | 警示圖示（`(!)`) ＋時間值變色 — 非僅顏色傳達 | [Q3] |
| 空值呈現 | 破折號 `—`；可聚焦（focusable），聚焦／hover 顯示說明文字（機制決策 [Q4] [Q4a]；文案「本功能上線前無活動資料」為示例、未經 Q&A 決議，refined-mockups 另定） | [Q4] [Q4a] |
| 裝置底線 | WCAG 2.1 AA 全裝置；小螢幕卡片式佈局、桌面維持表格 | [Q5] [Q5a] |

## 桌面版 — 使用者管理頁（表格，加入新欄）

```
+----------------------------------------------------------------------+
|使用者管理 (h1)                                                            |
+----------------------------------------------------------------------+
|+-------+------+----------------+----------------------+------+------+|
|| 使用者   | 授權狀態 | 角色             | 最後活動時間               | 操作   | 啟用   ||
|+-------+------+----------------+----------------------+------+------+|
|| alice | 已核准  | Platform_Admin | 2026-08-03 14:52     | [調整] | [on] ||
|| bob   | 已核准  | Developer      | (!) 2026-04-01 09:10 | [調整] | [on] ||
|| carol | 已核准  | SRE            | —                    | [調整] | [on] ||
|+-------+------+----------------+----------------------+------+------+|
+----------------------------------------------------------------------+
```

<!-- Text fallback: 既有表格於「角色」與「操作」之間新增「最後活動時間」欄。正常值顯示絕對時間；逾期值前綴警示圖示且變色；無紀錄顯示可聚焦的破折號。 -->

- 列 1（alice）：正常態 — 絕對時間，一般字色。
- 列 2（bob）：**逾期態** — 時間值前綴警示圖示 `(!)` 並以警示色呈現；圖示帶文字替代（「超過 N 天未活動」），非僅顏色傳達 [Q3]。
- 列 3（carol）：**無紀錄態** — 破折號 `—`，可聚焦；聚焦或 hover 顯示說明文字（示例文案「本功能上線前無活動資料」，措辭未經 Q&A 決議，refined-mockups 另定）[Q4] [Q4a]。

**無障礙註記（桌面）**：頁標題 h1；landmark：header／main（表格在 main 內）；表格用語意化 table 標記、新欄 th 帶欄名；鍵盤入口：Tab 依「表頭 → 逐列互動元素（含可聚焦破折號）」順序；圖示與顏色皆附文字替代；對比 4.5:1。

## 小螢幕 — 卡片式佈局（PU-5）

```
+--------------------------------+
| 使用者管理 (h1)                     |
+--------------------------------+
| +----------------------------+ |
| | alice          [on]  [調整]  | |
| | 角色: Platform_Admin         | |
| | 授權: 已核准                    | |
| | 最後活動: 2026-08-03 14:52     | |
| +----------------------------+ |
| +----------------------------+ |
| | bob            [on]  [調整]  | |
| | 角色: Developer              | |
| | 授權: 已核准                    | |
| | 最後活動: (!) 2026-04-01 09:10 | |
| +----------------------------+ |
| +----------------------------+ |
| | carol          [on]  [調整]  | |
| | 角色: SRE                    | |
| | 授權: 已核准                    | |
| | 最後活動: —                    | |
| +----------------------------+ |
+--------------------------------+
```

<!-- Text fallback: 小螢幕以一帳號一卡片呈現：卡片首行為使用者名與啟用／操作控制，其下逐行列出角色、授權狀態、最後活動時間；逾期與無紀錄的標示規則與桌面一致。 -->

- 一帳號一卡片；卡片內欄位以「標籤: 值」逐行呈現，掃讀順序＝表格欄序。
- 逾期／無紀錄標示規則與桌面完全一致（同一組樣式語彙）[Q3] [Q4]。
- 既有操作（調整角色、啟停用）在卡片首行保留，觸控目標最小 44x44 [Q5]。

**無障礙註記（小螢幕）**：h1 同桌面；landmark：同桌面（header／main，卡片清單在 main 內）；卡片為 list 語意（每卡片一 listitem）；鍵盤入口：Tab 逐卡片、卡片內依視覺序；斷點以既有內容破版處為準（refined-mockups 定值）。

## 畫面五態

| 態 | 呈現 | Source |
| --- | --- | --- |
| 正常（有資料） | 上列線框 | [Q2] |
| 逾期 | `(!)` 圖示＋警示色＋文字替代 | [Q3] |
| 無紀錄（空值） | 可聚焦 `—` ＋說明 tooltip；不套逾期標示 | [Q4] [Q4a] [feas:Q2] |
| 載入中 | 新欄位以 skeleton 佔位（與既有頁面載入模式一致） | — |
| 錯誤 | 沿用既有頁面的清單載入錯誤呈現；新欄不單獨報錯 | — |

## Assumptions & Open Questions

- [assumption] 逾期門檻 N 未定，線框中逾期態以「N 天」佔位表達；N 於 requirements-analysis 定案後不影響版面結構 [intent:Q3]
- [assumption] 載入與錯誤態沿用既有頁面模式，本階段不重新設計；若既有頁面無 skeleton 慣例，於 refined-mockups 對齊 [Q5]
- [assumption] 卡片式佈局的響應式斷點值未定，以既有內容破版處為準，refined-mockups 定值 [Q5] [Q5a]

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-04T01:00:02Z
**Iteration:** 2

### 逐項核對（iteration 1 的四項 findings）

| # | Iteration 1 finding | 修正宣稱 | 核對方法 | 結果 |
| --- | --- | --- | --- | --- |
| 1 | （Major）ASCII box 每行字元數不一致 | 兩 box 重生，桌面 72 字元、小螢幕 34 字元／行 | 以 Python `len()`（Unicode 字元計數，非 byte 計數）逐行量測 `wireframes.md` 第 25–35 行（桌面）與第 49–70 行（小螢幕）；macOS 內建 `awk`（非 multibyte-aware）對含 CJK 的行回報字元數偏高（如 82、110），初看似不一致，但改以正確的 Unicode 字元計數複核後，桌面 box **11 行全數為 72 字元**、小螢幕 box **22 行全數為 34 字元**，與檔頭「以字元數為準」的註記相符 | **已解決** |
| 2 | （Major）user-flow.md 缺流程圖 | 新增 `## 核心流程圖` ASCII 流程圖＋文字 fallback，覆蓋三條 Flow 關鍵節點與匯流 | 讀取 `user-flow.md` 第 11–37 行；方塊＋箭頭圖含「登入→進入頁面→桌面／小螢幕分流（Flow 3）→判讀三態→稽核抄錄（Flow 1）／管理處置（Flow 2）→稽核結論／治理決策」，並於圖後緊接文字 fallback 段落 | **已解決** |
| 3 | （Minor）tooltip 文案誤掛已核可標籤 | 文案標明「示例、未經 Q&A 決議，refined-mockups 另定」，與 [Q4][Q4a] 機制決策分開 | 逐字核對 `rough-mockups-questions.md` Q4（Answer B：破折號＋hover 說明）與 Q4a（Answer A：需可聚焦、聚焦時顯示說明）；`wireframes.md` 第 19、42 行的括號結構已將「機制決策 [Q4][Q4a]」與「文案『本功能上線前無活動資料』為示例、未經決議」明確分句區隔，[Q4][Q4a] 僅覆蓋機制（可聚焦＋聚焦/hover 顯示），不覆蓋具體文案 | **已解決** |
| 4 | （Minor）小螢幕無障礙註記缺 landmark | 補「landmark：同桌面（header／main，卡片清單在 main 內）」 | 讀取 `wireframes.md` 第 79 行「無障礙註記（小螢幕）」，landmark 子句已存在且與桌面註記（第 44 行）的表述方式一致 | **已解決** |

四項修正逐一核實落地，且複核桌面／小螢幕兩個 box 的字元數時，額外驗證了「視覺對不齊但字元數一致」與檔頭免責聲明相符，未發現迴歸（新增內容未破壞既有欄位語意、上游引用、五態表或 Assumptions 清單的完整性；`required-sections`／`upstream-coverage` 兩個 sensor 覆蓋的必要條件仍成立）。

### 新 Finding（本輪覆查中發現，非原四項之列）

| # | Severity | Location | Finding | Recommendation |
| --- | --- | --- | --- | --- |
| 5 | Minor | wireframes.md Assumptions 第 94 行 | 「載入與錯誤態沿用既有頁面模式…若既有頁面無 skeleton 慣例，於 refined-mockups 對齊」掛 `[Q5]`；逐字核對 `rough-mockups-questions.md` Q5（無障礙與裝置支援底線：WCAG 2.1 AA＋行動響應式）後，該題選項未觸及載入態／skeleton 慣例，引用與主張內容不對應 | 移除該處 `[Q5]` 標籤，或改為不掛引用（該句本身已標記為 `[assumption]`，屬待確認事項而非已核可決策，移除不影響決策效力） |

此項不影響 verdict：該句本身已明確標記為 `[assumption]`（待確認的開放問題），並非包裝成已核可事實，且不涉及使用者可見的行為或驗收標準；屬引用精確度的可即改小瑕疵，不構成「無來源主張冒充事實」的 grounding 違規。

### Summary

Iteration 1 的兩項 Major 與兩項 Minor findings 均已用可檢核的方式修正並驗證落地：ASCII box 字元數經 Unicode 字元計數複核後桌面／小螢幕各自一致；user-flow.md 新增的核心流程圖以方塊＋箭頭涵蓋三條 Flow 的分流與匯流並附文字 fallback；tooltip 文案與機制決策的引用範圍已分句釐清；小螢幕無障礙註記補齊 landmark。本輪覆查另發現一項與原四項無關的 Minor 引用瑕疵（Finding 5），不足以阻擋 READY。判定：**READY** — 工程與 refined-mockups 階段可依此線框、流程圖與問題檔的既有決議直接展開，不需回頭確認。

## Review — Iteration 3（Freshness Re-check）

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-06T12:11:42Z
**Iteration:** 3
**Trigger**：`rough-mockups-questions.md`（本 stage produces[] 之一）於 iteration 2 READY（2026-08-04T01:00:02Z）後被編輯兩次，engine 的 freshness guard 不分辨改動實質性，一律使 review receipt 失效，須重新取得 fresh 審查方能通過 gate。

### 變動範圍核對

逐一核對兩次編輯的實際內容，確認範圍宣稱屬實：

| 檔案 | 是否變動 | 核對方法 | 結果 |
| --- | --- | --- | --- |
| `wireframes.md` | 否 | 覆查全文（含桌面／小螢幕兩個 ASCII box、畫面五態表、Assumptions 清單），逐行比對 iteration 2 Review 區段引用的行號與內容 | 與 iteration 2 審查時完全一致，未見任何新增、刪除或改寫 |
| `user-flow.md` | 否 | 覆查全文（核心流程圖、Flow 1–3、資訊架構備註、Assumptions 清單） | 與 iteration 2 審查時完全一致 |
| `rough-mockups-questions.md` | 是 | 檢視 `## Assumption Confirmation` 區段 | 新增內容僅限：(1) wireframes.md 第二條 assumption 的轉錄旁加註一句說明（見下方核對）、(2) 補上 `[Answer][Answer]: A. Accept assumptions（2026-08-04）` | 其餘題目（Q1–Q5、Q4a、Q5a）之答案與 iteration 2 審查時相同，未被觸碰 |

結論：本輪唯一的實質變動是 Assumption Confirmation 這一道 meta 問題被作答，其餘內容（含兩份設計 artifact 全部、questions 檔的題目與既有答案）均未變。

### 對抗式核對：Assumption Confirmation 的作答內容

**1. 轉錄的 5 條 assumption 是否與來源逐字相符？**

逐字比對 `rough-mockups-questions.md` 第 107–116 行的轉錄 vs. `wireframes.md` 第 93–95 行與 `user-flow.md` 第 82–83 行：

| # | 來源 | 轉錄是否逐字相符 | 備註 |
| --- | --- | --- | --- |
| 1 | wireframes.md 逾期門檻 N | 是 | 完全逐字 |
| 2 | wireframes.md 載入／錯誤態沿用既有模式 | **否** | 轉錄拿掉了來源仍保留的 `[Q5]` 標籤，換成一句加註「本條的 [Q5] 引用經 reviewer Finding 5 指認為不對應，refined-mockups 修訂時移除」 |
| 3 | wireframes.md 卡片式佈局斷點值 | 是 | 完全逐字（含 `[Q5] [Q5a]`） |
| 4 | user-flow.md 稽核僅讀取＋人工抄錄 | 是 | 完全逐字 |
| 5 | user-flow.md 逾期帳號後續處置為開放問題 | 是 | 完全逐字 |

第 2 條的加註本身查有實據 —— 內容與 `memory.md` 第 20 行的 Open questions 紀錄（iteration 2 Finding 5：「READY 後不回改…refined-mockups 修訂該檔時一併移除」）一致，不是憑空捏造；但它讓「使用者確認接受的文字」與「wireframes.md 現存的實際文字」不再逐字對應 —— wireframes.md 本體那一行仍原樣掛著 `[Q5]`（未修正），只有問題檔的轉錄把它拿掉並換成說明。單獨讀問題檔的人可能誤以為 wireframes.md 已經修正，需回頭比對來源才會發現尚未修正。判定：**Minor，不擋 READY** —— 不構成無來源主張（加註本身有據可查），也不改變已核可的決策內容，wireframes.md 的 `[assumption]` 標籤本身依然原樣保留（符合本題「接受不等於把 assumption 變成事實」的前提）。

**2. 「Accept assumptions」是否與 scope-document（Revision 1，含 PU-5）矛盾？**

逐條核對 5 項 assumption 對照 `scope-document.md` 與 `intent-backlog.md`：

| Assumption | 對照 | 結果 |
| --- | --- | --- |
| N 值未定 | scope-document「(c) 逾期未活動視覺標示」與其自身 Assumptions「N 於 requirements-analysis 定案為上線前置依賴」 | 一致，無矛盾 |
| 載入／錯誤態沿用既有模式 | 無對應 scope 條款約束呈現細節 | 不構成矛盾 |
| 卡片斷點值留 refined-mockups 定值 | intent-backlog PU-5「無障礙底線 WCAG 2.1 AA 全裝置適用」未鎖定斷點數值 | 一致，無矛盾 |
| 稽核僅讀取＋人工抄錄，不做匯出 | scope-document「未承諾」段：「稽核報表匯出…狀態為『未承諾』，未來要做需重新立項」 | 一致 —— 正確地表述為「未承諾」而非「排除」，未越界宣告匯出被排除 |
| 逾期帳號後續處置沿用既有操作，非本 feature 範圍 | scope-document In scope 四類能力（記錄／顯示／標示／權限開通）與 PU-5 均不含新治理操作 | 一致，無矛盾 |

未發現新的無來源主張，亦未發現與已核可 scope-document（Revision 1，含 PU-5）矛盾之處。

**3. 「Accept」而非「Convert to follow-up questions」是否遺漏了本應追問的項目？**

檢視 5 項 assumption 的性質：N 值與斷點值屬「留待下一階段（requirements-analysis／refined-mockups）定案」的已知延遲決策，非本 stage 職權範圍內可答；載入態、匯出範圍、逾期後續處置三項均已有上游 artifact（scope-document／既有頁面模式）可資佐證，非空白猜測。五項皆非「本 stage 若追問即可當場解決」的性質，選擇 A（接受，不轉為追問）與其性質相符，非規避提問。

### 額外覆核（本輪重新檢查，非沿用 iteration 2 結論）

獨立以 `len()`（Unicode 字元計數）重新量測 `wireframes.md` 桌面 box（第 25–35 行）與小螢幕 box（第 49–70 行），確認桌面 11 行皆 72 字元、小螢幕 22 行皆 34 字元 —— 與 iteration 2 的驗證結果一致，未發生迴歸。

另發現一項與本輪變動範圍**無關**、先前兩輪審查皆未提及的既有瑕疵：`rough-mockups-questions.md` 檔案開頭（H1 標題之前）有 5 行孤立的 `[Answer]: A / A / B / B / B`（第 1–5 行），未緊接在對應題目之下，不符合檔案自身第 9–10 行宣告的作答慣例（答案應填在該題選項之後）。經比對內容順序與 Q1–Q5 的既有作答（Q1=A 欄位插入位置、Q2=A 絕對時間、Q3=B 圖示＋顏色、Q4=B 破折號＋hover、Q5=B WCAG AA＋行動響應式），並回頭核對 wireframes.md／user-flow.md 的實際呈現，五題決策皆正確反映在兩份設計 artifact 中，內容本身無誤判風險；純屬版面歸屬問題（answer 脫離其題目）。判定：**Minor、資訊性、不擋 READY** —— 非本輪變動所致（本輪只動到 Assumption Confirmation 區段），不影響任何已核可決策的實質內容，建議下次觸碰此檔案時（如 refined-mockups 需要回頭核對題目時）順手歸位到各題之下。

### Summary

本輪 iteration 3 由 produces[] 檔案的 freshness 失效觸發，非因設計內容有缺陷。核對確認：`wireframes.md`／`user-flow.md` 自 iteration 2 READY 以來逐字未變（含 ASCII box 字元數重新驗證通過）；`rough-mockups-questions.md` 的唯一實質變動是 Assumption Confirmation 被作答「A. Accept assumptions」，5 項轉錄 assumption 對照來源與 scope-document（Revision 1，含 PU-5）逐條核對後未發現新的無來源主張或範圍矛盾。本輪另發現兩項與變動範圍無關的既有 Minor 瑕疵（assumption #2 轉錄與來源逐字不符、問題檔開頭孤立答案區塊未歸位到各題之下）——均不涉及無來源主張冒充事實、不改變已核可範圍、不影響工程可據以開發的判斷，故不阻擋 READY。判定：**READY**——engineering 與 refined-mockups 可依現有 wireframes、user-flow 與問題檔決議直接展開，無需就本輪變動再次確認。
