# U1 `u1-iac-api` 程式碼摘要

本單元在既有 FastAPI 行程加上 `/api/iac`。產物只留在記憶體，沒有新資料表，也沒有改 `role_permissions` 種子。U2 的 React 工作區沒有做。

## 測試

在 `backend/` 執行：

`python -m unittest tests.test_iac_generator tests.test_iac_scanner tests.test_iac_redactor tests.test_iac_session tests.test_iac_http -v`

本機系統 Python 沒有 `langgraph`，實際用 `backend/.venv/bin/python` 跑同一道指令。最後一輪：

```
Ran 44 tests in 0.392s

OK
```

失敗 0。44 則含三個核心的 Hypothesis、session 的 16 MiB 與第三個 in-flight、以及 TestClient 的 US6.1 成對 403／200。沒有把斷言改成恆真，也沒有把門檻數字寫小。

## 遮罩突變

突變點是 `backend/iac/iac_redact.py` 的 `mask_secret_value`。暫時改成 `return plaintext` 後，`test_plaintext_absent_from_output_log_and_zip` 與 Hypothesis `test_random_token_is_absent` 變紅：

```
AssertionError: 'cloud360-fixture-plaintext-9f3a' unexpectedly found in 'password = cloud360-fixture-plaintext-9f3a\n'
AssertionError: 'pw-000000' unexpectedly found in 'password = pw-000000\n'
FAILED (failures=2)
```

已還原為 `return SECRET_MANAGER_REFERENCE`。還原後 `tests.test_iac_redactor` 為 `Ran 8 tests in 0.061s` / `OK`，全套 44 則也是 `OK`。未遮罩的版本沒有留在工作樹。

## 契約與 Checkov

`openapi.json` 已用 `backend/scripts/dump_openapi.py` 重產，`--check` 通過。`frontend/src/types/api.d.ts` 跟著重產，否則前端 CI 的 `check:types` 會紅；這不是 U2 畫面。Checkov 釘在 `backend/requirements.txt` 的 `checkov==3.4.3`。既有 `backend/Dockerfile` 仍用同一份 requirements 安裝，沒有新的掃描映像、compose 服務或 CI scan job。三環境的 `.env` 契約沒有改。

## 覆蓋率與量不到的 NFR

`org.md` 的 80% 行覆蓋率維持 80，沒有下修，也沒有把 `fail_under` 設成 0。這個 repo 沒有 coverage 設定、沒有 CI coverage 步驟，**80% 目前無法機械強制**。

下列數字保持原值，本單元沒有做負載量測：

- `POST /generate` 的 p95＜60 秒沒有壓測。硬逾時是 90 秒；逾時不寫入半成品，並保留同一張圖上一份成功草稿。`future.result` 逾時後，執行緒裡的模型呼叫無法硬殺，可能續跑到模型自己逾時，但結果不會寫進槽。
- `/session`、`/scan`、`/secrets/rewrite` 的 p95＜2 秒沒有壓測。這三條沒有 2 秒硬殺。Checkov 子行程硬逾時是 10 秒，因此 D2 的牆鐘時間可以超過 2 秒；那是可靠性上限，不是把 p95 改成 10 秒。
- `/download` 的 p95＜5 秒沒有壓測。zip 在記憶體組裝。

## 主要決定

- 閘錯誤是 `{"error":{"code","message"}}`。缺 `diagram_id` 是 422 `missing_diagram_id`，不是 FastAPI 的 `detail` 清單，也不是 404。
- 權限不足維持既有 `require_story_action` 的 403。種子已有 D1／D2／D3，本輪沒有改矩陣。
- 進程內同時 generate 最多 2；第 3 個是 `generate_busy`，HTTP 對應 429。同一槽的第二個寫入也是 `generate_busy`，不排隊。這兩層用不同使用者的測試分開驗證。
- 換圖會清掉上一張圖的草稿與報告，舊 `report_id` 回 `stale_report_id`。同一使用者最多留 3 個槽鍵，第 4 個清掉最久未用的鍵。
- Checkov exit 1 且 JSON 可解析是「有 finding 的成功」；缺 CLI、逾時、未知嚴重度是失敗，不是空的成功報告。零 finding 且成功時 `max_severity` 為 `NONE`。
- 下載不看 `HIGH`／`CRITICAL`。
- D1／D2／D3 的 agent 都走 `langgraph_runtime` 的 `default_invoke`；測試注入 `agent_invoke`。沒有 Claude SDK 專用路徑，沒有 apply、destroy 或雲端 Secret Manager 寫入。
- log 名稱是 `cloud360.iac`。欄位白名單不含 HCL 全文、prompt 或 JWT。

## 留給 U2 的驗收

畫面文案、進行中狀態、剪貼簿、HIGH／CRITICAL 下載確認 modal、入口 disabled，都還在 U2。API 在這些情況下仍回 zip 或閘錯誤碼，不代替那個 modal。
