## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-09-28T03:19:46Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `security-requirements.md` > `NFR5.7`「可測判準」 | `BR2.12`／`BR2.13` 的機械斷言依賴一份「禁用名單」，但文中只給出範例並以「等」收尾（`userId／user_id／role／token／turnId 等`），不是封閉集合。這與同一份文件其他判準（`NFR5.2` 的 `grep -c` 精確命令、`NFR5.3` 的四條指令字串、`NFR5.5` 的三個判定式）形成明顯的精確度落差——那幾條讓 `code-generation` 不需猜，這一條需要。 | 把禁用名單收斂為封閉清單（例如列舉 `userId`、`user_id`、`role`、`roles`、`token`、`accessToken`、`turnId` 等全部要擋的欄位名，並註明未來新增身分等價欄位時由誰更新這份清單），移除「等」字，使其與本文件其餘判準同等可執行。 | New |
| R-02 | Minor | `tech-stack-decisions.md` > `§四 D-4「這不是一個選擇題」` | 引用 `project.md` 的 `requirements-analysis:260822-ra-c5`（單一可行解不出成題目）來為契約模組的**確切檔案路徑** `backend/services/brain_ws_contract.py` 定案。該規則能證明的只是「模組不得寫在 `U13` 的 router 檔內」（單元擁有權邊界，確實被迫）；但「該放進 `backend/services/` 而非例如 `backend/models/` 或一個新的 `backend/contracts/`」是延伸既有三層慣例（`team.md` 的 `wa_rule_engine.py` 等純引擎放 `services/` 的先例）的**慣例選擇**，不是邏輯上唯一解——把兩者混在同一句話裡，讓一個可受質疑的慣例選擇借用了「單一可行解」規則本該保留給真正別無選擇情況的效力。 | 把該小節拆成兩層論證：(a) 為何不能在 `U13` 內（單元邊界，單一可行解，維持現有引用）；(b) 為何選 `backend/services/` 而非其他合法目錄（慣例延續，引用 `team.md` 的既有分層先例作為理由，而非 `requirements-analysis:260822-ra-c5`）。結論不必變動。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `bun .claude/tools/aidlc.ts engine sensor fire required-sections --output-path security-requirements.md` | `passed` | 通過。本輪未依賴「`consumes` 為空即無效通過」的陷阱——這是通用 H2 計數檢查，本檔 H2 數遠超門檻。 |
| `bun .claude/tools/aidlc.ts engine sensor fire upstream-coverage --output-path security-requirements.md` | `passed` | **已核實非空洞通過**：手動比對 stage frontmatter 的 `consumes:`（`functional-spec`、`rules`、`requirements`、`contract-summary`、`technology-stack`），五項在本 stage 產出的三份檔案中皆有實際引用（`grep -rl` 逐一命中），非「`consumes` 為空」造成的假通過。 |
| `bun .claude/tools/aidlc.ts engine sensor fire traceability --output-path traceability.json` | `failed`（`gaps: [GAP-1, GAP-2]`, `findings_count: 2`） | **屬設計行為，非缺陷**：讀 `.claude/tools/aidlc-sensor-traceability.ts:577-581`，`GAP` 是合法 status 值，任何 `GAP` 項都會讓 `pass:false`——這是刻意的機制，逼 `GAP` 在核可關卡被人看到，不是本單元誤用了 sensor。兩個 `GAP` 項本身在 `security-requirements.md §三` 與 `traceability.json` 皆有落點與修法（`U14`、`U13`），符合 `project.md` 的既定處置形狀。`orphans`／`missing_from_table`／`missing_from_upstream_ids`／`invalid_entries`／`invalid_targets` 全空，代表沒有真正的結構性缺陷。 |
| `python3 scripts/validate_repo_contract.py` | `passed`（exit 0） | 本輪未動任何實際檔案，基準通過符合預期；驗證的是本次審查未意外破壞既有 contract。 |
| `python3 scripts/validate_env_contract.py` | `passed`（exit 0） | 同上。 |
| `ast` 解析 `REQUIRED_TEXT` | 實算 **4 鍵**：`README.md`、`CLAUDE.md`、`team.md`、`project.md`；`schema_rbac.sql`／`DEPLOY.md` 確認位於 `project.md` 鍵值內（非鍵） | **與 artifact 逐字相符**，且與 artifact 自陳的「初版誤寫八鍵、已更正」一致。 |
| `grep -c 'openapi-typescript' frontend/package-lock.json` | `0` | 與 artifact 逐字相符。 |
| `grep -n 'gen:types'`／`check-api-types.mjs:19-21` | 兩處 `npx --yes openapi-typescript@7.13.0`，版本字串各自手寫，`GENERATOR` 常數註解逐字為「兩處若不一致，這道 gate 會比對到不同產生器的輸出而誤報」 | 與 artifact 逐字相符。 |
| `python3 -c "json.load(frontend/package.json)['devDependencies']"` | 17 項 | 與 artifact 聲稱的「17→18」基準相符。 |
| `.github/workflows/ci.yml` 行號核對 | `:198` = `npm run check:types`；`:260` = `python scripts/dump_openapi.py --check` | 與 artifact 逐字相符。 |
| `entities.md` 實體計數（腳本解析 `entities:` yaml 區塊的 `- name:` 項） | **22** | 與 artifact 聲稱的 22 個實體相符。`WsServerMessageType` 值域 9 個、`WsClientMessageType` 值域 6 個，皆與 artifact 相符。 |
| `rules.md` category 分佈（逐行核對 `category:` 欄位） | `validation:6`、`constraint:16`、`policy:8`、`authorization:1`、`calculation:0`，合計 31 | 與 artifact 相符。 |
| **實測**：`npx --yes openapi-typescript@7.13.0` 對一份含 `WsSubprotocol`（`const: "bearer"`／`"."`，帶中文 `description`）的最小 OpenAPI 3.1 components-only 文件 | 成功（17.8ms），`paths: {}` 被接受；`const` → 字面型別並帶 `@constant`；`description` → `/** @description ... */`，中文原樣保留 | **本審查獨立重現**，與 artifact 聲稱的三項實測結果（D-1 事實 3–5、`NFR5.5` `BR4.4` 前提）逐一相符，未依賴 artifact 自報的結果。 |
| **實測**：同一產生器對含 `x-subprotocol`（頂層）與 `x-subprotocol-format`（schema 內欄位層）的樣本 | 兩處 `x-` 擴充欄位在輸出的 `.d.ts` 中**完全消失**，`bar` 欄位的型別繫結未反映任何格式資訊 | 獨立驗證 `D-5`「`openapi-typescript` 不會為任意 `x-` 擴充欄位產生任何 TypeScript 繫結」的論證前提為真，不是文件自稱。 |
| 跨單元核實：`brain-infra/nfr-requirements/traceability.json` 的 `NFR7`／`NFR10` | `NFR7` 為 `Deferred`（該單元對加密承載面**有**部分交付：具名 volume）；`NFR10` 為 `N/A`（同樣未定案，同樣承認非承接站） | 本單元把同一 `NFR7` 標為 `N/A`（本單元對其**無任何**交付，非部分交付）——區分依據站得住；`NFR10` 的「這是第二次跑過本站、兩次都非承接站」之說法屬實，兩個單元的紀錄互相印證而非矛盾。 |

### Summary

三類計數：**(a) 本站新引入的問題 0 項；(b) 既存但先前審查漏抓的問題 0 項；(c) 本輪真正的新設計問題 2 項**（皆為 Minor：R-01 的機械斷言未封閉、R-02 的規則引用範圍略微過寬）。

本單元的產出品質顯著高於典型送審狀態：五道題目的機械事實逐一可重現（含本審查獨立重跑的兩次 `openapi-typescript` 實測，未依賴文件自報結果）、`REQUIRED_TEXT` 的鍵數與 `entities.md`／`rules.md` 的實體與規則計數全部覆核無誤、ADR-0006 四面向判定表論證扎實且與 `functional-spec.md` 的同名表做出明確區分（互補而非重複）、PBT hard constraint 判定為 N/A 有實質依據（`calculation` category 實算為 0）、`NFR7`／`NFR10` 兩處與 `brain-infra` 的交叉核實顯示判定一致且互相印證而非矛盾。兩項 Minor 發現皆為可低成本收斂的精確度問題，不影響本階段任何一條 NFR 的實質判準或安全結論，不阻擋 READY。

未深入覆核之處（誠實記載，供下一輪或 `code-generation` 留意）：`traceability.json` 的 `reverse` 區塊六項（`NFR5.2`–`NFR5.7`）逐條核對了其論證內容，但未逐字比對它們與 `security-requirements.md` 對應段落是否有隱性用詞漂移（僅做了跨檔一致性的抽樣，未做逐字 diff）；`nfr-requirements-questions.md` 的「模糊語檢查」與「跨題矛盾檢查」表格內容合理，但本審查未對五題以外、問題檔前言列出的「上游已定案、不重問」十項逐一回頭核對其可引用性（僅抽查其中 K-02／K-12 相關的三項並確認逐字相符）。
