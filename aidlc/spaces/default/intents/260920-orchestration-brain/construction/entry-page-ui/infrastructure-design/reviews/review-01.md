## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-17T04:55:26Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/infrastructure-design/cicd-pipeline.md > 三之二 「不受影響」段落（regression.spec.ts:55） | 既存漏審：該段把 `regression.spec.ts:55` 的 `not.toHaveURL(/\/workspace/)`（錯誤密碼）列為「不受影響」。實查該測試（`:51`）的 `@note` 逐字稱「不得導向 workspace 是關鍵斷言：只驗錯誤訊息無法排除顯示了錯誤但仍然放行」。`BR91.1` 之後成功登入的落點是 `/`（`LoginPage.tsx:107`），不是 `/workspace`；若登入被錯誤放行，URL 變成 `/`，`not /workspace/` 照樣為真。這條斷言在落點改變後變成恆真，是本 intent 最需要保護的 deny 方向之一。14 個測試的盤點只掃「斷言 workspace 為真」的位置，沒掃「斷言不是 workspace」的位置 | 把 `:55` 納入 EPI2 的處置：改為 `toHaveURL(/\/login$/)`（或斷言「登入系統」按鈕仍可見）並同步更新 `@step`／`@pass`；在 cicd-pipeline.md 三之二 改寫「不受影響」清單與合計數；突變驗證寫進 tcms-test-cases：讓後端放行錯誤密碼，該測試必須紅 | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/infrastructure-design/cicd-pipeline.md > 三之二 處置（EPI2=A，13 個測試改為 not.toHaveURL(/\/login$/)） | 新設計問題：新斷言嚴格弱於舊斷言。`/login$` 以外的任何落點（`/403`、`/waiting-approval`、載入中的空白）都會通過。對正向測試影響有限（後面有可見元素斷言），但 `Developer 看不到系統管理區`（`regression.spec.ts:173-176`）的唯一 deny 斷言是緊接在落點斷言之後的 `getByText('系統管理')).toHaveCount(0)`：落點斷言一旦只剩「離開登入頁」，沒有任何正向錨點證明頁面已渲染出導覽，`toHaveCount(0)` 在渲染前就為真，RBAC deny 方向形同虛設（`project.md` 的恆真 AC 規則與 `regression.spec.ts` 自己的 `@note` 都要求 allow／deny 成對有效）。文件只寫「不得順手放寬其他斷言」，沒有為「落點斷言被替換」指定替代錨點 | 在 EPI2 處置中規定：凡原本靠落點斷言當「頁面已就緒」的負向斷言（至少 `:173-176`），必須先加正向錨點（例如入口頁 testid 或側邊導覽地標可見）再斷言 `toHaveCount(0)`；其餘 12 個測試各列其後續的正向斷言作為錨點，code review 逐一核對；落點限定的測試（`管理員登入後進入入口頁`）維持 `toHaveURL(/\/$/)` 之類的精確斷言 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/infrastructure-design/cicd-pipeline.md > 二之一 步驟 6a 示意腳本 | 新設計問題：失敗訊息只說「沒有回 101 加協定名」，且 `2>/dev/null` 丟棄 curl 錯誤、最後一輪 `HDRS` 也未輸出。文件自己的原理區分了三種失敗（請求方向被剝為 403、回應方向被剝為 101 無該行、網路層失敗），腳本卻無法讓維運者在 Actions log 或 rollback 後分辨，只能回頭手動做 §五之二 第 3 步。步驟 6a 的第一次真實執行就是整個 intent 的合併部署，失敗代價是整個 intent 被回滾，診斷資訊不該省 | 失敗時輸出最後一輪的狀態列與是否有 sec-websocket-protocol 一行（不含 token，本檢查不帶任何機密），curl 結束碼也一併印出；結束碼 28 仍視為正常 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/entry-page-ui/infrastructure-design/cicd-pipeline.md > 三之二 處置（「舊案例標為停用」） | 新設計問題：處置假設 `tcms-test-cases` 能把孤兒 Kiwi 案例標為停用，但 `scripts/tcms_sync.py` 的註解（`:326`）寫明 `case_status` 由 junit plugin 維護、本工具只更新 text，無停用路徑。落實手段未指定，孤兒案例可能長期以「有案例、永遠無執行結果」的形式留在 TCMS，被讀成已覆蓋的證據（`project.md` 對 TCMS 錯誤覆蓋感的警告） | 在 tcms-test-cases 的交接事項中指定手段（維運者在 Kiwi UI 手動停用並記入 tcms-sync-report.md），或改為不更名、保留原案例名稱並更新描述，免去孤兒 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| jq 實算 traceability.json | upstream_ids 38、coverage 38、OK 16、N/A 22、reverse 3；upstream_ids 與 coverage 的 id 集合 diff 為空 | 與文件宣稱的 38／16／22／3 完全一致 |
| grep 實算 EPI2 的 14＝4＋8＋2 | regression.spec.ts 的落地斷言位於 `:73`、`:90`、`:113`、`:158`、`:173`、`:189`（4 個獨立測試加 `gotoAdmin` 8 處呼叫）；estimate-workspace.spec.ts 的 `login` helper `:17` 與 `:35`（2 個測試）；其他 spec 無 workspace 斷言 | 14 的算術成立；但漏列 `regression.spec.ts:55` 的反向斷言（R-01） |
| 讀取 deploy.yml 與 test_mcp_bridge_deploy.py:101-104 | 插入點在 `Verify sessions survive a Redis restart`（`:447`）之後、`Record this commit`（`:570`）之前，不破壞該 unittest 的前後步驟斷言；其他測試未釘住這兩步；rollback 條件為 pull_request 且 merged（`:599-602`），手動 dispatch 失敗不回滾，與文件一致 | 位置約束與回滾互動的陳述成立；6a 不進 rollback 驗證的理由成立 |
| 讀取 brain_gateway.py:651-653、718-725 與 brain_gateway_rules.py:106-121 | 僅帶協定名、無 bearer：accept 時回送 `cloud360.brain.v1` 後以 4401 關閉；協定名缺漏則未 accept 即 close；握手路徑無 Origin 判斷；僅帶協定名時 `has_protocol_name` 為真、`bearer_token` 為 None | 6a 的推論成立，免 token；請求被剝時走 403 路徑、回應被剝時無標頭行，可區分 |
| 讀取 main.py:82-85 與 ci.yml 的 import smoke | `build_brain_gateway(app)` 在 startup hook 內（`:84`）；註解逐字說明 import smoke 與 TestClient 不觸發 | 上游更正成立；資料面探測（`deploy.yml:313` 起，30 次，失敗即 `exit 1`）確實會擋部署 |
| 讀取 user_router.py 的使用者列表排序 | 以 `User.id` 排序（`:537`） | 14 個測試改為在 `/` 掛載大腦連線、更新 admin 最後活動時間，不會擾動分頁順序 |
| 失敗路徑與合併順序計數 | 失敗路徑表 21 列、合併順序表 7 列；四種性質欄位用法一致，所有 CI 紅燈均標為不擋合併，與 `ci.yml:557-562` 的無必要狀態檢查一致 | 「訊號」與「擋合併」沒有混淆；僅部署資料面探測與 6a 為真正擋部署 |
| 未執行項目 | 未執行任何測試、python、npm、curl，也未啟動 stack | curl 對 101 升級的實際行為與 Cloudflare 兩跳只能由 code-generation 本機驗證與首次部署證實，文件已如實承認 |

### Summary

基礎設施面站得住腳：6a 的原理、插入位置、與 rollback 的互動、上游 import smoke 更正、traceability 計數與 14 個測試的算術都經實查成立，沒有 Critical。主要缺口在 EPI2 的處置：落點改為 `/` 之後，`regression.spec.ts:55` 的「不得導向 workspace」變成恆真（R-01），而 13 個測試改用的 `not.toHaveURL(/\/login$/)` 讓 `Developer 看不到系統管理區` 的 deny 斷言失去就緒錨點（R-02），兩者都是 RBAC／登入的反向保護被悄悄削弱，應在 code-generation 前補進處置。判定 READY（0 Critical、2 Major）。三類計數：新引入 0、既存漏審 1（R-01）、新設計問題 3（R-02、R-03、R-04）。
