# 功能設計關卡：合併前必修清單

- 來源：2026-10-18 functional-design 補審，共 19 輪；另含 entry-page-ui 與 object-picker-ui 兩輪既有審查。
- 裁決：使用者於關卡選「核可，這些列為合併前必修」。
- 其餘發現多屬「設計文字落後已落地程式」，已隨核可轉為已接受風險，不列入本清單。
- 本清單的項目必須在分支合併進 `ut` 前修正，或由使用者逐項裁決；處置結果在 build-and-test 站回填。

| # | 單元 | 審查發現 | 問題 | 性質 | 處置 |
|---|---|---|---|---|---|
| 1 | membership-service | review-02 R-01 | 自動改選管理者在「每個專案至少一位管理者」成立時不可達：停用守門會擋下最後一位管理者，改選只在沒有其他管理者時執行，兩者互斥，因此 AC12.4.1 做不到，橫幅也不會出現 | 設計與程式一起錯 | 待處置 |
| 2 | brain-ws-contract | review-05 R-01 | `error` 被歸為回合訊息，`turnId` 必填且不可為 null，但設計要求在沒有回合的情境也送 `error` | 設計與程式一起錯 | 待處置 |
| 3 | hierarchy-data | review-06 R-04 | 使用者仍擁有預設專案時，刪除該使用者會被外鍵擋下，`_hard_delete_user` 最後回 500 | 程式缺陷 | 待處置 |
| 4 | rbac-story-ids | review-03 R-01 | BR7.1–BR7.3 只檢查受邀者的角色，未檢查 J5 `authorization_status` 與 `is_active`，待核准或已停用的帳號可能被加為成員或被自動選為管理者 | 授權缺口 | 待處置 |
| 5 | intent-router | review-03 R-04 | 使用者選定澄清選項後，`referent` 與其他 slot 的意圖遺失；`brain_gateway.py` 的 `_on_select` 只重建單一 `Intent(capability, None)` | 程式行為缺漏 | 待處置 |
| 6 | memory-page-ui | review-02 R-08 | `deleteMemoryRecord` 把任何 404 都視為「已刪除」 | 程式缺陷 | 待處置 |
| 7 | mcp-bridge | review-03 R-01 | 使用者 JWT 在 `internal` 橋接網段以明文往返；把「不離開本主機」當成滿足「本機迴環或加密」的詮釋從未經人裁決（ADR-0006 encryption） | 資安待裁決 | 待處置 |
| 8 | mcp-bridge | review-03 R-02 | 成功的讀取沒有帶使用者身分的稽核紀錄，與 `requirements.md` 的「稽核主體為使用者本人」不符（ADR-0006 audit logging） | 資安待裁決 | 待處置 |
| 9 | member-pages-ui | nfr-requirements review-05 R-02 | 成員數超過 100 時整份成員清單隱藏（UIP-1，純前端上限），而成員頁是唯一的成員管理入口，101 人的專案連移除成員回到 100 以下都做不到 | 功能斷崖（非功能需求站加入） | 待處置 |
| 10 | membership-service | nfr-design review-02 R-04 | 停用帳號後的自動改選逐專案各自一筆交易，失敗時只記 log 並回 200，沒有任何呼叫者負責重跑，失敗的專案會永久沒有管理者 | 程式缺陷（非功能設計站加入） | 待處置 |
| 11 | memory-purge | nfr-design review-03 R-02 | 清除工作使用的系統 actor 列可經 `DELETE /{user_id}` 刪除（`GET /list` 也未排除它），刪除後清除稽核的 INSERT 全部外鍵失敗，90 天保存期就此停擺 | 程式缺陷（非功能設計站加入） | 待處置 |
| 12 | session-store | nfr-design review-02 R-01 | 首次建立 session 與 `set_work_target` 都是多次 HSET 加上 EXPIRE，不是原子操作；中途 key 過期或程序當掉，可能留下永不過期的 Redis key | 程式缺陷（非功能設計站加入） | 待處置 |
| 13 | intent-router | nfr-design review-03 R-03 | `intent_routing.py:192-229` 以 `except Exception` 吞下記憶讀取的所有錯誤，連授權拒絕也被當成一般降級處理 | 授權處理缺口（非功能設計站加入） | 待處置 |
| 14 | project-pages-ui | nfr-design review-02 R-01 | 成員頁以回 403 或 404 洩漏專案是否存在，原設計推給 U19／U24，但這兩者都沒有處理 | 資安（非功能設計站加入） | 待處置 |
| 15 | membership-service | infrastructure-design review-03 R-01 | 首次部署後、手動回填 `project_members` 之前，專案擁有者會被拒絕存取（U23 已改成讀成員列）；部署步驟須把回填排在對外開放之前 | 部署順序（基礎設施站加入） | 待處置 |
| 16 | membership-service | infrastructure-design review-03 R-02 | 沒有任何鎖逾時設定，而連線池是預設的 15 條；只要有一筆交易一直卡著鎖，就可能耗盡共用連線池，拖垮整個 backend | 可用性風險（基礎設施站加入） | 待處置 |
| 17 | memory-purge | infrastructure-design review-03 R-03 | 排程 workflow 只會從預設分支 `main` 觸發，合併進 `ut` 不會啟動 90 天清除，要等 `ut` 併入 `main` 才會開始跑 | 部署順序（基礎設施站加入） | 待處置 |
| 18 | session-store／work-orchestrator | infrastructure-design work-orchestrator review-01 R-02；nfr-requirements session-store review-02 R-01 | Redis 設定為 `maxmemory 256mb` 加 `noeviction`，最壞情況約 35 個 session 就會滿，滿了之後所有 session 寫入都失敗，而且沒有做過容量分析 | 容量風險（基礎設施站加入） | 待處置 |
| 19 | brain-gateway | infrastructure-design review-02 R-03 | 合併前必須先把 `OPENROUTER_API_KEY` 設定為 secret；沒設定的話，deploy 會失敗並觸發 rollback，系統會對整批合併自動開 revert PR | 部署順序（既有守門項再確認） | 待處置 |
