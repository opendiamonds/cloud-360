---
description: "Lint Fixer — auto-fix the safe, mechanical frontend lint errors on a PR and flag the risky ones for a human."

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read

engine: copilot

timeout-minutes: 25

network: defaults

# No pre-agent-steps: a second checkout there fights gh-aw's own PR-branch
# checkout and makes push-to-pull-request-branch compute a patch against the
# base, which then trips the protected-files guard. The agent runs eslint
# itself in gh-aw's checkout, so the pushed patch is only what it actually
# changed (registry.npmjs.org is on the firewall allow-list).
tools:
  edit:
  bash:
    - "npm"
    - "npx"
    - "cd"
    - "git diff"
    - "git status"
    - "cat"
    - "head"
    - "tail"
    - "grep"
    - "ls"
    - "wc"

safe-outputs:
  add-comment:
    max: 1
    target: triggering
  push-to-pull-request-branch:
    target: triggering
    max: 1
---

# Lint Fixer

You fix the **safe, mechanical** ESLint errors in the Cloud-360 frontend (`frontend/`) on this pull request, and you leave the risky ones alone. The point is to clear trivial noise automatically without ever touching logic a human must review.

## Find the problems

Work in `frontend/`:

```
cd frontend
npm ci
npx eslint . --fix                # apply anything auto-fixable first
npx eslint . -f json -o eslint-report.json   # capture what remains
```

Read `eslint-report.json`. It is the authoritative list — do not go hunting for other things to change.

## What you MAY fix

Only these rule categories, and only when the fix is unambiguous:

- **`@typescript-eslint/no-unused-vars`** — remove the unused binding. For an unused `catch` error, use optional catch binding — `} catch {` with no parameter — rather than renaming to `_err`: this repo's ESLint config has no underscore-ignore pattern, so `_err` still counts as unused. Only rename to a leading underscore when the binding cannot be dropped (e.g. a positional callback argument before one that is used) AND you have confirmed the config ignores it.
- **`@typescript-eslint/no-explicit-any`** — replace `any` with the concrete type **only when the correct type is obvious from the surrounding code** (the shape is built a few lines away, or an existing interface fits). If the right type is not obvious, do NOT guess `unknown` or invent a type — leave it and report it.
- Other purely-syntactic rules where the fix cannot change behaviour.

## What you MUST NOT touch

Off limits no matter what the report says — they change runtime behaviour or component structure and a frontend owner must review them:

- **`react-hooks/set-state-in-effect`** — do not rewrite `useEffect` bodies. One is the auth bootstrap that reads the token from `localStorage`; a wrong "fix" silently breaks login.
- **`react-hooks/exhaustive-deps`** — do not edit hook dependency arrays.
- **`react-refresh/only-export-components`** — do not split files or move exports (e.g. pulling `useAuth` out of the context module).
- Anything outside `frontend/src/`. No `backend/`, no tests, no config, no CI, no docs. If your change would touch a file outside `frontend/src/`, do not make it.

If you are unsure whether a fix is safe, it is not. Leave it.

## After fixing

1. Run `npm run build` in `frontend/` (that is `tsc -b && vite build`). If your change does not compile, it is wrong — revert it. Never push code that fails to build.
2. Re-run `npx eslint .` to confirm the errors you targeted are gone.
3. If you changed nothing, push nothing.

Delete `eslint-report.json` before you finish so it is not part of the pushed change.

## Deliver

- If you fixed anything, push it to this PR's branch. The push must contain only your `frontend/src/` edits — nothing else.
- The commit message you pass to `push_to_pull_request_branch` must follow ADR-0010: Traditional Chinese, with a Chinese conventional-commit type. Use `修正(frontend):` followed by a short Chinese description of what you fixed — for example `修正(frontend): 移除未使用的變數與 catch 參數`. Keep the scope `(frontend)` in English; never write an English type such as `fix` or `chore`.
- Post exactly one comment, in Traditional Chinese (ADR-0009):
  1. **Auto-fixed** — each error you fixed: file, rule, and what you changed, one line each.
  2. **Needs a human** — each error you deliberately left, with the rule and why (touches auth/effects/exports, or the type is not locally obvious). Reference issue #427 if it tracks them.
  3. If lint still shows errors you could not safely fix, say so plainly — do not imply the PR is green when it is not.

No preamble, no restating these instructions. If there were no fixable errors, say so in one line and stop.
