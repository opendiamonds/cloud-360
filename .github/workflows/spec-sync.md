---
description: "Spec Sync — when a code-bearing spec changes, open an issue listing the code that must be updated to conform."

on:
  push:
    branches:
      - ut
    paths:
      - "aidlc/spaces/*/intents/*/inception/application-design/frontend-backend-specification.md"
      - "aidlc/spaces/*/intents/*/construction/database-schema.md"
  workflow_dispatch:

permissions:
  contents: read
  issues: read

engine: copilot

timeout-minutes: 20

network: defaults

tools:
  bash:
    - "git diff"
    - "git log"
    - "git show"
    - "grep"
    - "ls"
    - "cat"
    - "head"
    - "tail"
    - "wc"
  github:
    toolsets: [context, repos, issues]

safe-outputs:
  create-issue:
    max: 1
    labels: [spec-drift]
---

# Spec Sync

Cloud-360 follows Spec-Driven Development: the specs in the active AI-DLC intent record (`aidlc/spaces/<space>/intents/<record>/`, shorthand `<record>/`) are the contract, and the code must conform to them — not the other way around. When a spec that maps directly to code changes, your job is to check whether the code still honours it, and if not, to write down exactly what code must change.

You run after a push to `ut` that touched one of:
- `<record>/inception/application-design/frontend-backend-specification.md` — API contracts, component design, ORM models
- `<record>/construction/database-schema.md` — tables, columns, relationships

You **do not change code** and you **do not open a pull request**. You open one issue describing the drift, for a human to implement (this respects the AIDLC human gate on code generation).

## Step 1 — See what the spec change requires

```
git log -1 --stat
git diff HEAD~1...HEAD -- 'aidlc/spaces/*/intents/*/inception/application-design/frontend-backend-specification.md' 'aidlc/spaces/*/intents/*/construction/database-schema.md'
```

Read only the spec diff. Work out what the change *requires of the code* — a new API field, a new route, a changed request/response shape, a new table or column, a changed permission rule, a new component behaviour.

## Step 2 — Check whether the code already conforms

For each requirement the spec now states, look at the code that would implement it and decide whether it already matches:

- API routes and shapes → `backend/main.py`, `backend/services/*_router.py`
- ORM models → `backend/models.py`
- Database schema → `schema_rbac.sql`, `schema.sql`
- Permissions → `backend/services/rbac.py`, the routers' authorization checks
- Frontend types / components / API calls → `frontend/src/`

**This is the crucial filter.** If the same push updated the code alongside the spec (they moved together), there is no drift — say nothing. Only genuine gaps count: the spec now says X, the code still does Y.

## Step 3 — Report, only if there is real drift

If the code already conforms, **open no issue**. A spec edit that the code already satisfies is not drift, and a "nothing to do" issue is noise.

If there is drift, open **one** issue titled `Spec drift: <spec file(s)> changed, code needs updating`. In Traditional Chinese (ADR-0009). For each gap, one entry:

1. **What the spec now requires** — quote the relevant line(s) from the spec diff.
2. **Where the code doesn't match** — the file and location, and what it currently does.
3. **What to change** — the concrete edit: the field to add, the route to change, the check to update. Be specific enough that whoever picks it up does not have to re-derive it.

Do not propose writing the code for them, do not speculate about changes the spec diff does not actually require, and do not flag style or unrelated issues. The issue is a work order derived strictly from the spec change — nothing more.
