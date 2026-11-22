# CI Pipeline — 問題檔

> 本站以「精簡版」執行（2026-11-14 使用者選定「照跑精簡版」）：CI 已存在且於 PR #650 head `48f6349` 全綠，本站**不改 CI**，只記錄現有閘門、本次實跑證據與階段邊界檢查。
> stage 檔列的四題皆為 repo 與規則層**已定案的事實**，依 `project.md` 「上游已定案事項不重問」的規則，不向使用者重問；每題附可引用的來源，答案即該來源的現況。

## 已由 repo／規則層定案、不重問

### Q1 — 使用哪一套 CI 工具？

- A. GitHub Actions（含 gh-aw agentic workflow）
- B. AWS CodePipeline／CodeBuild
- C. Jenkins
- D. 其他

[Answer]: A <!-- 來源：`.github/workflows/ci.yml`、`deploy.yml` 與 `*.lock.yml`（gh-aw 編譯產物）；`project.md` `## Tech Stack`「CI/CD：GitHub Actions」 -->

### Q2 — 分支策略為何？

- A. 以 `ut` 為整合主幹的 trunk-based，短命分支合入 `ut`，`main` 只收 `ut` 的合併
- B. GitFlow
- C. 直接合入 `main`
- D. 其他

[Answer]: A <!-- 來源：`org.md` `## Way of Working`；分支命名 `<uploader>/<type>/<slug>` 見 `team.md`。一般 PR 走 merge commit（`team.md` Q2 定案） -->

### Q3 — 合併前需要哪些品質閘門？

- A. 沿用現有：repo／環境契約、前端 lint＋型別＋build＋契約漂移、後端 import＋三種契約漂移＋unittest、記憶 schema 斷言、真實 PostgreSQL 併發測試、Docker build，加上 PR 上的 gh-aw 檢查（`ui-regression` 為真閘門）
- B. 新增覆蓋率門檻
- C. 新增效能基準
- D. 其他

[Answer]: A <!-- 來源：`ci.yml` 九個 job（見 `ci-config.md`）；`team.md` `## Testing Posture` 記載 `ui-regression` 以 `stats.unexpected` 為閘門。B／C 皆無現成量測機制（`team.md`：「完全沒有覆蓋率量測機制」；build-and-test 矩陣的 14 個延遲目標「無後續擁有 stage」），不在本站以精簡版新增 -->

### Q4 — 使用哪些產物庫？

- A. 不使用產物庫：CI 的 `docker-build` 只建不推（`push: false`），部署在自架 runner 上以 `docker compose up -d --build` 就地建置
- B. ECR／GHCR
- C. S3／CodeArtifact
- D. 其他

[Answer]: A <!-- 來源：`ci.yml` `docker-build` job；`deploy.yml` 「Build and start the stack」步驟 -->
