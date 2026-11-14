"""intent_routing_config.py — `U11 intent-router` 的五個環境變數

**契約（部署資產依賴，請勿變更變數名）**

`TS-4`／`NFR8.60`／`NFR8.61`：本單元新增五個 `BRAIN_ROUTER_*` 變數，**四個有
預設、一個刻意無預設**。三處同步義務（`deploy/render-env.sh`、
`deploy/.env.example`、`deploy/docker-compose.deploy.yml`）＋ 本機範本
`backend/.env.example`，由 `python3 scripts/validate_env_contract.py` 機械檢查。

| 變數 | 預設 | 缺值行為 |
|---|---|---|
| `BRAIN_ROUTER_MODEL` | `typesafe/jev-1.13` | 取預設 ＋ INFO |
| `BRAIN_ROUTER_TIMEOUT_SEC` | `5` | 取預設 ＋ WARN |
| `BRAIN_ROUTER_MAX_CALLS_PER_TURN` | `1` | 取預設 ＋ WARN |
| `BRAIN_ROUTER_MAX_RETRIES` | `0` | 取預設 ＋ WARN |
| `BRAIN_ROUTER_CONFIDENCE_THRESHOLD` | **無** | **啟動失敗**（`BR3.4`） |

為什麼只有門檻無預設
--------------------

`BR3.4` 逐字「缺值**不得以預設值靜默啟動**」。其餘四個缺值時系統行為正確、
只是沒照設定跑；門檻缺值則**反問路徑的判定基準不存在**，而那是 `FR1.3`
這條 Must 的觸發條件。既有前例是 `EMBEDDING_PROVIDER` 與
`BRAIN_SESSION_HISTORY_MAX`（`backend/.env.example`）——兩者都 required
且無預設，缺值即大聲失敗。

**啟動期驗設定，執行期驗流量**（`reliability-design.md` §四）：本單元不提供
`/health`（`SEC-2` 明寫不建 `APIRouter`，所以那從來不是一個選項），
`configure_intent_routing_env()` 掛在 `main.py` 的 startup hook，形狀與
`configure_session_env()` 刻意相同——**失敗即拋**。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Final, Optional

logger = logging.getLogger("cloud360.intent_routing")

MODEL_ENV: Final = "BRAIN_ROUTER_MODEL"
TIMEOUT_ENV: Final = "BRAIN_ROUTER_TIMEOUT_SEC"
MAX_CALLS_ENV: Final = "BRAIN_ROUTER_MAX_CALLS_PER_TURN"
MAX_RETRIES_ENV: Final = "BRAIN_ROUTER_MAX_RETRIES"
THRESHOLD_ENV: Final = "BRAIN_ROUTER_CONFIDENCE_THRESHOLD"

#: `TS-1`／`OQ-4`：路由層模型。**獨立變數，不得沿用 `LLM_MODEL`**——後者是
#: A1／A3 功能 agent 在用的，共用會讓 `NFR10` 逐字允許的「編排層與功能 agent
#: 得使用不同模型」在設定層消失（`NFR10.60`）。
DEFAULT_MODEL: Final = "typesafe/jev-1.13"

#: `NFR3.61`：單次模型呼叫硬逾時 5 秒。
DEFAULT_TIMEOUT_SEC: Final = 5.0

#: `NFR3.62`：每輪最多 1 次模型呼叫。
DEFAULT_MAX_CALLS_PER_TURN: Final = 1

#: `NFR3.63`：重試 0 次（沿用 `langgraph_runtime` 現行的 `max_retries=0`）。
DEFAULT_MAX_RETRIES: Final = 0


@dataclass(frozen=True)
class RoutingConfig:
    """一次解析的結果。**不可變**——`NFR3.67` 禁止行程內共享可變狀態。"""

    model: str
    timeout_seconds: float
    max_calls_per_turn: int
    max_retries: int
    confidence_threshold: float


def _source(env: Optional[Any]) -> Any:
    return os.environ if env is None else env


def _raw(source: Any, name: str) -> str:
    return (source.get(name) or "").strip()


def resolve_confidence_threshold(env: Optional[Any] = None) -> float:
    """讀取並驗證 `BRAIN_ROUTER_CONFIDENCE_THRESHOLD`（`BR3.4`／`FR1.7`）。

    **缺值即大聲失敗。** 把缺值讀成某個預設門檻會讓「反問要不要發生」這件事
    由一個沒有人選過的數字決定，而 `FR1.7` 逐字把門檻定為**設定值而非常數**，
    正因為它要依 `NFR1` 的校正程序調整。

    值域為 `0 < t <= 1`，**下界開區間是刻意的**：門檻為 0 時「最高分 ≥ 門檻」
    恆真，反問路徑**永不觸發**——那正是 `FR1.6` 逐字警告的「`FR1.3` 會靜默
    永不觸發，而文件上看起來已解決」。一個會讓 Must 失效的設定值不該被接受。
    """
    raw = _raw(_source(env), THRESHOLD_ENV)
    if not raw:
        raise RuntimeError(
            f"{THRESHOLD_ENV} 未設定。它**刻意無預設值**（BR3.4／FR1.7）："
            "門檻缺值時反問路徑的判定基準不存在，而那是 FR1.3 這條 Must 的"
            "觸發條件。請在 backend/.env（本機）或 deploy/.env（部署，由 "
            "deploy/render-env.sh 產生）設定它；初版值 0.7。"
        )
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(
            f"{THRESHOLD_ENV} 必須是 0 與 1 之間的數字，收到 {raw!r}（BR3.4）"
        ) from exc
    if not 0.0 < value <= 1.0:
        raise RuntimeError(
            f"{THRESHOLD_ENV} 必須落在 0 < t <= 1，收到 {value}（BR3.4）。"
            "門檻為 0 會讓反問路徑永不觸發（FR1.6）；大於 1 會讓它永遠觸發。"
        )
    return value


def _positive_float(source: Any, name: str, default: float) -> float:
    raw = _raw(source, name)
    if not raw:
        logger.warning(
            "%s 未設定，取預設 %s（NFR8.60：缺值行為必須明確，不靜默降級）",
            name,
            default,
        )
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning("%s 不是數字（收到 %r），取預設 %s", name, raw, default)
        return default
    if value <= 0:
        logger.warning("%s 必須為正數（收到 %s），取預設 %s", name, value, default)
        return default
    return value


def _non_negative_int(source: Any, name: str, default: int) -> int:
    raw = _raw(source, name)
    if not raw:
        logger.warning(
            "%s 未設定，取預設 %s（NFR8.60：缺值行為必須明確，不靜默降級）",
            name,
            default,
        )
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s 不是整數（收到 %r），取預設 %s", name, raw, default)
        return default
    if value < 0:
        logger.warning("%s 不得為負（收到 %s），取預設 %s", name, value, default)
        return default
    return value


def resolve_routing_config(env: Optional[Any] = None) -> RoutingConfig:
    """解析全部五個變數。門檻缺值即拋，其餘四個取預設並記 log。"""
    source = _source(env)
    model = _raw(source, MODEL_ENV)
    if not model:
        logger.info(
            "%s 未設定，取預設 %s（TS-1：它有一個正確的預設，故不致命）",
            MODEL_ENV,
            DEFAULT_MODEL,
        )
        model = DEFAULT_MODEL
    return RoutingConfig(
        model=model,
        timeout_seconds=_positive_float(source, TIMEOUT_ENV, DEFAULT_TIMEOUT_SEC),
        max_calls_per_turn=_non_negative_int(
            source, MAX_CALLS_ENV, DEFAULT_MAX_CALLS_PER_TURN
        ),
        max_retries=_non_negative_int(source, MAX_RETRIES_ENV, DEFAULT_MAX_RETRIES),
        confidence_threshold=resolve_confidence_threshold(source),
    )


def configure_intent_routing_env(env: Optional[Any] = None) -> RoutingConfig:
    """啟動時驗證本單元的設定，記一條 INFO（`BR3.4`／`NFR8.60`）。

    由 `backend/main.py` 的 startup hook 呼叫，與 `configure_session_env()`
    並列、形狀刻意相同：**失敗即拋**。掛在 startup hook 而非 import 時，是為了
    讓既有測試（完全不設定本變數、且以 `TestClient(app)` 不觸發本 hook）不受
    影響——既有測試全綠本身就是這個選擇的驗證。
    """
    config = resolve_routing_config(env)
    logger.info(
        "intent router 設定已解析：模型 %s、逾時 %s 秒、每輪上限 %s 次、"
        "重試 %s 次、信心門檻 %s",
        config.model,
        config.timeout_seconds,
        config.max_calls_per_turn,
        config.max_retries,
        config.confidence_threshold,
    )
    return config


__all__ = [
    "DEFAULT_MAX_CALLS_PER_TURN",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SEC",
    "MAX_CALLS_ENV",
    "MAX_RETRIES_ENV",
    "MODEL_ENV",
    "THRESHOLD_ENV",
    "TIMEOUT_ENV",
    "RoutingConfig",
    "configure_intent_routing_env",
    "resolve_confidence_threshold",
    "resolve_routing_config",
]
