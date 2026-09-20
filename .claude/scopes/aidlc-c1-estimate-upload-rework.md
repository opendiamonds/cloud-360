---
name: c1-estimate-upload-rework
depth: Standard
keywords: []
description: Composed scope - C1 cost estimation rework - replace the agent framework + pivot from scraping the official calculators to parsing user-uploaded AWS/Azure/GCP estimate exports
skeleton: off
---

# c1-estimate-upload-rework scope

A composed scope (ARS 68 / Standard) for the C1 cost-estimation rework:
replacing the current agent framework, and reversing the estimation flow so
that the user uploads the three clouds' official estimate exports and an
agent parses them into cost recommendations, instead of the system driving
the official pricing calculators itself.

Both changes stay inside one intent by explicit human decision at the
approval gate: the replacement framework carries the cost agent that the new
parse-and-advise flow depends on, so splitting them would force the upload
work to be built twice.

Composed by the adaptive-workflows composer, not inferred. `keywords: []` is
deliberate: this scope resolves only via `--scope c1-estimate-upload-rework`
and never participates in scope detection.

## Entropy profile

| Component | Score | Band |
|-----------|-------|------|
| Intent Ambiguity (IAE) | 0.70 | HIGH |
| Codebase Structural Uncertainty (CSU) | 0.72 | HIGH |
| Verification Entropy (VE) | 0.60 | MED |
| Risk / Blast Radius (R) | 0.62 | MED |
| Unresolved Assumptions (UA) | 0.78 | HIGH |
| **Composite (advisory)** | **68 / 100** | **Comprehensive** |

Scored on the fallback path: the CodeKB MCP server was not exposed, so the
structural components come from the workspace scan plus a bounded read of the
affected subgraph (`backend/cost/`, `backend/services/`,
`frontend/src/pages/CostPage.tsx`, `openapi.json`, `backend/Dockerfile`).
The local `aidlc/spaces/default/codekb/cloud/` store was rejected as stale —
it dates from 2026-08-19, while the affected code changed on 09-11 and 09-16.
No call-graph evidence.

UA dominates. The replacement agent framework is undecided, and so is the
accepted export format per cloud, the semantics of a "cost recommendation",
and which of the existing scraping code dies versus stays as a fallback.

CSU is HIGH on coupling rather than size. `claude-agent-sdk` is shared
infrastructure, not a C1-local dependency: it reaches `design_agent.py`,
`review_agent.py`, `wa_lens_engine.py`, `llm_provider.py`, `llm_limits.py`,
`backend/requirements.txt` and `backend/Dockerfile`, so the framework swap
blast radius is wider than the feature being reworked. On top of that, this
intent reverses the direction of work completed on 09-11 (the Playwright
calculator runners), which makes a meaningful block of `backend/cost/`
obsolete without yet defining which block.

The composite lands in the Comprehensive band (22-28 typical stages) but the
grid is deliberately leaner at 20. The entropy here is concentrated in
undecided decisions, not in breadth: one repo, one developer, staging-only
deployment, one feature surface. Per the composer's fold discipline, a
concentrated high score belongs at the lean end of its band.

## Membership

20 stages EXECUTE, 14 SKIP.

**Ideation** keeps the cheap framing spine (intent-capture, scope-definition)
plus feasibility, which is the load-bearing stage for this intent: it owns
the framework-replacement decision, evaluating candidates against OpenRouter
routing, the four existing consumer modules, and the `claude` CLI hard
dependency baked into the backend image. market-research folds into it — the
only build-vs-buy question here is that framework choice, which is a
technical evaluation rather than market positioning. team-formation folds out
(single developer, per the `danniel/` branch convention). rough-mockups folds
into refined-mockups: `CostPage.tsx` already exists, so one design pass
grounded in the current screen is enough. approval-handoff runs as the phase
gate.

**Inception** runs reverse-engineering — the fold that CodeKB coverage would
have justified does not apply, because CodeKB is absent and the local store
is stale, so nothing else writes the RE artifacts that the design and
generation stages read. It is also the only stage that will map the
framework fan-out as a single subgraph, which has never been done.
practices-discovery folds out: conventions are documented (`CLAUDE.md`,
`TESTING.md`, `team.md`, `project.md`) and mechanically enforced by six CI
gates and two contract validators, and a full pass already ran on this
codebase in the predecessor intent. requirements-analysis is kept for its
unique outputs — the per-cloud accepted-format matrix, the out-of-scope
boundary naming which scraping code dies, and the NFR extraction that
`nfr-requirements` consumes. user-stories folds into it (single persona: the
cloud architect on `/cost`), with the UX narrative carried by
refined-mockups. domain-design is un-SKIPped against the mechanical screen's
structural default, because the intent's core is a genuinely new building
block: one normalized estimate model that has to unify three different
official export schemas. units-generation, contract-design and
delivery-planning are likewise un-SKIPped — the work splits into at least
four units with real ordering constraints (the framework abstraction gates
the recommendation agent; the retirement of the obsolete scraper must land
only after the new path proves parity), and there are three contracts that
must be pinned before code: the normalized schema crossing the unit
boundary, the new upload endpoints consumed by the frontend and mechanically
diffed against `openapi.json`, and the agent abstraction that all three
existing consumers implement.

**Construction** runs the full spine. functional-design owns the per-cloud
parsing and normalization rules. nfr-requirements pins the untrusted-upload
security targets required by the ADR-0006 baseline (size limits, formula
injection, archive expansion) together with the property-based testing
mandate that ADR-0006 places on the cost calculator specifically. nfr-design
folds into it: these are single measurable targets with existing
implementation precedent (`llm_limits.py`), not interacting NFRs needing
their own design pass. infrastructure-design folds out — same container,
same staging host, same tunnel, no new cloud resources. ci-pipeline folds
out: the six existing gates are adequate and the VE gap is missing tests for
a new surface, which build-and-test and `tcms-test-cases` close, not missing
CI. `tcms-test-cases` is mandatory here per
`aidlc/spaces/default/memory/project.md`; the numeric screen defaulted it to
SKIP only because the plugin stage has no cost prior in `ars-priors.json`.

**Operation** is almost entirely skipped. The CD pipeline already ships
deploy-on-merge with rollback and self-healing, no environment is
provisioned (production stays out of scope per ADR-0001/0002/0007), no new
service means no observability setup, a failed deploy is a normal PR fix
rather than an incident, and performance is not an explicit NFR — the new
upload path is strictly faster than the Playwright scraping it replaces.
deployment-execution is the one exception: the framework swap changes
`backend/requirements.txt`, `backend/Dockerfile` and the `deploy/.env`
template rendered by `render-env.sh`, and the env contract validator will
fail the build if those move out of lockstep.

## Accepted validator advisories

The grid is valid with zero errors and six advisories, all of them expected
brownfield folds, disclosed and accepted at the approval gate:

- `refined-mockups` is starved of `wireframes` and `user-flow` from the
  folded `rough-mockups`. The existing `CostPage.tsx` is the ground truth it
  designs against.
- `tcms-test-cases` is starved of `stories` from the folded `user-stories`.
  It consumes the acceptance criteria in the requirements-analysis artifact
  instead. Note that the predecessor composed scope
  (`aidlc-github-projects-sync`) resolved this same tension the other way by
  keeping `user-stories`; here the single-persona fold was judged to hold.
  Un-SKIP trigger: `tcms-test-cases` cannot write executable cases without
  story-level acceptance criteria.
- `deployment-execution` is starved of `cd-config`, `deployment-strategy` and
  `environment-inventory` from the folded `deployment-pipeline` and
  `environment-provisioning`. All three already exist on disk
  (`deploy/docker-compose.deploy.yml`, `deploy/render-env.sh`, ADR-0007).

## Skeleton

`skeleton: off`, consistent with the team stance recorded in
`aidlc/spaces/default/memory/team.md` (Q3), and with the Q1 decision that the
predecessor intent `260819-cost-finops` runs without a skeleton gate.

Worth a second look before the first Construction Bolt, though: `team.md`
allows a per-intent opt-in for a large intent that introduces an entirely new
technology layer, and replacing the agent framework is arguably exactly that
case. The default is kept here because the pipeline is mature and the swap
lands inside an existing, already-deployed service rather than bootstrapping
a new one.
