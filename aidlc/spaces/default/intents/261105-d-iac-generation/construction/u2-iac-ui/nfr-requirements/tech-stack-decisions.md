# Tech Stack Decisions — u2-iac-ui

> Unit: `u2-iac-ui`（ui）· Q4=A／Q5=A。

## 選定

| 層 | 選擇 | 理由 |
|---|---|---|
| UI | React＋Vite＋Tailwind；既有 Workspace 路由／語彙 | FD Q1；codekb |
| 測試 | Playwright e2e＋既有 test-id | NFR5.4；CI ui-regression |
| 平行開發 | MSW／stub 回契約形狀 | FD Q4=A |
| 可觀測 | UI 狀態＋`error.code`；無強制 RUM SDK | Q5=A |

## 明確不選

| 候選 | 原因 |
|---|---|
| 新 UI component library | Q4≠B |
| 前端 metrics／RUM 必做 | Q5≠B |
| 獨立 `/iac` 頂層路由 | FD Q1≠B |

## 與 U1 邊界

- 不實作 Checkov／PBT／session store。
- 延遲上限以 U1 NFR 為準；本檔只定 UI 等待與 Abort 策略。

<!-- confirmed: Looks correct -->
