---
description: "Deploy Doctor — analyse a failed deployment run and open an issue with the root cause and a concrete fix."

on:
  workflow_dispatch:
    inputs:
      run_id:
        description: "The failed Deploy workflow run id"
        required: true
      pr_number:
        description: "The PR whose merge triggered the failed deploy"
        required: false
      failure_log:
        description: "Tail of the failed deploy log (best-effort, may be truncated)"
        required: false

permissions:
  contents: read
  actions: read
  issues: read

engine: copilot

timeout-minutes: 15

network: defaults

tools:
  bash:
    - "grep"
    - "cat"
    - "head"
    - "tail"
    - "wc"
  github:
    toolsets: [context, repos, actions, issues]

safe-outputs:
  create-issue:
    max: 1
    labels: [deploy-failure]
---

# Deploy Doctor

A deployment of Cloud-360 to the self-hosted host `192.168.10.10` just failed. The running service was automatically rolled back to the last-good version and a revert PR was opened; your job is the part a machine cannot do — work out **why** the deploy failed and write it down so a human can fix the underlying cause.

## What you are given

- `run_id` = `${{ github.event.inputs.run_id }}` — the failed Deploy workflow run.
- `pr_number` = `${{ github.event.inputs.pr_number }}` — the pull request whose merge triggered it.
- A best-effort tail of the failure log is embedded below. It may be truncated or empty; when it is not enough, use the GitHub Actions tools to read the failed run's logs and failed steps for `run_id` directly.

<failure-log>
${{ github.event.inputs.failure_log }}
</failure-log>

## How to diagnose

Deploys in this repo fail in a small number of recognisable ways. Read the log against these before inventing something exotic:

1. **A failing step in the deploy job** — read which step failed. `Build and start the stack` failing usually means a Docker build error (a bad Dockerfile, a dependency that will not install, an image that will not pull).
2. **Health-check timeouts** — `Wait for the frontend to answer locally` failing means the frontend container never served on 8090; check the compose logs in the run for the crashing container. `Wait for the public hostname…` failing means the stack is up locally but the Cloudflare tunnel did not connect (this happened once already: the `cloudflared` container could not read its `0400` credentials file as the default `nonroot` user — the fix was `user: "1000:1000"` in the compose).
3. **Missing configuration** — `Require the secrets that must not default` failing means `JWT_SECRET` or `POSTGRES_PASSWORD` was unset.
4. **App-level failure** — the containers build and start but the backend crashes on boot (a bad migration, a missing env var, `schema_rbac.sql` failing on a non-empty volume).

Look at the actual failed step and its output. Read `backend/Dockerfile`, `frontend/Dockerfile`, `deploy/docker-compose.deploy.yml`, or the workflow as needed to tie a log line to a cause. Do not guess a cause you cannot point at evidence for.

## What to write

Open **one** issue, titled `Deploy failure: run ${{ github.event.inputs.run_id }}`.

The body is in Traditional Chinese (ADR-0009) and states:

1. **What failed** — which step, and the key error line(s) quoted from the log. Keep the quote tight.
2. **Root cause** — your best-supported explanation, tied to specific evidence. If the log is truncated and you genuinely cannot tell, say what you can see and what additional log you would need — do not fabricate a cause.
3. **Fix** — the concrete change that would make the next deploy succeed, naming the file and what to change. If it needs a human decision (e.g. a secret to rotate), say so.
4. **State** — note that the service was already rolled back to the last-good version and that a revert PR was opened, so the reader knows the site is up and the branch is being corrected.

No preamble, no restating these instructions. The reader is the person who has to fix the deploy; give them the shortest path from "it broke" to "here is the line to change".
