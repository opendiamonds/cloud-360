## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Iteration:** 1

### Summary

`security-design.md` 與 `traceability.json` 把 `NFR5.1`–`NFR5.7` 逐一轉成機制、失敗語意與可測判準，並與已落地的 `dump_ws_contract.py`、`brain_ws_contract.py`、`ci.yml`、`frontend/package.json`、`check-ws-types.mjs`、`eslint.config.js` 核對後大體一致（fail-closed 四情形、`npx --yes` 已移除、`openapi-typescript` 精確釘 `7.13.0`、`REQUIRED_TEXT` 的 `ci.yml` 四詞條、`BR1.5` 以 `model_validator` 落在契約模組內、`ADR-0019` 檔案存在）。但有兩處實質缺口：(1) 白名單斷言宣稱「由構造封閉」，實際上客戶端物件清單與白名單鍵兩份都是手維護、且都不是由 `_CLIENT_PAYLOAD_BY_TYPE` 推導，新增客戶端 payload 而兩份都漏掉時不會紅燈；(2) `NFR5.6` 的機械檢查被設計刻意交給 code-generation 而無人承接，現行 CI 的「Spec must not be served statically」只比對 `openapi*` 檔名，抓不到 `ws-contract.json`。兩項皆 Major、共 2 項，未超過 2 項門檻，故判 READY；其餘為 Minor。

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|----|----------|----------|---------|-----------------|--------|
| R-01 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-design/security-design.md > §五「設計解」與 §二 IAM 列（「由構造封閉」） | 設計宣稱白名單「由構造封閉：任何新欄位都會紅燈」。已逐行核對 `backend/scripts/dump_ws_contract.py:187-215` 與 `backend/services/brain_ws_contract.py:844-852`：`assert_client_field_whitelist` 只比對 `CLIENT_FACING_MODELS`（契約模組內手寫元組）與 `CLIENT_FIELD_WHITELIST`（dump 腳本內手寫 dict）兩份清單的鍵是否相等，兩者都不是由 `_CLIENT_PAYLOAD_BY_TYPE`／`WsClientPayload` 推導。`BR1.4`（`assert_type_payload_parity`）只比對 type 列舉與 `Payload` 結尾的 schema 名稱，不連到 `CLIENT_FACING_MODELS`。所以新增一個客戶端 type 與其 payload（含一個身分等價欄位，如 `actor`）而兩份清單都沒補時，`BR1.4` 通過、白名單通過、`extra="forbid"` 只擋該 payload 以外的欄位，缺口成立：封閉性只對「已登錄物件的欄位」成立，不對「物件集合」成立。`code-summary.md` 另宣稱「新增一個客戶端物件而忘了白名單它也會紅燈」，只在只漏白名單時成立，兩份都漏時不成立。 | 把 `CLIENT_FACING_MODELS` 改為由 `_CLIENT_PAYLOAD_BY_TYPE` 的值加 `WsClientEnvelope` 推導（或在 dump 斷言中加「`schemas` 內所有 client 方向 payload 必須在白名單內」），並補一個注入新客戶端 payload 的突變測試；在此之前，設計文件與 code-summary 的「由構造封閉」「忘了白名單也會紅燈」兩句須收窄為實際範圍。哪一邊對：程式行為是事實，設計文字過寬。 | New |
| R-02 | Major | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-design/security-design.md > §七表格 `NFR5.6` 列（「本站不指定落點」）與 nfr-design/traceability.json > NFR5.6 | `NFR5.6`（規格檔不得被公開讀取，ADR-0006 network exposure／資訊揭露面）的兩條機械檢查被設計列為「由 code-generation 決定落點」，沒有擁有者與期限。已核對現況：`scripts/validate_repo_contract.py` 與 `backend/tests/test_ws_contract.py` 均無 `frontend/public` 或 `ws-contract.json` 的檢查；`.github/workflows/ci.yml` frontend job 的「Spec must not be served statically」步驟只對 `dist` 比對 `openapi*`／`*.openapi.*` 檔名，`ws-contract.json` 落進 `frontend/public/` 後會被 Vite 複製進 `dist/` 而此步驟仍綠燈。`code-summary.md` §四之八 已自承「查了、但沒有新增閘門」。結果是 `traceability.json` 把 `NFR5.6` 標 `OK`，實際保護只有「目前檔案放對位置」這個事實，沒有任何會在未來漂移時紅燈的機制，而同一份設計對 `NFR5.2`／`NFR5.3` 都要求了「會紅燈」的機制。 | 二擇一：(a) 在 `ci.yml` 該步驟的 `find` 加入 `-name 'ws-contract*'`，並在 `validate_repo_contract.py` 加「`frontend/public/` 不得含 `ws-contract.json`」檢查；(b) 在 `traceability.json` 把 `NFR5.6` 改標 `Deferred` 或 `Accepted risk` 並寫明缺口與擁有者。未做 (a) 或 (b) 前不得標 `OK`。 | New |
| R-03 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-design/security-design.md > §三（lint 規則形狀）與 §九（WsSubprotocol 兩欄位） | 設計文字相對已落地程式過時：`brain_ws_contract.py:494-503` 的 `WsSubprotocol` 已有第三欄 `protocolName`（`ADR-0020 C-1`，伺服器只回送它，使 token 不出現在回應標頭），設計的 network exposure 敘述與 lint 示意仍只談 `scheme`／`separator` 與單一 `bearer.${token}`；`eslint.config.js:11-34` 實際是三條選擇器（陣列後代、單一字串、單一模板），且為避免 flat config 後者取代前者而抽成共用常數並在 tests 與 object-picker 區塊展開，設計未預見「後續區塊覆寫 `no-restricted-syntax` 會無聲關掉本規則」這個失敗模式。這是程式比設計更強，不是矛盾。 | 在 `nfr-design` 的更正檔或 ADR-0020 追認處補一句：現行規格以 `eslint.config.js` 與 `WsSubprotocol` 現狀為準；並把「`no-restricted-syntax` 的覆寫會取代而非疊加」寫進 §三 的殘餘清單。 | New |
| R-04 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-design/security-design.md > §三「排序約束」表（`BrainPage.tsx:83`） | 前次 review-02 R-03 已提：§三仍以現在式陳述 `BrainPage.tsx:83` 持有字面量、規則啟用前須二擇一處理。`eslint.config.js:106` 的註解已寫明該 demo 頁隨 `U13` 移除，約束已不存在，行號引用已無對應內容。 | 在 §三補一句現況（約束已解除、正式消費端為 `U14`），避免後人照舊行號撲空。 | New |
| R-05 | Minor | aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-design/traceability.json > coverage NFR5.7 | `NFR5.7` 標 `OK`，target 只描述建置期白名單；設計 §五末自己寫明 `BR2.13` 的執行期拒絕（伺服器收到即回 `INVALID_REQUEST`）屬 `U13`。`code-summary.md` 對自家 traceability 已發現同型問題並改標 `Deferred`，本站的 traceability 未同步。此處只能依 `contract-summary.md` 的授權責任指向 `U13`，未開啟 `U13` 的檔案核實其實作。 | 將 `NFR5.7` 改標部分承接，target 同時寫出建置期落點與 `U13` 的執行期落點。 | New |

### Validation Tool Results

| Tool | Result | Interpretation |
|------|--------|----------------|
| 讀 `backend/scripts/dump_ws_contract.py` 全文 | `assert_type_payload_parity`、`assert_client_field_whitelist` 皆存在；`main` 對缺檔、斷言失敗皆 `return 1`，契約模組 import 未被 try/except 包住 | 設計 §六 的 fail-closed 四情形成立；R-01 的缺口來自清單非推導，不是 fail-open |
| 讀 `backend/services/brain_ws_contract.py` 全文 | `BR1.5` 為 `WsEnvelope._validate_raw`（`mode="before"`）；`CLIENT_FACING_MODELS` 為手寫七元組 | `BR1.5` 落點與設計 §四 一致；R-01 成立 |
| 讀 `frontend/package.json`、`frontend/scripts/check-ws-types.mjs`（grep `npx`） | `openapi-typescript` 精確釘 `7.13.0` 於 `devDependencies`，兩個 `gen:*` 腳本無 `npx --yes`，`check-ws-types.mjs` 失敗路徑 `process.exit(1)` | `NFR5.2` 成立 |
| 讀 `scripts/validate_repo_contract.py` 第 134-154 行 | `REQUIRED_TEXT` 含 `.github/workflows/ci.yml` 與四個閘門指令字串 | `NFR5.3` 成立 |
| 讀 `.github/workflows/ci.yml` | 兩道 WS 閘門步驟存在，backend 步驟無 `env:`；「Spec must not be served statically」僅比對 `openapi*` | `NFR5.1` 成立；R-02 成立 |
| 讀 `frontend/eslint.config.js` | `no-restricted-syntax` 為 `error` 級，三條選擇器，tests 與 object-picker 區塊展開同一常數 | `NFR5.4` 的消費端強制成立；R-03 為文字落差 |
| 列 `inception/decisions/` 找 `0019` | `0019-ws-contract-gates-and-generator-supply-chain.md` 存在 | 設計 §九 對 `ADR-0019` 的引用可解析 |
| 跨單元核實 | 未開啟 `U13` 或其他單元的檔案（審查範圍限制） | `BR2.13` 執行期層與 `U13` 的對接僅依共享契約，見 R-05 |
