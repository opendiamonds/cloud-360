## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-18T15:21:32Z
**Iteration:** 1

### Summary

memory-service 的 nfr-design 產出大致自洽，並承接了上游 NFR；前次 review-02 的 Critical（`[D1]` 作答空白）與 Major（D8-5／D8-6 無承接）在凍結產出中已處置（`nfr-design-questions.md` 第 61 行已填答並誠實註記為事後補寫；D8-5／D8-6 已有明確承接）。剩一項設計與已落地程式的落差（刪除路徑對未核准帳號的 403，設計完全未提），以及數項 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-service/nfr-design/security-design.md §二之二、§二之四（reason 只列 owner／scope）；backend/services/memory_facade.py:198-202 與 :391（`_authorize_approved`、`REASON_PENDING`） | 設計宣稱刪除路徑「不回 403」且拒絕理由只有 owner／scope 兩種；已落地的 facade 在取列之前，對未核准帳號拋 `MemoryForbidden(reason=REASON_PENDING)` 而得 403（程式註解自述它只取決於呼叫者身分、對任何 id 相同，故不重開 oracle）。哪邊對：程式這一邊的推理正確，設計不完整。設計文件、NFR7.24 三案例判準與 ADR-0006 IAM 欄都沒有承認這第三條拒絕路徑，也沒有論證它不是 oracle。 | 在設計（或 corrections）補記第三個 reason 與其不構成 oracle 的論證，把「刪除路徑不回 403」改為「對 id 不敏感的 403 除外」，並為 NFR7.24 判準補一個未核准帳號案例。 | New |
| R-02 | Minor | construction/memory-service/nfr-design/logical-components.md §一（四個模組）、reliability-design.md §四（NFR4.20 判準範圍）；backend/services/ 下 memory_errors.py、memory_types.py | 設計以四個模組為範圍，實作實際有六個（另有 memory_errors.py、memory_types.py），NFR4.20「模組層無可變容器」的檢查範圍因此漏了兩檔。 | 把元件清單與判準範圍更新為六個模組，或說明兩者為純型別／例外檔而排除。 | New |
| R-03 | Minor | construction/memory-service/nfr-design/logical-components.md §二之一 `D8-7` | D8-7 承接於 U12／U13 的 functional-design，但該站為 CONDITIONAL 且 per-unit，未依 project.md 規則寫轉移目標；同檔 D8-6 有寫兩層，D8-7 沒有。 | 補上「若被 skip 則轉 code-generation（ALWAYS）」。 | New |
| R-04 | Minor | construction/memory-service/nfr-design/reliability-design.md §五（N8-9） | 90 天個人對話歷程沒有備份策略的缺口只被「誠實記載」，沒有承接站，也沒有「無自然承接站」宣告。 | 指派承接站，或明寫無自然承接站並要求在閘門重新提交。 | New |
| R-05 | Minor | construction/memory-service/nfr-design/nfr-design-questions.md 第 61-72 行 | `[D1]`=A 的作答是事後補寫（檔內自承晚於實際作答）。audit shard 不在本單元可讀範圍，本審查無法複驗 QUESTION_ANSWERED 事件是否已補登；前次 review-02 R-01 的稽核半邊因此未能確認（前次 review-02 已提）。 | 閘門上由 conductor 確認 audit 內存在對應事件。 | New |

### Validation Tool Results
| Tool | Result | Interpretation |
|------|--------|----------------|
| 手動交叉核對 D8-1 至 D8-7 承接 | D8-1 至 D8-6 有承接或明確無承接，D8-7 缺轉移目標 | 對應 R-03 |
| 抽查 memory_router.py `_translate`、memory_facade.py 刪除路徑 | 404 detail 一致、日誌 reason 依設計區分；另有設計未載的未核准帳號 403 | 對應 R-01 |
