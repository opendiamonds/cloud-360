"""`U6 embedding-port` 的單元測試（契約 `K-06`）。

Methodology `test-after`、strategy `standard`。17 個測試：16 個由
`unit-test-instructions.md §二` 定義，第 17 個是 conductor 稽核landed 模組時
查出的 Major 缺陷的回歸測試（見 `test_model_id_must_be_in_the_declared_set`）。

六個 property（`P1`–`P6`）是 ADR-0006 的 **property-based hard constraint**
落點，由 `functional-design/functional-spec.md §五` 定義，本檔只負責以
`hypothesis` 的 `@given` 實作它們。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import

import logging
import math
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from services.embedding_port import (
    ALLOWED_PROVIDERS,
    DEFAULT_EMBEDDING_TIMEOUT_SEC,
    DEFAULT_FASTEMBED_MODEL,
    DEFAULT_OLLAMA_EMBED_MODEL,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_TIMEOUT_SEC,
    EmbeddingPort,
    EmbeddingProviderUnavailable,
    FASTEMBED_REGISTRY_NAMES,
    FastembedAdapter,
    MEMORY_RECORD_EMBEDDING_MODELS,
    OllamaAdapter,
    PROVIDER_CONTEXT_LIMIT_CHARS,
    PROVIDER_FASTEMBED,
    PROVIDER_FULLTEXT,
    PROVIDER_LEGAL_MODEL_IDS,
    PROVIDER_OLLAMA,
    PROVIDER_STUB,
    ProviderSelection,
    STUB_MODEL_ID,
    StubAdapter,
    _host_and_port,
    _timeout_from_env,
    configure_embedding_env,
    logger,
    resolve_embedding_port,
    resolve_provider_selection,
)

LOGGER_NAME = "cloud360.embedding_port"
MODULE_PATH = Path(__file__).resolve().parents[1] / "services" / "embedding_port.py"

# 突變驗證時關閉 shrink。理由是實測的：M4（破壞批次不變性）讓多個 property
# 同時失敗，hypothesis 縮小反例在一個刻意壞掉的實作上跑到病態——單一突變燒掉
# 10 分 51 秒的 100% CPU 仍未結束。而對「這個測試有沒有抓到突變」這個問題，
# 最小反例沒有任何資訊量：紅燈本身就是答案。
#
# 只在 AIDLC_MUTATION_RUN=1 時生效，正常執行（含 CI）完全不受影響。必須在
# 下方 PBT 建立之前載入：`settings(...)` 在建立當下繼承當時的 profile。
if os.environ.get("AIDLC_MUTATION_RUN") == "1":
    settings.register_profile(
        "aidlc-mutation",
        deadline=None,
        phases=(Phase.explicit, Phase.reuse, Phase.generate),
    )
    settings.load_profile("aidlc-mutation")

# property 測試的文字值域。`max_size=8` 讓單次 example 的 sha256 次數維持在
# 8 × 128 個區塊；`deadline=None` 是因為批次大小本身就是被測的量，不是效能。
TEXTS = st.lists(st.text(max_size=64), max_size=8)
PBT = settings(max_examples=25, deadline=None)


def stub_selection() -> ProviderSelection:
    return ProviderSelection(
        provider_name=PROVIDER_STUB,
        port_present=True,
        model_id=STUB_MODEL_ID,
        endpoint=None,
    )


def stub_port() -> StubAdapter:
    return StubAdapter(stub_selection())


def ollama_selection(endpoint: str = "http://ollama:11434") -> ProviderSelection:
    return ProviderSelection(
        provider_name=PROVIDER_OLLAMA,
        port_present=True,
        model_id=DEFAULT_OLLAMA_EMBED_MODEL,
        endpoint=endpoint,
    )


class EmbedContractTests(unittest.TestCase):
    """`embed` 的六個 property。全部對 `stub` 執行——它是唯一在 CI 可達的實作。"""

    @PBT
    @given(TEXTS)
    def test_embed_returns_one_vector_per_input(self, texts):
        """
        @purpose 驗證回傳向量數與輸入筆數一致、順序一一對應
        @given 任意長度 0–8 的文字序列
        @step 以 stub Port 呼叫 embed(texts)
        @pass len(result) == len(texts)，且逐筆重算單筆結果相等（順序未被打亂）
        @story P1、BR2.1
        """
        port = stub_port()
        result = port.embed(texts)
        self.assertEqual(len(result), len(texts))
        for index, text in enumerate(texts):
            self.assertEqual(result[index], port.embed([text])[0])

    @PBT
    @given(TEXTS)
    def test_every_vector_is_exactly_1024_dimensions(self, texts):
        """
        @purpose 驗證維度恰為 1024，不是「至少」也不是「至多」
        @given 任意長度 0–8 的文字序列
        @step 以 stub Port 呼叫 embed(texts)
        @pass 每個向量的 len() 恰等於 EMBEDDING_DIMENSIONS（1024）
        @story P2、BR2.2
        """
        self.assertEqual(EMBEDDING_DIMENSIONS, 1024)
        for vector in stub_port().embed(texts):
            self.assertEqual(len(vector), EMBEDDING_DIMENSIONS)

    @PBT
    @given(TEXTS)
    def test_embedding_is_deterministic_for_the_same_input(self, texts):
        """
        @purpose 驗證同輸入兩次呼叫得到完全相同的向量
        @given 任意長度 0–8 的文字序列
        @step 以同一組輸入連續呼叫 embed 兩次
        @pass 兩次結果完全相等
        @story P3、BR2.3
        """
        port = stub_port()
        self.assertEqual(port.embed(texts), port.embed(texts))

    @PBT
    @given(TEXTS)
    def test_batching_does_not_change_the_vector(self, texts):
        """
        @purpose 驗證分批不變性：批次呼叫與逐筆呼叫得到相同向量
        @given 任意長度 0–8 的文字序列
        @step 比對 embed(texts)[i] 與 embed([texts[i]])[0]
        @pass 兩者逐筆完全相等
        @story P4、BR2.1
        """
        port = stub_port()
        batched = port.embed(texts)
        for index, text in enumerate(texts):
            self.assertEqual(batched[index], port.embed([text])[0])

    @PBT
    @given(st.text(max_size=64), st.text(max_size=64))
    def test_different_inputs_get_different_vectors(self, left, right):
        """
        @purpose 驗證相異輸入得到相異向量——若不成立，下游所有相似度測試都會恆真
        @given 任意兩段文字
        @step 分別取得兩者的向量
        @pass 輸入相異時向量必相異；輸入相同時向量必相同
        @story D-3（突變 M1 的標的）
        """
        port = stub_port()
        a = port.embed([left])[0]
        b = port.embed([right])[0]
        if left == right:
            self.assertEqual(a, b)
        else:
            self.assertNotEqual(a, b)

    def test_empty_input_returns_empty_and_touches_nothing(self):
        """
        @purpose 驗證空輸入回 [] 且不接觸任何外部資源
        @given EMBEDDING_PROVIDER=ollama 的 Port（其 _embed_batch 會發 HTTP）
        @step 呼叫 embed([])
        @pass 回傳 []，且 _embed_batch 完全未被呼叫
        @story P6、BR2.4
        """
        port = OllamaAdapter(ollama_selection())
        with mock.patch.object(
            OllamaAdapter, "_embed_batch", side_effect=AssertionError("外部被呼叫了")
        ) as batch:
            self.assertEqual(port.embed([]), [])
        batch.assert_not_called()


class ProviderSelectionTests(unittest.TestCase):
    """設定解析與啟動驗證。"""

    def test_model_id_set_matches_the_allowed_value_set_both_ways(self):
        """
        @purpose 雙向驗證「實作會產生的 model_id 集合」與「資料層宣告的合法集合」相等
        @given 三個有 Port 的提供者各自在預設環境下的 model_id
        @step 組出 I 側集合，與 MEMORY_RECORD_EMBEDDING_MODELS（S 側）雙向比對
        @pass I ⊆ S 且 S ⊆ I，且 S 恰有三個元素
        @story P5、BR3.3
        """
        implemented = {
            DEFAULT_OLLAMA_EMBED_MODEL,
            DEFAULT_FASTEMBED_MODEL,
            STUB_MODEL_ID,
        }
        declared = set(MEMORY_RECORD_EMBEDDING_MODELS)
        # 單向會讓 S 多出一個沒有實作產生的值而不被發現，而那個值在資料層
        # 看起來像一個合法的向量空間。
        self.assertLessEqual(implemented, declared)
        self.assertLessEqual(declared, implemented)
        # len 斷言是突變 M9（把 STUB_MODEL_ID 改成 bge-m3）的攔截點：少了它，
        # 兩側會同時塌成兩個元素而集合相等照樣成立。
        self.assertEqual(len(declared), 3)
        self.assertEqual(len(MEMORY_RECORD_EMBEDDING_MODELS), 3)

    def test_startup_validation_rejects_missing_and_illegal_provider(self):
        """
        @purpose 驗證提供者缺值或不在允許集合內時啟動失敗，且訊息列出可選值
        @given EMBEDDING_PROVIDER 為空字串、未設定、以及一個不合法值
        @step 呼叫 resolve_provider_selection
        @pass 三者皆拋 ValueError，訊息含全部四個可選值
        @story BR1.1、BR1.6
        """
        for env in ({}, {"EMBEDDING_PROVIDER": ""}, {"EMBEDDING_PROVIDER": "chroma"}):
            with self.subTest(env=env):
                with self.assertRaises(ValueError) as caught:
                    resolve_provider_selection(env=env)
                message = str(caught.exception)
                for option in ALLOWED_PROVIDERS:
                    self.assertIn(option, message)

    def test_startup_validation_rejects_non_internal_ollama_host(self):
        """
        @purpose 驗證 OLLAMA_BASE_URL 只接受 compose 內部服務名
        @given localhost、127.0.0.1、公開網域、公開 IP、以及缺值
        @step 以 EMBEDDING_PROVIDER=ollama 呼叫 resolve_provider_selection
        @pass 每一個都拋 ValueError
        @story NFR7.1
        """
        rejected = [
            "http://localhost:11434",
            "http://127.0.0.1:11434",
            "https://ollama.example.com",
            "http://8.8.8.8:11434",
            "",
        ]
        for url in rejected:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    resolve_provider_selection(
                        env={"EMBEDDING_PROVIDER": "ollama", "OLLAMA_BASE_URL": url}
                    )
        # 服務名形式必須通過，否則這條規則擋掉了它唯一允許的形狀。
        accepted = resolve_provider_selection(
            env={
                "EMBEDDING_PROVIDER": "ollama",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            }
        )
        self.assertEqual(accepted.provider_name, PROVIDER_OLLAMA)
        self.assertTrue(accepted.port_present)

    def test_fulltext_yields_no_port(self):
        """
        @purpose 驗證 fulltext 的語意是「不建立 Port」而非一個會算向量的實作
        @given 四個合法的 EMBEDDING_PROVIDER 值
        @step 解析設定後呼叫 resolve_embedding_port
        @pass fulltext 回 None 且 model_id 為 None；其餘三者回非 None
        @story BR1.4、D-10
        """
        env = {
            "EMBEDDING_PROVIDER": PROVIDER_FULLTEXT,
            "OLLAMA_BASE_URL": "http://ollama:11434",
        }
        selection = resolve_provider_selection(env=env)
        self.assertFalse(selection.port_present)
        self.assertIsNone(selection.model_id)
        self.assertIsNone(resolve_embedding_port(selection))

        for provider in (PROVIDER_OLLAMA, PROVIDER_FASTEMBED, PROVIDER_STUB):
            with self.subTest(provider=provider):
                env2 = dict(env, EMBEDDING_PROVIDER=provider)
                picked = resolve_provider_selection(env=env2)
                self.assertTrue(picked.port_present)
                self.assertIsNotNone(resolve_embedding_port(picked))

    def test_model_id_must_be_in_the_declared_set(self):
        """
        @purpose 回歸：設定覆寫不得產生宣告集合之外的 model_id（conductor 稽核查出的 Major）
        @given OLLAMA_EMBED_MODEL / FASTEMBED_MODEL 被設為不在宣告集合內的值
        @step 呼叫 resolve_provider_selection
        @pass 拋 ValueError；訊息點名該值與宣告集合
        @story BR3.3（缺口修補）、ADR-008
        """
        # 缺陷原貌：MEMORY_RECORD_EMBEDDING_MODELS 在模組內從未被讀取，而
        # OLLAMA_EMBED_MODEL／FASTEMBED_MODEL 可被設成任意非空字串，於是記憶列
        # 會被蓋上宣告集合之外的 embeddingModel——正是 ADR-008 要防的跨向量
        # 空間污染，而且只會在 U8 寫入時才（或根本不會）被發現。
        for key, provider in (
            ("OLLAMA_EMBED_MODEL", PROVIDER_OLLAMA),
            ("FASTEMBED_MODEL", PROVIDER_FASTEMBED),
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValueError) as caught:
                    resolve_provider_selection(
                        env={
                            "EMBEDDING_PROVIDER": provider,
                            "OLLAMA_BASE_URL": "http://ollama:11434",
                            key: "bge-large-zh",
                        }
                    )
                message = str(caught.exception)
                self.assertIn("bge-large-zh", message)

        # 宣告集合內的覆寫必須仍然通過，否則這條檢查把合法設定也擋掉了。
        ok = resolve_provider_selection(
            env={
                "EMBEDDING_PROVIDER": PROVIDER_OLLAMA,
                "OLLAMA_BASE_URL": "http://ollama:11434",
                "OLLAMA_EMBED_MODEL": DEFAULT_OLLAMA_EMBED_MODEL,
            }
        )
        self.assertEqual(ok.model_id, DEFAULT_OLLAMA_EMBED_MODEL)


class FailureAndObservabilityTests(unittest.TestCase):
    """例外形狀、日誌與截斷。"""

    def test_timeout_raises_provider_unavailable(self):
        """
        @purpose 驗證連線／逾時／HTTP 錯誤都收斂為單一例外型別，且不重試
        @given 一個無法解析的 compose 服務名（CI 內不存在該服務）
        @step 呼叫 embed(["x"])
        @pass 拋 EmbeddingProviderUnavailable；available_options 為四個可選值
        @story NFR3.2、D-6、BR2.6
        """
        port = OllamaAdapter(ollama_selection("http://ollama-does-not-resolve:11434"))
        with self.assertRaises(EmbeddingProviderUnavailable) as caught:
            port.embed(["x"])
        self.assertEqual(caught.exception.available_options, tuple(ALLOWED_PROVIDERS))
        self.assertEqual(caught.exception.selected_provider, PROVIDER_OLLAMA)

    def test_exception_message_strips_userinfo(self):
        """
        @purpose 驗證例外訊息不洩漏 URL 的帳密片段
        @given OLLAMA_BASE_URL 內含 user:sup3rsecret@
        @step 觸發連線失敗後檢查例外訊息與 target 欄位
        @pass 訊息與 target 皆不含密碼字串，也不含 '@' 前的 userinfo
        @story SEC-2、D-7、BR4.4
        """
        secret = "sup3rsecret"
        port = OllamaAdapter(
            ollama_selection(f"http://probe:{secret}@ollama-does-not-resolve:11434")
        )
        with self.assertRaises(EmbeddingProviderUnavailable) as caught:
            port.embed(["x"])
        message = str(caught.exception)
        self.assertNotIn(secret, message)
        self.assertNotIn("probe:", message)
        self.assertNotIn(secret, caught.exception.target or "")

    def test_exception_constructor_strips_userinfo_from_target_and_detail(self):
        """
        @purpose 直接驗證 _without_userinfo 這個剝除點本身
        @given 一個 target 與一個 detail，兩者都內嵌含 userinfo 的 URL
        @step 直接建構 EmbeddingProviderUnavailable
        @pass target、detail 與 str(例外) 三者都不含帳密片段
        @story SEC-2、D-7（突變 M7 的真正標的）

        為什麼需要這一個：上一個測試走的是 OllamaAdapter._target()，而它用
        urlsplit().hostname 取主機名——那條路徑**自己就會**丟掉 userinfo，與
        _without_userinfo 無關。所以上一個測試在 _without_userinfo 被整個拿掉
        時仍然綠（實測：突變 M7 存活）。模組 docstring 宣稱 _without_userinfo
        是「唯一的剝除點」並不成立：實際有兩個各自獨立的剝除點，而只有這一個
        測試碰得到它。
        """
        secret = "sup3rsecret"
        exc = EmbeddingProviderUnavailable(
            PROVIDER_OLLAMA,
            target=f"http://probe:{secret}@ollama:11434",
            detail=f"連線失敗：http://probe:{secret}@ollama:11434 無回應",
        )
        self.assertNotIn(secret, exc.target or "")
        self.assertNotIn(secret, exc.detail or "")
        self.assertNotIn(secret, str(exc))
        self.assertNotIn("probe:", str(exc))
        # 主機與埠必須留著，否則訊息就失去了可除錯性。
        self.assertIn("ollama:11434", str(exc))

    def test_oversized_input_is_truncated_with_a_warning(self):
        """
        @purpose 驗證超長輸入被截斷並記 WARN，而不是拋例外
        @given 長度超過該提供者字元上限 1 個字元的輸入
        @step 呼叫 embed
        @pass 不拋例外、回正常 1024 維向量，且 WARN 內含原長度與上限
        @story D-4
        """
        limit = PROVIDER_CONTEXT_LIMIT_CHARS[PROVIDER_STUB]
        oversized = "字" * (limit + 1)
        with self.assertLogs(LOGGER_NAME, level=logging.WARNING) as captured:
            vectors = stub_port().embed([oversized])
        self.assertEqual(len(vectors), 1)
        self.assertEqual(len(vectors[0]), EMBEDDING_DIMENSIONS)
        warnings = "\n".join(
            line for line in captured.output if "WARNING" in line
        )
        self.assertIn(str(limit + 1), warnings)
        self.assertIn(str(limit), warnings)
        # 截斷後的向量必須等於「手動截斷到上限」的向量——證明截斷真的發生了，
        # 而不是 WARN 記了但原字串照送（突變 M4 的標的）。
        self.assertEqual(vectors[0], stub_port().embed([oversized[:limit]])[0])

    def test_missing_fastembed_names_the_install_command(self):
        """
        @purpose 驗證 fastembed 未安裝時的例外訊息給得出安裝指令
        @given sys.modules['fastembed'] 被設為 None，使 import 失敗
        @step 呼叫 embed(['x'])
        @pass 拋 EmbeddingProviderUnavailable，訊息含 'pip install' 與 'fastembed'
        @story BR4.3
        """
        port = FastembedAdapter(
            ProviderSelection(
                provider_name=PROVIDER_FASTEMBED,
                port_present=True,
                model_id=DEFAULT_FASTEMBED_MODEL,
                endpoint=None,
            )
        )
        with mock.patch.dict(sys.modules, {"fastembed": None}):
            with self.assertRaises(EmbeddingProviderUnavailable) as caught:
                port.embed(["x"])
        message = str(caught.exception)
        self.assertIn("pip install", message)
        self.assertIn("fastembed", message)

    def test_fastembed_is_loaded_by_its_registry_name_not_the_identity(self):
        """
        @purpose 驗證 fastembed 以套件登錄名載入模型，而不是記憶列上的身分字串
        @given 以假的 fastembed 模組取代真套件，記錄 TextEmbedding 收到的 model_name；
               設定為預設身分 multilingual-e5-large
        @step 呼叫 embed(['x'])
        @pass TextEmbedding 收到 'intfloat/multilingual-e5-large'
        @story BR6.1
        @note 回歸：fastembed 0.7 不認裸名 multilingual-e5-large，會拋 ValueError，
              使本機 fastembed 路徑從未能用。CI 不裝 fastembed，故以假模組驗證傳入的名稱；
              「真套件認得這個登錄名」只能靠 LOCAL-DEV.md 的手動前置檢查。
        """
        received = []

        class FakeTextEmbedding:
            def __init__(self, model_name):
                received.append(model_name)

            def embed(self, texts):
                return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

        fake_module = mock.MagicMock(TextEmbedding=FakeTextEmbedding)
        port = FastembedAdapter(
            ProviderSelection(
                provider_name=PROVIDER_FASTEMBED,
                port_present=True,
                model_id=DEFAULT_FASTEMBED_MODEL,
                endpoint=None,
            )
        )
        with mock.patch.dict(sys.modules, {"fastembed": fake_module}):
            port.embed(["x"])
        self.assertEqual(received, ["intfloat/multilingual-e5-large"])

    def test_fastembed_registry_names_cover_every_legal_identity(self):
        """
        @purpose 驗證每個 fastembed 合法身分都有對應的套件登錄名
        @given PROVIDER_LEGAL_MODEL_IDS 與 FASTEMBED_REGISTRY_NAMES
        @step 比對 fastembed 合法身分集合與對照表的鍵集合
        @pass 兩集合相等
        @story BR6.1
        @note 新增合法身分卻漏了對照，載入時會 KeyError 並被包成「模型載入失敗」。
        """
        self.assertEqual(
            set(FASTEMBED_REGISTRY_NAMES),
            set(PROVIDER_LEGAL_MODEL_IDS[PROVIDER_FASTEMBED]),
        )

    def test_each_embed_logs_provider_model_and_duration(self):
        """
        @purpose 驗證每次 embed 記一條 INFO，含 provider、model、批次大小與耗時毫秒
        @given 兩筆輸入的 stub Port
        @step 在 assertLogs 下呼叫 embed
        @pass INFO 含 provider 名、model_id、批次大小 2，以及一個 ms 數值
        @story D-5 第 2 條、NFR3.1
        """
        # 用可辨識的哨兵字串當輸入，才驗得出「文字本身沒有被記進日誌」。
        sentinel = "SENTINEL_MEMORY_TEXT_7f3a"
        with self.assertLogs(LOGGER_NAME, level=logging.INFO) as captured:
            stub_port().embed([sentinel, "second"])
        info = "\n".join(line for line in captured.output if "INFO" in line)
        self.assertIn(PROVIDER_STUB, info)
        self.assertIn(STUB_MODEL_ID, info)
        self.assertIn("批次大小=2", info)
        self.assertRegex(info, r"耗時=\d+\.\d+ms")
        # 不得記下待向量化的文字本身——那等於在日誌裡複製一份記憶。
        self.assertNotIn(sentinel, info)

    def test_default_timeout_is_a_named_constant(self):
        """
        @purpose 驗證逾時取自具名常數而非裸數字，且預設為 10 秒
        @given 模組載入後的常數
        @step 讀取 DEFAULT_EMBEDDING_TIMEOUT_SEC 與模組原始碼
        @pass 預設為 10.0，且 httpx.Client 的 timeout 參數不是字面數字
        @story D-6、NFR3.2
        """
        self.assertEqual(DEFAULT_EMBEDDING_TIMEOUT_SEC, 10.0)
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertRegex(source, r"httpx\.Client\(timeout=EMBEDDING_TIMEOUT_SEC\)")
        self.assertNotRegex(source, r"timeout\s*=\s*\d")


class SourceBoundaryTests(unittest.TestCase):
    """`SEC-1` 唯一能被機械驗證的方式：讀模組原始碼做字串斷言。"""

    def test_port_imports_no_db_session_no_rbac_no_router(self):
        """
        @purpose 驗證本模組不碰授權判定、不讀資料庫、不新增 HTTP 入口
        @given services/embedding_port.py 的原始碼
        @step 對六個禁用符號各掃一次
        @pass 六者命中數皆為 0
        @story SEC-1、D-9、BR2.7
        """
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden = [
            "APIRouter",
            "HTTPException",
            "get_db",
            "require_story_action",
            "sqlalchemy",
            "Session(",
        ]
        for symbol in forbidden:
            with self.subTest(symbol=symbol):
                self.assertEqual(
                    source.count(symbol),
                    0,
                    f"{symbol} 出現在 embedding_port.py，違反 SEC-1",
                )
        # 模組層不得 import 任何第三方套件：`repo-contract` job 會 import 本模組
        # 取允許值集合，而那個 job 不安裝 requirements.txt。
        module_level = re.findall(r"^(?:import|from)\s+(\w+)", source, re.MULTILINE)
        stdlib_only = {
            "__future__",
            "hashlib",
            "ipaddress",
            "logging",
            "os",
            "re",
            "time",
            "dataclasses",
            "datetime",
            "typing",
            "urllib",
        }
        self.assertLessEqual(set(module_level), stdlib_only)


class _WrongDimensionAdapter(EmbeddingPort):
    """刻意回 1023 維，用來讓 `_verify_shape` 真的開火。"""

    def _embed_batch(self, texts):
        return [[0.0] * (EMBEDDING_DIMENSIONS - 1) for _ in texts]


class _WrongCountAdapter(EmbeddingPort):
    """刻意少回一個向量，用來讓 `_verify_shape` 的筆數分支開火。"""

    def _embed_batch(self, texts):
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts][:-1]


class MitigationCoverageTests(unittest.TestCase):
    """審查（iteration 1）查出的三個「被指名為緩解措施、卻零行為覆蓋」的落點。

    共同形狀：`configure_embedding_env`（ADR-008 的大聲失敗）、`_verify_shape`
    （`OPEN-1` 的攔截點）、`_host_and_port`（`SEC-2` 在 `target` 的內層）三者
    都可以被改成 no-op 而全套測試照綠，而三者在 `traceability.json` 都標 `OK`。
    """

    # --- R-01：啟動 hook 的直接覆蓋 -------------------------------------

    def test_configure_embedding_env_rejects_missing_and_illegal_provider(self):
        """
        @purpose 驗證啟動 hook 本身會對缺值／不合法的提供者拋錯（不是靜默降級）
        @given EMBEDDING_PROVIDER 未設定、空字串、不在允許集合內三種環境
        @step 直接呼叫 configure_embedding_env()
        @pass 三者皆拋 ValueError，訊息含四個可選值
        @story BR1.6、ADR-008、NFR8.2（審查 R-01）

        為什麼需要這一個：審查把整個 configure_embedding_env() 掏空成一個
        「驗證什麼都不做、永不拋錯、靜默選 fulltext」的 no-op，全套 458 個
        測試仍然全綠（MUT-G）。那正是 ADR-008 逐字禁止的靜默降級，而
        NFR8.2 原本以「458 tests OK」當作它的驗證——兩者是不同的陳述。
        """
        for env in ({}, {"EMBEDDING_PROVIDER": ""}, {"EMBEDDING_PROVIDER": "pinecone"}):
            with self.subTest(env=env):
                with mock.patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(ValueError) as caught:
                        configure_embedding_env()
                for option in ALLOWED_PROVIDERS:
                    self.assertIn(option, str(caught.exception))

    def test_configure_embedding_env_rejects_non_internal_ollama_host(self):
        """
        @purpose 驗證啟動 hook 會擋下 compose 網路外的 ollama 主機名
        @given EMBEDDING_PROVIDER=ollama 且 OLLAMA_BASE_URL 為 localhost
        @step 直接呼叫 configure_embedding_env()
        @pass 拋 ValueError
        @story NFR7.1、BR1.3（審查 R-01）
        """
        env = {
            "EMBEDDING_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                configure_embedding_env()

    def test_configure_embedding_env_logs_provider_model_host_and_timeout(self):
        """
        @purpose 驗證啟動成功時回傳有 Port 的 selection，並記一條含四項的 INFO
        @given 合法的 ollama 設定（compose 服務名）
        @step 在 assertLogs 下呼叫 configure_embedding_env()
        @pass 回傳 port_present=True；INFO 含 provider、model、host:port 與 timeout
        @story BR7.1、NFR8.2、ADR-0006 audit logging（審查 R-01）
        """
        env = {
            "EMBEDDING_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://ollama:11434",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertLogs(LOGGER_NAME, level=logging.INFO) as captured:
                selection = configure_embedding_env()
        self.assertTrue(selection.port_present)
        self.assertEqual(selection.provider_name, PROVIDER_OLLAMA)
        self.assertEqual(selection.model_id, DEFAULT_OLLAMA_EMBED_MODEL)
        info = "\n".join(captured.output)
        self.assertIn(PROVIDER_OLLAMA, info)
        self.assertIn(DEFAULT_OLLAMA_EMBED_MODEL, info)
        self.assertIn("ollama:11434", info)
        self.assertIn(str(EMBEDDING_TIMEOUT_SEC), info)

    def test_configure_embedding_env_fulltext_logs_no_port(self):
        """
        @purpose 驗證 fulltext 分支回無 Port 的 selection 並記下「無 Port」
        @given EMBEDDING_PROVIDER=fulltext
        @step 在 assertLogs 下呼叫 configure_embedding_env()
        @pass port_present 為 False、model_id 為 None，INFO 含「無 Port」與 NULL 說明
        @story BR1.4、D-10、BR7.1（審查 R-01）
        """
        with mock.patch.dict(os.environ, {"EMBEDDING_PROVIDER": "fulltext"}, clear=True):
            with self.assertLogs(LOGGER_NAME, level=logging.INFO) as captured:
                selection = configure_embedding_env()
        self.assertFalse(selection.port_present)
        self.assertIsNone(selection.model_id)
        info = "\n".join(captured.output)
        self.assertIn("無 Port", info)
        self.assertIn("NULL", info)

    # --- R-02：`_verify_shape` 的直接覆蓋 --------------------------------

    def test_verify_shape_rejects_wrong_dimension(self):
        """
        @purpose 驗證執行期維度斷言真的會開火（不是只存在於原始碼裡）
        @given 一個刻意回 1023 維的 EmbeddingPort 子類
        @step 呼叫 embed(['x'])
        @pass 拋 EmbeddingProviderUnavailable，detail 含實際維度與契約維度
        @story BR2.2、OPEN-1 的緩解措施（審查 R-02）

        為什麼需要這一個：套件裡每一條維度斷言都跑在 StubAdapter 上，而它本來
        就回 1024，所以這個 guard 在任何測試中都不會開火——審查把兩個分支
        都改成 `if False` 仍然 19 綠（MUT-C）。OPEN-1 把「真實提供者回錯維度」
        的風險整個託付給它，而它當時沒有任何覆蓋。
        """
        port = _WrongDimensionAdapter(stub_selection())
        with self.assertRaises(EmbeddingProviderUnavailable) as caught:
            port.embed(["x"])
        detail = caught.exception.detail or ""
        self.assertIn(str(EMBEDDING_DIMENSIONS - 1), detail)
        self.assertIn(str(EMBEDDING_DIMENSIONS), detail)

    def test_verify_shape_rejects_wrong_vector_count(self):
        """
        @purpose 驗證筆數不符時也會開火
        @given 一個刻意少回一個向量的 EmbeddingPort 子類
        @step 以兩筆輸入呼叫 embed
        @pass 拋 EmbeddingProviderUnavailable，detail 同時含回傳數與輸入數
        @story BR2.1、OPEN-1 的緩解措施（審查 R-02）
        """
        port = _WrongCountAdapter(stub_selection())
        with self.assertRaises(EmbeddingProviderUnavailable) as caught:
            port.embed(["a", "b"])
        detail = caught.exception.detail or ""
        self.assertIn("1", detail)
        self.assertIn("2", detail)

    # --- R-04：`target` 路徑的內層剝除 ----------------------------------

    def test_host_and_port_strips_userinfo(self):
        """
        @purpose 直接驗證 target 路徑的**內層**剝除點
        @given 一個含 user:password@ 的 URL
        @step 呼叫 _host_and_port()
        @pass 回傳值不含密碼與 'probe:'，但保留主機與埠
        @story SEC-2、BR4.4、NFR7.3（審查 R-04）

        為什麼需要這一個：`target` 經過兩層串聯剝除（`_host_and_port` 內層、
        例外建構子的 `_without_userinfo` 外層）。審查讓內層改用 `netloc`
        保留 userinfo，19 個測試全綠（MUT-F）——外層默默補上了。縱深防禦的
        每一層都要有自己的測試，否則內層壞掉不會有任何紅燈。
        """
        secret = "sup3rsecret"
        result = _host_and_port(f"http://probe:{secret}@ollama:11434")
        self.assertNotIn(secret, result)
        self.assertNotIn("probe:", result)
        self.assertIn("ollama", result)
        self.assertIn("11434", result)

    # --- R-05：提供者↔模型對應 ------------------------------------------

    def test_real_provider_cannot_claim_the_stub_identity(self):
        """
        @purpose 回歸：真實提供者不得宣告別人的向量空間身分
        @given ollama 配 stub-v1、ollama 配 multilingual-e5-large、fastembed 配 stub-v1
        @step 呼叫 resolve_provider_selection
        @pass 三者皆拋 ValueError
        @story BR3.6、ADR-008（審查 R-05）

        為什麼集合檢查不夠：`stub-v1` 在宣告集合內，所以第一版的集合成員檢查
        放行了 ollama + stub-v1——而那會把真實的 ollama 向量蓋上 stub 的身分，
        正是 BR3.6 註解描述的「CI 寫入的列與 staging 寫入的列在資料上不可區分」。
        """
        cases = [
            ("ollama", "OLLAMA_EMBED_MODEL", "stub-v1"),
            ("ollama", "OLLAMA_EMBED_MODEL", "multilingual-e5-large"),
            ("fastembed", "FASTEMBED_MODEL", "stub-v1"),
        ]
        for provider, key, model in cases:
            with self.subTest(provider=provider, model=model):
                with self.assertRaises(ValueError) as caught:
                    resolve_provider_selection(
                        env={
                            "EMBEDDING_PROVIDER": provider,
                            "OLLAMA_BASE_URL": "http://ollama:11434",
                            key: model,
                        }
                    )
                self.assertIn(model, str(caught.exception))

    def test_provider_model_map_matches_the_declared_set(self):
        """
        @purpose 鎖住「提供者↔模型對應表」與「資料層宣告集合」兩份字面值一致
        @given PROVIDER_LEGAL_MODEL_IDS 與 MEMORY_RECORD_EMBEDDING_MODELS
        @step 取對應表所有值的聯集，與宣告集合雙向比對
        @pass 兩者相等，且各有三個元素；每個提供者恰有一個合法身分
        @story BR3.3（審查 R-05 的連帶約束）

        兩份清單刻意不共用來源（否則突變 M9 會讓兩側同時塌掉而測試恆真），
        代價是它們可以各自漂移——這個測試就是鎖住那個代價的機制。
        """
        union = set()
        for legal in PROVIDER_LEGAL_MODEL_IDS.values():
            union |= set(legal)
        declared = set(MEMORY_RECORD_EMBEDDING_MODELS)
        self.assertLessEqual(union, declared)
        self.assertLessEqual(declared, union)
        self.assertEqual(len(declared), 3)
        # 每個有 Port 的提供者恰有一個合法身分，且三者互不重疊。
        self.assertEqual(
            set(PROVIDER_LEGAL_MODEL_IDS), {PROVIDER_OLLAMA, PROVIDER_FASTEMBED, PROVIDER_STUB}
        )
        self.assertEqual(sum(len(v) for v in PROVIDER_LEGAL_MODEL_IDS.values()), 3)

    # --- R-06：逾時值的行為斷言 -----------------------------------------

    def test_timeout_from_env_handles_every_input_shape(self):
        """
        @purpose 驗證逾時解析的實際回傳值與 WARN，而非只驗原始碼文字
        @given EMBEDDING_TIMEOUT_SEC 為缺值／合法值／非數字／0／負數
        @step 呼叫 _timeout_from_env()
        @pass 缺值與合法值不記 WARN 且回正確值；三種壞值記 WARN 並回預設 10
        @story NFR3.2、D-6（審查 R-06）

        為什麼需要這一個：原本只有一個讀原始碼的正則斷言，而審查把模組層的
        EMBEDDING_TIMEOUT_SEC 直接設為 None（**無限逾時**，正是 M6 聲稱已
        駁倒的那件事），常數與 httpx 那一行都不動——19 個測試全綠（MUT-A）。
        套件保護的是「有人寫死數字」，不是「具名常數解析成無限」。
        """
        self.assertEqual(_timeout_from_env_with({}), DEFAULT_EMBEDDING_TIMEOUT_SEC)
        self.assertEqual(_timeout_from_env_with({"EMBEDDING_TIMEOUT_SEC": "2.5"}), 2.5)
        self.assertEqual(_timeout_from_env_with({"EMBEDDING_TIMEOUT_SEC": "  7 "}), 7.0)

        for bad in ("abc", "0", "-3"):
            with self.subTest(bad=bad):
                with mock.patch.dict(
                    os.environ, {"EMBEDDING_TIMEOUT_SEC": bad}, clear=True
                ):
                    with self.assertLogs(LOGGER_NAME, level=logging.WARNING) as captured:
                        value = _timeout_from_env()
                self.assertEqual(value, DEFAULT_EMBEDDING_TIMEOUT_SEC)
                self.assertIn(bad.strip(), "\n".join(captured.output))

    def test_effective_timeout_is_a_positive_finite_number(self):
        """
        @purpose 驗證模組層生效的逾時值是正的有限浮點數，不是 None／inf／0
        @given 模組載入後的 EMBEDDING_TIMEOUT_SEC
        @step 檢查型別與數值
        @pass 是 float、> 0、isfinite
        @story NFR3.2、D-6（審查 R-06，攔截 MUT-A）
        """
        self.assertIsInstance(EMBEDDING_TIMEOUT_SEC, float)
        self.assertGreater(EMBEDDING_TIMEOUT_SEC, 0)
        self.assertTrue(math.isfinite(EMBEDDING_TIMEOUT_SEC))


def _timeout_from_env_with(env: dict) -> float:
    """在指定環境下取逾時值，且斷言不產生 WARN（合法輸入不該有警告）。"""
    with mock.patch.dict(os.environ, env, clear=True):
        with mock.patch.object(logger, "warning") as warned:
            value = _timeout_from_env()
    warned.assert_not_called()
    return value


if __name__ == "__main__":
    unittest.main()
