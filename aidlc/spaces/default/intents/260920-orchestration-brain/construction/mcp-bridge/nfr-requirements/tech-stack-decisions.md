# 技術選型 — `U21 mcp-bridge`

> `NFR21` 的 parent id 理由見 `performance-requirements.md` 檔頭。

## 〇、選型（皆已由上游或 functional-design 定案，本站不重選）

| 層 | 選擇 | 依據 |
|---|---|---|
| 語言與執行環境 | Python 3.12，沿用 backend 映像（`python:3.12-slim`，`backend/Dockerfile:5`）；compose 第七服務，以不同啟動指令執行 | `[MB5]`=A；`BR71.1`；codekb `technology-stack.md:14` |
| MCP 伺服器 | 官方 Python `mcp` SDK，streamable HTTP、無狀態模式，掛為 ASGI 應用 | `[MB5]`=A；`BR71.2`；D-8 |
| ASGI server | uvicorn（`backend/requirements.txt:10`，既有），由 `__main__` 以程式方式啟動（`limit_concurrency` 見 `NFR21.21`、`access_log=False` 見 `NFR21.36`） | 既有依賴 |
| 對 backend 的 HTTP client | `httpx.AsyncClient`（`backend/requirements.txt:11`，既有）；`follow_redirects=False`、不設預設 `Authorization`、整體逾時另以 `asyncio` 包住 | `BR73.2`、`BR73.3`；`NFR21.1` |
| 產生器 | 純函式 `generate_tools`，外層腳本 `backend/scripts/gen_mcp_tools.py` | `[I7]`=A；`BR72.1`、`BR72.9` |
| 測試 | `unittest` ＋ `hypothesis`（`backend/requirements.txt:30`，既有）；驗證拓樸為真實 uvicorn ＋ `httpx.ASGITransport` 直達真實 FastAPI app；**非 pytest** | `team.md ## Testing Posture`；`BR78.1`–`BR78.3` |
| 依賴路線 | 依 `functional-spec.md` §十二 第 1 步（`:335` 起）的退路順序：第一順位 `mcp==<版本>` 進 `backend/requirements.txt` → 相容的較舊版本 → 獨立 virtualenv（`backend/requirements-mcp.txt`）→ 升 FastAPI 須另開題 | `[MB5]`=A；H-5；`OPEN-MB21-15` |

## 一、決定

| id | 決定 | 二元判準 |
|---|---|---|
| **`NFR21.37`** | （`OPEN-MB21-15`；H-5）`mcp` 以 `==` 精確釘選（比照 `fastapi`／`pydantic` 的紀律，`backend/requirements.txt:1-9`）；選定的版本、其 Starlette／anyio 範圍與 `fastapi==0.111.0` 解析結果的比對、以及所選路線，寫進 `code-generation` 的計畫並於計畫核可時呈現；**不得**以升級 FastAPI 解決相容問題，除非另開題經使用者裁決 | `git diff` 下 `backend/requirements.txt`（或 `requirements-mcp.txt`）的 `mcp` 行為 `mcp==<x.y.z>` 形式；`fastapi==0.111.0` 與 `pydantic==2.13.4` 兩行未變；`openapi.json` 的 diff 為空（`dump_openapi.py --check` 在 CI 通過） |
| **`NFR21.38`** | 本單元新增的**直接依賴**只有 `mcp` 一個；不新增 `pytest`、JWT 函式庫、限流套件或其他 HTTP client | `git diff` 下依賴檔新增的非註解行恰為 1（`mcp==…`）；`frontend/package.json` 無變更 |
| **`NFR21.39`** | （**ADR-0006 PBT hard constraint**；`functional-spec.md` §六、`T-3`；帶入項 `R-14`）產生器的 property-based 測試：§六 的八個類別、七條性質，策略由 openapi **衍生**一致的 allowlist 再施加單一破壞；**閘門必須決定性**——成功分支的覆蓋不得以「隨機抽類別後的次數比例」為判準（`R-14` 算出約 2% 的純統計誤判）。可接受的形式擇一並在 code-summary 寫明：(a) 每個類別各自一個 `@given` 測試；(b) 以固定輪替取代隨機抽類別；(c) `derandomize=True` 且下限定在期望值的一半以下並註明計數是否含縮減與重放。§六 突變表七列為必做 | ① 八個類別各至少一個測試在 CI 執行且全綠；② 以同一 commit 連續執行兩次，閘門結果相同（`code-generation` 本機實證並記錄，選 (a)／(b) 時由結構保證）；③ 突變表七列逐列套用後對應性質紅燈、還原後全綠，結果寫進 `automation-test-plan`。**定位**：`project.md` 點名的三個 hard-constraint 落點不含本單元，但 `brain-infra` 的 `S-15` 已把產生器判為 PBT 標的，`functional-spec.md` §六 判為**必須**，本站沿用，不以 N/A 處理 |
| **`NFR21.40`** | （`BR72.1`、`BR75.4` 的純函式邊界；帶入項 `R-11` 第 2 點）純函式模組 `generator.py`、`calls.py`、`outcomes.py`、`credentials.py`、`agents.py` 不得 import `mcp`、`httpx`、`sqlalchemy`（含任何 DB session 型別）、`fastapi`（含 `HTTPException`）——使它們在任何依賴路線下都能在主直譯器跑 PBT 與 `--check` | 五個檔各自 grep `^\s*(import|from)\s+(mcp|httpx|sqlalchemy|fastapi)\b`：結果皆 0 |
| **`NFR21.41`** | 第一順位路線下**不改 `backend/Dockerfile`**（compose 以 `command` 覆寫啟動指令、以 healthcheck 覆寫探測，`NFR21.32`）；走第二退路時 Dockerfile 的改動限於建立獨立 virtualenv，且 compose 的 `command` 改用該 venv 的直譯器——兩者皆為交給 `infrastructure-design`／`code-generation` 的交接項，於計畫核可時呈現 | 第一順位：`git diff backend/Dockerfile` 為空。第二退路：Dockerfile 的 diff 只含 venv 建立與 `requirements-mcp.txt` 的安裝；backend 的 `CMD`（`Dockerfile:30`）未變 |

## 二、刻意不採用

| 不採用 | 理由 |
|---|---|
| Node／TypeScript SDK | `[MB5]`=A 未採選項 B |
| 舊 HTTP＋SSE 雙端點傳輸 | D-8：需長駐連線與伺服器端 session，與逐請求身分相反 |
| 執行期向 backend 取 `openapi.json` | `BR71.4`：啟動不依賴 backend；產物進版控 |
| JWT 函式庫（解碼取使用者 id） | `BR73.5`；`[MBN1]`=A 未採選項 C |
| `pytest`、`pytest-asyncio` | `team.md`：backend 測試為 `unittest`；`unittest.IsolatedAsyncioTestCase` 已足 |
| 升級 FastAPI 以配合 `mcp` | 連動 `openapi.json` 重 dump 與前端型別重產（`backend/requirements.txt:1-7`），代價與一個尚無 client 的 bridge 不成比例；只作最後手段且須另開題 |
