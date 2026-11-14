# 可靠性需求 — `U21 mcp-bridge`

> `NFR21` 的 parent id 理由與判準前提見 `performance-requirements.md` 檔頭。

## 〇、本單元的可靠性面

bridge 本版沒有實際 client（`OPEN-MB21-1`），對使用者不可見，故**不設可用性百分比**（理由見第五節）。可靠性需求只管兩條：
**bridge 不得因 backend 的故障而退出或失控**（可恢復錯誤），以及**設定錯誤時不得帶病上線**（致命錯誤）——兩者刻意相反
（`BR71.4` 與 `BR71.5`，`construction.md` 的 recoverable vs fatal）。另有一條交付面的可靠性：**必測清單必須真的在 CI 裡跑**
（帶入項 `R-11`）。

## 一、backend 不可用

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.25`** | （`BR71.4`；MB-W6）啟動不依賴 backend；backend 不可達時只讓該次工具呼叫失敗，進程不退出 | **真實 TCP**：bridge 的 `--backend-url` 指向已關閉的本機埠後啟動：`/healthz` 回 200、`tools/list` 成功、`tools/call` 回 `backend_unavailable` 且 `retryable` 為真；連續 5 次 `tools/call` 後 `/healthz` 仍回 200（進程存活）。隨後在該埠起一個回 200 的替身 backend，下一次 `tools/call` 成功（無需重啟 bridge） |
| **`NFR21.26`** | （帶入項 `R-20` 第 1 點；`BR76.1`）傳輸層失敗由**執行層**歸類為封閉枚舉 `TransportFailure`（至少 `refused`、`timeout`、`dns`、`protocol`），`map_outcome` 只接收此枚舉或 HTTP 狀態碼；純函式模組不 import `httpx` | ① `map_outcome` 的 example 測試：枚舉每一值 → `backend_unavailable`、`retryable` 為真；backend 500／502／503／504 → 同上。② 執行層的歸類測試：`httpx.ConnectError`、`httpx.ConnectTimeout`、`httpx.ReadTimeout`、`httpx.RemoteProtocolError` 與整體逾時各對應一個枚舉值（DNS 失敗以 `--backend-url http://does-not-exist.invalid` 觸發）；未列舉的 `httpx` 例外 → `internal_error`。③ grep `outcomes.py`：`import httpx` 為 0 |
| **`NFR21.27`** | （`BR75.1`；D-12）每次工具呼叫**恰好**對 backend 發一次請求，含 5xx、逾時與連線中斷——不重試 | 記錄包裝分別回 503、延遲至逾時、中途斷線三案：每案記錄筆數恰為 1，工具結果為 `backend_unavailable`、`retryable` 為真 |

## 二、請求間的隔離與例外

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.28`** | （`BR73.3`）middleware 在**任何**結束路徑（含例外）於 `finally` 重設 contextvar：前一次請求的 token 不得殘留到下一次 | 使用者 A 的工具呼叫中令記錄包裝拋例外（結果為 `internal_error`）；緊接著同一個連線池發一次**不帶** `Authorization` 的工具呼叫 → 結果為 `unauthenticated`、記錄包裝 0 筆（若殘留 A 的 token，會以 A 的身分送出）。突變驗證：移除 `finally` 的重設 → 紅燈 |
| **`NFR21.29`** | （`BR76.1`、`BR76.3`）工具處理函式內的未預期例外 → `internal_error`（固定訊息、不含例外文字），進程不退出、後續呼叫不受影響 | 以替身令 `build_backend_call` 拋 `RuntimeError("SECRET-MARKER")`：結果為 `internal_error`，結果與 log 皆不含 `SECRET-MARKER`（log 只記例外型別名，`BR77.2`）；下一次正常呼叫成功 |

## 三、交付面：必測清單必須在 CI 實際執行（帶入項 `R-11`）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.30`** | 不論 `functional-spec.md` §十二 第 1 步選定哪條依賴路線，`T-1`、`T-2`、`T-4`、`T-8`（`NFR21.7`、`NFR21.8`、`NFR21.9`、`NFR21.6`）與 `NFR21.25`、`NFR21.1` 必須在 CI 的 `backend` job 內**實際執行**，不得以缺少 `mcp` 為由 skip。走第一順位（`mcp` 進 `backend/requirements.txt`）時自然成立；走第二退路（獨立 virtualenv）時，`ci.yml` 的 `backend` job 必須另建同一份 `requirements-mcp.txt` 的環境並以其直譯器執行這些測試——這是交給 `infrastructure-design`／`code-generation` 的 CI 交接項，與 `BR78.2` 的子進程拓樸一併在計畫核可時呈現 | CI `backend` job 的 `unittest -v` 輸出中，上列測試的名稱全部以 `ok` 結尾、`skipped` 計數中不含它們；且 `backend/tests/` 內對 `mcp` 的匯入失敗不得以 `skipTest`／`skipUnless` 包住（grep `skipUnless` 與 `skipTest` 在本單元測試檔內不得以 `mcp` 為條件） |
| **`NFR21.31`** | （`BR72.9`；`functional-spec.md` §八 H-4）漂移閘門：`gen_mcp_tools.py --check` 在 CI 的 `backend` job 執行，緊鄰 `dump_openapi.py --check`；`openapi.json` 或 `allowlist.json` 改了而產物未重產即紅燈 | `ci.yml` 的 `backend` job 含該步驟（grep）；突變驗證（`code-generation` 本機執行並記錄）：手改 `generated_tools.json` 的一個描述字串 → `--check` 退出碼非 0；還原 → 0 |

## 四、部署形狀（交接，落點 `infrastructure-design` → `code-generation`）

| id | 需求 | 二元判準 |
|---|---|---|
| **`NFR21.32`** | （`functional-spec.md` §八 H-1–H-3、H-7）compose 服務 `mcp-bridge`：`restart: unless-stopped`；healthcheck **覆寫**映像內建的 `HEALTHCHECK`（該 HEALTHCHECK 探 8000，`backend/Dockerfile:27-28`，不覆寫則容器恆為 unhealthy），改探 `http://127.0.0.1:8080/healthz`；有記憶體上限（數值由 `infrastructure-design` 定，`DEPLOY.md` 標記「未量測」）；`depends_on: [backend]` 不帶 `condition`；`logging` 沿用有界的 `json_file_bounded`；網路與埠見 `NFR21.16` | 以 YAML 解析 `deploy/docker-compose.deploy.yml` 的 `mcp-bridge` 服務，斷言：`restart` 為 `unless-stopped`；`healthcheck.test` 含 `8080/healthz`；記憶體上限欄位存在；`depends_on` 含 `backend`；`ports` 不存在；`networks` 恰為 `[internal]`。部署後實測：`docker inspect` 的健康狀態為 `healthy` |

## 五、刻意不設的目標

| 不設 | 理由 |
|---|---|
| 可用性 SLO 百分比 | 本版無實際 client，對使用者不可見；百分比沒有量測母體。以 `NFR21.25`（backend 故障不使 bridge 退出）與 `NFR21.32`（自動重啟、healthcheck 正確）兩條二元需求代替。大腦 client 落地時（`OPEN-MB21-1`）再定 |
| 重試與熔斷 | `BR75.1`／D-12：重試交給 agent（`retryable`），bridge 只轉發一次；bridge 無狀態，熔斷需要跨請求狀態 |
| 備份與還原 | bridge 不持久化任何資料；三份設定檔進版控 |
| 優雅關閉的排空時限 | 每次工具呼叫 ≤ 10 秒（`NFR21.1`），uvicorn 的預設關閉行為足以；compose 的 `stop_grace_period` 預設 10 秒，與上限同量級，不另設 |
