## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-28T04:12:05Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `security-design.md` §五「與 `BR2.13` 的分工」 | 白名單斷言比對 `ws-contract.json` 每個客戶端 schema 的頂層 `properties` 鍵集合。這在今天成立是因為全部 7 個客戶端物件（已逐一核對 `entities.md`）**全部是扁平物件**——沒有巢狀 sub-object。設計文件本身沒有寫下這個前提；若未來某個 client payload 長出一個巢狀物件（例如一個 `context: {...}` 欄位），而斷言只比對頂層鍵，一個藏在巢狀物件內、叫別的名字的身分等價欄位就會逃過這道「由構造封閉」的保護——正是 ADR 在 Alternatives Rejected 表中判定「維持禁用名單」不可取的那個理由（叫別的名字的身分欄位仍然通得過），只是換了一層。 | 在 `security-design.md` §五或 `dump_ws_contract.py` 的判定式旁明寫這個前提（「本判定式僅比對頂層鍵；巢狀物件需遞迴或明確排除」），讓下一個新增巢狀 client payload 的人知道要重新檢查這道閘門是否仍然涵蓋得到。 | New |
| R-02 | Minor | `nfr-design-questions.md`「一處必須揭露的紀錄瑕疵」與 audit shard `QUESTION_ANSWERED`（`2026-09-28T03:56:07Z`） | 已獨立核對：本輪 `QUESTION_ANSWERED` 事件把 Q1 記成 `A`，但問題檔的內容敘述與最終定案都正確指向 `B`；補記該筆的 `aidlc-log answer` 呼叫因「無新人工回合」被引擎拒絕（`ERROR_LOGGED`，`2026-09-28T03:56:29Z`），且 Consolidated Summary Confirmation 的時間戳（`04:01:03Z`）晚於問題檔就地更正完成的時間（`03:57:22Z`），故人工是在看到更正後的內容下確認的——這個處置是恰當的，且完全誠實揭露、可稽核。唯一殘餘：這個更正目前**只存在於問題檔的一段散文**裡；一個只讀 audit shard（不交叉核對問題檔）的未來讀者，或任何只掃 `QUESTION_ANSWERED` 事件做自動化統計的工具，會把 Q1 永久讀成 `A`。 | 非阻擋；建議在 `traceability.json` 的某個 `reverse` 條目或 ADR 的「觸發來源」段落也交叉引用一次這個更正（例如加一句「`nfr-design` 的 `QUESTION_ANSWERED` 事件把 Q1 誤記為 A，現行定案為 B，見問題檔就地更正」），讓依賴 audit shard 而非問題檔的下游工具也有機會發現。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `required-sections`（人工以 `aidlc-sensor-required-sections.ts --stage nfr-design --output-path security-design.md` 重跑） | `pass:true, h2_count:11` | 11 個 H2 與檔內 `grep "^## "` 逐字核對一致，非空洞通過 |
| `traceability`（`aidlc-sensor-traceability.ts --stage nfr-design --output-path traceability.json`） | `pass:true, gaps:[], orphans:[], missing_from_table:[], missing_from_upstream_ids:[]` | 7 個 `NFR5.x` 全數在 `coverage` 有對應項、無孤兒、無缺口 |
| `upstream-coverage`（naive：`--stage nfr-design --output-path security-design.md`，不帶 `--consumes`） | `pass:true, consumes:[], reason:"no upstream"` | **這正是 dispatch brief 警告的陷阱**：不帶 `--consumes` 時腳本什麼都沒驗證，`pass:true` 只代表「沒有東西可查」，不得讀成「上游覆蓋已驗證」 |
| `upstream-coverage`（補上 stage-graph.json 宣告的 required consumes：`security-requirements:nfr-requirements,tech-stack-decisions:nfr-requirements,functional-spec:functional-design`） | `pass:true, consumes:[3 項], unreferenced:[]` | 補上正確參數後才是真的驗證：`security-design.md` 對三項必要上游全數有指名引用，`unreferenced` 為空 |
| `python3 scripts/validate_repo_contract.py` | 全綠（"validation passed"） | 本站產出（含新 ADR）未違反 repo contract |
| `python3 scripts/validate_env_contract.py` | 全綠（"validation passed"） | 本站產出未涉及環境設定，符合預期 |
| ESLint 選擇器實測（獨立 `no-restricted-syntax` 規則套用設計文件逐字給的 selector，對照 3 種輸入：模板字面量、字串字面量、變數） | 模板字面量與字串字面量各觸發 1 個 error；變數形式與無第二引數皆不觸發 | 與設計文件 §三 逐字聲稱的行為（含「擋不住存進變數再傳入」的殘餘）完全一致，非裝飾性設計 |
| `grep -rn "new WebSocket" frontend/src/` | 2 hits：`useCollaboration.ts:25`（無第二引數）、`BrainPage.tsx:83`（`` [`bearer.${token}`] ``） | 與 claim 1 逐字相符 |
| `entities.md` 客戶端物件計數 | `WsClientEnvelope` ＋ 6 個 client payload（`Hello/UserMessage/SelectClarifyCandidate/CorrectWorkItem/SetSharingMode/SetWorkTarget`） | 與 claim 2（7 個）相符，且與 `rules.md BR2.12 applies_to: 全部 client→server payload` 及 `BR2.13 applies_to: WsClientEnvelope 與六個 client payload` 的宣告口徑一致 |
| ADR 編號全域掃描（`find .../decisions/*.md`） | 既有最大為 `0018`（`260916-estimate-upload-rework`），`0019` 未被占用 | 與 claim 3 相符；歷史上的 `0013`／`0014` 撞號未再重演 |
| `frontend/package.json` 的 `"lint"` 腳本 | `"eslint ."`，無 `--max-warnings 0` | 與 claim 4 相符，`error` 級要求是必要的，非過度設計 |
| `functional-spec.md:11` 與 `unit-of-work.md:69` 逐字核對 | 前者：「沒有執行期程式碼」；後者：「型別來源 ＋ 一道 CI 檢查」 | 與 claim 5 相符；§四對此矛盾的揭露與更正處置（不回改上游、明列 S-5）符合 `project.md`／`team.md` 既有的處置慣例（`refined-mockups:c3` 等） |
| R-01/R-02（上一站兩項 Minor）逐字核對 | `nfr-requirements/reviews/review-01.md` 的 R-01、R-02 內容與本站聲稱的處置一致；`tech-stack-decisions.md` 的 audit 寫入時間戳（最後一次 `03:12:09Z`）早於其審查時間（`03:19:46Z`），本站期間（`03:2x`起）對該檔無任何 `ARTIFACT_UPDATED` | 兩項 Minor 的處置聲稱皆屬實：R-01 由白名單整個取代（非僅收斂清單）；R-02 以分層論證處置、確認未回改上游檔案 |
| 逐頁核對 §二 ADR-0006 四面向表 ＋ PBT 判定 | 四面向皆「適用」並各附具體設計解；PBT 判定「不適用」並引用 `rules.md` 的 `category: calculation` 實際計數（人工複算為 0，與宣稱一致） | 符合 `project.md` 自檢第七項（逐項對照 ADR-0006 四面向 ＋ PBT hard constraint，且說理由） |

### Summary

三類計數：(a) 本站新增的問題 — 0；(b) 既存但先前未被抓到、本輪才發現 — 2（R-01 白名單的扁平物件前提未明寫；R-02 audit shard 的 Q1 誤記僅單點揭露）；(c) 真正新的設計缺陷 — 0。

本站的六項可驗證主張（`new WebSocket` 命中數、client payload 計數、ADR 編號無衝突、ESLint 腳本無 `--max-warnings`、`functional-spec.md`／`unit-of-work.md` 的字面範圍、ESLint selector 的實際匹配行為）逐一獨立複驗，全部屬實，沒有一項是誇大或裝飾性的宣稱。上一站兩項 Minor 的處置（R-01 用白名單整個取代禁用名單、R-02 以分層論證且未回改上游）均查證屬實。`traceability.json` 的 7 項 `NFR5.x` 覆蓋在人工重讀設計內容後確認是真的設計解而非需求的同義轉述（尤其 `NFR5.5`／`NFR5.7` 給出了具體機制、失敗語意與代價），`NFR5.1/5.2/5.3/5.6` 誠實標註「承接上一站」而非冒稱本站新解。ADR-0019 具備 Context/Decision/Consequences/Alternatives Rejected 四段，與 `nfr-requirements`、`contract-design` 的 `K-02`／`K-12` 無矛盾，且經查證確實未與既有 ADR 編號衝突。兩項 Minor 均為「可以更好但不阻擋」層級：白名單機制對扁平物件之外的情形缺乏書面前提聲明、以及 Q1 記錄更正目前只有單點揭露而非跨檔交叉引用；兩者皆不影響本站設計本身的正確性或可實作性。
