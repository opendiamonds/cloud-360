## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T13:55:24Z
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Minor | `security-requirements.md` > `NFR5.7`「可測判準」 | `BR2.12`／`BR2.13` 的機械斷言仍依賴一份開放式「禁用名單」（`userId`／`user_id`／`role`／`token`／`turnId` 等，以「等」收尾），與本文件其餘判準（`NFR5.2`／`NFR5.3`／`NFR5.5` 的精確命令或判定式）的精確度不一致。此發現在上一輪已記錄且仍未修正；另見 R-03，該缺口現已被更嚴重的事實取代——整個機制已被 ADR-0019 §6 推翻為白名單等式斷言，而非改良版的封閉式禁用名單。 | 見 R-03 的處置；`NFR5.7` 整段需改寫為白名單形狀並引用 `ADR-0019 §6`，而不只是把名單收斂為封閉集合。 | Unresolved |
| R-02 | Minor | `tech-stack-decisions.md` > `§四「這不是一個選擇題」` | 引用 `project.md` 的 `requirements-analysis:260822-ra-c5`（單一可行解不出成題目）為契約模組的**確切檔案路徑** `backend/services/brain_ws_contract.py` 定案，把「不得寫進 `U13` 的 router 檔內」（單元邊界，確實別無選擇）與「該放 `backend/services/` 而非其他合法目錄」（延續既有三層慣例的選擇）混為一談，讓一個可受質疑的慣例選擇借用了「單一可行解」規則本該保留給真正別無選擇情況的效力。此發現在上一輪已記錄，文字未改動，問題仍在。 | 拆成兩層論證：(a) 為何不能在 `U13` 內（單元邊界，單一可行解，維持現有引用）；(b) 為何選 `backend/services/` 而非其他合法目錄（慣例延續，引用 `team.md` 的既有分層先例，而非 `requirements-analysis:260822-ra-c5`）。結論不必變動。 | Unresolved |
| R-03 | Major | `security-requirements.md` > `NFR5.7`；`traceability.json` > `reverse[NFR5.7]` | **本單元自己的 `nfr-requirements` 產出與同一個 commit（`c619c3f`）一併送出的 `ADR-0019 §6` 直接矛盾，且已被已合併的程式碼證實採用了 ADR 的版本而非本檔的版本。** `security-requirements.md` 的 `NFR5.7` 寫「六個 client payload 與 `WsClientEnvelope` 的欄位名集合與一份禁用名單……的交集為空」（denylist intersection，斷言對象是**產生的 `ws-contract.d.ts`**）；`ADR-0019 §6`（標題逐字「客戶端訊息的身分欄位以白名單斷言，不用禁用名單」）則明確拒絕禁用名單、改採「欄位名集合**逐一等於**一份釘在 `dump_ws_contract.py` 內的預期集合」（whitelist equality，斷言對象是**後端 schema**，不是生成後的 `.d.ts`），並給出具體理由：「禁用名單擋不住叫別的名字的身分欄位（`actor`、`onBehalfOf`、`impersonate`…），那個命名空間是開放的、列不完」。已讀 `backend/scripts/dump_ws_contract.py:85-198`，確認實際實作函式 `assert_client_field_whitelist()` 完全依 ADR-0019 §6 的白名單等式做法，程式碼內的註解逐字寫「`NFR5.7` 客戶端欄位白名單（`ADR-0019 §6`）」並重述同一段「為何是白名單而不是禁用名單」的理由——即已合併的實作採用的是 ADR 的版本，不是本單元 `nfr-requirements` 兩份產出描述的版本。本單元的三份產出（`security-requirements.md`、`tech-stack-decisions.md`、`traceability.json`）對 `ADR-0019` 的引用次數分別為 7（僅 `security-requirements.md`，且全部是在講 ADR-0006 四面向判定表旁的不相關段落，非指 ADR-0019）、0、0——**零處**引用這份「直接治理本單元」的 ADR。對於一份 advisory 審查交給人工在核可關卡判讀的文件而言，`NFR5.7` 現在描述的是一個已經被推翻、且已被證實不是實際交付內容的機制，會誤導任何只讀這份 `nfr-requirements` 產出（而未去讀 `ADR-0019` 或已合併程式碼）的人。 | 改寫 `security-requirements.md` `NFR5.7` 與 `traceability.json` 的 `NFR5.7` 條目，使其描述與 `ADR-0019 §6` 一致：斷言對象為後端 `components.schemas`（非生成後的 `.d.ts`）；機制為白名單欄位集合等式（非禁用名單交集）；引用 `ADR-0019 §6`、並沿用其「封閉性而非精確度」的理由。同時核對 `ADR-0019 §6` 註記的「判定式只比對頂層 `properties` 鍵、不遞迴進巢狀物件」這項適用前提是否也需要寫進本單元文件（它目前完全不在 `security-requirements.md` 內）。 | New |
| R-04 | Minor | `tech-stack-decisions.md` > `§八「CI 落點」` | 表格引用「既有 `python scripts/dump_openapi.py --check` 在 `ci.yml:260`」，但已讀 `.github/workflows/ci.yml` 確認該步驟的 `name:` 在 `:272`、`run:` 在 `:280`，與 `:260` 皆不符（`:260` 附近是其他內容，不屬此步驟）。同表「既有 `npm run check:types` 在 `ci.yml:198`」經核對為**準確**（`name:` 在 `:197`、`run:` 在 `:198`，與引用相符）。此為內容正確但定位錯誤的引用（`project.md` 已多次記載這類缺陷最危險，因為它通過任何只核對內容的核對，而照行號去讀的人會讀到別的東西）。 | 把 `ci.yml:260` 更正為 `:280`（`run:` 所在行，與 `:198` 的既有引用方式一致）。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `bun .claude/tools/aidlc-review-brief.ts context --stage nfr-requirements --unit brain-ws-contract` | 回傳 R-01、R-02 兩項既有發現（皆 Minor） | 兩項在本輪逐字核對後文字皆未變動，狀態維持 Unresolved；R-01 的根本問題已被 R-03 的更嚴重發現取代其處置方向 |
| `grep -c "ADR-0019"` 於三份產出 | `security-requirements.md`=0、`tech-stack-decisions.md`=0、`traceability.json`=0 | 直接治理本單元的 ADR 完全未被引用，支撐 R-03 |
| `git log --follow` 對 `security-requirements.md` 與 `0019-ws-contract-gates-and-generator-supply-chain.md` | 兩檔同一 commit `c619c3f`（2026-09-28 23:04:13 +0800）一併送出 | 排除「ADR 晚於本單元產出、單元尚未來得及更新」的解釋——兩者是同一次送出，矛盾是內部自相矛盾，不是時序落差 |
| `grep -n` 於 `backend/scripts/dump_ws_contract.py` | `assert_client_field_whitelist()`（白名單等式），非 `security-requirements.md` 描述的禁用名單交集 | 已合併實作遵循 `ADR-0019 §6`，證實本單元產出的 `NFR5.7` 文字描述的不是實際交付的機制 |
| `grep -n "name:\|run:" .github/workflows/ci.yml` 針對四道型別閘門 | `check:types` `:197`/`:198`；`WS contract type drift` `:209`/`:210`；`OpenAPI spec drift` `:272`/`:280`；`WS contract spec drift` `:290`/`:291` | 支撐 R-04；其餘三道閘門在本單元產出中未被引用行號，故未發現額外的行號缺陷 |
| `grep -n "REQUIRED_TEXT"` 於 `scripts/validate_repo_contract.py` | `ci.yml` 鍵已含四條指令字串，逐字與 `NFR5.3` 要求相符 | `NFR5.3` 的描述與已合併實作一致，無缺陷 |
| `grep -n "openapi-typescript\|npx --yes"` 於 `frontend/package.json`／`package-lock.json`／`check-api-types.mjs` | 精確釘選 `7.13.0`、`npx --yes` 已移除、本地解析 | `NFR5.2` 的描述與已合併實作一致，無缺陷 |
| 關鍵詞掃描（能力 11／12／13、`project_members`、`MCP`、`progress`、`ProgressChannel` 等） | 本單元三份產出合計 0 命中 | 經查 `requirements.md`／`contract-summary.md`，能力 11（`U21 mcp-bridge`，傳輸為 `mcp`）、能力 13（`K-18 U22 progress-channel`，傳輸為 `in-process`）皆不在 WS 訊息型別契約（`K-02`／`U2`）範圍內，判定為真實的「未觸及」而非缺口 |

### Summary

本輪最嚴重的問題不是新引入的設計缺陷，而是**本單元自己的產出與自己同一個 commit 送出的治理 ADR 互相矛盾，且已合併的程式碼證實採用的是 ADR 的版本**：`security-requirements.md` 的 `NFR5.7` 描述一個已被 `ADR-0019 §6` 明確否決、且未被實際採用的「禁用名單」機制，三份產出對這份直接治理本單元的 ADR 零引用。其餘發現（兩項既有 Minor 未修正、一處內容正確但行號錯誤的 CI 引用）屬次要。本單元的核心機制（兩道 CI 閘門、依賴鎖定、subprotocol 契約化、三條機械斷言、規格檔放置）本身設計健全且已與已合併程式碼逐項核對一致，問題集中在 `NFR5.7` 這一條判準描述過時這件事上。
