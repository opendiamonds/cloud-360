## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

本單元（U2，kind=spec）的 nfr-requirements 兩份產出整體自洽，核心機制（兩道 CI 閘門、產生器精確釘選、subprotocol 契約化、規格檔放置於 repo 根、REQUIRED_TEXT 涵蓋四道閘門）與已落地程式逐項核對一致，ADR-0006 四面向皆有判定與落點。主要問題是 NFR5.7 描述的「禁用名單交集」機制已被同批 ADR-0019 §6 與已落地的 dump_ws_contract.py 改為「白名單等式」，而兩份產出零處引用 ADR-0019，這是會誤導只讀本站產出者的 Major；其餘為可折入的 Minor。依規則（0 Critical、1 Major）判 READY，供關卡上的人裁決。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | construction/brain-ws-contract/nfr-requirements/security-requirements.md > NFR5.7「可測判準」；traceability.json > NFR5.7；同檔 §一 IAM 列 | NFR5.7 寫「六個 client payload 與 WsClientEnvelope 的欄位名集合與一份禁用名單（userId／user_id／role／token／turnId 等）的交集為空」，斷言對象是產生後的 ws-contract.d.ts。但已落地的 backend/scripts/dump_ws_contract.py:85-210 實作的是 assert_client_field_whitelist()：以後端 components.schemas 為對象，七個客戶端物件的欄位集合「逐一等於」釘在腳本內的預期集合，註解逐字引用 ADR-0019 §6（標題「以白名單斷言，不用禁用名單」，理由為禁用名單擋不住 actor／onBehalfOf／impersonate 等開放命名空間）。本站兩份產出對 ADR-0019 的引用為 0 次（grep -c 實測 security-requirements.md=0、tech-stack-decisions.md=0），且 NFR5.7 未記載 ADR-0019 §6 的適用前提（判定式只比對頂層 properties 鍵、不遞迴巢狀物件，其成立依賴七個物件皆為扁平）。另「六個 client payload」與落地的「七個客戶端物件」計數不一致。此項在關卡上以 nfr-requirements 為準的讀者會得到錯誤的機制描述；落地程式是對的一邊。前次 review-02 R-01／R-03 已提。 | 改寫 NFR5.7 與 traceability.json 條目：斷言對象改為後端 components.schemas、機制改為白名單欄位集合等式、引用 ADR-0019 §6 與其「判定式僅比對頂層 properties」前提、更正物件計數；或在檔內以 corrections 形式註明被 ADR-0019 §6 取代。 | New |
| R-02 | Minor | construction/brain-ws-contract/nfr-requirements/security-requirements.md > NFR5.2「可測判準」 | 判準「grep -c 'npx --yes' frontend/package.json frontend/scripts/*.mjs 回 0」在落地後無法字面成立：frontend/scripts/check-api-types.mjs:23、:25 的註解仍含 npx --yes 字樣（實測 2 處；package.json 為 0）。實際可執行程式已無 npx --yes，是判準寫得過寬而非實作違反，但它是本站自己宣稱的二元判準，照字面執行會得到假紅燈。 | 將判準改為「可執行行（排除註解）不含 npx --yes」，或改以 npm_config_offline 執行兩道閘門成功為唯一判準。 | New |
| R-03 | Minor | construction/brain-ws-contract/nfr-requirements/tech-stack-decisions.md > §八 CI 落點 | 引用「dump_openapi.py --check 在 ci.yml:260」「check:types 在 ci.yml:198」。實測現況 check:types 的 run 在 :207、dump_openapi.py --check 在 :294，新增的兩道在 :219 與 :305。:260 從來不是 dump_openapi 步驟（前次 review-02 R-04 已提 :272/:280 為當時位置）。行號引用已失效，且在 ci.yml 持續演進下必然再漂移。 | 以步驟名稱而非行號定位（例如「backend job 的 OpenAPI spec drift 步驟」），或更正為現行行號並註明基準 commit。 | New |
| R-04 | Minor | construction/brain-ws-contract/nfr-requirements/tech-stack-decisions.md > §四「這不是一個選擇題」 | 以 project.md 的 requirements-analysis:260822-ra-c5（單一可行解不出成題目）論證 backend/services/brain_ws_contract.py 的確切路徑。「不得在 U13 router 內」確為單元邊界逼出的單一解，但「放 backend/services/ 而非其他合法目錄」是延續三層慣例的選擇，借用了該規則的效力。前次 review-02 R-02 已提，文字未改。 | 拆成兩層論證：邊界逼出的部分維持引用 ra-c5，目錄選擇改引 team.md 的後端分層慣例。 | New |
| R-05 | Minor | construction/brain-ws-contract/nfr-requirements/security-requirements.md > §五 Assumptions；§0 S-2 | K-02 的三項擴充（ready、select_clarify_candidate、WsSubprotocol）標記為「尚未取得上游追認」，但 ADR-0019 已落地且 contract-summary 為上游的單一真實來源，本站未指名誰負責追認、落點在何站。契約端點三問中「誰清」此項懸空，且 WsSubprotocol 的 bearer／. 值亦屬同一待追認項。 | 指名追認的承接站與負責方（或記為無自然承接站並交 conductor 提交使用者），並確認該站的 execution 值與游標位置。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| grep -c ADR-0019（本站 security-requirements.md／tech-stack-decisions.md） | 0／0 | 支持 R-01：直接治理本單元的 ADR 未被引用 |
| grep 於 backend/scripts/dump_ws_contract.py | assert_client_field_whitelist 存在，註解引用 ADR-0019 §6 | 落地採白名單等式，與 NFR5.7 文字不符，落地為正確一邊 |
| grep 於 ADR-0019 | §6 標題為白名單斷言，Alternatives Rejected 列「維持禁用名單」 | 設計決定已被推翻，本站產出未同步 |
| grep -n 於 .github/workflows/ci.yml | check:types :207、check:ws-types :219、dump_openapi --check :294、dump_ws_contract --check :305 | 支持 R-03；四道閘門皆存在，NFR5.1 描述成立 |
| grep -n openapi-typescript 於 frontend/package.json | devDependencies 精確釘選 7.13.0；gen:types 已為本地呼叫 | NFR5.2 要求 1、2 成立 |
| grep -n npx --yes 於 frontend/scripts/check-api-types.mjs | 僅註解 :23、:25 | 支持 R-02 |
| grep -n ci.yml 於 scripts/validate_repo_contract.py | REQUIRED_TEXT 已含 ci.yml 鍵與四道閘門字串（:134-150） | NFR5.3 與落地一致，無缺陷 |
