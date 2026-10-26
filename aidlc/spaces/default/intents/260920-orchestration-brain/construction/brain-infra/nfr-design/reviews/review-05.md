## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

brain-infra 的 nfr-design（kind: packaging，僅 security-design.md 與 traceability.json）設計本身自洽：ADR-0006 四面向逐項有判定，D-1 至 D-4 與 PROBE-CONTRACT（P-1 至 P-7）可實作，traceability 20/20 全覆蓋，舊審查 review-01 至 review-04 的發現多已處置。本次補審實查已落地程式後，發現兩項會讓下游讀者誤判的設計與程式落差：(1) 大量行號與一處「逐字」引用已因後續合併過期；(2) 設計把網段模型凍結為 edge／internal 兩個、六個服務、且「一律不得 internal: true」，但已落地的 deploy compose 已有第七個服務 mcp-bridge 與第三個 `internal: true` 的 mcp 網段，設計沒有前向指標。兩項皆不改變 D-1 至 D-4 的安全結論，已落地程式一側是對的。Major 共 2 項，未超過 2，故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/nfr-design/security-design.md > D-2「現況基線」、D-3 探測契約 P-2／P-7、重試窗口表、rollback 專節 | 前次 review-04 已提的 R-29，現況仍在凍結產出裡。實查：(a) D-2 逐字引用 `deploy/docker-compose.deploy.yml:36` 的 `DATABASE_URL: postgresql://...`，現況為 `:85` 且驅動為 `postgresql+psycopg://`，逐字引用不再成立。(b) P-2 與步驟 1、2 引用 `user_router.py:386`、`:389`、`:387-388`，現況 `db.query(User)` 在 `:403`、不存在即 raise 在 `:404-405`、`verify_password` 在 `:406`（login 函式 `:397`）；行為仍成立（先查 DB、不存在即 401）。(c) deploy.yml 的 `:169-175`（rollback 觸發）、`:177`（timeout 20）、`:229-236`（健康檢查迴圈）、`:381-386`（notify 的 case）現況分別約為 `:653`、`:657`、`:700-775` 區間、遠後方；`:10-14`、`:27`、`:28` 仍準確。(d) 「`:63-65` depends_on service_healthy」現況在 `:148-166`。這些引用指向無關內容，照行號去讀的實作者或下一站審查者會讀到別處。行為主張大多仍正確，故不升 Critical。 | 在 nfr-design 目錄新增 corrections 檔（或在 stage 日記記錄），列出本檔每個 `<file>:<n>` 的現況行號與驅動變更（postgresql+psycopg），並註明「行為主張未變、僅定位漂移」。不回改已凍結的 security-design.md。 | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/nfr-design/security-design.md > D-3「服務歸屬」兩張表、「不得設 internal: true」、「所以兩份 compose 的 networks: 宣告一律不帶 internal: true」、blast radius 表 | 設計與已落地的 deploy compose 矛盾，且程式一側是對的。設計定案：deploy 為「六個服務」、網段僅 edge／internal、`backend` 是「唯一的橋」、「一律不帶 internal: true」。落地後 `deploy/docker-compose.deploy.yml` 有 `mcp-bridge`（`:400`）、第三個網段 `mcp`（`:472-473`，刻意 `internal: true`，註解 `:431-433`、`:450-453` 說明理由：bridge 不需要外連）、`backend` 掛 `[edge, internal, mcp]`（`:172`）。這不削弱 D-3（`mcp-bridge` 不在 internal、不在 edge，blast radius 表的 internal 成員計數 3 與 5→3 仍成立），且 internal: true 的風險（斷出向）對只掛 mcp 的 bridge 不成立，設計的規則是針對 ollama 寫的、被寫成了無條件。但設計未留任何前向指標，「一律」一詞已與程式矛盾。上游 unit-of-work 修訂 4 已把「是否為 U21 新增第七個 compose 服務」指派給 infrastructure-design，前次 review-04 的 R-30 同樣指出本檔沒有指向該決策的句子。 | 在 corrections 檔寫明：(1) deploy compose 現為七個服務、三個網段，`mcp` 為刻意 `internal: true` 的例外，規則收窄為「internal: true 不得用於需要出向的服務所在網段」；(2) blast radius 表需補 `mcp-bridge` 一列（可達 backend:8000，且被 backend 呼叫 8080），並判定對 Redis／Ollama 可達者仍為 3；(3) 以 compose 為準，不以本檔的「一律」為準。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/nfr-design/security-design.md > D-3 失敗分類表、「init_db() 的最壞時間評估」 | 502 診斷與時間評估建立在舊 `init_db()` 形狀：設計稱「六個 `_ensure_*_schema`」且 `create_all` 為第一步。現況 `backend/database.py` 的 `init_db()`（`:85` 起）先呼叫 `_ensure_vector_extension()`（註解標明必須早於 create_all），之後 `_ensure_*` 補丁至少為 `a4/j5/a3/cost/estimate_intake/last_activity` 等，數量已超過六。診斷結論（db 不可達 → startup 失敗 → 持續 502）仍成立，30×5s 窗口是否仍足夠未重評（設計稱由 local-dev-drift 提醒、非阻擋）。 | 在 corrections 檔記錄 init_db 現況，並註明窗口重評結果（或指派實測於 code-generation 後的部署）。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/nfr-design/security-design.md > §二「IAM 的誠實現況」、「Audit 的缺口與承接單元」 | 兩個 ADR-0006 缺口只有「承接單元」而沒有已確認的承接：(a) PostgreSQL 單一 superuser 縮窄，Assumptions 明寫「尚未有任何單元正式承接」；(b) correlation ID 指派給 U13／U12 的 nfr-design，而該站為 CONDITIONAL，設計已誠實標出 skip 風險並要求 skip 時重交使用者。兩者作為設計是誠實的，但不是閉環。 | 在 phase 交接清單登記這兩項為待承接事項，並於 U12／U13 判定 skip 時重新提交使用者。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-infra/nfr-design/security-design.md > D-1 驗證方式 | D-1 的全碟加密與四個掛載點檢查已進 DEPLOY.md（`DEPLOY.md:1455-1497` 含祖先鏈判定與 ZFS 分支），設計與落地一致。但設計自承 CI 完全驗不到，且對既有主機是一次重裝或資料遷移，實際主機（192.168.10.10）是否已加密在產出內仍為 [assumption]；此為已接受的風險，列此以便關卡知悉。 | 無需修改產出；關卡上確認是否有人負責實測主機並記錄結果。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| traceability.json 結構檢查（python 解析） | keys: stage, unit, upstream_ids, coverage, reverse；coverage 20 筆、upstream_ids 20 筆 | 20/20 對應完整，無裸缺口 |
| grep 核對 deploy compose（networks、depends_on、DATABASE_URL、mcp） | 確認 `mcp-bridge`、`mcp` 網段（internal: true）、backend 掛三網段、DATABASE_URL 為 postgresql+psycopg 於 `:85` | 證實 R-01(a)、R-02 |
| grep 核對 deploy.yml（Probe 步驟、runs-on、timeout、restored 輸出） | 探測為獨立步驟（`:313`），含 connect-timeout／max-time、條件位置取值；rollback 以 `restored` 輸出，timeout 20 | 設計契約 P-1 至 P-7 已被忠實落地；僅定位漂移 |
| 讀 `backend/services/user_router.py` login | 不存在使用者即 401，且在 verify_password 之前查 DB | 探測的 401 語意成立，P-2、P-3 仍正確 |
| 讀 `backend/database.py` init_db | 先 `_ensure_vector_extension()` 再 create_all，補丁數超過六 | 證實 R-03 |
| 舊審查 review-04（nfr-design） | R-14 至 R-23 為 Resolved，R-29、R-30 為前次已提 | R-01、R-02 的來源之一，仍留在凍結產出裡 |
