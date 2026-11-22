# Unit Test Instructions — U3: u3-design-agent-compound

> Stage: code-generation (3.5) · Phase: Construction · Scope: feature · Depth: Standard
> Unit: `u3-design-agent-compound` (kind: `service`)

---

## 1. 測試框架與環境設置 (Test Framework & Environment Setup)

- **框架**: Python 3.11 `unittest`
- **測試檔案路徑**: `backend/tests/test_design_agent.py` 與 `backend/tests/test_diagram_builder_compound.py`
- **執行環境**: 本專案虛擬環境 (`.venv/bin/python3`)

---

## 2. 單元執行指令 (Unit-Scoped Test Command)

在執行任何測試前，確保執行以下專屬此單元的精確指令：

```bash
PYTHONPATH=backend .venv/bin/python3 -m unittest backend/tests/test_design_agent.py
```

---

## 3. 測試範圍與覆蓋率目標 (Coverage Targets & Test Cases)

- **覆蓋率門檻**: 行覆蓋率 $\ge 80\%$。
- **核心測試案例清單 (5-8 tests)**:
  1. `test_system_prompt_includes_compound_hybrid_cloud`: 驗證載入的提示詞中包含「混合雲」或「compound」之 Hub-and-Spoke 空間幾何指示。
  2. `test_draw_architecture_diagram_accepts_compound_provider`: 驗證工具介面接受 `provider="compound"` 並正確轉發至繪圖邏輯。
  3. `test_draw_architecture_diagram_rbac_guard`: 驗證在缺少編輯權限時阻擋繪圖並提示防護訊息。
  4. 既有 Prompt 格式化與 XML 草稿拼接等 5 個單元測試持續綠燈。

---

## 4. 測試資料與 Mock 指引 (Mocking Guidance)

- 使用 `tests.helpers` 中的 LangGraph/LangChain mock stub 避免外部網路連線或未安裝套件之影響。

