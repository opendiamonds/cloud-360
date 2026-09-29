## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-09-25T01:19:01Z
**Iteration:** 1

本輪為**定向複驗**（advisory）：只查修訂 2 宣稱的 10 項修法是否落地、以及這些修法有沒有弄壞相鄰的內容，不重開前兩輪未提出的區域。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements.md` > FR1.8 與 ADR-0006 表 IAM 列 | 前輪已判 Resolved，本輪未受這 10 項修法影響，維持成立 | 無 | Resolved |
| R-02 | Critical | 同上 > FR1.6、FR1.7、OQ-10 | 前輪已判 Resolved；本輪 FR1.7 的 0.7 仍在、二元判定仍在，且已由 R-11 的追認承接 | 無 | Resolved |
| R-03 | Major | 同上 > FR9.5、IAM 列、OQ-14 | 前輪已判 Resolved；本輪 FR9.5 未被改動，且其「建立路徑必須存在且被指名」已由 N-7 承接（見 R-12） | 無 | Resolved |
| R-04 | Major | 同上 > NFR1、NFR2、NFR3 | 前輪已判 Resolved；三條 NFR 的母體與落點仍在。NFR2 的量測機制另見 R-14 | 無 | Resolved |
| R-05 | Major | 同上 > FR4.5a、OQ-13、N-6 | 前輪已判 Resolved，本輪未受影響 | 無 | Resolved |
| R-06 | Major | 同上 > FR1.2 | 前輪已判 Resolved；五個狀態值與 `[線框 §8][線框 §13][線框 assumption]` 標籤原樣保留 | 無 | Resolved |
| R-07 | Major | 同上 > FR4.3a、FR4.3b、OQ-12、Audit logging 列 | 前輪已判 Resolved，本輪未受影響 | 無 | Resolved |
| R-08 | Minor | 同上 > NFR1 校正程序 | 前輪已判 Resolved；本輪該程序被擴充（見 R-15），三種處置與決策者未被刪 | 無 | Resolved |
| R-09 | Minor | 同上 > 來源標籤慣例表（第 9–36 行）、FR1.4、FR5.1 | 已修正並機械複驗：`grep 'rough-mockups 第'` 命中數為 **0**，FR1.4 與 FR5.1 已改為 `[線框 §13]`／`[線框 §8]`；慣例表由 14 列擴至 **21 列**（實數）；證據標記改以「正交的第二套標記」段落解釋而非混入表內，該解釋正確（`[讀]`／`[簽]`／`[算]`／`[未驗]` 標的是取得方式，其舉例 `[kb:architecture `[讀]`]` 與全檔實際用法一致）。殘留三種未入表的形式（`[A-7]`、`[本站直接定義，於摘要確認時呈現]`、`[R-NN 的修正]`）字面自解，不影響下游判讀；該段新增的計數本身有誤，另記於 R-19 | 無 | Resolved |
| R-10 | Critical | 同上 > NFR11（第 390–414 行）、NFR2 第三個項目符號 | 已依人工裁決恢復為獨立 **NFR11**，並逐字複驗其引用的上游原文：`intent-statement.md` 第 52 行逐字為「第一版要以下列三項可量測結果判斷是否成功」，跨頁面上下文保留率那一項逐字含「本項一併涵蓋『完成一個跨功能任務所需的頁面切換次數下降』」——**與 NFR2 新版說明所引一字不差**，前輪指出的誤述已消除。NFR11 可驗收：母體為具名跨功能任務情境（`user-stories` 產生，CONDITIONAL，已附 `build-and-test` 轉移）、基準為現行 UI 的人工實際清點、門檻為「每個情境嚴格少於其基準值」（二元可判，未再發明百分比）、量測機制為 Playwright 計數路由變更且明寫「用次數而非比率，故與 e2e 的二元閘門相容」——此相容性判斷正確。NFR2 的說明已改為「已移出本條，改為獨立的 NFR11（不是移除）」 | 無 | Resolved |
| R-11 | Major | 同上 > 「人工確認範圍的落差與其處置（R-11）」（第 529–544 行）／`aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements-analysis-questions.md` 第 296–329 行 | 記錄誠實且足夠：問題檔逐字複驗確為「四項本階段新增…（N-1 至 N-4）」且 `grep '0\.7'` 在問題檔命中數為 **0**，與本節的陳述一致；所稱的稽核憑據（`DECISION_RECORDED` ＋ `QUESTION_ANSWERED` 配對，決議內容含「R-11: 當場追認 0.7、N-5、N-6」）在 audit shard 確實存在，非空言；且本節明寫「讀者若比對兩份文件發現『四項 vs 七項』的差異，本節即是答案，不是遺漏」，比對兩檔的讀者不會被誤導。不編輯問題檔的理由（雜湊綁定的收據會失效並須整輪重取）與 `project.md` 已記載的 `SUMMARY_CONTENT_STALE` 機制相符。但該裁決原文還有第二個子句未被執行，另記於 R-18 | 無 | Resolved |
| R-12 | Major | 同上 > N-7 與「本階段新增…需回補」表 | 已修正並複驗其理由成立：`scope-document.md` 第 60 行的能力 9 逐字只有「專案 → 系統 → 架構圖 階層」；`wireframes.md` §3 的控件逐字只有 `[切換對象]` 與 `[改為獨立對話]`，零建立畫面。N-7 明寫它需要線框、互動設計與授權決定，不是能力 9（資料模型）的自然延伸 | 無 | Resolved |
| R-13 | Major | 同上 > 第 510–513 行與第 525 行 | 已修正：前言改為「**七項**」，與表列七列、回補請求的「七項」三處一致；並拆為三類——驗證機制或資料交付物（N-1、N-2、N-3）、權限模型變更（N-5）、新交付物或新使用者可見面（N-4、N-6、N-7），計數 3+1+3＝7 相符。且就地寫明「N-5 觸發兩條 blocking 規則、N-7 是線框零畫面的全新使用者可見面，兩者都不是測試資產」，`delivery-planning` 不會把 N-5 讀成測試資產 | 無 | Resolved |
| R-14 | Major | 同上 > NFR2「量測機制（R-14 修正）」（第 289–300 行） | 比率的算法已講清（分母 N 個具名切換情境、分子斷言通過數、腳本自身通過條件 `比率 ≥ 0.95`），且正確點出既有閘門產不出比率——這部分成立。但「該量測腳本**不掛在** `ui-regression` 的 `.stats.unexpected` 判定上…它是獨立的一支測試」在本 repo 的工具鏈下**目前無法照字面成立**：`frontend/playwright.config.ts` 只有一個 `chromium` project 且 `testDir: './tests/e2e'`，`ui-regression` 執行的是 `timeout 15m npx playwright test`（`.github/workflows/ui-regression.md:191`）後讀 `jq '.stats.unexpected' pw-report.json` 非 0 即 `exit 1`（同檔 281–284 行）。前端唯一的瀏覽器自動化層就是 Playwright（`team.md ## Testing Posture`），因此「每個情境一次斷言」若各自是一個 `test()`／`expect()`，任一情境失敗即 `.stats.unexpected != 0`，實際門檻又回到 100%——正是本 finding 要消除的形狀。可行形狀存在（單一 `test()` 內以 soft assertion 或自行計數跑完 N 個情境、最後只對比率下斷言），但文件未指名，實作者必須自行猜 | 指名 N 個情境的逐項結果如何被收集成比率而**不使每個情境成為套件失敗**（例如單一 Playwright 測試內以 soft assertion／自行計數，最後只對 `比率 ≥ 0.95` 下一次斷言），或指名一個確實落在 `npx playwright test` 掃描範圍之外的載體 | Unresolved |
| R-15 | Minor | 同上 > NFR1 校正程序（第 264–276 行）、NFR3 校正立場、A-7 | 已修正：程序明寫同時涵蓋四個無實證基礎的數值（80%、0.7、95%、2 秒）；連動條款落實 A-7（「調整 80% 時必須同時處理 0.7，兩者不得分開調」，並寫出互相補償的理由與「只改一個即為無效的校正」）；驗收立場明寫四項一律「未達標即為驗收未通過」。兩處殘留不阻擋：NFR2 本節內沒有自己的校正立場句（僅由 NFR1 段落點名涵蓋 95%），只讀 NFR2 的人看不到；NFR11 寫「同 NFR1 的校正程序」而 NFR1 逐字只列四個數值、不含 NFR11 的基準相對門檻——不過 NFR11 同句已自帶處置（由決策者裁決該情境是否屬設計目標、不得自動放寬），不致落空 | 無 | Resolved |
| R-16 | Minor | 同上 > FR1.8 第一個項目符號（第 109 行）、慣例表第 25 行 | 已修正：改為 `[user-flow Flow 4]`，且該形式已入慣例表並註明「**與 `[線框 §n]` 是不同的檔案**」。指向複驗成立——`user-flow.md` 的 `## Flow 4` 即「不存在『無權限的入口頁』畫面」 | 無 | Resolved |
| R-17 | Minor | 同上 > Open Questions 表下方註腳（第 575–586 行） | 已修正：`units-generation`（2.7）已補進 ALWAYS 清單並加粗，且補寫理由——它是本表最常用的轉移目標（OQ-1、OQ-2、OQ-9、OQ-11、OQ-12 與 FR9.3 共六處），讀者現在可自註腳確認這六項轉移不是落在另一個 CONDITIONAL 站 | 無 | Resolved |
| R-18 | Major | 同上 > 「人工確認範圍的落差與其處置（R-11）」第 541–544 行／`aidlc/spaces/default/intents/260920-orchestration-brain/audit/` 的 `QUESTION_ANSWERED` 明細 | 人工裁決的**第二個子句未被執行，且該替代做法未回頭取得使用者同意**。audit 記載的裁決內容逐字為「R-11: 當場追認 0.7、N-5、N-6，**並補寫進問題檔的確認區塊並記明追認時點與來源**」；而 artifact 寫的是「**問題檔本身刻意不動**」，理由是雜湊綁定的收據會失效。該技術理由成立（與 `project.md` 記載的 `SUMMARY_CONTENT_STALE` 相符），替代紀錄也確實存在且誠實（見 R-11），但這是把使用者指定的紀錄落點換成另一個落點，而使用者沒有對這個替換表態。後果落在稽核可驗證性上：追認紀錄現在只存在於 artifact 與 audit，不在使用者被要求要寫的那一份問答紀錄裡 | 在本核可關卡把這個偏離明白攤給使用者裁決：接受「追認紀錄寫在 artifact ＋ audit、問題檔不動」，或要求以不改變最終內容的方式（`project.md` 已記載的兩次 Edit 手法）把追認時點與來源補進問題檔的確認區塊 | New |
| R-19 | Minor | 同上 > 慣例表下方的證據標記說明（第 36 行） | R-09 的修法新寫了一個可算的數字且算錯：該句稱「全檔共 **25** 處證據標記」，本輪實算為——全檔 `[讀]`／`[簽]`／`[算]`／`[未驗]` 出現 31 次（含說明段與 A-6 的元敘述），扣除第 33–45 行的說明段為 22 次，再扣除 A-6（第 477 行）對這組標記本身的元敘述則為 21 次。25 在任一種算法下都不成立。這正是前輪 R-13 的同型失誤（可算的數字沒先算），且是在修 R-09 的動作裡新引入的 | 把該句改為實算值並寫明採用哪一種計算範圍（是否含說明段與 A-6 的元敘述），或直接刪掉這個計數——它不承載任何下游判讀 | New |

### Summary

十項修法有**八項乾淨落地**（R-09、R-10、R-12、R-13、R-15、R-16、R-17 與自報數字的複驗），另加 R-11 的紀錄誠實可查。自報的六個數字我逐一重算後**全部相符**：49 條 FR 子需求無重複 id（`FR10.2` 第二次出現在 ADR-0006 表內是引用而非第二個定義）、10 個 FR 群組、11 條 NFR、7 個 N 項、14 個 OQ、7 條假設；跨引用以程式掃描 `FR`／`NFR`／`OQ-`／`N-`／`A-` 全部指向已定義 id，**零懸空**；`python3 scripts/validate_repo_contract.py` PASS。R-10 的上游引用逐字核對無誤，前輪那項 Critical 的誤述已消除，NFR11 本身可驗收。

兩項留給關卡裁決：**R-14** 的比率算法講對了，但它宣稱的「獨立於 `ui-regression` 判定之外的一支測試」在本 repo 的工具鏈下照字面不成立（單一 Playwright project、`npx playwright test` 掃全 `tests/e2e`、`.stats.unexpected` 非 0 即失敗），NFR2 的 95% 仍有退回 100% 的實作路徑；**R-18** 是修法偏離了人工裁決原文的第二個子句（追認應補寫進問題檔的確認區塊）且未回頭取得同意——技術理由站得住，但這個替換該由使用者點頭而非由產出自行決定。兩者皆有明確的可行處置，故不阻擋；本輪唯一新引入的缺陷是 R-19 這個算錯的計數（本 intent 第五次同型失誤），零 Critical。
