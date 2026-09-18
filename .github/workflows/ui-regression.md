---
description: "UI Regression — run the Playwright suite against an ephemeral stack on every PR and report the failing cases."

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: read

engine: copilot

# NOTE (#513): this bounds only the *agent execution step* (the Copilot CLI
# call) — gh-aw compiles it onto that step, not onto the agent job. The
# pre-agent-steps below are NOT covered; they inherit GitHub's 360-minute
# default — and that default has been reached in anger: on PR #510 a stalled
# browser download ran 5h59m24s before GitHub killed the job at the 6-hour
# limit, leaving no downloadable log. It was re-run and stalled again, ~7 hours
# of runner time on one PR for zero tests executed.
#
# The obvious fix — `timeout-minutes:` on each pre-agent step — DOES NOT WORK:
# gh-aw silently strips that key when compiling pre-agent-steps — verified on
# v0.81.6 and again on v0.86.2, so do not assume a compiler bump fixed it
# (`env`, `id`, `if`, `uses`, `with`, `working-directory` and
# `continue-on-error` all survive; `timeout-minutes` does not) and reports
# 0 errors / 0 warnings. Verify with `gh aw compile ui-regression` then
# `grep timeout-minutes` on the .lock.yml before trusting it.
#
# So every long-running pre-agent step wraps its own commands in `timeout(1)`
# instead — that lives inside `run:` where the compiler cannot drop it.
# Keep it that way when adding steps.
timeout-minutes: 30

network: defaults

# Deterministic work runs here, before the agent: build the stack, run
# Playwright, tear the stack down. The agent's only job is to read the JSON
# report and explain the failures — it never runs the tests itself.
pre-agent-steps:
  - uses: actions/checkout@v4

  - uses: actions/setup-node@v4
    with:
      node-version: '22'
      cache: npm
      cache-dependency-path: frontend/package-lock.json

  - name: Build and start the ephemeral test stack
    env:
      POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
      JWT_SECRET: ${{ secrets.JWT_SECRET }}
    # Two observed samples: 56s (warm layer cache) and 3m18s (cold, on a fresh
    # branch) — 3.5x spread, the widest of any step here, because it pulls base
    # images from an external registry. 20m is ~6x the slow sample; 15m would
    # have been only 4.5x, and a spurious red on a legitimately slow build is
    # the same pathology this whole change is fixing (a gate people learn to
    # ignore). Erring high still fails 18x faster than the 360m default.
    run: |
      timeout 20m docker compose -f deploy/docker-compose.test.yml up -d --build || {
        echo "docker compose up exceeded 20m (or failed); see exit code above" >&2
        exit 1
      }

  - name: Wait for the stack to answer on 8090
    run: |
      for i in $(seq 1 40); do
        if curl -fsS -o /dev/null http://localhost:8090/; then
          echo "stack up"; exit 0
        fi
        sleep 5
      done
      echo "stack did not come up on 8090" >&2
      docker compose -f deploy/docker-compose.test.yml ps
      docker compose -f deploy/docker-compose.test.yml logs --tail=100
      exit 1

  # `npx playwright install` pulls ~294 MiB from cdn.playwright.dev on every
  # run — Chrome for Testing 177 MiB + chrome-headless-shell 114.2 MiB + ffmpeg
  # 2.3 MiB (full download list from run 32540341190; an earlier reading of only
  # the log tail undercounted this as ~117 MiB by missing the first artifact).
  # setup-node's `cache: npm` does not cover ~/.cache/ms-playwright, so that
  # download is the job's only large, uncached third-party dependency.
  # The key is the lockfile hash: a Playwright version bump misses the cache and
  # re-downloads, which is the correct behaviour.
  - name: Cache Playwright browsers
    uses: actions/cache@v4
    with:
      path: ~/.cache/ms-playwright
      key: ${{ runner.os }}-ms-playwright-${{ hashFiles('frontend/package-lock.json') }}
      # The exact key is the whole lockfile, so ANY dependency bump invalidates
      # it — but the browser binaries only track the Playwright version, not the
      # other ~207 packages. That is not theoretical: `ut` and PR #523 produced
      # two different hashes within the same hour because b8d69a6 touched the
      # lockfile in between, wasting the freshly seeded cache.
      #
      # The prefix fallback restores whatever browser directory exists on a near
      # miss; `playwright install` then downloads only what is missing (nothing,
      # when the Playwright version is unchanged). Cost: the directory can
      # accumulate superseded browser builds — Playwright ignores versions it
      # does not need, so this is disk, not correctness.
      restore-keys: ${{ runner.os }}-ms-playwright-

  - name: Install Playwright and browsers
    working-directory: frontend
    # Baselines: npm ci 5s (registry, cushioned by setup-node's npm cache),
    # browser download 23s. Bounded separately so the log says which one stalled
    # — the question we could not answer for the run that started #513, because
    # a cancelled job leaves no downloadable log at all.
    run: |
      timeout 3m npm ci || { echo "npm ci exceeded 3m (or failed)" >&2; exit 1; }
      timeout 8m npx playwright install --with-deps chromium || {
        echo "playwright browser install exceeded 8m (or failed)" >&2
        exit 1
      }

  - name: Run the regression suite
    working-directory: frontend
    id: playwright
    # continue-on-error so a failing suite still lets the agent comment; the
    # red gate is re-asserted in post-steps after the comment is posted.
    continue-on-error: true
    env:
      BASE_URL: http://localhost:8090
      PW_RUN_ID: ${{ github.run_id }}
    # Baseline 39s for 14 tests. 15m lets the suite grow several-fold while
    # still catching a hung browser.
    run: timeout 15m npx playwright test

  # Record this run in Kiwi TCMS for the trend dashboard. Best-effort: a Kiwi
  # outage must never block a PR, so continue-on-error, and it runs whether the
  # suite passed or failed (the dashboard needs the failures too). GITHUB_* are
  # read from the runner env rather than ${{ }} to stay clear of gh-aw's
  # expression allow-list.
  # Baseline 36s. continue-on-error covers a Kiwi *error*, not a Kiwi *hang* —
  # without the timeouts below, an unresponsive Kiwi would park the job for 360
  # minutes. The three network-bound commands are bounded individually.
  - name: Report results to Kiwi TCMS
    if: always()
    continue-on-error: true
    working-directory: frontend
    env:
      KIWI_TCMS_URL: ${{ secrets.KIWI_TCMS_URL }}
      KIWI_TCMS_USERNAME: ${{ secrets.KIWI_TCMS_USERNAME }}
      KIWI_TCMS_PASSWORD: ${{ secrets.KIWI_TCMS_PASSWORD }}
      TCMS_PRODUCT: Cloud-360
    run: |
      if [ ! -f junit.xml ]; then
        echo "no junit.xml produced — skipping Kiwi report"
        exit 0
      fi
      # tcms-api reads connection settings from ~/.tcms.conf, not env vars.
      umask 077
      cat > "$HOME/.tcms.conf" <<EOF
      [tcms]
      url = ${KIWI_TCMS_URL}
      username = ${KIWI_TCMS_USERNAME}
      password = ${KIWI_TCMS_PASSWORD}
      EOF
      # Playwright's junit timestamps carry milliseconds and a trailing Z
      # (2026-07-13T00:57:57.203Z) which the plugin's parser rejects; trim to
      # whole seconds.
      sed -E 's/(timestamp="[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})\.[0-9]+Z?"/\1"/g' junit.xml > junit.kiwi.xml
      export TCMS_PRODUCT_VERSION="${GITHUB_HEAD_REF:-$GITHUB_REF_NAME}"
      export TCMS_BUILD="${GITHUB_RUN_ID}-$(echo "${GITHUB_SHA}" | cut -c1-7)"
      timeout 3m pip install --quiet kiwitcms-junit.xml-plugin
      # --summary-template '${name}' drops the "regression.spec.ts." classname
      # prefix so the Kiwi case name is just the test title. Single-quoted so
      # bash does not expand it. The template must stay stable — it is the key
      # the plugin reuses cases by; changing it orphans the old cases.
      timeout 5m tcms-junit.xml-plugin --summary-template '${name}' junit.kiwi.xml
      # This Kiwi instance is shared across projects. Tag every case "Cloud-360"
      # (Product is the structural separator; the tag aids cross-project views)
      # and mark it is_automated so manual cases stay distinguishable. Idempotent.
      timeout 3m python3 -c "
      from tcms_api import TCMS
      rpc = TCMS().exec
      prod = rpc.Product.filter({'name': 'Cloud-360'})
      cases = rpc.TestCase.filter({'category__product': prod[0]['id']}) if prod else []
      for c in cases:
          rpc.TestCase.add_tag(c['id'], 'Cloud-360')
          rpc.TestCase.update(c['id'], {'is_automated': True})
      print('processed', len(cases), 'Cloud-360 cases')
      "
      rm -f "$HOME/.tcms.conf"

# The report lives at frontend/pw-report.json (see playwright.config.ts). Let
# the agent read it with these bash tools; it needs nothing else.
tools:
  bash:
    - "cat"
    - "ls"
    - "head"
    - "tail"
    - "grep"
    - "wc"

safe-outputs:
  add-comment:
    max: 1
    target: triggering

# Cleanup first (always), then re-raise the failure so the PR check goes red
# when tests failed — the comment is informational, this is the gate.
post-steps:
  - name: Tear down the test stack
    if: always()
    run: docker compose -f deploy/docker-compose.test.yml down -v || true

  - name: Fail the job if any test failed
    if: always()
    working-directory: frontend
    run: |
      if [ ! -f pw-report.json ]; then
        echo "no Playwright report produced — the suite did not run" >&2
        exit 1
      fi
      # Playwright's json reporter records the failure count in stats.unexpected
      # (a retried-then-passed test is stats.flaky, which we allow). Read it
      # authoritatively rather than grepping the nested results.
      unexpected=$(jq '.stats.unexpected' pw-report.json)
      flaky=$(jq '.stats.flaky' pw-report.json)
      echo "unexpected=${unexpected} flaky=${flaky}"
      if [ "${unexpected}" != "0" ]; then
        echo "Playwright reported ${unexpected} failing test(s)" >&2
        exit 1
      fi
      echo "all Playwright tests passed"
---

# UI Regression Reporter

An ephemeral copy of the Cloud-360 stack was just built from this pull request and driven by the Playwright regression suite. Your job is to read the machine-readable result and tell the author, in one PR comment, exactly what failed and why — nothing more.

## Read the result

The JSON report is at `frontend/pw-report.json` (Playwright's `json` reporter). Read it. Its structure nests `suites[].specs[].tests[].results[]`; each spec has a `title` and an `ok` boolean, and failed results carry an `error` with a `message` and a `snippet`.

Do not run any tests yourself, and do not trust the surrounding CI logs over the report — the JSON is the source of truth for what passed and failed.

## Comment

Post exactly one comment, in Traditional Chinese (ADR-0009).

- **If every test passed**, say so in one line per language, and stop. Do not list the passing cases.
- **If any test failed**, lead with the count (e.g. "2 of 6 UI regression tests failed"). Then, one bullet per failed test:
  - the test title (the human-readable spec name, e.g. *"admin logs in and reaches the workspace"*),
  - the assertion or error that failed, quoted from the report's `error.message` — trimmed to the meaningful line, not the whole stack,
  - if the message makes the cause obvious (a selector that no longer matches, a navigation that did not happen, a timeout), say so in a few words. If it does not, say what the test was checking and stop — do not invent a root cause you cannot see in the report.

Keep it tight and factual. No preamble, no restating these instructions, no praise, no advice about how to fix beyond what the error plainly implies. The author wants to know which cases broke and what the failure was, so they can open the trace — that is the whole deliverable.
