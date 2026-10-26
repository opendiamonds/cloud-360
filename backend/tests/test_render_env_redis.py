"""`deploy/render-env.sh` 對 `REDIS_PASSWORD` 與六個字面值的行為（U1 `brain-infra`）。

受測對象是 **repo 根目錄下的 shell 腳本**，不是 backend 模組。它被放在
`backend/tests/` 的理由與 `test_repo_contract_production_paths.py` 相同：那是 CI 唯一
會 discover 的 Python 測試路徑（`ci.yml` 以 `working-directory: backend` 執行
`python -m unittest discover -s tests`）。放在 `deploy/tests/` 會滿足「有測試」而永遠
不在 PR 上跑——而那正是本檔要防的失敗形狀之一。

**以真實 `bash` 子行程執行，不 mock shell。** 這支腳本的價值就在它的實際退出行為；
mock 掉等於什麼都沒測。

三個被測的失敗模式，兩個是無聲的：

1. **空的 `REDIS_PASSWORD`**（案例 1）——它不會自己壞掉，只會渲染出一個密碼為空的
   ACL 使用者。而 rollback job **沒有**等價於 deploy job「Require the secrets that
   must not default」的守門步驟，所以這支腳本的必填檢查是那條路徑上唯一的守門。
2. **含 `$` 的 `REDIS_PASSWORD`**（案例 2，`project.md ## Forbidden` 的硬規則）——
   docker compose 會對 `--env-file` 的值做內插，`ab$cd` 被**無聲截斷**成 `ab`：
   Redis 照樣接受、`redis-cli ping` 照樣回 PONG、healthcheck 照樣過，session store
   以兩個字元的密碼運行且沒有任何錯誤訊息。
3. **六個非機敏變數被做成 `env:` 傳入**（案例 4，審查 R-40）——它們沒有對應的
   repository secret，會解析成**空字串**寫進 `deploy/.env`，而 `EMBEDDING_PROVIDER`
   依契約 `K-01` 是 required、無預設、偵測不到提供者時須大聲失敗 → backend 啟動失敗
   → deploy 紅燈 → 觸發自動 rollback ＋ revert PR。所以「它們是字面值」不是風格
   選擇，是一條要被鎖住的判準。

測試一律使用明顯的假值（`test-only-value`）。本 repo 為 public，任何真實憑證都不得
出現在測試檔裡。含 `$` 的那一例用 `ab$cd` 這個最小重現字串（即 `render-env.sh` 自己
註解裡的那個例子）。

受測對象既無 HTTP 端點也無 UI route，故本檔不掛 `@api`／`@ui`。
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERER = REPO_ROOT / "deploy" / "render-env.sh"

# 本單元新增的七個變數。前六個是字面值，只有 REDIS_PASSWORD 走環境。
LITERAL_VARIABLES = (
    "REDIS_URL",
    "REDIS_USER",
    "EMBEDDING_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_EMBED_MODEL",
    "FASTEMBED_MODEL",
)
SECRET_VARIABLE = "REDIS_PASSWORD"
NEW_VARIABLES = LITERAL_VARIABLES + (SECRET_VARIABLE,)

# 明顯的假值。絕不使用任何像真實憑證的字串。
FAKE_POSTGRES_PASSWORD = "test-only-value-postgres"
FAKE_JWT_SECRET = "test-only-value-jwt"
FAKE_REDIS_PASSWORD = "test-only-value-redis"
DOLLAR_REDIS_PASSWORD = "ab$cd"  # render-env.sh 註解裡的最小重現字串


def _run_renderer(env_overrides: dict[str, str | None]) -> tuple[int, str, str, str]:
    """在暫存目錄渲染，回傳 (returncode, stdout, stderr, 產生的檔案內容)。

    `HOME` 一併指向暫存目錄：heredoc 的 `CLOUDFLARED_CREDENTIALS_FILE` 會內插它，
    所以不覆寫會讓輸出夾帶開發者的家目錄路徑。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "rendered.env"

        env = dict(os.environ)
        # 先清掉本測試會判定的每一個名字，避免開發者 shell 裡剛好有同名變數讓
        # 「缺值」案例空洞通過。
        for name in (
            "POSTGRES_PASSWORD",
            "JWT_SECRET",
            "REDIS_PASSWORD",
            "CLOUD360_BOOTSTRAP_ADMIN_PASSWORD",
            "OPENROUTER_API_KEY",
            "N8N_WEBHOOK_URL",
            "N8N_USER",
            "N8N_PASSWORD",
            "APP_ENV",
            *NEW_VARIABLES,
        ):
            env.pop(name, None)
        env["HOME"] = tmpdir

        for name, value in env_overrides.items():
            if value is None:
                env.pop(name, None)
            else:
                env[name] = value

        result = subprocess.run(
            ["bash", str(RENDERER), str(out)],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
        )
        rendered = out.read_text(encoding="utf-8") if out.exists() else ""
        return result.returncode, result.stdout, result.stderr, rendered


def _happy_env(**overrides: str) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "POSTGRES_PASSWORD": FAKE_POSTGRES_PASSWORD,
        "JWT_SECRET": FAKE_JWT_SECRET,
        "REDIS_PASSWORD": FAKE_REDIS_PASSWORD,
    }
    base.update(overrides)
    return base


def _assignments(rendered: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in rendered.splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name, _, value = line.partition("=")
            values[name.strip()] = value
    return values


class RenderEnvRedisPasswordTest(unittest.TestCase):
    def test_empty_redis_password_exits_non_zero(self):
        """案例 1：空的 `REDIS_PASSWORD` → 非零退出（清單第 4a 項的可測判準）。"""
        code, _, stderr, rendered = _run_renderer(_happy_env(REDIS_PASSWORD=""))
        self.assertNotEqual(code, 0, "空的 REDIS_PASSWORD 必須讓 render-env.sh 失敗")
        self.assertIn("REDIS_PASSWORD", stderr)
        self.assertEqual(
            rendered, "", "拒絕的情況下不得產生（或留下）一份殘缺的 deploy/.env"
        )

    def test_unset_redis_password_exits_non_zero(self):
        """案例 1b：完全沒設也算缺值。

        `${REDIS_PASSWORD:-}` 與 `${REDIS_PASSWORD}` 在 `set -u` 下的行為不同，
        而必填檢查寫成前者；「空字串」與「未設定」兩種缺法都必須被同一條檢查擋下。
        """
        code, _, stderr, rendered = _run_renderer(_happy_env(REDIS_PASSWORD=None))
        self.assertNotEqual(code, 0)
        self.assertIn("REDIS_PASSWORD", stderr)
        self.assertEqual(rendered, "")

    def test_dollar_sign_in_redis_password_exits_non_zero(self):
        """案例 2：含 `$` 的 `REDIS_PASSWORD` → 非零退出。

        `project.md ## Forbidden` 的硬規則。這個失敗模式是**無聲的**：不擋下來的話
        Redis 會以 `ab` 運行，而每一道既有檢查都會綠燈。
        """
        code, _, stderr, rendered = _run_renderer(
            _happy_env(REDIS_PASSWORD=DOLLAR_REDIS_PASSWORD)
        )
        self.assertNotEqual(code, 0, "含 $ 的 REDIS_PASSWORD 必須被拒絕而不是被截斷")
        self.assertIn("REDIS_PASSWORD", stderr)
        self.assertEqual(rendered, "")

    def test_redis_password_value_is_written_verbatim(self):
        """案例 5：`REDIS_PASSWORD` 的值逐字等於傳入值，未被截斷或改寫。"""
        code, _, stderr, rendered = _run_renderer(_happy_env())
        self.assertEqual(code, 0, f"正常值應渲染成功：{stderr}")
        values = _assignments(rendered)
        self.assertEqual(values.get(SECRET_VARIABLE), FAKE_REDIS_PASSWORD)


class RenderEnvNewVariablesTest(unittest.TestCase):
    def test_all_seven_new_variables_are_written(self):
        """案例 3：正常值 → 零退出，且七個新變數名都出現在產生的檔裡。"""
        code, _, stderr, rendered = _run_renderer(_happy_env())
        self.assertEqual(code, 0, f"render-env.sh 應成功：{stderr}")
        values = _assignments(rendered)
        missing = [name for name in NEW_VARIABLES if name not in values]
        self.assertEqual(
            missing,
            [],
            f"deploy/.env 缺少 {missing}；deploy compose 讀它們時無 `:-` fallback，"
            "缺一個就是一個空字串進到容器裡",
        )

    def test_the_six_literals_are_non_empty_literal_values(self):
        """案例 4（核心，審查 R-40）：六個非機敏變數是**字面值**而非空字串。

        把它們做成 `deploy.yml` 的 `env:` 傳入是最自然的誤解，而那會讓每一個都
        解析成空字串。這個案例鎖住的是：即使**完全不提供**這六個名字的環境變數，
        渲染出來的值也必須是非空的字面值。
        """
        overrides = _happy_env()
        for name in LITERAL_VARIABLES:
            overrides[name] = None  # 刻意不提供
        code, _, stderr, rendered = _run_renderer(overrides)
        self.assertEqual(code, 0, f"render-env.sh 應成功：{stderr}")

        values = _assignments(rendered)
        empty = [name for name in LITERAL_VARIABLES if not values.get(name, "")]
        self.assertEqual(
            empty,
            [],
            f"{empty} 渲染成空字串。它們必須是 heredoc 內的字面值——"
            "EMBEDDING_PROVIDER 依契約 K-01 為 required、無預設，空值會讓 backend "
            "啟動失敗 → deploy 紅燈 → 自動 rollback ＋ revert PR",
        )

    def test_environment_cannot_override_the_six_literals(self):
        """案例 4b：字面值就是字面值——外部環境設了同名變數也不得改變輸出。

        沒有這一條，案例 4 可以在「它們其實是 `${NAME:-default}`」的實作下通過，
        而那種實作會在 deploy.yml 真的傳入空字串時退回空值——正是要防的那件事。
        """
        overrides = _happy_env()
        for name in LITERAL_VARIABLES:
            overrides[name] = ""  # 明確傳入空字串
        code, _, stderr, rendered = _run_renderer(overrides)
        self.assertEqual(code, 0, f"render-env.sh 應成功：{stderr}")

        values = _assignments(rendered)
        empty = [name for name in LITERAL_VARIABLES if not values.get(name, "")]
        self.assertEqual(
            empty,
            [],
            f"{empty} 被外部空字串蓋掉了。它們不得帶 `${{NAME:-...}}` 形式，"
            "否則 deploy.yml 傳入一個不存在的 secret 就會讓它們變空",
        )

    def test_redis_url_and_ollama_base_url_use_compose_service_names(self):
        """案例 4c：兩個 URL 的主機名必須是 compose 內部服務名。

        契約 `K-01` 對 `REDIS_URL` 逐字要求「主機名須為 compose 內部服務名，
        不得為 `localhost`」；`NFR8.8` 對 Ollama 同理。寫成 `localhost` 在部署
        stack 裡指向 backend 容器自己，連不上但錯誤訊息不會說出原因。
        """
        code, _, stderr, rendered = _run_renderer(_happy_env())
        self.assertEqual(code, 0, stderr)
        values = _assignments(rendered)

        self.assertTrue(
            values["REDIS_URL"].startswith("redis://"),
            f"REDIS_URL 必須以 redis:// 開頭，實際為 {values['REDIS_URL']!r}",
        )
        for name in ("REDIS_URL", "OLLAMA_BASE_URL"):
            for marker in ("localhost", "127.0.0.1"):
                self.assertNotIn(
                    marker,
                    values[name],
                    f"{name} 不得指向 {marker}（部署 stack 內那是容器自己）",
                )

    def test_redis_user_is_not_the_default_redis_account(self):
        """案例 4d：`REDIS_USER` 不得為 `default`（`NFR4.1(b)`／`(c)`）。

        以 `default` 連線取得的是 full command access（含 `FLUSHALL`／`CONFIG`／
        `KEYS`），那是最小權限的反面。契約的驗證規則逐字是「值不得為 `default`」。
        """
        code, _, stderr, rendered = _run_renderer(_happy_env())
        self.assertEqual(code, 0, stderr)
        values = _assignments(rendered)
        self.assertNotEqual(values["REDIS_USER"].strip(), "default")
        self.assertTrue(values["REDIS_USER"].strip())


if __name__ == "__main__":
    unittest.main()
