#!/bin/bash
# Set the password of the memory-only database role `cloud360_memory`
# (merge-blockers row 20/29; 2026-10-31 decision: "SQL creates the role, the
# deployment sets the password").
#
# schema_rbac.sql creates the role WITHOUT a password: neither of its execution
# paths (docker-entrypoint-initdb.d, and run_meta_schema_migration.py through
# SQLAlchemy) can receive a psql variable. This script is the ONE place the
# password is set, used by:
#   * deploy/docker-compose.test.yml -- mounted as
#     /docker-entrypoint-initdb.d/02-memory-role-password.sh, runs after 01 on an
#     empty volume;
#   * .github/workflows/deploy.yml -- piped into `docker compose exec -T db bash -s`
#     after the stack is up, on every deploy (idempotent);
#   * local development -- see LOCAL-DEV.md H6.
#
# Inputs (environment): MEMORY_DB_PASSWORD (required, must not contain '$'),
# POSTGRES_USER and POSTGRES_DB (the postgres image sets both in the db container).
#
# The password NEVER appears on a command line: psql reads it from the
# environment with `\getenv` (PostgreSQL >= 15; both stacks run pg18) and quotes
# it with :'...' interpolation. Nothing here echoes it.

set -euo pipefail

ROLE=cloud360_memory

if [ -z "${MEMORY_DB_PASSWORD:-}" ]; then
  echo "02-memory-role-password.sh: MEMORY_DB_PASSWORD is empty; refusing to leave ${ROLE} without a password" >&2
  exit 1
fi
case "${MEMORY_DB_PASSWORD}" in
  *'$'*)
    echo "02-memory-role-password.sh: MEMORY_DB_PASSWORD contains '\$' (docker compose would truncate it); use openssl rand -hex 32" >&2
    exit 1
    ;;
esac

PSQL=(psql -v ON_ERROR_STOP=1 --no-psqlrc --username "${POSTGRES_USER:-postgres}" --dbname "${POSTGRES_DB:-cloud360}")

exists="$("${PSQL[@]}" -Atc "SELECT 1 FROM pg_roles WHERE rolname = '${ROLE}'")"
if [ "${exists}" != "1" ]; then
  echo "02-memory-role-password.sh: role ${ROLE} does not exist. It is created by schema_rbac.sql (empty volume) or by 'cd backend && python scripts/run_meta_schema_migration.py' (existing database) -- run that first. See DEPLOY.md 2.2.8." >&2
  exit 1
fi

"${PSQL[@]}" <<'SQL'
\getenv memory_db_password MEMORY_DB_PASSWORD
ALTER ROLE cloud360_memory WITH LOGIN PASSWORD :'memory_db_password';
\unset memory_db_password
SQL
echo "02-memory-role-password.sh: password set for ${ROLE}"
