# Monitoring Design — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: infrastructure-design（Construction 3.4）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 本單元沒有執行期可監控的東西

`U17` 不在任何使用者請求路徑上，也不部署。依 `produces_kinds`，`nfr-design` 的 `observability-design` 不適用於 `packaging`，本檔沒有上游的 observability 策略可落實。它唯一的「訊號」是 CI 上的閘門結果，以下只寫這一件。

## Metrics & KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| `a11y.spec.ts` 的失敗數 | `frontend/pw-report.json` 的 `stats.unexpected`（`ui-regression.md` post-steps 讀取） | 非 0 即擋 PR | 這就是閘門本身 |
| `a11y.spec.ts` 的 flaky 數 | 同上的 `stats.flaky` | 不擋，但非 0 時須看 | `retries: 1` 會讓偶發失敗變綠；掃描點若經常 flaky，就緒層可能沒等到真正就緒 |
| 基準清單筆數 | `a11y-baseline.json` 的條目數 | 只准減少（審查把關，`A11Y-S9` 規則 3） | 筆數上升是「把新違規藏進清單」的唯一可見訊號 |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| PR 紅燈 | `stats.unexpected` 非 0 | 擋合併 | PR 作者（`ui-regression` 的 agent 在 PR 留言列出失敗案例） |

沒有其他告警。本單元不設排程掃描、不設 staging 掃描。

## SLIs / SLOs

不適用：沒有服務、沒有使用者請求。

## Logs & Tracing

- **報告內容**：每個掃描點以 `testInfo.attach` 附上 axe 的 `violations` 與 `incomplete`（`A11Y-S8`）。Playwright 的 `json` reporter 會把附件寫進 `pw-report.json`，`ui-regression` 的 agent 讀它來寫 PR 留言。
- **保存期限——已知缺口，如實記載**：實讀 `ui-regression.md`，該工作流程**沒有** `upload-artifact` 步驟；`pw-report.json` 與附件只活在 runner 上，job 結束即消失。能留下來的只有兩樣：agent 的 PR 留言（摘要，不含完整 axe 結果），以及送進 Kiwi TCMS 的 junit 結果（只有通過／失敗，沒有違規內容）。所以 `security-requirements.md` 的 Audit logging 變形（「證據若只是綠燈而無內容就無從複查」）在**綠燈時**沒有任何留存，在**紅燈時**只留摘要。
- **處置**：本單元不改 `ui-regression`（`infrastructure-specification.md`「不改 `ui-regression`」判定）。補上 artifact 上傳會改到一個 gh-aw 工作流程並需重新編譯 `.lock.yml`，且本 repo 為 public、artifact 公開可下載——附件內容雖已限定為不含憑證（`A11Y-S6`），仍是一個新的公開資料面。交 `build-and-test` 判定是否需要；若需要，以獨立變更處理。

## Dashboards

無。TCMS 的趨勢頁已按 `<describe> › <test>` 逐案呈現通過與失敗歷史，本單元的 21 個 `test()` 會自動出現在那裡（`test-case-authoring.md` §4.4）。
