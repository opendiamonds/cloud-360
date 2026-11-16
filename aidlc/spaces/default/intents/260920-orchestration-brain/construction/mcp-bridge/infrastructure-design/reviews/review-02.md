## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

mcp-bridge 這一站的核心形狀（零環境變數、與 backend 同映像覆寫 command 與 healthcheck、無 ports、CI 不新增 job、非阻擋的部署後健康紀錄）與已落地的 compose、ci.yml、deploy.yml 逐項對得上；算式、記憶體上限推導、日誌上界 1750m、60 秒預算、ADR-0006 四面向判定都自洽。最大的問題是網路拓樸：凍結的產出仍寫 bridge 掛在 `internal` 網段並據此算 blast radius，而使用者在前次審查 R-01 已裁決改走專屬網段 `mcp`（`internal: true`），已落地的 compose 也是如此。這個裁決只存在於 carried-review-items.md、code-generation-plan.md 與 code-summary.md，本站沒有任何 corrections 檔承載，所以只讀本站產出的人會得到錯的網路圖。已落地的程式是對的，設計產出是舊的。0 Critical、1 Major、2 Minor，依規則判 READY；建議在關卡上要求補一份 infrastructure-design-corrections.md。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/mcp-bridge/infrastructure-design/infrastructure-specification.md > 一 網路拓樸列；二之一 networks 列；三 compose internal 網段列；四 整節 blast radius；六 IC-6 驗證指令②；八 Encryption 與 Network exposure 列；cicd-pipeline.md > 三 CC-5；monitoring-design.md > 五 第 3 列；traceability.json > NFR21.16 | 類別：設計與已落地程式矛盾，程式那一邊是對的。產出全篇寫 bridge「只在 internal」「networks: [internal]」「internal 成員 4 到 5」「鍵集合恰為 cloud360_internal」，並在 blast radius 表宣稱 redis、ollama、db 的可達來源因 bridge 加入而各增為 4。已落地的 deploy/docker-compose.deploy.yml 於 mcp-bridge 區塊寫 networks: [mcp]，頂層 mcp 設 internal: true，backend 改掛 [edge, internal, mcp]，註解明說 bridge 不進 internal 且出站被切斷。此為使用者 2026-10-15T00:38:42Z 對本站前次審查 R-01 的裁決（carried-review-items.md:63；code-generation-plan.md 第 31 項；code-summary.md 第 108 與 187 行），code-summary 把本站 §二之一 與 §四 記為「取代」。但本站目錄沒有 infrastructure-design-corrections.md，凍結的產出仍是舊拓樸；若照 IC-6 驗證指令在主機執行，鍵集合會與實際的 cloud360_mcp 不符（DEPLOY.md:2040 已改為 cloud360_mcp）。連帶：Encryption 列的殘留面（能竊聽的容器）與 blast radius 結論都與實際相反，實際是 db、redis、ollama 不可達 bridge。 | 在本站目錄新增 infrastructure-design-corrections.md，逐項取代上列位置：網段改為專屬 mcp（internal: true，成員恰為 backend 與 mcp-bridge）、blast radius 改為 bridge 對 db／redis／ollama 零可達與出站切斷、IC-6 驗證指令②改為 cloud360_mcp、CC-5 斷言改為 networks 恰為 mcp 且 mcp 成員恰為兩者、Encryption 殘留面縮為 backend 一個容器；並寫明裁決來源與時間戳。不必回改凍結的原產出。 | New |
| R-02 | Minor | construction/mcp-bridge/infrastructure-design/infrastructure-specification.md > 四 host 可達面；六 IC-9；十 第 4 點 | 類別：設計與已落地程式矛盾。產出斷言「192.168.10.10 上任何行程能以容器 IP 連 mcp-bridge:8080」並要求把它加進 DEPLOY.md 的 host 可達清單。bridge 移到 internal: true 的 mcp 網段後，已落地的 compose 註解（約 :463-468）改為「host 行程是否可達取決於引擎版本，部署後實測，結果填入 DEPLOY.md §5.12」。兩者結論不同，產出的第 4 點揭露事項因此不成立。這與前次審查 R-07（容器 IP 形式的 Host 不在允許清單）同源，仍在凍結產出中未處置。 | 併入 R-01 的 corrections 檔：把 host 可達改為「未知，待部署後實測」，並指向 DEPLOY.md §5.12 為填寫處；關卡揭露事項第 4 點同步改寫。 | New |
| R-03 | Minor | construction/mcp-bridge/infrastructure-design/cicd-pipeline.md > 二 S-3；五 回滾程序第一列；infrastructure-specification.md > 五 Dockerfile 列；六 IC-6 ② | 類別：前次 review-01 已提（R-03 至 R-06）。凍結產出仍保留：S-3 未寫 working-directory 覆寫（backend job 預設在 backend/，.mcp-venv/ 會落在 build context 內）、`docker compose stop mcp-bridge` 不是持久止損（下一次 up -d 會拉回）、第二退路 venv 建立點在 COPY . . 之後造成快取失效、IC-6 ② 的 DEPLOY.md「六」清單不完整。這些已由 code-generation-plan.md 第 33 至 36 項承接，且已落地走第一順位（backend/requirements.txt 的 mcp==2.3.0，Dockerfile 未改），第二退路的三項實際未觸發。風險僅在於日後有人改走第二退路時讀到未修正的設計。 | 併入 corrections 檔，一句話指向 code-generation-plan.md 第 33 至 36 項為正本，並註明第二退路的 S-3 須帶 working-directory: . 且 venv 建立在 COPY . . 之前單獨 COPY requirements-mcp.txt。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀碼比對 deploy/docker-compose.deploy.yml（未執行任何指令） | mcp-bridge 區塊：build、restart、command（--host 0.0.0.0 --port 8080）、healthcheck（10s/5s/3/10s）、depends_on 無 condition、stop_grace_period 15s、logging、memory 512m 皆與 §二之一 相符；networks 為 mcp 而非 internal，無 ports、無 environment | 除網段外落地一致；網段差異為使用者裁決，成立 R-01 |
| 讀碼比對 deploy.yml:372-420 | 步驟 continue-on-error、12 次乘 5 秒、容錯取值、結束碼恆 0、不呼叫 /mcp、不持 token，與 cicd-pipeline.md 第四節與 CC-7 相符；另有靜態測試鎖住升級為阻擋的觸發條件 | 設計主張與落地一致 |
| 讀碼比對 ci.yml:247-314 | backend job 有 timeout-minutes 與 gen_mcp_tools.py --check 步驟，未帶 env | 與 S-1、S-2 相符 |
| 算式重算 | 16×(65536+1048576)=17825792；×10=178257920；512/370≈1.38；50×5×7=1750；12×5=60；1260+60=1320；540−60=480；13s 牆鐘＝2+10+1 且 15s 大於 13+1 | 全部成立，落地的 limits.py 註解與 stop_grace_period 關係式一致 |
| 契約端點三問（IC、CC、S 編號與設定項） | 每個新增設定與步驟皆可指名寫、讀、清或擁有、呼叫者；無孤兒 | 無缺口 |
| ADR-0006 四面向逐格比對 | 四格判定欄與上游相同；Encryption 為使用者接受的例外而非符合，措辭正確 | 判定無誤，內容受 R-01 影響需更正 |
