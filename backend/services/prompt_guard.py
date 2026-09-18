"""Detect prompts that try to alter Cloud-360 platform internals (not customer cloud diagrams)."""

from __future__ import annotations

import re

REFUSAL_MESSAGE = "此需求毫無相關，請重新輸入"

# Platform self-reference
_PLATFORM = re.compile(
    r"(cloud[\s\-]?360|cloud360|本系統|本平台|我們的系統|你們的系統|這套系統)",
    re.IGNORECASE,
)

# Sensitive change intents about the running product
_SENSITIVE = re.compile(
    r"("
    r"資料庫|數據庫|database|db\s*schema|schema\s*migration|連線字串|connection\s*string|"
    r"系統值|系統設定|環境變數|env\s*var|"
    r"api\s*key|apikey|openrouter|anthropic|"
    r"金鑰|密钥|credential|secret|密碼|口令|"
    r"auth(?:entication)?\s*token|access\s*token|bearer\s*token|"
    r"rbac|權限矩陣(?:變更表)?|role_permissions|"
    r"刪除所有使用者|drop\s+table|alter\s+table"
    r")",
    re.IGNORECASE,
)

# Verbs of modifying the platform
_MUTATE = re.compile(
    r"(改|修改|變更|更新|寫入|設定|塞入|放到|換成|刪除|清除|重置|reset|update|change|modify|set|write|inject)",
    re.IGNORECASE,
)


def is_platform_self_modification(text: str) -> bool:
    """True when the user asks to change Cloud-360's own data/config/secrets."""
    if not text or not text.strip():
        return False
    t = text.strip()
    # Strong platform + sensitive target
    if _PLATFORM.search(t) and _SENSITIVE.search(t) and _MUTATE.search(t):
        return True
    # Explicit "our DB / our API key" style without product name
    our = re.search(r"(我們的|你们的|你們的|自家|平台的|後台的|后台的)", t)
    if our and _SENSITIVE.search(t) and _MUTATE.search(t):
        return True
    return False


def latest_user_text(messages: list[dict[str, str]] | list) -> str:
    """Concatenate recent user message contents for guard checks."""
    parts: list[str] = []
    for m in messages or []:
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content") or ""
        else:
            role = getattr(m, "role", None)
            content = getattr(m, "content", "") or ""
        if role == "user" and content:
            parts.append(str(content))
    return "\n".join(parts[-3:])
