## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T14:03:34Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `security-design.md` §五「與 `BR2.13` 的分工」 | 白名單斷言只比對頂層 `properties` 鍵集合，對巢狀 sub-object 不設防，而設計文件本身原未寫下這個前提。 | 已查證：required action 要求「在 `security-design.md` §五或 `dump_ws_contract.py` 的判定式旁明寫這個前提」，兩擇一即可滿足。實際已落在 `backend/scripts/dump_ws_contract.py` 的 `CLIENT_FIELD_WHITELIST` 上方註解與 `ADR-0019` §6 新增的「判定式的適用前提（`nfr-design` 審查 R-01 補，必讀）」小節，逐字對巢狀物件的殘餘與升級路徑（遞迴或明文排除）做了交代。`security-design.md` 本文雖未逐字覆寫，但 required action 給的是「或」而非「且」，已滿足。 | Resolved |
| R-02 | Minor | `nfr-design-questions.md`「一處必須揭露的紀錄瑕疵」與 audit shard `QUESTION_ANSWERED`（`2026-09-28T03:56:07Z`） | `QUESTION_ANSWERED` 把 Q1 誤記為 `A`，定案實為 `B`；此更正當時只存在於問題檔散文，依賴 audit shard 的下游工具讀不到。 | 已查證：`ADR-0019` 檔頭已新增「**紀錄更正（`nfr-design` 審查 R-02 補，2026-09-28T04:13:56Z）**」一段，逐字交叉引用這筆誤記與現行定案，並說明成因與補記被引擎拒絕的機制性理由。這正是 required action 建議的落點之一（ADR 的「觸發來源」段落）。 | Resolved |
| R-03 | Minor | `security-design.md` §三「這條規則的排序約束（本站實測後補）」 | 本節把 `frontend/src/pages/BrainPage.tsx:83` 持有字面量 `` [`bearer.${token}`] `` 描述為**目前仍待解決**的排序約束，並要求「同一個 PR 內必須二擇一：(a) 改為由型別取值；或 (b) 先刪掉 demo 頁」，語氣上是一個尚未滿足的前置條件。已查證（Unit 已建置並合併）：`frontend/src/pages/BrainPage.tsx` 現行內容在第 83 行已是 `const wsRef = useRef<WebSocket｜null>(null);`，與字面量無關；實際 `new WebSocket(...)` 呼叫（現位於第 98–100 行）已改為 `SUBPROTOCOL_SCHEME + SUBPROTOCOL_SEPARATOR + token`，兩個常數的型別分別鎖定為 `WsSubprotocol['scheme']` 與 `['separator']`，與設計要求的「由型別取值」形狀完全一致；`frontend/eslint.config.js` 亦已以 `error` 級 `no-restricted-syntax` 規則落地（且比設計文件 §三 的「≤15 行示意」更完整，額外涵蓋單一字串字面量形式，非僅陣列形式）。換言之，本節描述的排序約束**已被滿足**，但文件仍以現在式陳述一個待決的阻塞條件、並引用一個如今內容已不相符的行號（`:83`）。這不是設計邏輯錯誤，而是設計文件相對於已出貨程式碼的時效性落差——若有人依本節字面去複查「demo 頁是否仍持有字面量」，會先在行號上撲空，且被引導去以為這仍是一個需要處理的待辦，而非已完成並可驗證之事。 | 非阻擋；建議在 §三補一句現況更新（例如「本排序約束已於 `code-generation` 落地：`BrainPage.tsx` 已改用 `SUBPROTOCOL_SCHEME`／`SUBPROTOCOL_SEPARATOR` 兩個型別取值常數，原 `:83` 之字面量已不存在，現行行號請見 `frontend/eslint.config.js` 與 `BrainPage.tsx:98-100`」），讓文件的「待解決」語氣與已合併程式碼的現況一致。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `bun .claude/tools/aidlc-review-brief.ts context --stage nfr-design --unit brain-ws-contract` | 回報兩筆既有發現 R-01、R-02，皆標 `New` | 本輪逐一開檔查證後，兩筆的 required action 皆已在 `dump_ws_contract.py` 與 `ADR-0019` 實際落地，故本輪狀態更新為 `Resolved`；詳見上表理由欄 |
| 讀 `backend/services/brain_ws_contract.py` 全文 | `BR1.5` 以 `@model_validator(mode="before")` 實作，置於契約模組內；`CONTRACT_MODELS`／`CLIENT_FACING_MODELS` 與 `security-design.md` 所列七個客戶端物件逐一相符 | `security-design.md` §四、§五對實作落點與物件清單的具體宣稱，與已合併程式碼一致，無設計與程式碼落差 |
| 讀 `backend/scripts/dump_ws_contract.py` 全文 | `assert_type_payload_parity`（`BR1.4`）與 `assert_client_field_whitelist`（`NFR5.7`，白名單等於比對，非禁用名單）皆已實作，且白名單上方附有 `ADR-0019 §6` 逐字的巢狀物件適用前提註解 | `security-design.md` §五宣稱的白名單設計已如實落地，且上游 `security-requirements.md` `NFR5.7` 條文本身仍停留在舊的禁用名單敘述——但 `security-design.md` 明確標出「上一站的可測判準是禁用名單……本站改為白名單」並給理由，不是靜默繼承也不是靜默矛盾，正確地把 `ADR-0019 §6` 的決定（拒絕禁用名單、改採白名單）落實到設計與程式碼，未重蹈 `nfr-requirements` 審查發現的缺陷 |
| 讀 `.github/workflows/ci.yml`（`backend`／`frontend` 兩個 job 的 WS 相關步驟） | `WS contract spec drift` 步驟確認**無 `env:` 區塊**，註解逐字「Deliberately has NO env block ... That is the point (ADR-0019 D-4)」；`WS contract type drift` 步驟存在且註解引用 `ADR-0019 / NFR5.1` | `security-design.md` §八對 `tech-stack-decisions.md §四` 的 D-4 處置（`(a)` 被迫、`(b)` 慣例選擇）與 ADR-0019 §4 的「deliberately no env:」理由在程式碼現況中一致，未見矛盾或行號／步驟名誤引 |
| 讀 `backend/scripts/dump_openapi.py`、`backend/scripts/dump_ws_contract.py` 的 `--check` 分支 | 兩者對「規格檔不存在」「斷言失敗」皆 `return 1` 並印出診斷訊息，無 try/except 吞例外 | `security-design.md` §六 fail-closed 表格的四種情形與既有先例的對照宣稱屬實 |
| 讀 `frontend/eslint.config.js`、`frontend/src/pages/BrainPage.tsx`（98–100 行） | lint 規則為 `error` 級 `no-restricted-syntax`，涵蓋陣列與單一字串兩種字面量形式；`BrainPage.tsx` 已改用型別取值常數 | 確認 R-03：`security-design.md` §三描述的「排序約束」在已合併程式碼中已滿足，但設計文件仍以現在式／待決語氣描述並引用舊行號 |
| 讀 `functional-spec.md` §七之二（本單元自身產出，非跨單元讀取） | ADR-0006 四面向判定（IAM／Encryption／Network exposure／Audit logging 皆「適用」）與 `security-design.md` §二的判定詞逐一一致，無相反判定 | 未發現本單元內部跨檔的 ADR-0006 判定矛盾 |
| `grep -c "category: calculation"`（`rules.md`） | 0 | `security-design.md` §二對 PBT hard constraint「不適用，附理由」所引用的「`calculation` category 實算為 0」屬實 |

### Summary

`security-design.md` 與 `traceability.json` 把 `NFR5.1`–`NFR5.7` 逐一轉成具體機制、失敗語意與可測判準，並與已合併的 `backend/services/brain_ws_contract.py`、`backend/scripts/dump_ws_contract.py`、`.github/workflows/ci.yml`、`frontend/eslint.config.js`、`frontend/src/pages/BrainPage.tsx` 逐一核對後一致，未見設計與實作落差，也未見對 `ADR-0019`（含其 §6 白名單決定與 §4／D-4 的 fail-closed、無 `env:` 理由）的矛盾或遺漏引用。上一站 `nfr-requirements` 審查抓到的禁用名單缺陷，在本站 §五被正確辨識、改寫為白名單等值比對，並未繼承或放大該錯誤。兩筆上一輪留下的 Minor 發現（R-01 巢狀物件前提、R-02 紀錄更正的交叉引用）其 required action 皆已在 `ADR-0019` 與 `dump_ws_contract.py` 落地，本輪判定為 Resolved。新查出一筆 Minor（R-03）：`security-design.md` §三對 `BrainPage.tsx` 字面量的排序約束描述已被程式碼現況超車而顯得過時（舊行號、現在式待決語氣），建議補一句現況更新，但不影響可實作性，不構成阻擋。
