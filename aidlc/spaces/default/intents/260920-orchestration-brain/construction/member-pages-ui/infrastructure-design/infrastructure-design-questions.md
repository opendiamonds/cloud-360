# Infrastructure Design 問題檔 — `U24 member-pages-ui`

> **本站問 0 題，而這是判定而不是省略。** 依既有慣例（`tcms-test-cases:c1`：
> 判定為 0 時仍須逐項列出標的與分桶理由，空檔或一句「無」會被下一個人讀成漏寫），
> 本檔逐項記下 stage 檔六個 focus area 的判定與其查證依據。
>
> 單元類型 **`ui`**，`produces_kinds` 使四份產出全數適用
> （`infrastructure-specification` / `monitoring-design` / `cicd-pipeline` 皆含 `ui`）。
>
> **本站不派審查員**，依 2026-10-06 核可的做法：per-unit skip 不可行
> （8 站清單 24 單元共用），故不適用的 design 階段改跑精簡 by-reference ＋
> 不派 reviewer，而 `produces` 仍須全部落在磁碟才能 `unit complete`。
> 此決定於核可關卡一併揭露，不夾帶。

## 一、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據（可複驗的指令或行號） |
|---|---|---|
| 部署策略（容器／serverless／多區） | **無標的** | 本單元零新服務、零新進程。既有拓樸不動：`deploy/docker-compose.deploy.yml` 的服務集合不變 |
| 運算／儲存／網路（sizing、拓樸、延遲） | **無標的** | 零新端點；六個消費點全屬 `U19` 既有端點。反向代理已涵蓋：`frontend/nginx.conf:16` 為 `location /api/ { proxy_pass http://backend:8000; }` |
| 監控（metrics／log／trace／告警門檻） | **無可交付** | 本 intent 無任何 dashboard 或告警通道（`U10` 的 `OPEN-N10-4`）。本單元唯一的訊號是 `SEC-U24-6` 的 console 輸出，其消費者是開發者 devtools 與 e2e 斷言。詳見 `monitoring-design.md` |
| CI/CD（建置階段、部署策略、回滾） | **無變更** | `ui-regression.lock.yml:558` 跑裸 `npx playwright test`，`frontend/playwright.config.ts:10` 的 `testDir: './tests/e2e'`——新 spec 檔丟進該目錄即被撿到，管線零改動 |
| Secrets 管理（vault／環境變數／輪替） | **無標的** | 本單元**零新環境變數**（`TS-U24-7`／`NFR8.80`），故 `render-env.sh` ＋ `deploy/.env.example` 的同步義務為空集合；`docker-compose.test.yml` 亦無需改動（其 `backend.environment` 全部自帶預設） |
| 擴縮政策（觸發條件、容量上限、成本） | **無標的** | 前端為靜態資產，由既有 nginx 容器提供；本單元不新增任何可擴縮單元。唯一與容量有關的決定是 `UIP-1` 的 100 列**渲染**上限，屬前端設計而非基礎設施 |

## 二、為什麼不出題（而不是出一題形式題）

出題的門檻是「預設錯了會造成真實重工」。上表六項的預設都不是「我選的」，
而是**實測的現況**：三項查證（CI 不用改、nginx 不用加規則、test stack 不用改）
各自有一條可複驗的指令，三者皆為 0 改動。在這種情形下出題會是
`requirements-analysis:260822-ra-c5` 記過的形狀——**單一可行解的假選擇**，
讓紀錄看起來像有人選過而實際沒有。

本站的實質工作因此不是「設計」而是**把那三項查證寫成下游可複驗的形式**，
並誠實記載監控面的空缺。
