## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Prior Findings

| ID | Now | Severity | Note |
|---|---|---|---|
| R-09 | Fixed | Minor | code-summary.md 檔尾新節「四、勾選重設」（第 666 行）已明寫：Step 8／9 中指名 BrainPage.tsx 的格子，標的已由 U13 移到 brainProtocol.ts 與 useBrainConnection.ts:150，由 S9-3／S9-4 在現行落點重驗，計畫內文保留為當時紀錄。替代落點重驗而非原文條件達成，這一點已據實揭露，符合原要求。 |
| R-10 | Still applies | Minor | code-summary.md 第 636 行等多處仍寫 0 errors, 2 warnings，未說明與 team.md 記載基準 3 個 warnings 的差距（LoginPage.tsx:36 的 warning 不在現行清單）。無證據顯示本單元造成，不影響結論；仍只是紀錄精確度問題。 |

### New Findings

| Severity | Location | Finding | Required action |
|---|---|---|---|

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| shasum -a 256 對 reviewed-source-0504fe12eb5c.tsv 的 14 個路徑逐檔重算（awk -F tab 取欄位） | 14 同、0 變 | 與 conductor 重算一致；ci.yml、brain_ws_contract.py、ws-contract.json、ws-contract.d.ts、useBrainConnection.ts、eslint.config.js、兩支測試與 dump 腳本全部逐位元等於已審版本。本單元沒有新的程式改動。 |
| git diff HEAD 對 code-generation-plan.md | 零差異（0 行） | 勾選回復與 HEAD 版逐位元相同；沒有碰到修正段落。 |
| 計畫勾選計數 | grep 實算 74 勾、0 未勾 | 與 code-summary 新節宣稱一致；沒有仍待 CI 實跑才能勾的格子。 |
| code-summary.md 新節「整站重跑後的勾選回復」 | 屬實 | 時間、收據檔名、14 同 0 變、74／0 皆可由上列結果複驗。其他單元的工作樹改動與 33deb2e 的三個檔案不在收據 14 檔之內，不影響本單元。 |
| 測試、lint、建置 | 依限制未執行 | 以讀碼與雜湊判定；本單元程式與已審 READY 版逐位元相同，前次實跑結果仍適用。 |

### Summary

本單元收據 14 檔全部逐位元未變，計畫檔零差異且 74 格全勾，新增的 code-summary 一節內容屬實。前次的 R-09 已由新節據實揭露替代落點而解決，R-10 的 warning 基準說明仍缺，僅為 Minor 紀錄問題。跨單元的 C3（membership-service）已知事實未重複報告。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `code-generation/traceability.json` row `BR2.13` | Verified fixed: `BR2.13` now a single `Deferred` row whose `target` text spells out both halves (type-layer delivered here; runtime `error(INVALID_REQUEST)` reject deferred to `U13`), matching the treatment of the structurally identical `BR1.3`/`BR2.5` rows (both bare `Deferred → U13 brain-gateway`, no paired `OK` row). Coverage distribution moved 32 OK/14 Deferred → 31 OK/15 Deferred, confirmed by direct read of `traceability.json`. | None — fix verified faithful and consistent with sibling rows. | Resolved (reviewer) |
| R-02 | Major | Audit shard `SENSOR_FIRED`/`SENSOR_PASSED` events for `code-generation`; `code-summary.md §十` (R-02 disposition) | The `required-sections` sensor still never fired for this unit's three `code-generation` documents (mechanism gap unchanged). The conductor instead manually ran the equivalent check and recorded 7/9/8 H2 headings, 0 findings for the three files — I independently re-counted `^## ` headings in `code-generation-plan.md` (7), `unit-test-instructions.md` (9), and `code-summary.md` (10, since §九/§十 were added after the manual check recorded 8) and these match the conductor's self-report exactly. The stated reason for not fixing the *mechanism* (framework-layer trigger; `project.md` forbids editing `.claude/` upstream files to express project rules) is a legitimate application of that constraint. I was mid-investigation into *why* the hook didn't fire for this unit but not for the sibling `brain-infra` (to judge whether a conductor-side workflow fix, not a `.claude/` edit, was available) when the turn budget for this iteration was reached; I did not complete that specific judgment. The substantive content-check gap is closed; the automation gap is honestly recorded as unresolved and deferred to the next practices-discovery/framework upgrade, which is a defensible disposition given the constraint cited. | No code action needed this iteration. Recommend the next practices-discovery pass investigate why `required-sections` fired for `brain-infra`'s equivalent files but not for `brain-ws-contract`'s (a write-path/tool-use difference is plausible), since if the cause is conductor-side rather than truly framework-layer, the `project.md` "don't edit `.claude/`" reasoning would not actually apply and the gap could be closed without any upstream edit. | Resolved (reviewer) |
| R-03 | Minor | `code-generation-plan.md` Step 8/9 vs. `code-summary.md §五` `D-1` | Already fixed within iteration 1; `§十` records it honestly as a planning-quality defect I introduced, not silently absorbed. No code defect remains. | Feed back to code-generation planning practice as iteration 1 already recommended. | Resolved (reviewer) |
| R-04 | Major | `functional-design/nfr-requirements/security-requirements.md` line ~275 (`NFR5.7`) vs. `code-generation/traceability.json` row `NFR5.7` (status `OK`, target `backend/scripts/dump_ws_contract.py`) | `NFR5.7`'s own requirement text states, verbatim: "`WsClientEnvelope` **不得**含 `turnId` 欄位（`BR2.13`）；型別上不可構造是第一層，伺服器收到即回 `error(INVALID_REQUEST)`（而非靜默忽略）是第二層，屬 `U13`。" — the identical two-layer split that R-01 flagged for `BR2.13` itself, using the identical `U13`/execution-reject language. `traceability.json` marks `NFR5.7` fully `OK` with no `Deferred` counterpart or qualifying target text, even though its own carried rule (`BR2.13`) was just corrected in this same file to acknowledge exactly this split. A downstream reader of `traceability.json` trusting the `NFR5.7: OK` row would conclude the IAM/authorization-bypass NFR is fully closed by this station, when its runtime-reject half is not delivered here (no live WS handler in this unit). This is precisely the sibling-defect risk the dispatch brief anticipated when it asked to check every `OK` row whose rule text contains a runtime/server-side obligation — confirmed by grep across all 19 other `OK`-status `BR*` rule statements for `U13`/`執行期`/`伺服器收到` language, which found no further instances (only `BR1.1` and `BR4.3` mention execution-time/`U13` language, and in both cases the *rule itself* is scoped purely to the type layer, so those are not splits). | Reword `NFR5.7`'s `target` in `traceability.json` to spell out the same two-layer split now used for `BR2.13` (type layer delivered here; runtime reject-and-respond deferred to `U13`), or mark it `Deferred → U13` to match `BR2.13`/`BR1.3`/`BR2.5`. | Resolved (reviewer) |
| R-05 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/functional-design/merge-blockers.md > 第 2 項；construction/brain-ws-contract/code-generation/code-summary.md > 交接 | 合併前必修第 2 項的缺陷是「伺服器只能捏造 turnId」，但本單元只改了契約。`backend/services/brain_gateway.py:1127-1128` 仍是 `tid = turn_id or _mint_turn_id()`，執行期行為一點都沒變。清單裡第 2 項只有 brain-ws-contract 一列，沒有 brain-gateway 或 entry-page-ui 的對應列，交接只存在於本單元的 code-summary。build-and-test 站若只依清單回填「已處置」，閘道與前端的落點會被漏掉。U14 又已交付（624c170），所謂「在 U14 處理」其實是重開已完成的單元。 | 在 merge-blockers.md 為第 2 項補上 U13（閘道四種非輪次情境改送 turnId=null，附 TestClient／WS 測試）與 U14（null error 的呈現）兩個落點，並寫明「契約已完成、執行期與呈現未完成」。第 2 項在兩者落地前不得標為已處置。 | Resolved (reviewer) |
| R-06 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/functional-design/reviews/review-05.md > R-01 required action；code-generation/code-summary.md > 合併前必修第 2 項 | review-05 R-01 要求「在 BR2.8 逐條標明每個 code 在輪次內與輪次外各自的 turnId 規則」。本輪只把判準寫成情境（ErrorPayload.turnId 的 description），沒有逐 code 的表，也沒有把這項交接出去。上游 rules.md 依規定不回改，所以沒有任何地方寫明各 code 的規則。實作者無法判定：INVALID_REQUEST 在 select_clarify_candidate 的 candidateId 格式錯誤時是否屬於該輪；INTERNAL_ERROR 何時為 null；UNAUTHORIZED 只有非輪次還是兩者皆可。EMPTY_RESPONSE 應恆為輪次內，但契約沒有強制。 | 在 code-summary 或 ErrorPayload.code 的 description 補一張逐 code 表（輪次內／輪次外／兩者皆可，各附情境）。若認為不宜在契約層強制，明寫為 U13 的實作指引並在交接列出。 | Resolved (reviewer) |
| R-07 | Minor | frontend/src/brain/useBrainConnection.ts > case 'error'（約 169-186 行）；frontend/src/brain/brainTranscript.ts > updateTurn、case 'error' | `?? ''` 讓 null error 帶 turnId='' 進 reducer，之後會發生四件事：(1) 在對話裡新建一則 turnId 為空字串的大腦錯誤訊息；(2) 第二個非輪次 error 會因 turnSegment[''] 已存在而覆寫第一則；(3) `setAwaitingReply(false)` 與 reducer 的 clearPending 會解除另一個進行中真實輪次的等待狀態，例如串流中 set_work_target 失敗時；(4) 這四件事都不會把錯誤歸到不存在的輪次，所以不算誤歸，但行為並非「只讓型別成立」。目前契約的 null 還沒有人送，所以是潛伏風險，code-summary 也已誠實標明未設計過。交接只寫「呈現」，沒點出這些副作用。 | 把(1)(2)(3)寫進 U14 的交接與 merge-blockers 第 2 項的 U14 落點。U14 處理時 null error 應走獨立路徑：不建輪次訊息、不動等待旗標，只顯示提示。 | Resolved (reviewer) |
| R-08 | Minor | backend/tests/test_ws_contract.py > WsEnvelopeErrorTurnIdNullableTest.test_relaxation_is_limited_to_error | done 的 null 子案例只斷言 ValidationError，實際擋下它的是 DonePayload.turnId 的 str 型別，不是 BR1.6 的分類。若有人把 DONE 誤移進 _EITHER_SCOPED_TYPES，這個子案例仍會綠。token 子案例與三集合斷言能抓到 error 以外的誤移，但 done 這一路沒有獨立保護。另外沒有測試斷言 `turnId` 鍵缺席時 ErrorPayload 被拒；JSON 的 required 含 turnId，但只靠 dump 閘門守著。 | done 的 null 測試改為只讓 envelope.turnId=None 而 payload 帶值，才會落到 BR1.6 或 BR1.5。補一個 ErrorPayload 缺 turnId 鍵必須被拒的測試。 | Resolved (reviewer) |
| R-09 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/code-generation/code-generation-plan.md > Step 8 第 202 行與 Step 9 第 216-217 行的已勾格 | 這三格的字面條件是以 BrainPage.tsx 為標的（第 202 行為「BrainPage.tsx:83 改為由產生的型別取值」），而該檔已由 U13 刪除，字面條件不可能再成立。code-summary 把它們改在 brainProtocol.ts 與 useBrainConnection.ts:150 重驗後勾回。我在副本重現了等效的突變：把第 150 行改成寫死字串，ESLint 在 150:55 回 no-restricted-syntax 錯誤，所以保護本身是真的。但勾選的是替代條件，不是原文條件。code-summary 第四節已據實揭露這一點，所以只算紀錄精確度問題。 | 在 code-summary 第四節補一句：這三格是以替代落點重驗，不是原文條件達成。不需改程式。 | New |
| R-10 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/code-generation/code-summary.md > 2026-11-01 回歸驗證節、第二節 lint 列 | 該節寫 npm run lint 為「0 errors, 2 warnings（既存）」，但 team.md 記載的基準是 3 個 warnings。我沒有重跑全套 lint，只對 useBrainConnection.ts 與 brainProtocol.ts 跑 ESLint，結果乾淨。2 對 3 的差距沒有說明。這很可能是其他單元已修掉其中一個，不影響本單元結論。 | 註明 warning 數與 team.md 基準不同的原因，或改寫成與基準無關的說法。 | New |

> R-09 Not re-checked this round

> R-10 Not re-checked this round
