#!/usr/bin/env python3
"""把大腦 WebSocket 契約 dump 成 repo 根目錄的 `ws-contract.json`（`U2`／`NFR5.1`）。

**為何需要這一支，而 `dump_openapi.py` 不夠**：FastAPI **不登錄 websocket route**，
所以既有的 `/api/collab/ws/...` 根本不在 `openapi.json` 的 42 個 path 內。
`dump_openapi.py --check` 與 `npm run check:types` 兩道既有漂移閘門對 WebSocket
**結構上完全無效**——不是覆蓋不足，是那條路徑上沒有任何斷言存在。

**為何不 import `main`**（`ADR-0019` D-4 的連帶，這是與 `dump_openapi.py` 最大的
差別）：本腳本只需要 Pydantic 模型本身，不需要 `app.openapi()`。少 import 的三個
實際差別——
  1. **閘門的訊號變乾淨**：應用程式任何 import 失敗（新依賴沒裝、某支 router 打
     字錯）都不會讓本閘門連帶紅燈。紅燈只代表**契約本身**漂移了。
  2. **不需要 DB 樁**：`dump_openapi.py:36` 得先
     `sys.modules.setdefault("psycopg", MagicMock())`，本腳本不需要。
  3. **契約的邊界更誠實**：模型定義了即進契約，與它有沒有被某支 router 用到無關
     ——對一個 `spec` 單元而言這是對的，`U2` 交付的就是型別本身。

**為何規格檔在 repo 根而不在 `frontend/public/`**（`NFR5.6`，理由逐字沿用
`dump_openapi.py` 的既有先例）：`frontend/nginx.conf` 是 `root
/usr/share/nginx/html` + `try_files $uri`，而 Vite 會把 `public/` 原樣複製進
`dist/`。規格檔落在那裡等於把**完整的訊息地圖**（九種伺服器訊息、六種客戶端訊息
與全部 payload 欄位，即大腦的內部協定與能力邊界）對未認證訪客公開。
連帶禁止：**不得**為了方便而把本規格檔 import 進前端程式碼——那會讓同一份地圖
進 bundle。型別檔（`.d.ts`）只有型別、不產生執行期程式碼，故它本身不是洩漏面。

**檔案為何帶一層 OpenAPI 外殼**（`paths: {}`）：型別產生器是
`openapi-typescript@7.13.0`，它只吃 OpenAPI 3.x 文件，不吃任意 JSON Schema。
外殼彆扭是刻意接受的代價，換到的是零新增的供應鏈面與零新增的工具鏈知識
（`tech-stack-decisions.md` D-1／D-2）。

**決定性**（`BR4.2`／`BR4.6`）：`sort_keys=True` 讓輸出與 dict 插入順序無關、
`ensure_ascii=False` 讓中文 description 以原字元存放使 diff 可讀、尾端換行符合
文字檔慣例。跨 `pydantic` 版本會飄，故 `requirements.txt` 對它採**精確等值**釘選
（`pydantic==2.13.4`）；升版時必須在同一個 PR 內重新 dump 並 commit。

**fail-closed**（`nfr-design §六`）：規格檔不存在、契約模組 import 失敗、任一斷言
失敗，三者皆 exit 非 0。本腳本**刻意不**以 try/except 包住契約模組的 import——
一個把例外吞掉後回報「無漂移」的檢查腳本，它的綠燈不構成任何證據，而
`construction.md` 的 `## Error Handling` 逐字禁止那個形狀。

用法（於 `backend/` 目錄）：
    python scripts/dump_ws_contract.py           # 寫入 ../ws-contract.json
    python scripts/dump_ws_contract.py --check   # 只比對，不一致則 exit 1（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SPEC_PATH = REPO_ROOT / "ws-contract.json"

for _path in (BACKEND_DIR, BACKEND_DIR / "services"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# 刻意在模組層 import 且不包 try/except（見 docstring 的 fail-closed 段）。
from pydantic.json_schema import models_json_schema  # noqa: E402

from services.brain_ws_contract import (  # noqa: E402
    CLIENT_FACING_MODELS,
    CONTRACT_MODELS,
)

REF_TEMPLATE = "#/components/schemas/{model}"
SPEC_VERSION = "3.1.0"
CONTRACT_TITLE = "Brain WS Contract"
CONTRACT_VERSION = "1.0.0"

# `BR1.4` 的 payload 判定式：名稱以 `Payload` 結尾者。此式**排除**
# `ClarifyCandidate` 與 `WorkItem` 兩個被組成的子實體、三個 Envelope、
# 兩個 type 列舉與 `WsSubprotocol`——它們都不是某個 type 的 payload。
PAYLOAD_SUFFIX = "Payload"
SERVER_TYPE_ENUM = "WsServerMessageType"
CLIENT_TYPE_ENUM = "WsClientMessageType"

# ---------------------------------------------------------------------------
# `NFR5.7` 客戶端欄位白名單（`ADR-0019 §6`）
# ---------------------------------------------------------------------------
#
# 為何是白名單而不是禁用名單：差別不是精確度而是**封閉性**。禁用名單擋不住叫別的
# 名字的身分欄位（`actor`、`onBehalfOf`、`impersonate`…），而那個命名空間是開放
# 的、列不完。白名單由構造封閉——任何新欄位都紅燈，直到有人**刻意**來改這裡。
# 那個「刻意」正是本斷言要的東西：新增一個客戶端欄位不再是一個人可以順手做完的事。
#
# 代價（寫下而非假裝沒有）：新增合法欄位要改兩處（契約模型 ＋ 本表），且紅燈訊息
# 只會說「欄位集合與預期不符」，**不會**指出「這是身分欄位」。診斷性換封閉性。
#
# ⚠ **判定式的適用前提（`ADR-0019 §6`，必讀）**：
#     本判定式**只比對每個 schema 的頂層 `properties` 鍵集合**。它今天「由構造
#     封閉」成立的前提是：目前七個客戶端物件**全部是扁平物件**，沒有任何巢狀
#     sub-object（已逐一核對 `entities.md`）。
#
#     **若日後任一 client payload 長出巢狀物件**（例如一個 `context: {...}`
#     欄位），只比對頂層鍵的斷言**碰不到巢狀物件內部**——一個藏在裡面、叫別的
#     名字的身分等價欄位就會逃過這道保護。那正是「維持禁用名單」被判定不可取的
#     同一個理由，只是換了一層。
#
#     **屆時必須二擇一**：讓判定式**遞迴進巢狀 schema**，或在此處**明文排除**並
#     說明為何安全。**不得**沿用現行寫法而假設它仍然涵蓋得到。
CLIENT_FIELD_WHITELIST: dict[str, frozenset[str]] = {
    "WsClientEnvelope": frozenset({"v", "type", "payload"}),
    "HelloPayload": frozenset({"v"}),
    "UserMessagePayload": frozenset({"text"}),
    "SelectClarifyCandidatePayload": frozenset({"candidateId"}),
    "CorrectWorkItemPayload": frozenset({"workItemId"}),
    "SetSharingModePayload": frozenset({"mode"}),
    "SetWorkTargetPayload": frozenset({"projectId", "systemId", "diagramId"}),
}


class ContractAssertionError(RuntimeError):
    """契約不變量被違反。與「規格檔漂移」分開，因為處置不同：漂移重跑 dump 即可，
    不變量被違反要改契約模型。"""


def _display(path: Path) -> str:
    """給人看的路徑。測試會把 `SPEC_PATH` 指到暫存目錄，那時 `relative_to` 會拋錯。"""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _pascal_case(snake: str) -> str:
    """`work_items` → `WorkItems`。`BR1.4` 對應關係的正規化步驟之一。"""
    return "".join(part[:1].upper() + part[1:] for part in snake.split("_"))


def _enum_values(schemas: Mapping[str, Any], enum_name: str) -> list[str]:
    schema = schemas.get(enum_name)
    if schema is None:
        raise ContractAssertionError(
            f"BR1.4 無法判定：`components.schemas` 缺少 type 列舉 {enum_name}。"
        )
    values = schema.get("enum")
    if not isinstance(values, list) or not values:
        raise ContractAssertionError(
            f"BR1.4 無法判定：{enum_name} 沒有可讀的 `enum` 值域（讀到 {values!r}）。"
        )
    return [str(value) for value in values]


def assert_type_payload_parity(schemas: Mapping[str, Any]) -> None:
    """`BR1.4` — 兩個 type 列舉與對應方向的 payload 實體集合等勢且可一一對應。

    三件事各自是一種真實的缺陷：
      * 有 type 沒有 payload → 消費端收到該 type 時無從處理；
      * 有 payload 沒有 type → 一段永不可達的死碼；
      * 兩集合不等勢 → 上面兩者至少發生一個。
    """
    expected: dict[str, str] = {}
    for enum_name in (SERVER_TYPE_ENUM, CLIENT_TYPE_ENUM):
        for value in _enum_values(schemas, enum_name):
            expected[_pascal_case(value) + PAYLOAD_SUFFIX] = f"{enum_name}.{value}"

    actual = {name for name in schemas if name.endswith(PAYLOAD_SUFFIX)}

    missing = sorted(set(expected) - actual)
    if missing:
        raise ContractAssertionError(
            "BR1.4 違反：有 type 沒有對應的 payload 實體——"
            + "；".join(f"{expected[name]} 需要 {name}" for name in missing)
            + "。消費端收到該 type 時無從處理它的形狀。"
        )

    orphans = sorted(actual - set(expected))
    if orphans:
        raise ContractAssertionError(
            "BR1.4 違反：有 payload 實體不被任何 type 對應（永不可達的死碼）——"
            f"{orphans}。"
        )

    if len(actual) != len(expected):
        raise ContractAssertionError(
            f"BR1.4 違反：兩集合不等勢（payload {len(actual)} 個、type {len(expected)} 個）。"
        )


def assert_client_field_whitelist(schemas: Mapping[str, Any]) -> None:
    """`NFR5.7` — 七個客戶端物件的欄位名集合**逐一等於**上面釘住的預期集合。

    見 `CLIENT_FIELD_WHITELIST` 上方的適用前提註解（`ADR-0019 §6`）：本判定式
    只比對頂層 `properties` 鍵。
    """
    declared = {model.__name__ for model in CLIENT_FACING_MODELS}
    if declared != set(CLIENT_FIELD_WHITELIST):
        raise ContractAssertionError(
            "NFR5.7 無法判定：契約宣告的客戶端物件集合與本腳本的白名單鍵不一致。"
            f"契約有而白名單沒有：{sorted(declared - set(CLIENT_FIELD_WHITELIST))}；"
            f"白名單有而契約沒有：{sorted(set(CLIENT_FIELD_WHITELIST) - declared)}。"
        )

    for name, allowed in CLIENT_FIELD_WHITELIST.items():
        schema = schemas.get(name)
        if schema is None:
            raise ContractAssertionError(
                f"NFR5.7 無法判定：`components.schemas` 缺少客戶端物件 {name}。"
            )
        actual = frozenset(schema.get("properties", {}))
        if actual != allowed:
            raise ContractAssertionError(
                f"NFR5.7 違反：{name} 的欄位集合與預期不符。"
                f"多出：{sorted(actual - allowed)}；缺少：{sorted(allowed - actual)}。"
                "客戶端訊息不得攜帶身分或 turnId（BR2.12／BR2.13）——"
                "principal 綁在連線上。若這個欄位確實合法，請刻意修改 "
                "dump_ws_contract.py 的 CLIENT_FIELD_WHITELIST。"
            )


def build_spec() -> dict[str, Any]:
    """產生最小 OpenAPI 3.1 外殼 ＋ `components.schemas`，並跑完兩條建置期斷言。"""
    _, definitions = models_json_schema(
        [(model, "validation") for model in CONTRACT_MODELS],
        ref_template=REF_TEMPLATE,
    )
    schemas = definitions["$defs"]

    assert_type_payload_parity(schemas)
    assert_client_field_whitelist(schemas)

    return {
        "openapi": SPEC_VERSION,
        "info": {"title": CONTRACT_TITLE, "version": CONTRACT_VERSION},
        "paths": {},
        "components": {"schemas": schemas},
    }


def render_spec() -> str:
    # sort_keys 讓輸出與 dict 插入順序無關（BR4.2）；ensure_ascii=False 讓中文
    # description 以原字元存放（diff 可讀）；結尾換行符合一般文字檔慣例。
    return json.dumps(build_spec(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="只比對 committed 的規格檔與重新產生的結果，不寫入",
    )
    args = parser.parse_args(argv)

    try:
        rendered = render_spec()
    except ContractAssertionError as exc:
        # 斷言失敗與斷言跑不動，兩者都不得等同於通過。訊息送 stderr 並 exit 1，
        # **不**回報「無漂移」。
        print(f"契約不變量被違反：{exc}", file=sys.stderr)
        return 1

    if not args.check:
        SPEC_PATH.write_text(rendered, encoding="utf-8")
        print(f"已寫入 {_display(SPEC_PATH)}")
        return 0

    if not SPEC_PATH.exists():
        print(
            f"規格檔不存在：{_display(SPEC_PATH)}\n"
            "請於 backend/ 執行 `python scripts/dump_ws_contract.py` 並 commit 產出。",
            file=sys.stderr,
        )
        return 1

    committed = SPEC_PATH.read_text(encoding="utf-8")
    if committed == rendered:
        print("WS 契約規格檔與後端程式碼一致。")
        return 0

    print(
        f"規格檔已漂移：{_display(SPEC_PATH)} 與 services/brain_ws_contract.py 不一致。\n"
        "契約的訊息形狀改了但規格檔沒重新產生。請於 backend/ 執行\n"
        "  python scripts/dump_ws_contract.py\n"
        "並把產出與**重新產生的前端型別檔**一併 commit（於 frontend/ 執行 npm run gen:ws-types）。",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
