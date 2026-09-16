---
name: aidlc-github-projects-sync
depth: Standard
keywords: []
description: Composed scope - README as intent requirement source + periodic AI-DLC stage progress sync to GitHub Projects Status
skeleton: off
---

# aidlc-github-projects-sync scope

A composed scope (ARS 54 / Standard) for building the integration between
AI-DLC and GitHub Projects: making the repo-root `README.md` the requirement
source for every intent, and periodically syncing each intent's AI-DLC stage
progress onto the Status field of the matching item in the `opendiamonds`
org Project #16.

Composed by the adaptive-workflows composer, not inferred. `keywords: []` is
deliberate: this scope resolves only via `--scope aidlc-github-projects-sync`
and never participates in scope detection.

## Entropy profile

| Component | Score | Band |
|-----------|-------|------|
| Intent Ambiguity (IAE) | 0.60 | MED |
| Codebase Structural Uncertainty (CSU) | 0.40 | MED |
| Verification Entropy (VE) | 0.60 | MED |
| Risk / Blast Radius (R) | 0.55 | MED |
| Unresolved Assumptions (UA) | 0.70 | HIGH |
| **Composite (advisory)** | **54 / 100** | **Standard** |

Scored on the fallback path: the CodeKB MCP server was not exposed, so the
structural components come from the workspace scan plus a bounded read of the
affected subgraph (`.github/workflows/`, `scripts/`, `.claude/hooks/`,
`aidlc/spaces/default/intents/`, `README.md`). No call-graph evidence.

UA dominates. The target side of the sync is pinned exactly (project id,
Status field id, six option names), but the mapping layer is undefined: how
the compiled stage graph collapses onto six Status options, how an intent
binds to a Project item when neither side carries the other's id, what
happens to the 71 items already on the board, and which artifact wins when
`intents.json` disagrees with a record's `Current Stage` / `Status`.

CSU stays MED-low because the affected surface is peripheral and strongly
precedented: `scripts/tcms_sync.py` is already an AI-DLC-artifact to
external-system sync with a parse / dry-run / write shape, and
`daily-digest.md` is already a cron-scheduled gh-aw workflow. No backend,
frontend, or database coupling.

## Membership

19 stages EXECUTE, 14 SKIP.

**Ideation** keeps the cheap framing spine (intent-capture,
scope-definition), plus feasibility - its condition clauses genuinely fire
here on the integration constraint and on a real viability question, since a
scheduled job can only observe committed state. market-research,
team-formation, and both mockup stages are folded out: there is no market,
one decision-maker, and no UI (the only interface is GitHub's own board,
which this work does not design).

**Inception** runs reverse-engineering, which the numeric screen missed on an
exact boundary. It is un-SKIPped because CodeKB is absent, so nothing else
writes the local RE artifact store that the design and generation stages
read, and because the sync's source of truth is AI-DLC's own state
representation, which is demonstrably inconsistent across existing records.
practices-discovery folds out: a full pass ran on 2026-08-09 and its output
is already on disk as an affirmed `team.md`. user-stories is kept against the
fold because the blocking `tcms-test-cases` stage consumes `stories.md`
acceptance criteria by name. units-generation and delivery-planning are
un-SKIPped: both are ALWAYS in the graph, the work splits into four units
with different failure modes, and under deploy-on-merge each Bolt boundary is
a live deployment.

**Construction** runs the full spine. functional-design is un-SKIPped because
the intent's entire risk concentrates in one piece of business logic - the
stage-to-Status state machine, with its idempotency and tie-breaking rules.
nfr-requirements pins the sync interval, GraphQL rate limits, and the
ADR-0006 token and audit-logging targets; nfr-design folds into it, since
these are single measurable targets rather than interacting NFRs.
infrastructure-design folds out - there is no new environment, service, or
cloud resource. `tcms-test-cases` is mandatory here, per
`aidlc/spaces/default/memory/project.md`.

**Operation** is entirely skipped. `deploy.yml` already ships deploy-on-merge
with rollback and self-healing, no environment is provisioned, performance is
not an explicit NFR for a handful of mutations on a cron, and a failed sync
is a normal PR fix rather than an incident. observability-setup was proposed
EXECUTE and folded to SKIP at the approval gate: it was starved of all five
of its inputs, and the visibility target it owned is carried by
nfr-requirements plus a run-report and dry-run from code-generation,
following the existing `daily-digest` and `deploy-doctor` precedents. That
fold is what makes this grid strict-clean with zero validator advisories.

## Skeleton

`skeleton: off`, consistent with the team stance recorded in
`aidlc/spaces/default/memory/team.md`. There is no pipeline to bootstrap:
this work adds a script and a scheduled workflow beside twelve existing
gh-aw precedents.
