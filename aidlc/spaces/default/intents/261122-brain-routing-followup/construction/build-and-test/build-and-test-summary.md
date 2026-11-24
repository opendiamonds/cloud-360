# Build and Test Summary

## 整體 build 狀態與前置條件

- **Build：成功。** import smoke、OpenAPI 漂移、WS 契約漂移、repo contract、env contract 五項全過（`test-results.md`）。
- 前置條件：Python 3 加上 `backend/requirements.txt`。不需資料庫、Redis 或網路。
- 變更面只在後端路由與工作編排兩組模組，不碰前端、契約、schema 或環境變數。

## 測試類型盤點

| 類型 | 是否產生 | 說明 |
|---|---|---|
| 單元測試（含 Hypothesis 性質測試） | 是，由 code-generation 產生 | 範圍指令 124 個，全綠 |
| 後端全套回歸 | 是 | 1631 個，0 失敗、3 略過 |
| 整合測試 | 否 | Minimal 策略；跨模組行為已由端對端形狀的單元測試涵蓋（`integration-test-instructions.md`） |
| 效能測試 | 否 | 沒有效能目標（`performance-test-instructions.md`） |
| 資安測試 | 否 | ADR-0006 四面向逐項落點見 `security-test-instructions.md` |
| staging 真實路由量測（NFR1） | 待部署後 | 本機無法執行 |

## 各單元的覆蓋預期

本 intent 沒有 per-unit 拆分（bugfix scope，stage 層 code-generation）。覆蓋預期依 Testing Contract 的 bugfix 底線來看：每個缺陷各有針對性回歸測試，既有套件維持綠燈，agent routing 須有性質測試。不設行覆蓋率門檻。

## Target Verification Matrix

目標來源：code-generation-plan.md 的 Testing Contract。本 intent 沒有 nfr-requirements／nfr-design 產出。

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| TC-REG | Testing Contract > obligations.scope_floor[0] | 每個缺陷各有針對性回歸測試 | 兩個缺陷各有回歸測試，皆通過，突變 M6、M8 紅燈 | `test-results.md` | build-and-test | Met |
| TC-GREEN | Testing Contract > obligations.scope_floor[1] | 既有後端套件全綠 | 1631 個，0 失敗、3 略過 | `test-results.md` | build-and-test | Met |
| TC-REQ | Testing Contract > obligations.strategy_volume[0] | 每項需求至少一個可驗證測試 | FR／NFR 均有測試或檔案核對 | `cross-unit-traceability.md` | build-and-test | Met |
| TC-COMP | Testing Contract > obligations.strategy_volume[1] | 每個被改元件至少一個 happy-path 測試 | 六個被改模組均有 | `test-results.md` | build-and-test | Met |
| TC-PBT | Testing Contract > applicable_notes[project]（ADR-0006） | agent routing 有 property-based 測試 | `BuildStatePropertyTest` 通過，突變 M1、M4、M5 紅燈 | `test-results.md` | build-and-test | Met |

## 就緒評估

- **Build-ready**：是。
- **Test-ready**：是。範圍測試與全套都綠，突變驗證 11 項全部紅燈後還原。
- **Deployment-ready**：可進入部署流程。但 NFR1（staging 真實路由量測）要部署後才能驗；量不過就要回頭調整延續規則的文字（requirements NFR1：不得以調低門檻代替）。

## 已知限制與未結項

1. **NFR1 未驗**：見 `cross-unit-traceability.md`。ADR-0025 維持 Proposed，直到量測通過。
2. **已接受風險**（不在本 stage 處置）：
   - requirements 審查 R-01：提示訊息是最後一則系統訊息，NFR1 量測時以真實歷程形狀驗證。
   - requirements 審查 R-02：平台竄改預檢的固定拒絕語會被當成「在等你回覆」，沒有測試覆蓋。
   - code-generation 審查 R-01～R-04（Minor）：分別是「等你回覆」靠 `dispatchStage` 推論、一段註解錯位、歷程換行可偽造發言行、性質測試的使用者句子未達 4000 字截斷。
3. 下一站 `tcms-test-cases` 為 blocking，須完成覆蓋盤點、手動測案、自動化腳本規格註解與 TCMS 同步。
