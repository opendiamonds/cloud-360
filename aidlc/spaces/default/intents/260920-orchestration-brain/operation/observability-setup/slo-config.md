# SLO／SLI 設定

> 決定來源：[Q6]=B——照上游的兩個 SLO，另加一個使用者感受的可用性 SLO。
> `phases/operation.md` 要求 SLO 以百分比與時間窗量化、且告警門檻低於 SLO 違反點；下表逐列對照。

| ID | SLI | 目標 | 時間窗 | 量測方式 | 告警門檻（低於違反點） | 來源 |
|---|---|---|---|---|---|---|
| S1 | 大腦對話輪次「非錯誤結束」比率 = 1 − `outcome=error:*` ÷ 全部 `turn_end` | **≥ 99%** | 7 天滾動 | `brain-health-watch.yml` 的 `scan` job 每小時以 `docker logs --since 168h` 計算；樣本 < 50 輪不判 | 1 小時內錯誤率 > 5% 且 ≥ 2 次（`TURN_ERRORS`）；7 天跌破 99%（`SLO_7D_BREACH`） | 本站新增（[Q6]=B） |
| S2 | 路由層 `classify` 耗時 P50 | **≤ 800 ms** | 線上滾動 | `intent routing turn=… elapsed_ms=` 欄位；以 `log-queries.md` Q4 人工計算 | 無自動告警（見下方說明） | `intent-router` monitoring-design §三（`NFR3.60`） |
| S3 | 意圖識別準確率 | **≥ 80%** | 每次模型或 prompt 變更後 | ≥ 50 筆人工標註集，離線重跑 | 不適用（離線） | `intent-router` monitoring-design §三（`NFR1`，初版無實證值） |

**分類成功率不設 SLO**（照上游）：失敗多在供應商側，設一個我們控制不了的 SLO 沒有意義；但它的使用者後果已由 S1 涵蓋——路由失敗會讓該輪以錯誤結束。

## 說明

- **S1 的 `ended_silent`、`clarify`、`guard` 都算非錯誤**：反問與攔截是設計內的回覆，不是服務失敗。
- **S1 的資料保留上限**：容器日誌為 `json-file` 50 MB × 5 份輪替（`deploy/docker-compose.deploy.yml:69-75`）。若 7 天內日誌量超過 250 MB，最舊的部分會被輪替掉，S1 實際上變成「保留範圍內」的可用性；issue 與 step summary 會列出實際樣本數，可據此判斷。
- **S2 不自動告警**：`elapsed_ms` 的分位數在 shell 裡算得出來，但 P50 的意義需要足夠樣本，staging 每小時的輪次很少，自動判定會頻繁誤報。改為每週以 Q4 人工檢視；`performance-validation` 站會給出基準量測。
- **S3 由 Jev 1.14 切換觸發重測**（ADR-0024 已登記為待辦）：首次實測未達標時依 `requirements.md` 的校正程序，由決策者裁決，不得自動改寫門檻。

## 上游涵蓋

本表承接 `construction/*/nfr-design/performance-design.md` 與 `reliability-design.md` 的延遲與可用性設計、`construction/intent-router/infrastructure-design/monitoring-design.md` §三，以及 `construction/brain-infra/infrastructure-design/infrastructure-specification.md` 的日誌上限；安全面（日誌白名單、不印內容）承接 `construction/*/nfr-design/security-design.md`。
