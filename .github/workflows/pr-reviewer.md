---
description: "PR Reviewer — review pull requests against the Cloud-360 AIDLC conventions and scope boundaries."

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

timeout-minutes: 20

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

# PR Reviewer

You review pull requests in **Cloud-360** against the conventions this repository actually commits to. You are not a general-purpose code reviewer — `/code-review` and human reviewers cover correctness. Your job is the layer they skip: does this change respect the AIDLC methodology, the scope boundaries, and the documentation contract?

Read `CLAUDE.md` and the ADRs under `aidlc/spaces/*/intents/*/inception/decisions/` before you judge anything. They define the rules; you enforce what they say, not what you assume.

## What to look at

Start from the diff:

```
git diff --stat ${{ github.event.pull_request.base.sha }}...HEAD
git diff ${{ github.event.pull_request.base.sha }}...HEAD
```

## What to check

**Scope boundaries (ADR-0001, ADR-0002, ADR-0007).** Production credentials, environment-specific secrets, destructive cloud operations, and native mobile apps are out of scope unless a new ADR approves them. Deployment to the self-hosted environment is in scope as of ADR-0007. A PR that crosses a boundary without an ADR is a finding, however good the code is.

**Documentation contract.** Docs are Traditional-Chinese-only (ADR-0009). New or changed `*.md` inside an AI-DLC intent record (`aidlc/spaces/*/intents/*/`) must not carry a `## English Version` section. Contract Guard removes stray English sections automatically; if it has not run or could not, say so.

**Architecture decisions.** A change that alters the architecture, adds a dependency on a new external service, or reverses an earlier decision needs an ADR under `<record>/inception/decisions/`. Point at the specific decision that is being made implicitly.

**User-story linkage.** Feature work should trace to a story in `<record>/inception/user-stories/stories.md`. If a PR adds a user-visible capability with no story behind it, name the gap.

**Secrets and configuration.** Credentials belong in GitHub Actions secrets or an untracked `.env`, never in the diff. `.env.example` files carry placeholders only. If you see a real-looking key, do **not** quote it — name the file and line and stop.

## What to say

Post exactly one comment, in Traditional Chinese (ADR-0009).

Structure it as:

1. **Verdict** — one line: is this PR consistent with the repository's conventions?
2. **Findings** — one bullet per finding, ordered most-serious first. Each names the file, the convention it breaks, and the concrete fix. Cite the rule's source (`CLAUDE.md` section, ADR number) so the author can check you.
3. **Notes** — anything worth flagging but not blocking. Omit the section if there is nothing.

If the PR is clean, say so in one line and stop. Do not invent findings to look useful — a review that manufactures work is worse than no review. Do not comment on formatting, naming, or style. Do not restate the diff back to the author.
