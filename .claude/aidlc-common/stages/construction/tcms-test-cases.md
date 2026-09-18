---
slug: tcms-test-cases
plugin: tcms
name: TCMS Test Cases
phase: construction
execution: ALWAYS
condition: Always executes once after build-and-test, for every scope. Every change ships with test cases that are executable by a person who was not in the room.
lead_agent: aidlc-quality-agent
support_agents:
  - aidlc-developer-agent
mode: inline
produces:
  - manual-test-cases
  - automation-test-plan
  - tcms-sync-report
consumes:
  - artifact: stories
    required: true
  - artifact: build-and-test-summary
    required: true
  - artifact: code-summary
    required: true
requires_stage:
  - build-and-test
sensors:
  - required-sections
scopes:
  - enterprise
  - feature
  - mvp
  - poc
  - bugfix
  - refactor
  - security-patch
  - workshop
inputs: Approved user stories with acceptance criteria, the build-and-test summary and its test instructions, and the code summary for every unit in this intent.
outputs: manual-test-cases.md, automation-test-plan.md, tcms-sync-report.md (under this stage's record dir, engine-resolved)
---

# TCMS Test Cases

MANDATORY: Follow stage-protocol.md for approval gates, question format, and completion messages.

This stage exists because the automated suite cannot be the whole story here.
`ui-regression` deliberately touches no LLM path (it costs money and is
externally flaky), the icon catalogue lives behind an external webhook, and
provider switching is a local-environment concern. Those paths are real, they
break, and nothing in CI watches them. This stage is where they get written
down as cases a human can execute.

Read `aidlc/spaces/<active-space>/knowledge/aidlc-quality-agent/test-case-authoring.md`
before writing anything. It carries the authoring standard, the manual-vs-automated
split, the TCMS field mapping, and the worked examples. This stage file says
*what to produce*; that file says *how to write it well*.

## Steps

### Step 1: Load Personas

Load aidlc-quality-agent (lead) persona from `agents/aidlc-quality-agent.md` and
knowledge from `.claude/knowledge/aidlc-quality-agent/`. Load
aidlc-developer-agent persona from `agents/aidlc-developer-agent.md` for the
automation-script side. Then load the team knowledge at
`aidlc/spaces/<active-space>/knowledge/aidlc-quality-agent/test-case-authoring.md`
— it is the authoring standard this stage is judged against.

Apply aidlc-quality-agent as the primary perspective; aidlc-developer-agent
decides where automated scripts land and what they can realistically assert.

### Step 2: Inventory What Needs Covering

Build a coverage inventory before writing any case. For this intent:

1. Read every acceptance criterion from `<record>/inception/user-stories/stories.md`.
2. Read `<record>/construction/build-and-test/build-and-test-summary.md` and the
   test-instruction files beside it — these say what the automated layer already
   asserts.
3. Read `<record>/construction/*/code-generation/code-summary.md` for every unit.
4. List each externally-observable behaviour this intent introduces or changes.

For each item, classify it into exactly one of three buckets:

| Bucket | Meaning | Where the case lives |
|---|---|---|
| Already automated | An existing or newly-written automated test asserts it | Automation plan only; no manual case |
| To be automated | Automatable and worth automating; script does not exist yet | Automation plan, with the script written this stage |
| Manual only | Cannot or should not be automated (costs money per run, needs an external service, needs human judgement, needs a real browser session against a real LLM) | Manual case in TCMS |

**Do not write a manual case for something the automated suite already asserts.**
Duplicate coverage in two sources of truth means two things to maintain and one
of them silently rots. `test-case-management-plan.md` fixes this: automated cases
are owned by the repo's spec code and only their metadata and results reach TCMS;
manual cases are owned by TCMS.

State the bucket counts in the summary. If a behaviour is unclassifiable, say so
rather than defaulting it to manual.

### Step 3: Write the Manual Test Cases

Create `<record>/construction/tcms-test-cases/manual-test-cases.md`.

This file is the **authored source** for every manual case; TCMS is the system of
record once synced, and the sync tool reads exactly this file. Its structure is
machine-parsed, so follow it exactly — the authoring knowledge file carries the
full template and a worked example.

Required per case:

- `## TC: <summary>` — the case title. Stable: it is the sync key. Renaming a
  title creates a second case in TCMS rather than updating the first.
- A `- plan:` / `- priority:` metadata block.
- **目的** — what this case protects, in one or two sentences.
- **背景** — why the case exists. For a regression case, state the defect it
  guards: the observed symptom, verbatim error text where one exists, and the
  reason the existing automated layer did not catch it. A regression case whose
  背景 does not say what broke is not reviewable a year later.
- **前置條件** — everything needed before step 1, with copy-pasteable commands.
- **測試步驟** — a numbered table of 操作 ↔ 預期結果. Each row is one action
  with one observable result. A step whose expected result is "正常" is not a
  step; say what "正常" looks like on screen or in the log.
- **通過條件** — the pass/fail line. Unambiguous.
- **追溯** — implementing files, the corresponding automated test if any, the
  PR/commit, and the user story id.

Optional but strongly encouraged for regression cases: a **失敗徵兆與對應肇因**
table mapping each plausible symptom to its cause. That table is what makes a
failed run actionable instead of just red.

Write in Traditional Chinese, per ADR-0009.

### Step 4: Write the Automation Plan and the Scripts

Create `<record>/construction/tcms-test-cases/automation-test-plan.md` covering
every item in the "to be automated" bucket:

- Which layer it belongs in, and why:
  - **Backend unit / behaviour** → `backend/tests/test_*.py`, stdlib `unittest`
    (this repo does not use pytest), `hypothesis` where a property is the honest
    assertion.
  - **Backend HTTP contract** → `starlette.testclient.TestClient`, asserting
    status code and the `response_model` field set. Required by `team.md` for any
    new or changed endpoint.
  - **Frontend end-to-end** → `frontend/tests/e2e/*.spec.ts`, Playwright. This is
    the only automated layer that reaches the UI; the repo has no frontend
    unit-test framework and adding one is out of this stage's scope.
- The concrete assertion each script makes — not "測試 X 正常" but the exact
  condition that fails when the defect returns.
- Where the script lives, and its test name.

Then **write the scripts**. This stage does not produce a wish list; the scripts
land in the repo in this stage, run green, and are referenced by path and test
name from the plan. A plan entry with no script is an open item and must be
listed as such in the summary, with the reason.

Every automated test — new or touched — also carries a structured spec comment
(`@purpose` / `@given` / `@step` / `@pass` / `@story`, see the authoring
knowledge file § 4.4). That comment is what gives the automated case a readable
description in TCMS. Writing the description in TCMS by hand instead is not an
option: the code is the copy that gets changed, so a hand-written description
goes stale with nothing to announce it.

For every script written, verify it actually catches what it claims:

```
# run the new tests
cd backend && .venv/bin/python -m unittest discover -s tests
cd frontend && npx playwright test
```

Then mutate the fix and confirm the test goes red. A test that passes against
the broken code protects nothing. Record the mutation and its result in the plan
— per `construction.md`, a test that always passes is not acceptable, and the
only proof is having seen it fail.

### Step 5: Verify — the gate before anything reaches TCMS

Run `/tcms-verify`. It is the blocking gate; nothing syncs before it passes.

The mechanical layer first:

```
python3 scripts/tcms_validate.py --all
```

It checks four things, all decidable: required sections present, no
undecidable expected results ("正常", "成功"), every traced path and test name
actually exists in the repo, and every declared API endpoint / UI route matches
`openapi.json` and `App.tsx`. A non-zero exit stops the stage here.

Then the semantic layer, per the skill: does each purpose point at a failure
that can actually happen; does a regression case say what broke and why the
automated layer missed it; can a person who was not in the room execute the
steps; does the declared interface list cover what the case actually touches;
is the pass condition binary; does it duplicate something the automated suite
already asserts; does it verify what the acceptance criterion actually says.

**Do not sync a case that failed verification and plan to fix it after.** A
wrong case in TCMS reads as evidence of coverage, and false coverage is worse
than none.

One class of ERROR is not a case defect: a traced path that lives on another
branch not yet merged. That is a real cross-branch dependency — state it and
confirm the merge order, do not delete the trace to make the check pass.

### Step 6: Sync to TCMS

Two syncs, two sources — they are not interchangeable. Generate
`<record>/construction/tcms-test-cases/tcms-sync-report.md` covering both.

**Manual cases** — authored in the record, executed in TCMS:

1. Preview — never write blind:
   ```
   python3 scripts/tcms_sync.py --file <record>/construction/tcms-test-cases/manual-test-cases.md --dry-run
   ```
2. Show the user the preview at the approval gate.
3. After approval, run without `--dry-run`.

**Automated cases** — the case is owned by the junit plugin; only the
description comes from here:

```
python3 scripts/tcms_sync.py --spec frontend/tests/e2e/regression.spec.ts --dry-run
python3 scripts/tcms_sync.py --spec frontend/tests/e2e/regression.spec.ts
```

This updates existing cases only. A test that has never run in CI has no case
yet — the tool lists those rather than creating orphans, and the sync report
records them.

The tool is idempotent: it keys on the case title, updating an existing case
rather than creating a duplicate. It requires `~/.tcms.conf`; if that file is
absent the sync is **not** silently skipped — record it as an open item in the
sync report and say so at the gate. A skipped sync that nobody notices is the
failure mode this whole stage exists to prevent.

Record in the sync report: cases created, cases updated, the TCMS plan they
landed in, and anything that did not sync plus why.

### Step 7: Completion Handoff

Hand completion to `stage-protocol.md` via
`bun .claude/tools/aidlc-orchestrate.ts report --stage tcms-test-cases --result <outcome>`.
The engine owns all lifecycle transitions and advancement.

### Step 8: Completion

Report at the gate:

- Coverage inventory: counts per bucket, and any unclassifiable behaviour.
- Manual cases written, by plan and priority.
- Automation scripts written, with paths, test names, and the mutation result
  proving each one fails against the defect.
- Any automation-plan entry left without a script, and why.
- TCMS sync outcome, including anything that did not sync.

This stage is **blocking** (`project.md` § Mandated). It may not be reported
complete while any externally-observable change from this intent sits in no
bucket at all.
