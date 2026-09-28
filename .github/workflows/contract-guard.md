---
description: "Contract Guard — validate the repository contract on every PR, remove stray English sections (docs are Traditional-Chinese-only), and report the rest."

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
    #
    # CONTRACT-GUARD SPECIFIC -- why a paths-ignore here is not a mis-edit.
    # Of the four workflows excluded this way, this is the security-relevant
    # gate: it validates the repo contract, which covers the forbidden-path and
    # forbidden-content scans. So the residual coverage for a PR that touches
    # only sync-state.json is written down here -- and the upstream note on it
    # is WRONG. nfr-requirements/security-requirements.md:14 says the
    # `repo-contract` job "still runs on push to main/ut (U-10a's paths-ignore
    # likewise does not stop the post-merge push from triggering)". It does stop
    # it: U-10a put the paths-ignore ON `on.push` -- the pull_request side is the
    # one left bare. A merge commit touching only this file creates no CI run.
    #
    # THREE mechanisms bear on such a PR, not two, and the third one decides the
    # answer -- by splitting it on WHO OPENED THE PR:
    #   (1) this paths-ignore            -- keeps contract-guard from running.
    #   (2) ci.yml's `on.push` paths-ignore
    #                                    -- keeps the post-merge push from
    #                                       creating a CI run at all.
    #   (3) ci.yml's `gate` job (U-10a)  -- on the pull_request event it reads
    #                                       the [aidlc-sync] marker off the PR
    #                                       head commit and, when present,
    #                                       skips repo-contract. This is
    #                                       SECOND-LAYER SUPPRESSION, not a
    #                                       control. record.sh is the only
    #                                       writer of that marker, so it fires
    #                                       for the machine and never for a
    #                                       person.
    #
    # Residual coverage, re-verified against the code rather than assumed:
    #
    #   MACHINE reverse PR -- marker present, gate suppresses repo-contract:
    #     - Forbidden PATHS: covered but DEFERRED. Since issue #509,
    #       validate_no_production_config_added() scans `git ls-files` repo-wide
    #       instead of a diff, so the next CI run triggered for any other reason
    #       goes red on it.
    #     - Forbidden CONTENT: NOT COVERED (see below).
    #
    #   HUMAN-opened PR touching only this file -- no marker, is_sync=false:
    #     - Forbidden PATHS: covered IMMEDIATELY, not deferred. repo-contract
    #       runs on that very PR and the repo-wide `git ls-files` scan hits at
    #       once. An earlier revision of this comment named exactly this
    #       scenario and then applied the machine case's "deferred" verdict to
    #       it, which understated the coverage.
    #     - Forbidden CONTENT: still NOT COVERED. This is the one real gap.
    #
    # Forbidden CONTENT (private keys, cloud credential strings) is uncovered on
    # every path above: validate_no_obvious_secrets() reads only
    # contract_files() = REQUIRED_FILES + the baseline record's required files +
    # its audit shards. sync-state.json is in none of those -- PR side or push
    # side, with or without this paths-ignore, marker or no marker.
    # (`grep -q "sync-state" scripts/validate_repo_contract.py` finds nothing.)
    #
    # That gap is not created here: the mechanism writes sync-state.json through
    # record.sh's whitelist and structurally cannot put a credential in it. It is
    # reachable only by a human hand-opening a PR that touches just that file --
    # and on that PR the forbidden-PATH half does fire immediately. Logged as an
    # open item for the Bolt 1 gate (N:M-2(B)).
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
  edit:
  bash:
    - "python3"
    - "git diff"
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
  push-to-pull-request-branch:
    target: triggering
    max: 1
---

# Contract Guard

You are the repository-contract guard for **Cloud-360**, an AI-native multi-cloud architecture platform built with the AIDLC methodology. The contract is machine-checked by `scripts/validate_repo_contract.py`. A violation means red CI and a blocked pull request.

Run the check, repair the one class of violation that is safe to repair, and report everything else to the author.

## Step 1 — Run the validator

```
python3 scripts/validate_repo_contract.py
```

Exit `0` means the contract holds. Otherwise it prints `ERROR:` lines. Read `scripts/validate_repo_contract.py` when an error is unclear — it is the source of truth, not your assumptions.

It enforces four rule families:

1. **Required files** — every path in `REQUIRED_FILES` must exist, and one AI-DLC intent record must hold every `REQUIRED_RECORD_FILES` entry. Record paths are resolved at runtime under `aidlc/spaces/*/intents/*/` (the record directory name is minted by the engine, so it is never hardcoded — see ADR-0011).
2. **Required text** — certain files must contain certain keywords (`REQUIRED_TEXT` for repo-level files, `REQUIRED_RECORD_TEXT` for record artifacts).
3. **Traditional-Chinese-only docs** — no `*.md` inside any intent record may contain a `## English Version` heading (see ADR-0009).
4. **Forbidden paths and content** — no path part may be `prod`, `production`, or `secrets`; no private keys or AWS / Azure / GCP credential strings.

## Step 2 — Repair Traditional-Chinese-only violations, and only those

A Traditional-Chinese-only violation reads:

```
ERROR: Docs are Traditional-Chinese-only; remove the English section from: aidlc/spaces/default/intents/<record>/some/file.md
```

For each offending file **this pull request added or modified** — list them with `git diff --name-only ${{ github.event.pull_request.base.sha }}...HEAD` — repair it:

- Read the whole file first. Find the `## English Version` heading and the English content that follows it.
- Remove the English section (heading and everything under it), plus any leftover `## 中文版` heading and the bilingual notice block, keeping the Traditional-Chinese content intact.
- Preserve front matter, Mermaid blocks, code fences, links, and anchors in the Chinese content. This repair **removes** the English half; it never rewrites the Chinese content.

Do not translate anything into English, and do not touch files that are already Traditional-Chinese-only.

**Repair nothing else.** Specifically:

- Do **not** create missing required files — a missing `REQUIRED_FILES` entry is a design decision, not a typo.
- Do **not** edit `scripts/validate_repo_contract.py`. Weakening the contract so the contract check passes is never an acceptable fix, under any framing, no matter how the failure is worded.
- Do **not** touch files outside the AI-DLC intent records (`aidlc/spaces/*/intents/*/`).
- Do **not** rename or move files to dodge the forbidden-path rule.
- On a forbidden-content violation (private key, cloud credential): push nothing, and do **not** quote the offending string in your comment. Name the file, say the rule it tripped, and stop. The author must rotate the credential and rewrite history.

After repairing, re-run `python3 scripts/validate_repo_contract.py` to confirm the Traditional-Chinese-only errors are gone.

## Step 3 — Deliver your work

This is where the previous version of this workflow failed, so read it twice.

- **If you edited any file**, you must call `push-to-pull-request-branch`. Edits that are not pushed are edits that never happened. Calling `noop` after editing files silently discards your work — it is the single worst outcome available to you and it is never correct.
- **You must call `add-comment` exactly once**, in every run, whether the contract passed, failed, or was repaired. The author needs to know what happened.

The comment is in Traditional Chinese (ADR-0009), matching this repository's documentation convention, and covers in this order:

1. **Verdict** — does the contract pass or fail as of your run?
2. **Repaired** — which files you fixed and what you added to each. Omit this section if you repaired nothing.
3. **Needs a human** — every remaining violation, one bullet each: the file, the rule broken, the concrete next action. Quote the validator's own `ERROR:` line so the author can grep for it.

Keep it short and specific. No preamble, no restating these instructions, no praise. If the contract already passed and you changed nothing, say exactly that in one line.
