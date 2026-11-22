## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-07T23:41:14Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `security-requirements.md` §二 `NFR6.10` ＋ 判準欄 | `NFR6.10` 的判準寫「連線不帶 `-U postgres` 之類的 superuser 覆寫；`docker compose exec -T db psql` 的預設身分即 `POSTGRES_USER`」，暗示 `POSTGRES_USER` 與 superuser 是兩個不同身分，「用 `POSTGRES_USER` 連線」即避開了 superuser。但實測 `deploy/docker-compose.deploy.yml:42-44` 只設了 `POSTGRES_USER`／`POSTGRES_PASSWORD`／`POSTGRES_DB` 三個環境變數，而官方 `postgres`／`pgvector` image 的既定行為是：由 `POSTGRES_USER` 建立的角色**本身就是 superuser**。`schema_rbac.sql:524` 的 `GRANT USAGE ON SCHEMA memory TO %I', current_user` 把 schema 權限授予「目前執行初始化腳本的身分」——也就是那個已經是 superuser 的 `POSTGRES_USER` 自己，不是授予一個另外存在的受限角色。`U5` 自己的 `OPEN-CG5-1` 已點出「service container 只有 superuser」，但 `U9` 把這個已知事實寫成「無機械強制」（聽起來只是缺 CI 驗證），沒有把更根本的事實講清楚：**本系統目前不存在任何非 superuser 的資料庫連線身分**，所以 `NFR6.10` 字面上要求的「以 `POSTGRES_USER`、不以 superuser」是一個在本架構下無法被兩個不同連線區分的判準——不管清除 workflow 怎麼連，都是用 superuser 連線，`NFR6.10` 目前恆真（永遠通過），而不是「未驗證但可能失敗」。 | 修訂 `NFR6.10` 的敘述與判準，明確寫出「本系統現狀是 `POSTGRES_USER` 本身即 superuser，`NFR6.10` 目前無法區分『用 `POSTGRES_USER`』與『用 superuser』，是同一件事」，並把「是否需要為清除動作新增一個真正受限的資料庫角色」交給 `infrastructure-design`／`code-generation` 判斷，而不是讓現有判準看起來像是已經在防護 IAM 邊界。 | New |
| R-02 | Major | `security-requirements.md` §二 `NFR7.11`；`schema_rbac.sql:483-484`／`:508-509` | `NFR7.11` 要求每筆 `purged_by_retention` 稽核事件的 `actor_user_id` 為「保留的系統 actor」，而 `memory_audit_events.actor_user_id` 是 `NOT NULL REFERENCES public.users(id)`——寫入時必須給一個指向 `public.users` 既有列的具體整數值。全樹搜尋（`schema_rbac.sql`、`backend/`、`U5`／`U9` 的所有產出）找不到任何地方定義或 seed 這個「系統 actor」的實際 `user_id`。`U5` 的 `rules.md BR2.4` 與 `entities.md` 只在概念層定義「系統行為者」，`U9` 的八條需求與三個殘留風險（`OPEN-N9-1/2/3`）也完全沒有提到這個缺口。若無具體值，清除 workflow 的 `INSERT INTO memory_audit_events` 這一步**在語法層就會失敗**（違反 `NOT NULL` 外鍵），`NFR7.11` 因此不是「未強制」而是「目前無法被任何 SQL 滿足」。 | 在 `security-requirements.md` 新增一個殘留風險項（如 `OPEN-N9-4`），明記「系統 actor 的具體 `user_id` 尚未提供（seed 列或固定常數皆可），須在 `code-generation` 落地前補齊，否則 `purged_by_retention` 的 INSERT 無法執行」，並指出此缺口同樣適用於 `U5` 自己（`U5` 定義了概念但同樣沒有 seed 具體值）。 | New |
| R-03 | Minor | `security-requirements.md` §二 `NFR7.10`／`NFR7.15`；`tech-stack-decisions.md` | 兩條 DELETE（記憶列、稽核列）與一次 INSERT（`purged_by_retention` 稽核）之間的交易邊界、執行順序與部分失敗（例如記憶列刪除成功但稽核寫入失敗、或稽核清除與本次新寫入的稽核列交錯）皆未討論。`construction.md` phase guardrail 要求「整合邊界（DB 操作）須有錯誤處理，區分可重試與致命錯誤」，本站八條需求對此完全沒有涉及——雖然這更貼近 `infrastructure-design`／`code-generation` 的實作細節，但本站連「須交給下一站決定」這句話都沒寫，是一個無聲的缺口而非已承接的缺口。 | 在殘留風險清單新增一項，要求 `infrastructure-design` 或 `code-generation` 明定：兩次 DELETE 與一次 INSERT 的交易邊界、順序（建議先寫稽核再刪記憶，確保稽核先於記憶消失落地）、以及任一步失敗時整個 run 是否需要可重試（而非部分提交）。 | New |

### 摘要

- 分類：`R-01`、`R-02` 為 `new-design-problem`（判準本身的邏輯缺口，雖然根因部分承自 `U5` 已知的 `OPEN-CG5-1` 與未 seed 的系統 actor 概念，但本站是第一個真正需要寫入/連線的消費者，問題在本站才變得可觸發且本應被指出而未指出）；`R-03` 為 `new-design-problem`（本站範圍內的沉默缺口）。
- 計數：`new-design-problem` 3、`pre-existing-unreviewed` 0、`propagated-from-upstream` 0。

### 覆蓋範圍

**已查證（有機械證據）**：
- `DG-1` 關閉的依據：開 `schema_rbac.sql:480-512` 逐字核對 `memory_audit_events` 的 COMMENT，與 `security-requirements.md §三`、問題檔 §〇之一 逐字一致，判定成立。
- 兩個清除目標的欄位與索引存在：`memory_records.expires_at`（`ix_memory_records_expires_at`）與 `memory_audit_events.occurred_at`（`ix_memory_audit_events_occurred_at`）皆已開檔確認存在。
- 「本 repo 無自架 runner 排程先例」的雙向查證：重跑 `grep -q "schedule:"` 逐檔取 `runs-on`（7 個 schedule workflow 全為 `ubuntu-slim`／`ubuntu-latest`）與 `grep -rln "self-hosted"` 反向查（`ci.yml`／`deploy.yml` 兩者 `schedule:` 命中數皆為 0），與站內文件逐字一致。
- `deploy.yml:27`、`:146-148`、`:402` 的引用內容與行號皆核對通過（self-hosted runner、db 無 host port、`-T` 必要性、rollback job 亦用 self-hosted）。
- `unit-of-work.md:221`（`DG-1 尚未解決` 原文）、`contract-summary.md` 的三個葉節點與 `K-05` 條目皆核對通過。
- `NFR6.10` 與 `NFR7.11` 的判準經實際開 `deploy/docker-compose.deploy.yml` 與 `schema_rbac.sql` 的 schema 定義逐行核對，查出 R-01、R-02 兩項。
- `NFR9`（成本）、PBT `N/A` 判定、ADR-0006 四面向表與 `U5` 同名表逐格比對，無矛盾。
- `NFR1`／`NFR2`／`NFR3`／`NFR4`／`NFR5`／`NFR10`／`NFR11` 的 `N/A` 判定逐條核對其理由（packaging、零端點、零 session、零前端面、零 LLM），皆合理。

**未查證／本輪未覆蓋**：
- `NFR7.13`（runner 離線偵測）的具體機制，因本站明確不預選、交 `infrastructure-design` 決定，故本輪不評估機制本身的可行性，只確認「不預選是否恰當」——判定恰當（`infrastructure-design` 是正確落點，且本站已固定可機械判定的判準）。
- 未逐一驗證 `NFR8.10`（「零新部署設定」）在實際 `code-generation` 落地時是否真的不會觸及 `deploy/` 任何檔案——本輪只確認該判準本身可機械執行（`validate_env_contract.py` ＋ diff 範圍檢查），未實際跑過（因為本單元尚未進入 `code-generation`）。
- 未深入複驗 `contract-summary.md` 全文與 `U5` 全部六個 ADR 的交叉一致性，僅核對與本單元直接相關的段落。
- 未檢查 `tech-stack-decisions.md` 之外是否存在其他隱性新依賴（例如 `psql` CLI 版本與 PG18 的相容性），判斷為超出本站範圍。

VERDICT: READY
