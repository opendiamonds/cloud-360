## Review

**Verdict:** NOT-READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | `inception/contract-design/contract-summary.md` § K-16 `existing_endpoint_extension.preserved_existing_protections.guards` | 兩個既有保護的行號引用皆錯。開 `backend/services/user_router.py` 逐行核對：自我停用守門 `if target_user.id == admin_user.id and not request.is_active:` 實際在 **`:645`**，契約寫 **`:651`**（該行實為 `user_can()` 呼叫的 `db,` 參數，差 6 行）；最後一位可編輯角色守門 `if admin_edit_count <= 1:` 實際在 **`:667`**，契約寫 **`:668-671`**（那是 `raise HTTPException(...)` 本體，條件判斷那一行被排除在引用範圍外）。更要緊的是，本輪的七項自檢第 3 項（引用逐字核對）明文宣稱「一處因核對而改寫……實測兩道分別在 `:651`…與 `:668-671`…」——即這兩個行號是**本輪特意重新查證並修正過的結果**，而修正後仍是錯的。這正是 `project.md` 反覆記載的「內容對、定位錯，只檢查內容的核對會放過它」那個形狀，這次連「重新核對」本身也沒攔住 | 重新開檔逐行核對，把兩處行號改為 `:645-646` 與 `:667-671`（或擴大範圍以涵蓋條件判斷本身），並在自檢表的措辭上誠實反映這是第二次嘗試 | New |
| R-02 | Major | `inception/contract-design/contract-summary.md`：① `## 修訂 1 的 ADR-0006 四面向逐項判定` 小節開頭「承已核可的 `requirements.md:617`『四面向皆適用，無不適用項』」；② K-16 `existing_endpoint_extension` 之前段落、X-04 `process_boundary.exposure` 引用的「`requirements.md:614`」 | 兩處對 `requirements.md` 的行號引用皆錯，且皆**不在**自檢 3 聲稱已核對的五處清單內（自檢 3 只開檔核對了 `design_agent.py:218`、`hierarchy_migration.py:411`、`user_router.py:213`、`user_router.py:673`、`.mcp.json`，未涵蓋這兩處）。實測：『四面向皆適用，無不適用項。』這句逐字獨立成段，實際在 `requirements.md:622`，而 `:617` 是修訂 1 四面向表的 IAM 列內容；「不得對外暴露，僅供同主機的大腦進程連接」實際在 `requirements.md:619`，不是 `:614`。兩處皆恰好差 5 行，提示 `requirements.md` 在這兩個引用被記下之後曾被編輯過、行號未重新核對 | 重新核對本檔對 `requirements.md` 的每一處 `:<n>` 引用並更正為 `:622`／`:619`（或等價的準確行），並把自檢 3 的核對範圍擴大到契約文字中每一個 `<file>:<n>` 形式的引用，不只是本輪「新寫」的那五處 | New |
| R-03 | Major | `inception/contract-design/contract-summary.md` K-16 `authorization_model.two_facade_layers`（第 1635 行附近） | `two_facade_layers` 區塊描述 `U19`（membership-service）與 `U20`（requirement-field-service）兩層 facade 的責任切分，但第二層的鍵寫成 `U17_layer`，而 `U17` 在本契約文件的其他每一處都指 `a11y-gate`（CI 無障礙掃描單元，K-19／K-20 的消費端），與需求欄位授權完全無關。這正是本次審查被要求重點查證的「兩層 facade 責任切分」條款裡的一個字面錯誤——若實作者照 YAML 鍵名字面理解，會誤以為無障礙掃描單元在這條授權鏈裡扮演一層角色 | 把 `U17_layer` 改名為 `U20_layer`，與 `U19_layer` 對稱；順帶檢查本檔其餘處是否有同型的單元編號誤植 | New |
| R-04 | Minor | `inception/contract-design/contract-summary.md` § `## 契約表`（第 55–58 行，原始「機制欄的值」清單）對照修訂 1 § `## 機制欄新增第 11 個值` | 修訂 1 的自檢 5 宣稱「`機制` 欄由 10 個值增為 11 個（新增 `mcp`），已在本檔前段明寫」，但本檔**最前段**（契約表上方、列出全部機制值供讀者查閱的那句「機制欄的值：facade、in-process、ws、http、schema、types、env、seed、dom、test-target」）仍只列 10 個值，沒有加入 `mcp`。`mcp` 只出現在修訂 1 區塊自己的說明段與契約表列裡，不在這份作為全檔術語總表的清單中，讀者若只看那句定義會誤以為機制值仍是 10 個 | 在契約表上方「機制欄的值」那句補上 `、mcp（MCP 協定的工具宣告）`，使它與修訂 1 的契約表一致 | New |

### Summary

本輪範圍是 24 條契約中新增的 7 條與擴充的 4 條既有消費端。以腳本核對了全部機械可驗證的事實：`unit-of-work-dependency.md` 的 21 條新邊逐一映射到本輪 7 條契約與 4 條擴充列，**無缺邊、無發明邊**；26 個 fenced YAML 區塊（21 shared-schema + 4 OpenAPI + 1 AsyncAPI）**全部是合法 YAML**；21 個 shared-schema 區塊**全部**含 `[C7]` 要求的三個 behaviour 鍵；契約總數 20 K + 4 X = 24 無誤；46 條單元依賴邊整體**無環**；`[C1]`=C 唯一授權門面原則、`[C7]` 的同進程契約形式、`[CD1]`–`[CD4]` 四題定案在逐條規格裡皆有對應落點，兩層 facade（`K-16`／`K-17`）的責任分工概念本身合理、`X-04` 對 `OQ-15`／`OQ-16` 的部分契約取捨誠實、未把 2.9 的 Bolt 排序決定寫進本站。

但本輪的核心風險恰恰出在它自己最自豪的那一項——「逐字核對」——本身不可靠：對既有端點兩道既有守門的行號引用（經本輪「重新核對」後仍然錯）、對 `requirements.md` 兩處引用的行號（皆差 5 行、且不在自檢涵蓋範圍內），以及 `K-16` 兩層 facade 責任切分區塊裡把 `U20_layer`誤植為 `U17_layer`（一個與本契約無關的 CI 無障礙單元）。三項皆為具體、可重現的事實錯誤，而非架構判斷上的分歧；其中兩項正是這個 intent 的規則層反覆記載過的「內容對、定位錯」形狀，而且是在自稱已修正之後仍然發生。3 項 Major、1 項 Minor，依驗證規則（>2 Major 即 NOT-READY）判定 **NOT-READY**。建議修正後的下一輪只需覆核這四處引用與命名，不需重新審查契約的結構或授權模型本身。
