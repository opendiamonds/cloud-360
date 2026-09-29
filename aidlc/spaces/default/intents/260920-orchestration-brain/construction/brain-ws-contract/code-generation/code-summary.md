# Code Summary — `U2 brain-ws-contract`（`spec`）

<!-- Stage: code-generation（Construction 3.5）· Unit: brain-ws-contract · kind: spec -->

方法論為 **`test-after`**（`AIDLC-TESTING-CONTRACT: sha256:1f0b6822…`）：每一個適用的
可測層先實作、再寫並跑該層的測試。十一個步驟全部執行完畢，計畫檔內的核取方塊已逐項勾選。

---

## 一、檔案清單（14 個應用程式來源路徑）

`source-manifest.json` 為正式來源，本表附上每一個路徑的理由。

### 新建（7）

| 路徑 | 為什麼 |
|---|---|
| `backend/services/brain_ws_contract.py` | 契約的**唯一人手改的真實來源**：23 個 schema（3 envelope ＋ 2 列舉 ＋ 15 payload ＋ 2 子實體 ＋ `WsSubprotocol`），含 `BR1.2`／`BR1.5`／`BR1.6`／`BR2.1`／`BR2.4` 的執行期 validator |
| `backend/scripts/dump_ws_contract.py` | 第一道閘門：把契約 dump 成 `ws-contract.json`，`--check` 斷言「規格檔 == 程式碼」，並承載 `BR1.4` 與 `NFR5.7` 兩條建置期斷言 |
| `backend/tests/test_ws_contract.py` | 契約模型的 7 個不變量測試 |
| `backend/tests/test_dump_ws_contract.py` | dump 腳本的 6 個閘門語意測試 |
| `ws-contract.json` | 衍生物 1（repo 根，**不得手改**——`BR4.1`；**不得**進 `frontend/public/`——`NFR5.6`） |
| `frontend/src/types/ws-contract.d.ts` | 衍生物 2（470 行，由衍生物 1 產生，**不得手改**） |
| `frontend/scripts/check-ws-types.mjs` | 第二道閘門：重產型別檔並逐位元比對，另承載 `BR4.4` 的註解保留斷言 |

### 修改（7）

| 路徑 | 改了什麼 |
|---|---|
| `frontend/package.json` | `devDependencies` 新增 `"openapi-typescript": "7.13.0"`（**精確釘選**）；`gen:types` 移除 `npx --yes` 與版本字串；新增 `gen:ws-types`／`check:ws-types`；新增一條 `overrides`（見 §四之一） |
| `frontend/package-lock.json` | 產生器首次進 lockfile（`integrity` 為 `sha512-EFP392gcqXS7…`）。落地前 `grep -c 'openapi-typescript' package-lock.json` 為 **0**，現為 **4** |
| `frontend/scripts/check-api-types.mjs` | `GENERATOR` 常數與 `execFileSync('npx', ['--yes', …])` 改為本地解析；`:19–21` 那段「兩處若不一致」的註解已作廢並**改寫成新的事實** |
| `frontend/eslint.config.js` | 新增 **error 級** `no-restricted-syntax`（三條選擇器，`ADR-0019 §5`） |
| `frontend/src/pages/BrainPage.tsx` | 第 83 行的 `` [`bearer.${token}`] `` 改為由產生的型別取值（衝突裁決 (a)） |
| `.github/workflows/ci.yml` | frontend job 新增 `npm run check:ws-types`；backend job 新增 `python scripts/dump_ws_contract.py --check`。型別閘門數 **2 → 4** |
| `scripts/validate_repo_contract.py` | `REQUIRED_TEXT` 新增 `.github/workflows/ci.yml` 一鍵，詞條涵蓋**四道**閘門的指令字串（`ADR-0019 §4`） |

### 刪除（0）

本單元沒有刪除任何檔案。

### 一個**沒有**出現在清單裡的檔案，以及它為什麼重要

`frontend/src/types/api.d.ts` **不在清單內**，因為 `ADR-0019 §2` 要求的一次性複驗
**實測無差異**：以 lockfile 鎖定的 `7.13.0` 重產出來的 `api.d.ts` 與 `npx --yes` 時代
committed 的那一份**逐位元相同**（`diff` 零輸出）。`nfr-requirements §九` 與
`tech-stack-decisions §五` 都把「兩者是否逐位元相同」誠實列為**未實測**的開放項——
**本站已實測，結論是相同**，該開放項可結案。

---

## 二、Step 7：兩個不適用的可測層（明文記載，不靜默略過）

Testing Contract 的 `plan_profile.testable_layers` 列五層，其中兩層對本單元不適用。
逐項寫出理由而非省略：

| 層 | 判定 | 理由（可機械複驗） |
|---|---|---|
| **Repository / data access** | **不適用** | 本單元沒有任何資料存取。可複驗：`grep -nE 'import httpx\|HTTPException\|Session\|sqlalchemy\|fastapi\|psycopg2\|logging' backend/services/brain_ws_contract.py` 唯一命中落在 docstring 第 10 行（那一行正是宣告這些東西不存在的句子），程式碼區零命中。契約模組只 import `collections.abc`、`enum`、`typing` 與 `pydantic` |
| **API / endpoint** | **不適用** | 本單元不新增任何 HTTP 或 WebSocket 端點。`/api/brain/ws` 是 `U13 brain-gateway` 的交付。可複驗：`openapi.json` 未被本單元改動（不在 `source-manifest.json` 內），CI 的 OpenAPI 漂移閘門本輪維持綠燈 |

其餘三層皆已執行：**Data model／database behavior**（Step 3–4）、**Business logic**
（Step 5–6）、**Frontend behavior**（Step 8–9）。

---

## 三、六項突變驗證的逐項結果

計畫要求五項（`M1`–`M5`）。**實際做了六項**——`M2` 的規定突變會在 import 時就被
`BR1.6` 的窮盡性斷言擋下，波及範圍大於預測的 `(4)(5)`，故另加一項外科式的 `M2b`
證明那兩條斷言**本身**真的在守門。每一項都機械確認「檔案內容真的變了」，理由是本 repo
踩過 `_SERVICE_ABBREVIATIONS = {} or {...}`——`or` 回傳右側，突變根本沒作用而測試照綠。

| # | 突變內容（逐字） | 預期轉紅 | 實際結果 |
|---|---|---|---|
| **M1** | `backend/services/brain_ws_contract.py`：`if type_value in _TERMINAL_TYPE_VALUES:` → `if False:`（整段 `BR1.5` 檢查失效） | `(2)(3)` | ✅ **紅燈，恰為 (2)(3)**。`exit=1`，4 個 subTest 失敗：`(2)` 兩個（`type='done'`／`type='error'`）為 `AssertionError: ValidationError not raised`；`(3)` 兩個為 `AssertionError: 'BR1.5' not found in '1 validation error for WsEnvelope\nturnId\n  Field required…'`。`(1)(4)(5)(6)(7)` 維持綠。還原後 `exit=0` |
| **M2** | 同檔：`_TURN_SCOPED_TYPES … = frozenset(` → `frozenset()`（輪次型別集合改為空集合） | `(4)(5)` | ✅ **紅燈，但波及全部 7 個**。`RuntimeError: BR1.6 違反：輪次與非輪次兩集合未窮盡九個伺服器 type，未分類的有 ['clarify', 'cost_card', 'done', 'error', 'token']` 在 **import 時**拋出，故整個模組載入失敗、7 個測試全部 error（`(4)(5)` 是其真子集）。**這是正確行為而非測試弱點**：`BR1.6` 逐字要求「兩個集合互斥且聯集等於九個 type 的全部——可機械斷言」，把它放在 import 時 fail-fast，是為了不讓「某些 type 完全不受 turnId 檢查」這件事在執行期毫無訊號地存在。還原後 `exit=0` |
| **M2b** | 同檔：在互斥斷言前插入 `_TURN_SCOPED_TYPES, _SESSION_SCOPED_TYPES = _SESSION_SCOPED_TYPES, _TURN_SCOPED_TYPES`（兩集合互換，**保持窮盡與互斥**，故繞過 import 時斷言） | `(4)(5)` | ✅ **紅燈，恰為 (4)(5)**。`FAILED (failures=2, errors=2)`；`(4)` `AssertionError: 4 != 5`、`(5)` `AssertionError: 5 != 4`（兩條斷言的集合大小檢查先命中），其餘 5 個維持綠。還原後 `exit=0` |
| **M3** | `backend/scripts/dump_ws_contract.py`：在 `assert_type_payload_parity` 的 docstring 之後插入 `return`（整條 `BR1.4` 斷言失效） | `(4)` | ✅ **紅燈，恰為 (4)**。`FAILED (failures=1)`：`test_parity_assertion_catches_a_type_without_a_payload` 的 `AssertionError: ContractAssertionError not raised`。還原後 `exit=0` |
| **M4** | 同檔：`if actual != allowed:` → `if not allowed.issubset(actual):`（白名單由**相等**鬆成**只要是子集就通過**） | `(5)` | ✅ **紅燈，恰為 (5)**。`FAILED (failures=1)`：`test_whitelist_assertion_catches_an_undeclared_client_field` 的 `AssertionError: ContractAssertionError not raised`（注入的 `onBehalfOf` 讓 actual 變成 expected 的超集，子集判定隨即放行）。還原後 `exit=0` |
| **M5** | 同檔：`json.dumps(build_spec(), indent=2, sort_keys=True, ensure_ascii=False)` 拿掉 `sort_keys=True` | `(6)` | ✅ **紅燈，恰為 (6)**。`FAILED (failures=1)`：`test_render_is_byte_identical_and_key_order_is_sorted` 的 `AssertionError: Lists differ: ['id,label,capability,confidence', 'estima[293 chars]nts'] != []`。**這一項是 `{} or {...}` 那個陷阱的同型**：只比「連跑兩次相同」**抓不到** `sort_keys` 被拿掉（同一行程內 dict 插入順序穩定，兩次輸出仍會一樣），真正鎖住 `BR4.2` 的是測試裡以 `object_pairs_hook` 走訪每一個 JSON 物件的鍵序斷言。還原後 `exit=0` |

### Step 9 的四項閘門突變（前端層，`test-after` 的「測試」就是閘門本身）

| # | 突變 | 實際結果 |
|---|---|---|
| **S9-1** | 手改 `frontend/src/types/ws-contract.d.ts` 一個字元（`export type webhooks = Record<string, never>;` → `…;;`） | ✅ `npm run check:ws-types` `exit=1`：「型別檔已漂移：`src/types/ws-contract.d.ts` 與 `../ws-contract.json` 不一致」。還原後綠 |
| **S9-2** | 拿掉契約模組 `WorkItem.sideEffect` 的 `description=` → 重新 dump | ✅ 規格檔內該欄位只剩 `['title', 'type']`（`description` 消失），`npm run check:ws-types` `exit=1`：「`BR4.4` 違反：由 `../ws-contract.json` 重產的型別檔 的 sideEffect JSDoc 沒有 @description 段——通常表示後端 Pydantic 欄位的 description= 被拿掉了。」還原三份後綠。**注意這一項的失敗模式**：兩個型別檔仍然逐位元一致，純比對的漂移檢查看不到它，所以 `BR4.4` 需要自己一條斷言 |
| **S9-3** | 把 `BrainPage.tsx` 改回 `` [`bearer.${token}`] `` | ✅ `npm run lint` `exit=1`：`98:55 error subprotocol 必須由 ws-contract.d.ts 的 WsSubprotocol 取值，不得寫死字串（ADR-0019 §5／NFR5.4）。 no-restricted-syntax`（另附帶兩個 `no-unused-vars` error，因為兩個常數變成沒人用）。還原後 `0 errors, 2 warnings` |
| **S9-4** | `WsSubprotocol.scheme` 改為 `Literal["brain"]` → 重新 dump → 重產型別檔 | ✅ 型別檔變成 `scheme: "brain";`，`npm run build` `exit=2`：`src/pages/BrainPage.tsx(36,7): error TS2322: Type '"bearer"' is not assignable to type '"brain"'.` 還原三份後 build 綠。**這一項證明 `NFR5.4` 的整條保護真的成立**——不只是型別檔裡有一個字面值，而是「後端改值 → 前端編譯失敗」這條鏈實際跑通過一次 |

### `S10` 閘門存在性的突變（四道各一次）

把 `ci.yml` 的閘門步驟逐一替換成 `echo GATE-DELETED-BY-MUTATION`，四次皆
`python3 scripts/validate_repo_contract.py` `exit=1` 並**指名缺哪一條**：

- `ERROR: Required contract text missing: .github/workflows/ci.yml missing 'npm run check:ws-types'`
- `… missing 'scripts/dump_ws_contract.py --check'`
- `… missing 'npm run check:types'`
- `… missing 'scripts/dump_openapi.py --check'`

四次還原後皆 `Cloud-360 repository contract validation passed.`。**落地前，把
`npm run check:types` 那一步從 `ci.yml` 刪掉是零偵測的**（`ci.yml` 雖在
`REQUIRED_FILES` 內，`REQUIRED_TEXT` 卻沒有它那一鍵）。

---

## 四、關鍵實作決定

### 之一、`frontend/package.json` 多了一條 `overrides`（計畫沒有預見的必要改動）

`openapi-typescript@7.13.0` 宣告 `peerDependencies: typescript ^5.x`，而本專案用
`typescript ~6.0.2`（實際解析到 `6.0.3`）。把它放進 `devDependencies` 之後，
`npm install` 與 `npm ci` **雙雙 ERESOLVE 失敗**：

```
npm error Could not resolve dependency:
npm error peer typescript@"^5.x" from openapi-typescript@7.13.0
```

這是一個**只有在真的把它鎖進 lockfile 時才會浮現的事實**——`npx --yes` 不對專案樹
做 peer 解析，所以既有實作從未撞到它。它本身就是「未鎖定」的另一面證據。

三條路都試過，採最小範圍的那一條：

| 方案 | 結果 |
|---|---|
| `npm install --legacy-peer-deps` | lockfile 產生成功，但**之後的 `npm ci` 仍失敗**（實測 `npm ci --dry-run` 回同一個 ERESOLVE），而 CI 跑的是不帶旗標的 `npm ci`。不可行 |
| `.npmrc` 設 `legacy-peer-deps=true` | 可行，但它**對整個專案的所有依賴**關閉 peer 檢查——一個為了單一套件而放寬全域的副作用。不採 |
| **`overrides: { "openapi-typescript": { "typescript": "$typescript" } }`** | **採用**。只改這一個套件看到的 `typescript`（指向根專案宣告的同一版），peer 檢查對其餘依賴維持有效。實測 `npm install` 與 `npm ci --dry-run` 皆通過，且產生的 `api.d.ts` 與 committed 版**逐位元相同** |

JSON 不能寫註解，所以這條 `overrides` 的**理由寫在
`frontend/scripts/check-api-types.mjs` 的檔頭**——改 `gen:types` 的人一定會讀到那支腳本。
`ADR-0019 §2` 沒有預見這個衝突；本段即為其落地補充（不回改已核可的 ADR）。

### 之二、產生器的本地解析路徑不能用 `require.resolve('openapi-typescript/bin/cli.js')`

該套件的 `exports` 有一條 `"./*.js": "./*.mjs"` 改寫規則，會把實際存在的 `bin/cli.js`
解析成**不存在的** `bin/cli.mjs` 並拋 `MODULE_NOT_FOUND`。兩支 gate 腳本改為
resolve `openapi-typescript/package.json`、讀它自己宣告的 `bin` 欄位再組路徑——那是
唯一不依賴那張 map 的取法，而且它由套件自述而非我們猜。

### 之三、`BR1.5` 必須是 `mode="before"` 的 model validator，不能是 `mode="after"`

若放 `mode="after"`，終止事件的 payload 缺 `turnId` 時 `DonePayload` 自己的必填檢查
會**先**擋下並回報 `Field required`——那個訊息沒有指出違反的是 `BR1.5`（兩份 `turnId`
的一致性），讀訊息的人只會以為漏填了一個欄位，不知道那個欄位的值受另一個欄位約束。
測試 `(3)` 因此斷言錯誤訊息**含 `BR1.5`** 而不只是「拋了 `ValidationError`」，而那正是
`M1` 能被看見的原因。

### 之四、`BR1.2` 補了一條執行期 validator（計畫未列，但缺了它會有一條靜默路徑）

產生的 TypeScript 把 `WsEnvelope.payload` 表達為**九個 `$ref` 的平聯集**（見 §五之一），
沒有判別器。所以 `type="ready"` 配一個 `TokenPayload` 在型別上完全合法。處置是在契約
模組內以 `_SERVER_PAYLOAD_BY_TYPE`／`_CLIENT_PAYLOAD_BY_TYPE` 兩張表把 raw payload
綁到**唯一**對應的模型（`mode="before"` 綁定 ＋ `mode="after"` 的 `isinstance` 覆核），
不靠 Pydantic 的 smart union 去猜——猜中與猜錯在輸出上沒有差別。

### 之五、`extra="forbid"` 是 `BR2.12`／`BR2.13` 的第一層，不只是衛生

Pydantic 的預設是 `extra="ignore"`。若沿用預設，客戶端偷帶 `turnId` 會被**靜默丟掉**，
而客戶端會以為自己成功指定了輪次——`BR2.13` 逐字說「靜默忽略比拒絕更糟」。故除
`WsUnvalidatedEnvelope`（它的存在目的就是寬鬆解析不同版本的入站訊息）之外，全部
契約模型皆 `extra="forbid"`。測試 `(6)` 對 `turnId`／`userId`／`role`／`token`／
`actor`／`onBehalfOf` 六個欄位各驗一次。

### 之六、`WsUnvalidatedEnvelope` 的轉換義務寫進了 class docstring

它是寬鬆模型，客戶端偷帶的 `turnId` 在這一層會被丟掉。若 `U13` 之後用「本模型的欄位」
重組一個 dict 再餵給 `WsClientEnvelope`，`extra="forbid"` 就永遠看不到那個欄位，
`BR2.13` 的執行期拒絕隨即失效。處置是在該 class 的 docstring 明文要求
**以原始 dict 轉換**。這是本站發現的一個實作陷阱，落點 `U13`。

### 之七、lint 規則的可達性實測（自檢第 1 項：每條規則先驗它抓得到）

新增一條「偵測 X」的規則之前必須先確認 X 可達，否則它是死碼而在文件上長得像已解決。
三條選擇器逐一以 `eslint --stdin` 對六種呼叫形狀實跑，數字是 `no-restricted-syntax`
的命中數：

| 呼叫形狀 | 命中 | 判定 |
|---|---|---|
| `new WebSocket(u, 'bearer.x')` | **1** | 擋下（單一字串形式，選擇器 2 生效） |
| ``new WebSocket(u, `bearer.${t}`)`` | **1** | 擋下（單一模板形式，選擇器 3 生效） |
| `new WebSocket(u, ['bearer' + '.' + t])` | **2** | 擋下（後代選擇器抓到兩個字面量——直接子選擇器會漏） |
| ``new WebSocket(u, [`bearer.${t}`])`` | **1** | 擋下（即 `BrainPage.tsx` 落地前的形狀） |
| `new WebSocket(u, [S + P + t])` | **0** | **放行**（現行正確寫法） |
| `new WebSocket(u)` | **0** | **放行**（`useCollaboration.ts:25` 無第二引數，不受影響） |

三條選擇器全部有實際命中，沒有一條是死規則；正確寫法與既有無第二引數的呼叫皆不誤報。

### 之八、`NFR5.6` 的兩條機械檢查：本站查了、但沒有新增閘門

`nfr-design §七` 把落點留給 `code-generation`。三項皆實查通過：`ws-contract.json` 不在
`frontend/public/`；`grep -rn "ws-contract.json" frontend/src/` 為空；`frontend/dist/`
內 `find -name 'ws-contract*'` 零命中。**沒有把它加成新的 CI 步驟**，理由是計畫的
Step 10 明列該加哪幾件、不含這一項，而現有的「Spec must not be served statically」
步驟只比對 `openapi*` 樣式。**這是一個已知缺口**：今天 `ws-contract.json` 沒有結構性
保護不被移進 `frontend/public/`。建議的最小修法是把該步驟的 `find` 樣式擴為
`\( -name 'openapi*' -o -name 'ws-contract*' \)`，落點為下一個碰 `ci.yml` 的單元
（`U13` 或 `ci-pipeline`）。

---

## 五、與計畫的偏離（逐項）

| # | 偏離 | 為什麼 |
|---|---|---|
| **D-1** | Step 8 寫「以 `` `${SCHEME}${SEP}${token}` `` 組出 subprotocol」，**實作改為 `SUBPROTOCOL_SCHEME + SUBPROTOCOL_SEPARATOR + token`** | **計畫的兩個步驟互相牴觸**：同一個 Step 8 要求的 lint 規則（`ADR-0019 §5`：第二引數不得出現字串字面量**或模板字面量**）會把 `` `${SCHEME}${SEP}${token}` `` 這個模板字面量一起抓進去，而 Step 9 的第三項要求「還原後 `npm run lint` 必須綠」。以字串相加組出的運算式沒有任何字面量節點，兩個要求同時成立。**已實測兩端**：改回模板字面量時規則紅燈（`S9-3`），現行寫法 `0 errors` |
| **D-2** | lint 選擇器由設計文件示意的**直接子**（`> ArrayExpression > :matches(...)`）改為**後代**（`> ArrayExpression :matches(...)`），並加兩條涵蓋「第二引數是單一字串」的形式 | 直接子選擇器放過 `['bearer' + '.' + token]`（字面量被包在 `BinaryExpression` 底下）；只擋陣列則放過 `new WebSocket(url, 'bearer.x')`——WebSocket 的第二引數可以是字串或字串陣列。兩者都是與被擋形狀**等價**的繞道。`ADR-0019 §5` 已接受的殘餘（「先把字串存進變數再傳入」）不變 |
| **D-3** | 測試檔**首行**是 module docstring，`import tests.helpers` 是**第一個 import** | `unit-test-instructions.md` 寫「首行必須是 `import tests.helpers`」。本 repo 四個既有先例（`test_database_security.py:8`、`test_diagram_icons.py:20`、`test_llm_provider.py:12`、`test_wa_rule_engine.py:10`）全部是「docstring 在前、該 import 為首個 import」。照字面做會讓 docstring 退化成一個 import 之後的裸字串運算式，即死碼——而 `team.md` 逐字把「零 TODO／無死碼區塊」列為應保護的既有紀律。功能意圖（在任何 DB import 之前裝 psycopg2 樁）兩種寫法都滿足 |
| **D-4** | 十三個測試各加了結構化規格註解（`@purpose`／`@given`／`@step`／`@pass`／`@story`／`@note`） | 計畫沒有要求，但 `project.md ## Mandated` 的 `tcms-test-cases` 必做 3b 對「每個新增或改動的自動化測試」都要求它，而那個 stage 是本 intent construction 的 **blocking** 關卡。現在寫成本為零，之後補要重讀十三個測試。`@api`／`@ui` **刻意缺席**並在兩個檔的 docstring 說明理由——本單元既無端點也無頁面，依 `project.md` 的既有更正「寧可缺、不得捏造」 |
| **D-5** | 突變驗證做了六項（`M1`–`M5` ＋ `M2b`），另加 `S9`／`S10` 共五次閘門突變 | 見 §三：`M2` 的規定突變波及範圍大於預測值，`M2b` 補上「恰為 `(4)(5)`」的證據。多做不少做 |
| **D-6** | `frontend/package.json` 多一條 `overrides` | 見 §四之一。不加則 `npm ci` 無法安裝產生器，`NFR5.2` 整條無法落地 |
| **D-7** | `BR1.2` 多了一條執行期 validator | 見 §四之四。計畫 Step 3 未列，但缺了它有一條型別上合法的靜默路徑 |

**沒有偏離的部分（明確記載）**：衝突裁決採計畫指定的 **(a)**（改 `BrainPage.tsx`，不刪
demo 頁）；三個 envelope、15 個 payload、2 個子實體、`WsSubprotocol` 的數量與名稱逐一
照 `entities.md`；序列化形狀逐字照 `BR4.2`；`ws-contract.json` 在 repo 根；dump 腳本
**不 import `main`**（實測：`ci.yml` 的新步驟不需要 `DATABASE_URL`／`JWT_SECRET` env
即可執行）；白名單旁已寫下 `ADR-0019 §6` 的適用前提註解。

---

## 六、測試結果與覆蓋率門檻的逐項回報

`unit-test-instructions.md` 逐字要求「這一點必須在 `code-summary.md` 逐項回報，不得以
『測試都綠了』帶過」。

### 本單元專用指令與其輸出

```
cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ws_contract tests.test_dump_ws_contract -v
```

```
----------------------------------------------------------------------
Ran 13 tests in 0.067s

OK
```

十三個測試的組成（`7 ＋ 6`，與 `unit-test-instructions.md` 的目標數相符）：

| 元件 | 數 | 測試方法 |
|---|---|---|
| `brain_ws_contract.py` | 7 | `test_terminal_event_with_matching_turn_ids_is_accepted`、`test_terminal_event_with_mismatched_turn_ids_is_rejected`、`test_terminal_event_without_payload_turn_id_is_rejected`、`test_turn_scoped_type_requires_non_null_turn_id`、`test_session_scoped_type_forbids_turn_id`、`test_client_envelope_rejects_turn_id_and_identity_fields`、`test_subprotocol_fields_are_literals_and_reject_other_values` |
| `dump_ws_contract.py` | 6 | `test_check_fails_closed_when_spec_file_is_absent`、`test_check_passes_when_spec_matches_the_models`、`test_check_detects_a_hand_edited_spec_file`、`test_parity_assertion_catches_a_type_without_a_payload`、`test_whitelist_assertion_catches_an_undeclared_client_field`、`test_render_is_byte_identical_and_key_order_is_sorted` |

### 全專案迴歸

```
cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
Ran 378 tests in 27.399s
OK
```

（`378 − 13 = 365` 為落地前的推得值，不是另外量測的；新增 13 個，**零迴歸**。）

### `team.md` 三項二元可判規則的適用性

| 規則 | 判定 | 依據 |
|---|---|---|
| **A** `role_permissions` 變更需 allow/deny 雙向測試 | **不適用** | 本單元不動 RBAC seed。`git status` 顯示 `rbac_seed_data.py`／`schema_rbac.sql` 皆未改 |
| **B** 新增／修改 HTTP 端點需 `TestClient` 測試 | **不適用** | 本單元不新增任何端點；`openapi.json` 未改動 |
| **C** 前端資料形狀變更需 e2e 斷言 | **不適用** | 本單元不改任何使用者可見的資料形狀。`BrainPage.tsx` 的改動只換了 subprotocol 字串的**來源**（字面量 → 型別常數），組出來的值不變（`bearer.` ＋ token），畫面零變化 |

三項皆不適用，故本單元的實際門檻是**上表 13 個測試 ＋ 五（實際六）項突變驗證全部做到**
——兩者皆已完成，逐項結果在 §三。

### 80% 覆蓋率門檻

`org.md` 宣告最低 80% line coverage。本 repo **目前無覆蓋率量測機制**（無 `.coveragerc`、
無 `coverage`／`pytest-cov`、CI 無 coverage step——`team.md` 逐字記載「既無法量測也無法
強制，是宣告而非閘門」）。**本單元不引入覆蓋率工具**（獨立的工具鏈決策，不由本單元
夾帶）。**這是一個未被量測的缺口，如實記載，不宣稱達標、也不下修門檻。**

### 其他閘門的落地後狀態（實跑）

| 閘門 | 結果 |
|---|---|
| `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |
| `python3 scripts/validate_env_contract.py` | `Cloud-360 environment configuration contract validation passed.` |
| `npm run lint` | `✖ 2 problems (0 errors, 2 warnings)`（`AssessmentPage.tsx:365`、`WorkspacePage.tsx:302`，皆為既有 `exhaustive-deps`） |
| `npm run build` | `✓ built in 833ms` |
| `python scripts/dump_openapi.py --check` | 規格檔與後端程式碼一致 |
| `python scripts/dump_ws_contract.py --check` | WS 契約規格檔與後端程式碼一致 |
| `npm run check:types` | API 型別檔與規格檔一致 |
| `npm run check:ws-types` | WS 契約型別檔與規格檔一致，且 `sideEffect` 的哨兵值說明仍在（`BR4.4`） |

`NFR5.2` 的可測判準逐項：`grep -c 'npx --yes' frontend/package.json frontend/scripts/*.mjs`
→ 全為 **0**；`grep -c 'openapi-typescript' frontend/package-lock.json` → **4**（非 0）；
以 `npm_config_offline=true` 執行 `npm run check:types` 仍成功（`npm ci` 之後不再取
registry）。

---

## 七、`ADR-0006` Security Baseline 四面向逐項判定（自檢第七項）

`project.md` 把這一項升為自檢第七項，並逐字記載它在 `domain-design`／
`units-generation` 兩站重犯過。

| 面向 | 判定 | 本站的實作處置 |
|---|---|---|
| **IAM** | **適用** | 兩層都落地了。**型別層**：`WsClientEnvelope` 無 `turnId` 欄位 ＋ 全部客戶端模型 `extra="forbid"`，使 `userId`／`role`／`token`／`actor`／`onBehalfOf`／`turnId` 皆不可構造（測試 `(6)` 六個欄位各驗一次）。**建置期層**：`dump_ws_contract.py` 的白名單斷言比對七個客戶端物件的欄位集合，且另斷言「契約宣告的客戶端物件集合 == 白名單的鍵」，使新增一個客戶端物件而忘了白名單它也會紅燈。`M4` 證明把相等鬆成子集會讓多欄位那一半靜默放行 |
| **Encryption** | **適用（處置全在別的單元）** | 本單元不引入連線、不持久化資料。唯一的否定式要求 `NFR5.6`（規格檔不得公開可讀）已實查通過（§四之八），但**沒有新增機械閘門**——那是一個已記載的缺口與其修法。對話內容的靜態加密是 `OQ-3`，落 `U5 memory-data` |
| **Network exposure** | **適用（本單元的主要安全面之一）** | `WsSubprotocol` 進契約使 token 的載體格式首次受保護，且 `S9-4` 實測證明「後端改值 → 前端 `npm run build` 紅燈」這條鏈真的通。消費端強制由 error 級 lint 規則承載（`S9-3` 實測紅燈）。**誠實記載未擋住的**：`AC8.1.3`（token 不得在 query string）本單元只擋了「token 放在訊息內」那一半，對 URL 零約束——實際擋它的是 `K-12` 的 `x-hard-constraints.token_transport`，落點 `U13`，故 traceability 標 `Deferred` |
| **Audit logging** | **適用（處置是「讓閘門的判決可信」）** | 本單元不產生執行期稽核記錄，它產生 **CI 的判決**。兩項處置：(1) 四道閘門執行的程式碼現由 lockfile ＋ `integrity` 雜湊鎖定（`NFR5.2`），綠燈開始構成證據；(2) 閘門的**存在**本身被 `REQUIRED_TEXT` 斷言，四道各實測過一次刪除即紅燈（`S10`）。`AC8.1.2`（走 WS 仍更新最後活動時間）本單元無型別手段，標 `Deferred` → `U13` |

**`ADR-0006` property-based testing hard constraint**：**不適用，附理由。** 該約束點名
IaC generator、cost calculator、agent routing 三類純計算模組，本單元不含其中任何一個。
更根本的是 `rules.md` 的 `category` 分佈中 `calculation` 實算為 **0**。本單元最接近純函式
的兩個候選是 `_pascal_case`（`work_items` → `WorkItems` 的單行對映）與 `BR1.5` 的兩值
相等比對，兩者都沒有值域可供性質測試。PBT 在本 intent 的落點是 `U11` 的 IntentRouter
門檻純函式與 `U6` 的 EmbeddingPort。

---

## 八、交給下游的三件事（不是遺漏，是有落點的缺口）

| # | 事實 | 為什麼重要 | 落點 |
|---|---|---|---|
| **H-1** | **`WsEnvelope.payload` 產生出來是平聯集，不是判別聯集**。實際輸出為 `payload: components["schemas"]["ReadyPayload"] \| components["schemas"]["TokenPayload"] \| …`（九個），`switch (msg.type)` **不會**把它收窄到對應的 payload 型別 | `tech-stack-decisions §九` 要求「`code-generation` 的第一步先跑一次完整 dump 並人工檢視，確認判別 union 真的可用」——**本站已檢視，結論是不可用**。它給的退路是「把 envelope 拆成九個具名型別的聯集」，但計畫 Step 3 明訂「三個 envelope」，故本站照計畫做並在此標出落差。伺服器側的 `BR1.2` 已由執行期 validator 鎖住（§四之四），**消費端側沒有型別保護**：前端拿到 `payload` 後必須自己以 type guard 收窄 | `U13`／`U14`。若要型別層的收窄，需一次上游決定把 envelope 拆成九個具名型別 |
| **H-2** | `ws-contract.json` 沒有結構性保護不被移進 `frontend/public/` | 現有的「Spec must not be served statically」CI 步驟只比對 `openapi*` 樣式。最小修法見 §四之八 | 下一個碰 `ci.yml` 的單元 |
| **H-3** | `WsUnvalidatedEnvelope` → `WsClientEnvelope` 的轉換必須餵**原始 dict** | 否則 `BR2.13` 的執行期拒絕會靜默失效（§四之六）。已寫進該 class 的 docstring | `U13` |

`K-02` 的三項擴充（`ready`、`select_clarify_candidate`、`WsSubprotocol`）已由
`ADR-0019` 作為上游追認的載體，本站不再另列。`BR2.14` 的一欄兩義可區分性缺陷已逐字
寫進 `SelectClarifyCandidatePayload` 的欄位說明，它是 `functional-design` 留給核可關卡
的 open item，本站不自行裁決。

---

## 九、Conductor 覆核（我自己重跑了什麼，以及哪一項自報被我更正）

本節由 conductor 寫，不是開發 agent 的自報。依 `project.md` 的既有教訓
（派工回報不得照單全收），逐項獨立重跑，時間 `2026-09-28T05:52:08Z`。

| 項 | agent 自報 | 我的獨立複驗 | 結果 |
|---|---|---|---|
| 本單元 13 個測試 | `Ran 13 tests … OK` | `cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ws_contract tests.test_dump_ws_contract` | **相符**，`Ran 13 tests in 0.063s OK` |
| 全套無迴歸 | `Ran 378 tests … OK`（365 → 378） | `python3 -m unittest discover -s tests` | **相符**，`Ran 378 tests in 27.536s OK` |
| `validate_repo_contract.py` | 綠 | 實跑 | **相符** |
| `validate_env_contract.py` | 綠 | 實跑 | **相符** |
| 第一道閘門（OpenAPI） | 綠 | `dump_openapi.py --check` | **相符**，「規格檔與後端程式碼一致。」 |
| 第一道閘門（WS） | 綠 | `dump_ws_contract.py --check` | **相符**，「WS 契約規格檔與後端程式碼一致。」 |
| `npm run lint` | `0 errors, 2 warnings` | `npx eslint .` | **相符**，兩個 warning 都是既存的 `exhaustive-deps` |
| 第二道閘門（API 型別） | 綠 | `npm run check:types` | **相符** |
| 第二道閘門（WS 型別）＋ `BR4.4` | 綠 | `npm run check:ws-types` | **相符**，訊息逐字含「且 sideEffect 的哨兵值說明仍在（BR4.4）」——`BR4.4` 的斷言確實是活的，不是只寫在計畫裡 |
| **`overrides` 讓 `npm ci` 不會 ERESOLVE** | 「`--legacy-peer-deps` 沒用、`overrides` 是最小修法」 | **實跑 `npm ci`（乾淨重裝）** | **相符，`EXIT=0`**。這是本站**最該實測的一項**——CI 跑的是裸 `npm ci`，若這裡錯了，之後每一個 PR 都紅燈。重裝後兩道型別閘門再跑一次仍綠，`node_modules/.bin/openapi-typescript` 存在，`package-lock.json` 對該套件命中數 **0 → 4** |
| ESLint 規則真的會擋 | 三種形狀的命中數 1／1／0 | 以 `eslint --stdin` 餵入四種寫法實測 | **相符**：模板字面量在陣列內 → error；裸字串第二引數 → error；`S + P + t` 常數相加 → **無 error**（正確寫法通得過）。規則有效且不誤傷 |
| `source-manifest.json` 完整 | 14 個路徑 | 與 `git status` 逐一比對 | **相符**：新增 7 ＋ 修改 7 ＝ 14，無未申報的改動路徑；record 目錄的變動正確地不列入（非應用程式來源） |

### 一項我自己先報錯、又自己更正的

我用 `grep -rn 'npx --yes' package.json scripts/` 得到 **2**，一度以為 agent 宣稱的
「零處 `npx --yes`」不實。逐行開啟後確認**兩個命中都在註解裡**
（`check-api-types.mjs:23`／`:25`，內容是在說明歷史與為何改掉），
可執行碼確實已無 `npx`——`:39` 逐字寫「本地解析：由套件**自己宣告的** bin 欄位推出入口路徑，
不經 PATH、不經 npx」。**agent 的宣稱成立，是我的 grep 太粗。** 記在此處而非默默改掉，
因為「覆核者自己誤判」與「被覆核者造假」在紀錄上必須分得開。

### 三項自報我**沒有**獨立複驗，如實標示

| 項 | 為何沒驗 |
|---|---|
| 六項突變驗證（M1／M2／M2b／M3／M4／M5）的逐項紅燈 | 重跑需反覆改動受測原始碼，而本站接下來就要送審——審查收據綁 source fingerprint，改動會讓議決記不進去。**改為在審查 brief 中點名要求審查者自行挑一項複驗** |
| Step 9 的四項閘門突變（含 S9-4 的 `Literal["brain"]` 端到端證明） | 同上，需重產衍生物 |
| Step 10 的四項 `REQUIRED_TEXT` 突變 | 同上，需改 `ci.yml` |

這三項是本站**未經第二人查證**的部分，不得在摘要中寫成「全部已驗證」。

### 一項需要下游注意的環境副作用

`npm run build` 重寫了 `frontend/dist/`。它被 `frontend/.gitignore:11` 忽略，
`git status` 看不到它，但它**不在**引擎的 `SOURCE_FINGERPRINT_HARD_EXCLUDED_NAMES` 內。
本站在送審前不再執行任何 build；審查 brief 亦明文禁止審查者執行 build 或測試。

---

## 十、審查後的處置（attempt 2）

`code-generation` 審查 iteration 1 議決 **READY**（0 Critical、2 Major、1 Minor），
但使用者於核可關卡選擇 **Request Changes** 以修掉 R-01。理由不是議決有誤，
而是 R-01 的性質：它是**會讓下游漏做事的交接缺陷**，而修它必須動
`traceability.json`（`produces[]`），那會讓 READY 收據失效——所以正規路徑就是開新一輪。

### R-01（Major）— 已修

**發現**：`traceability.json` 把 `BR2.13` 標成純 `OK`，`target` 指向
`backend/tests/test_ws_contract.py`。但 `rules.md:289–296` 的 `statement` 有**兩半**：

| 半 | 內容 | 本單元能否承載 |
|---|---|---|
| 型別層 | 「客戶端訊息**不得攜帶** `turnId`」 | **能**，且已交付：`WsClientEnvelope` 與六個 client payload 皆無此欄位 |
| 執行期 | 「伺服器收到即視為協定違規：**拒絕該訊息**並回 `error(INVALID_REQUEST)`，**不得靜默忽略**」 | **不能**——本單元無執行期訊息處理迴圈 |

**為何是 Major 而非 Minor**：`traceability.json` 是給下游讀的**機器可讀交接檔**。
`U13` 打開它看到 `BR2.13: OK` 會得到「這條不用我做」的結論，那個執行期拒絕隨之靜默消失。
而同一份檔裡結構完全相同的 `BR1.3`（同一輪 `turnId` 相同）與 `BR2.5`（欄位相依）
**都已正確標為 `Deferred → U13`**——只有 `BR2.13` 不一致。寫在別處的散文補不回這件事。

**處置**：`BR2.13` 改標 `Deferred`，`target` 逐字寫出兩半的分工、型別層四個已交付的落點
（模組、測試、白名單斷言）、以及執行期那半的落點 `U13`。
覆蓋分佈由 32 `OK`／14 `Deferred` 變為 **31 `OK`／15 `Deferred`**。
**程式碼一個字元都沒動**——本輪只改這一個 JSON 條目。

### R-02（Major）— 實質面已補，機制面如實記載

**發現**：`required-sections` sensor 從未對本單元的三份 code-generation 文件自動 fire。
本站複驗屬實：audit shard 對 `code-generation-plan.md`／`unit-test-instructions.md`
的命中數為 **24**，而對照組 `brain-infra` 的 `infrastructure-specification.md` 為 **101**。

**處置**：手動補跑三份，結果逐一記錄——

| 文件 | H2 數 | findings |
|---|---|---|
| `code-generation-plan.md` | 7 | **0** |
| `unit-test-instructions.md` | 9 | **0** |
| `code-summary.md` | 8（本節後為 10） | **0** |

**文件本身沒有問題**；缺的是自動觸發這件事本身。本站**不修 sensor 的觸發機制**——
那是框架層行為，不屬本單元範圍，且 `project.md` 明文禁止以修改 `.claude/` 內的
upstream 檔來表達專案規則。如實記為一項**機制缺口**，留給下一次
practices-discovery 或框架升級處理。

### R-03（Minor）— 本站內已修，無殘留

計畫的 Step 8 要求以 `` `${SCHEME}${SEP}${token}` `` 組 subprotocol，
而**同一個 Step** 要求的 lint 規則禁止該引數出現模板字面量，Step 9 又要求 lint 綠。
**計畫自相矛盾，那是我規劃時的缺陷**，在此記錄而非淡化。
開發 agent 已改用 `SUBPROTOCOL_SCHEME + SUBPROTOCOL_SEPARATOR + token`，兩端皆實測。

### 本輪未變更的部分

除 `traceability.json` 的一個條目與本節之外，**attempt 1 的全部產出與 14 個應用程式
路徑均未改動**。`§九` 的 conductor 覆核結果（13 測試綠、全套 378 綠、四道閘門綠、
`npm ci` EXIT=0、lint 0 error）仍然成立，不需重跑。

---

## 十一、iteration 2 審查後的處置（R-04），以及一次系統性掃查

iteration 2 議決 **READY**（0 Critical、1 open Major、0 open Minor）。
R-01／R-02／R-03 皆經審查確認 **Resolved**；新發現 **R-04**。

### R-04（Major）— 已修，但**這個修法未經審查**

**發現**：`traceability.json` 把 `NFR5.7` 標成純 `OK`，而
`nfr-requirements/security-requirements.md:275–276` 逐字把它分兩層：

> 「`WsClientEnvelope` **不得**含 `turnId` 欄位（`BR2.13`）；型別上不可構造是**第一層**，
> 伺服器收到即回 `error(INVALID_REQUEST)`（而非靜默忽略）是**第二層**，屬 `U13`。」

**這是 R-01 的兄弟缺陷，而我修 R-01 時沒把它一起掃出來**——
即使 iteration 2 的派工 brief 裡我親手寫了「`BR2.13` 是靠比對找到的，可能有兄弟項，
請檢查每一個 `OK` 條目」。我寫下了那句話，卻只修了被指名的那一個。

**處置**：`NFR5.7` 改標 `Deferred`，`target` 寫出建置期那層的兩個實際落點
（白名單斷言、型別層不可構造）與第二層的落點 `U13`。
覆蓋分佈 31 `OK`／15 `Deferred` → **30／16**。程式碼未動。

### 這次改為系統性掃查，不再一個一個撿

R-01 與 R-04 都是靠**比對**發現的，那代表逐案撿必然會漏。改以腳本掃全部 `OK` 條目：
對每個條目取出其上游文字（`BR*` 取 `rules.md`、`NFR*` 取 `security-requirements.md`），
以 `U13｜伺服器(收到|送出|端)｜執行期｜runtime` 比對，**9 項命中**，逐一人工判定：

| 條目 | 命中 | 判定 |
|---|---|---|
| `BR1.5`／`BR2.1`／`BR2.2` | 「伺服器送出 X」 | **OK 成立**——那是 `trigger`（規則何時被觸發），而強制點正是本模組在該時刻執行的 validator |
| `BR2.8` | 「伺服器端失敗」「伺服器送出 error」 | **OK 成立**——`statement` 只講「code 取自封閉列舉」與「新增成員必須改契約」，兩半都是建置期；各 code 的判準是給 `U13` 的選用指引，不在 `statement` 內 |
| `NFR5.1`／`NFR5.6`／`BR4.3` | 「執行期」 | **OK 成立**——該詞出現在**失敗後果的說明**裡（「前端在執行期拿到未定義值」），不是義務 |
| `BR1.1` | 「`U13`」「執行期」 | **OK 成立**——規則自己就寫「該處置屬 `K-12`／`U13`，**不屬本單元**」，已自我限縮，本單元的責任（型別層不可構造）完整交付 |
| **`NFR5.7`** | 「`U13`」「伺服器收到」 | **真缺陷**，已修（見上） |

**結論：全 31 個 `OK` 條目中，真正的分層缺陷恰為一項。** 掃查本身的價值不只是找到它，
而是能說出「沒有第三個」——逐案撿永遠說不出這句話。

### 必須揭露的一件事：R-04 的修法沒有第二人看過

`reviewer_max_iterations: 2` 已用盡，而修 `traceability.json`（`produces[]`）
使 iteration 2 的 READY 收據失效。取得第三輪需要 redo jump，而 redo jump 會重設
stage attempt，**連帶讓 Plan Approval 收據一併失效、必須重走整個核可流程**
（`code-generation.md` 逐字：「to the stage attempt (a jump, a rejection, or a workflow
restart) invalidates the fingerprint/receipt and reopens Plan Approval」）。

**選擇留下未經審查的修法，理由**：(1) 它與 R-01 的修法**形狀完全相同**，
而 R-01 的修法已經審查確認「faithful，且與 `BR1.3`／`BR2.5` 的處理完全一致」；
(2) 它只改一個 JSON 條目的 `status` 與 `target`，程式碼零改動，`traceability` sensor 仍 0 findings；
(3) 留著 R-04 的代價是我們剛為 `BR2.13` 修掉的那個**靜默漏做**，只是換一個 id。

**這是一項如實記載的殘留風險，不得在摘要中寫成「全部經審查確認」。**
