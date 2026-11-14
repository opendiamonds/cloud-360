## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-03T13:45:32Z
**Iteration:** 2

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | .../functional-design/functional-spec.md:150 | 已修。我實算 `entities.md` 頂層 `- name:` 條目為 22，`functional-spec.md:150` 已寫「22 個實體」並附修訂說明（18→22 的由來）。全檔（`functional-spec.md`／`entities.md`／`rules.md`）grep「18 個」「共 18」「= 18」零殘留命中；`entities.md:527` 的「由 18 增為 22」是歷史敘述，非殘留。 | 無。 | Resolved |
| R-02 | Critical | .../functional-design/entities.md > `WsClientMessageType`、`SelectClarifyCandidatePayload` | 已修並以 `backend/services/brain_ws_contract.py:89-103` 之 `WsClientMessageType` 列舉實測核對：`select_clarify_candidate` 在列，共六值，與設計一致。 | 無。 | Resolved |
| R-03 | Critical | .../functional-design/entities.md > `WsUnvalidatedEnvelope` | 已修，以 `brain_ws_contract.py` 的 `class WsUnvalidatedEnvelope` 核對欄位與命名一致。 | 無。 | Resolved |
| R-04 | Major | .../functional-design/rules.md > `BR3.1`；`functional-spec.md` 的 `SM-2` | 已修，四值封閉列舉在 `rules.md`／`functional-spec.md` 兩處一致。 | 無。 | Resolved |
| R-05 | Major | .../functional-design/entities.md、`rules.md` | 已修，三個子問題（原 R-14／R-17／R-18）本輪重新核對均已修復。 | 無。 | Resolved |
| R-06 | Major | .../functional-design/functional-spec.md > `§七之二` | 已修，改寫為「本單元只擋了一半」並點名 `K-12 x-hard-constraints.token_transport`。 | 無。 | Resolved |
| R-07 | Major | .../functional-design/functional-spec.md > `§八` | 已修，四列表格含 subprotocol 名稱與編碼格式。 | 無。 | Resolved |
| R-08 | Major | .../functional-design/functional-spec.md > `§七之二` | 已修，四面向逐項判定表完整。 | 無。 | Resolved |
| R-09 | Major | .../functional-design/functional-spec.md > `§四` | 已修；`functional-spec.md:183` 明文「初版把它稱為『舊描述』是錯的」，已改錨 `BR3.3`。 | 無。 | Resolved |
| R-10 | Minor | .../functional-design/rules.md > `BR2.5` | 已修。 | 無。 | Resolved |
| R-11 | Minor | .../functional-design/rules.md > `BR1.4` | 已修，以 `brain_ws_contract.py` 的 payload 命名核對判定式一致。 | 無。 | Resolved |
| R-12 | Minor | .../functional-design/rules.md > `BR1.5` | 已修，以 `brain_ws_contract.py` docstring（逐字列 `BR1.2`／`BR1.5`／`BR1.6`）核對已被下游採用。 | 無。 | Resolved |
| R-13 | Minor | .../functional-design/functional-spec.md > 章節序號 | 已修。 | 無。 | Resolved |
| R-14 | Critical | .../functional-design/entities.md > `WsEnvelope.turnId` | 已修，`BR1.6` 承載二分判準，以 `brain_ws_contract.py` docstring 核對已被下游採用。 | 無。 | Resolved |
| R-15 | Critical | .../functional-design/functional-spec.md > `§二` `SM-2` | 已修，`candidateId` 為 null 的路徑與 `BR2.14` 一致。 | 無。 | Resolved |
| R-16 | Critical | .../functional-design/rules.md > `BR3.2`、`BR3.5`；`entities.md` | 已修，`WsUnvalidatedEnvelope` 雙向化。 | 無。 | Resolved |
| R-17 | Major | .../functional-design/entities.md:41 附近 | 已修。 | 無。 | Resolved |
| R-18 | Major | .../functional-design/rules.md > `BR1.1`／`BR1.2`／`BR1.3` | 已修。 | 無。 | Resolved |
| R-19 | Major | .../functional-design/entities.md、`rules.md` | 已修，`BR2.14` 承載此處置，為可接受的既定取捨。 | 無。 | Resolved |
| R-20 | Major | .../functional-design/entities.md > `WsClientEnvelope` | 已修，`turnId` 已移除並新增 `BR2.13`；以 `_CONTRACT_CONFIG = ConfigDict(extra="forbid")` 與 docstring 核對一致。 | 無。 | Resolved |
| R-21 | Minor | .../functional-design/rules.md、functional-spec.md 的計數 | 已修。我重新機械實算：`rules.md` 規則總數 31（`grep -c "^  - id: BR"`），category 分佈 `validation` 6／`constraint` 16／`policy` 8／`authorization` 1／`calculation` 0，合計 31，與 `functional-spec.md §五` 一致；`entities.md` 的 22 個實體計數同前核對。 | 無。 | Resolved |
| R-22 | Minor | .../functional-design/functional-spec.md > `§七之二` Encryption 列 | 已修，判定詞與 Audit logging 列同構。 | 無。 | Resolved |
| R-23 | Minor | .../functional-design/entities.md（原引用「`:552`」殘留，現已位移） | **仍未完全修復，且殘留處已與 R-23b 的修正方向相反。** 我以 `contract-summary.md:210-230` 逐行核對：第 222 行逐字為「`types:` # components.md 逐字列舉的六種為下限，不得更少」，第 220 行為「`type: { type: string, required: true }」`，與下限主張無關——即 `:222` 正確、`:220` 錯誤。`entities.md` 的 §三「新增」區塊（現約行 557-558，原稱 `:552`）已正確改為 `:222` 並附更正說明，此部分已修。**但 `entities.md` 另一處（`ready` 實體的 `entity_constraints`，現約行 167-168，R-23 原先認定「已在 `:162` 正確更正為 `:222`」的那一處）現在反而寫「初版寫『K-02:222……』——那是誤讀。`:220` 逐字為『types: # ……』」——把經我核對為正確的 `:222` 指為誤讀，把經核對為無關的 `:220` 當成正確依據，與同檔 §三 的最新修正直接矛盾。見新發現 R-28 的進一步說明。 | 把 entities.md 中 `ready` entity_constraints 區塊（約行 167-168）的「初版寫『K-02:222』——那是誤讀。`:220` 逐字為……」改為與 §三（約行 557-558）一致的「`:222` 才是該註記所在，`:220` 無關」，消除同檔內兩處方向相反的引用。 | Unresolved |
| R-24 | Minor | .../functional-design/entities.md > `WsEnvelope.description`；`rules.md` > `BR2.7` | 已修。`entities.md` 現不再引用 `BR2.7` 支撐「`set_sharing_mode`／`set_work_target` 不屬任何一輪」的結論，改以該實體自身的方向界定為依據，核對 `rules.md` 的 `BR2.7`（`applies_to: WsEnvelope（done／error）`）確實只談伺服器方向，修法正確。 | 無。 | Resolved |
| R-25 | Minor | .../functional-design/functional-design-questions.md:122、:188、:195 | 本輪不重新查證問題檔本身（收據綁定、依規則不回改）。但 `functional-spec.md:183` 已明文「初版把它稱為『舊描述』是錯的（審查 R-09）」，直接點出並更正了問題檔仍殘留的「舊描述」用詞，且 `functional-spec.md:208` 明寫兩份文件對 H-7 不一致、現行規格為本檔。視為已以替代方式處理，不再視為缺口。 | 無。 | Resolved |
| R-26 | Major | .../functional-design/rules.md > `§三 本站新增的規則` | 已修。標題已改為「本站新增的 9 條規則」，清單逐一列出全部 9 條（`BR1.4`／`BR1.5`／`BR1.6`／`BR2.2`／`BR2.5`／`BR2.13`／`BR2.14`／`BR3.2`／`BR4.4`），並明文排除 `BR1.2`（`source` 為「本站明文化」，屬上游衍生）。我核對 `source` 欄含「本站新增」或「審查 R-xx 新增」字樣的規則，與這 9 條一致，無漏列。 | 無。 | Resolved |
| R-27 | Major | .../functional-design/functional-spec.md、entities.md、rules.md（全檔） | 已修，但落點與建議位置不同、且新引出一處行號誤差（見 R-29）。`rules.md` §三新增 `ADR-0019` 引用（非原建議的 `functional-spec.md`），我已確認 `inception/decisions/0019-ws-contract-gates-and-generator-supply-chain.md` 存在；三個落點路徑經我逐一 `ls` 核對存在：`backend/services/brain_ws_contract.py`、`backend/scripts/dump_ws_contract.py`（`rules.md` 寫「`scripts/dump_ws_contract.py`」，相對於 CI `backend` job 的 `working-directory: backend` 是正確的相對路徑，非錯誤）、`frontend/src/types/ws-contract.d.ts`；`traceability.json` 的 `reverse` 新增 `R-27-ADR0019-CITED` 項指向此處。落點選在 `rules.md`（機械斷言表之後）而非原建議的 `functional-spec.md`／`WF-1`，但內容與追溯鏈完整，視為可接受的等效修法。 | 無（行號誤差見 R-29）。 | Resolved |
| R-28 | Major | .../functional-design/entities.md（`ready` 實體的 `entity_constraints`，約行 161-173） | **新發現，驗證 dispatch 要求查核的「兩處 `K-02:220` 均已更正」宣稱後確認：宣稱不實，且 traceability.json 的審計紀錄本身是錯的。** `traceability.json` 的 `reverse` 項 `R-23b-K02-LINE-CORRECTED` 逐字宣稱「`entities.md` **兩處** `K-02:220` 更正為 `K-02:222`」。我以 `contract-summary.md:210-230` 核對：`:222` 正確（`types: # components.md 逐字列舉的六種為下限，不得更少`），`:220` 無關（`type: { type: string, required: true }`）——此事實方向正確，且 §三（約行 557-561）確實已修正為 `:222` 並附此核對結果。**但 `ready` entity_constraints 區塊（約行 167-168）並未被修正，而是呈現與 §三 完全相反的敘述**：「初版寫『`K-02:222` 逐字寫該清單為下限……』——那是誤讀。`:220` 逐字為『`types:` # ……』」——此處把（我核對為正確的）`:222` 判為「誤讀」、把（我核對為無關）`:220` 當成依據寫入。這不是單純的「內容對、行號錯」，而是同一份檔案內兩處對同一件事給出互斥結論，其中一處（entity_constraints 區塊）的結論本身經源頭核對為假，且 traceability.json 審計紀錄對「兩處皆已修正」的宣稱與檔案現況不符。這是本 intent 已記載多次之「內容對而行號錯」模式的再一次出現（`project.md` 記為第五次），但這次額外伴隨一筆失真的審計記錄。 | 修正 entities.md 約行 167-168 的敘述，使其與 §三（約行 557-561）一致地指向 `:222` 為正確依據、`:220` 為無關；同時更正 `traceability.json` 的 `R-23b-K02-LINE-CORRECTED` 項，使其不再宣稱「兩處皆已更正」。 | New |
| R-29 | Minor | .../functional-design/rules.md:529 | 新發現。`rules.md:529` 引用「`.github/workflows/ci.yml:290` 的 `python scripts/dump_ws_contract.py --check`」。我以 `grep -n` 核對 `ci.yml`：第 290 行實為 `- name: WS contract spec drift`（步驟名稱），實際的 `run: python scripts/dump_ws_contract.py --check` 在第 **291** 行。內容與相對路徑皆正確（`backend` job 有 `working-directory: backend`，故 `scripts/dump_ws_contract.py` 解析無誤），僅行號差一。 | 把 `rules.md:529` 的行號由 `:290` 改為 `:291`，或改引整個步驟區塊（`:290-291`）。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| `grep -c "^  - id: BR" rules.md` | 31 | 與 `functional-spec.md §五` 宣稱的規則總數一致。 |
| `grep -c "category: (validation\|constraint\|policy\|authorization\|calculation)"` | 6／16／8／1／0，合計 31 | 與 `functional-spec.md §五` 的分佈表逐欄一致，無殘留誤差。 |
| `grep -n "^  - name:" entities.md` | 22 | 與 `functional-spec.md:150` 的「22 個實體」一致，`R-01`／`R-21` 確認已修。 |
| `python3` 解析 `traceability.json` | `coverage` 8 列（`OK` 5／`Deferred` 3），`reverse` 30 列（`N/A` 22／`OK` 7／`Deferred` 1） | 無重複 id；`OK`／`Deferred` 列皆有非空 `target`；`reverse` 中 9 條 `BR*` 規則缺席，經核對皆已透過 `coverage` 列的 `target` 自由文字引用（有 AC 對應，依設計不需進 `reverse`），非孤兒。 |
| 開 `contract-summary.md:210-230` 逐行核對 | `:222` = 「`types:` # components.md 逐字列舉的六種為下限，不得更少」；`:220` = `type: { type: string, required: true }` | 證實 dispatch 要求查核的「`:222` 正確、`:220` 無關」方向成立，但同時發現 `entities.md` 僅修正一處、另一處（約行 167-168）方向相反且本身錯誤 → R-28。 |
| `ls`／`grep -n` 核對 `backend/services/brain_ws_contract.py`、`backend/scripts/dump_ws_contract.py`、`frontend/src/types/ws-contract.d.ts`、`.github/workflows/ci.yml` | 三路徑皆存在；`ci.yml:291`（非 290）為 `dump_ws_contract.py --check` 的 `run:` 行；`ci.yml:210` 為 `npm run check:ws-types`（`frontend` job） | 證實 R-27 修法的落點真實存在、供應鏈敘述與 `ci.yml` 註解（`ADR-0019 D-4`）相符；但行號有一處差一（R-29）。 |
| `class WsServerMessageType`／`WsClientMessageType`（`brain_ws_contract.py:70-104`） | 伺服器 9 值（含 `ready`）、客戶端 6 值（含 `select_clarify_candidate`） | 與設計文件宣稱的 9／6 值一致，無漂移；`ready`／`select_clarify_candidate` 的 docstring 逐字引用本單元的審查編號（R-01／R-02）與 `ADR-0019`，顯示上游追認已落地。 |

### Summary

本輪（iteration 2，stale-receipt 恢復）對照 iteration 1 的 27 項發現逐一複驗：25 項確認已修（含全部 6 項 Critical），其中 `R-25` 以替代方式（`functional-spec.md:183` 的顯性更正句）視為已處理。`R-23` 仍未完全修復——dispatch 要求重點查核的「`entities.md` 兩處 `K-02:220` 均已更正為 `:222`」宣稱，經我開 `contract-summary.md` 逐行核對後確認**不實**：§三處已正確修正，但 `ready` 實體的 `entity_constraints` 區塊仍殘留一處方向相反、且本身錯誤的引用，與 `traceability.json` 的 `R-23b-K02-LINE-CORRECTED` 審計項之宣稱不符，已另立 `R-28`（Major）記錄此一具體矛盾與其對審計紀錄可信度的影響。另發現 `rules.md:529` 一處行號差一的新殘留（`R-29`，Minor）。規則總數（31）、category 分佈、實體總數（22）、sever/client 列舉值、`traceability.json` 結構完整性、以及本單元設計與已出貨實作（`backend/services/brain_ws_contract.py`）之間，本輪複驗均未發現漂移。現存發現為 0 Critical、1 Major（`R-28`，新發現）、2 Minor（`R-23` 殘留、`R-29` 新發現），對照 READY 規則（0 Critical 且 ≤2 Major）判定為 READY；但 `R-28` 涉及的審計紀錄失真（`traceability.json` 宣稱「兩處皆已修正」而實際只有一處）建議人工在核可前一併處理，不應只視為格式瑕疵。
