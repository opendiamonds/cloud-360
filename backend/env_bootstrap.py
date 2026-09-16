"""backend/.env 的單一載入點。

`load_dotenv()` 不給路徑時會呼叫 find_dotenv()，從 **當前工作目錄** 一路往上
找第一份 .env。從 backend/ 以外的目錄啟動 uvicorn 時，它會安靜地載入樹上任何
一份不相干的 .env——實際發生過一次，摸到了使用者家目錄的 .env，於是
backend/.env 明明寫著 LLM_PROVIDER=cli，API 卻回報「尚未設定
OPENROUTER_API_KEY」。

失敗是安靜的：載到的不是「沒有設定」而是「別人的設定」，錯誤離肇因三層遠。

這個模組存在的理由是**只有一個地方決定路徑**。原本 main.py 與 database.py 各
自呼叫 load_dotenv()，修好其中一個不會讓另一個變安全——database.py 是被 main
在第 13 行匯入的，比 main 自己那行更早跑，所以只修 main 完全無效。
回歸測試 tests/test_dotenv_path.py 守著這件事。

檔案不存在不是錯誤：部署的容器直接注入環境變數，根本沒有 backend/.env。
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
DOTENV_PATH = BACKEND_DIR / ".env"


def load_backend_dotenv(*, override: bool = False) -> bool:
    """載入 backend/.env。回傳是否真的讀到檔案。

    override 預設 False，與 python-dotenv 一致：已存在的環境變數優先，讓
    shell 與容器注入的值蓋過檔案。應用程式入口 (main.py) 會用 override=True，
    因為本機開發時 .env 才是唯一事實來源。
    """
    return load_dotenv(DOTENV_PATH, override=override)
