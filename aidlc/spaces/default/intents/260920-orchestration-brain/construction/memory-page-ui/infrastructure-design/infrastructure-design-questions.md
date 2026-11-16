# Infrastructure Design 問題檔 — `U15 memory-page-ui`

> **本站問 0 題，而這是判定而不是省略**（`tcms-test-cases:c1`：判定為 0 時仍須
> 逐項列出標的與理由）。
>
> 單元類型 **`ui`**，`produces_kinds` 使四份產出全數適用。
>
> **stage condition 逐字**：「Infrastructure services need mapping, deployment
> architecture required, or cloud resources needed. Skip if no infrastructure changes
> and infrastructure already defined.」本單元三個子句皆不成立（下表），故依
> 2026-10-06 核可的精簡做法跑 by-reference：per-unit skip 不可行（8 站清單 24 單元
> 共用），故產出精簡文件、**不派審查員**，`produces` 仍全部落在磁碟以滿足
> `unit complete`。先例 `U24 member-pages-ui` 同形。此決定於核可關卡一併揭露。

## 一、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據（本站重新實測） |
|---|---|---|
| 部署策略 | **無標的** | 零新服務、零新進程；`deploy/docker-compose.deploy.yml` 的服務集合不變 |
| 運算／儲存／網路 | **無標的** | 只消費 `U8` 既有的 `GET`／`DELETE /api/memory/records`；`frontend/nginx.conf:16-17` 的 `location /api/ { proxy_pass http://backend:8000;` 已涵蓋 |
| 監控 | **無可交付** | 本 intent 無 dashboard 或告警通道；本單元唯一訊號是 `SEC-U15-5` 的 console 輸出（見 `monitoring-design.md`） |
| CI/CD | **前端零變更；後端一處連帶變更** | `.github/workflows/ui-regression.lock.yml:558` 為裸 `npx playwright test`、`frontend/playwright.config.ts:10` 為 `testDir: './tests/e2e'`，新 spec 丟進該目錄即被撿到。連帶變更見 `cicd-pipeline.md §三` |
| Secrets | **無標的** | 零新環境變數（`NFR8.90`） |
| 擴縮 | **無標的** | 前端為靜態資產；筆數上限屬前端設計（`UIP-2`、`UIP-5`） |

## 二、為什麼不出題

六項的預設都是**實測現況**而非選擇，出題會是單一可行解的假選擇
（`requirements-analysis:260822-ra-c5`）。唯一非零的項目——後端「已核准」檢查
連帶影響 OpenAPI 漂移閘門——的處置方向已由使用者裁決（帶進 code-generation），
本站只把它的管線後果寫清楚。
