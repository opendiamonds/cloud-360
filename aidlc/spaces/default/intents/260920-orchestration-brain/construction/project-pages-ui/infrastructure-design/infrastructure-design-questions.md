# Infrastructure Design 問題檔 — `U23 project-pages-ui`

> 撰寫時間 2026-10-15T23:44:13Z（`date -u` 取值）。
>
> **本站問 0 題，而這是判定而不是省略。** 依既有慣例（`tcms-test-cases:c1`：判定為 0 時仍須逐項列出標的與理由），
> 本檔逐項記下 stage 檔六個 focus area 的判定與查證依據，以及**考慮過但刻意不出成題目**的候選。
>
> 單元類型 **`ui`**（但本單元依 `[PP1]`=A 含後端改動）；`produces_kinds` 使四份產出全數適用。

## 〇、上游已定案、本站不重問

| 事項 | 定案 | 出處 |
|---|---|---|
| 索引寫進 `schema_rbac.sql` ＋ 遷移腳本（含 `EXPECTED_INDEXES`）＋ `DEPLOY.md` 部署後重跑步驟；**不動啟動路徑** | 使用者 2026-10-15T23:20:19Z 裁決 | `../carried-review-items.md` nfr-requirements `R-02` |
| 建索引本身 | `[PPN1]`=A | `../nfr-requirements/nfr-requirements-questions.md` |
| 成功刪除加記刪除者 | `[PPD1]`=A | `../nfr-design/nfr-design-questions.md` |
| 被拒寫入不記 log | nfr-requirements 定案 | `../nfr-requirements/security-requirements.md` §五 |
| 連線池不改 | nfr-requirements `R-05` 的 Required action「數值不必改」；`performance-design.md` §三 | — |

## 一、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據 |
|---|---|---|
| 部署策略 | **無標的** | 既有 compose 7 個服務不變（`deploy/docker-compose.deploy.yml` 服務鍵 `:35`／`:79`／`:184`／`:312`／`:353`／`:375`／`:400`） |
| 運算／儲存／網路 | **一個索引；其餘無標的** | `frontend/nginx.conf:16-17` 的 `/api/` 與 `:35-37` 的 SPA fallback 已涵蓋新端點與新路由；索引的三種到達路徑見 `infrastructure-specification.md` §二之一 |
| 監控 | **無可交付** | 無告警通道（`OPEN-N10-4`）；`[PPD1]`=A 的 log 落在既有 stdout。見 `monitoring-design.md` |
| CI/CD | **管線定義零改動**；部署後一個人工步驟 | 漂移閘門、unittest、`ui-regression` 皆自動撿到本單元產物（`cicd-pipeline.md` §一）；人工步驟由使用者裁決定案（`cicd-pipeline.md` §二） |
| Secrets 管理 | **無標的** | 零新環境變數、零新 secret（`infrastructure-specification.md` §一） |
| 擴縮政策 | **無標的** | 單一 uvicorn 進程與預設連線池不變；已知代價在 `performance-design.md` §三 |

## 二、考慮過、刻意不出成題目的候選（附理由）

| # | 候選 | 不出題的理由 |
|---|---|---|
| 1 | 讓 `deploy.yml` 自動跑遷移腳本，免去人工步驟 | 使用者已裁決「沿用 `U18` 路徑」；`DEPLOY.md` 2.2.9 的「誠實的代價」段已把「`deploy.yml` 不呼叫任何遷移腳本」記為既有、全 intent 共用的取捨。改它影響 `U5`／`U18`／`U20` 的遷移與 `NFR8.4`，超出本單元範圍；出題等於重開已裁決事項 |
| 2 | 改用 `CREATE INDEX CONCURRENTLY` | 與遷移腳本的「單一交易」形狀不相容，等於另開一條遷移路徑，牴觸裁決；表規模小，收益為零。單一可行解，不出假選擇（`requirements-analysis:260822-ra-c5`） |
| 3 | 為「staging 是否已有索引」加自動檢查 | 由事件觸發的檢查若以 repo 內 script 承載，牴觸 `project.md ## Forbidden` 的無人值守自動化條款；以 workflow 承載則需連 staging DB，屬新機制、超出本單元。現況以人工驗證 ＋ `tcms-test-cases` 手動桶承接 |
| 4 | 在部署冒煙加打一支 `/api/hierarchy/*` | 需帶身分 token 的冒煙是 `deploy.yml` 層的新設計，影響全部單元；記為已知事實（`monitoring-design.md` §五），不在本單元開題 |
| 5 | `EXPECTED_INDEXES` 漏列無閘門（`cicd-pipeline.md` §四 第 7 列）的補強 | 補強是一個 `assertIn`，無取捨、無替代方案；本站直接設計（`cicd-pipeline.md` §四之一）並於核可關卡揭露，code-generation 可記明拒絕理由 |

本站的實質工作因此是**把上游裁決落到三種資料庫狀態與部署順序上**，並誠實記下哪幾條失敗路徑沒有閘門。
