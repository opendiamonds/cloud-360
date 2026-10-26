## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-10T00:45:37Z
**Iteration:** 1
**Review class:** advisory（單輪，兩種 verdict 皆為終局；本審查為決策支援，不擋閘門）

**覆蓋聲明：** 七個受審檔（`security-design.md`、`performance-design.md`、
`scalability-design.md`、`reliability-design.md`、`observability-design.md`、
`logical-components.md`、`traceability.json`）與 `nfr-design-questions.md` 皆已
開檔逐字核對。必讀上游（`nfr-requirements/` 六檔含其 `reviews/review-01.md`／
`review-02.md`、`functional-design/entities.md`／`rules.md`、
`contract-summary.md` 的 `K-02`／`K-08`／`K-09`／`K-10`、`requirements.md` 的
`NFR1`–`NFR11`、`FR5.1`）已讀。repo 實碼對照：`backend/services/langgraph_runtime.py`
（`:71`／`:75`／`:95`／`:16`）、`backend/cost/advice_orchestrator.py`（`:1`–`:25`，
確認 `ThreadPoolExecutor` 同進程）、`backend/services/memory_facade.py`（`:258`–`:291`，
`search` 簽章）、`backend/services/memory_router.py`（`:158`–`:183`，`create_memory`）、
`backend/cost/cost_advice_agent.py`（`:135`–`:165`）、`aidlc/spaces/default/memory/team.md`
的命名慣例段。對照組（`session-store`、`memory-service` 的 `nfr-design/`）僅瀏覽
目錄結構以確認 ID 帶位未撞號，未逐字精讀其設計內容——此為**部分覆蓋**，記於此。
機械 sensor（`traceability`、`upstream-coverage`、`required-sections` 六檔）已
獨立重跑，結果見下方表格。深度為 full（除對照組一項為 skimmed）。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | `logical-components.md` §一（Mermaid `:32`「`CTX -.讀該段歷程與作業對象.-> U10`」與其文字 fallback `:39`「**唯讀**地從 `U10` 取該段的作業對象與歷程、從 `U8` 經 `MemoryFacade` 取語意／程序記憶」）**對照** §二 的表格（`:52`「L2 context-builder \| **純函式**（取得資料的 I/O 在它之外） \| 無（接收已取得的資料）」）與 `:62`「**L2 的純度是刻意設計的**：取資料的 I/O 放在它之外（呼叫端先取好再傳進來）」 | **同一份檔案內，§一（圖＋文字 fallback）與§二（表格＋說明）對 L2 是否做 I/O 給出相反答案。** §一的圖把「讀 `U10`」「`search` `U8`」兩條邊的起點畫在 `CTX`（L2）節點本身，文字 fallback 逐字說「**L2 context-builder，它是純函式，唯讀地從 U10 取…從 U8…取**」——即 L2 自己執行 I/O。§二的表格與其下方的說明卻明白宣稱 L2「外部依賴：無（接收已取得的資料）」、I/O 由「呼叫端先取好再傳進來」。兩者對「誰呼叫 `SessionStore`／`MemoryFacade.search`」給出互斥答案。**可構造的失敗情境**：`code-generation` 若信 §二，會把 I/O 呼叫寫在 L1/某個外層函式、讓 L2 的函式簽章只接收已取資料，測試照 §二「不需要 mock」的承諾直接測；若信 §一與其 fallback，L2 內部會直呼 `SessionStore`／`MemoryFacade`，測試必須 mock 兩個依賴——兩種實作在單元邊界、可測性、`BR6.1`「最少上下文」能否用無 mock 測試驗證（§二自己給的理由）上完全不同，而本檔沒有給出任何判準告訴實作者該信哪一份 | 二者擇一並刪除另一份矛盾陳述：若維持「L2 純函式、I/O 在外層」（與§二測試策略一致），改寫§一的圖與 fallback，加一個顯式的 I/O 層節點（例如 `L0 fetch` 或把讀取動作畫在 `GUARD`/`classify` 入口）把邊的起點改過去；若維持「L2 自己做 I/O」（與圖一致），改寫§二的表格與說明為「不純（I/O：讀 `U10`、`search` `U8`）」，並說明 `BR6.1` 的測試改用替身而非無 mock 直接測 | New |
| R-02 | Major | `logical-components.md` §三（`:88`-`:89`：「降級必須被觀測（`observability-design.md` 的 `RoutingObservation` 需加一個 `memory_degraded: bool`）」）對照 `security-design.md` §二 SEC-3 的 `RoutingObservation` 定義（`:66`-`:76`）與 `observability-design.md` §一的同一定義（`:9`-`:19`） | **本站自己要求的補救欄位，在本站自己寫的兩份權威定義裡都不存在。** `grep -c memory_degraded` 全站僅 1 處命中（`logical-components.md:89` 的要求句），`security-design.md` 與 `observability-design.md` 各自宣告的 `RoutingObservation` dataclass（兩者欄位集合逐字相同：`turn_id`／`slot_count`／`capability_ranks`／`scores_available`／`can_single_out`／`elapsed_ms`／`error_kind`）都沒有這個欄位。D-1（`U8` 不可用時降級而非失敗）是本檔**唯一**偏離「一律大聲失敗」的判斷，而它的正當性建立在「降級必須可觀測，否則會變成無聲的長期降級」這個單一條件上——這正是本 intent 已記過的 `N8N_USER` 失敗形狀。**可構造的失敗情境**：`code-generation` 直接照抄 §二／§一的 `RoutingObservation` 定義（兩份都寫得像是定案的程式碼），不會發現還要加欄位；`U8` 真的長期降級時，`observability-design.md` §二列的五個訊號裡沒有一個能回答「記憶多久沒取到過」，降級就真的變成無聲的 | 在 `security-design.md` 與 `observability-design.md` 的 `RoutingObservation` dataclass 都補上 `memory_degraded: bool` 欄位（SEC-3/SEC-5 白名單需同步納入），並在 `observability-design.md` §二的訊號表新增一列（記憶降級率／連續降級次數），否則 D-1 的正當性論證沒有落地 | New |
| R-03 | Major | `logical-components.md` §三（`:75`-`:93`，D-1 的完整論證）對照 `functional-design/rules.md` 的 `BR5.5.residual_gap`（「語意記憶…『用記憶理解術語』與『用記憶決定 referent』在**模型內部不可區分**…決定不加機制是可以的，不追蹤它不行」） | **D-1 的論證只處理「要不要失敗」，沒有處理「降級會不會悄悄改變答案」——而這正是我自己要求重點打的那一處。** D-1 把記憶定性為「加分項」，理由是 `BR5.1` 只讀 `SessionContext`；但 `BR5.5.residual_gap` 自己承認，模型在**實際生成** `capability`／`referent` 時，「理解術語」與「決定指涉」這兩件事無法在模型內部切開。這意味著：有記憶時，模型可能（經由術語理解）把某個候選的信心推高、使 `can_single_out` 為真並選定一個特定答案；記憶降級後，同一句話可能得到一個**不同但同樣自信**的答案——而不是如 D-1 隱含假設的那樣退化成「更常反問」。D-1 只設計了觀測（且如 R-02 所述連觀測欄位都沒補上），沒有設計任何**功能性**的保險（例如：記憶降級時提高內部門檻、或強制該輪的 `capability` 判定走保守路徑）。**可構造的失敗情境**：使用者兩次問同一句含術語的話，一次 `U8` 正常、一次降級，系統給出兩個不同的 `capability` 判定且兩次都顯示為「成功交辦」而非反問——使用者毫無線索這是因為記憶服務不穩定 | 在 D-1 補一句功能性邊界：記憶降級時，若 `scoresAvailable` 分支的分數差距在某個邊界內（原本就該觸發反問），不得因為記憶缺失而被模型「補齊」成一個確定答案——需要這一條，或至少把「這是未解決的殘留風險」明寫進殘留缺口表（§三的既有表格只收了「語意記憶仍可能載有產出物名稱」與「同進程呼叫者身分真偽」兩項，沒有「記憶降級改變分類結果」這一項） | New |
| R-04 | Major | `performance-design.md` §三（`:57`：「超過上界即走 `BR2.4` 的失敗路徑（分類失敗），不是截斷」）對照 `reliability-design.md` §二 V-3 的表格列（`:32`：「`slot` 自 0 連續、最大值 ≤ 3（即 ≤ 4 槽位） \| `MalformedRouting`」）與 `functional-design/rules.md` 的 `BR2.4` 定義（`statement: "分類器回空候選清單是失敗，不是「判不出來」"`，`trigger: "分類回傳"`，`logic: "IF candidates 為空 THEN..."`） | **同一個檢查點（槽位數超過 4）被兩份本站自己的檔案指派了兩個不同的失敗型別。** `performance-design.md` 明寫「走 `BR2.4` 的失敗路徑」，但 `BR2.4` 逐字定義是「`candidates` **為空**」才觸發——與「`slot` 超出上界」是完全不同的條件。`reliability-design.md` 的 V-3 自己把同一個違規正確分類為 `MalformedRouting`（不是 `EmptyCandidates`／`BR2.4`）。`reliability-design.md` §一已經強調「四個型別、一種使用者體驗，但維運必須分得出來……混成一個 `RoutingError` 會讓這兩件事在圖表上長得一樣」，而 `NFR3.74` 要求按型別分計失敗率——這正是本檔反覆強調的設計主軸。**可構造的失敗情境**：`code-generation` 若依 `performance-design.md` 的字面把槽位超界實作成丟 `EmptyCandidates`（`BR2.4` 對應的型別），`observability-design.md` 的「失敗率（按型別）」訊號會把「供應商吐出一個失控的大槽位數」與「供應商真的吐空清單」計進同一條曲線，直接違反本檔自己在別處堅持的分型原則 | 把 `performance-design.md` §三的「走 `BR2.4` 的失敗路徑」改為「走 `MalformedRouting` 的失敗路徑（`reliability-design.md` §二 V-3）」，移除對 `BR2.4` 的誤引 | New |
| R-05 | Major | `performance-design.md` §二 P-4（`:35`：「這不違反 `NFR3.67`——它禁的是可變狀態，連線池是不可變的基礎設施 handle」）與 `scalability-design.md` S-2（`:16`）對照 `nfr-requirements/scalability-requirements.md:26`（「`NFR3.67` 本單元**不得**引入行程內的共享可變狀態（**快取、計數器、連線池**）作為擴展手段」） | **上游需求把「連線池」與「快取」「計數器」並列為三個被明文禁止的範例，而本站用一句自己的論證把其中一個範例判定為不算違反——卻沒有回頭修正或標注上游這條需求。** `scalability-requirements.md:26` 的括號是三個**同等地位**的例子，不是「快取、計數器之類」的模糊措辭。本站的理由（「連線池不持有語意狀態，是基礎設施 handle」）是一個合理的工程判斷，但它與上游的字面直接衝突，而本 intent 在同一個單元的上一站（`nfr-requirements` 的 `R-04`）剛好因為同一條 `NFR3.67` 的誤讀被抓過一次——這次的形狀是反過來：**不是誤讀禁令範圍過寬，而是解釋掉一個被明文列出的禁止項**。`project.md` 已記過「下游修正上游已核可 artifact 的內部瑕疵時，必須在本站 artifact 明記『這是對齊修正、非本站新定案』並說明原瑕疵」——本站沒有這麼做，只是在下游給了一個新論證，上游的禁止清單原樣不動。**可構造的失敗情境**：下一個讀 `scalability-requirements.md:26` 而沒讀 `performance-design.md` P-4 的人（例如 `infrastructure-design` 或日後的稽核），會依字面判定本單元的 client factory 違反 `NFR3.67` | 回 `nfr-requirements/scalability-requirements.md:26`，把「連線池」從禁止例子中移除或加註「僅指持有跨請求語意狀態的連線池，不含單純的連線重用/keep-alive」，並依 `project.md` 的既有規則標注這是下游（`nfr-design`）發現並對齊修正的上游瑕疵；不得只在 `nfr-design` 單方面解釋掉一個上游的明文例子 | New |
| R-06 | Major | `reliability-design.md` §二（`:25`：「扁平 schema 把兩層的還原放在我方，所以**驗證也在我方**。五道，**缺一則 `EC6`–`EC8` 不成立**」）對照 V-1～V-5 的表格內容（`:30`-`:34`）與 `entities.md` 的 `EC8`（「`candidates` 的來源規則……`ClarifyCandidate.label` 必須寫出它屬於哪一件事」） | **V-1～V-5 驗證的是 Jev 回來的原始輸入（扁平 `candidates[]`＋`slot`），`EC8` 約束的是另一個完全不同的輸出構造步驟（`below_threshold` 為真時，把所有不可單選槽位的候選攤平成 `IntentDecision.candidates` 並要求 `label` 帶出處）——五道驗證裡沒有一條檢查這件事。** 逐條核對：V-1 檢查 `candidates` 非空、V-2 檢查 `capability` 列舉、V-3 檢查 `slot` 連續性與上界、V-4 檢查組內 `rank`、V-5 檢查分數全有全無——全部作用於**輸入解析**（§二標題自己寫「`[D1]`=A 的直接後果」，指的是解析 Jev 回應這一步），沒有一條觸及**多槽位攤平成使用者看到的候選清單時 `label` 是否帶出處**這個構造邏輯。`EC8` 的依據（`entities.md`）本身也承認這條規則故意不改 `K-10`，必須「在既有形狀內解決」——但「在既有形狀內解決」具體怎麼做（例如：L5 在攤平時用程式**附加**槽位描述到 `label` 前綴，還是要求 prompt 指示模型自己把任務描述寫進 `label`）本站完全沒有設計，只是宣稱五道驗證「缺一則不成立」。**可構造的失敗情境**：使用者一句話含兩個不可單選的意圖，`code-generation` 依本檔字面以為 V-1～V-5 全部通過就代表 `EC8` 已滿足，於是把兩組候選直接攤平不加任何來源標記，使用者在反問畫面上看到 4 個候選卻看不出哪兩個是同一件事、哪兩個是另一件事 | 在 `reliability-design.md` §二新增一條設計決定（不必是「V-6」，因為它不是輸入驗證），明確指派 L5 或攤平邏輯必須對每個攤平後的 `ClarifyCandidate.label` **以程式方式**前綴或附加它所屬槽位的任務描述（而不是依賴模型在生成 `label` 時自動做到），並刪除或改寫「缺一則 `EC6`–`EC8` 不成立」這句過度宣稱 | New |
| R-07 | Minor | `traceability.json` 的 `coverage` 陣列（`NFR4.60`／`NFR4.65`／`NFR7.60` 三列皆 `status: "N/A"`，`:228`-`:244`）對照 `nfr-requirements/observability-requirements.md:27`（「**修訂 1（審查 `R-03`）：原編號 `NFR7.63`**，因 `NFR7` 的字面是 episodic 的保存與刪除稽核……已改為孤兒 ID」） | **同一次改號（`security-requirements.md` 審查 `R-03`：`NFR7.60`／`.61`／`.63` → `SEC-3`／`SEC-4`／`SEC-5`）產生了三個歷史 ID，本檔的 N/A 清單只處理了其中一個（`NFR7.60`）。** `NFR7.63` 以完整型式出現在 `observability-requirements.md:27`（`NFR7.61` 只以縮寫「`.61`」出現，從未以完整字串形式單獨出現，故不會被任何逐字掃描工具當成一個獨立 ID），與 `NFR4.60`／`NFR4.65` 的處置形狀（「它仍出現在上游檔案裡，是刻意的修訂紀錄，不是殘留」）完全相同，卻沒有被同樣列為 N/A。這正是本站自己在 `traceability.json:231` 說的理由：「sensor 看得到檔案裡的 ID，分不出『本單元定義的』與『修訂紀錄提到的』」——這個理由同樣適用於 `NFR7.63`，而本檔沒有把它收進來 | 在 `traceability.json` 的 `coverage` 陣列新增一列 `NFR7.63`，`status: "N/A"`，`target` 與 `note` 比照 `NFR7.60` 的處置（指向 `observability-requirements.md:27` 的改號紀錄） | New |
| R-08 | Minor | `nfr-design-questions.md` `[D1]` 的 D-2 新定（`performance-design.md` §三：`len(slots)` 上界 4，依據「`FR5.1` 的官方例子是 2 個意圖」） | **上界 4 是本站單方面定案的數字，依據是把官方唯一例子（2）乘以一個沒有寫明的安全係數，而它的失敗後果（整輪失敗，不是降級）對使用者體驗有真實影響。** 本站把 D-1（扁平 schema 形狀）正確地升級為使用者問題（`[D1]` 經 `AskUserQuestion` 取得人工確認），但同屬「選錯會在 code-generation 才爆出來」性質的 D-2（上界取多少）卻放進「本站自行定案、不提問」清單，沒有給使用者任何選項。使用者一句話列五件事並不難想像（例如「幫我把這五個系統都加上監控、備份、擴容、告警跟成本分析」），屆時使用者得到的不是部分成功也不是反問，而是整輪失敗，且沒有任何上游文件對「5 個意圖該怎麼辦」表達過意見 | 在 `nfr-design-questions.md` 補記選擇 4（而非 3 或 6）的具體權衡：寫明「超界即整輪失敗」這個 UX 代價已向使用者揭露，或改列為**待 `code-generation`／`build-and-test` 以真實使用型態覆核的交接事項**（而不是視為已定案的數字），比照 `D-3`／`D-4` 的交接事項格式 | New |
| R-09 | Minor | `reliability-design.md` §四（`:57`：「**設計決定：不建獨立健康檢查端點，理由是它會說謊。**」） | **給出的理由是次要理由，而真正、結構性的理由（`SEC-2`：本單元不建 `APIRouter`、不暴露任何端點）沒有被引用。** `security-design.md` §二 `SEC-2` 逐字「模組不建立 `APIRouter`，不被 `main.py` `include_router`」——這代表本單元**在架構上從來沒有「要不要建健康檢查端點」這個選項**：建端點本身就違反 `SEC-2`。本檔用一個品質論證（「它會說謊」）去解釋一件其實是被另一條更早的設計決定結構性排除的事，讀起來像是經過權衡後拒絕了一個真實可行的選項，但實際上那個選項從一開始就不存在。這不影響結論，但會誤導審視這份文件的人以為「不建健康檢查」是本檔權衡的結果，而不是 `SEC-2` 的直接推論 | 在 §四補一句：「本單元無獨立端點（`SEC-2`），故健康檢查端點本來就不是一個可選項；『它會說謊』是補充說明為什麼即使不受此限也不會建它，不是唯一理由」 | New |
| R-10 | Minor | `security-design.md` §二 `SEC-1` 的可執行檢查（`:44`：`src = Path("backend/services/intent_router.py").read_text()`） | **這個模組路徑在本站之外任何上游產出（`domain-design`／`contract-design`／`functional-design`）都未出現過，而 `_router.py` 這個字尾在 `team.md` 的既成命名慣例裡專指「建立 `APIRouter` 並被 `main.py` include」的 HTTP 路由模組**——而本單元 `SEC-2` 明寫它**沒有** `APIRouter`。用 `_router.py` 字尾命名一個刻意無端點的模組，與既有慣例所暗示的意思相反，容易讓日後維護者誤判它是一個 HTTP 路由檔 | 若 `code-generation` 尚未定案實際檔名，在本檔加註「檔名為暫定範例，實際路徑由 `code-generation` 決定；若沿用 `_router.py` 字尾，須在模組頂部註明『非 HTTP router，無 `APIRouter`』以避免與既有命名慣例混淆」 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `aidlc-sensor-traceability.ts --stage nfr-design --output-path <traceability.json>` | 獨立重跑：`pass:true, findings_count:0` | 與作者自報一致；但本審查的 R-07 顯示該 sensor 只驗內部一致性（宣告的 `upstream_ids` 與 `coverage`/`reverse` 的格式），看不到「某個曾存在過的 ID 字串在上游語料裡還有一個未被登記為 N/A 的歷史引用」這種跨檔案文字掃描缺口 |
| `aidlc-sensor-upstream-coverage.ts`（`--deliverables` 六個產出檔，`--consumes` 八個上游 slug） | 獨立重跑：`pass:true, unreferenced:[]` | 與作者自報一致 |
| `aidlc-sensor-required-sections.ts`（六個產出檔逐一跑） | 全部 `pass:true, h2_count:5, findings_count:0` | 與作者自報一致 |
| `grep -roE "\b(NFR[0-9]+\.[0-9]+\|SEC-[0-9]+)\b"` 全量枚舉 `nfr-requirements/*.md`（排除 `reviews/`），與 `traceability.json` 的 `upstream_ids`（34 項）比對 | 多出 `NFR7.63`（完整字串出現於 `observability-requirements.md:27`，不在 `upstream_ids` 清單、也不在 `coverage` 的 N/A 列表） | 證實 R-07；`NFR7.61` 僅以縮寫形式出現，未形成獨立可枚舉字串，故不構成同型缺口 |
| `backend/cost/advice_orchestrator.py:1-25` 實讀 | `ThreadPoolExecutor`（`_MAX_WORKERS = 2`）＋ module-level `_progress` dict，**同一 Python 行程內的執行緒**，非獨立部署單位或外部服務 | **驗證通過，支持設計**：`observability-design.md` §三「本 intent 的呼叫鏈是同進程的四跳」對 C1 這一跳的宣稱成立，C1 的 `invoke` 確實在 backend 同一行程的執行緒內發生，不經跨行程呼叫；brief 第 5 項的疑慮在 C1 這一跳上未成立 |
| `backend/services/langgraph_runtime.py:71/:75/:95/:16`、`memory_facade.py:258-291`、`memory_router.py:158-183` 實讀 | 與 `security-design.md`／`performance-design.md`／`nfr-design-questions.md` 的逐字引用一致，`temperature: float = 0.0` 的無條件傳遞與 `facade.search`／`facade.write` 簽章皆如本站所述 | 本站對 repo 既有碼的引用未發現錯誤定位或錯誤內容 |
| 全檔程式片段行數計數（6 個檔共 5 個程式區塊） | 全部 ≤ 11 行內容行，無超過 15 行限制 | 符合 stage 檔的設計階段程式片段上界 |

### Summary

**發現分類計數**：新引入 0、既存漏審 0、新設計問題 10（R-01～R-10；全部是本站自己
在產出中造成或遺留的缺口，上游的六項 `nfr-requirements` 審查發現皆已逐一妥善收斂，
未發現殘留）。**Critical 2、Major 4、Minor 4。**

本站承接的上游（`nfr-requirements`）六項發現（ID 碰撞、`NFR7.62` 可達性、`NFR7`
親代歸屬、斷路器論證、預算歸因缺口、金鑰前置條件）皆已核實妥善處置，查無殘留——
這部分的查證紀律值得肯定。但本站自己新產出的六份設計文件之間出現了**三種**值得
注意的失誤形狀：(1) **同一份檔案內部自相矛盾**（R-01：§一的圖與 fallback 說 L2
做 I/O，§二的表格說它不做）；(2) **本站自己要求的補救措施沒有落地到本站自己寫的
型別定義裡**（R-02：`memory_degraded` 欄位被要求存在，但兩份權威定義都沒有它）；
(3) **跨檔案的失敗型別歸因錯誤**（R-04：`performance-design.md` 把槽位超界錯誤
歸給 `BR2.4`，與 `reliability-design.md` 自己的分類表矛盾）。這三者都是 `project.md`
已記過的「跨檔傳播」「同份檔內自相矛盾」失誤家族的新實例，且都發生在同一輪、
同一位作者寫的六份檔案之間——說明送審前的自檢沒有覆蓋「本站自己新增的決定
（D-1／D-2／`EC6`–`EC8` 的驗證聲稱）是否在本站自己的其他檔案裡被正確落實」
這一類交叉檢查。brief 要求特別用力打的兩項（item 1 的 `U8` 降級與 item 5 的
同進程假設）：item 5 經 repo 實讀驗證**成立**（C1 確實同進程）；item 1 經查
**部分不成立**——D-1 本身的失敗分類判斷（記憶是加分項）站得住，但它賴以成立的
觀測安全網（R-02／R-03）並未落地，使「降級不會悄悄改變答案」這句話目前只是
宣稱，沒有機制。

VERDICT: NOT-READY
