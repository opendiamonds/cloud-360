## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-06 | Unresolved | Minor | traceability.json 沒有改。第 246 行（BR4.1）與第 252 行（BR4.2）的 note 仍是未標示施工當時的舊行號（檔頭第 12 行、:577／:591／:596／:1259／:1270，以及 grep -c 308 回 0 的敘述），全檔搜尋不到「施工當時」或「現況見」字樣。開發代理改在 code-summary.md 的回歸節補記，並說明是依派工指示不動 traceability.json。現況行號我已逐一實測：schema_rbac.sql 第 16 行為「預設矩陣（352 列）」，第 1306 行為「-- 352」，DEPLOY.md 的 1488、1502、1507、2407、2418 都含 352，DEPLOY.md 第 1920 行確有無關的「≈ 308.8」。補記內容正確，但讀 traceability.json 的人看不到。因為有書面的延後理由，維持 Minor、不阻擋。 |
| R-07 | Resolved | Minor | code-summary.md 的三處舊行號（Step 8 列、「重做」節的逐步查驗摘要、「與已核可計畫／測試說明的落差」）旁都已就地加上「review-03 R-07：之後又再後移，2026-11-01 現況為 :1488／:1502／:1507／:2407／:2418，見文末回歸一節」。新行號與我實測的 grep 結果逐字相符。 |
| R-08 | Unresolved | Minor | 原問題是「照 unit-test-instructions.md 執行的人看不到 M3、M4 照字面仍為綠」。unit-test-instructions.md 第 112、113 行的 M3、M4 兩列沒有任何註記，全檔也搜尋不到 PD-2。改記在 code-summary.md 的回歸節無法解決這個問題：照指示文件操作的人不會去讀 code-summary.md 的最後一節，所以讀者仍會做出會是綠燈的突變，並誤以為測試失去偵測力。開發代理說明就地加註會觸發計畫核可保護而被迫還原，這個理由屬實，卻是流程限制，不是問題已解。需要由 conductor 在重新核可計畫時一併加註，或把指向 PD-2 的一行放進計畫核可範圍內的檔案。仍為 Minor。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|
| Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md > 「2026-11-01 回歸」節 > 「有沒有碰到本單元負責的部分」第一點 | 這一點寫「44 列權限種子」的 sha256 為 96dd4eef。實測：schema_rbac.sql 第 946 至 1300 行是整個 352 列的 INSERT 區塊，它的 sha256 才是 96dd4eef…（HEAD 的區塊在第 888 行起，雜湊相同）。真正只含 K1 至 K4 的 44 列（第 1256 至 1299 行）雜湊是 0c0c120c…，HEAD 與工作樹同樣一致。結論（種子沒被碰）正確，但標籤把整個區塊說成 44 列，下一個照這句重算的人會得到不同的數字。 | 把「44 列權限種子」改成「352 列的 INSERT 區塊（第 946 至 1300 行）」，並另補一句 K1 至 K4 的 44 列雜湊為 0c0c120c…。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 種子區塊雜湊：`awk 'NR>=946 && NR<=1300' schema_rbac.sql` 與 HEAD 的同區塊（`git show HEAD:schema_rbac.sql`，區塊起點 888） | 兩者皆 96dd4eef5e695ebb771a4c06d4e5024fcd3d0e9c9d56ef142cc70f034f93e710 | 與開發代理回報一致，起始行從 888 移到 946，種子逐位元未變 |
| K1 至 K4 列雜湊：`grep -E "'K[1-4]'" schema_rbac.sql`，HEAD 與工作樹 | 兩者皆 0c0c120cdcdf66052c456824d55b30cab001505c8b12323076612ad4fb9854f2，列數 44（第 1256 至 1299 行） | K 列未變，並顯示 96dd4eef 對應的是整個 352 列區塊（見新發現） |
| `user_router.py` 標籤與排除清單 | K1 至 K4 在第 126 至 129 行，`CATALOG_EXCLUDED_STORIES` 在第 132 行且只含 J1，`/roles/catalog` 在第 690 行 | 與 code-summary.md 回歸節所寫的行號逐字相符 |
| 副本測試：`-m unittest tests.test_rbac_story_ids_seed tests.test_rbac -v`（rsync 複製到 scratchpad，cwd 為副本的 backend） | `Ran 13 tests`，`OK`（本單元 7 個加 test_rbac 6 個） | 本單元保證成立 |
| 副本全套：`-m unittest discover -s tests` | `Ran 1372 tests`，`FAILED (errors=1, skipped=3)` | 總數與開發代理回報的 1372 相符。唯一的 error 是 `test_legacy_cost_retirement` 找不到 `frontend/tests/e2e/regression.spec.ts`，原因是派工指定的 rsync 排除了 frontend 目錄，屬複製副本的人為產物，與本單元無關，不判為失敗 |
| 清理 | 已刪除 `rv-u3/` 與 `rv-u3-hyp/`；沒有在 repo 內執行 Python | 符合禁止事項 |

### Summary

本單元的保證在共用檔被其他單元修改後仍然成立：352 列種子區塊與 K1 至 K4 的 44 列逐位元未變，標籤與排除清單正確，13 個目標測試全綠，全套 1372 個測試只有一個因副本排除 frontend 而產生的非實質 error。R-07 已解決。R-06 與 R-08 都是把修正改記到 code-summary.md，而不是記到原本會被讀者看到的地方，其中 R-08 無法讓照 unit-test-instructions.md 操作的人看到警告，故判 Unresolved。三項都只是 Minor，另有一項 Minor 的雜湊標籤不精確，沒有 Critical 或 Major，判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-generation-plan.md > 一之一 第 3 點與第 184 行 | 把第 4 項移到 membership-service（U19）的方向合理：本單元只有 seed、log 與標籤，沒有邀請或改選的執行路徑，規則也寫明由 U19 執行。但這個移交沒有落地。第 3 點說以「membership-service 計畫中的對齊紀錄為準」，而 membership-service/code-generation 底下的計畫、摘要與測試指示全文都沒有提到 merge-blockers、BR7 或帳號狀態檢查（逐一 grep 為零命中），merge-blockers.md 第 13 列又指回本計畫的 §一之一。兩邊互相指向，沒有任何一邊有可執行步驟，第 4 項實際上沒有承接者。§一之一也只有「疊加 authorization_status 與 is_active」一句，沒有寫出 U19 要改的函式與要測的案例。 | 在 membership-service 的計畫補上第 4 項的實際步驟與對齊紀錄，或在 §一之一直接寫清楚交接內容：要改哪些函式、要加哪些案例（待核准受邀被拒、已停用受邀被拒、改選略過待核准與已停用者），並確認 U19 已接手。 | Resolved (reviewer) |
| R-02 | Major | backend/services/membership_service.py > assert_invitee_has_global_permission（約 657-682 行）、member_snapshots（282-296 行）、reselect_for_project（752 行起） | 現行程式與第 4 項描述的缺口只部分吻合，§一之一沒有區分。邀請端已經把 authorization_status 傳給 user_can，user_can 對非 approved 回 false，所以「待核准被邀請」其實已被擋；真正沒擋的是 is_active，這個函式完全沒有檢查。改選端更嚴重：member_snapshots 只讀 project_members 三個欄位，reselect_for_project 的候選只排除被停用的 owner，沒有任何地方過濾 K3.edit、approved 或 is_active，所以 BR7.3 的「持有 K3.edit」目前並未實作，待核准、已停用或只有 K3.view 的成員都可能被自動升為專案管理者。這是已提交程式裡的授權缺口，而它的修正步驟目前不在任何單元的計畫裡。 | 在移交內容中明寫兩點：邀請端補 is_active 檢查，改選端的候選集合必須過濾 K3.edit、approved、is_active，並用純函式（select_successor）以外的轉換層完成，以保持挑選函式的純度與排列不變性測試。對應的 allow/deny 雙向案例列入 U19 的測試。 | Resolved (reviewer) |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-generation-plan.md > Step 10c、10d | 兩格維持未勾的處理是誠實的，也不阻擋：照字面執行的 M3、M4 仍為綠（PD-2），有效版本 M3-eff、M4-eff 已證明斷言不是恆真，勾上會讓計畫宣稱字面上沒發生的事。但計畫裡永遠留著兩個未勾項，之後的讀者要翻到摘要才知道原因。 | 在 10c、10d 旁加一行指向 code-summary 的 PD-2，並把 M3-eff、M4-eff 列為已勾的替代步驟，讓計畫自身說得清楚。 | Resolved (reviewer) |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md > 七（最後一段） | 該段仍寫 schema_rbac.sql 驗證註解「位移至第 805 行」，現況是第 1248 行（檔頭的涵蓋清單在第 16 行，不是第 12 行），重新查驗表已用新行號，但原段落與 §二表格的「第 12 行」沒有同步。 | 在原段落加上行號已位移的註記，或改成不寫死行號的描述。 | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md > 三、七個測試與全套前後比對 | §三 的指令寫成 `cd backend && python -m unittest …`，基準數寫 432、439；重做節才寫須用 .venv，現為 1319。§三 沒有就地指向重做節。 | 在 §三 加一行指向「與已核可計畫／測試說明的落差」，避免照 §三 的指令跑會失敗或比錯基準。 | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/traceability.json > coverage 第 23、24 筆的 note（BR4.1′、BR4.2′） | note 仍寫「檔頭第 12 行 308→352」與「DEPLOY.md 五處 :577／:591／:596、:1259／:1270」。現況分別是 schema_rbac.sql 第 16 行，以及 DEPLOY.md 的 :1392、:1406、:1411、:2306、:2317。note 沒有任何施工當時行號的標示。「施工後 grep -c 308 回 0」今天也不再逐字成立：DEPLOY.md 第 1824 行有一個無關的「≈ 308.8」。 | 在這兩筆 note 後加註「施工當時行號，現況見 code-summary 最後一節」，並把 grep 敘述限定為「與 role_permissions 列數相關的 308」。本輪沒改 traceability.json，這項只是延續既有的註記慣例，不阻擋。 | New |
| R-07 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/code-summary.md > 「重做」一節的「與已核可計畫／測試說明的落差」，以及「重新查驗」一節的 Step 8 列 | 兩處把 DEPLOY.md 的現況行號寫成 1386／1400／1405／2300／2311（重新查驗那節更早的 1347 等也一樣）。DEPLOY.md 因合併前必修 #24 的 hunk（原 3 行變 9 行）後移了 6 行，現為 1392／1406／1411／2306／2317。最後一節已說明這 6 行的位移，但上面兩處本身沒有就地加註。 | 在那兩處各加一句「之後又後移 6 行，見最後一節」，或把行號改成不寫死的描述。 | New |
| R-08 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/rbac-story-ids/code-generation/unit-test-instructions.md > §三 突變驗證表的 M3、M4 兩列 | 兩列仍是 PD-2 已證明無法讓目標測試變紅的單一角色寫法，列上沒有指向 PD-2 或 M3-eff／M4-eff 的註記。code-summary 的重做節有說明，但照 unit-test-instructions 這份指示執行的人看不到。 | 在 M3、M4 兩列旁加一句「照字面執行仍為綠，有效版本見 code-summary PD-2」。 | New |

> R-06 Not re-checked this round

> R-07 Not re-checked this round

> R-08 Not re-checked this round
