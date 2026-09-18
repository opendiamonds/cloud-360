#!/usr/bin/env bash
# Render deploy/.env for the deployment stack (deploy/docker-compose.deploy.yml).
#
# This is the single source of truth for deploy-time configuration. Both the
# deploy job and the rollback job in .github/workflows/deploy.yml call it, so
# a rollback can never restore the service with a different environment than
# the deploy that preceded it.
#
# Local development does NOT use this file. Bare-metal dev is configured by
# backend/.env and frontend/.env (templates: backend/.env.example,
# frontend/.env.example) and never reads deploy/.env. Keeping the two apart is
# checked by scripts/validate_env_contract.py.
#
# Secret values arrive through the environment, never as arguments -- arguments
# are visible in the process list to every user on the host.
#
#   POSTGRES_PASSWORD  required   database superuser password
#   JWT_SECRET         required   signs every login token
#   CLOUD360_BOOTSTRAP_ADMIN_PASSWORD optional one-time admin bootstrap password
#   OPENROUTER_API_KEY optional   A1 design agent; empty disables generation
#   N8N_WEBHOOK_URL    optional   dynamic architecture icons
#   N8N_USER           optional   basic auth for the n8n webhook
#   N8N_PASSWORD       optional   basic auth for the n8n webhook
#   APP_ENV            optional   defaults to staging
#
# LLM_PROVIDER is pinned to openrouter here and is not overridable: the other
# mode (cli) needs an interactively logged-in claude CLI, which a container
# does not have.
#
# Usage: deploy/render-env.sh [output-path]   (default: deploy/.env)

set -euo pipefail

OUT="${1:-deploy/.env}"

missing=""
[ -n "${POSTGRES_PASSWORD:-}" ] || missing="${missing} POSTGRES_PASSWORD"
[ -n "${JWT_SECRET:-}" ] || missing="${missing} JWT_SECRET"
if [ -n "${missing}" ]; then
  echo "render-env.sh: missing required value(s):${missing}" >&2
  exit 1
fi

# docker compose interpolates ${...} and $NAME inside --env-file values, so a
# credential containing '$' is silently TRUNCATED rather than rejected:
# POSTGRES_PASSWORD=ab$cd reaches postgres as "ab", the stack starts, and
# nothing anywhere reports that the database is running on a two-character
# password. Refuse the value instead of shipping a weakened one.
for name in POSTGRES_PASSWORD JWT_SECRET N8N_PASSWORD; do
  eval "value=\${${name}:-}"
  case "${value}" in
    *'$'*)
      echo "render-env.sh: ${name} contains '\$', which docker compose would" >&2
      echo "silently truncate when reading deploy/.env. Use a value without it" >&2
      echo "-- e.g. openssl rand -hex 32." >&2
      exit 1
      ;;
  esac
done

# 077 so the rendered file is not world-readable even for the instant it exists.
umask 077
cat > "${OUT}" <<EOF
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=cloud360
JWT_SECRET=${JWT_SECRET}
CLOUD360_BOOTSTRAP_ADMIN_PASSWORD=${CLOUD360_BOOTSTRAP_ADMIN_PASSWORD:-}
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
ANTHROPIC_BASE_URL=https://openrouter.ai/api
ANTHROPIC_DEFAULT_SONNET_MODEL=anthropic/claude-sonnet-4.6
LLM_MODEL=anthropic/claude-sonnet-4.6
LLM_MAX_OUTPUT_TOKENS=12000
LLM_XML_CONTEXT_MAX_CHARS=32000
N8N_WEBHOOK_URL=${N8N_WEBHOOK_URL:-}
N8N_USER=${N8N_USER:-}
N8N_PASSWORD=${N8N_PASSWORD:-}
APP_ENV=${APP_ENV:-staging}
PUBLIC_URL=https://cloud360.danniel.cc
FRONTEND_HOST_PORT=8090
CLOUDFLARED_CREDENTIALS_FILE=${HOME}/.cloudflared/b460a579-9e0d-42f1-a31d-c84d35bef065.json
EOF
