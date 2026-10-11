<!-- 本檔不是正式的審查收據。 -->

# iteration 2 審查（**無收據，不得被當成已記錄的審查**）

**為什麼沒有收據**：conductor（我）在讀完本輪 findings 後**先修改了產出才要錄裁決**，
順序反了。引擎因此拒絕 `REVIEW_COMPLETED`：「its output documents changed after
review iteration 2 started」。每站只允許一次 stale-receipt 補救，而該次補救已在
本輪的 `REVIEW_REQUESTED` 被用掉（請求回傳 `"recovery":"stale-receipt"`），
故無第二次補救可用。我嘗試逆轉那兩處修改以還原位元組，仍未被接受，兩次被拒後停止。

**同一個錯誤在本 session 已發生第二次**：稍早的 `nfr-design` 站是同一個順序錯誤、
同一個結果。正確順序是**先 `log review --verdict` 再動任何產出**。

**本檔的效力**：審查內容本身有效且已被據以修正（見下方 findings 與各自的處置），
但它在稽核紀錄上**沒有對應的 `REVIEW_COMPLETED` 事件**。任何依賴「本站已完成
兩輪審查」的下游判斷，都必須讀這一段。

**iteration 1 的裁決有正式收據**（`REVIEW_COMPLETED`，NOT-READY，
`reviews/review-03.md`）；缺的只有 iteration 2。

**本輪 findings 的處置**：R-01 Resolved、R-03 Resolved、R-02 Partially resolved；
新增的 R-05（§16 text fallback 殘留「成員」）與 R-06（§2 與 §20 同一狀態兩種描述、
覆蓋表未更新）**兩者皆已修正並機械複驗**——但該修正本身未經第三方審查。

---

## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-09-28T23:04:57Z
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Suggested fix | Status |
|---|---|---|---|---|---|
| R-01 | Major | `wireframes.md` §16–§18 (button removed); new `## 本站查出、已核可 scope 尚未涵蓋的項目` section | Verified: the `[成員]` button is gone from all three ASCII boxes (§16–§18 header lines now read `[設定]` only), and the new section correctly traces the root cause back to the capability-11 definition written in `scope-document.md` revision 2, which lists only four responsibilities and omits member management despite `[S14]=A` presupposing it exists. The decision (fold into 11 / new capability 12 / explicit exclusion) is routed back to `scope-definition` rather than decided here. **This is the correct call, not just an acceptable one**: `phases/ideation.md`'s Scope Discipline forbids carrying forward undecided scope, and drawing a placeholder screen for a responsibility that may not even belong to this capability would have been rough-mockups inventing scope, which is exactly the failure mode `project.md`'s "本階段新增或推翻…須逐處明標並要求回補" rule exists to prevent. Answering the coordinator's direct question: routing back is correct; this stage should not have drawn a placeholder. | None — this is resolved as designed. | Resolved |
| R-02 | Partially resolved | `wireframes.md` §20, §21, §19 `G-3`/`G-4` rows | §20 and §21 are now drawn. The `[R2]=C` reconciliation for §20 holds up under attack: it is grounded in the actual Figma read (welcome card + eight cards sit in the central column above the input bar, replaced by conversation on first send) and it correctly identifies §20 as an elaboration of §2's existing empty-state role rather than a competing information architecture — not rhetorical. The `G-4` reclassification (§21, "same 240px assigned to a different mental model") is a real correction, not padding, and its baseline (keep app nav in the left column, move history into the entry page) is defensible and appropriately deferred at the edges (retention/count limits) to `refined-mockups`. **However, the fix itself introduced two residual defects — see R-05 and R-06.** Because "done" for R-02 means the artifact is now internally consistent, and it isn't yet, this is partially rather than fully resolved. | See R-05, R-06. | Partially resolved |
| R-03 | Resolved | `wireframes.md` Assumptions (last block) | Verified: the new Assumptions entry names the three tabs' distinct failure modes (count wrong / write lost / summary stale), cites `units-generation:c6`'s splitting criterion by name, explicitly tells `units-generation` not to default to treating the tabs as one unit because they share a page, and separately notes "being the agents' data source" as a fourth, UI-less surface. This is exactly what was asked for. | None. | Resolved |
| R-04 | — | `wireframes.md` §17 ("清除端沒有任何畫面") | Carried forward from iteration 1 for visibility only, per the original dispatch brief's instruction not to re-report it. Still present, still correctly scoped to `domain-design`, unchanged this round. | No action requested. | Accepted risk |
| R-05 | Major | `wireframes.md` §16 text fallback (the line beginning "專案詳情頁頂部為麵包屑與設定、成員兩個動作") | New, introduced by the R-01 fix. The ASCII box and header for §16 (and §17, §18) correctly dropped `[成員]`, but the text-fallback comment for §16 was not updated and still reads "頂部為麵包屑與設定、成員兩個動作" (top bar has breadcrumb, settings, **and member**, two actions). Text fallbacks in this document exist specifically so a reader who can't parse the ASCII box gets an equivalent description — this one now describes a control that was deliberately removed for being undesigned. This is exactly the "跨檔傳播失敗" pattern this project's own corrections log flags repeatedly (residual references after an edit): the fix touched the picture but not its prose twin. | Update the §16 text-fallback sentence to drop "、成員" (leave breadcrumb + settings), matching the ASCII box and the §17/§18 fallbacks (which were correctly not touched, since they never mentioned 成員 in prose). | New |
| R-06 | Major | `wireframes.md` §2 vs §20; `## 能力覆蓋逐項對照表` capability-1 row | New. §20's own text argues it is "§2's expanded version, same position, same role" — but §2 was never edited to say so, and nothing in §2, in the coverage table (capability 1 still cites only "第 2、3 節"), or anywhere else cross-references §20. The document now carries two materially different depictions of the same state ("入口頁 — 尚未選定作業對象"): §2 shows two plain example sentences with no cards; §20 shows a welcome message plus an eight-card grid. Nothing in the artifact says which one a builder should treat as authoritative, whether §20 replaces §2, or whether they're two facets of one state that need to be shown together. This is the same class of defect as R-05 — a fix added new content without updating the older content or the index (coverage table) that points into it — just at the section level instead of the sentence level. | Either merge §2 into §20 (delete the now-superseded plain-text example) and update every place that cites §2 (including the coverage table's capability-1 row) to cite §20 instead, or add one explicit sentence to §2 stating it is superseded by / a subset of §20 and update the coverage table to also cite §20. Either way, exactly one section should be the thing a builder implements for this state. | New |

### Answering the two things you flagged yourself

1. **Tab-component precedent gap** (`AssessmentPage.tsx:134` is bare `useState`, no `role="tablist"`/`aria-selected`/arrow-key handling anywhere in the tree) — checked directly with a tree-wide grep, confirmed zero hits for all three. Correctly disclosed as an undisclosed cost of `[R10]=B` at the time it was recommended. Good catch; no further finding.
2. **Silent write failure** on two Assumptions entries — checked both are now present verbatim (the "三籤是「導覽上的分組」…" entry and the "能力 11 的三籤需要一個可無障礙存取的籤元件…" entry). Confirmed present, not just claimed present.

### Summary

Three of the prior three findings were substantively addressed; two of the three (R-01, R-03) are clean. R-02's underlying content is genuinely good — the reconciliation arguments hold up under direct attack rather than being hand-waved — but the fix left the artifact internally inconsistent in two places (R-05, R-06), both same-shaped: new content added, an older sibling (a sentence, a whole section) left uncoordinated with it. Neither is a design flaw in what was newly drawn; both are residue from the edit itself, the exact failure mode this project's memory has flagged repeatedly across other stages ("改動任何已產出的 artifact 之前，先列出本輪要改動的每一個主張；改完逐一 grep 全部產出檔"). Two Major findings open (R-05, R-06) plus R-02 not fully closed is enough to hold this at NOT-READY for one more small pass — both fixes are mechanical (one sentence edit, one cross-reference decision) and don't require new design judgment, so I'd expect this to close quickly.
