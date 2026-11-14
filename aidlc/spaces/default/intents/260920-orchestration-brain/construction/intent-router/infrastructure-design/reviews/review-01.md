## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-10T01:58:23Z
**Iteration:** 1
**review_class:** advisory（本輪為單輪終局，verdict 僅供人工在關卡權衡，非自動擋關）
**覆蓋聲明：** 四個受審產出逐檔讀過（`cicd-pipeline.md`／`infrastructure-specification.md`／`monitoring-design.md`／`traceability.json`）；上游三站（`functional-design`／`nfr-requirements`／`nfr-design`）及其 `reviews/review-01.md` 已讀；`ci.yml`／`deploy.yml`／`render-env.sh`／`docker-compose.deploy.yml`／`build-and-test.md`／`langgraph_runtime.py` 等 repo 實檔已逐一 `grep`／`sed -n` 核對，非轉引。對照組 `brain-infra`／`session-store` 的 `infrastructure-design` 已讀其 `traceability.json`。深度為**完整**，非 skimmed。

### 機械面查證結果（獨立復現，未沿用作者自述）

| 查證項 | 命令／方法 | 結果 |
|---|---|---|
| `ci.yml` 全檔 `OPENROUTER` 零命中 | `grep -n "OPENROUTER" .github/workflows/ci.yml` | **確認為真**，exit 1（零命中） |
| 七個既有 job 名稱 | `grep -n "^  [a-zA-Z_-]*:$"` | `gate`／`repo-contract`／`frontend`／`backend`／`memory-schema`／`concurrency`／`docker-build`，七個名稱逐字相符 |
| job 之間的依賴關係 | `grep -n "needs:"` | **六個非 `gate` 的 job 全部只 `needs: gate`，彼此並行**——doc 原文「七個 job **依序**」的措辭與實際執行模型不符（見 R-03） |
| `build-and-test` 的 `Unverified` 升級路徑 | `sed -n` 讀 `build-and-test.md` Step 9 與失敗梯 | **確認為真**：任何 applicable target 為 `Unverified` 觸發 Failure predicate → 失敗升級梯（in-stage fix → classify → autonomous loop-back ≤3 → halt-and-ask）。這是 AI-DLC 工作流程本身的強制點，**不是** CI job——文件用詞正確地把它稱為「`build-and-test`（3.6，`ALWAYS`）的核可關卡」，沒有把兩者混為一談。作者自疑的「我可能把 stage 與 CI job 搞混」**未成立**：全文檢索，文件沒有一處宣稱 `build-and-test` 在 `ci.yml` 裡執行 |
| 「比提醒更可靠」的實際強度 | 讀 `stage-protocol-construction.md` halt-and-ask 段 | 部分成立：它強制一個**人工決策點**（不是靜默通過），但 halt-and-ask 的候選項包含「接受失敗」，人工仍可選擇帶著 `Unverified` 繼續——不是不可逾越的硬閂。文件本身已誠實標註「它不是閘門、不擋 PR、不擋 merge」，沒有誇大，故不另立發現 |
| `[I2]` 字面值 vs 應用層預設的區分 | 讀 `tech-stack-decisions.md`／`rules.md` 的 `BR3.4` | 成立：應用層仍是 required-no-default（缺值即 raise），`render-env.sh` 寫字面值只是**顯式供給**而非**降低應用層門檻**；且有 `V7`／`BRAIN_SESSION_HISTORY_MAX` 既有先例。不另立發現 |
| `D-6` 出站零增量 | `grep -rn "openrouter.ai" backend/services/langgraph_runtime.py`；`grep -n "networks\|internal" deploy/docker-compose.deploy.yml` | **確認為真**：`langgraph_runtime.py:16` 的 `DEFAULT_OPENROUTER_BASE_URL` 已被 A1/A3/C1 使用；compose 的 `internal` network **未設 `internal: true`**，無防火牆規則、無 Cloudflare Tunnel 層的出站限制。零增量成立 |
| `I-1` 推論鏈（空金鑰 → 入口頁每輪失敗） | 讀 `functional-design/rules.md` 的 `BR2.1`／`BR8.2` | **確認為真**：`BR2.1` 無快路徑、每輪必經分類；`BR8.2` 模型失效 raise `LlmUnavailable`、不降級猜測。鏈條成立，交給 `U13` 而非自改屬合理的跨單元邊界（會影響 A1/A3/C1 既有降級行為），但見 R-02 |
| `traceability.json` 的 35 個 `upstream_ids` | 自行 `grep -ohE` 枚舉 `nfr-requirements/*.md` ＋ `nfr-design/*.md` 全部 `NFR*.*`／`SEC-*` 識別字，與 claimed 集合做差集 | **完全相等**（35 = 35，雙向差集皆空）。35 列確實是這兩站的識別字聯集，不是作者自稱的子集造假 |
| `traceability` sensor | `bun .claude/tools/aidlc-sensor-traceability.ts --output-path traceability.json` | `{"pass":true,"findings_count":0}`，獨立復現成立 |
| `required-sections` sensor（三檔） | 逐檔執行 | 三檔皆 `pass:true, findings_count:0` |
| `upstream-coverage` sensor | 逐檔以 `--consumes` 清單執行 | 單檔執行時 `contract-summary` 在 `cicd-pipeline.md`／`monitoring-design.md` 回報 unreferenced（因為該引用只在 `infrastructure-specification.md` 出現）——這是該 sensor **逐檔**掃描的已知特性（非本單元獨有），作者宣稱的「pass 0 unreferenced」若是對整個 stage 目錄跑則需確認用的是何種聚合方式；本身不構成設計缺陷，不列為發現 |
| 設計階段 ≤15 行片段限制 | 數 `cicd-pipeline.md` 的 yaml 區塊行數 | 11 行，合規 |
| OpenAPI drift 對本單元無影響 | 讀 `nfr-design/security-design.md` 的 `SEC-2`（無 `APIRouter`） | 確認為真，`SEC-2` 已在上一站審查（`R-09`/`R-10`）核可為結構性事實 |

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `traceability.json` 的 `NFR1.60`／`SEC-4` 兩列（`status: "N/A"`） | 兩列的 `note` 都明確點名**已有承接站**——`monitoring-design.md` §五逐字「承接：`observability-setup`（4.x）——與 `OPEN-N10-4` 同一站」。`traceability` sensor 的 schema（`.claude/sensors/aidlc-traceability.md`）定義 `N/A` 的語意是「無基礎設施落點」（本次對 `NFR3.65`／`NFR9.61`／`SEC-1` 等純應用層項是正確用法），而 `Deferred` 才是「有名字的未來承接站」的正確狀態——**同一個 intent 內的對照組已示範這個區分並正確使用**：`brain-infra/infrastructure-design/traceability.json` 的 `AUDIT-CORRELATION-ID` 列用 `Deferred`，target 寫「承接點為 `U13 brain-gateway`...的 `nfr-design` 迭代」；`session-store` 的 `NFR4.41` 同樣用 `Deferred`，target 寫「`OPEN-N10-6` → `U10` 的 `code-generation`」。本單元把同形狀的缺口標成 `N/A`，使讀這份 `traceability.json` 的人（或任何只信任 sensor 輸出的下游工具）把「已知、已承接、只是本站做不到」誤讀成「這題跟基礎設施無關，沒有要追的東西」。可構造的失敗情境：`observability-setup`（4.x）執行時若只依賴各單元 `traceability.json` 的 `Deferred`／`GAP` 列彙總待辦清單（這是合理的實作方式），`NFR1.60`／`SEC-4` 不會出現在那份清單裡，dashboard／告警通道的建置會漏掉「反問率要與準確率同圖」與「`prompt_guard` 命中要可觀測」這兩個具體要求，而不是被完整轉達。 | 把 `NFR1.60`／`SEC-4` 的 `status` 改為 `Deferred`，`target` 改為與 `brain-infra`／`session-store` 同形狀的具名承接站（`observability-setup（4.x）`），`note` 可保留現有文字。這不會讓 `traceability` sensor 變紅（`Deferred` 與 `N/A` 同屬不觸發 `findings_count` 的狀態），純粹是把真實語意寫對。 | New |
| R-02 | Major | `cicd-pipeline.md` 第 144-146 行（`I-1` 交接事項） | `I-1` 交給 `U13 brain-gateway` 的 `infrastructure-design`，但 `infrastructure-design` 的 `execution` 是 **`CONDITIONAL`**（`condition`: 「Infrastructure services need mapping, deployment architecture required, or cloud resources needed. Skip if no infrastructure changes and infrastructure already defined.」）。`project.md` 已有明文規則（`approval-handoff:e4b6b5c2` 等多筆）：指派給 `CONDITIONAL` stage 的交接事項必須額外註明「該 stage 可能被 skip」的風險並指出誰要確認，否則指派會無聲落空。**本單元自己在同一個 intent 內已有正確示範**——`brain-infra` 的 `AUDIT-CORRELATION-ID` 交接項逐字寫「該站是 CONDITIONAL、condition 為連言，`brain-infra` 跑過不保證 `U12`／`U13` 會跑，屆時判定 skip 的執行者須重新提交使用者裁決」——而 `I-1` 完全沒有這句。可構造的失敗情境：`U13` 的 conductor 判定「入口頁沒有需要新增的基礎設施（WS 端點已存在、不需新 infra）」而 skip 本站的 `infrastructure-design`；`I-1` 所承載的真實生產風險（空 `OPENROUTER_API_KEY` 會讓入口頁**每一輪**輸入失敗，不只是 A1 降級）就永久消失在沒有人讀的交接表裡——而這條風險鏈本身（`BR2.1`／`BR8.2`）已被本審查獨立核實為真，後果不是假設性的。 | 在 `I-1` 的文字後面補一句，比照 `brain-infra` 的 `AUDIT-CORRELATION-ID` 形狀：點名 `infrastructure-design` 對 `U13` 是 CONDITIONAL、可能被 skip，並指定判定 skip 的執行者（conductor／人工）須在那一刻把 `I-1` 重新提交使用者裁決，不得隨 skip 靜默消失。 | New |
| R-03 | Minor | `cicd-pipeline.md` 第 11 行「`ci.yml` 的七個 job **依序**：`gate` → `repo-contract` → ... → `docker-build`」 | 名稱與數量正確（已獨立 `grep` 復現），但「依序」與箭頭鏈暗示順序執行；實際上除 `gate` 外的六個 job **全部只 `needs: gate`，彼此並行**（`ci.yml:422` 自己的註解逐字「wall-clock 增量約為 0...故全部並行」）。這與 `project.md` 已記過的「箭頭鏈是順序的語法，用它說明約束規模等於在排序」是同一類精度問題——雖然這裡描述的是既有管線而非建議新順序，但讀者（尤其是要在這張清單上插入新 job 的下一個單元）可能誤以為必須排在 `docker-build` 之前或之後，而實際只需 `needs: gate`。不影響本單元任何技術結論（`[I1]` 的 `routing-accuracy` job 本身正確地只 `on: workflow_dispatch`，不受此清單順序影響）。 | 把列舉方式改成無序清單或加一句「六者彼此並行，僅共同依賴 `gate`」，避免下游誤讀為執行序列。 | New |

### 新引入／既存漏審／新設計問題 分類與 Summary 計數

- **新引入**：0（本輪未修改任何受審產出，純審查）
- **既存漏審**：2（R-01、R-02 —— 兩者都是本單元首次產出時即存在的狀態標記與交接文字缺口，上游三站的審查未觸及基礎設施層的狀態語意一致性）
- **新設計問題**：1（R-03 —— 文件措辭精度，不影響技術正確性）

### Summary

四個受審產出的核心技術主張（CI 零金鑰、egress 零增量、required-no-default 的分層、`BR2.1`/`BR8.2` 的失敗鏈、35 個 upstream_ids 的完整性、三個 sensor 的通過狀態）逐一獨立復現後**全部成立**，作者自己點名的七個高風險項裡六項查無問題、一項（`I-1` 的 CONDITIONAL 交接）確實有缺口。真正的問題不在本單元的技術判斷，而在**狀態標記的語意精度**：`traceability.json` 把兩個已有具名承接站的缺口標成 `N/A` 而非 `Deferred`（R-01），以及交接事項 `I-1` 沒有照本 intent 內已有的正確先例註明 CONDITIONAL-skip 風險（R-02）——兩者都在本單元自己的對照組（`brain-infra`／`session-store`）裡有現成的正確寫法可以直接比照，修正成本低。零 Critical、2 Major（未超過 ≤2 的門檻）、1 Minor，verdict 為 READY，但人工在關卡應留意 R-01／R-02 是否要在合入前補上（成本各約一行文字）。

VERDICT: READY
