# Org-Level Rules

> Framework defaults. Read with `team.md` and `project.md` from the active
> space. The resolver loads every applicable layer; narrower layers add
> specialisation and must not contradict broader policy.

## Way of Working

We use **trunk-based development** with `ut` as the integration trunk.
All work merges to `ut` via short-lived feature branches (typically
resolved within 1-2 days). Long-lived branches accumulate merge debt; we
avoid them.

For Construction worktrees, the worktree base branch is `ut` and the
merge target is `ut`.

`main` is the outward-facing release line, not a second trunk. It
receives merges from `ut`, never direct feature work. We keep one trunk
and gate releases via tags or environment-specific deployment configs —
not via long-lived release branches.

We **squash-merge** Bolt branches into `ut`. Each Bolt becomes one
commit on the trunk, named by the Bolt slug, with the full Bolt commit
history preserved on the source branch until the worktree is discarded.

Squash gives us a clean linear `ut` history that maps 1:1 to
delivery-planning's Bolt sequence. We accept the trade-off of losing
intermediate commits on `ut` because the audit log preserves the full
event sequence anyway.

## Walking Skeleton

When practices are scope-dependent, we run the walking-skeleton Bolt
**first** only when the active scope file declares `skeleton: on`. Bolt 1
is solo, gated, and the user explicitly approves before remaining Bolts
run.

We **skip the skeleton ceremony** when the active scope file declares
`skeleton: off`. The first Bolt runs like any other — there's nothing to
bootstrap.

After Bolt 1 ships (when it runs), the orchestrator fires the **ladder
prompt**: "How should the remaining Bolts run?" Options: continue
autonomously, gate every Bolt. The team picks per project. The choice
persists as `Construction Autonomy Mode` in `aidlc-state.md`.

## Testing Posture

We treat tests as a first-class deliverable in every Bolt. Specific
methodology — TDD, BDD, ATDD, or classic test-after — is captured by the
testing-strategy stage when it ships.

Until then, our default per scope is:
- `mvp`, `enterprise`, `feature`, `infra` → tests written alongside
  code; minimum 80% line coverage; tests run in CI before merge.
- `bugfix`, `security-patch` → regression test for the specific
  bug/vulnerability; existing test suite must remain green.
- `poc`, `refactor`, `workshop` → existing test suite remains green;
  no new test floor required.

Affirm a stricter posture in `team.md` if the team commits to one.

## Deployment

We **deploy on merge** to staging. A merge into `ut` triggers
`.github/workflows/deploy.yml`, which ships to our self-hosted staging
host (`192.168.10.10`), exposed publicly as `cloud360.danniel.cc`
through a Cloudflare Tunnel. See ADR-0007.

Cloud-provider **production is out of scope** for this repository (see
ADR-0001 / ADR-0002). There is no production deploy target to gate; any
change to that boundary needs a new ADR, not a config tweak.

Any high-risk action — IaC apply, IAM change, destructive cloud
operation — requires a plan + impact assessment + rollback path and a
human approval gate before execution.

## Code Style

We defer to project-level configurations:
- Formatter: Prettier (JS/TS), Black (Python), `gofmt` (Go), or
  language-default. Configured in repo root (`.prettierrc`,
  `pyproject.toml`, etc.).
- Linter: ESLint, Ruff, golangci-lint, etc. Run in CI before merge;
  failure blocks the PR.
- Naming conventions: language idiomatic (camelCase for JS/TS,
  snake_case for Python, etc.). No project-wide rename rules unless
  team affirms one.

When the framework makes a code-style suggestion, agents read the
project's linter config first; the agent's suggestion only fires if the
linter doesn't already cover it.

## Forbidden

<!-- Things agents must never do -->
<!-- Example: Do not ask questions about topics already decided in previous stages -->

## Mandated

<!-- Things agents must always do -->
<!-- Example: All architecture decisions must include an ADR -->

## Corrections

<!-- Self-learning loop appends here. -->
<!-- Use team.md to record team-wide additions and project.md for
     project-specific specialisation. The loader resolves org → team →
     project at session start and retains every applicable rule. -->
