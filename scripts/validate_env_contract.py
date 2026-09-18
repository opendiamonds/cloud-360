#!/usr/bin/env python3
"""Validate the Cloud-360 environment-configuration contract.

Cloud-360 runs in three environments that MUST keep their configuration
separate. Nothing but this script enforces that separation, and the three
sources of truth below can otherwise drift silently -- a variable the deploy
stack consumes but nobody writes becomes an empty string, and an empty string
is a *degraded feature*, not a crash.

    scope        config source                      consumed by
    -----------  ---------------------------------  --------------------------
    local dev    backend/.env, frontend/.env         uvicorn + vite, bare metal
                 (templates: backend/.env.example,
                  frontend/.env.example)
    ci-test      deploy/docker-compose.test.yml      ui-regression ephemeral
                 (inlined, every value defaulted)    stack
    deploy       deploy/.env                         deploy/docker-compose.
                 (written by .github/workflows/      deploy.yml
                  deploy.yml, template
                  deploy/.env.example)

Concretely this catches the class of bug that motivated the script: compose
read ``${N8N_USER}`` / ``${N8N_PASSWORD}`` with no fallback while deploy.yml
never wrote them, so every GitHub Actions deploy shipped the backend with empty
n8n credentials and the architecture icons silently fell back to grey
placeholders. No existing gate could see it -- it is a gap *between* three
files, and each file is individually valid.

Run: ``python3 scripts/validate_env_contract.py`` (also runs in CI).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEPLOY_COMPOSE = "deploy/docker-compose.deploy.yml"
DEPLOY_WORKFLOW = ".github/workflows/deploy.yml"
DEPLOY_RENDERER = "deploy/render-env.sh"
DEPLOY_TEMPLATE = "deploy/.env.example"
BACKEND_TEMPLATE = "backend/.env.example"
FRONTEND_TEMPLATE = "frontend/.env.example"

# Variables the deploy stack composes from other variables rather than reading
# from deploy/.env. Setting them in the template would be silently ignored,
# which reads as configuration but is not.
DEPLOY_DERIVED = {
    "DATABASE_URL",       # compose builds it from POSTGRES_USER/PASSWORD/DB
    "VITE_API_BASE_URL",  # compose passes PUBLIC_URL as the frontend build arg
}

# Keys that belong to the deploy stack only. A local dev template listing any of
# them is mixing the two scopes.
DEPLOY_ONLY_KEYS = {
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "PUBLIC_URL",
    "FRONTEND_HOST_PORT",
    "CLOUDFLARED_CREDENTIALS_FILE",
}

# Set by the app for the Agent SDK subprocess rather than read from user
# configuration -- documenting them in .env.example would invite overriding
# values the app overwrites at startup (see backend/services/llm_limits.py).
SDK_INTERNAL_KEYS = {
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS",
    "MAX_THINKING_TOKENS",
}

# Loopback origins are a local-dev concept. In a deploy template they widen the
# backend's CORS allowlist on the public host for no operational reason.
DEV_ONLY_MARKERS = ("localhost", "127.0.0.1")

# ``${VAR}``, ``${VAR:-default}``, ``${VAR-default}``, ``${VAR:?msg}``.
COMPOSE_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:?[-?+])?")
ENV_ASSIGNMENT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=", re.MULTILINE)
COMMENTED_ASSIGNMENT = re.compile(r"^\s*#\s*([A-Za-z_][A-Za-z0-9_]*)=", re.MULTILINE)
# "your_openrouter_api_key_here", "changeme", "<your-token>", "TODO" ...
PLACEHOLDER_VALUE = re.compile(
    r"^(your[_-].*|.*[_-]here|<.*>|changeme|change[_-]me|xxx+|todo|placeholder)$",
    re.IGNORECASE,
)
PY_ENV_READ = re.compile(
    r"""os\.(?:environ\.get|getenv)\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']"""
)


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def compose_variables(rel: str) -> tuple[set[str], set[str]]:
    """Return (required, defaulted) variable names used by a compose file."""
    required: set[str] = set()
    defaulted: set[str] = set()
    for name, operator in COMPOSE_VAR.findall(read(rel)):
        (defaulted if operator else required).add(name)
    # A name used both ways somewhere in the file is satisfied by its default.
    return required - defaulted, defaulted


def rendered_variables() -> set[str]:
    """Variable names deploy/render-env.sh writes into deploy/.env.

    Scoped to the heredoc that generates the file so that the script's own
    argument handling and required-value checks cannot be mistaken for
    deploy/.env content.
    """
    text = read(DEPLOY_RENDERER)
    match = re.search(r"""cat > "\$\{OUT\}" <<'?EOF'?\n(.*?)\nEOF""", text, re.DOTALL)
    if match is None:
        raise SystemExit(
            fail(
                f"{DEPLOY_RENDERER}: cannot find the `cat > \"${{OUT}}\" <<EOF` "
                "heredoc. This guard parses that block to know which variables "
                "reach the deploy stack; update the guard alongside the renderer."
            )
        )
    return set(ENV_ASSIGNMENT.findall(match.group(1)))


def validate_workflow_uses_the_renderer() -> int:
    """Neither deploy job may hand-roll deploy/.env behind the guard's back.

    The guard reads deploy/render-env.sh. A job that writes the file inline
    again would be invisible to every check below -- which is exactly how the
    deploy and rollback heredocs came to be two copies of the same list.
    """
    text = read(DEPLOY_WORKFLOW)
    if re.search(r"cat\s*>\s*deploy/\.env", text):
        return fail(
            f"{DEPLOY_WORKFLOW} writes deploy/.env inline. Call "
            f"{DEPLOY_RENDERER} instead -- it is the single source of deploy-time "
            "configuration, and an inline heredoc silently escapes this guard."
        )
    if "render-env.sh" not in text:
        return fail(
            f"{DEPLOY_WORKFLOW} never calls {DEPLOY_RENDERER}, so the deploy "
            "stack is configured from somewhere this guard cannot see."
        )
    return 0


def template_keys(rel: str) -> set[str]:
    """Keys the template actually sets."""
    return set(ENV_ASSIGNMENT.findall(read(rel)))


def template_documented_keys(rel: str) -> set[str]:
    """Keys the template sets *or* documents as a commented-out knob.

    A commented ``# KEY=`` is how an optional variable is documented without
    forcing a value on every developer, so it counts as documented -- but not
    as supplied, which is why the completeness checks use template_keys().
    """
    return template_keys(rel) | set(COMMENTED_ASSIGNMENT.findall(read(rel)))


def validate_deploy_stack_is_fully_supplied() -> int:
    """Every variable the deploy stack requires must actually be written."""
    required, _ = compose_variables(DEPLOY_COMPOSE)
    written = rendered_variables()
    missing = sorted(required - written)
    if missing:
        return fail(
            f"{DEPLOY_COMPOSE} requires {', '.join(missing)} with no fallback, but "
            f"{DEPLOY_RENDERER} never writes them. GitHub Actions deploys would "
            "start the stack with those values empty -- a silently degraded "
            "service, not a failed deploy. Add them to the heredoc (and to the "
            "repository secrets if they hold credentials)."
        )
    return 0


def validate_deploy_template_is_complete() -> int:
    """The manual host-copy path must be able to fill in every required value."""
    required, _ = compose_variables(DEPLOY_COMPOSE)
    keys = template_keys(DEPLOY_TEMPLATE)
    missing = sorted(required - keys)
    if missing:
        return fail(
            f"{DEPLOY_TEMPLATE} is missing {', '.join(missing)}, which "
            f"{DEPLOY_COMPOSE} requires. DEPLOY.md documents copying this "
            "template onto the host, so an incomplete template is an "
            "undeployable stack."
        )
    return 0


def validate_deploy_template_sets_nothing_derived() -> int:
    """Values compose derives must not look configurable in the template."""
    present = sorted(template_keys(DEPLOY_TEMPLATE) & DEPLOY_DERIVED)
    if present:
        return fail(
            f"{DEPLOY_TEMPLATE} sets {', '.join(present)}, but "
            f"{DEPLOY_COMPOSE} derives those from other variables and ignores "
            "whatever the file says. Remove them so the template cannot promise "
            "a knob that does nothing."
        )
    return 0


def validate_scopes_are_separated() -> int:
    """Deploy config and local-dev config must not bleed into each other."""
    violations: list[str] = []

    deploy_text = read(DEPLOY_TEMPLATE)
    for lineno, line in enumerate(deploy_text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        for marker in DEV_ONLY_MARKERS:
            if marker in line:
                violations.append(
                    f"{DEPLOY_TEMPLATE}:{lineno} carries the local-dev origin "
                    f"'{marker}': {line.strip()}"
                )

    for template in (BACKEND_TEMPLATE, FRONTEND_TEMPLATE):
        leaked = sorted(template_keys(template) & DEPLOY_ONLY_KEYS)
        if leaked:
            violations.append(
                f"{template} sets deploy-only key(s) {', '.join(leaked)}"
            )

    if violations:
        return fail(
            "Local-dev and deploy configuration are mixed:\n  - "
            + "\n  - ".join(violations)
        )
    return 0


def validate_local_dev_template_is_complete() -> int:
    """Every variable the backend reads must be documented for local dev."""
    read_names: set[str] = set()
    for path in sorted((ROOT / "backend").rglob("*.py")):
        if "tests" in path.parts or ".venv" in path.parts:
            continue
        read_names |= set(PY_ENV_READ.findall(path.read_text(encoding="utf-8")))

    documented = template_documented_keys(BACKEND_TEMPLATE)
    missing = sorted(read_names - documented - SDK_INTERNAL_KEYS)
    if missing:
        return fail(
            f"backend/ reads {', '.join(missing)} but {BACKEND_TEMPLATE} does not "
            "document them. An undocumented variable is one a developer cannot "
            "set without reading the source. Add them to the template (commented "
            "out if optional), or to SDK_INTERNAL_KEYS in this script if the app "
            "sets them for the Agent SDK rather than reading user configuration."
        )
    return 0


def validate_templates_ship_no_placeholder_values() -> int:
    """A template must express "not configured" as an empty value.

    Code decides a feature is configured by testing the variable for a non-empty
    value. A placeholder like ``your_openrouter_api_key_here`` is non-empty, so
    copying the template and not filling it in does not read as "unset" -- it
    reads as a credential, and gets sent upstream. The resulting failure is an
    authentication error three layers away from the file that caused it, rather
    than the clear "not set" message the code already knows how to produce.
    """
    violations: list[str] = []
    for template in (BACKEND_TEMPLATE, FRONTEND_TEMPLATE, DEPLOY_TEMPLATE):
        for lineno, line in enumerate(read(template).splitlines(), start=1):
            if line.lstrip().startswith("#"):
                continue
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if match is None:
                continue
            value = match.group(2).strip().strip("\"'")
            if PLACEHOLDER_VALUE.match(value):
                violations.append(f"{template}:{lineno} {match.group(1)}={value}")

    if violations:
        return fail(
            "Template(s) ship a non-empty placeholder value:\n  - "
            + "\n  - ".join(violations)
            + "\nLeave the value empty and put the example in a comment above it, "
            "so an unfilled template reads as unset rather than as a credential."
        )
    return 0


def main() -> int:
    checks = (
        validate_workflow_uses_the_renderer,
        validate_deploy_stack_is_fully_supplied,
        validate_deploy_template_is_complete,
        validate_deploy_template_sets_nothing_derived,
        validate_scopes_are_separated,
        validate_local_dev_template_is_complete,
        validate_templates_ship_no_placeholder_values,
    )
    for check in checks:
        result = check()
        if result != 0:
            return result

    print("Cloud-360 environment configuration contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
