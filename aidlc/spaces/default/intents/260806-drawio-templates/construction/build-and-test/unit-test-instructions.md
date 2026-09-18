# Unit Test Instructions

## Test Framework Setup
- 本專案採用 `unittest` 與 `pytest` 來執行後端測試。

## How to Run Tests
- 在後端目錄下執行單元測試：
  ```bash
  pytest backend/tests/test_diagram_builder.py
  ```

## Expected Coverage Targets
- 單元測試需完全覆蓋 `diagram_builder` 針對各雲端（AWS, GCP, Azure）產圖 XML 合成邏輯。
- 此次變更已同步至系統提示詞中，本機單元測試應維持 100% 通過。
