<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-28T11:46:42Z — **五項 Major 裡有三項是同一個毛病：我把「本站做了設計」寫成「本站結案了」**。R-01 是 OQ-3（結案的只有 S-4）、R-02 是 SEC-4（只關掉兩個分支中的一個）、R-04 是 S-6（設計了範圍擴充但那個 job 尚不存在且不歸我）。三者都不是設計錯誤，是**完成度的宣稱超過實際**。可執行的檢查：每寫下一句「已結案／已滿足／已變強」，就問「這件事的另一半在誰手上？」——如果答得出一個別的單元或站，那就不是結案
- 2026-09-28T11:46:42Z — R-03 特別值得記：我設計了一個 CI job 的步驟，卻沒注意那個 job 是別人的交付物（brain-infra 的 NFR6.1 落點 3 逐字寫「N-2 的真實 PostgreSQL CI job」、狀態「尚未存在」，屬 U5）。我自己的需求 U4-V1 明文寫「共用」「不另開第二個 job」，而設計檔全篇對「共用」「N-2」「U5」零命中——**我的設計與我自己的需求脫節，而不是與上游脫節**。送審前自檢應該加一問：本站的設計裡，每一個被設計的東西，擁有者是誰？

- 2026-09-28T11:23:40Z — **第三次同型錯誤，而且是在前一站剛寫下教訓之後**。我在 U4 的 nfr-requirements 寫「沒有任何一份上游說過這個共用 CI job 該用哪個映像」，實際上 brain-infra 的 nfr-requirements 自己的 NFR6.1 逐字把「N-2 的真實 PG CI job service container」列為映像必須一致的四個落點之一（pgvector/pgvector:pg18），而 deploy/docker-compose.deploy.yml:40 現況亦然。根因與 R-03／R-14 完全一樣：對另一份檔案的狀態下斷言而沒有開那份檔案。**新增的具體教訓**：我只讀了共用契約（K-01），而**兄弟單元自己的 NFR 產出不在契約裡**——閱讀範圍限制是給審查者的，不是給 conductor 的，所以「查上游」必須包含兄弟單元的 per-unit 產出，不能只查 inception 的共用檔
- 2026-09-28T11:23:40Z — 順帶發現 R-01 那次改編號（NFR6.x → U4-V*）除了「不宣稱不成立的父項」之外還有第二個好處：brain-infra 也用了 NFR6.1 指別的東西，原本的編號在同一個 intent 內跨單元碰撞。改編號是誤打誤撞避開的，但它說明 per-unit 的需求應該帶單元前綴，而不是掛 inception 的 NFR 號

<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-27T00:46:33Z — **本單元是 `kind: packaging`，引擎解析後本站只產 `security-design.md` 與 `traceability.json`**。另五項（`performance-design`／`scalability-design`／`reliability-design`／`observability-design`／`logical-components`）的 `produces_kinds` 皆不含 `packaging`，是設計上的缺席、不是漏寫。這使本站的實質範圍縮成「這個部署包的安全設計」，而 stage 檔 Step 4 列的五類 NFR 只有 Security 一類有落點。
- 2026-09-27T00:46:33Z — **本站只問 requirement 完全沒碰到的事**。`nfr-requirements` 已鎖 20 條編號需求，`§五` 又明文把六件事交給 `U10`／`U5`／`U8`／部署者。逐一比對後，真正還開著且屬本單元的只有四件：靜態加密由哪一層承載、容器間傳輸加密、Ollama 零認證在扁平網段上的處置、升版 dump 檔的處置——四件全部落在 ADR-0006 的 encryption 與 network exposure 兩個面向。
- 2026-09-27T01:43:52Z — **本 repo 有三份 compose，不是兩份**。除 `deploy/docker-compose.deploy.yml` 與 `deploy/docker-compose.test.yml`，repo 根還有 `docker-compose.yml`（`db` 為 `postgres:15-alpine`、publish `5432`，另有 `adminer` publish `8080`），而已核可的 `NFR6.1` **落點 4 逐字**就是它。初版把 `NFR8.4` 判為 N/A 的理由寫成「本機 dev 無 compose」——與已核可需求直接矛盾。D-3 刻意不適用於它（publish 端口是它存在的目的，且它上面沒有 `cloudflared`／Redis／Ollama、沒有要擋的威脅），但那要寫成理由而不是忽略它的存在。
- 2026-09-28T03:27:07Z — **`U2` 是 `spec`，`produces_kinds` 把七項產出濾成兩項**（`security-design.md` ＋ `traceability.json`）。`logical-components` 的 kind 清單是 `[service, ui, library]`，不含 `spec`，故一併濾除。本站的 `traceability.json` 要逐條覆蓋上一站的 `NFR5.1`–`NFR5.7` 共七個 `NFRx.y`。
- 2026-09-28T03:27:07Z — **本站是解掉上一站兩項 Minor 的正確落點，不需回改凍結的產出**。審查 R-01 指出 `NFR5.7` 的禁用名單以「等」收尾、不是封閉集合——而「把需求轉成具體可執行的設計解」正是 `nfr-design` 的職責。在此收斂它，比要求 `code-generation` 自行猜測或回頭解凍 `nfr-requirements` 都乾淨。

## Deviations
- 2026-09-28T11:46:42Z — R-07 讓我把 U4-R1 從 N/A 改成 OK。原本的理由是「規則已在上游定好，本站沒有可加的設計」，但 spec 單元的 performance-design 被 produces_kinds 濾掉，於是「截止欄位是哪一欄」「要不要索引」這兩個資料面決定**沒有別的落點**。抽身太快的代價是把決定丟給 S-5 的實作者去猜

- 2026-09-28T11:23:40Z — Q1 使用者以自由文字答「不需要做任何加密」，比選項 A 更乾脆。我沒有直接當成 A 寫進去，也沒有整題重問——改為一次窄化確認：結論照他的，但 ADR-0006 的判定、理由與殘餘風險照寫（那是 hard constraint，要求每個面向都有明確判定且不得留空）。這是「不猜使用者的意思」與「不放棄 hard constraint」兩者同時成立的最短路徑
- 2026-09-28T11:23:40Z — U4-V4 的 traceability 狀態記為 Deferred 而不是 OK。它在 CI 上刻意不設案例：依前一站的可達性更正，在 BR2.2 的「取用既有」之下，約束拒絕只在實作已經寫錯時才可達，構造那種夾具等於測試一份不會被交付的程式。記 OK 會讓它看起來有自動化承載者，實際上沒有

<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-27T00:46:33Z — **stage 檔 Step 2 列的六個 focus areas，本站只用到兩個**（Security approach、部分的 Logical component boundaries——後者以網段分段的形式出現在 security 設計裡）。Resilience／Scalability／Performance／Observability 四項對 packaging 單元沒有承載的產出檔，故不出題；理由記在問題檔前言。這是 `project.md` 的 `feasibility:c2`（stage 檔的範例問題清單是 guidance 不是 script）的直接套用。
- 2026-09-27T01:43:52Z — **D-3 推翻了已核可的 `[N4]`=A，而我出題時沒揭露**。`NFR8.8` 的「未採用的替代方案與其代價」逐字排除了「另切一個只含 `db`／`backend`／`ollama` 的內部 network」，同節寫明「這是刻意決定，不是遺漏」。我在 G3 把它當成「補措辭缺口」的選項 A 給使用者，沒有指出它是反轉——`project.md` 有明文規則要求這種情形先界定範圍、再把處置交給使用者裁決。由審查 R-02 查出後補做，使用者裁決保留 D-3 並明寫反轉。**可執行補強**：出題前對每一個候選選項，去上游該條需求的「未採用的替代方案」段 grep 一次；那一段的存在本身就是「有人考慮過並排除」的訊號。
- 2026-09-27T01:44:05Z — **本 session 第二次寫出未實測的時間戳，兩次都是我自己抓到並更正的，但根因沒被修掉**。第一次在 `nfr-design-questions.md` 的 `G5` 作答註解（填 `00:41:30`，實測 `00:46:09`），第二次在本日記（填 `01:20:00`，實測 `01:43:52`，五處）。`project.md` 的 `user-stories:260822-us-L1` 早已明文禁止憑感覺寫時間戳。**根因是流程形狀**：我把時間戳字面值寫進 heredoc 或腳本常數，而 `date -u` 的呼叫與它是兩個獨立動作，中間有落差就會被我用「看起來合理的值」填掉。**可執行修法**：一律 `TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)` 取值後把它當**參數**傳進腳本（`python3 - "$TS"` ＋ `sys.argv[1]`），不在腳本內寫任何時間字面值。本輪之後照此執行。
- 2026-09-27T02:07:10Z — **R-01 的修法第一版沒有關上它要關的洞，因為我沒問「這條失敗路徑是有人在場還是無人值守」**。探測只落在 `DEPLOY.md` 的手動升版章節，而 `deploy.yml:10–14` 觸發於合併進 `ut`——D-3 這次網段變更本身就走那條路。照第一版實作，`deploy.yml` 對 `/api` 的命中數仍是 0，引入分段的那一次部署仍綠燈通過。使用者於 `[G6]`=A 裁決把探測推進 `deploy.yml` 的部署後步驟，並接受它擴大本單元範圍（從「改 deploy.yml 的環境變數同步」到「改它的部署流程」，且因失敗會觸發既有 rollback，實質是一個新的自動回滾觸發條件）。**可執行檢查**：為任何缺口設計驗證時，先問那個缺口會在哪幾條路徑上出現（手動 vs 自動、有人 vs 無人），再決定驗證要放幾個地方；只放一個地方時必須寫出「另一條路徑仍無閘門」。
- 2026-09-27T02:47:38Z — **`review-freeze` 的正解是「開下一個 iteration」，不是跳躍**。本 stage 我先後試了三條路：(1) 直接編輯 → 被 freeze 擋；(2) `jump execute --direction redo` 取得新 attempt → **可行但代價被我低估**：redo 重設的是整個 construction 區塊的 run floor，連已 commit 的 `nfr-requirements` 收據一起作廢，害它要重取一次 summary confirmation（多花一個使用者回合）；(3) **`log review --iteration <下一個>` 直接開下一輪 → freeze 立刻解除、零代價**。只要 `reviewer_max_iterations` 還有餘額，(3) 就是唯一該用的。guard 提供的唯一補救（`next --stage <slug>`）在 `Current Stage` ≠ 目標時會解析成 forward jump 並把當前 in-flight 的 stage 標 `[S]`，兩次都不能照做。

## Tradeoffs
- 2026-09-28T11:46:42Z — R-05 是我給使用者的選項描述裡寫了一個假代價（說選 B 會動到 AC9.1.3 的論證，實際上那個數字的範圍只涵蓋既有實體）。已揭露並重新徵詢，使用者維持 A。教訓與 R-03／R-14 同族但更嚴重一級：前兩者是我在產出裡寫錯，這一次是**錯的資訊進了決策選項**，而使用者是拿那個描述在做選擇

- 2026-09-28T11:23:40Z — Q3=A（認不出行動者就讓整個異動失敗）讓一條使用者可見的操作多一個失敗理由，換來的是稽核保證從「可能有一個指錯人的紀錄」變成「要麼有可信的行動者，要麼這次異動根本沒發生」。不選「填擁有者並標記非確證」的理由是它需要多一個欄位，而本單元「新增欄位總數：1」是 AC9.1.3 論證的一部分

<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-27T00:46:33Z — **`G3`（網段分段）是 `G2`（維持明文）的承載前提，不是兩個獨立決定**。`G2`=A 的理由是「信任邊界就是 compose network」；但查證後那個網段是扁平的、而 `cloudflared`（唯一對網際網路持續開著連線的容器）就在上面——**分段之前，那個理由是空的**。兩者必須成對寫進產出，且順序上 `G3` 是 `G2` 可被接受的條件。
- 2026-09-27T00:46:33Z — **`G1`=A（主機層加密）保護的是磁碟層曝露，不保護被攻陷的容器；而 `G2`=A 正是接受後者**。所以「volume 有加密」這句話在本設計裡的保護範圍比一般讀者的預期小，必須在產出裡把兩者的分界寫清楚，否則會被讀成比實際更強的保證。
- 2026-09-27T00:46:33Z — **`G5`=A（全碟加密）選的是「不維護清單」而不是「範圍最小」**。選 B／C 要在 `DEPLOY.md` 維護一張「哪些目錄有加密」的清單，而那張清單每加一個新服務就會漏一項，且本 repo 沒有任何機械閘門會發現漏項。代價已向使用者揭露：對現有主機是一次重裝或資料遷移，且開機解鎖會與斷電後的自動回復產生張力。
- 2026-09-27T01:43:52Z — **D-3 的代價是製造一條沒有閘門的新失敗路徑，而本站必須自己補上驗證**。把既有的 `db` 移進 internal 網段之後，若歸屬打錯、`backend`→`db` 斷掉，現有四道機制一個都不會發現：`deploy.yml:116`／`:131` 兩個 curl 都打 `/` 並由 `frontend/nginx.conf:35–37` 的 `try_files` 回靜態檔，`db` 的 `pg_isready` 在容器內部執行，`depends_on: service_healthy` 只管啟動順序，而 `deploy.yml` 全檔對 `/api` 命中數為 **0**。處置是新增一個穿過 `location /api/` 且會查 Postgres 的探測（`POST /api/auth/login` 帶刻意錯誤憑證、斷言 401——`db.query` 在任何密碼比對之前執行，故 401 是「兩段都通」的唯一結果）。**初版反向宣稱既有閘門已覆蓋**，那正是本 repo 規則層一再警告的形狀。
- 2026-09-27T02:07:10Z — **D-3 的實際效益比我初版宣稱的小，而錯的方向讓它看起來更有效**。user-defined bridge 預設 `enable_icc` 為 true，同網段成員彼此可達全部端口，所以 **D-3 隔離的是 `edge`↔`internal`、不隔離 `internal` 內部**——`db` 被攻陷後仍碰得到 Redis 的全部 session 與零認證的 Ollama。前兩列的真實變化是 **5 → 3**（移除 `frontend` 與 `cloudflared`），不是 4 → 1。**D-3 真正的價值在第三列**：把唯一對網際網路持續開著連線的容器完全移出資料面，3 → 0。要把前兩列壓到 1 需要 `internal` 內部再分段（每個資料面服務各一個網段）或關閉 ICC，兩者皆不在本站範圍，已記為未採用選項。可執行檢查：寫任何「可達性由 N 降到 M」之前，先把網段成員集合列出來實算差集，不要憑「誰依賴誰」推導——依賴關係與可達性是兩件事。
- 2026-09-27T03:05:24Z — **在設計文件裡寫可執行的 shell，本身就是一個缺陷來源；本輪把它整類移除而不是逐個修**。第三輪的六項修正裡有三項（R-24／R-25／R-28）是「我寫的 bash 照抄會壞掉或規格留白」——`code=$(curl …)` 在 `set -euo pipefail` 下第一次失敗即中止整步（實測 `exit=7`、零迭代訊息），而既有兩道檢查沒事只因為它們把 `curl` 放在 `if` 條件位置；`rollback` 的迴圈以 `$GITHUB_OUTPUT` 表達結果、照搬 `exit` 會讓 `:237` 永不執行並讓 Slack 印「結果未知」。stage 檔明文說設計階段產出**不是**可實作的程式碼，而那幾行在 `code-generation` 之前不會被執行、不會被測試——所以它們是零驗證的實作。**處置（使用者裁決）**：抽掉全部 `bash` 區塊，改寫成 `PROBE-CONTRACT` 七條（P-1…P-7），只保留「不寫就一定會踩」的**事實陳述**（`set -e` 對賦值語句的行為、兩個 job 的結果表達機制不同）。可執行判準：設計文件裡出現可直接複製執行的程式碼時，問「它在本階段會被執行嗎」——答案是否，就該改成契約。

## Open questions
- 2026-09-28T11:23:40Z — 加密判定的成立條件是環境性的（db 不對外、與應用同主機），一旦改變即失效，而**沒有任何機制會在條件改變時提醒**。已寫成界線並列入殘餘風險，但這仍是一個結構性缺口——它不是設計錯誤，是這類環境依賴判定的通病
- 2026-09-28T11:23:40Z — S-10 的落點（U5 的 nfr-design）與 S-11 的落點（U12 的 functional-design）都是 CONDITIONAL。兩者若被 skip，OQ-3 的另一半與 OQ-H3 都會失去承接站。已依 R-10 的形狀寫明再提交義務，但本站無法驗證那個指派會被看到

<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-27T00:46:33Z — **ADR-0006 的另兩個面向在本單元幾乎無新增落點，但不是 N/A**。IAM：`NFR4.1` 的 Redis ACL 已承接，確切指令集交給 `U10`；但 **Postgres 至今以單一 superuser（`POSTGRES_USER`）連線、無最小權限拆分**，那是既有基線而非本單元引入，產出裡要如實記載、不得寫成已處置。Audit logging：`NFR8.9` 覆蓋兩個新容器的記錄承載，但 **correlation ID 傳遞在本單元沒有落點**（`observability-design` 對 packaging kind-vacuous），必須指名承接單元。
- 2026-09-27T00:46:33Z — **`G3` 的分段會動到既有的 `db` 服務**，不只是新容器。把 `db` 移到 internal 網段本身零風險（只有 `backend` 連它），但它是對**既有服務**的設定變更，部署時的失敗面比「只加新容器」大。且 `validate_env_contract.py` 只解析環境變數，對 `networks:` 宣告完全無感——這條沒有機械閘門。
- 2026-09-27T01:43:52Z — **`NFR8.8` 的文字與本站設計自此並存矛盾**（它說內部 network 分段「未採用」，本站說要用）。依 `project.md` 不回改已核可上游，靠交叉引用維持可讀性。**承接點**：下一次觸及 `NFR8.8` 的人，或後續的 practices-discovery，應把該段就地標為已被本站反轉。
- 2026-09-27T01:43:52Z — **`project.md ## Mandated` 的 `LOCAL-DEV.md` 同步規則逐字寫 `deploy/nginx.conf`，而該路徑不存在**——實際檔案在 `frontend/nginx.conf`（由 `frontend/Dockerfile` 烘進映像）。這是規則層的路徑誤植，任何依該規則去找檔案的人會找不到。留給後續 practices-discovery 更正。
- 2026-09-27T02:07:10Z — **本站新增兩項需回補進 scope 的工作量**（已寫進 `security-design.md` `§〇`）：`S-6` 把 `/api` 探測加進 `deploy.yml` 的部署後步驟（新的自動回滾觸發條件）、`S-7` `DEPLOY.md` 新增全碟加密前置條件與四個掛載點檢查。兩者都不在 `G1`–`G5` 五題的任何一題裡，`S-6` 的後果已在 `[G6]` 的選項說明中向使用者揭露。承接點為後續的 scope 回補。
- 2026-09-27T02:47:38Z — **R-18…R-23 這六項修正沒有獨立審查覆蓋，這是本單元交付時的已知缺口**。時序是：pass 1 記錄 READY（含六項新發現）→ 我開 pass 2 解 freeze → 完成六項修正 → 再要 pass 3 被拒（`REVIEW_BUDGET_EXHAUSTED`，`reviewer_max_iterations: 2`），而 pass 2 的請求綁定編輯前的位元、`--retry-pending` 明文拒絕 rebaseline。引擎的指示逐字是「Present the unresolved findings at the approval gate for the human instead of starting another review」。**我自己做的驗證**：15 項機械檢查全過、本輪新增引用逐字開檔核對、行號越界 0、三支 sensor 綠、數字實算。**但其中包含 R-18 的修法（Critical 的修正本身）**，而本 session 的實測樣態是修正動作製造缺陷的比率長期在 75%–100%——所以「我自己驗過」在這個 record 的歷史下不等於低風險。此項須在 nfr-design 的 stage 關卡（17 個單元跑完後）明示，且 `infrastructure-design` 與 `code-generation` 都以 `security-design.md` 為 consumes。
- 2026-09-27T03:05:24Z — **R-24…R-28 的修法同樣沒有獨立審查覆蓋**（審查預算在本 attempt 已用完，第四輪是使用者裁決的「未收據驗證」、其產出在 `reviews/unreceipted-verification-01.md`，不是收據）。我自己的驗證：13 項機械檢查全過、五處新增引用逐字開檔（`deploy.yml:114`／`:129`／`:208`／`:237`、`database.py:86`）、`set -e` 行為實測、三支 sensor 綠、`bash` 區塊殘留數 0。**與上一批的差別**：這一批移除的是缺陷的來源（可執行 shell），不是修補四個實例，所以剩下的內容是契約敘述與對既有檔案的事實陳述，缺陷面比上一批小。但這仍是未被第二隻眼睛看過的批次，須在 stage 關卡明示。
- 2026-09-28T03:27:07Z — **上一站留下一個我自己製造的矛盾，本站必須解**：`NFR5.5` 把 `BR1.5`（終止事件兩份 `turnId` 必須相等）的斷言落點寫成「後端模型的 validator」，而 `functional-spec.md:11` 逐字寫本單元「**沒有執行期程式碼**」——Pydantic 的 `model_validator` 是執行期程式碼。兩句話不能同時為真。這不是措辭問題：它決定 `U2` 的交付物裡有沒有會在正式請求路徑上跑的程式。已出成本站的一題。

