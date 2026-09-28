# Business Logic Model — U-9 自我測試 workflow

<!-- Stage: functional-design（Construction，per-unit）· Unit: U-9-selftest-workflow · kind: service -->

## 這個單元在做什麼

**它是本 intent 裡唯一會因為別的單元壞掉而紅燈的東西。**

其餘十一個單元交付的是機制；本單元交付的是「機制壞了會有人知道」。交付 `aidlc-sync-selftest.yml` ＋ fixture 集的驅動端。複雜度 **M**，驗證方式 **⑥workflow 執行期（CI 紅綠、突變驗證）**。

## 兩段式驗證（[ad:S-D]）

```
PR 觸及同步機制檔案（R-3 的 allowlist）
   │
   ├─► 第一段：fixture 驅動的 dry-run（無網路、無 I/O）
   │      ├─ U-1 的七條判定順序 ＋ get_field 四行為
   │      ├─ A-1 憑證樣式不外洩
   │      ├─ A-2 Block 序列化逐位元相同
   │      ├─ A-3 無漂移時不重寫（連續兩輪）
   │      ├─ A-6 路徑集合的兩個包含關係（靜態，跨檔）
   │      └─ R-1.2 靜態檢查：.lock.yml 的決定性 job 不含代理式引擎步驟
   │
   └─► 第二段：對獨立測試 Project 的端到端
          ├─ 建立本次執行專屬的測試 item
          ├─ 真實走一次 read → 判定 → write → 回讀
          ├─ R-1.3 憑證做範圍外寫入 → 斷言 403
          ├─ A-4 反向 PR 的 diff 不含 aidlc-state.md
          ├─ A-5 注入 PR 建立失敗 → 斷言分支被刪 ＋ 該次執行紅燈含 intent id/分支名
          └─ 清理（if: always()）
```

文字 fallback：先用純文字 fixture 把不需要網路的部分全部驗完，再對一個獨立的測試看板建一張本次專屬的卡，真實走一次讀寫回讀，最後不論成敗都刪掉那張卡。

**兩段的順序不是美學。** 第一段不需要憑證也不需要網路，跑得快且失敗訊息精確；第二段需要真實憑證與外部服務，慢且失敗原因可能是外部的。**第一段全綠才跑第二段**，否則一個 fixture 級的錯誤會以「端到端失敗」的面貌出現，把診斷成本推高一個量級。

## 為什麼六項斷言全部落在 Bolt 4 是一件需要被說出來的事

`domain-entities.md` 的表格列出六項繼承斷言。它們的**來源**分佈如下：

| 斷言 | 被斷言的行為在哪個 Bolt 上線 | 斷言在哪個 Bolt 上線 | 空窗 |
| --- | --- | --- | --- |
| A-1 | Bolt 1（U-1） | Bolt 4 | 3 個 Bolt |
| A-2 | Bolt 1（U-2） | Bolt 4 | 3 個 Bolt |
| A-3 | Bolt 1（U-2） | Bolt 4 | 3 個 Bolt |
| A-4 | Bolt 3（U-8） | Bolt 4 | 1 個 Bolt |
| A-5 | Bolt 3（U-8） | Bolt 4 | 1 個 Bolt |
| A-6 | Bolt 3（U-10b） | Bolt 4 | 1 個 Bolt |

**每一項單獨看都被接受過**——A-1 的空窗在 U-1 的 [Q2=A] 選項本文中逐字載明並經作答確認。**但「六項一起」是沒有任何一個決定看過的形狀**：deploy-on-merge 之下每個 Bolt 邊界都是一次真實部署，所以在 Bolt 1～3 期間，這個機制的六條防線一條都不在線上，而它每一次合併都會真的寫到看板。

**本站不據此改動 Bolt 順序**——那是 delivery-planning 已核可的決定，且改動它會動到三個真捆綁與一條排序邊。**本站做的是把這個累積事實寫下來並指派**：列為 **Bolt 1 gate 的揭露項**，讓核可 Bolt 1 的人在按下核可前看到「接下來三個 Bolt 沒有這六條防線」，而不是在 Bolt 4 才第一次看到這張表。

**這是揭露，不是異議。** 六項中沒有一項的空窗會造成不可逆後果：A-1 是資訊外洩風險（最重，但 U-1 的 output 落在 workflow log 而非公開產物）、A-2／A-3 是雜訊、A-4／A-5／A-6 的被保護行為在 Bolt 3 才存在。（A-5 的內容已於 reviewer iteration 2 改寫——先前指派給 U-7 的那一半因目標狀態構造上不可達而撤回，見 `domain-entities.md`。）

## 上游對這支 workflow 的既有記載，與本檔的差異

| 項 | [ad:services.md] S-D／[ad:components.md] 對照表 | 本檔 |
| --- | --- | --- |
| 觸發 | `pull_request`，僅當同步相關路徑變動 | 相同（R-3 把「同步相關路徑」寫成具體 allowlist） |
| 第一段 | 純文字 fixture 驅動 **C-1／C-2** 的 dry-run，不發任何 API 寫入請求 | **擴張至 C-6**（A-2／A-3），理由見 `domain-entities.md` |
| 第二段 | 對獨立測試 Project 驅動 **C-3** 的端到端寫入讀回 | **擴張至 C-4**（A-4／A-5） |
| 失敗語意 | **真閘門**，斷言失敗即 CI 紅燈 | 相同 |
| 突變驗證 | **AC 本身的一部分**，非另立的元層次 AC | 相同（R-1 三條） |

**兩處擴張是本 stage 的路由決定造成的，時間上晚於 application-design**，須讀成新增而非矛盾。其餘四項逐字沿用。

## 錯誤處理

| 情形 | 行為 |
| --- | --- |
| 第一段任一斷言失敗 | **紅燈，不跑第二段**。訊息含預期與實得（R-1.1） |
| 第二段建立測試 item 失敗 | 紅燈。這通常代表憑證或測試 Project 有問題，訊息須指出是哪一個 |
| 第二段斷言失敗 | 紅燈。**清理仍執行**（R-4） |
| 清理失敗 | **紅燈**，且訊息須含殘留 item 的識別資訊——留一張卡在測試看板上而無人知情，會讓下一次執行假紅燈 |

## 邊界情形

| 情形 | 行為 | 依據 |
| --- | --- | --- |
| 反向 PR（只改 `sync-state.json`） | **不觸發本單元** | R-3 的 allowlist 不含該路徑 |
| 只改 fixture 不改機制 | **觸發**（fixture 在 allowlist 內） | 改壞 fixture 等於改壞斷言 |
| 改了 `.md` 未重編 `.lock.yml` | R-1.2 的靜態檢查讀 `.lock.yml`，**看到的是舊的** | NFR-M1 的已知漂移風險；本單元不解決它，收斂落點見 OQ-4 |
| 獨立測試 Project 不存在 | 第二段失敗 | 外部依賴，見 `domain-entities.md` 的待確認項 |

## 與上游的對應

[ad:S-D] 的兩段式驗證、[ad:ADR-A3] 的回讀不符增生引自 `application-design`；本單元的擁有範圍、交付物、完成判準與測試 item 危害引自 [ug:unit-of-work.md] 的 U-9；Bolt 歸屬、真捆綁與排序邊引自 `delivery-planning/bolt-plan.md` 與 `unit-of-work-dependency.md`；六項繼承斷言與其原始接受紀錄引自 U-1、U-2、U-8、U-10b 的對應 artifact；A-5 的拆分與 U-7 的指派見本單元 `domain-entities.md`；R-1～R-5 見本單元 `business-rules.md`；NFR-M1 與 OQ-4 引自 `requirements.md`；deploy-on-merge 之下每個 Bolt 邊界即一次真實部署引自 `project.md ## Deployment`；S-D 的兩段生命週期、失敗語意與 [Q4=A] 的獨立測試 Project 理由引自 [ad:services.md]；`aidlc-sync-selftest.yml` 的元件職掌與四支 workflow 的觸發對照引自 [ad:components.md]；`render`／`content_hash` 的純函式性質與 fixture record 不進 registry 的選取邊界引自 [ad:component-methods.md]；本單元擁有 [US:S-10] 全部 AC 且僅此一則故事引自 [ug:unit-of-work-story-map.md]。

## Review

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T13:55:39Z
**Iteration**: 1

### 審查範圍與工具限制（誠實記載）

本輪 dispatch 要求審查全部 12 個單元（38 檔）的 functional-design 產出，理由是本 stage 對每個單元皆 `gate: false`，這是唯一一次 reviewer pass。但實際執行時，讀取範圍被鎖在 U-9 本身，加上「僅限本單元設計已具名指向的整合點」的 spot-check 例外——凡是 U-9 自己的產出（或本 dispatch 提示）已具名引用的上游檔案（如 U-1／U-2／U-4／U-6／U-7／U-8／U-10b／U-11 的特定檔）可個別開啟，但跨單元的全文搜尋、目錄列舉一律被擋，包含對框架自身 stage 定義檔的讀取（因路徑片段誤觸同一條規則）。

**後果**：orchestrator 要求的第 4 項核對（六項繼承斷言是否真的窮舉）無法用全庫搜尋驗證。本輪只能核對六項各自具名的來源檔（U-1 安全需求檔、U-2 技術選型與規則檔、U-8 規則與可靠性需求檔、U-10b 技術選型檔）與另外可讀到的 U-4／U-5／U-6／U-7／U-11 全部 functional-design 產出，未能讀取 U-3、U-10a 的任一檔案（未被列入本輪的具名整合點）。在已讀範圍內未發現第七項遺漏的「落點：U-9」路由，但不能排除 U-3（本單元第二段驅動的元件，複雜度 L）或 U-10a 藏有未具名指向 U-9 的斷言。此為驗證缺口而非否定性結論，如實記載。

### Findings

| # | 嚴重度 | 檔案:行 | 問題 | 建議 |
|---|---|---|---|---|
| 1 | Critical | 本檔 A-5 列；U-8 業務邏輯檔第 57、64 行；U-8 業務規則檔第 34-35 行；U-4 領域實體檔（「誰寫、何時清空由 U-8 與 U-6 決定」句） | `sync-state.json` 的 `pending_reverse` 欄位沒有任何單元定義清除時機。U-4 明文把「何時清空」指派給 U-8 與 U-6（原句：「本單元只負責讀寫與保存它，不解讀其內容（誰寫、何時清空由 U-8 與 U-6 決定）」），但逐檔核對 U-8 業務邏輯檔／業務規則檔全文，只找到「寫入」（R-1.3）與「恢復覆寫」（R-3.3，針對的是 `Config.reverse_pending`——一個由 U-6 每輪從開啟中 PR 的 diff 路徑即時算出的獨立集合，與 `sync-state.json` 的 `pending_reverse` 欄位無關），沒有任何一處把 `pending_reverse` 寫回 `null`。這造成兩個可驗證的失效：(a) U-8 自己的邊界情形表把「同一 intent 已有開啟中的反向 PR，又被改一次」的防重複開 PR 判斷定義為「`pending_reverse` 非空即代表已有未處理紀錄」——若該欄位永不歸零，該 intent 在第一次反向 PR 之後，往後所有真實的人為改動都會被判定為「已有未處理紀錄」而永遠不開新 PR，等同 U-8 對每個 intent 只能生效一次。(b) 本檔 A-5 指派 U-7 增設「偵測 `pending_reverse` 非空卻無對應開啟中 PR」的清單——但若正常合併／關閉後 `pending_reverse` 本來就不會被清空，這個偵測會在每一次成功的反向同步之後都觸發，無法區分「正常已解決」與「E-1 的原子性失敗」，使 A-5 第二半本身不可行。 | 在 U-8 或 U-6 補一條規則：PR 合併或關閉後（`Config.reverse_pending` 的來源本來就是即時查詢，可在同一次查詢中一併判定），把該 intent 的 `pending_reverse` 寫回 `null`（走 C-4 `write_sync_state`）。修正後 A-5 第二半的偵測才有意義；並回頭確認 R-1.3 的防重複判斷邏輯正確。 |
| 2 | Major | 本檔（`domain-entities.md`）第 13 行；來源實際位置 U-2 業務規則檔第 18-29 行（R-2 群，非 R-1 群） | A-3 列引用來源寫「U-2 `business-rules.md` R-1 群的註」，但該註實際位於 R-2 群（標題「R-2 群：雜湊」），具體是 R-2.3 的說明段。且對「落點更正」的敘述失準：本檔寫「該註寫『在 U-6 的自我測試中』」，暗示原文只指向 U-6、需要本站更正為 U-9；但 U-2 的實際原文是「……但那是 U-6／U-9 的落點，本站只標出」——U-9 本來就已經在來源清單內，並非本站發現的新落點。本輪修正的結論（承接方落在 U-9）沒有錯，但「來源在哪」與「本站修正了什麼」兩點的具體描述都與可核對的原文不符，違反本專案已多次記載的「掛來源標籤前須逐字核對原文，不得憑印象引用」紀律。 | 修正引用為「U-2 `business-rules.md` R-2 群（R-2.3 的說明）」；「落點更正」段落改寫為如實反映 U-2 原文已將 U-9 列為候選落點之一，本站是確認並承接而非發現並更正。 |
| 3 | Major | U-9 整個 `functional-design/` 目錄（無 `functional-design-questions.md`）；對照 U-6、U-8 各自的 `functional-design-questions.md` | U-9 是本輪可核對的單元中唯一完全沒有 `functional-design-questions.md` 的一個（已用 `find` 確認 U-9 的 `functional-design/` 只有三份最終產出）。對照組：U-6 與 U-8 都有此檔，且兩者的「本站裁定（未經人工提問）」段落都以獨立小節呈現、逐項附理由、並以 `[Answer]: 本站裁定，非人工裁決` 加上以 `date -u` 讀出的時間戳明確揭露「這不是人工答案」（U-6 額外記載「使用者中止提問並指示繼續」這個真實授權事件）。U-9 的六項繼承斷言逐項判定與 A-5 兩半拆分是本輪 dispatch 明確要求審查的「本站裁定」項目之一，但這兩項判斷只是直接寫進 `domain-entities.md` 的表格與段落裡，沒有比照 U-6／U-8 的揭露格式（獨立問答檔、`[Answer]` tag、時間戳、CONDITIONAL 適用性判定）。這使一個只讀 U-9 產出、不知道 U-6 曾發生「使用者中止提問」事件的人，無法從 U-9 自己的 artifact 分辨這些判斷是已核可的上游事實，還是 U-9 單方面的架構判斷——而這正是本輪 dispatch 要求重點檢查的東西。 | 比照 U-6／U-8 的形狀，為 U-9 補一份 `functional-design-questions.md`：列出 CONDITIONAL 適用性判定、六項繼承斷言判定與 A-5 拆分的 `[Answer]: 本站裁定，非人工裁決` 揭露段（含 `date -u` 時間戳），使三個單元的自我裁決留下同等可稽核的紀錄形狀。 |
| 4 | Minor | 本單元 `business-rules.md` 章節順序 | 規則群組標題順序為 R-1、R-2、R-3、R-4、R-6、R-5（已用 `grep '^## R-'` 確認：R-6 在 R-5 之前）。純編號順序問題，不影響規則本身的正確性或可判定性，但下一個編輯此檔的人若依編號插入新規則容易插錯位置。 | 把 R-6（S-10 全部 AC 歸屬）與 R-5（本單元不擁有的部分）互換順序，或把 R-6 重新編號以維持遞增。 |

### 對 lead 自我批評的查證

**U-9 安全需求檔的 Q-1（R-1.3 的 403 斷言在組織層 Projects 授權下恆真）：查證後成立，處置得當，非過度謹慎的假警報。** 逐一核對 `requirements.md` NFR-S1（經 ADR-0014 更正為「組織層 Projects 讀寫 ＋ 用途受限的 repo 內容寫入 ＋ Issues 寫入」三項）與 application-design 決策檔的 ADR-A2 憑證模型，確認「組織層」授權字面上涵蓋該組織下所有 Project（含測試 Project），R-1.3 若照組織層憑證實作，確實沒有任何組織內 Project 是範圍外的——這條斷言在此授權模型下永遠不會失敗。Q-1 依 `project.md` 的既有教訓（恆真 AC 應改寫而非刪除）把它標為缺口、指派 units-generation 的 U-9 完成判準第 3 條、確認人定為 Bolt 0 gate，且已核對指派目標非 CONDITIONAL、無跳過風險。本站在 U-9 的其餘五項斷言（A-1～A-6 對應的 R-1.1／R-1.2／R-3／R-4）中未發現第二個同型恆真斷言——皆為可真實失敗的行為斷言。

### 其餘核對（無新增問題）

- **U-8 的 E-1／E-2**：與 U-8 自己的 `functional-design-questions.md` 裁定內容逐字一致；E-1 對 `pending_reverse` 欄位的指派已確認落在 U-4 領域實體檔（見上方 Critical #1，欄位本身存在且已定案，缺陷是清除時機而非欄位本身）；E-2（一 intent 一 PR）未與任何已核可上游矛盾，且確實把 CAP-11 的 over-suppression 風險嚴重度從「全域誤暫停」降為「單一 intent 未暫停」，理由站得住。
- **branch 命名一致性**（U-6 D-1、U-8、U-10b 三處）：U-8 技術選型檔對 U-6 D-1 原文「`aidlc-sync/reverse/<date>`（無 intent_id）」的引用，經比對 U-6 `functional-design-questions.md`（逐字：「裁定：分支一律 `aidlc-sync/reverse/<date>`，且掛 label `aidlc-sync-reverse`」）準確無誤；U-8 加入 `<intent_id>` 的理由（E-2 的必要後果）成立；U-10b 技術選型檔明確記載「不採用 `branches-ignore`」並說明與 D-1 理由（非裁定）的落差、指派 PRE-1 實測——三處一致且落差已被誠實揭露，非缺陷。
- **U-8 承載形式（純 Actions vs gh-aw）在 fd 與 nfr 兩處**：業務邏輯檔未明寫承載形式，技術選型檔明確定案純 Actions 兩檔拆分並主動更正「先前寫成 gh-aw」的錯誤、說明與 ADR-0013 §3 承載位置對照表的落差來源（收斂發生在 U-6，非本單元）。兩處不矛盾。
- **U-9 對元件範圍擴張的宣稱**：核對 application-design 元件清單檔的 workflow 對照表原文「以 fixture 驅動 C-1／C-2；對獨立測試 Project 驅動 C-3」——確認上游只記載 C-1/C-2/C-3，U-9 主張的 C-6（A-2/A-3）、C-4（A-4/A-5）擴張確實不在此列。時序論證（四項擴張皆源自 construction 階段的 per-unit 設計，時間晚於 application-design）核對 U-2 業務規則檔／技術選型檔、U-8 可靠性需求檔、U-10b 技術選型檔的實際內容，四處的路由決定確實都發生在這些 construction 階段文件中。宣稱成立。
- **U-11-readme-pointer**：「若可逐單元 skip 本單元應被 skip」的判定附完整的 condition 逐項對照表（New data models／Complex business logic／Business rules need design／Skip if simple logic changes 四款皆有理由），三份產出各自都有 ≥2 個 H2 段落且非空洞重複——是判定加簡短內容，不是空白佔位符。

### Summary

一個 Critical：`pending_reverse` 欄位在 U-4／U-6／U-8 任何一處都沒有定義清除時機，這既讓 U-8 自己的防重複開 PR 判斷在第一次使用後失效，也讓本檔（U-9）自己提案指派 U-7 的 A-5 偵測機制在設計上就無法達成其目的——這是一個橫跨三個已核可單元、會在實作或執行期造成真實失敗的缺口。加上兩個 Major（A-3 的來源引用有可核對的錯誤、且本檔缺少對照組單元都具備的自我裁決揭露格式），依規則已達 NOT-READY 門檻。六項繼承斷言的逐項判定、A-5 拆分、U-8 的 E-1／E-2、branch 命名三處一致性、元件範圍擴張宣稱、U-11 的適用性判定、以及 Q-1 的恆真斷言自我批評，查證後全部站得住，不需修改。

## Review (Iteration 2 — 驗證輪)

**Verdict**: NOT-READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T14:17:15Z
**Iteration**: 2

### 四項修正的查證

| # | 原發現 | 修正是否成立 | 說明 |
|---|---|---|---|
| 1 | Critical — `pending_reverse` 沒有清除時機 | **部分成立**——(a) 防重複開 PR 的修正成立；(b) 清除規則的修正**不成立**，且暴露一個新的 Critical（見下方「新引入的問題」） | (a) U-8 `business-rules.md` R-6.1（第 30 行）改為即時查詢 label `aidlc-sync-reverse` 的開啟中 PR，**不讀 `pending_reverse`**，故此判斷不再受欄位陳舊影響。與 U-6 `business-rules.md` R-2.1（「以 label `aidlc-sync-reverse` 列出開啟中的 PR（一次查詢）」）比對後**無重複查詢、無語意衝突**——兩者是不同觸發（U-6：push/PR 事件；U-8：排程）的獨立 workflow run，各自查一次，讀的是同一份 GitHub 資料但互不依賴彼此的查詢結果，也不共享任何可變狀態。U-8 R-6.1 與同檔 R-6.2（「每輪開始時」的對帳）在**同一輪**內確實會對重疊的「這個 intent 有沒有開啟中 PR」做兩次查詢，但這是防禦性重複（R-6.2 是每輪一次的整批對帳、R-6.1 是開 PR 前的最後把關），不是相沖突的兩個判斷，只達 Minor 等級的效率備註，不影響正確性。(b) 見下方新引入的 Critical——R-6.2 的「已關閉」分支與 R-6.3 整條規則所描述的狀態，依 `commit_and_push` 的實際寫入機制推導，**構造上不可能被觀察到**，「本項才有可實作的定義」（`domain-entities.md:24`）這句話不成立。已重讀 U-8 `business-logic-model.md` 錯誤處理表（第 56、59、61 行）與 `business-rules.md` R-6 群陳舊視窗論證（第 36 行）——**陳舊視窗論證本身的前提（「PR 合併後」pending_reverse 才變舊值）與下方新發現互相印證，只是原作者沒有把它推到「所以 R-6.3 打不到」這一步**。 |
| 2 | Major — A-3 來源引用錯誤（誤植為 U-2 R-1 群，且把「確認」寫成「更正」） | **成立** | 已直接開 `aidlc/.../U-2-managed-block/functional-design/business-rules.md` 核對原文（第 18-29 行，R-2 群「雜湊」，R-2.3 之下的說明段第 29 行逐字：「……但那是 U-6／U-9 的落點，本站只標出」）。`domain-entities.md`（第 13、18 行）現在的引用「U-2 `business-rules.md` R-2 群（R-2.3 的說明段）」與「U-9 本來就在候選清單內，本站是確認並承接，不是發現並更正」**與原文逐字相符**。 |
| 3 | Major — U-9 缺 `functional-design-questions.md` | **成立** | 檔案已建立（`functional-design/functional-design-questions.md`），CONDITIONAL 四款判定表、三項「本站裁定」（E-3／E-4／E-5，逐項附理由）與 Revision 段落齊備，格式與揭露深度比對 U-6／U-8 同名檔一致。三個 `[Answer]: 本站裁定，非人工裁決` 皆帶 `date -u` 時間戳 `2026-08-29T14:01:39Z`——已用 `TZ=UTC stat` 核對檔案 mtime，**逐秒相符**；並在 audit shard（`audit/jiangzhengdaodemacbook-pro-local-82da74e002f9.md` 第 16750-16878 行附近）找到同一分鐘內連續的 `SENSOR_FIRED`／`SENSOR_PASSED` 事件，涵蓋 U-8 `business-rules.md`／`domain-entities.md`／`functional-design-questions.md` 的編輯，與本檔時間戳同一次編輯批次一致。**非造假**。 |
| 4 | Minor — R-6 排在 R-5 之前 | **成立** | 已重讀 `business-rules.md` 全文，章節順序現為 R-1、R-2、R-3、R-4、R-5、R-6，遞增。 |

### 補做的窮舉核對（U-3 / U-10a）

依 orchestrator 指示自行查證，不採信 lead 的 grep 結論。實測結果：

- **U-3-board-client**：直接開啟並通讀 `functional-design/` 全部四檔（`business-logic-model.md`、`business-rules.md`、`domain-entities.md`、`functional-design-questions.md`）與 `nfr-requirements/` 中可讀到的 `security-requirements.md`、`tech-stack-decisions.md`（`reliability-requirements.md`／`performance-requirements.md`／`scalability-requirements.md` 三檔被 reviewer 讀取範圍擋下，無法確認是否存在或內容，如實記載為未覆蓋而非「已查無」）。**六檔內文完整讀過，無一處出現「U-9」「selftest」「自我測試」或指向本單元的落點字樣**。U-3 的複雜度 L、承載 Projects v2 六個方法，是本輪指示重點懷疑的對象，但實測後未發現漏接的路由。
- **U-10a-ci-writeback-exclusion**：`functional-design/` 目錄下四個慣用檔名（`business-logic-model.md`、`business-rules.md`、`domain-entities.md`、`functional-design-questions.md`）**全數被讀取範圍擋下**，而 `nfr-requirements/tech-stack-decisions.md` 與 `nfr-requirements/security-requirements.md` 可讀、其餘三份 nfr 檔同樣被擋。對照 `unit-of-work.md` 對 U-10a 的定義（`kind: packaging`、複雜度 **XS**、「建置與觸發設定，非新行為」）與 CONDITIONAL 判定慣例（U-11 的 `functional-design-questions.md` 逐款附理由後仍判定 EXECUTE），**較可能的解讀是 U-10a 的 functional-design 被判定不適用而整段 SKIP**，而非「檔案存在但這輪剛好沒被排進 exempt list」——因為若檔案存在，依 U-3／U-8／U-9 的先例應與其 nfr-requirements 一併被排入 exempt。此為讀取範圍限制下的推論而非直接證據，**如實記載為未完全確認**，但可讀到的兩份 nfr 檔全文皆無「U-9」「selftest」「落點」字樣。
- **結論**：在讀取範圍允許的部分（U-3 全部 functional-design ＋ 兩份 nfr；U-10a 兩份 nfr）沒有發現任何指向 U-9 的未具名路由，六項繼承斷言維持窮舉。U-10a 的 functional-design 四檔與 U-3 的三份 nfr 檔仍是本輪工具限制下的**驗證缺口**，不是「已確認排除」——如實記載，不代為結案。

### 新引入的問題

**新增 1 項 Critical（由本輪修正暴露，非新的設計錯誤——原機制早已如此，只是本輪新增的 R-6.2／R-6.3 才把它的後果變成一條會被依賴的規則）：**

**R-6.3（以及 R-6.2 的「已關閉」分支）描述的狀態，依 `pending_reverse` 實際的寫入機制，構造上不可觀察，使 R-6.3 整條規則與 A-5 第二半指派給 U-7 的偵測都是打不到目標的空規則。**

推導鏈（每一步都可回頭核對）：

1. `pending_reverse` 的**設定**（R-1.3「寫 `pending_reverse` 並開 PR」）不是直接寫進 `ut`：U-8 `business-rules.md` R-4c（第 93-96 行）明列本單元對 `write_sync_state`／`commit_and_push` 的用法——`commit_and_push` 的 `branch` 參數是**新建的反向分支** `aidlc-sync/reverse/<intent_id>-<date>`，且第 96 行明白承認這是「對 C-4 契約的一個**特殊用法**」，因為 [ad:component-methods.md]（`aidlc/.../application-design/component-methods.md:106`）與 U-4 `domain-entities.md` 對 `commit_and_push` 的標準定義是「**只推觸發分支**」。也就是說，設定 `pending_reverse` 的那個 commit，落在**反向分支**上，不落在 `ut` 上。
2. 這與 E-1 的敘述完全吻合：U-8 `business-logic-model.md` 第 38 行「**PR 的 diff 因此結構上只含該檔**」——若 `pending_reverse` 是先直接寫進 `ut` 再另開分支，這個分支對 `ut` 的 diff 會是空的（沒有東西可審），與「PR 的 diff 只含該檔」（暗示非空、恰有一個變更）矛盾。E-1 的敘述只有在「`pending_reverse` 的變更本身就是 PR 的 payload」下才成立。
3. 因此，`pending_reverse` 要成為 `ut` 上可被讀到的非 `null` 值，**唯一路徑是這個 PR 被合併**（分支的 commit 併入 `ut`）。這與 R-6 群自己的陳述互相印證——`business-rules.md` 第 36 行的陳舊視窗論證寫的正是「**PR 合併後**到下一次執行之間，`pending_reverse` 仍是舊值」，即隱含承認了「`pending_reverse` 變成非 `null`」這件事本身是**由合併觸發**的。
4. 再看 `business-logic-model.md` 第 61 行的原子性規則：「PR 建立失敗時該 commit 不得留在任何分支上（分支未推送或推送後刪除）」——若 PR 開不成，規則要求連分支帶 commit 一起刪掉，`ut` 從頭到尾沒被改過。**即使這道回滾本身失敗**（孤兒分支殘留），孤兒分支仍是未合併狀態，不影響 `ut`。
5. 綜合 1–4：`pending_reverse` 在 `ut` 上非 `null`，若且唯若**曾經有一個反向 PR 合併過**。反推：
   - R-6.3「無開啟中、也**從未有過任何反向 PR**（開啟或關閉）」——若這是真的（intent 從未有過任何 PR），依上述推導 `pending_reverse` 在 `ut` 上根本不可能是非 `null`，R-6.3 的觸發條件（`pending_reverse` 非 `null` 且從未有過 PR）**兩個子句自相矛盾**，這條規則永遠不會為真。`domain-entities.md` 第 24 行「本項才有可實作的定義」與 `business-rules.md` 第 32 行「這正是 E-1 的原子性失敗（`pending_reverse` 已寫但 PR 沒開成）」描述的正是「寫已生效但 PR 沒開成」——但依第 1-4 步，寫**只透過** PR 分支生效，PR 沒開成（或開成但未合併）時寫根本沒有落地，不存在「已寫但沒有 PR」這個可觀察狀態。
   - R-6.2「無開啟中但有**已關閉**（未合併）」的分支同理不可達——已關閉未合併的 PR，其 commit 從未進入 `ut`，不會是 `pending_reverse` 非 `null` 的成因；若當下 `pending_reverse` 恰好非 `null`，那必然是**另一個更早、已合併**的 PR 留下的舊值，跟這個「已關閉」的 PR 無關，R-6.2 把兩者混為一談會誤判成因（雖然清除動作本身無害，因為確實該清）。R-6.2 真正可靠、且會被觸發的只有「已合併」這個分支。
6. **後果**：U-9 `domain-entities.md`（第 20-35 行）A-5 第二半「執行期不變量的偵測」指派給 U-7、且聲稱「這正是 reviewer iteration 1 之後才成立」的可實作定義（第 24 行），實際上是把一個構造上永遠不會為真的條件指派給 U-7 的 `ReconcileReport` 去偵測——U-7 依此規格實作出來的欄位會是一段永遠不觸發的死碼，卻在文件上呈現為「已解決」。這使 iteration 1 原始 Critical 的 (b) 半邊（A-5 指派給 U-7 的偵測在設計上無法達成目的）**實質上仍未解決**，只是換了一種不會被表面核對發現的方式維持未解決。

**建議處置**（供 lead 參考，非本輪代為修改）：
- 若 E-1 的「反向分支承載寫入」機制維持不變，R-6.3 與 R-6.2 的「已關閉」分支應**整條移除**，因為它們描述的狀態不可達；E-1 的原子性失敗（commit 未推送成功、或推送後 PR 開不成）若要能被偵測，偵測點必須改到**本次執行內**（例如 U-8 自己在 `commit_and_push` 回傳與「開 PR」呼叫之間，若後者失敗且回滾也失敗，當場记入本次執行的錯誤報告並紅燈——而不是留給下一輪或 U-7 去讀一個永遠不會被設起來的欄位）。
- 或者，若確實需要「跨輪、可由 U-7 每日對帳偵測」的 E-1 安全網，`pending_reverse` 的**設定**必須改為不經過 PR 合併就能落地（例如比照 R-6.2 的清除動作，用標準 `commit_and_push`「只推觸發分支」直接寫 `ut`，PR 分支則只承載給人審閱的內容）——但這會改變 E-1「PR 的 diff 結構上只含該檔」這個已被上游認可的設計特性，屬於需要重新過 reviewer 的實質變更，不是本輪可以就地補的小修。
- 兩條路都不是本檔（U-9）能單方面決定的——如同 iteration 1 原 Critical 的處置原則，這裡同樣是**標出缺口、寫明後果、指派落點**，不逕自改寫已核可的 U-8／U-9 產出。落點應回 U-8（E-1 的原子性語意）與 U-9（A-5 第二半的指派對象），確認人建議定為 Bolt 3 gate（U-8 上線時）而非目前寫的 Bolt 2 gate，因為問題的根源在 U-8 自己的寫入機制，U-7（Bolt 2）不是能解的一方。

**其餘檢查（無新增問題）**：R-6.1 的即時查詢設計本身正確、且是這四項修正中唯一站得住的一半；finding #2／#3／#4 的修正逐一核對後與原文、既有格式、審計紀錄皆相符，未發現修正動作本身引入的其他新問題。

## Review (Iteration 3 — R-6 改寫驗證)

**Verdict**: READY
**Reviewer**: aidlc-architecture-reviewer-agent
**Date**: 2026-08-29T14:30:46Z
**Iteration**: 3

### 範圍聲明

本輪為極窄驗證輪，只查 iteration 2 判定的新 Critical（R-6.3／R-6.2「已關閉」分支構造上不可觀察）在 lead 修法後是否正確、跨檔是否傳播完整、修法有無新引入問題。不重審 iteration 1／2 已結案項目。讀取範圍：U-9 本身全部產出、`requirements.md`、`component-methods.md`（皆可讀，屬 dispatch 具名的整合點／已通過的 inception 契約）；U-8 全部 `functional-design/` 與 `nfr-requirements/` 三檔、U-4 `domain-entities.md`、U-6 全部 `functional-design/`（`business-rules.md`／`business-logic-model.md`／`domain-entities.md`）、U-7 同名三檔皆可讀。U-7 的 `functional-design-questions.md` 與 `nfr-requirements/*` 被讀取範圍擋下，如實記載為未覆蓋（見下方 Q2）。

### Q1 R-6 群的正確性

**R-6.0 推導鏈——四步全部可回頭核對，成立。**
- 第 1 步（`business-rules.md:25`）引用 R-4c（`business-rules.md:110`「`commit_and_push(...)` | C-4 | 推反向分支；`branch` 為 `aidlc-sync/reverse/...` 而非觸發分支」）：已對照 R-4c 全文（`business-rules.md:102-114`），與描述一致——`branch` 參數確實是新建反向分支，非觸發分支。
- 第 2 步（`business-rules.md:26`）引用 E-1（`business-logic-model.md:34`「PR 的 diff 因此結構上只含該檔」）：逐字核對相符。
- 第 3、4 步（`business-rules.md:27-28`）是第 1、2 步的直接邏輯推論（寫入只在反向分支上發生 ⇒ 進 `ut` 唯一路徑是該 PR 被合併；PR 開不成、或回滾刪除分支也失敗，孤兒分支仍是未合併狀態，`ut` 全程未變），推論本身站得住，無跳步。

**R-6.2「沒有任何單元讀它做控制流」（`business-rules.md:38`）——已自行對 U-4／U-6／U-7／U-8／U-9 逐檔搜尋 `pending_reverse`，結論成立，零反例：**
- U-8 自己：`business-rules.md:30`（R-6.1 標題「不看儲存欄位」）與 `business-logic-model.md:70`（邊界情形表「以 label 即時查詢開啟中的反向 PR 判定，**不看儲存欄位**」）皆明文不以此欄位判斷流程走向。
- U-6：`business-rules.md`／`business-logic-model.md`／`domain-entities.md` 三檔全文搜尋 `pending_reverse`，**零命中**（`grep -n` 三檔皆 exit 1）。U-6 用的 `reverse_pending`／`Config.reverse_pending`（`business-rules.md` R-2 群，`domain-entities.md:23-30`）是不同名稱的獨立集合，每輪由 label `aidlc-sync-reverse` 即時查詢算出，與本欄位無關——與 R-6.2 表格的描述一致。
- U-7：`business-rules.md`／`business-logic-model.md`／`domain-entities.md` 三檔全文搜尋，**零命中**。`ReconcileReport`（`domain-entities.md:9-19`）的八個欄位無一涉及 `pending_reverse`。`functional-design-questions.md` 與 `nfr-requirements/*` 被讀取範圍擋下未能開啟，如實記載為未覆蓋，但核心設計三檔（含欄位契約檔 `domain-entities.md`）已足以支撐「零讀者」結論——若真有讀取，理應出現在這三檔之一。
- U-4：`domain-entities.md:26` 明文「本機制不清除它……無任何單元讀它做控制流」，且同一行已同步更正舊版「何時清空由 U-8 與 U-6 決定」的錯誤指派敘述。
- U-9：僅在自我測試設計與歷史 Review 段中提及該欄位（分析性文字），不構成執行期讀取。

**「無盡遞迴」論證（`functional-design-questions.md:75`）——結論可用於支持 R-6.2，但論證字面本身有一個未點破的跳躍，記錄為 Minor，不影響 READY：**

R-1.5（`business-rules.md:13`「不得直接推 `ut`」）逐字對應 `requirements.md:105`（FR-G1「……並開 PR 呈現給人審，**不得直接推 `ut`**」）——來源查證屬實，且清除動作確實需要再開一則 PR（欄位只能經 `commit_and_push` 寫，而該方法在本單元只推反向分支）。**但「那則 PR 合併後又留下新的待清狀態」這句字面上不嚴謹**：若清除動作寫入的是字面值 `null`，該 PR 合併後 `pending_reverse` 就是 `null`——R-6.0 的「非 `null` 等價於曾有 PR 合併」這條 biconditional 建立在「本機制目前唯一的寫入來源（R-1.3）永遠寫非 `null` 觀察值」這個現況假設上；新增一個「寫 `null`」的清除操作後，這條 biconditional 需要改寫，不會自動觸發又一輪「待清狀態」——除非清除規則被定義成「任何一則本 workflow 的 PR 合併後都觸發清除」而未排除清除 PR 自己，那樣才真的無界重複。這是**可靠特判避免、非邏輯必然**，用「無盡」形容略為誇大。**但不影響 R-6.2 的最終判斷**：R-6.2 真正站得住的理由是獨立且已驗證的「沒有讀者」（見上）——清除本身沒有任何下游收益，多開一則需要人審的 PR（無論一次或無界次）都是純成本、零收益，不清除是正確決定。建議：`functional-design-questions.md:75` 若要保留「無盡遞迴」一詞，補一句區分「若未特判清除 PR 自身則無界重複；即使有特判，仍是每次反向合併多一輪人審成本」，使論證的必然與可避免部分分開陳述。此為既有文字精確度問題，非本輪新引入的設計風險。

**R-6.3 是否可實作、且不依賴任何不可觀察狀態——成立。**
`business-rules.md:48-52` 的觸發條件與行為（`commit_and_push` 回傳 `Rejected` 或開 PR 步驟失敗 → 刪分支；刪除也失敗 → 保留孤兒分支；兩種情形都在**同一次執行**記報告並紅燈，附 intent id 與分支名）全部只依賴該次 run 內兩個步驟的直接回傳值——`commit_and_push` 的 `Pushed｜Rejected`（`component-methods.md:106`「只推觸發分支」的標準定義已於 U-8 `business-rules.md:112-114` 就地修正為「不得推 `ut`／`main`」，`branch` 本為參數，U-8 推反向分支不違反此契約）；「開 PR」本身在 `component-methods.md` 的 C-1～C-7 中沒有對應方法，屬承載形式層級的 workflow step（符合檔頭「型別語言中立、承載形式留給 construction」的既定分工）。R-6.3 完全不讀取任何跨輪儲存欄位，`business-rules.md:52` 亦明文自陳「不留給下一輪、也不留給 U-7」，與此判定一致。

### Q2 跨檔傳播（逐檔）

逐檔核對四個事實——(a) R-6.2/R-6.3 舊版整組移除、(b) `pending_reverse` 不清除、(c) A-5 不再拆半、對 U-7 的指派撤回、(d) U-8 的不一致視窗由跨輪改為 run 內且 `ut` 不受影響——**全部一致，未發現殘留舊敘述**：

| 檔案 | 涵蓋事實 | 核對結果 |
| --- | --- | --- |
| `U-8-reverse-workflow/functional-design/business-rules.md`（R-6 群，17-53 行） | (a)(b)(d) | 一致。42-46 行以區塊引言明文列出舊版 R-6.2／R-6.3 已整組移除，並逐條說明不成立的理由，非事後模糊帶過 |
| `U-8-reverse-workflow/functional-design/business-logic-model.md`（46-81 行） | (a)(b)(d) | 一致。55 行明確標出「先前此處寫……那是錯的，已於 reviewer iteration 2 更正」；72、81 行的邊界表與上游補充段同步反映新結論 |
| `U-8-reverse-workflow/nfr-requirements/reliability-requirements.md`（5-20 行） | (b)(d) | 一致。9 行同樣有「先前本節宣稱……那是錯的」的更正引言，20 行明文「先前指派給 U-7 的『執行期不變量偵測』已撤回」 |
| `U-8-reverse-workflow/nfr-requirements/performance-requirements.md` | (b) | 一致，僅描述性提及欄位命名與行為（第 17 行），無舊敘述殘留 |
| `U-8-reverse-workflow/nfr-requirements/scalability-requirements.md` | (b) | 一致，僅描述欄位不隨規模成長（第 28 行），無舊敘述殘留 |
| `U-4-binding-store/functional-design/domain-entities.md`（20-26 行） | (b) | 一致。26 行完整重寫，並主動點名、更正自己先前「何時清空由 U-8 與 U-6 決定」的錯誤指派敘述 |
| `U-9-selftest-workflow/functional-design/domain-entities.md`（20-30 行） | (b)(c) | 一致。24、28 行明確記載撤回理由與「對 U-7 的指派已撤回」 |
| `U-9-selftest-workflow/functional-design/business-rules.md`（R-5 表，49 行） | (c) | 一致：「A-5 完全承接，不再拆半——對 U-7 的指派已於 reviewer iteration 2 撤回」 |
| `U-9-selftest-workflow/functional-design/business-logic-model.md`（本檔，Review 段 128-174 行） | (a)(b)(c)(d) | 一致——**且此段為 iteration 1／2 的歷史審查紀錄，依規則保留原樣即正確，其中的舊敘述屬歷史轉引，不計為殘留** |
| `U-9-selftest-workflow/functional-design/functional-design-questions.md`（E-4，28-36 行；Revision iter.2，63-77 行） | (a)(b)(c) | 一致 |
| `U-7-reconcile-workflow/`（`business-rules.md`／`business-logic-model.md`／`domain-entities.md`） | (c) | **一致，且更精確地說是「本來就沒有」而非「改了又改回來」**——三檔全文搜尋 `pending_reverse` 零命中，`ReconcileReport`（`domain-entities.md:9-19`）沒有任何欄位涉及此事。`functional-design-questions.md` 與 `nfr-requirements/*` 因讀取範圍限制未能開啟，如實記載為未覆蓋，但三份核心設計檔已足以確認撤回未曾落地過 |

### Q3 新引入的問題

**無。**

A-5 現在只驗「注入式的 PR 建立失敗」（`domain-entities.md:28`：分支被刪除、該次執行紅燈含 intent id/分支名）。撤回的另一半（指派 U-7 偵測「`pending_reverse` 非 `null` 卻無對應開啟中 PR」）依 R-6.0 的推導，**該條件的兩個子句本來就自相矛盾、永遠不會為真**——即使保留這個指派，它在任何真實失敗情境下都不會被觸發，不曾提供、也不可能提供實質保護。撤回它不減少任何實際涵蓋範圍，只是移除一段會被誤讀為「已覆蓋」的死碼式指派。

唯一殘留、且與本輪改寫無關的既有限制，是 `domain-entities.md:30` 已誠實記載的「注入式測試驗的是錯誤處理分支存在且正確，不是它在所有真實失敗形態下都會被走到」（例如 runner 在寫報告前整個崩潰的極端情形）——這是任何注入式失敗測試方法論的固有侷限，非本輪 R-6 改寫新增或放大的風險，且已在同一份文件如實揭露，不需本輪追加動作。

### Summary

R-6 群的改寫正確且自洽：四步推導鏈全部可回頭核對到實際檔案，R-6.2「零讀者」的結論經獨立逐檔搜尋 U-4／U-6／U-7／U-8／U-9 驗證屬實，R-6.3 完全落在 run 內、不依賴任何不可觀察狀態，可實作。「無盡遞迴」論證字面上略有跳躍（Minor，已記錄具體修法），但不影響其支持的最終決定（不清除），該決定另有獨立且成立的理由。四個關鍵事實在指定的十一份檔案（含 U-7 的三份核心設計檔）中傳播完整，無殘留舊敘述。A-5 的範圍收斂沒有製造保護真空——被撤回的一半原本就是永遠不會觸發的死碼。判定 READY。
