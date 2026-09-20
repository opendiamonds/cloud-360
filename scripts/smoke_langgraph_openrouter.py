#!/usr/bin/env python3
"""Optional live smoke: one OpenRouter chat via langgraph_runtime.

Skip (exit 0) when OPENROUTER_API_KEY is unset — CI must not fail for missing keys.
Usage (local):
  cd backend && PYTHONPATH=. python3 ../scripts/smoke_langgraph_openrouter.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def main() -> int:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("SKIP: OPENROUTER_API_KEY unset — not running live OpenRouter smoke")
        return 0

    from services.langgraph_runtime import (
        DEFAULT_OPENROUTER_MODEL,
        openrouter_chat_model,
    )

    model = openrouter_chat_model(model=DEFAULT_OPENROUTER_MODEL, timeout_seconds=60)
    # Minimal one-shot inference; do not print api key or full raw response secrets.
    result = model.invoke("Reply with exactly: ok")
    content = getattr(result, "content", result)
    text = content if isinstance(content, str) else str(content)
    print(f"smoke_ok model={DEFAULT_OPENROUTER_MODEL} chars={len(text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
