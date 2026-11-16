## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

U9 memory-purge 的 nfr-requirements 產出（security-requirements.md、tech-stack-decisions.md、traceability.json）整體自洽：八條需求皆有二元判準，`DG-1` 過期記載的關閉依據、「無自架 runner 排程先例」的雙向查證、`unit-of-work.md:221`、`contract-summary.md:27`／`:389` 的引用，我都逐一開檔核對，內容正確。主要問題有兩個，都是前次 review-01／review-02 已提、仍留在凍結產出裡的舊發現：`NFR6.10` 在本系統現況下恆真，卻仍被 ADR-0006 IAM 格寫成「守住 grant 邊界」；`NFR7.11` 要求的系統 actor 在本站完全沒有具體落點（`actor_user_id` 為 NOT NULL 外鍵）。兩者在下游 nfr-design（`[ND1]`／`[ND2]`）與已落地的 `schema_rbac.sql` 已被實質處置，故判斷是「凍結產出本身需要被標註已被取代」而非設計仍有缺口，不構成 NOT-READY。另有三項 Minor：story map 指派給本單元的 `AC4.2.3` 未被引用、`NFR7.15` 判準在同一次 run 內可能被 `NFR7.11` 的 INSERT 干擾、`deploy.yml` 行號已漂移。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/memory-purge/nfr-requirements/security-requirements.md §二 `NFR6.10`、§四 ADR-0006 IAM 列、§五 殘餘風險 2；traceability.json coverage `NFR6` | 前次 review-01／review-02 的 R-01 已提，仍留在凍結產出裡：`NFR6.10` 與 IAM 格把「以 `POSTGRES_USER` 連線、不用 superuser」寫成一條有意義的 IAM 邊界，並把缺口定性為「無機械強制」（像是只缺 CI 驗證）。我核對 `deploy/docker-compose.deploy.yml:42-44` 只設 `POSTGRES_USER`／`POSTGRES_PASSWORD`／`POSTGRES_DB`，官方 pgvector image 由 `POSTGRES_USER` 建立的角色本身就是 superuser；`schema_rbac.sql:557-563` 的 GRANT 授予 `current_user`，即該 superuser 自己。因此本系統目前不存在任何非 superuser 連線身分，`NFR6.10` 的判準永遠通過（恆真），不是「未驗證但可能失敗」。下游 nfr-design/security-design.md §二（`[ND2]`=A）已更正這點，且 memory-retention-purge.yml 註解亦承認 `POSTGRES_USER` 是唯一身分，所以設計與落地沒有矛盾，下游那邊是對的；但 nfr-requirements 本站沒有 corrections 檔，讀者若只讀本站會得到錯誤的 IAM 強度。 | 在關卡上把本項記為「已被 nfr-design §二 取代」的接受風險，或補一份 `*-corrections.md` 說明 `NFR6.10` 恆真、IAM 格的強度須以 nfr-design 為準。不要讓本站單獨被讀成 IAM 邊界已存在。 | New |
| R-02 | Major | construction/memory-purge/nfr-requirements/security-requirements.md §二 `NFR7.11`、§五 殘餘風險（無 `OPEN-N9-4`）；traceability.json open_items | 前次 review-01／review-02 的 R-02 已提，仍留在凍結產出裡：`NFR7.11` 要求每筆 `purged_by_retention` 稽核事件的 `actor_user_id` 為「保留的系統 actor」，但 `memory.memory_audit_events.actor_user_id` 是 `NOT NULL REFERENCES public.users (id)`（`schema_rbac.sql:517`），本站三個殘餘風險與 `OPEN-N9-1/2/3` 都沒有指出「該 actor 的具體 user_id 從哪來、誰 seed、誰保證它不被刪」。契約端點三問中，這個欄位的「誰寫」（清除 SQL）有、「誰建立被引用的列」與「誰保證它存在」沒有。實際影響：本站判準「新列數為 N 且 actor 不是擁有者」在沒有該列時，INSERT 會因外鍵違反而整個失敗。下游已處置：nfr-design §一（`[ND1]`=A）設計了系統 actor 列，`schema_rbac.sql:810-862` 已 seed `SYSTEM.retention-purge` 並寫明四道鎖與「不可刪除」，所以落地是對的；本站缺的是在當下把這個依賴指名出來。 | 在關卡上記為「已由 nfr-design §一與 schema_rbac.sql K 區塊承接」，或在 corrections 中補上 `OPEN-N9-4`（系統 actor 的具體列）。另請把 nfr-design 的 `OPEN-ND9-1`（Admin 清單可能被誤刪該列）視為本需求的延伸風險一併帶入關卡。 | New |
| R-03 | Minor | construction/memory-purge/nfr-requirements/traceability.json；security-requirements.md §〇 上游依據表 | `unit-of-work-story-map.md:53`／`:114` 把 `US4.2` 指派給 `U9`，而 `stories.md:253` 的 `AC4.2.3`（「一筆情節記憶已存在超過 90 天，清除執行過後不再出現在脈絡組裝中」）正是本單元唯一承接的 AC。本站三份產出對 `US4.2`／`AC4.2.3` 的出現次數為 0（grep 實算），上游依據表也沒列 stories。後果是追溯鏈只有 FR／NFR 這一側，AC 側斷開；另外「到期後到下一次清除之間，已逾期但未刪的列是否仍可被脈絡組裝取到」這個窗口（排程為每日一次）沒有被指名由誰負責（清除端或 U8 的檢索端）。 | 在 traceability.json 補一列 `AC4.2.3` 的 coverage，並註明到期到清除之間的窗口屬於 U8 檢索過濾還是接受每日延遲。 | New |
| R-04 | Minor | construction/memory-purge/nfr-requirements/security-requirements.md §二 `NFR7.15` 判準欄、`NFR7.11` | `NFR7.15` 的判準是「稽核清除步驟執行後，`memory_audit_events` 的列數只減不增」，但 `NFR7.11` 要求同一次 run 為每列被清除的記憶 INSERT 一筆稽核。若以整個 run 前後計數，INSERT 會使列數上升而違反判準；判準沒有限定「只量稽核 DELETE 那一條語句」或「以 `action <> 'purged_by_retention'` 或 `occurred_at` 早於本次 run 的子集計」。判準字面上可被誤讀為與 `NFR7.11` 互斥，無法二元判定。 | 把判準改寫成限定在稽核 DELETE 語句本身（例如「該語句受影響列數 ≥ 0 且其後沒有針對 `action = 'purged_by_retention'` 的、由該語句產生的 INSERT」），或明寫量測子集。 | New |
| R-05 | Minor | construction/memory-purge/nfr-requirements/security-requirements.md §〇 上游依據表、tech-stack-decisions.md §一 | 本站引用 `deploy.yml` 的「兩個 job（`:27`／`:402`）」與「`:146-148`」。我開檔核對：`:27` 正確；但現在自架 runner 的第二個 job 在 `:656`，`db` 無 host port 與 `-T` 說明在 `:152-154`，`:402` 不再是 runner 宣告。`deploy.yml` 在工作樹中已被後續修改（git status 為 M），行號漂移可解釋，但引用已不能機械複驗；前次 review 當時核對通過是真的。內容事實（兩個 job 用自架 runner、db 無 host port）仍成立。 | 改以內容錨點引用（例如「rollback job 的 `runs-on`」），或在關卡註明引用以當時版本為準。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 逐檔開檔核對（deploy.yml、schema_rbac.sql、docker-compose.deploy.yml、unit-of-work.md、contract-summary.md、stories.md、story-map） | 多數引用正確；`deploy.yml:402`／`:146-148` 已漂移 | 對應 R-05 |
| grep `\*\*`NFR..`\*\*`（粗體 id 計數） | 8 | 與 §一「恰等於 8」的自述一致，無問題 |
| grep `US4.2`／`AC4.2` 於本站三份產出與 traceability | 0 命中 | 對應 R-03 |
| 檢查下游承接（nfr-design §一／§二、schema_rbac.sql:810-862、memory-retention-watchdog.yml） | 系統 actor 已 seed；`NFR6.10` 已更正；`NFR7.13` 偵測 workflow 存在 | R-01、R-02 的實質風險已由下游處置，`OPEN-N9-1` 已有落地 |
