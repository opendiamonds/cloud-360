# Stage Diary — intent-capture

## Interpretations

- 2026-08-02T13:45:00Z — 本 stage 的 diary 一度使用 `## Interpretations（續）`、`（續 2）` 等標題累積條目，導致 `aidlc-learnings.ts surface` 只抓到 4 項（工具只認四個標準標題）。合併回標準標題後候選數從 4 變 17。日記若要被 §13 ritual 看見，必須始終只用四個標準 H2，新增條目一律 append 到既有標題下。
- 2026-08-02T06:30:00Z — Sources register 只登錄三條 memory 規則（M1 schema/deploy 同步、M2 Out of scope、M3 小步前進）；ideation 階段禁止實作細節，其餘 memory 規則（branch 命名、commit message）要到 construction 才有約束力，登錄了反而是雜訊。
- 2026-08-02T06:30:00Z — 題數取 8 題（Standard 深度上緣）。功能本身小，但 brownfield 專案的既有 RBAC 角色體系讓「誰看得到這個欄位」不是自明的，值得問滿。
- 2026-08-02T06:45:00Z — 使用者說「只有 Platform_Admin 和 Security_Reviewer 看得到」，我記為 Q2 的 X（自由填答）而非 A+B；因為選項 A 把 `Platform_Owner` 與 `Platform_Admin` 併列，而使用者只點名了後者。不把未選的角色當成已排除，也不把它當成已包含。
- 2026-08-02T07:05:00Z — 使用者以自行編輯檔案的方式回答 Q3–Q8（非 chat 萃取），且 6 題中有 4 題與我的判讀不同（Q3 C≠B、Q4 E≠C、Q5 A≠A,B,D、Q7 B≠C）。依協定「autonomy is never inferred」，我未把「Done」當成採用我判讀的授權，先讀檔確認 —— 結果證明這個保留是對的。
- 2026-08-02T07:20:00Z — Q9／Q10／Q11／Q12 在對話中是以實作語彙討論的（單一欄位 vs 歷史表、J3a 權限、欄位級權限），但 phases/ideation.md 禁止 ideation artifact 含實作細節。我把它們改寫到「產品邊界／政策」的高度寫進 Initial Scope Signal（例如「稽核只需最後一次登入，不需保留完整登入歷史」而非「users 加 last_login_at 欄位」），保留決策的約束力而不下沉到設計。

## Deviations

- 2026-08-02T14:10:00Z — Reviewer iteration 3 抓到：confirmation 標題帶「（第 2 輪）」後綴使 claim-sources sensor 的精確字串比對失效。實測 sensor 後發現合約更嚴：confirmation 必須是帶 [assumption] 標籤的清單項且與 artifact 逐字一致（我原本用表格＋改寫摘要 → accepted 集合為空）。已改為由 script 從 artifact 逐字抽取生成，杜絕手抄漂移。
- 2026-08-02T14:10:00Z — stage 檔 Step 5 要求表格未解欄位寫「Unknown (open question) [assumption]」，但 sensor 禁止 [assumption] 字面標籤出現在 Assumptions 區以外 —— 框架自我矛盾（reviewer iteration 3 亦認定）。取捨：以確定性 sensor 為準，表格改寫為「Unknown（開放問題，見 Assumptions A5/A6）」，去掉字面標籤但保留指向。
- 2026-08-02T14:10:00Z — artifact 的 [open question] 條目改掛 [assumption] 標籤（sensor 只認字面 [assumption]），開放問題性質改以「（開放問題）」前綴保留在文字。§13 的 parked 判定讀 diary 的 Open questions 標題、不讀 artifact 標籤，故不受影響。
- 2026-08-02T13:45:00Z — Q10 的選項只寫「給 `Security_Reviewer` J3a 的 view 權限」，未揭露該權限實際涵蓋的範圍（帳號清單、角色、啟用狀態、授權申請）。使用者在資訊不完整下作答，副作用直到 assumption A4 才被記錄。權限類問題的選項應寫明授予後實際看得到／做得到什麼，而非只寫授予哪個 story id。
- 2026-08-02T06:30:00Z — Q8 的 scope 確認題額外列出 29 個 approval gate 的成本；stage 檔只要求區分「確認 scope」與「定義不同邊界」，但不揭露 gate 數量會讓使用者無法真正評估 scope 是否過重。
- 2026-08-02T06:45:00Z — 在 ideation 階段查了 `schema_rbac.sql` 與 `rbac.py` 的實際權限矩陣。phases/ideation.md 規定「No implementation details in ideation artifacts」，我遵守該規定（artifact 不會寫實作），但**問對問題需要事實**：不查就不會知道 Security_Reviewer 根本沒有 J3a 權限，會讓「限這兩個角色可見」看似無成本。查證用於形成問題，不寫進產出。
- 2026-08-02T07:20:00Z — stakeholder-map 未列出開發團隊與一般使用者，且**未**寫成「已排除」。Q13 的選項 C（補開發團隊）與 Q5 的選項 C（一般使用者隱私）皆未被選取，而 stage 檔的 grounding contract 明訂「Never turn an unselected option into an exclusion or requirement」。因此以「未列出＝本階段未確認」的表頭註記處理，而非宣告排除。
- 2026-08-02T13:20:00Z — Reviewer iteration 1 判 NOT-READY（1 Critical + 4 Major + 1 Minor），全部成立，已修正。Critical 是我把 Q2 選項 A 的措辭「Platform_Admin／Platform_Owner」誤植到 Q5 的來源上 —— Q5 選項 A 只有 `Platform_Admin`。這個錯誤還被寫進給使用者的決策摘要，使用者是在含錯的摘要上按下 Looks correct。
- 2026-08-02T13:35:00Z — Reviewer iteration 2 判 NOT-READY，迭代用盡。Finding 1（Critical）是**我修 iteration 1 的 Critical 時新引入的**：為了不發明 `Platform_Owner` 的利益，我在 stakeholder-map 加了一條 assumption，卻沒把它加進已被人工確認的 Assumption Confirmation 表。修 bug 引入 bug，且引入的位置正好是「人工確認的完整性」這個機制本身。
- 2026-08-02T13:35:00Z — Finding 3 我沒有照 reviewer 的建議做。它主張把「超過 N 天未登入」整條移出 Success Metrics、只留在 Assumptions。但「有視覺標示」這個機制由 Q3=C 確認、是真的成功指標；未確認的只有門檻**數值**。整條移走會讓 Success Metrics 遺漏一項已確認的成功條件。改為：Success Metrics 保留「未登入超過設定門檻的帳號帶有視覺標示 [Q3]」＋指向 Assumptions 的導航註記（非重複主張），數值狀態只在 A1 陳述一次。

## Tradeoffs

- 2026-08-02T06:30:00Z — M1（schema/deploy 同步）在 ideation 就登錄，而非留到 construction。理由：加「最後登入時間」必然是 DDL 變更，這條規則會直接影響 scope 與成功定義；早點讓它進入 sources，後續 artifact 才能合法引用。
- 2026-08-02T06:45:00Z — 把 Q9（歷史 vs 單一欄位）獨立成題而非併入 Q3 成功定義。理由：它是資料模型分岔，會傳遞到 units-generation 與 schema/deploy 同步規則（M1）；混在成功定義裡會被當成細節略過。
- 2026-08-02T07:05:00Z — Q1（稽核需求）與 Q4（無特定觸發、機會性改善）之間有張力但不判為矛盾：可以自發建立稽核能力而無外部期限。此張力反而讓 Q7=B（記 decisions-log 而非開 ADR）更一致。改以 assumption 記入 artifact，不阻斷流程。
- 2026-08-02T07:05:00Z — Q4（機會性改善）與 Q8（feature scope、32 stages、29 gates）在成本比例上不相稱，但使用者先前已明示目的是完整試跑工具，屬審慎的刻意選擇，非答案矛盾。記為 assumption 供後續讀者理解。
- 2026-08-02T07:20:00Z — Q10 的權限擴張同時寫進兩份 artifact 的 Assumptions（intent-statement 記其與 M4 的張力、stakeholder-map 記其與 Security_Reviewer 利益範圍的未釐清）。重複看似冗餘，但兩份文件的下游讀者不同（前者給 requirements、後者給溝通規劃），只寫一處會讓另一條路徑漏掉。
- 2026-08-02T13:20:00Z — Reviewer Finding 2 建議把 `Project_Admin` 補進 Target Customer 表並掛 [Q11][Q12]。我沒有照做：Q11／Q12 只確認「可見」，不確認「受益」，直接補列等於製造新的無來源主張。改以表下註記說明「可見範圍大於受益者清單」，既解消文件內部不一致，又不發明利益。

## Open questions

- 2026-08-02T14:10:00Z — 向 upstream 回報候選：stage 檔 Step 5 的「Unknown (open question) [assumption]」指示與 claim-sources sensor 的「[assumption] 僅限 Assumptions 區」互相矛盾；另 sensor 對 confirmation 的逐字清單合約在 stage 檔中無任何說明，只能讀 sensor 原始碼得知。
- 2026-08-02T06:30:00Z — 「最後登入時間」是否需要保留歷史（登入紀錄表）而不只是單一欄位？這會決定是 ALTER TABLE 加欄位還是新增資料表，影響 units-generation。待 Q1/Q3 答案釐清。
- 2026-08-02T06:45:00Z — 若 Q11 選 B（欄位級權限），現行 RBAC 的 story × action 粒度需要擴充，這可能大於功能本身。屆時應評估是否值得開 ADR。
- 2026-08-02T06:55:00Z — Q10=A 有一個副作用未被明確同意：給 `Security_Reviewer` J3a view 等於讓他看到 Admin 使用者頁的**全部**欄位（帳號、角色、啟用狀態、授權申請），不只稽核欄位。這是權限擴張，與 M4（security baseline hard constraint，含 IAM 最小權限）有張力。已併入 Q12 的選項脈絡，若使用者選 A 應在 artifact 的 Assumptions 標註。
- 2026-08-02T13:20:00Z — Reviewer 的 Minor 指控（artifact 寫「constraint compliance」但來源 M3 原文是「extension compliance」）暴露一個更大的問題：`aidlc/spaces/default/memory/team.md` 的 M3 仍是 v1 詞彙 `extension compliance`，而 `CLAUDE.md` 已於 ADR-0011 的 C 項清理改為 `constraint compliance`。兩者不一致，屬 v2 遷移的漏網。artifact 已依規定逐字引用 M3 現行原文；team.md 的用詞修正不應在 stage 執行中順手改（規則檔變更應走 §13 learnings 或獨立行動），留待 learnings ritual 提出。
- 2026-08-02T13:35:00Z — Finding 2、3 的修正發生在 reviewer 迭代用盡**之後**，因此**未經審查**。approval gate 必須向人類明示這一點，不得讓人誤以為所有修正都通過了對抗性審查。
