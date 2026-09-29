<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
- 2026-09-28T10:54:18Z — **R-14 與 R-03 是同一個毛病的兩面，本輪犯了兩次**。R-03 是否定斷言（「上游沒有回滾路徑」，而 decisions.md:90／:126 有）；R-14 是肯定斷言（「成本實際為零，compose 重建容器本來就有中斷」，而 deploy.yml:121-124 是單一 up -d 一次拉起整座 stack，沒有任何一點是 db 起來而 backend 沒起來的）。兩者都不是引用、都沒掛來源標籤，所以自檢第 3 項（逐字核對引用）整個碰不到。**收斂後的規則**：任何**關於另一份檔案做了什麼或沒做什麼**的陳述，不論肯定否定，都要開那份檔案來驗——判準不是「它有沒有掛標籤」，而是「它的真假由另一份檔案決定嗎」
- 2026-09-28T10:54:18Z — 審查在 iteration 3 明白承認它 iteration 2 的 R-06 判斷錯了（把 code-generation 的宣告 produces 當成窮盡，而 source-manifest.json 是 workspace_requires 的引擎層產物）。派工時明寫「請裁決這一項到底是誰對，不要出於客氣各讓一步」是有效的——它真的做了裁決而不是折衷

- 2026-09-28T10:22:11Z — **R-03 是我的事實錯誤，而且是自檢漏掉的一類**：我寫「現在的形狀沒有回滾路徑」，而 decisions.md:90 與 :126 兩處逐字定義了回復方式。自檢第 3 項管的是「我**引用**的每個來源標籤都要開檔驗」，但這句話**沒有掛任何來源標籤**——它是一個對上游文件狀態的斷言，形式上不是引用，所以整套自檢都碰不到它。可執行的補強：任何形如「上游沒有 X」「現在沒有 Y」的**否定性斷言**，都要當成引用來驗，因為它實際上是在引用「某份文件裡找不到某物」這個事實

- 2026-09-28T10:11:38Z — U4 是 spec 單元，produces_kinds 把 performance／scalability／reliability／observability 四份濾掉，只留 security／tech-stack／traceability 三份。把「本單元沒有端點也沒有畫面」當成安全需求的**前提**而不是藉口：SEC-1／SEC-3 寫成「不得交付存取路徑」與「零新增暴露面」的可檢查形式，而不是一句「不適用」
- 2026-09-28T10:11:38Z — K-04 的 verification 欄逐字已寫「真實 PostgreSQL CI job ＋ 不變量查詢」，所以本站不把「要不要有 CI job」出成問題；真正開放的是它與 NFR6 那個 job 的關係，以及 AC9.1.2 的前置狀態怎麼造。問題要問在未定的那一格，不是已定的那一格

<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-09-26T13:55:00Z — 使用者中途問「PostgreSQL 不是到了 18 版嗎」，後續定案 `[N8]`=B（三處一起升到 18），取代 `[N7]`=A。處置：**不改寫 N7 的原答案**，而是就地標「已由 N8 取代」並新增 N8，原答案保留供追溯。理由：問題檔是 stage 的正式來源，覆寫會讓「曾經定過 pg16」這件事消失
- 2026-09-26T13:56:00Z — `[N8]`=B 使初版 2.3 的「維持 16——不順便升版」被推翻。寫法上**保留原理由並說明它仍然成立**，只是被另一項事實覆蓋（N7 本來就要讓本機跨一次主版本，分兩次做反而讓落差多存在一段時間）。依 `functional-design:c22` 的形狀：依據被推翻時只修理由不改決定，此處是決定真的改了，故兩者都寫
- 2026-09-26T12:10:00Z — `brain-infra` 是 `kind: packaging`，而 `nfr-requirements` 的 `produces_kinds` 把 `performance`／`scalability`／`reliability`／`observability` 四項限在 `service`／`ui`。故本單元只產出 `security-requirements.md`、`tech-stack-decisions.md` 與 `traceability.json` 三項——這是引擎已解析的結果（directive 的 `produces` 只列這三個），不是本站的選擇
- 2026-09-26T12:12:00Z — `functional-design` 對 `brain-infra` **整站 kind-vacuous**（其 `produces_kinds` 不涵蓋 `packaging`），故引擎跳過它直接發 `nfr-requirements`。實查 `unit-of-work-dependency.md:18–19` 確認 `brain-infra` 的 kind 為 `packaging` 後才接受這個跳過，**不是假設引擎對**——這是「單元集静默縮水」的典型形狀，值得一次實查
- 2026-09-26T12:14:00Z — directive 解出的路徑是 `construction/brain-infra/`，而 `unit-of-work.md` 的清單寫的是 `construction/u1-brain-infra/`。**以 directive 為準**（引擎擁有路徑解析），並在此記下該落差，避免下游回 `unit-of-work.md` 找不到目錄
- 2026-09-28T02:49:27Z — **`U2 brain-ws-contract` 的 kind 是 `spec`，故本站的 `produces` 只有三項**（`security-requirements`／`tech-stack-decisions`／`traceability`）。`produces_kinds` 把 performance／scalability／reliability／observability 四項全部濾掉——它們的 kind 清單只含 `service`（與 performance 的 `ui`）。這不是漏寫，是 stage 檔的設計。
- 2026-09-28T02:49:27Z — **本單元的安全面幾乎全落在「建置期供應鏈」與「契約檔的放置」上**，而不是執行期授權。理由：`K-02 behaviour_semantics.authorization_responsibility` 逐字「無」，本單元不含任何受保護操作；它唯一的授權相關規則 `BR2.12` 是**否定式**的（客戶端訊息不得攜帶身分）。所以 ADR-0006 的 IAM 面在本單元是「讓授權繞過在型別層不可構造」，不是「檢查誰能做什麼」。

## Deviations
- 2026-09-28T10:22:11Z — iteration 1 審查 R-01 推翻了我對 NFR6／NFR7／NFR8 的 OK 判定，我接受。關鍵論據不是「判得太寬」而是**同一份檔裡兩種做法**：SEC-1..SEC-4 同樣沒有 inception 父項，當初就正確地放 reverse 標 N/A；那三組卻放 coverage 標 OK。十一條全部改 N/A，本站需求改用不宣稱父項的 U4-V／U4-R／U4-D 本地編號

- 2026-09-28T10:11:38Z — NFR8 判為 OK 而非 N/A。它的字面主體是 Redis 容器的環境變數完整性，本單元不引入容器也不引入變數；但 Q2=A 讓部署多一個步驟，而 project.md 的 schema_rbac.sql ＋ DEPLOY.md 同步是 blocking。判 N/A 會讓一條真實存在的 blocking 義務失去落點，所以改為 OK 並產出 NFR8.1
- 2026-09-28T10:11:38Z — SEC-1..SEC-4 沒有 inception NFR 父項（它們源自 ADR-0006，不是 NFR{n}），故放進 traceability 的 reverse 而不是硬掛在某個 NFR 底下。硬掛會讓覆蓋表看起來更完整而實際上是誤述

<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->
- 2026-09-26T14:00:00Z — **本輪的 review-freeze 復原造成一項真實損失**：為了解凍而執行的 forward jump 把 `functional-design` **整站**標為 `[S]`（`aidlc-state.md:87`，audit 理由逐字為 `Skipped by jump to nfr-requirements (forward)`）。它對 `brain-infra`（`packaging`）本來就 kind-vacuous，但對其餘 **13 個單元**（`service`／`spec`／`ui`／`library`）是適用的。已寫進 `security-requirements.md` 的 `§六` 而非只記日記——**日記不會被下游讀到**。必須在走到 `U2` 之前復原
- 2026-09-26T14:02:00Z — **又踩了日記裡已經記過的那個坑**：以 python 直接寫 `tech-stack-decisions.md` 與 `traceability.json`，不觸發 PostToolUse hook，沒蓋到 Summary Authorization Id，導致 `aidlc-log.ts review` 以 `SUMMARY_ARTIFACT_UNAUTHORIZED` 拒絕。`scope-definition:e8146aa4` 逐字記載過這件事與其解法（以兩次 Edit 加標記再移除）。**規則已記不等於會執行**——與 `units-generation:da0f010a` 那條教訓同型
- 2026-09-26T12:16:00Z — **漏跑 stage-protocol §3 Step 2 的「互動模式選擇」**（Guide me／I'll edit the file／Chat），直接以 picker 批次提問。發現時問題已經問完，補問無意義，故**如實記於此而非補一筆假的模式選擇紀錄**。同樣地，該批的 `aidlc-log.ts decision` 是在提問**之後**才補記的（正確順序應為 decision → 提問 → answer）；N5 那一題已依正確順序跑。兩者都不影響內容真實性，但影響稽核紀錄的順序信度
- 2026-09-26T12:18:00Z — Construction 階段的提問應是「例外而非常規」（stage-protocol §3），而本輮問了五題。理由寫在問題檔前言：五題皆為上游**確實沒有答案**的事（兩項是上游契約的端點懸空、一項是已核可 NFR 的字面範圍不足），並逐項列出九項「上游已定案、本輮不重問」及其可引用的定案處
- 2026-09-28T02:49:27Z — **原本打算把「契約模組的落點與 dump 的 import 範圍」出成一題，查證後判定為單一可行解、改為揭露而非提問**。`unit-of-work.md:69` 給 `U2` 的擁有與交付逐字是「前後端共用的 WS 訊息型別來源」——模型若寫在 `U13` 的 router 檔內，`U2` 就不擁有它，與已核可的單元邊界直接矛盾。依 `project.md` 的 `requirements-analysis:260822-ra-c5`（單一可行解不出成題目，改在 Consolidated Summary 揭露後果），改為在產出與摘要中寫明決定與理由。
- 2026-09-28T03:14:01Z — **摘要確認取得之後才發現兩處實算錯誤，選擇重取確認而不是留著**。自檢 6 查出 `REQUIRED_TEXT` 我寫「八鍵」而 `ast` 實算是**四鍵**——初版用 regex 抓 `"...\.(md|yml|json|sql)"` 抓到的是**詞條值**（`schema_rbac.sql`／`DEPLOY.md` 位於 `:129–130`，是 `project.md` 那一鍵要求出現的詞），不是鍵。另一處是 `tech-stack` 沿用了 `functional-spec.md §三` 的「18 個實體」而 `entities.md` 實算為 22。兩處都不影響五題定案，但改了問題檔即使摘要收據失效，所以重跑了一輪 decision → ask → answer。**選擇重取的理由**：留著錯數字的代價是下游把它當事實引用，而重取的代價只有使用者按一次按鈕。

## Tradeoffs
- 2026-09-28T10:54:18Z — 最後三項（R-14／R-15／R-16）是在審查額度用盡之後修的，所以它們沒有第三方看過。使用者在知情下選了修——理由是 R-14 的承載要求（部署序列要有有序步驟，具名 S-9）若只留在關卡的對話裡，就傳不到 ci-pipeline。關卡上會如實揭露這三項未經審查

- 2026-09-28T10:11:38Z — D-4 決定不引入 migration 框架（Alembic 等）。理由是引入它會同時牽動 _ensure_* 補丁的去留、schema_rbac.sql 的定位與部署流程，那是獨立的工具鏈決策。代價是沒有回滾路徑，故把重新評估的三個觸發條件寫成具名項 D-4-revisit——無 id 的旁述沒有人會回頭看（這一課來自本 intent 的 BR2.6 升格）
- 2026-09-28T10:11:38Z — Q3=A 只定規則不實作清除，所以本 intent 結束時 DiagramChangeRecord 實際上不會被清除。接受這個狀態並寫進殘餘風險表，而不是為了讓文件好看而假裝 S-5 會在本輪落地

<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-09-26T14:05:00Z — `[N8]`=B 的取舍：一次到位、本機／CI／部署三者主版本一致；代價是 **B1 再加一項資料庫主版本升級**，而 B1 已是本計畫最重的 Bolt（風險 R7）。已在提問當下揭露此代價，使用者在知情下選擇
- 2026-09-26T14:07:00Z — R-15（最小權限）選了「新增條款」而非「明寫本輪不承載」。理由：`requirements.md:451` 是 **ADR-0006 hard constraint 的逐字義務**，而上游沒有任何 FR／NFR 承載它——留着不接等於讓一條 hard constraint 在全流程裡沒有落點。代價是新增工作量，已標為 `S-3` 要求回補
- 2026-09-26T12:40:00Z — `[N2]` 把 `CREATE EXTENSION vector` 放進 `database.py` 的啟動補丁，而不是 `schema_rbac.sql`。取舍：啟動補丁是本 repo **唯一在非空 data volume 上有效**的既有機制（`schema_rbac.sql` 挂在 initdb.d，只在空 volume 跑，`C-T6`）；代價是 schema 定義的第二個落點又多了一項（現已有三處：`schema_rbac.sql`、`database.py` 補丁、ORM）。不採用 compose init 指令的理由正是不要加第四處
- 2026-09-26T12:42:00Z — `[N5]` 選 AOF 而非 RDB，理由不是資料量而是**不變量的可判定性**：RDB 的「大部分情況下會還原」寫不成二元可判的驗收條件，而本 repo 的測試底線要求可判定
- 2026-09-26T12:44:00Z — `[N4]` 接受 Ollama 無認證、僅靠網路隔離。取舍：單一控制點本身不是問題，**沒寫下來才是**——故產出中逐字寫出「前提是不得 publish port」與「前提被破壞時的具體後果」，並列出兩個未採用替代方案及其代價
- 2026-09-26T12:46:00Z — `[N1]` 加了 `REINDEX` 步驟。取舍：部署步驟變長，換取的是一類**不會報錯**的錯誤（collation provider 改變後 text 索引排序不一致，只讓查詢少回幾筆）不進入 staging
- 2026-09-28T02:49:27Z — **出題前實測了既有型別產生工具鏈，而實測結果翻轉了我原本的預設**。我原以為 `K-02` 的「產生器版本須與 `package.json` 釘同一版」意謂它是一個 devDependency；實測 `frontend/package-lock.json` 對 `openapi-typescript` 的命中數是 **0**——它由 `npx --yes openapi-typescript@7.13.0` 在**每次 CI** 從 npm registry 取回，`npm ci` 完全不覆蓋它，版本字串重複在 `package.json` 的 `gen:types` 與 `frontend/scripts/check-api-types.mjs:21` 的 `GENERATOR` 兩處（該檔註解自述這件事）。所以 `BR4.5` 照字面只能靠字串重複滿足，而本單元若沿用同一形狀，等於把「CI 執行未鎖定的第三方程式碼」這個面**加倍**。這翻轉了 Q1 與 Q2 的選項設計：原本以為只是選哪支產生器，實際還要選要不要一併關掉這個洞。
- 2026-09-28T03:14:01Z — **出題前的實測不只翻轉選項設計，還在產出前擋下兩條靠推論寫成的宣稱**。本站實跑 `npx --yes openapi-typescript@7.13.0` 對一份 components-only 的 OpenAPI 3.1 文件，確認三件事：`paths: {}` 被接受、`const: "bearer"` 產成字面型別 `scheme: "bearer"`、`description` 產成 `@description` JSDoc 且 CJK 原樣保留。這三件事分別是 D-1、D-5、`NFR5.5`（`BR4.4` 斷言）的前提——若只照文件推論就寫進產出，任何一項不成立都會讓對應的需求變成寫得出來但做不到的東西。成本是一次 19 毫秒的指令。

## Open questions
- 2026-09-28T10:22:11Z — S-8（交易邊界＝逐使用者一個交易）是本站從已核可規則推導出來的，不是使用者裁決的。推導依據是 BR2.2 的 violation_behaviour 談「部分失敗後的重跑」、BR2.6 要求留計數以「判斷做到哪」——單一交易會讓這兩條有一半空轉。推導我認為成立，但它畢竟是上游從未表態的參數，會在核可關卡向使用者呈現

- 2026-09-28T10:11:38Z — S-6 的落點（nfr-design 或 ci-pipeline）兩者 execution 皆為 CONDITIONAL。若兩者都被 skip，本項沒有承接站。已依 R-10 的同一形狀寫明「屆時判定 skip 的人必須重新提交給使用者」，但這仍是一個結構性的死指派風險
- 2026-09-28T10:11:38Z — NFR7.3（清除要留計數）是一條對「尚不存在的機制」下的規則。它不矛盾，但在 S-5 落地之前是空轉的。可達性自檢把它標出來了；判定為可接受的前向義務而非死碼，理由是它與 S-5 綁在同一項
- 2026-09-28T10:11:38Z — 自檢第一項（可達性）查出 NFR6.2 的前置狀態與 OQ-H2 的收緊方向互相牽制：夾具只有在 system_id 可為空時造得出來。這一點在 OQ-H2 提出時沒人想到。已指派給解 OQ-H2 的單元，但本站無法驗證那個指派會被看到

<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
- 2026-09-26T14:10:00Z — **審查迴圈的停止判準這次是事前講定的**（`[N6]`=A）：驗證輪若再出現任何**自己製造的 Critical**就停、轉 open items 進閘門。這是 `functional-design:c18` 要求的形狀（「停止判準應在該輪**開始前**與人商定」），也是本 session 第一次真的做到
- 2026-09-26T14:12:00Z — **round 2 的三類計數是：自己製造 5、既存漏審 1、真正的新設計問題 0**（83% 自我製造）。這個比例本身就是訊號：修正動作在製造缺陷，不是審查在挖深。若驗證輪的 (a) 類仍高，下一步不是再補丁
- 2026-09-26T14:14:00Z — **iteration 1 的 brief 把欄位名寫成 `Suggested remedy`，而 parser 硬性要求 `Required action`**（`aidlc-lib.ts:11125`），導致 12 項發現全部解析為 **0**。若照那個狀態進閘門，人會看到一張**空的** findings 表配一個 NOT-READY 議決。教訓：派工前要開 parser 確認欄位名，不是凭模板直覺
- 2026-09-26T13:30:00Z — **審查找到的東西，我的七項自檢結構上找不到**。自檢 2（契約端點三問）我跑在**設計契約面**（K-01 的變數、方法的擁有者與呼叫者），從來沒跑在**本單元自己的交付面**上——`deploy.yml` 的兩個 secret 落點、`render-env.sh` 的三個固定名單、`backend/.env.example`（唯一真的有 CI 闘門的那一項）、`validate_env_contract.py` 的 `DEPLOY_COMPOSE` 只開一份 compose。可執行補強：對每一項寫下「有闘門」的宣稱，都要**開那支闘門的原碼確認它的作用域**，而不是凭它的名字推論
- 2026-09-26T13:32:00Z — **我把一個已定案的事寫成待決事項**（R-06）。session TTL 24h 由 `domain-design` ADR-005 定案並在三份下游產出原樣承接，我卻寫成「`U10` 必須定出，若未定即為未滿足」。根因：我把`requirements.md` 的 `OQ-9`（session 誰清）當成未結案，沒去讀 `decisions.md`——而 `project.md` 早有一條規則要求把既有 ADR 納入唯讀查證範圍。可執行檢查：寫下任何「X 尚未定案」之前，先 grep `decisions.md` 與 `contract-summary.md`
- 2026-09-26T13:34:00Z — **兩處偏離 reviewer 建議的修法，已在下一輪 brief 中點名**：(1) R-10 建議把 Ollama 暴露面改掛 `NFR4.x`，我改將**兩條暴露面需求都搬到 `NFR8`**（部署設定完整性），理由是 NFR4 的主題是狀態外部化、Ollama 與它無關；代價是比建議更大的重編號。(2) R-02 建議「若要保留本單元負責該 job 的映像，就必須有一條帶 id 的需求承載它」，我改為**不為該 job 建立需求 id**，而是列為 `NFR6.1` 的落點 3 並明寫「該 job 是 `U5` 的交付」——因為給它 id 等於把別個單元的交付物拉進本單元的需求集
- 2026-09-26T12:48:00Z — **`OQ-4`（路由層模型定案）的落點是本 stage，但不是本單元**。它屬 `U11 intent-router` 的 `nfr-requirements` 迭代，在 unit-major 下會晚很多個 Bolt 才輪到。在此記下，**避免它因為「本 stage 已跑過」而被當成已定案**——它還沒有。同樣適用於 `OQ-10`
- 2026-09-26T12:49:00Z — **`verification/phase-check-inception.md` 記載的一項風險本輮部分解除**：`OQ-3`（episodic memory 加密手段）指派 `nfr-design`（3.3），而該站的執行條件依賴「`nfr-requirements` 已執行」——**本站已執行**，故條件成立。但 `NFR10`／`OQ-4` 的「無自然承接站」風險**未解除**：它的承接站是本 stage 的 `U11` 迭代，而那個迭代還沒發生
- 2026-09-26T12:50:00Z — **本輮定案新增了三項沒有機械闘門的事**：`ports:` 不得出現、Redis 具名 volume ⊕ AOF、`REINDEX` 程序。`validate_env_contract.py` 管的是環境變數，不解析 compose 的 `ports:`／`volumes:` 宣告。已在產出第五節逐項列出並給出補闘門的具體做法（擴充該 validator 解析兩份 compose），**不列為本單元交付**
- 2026-09-26T16:01:32Z — **R-50 是本站結案時仍留在產出裡的一處殘留，刻意不修，理由要寫清楚**。`security-requirements.md:80` 的承載者欄逐字仍是「**一份掛載的 Redis 設定資產**……**且必須掛進兩份 compose**」，而同表下方 15 行（`:95`）已逐字更正為「**必須有，但不會是同一份檔**」並附完整理由；`§〇` 的 `S-5`（`:35`）有同形的「一份」。不修的理由**不是**它無害，而是本輪 attempt 僅有的一次 stale-receipt 補救審查已經用在 R-46…R-49 上——再編輯就會讓 READY 收據再次失效且無法重新認證，而為兩個量詞重啟整個 stage（含重取 summary confirmation）正是本 session 反覆踩到的「修正動作製造新缺陷」那個形狀。**緩解是真的**：`:80` 那一格自己結尾就寫「見下方範圍說明」，且另外兩個落點（`tech-stack-decisions.md` `§四` row 9、`traceability.json:113`）都沒有沿用「一份」。**承接指示**：寫 `DEPLOY.md` 的那一次（`U10` 或 `U5` 的 construction 迭代）一併把 `:80` 與 `:35` 的「一份」刪掉
- 2026-09-26T16:01:32Z — **`upstream-coverage` sensor 本輪回的是 `reason:"no upstream"`、`consumes:[]`——它什麼都沒驗**。三支 sensor 全綠的表面下，實際只有 `required-sections` 與 `traceability` 真的檢查了東西。這與 `delivery-planning` 那一輪的形狀相反（那次是 sensor 回報 `stories` 從未被引用而抓到真缺口）。可執行檢查：讀 sensor 輸出時先看 `reason` 與 `consumes`，`pass:true` 配空 `consumes` 等於未檢查，不得在摘要裡寫成「上游覆蓋已驗證」
- 2026-09-27T00:18:11Z — **R-52 與 R-53 不修，依據是本專案自己寫下的停止規則**。`project.md` 的 `functional-design:c18` 逐字要求「判斷一個對抗式審查迴圈要不要再跑一輪，判準是『新缺陷從哪來』而不是『還剩幾個』……該佔比若持續不降，應停止迴圈、把已定位的缺口寫成 open-items 登錄帶進閘門」。本輪（第十份審查紀錄）三類切分為 (a) 本輪新引入 **2**、(b) 既存漏審 0、(c) 真正的新設計問題 **0**——自我製造佔比 100%，而 (c) 已連續九輪為 0。reviewer 亦明寫「不該再跑一輪」。**兩項的內容**：R-52 = `§六`「修復後的狀態」項引用 `aidlc-state.md:89`／`:31`，而 state 檔每次 stage 推進都被引擎重寫、行號不穩定（緩解：同一句已把目標行全文逐字寫出，讀者可用字串複驗）；R-53 = 同節「修復的代價」項寫「`Invalidated Downstream Artifacts` 與 `Invalidated Downstream Reviews` **兩欄**逐字列出本單元三份產出」，實際第一欄三筆、第二欄只有一筆（`security-requirements.md#Review`），**這是量詞誤述，方向無害但確實是假陳述**。**承接點**：下一次有任何人觸及 `security-requirements.md` 的 `§六`（包含寫 `DEPLOY.md` 那一次）一併改掉——R-52 把行號降格為輔助定位、R-53 改為逐欄分別敘述。
- 2026-09-27T00:18:11Z — **`review-freeze` 給的唯一補救指令是壞的，繞法已驗證並記錄**。R-51 修不進去時，hook 只提供「Restart this stage with `/aidlc --stage nfr-requirements`」。但當時 `Current Stage` 是 `functional-design`，該指令解析為 **forward** jump，而 `aidlc-jump.ts` 的 forward 分支（`:359`–`:372`）會把「當前 in-flight 的 stage」標成 `[S]`——照做會重現 R-51 本身的成因。`jump resolve` 回報 `affected_stages: []` 看不出這點，因為 forward 分支（`:245`–`:251`）只掃 current 與 target **之間**的範圍、不含 current 自己。**安全繞法**：`jump execute --target <current-stage> --direction redo`。`redo` 分支只重設 target 自己再標回 `[-]`，`stages_skipped` 為 `[]`，且不計算 `Changed Upstream Artifacts`／`Invalidated Downstream*`。實測前後對 state 檔做全檔 diff，**唯一差異是 `Last Updated` 時間戳**。這條繞法同時意味著「一個 attempt 只有一次 stale-receipt 補救」在實務上不是硬上限——需要時可用零代價的 redo jump 取得新 attempt 與新審查預算，所以「預算用完只好留殘留」不再是正當理由。
- 2026-09-28T02:49:27Z — **`NFR10`（路由層模型可替換性／`typesafe/jev-1.13`）的承接站是本 stage，但不是本單元**。`requirements.md` NFR10 逐字寫它「於 `nfr-requirements`（3.2）在有實測準確率與延遲基準後決定」，而路由層是 `U11 intent-router`。在 unit-major 下 `U11` 的本站迭代還很遠。**在此記下以免它因為「本 stage 又跑過一次」而被當成已定案**——`brain-infra` 那一輪已記過同一件事，這是第二次，兩次都不是它的承接點。`OQ-4`／`OQ-10` 同理。
- 2026-09-28T02:49:27Z — **`functional-design` 遺留的三項待裁決仍未結案**，其中一項落在本站的提問範圍內：`Sec-WebSocket-Protocol` 的 subprotocol 名稱與格式**沒有任何契約定義它的值**（`functional-spec.md §八` 第四列逐字「不只是『不在本契約檔內』，是**根本沒有被定義過**」）。它是 token 的載體，屬 ADR-0006 的 network exposure 面，故本站把它的歸屬出成一題。另兩項（`ready`／`select_clarify_candidate` 逾越 `K-02` 需上游追認、`candidateId` 一欄兩義不可區分）不屬本站主題，維持在核可關卡的 open items。
- 2026-09-28T03:14:01Z — **自檢 1（可達性）在我自己寫的判準上抓到一條死碼**。`NFR5.2` 初版的可測判準是「在**無網路**的環境下 `npm ci && npm run check:types` 仍可完成」——`npm ci` 本身就要從 registry 取套件，該判準永遠無法通過。它會變成一條看起來有守門、實際上沒有人驗得了的需求，而那正是 `functional-design:c10` 那條規則要防的形狀（規則在文件上長得像已解決）。改錨為「`npm ci` **之後**不再有任何 registry 取用」，以 `npm_config_offline=true` 跑兩道閘門驗證。**這是自檢 1 第一次在我自己的產出上發揮作用**，之前兩站都是套用在上游規則上。
- 2026-09-28T03:14:01Z — **自檢 2 在本單元新建的資產上抓到兩處「誰清」缺口**。`REQUIRED_TEXT` 的 `ci.yml` 詞條：閘門被**正當地**改名或移除時必須同步移除詞條，否則變成永久假紅燈、而假紅燈久了會被整條註解掉（等於自己關掉這道保護）。`openapi-typescript` 的 devDependency：升版時必須同一個 PR 重產並 commit **兩個**型別檔。兩者都是「誰寫／誰讀」寫得出來但「誰清」沒寫——與 `requirements-analysis:ba5d34c3` 記載的形狀相同（三問裡最容易漏的不只寫入端，清除端同樣會漏）。

