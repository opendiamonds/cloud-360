# Practices Discovery — 訪談問題

> Stage: practices-discovery（Inception 2.2）· Depth: Standard · Scope: feature
> 作答方式：在每題的 `[Answer]:` 後面填入選項字母（可含說明）。X 為自由填答。
> **成本揭露**：本題組共 6 題。核可後會執行 `practices-promote`，把 `team-practices.md` 的五個 section **整段替換**進 `aidlc/spaces/default/memory/team.md`，並把 `discovered-rules.md` 的硬約束追加進 `project.md`。這些內容之後每個 workflow session 都會被載入為規則，影響所有後續 stage 與 agent 行為。
> **已由證據確立、不問**：backend 無 linter／formatter／type checker；依賴未 pin 且無 lockfile；ESLint 16 條 error 級規則已隱性約束前端結構；zero TODO 標記紀律；docstring 品質高於平均。這些直接如實記載，不需人工裁決。

## Sources

- [lead] `team-practices.md`、`evidence.md`（pipeline-deploy-agent 草稿）
- [Q] `contributions/aidlc-quality-agent.md` — 品質視角盲審，7 項 OBJECT
- [D] `contributions/aidlc-developer-agent.md` — 開發者視角盲審，6 項 OBJECT
- [S] `contributions/aidlc-devsecops-agent.md` — 安全視角盲審，5 項 OBJECT
- [kb] `aidlc/spaces/default/codekb/cloud-360/`（reverse-engineering 產出）

---

## Q1. `team.md` 的記載姿態：寫現況，還是寫理想？

> **這題決定後面五題的答法框架。**
>
> 三位審查者各自獨立發現同一個模式：**多條規則的宣稱大於它的承載機制**。
>
> | 規則宣稱                                      | 實際承載                                                                                | 來源   |
> | --------------------------------------------- | --------------------------------------------------------------------------------------- | ------ |
> | `feature` scope 需 80% line coverage        | 無任何覆蓋率工具，量不到也擋不住                                                        | [Q]    |
> | ADR-0006 security baseline 為 hard constraint | 綁定的`extensions/security/baseline/` 路徑在 v2 遷移後全 repo 零命中                  | [S]    |
> | schema↔deploy 同步為 blocking                | 無自動化執行者；contract 只驗`project.md` 裡有沒有那兩個字串                          | [Q]    |
> | 私鑰／credential 樣式 CI 會擋                 | 掃描函式只看 12 個 contract 檔，結構上看不到`backend/`、`deploy/`、`.env.example` | [S]    |
> | 禁止 production 路徑 CI 會擋                  | 該函式以`git diff` 為輸入，在 CI 乾淨 checkout 上恆為空集合，是 no-op                 | [S]    |
> | org.md 宣告 squash-merge                      | 既有 PR 全數為 merge commit                                                             | [lead] |
>
> `team.md` 是每次 session 都會載入的規則層。它該描述「我們實際怎麼做」還是「我們認為應該怎麼做」，決定了 agent 讀到它之後的行為。

A. **寫現況，落差另立待辦** — `team.md` 只寫真實成立的實務；上述落差逐條記入 `evidence.md` 與技術債，不寫進規則層。好處：agent 讀到的規則都是真的，不會依賴不存在的護欄。代價：規則層看起來比較「不理想」。
B. **寫理想，標註未達成** — 保留 80% 覆蓋率等宣稱，但每條加註「目前無強制機制」。好處：保留改進方向的可見性。代價：agent 可能誤判護欄存在（例如假設 CI 會擋 secret 而放鬆自查）。
C. **分層寫** — `team.md` 只寫現況（A 的做法），另在 `discovered-rules.md` 把「補上承載機制」列為明確待辦。兼顧兩者，但本 stage 產出會變長。
D. Not yet defined
X. Other (please specify)

[Answer]:  C

---

## Q2. PR 合併策略：`org.md` 說 squash-merge，實際全是 merge commit

> `org.md` 的 `## Way of Working` 明文寫「We **squash-merge** Bolt branches into `ut`」，但 `git log` 顯示既有 PR 全數為 merge commit（本 repo 近期歷史可見 `Merge pull request #477`）。
>
> 這是 **strict-additive 衝突**：`team.md` 若寫「我們用 merge commit」，就與 `org.md` 的 squash 宣告矛盾，會在 §13 learning admission check 被擋下。需要你裁決方向。

A. **改用 squash-merge** — 承認 `org.md` 的規則，之後 PR 一律 squash。`team.md` 記載此決定並說明過渡（既有 merge commit 不追溯）。
B. **維持 merge commit，修正 `org.md`** — `org.md` 是本專案已客製過的檔（trunk 與部署段已改），把 squash 段一併改為 merge commit 即可解除衝突。`team.md` 則如實記載。
C. **視情況並用** — Bolt branch 用 squash（保持 `ut` 線性對應 Bolt 序列），一般 feature PR 用 merge commit。需在 `team.md` 寫明分界。
D. Not yet defined — 本輪 `team.md` 的 `## Way of Working` 不動合併策略，留待實際跑 Construction Bolt 時再定。
X. Other (please specify)

[Answer]: C

---

## Q3. Walking Skeleton：本專案的姿態？

> `team.md` 的 `## Walking Skeleton` 目前為空。此欄位會影響 Construction 第一個 Bolt 是否走 skeleton 儀式（solo、gated、需你明確核可後其餘 Bolt 才跑）。
>
> 證據面：本專案的部署管線已成熟（CI 四個 job、deploy 含 rollback job、10 組 agentic workflow、e2e 進 Kiwi TCMS），且本 intent 是在既有頁面加欄，不是打通新架構。

A. **宣告 `skeleton: off`** — 部署管線已成熟，沒有要 bootstrap 的東西；第一個 Bolt 照常跑。省下一次 gate 與一輪儀式。
B. **維持 scope-dependent** — 沿用 `org.md` 預設，由各 scope 檔的 `skeleton:` 欄位決定。本專案不表態。
C. **宣告 `skeleton: on`** — 即使管線成熟，仍要求第一個 Bolt 先打通端到端最小切片。代價：多一次 gate 與一輪儀式。
D. Not yet defined
X. Other (please specify)

[Answer]: A（2026-08-09 確認修訂：初答為 C，經成本確認後改為 A —— 部署管線已成熟、本 intent 為加欄非打通新架構，無 bootstrap 標的）

---

## Q4. 測試底線：既然覆蓋率量不到，改用什麼可執行的形式？

> [Q] 的核心發現：**本 intent 的六道 CI 閘門全部可以在功能壞掉時亮綠燈**。逐道查證——`repo-contract` 只做子字串比對；ESLint 不看資料形狀；`tsc -b` 因 `DbUser` 是手寫本地 interface 且 `res.json()` 回傳 `any` 而無效；import smoke 不驗行為；`unittest` 無任何測試涉及 `list_users`／`UserSchema`；Playwright 6 個 case 無一導覽至 Admin 頁。
>
> 這不是「覆蓋率幾 %」的程度問題，是這條路徑上**零斷言**的有無問題。
>
> [S] 另指出：本 intent 的核心安全變更是**授權矩陣變更**（開通 `Security_Reviewer`），既有 `test_rbac.py`／`test_j5_authz.py` 已在 service 層測授權，缺的是「矩陣變更需 allow/deny 雙向測試」——這項**今天就能寫，零新依賴**。
>
> 成本揭露：`TestClient` 採用成本為零（`httpx`、`fastapi[standard]` 已在 `requirements.txt`）；前端目前**完全沒有** unit／component 測試框架（`package.json` 僅 `@playwright/test`），要補需新增依賴。

（可複選，請列出所有要納入的字母）

A. **授權矩陣變更需 allow/deny 雙向測試** — 任何 `role_permissions` seed 變更，必須有測試同時驗證「該角色能做到」與「其他角色做不到」。零新依賴，今天就能寫。
B. **新增或修改 HTTP 端點需 `TestClient` 測試** — 補上 router 層的系統性缺口。零新依賴，但需建立第一支範例測試。
C. **前端資料形狀變更需 e2e 斷言** — 例如 Admin 表格加欄後，e2e 須斷言該欄存在且有值。用既有 Playwright，不需新依賴。
D. **引入前端 unit／component 測試框架** — 需新增依賴（Vitest 或類似），成本明顯較高。
E. **維持現狀，不新增測試底線** — 沿用 `org.md` 預設。
X. Other (please specify)

[Answer]: A, B, C（三項零新依賴的底線全採；D 前端 unit 框架本輪不引入，因 C 的 e2e 斷言已覆蓋加欄驗證需求）

---

## Q5. ADR-0006 的 security baseline 失去承載機制，要不要補進 `discovered-rules.md`？

> [S] 的發現：`CLAUDE.md` 第 3 章逐字把 security baseline 列為 Hard constraint（IAM、encryption、network exposure、audit logging），但 ADR-0006 把它綁在 `extensions/security/baseline/` —— **該路徑在 v2 遷移後全 repo 零命中**。目前只剩 `project.md` 的 `## Decided` 一行引用，`## Mandated`／`## Forbidden` 沒有任何可執行形式。
>
> 換句話說：這條 hard constraint 現在只是一句宣告，沒有任何規則或檢查承載它。
>
> [S] 判定這是唯一符合「人類已明述的硬約束」判準、卻未被記載為可執行規則的項目。

A. **補進 `discovered-rules.md` 的 `## Mandated`** — 以可執行形式重述（例如「涉及 IAM／權限矩陣／網路暴露／稽核記錄的變更，須在該 stage 產出中明列 security 影響與處置」），使其重新有承載。
B. **不補，另開 ADR 處理** — 這是 ADR-0006 的承載機制問題，屬架構級決策，應開新 ADR 而非在 practices 層補丁。
C. **不補，維持現狀** — 宣告存在即足夠，不需可執行形式。
D. Not yet defined
X. Other (please specify)

[Answer]: A

---

## Q6. `J3a:view` 的實際涵蓋範圍比 scope 文件措辭寬，需要確認

> [S] 查證：`Security_Reviewer` 對 `J3a` 目前在兩處 seed 皆為 `(false, false, false)`。本 intent 的 PU-4 要把 view 開為 true。
>
> **但 `J3a:view` 這一個旗標同時解鎖兩個頁面**：
>
> 1. `/admin/users` —— 使用者清單（含新的最後活動時間欄），這是 scope 文件 (d) 明確要的
> 2. `/admin/authorization-requests` —— **升權申請佇列**，可看到誰申請了什麼角色、目前狀態
>
> scope-document 的 (d) 寫的是「開通使用者管理介面的檢視權限」，intent-capture Q10 的已選答案是「給 `Security_Reviewer` J3a 的 view 權限」。**權限邊界本身沒有改變**（一直都是 J3a:view），但第 2 個頁面的存在在先前階段未被明確揭露。
>
> 另一項相關查證：權限稽核軌跡 `_audit_append()` 實作為 `logger.info`，而每次部署會 `--remove-orphans` 重建容器 —— **稽核軌跡的實際保存期約等於兩次部署間隔**。

A. **確認範圍，不改 scope** — `Security_Reviewer` 看得到升權申請佇列是可接受的（稽核角色本就該看得到誰在申請權限）。以本題的確認紀錄向下游傳遞，不回改已核可的上游 artifact。
B. **確認範圍，但要求收窄** — 只希望開通使用者清單，不希望開通升權申請佇列。這需要比現行 story×action 更細的權限粒度，屬 scope 擴充，需回跳 scope-definition 修訂重審。
C. **暫緩，需要更多資訊** — 請先說明升權申請佇列會顯示哪些具體欄位再決定。
D. Not yet defined
X. Other (please specify)

[Answer]: A
