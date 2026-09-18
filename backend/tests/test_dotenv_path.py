"""main.py 必須只讀 backend/.env，不得沿著 cwd 往上找到別的 .env。

這個 bug 的形狀：`load_dotenv(override=True)` 不給路徑時會呼叫 find_dotenv()，
從 cwd 一路往上找。從 backend/ 以外的目錄啟動 uvicorn 時，它會安靜地載入樹上
任何一份 .env——實際發生過一次，摸到了使用者家目錄的 .env，於是 backend/.env
明明寫著 LLM_PROVIDER=cli，API 卻回報「尚未設定 OPENROUTER_API_KEY」。

失敗是安靜的：載到的不是「沒有設定」而是「別人的設定」，錯誤離肇因三層遠。
所以這裡用子行程實測 import 後的環境，而不是斷言原始碼長什麼樣子。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

PROBE = "CLOUD360_DOTENV_PROBE"

_IMPORT_MAIN = textwrap.dedent(
    """
    import json, os, sys
    sys.path.insert(0, os.environ["CLOUD360_BACKEND_DIR"])
    import main
    print(json.dumps({
        "backend_dir": str(main.BACKEND_DIR),
        "probe": os.environ.get("CLOUD360_DOTENV_PROBE"),
    }))
    """
)


class DotenvPathTests(unittest.TestCase):
    def _import_main_from(self, cwd: Path) -> dict:
        env = dict(os.environ)
        env["CLOUD360_BACKEND_DIR"] = str(BACKEND_DIR)
        env.pop(PROBE, None)
        result = subprocess.run(
            [sys.executable, "-c", _IMPORT_MAIN],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0, f"import main 失敗：\n{result.stderr}"
        )
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_does_not_load_a_dotenv_from_an_ancestor_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(f"{PROBE}=decoy\n", encoding="utf-8")
            workdir = root / "nested" / "deeper"
            workdir.mkdir(parents=True)

            # 守衛：先證明「沒釘路徑的話真的會撿到這份誘餌」，否則這個測試是空的。
            from dotenv import find_dotenv

            found = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from dotenv import find_dotenv; print(find_dotenv(usecwd=True))",
                ],
                cwd=str(workdir),
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                Path(found.stdout.strip()).resolve(),
                (root / ".env").resolve(),
                "誘餌沒有被 find_dotenv 撿到，這個測試證明不了任何事",
            )
            del find_dotenv

            payload = self._import_main_from(workdir)
            self.assertIsNone(
                payload["probe"],
                "main.py 從祖先目錄載入了不相干的 .env",
            )

    def test_backend_dir_points_at_the_backend_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._import_main_from(Path(tmp))
        self.assertEqual(
            Path(payload["backend_dir"]).resolve(),
            BACKEND_DIR.resolve(),
            "BACKEND_DIR 沒有指向 backend/，.env 的查找基準就會跟著漂",
        )


if __name__ == "__main__":
    unittest.main()
