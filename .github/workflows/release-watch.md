---
description: "Release Watch — track upstream releases that Cloud-360 depends on and open an issue when an upgrade is worth taking."

on:
  # Fuzzy schedule: gh-aw scatters the exact minute so every repo on the
  # planet does not hammer the API at 01:00 Monday.
  schedule: weekly on monday
  workflow_dispatch:

permissions:
  contents: read
  issues: read

engine: copilot

timeout-minutes: 25

network: defaults

tools:
  bash:
    - "grep"
    - "ls"
    - "cat"
    - "head"
    - "tail"
  github:
    toolsets: [context, repos, issues]

safe-outputs:
  create-issue:
    max: 1
    labels: [dependencies]
---

# Release Watch

Once a week, check whether the things Cloud-360 is pinned to have moved, and tell the team only when it matters.

## What to watch

**The AIDLC framework.** The `AIDLC_VERSION` constant in `.claude/tools/aidlc-version.ts` records the AI-DLC v2 version this repo vendored from [`awslabs/aidlc-workflows`](https://github.com/awslabs/aidlc-workflows) (the `v2` branch, `dist/claude/`). Compare it against the latest release. An upgrade here is not a routine bump — per `CLAUDE.md` §7 it requires re-copying `dist/claude/` over `.claude/`, restoring the local `settings.json` delta documented in `.claude/README-cloud360.md`, leaving the `aidlc/` workspace untouched, re-running `/aidlc --doctor` plus `scripts/validate_repo_contract.py`, and recording the upgrade in a new ADR.

**gh-aw.** The agentic workflows under `.github/workflows/*.md` compile with `gh aw`. Check [`github/gh-aw`](https://github.com/github/gh-aw) releases for breaking changes to frontmatter, safe-outputs, or the engine contract.

**Direct dependencies.** `backend/requirements.txt` and `frontend/package.json` — but only report a dependency when there is a reason to move: a security advisory, a breaking change that affects code in this repo, or a fix for a problem this repo actually has.

Use the GitHub tools to read releases and changelogs. Read the actual release notes; do not infer what a version number means.

## What to report

Open **one** issue, and only if there is something worth acting on. Title it `Release watch: <date>`.

The body is in Traditional Chinese (ADR-0009) and, for each upgrade worth taking:

1. **What moved** — component, current version in this repo, latest version, and a link to the release notes.
2. **Why it matters here** — the specific thing in *this* codebase that the change affects. Not the vendor's summary; your reading of it against these files. If you cannot name what it affects here, it does not belong in the issue.
3. **What upgrading costs** — the steps, the risk, and what to verify afterwards. For AIDLC, spell out the custom-file preservation dance and the ADR.
4. **Recommendation** — take it now, take it later, or skip. Commit to one.

**If nothing moved, or nothing that moved matters, create no issue.** A weekly "no changes" issue trains everyone to ignore this workflow, which costs more than the workflow is worth. Silence is the correct output.

Do not list every available version bump. A wall of routine patch upgrades is noise, and noise is what this workflow exists to filter out.
