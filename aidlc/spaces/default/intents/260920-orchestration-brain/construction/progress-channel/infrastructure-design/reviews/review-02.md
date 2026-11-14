## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本站產出（`cicd-pipeline.md`、`traceability.json`）凍結後，前次 review-01 的多項 Major 幾乎原樣留在文字裡，而已落地的程式在多處已超前或偏離設計。偏離方向皆為程式較強，但設計仍描述舊狀態：呼叫點行號過期、`DuplicateChannelKey` 仍被標為無法收的 GAP、閘門 3 的 canary 數值與設計相反。「零設定變更、閘門寄生於 ci.yml 步 7」的核心主張成立，我已核對 `ci.yml:320`。但閘門規格與實際測試檔不一致，下游若照設計復驗會得到錯誤的期望值。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/progress-channel/infrastructure-design/cicd-pipeline.md 閘門 1 的 1e 與突變 4；traceability.json 的 U22-V3 note | 前次 review-01 已提（R-02）。1e 仍只寫「先數出呼叫點總數」而沒指定從哪裡數，且引用的三個呼叫點行號全部過期：設計寫 agent_router.py:125、wa_collab_orchestrator.py:79、backend/test_agent.py:41，實際為 agent_router.py:150、wa_collab_orchestrator.py:96、backend/test_agent.py:53（grep run_design_agent 逐一核對）。程式才是對的：test_progress_channel_contract.py:172-190 以 AST 枚舉全樹呼叫點並斷言至少三個，與設計的寫死路徑不同。突變 4 也引用過期的 :79 | 在設計中補上發現來源（AST 全樹枚舉，不得寫死路徑），更正三個行號與突變 4 的行號，並註明以程式為準 | New |
| R-02 | Major | cicd-pipeline.md §四 R-02 列；traceability.json 的 R-02-nfr-design note | 前次 review-01 已提（R-05）。設計仍宣稱 DuplicateChannelKey 無人接住、風險為高、「沒有任何 grep 能斷言」。已落地程式相反：agent_router.py:139 與 wa_collab_orchestrator.py:90 皆有 except DuplicateChannelKey，agent_router 的 handler（:139-147）送出固定的 error 事件後 return。設計因此留著一個實際已關閉的高風險 GAP，且「不可 grep」的宣稱也被 except 名稱可 grep 這件事否定。我未查證是否有測試鎖住該 handler 的存在 | 把 R-02 改記為已由程式落地關閉並指名鎖住它的測試；若無測試，補一條存在性斷言（兩支入口檔內存在 except DuplicateChannelKey，且 handler 內有 error 事件） | New |
| R-03 | Major | cicd-pipeline.md 閘門 2 子句二與 §四 U22-V7 列 | 前次 review-01 已提（R-03、R-04）。子句二「無任何回傳新鍵的函式」仍沒有可執行形狀，突變 2 只運動到 import 子句。U22-V7 仍只點名兩支鑄造端檔，漏掉 backend/test_agent.py（其鑄造在 :45，secrets.token_urlsafe）。程式端 test_progress_channel_contract.py:229 起以 all_sites 全覆蓋三處，程式較完整、設計未跟上 | 刪除子句二或給它可執行形狀；U22-V7 補上第三個落點 backend/test_agent.py，並明記測試以 all_sites 全覆蓋 | New |
| R-04 | Major | cicd-pipeline.md 閘門 3 與 §三 突變 3；traceability.json 的 S-7 note | 設計與已落地測試直接矛盾。設計寫 design_agent.py 全檔恰兩個 except … as e，canary 為綁定數等於 2。實際 design_agent.py 只剩兩個裸 except Exception（:111、:275），test_progress_channel_contract.py:351-364 的 EXPECTED_EXCEPTION_BINDINGS 為 0，並註明此偏離。程式是對的（0 比 2 更強，且不需保留死變數）。設計又主張完整需 AST 層、成本過高；測試實際已用 ast.walk（:406），該二分法已被推翻。前次 review-01 已提（R-07） | 把閘門 3 的規格改為 AST 綁定數固定為 0 且綁定名限於 e 或 exc；突變 3 改為新增一個 except … as e；刪除「需 AST 成本過高」並同步 S-10 | New |
| R-05 | Major | cicd-pipeline.md 與 traceability.json 全檔（本站宣告的 sensors） | 前次 review-01 已提（R-06）：sensor 結果零揭露。我未重跑 sensor，此條沿用前次紀錄的結論（traceability 的 NFRx.y 解析無命中，upstream-coverage 九項未引用），產出未改動故仍成立。另外 ADR-0006 四面向在本站只靠 SEC-4 一句帶過，network exposure 以 compose 6 服務為證據，其餘三面沒有逐項判定表，與 project.md 要求的逐項判定不符 | 補一張 ADR-0006 四面向判定表（不適用者附理由），並揭露 sensor 結果與 library 單元不引用 NFR 設計檔的判定 | New |
| R-06 | Minor | cicd-pipeline.md §〇；§四 S-9 列 | 前次 review-01 已提（R-08、R-09）。CONDITIONAL 判定以 produces_kinds 當適用性測試，理由不成立；S-9 的落點清單把 security-design.md 列為落點，該檔無此宣告，且漏掉 logical-components.md:7 | 改寫執行理由為 condition 未涵蓋 cicd-pipeline；S-9 改指 logical-components.md:7、:77 與 nfr-design/traceability.json | New |
| R-07 | Minor | cicd-pipeline.md §一 被否決的選項 B | 前次 review-01 已提（R-01）。選項 B 被描述為落在 project.md Forbidden 的無人值守條款內，但 ci.yml 已有 dump_openapi.py --check 與 dump_ws_contract.py --check 在 push 或 PR 觸發下執行，同形先例成立。決定 A 的結論站得住，理由應改為失敗訊息與本機一致 | 改寫否決理由，不再宣稱 B 違反 Forbidden | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep run_design_agent 呼叫點 | 3 處：agent_router.py:150、wa_collab_orchestrator.py:96、test_agent.py:53 | 設計行號 :125、:79、:41 全部過期，見 R-01 |
| grep 鑄造與 DuplicateChannelKey | 三支入口皆以 secrets.token_urlsafe 鑄造；兩支入口有 except DuplicateChannelKey | 見 R-02、R-03 |
| design_agent.py 的 except 掃描 | 2 處，皆為裸 except Exception | 與設計的 as e 相反，見 R-04 |
| ci.yml backend job | :320 為 unittest discover | 零設定變更的主張成立 |
| 測試與 sensor 執行 | 未執行（brief 禁止產生快取） | R-05 的 sensor 結論沿用前次紀錄 |
