"""Embedding Port 與其三個實作（`U6 embedding-port`，契約 `K-06`）。

這個模組把文字變成 1024 維向量，並回報該向量所屬的**向量空間身分**
（`model_id`）。消費端只有一個：`U8 memory-service`。

契約（消費端依賴，請勿變更）
-----------------------------
- `embed(texts) -> list[list[float]]`：長度等於輸入長度、順序一一對應，
  每個向量**恰為** 1024 維（`BR2.1`／`BR2.2`）。
- `model_id() -> str`：寫入記憶列的 `embeddingModel` 的值。回報的是**模型身分**
  而不是提供者名稱（`BR3.5`）——`OLLAMA_EMBED_MODEL` 是可設定變數，用提供者名稱
  當身分會讓換模型之後兩個不同的向量空間共用同一個標籤，而「只比對同一
  `embeddingModel` 的列」那道過濾會把它們判定為可比較：回垃圾且不報錯。
- 唯一的例外型別是 `EmbeddingProviderUnavailable`（`K-06` 的 `raises`）。
  偵測不到選定提供者時**大聲失敗並列出可選值，不得靜默降級為全文檢索**
  （ADR-008）。
- 本 Port **不重試**（`BR2.6`）；重試上限由呼叫端決定。
- 本 Port **不碰授權判定、不讀資料庫、不新增任何 HTTP 入口**（`SEC-1`／`BR2.7`）。
  這三條以 `tests/test_embedding_port.py` 的原始碼掃描機械保證（`D-9`）。

這個模組刻意沒有的東西
----------------------
- **沒有啟動探測**（`BR1.5`）。建構 Port 只讀設定，不發請求、不載模型。理由是兩條
  已查證的既有事實：CI 的短生命週期 stack 根本沒有 ollama 服務
  （`deploy/docker-compose.test.yml:18` 逐字「NO ollama」），而部署流程是在
  `up -d` **之後**才跑 `ollama pull`——啟動探測會讓每次部署在模型就位前就紅燈，
  然後觸發自動回退。
- **沒有重試、沒有斷路器、沒有降級**（`logical-components.md §五`）。降級會讓
  「為什麼找不到我的記憶」變成無法除錯的問題。
- **沒有第三方 import 在模組層**。`httpx` 在用到它的那個方法裡才 import：
  `scripts/validate_embedding_provider_value.py` 會在 CI 的 `repo-contract` job
  裡 import 本模組取允許值集合，而那個 job 不安裝 `requirements.txt`。
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

logger = logging.getLogger("cloud360.embedding_port")


# --- 提供者的允許值集合（**單一真實來源**）---------------------------------
#
# `scripts/validate_embedding_provider_value.py` 直接 import 這個 tuple 去驗
# `deploy/render-env.sh` 寫出的值。**它不得自行列舉這四個字串**——那會製造第二份
# 清單，而第二份清單一定會漂移（`cicd-pipeline.md` 的 `H-I3` 逐字禁止）。
PROVIDER_OLLAMA = "ollama"
PROVIDER_FASTEMBED = "fastembed"
PROVIDER_FULLTEXT = "fulltext"
PROVIDER_STUB = "stub"
ALLOWED_PROVIDERS = (
    PROVIDER_OLLAMA,
    PROVIDER_FASTEMBED,
    PROVIDER_FULLTEXT,
    PROVIDER_STUB,
)

# 向量維度。**恰為** 1024，不是「至少」也不是「至多」（`BR2.2`）。
# 1024 是 ADR-008 的定案（記憶列的 `vector(1024)` 欄位），兩個真實提供者同維度。
EMBEDDING_DIMENSIONS = 1024

# 預設的模型身分。`ollama`／`fastembed` 兩者可由環境變數覆寫（它們的 context
# 維度約束仍是 1024）；`stub` **不可設定**。
DEFAULT_OLLAMA_EMBED_MODEL = "bge-m3"
DEFAULT_FASTEMBED_MODEL = "multilingual-e5-large"
STUB_MODEL_ID = "stub-v1"

# 記憶列的 `embeddingModel` 合法值集合（不含 `NULL`）——`BR3.3` 雙向一致性的
# **S 側**。
#
# **刻意寫成字面值，而不是引用上面那三個常數。** 若兩側共用同一組常數，
# `BR3.3` 的那個測試就變成恆真：把 `STUB_MODEL_ID` 改成 `bge-m3` 會讓兩側同時
# 塌成兩個元素而測試照樣綠。這份清單是「資料層認得哪些向量空間」的宣告，
# I 側則是「實作實際會產生哪些值」，兩者必須能各自漂移才驗得出漂移。
#
# `NULL` 的唯一意義是「該列在無 Port（`fulltext`）模式下建立」，其向量欄位
# 必須同時為 `NULL`——該不變量的執行落點在 `U5`／`U8`，不在本模組（交接 `H-E1`）。
MEMORY_RECORD_EMBEDDING_MODELS = ("bge-m3", "multilingual-e5-large", "stub-v1")

# **哪個提供者可以合法宣告哪個向量空間身分。**
#
# 集合成員檢查不足以防住污染：審查實測 `EMBEDDING_PROVIDER=ollama` ＋
# `OLLAMA_EMBED_MODEL=stub-v1` 會被接受，而那會把**真實的 ollama 向量**蓋上
# stub 的身分——正是 `BR3.6` 註解逐字描述的後果（「CI 短生命週期 stack 每個 PR
# 寫入的列會與 staging 寫入的列在資料上不可區分」）。集合檢查看不到這件事，
# 因為 `stub-v1` 確實在集合內；錯的是**對應關係**而不是成員資格。
#
# 本表以 provider 為鍵，故檢查的是對應關係；它同時蘊含集合成員檢查
# （聯集等於上面那個集合，由 `test_provider_model_map_matches_the_declared_set`
# 機械鎖住）。換 ollama 的模型是**刻意**要同時改這裡與上面那一行的——因為那同時
# 需要既有列的遷移方式（ADR-008）。
#
# 仍然寫成字面值而不引用 `DEFAULT_*` 常數：`BR3.3` 的雙向測試需要 I 側與 S 側
# 能各自漂移，共用來源會讓突變 `M9` 照樣綠。
PROVIDER_LEGAL_MODEL_IDS = {
    PROVIDER_OLLAMA: ("bge-m3",),
    PROVIDER_FASTEMBED: ("multilingual-e5-large",),
    PROVIDER_STUB: ("stub-v1",),
}

# **記憶列上的向量空間身分 ≠ fastembed 套件登錄的模型名。**
#
# 身分（`multilingual-e5-large`）是寫進記憶列 `embeddingModel` 的值，也是
# `FASTEMBED_MODEL` 的設定值；fastembed 0.7 的 `TextEmbedding` 只認它自己的登錄名
# `intfloat/multilingual-e5-large`，傳身分進去會直接 `ValueError: Model
# multilingual-e5-large is not supported`——本模組落地後這條路徑因此從未能用過
# （2026-10-20 以 `fastembed>=0.7,<0.8` 實測；CI 與部署都不裝它，所以沒被抓到）。
# 改在這裡對照，而不是把身分改成登錄名：身分是資料層的宣告，改它要動
# `MEMORY_RECORD_EMBEDDING_MODELS`、四份設定範本與既有列的遷移（ADR-008），
# 而套件換登錄名只需要改這一行。鍵集合必須等於 fastembed 的合法身分，
# 由 `test_fastembed_registry_names_cover_every_legal_identity` 鎖住。
FASTEMBED_REGISTRY_NAMES = {
    "multilingual-e5-large": "intfloat/multilingual-e5-large",
}

# 各提供者的輸入上限，單位是**字元**。
#
# 本模組不引入 tokenizer（零新依賴），所以這裡量的是字元數而非 token 數，
# 換算取**保守**的 1 token ≈ 1 字元：中日韓文字在這兩個模型的 tokenizer 下
# 接近 1:1，拉丁文字遠低於 1。低估上限只會讓截斷早一點發生並記一條 WARN；
# 高估會讓請求被提供者拒絕。鍵是**提供者**而非模型（`D-4` 逐字「選定提供者的
# context 上限」）；若有人為 `ollama` 設了一個 context 更小的 1024 維模型，
# 這個值會偏大——那是已知限制，不是靜默的：超限會由該提供者回錯而成為
# `EmbeddingProviderUnavailable`。
PROVIDER_CONTEXT_LIMIT_CHARS = {
    PROVIDER_OLLAMA: 8192,  # bge-m3 的 context 為 8192 token
    PROVIDER_FASTEMBED: 512,  # multilingual-e5-large 的 context 為 512 token
    PROVIDER_STUB: 8192,  # 無真實上限；取與 ollama 相同值讓三者行為一致
}

# 外部呼叫的逾時上界（秒）。預設 10，可由 `EMBEDDING_TIMEOUT_SEC` 覆寫。
DEFAULT_EMBEDDING_TIMEOUT_SEC = 10.0

_FASTEMBED_INSTALL_HINT = "pip install 'fastembed>=0.7,<0.8'"

# 合法的 compose 內部服務名：單一 DNS label。有點就是 FQDN、是 IP 字面值就不是
# 服務名——兩者都不被接受（`NFR7.1`）。
_SERVICE_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$", re.IGNORECASE)

# URL 文法裡的 userinfo 片段：`//user:pass@host`。
#
# 以這個片段為錨點而不是用結構化解析，是因為要清的不只有我們自己組的 URL——
# 第三方套件的例外訊息裡也可能夾著一個完整 URL，而它不保證是整個字串。
_URL_USERINFO = re.compile(r"//[^/\s@]*@")


def _without_userinfo(text: Optional[str]) -> Optional[str]:
    """移除 URL（或任何含 URL 的文字）的 userinfo 區段。

    `SEC-2`／`D-7`／`BR4.4`／`BR7.2`：帶 endpoint 時只帶主機與埠，
    不得帶 `http://user:pass@host` 的帳密部分。

    **這不是唯一的剝除點，但兩個剝除點也不是各自獨立的——它們是串聯的。**
    此處的敘述經過兩次更正，兩次都由突變驗證推翻，故逐字寫清楚：

    - `detail` 只經過**一層**：本函式。這是它唯一的保護，突變 `M7`（把本函式
      從例外建構子拿掉）即由此被攔下。
    - `target` 經過**兩層，串聯**：`OllamaAdapter._target()` 先以
      `_host_and_port()` 把它縮到 `scheme://host:port`（`urlsplit().hostname`
      天然丟掉 userinfo），例外建構子再對它呼叫一次本函式當後備。

    最初的註解宣稱本函式是「唯一的剝除點」——錯。第一次更正改成「兩個各自
    **獨立**的剝除點」——也錯，而且錯的方式更隱蔽：審查的 `MUT-F`（讓
    `_host_and_port` 改用 `netloc`、保留 userinfo）**19 個測試全綠**，正因為
    建構子這一層默默補上了，兩者並非各自獨立而是同一個欄位上的縱深防禦。

    實務後果：今天沒有外洩（建構子是後備），但 `target` 路徑上**兩層都要有
    自己的測試**，否則內層壞掉不會有任何紅燈。覆蓋現況：
    `test_host_and_port_strips_userinfo`（內層）與
    `test_exception_constructor_strips_userinfo_from_target_and_detail`（外層）。
    """
    if not text:
        return text
    return _URL_USERINFO.sub("//", text)


def _host_and_port(url: str) -> str:
    """只取 URL 的主機與埠，供日誌使用（`BR7.1`）。"""
    parts = urlsplit(url)
    if not parts.hostname:
        return _without_userinfo(url) or ""
    host = parts.hostname
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, "", "", ""))


class EmbeddingProviderUnavailable(RuntimeError):
    """選定的 embedding 提供者不可用（`K-06` 的唯一例外）。

    三個欄位都是契約的一部分（`entities.md`／`D-7`）：
    `selected_provider`、`target`、`available_options`。`available_options`
    恆為四個可選值——那是 ADR-008「**列出可選值**」唯一可機械斷言的落點。

    本 Port **不自己記 ERROR**（`D-8`）：拋出即交給呼叫端。同一個失敗被兩層
    各記一次，會讓日誌上的錯誤數是真實數的兩倍，而呼叫端才有「這次失敗要不要
    降級」的上下文。
    """

    def __init__(
        self,
        selected_provider: str,
        target: Optional[str] = None,
        detail: Optional[str] = None,
        available_options: Sequence[str] = ALLOWED_PROVIDERS,
    ) -> None:
        self.selected_provider = selected_provider
        self.target = _without_userinfo(target)
        self.detail = _without_userinfo(detail)
        self.available_options = tuple(available_options)

        message = f"embedding 提供者 {selected_provider!r} 不可用"
        if self.target:
            message += f"（目標：{self.target}）"
        if self.detail:
            message += f"：{self.detail}"
        message += (
            "。可選值："
            + "｜".join(self.available_options)
            + "。不得靜默降級為全文檢索——請修好該提供者，"
            "或改設 EMBEDDING_PROVIDER。"
        )
        super().__init__(message)


@dataclass(frozen=True)
class ProviderSelection:
    """啟動時對設定解析一次的結果。**不可變**（`BR1.2`）。

    不支援執行期切換提供者：切換會讓同一個行程先後落在兩個向量空間，
    而 `embed` 的純函式語意（同輸入同輸出）在那之下不成立。

    `resolved_at` 以 `compare=False` 排除於相等比較之外。欄位本身是 `entities.md`
    要求的（啟動日誌要能回答「這個行程跑的是哪個提供者、哪個模型」），但 `D-2`
    的驗證方式是「連續呼叫兩次結果相等」——把一個時間戳算進相等就永遠不會相等。
    """

    provider_name: str
    port_present: bool
    model_id: Optional[str]
    endpoint: Optional[str]
    resolved_at: datetime = field(
        compare=False, default_factory=lambda: datetime.now(timezone.utc)
    )


def _timeout_from_env() -> float:
    """`EMBEDDING_TIMEOUT_SEC` → 秒數，缺值或壞值回預設 10。

    這個變數是**選填**的（`tech-stack-decisions.md §二`），所以壞值記 WARN 後取
    預設，不終止啟動。`BR1.6`「驗證失敗即終止」的範圍逐字是 `BR1.1` 與 `BR1.3`
    ——提供者與 endpoint，不是這個可選的調節值。拿一行過期的調節值去換整個 API
    的開機失敗，與 `llm_provider.py` 對同一個形狀寫下的理由相反。
    """
    raw = os.environ.get("EMBEDDING_TIMEOUT_SEC", "").strip()
    if not raw:
        return DEFAULT_EMBEDDING_TIMEOUT_SEC
    try:
        value = float(raw)
    except ValueError:
        logger.warning(
            "EMBEDDING_TIMEOUT_SEC=%r 不是數字，改用預設 %s 秒。",
            raw,
            DEFAULT_EMBEDDING_TIMEOUT_SEC,
        )
        return DEFAULT_EMBEDDING_TIMEOUT_SEC
    if value <= 0:
        logger.warning(
            "EMBEDDING_TIMEOUT_SEC=%r 不是正數，改用預設 %s 秒"
            "（無上界的呼叫會讓記憶路徑無限期掛住）。",
            raw,
            DEFAULT_EMBEDDING_TIMEOUT_SEC,
        )
        return DEFAULT_EMBEDDING_TIMEOUT_SEC
    return value


# 模組層**具名常數**（`D-6`／`NFR3.2`）。模組內不得出現裸數字 timeout——
# 形狀沿用既有的 `LENS_AGENT_TIMEOUT_SEC`。
#
# 它**不是** `NFR3`（首字回應 P50 ≤ 2 秒）的保護機制：10 秒是那條預算的 5 倍。
# 它保護的是「服務掛掉時不要無限期掛住」。
EMBEDDING_TIMEOUT_SEC: float = _timeout_from_env()


def _read_embedding_env() -> dict:
    """本模組消費的四個既有環境變數（契約 `K-01`）。

    逐一寫成 `os.environ.get("…")` 字面形式是刻意的：
    `scripts/validate_env_contract.py` 的 `validate_local_dev_template_is_complete`
    以這個形狀掃出「backend 讀了哪些變數」，而每一個都必須被
    `backend/.env.example` 記載。間接取值會讓那道檢查看不到它們。
    """
    return {
        "EMBEDDING_PROVIDER": os.environ.get("EMBEDDING_PROVIDER", ""),
        "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", ""),
        "OLLAMA_EMBED_MODEL": os.environ.get("OLLAMA_EMBED_MODEL", ""),
        "FASTEMBED_MODEL": os.environ.get("FASTEMBED_MODEL", ""),
    }


def _reject(reason: str) -> None:
    """設定層錯誤一律終止啟動（`BR1.6`、ADR-008「不得靜默降級」）。

    `ValueError` 而不是 `EmbeddingProviderUnavailable`：`BR4.2` 把兩類失敗分開
    ——設定值缺失或不在允許集合內走啟動失敗，提供者連不上才走那個例外。
    兩類混用會讓啟動失敗的訊息與執行期例外無法分辨肇因。
    """
    raise ValueError(
        reason + " 可選值：" + "｜".join(ALLOWED_PROVIDERS) + "。"
        "（偵測不到選定提供者時須大聲失敗，不得靜默降級為全文檢索。）"
    )


def _validate_ollama_endpoint(raw_url: str) -> str:
    """`OLLAMA_BASE_URL` 必填，且主機名須為 compose 內部服務名（`NFR7.1`）。

    不得為 `localhost`、`127.0.0.1`、任何 IP 字面值或任何 FQDN。唯一的存取控制
    是網段隔離（該服務的 HTTP API 零認證、無 host port），而把 base URL 指到
    compose 網路之外就直接繞過它——記憶文字會以明文送到那個位址。
    """
    url = raw_url.strip()
    if not url:
        _reject(
            "EMBEDDING_PROVIDER=ollama 但 OLLAMA_BASE_URL 未設定。"
            "它沒有預設值：空字串會讓服務照常啟動而記憶功能靜默失效。"
        )
    parts = urlsplit(url)
    host = parts.hostname
    if not host:
        _reject(
            f"OLLAMA_BASE_URL={_without_userinfo(url)!r} 解析不出主機名"
            "（需要 scheme://host[:port] 形式）。"
        )
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".localhost"):
        _reject(
            f"OLLAMA_BASE_URL 的主機名為 {host!r}，而它必須是 compose 內部服務名"
            "（例如 ollama）。在部署 stack 裡 localhost 指向 backend 容器自己。"
        )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        _reject(
            f"OLLAMA_BASE_URL 的主機名為 IP 字面值 {host!r}，"
            "而 compose 內部服務名是 DNS 名稱，不是 IP。"
        )
    if not _SERVICE_NAME.match(host):
        _reject(
            f"OLLAMA_BASE_URL 的主機名為 {host!r}，看起來是對外網域而不是 compose "
            "內部服務名。該服務的 HTTP API 零認證，網段隔離是它唯一的存取控制。"
        )
    return url


def resolve_provider_selection(
    env: Optional[Mapping[str, str]] = None,
) -> ProviderSelection:
    """解析並驗證 embedding 設定，回傳不可變的 `ProviderSelection`。

    **冪等、無副作用**（`D-2`）：只讀環境變數、不建連線、不載模型、不發請求。
    失敗一律拋 `ValueError`（`BR1.6`）。

    `env` 參數讓 CI 的 `scripts/validate_embedding_provider_value.py` 把
    `deploy/render-env.sh` 會寫出的那組值餵進同一條驗證路徑，
    而不需要在那支腳本裡複製一份允許值清單。
    """
    source = _read_embedding_env() if env is None else env

    raw_provider = (source.get("EMBEDDING_PROVIDER") or "").strip()
    if not raw_provider:
        _reject("EMBEDDING_PROVIDER 未設定，而它刻意沒有預設值。")
    provider = raw_provider.lower()
    if provider not in ALLOWED_PROVIDERS:
        _reject(f"EMBEDDING_PROVIDER={raw_provider!r} 不是合法值。")

    if provider == PROVIDER_FULLTEXT:
        # 無 Port（`BR1.4`／`D-10`）。三者等價：port_present 為 false
        # ⟺ model_id 為 None ⟺ provider 為 fulltext。
        return ProviderSelection(
            provider_name=provider,
            port_present=False,
            model_id=None,
            endpoint=None,
        )

    endpoint: Optional[str] = None
    if provider == PROVIDER_OLLAMA:
        endpoint = _validate_ollama_endpoint(source.get("OLLAMA_BASE_URL") or "")
        model_id = (
            source.get("OLLAMA_EMBED_MODEL") or ""
        ).strip() or DEFAULT_OLLAMA_EMBED_MODEL
    elif provider == PROVIDER_FASTEMBED:
        model_id = (
            source.get("FASTEMBED_MODEL") or ""
        ).strip() or DEFAULT_FASTEMBED_MODEL
    else:
        # stub 的身分**不可設定**（`BR3.6`）。若它回 `bge-m3`，CI 寫入的列與
        # staging 寫入的列在資料上不可區分——那正是 ADR-008 要防的跨向量空間
        # 污染，而 CI 的短生命週期 stack 每個 PR 都會寫入。
        model_id = STUB_MODEL_ID

    # 不屬於該提供者的 model_id 一律擋在啟動。
    #
    # 這個檢查原本不存在，而 `OLLAMA_EMBED_MODEL`／`FASTEMBED_MODEL` 可被設成
    # 任意非空字串：少了它，記憶列會被蓋上錯誤的 `embeddingModel`，而「只比對
    # 同一 `embeddingModel` 的列」那道過濾會把兩個不同向量空間判定為可比較
    # ——正是 ADR-008 要防的污染，且最早只會在 `U8` 寫入時才（或根本不會）
    # 被發現。**設定錯誤要在啟動就大聲失敗。**
    #
    # **檢查的是對應關係，不是集合成員資格。** 第一版只驗「在宣告集合內」，
    # 而審查實測 `ollama` ＋ `stub-v1` 因此被放行——`stub-v1` 在集合內，但它
    # 不是 ollama 能合法宣告的身分。以 provider 為鍵的檢查同時涵蓋兩者。
    legal_for_provider = PROVIDER_LEGAL_MODEL_IDS[provider]
    if model_id not in legal_for_provider:
        raise ValueError(
            f"提供者 {provider} 不得宣告模型身分 {model_id!r}。"
            f"{provider} 的合法身分為：" + "｜".join(legal_for_provider) + "。"
            "（記憶列的合法 embeddingModel 集合為 "
            + "｜".join(MEMORY_RECORD_EMBEDDING_MODELS)
            + "，但身分必須與產生它的提供者相符：把真實提供者的向量蓋上別人的"
            "身分，會讓兩個不同的向量空間在資料上不可區分，檢索時被當成可比較"
            "而回垃圾且不報錯。）換模型必須同時更新 PROVIDER_LEGAL_MODEL_IDS、"
            "MEMORY_RECORD_EMBEDDING_MODELS 與既有列的遷移方式（ADR-008）。"
        )

    return ProviderSelection(
        provider_name=provider,
        port_present=True,
        model_id=model_id,
        endpoint=endpoint,
    )


class EmbeddingPort:
    """`K-06` 的介面。公開方法只有 `embed` 與 `model_id`，兩者皆同步。

    `embed` 在這裡是 template method，三個共通行為因此只有一處實作：
    截斷（`D-4`）、回傳形狀的執行期斷言（`BR2.1`／`BR2.2`）、
    以及每次呼叫的一條 INFO（`D-5` 第 2 條）。
    """

    def __init__(self, selection: ProviderSelection) -> None:
        self._selection = selection

    # --- 公開介面（契約，請勿變更）-----------------------------------------

    def model_id(self) -> str:
        """該向量空間的身分。同一個 `ProviderSelection` 下恆定（`BR3.2`）。"""
        model = self._selection.model_id
        if model is None:  # port_present 為 true 時不可能發生
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name, detail="這個選擇沒有模型身分"
            )
        return model

    def embed(self, texts: Sequence[str]) -> list:
        """把文字變成向量。長度與順序一一對應，每個恰 1024 維。

        空輸入回 `[]` 且**不接觸外部**（`BR2.4`）。任一元素失敗則整批拋例外，
        不回傳部分結果、不以零向量填補（`BR2.5`）——以零向量填補會讓一個
        看起來合法的 1024 維向量被寫進記憶，而檢索會回垃圾且不報錯。
        """
        prepared = list(texts)
        started = time.perf_counter()
        if prepared:
            vectors = self._embed_batch(self._truncate(prepared))
        else:
            vectors = []
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        self._verify_shape(vectors, prepared)

        # `D-5` 第 2 條：每次 embed 一條 INFO，含耗時毫秒。它讓延遲可由日誌
        # 事後統計出 P50／P95（一條 awk 即可），不需要任何端點或新依賴。
        # **它不是自動化斷言**——沒有任何 CI 檢查會因為 embed 變慢而紅燈（`RR-4`）。
        # 不記的事：待向量化的文字、向量值本身、任何憑證。前兩者是使用者的對話
        # 內容，記進日誌等於在另一個地方複製一份記憶。
        logger.info(
            "embed 完成：provider=%s model=%s 批次大小=%d 耗時=%.1fms",
            self._selection.provider_name,
            self._selection.model_id,
            len(prepared),
            elapsed_ms,
        )
        return vectors

    # --- 子類別實作這一個 ---------------------------------------------------

    def _embed_batch(self, texts: Sequence[str]) -> list:
        raise NotImplementedError

    # --- 共通行為 -----------------------------------------------------------

    def _truncate(self, texts: Sequence[str]) -> list:
        """超長輸入截斷到提供者上限並記 WARN，**不拋例外**（`D-4`）。

        截斷會**靜默降低**該筆記憶的檢索品質，WARN 是唯一的可見訊號。
        拋例外在這裡是錯的：一句過長的對話不該讓整批記憶寫入失敗。
        """
        limit = PROVIDER_CONTEXT_LIMIT_CHARS.get(self._selection.provider_name)
        if not limit:
            return list(texts)
        out = []
        for index, text in enumerate(texts):
            if len(text) > limit:
                dropped = len(text) - limit
                logger.warning(
                    "embedding 輸入超過上限已截斷：provider=%s 索引=%d 原長度=%d "
                    "上限=%d 截掉字元數=%d。該筆的檢索品質會下降。",
                    self._selection.provider_name,
                    index,
                    len(text),
                    limit,
                    dropped,
                )
                out.append(text[:limit])
            else:
                out.append(text)
        return out

    def _verify_shape(self, vectors, texts: Sequence[str]) -> None:
        """執行期斷言 `BR2.1`／`BR2.2`，對三個實作一視同仁。

        它存在的理由是 CI 跑不到 `ollama` 與 `fastembed`（test stack 無該服務、
        該套件不在 `requirements.txt`）。「它們實際回傳的向量是否真為 1024 維」
        因此只能在首次真實呼叫時被攔下——而這一行就是攔它的地方：
        **大聲失敗，不是靜默**，更不是等到寫入 `vector(1024)` 欄位時才變成
        一個資料庫錯誤（具名缺口 `OQ-E2`）。
        """
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=self._target(),
                detail=(
                    f"回傳 {len(vectors) if isinstance(vectors, list) else '非序列'} "
                    f"個向量，但輸入有 {len(texts)} 筆"
                ),
            )
        for index, vector in enumerate(vectors):
            if len(vector) != EMBEDDING_DIMENSIONS:
                raise EmbeddingProviderUnavailable(
                    self._selection.provider_name,
                    target=self._target(),
                    detail=(
                        f"第 {index} 個向量為 {len(vector)} 維，"
                        f"而契約要求恰為 {EMBEDDING_DIMENSIONS} 維"
                    ),
                )

    def _target(self) -> Optional[str]:
        """例外的 `target` 欄位。`stub` 無目標可言。"""
        return self._selection.endpoint


class StubAdapter(EmbeddingPort):
    """決定性替身。無外部依賴、不可能不可用。

    向量由輸入文字的 SHA-256 摘要**決定性展開**為 1024 個 float（`D-3`）。

    **不同輸入必須得到不同向量，這不是裝飾性的。** 若它對所有輸入回同一個向量，
    `P1`／`P2`／`P3`／`P6` 全部會過，而 `U8` 日後用它寫的任何相似度測試都變成
    恆真——每一列的距離都相同。那正是 `D-3` 存在的全部理由（突變 `M1`）。

    它**不具語意**：相近的句子不會得到相近的向量。
    """

    def _embed_batch(self, texts: Sequence[str]) -> list:
        return [_stub_vector(text) for text in texts]


def _stub_vector(text: str) -> list:
    """SHA-256 的 counter 區塊展開為 1024 個 [-1, 1] 的 float。

    每個區塊 32 bytes 給 8 個 float，故 1024 維需 128 個區塊。輸入進了摘要，
    所以同輸入同輸出、不同輸入幾乎必然不同；而**單筆與分批走同一條路徑**，
    `P4`（分批不變性）因此成立——那是六個性質裡最有價值的一個，因為批次與
    單筆不一致所產生的向量在資料上不可偵測（兩者都是合法的 1024 維向量）。
    """
    seed = text.encode("utf-8")
    values = []
    counter = 0
    while len(values) < EMBEDDING_DIMENSIONS:
        block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        for offset in range(0, len(block), 4):
            if len(values) >= EMBEDDING_DIMENSIONS:
                break
            word = int.from_bytes(block[offset : offset + 4], "big")
            values.append(word / 0xFFFFFFFF * 2.0 - 1.0)
        counter += 1
    return values


class OllamaAdapter(EmbeddingPort):
    """對同主機的 ollama 服務發一次明文 HTTP 請求。

    這是本模組**唯一**把資料送出 backend 行程的那一步（`security-design.md §三`）。
    具名殘餘風險 `RR-1`：明文傳輸 ＋ 零認證的端點，唯一的控制是網段隔離
    （啟動時的主機名驗證 ＋ 該服務不得 publish host port）。

    `httpx` 是既有依賴，不新增第二個 HTTP 客戶端（`BR6.2`）。
    """

    def _embed_batch(self, texts: Sequence[str]) -> list:
        # 在方法內 import：本模組會被 CI 的 `repo-contract` job import（為了取
        # 允許值集合），而那個 job 不安裝 `requirements.txt`。
        import httpx

        endpoint = self._selection.endpoint or ""
        url = endpoint.rstrip("/") + "/api/embed"
        payload = {"model": self._selection.model_id, "input": list(texts)}
        try:
            # timeout 永遠是那個具名常數（`D-6`）。**本模組不得出現裸數字 timeout。**
            with httpx.Client(timeout=EMBEDDING_TIMEOUT_SEC) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            # 逾時、連線失敗、HTTP 錯誤狀態三者都歸入這一個例外型別
            # （`NFR3.2` 逐字「不新增第二種例外」）。**不重試**（`BR2.6`）。
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=self._target(),
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc
        except ValueError as exc:  # 回應不是 JSON
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=self._target(),
                detail=f"回應不是合法 JSON：{exc}",
            ) from exc

        vectors = body.get("embeddings") if isinstance(body, dict) else None
        if not isinstance(vectors, list):
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=self._target(),
                detail="回應沒有 embeddings 陣列",
            )
        try:
            return [[float(value) for value in vector] for vector in vectors]
        except (TypeError, ValueError) as exc:
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=self._target(),
                detail=f"embeddings 內含非數值：{exc}",
            ) from exc

    def _target(self) -> Optional[str]:
        endpoint = self._selection.endpoint
        return _host_and_port(endpoint) if endpoint else None


class FastembedAdapter(EmbeddingPort):
    """行程內 ONNX 推論。套件由使用者自裝，**不在 `requirements.txt`**（`BR6.1`）。

    無條件安裝會把 ONNX runtime 與模型載入器放進每個 image，而三個環境中只有
    「本機且無 ollama」會選它。首次使用會從 HuggingFace 下載約 1GB 權重，
    且這條路徑**不經 CI**——其供應鏈風險由使用它的開發者承擔（具名風險 `RR-2`、
    `SEC-3`，說明寫在 `LOCAL-DEV.md`）。

    它在 backend 行程內吃 CPU 與記憶體，與請求處理競爭。這是本機限定的取捨。
    """

    def __init__(self, selection: ProviderSelection) -> None:
        super().__init__(selection)
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            # lazy import（`BR6.1`）：套件不在依賴宣告裡，所以模組層 import 會讓
            # 整個 backend 在三個環境中有兩個無法啟動。
            from fastembed import TextEmbedding
        except Exception as exc:  # ImportError，以及 sys.modules 被設為 None 時的 TypeError
            # 不讓原始的 ImportError 傳出去：它不會告訴使用者該裝什麼（`BR4.3`）。
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=f"{self._selection.model_id}（{_FASTEMBED_INSTALL_HINT}）",
                detail=(
                    "fastembed 未安裝。它刻意不在 backend/requirements.txt 內"
                    "（選用依賴，只有本機且無 ollama 時才需要）。"
                    f"安裝指令：{_FASTEMBED_INSTALL_HINT}"
                ),
            ) from exc
        try:
            self._model = TextEmbedding(
                model_name=FASTEMBED_REGISTRY_NAMES[self._selection.model_id]
            )
        except Exception as exc:
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=f"{self._selection.model_id}（{_FASTEMBED_INSTALL_HINT}）",
                detail=f"模型載入失敗 {type(exc).__name__}: {exc}",
            ) from exc
        return self._model

    def _embed_batch(self, texts: Sequence[str]) -> list:
        model = self._load_model()
        try:
            return [[float(value) for value in vector] for vector in model.embed(list(texts))]
        except EmbeddingProviderUnavailable:
            raise
        except Exception as exc:
            raise EmbeddingProviderUnavailable(
                self._selection.provider_name,
                target=f"{self._selection.model_id}（{_FASTEMBED_INSTALL_HINT}）",
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

    def _target(self) -> Optional[str]:
        return f"{self._selection.model_id}（{_FASTEMBED_INSTALL_HINT}）"


_IMPLEMENTATIONS = {
    PROVIDER_OLLAMA: OllamaAdapter,
    PROVIDER_FASTEMBED: FastembedAdapter,
    PROVIDER_STUB: StubAdapter,
}


def resolve_embedding_port(
    selection: Optional[ProviderSelection] = None,
) -> Optional[EmbeddingPort]:
    """選定提供者的 Port，或 `None`（`fulltext`）。

    **回傳 `Optional` 是契約的一部分**（`BR1.4`／`D-10`）：`fulltext` 的語意是
    「不建立 Port」而不是「一個會算向量的實作」，所以呼叫端以「有沒有拿到 Port」
    分流，**不以例外分流**。`K-06` 的 `implementations` 四個值在型別上讀作
    「三個實作 ＋ 一個停用狀態」（交接 `H-E3`）。

    建構**只讀設定**：不發請求、不載模型（`BR1.5`）。
    """
    if selection is None:
        selection = resolve_provider_selection()
    if not selection.port_present:
        return None
    return _IMPLEMENTATIONS[selection.provider_name](selection)


def configure_embedding_env() -> ProviderSelection:
    """啟動時解析並驗證 embedding 設定，記一條 INFO（`D-1`／`BR7.1`）。

    由 `backend/main.py` 的 startup hook 呼叫，位置在 `configure_provider_env()`
    與 `init_db()` 之間。

    **失敗即拋**（`BR1.6`）——這與相鄰的 `configure_provider_env()` 只記日誌
    刻意不同：ADR-008 逐字「不得靜默降級」，而一個拼錯的提供者名若只記 WARN，
    記憶功能會在沒有任何錯誤訊息的情況下整個消失。

    **掛在 startup hook 而不是 import 時**也是刻意的：既有的測試完全不設定
    embedding 環境變數，而以 `TestClient(app)` 直接使用不觸發這個 hook。
    既有測試全綠本身就是這個選擇的驗證。
    """
    selection = resolve_provider_selection()
    if selection.port_present:
        logger.info(
            "embedding 提供者已解析：provider=%s model=%s endpoint=%s timeout=%ss",
            selection.provider_name,
            selection.model_id,
            _host_and_port(selection.endpoint) if selection.endpoint else "（行程內）",
            EMBEDDING_TIMEOUT_SEC,
        )
    else:
        logger.info(
            "embedding 提供者已解析：provider=%s —— 無 Port（fulltext），"
            "記憶檢索走全文搜尋，寫入的列其向量與 embeddingModel 同時為 NULL。",
            selection.provider_name,
        )
    return selection


__all__ = [
    "ALLOWED_PROVIDERS",
    "DEFAULT_EMBEDDING_TIMEOUT_SEC",
    "DEFAULT_FASTEMBED_MODEL",
    "FASTEMBED_REGISTRY_NAMES",
    "DEFAULT_OLLAMA_EMBED_MODEL",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_TIMEOUT_SEC",
    "EmbeddingPort",
    "EmbeddingProviderUnavailable",
    "FastembedAdapter",
    "MEMORY_RECORD_EMBEDDING_MODELS",
    "OllamaAdapter",
    "PROVIDER_CONTEXT_LIMIT_CHARS",
    "PROVIDER_FASTEMBED",
    "PROVIDER_FULLTEXT",
    "PROVIDER_OLLAMA",
    "PROVIDER_STUB",
    "ProviderSelection",
    "STUB_MODEL_ID",
    "StubAdapter",
    "configure_embedding_env",
    "resolve_embedding_port",
    "resolve_provider_selection",
]
