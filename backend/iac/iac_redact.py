"""Pure secret-literal redactor.

Rewrites quoted assignments of known secret keys to a Secret Manager
reference expression. This module does not call a cloud API.
"""

from __future__ import annotations

import re

from iac.iac_types import FileEntry, Redaction

# Mutation point: ``mask_secret_value`` must not return the captured literal.
_ASSIGNMENT = re.compile(
    r'(?P<prefix>\b(?:password|secret|api_key|access_key|token|private_key)\b'
    r'\s*=\s*)"(?P<value>[^"\n]*)"',
    re.IGNORECASE,
)

SECRET_MANAGER_REFERENCE = (
    "data.aws_secretsmanager_secret_version.cloud360.secret_string"
)


def mask_secret_value(plaintext: str) -> str:
    """Replace one captured literal with a Secret Manager reference.

    The argument is accepted so callers can see the boundary. The return
    value must not contain ``plaintext``.
    """
    if not isinstance(plaintext, str):
        raise TypeError("plaintext must be a string")
    return SECRET_MANAGER_REFERENCE


def redact_files(files: list[FileEntry]) -> Redaction:
    rewritten: list[FileEntry] = []
    paths: list[str] = []
    for entry in files:
        content, changed = _redact_text(entry.content)
        rewritten.append(FileEntry(entry.path, content))
        if changed:
            paths.append(entry.path)
    return Redaction(files=rewritten, rewritten_paths=paths)


def _redact_text(content: str) -> tuple[str, bool]:
    changed = False

    def _replace(match: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        masked = mask_secret_value(match.group("value"))
        return f"{match.group('prefix')}{masked}"

    return _ASSIGNMENT.sub(_replace, content), changed
