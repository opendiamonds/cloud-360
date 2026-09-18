---
description: "Local Dev Drift — when a PR changes something LOCAL-DEV.md documents as a prerequisite without updating that document, ask the author whether it should follow."

on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - "backend/database.py"
      - "deploy/nginx.conf"
      - "deploy/render-env.sh"
      - "backend/.env.example"
      - "frontend/.env.example"
      - "deploy/.env.example"
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read

engine: copilot

timeout-minutes: 15

network: defaults

tools:
  bash:
    - "git diff"
    - "git log"
    - "grep"
    - "ls"
    - "cat"
    - "head"
    - "tail"
    - "wc"
  github:
    toolsets: [context, repos, pull_requests]

safe-outputs:
  add-comment:
    max: 1
    target: triggering
---

# Local Dev Drift

`LOCAL-DEV.md` is the only document that records what a developer needs in order to run **every** Cloud-360 feature on their own machine. Some of those prerequisites are implicit — they are not in `requirements.txt`, not in `package.json`, and nothing fails loudly when they are missing. That is precisely why the document going stale is expensive: it does not look stale, it looks correct, and the developer following it hits a failure the document promised would not happen.

This workflow guards that document against the files whose changes invalidate it. You **never** edit `LOCAL-DEV.md` yourself — you ask the author, because only they know whether their change alters what a developer must do.

The rule this enforces is stated in `aidlc/spaces/default/memory/project.md` under `## Mandated`. If the two ever disagree, `project.md` is the source of truth and this workflow is the one that is wrong.

## The mapping

| Changed file | Why LOCAL-DEV.md depends on it |
|---|---|
| `backend/database.py` | The `_ensure_*_schema()` startup patches are one of the two schema-evolution paths the document explains; §2 tells developers which changes need a database rebuild and which do not |
| `deploy/nginx.conf` | §8 explains what the Docker mode verifies that bare-metal cannot (the reverse-proxy and SSE paths) |
| `deploy/render-env.sh` | §3 and §10 describe how deploy-time configuration is produced and how it stays separate from local dev |
| `backend/.env.example`, `frontend/.env.example` | §3 and §4 tell developers which variables to set; a new or renamed variable that the document does not mention is a variable nobody will set |
| `deploy/.env.example` | §3 states the boundary between local-dev and deploy configuration; a change to what deploy owns can move that boundary |

## Step 1 — See what this PR changed

Use the GitHub tools to list the files changed in this pull request and read the diffs of the files above. The changed-file list also tells you whether `LOCAL-DEV.md` was updated in the same PR.

## Step 2 — Decide whether this is drift worth flagging

Flag **only** a change that alters what a developer must know or do to run the project locally, when `LOCAL-DEV.md` was **not** changed in this PR:

- a new, renamed, or removed environment variable a developer has to set
- a changed default that the document quotes (a port, a connection string, a model slug)
- a new startup-time schema patch, or a change to which schema path applies
- a new prerequisite: a binary, a service, a credential, a one-time setup step
- a change to how deploy-time configuration is produced, when the document describes that process

Do **not** flag — stay silent — when:

- `LOCAL-DEV.md` **was** updated in the same PR (they moved together — the correct case)
- the change is invisible to a developer running locally: a comment, a reworded error message, an internal refactor, a formatting change, a test
- the change only affects the deployment host and the document does not describe that behaviour
- you are not confident a developer's setup steps actually change. A false alarm trains the author to ignore this workflow; when unsure, say nothing.

## Step 3 — Ask, don't assert

If and only if there is real, unaccompanied drift, post exactly one comment, in Traditional Chinese (ADR-0009):

1. **What changed** — the file and the developer-visible change, quoted from the diff.
2. **Which part of LOCAL-DEV.md it affects** — name the section, and state plainly that the document was not updated in this PR.
3. **The choice** — ask the author to either update `LOCAL-DEV.md` in this PR, or confirm the change does not alter local setup. Do not decide for them, and do not propose replacement wording.

Keep it short. No preamble, no restating these instructions. If there is no unaccompanied drift, post nothing at all.
