## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-06 | Still applies | Minor | traceability.json 第 246、252 行的 note 仍寫「檔頭第 12 行 308→352」與「:577／:591／:596、:1259／:1270」，沒有標示是施工當時行號。補記只在 code-summary 的 2026-11-01 回歸一節（該節 R-06 項），這是依派工指示不改 traceability.json 的結果。DEPLOY.md 現況實查為 :1488／:1502／:1507／:2407／:2418，schema_rbac.sql 為 :16，與 code-summary 補記一致。DEPLOY.md:1920 的「≈ 308.8」仍是無關命中。不阻擋。 |
| R-07 | Fixed | Minor | code-summary 第 310、335、351 行三處舊行號旁都已就地加註「之後又再後移，現況 1488 等，見文末 2026-11-01 回歸」。第 387 行所在的 10 月底小節仍寫 :1392 等，但它屬依時序保留的歷史紀錄，且最後一節已給出實查的現況行號。 |
| R-08 | Still applies | Minor | unit-test-instructions.md 第 112、113 行 M3、M4 兩列仍是單一角色寫法，檔內沒有任何 PD-2 或 M3-eff／M4-eff 註記。code-summary 的 2026-11-01 回歸一節已說明不能就地加註的原因（測試說明在計畫核可指紋內）以及照字面執行仍為綠。計畫 10c、10d 也維持未勾，與此一致。不阻擋，交由 conductor 在下次計畫核可時決定是否補註。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 對收據 reviewed-source-b07d283df9f1.tsv 六列獨立重算 | 6 同、0 變（DEPLOY.md、rbac.py、rbac_seed_data.py、user_router.py、test_rbac_story_ids_seed.py、schema_rbac.sql） | 與 conductor 重算一致。這六個檔 git status 皆無變動，最近變更為 commit ff537a7 之前，本單元修正段落未被碰到。 |
| git diff HEAD 對 code-generation-plan.md | 零差異 | 勾選回復與 HEAD 版逐字相同。 |
| 勾選計數 | 60 勾、2 未勾 | 與 code-summary 新節所述相符。 |
| 未勾格 10c、10d | 理由仍成立 | 照字面只改 SRE 一列時測試仍為綠（PD-2）。有效版本 10c′、10d′ 已勾。這些是突變驗證項，需要執行測試，本輪依限制未重跑，也不能以 CI 已實跑視為已勾。 |
| code-summary 檔尾「整站重跑後的勾選回復」一節 | 內容屬實 | 收據 6 同 0 變、60 勾 2 未勾、兩個未勾格的文字都已實查。 |
| 測試與突變 | 未執行 | 依審查限制不跑任何測試，改以收據雜湊相同加上上一輪 READY 的實跑紀錄（7 測試 OK、全套 1372 OK）判定。 |
| 已知跨單元事實 | 未重複報告 | C3（membership-service）不屬本單元。 |

### Summary

來源與收據逐位元相同，計畫與 HEAD 零差異，勾選回復與新增小節內容屬實。三項開放發現中 R-07 已修，R-06 與 R-08 為不阻擋的文件註記 Minor，延續既有處置。沒有新發現，判定 READY。

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
