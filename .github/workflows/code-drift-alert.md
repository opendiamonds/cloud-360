---
description: "Code Drift Alert — when a PR changes a contract-bearing code file without updating the matching spec, ask the author whether the spec should follow."

on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - "backend/main.py"
      - "backend/services/**"
      - "backend/models.py"
      - "schema_rbac.sql"
      - "schema.sql"
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

# Code Drift Alert

Cloud-360 is spec-driven: the specs in the active AI-DLC intent record (`aidlc/spaces/<space>/intents/<record>/`, shorthand `<record>/`) are the contract and the code conforms to them. This workflow guards the direction the [[spec-sync]] workflow does not — code moving ahead of its spec. When a pull request changes code that a spec describes, but does not update that spec, you ask the author to make a deliberate choice. You **never** edit the spec yourself — auto-rewriting a spec to match code is exactly the anti-pattern this project rejects (it launders drift into the contract).

## The mapping

These code files are governed by these specs:

| Code changed | Governing spec |
|---|---|
| `backend/services/*_router.py`, `backend/main.py` (routes, request/response shapes) | `<record>/inception/application-design/frontend-backend-specification.md` |
| `backend/models.py`, `schema_rbac.sql`, `schema.sql` (tables, columns, relationships) | `<record>/construction/database-schema.md` |
| `backend/services/rbac.py`, authorization checks in routers (permission rules) | `<record>/inception/application-design/frontend-backend-specification.md` (RBAC section) |

## Step 1 — See what this PR changed

Use the GitHub tools to list the files changed in this pull request, and read the diffs of the code files above. The changed-file list also tells you whether either governing spec was updated in the same PR.

## Step 2 — Decide whether this is drift worth flagging

Flag **only** a change that alters the contract a spec is responsible for, when that spec was **not** changed in this PR:

- a new, removed, or renamed API route
- a changed request or response shape (a field added/removed/retyped)
- a new or changed table, column, or relationship
- a changed authorization rule (who may do what)

Do **not** flag — stay silent — when:

- the governing spec **was** updated in the same PR (code and spec moved together — the correct case)
- the change is internal and preserves the contract: a refactor, a bug fix that restores intended behaviour, logging, error handling, performance, comments, or tests
- you are not confident the contract actually changed. A false alarm trains the author to ignore this workflow; when unsure, say nothing.

## Step 3 — Ask, don't assert

If and only if there is real, unaccompanied contract drift, post exactly one comment, in Traditional Chinese (ADR-0009):

1. **What changed** — the code file and the contract-level change (the field, route, or rule), quoted from the diff.
2. **The spec that should reflect it** — name the spec file and section, and state plainly that it was not updated in this PR.
3. **The choice** — ask the author to either update the spec in this PR (if this is a deliberate contract change) or confirm it is an implementation detail the spec need not track. Do not decide for them, and do not propose spec wording.

Keep it short. No preamble, no restating these instructions. If there is no unaccompanied contract drift, post nothing at all.
