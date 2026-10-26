## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

規格對 nginx 一跳透傳、單一行程、三環境變數與 ADR-0006 四面向的處置扎實，但仍凍結在 IG1／IG2 作答之前：IG1=A、IG2=A 已於問題檔作答（2026-10-13T01:56:38Z），規格與 cicd、traceability 仍寫「待使用者裁決」，IG2 在四份產出零命中。前次 review-01 的三項 Major（R-01 至 R-03）在凍結產出中皆未處置，且 DEMO 檔案在工作樹已被移除（BrainPage.tsx、brain_router.py 不存在），第五節的前提與實況相反。依規則 Major 超過 2 項，判 NOT-READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | infrastructure-design/infrastructure-specification.md 第二節 OpenRouter 列（:32）、第八節、第十一節處置表（:256）；cicd-pipeline.md；traceability.json；infrastructure-design-questions.md:55、:65 | 前次 review-01 已提（R-01）。問題檔 IG1=A、IG2=A 已作答，但規格 :32 與 :256 仍寫「處置待使用者裁決」，第八節寫「本規格不改 render-env.sh、deploy.yml、deploy/.env.example」。grep 實測 IG2 在規格、cicd-pipeline、monitoring-design、traceability.json 命中 0 次。code-generation 讀這份規格不知道要在 deploy.yml:71-91 加必要檢查，也不知道 IG2=A 的同批約束由誰承擔。IG1=A 動到部署設定，依 project.md Mandated 還須同步 LOCAL-DEV.md，6.3 清單未含。設計一邊是問題檔（已定案），另一邊是規格（未定案），以問題檔為對。 | 把 IG1=A、IG2=A 寫成確定設計：列出 deploy.yml 檢查新增項與各文件改動、LOCAL-DEV.md 同步；指定 DEMO 移除由哪個單元與 Bolt 承擔；刪除所有「待裁決」措辭並更新 traceability 與第十一節。 | New |
| R-02 | Major | infrastructure-specification.md 5.2 DEMO 後端與前端列、5.3、第十節 Network exposure 列 | 前次 review-01 已提（R-02）。5.2 與 5.3 把 DEMO 刪除寫成待辦且「同批」，但工作樹中 backend/services/brain_router.py 與 frontend/src/pages/BrainPage.tsx 皆已不存在，前提與落地矛盾，工作樹為對。5.2 稱「無 /brain 的 e2e」，前次審查以 git grep 證實 member-pages.spec.ts 與 memory-page.spec.ts 以 page.goto('/brain') 作落地頁，另有 test_intent_routing_structure.py 讀 DEMO 檔，皆未列入。Sidebar 行號 212-219 越界（實為 211-217）。 | 以現況重寫第五節：DEMO 已移除則改為驗證項（路由唯一性測試、e2e 與結構測試已改鎖正式閘道）；更正「無 /brain e2e」與行號；寫明 IG2=A 下中間 Bolt 的 /brain 落地頁替代方案。 | New |
| R-03 | Major | infrastructure-specification.md 第八節；cicd-pipeline.md OPENROUTER_API_KEY 列；.github/workflows/deploy.yml:71-91、rollback job | 前次 review-01 已提（R-03）。IG1=A 要在 deploy job 擋空金鑰，但規格沒有上線順序：若合併時 secret 尚未設定，deploy 失敗會觸發 rollback，對整批合併（領先 origin/ut 83 個 commit）自動開 revert PR。規格未要求合併前以 gh api 查證 secrets 與 variables（project.md Mandated 的同步查證規則），也未說明失敗與 rollback 的關係。 | 寫入合併前置條件（查證 secret 名稱存在且未誤存為 variable）；寫明檢查失敗觸發 rollback 的後果，並決定放在合併前人工關卡或接受此行為。 | New |
| R-04 | Minor | infrastructure-specification.md 第二節 backend 列（:26）、4.4 前置 2；backend/requirements.txt:8-10、:56 | 前次 review-01 已提（R-04）。規格稱 websockets 與 uvicorn[standard] 隨 fastapi[standard] 安裝，但 requirements.txt 為 fastapi==0.111.0 與裸 uvicorn；websockets 在 :56 為獨立未釘版列。「uvicorn 預設 20 秒 ping」的假設因此落在未釘版間接依賴上。 | 更正依賴來源為 requirements.txt:56；4.4 加 import websockets 前置確認，build-and-test 記錄 uvicorn 實際使用的 WebSocket 實作。 | New |
| R-05 | Minor | infrastructure-specification.md 4.5 L2 失敗列 | 前次 review-01 已提（R-05）。建議加 proxy_set_header Sec-WebSocket-Protocol $http_sec_websocket_protocol，但 4.2 自己的靜態判定是 nginx 預設已透傳，該指令近乎空操作，會讓人誤以為已修復。 | 改為先診斷（比對 L1 與 L2 的請求標頭、nginx error_log）再決定修法，降級此建議。 | New |
| R-06 | Minor | infrastructure-specification.md 4.4 前置與 curl 補充檢查 | 前次 review-01 已提（R-06）。token 衛生不足：未要求 export 的取得方式（如 read -rs）、curl 的 -H 內插使 token 出現在 ps argv、-D - 全印標頭可能顯示被回送的 token。 | 補 read -rs 取得方式；curl 改由檔案或 stdin 讀標頭；輸出先經 grep 過濾。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep IG2 於 infrastructure-design 四份產出 | spec 0、cicd 0、monitoring 0、traceability.json 0；僅問題檔 1 | 確認 R-01，產出未承接 IG2 |
| grep 待裁決 | spec :32、:256 命中 | 確認 R-01，與問題檔 [Answer]: A 矛盾 |
| ls brain_router.py、BrainPage.tsx | 兩者皆不存在 | 確認 R-02，第五節前提與工作樹相反 |
| backend/requirements.txt | fastapi==0.111.0、uvicorn 裸、websockets 未釘（:56） | 確認 R-04 |
