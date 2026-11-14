# ADR 0019: WebSocket 契約閘門與型別產生器的供應鏈

- Status: Accepted
- Date: 2026-09-28（建立於 2026-09-28T04:03:23Z，讀自 `date -u`）
- 節數：**6**（§6 含一段 `nfr-design` 審查後補入的適用前提）
- Amends: 無既有 ADR。本 ADR **新增**約束，不修訂任何既有決定。
- Touches（動到既有資產，非本 intent 新建）：`frontend/package.json`、
  `frontend/scripts/check-api-types.mjs`、`frontend/eslint.config.js`、
  `scripts/validate_repo_contract.py`、`.github/workflows/ci.yml`。
- 觸發來源：intent `260920-orchestration-brain`、單元 `U2 brain-ws-contract` 的
  `nfr-requirements`（`[Q1]`／`[Q2]`／`[Q5]`）與 `nfr-design`（`[Q1]`／`[Q4]`）兩站問答。
- **紀錄更正（`nfr-design` 審查 R-02 補，2026-09-28T04:13:56Z）**：`nfr-design` 的
  `QUESTION_ANSWERED` audit 事件（`2026-09-28T03:56:07Z`）把 **Q1 誤記為 `A`**，
  **現行定案為 `B`**（ESLint error 規則，即本 ADR §5）。成因是提問時重排選單順序後
  依位置而非依內容回寫；補記被引擎以「無新人工回合」正確拒絕
  （`ERROR_LOGGED`，`2026-09-28T03:56:29Z`），故更正就地寫在問題檔內，
  而人工的摘要確認（`04:01:03Z`）晚於更正完成（`03:57:22Z`），是在看到更正後才確認的。
  **在此交叉引用**，使只讀 audit shard 或只掃 `QUESTION_ANSWERED` 做統計的下游工具
  也有機會發現這筆誤記。
- 下游依據：`construction/brain-ws-contract/nfr-requirements/{security-requirements.md,tech-stack-decisions.md}`、
  `construction/brain-ws-contract/nfr-design/security-design.md`。

## Context

本 intent 要新增一個 WebSocket 端點。`requirements.md` 的 `NFR5` 逐字要求它有
「一份前後端共用的訊息型別契約來源，並有一個 CI 檢查斷言兩端一致」，理由是機械事實而非偏好：
既有的 `/api/collab/ws/...` **不在 `openapi.json` 的 42 個 path 內**（FastAPI 不登錄
websocket route），所以 `dump_openapi.py --check` 與 `npm run check:types` 兩道既有漂移閘門
**對 WebSocket 完全無效**。

`contract-design` 的 `K-02` 已定案「後端 Pydantic 模型為唯一真實來源」與「鏡射既有 OpenAPI
的兩道 gate」，但**沒有指定用哪一支型別產生器**。`nfr-requirements` 為此出題時做了一次
唯讀實測，結果翻轉了原本的預設，而翻轉出來的事實影響範圍**超出本單元**——這是本 ADR 存在的理由。

### 那個實測事實

`grep -c 'openapi-typescript' frontend/package-lock.json` 回 **0**。

既有的第二道型別閘門由 `npx --yes openapi-typescript@7.13.0` 在**每一次 CI** 從
npm registry 取回並執行，`npm ci` 完全不覆蓋它。版本字串重複在兩處：
`frontend/package.json` 的 `gen:types` 與 `frontend/scripts/check-api-types.mjs:21` 的
`GENERATOR` 常數（該檔註解逐字自述「兩處若不一致，這道 gate 會比對到不同產生器的輸出而誤報」）。

所以 `K-02` 逐字的「產生器版本須與 `package.json` 釘同一版」，在既有實作中是
**字串重複**，不是依賴鎖定。本 intent 若原樣沿用，等於把「CI 執行未鎖定的第三方程式碼」
這個面**加倍**。

## Decision

### 1. 型別產生器沿用 `openapi-typescript@7.13.0`，契約檔做成最小 OpenAPI 外殼

`ws-contract.json` 的形狀為 `openapi: 3.1.0` ＋ `info` ＋ `paths: {}` ＋ `components.schemas`，
由 `pydantic.json_schema.models_json_schema(..., ref_template="#/components/schemas/{model}")`
產生——這正是 FastAPI 自己在做的事。

**已實測驗證**（`nfr-requirements` 與該站審查各獨立跑過一次）：該產生器接受
components-only 文件；`const` 產成字面型別並帶 `@constant`；`description` 產成
`@description` JSDoc 且 CJK 原樣保留；**`x-` 擴充欄位在 top-level 與 schema-property
兩個位置都產出零 TS 繫結**（最後這一項決定了 §3 不能用擴充欄位承載）。

不引入第二支產生器（`json-schema-to-typescript`）的理由是它會再加一份供應鏈面，
且兩個型別檔的判別 union 輸出形狀會不同。不自寫產生器的理由是判別 union 的正確性與
註解保留都要自己驗，而既有工具已被驗證過。

### 2. 產生器改由 lockfile 鎖定，四道型別閘門皆用本地解析版本

| 項 | 決定 |
|---|---|
| 宣告位置 | `frontend/package.json` 的 `devDependencies` |
| 版本 | **精確 `"7.13.0"`，不得用 `^` 或 `~`** |
| 安裝 | `npm ci`（CI 已在用），完整性由 `package-lock.json` 的 `integrity` 欄保證 |
| 取得方式 | 本地解析；**移除兩處 `npx --yes`** 與重複的版本字串 |
| 涵蓋範圍 | **四道**——既有 OpenAPI 兩道 ＋ 本 intent 新增的 WS 兩道 |

精確釘選的理由與 `backend/requirements.txt:1–7` 對 `fastapi`／`pydantic` 的理由同源：
產生器版本一變輸出就變，閘門會在程式碼沒改時紅燈，而那種紅燈與「真的漂移了」
在訊號上不可區分。

**連帶義務**：升級 `openapi-typescript` 時，**同一個 PR 內必須重產並 commit 兩個型別檔**
（`api.d.ts` 與 `ws-contract.d.ts`）。

**落地時的一次性複驗**：「`npx --yes` 取回的 7.13.0」與「lockfile 鎖定的 7.13.0」
理論上產生同一位元，但 `npx --yes` 過去實際解析到什麼並無紀錄。重產後若 `api.d.ts`
有差異，**必須把新的一併 commit**，不得讓差異留到之後某個無關的 PR 才爆。

### 3. `Sec-WebSocket-Protocol` 的名稱與格式納入契約

`K-12:876` 只規定「token 走該標頭」，**全檔未定其值格式**；`functional-spec.md §八`
把它列為最靜默的缺口——前端改格式而後端沒跟上時，**握手直接失敗且沒有任何閘門會紅燈**。

以一個進 `components.schemas` 的模型承載（不用 `x-` 擴充欄位，理由見 §1 末）：

```python
class WsSubprotocol(BaseModel):
    """握手用 subprotocol 的格式；實際值為 f"{scheme}{separator}{token}"。"""
    scheme: Literal["bearer"]
    separator: Literal["."]
```

前端以 `const SCHEME: Sub['scheme'] = 'bearer'` 形狀取值；後端改值即 `tsc -b` 紅燈。

**這是 `K-02` 的第三次擴充**（前兩次為 `functional-design` 審查 R-01 的 `ready` 與
R-02 的 `select_clarify_candidate`）。三項一併以本 ADR 作為上游追認的載體。

**實作陷阱**：JWT 以 `.` 分三段，故 `bearer.<jwt>` 的解析必須以**第一個** `.` 切分
（`split('.', 1)`），不得 `split('.')` 取兩段。落點 `U13`。

### 4. 閘門的存在本身必須被斷言

`scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT` 新增
`.github/workflows/ci.yml` 一鍵，詞條涵蓋**四道**型別閘門的指令字串。

理由是實測事實：`ci.yml` 雖在 `REQUIRED_FILES` 內（`:30`），`REQUIRED_TEXT` 卻沒有它
（實算為四鍵：`README.md`、`CLAUDE.md`、`team.md`、`project.md`）。
所以今天把 `npm run check:types` 那一步從 `ci.yml` 刪掉，**沒有任何機制會發現**。

**已知脆弱處**：這是字串比對，改寫法會造成假紅燈。刻意接受——假紅燈會被立刻發現並修正，
漏偵測不會。**詞條與步驟是一對一的**：閘門被正當改名或移除時必須同步改／刪詞條；
**不得**把詞條整條註解掉。

### 5. subprotocol 的消費端以 lint 規則強制

§3 的型別保護**只在前端真的由型別取值時成立**。前端寫死 `` `bearer.${token}` `` 時
型別層碰不到它。故在 `frontend/eslint.config.js` 新增一條 **error 級**規則：
**`new WebSocket` 的第二引數不得出現字串字面量或模板字面量**。

**必須是 `error`**：CI 跑 `eslint .` 且未加 `--max-warnings 0`，warn 級等於沒有閘門。

**排序約束（實測）**：`frontend/src/pages/BrainPage.tsx:83` 現持有
`` [`bearer.${token}`] ``（本 session 為展示加的 demo-scope 頁面），**規則一開即紅燈**。
規則啟用的同一個 PR 內必須二擇一：把該頁改為由型別取值，或先刪掉它
（`U13`／`U14` 本來就會取代）。`frontend/src/hooks/useCollaboration.ts:25` 無第二引數，不受影響。

**擋不住的**：先把字串存進變數再傳入。接受此殘餘——它擋掉無心之失，擋不住刻意繞過，
而刻意繞過會在 code review 留下痕跡。

### 6. 客戶端訊息的身分欄位以白名單斷言，不用禁用名單

斷言七個客戶端物件（`WsClientEnvelope` ＋ 六個 client payload）的欄位名集合
**等於**一份釘在 `dump_ws_contract.py` 內的預期集合。

**理由不是精確度而是封閉性**：禁用名單擋不住叫別的名字的身分欄位
（`actor`、`onBehalfOf`、`impersonate`…），而那個命名空間是開放的、列不完。
白名單由構造封閉——任何新欄位都紅燈，直到有人**刻意**去改預期集合。

**代價**：新增合法欄位要改兩處；紅燈訊息只說「欄位集合與預期不符」，
不會指出「這是身分欄位」。診斷性換封閉性，本 ADR 認為對授權繞過這個威脅而言值得。

#### 判定式的適用前提（`nfr-design` 審查 R-01 補，**必讀**）

**本判定式只比對每個 schema 的頂層 `properties` 鍵集合。** 它今天「由構造封閉」
成立的前提是：目前七個客戶端物件**全部是扁平物件**，沒有任何巢狀 sub-object
（已逐一核對 `entities.md`）。

> **若日後任一 client payload 長出巢狀物件**（例如一個 `context: {...}` 欄位），
> 只比對頂層鍵的斷言**碰不到巢狀物件內部**——一個藏在裡面、叫別的名字的身分等價欄位
> 就會逃過這道保護。那正是本 ADR 在 Alternatives Rejected 判定「維持禁用名單」不可取的
> 同一個理由，只是換了一層。
>
> **屆時必須二擇一**：讓判定式遞迴進巢狀 schema，或在判定式旁明文排除並說明為何安全。
> **不得**沿用現行寫法而假設它仍然涵蓋得到。

這段前提必須同時出現在 `dump_ws_contract.py` 判定式旁的註解裡——寫在 ADR 裡
只保證「查得到」，寫在程式碼旁才保證「改的人看得到」。落點 `code-generation`。

## Consequences

### 正面

- 四道型別閘門執行的是 lockfile 鎖定且帶 integrity 雜湊的程式碼，綠燈開始構成證據。
- 版本字串的物化份數由 **2** 降為 **1**（`devDependencies`），消除「兩處不同步即誤報」。
- WebSocket 首次擁有漂移閘門，補上 `openapi.json` 結構上碰不到的那一塊。
- subprotocol 從「沒有任何契約定義它的值」變成受兩道閘門 ＋ 一條 lint 規則保護。
- 「閘門被刪掉」從零偵測變成 `repo-contract` job 會擋。

### 負面

- **動到四份既有資產**（§2 的兩份、§4 的一份、§5 的一份），皆不在已核可的
  `scope-document.md` 內，已列為該 intent 的 S-1／S-3／S-4 需回補項。
- `ws-contract.json` 帶一層與 WebSocket 無關的 OpenAPI 外殼（`paths: {}`），檔案外觀彆扭。
- §4 的字串比對會產生假紅燈。
- §6 的紅燈訊息診斷性較差。
- §5 的排序約束在 demo 頁存在期間有效，執行者須當下複查而非照抄。

### 中性

- `npm ci` 仍從 registry 取套件。本 ADR 消除的是「未鎖定版本」，不是「不信任 registry」。
  完全離線的供應鏈（vendoring、私有 proxy）不在範圍。
- 後端側不引入任何新 Python 依賴——`pydantic==2.13.4` 已精確釘選，
  `models_json_schema` 是它自帶的 API。codekb 記載的「backend 無 lockfile、11 支未 pin」
  這個既有風險，本 ADR **不加重也不改善**。

## Alternatives Rejected

| 方案 | 不採用的理由 |
|---|---|
| **引入 `json-schema-to-typescript`** | `ws-contract.json` 可以是乾淨 JSON Schema、形狀最自然，但這是第二支產生器（多一份供應鏈面、多一個要跟版的依賴），且兩個型別檔的判別 union 輸出形狀會不同 |
| **自寫型別產生器** | CI 不執行任何第三方程式碼是真正的優點，但判別 union 的正確性與 `sideEffect` 註解保留都要自己實作並自己驗，而那兩件事正是產生器最易出錯處。既有工具已被驗證過，收益小於成本 |
| **只修新閘門的供應鏈、既有兩道不動** | 在「沿用 `openapi-typescript`」之下會出現**同一個套件兩條解析路徑**（既有從 registry、新的用 lockfile），兩者可能解析到不同位元而讓兩道型別閘門互相矛盾 |
| **subprotocol 用 `x-subprotocol` 擴充欄位承載** | 實測確認 `openapi-typescript` 對 `x-` 欄位產出**零** TS 繫結，前端拿不到型別，閘門等於不存在——而文件上看起來已經解決 |
| **subprotocol 留給 `U13` 或一次 `K-12` 修訂** | 缺口原樣留著。它不會因為被寫進某份文件而消失，只有進契約檔才有閘門 |
| **多產一支執行期常數模組承載 subprotocol** | 需要第三個衍生物 ＋ 第三道閘門；且它真正的保護只是「只有一個地方有那個字串」，寫死字串仍通過型別檢查——保護強度不如一條 error 級 lint 規則 |
| **維持禁用名單並收斂成封閉清單** | 比現況精確但保護強度不變：叫別的名字的身分欄位仍然通得過 |
| **不開本 ADR，理由只寫進 intent record** | §2 改的是全 repo 的型別產生方式。下一個碰 `gen:types` 的人需要知道為什麼那裡不再有 `npx --yes`，而那個理由不應只存在於一個 intent 的 record 深處 |

## References

- `aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-requirements/security-requirements.md`（`NFR5.1`–`NFR5.7`）
- 同上 `tech-stack-decisions.md`（D-1…D-7 與釘版現況表）
- `aidlc/spaces/default/intents/260920-orchestration-brain/construction/brain-ws-contract/nfr-design/security-design.md`（STRIDE、排序約束、白名單判定式）
- `aidlc/spaces/default/intents/260920-orchestration-brain/inception/contract-design/contract-summary.md`（`K-02` `derived_artifacts`／`ci_gates`；`K-12` `x-hard-constraints`）
- `aidlc/spaces/default/intents/260920-orchestration-brain/inception/requirements-analysis/requirements.md`（`NFR5`）
- `frontend/scripts/check-api-types.mjs`、`backend/scripts/dump_openapi.py`（兩道既有閘門的先例與其註解所記的理由）
