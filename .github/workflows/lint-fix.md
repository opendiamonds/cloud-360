---
description: "Lint Fixer — auto-fix the safe, mechanical frontend lint errors on a PR and flag the risky ones for a human."

on:
  pull_request:
    types: [opened, synchronize, reopened]
    # Excluded: the reverse-sync PR opened by the AIDLC <-> GitHub Projects sync
    # mechanism (U-8, .github/workflows/aidlc-sync-reverse-impl.yml). That PR
    # writes one field back into <record>/sync-state.json and opens a PR for it:
    # a machine-authored, single-field data change this workflow has nothing to
    # say about. Without this filter a reverse PR created SIX workflow runs,
    # this one among them.
    #
    # SIX -- and the two that remain -- are counted by parsing on.pull_request
    # out of every .yml/.lock.yml under .github/workflows, NOT by grepping the
    # *.md sources. GitHub runs the .lock.yml, and two of the triggered
    # workflows (ci.yml, aidlc-sync-forward.yml) are plain Actions with no .md
    # at all. An earlier revision of this comment said "five" because it counted
    # over the *.md set and then quoted a total meant to include them.
    #
    # WHAT STILL HAPPENS ON A REVERSE PR, with this filter in place:
    #   * ci.yml -- A RUN IS CREATED. Its `pull_request:` is bare (see below),
    #     so nothing filters it out. The `gate` job runs, reads the
    #     [aidlc-sync] marker off the PR head commit and sets is_sync=true;
    #     repo-contract / frontend / backend / docker-build then evaluate
    #     `if: needs.gate.outputs.is_sync != 'true'` to false and show up as
    #     Skipped. A ci.yml run with four Skipped jobs is the CORRECT outcome
    #     here -- it is not a sign this exclusion failed.
    #   * aidlc-sync-forward.yml -- A RUN IS CREATED (it filters on neither
    #     paths nor branches). Its orchestration step then hits guard 2
    #     (R-4.2 -- the same [aidlc-sync] marker) and exits 0 before it queries
    #     or writes the board. That forward-runs-on-a-reverse-PR overlap is
    #     open-items.md N:C-2 (Critical, unresolved, Bolt 2/3 gate); that item
    #     owns the decision, so do NOT add a paths-ignore there to silence it.
    #   * deploy.yml fires later, on merge (types: [closed], branches: [ut], no
    #     path filter). Logged for the gate; not this unit's to change.
    # These four -- ui-regression, pr-reviewer, lint-fix, contract-guard --
    # create no run at all. That is the whole delta: six down to two.
    #
    # The glob below is the same literal ci.yml carries (there it sits on
    # `on.push`; its pull_request side is deliberately bare). Read ci.yml's
    # stated reason with one qualifier that neither it nor check-ci-yml.py
    # carries: it argues -- and SEC-1d in that checker enforces as an absolute
    # -- that a pull_request paths filter "can never hold, because a PR always
    # contains other files". That is true of DEVELOPER PRs, which is what ci.yml
    # is reasoning about. It is false for this machine PR, whose changed-file
    # set is exactly one entry. Same glob: load-bearing on pull_request here,
    # forbidden on pull_request there, and both are right.
    # One mechanism, one glob -- change one, change both.
    #
    # THE ONE PREMISE THIS RESTS ON: `paths-ignore` skips a PR only when EVERY
    # changed file matches the pattern. It is not a majority vote. The reverse
    # PR touches exactly one file, and that is structural rather than lucky --
    # the commit_and_push whitelist in .github/actions/aidlc-sync-record/record.sh
    # accepts only <record_path>/sync-state.json, and aidlc-sync-reverse-impl.yml
    # passes exactly that one path in AIDLC_PATHS. ADD A SECOND FILE TO THE
    # REVERSE PR AND THIS EXCLUSION SILENTLY STOPS WORKING: no error, no failed
    # check, these four simply start running again. The cause would be a
    # change in U-8; the consequence lands here.
    #
    # A workflow filtered out this way is INVISIBLE, not marked skipped: GitHub
    # creates no run at all, so the Actions page shows nothing for it -- which
    # looks exactly like "this workflow was never configured". Do not read a
    # missing run on a reverse-sync PR as a broken workflow. Contrast ci.yml
    # above, which DOES appear and DOES show Skipped jobs: on a reverse PR you
    # should see two runs, not zero.
    paths-ignore:
      - "aidlc/spaces/*/intents/*/sync-state.json"
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
