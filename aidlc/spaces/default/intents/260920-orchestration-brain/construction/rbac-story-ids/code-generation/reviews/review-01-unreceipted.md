# Code Review — `U3 rbac-story-ids` · `code-generation` · iteration 1（**無收據**）

> **這份審查是有效的，但它在 audit 裡沒有 `REVIEW_COMPLETED` 收據。**
> 原因不是審查品質，也不是忘了記錄——是結構性的，**在本 repo 不可能記錄成功**。
> 下面先寫清楚原因，審查全文在 `## Review` 之後逐字保留。

## 為什麼記不進去（已查證的根因）

`aidlc-log.ts review --verdict` 被拒，訊息逐字：

```
Refusing REVIEW_COMPLETED for "code-generation": workspace source changed after
REVIEW_REQUESTED iteration 1. Restore the requested source state and re-dispatch the reviewer.
```

守衛在 `.claude/tools/aidlc-log.ts:2352-2366`：把 `workspaceSourceState()` 的
指紋與 `REVIEW_REQUESTED` 當時的值逐位元比對。

**該指紋把 git 已忽略的測試／建置快取一起算進去。** 查證：

| 事實 | 證據 |
|---|---|
| 指紋的 listing 共 **591** 筆，含 **102** 筆 `backend/.hypothesis/**` 與 `__pycache__/*.pyc` | 直接呼叫 `workspaceSourceState()` 匯出 listing 後實算 |
| 走訪**完全不看 gitignore** | `.gitignore:2` 有 `.DS_Store`、`.gitignore:32` 有 `__pycache__/`，兩者**都出現在 listing 裡** |
| 指紋用的是**內容 SHA** 不是 mtime | `aidlc-lib.ts` 的 `filesystemSourceIdentity`：``lines.push(`file:${rel}:${executable ? "x" : "-"}=${sha}`)`` |
| `REVIEW_REQUESTED`（2026-10-04T14:13:09Z）之後全樹（排除 `aidlc/`）只有 **3** 個檔變動 | `find … -newermt "2026-10-04T14:13:09Z"` |

那三個檔是：

1. `backend/services/rbac_seed_data.py` — **只有 mtime 變**。審查者的三次突變皆已還原，
   內容完好：`git diff --stat` 為 `+44 −0`，本單元 7 個測試 `OK`。
2. `backend/services/__pycache__/rbac_seed_data.cpython-313.pyc` — 因上一項的 mtime 改變而**重新編譯**
   （`.pyc` 檔頭嵌入原始檔 mtime 與 size）。
3. `backend/.hypothesis/unicode_data/15.1.0/codec-v2-utf-8.json.gz` — **新檔**，
   `hypothesis` 在跑測試時自己建的。

### 結論：這是一個無法靠紀律避免的死結

審查者**必須**跑測試套件才能獨立查證（它正是這麼做的，`Ran 439 tests … OK`），
而**跑測試這個動作本身**就會建立／更新 `.hypothesis` 與 `__pycache__`，
於是 source 指紋必然改變，`REVIEW_COMPLETED` 必然被拒。

對本 repo 的任何 **workspace-writing stage**（`code-generation`）都成立。
`--retry-pending` 不是出路：`aidlc-log.ts:2254` 逐字「`--retry-pending` cannot
rebaseline changed content」，且 source 指紋那條路徑只處理**沒有**指紋的舊請求。

**這是 `progress-channel` 與 `rbac-story-ids` 兩次審查都無收據的同一個根因**——
前一次被當成個案（`progress-channel/code-generation/reviews/review-01-unrecorded.md`），
本次查出它是結構問題。

### 本單元的 audit 現況（如實）

| 事件 | 有無 |
|---|---|
| `DECISION_RECORDED`（Plan Approval） | ✅ |
| `PLAN_APPROVAL_RECORDED` | ✅ |
| `REVIEW_REQUESTED` iteration 1 | ✅ `review:729660ef76006df69080e6621e1b7548` |
| `REVIEW_COMPLETED` | ❌ **本檔即替代紀錄** |
| `UNIT_STARTED` / `UNIT_COMPLETED` | ❌ 另一個缺口，成因不同（見下） |

`UNIT_STARTED`／`UNIT_COMPLETED` 缺失的成因是 `plan-approval-guard` 在
`PLAN_APPROVAL_RECORDED` 之前擋下**所有**可變更的 shell 指令（含
`aidlc-state.ts unit start`），核可之後我直接去派工沒補跑；等實作與審查跑完，
路由已移到下一個單元，兩個指令都被拒：
*"Refusing to start unit \"rbac-story-ids\" for \"code-generation\": the engine
currently routes \"functional-design\"/\"embedding-port\"."*
可執行的修正：**核可收據一記下、派工之前，立刻跑 `unit start`**。

### 不影響的事

程式本身已獨立查證：439 測試全綠、矩陣 352 列／11 角色／32 story id 組合完整、
兩份 seed 逐列相等、六個檔的 diff 範圍符合 `source-manifest.json`、四個不得變動的檔
位元相同。審查者另外自建三個突變，三個都紅。**缺的只是稽核收據，不是驗證。**

---

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-04T14:19:11Z
**Iteration:** 1

### Independent verification performed (all confirmed, no claim taken on faith)

| Claim | Verification method | Result |
|---|---|---|
| 439 tests OK (baseline 432, +7, zero existing failures) | Ran `python3 -m unittest discover -s tests` myself | Confirmed: `Ran 439 tests … OK` |
| Matrix: 352 rows, 11 roles, 32 story ids, combination-complete | Parsed `DEFAULT_ROLE_PERMISSIONS` with a standalone script (not the unit's own test) | Confirmed exactly: len=352, roles=11, sids=32, dupes=[], missing=[] |
| Per-column counts K1 view=8/edit=0/allfalse=3, K2 11/4/0, K3 8/4/3, K4 8/4/3 | Same script, independent counting logic | Confirmed exactly, matches `functional-spec.md` §一′ line-for-line |
| Two seed copies agree | Parsed `schema_rbac.sql`'s INSERT block and `DEFAULT_ROLE_PERMISSIONS` with my own regex/tuple comparison, not the shipped test | Confirmed: 352 vs 352, `only in sql: set()`, `only in py: set()` |
| `-- 352` verification comment never edited | `git diff -- schema_rbac.sql` around that line is empty; `git show HEAD:schema_rbac.sql` shows the same literal `-- 352` at the pre-existing line 761 (now 805 after the 44-row insert shifted it) | Confirmed — pre-existing drift from `6f9227d`, untouched, coincidentally correct now |
| `requirements.txt`, `ci.yml`, `database.py`, `schema.sql` unchanged | `git diff --stat` on all four | Confirmed: empty |
| `DEPLOY.md` has exactly 5 "308→352" edits | `git diff -- DEPLOY.md` | Confirmed: 5 hunks, all 308→352, no other content touched |
| `source-manifest.json` writes == actual changed app files for this unit | `git status --short` vs manifest's 6 paths | Confirmed: exact match; other modified files in the tree (`agent_router.py`, `design_agent.py`, `wa_collab_orchestrator.py`, `test_agent.py`, `progress_channel.py`) belong to sibling units and are correctly excluded |
| `traceability.json` sensor passes after the orchestrator's restructuring, no coverage weakened | Ran `bun .claude/tools/aidlc.ts engine sensor-traceability` myself against the file | Confirmed: `{"pass":true,"gaps":[],"orphans":[],...,"findings_count":0}`. Also independently confirmed all 62 `OK` targets exist as files, and `PD-1`/`PD-2`/`PD-3` are present only in `reverse` (not `upstream_ids`/`coverage`), consistent with the claim that no coverage claim was moved or dropped. |
| Plan checkboxes: only 10c/10d unticked | Read `code-generation-plan.md` Step 10 | Confirmed: 10a,10b,10e–10i are `[x]`; 10c (`M3`), 10d (`M4`) are the only `[ ]` in the whole file |
| `/roles/catalog` is genuinely unauthenticated and this was a decision, not an oversight (`BR4.5`) | Read `user_router.py:319-323`: `def roles_catalog(db: Session = Depends(get_db))` — no `get_current_user` dependency anywhere in the handler or its decorator | Confirmed. The `K1`–`K4` additions to `STORY_FEATURE_LABELS` carry an inline comment citing `BR4.5` and explaining the precedent (`J3a`/`J3b` already public); `functional-spec.md` §六′ documents this as a self-check finding (`R-04`) with the precise distinction between "which labels a role holds" (already exposed) vs "who holds which role" (not exposed). This is a documented decision, not an oversight. |
| `SEC-4` log leaks no user identity; `assertLogs` bound at the right granularity | Read `rbac.py` diff: log message is `"inserted %d rows: %s" % (len(pairs), "role/story_id, ...")` — role names and story ids only, no username/user id. Test asserts each of 4 story-id substrings individually plus one role-name substring, not the whole message verbatim | Confirmed — no identity leak; assertion granularity is per-substring as claimed, not whole-message literal matching (which would make the test brittle to wording changes) |

### Mutations I independently constructed (not the ones in the plan/summary — fresh ones, to avoid rubber-stamping the implementer's own mutation table)

- **Deleted the last row** (`Platform_Owner, K4`) → `test_the_matrix_has_exactly_352_rows…` failed as expected (`351 != 352`), file restored byte-identical (verified with `diff`).
- **Flipped `can_review` to `True`** on one `K3` row (`Developer, K3`) → `test_the_four_new_story_ids_never_grant_review` failed as expected, file restored byte-identical.
- **Changed only the Python side's `Platform_Admin/K4` row** (`can_edit` True→False, SQL untouched) → `test_the_sql_seed_block_matches_the_python_default_row_for_row` failed with the three-way diff exactly as the code-summary describes (one row "only in SQL", one "only in Python", one "both but differing flags"), file restored byte-identical.

I could not find a mutation this test suite would pass through silently; every attempt I made that changed a tested invariant turned a test red.

### `PD-2` verified as a real, accurately-diagnosed defect (not an implementer excuse)

I independently confirmed `BR5.3`'s statement in `rules.md:395-396` reads "**至少一個**持有 A1 view 的正式角色不得持有 K3 的任何旗標" (an existential quantifier — "at least one"), and `unit-test-instructions.md:108-109` does specify the `M3`/`M4` mutations as changing only `SRE`'s row. I simulated the literal mutation myself (changing only `SRE`'s `K3` row) and confirmed the existential assertion still holds — `Ops_Lead` and `Platform_Engineer` remain as witnesses, so the test stays green exactly as disclosed. The design defect is real, lives in `nfr-design`'s `D-10` table and this stage's own `unit-test-instructions.md §三`, and predates this stage's work.

**Judgment on the two questions `PD-2` raises:**
1. **Leaving the tests existential is correct, not a weakness.** Pinning today's exact non-holder set (`{SRE, Ops_Lead, Platform_Engineer}`) into the assertion would convert a reachability guarantee into a frozen snapshot — any future legitimate adjustment to one of those three roles' `K3` flags (which `BR5.1`/`BR6.1` do not forbid) would redden the test for no real regression. The test's job is to prove the *set is non-empty*, which is exactly what `BR5.3`/`BR6.5` require; it is doing that job correctly.
2. **Not fixing `D-10`/`unit-test-instructions.md §三` is correct, not an evasion.** Both are stage outputs from an earlier, already-gated stage (`nfr-design` has its own `reviews/` directory, confirming it passed its own gate) or are fingerprint-bound to this stage's own already-approved plan (`contract_sha256` in the plan header). Reopening either would violate the project's own standing rule against silently re-opening upstream-approved artifacts (`refined-mockups:c3` / `units-generation:260822-ug-L2` pattern in `project.md`): the correct move is exactly what was done — disclose the defect, show both the literal (green) and the effective (red) mutation runs, and hand the fix (change `D-10`'s `M3`/`M4` column to "all three qualifying roles") to whoever next touches `nfr-design`. This is traceable, not hidden — the defect and its fix recommendation are both written into `code-summary.md §五` in enough detail that a future editor doesn't have to rediscover it.

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `code-summary.md §七` (`H-10`) | `unit-of-work-story-map.md` assigns only `US1.4`/`US9.2` to `U3`, so `traceability.json`'s `upstream_ids` cannot list the `AC12.*` acceptance criteria that `BR5`–`BR7` (and tests 2–4) actually support. This is an honestly-disclosed, pre-existing gap in an upstream artifact from before this stage, not a defect introduced here. | No action required of this unit; the gap is correctly flagged for whoever next revises `unit-of-work-story-map.md`. Leaving it recorded (as done) is sufficient. | New |
| R-02 | Minor | `code-summary.md §七` (`H-11`) | `BR7.3` narrows the already-approved `AC12.4.1` ("earliest-joined member", no qualifier) to "earliest-joined **and** holds global `K3.edit`". The narrowing is substantively correct (not narrowing would let a selected successor get 403'd on every action) and is not rewritten back into `stories.md`, per the project's rule against re-opening upstream-approved artifacts mid-stream. | No action required of this unit; flagged correctly for `stories.md`'s next revision. | New |
| R-03 | Minor | `code-generation-plan.md` Step 6 vs Step 7 (`PD-1`) | The approved plan requires the `SEC-5` seed-equivalence test to pass at Step 6e, before the SQL side's 44 rows are added in Step 7a — making it literally impossible for Step 6e to go green as written. This is a genuine step-ordering defect in the plan itself (pre-existing, not introduced during code-gen). The implementer's handling — execute in the documented order, record the resulting red literally, then re-verify green after Step 7 — is honest and traceable, and incidentally doubled as a correct mutation-style mid-build check (the Step-6 red output is exactly the "44 rows only in Python" diff). | None blocking; recommend whoever edits this plan template next either reorders Steps 6/7 or rewords 6e as "write the test and record its red; verify green after Step 7," per the implementer's own suggested fix. | New |
| R-04 | Minor | `code-summary.md §五` (`PD-2`) | `nfr-design`'s `D-10` table and this stage's `unit-test-instructions.md §三` specify `M3`/`M4` as single-role (`SRE`-only) mutations against existential (`BR5.3`/`BR6.5`: "at least one role…") assertions with three qualifying roles today — so the literal mutation leaves two witnesses and the targeted test stays green. Independently reproduced: confirmed real. The implementer's resolution (run literal mutation and record it green, then run the effective mutation — all three qualifying roles — and record it red; decline to over-strengthen the test into a role-set snapshot) is the architecturally correct call, and not rewriting `nfr-design`'s already-approved `D-10` is consistent with house rules on not reopening upstream-approved, already-gated artifacts. | None blocking; recommend `D-10`'s `M3`/`M4` column be corrected to "mutate every role currently satisfying the reachability guarantee" when `nfr-design` is next touched. | New |
| R-05 | Minor | `code-summary.md §六` (`RR-1`) | The newly-public exposure of 4 Chinese feature labels via the unauthenticated `/roles/catalog` endpoint is correctly identified as a decision (not an oversight, verified above) under `BR4.5`, but its DoS/enumeration surface is deferred to `observability-setup` rather than mitigated here. This is an honest, bounded handoff — the unit does not claim the risk is closed. | None blocking for this unit; `observability-setup` should pick up `RR-1` per the existing handoff. | New |

No Critical or Major findings. I was unable to construct any mutation — mine or the ones specified in the plan — that the shipped test suite failed to catch for the properties it claims to cover (except the two instances the implementer itself disclosed and correctly worked around, `PD-2`'s `M3`/`M4`, which I independently reproduced as genuine design defects in an *upstream* artifact, not in this unit's code or tests).

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `python3 -m unittest discover -s tests` | `Ran 439 tests … OK` | Confirms code-summary.md's claim exactly; baseline 432 independently inferred from `+7` new cases, all pre-existing tests still pass |
| `bun .claude/tools/aidlc.ts engine sensor-traceability` | `{"pass":true,"findings_count":0}` | Confirms the orchestrator's `traceability.json` restructuring is schema-valid and introduces no gaps, orphans, or invalid targets |
| Independent Python seed-parity script (ad hoc) | `only in sql: set()`, `only in py: set()` | Confirms `SEC-5`'s claim without relying on the shipped test to grade itself |
| Independent Python matrix-stats script (ad hoc) | len=352, roles=11, sids=32, per-column counts all match | Confirms the matrix arithmetic in `code-summary.md §二`/`§六` without relying on the implementer's own printed numbers |

### Summary

**Classification of the 5 findings:** 0 newly introduced by this stage's code; 3 pre-existing and already honestly disclosed/unreviewed by an earlier stage (`R-01`, `R-02`, `R-03` — all pre-date this unit's work and are correctly not silently fixed in place, per the project's own rule against reopening upstream-approved artifacts); 2 new design problems surfaced during this stage's self-checks (`R-04` — a genuine `nfr-design` test-design defect, confirmed real and correctly worked around rather than papered over; `R-05` — a scoped, disclosed residual risk handed to the right downstream stage).

**What I did not reach:** I did not independently re-derive the ADR-0006 four-face table from first principles (I spot-checked IAM and network-exposure claims against the code and found them accurate; I did not independently verify the Encryption/Audit-logging "not applicable"/"partial" judgments against the full requirement set). I did not open sibling units' `construction/` directories (out of scope per the dispatch). I did not attempt every one of the 8 documented mutations myself — I reproduced 3 independently plus verified `PD-2`'s diagnosis by simulation; the other 5 (`M2`, `M5`, `M7`, and the two literal `M3`/`M4` "stays green" cases) I verified only by reading the code-summary's claimed error output against the test source and judging it internally consistent, not by re-running them myself.

This unit's deliverable is unusually well self-audited: every deviation disclosed in the dispatch brief checked out as accurately described, the two seed copies are provably identical (not just test-asserted), the matrix arithmetic is independently reproducible, and the test suite demonstrably catches every mutation I threw at it. The three plan/design defects (`PD-1`–`PD-3`) are real but belong to upstream artifacts, were handled by the book (disclose, don't paper over, don't silently patch an already-gated artifact), and are each handed to a concrete next owner.
