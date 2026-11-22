"""In-memory zip of a module tree. No temp file is left behind."""

from __future__ import annotations

import io
import zipfile

from iac.iac_generate import is_safe_relative_path
from iac.iac_types import FileEntry, IacGateError


def build_module_zip(files: list[FileEntry]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in files:
            if not is_safe_relative_path(entry.path):
                raise IacGateError("generate_failed", "Draft contains an unsafe path.")
            archive.writestr(entry.path, entry.content)
    return buffer.getvalue()
