# 階段邊界檢查：Construction → Operation

- 時間：2026-11-14T04:54:15Z（`date -u`）
- 執行者：CI Pipeline 站（精簡版）
- 依據：`.claude/aidlc-common/stages/construction/ci-pipeline.md` Step 5

## 結論：**形式上不通過**（實質缺口見下）

stage 檔的四個條件逐項判定：

| 條件 | 判定 | 依據 |
|---|---|---|
| 所有單元都已建置並測試 | **通過** | 24 個單元的 code-generation 均經重審判定 READY（2026-11-08～11-09）。後端 1480 tests OK、`tests_pg` 19 OK；PR #650 head `48f6349` 的 `ui-regression` 為 `215 passed`、`unexpected=0` |
| 各單元 code-generation 紀錄沒有未解決的發現 | **不通過** | 多個單元仍有判為 `Still applies` 的 Minor（例：entry-page-ui R-05、R-06、R-13～R-16；object-picker-ui R-10、R-11；a11y-gate Step 11 突變未在最新 spec 重跑）。全部是 Minor，沒有 Critical 或 Major，承接者見 `construction/build-and-test/test-results.md` |
| 跨單元 FR／NFR／AC 閘門通過 | **形式上不通過** | 以 build-and-test 的覆蓋腳本（`bt-gen/gate.py`）對**現況**重算：206 個 ID 中 87 個沒有直接的追溯條目，全部是需求（REQ），**106 條 AC 全數覆蓋** |
| CI 品質閘門強制 Build and Test 記錄的建置與測試指令 | **通過** | 逐項對照見 `construction/ci-pipeline/quality-gates.md` |

## 跨單元閘門的實質拆解（重算結果）

87 條沒有直接追溯條目的需求，是因為各單元的 `traceability.json` 以 AC 為單位記錄，不記 FR。經 `inception/user-stories/traceability.json` 把需求轉譯到故事、再看故事的 AC 是否覆蓋，結果如下：

- **75 條**：轉譯後對應的 AC 全數覆蓋。
- **12 條**：沒有對應的故事，分三類：
  - **`NFR1`、`NFR2`、`NFR3`、`NFR5`、`NFR6`、`NFR8`、`NFR9`、`NFR10`、`NFR11`**：由 build-and-test 的 Target Verification Matrix 承擔，而不是由故事承擔。其中延遲類（如 `NFR3` 首字回應時間）在矩陣裡是 `Unverified`：repo 沒有量測機制，也沒有後續擁有 stage。
  - **`FR9.4`**：是排除條款（「跨雲分析……本次不納入」），沒有可實作的行為。
  - **`FR12.5c`、`FR12.6b`**：說明理由與已指名後果的條款，不是可測行為。

**實質判斷**：沒有任何可測的功能需求漏做。形式上不通過的原因有兩個：

1. 追溯的粒度不一致（單元記 AC、閘門要 FR）。
2. 非功能目標缺乏量測機制。

## 依 stage 檔應有的處置

stage 檔規定：「若任一追溯檔缺失或有未解決發現，停止 Construction → Operation 的轉換，回到擁有的 stage」。本檢查**不自行放行**，交 CI Pipeline 的核可關卡由使用者決定：

- 接受上述形式缺口繼續；
- 或退回補齊：在各單元的 traceability 補 FR 粒度條目、關閉 Minor、為延遲目標建立量測機制。

## 另需揭露的範圍新增

以下三項都沒有對應的 requirements 或 stories 條目，各單元 traceability 已以 `scope` 欄標記「待回補」：

- 架構圖掛到系統（F1）
- 從對話寫入語意記憶
- 本機 Claude Code provider

回補前，這三項在任何以需求為起點的追溯裡都看不到。
