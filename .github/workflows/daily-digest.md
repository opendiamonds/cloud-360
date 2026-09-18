---
description: "Daily Digest — one issue a day summarising what actually moved: PRs, issues, CI, and deploys."

on:
  schedule:
    - cron: "0 23 * * 1-5"
  workflow_dispatch:

permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read

engine: copilot

timeout-minutes: 20

network: defaults

tools:
  bash:
    - "git log"
    - "grep"
    - "ls"
    - "cat"
    - "head"
  github:
    toolsets: [context, repos, issues, pull_requests, actions]

safe-outputs:
  create-issue:
    max: 1
    labels: [digest]
  close-issue:
    max: 1
---

# Daily Digest

Once each weekday evening (23:00 UTC — early morning in Taipei), summarise what actually happened in **Cloud-360** in the last 24 hours, for someone who was not watching.

## What to gather

Use the GitHub tools:

- **Pull requests** — opened, merged, and closed-without-merge. For merged ones: what shipped, in one clause.
- **Issues** — opened and closed.
- **CI** — runs of the `CI` workflow on `main` and `ut`. Which failed, and on what.
- **Deploys** — runs of the `Deploy (ut → 192.168.10.10)` workflow. Did `ut` reach https://cloud360.danniel.cc, or did it fail?
- **Agentic workflows** — did Contract Guard, PR Reviewer, Issue Triage, Spec Sync, or Lint Fixer fail? A silently broken agent is worse than no agent, and this digest is where that surfaces.

## What to write

Create **one** issue titled `Daily digest: <YYYY-MM-DD>`, in Traditional Chinese (ADR-0009).

Lead with what a person would want to know first:

1. **Is anything broken?** Failing CI on `main` or `ut`, a failed deploy, a broken agentic workflow. If nothing is broken, say so in one line and move on.
2. **What shipped** — merged PRs, one line each, in plain language. Not the commit subject copied verbatim: say what changed for a user or a developer.
3. **What is waiting** — open PRs that are green and unreviewed, and issues opened today that nobody has answered.

Then close yesterday's digest issue (the most recent open issue labelled `digest`) with a one-line comment pointing at today's. Only close a digest issue — never anything else.

Keep it short. This is a digest, not a changelog: if a day had two merges and a green CI, that is three lines, not three sections. Skip empty sections entirely rather than writing "nothing to report" under each heading.

**If literally nothing happened in 24 hours — no PRs, no issues, no CI runs — create no issue and close nothing.** A digest of an empty day is noise, and a stream of noise gets muted, which is how a monitoring workflow dies.
