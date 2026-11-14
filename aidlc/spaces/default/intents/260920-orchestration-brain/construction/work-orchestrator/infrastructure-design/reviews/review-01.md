## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-18T16:29:56Z
**Iteration:** 1

### Summary

U12 work-orchestrator 的基礎設施面確實近乎為空，精簡形式合理；已實作的落點抽查屬實（`session_scripts/` 下有 `put_work_item.lua` 與 `update_work_item.lua`，`session_store.py:421/426/445` 與 `hierarchy_facade.py:481` 的方法存在，`work_orchestrator_capabilities.py:240` 用 ASGITransport，`redis_gateway.py` 有 EVALSHA 與 NOSCRIPT 退回）。有兩項 Major 需要人在關卡上裁決：(1) 上游 OQ-3（使用者內容落地的加密）在 nfr-design 被轉給本站，而本站只寫「併入 OQ-3」，沒有處置，等於無人承接；(2) 本單元唯一真正動到的資源是 Redis，而 compose 設定為 `maxmemory 256mb` 加 `noeviction`，本站寫「無變化」卻沒有容量分析。兩項都不阻擋實作（Major 數量為 2，未超過 2），故判 READY。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/work-orchestrator/infrastructure-design/infrastructure-specification.md 資源清單「加密」列；nfr-design/security-design.md 第六節 | 加密面無人承接。security-design 第六節寫明 `requestText`（Redis）與需求摘要（DB）兩處使用者內容落地併入上游 OQ-3，並說「被 skip 時轉 infrastructure-design（Redis 部署面）與 code-generation」，同時又寫「本單元不另定加密手段」。nfr-design 並未被 skip，但本站的規格只寫「無變化」並引用 OQ-3，沒有說 Redis 的 AOF 檔與 volume 是否加密、結論是什麼、誰負責。結果是 OQ-3 在兩站之間來回轉交，ADR-0006 的 encryption 面沒有落點。 | 在本站明寫 Redis（`appendonly yes` 持久化的使用者文字）與 DB 兩處的處置：接受風險並寫理由，或指派具體承接站與動作（code-generation 為 ALWAYS，可作兜底）。同時補一張 ADR-0006 四面向判定表，不得只引用上游。 | New |
| R-02 | Major | construction/work-orchestrator/infrastructure-design/infrastructure-specification.md 第一節 Redis 列；deploy/docker-compose.deploy.yml 約 254-260 行 | 容量未分析。實際 Redis 為 `--maxmemory 256mb --maxmemory-policy noeviction`（該檔註解指明 U12 的工作項放在同一個 session key 下）。本單元讓每個 session 多出 `wi:<id>` 欄位（含 `requestText` 與結果摘要），規格卻只說「不改 TTL、不建新 key」。noeviction 之下記憶體滿時是寫入失敗而不是淘汰，會連帶讓 U10 的其他 session 寫入失敗，影響範圍超出本單元。規格沒有估單一工作項大小、每 session 上限、也沒說 `put_work_item` 在 OOM 時的失敗路徑。 | 補單一工作項位元組上限與每 session 工作項上限的估算（可引用 NFR12.14-15），並說明 OOM 寫入失敗時 `dispatch` 的行為與 log 類別；若上限由 code-generation 承擔，須明寫並指派。 | New |
| R-03 | Minor | construction/work-orchestrator/infrastructure-design/cicd-pipeline.md「Lua 在真 Redis 上的一致性」列 | 比對後寫入（NFR12.12）的核心正確性只靠 opt-in 本機測試，CI 沒有 Redis 服務。檔案已誠實揭露並指向 scalability-design 第三節，但沒有指派誰在何時決定加 Redis service，容易永遠停在「可行的改進」。 | 指派一個承接站或標明為已接受風險。 | New |
| R-04 | Minor | construction/work-orchestrator/infrastructure-design/infrastructure-specification.md 第二節 | 部署順序表標題說三者「必須同一次合併」，但第三列又說 U13 呼叫「先上線無害（死碼）」，兩句對 U13 的約束方向不一致。 | 改成明確句子：U10/U7 必須同批，U13 順序不限。 | New |
| R-05 | Minor | construction/work-orchestrator/infrastructure-design/monitoring-design.md | 只列應用 log，沒有提到 audit logging 面：變更紀錄與記憶寫入（旁支寫入）失敗只有 WARNING，沒有說明失敗後稽核紀錄缺漏如何被察覺。 | 在監控設計補一句稽核寫入失敗的察覺方式，或明寫接受。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep 抽查已實作落點 | session_scripts 兩支 Lua、session_store 三個方法、hierarchy_facade.list_diagrams_of_system、ASGITransport、EVALSHA 皆存在 | 設計主張與落地一致，無矛盾 |
| 讀取 compose Redis command | maxmemory 256mb、noeviction、appendonly yes | 支持 R-02 |
| 依規定未執行測試或建置 | 不適用 | 遵守不得產生快取的限制 |
