# Unit Test Instructions — U1: u1-icon-service-gateway

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u1-icon-service-gateway` (kind: `library`)

---

## 1. 測試框架與環境設置 (Test Framework & Environment Setup)

- **框架**: Python 3.11 `pytest` / `unittest` 與 `unittest.mock`
- **測試檔案路徑**: `backend/tests/test_diagram_builder_compound.py`
- **依賴套件**: 已存在於專案環境（`pytest`, `pytest-asyncio`, `httpx`），無新增依賴。

---

## 2. 單元執行指令 (Unit-Scoped Test Command)

在執行任何測試前，確保執行以下專屬此單元的精確指令：

```bash
pytest backend/tests/test_diagram_builder_compound.py -k "test_fetch_icon or test_fallback" -v
```

或全套複合測試：

```bash
pytest backend/tests/test_diagram_builder_compound.py -v
```

---

## 3. 測試範圍與覆蓋率目標 (Coverage Targets & Test Cases)

- **覆蓋率門檻**: 行覆蓋率 $\ge 80\%$。
- **核心測試案例清單 (5-8 tests)**:
  1. `test_fetch_icon_compound_payload_success`: 驗證呼叫 `fetch_icon_from_n8n("ec2", provider="compound")` 時，向 n8n 發送之 JSON 確為 `{"service": "ec2", "provider": "compound"}` 且正確解析回傳的 SVG。
  2. `test_fetch_icon_compound_timeout_fallback`: 模擬 n8n 延遲超過 5.0 秒，驗證在 5.0 秒內安全中斷並觸發 Fallback，回傳 40x40 灰底文字 SVG，不拋出 TimeoutException。
  3. `test_fetch_icon_compound_http_error_fallback`: 模擬 n8n 回應 HTTP 404/500，驗證捕獲異常並回傳 40x40 灰底文字 SVG。
  4. `test_fallback_svg_content_format`: 驗證 Fallback SVG 規範（`viewBox="0 0 40 40"`, `#F1F5F9`, 截取前 4 碼英數字大寫）。
  5. `test_fetch_icon_caching`: 驗證同一個服務名稱重複查詢時命中記憶體快取，不發起第二次 HTTP 呼叫。

---

## 4. 測試資料與 Mock 指引 (Mocking & Test Data Guidance)

- 使用 `unittest.mock.patch("httpx.AsyncClient.post")` 進行網路隔離，確保測試離線且執行時間 $< 1.0$ 秒。
- 模擬回傳格式範例：
  - 成功: `httpx.Response(200, text='<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><circle cx="20" cy="20" r="15"/></svg>')`
  - 逾時: `httpx.TimeoutException("ReadTimeout")`
  - 伺服器錯誤: `httpx.Response(500, text='Internal Server Error')`

