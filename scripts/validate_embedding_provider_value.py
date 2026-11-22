#!/usr/bin/env python3
"""驗證三份設定來源寫出的 embedding 設定值真的能通過啟動驗證（`H-I3`）。

它存在的理由是一個**部署期**缺口：`EMBEDDING_PROVIDER` 刻意沒有預設值，
而它的值是由 `deploy/render-env.sh` 以字面值寫出的。若有人把那個字面值改錯
（打錯字、改成一個不存在的提供者、把 `OLLAMA_BASE_URL` 指到 compose 網路之外），
**沒有任何既有閘門會發現**：`validate_env_contract.py` 只檢查變數有沒有被寫出、
不檢查值合不合法；CI 的 test stack 用 `stub`，根本不會走到 deploy 的那組值；
而 backend 要到部署後啟動時才會拒絕啟動——那時 deploy job 已經在跑了。

**本腳本不自行列舉任何允許值。** 它 import `services.embedding_port` 的
`ALLOWED_PROVIDERS` 與 `resolve_provider_selection`，讓設定值走**同一條**驗證
路徑。`H-I3` 逐字禁止第二份清單——第二份清單一定會漂移，而漂移的方向正好是
「CI 說可以、執行期說不行」。

本腳本可在 CI 的 `repo-contract` job 執行：該 job 只跑 `actions/setup-python`、
**不安裝 `requirements.txt`**，而 `embedding_port.py` 的模組層只 import 標準庫
（`httpx` 延到用到它的方法內才 import），所以這個 import 不需要任何依賴。

用法：
    python3 scripts/validate_embedding_provider_value.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

try:
    from services.embedding_port import (  # noqa: E402
        ALLOWED_PROVIDERS,
        MEMORY_RECORD_EMBEDDING_MODELS,
        resolve_provider_selection,
    )
except Exception as exc:  # pragma: no cover - 本身就是要報告的失敗
    print(
        "ERROR: 無法 import backend/services/embedding_port.py："
        f"{type(exc).__name__}: {exc}\n"
        "       本腳本刻意 import 該模組以取得允許值集合與驗證函式（H-I3）。\n"
        "       若這個 import 需要第三方套件才成立，就表示模組層被加進了\n"
        "       非標準庫的 import —— 那會讓 CI 的 repo-contract job 失敗，\n"
        "       因為該 job 不安裝 requirements.txt。",
        file=sys.stderr,
    )
    raise SystemExit(1)

# 本模組消費的設定鍵。順序無意義，集合才有。
KEYS = (
    "EMBEDDING_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_EMBED_MODEL",
    "FASTEMBED_MODEL",
    "EMBEDDING_TIMEOUT_SEC",
)

# 只取字面值：含 `${...}` 的右手邊是部署期才決定的，不在本腳本的判定範圍。
ASSIGNMENT = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)=(.*)$")


def literal_assignments(path: Path) -> dict[str, str]:
    """抓出該檔中對 KEYS 的字面值賦值（跳過註解與含 `${}` 的值）。"""
    found: dict[str, str] = {}
    if not path.exists():
        return found
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if key not in KEYS:
            continue
        if "${" in value:
            # 由部署期的 secret／variable 決定，這裡判定不了。
            continue
        found[key] = value
    return found


def check(label: str, path: Path) -> list[str]:
    """把一份設定來源的值餵進真正的啟動驗證路徑。"""
    problems: list[str] = []
    env = literal_assignments(path)
    if "EMBEDDING_PROVIDER" not in env:
        # 沒有字面值不是錯：該來源可能刻意把它留給部署期。
        return problems
    try:
        selection = resolve_provider_selection(env=env)
    except ValueError as exc:
        problems.append(
            f"{label}（{path.relative_to(REPO_ROOT)}）寫出的 embedding 設定"
            f"無法通過啟動驗證：{exc}"
        )
        return problems

    # 有 Port 時，model_id 必須落在記憶列宣告的合法集合內。這一條在
    # resolve_provider_selection 內已經擋了，這裡再斷言一次是為了讓失敗訊息
    # 指名是哪一份設定來源，而不是只說「啟動會失敗」。
    if selection.port_present and selection.model_id not in MEMORY_RECORD_EMBEDDING_MODELS:
        problems.append(
            f"{label} 的 model_id {selection.model_id!r} 不在合法的 embeddingModel "
            "集合內：" + "｜".join(MEMORY_RECORD_EMBEDDING_MODELS)
        )
    return problems


def main() -> int:
    sources = [
        ("部署設定的產生點", REPO_ROOT / "deploy" / "render-env.sh"),
        ("部署範本", REPO_ROOT / "deploy" / ".env.example"),
        ("本機 dev 範本", REPO_ROOT / "backend" / ".env.example"),
    ]

    problems: list[str] = []
    checked = 0
    for label, path in sources:
        if not path.exists():
            problems.append(f"{label} 不存在：{path.relative_to(REPO_ROOT)}")
            continue
        before = len(problems)
        problems.extend(check(label, path))
        if len(problems) == before:
            checked += 1

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        print(
            "\n可選的 EMBEDDING_PROVIDER 值："
            + "｜".join(ALLOWED_PROVIDERS)
            + "\n（本清單由 backend/services/embedding_port.py import 而來，"
            "不是這支腳本自己列的。）",
            file=sys.stderr,
        )
        return 1

    print(
        f"Cloud-360 embedding provider value validation passed（{checked} 份設定來源）。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
