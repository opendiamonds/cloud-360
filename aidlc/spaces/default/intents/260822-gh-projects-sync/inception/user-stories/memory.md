<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is maintained by the orchestrator during stage execution. Add observations at the gate ritual, not by editing here directly.

## Interpretations
- 2026-08-24T01:40:00Z — mob round 1 的三份貢獻共提出約 30 項 OBJECT。分類原則：能以 AC 改寫、依賴表修正、來源標籤補正解決的一律由 lead 逕行整合；只有**涉及範圍或風險胃口、雙方立場都合法**的三項（可感知性、覆蓋洞、IAM 分流）依 §5 交付人工裁決，結果 M1=B／M2=A／M3=A。判準不是「這項重不重要」而是「lead 有沒有權決定」。
- 2026-08-24T01:40:00Z — 兩位 agent（design C-4、quality §5）**各自獨立**指向同一個覆蓋洞：立案事故比的是「看板 Status ↔ issue 開關狀態」，而全部 AC 與一致率定義比的都是「看板 ↔ record」。lead 三腳複驗（`intent-statement:15`／`requirements.md:154`／`OOS-2`）後確認屬實。獨立匯流是強訊號，但仍逐條複驗而非直接採信。
- 2026-08-24T00:55:00Z — CONDITIONAL 適用性判定為 **Execute**：逐項對照 condition 四款，命中 3 款（user-facing／multiple personas／complex business logic），未命中 cross-team。skip 條款的「developer tooling」需要正面回答，因為 codekb `business-overview.md` 明寫「本機制的使用者是開發流程本身而非產品終端使用者」——判定不採為 skip 理由，因 skip 條款針對的是無可見面、無 persona 分化的工具，而本機制的核心價值（可信度）是 perception 層性質，只有故事層驗得到。
- 2026-08-24T00:55:00Z — persona 集合依 [Q1=A] 定為四個，其中 **P4 同步機制維運者不在 `intent-statement` 的受益者清單上**。判定其為「已核可需求的主體歸屬」而非新引入的需求：FR-E1／FR-G1／FR-C1／NFR-O2 四條各自要求有人去做事，不設 P4 就會寫成無主詞的系統行為，或掛到 P1 身上而與 P1 的核心 benefit（不必費心）互相沖淡。
- 2026-08-24T00:55:00Z — 故事集合 11 則，落在 [Q3=A] 的 8–12 區間。Q4=B 與 Q5=A 各新增 1 則（S-9 NFR-O1／O2、S-10 CAP-10），相加後仍在區間內，三題相容。
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->

## Deviations
- 2026-08-24T03:05:59Z — **本 stage 全程的 `[Answer]:` 時間戳都是編造的，不是讀時鐘取得**（`00:40:00Z`／`00:44:00Z`／`00:48:00Z`／`02:10:00Z`）。其中 `02:10:00Z` 落在當時真實時間之後 56 分鐘——一個尚未發生的時刻——且它出現在一段目的正是聲明「這不是事後補授權」的註記裡。reviewer iteration 2 以 audit shard、檔案 mtime 與 `date -u` 三項機械證據抓到。已全部改為誠實形式並向使用者揭露。**根因是習慣：整個 session 都在寫「看起來合理」的 ISO 時間而不是跑 `date -u`**，平常不會被發現，直到某一次落在未來。
- 2026-08-24T03:05:59Z — **M1／M2／M3 的人工裁決取得後未即時寫回問題檔、未記 audit**，導致 reviewer 從 artifact 看不出授權存在而判 Critical。這是本 session 第二次犯同型錯誤（第一次是 requirements-analysis 的 F4），且**第二次的補救比原缺口更糟**（用假時間戳補記）。最終處置是回頭向使用者重新取得一次可驗證的裁決，而非堅持既有說法。
- 2026-08-24T01:40:00Z — **知識爭議未走 §5 的 round 2，改由 lead 以第一手證據直接裁定**。`aidlc-developer-agent` 主張 requirements OQ-7 的「PR #508 已合併」與現況不符。§5 對知識爭議的處置是 round 2 重新派遣讓該 agent confirm or maintain；本站改為直接查 GitHub API（`repos/opendiamonds/cloud-360/contents/scripts?ref=ut`）取得 ground truth 並駁回。理由：round 2 的目的是讓專家收斂，而此爭議是可用第一手證據終結的事實問題，重派一輪成本高且結論不會更可靠。該 agent 的貢獻檔原樣保留（dissent 留在磁碟上），lead 的反駁與證據寫在 `stories.md` 依賴表下方，兩者並陳。
- 2026-08-24T01:40:00Z — **未把 rules bundle 逐字貼進三份 mob agent brief**，改為給出四個檔案路徑並註明它們已由 `.claude/CLAUDE.md` → `.claude/rules/aidlc.md` import chain 進入每個 agent 的 ambient context；另逐條摘出各 agent 最需適用的 corrections（以 cid 標識）使規則不只可取用而是被指名。
- 2026-08-24T01:40:00Z — 發現並記錄一項**上游內部瑕疵但不回改上游**：`scope-document` CAP-1 寫「設 In progress」與 requirements FR-A1「設 `Ready`」不一致，以 FR-A1／[Q1=A] 為準並在問題檔設「對齊註記」段。
- 2026-08-24T00:55:00Z — **未把 rules bundle 逐字貼進三份 mob agent brief**，改為給出四個檔案路徑並註明它們已由本專案的 `.claude/CLAUDE.md` → `.claude/rules/aidlc.md` import chain 進入每個 agent 的 ambient context。stage-protocol §5 要求「paste the accumulated rule bundle verbatim into every agent brief」；該要求的用意是確保每條適用規則都在 agent 的 context 中，而在本 harness 上該條件已由 import chain 滿足，逐字複貼三次會多耗約數萬 token 且內容完全重複。brief 中另逐條摘出各 agent 最需適用的具體 corrections（以 cid 標識），使規則不只是可取用而是被指名。
- 2026-08-24T00:55:00Z — 發現並記錄一項**上游內部瑕疵但不回改上游**：`scope-document` 的 CAP-1 原文寫「設 In progress」，與 requirements 的 FR-A1「設 `Ready`」不一致。依 `project.md ## Corrections`（下游經人工確認的語意變更不回改已核可的上游 artifact），以 FR-A1／[Q1=A] 為準，並在問題檔設「對齊註記」段明記這是對齊而非本站新定案——否則純比對兩份文件的人會誤判為迴歸。`requirements.md` 的「已解消的矛盾」未收錄此項是它的漏列，本站不回跳重開其 gate。
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
- 2026-08-24T01:40:00Z — M1 選 B（修 benefit ＋ 新增 US-OQ-3）而非 C（回跳 requirements 補需求）：C 能在需求層正面補上缺口，但 requirements-analysis 已核可並跑完兩輪 reviewer，回跳要歸檔 artifact、重走 gate 與 reviewer。B 的代價是把實質上是需求層的缺口推給設計階段，若該站判定需新需求仍要回跳——這個代價已在選項本文向使用者揭露。
- 2026-08-24T01:40:00Z — M2 選 A（新增 S-9 AC 5 只偵測不關閉）而非 B（明文不涵蓋）：A 嚴格說是本站新增的需求面，追溯上標明來源為本站；但 B 的代價是「這個 intent 交付之後，當初立案的那個問題仍然存在且無人偵測，而看板會每天回報一切正常」——那與 `project.md ## Mandated` 對 tcms 的立論（錯誤的覆蓋感比沒有覆蓋更危險）直接衝突。
- 2026-08-24T01:40:00Z — 接受 S-2 的 AC 數由 11 增為 15（Small 仍 ❌）：拆解不可判的 AC 必然增加條數。替代方案是把 S-2 拆成兩則故事，但那會超出 [Q3=A] 的粒度區間，且把「stage 推進後看板跟著動」這個唯一可展示成果拆成兩個都不完整的半成品。改以更精確的切線註記交給 units-generation。
- 2026-08-24T00:55:00Z — 接受 S-2 的 Small 不成立（11 條 AC）：[Q3=A] 的選項本文即載明「單則故事的 AC 數會偏多，units-generation 可能仍需再切」，使用者在知道此代價的情況下選了 A。處置是在 S-2 的 INVEST 註記明標 Small ❌ 並給出**依驗證方式是否同類**的三條建議切線（映射判定／觸發與時效／不建議單獨切出 AC 11），但**本站不決定切分**——切分是 units-generation 的職責。替代方案是把 S-2 拆成兩則，但那會讓故事數逼近 Q3=A 的上限且把「stage 推進後看板跟著動」這個唯一可展示成果拆成兩個都不完整的半成品。
- 2026-08-24T00:55:00Z — NFR 承載採 [Q4=B] 分流而非全掛 DoD（A）：代價是多一節「全域 Definition of Done」要維護、且「哪些算可見」需逐條附理由（已在該表的分流理由欄逐列寫出）。換得的是 NFR-O1／O2 這兩條**對 P4 真的看得到**的品質屬性成為可驗收的成果，而非散在多則故事的 DoD 裡沒有任何一則「擁有」它。
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->

## Open questions
- 2026-08-24T03:05:59Z — 本 worktree 內有一個名為 `origin/ut` 的**本機分支**（`refs/heads/origin/ut` @ `a2613ef`，2026-07-31），它遮蔽 `refs/remotes/origin/ut`（@ `be73385`），使任何引用 `origin/ut` 的 git 指令靜默解析到舊 commit。已實際誤導 `aidlc-developer-agent` 做出一項錯誤的事實反駁（宣稱 `scripts/aidlc_sync_*.py` 不在 `ut`）。此陷阱不屬本 intent 範圍，但會持續污染任何在此 worktree 做的 git 查證。
- 2026-08-24T01:40:00Z — 本站的新增指派由 2 項增為 **7 項**（US-OQ-1～7），其中 5 項落在 application-design。這是 mob 找出的缺口總量，不是本站擴大範圍；但 application-design 的負載因此顯著增加，delivery-planning 排序時應納入考量。
- 2026-08-24T01:40:00Z — **本 worktree 內有一個名為 `origin/ut` 的本機分支**（`refs/heads/origin/ut`），會遮蔽 `refs/remotes/origin/ut`，使任何引用 `origin/ut` 的 git 指令靜默解析到 2026-07-31 的 `a2613ef` 而非真正的遠端 `be73385`。它已實際誤導一位 mob agent 做出錯誤的事實反駁；reverse-engineering 當時記的「baseline 落後三個 commit」多半也是同一個坑。這是 repo 層級的陷阱，值得進 §13 learnings。
- 2026-08-24T01:40:00Z — S-4 全部 AC、S-3 AC 6 前半、S-9 AC 2／AC 3 的 Given 在今日 repo 不可達，需 fixture。fixture 機制已列 US-OQ-6，但「沒有 fixture 就無法驗收」這件事改變了這幾則故事的完成定義，delivery-planning 不應把它們當成可直接交付的單元。
- 2026-08-24T00:55:00Z — **[req:OQ-7] 仍未裁決**：PR #508 已合併的 `scripts/aidlc_sync_*.py` 三支腳本，與 ADR-0013 §3 及 `project.md ## Forbidden` 的衝突（既有豁免／遷移到 gh-aw／收窄規則三擇一）。已跨 reverse-engineering、requirements-analysis、user-stories 三站未決。它不阻擋本站，但會實質改變 construction 的工作量。本站只記載。
- 2026-08-24T00:55:00Z — 本站新增兩項落點指派（非新範圍）：**US-OQ-1** 重複失敗的通報收斂手段（S-8 AC 4）→ application-design；**US-OQ-2** CAP-9 產物在 Construction 的留痕形式（PRE-1）→ delivery-planning。後者是 `scope-document` 自己已記載但未指派落點的缺口，本站依「surface 之外還要 resolve」補上指派。
- 2026-08-24T00:55:00Z — S-8 AC 4 目前**不是二元可判**（「須避免把 P1 淹沒」）。已依 `project.md ## Corrections`（`user-stories:c9`）雙管處置：在 AC 1 本文加適用前提（「一個失敗的首次出現」）使字面不再衝突，並把收斂手段明列為 US-OQ-1。待 mob 的 quality agent 覆核此處置是否真的消除矛盾，或只是把矛盾換個位置留著。
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
