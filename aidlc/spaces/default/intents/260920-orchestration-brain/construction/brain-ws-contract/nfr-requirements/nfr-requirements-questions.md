# NFR Requirements 問題檔 — `U2 brain-ws-contract`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: brain-ws-contract · kind: spec -->

## 前言：本站問什麼、不問什麼

`U2` 的 kind 是 `spec`，`produces_kinds` 因此把 performance／scalability／reliability／
observability 四項產出全部濾掉（它們的 kind 清單只含 `service`，performance 另含 `ui`）。
本站的產出只有三項：`security-requirements.md`、`tech-stack-decisions.md`、`traceability.json`。

本單元不含執行期程式碼，也不含任何受保護操作（`K-02` `behaviour_semantics.
authorization_responsibility` 逐字「**無**」）。它的安全面因此落在三處：**建置期供應鏈**、
**契約檔的放置**、以及**讓授權繞過在型別層不可構造**。五道題全部長在這三處上。

### 上游已定案、本站不重問（每項附可引用的依據）

| 事項 | 定案 | 依據（可逐字複驗） |
|---|---|---|
| 唯一真實來源 | 後端 Pydantic 模型 | `contract-summary.md:173` `[C2]`=A 逐字「後端 Pydantic 模型為唯一真實來源」 |
| 兩道 CI 閘門與其職責分工 | backend 驗「規格檔 == 程式碼」、frontend 驗「型別檔 == 由規格檔重產」 | `K-02` `ci_gates`；`BR4.3` |
| 規格檔路徑 | repo 根 `ws-contract.json` | `K-02` `derived_artifacts[0].path` |
| 型別檔路徑 | `frontend/src/types/ws-contract.d.ts` | `K-02` `derived_artifacts[1].path` |
| dump 的序列化形狀 | `indent=2, sort_keys=True, ensure_ascii=False` ＋ 尾端換行 | `K-02` `derived_artifacts[0].note` 逐字；`BR4.2` |
| 版本協商走首則訊息、`v` 為字面型別、不做向後相容 | `[C4]`=B ＋ `[Q2]`=A ＋ `[Q6]`=A | `K-12` `x-handshake.version_note`；`BR1.1` |
| token 走 `Sec-WebSocket-Protocol`、不得進 query string | 硬約束 | `K-12` `x-hard-constraints.token_transport` 逐字 |
| `error.code` 為封閉四值 | `EMPTY_RESPONSE`／`INTERNAL_ERROR`／`UNAUTHORIZED`／`INVALID_REQUEST` | `BR2.8`（`[Q1]`=A ＋ 審查 R-04） |
| 端點掛在 `/api/` 之下 | 硬約束（nginx 只有 `location /api/` 帶 Upgrade 標頭） | `K-12` `x-hard-constraints.path_prefix` 逐字 |

### 單一可行解，故不出成題目、改為揭露（`project.md` `requirements-analysis:260822-ra-c5`）

**契約模組的落點**：`backend/services/brain_ws_contract.py`（純 Pydantic 模型，無 router），
由 `U13` import。理由：`unit-of-work.md:69` 給 `U2` 的擁有與交付逐字是「前後端共用的 WS
訊息型別來源」——模型若寫在 `U13` 的 router 檔內，`U2` 就不擁有它，與已核可的單元邊界
直接矛盾。**連帶的後果**：`dump_ws_contract.py` 只 import 該模組，**不 import `main`**
（既有 `dump_openapi.py` 必須 import `main` 才拿得到 `app.openapi()`，並因此需要
`sys.modules.setdefault("psycopg2", MagicMock())` 的 DB 樁）。少 import 的實際差別是：
應用程式任何 import 失敗都不會讓本閘門連帶紅燈，閘門的訊號因此只代表契約本身。

---

## 本站查證到的事實（供題幹與選項引用，非來源標籤）

出題前對既有型別產生工具鏈做的唯讀實測。**其中第 1 項翻轉了我原本的預設。**

1. **`openapi-typescript@7.13.0` 不在 `frontend/package-lock.json` 內**（`grep -c` 回 `0`）。
   它由 `npx --yes openapi-typescript@7.13.0` 在**每一次 CI** 從 npm registry 取回，
   `npm ci` 完全不覆蓋它。版本字串重複在兩處：`frontend/package.json` 的 `gen:types`
   與 `frontend/scripts/check-api-types.mjs:21` 的 `GENERATOR` 常數（該檔註解逐字自述
   「兩處若不一致，這道 gate 會比對到不同產生器的輸出而誤報」）。
   → 所以 `K-02` 的「產生器版本須與 `package.json` 釘同一版」在既有實作中是**字串重複**，
   不是依賴鎖定。
2. **`openapi-typescript` 只吃 OpenAPI 3.x 文件**，不吃任意 JSON Schema。Pydantic 的
   `model_json_schema()` 產出的是 JSON Schema（`$defs`／`#/$defs/...` refs）。
   要沿用它，dump 必須把模型包成最小 OpenAPI 外殼
   （`openapi: 3.1.0` ＋ `info` ＋ `paths: {}` ＋ `components.schemas`），
   而 `pydantic.json_schema.models_json_schema(..., ref_template="#/components/schemas/{model}")`
   正是 FastAPI 自己在做的事。
3. **`dump_openapi.py` 刻意把規格檔寫在 repo 根、不寫進 `frontend/public/`**，該檔
   docstring 逐字給的理由是「Vite 會把 `public/` 原樣複製進 `dist/`。規格檔落在那裡
   等於把完整的 API 地圖對未認證訪客公開」。
4. **兩道既有閘門在 `ci.yml` 的落點**：`npm run check:types` 在 frontend job（`:198`），
   `python scripts/dump_openapi.py --check` 在 backend job（`:260`）。
5. **`.github/workflows/ci.yml` 已在 `scripts/validate_repo_contract.py` 的
   `REQUIRED_FILES` 內**（`:30`），但 `REQUIRED_TEXT` **沒有** `ci.yml` 這一鍵
   （**以 `ast` 解析該 dict 實算為四鍵**：`README.md`、`CLAUDE.md`、
   `aidlc/spaces/default/memory/team.md`、`aidlc/spaces/default/memory/project.md`。
   <!-- 更正：初版寫「八鍵」並列出 SKILL.md／decisions-log.md／schema_rbac.sql／
        DEPLOY.md，那是用 regex 抓字串抓到的**詞條值**而非鍵——schema_rbac.sql 與
        DEPLOY.md 實際位於 :129–130，是 project.md 那一鍵**要求出現的詞**。
        已依 project.md `delivery-planning:dp-L1`（可算的數字先算再寫）改為實算值。
        本題的定案不受影響：ci.yml 不是這四鍵之一，所以閘門被刪不會被發現，
        這個核心事實原樣成立。 -->）
   → 所以「閘門步驟被人刪掉」這件事，**既有兩道閘門目前也沒有任何偵測**。
6. **前端 `devDependencies` 共 17 項**，無 vitest／jest；`@playwright/test` 是唯一測試框架。

---

## Q1 — `ws-contract.json` → `.d.ts` 的產生器要選哪一個？

`K-02` 指定了「由 `ws-contract.json` 產生」與「版本須釘」，但**沒有指定用哪支產生器**。
這是本站要定的事，且它同時決定 `ws-contract.json` 本身要長成什麼形狀（事實 2）。

**共同約束（三個選項都必須滿足）**：`BR4.4` 要求產生的型別檔必須保留 `sideEffect`
兩個哨兵值的說明註解——因為 TS 會把 `"none" | "unknown" | string` 塌縮為 `string`，
註解是該語意在消費端唯一的殘留。選項 A 與 B 都以 `description` → JSDoc 的既有行為滿足它；
選項 C 必須自己實作。

- **A（建議）— 沿用既有 `openapi-typescript@7.13.0`，dump 產出最小 OpenAPI 外殼**：
  零新工具、零新學習成本；兩個型別檔（`api.d.ts`／`ws-contract.d.ts`）輸出風格一致；
  失敗模式與既有閘門完全相同，reviewer 不需要理解第二套。代價是 `ws-contract.json`
  會帶一層與 WebSocket 無關的 OpenAPI 外殼（`paths: {}`），檔案本身略顯彆扭。
- **B — 引入 `json-schema-to-typescript`**：`ws-contract.json` 可以是乾淨的 JSON Schema，
  形狀最自然。代價是**新增第二支產生器**，其取得方式若沿用 `npx --yes` 就是把事實 1
  的供應鏈面再加一份；且兩個型別檔的輸出風格會不同（判別 union 的產出形狀不一樣）。
- **C — 自寫產生器（一支 `.mjs`，走訪 JSON Schema）**：CI 不執行任何第三方程式碼，
  事實 1 的洞對新閘門直接不存在；`BR4.5`（產生器釘版）隨之變成「釘我們自己的檔案」。
  代價是我們自己維護它，且 `BR4.4` 的註解保留要自己實作、判別 union 的正確性要自己驗。

[Answer]: A <!-- answered 2026-09-28T03:01:49Z — 沿用既有 openapi-typescript@7.13.0，dump 產出最小 OpenAPI 外殼 -->

## Q2 — 事實 1 的 `npx --yes` 供應鏈缺口要修到什麼範圍？

CI 每次從 npm registry 取回未鎖定的第三方程式碼並執行它。這是**既有**狀態，不是本單元
造成的；但本單元若沿用同一形狀就是把它**加倍**。

**注意 Q1=A 與本題的交互**：若 Q1 選 A（沿用 `openapi-typescript`）而本題只修新閘門，
會出現**同一個套件兩條解析路徑**（既有用 `npx --yes` 從 registry 取、新的用 lockfile 鎖的
本地版本），兩者可能解析到不同位元而讓兩道型別閘門互相矛盾。所以在 Q1=A 之下，
「只修新的」實際上不是一個乾淨的選項——這一點必須先講清楚再選。

- **A（建議）— 一併修：把產生器加入 `devDependencies` 由 `package-lock.json` 鎖住，
  兩道型別閘門都改用本地解析版本，移除兩處 `npx --yes` 與重複的版本字串**：
  一次消除供應鏈面、版本字串重複、以及 Q1=A 的雙路徑矛盾。
  **代價：這動到既有的 `check-api-types.mjs` 與 `gen:types`，屬本階段新增、
  `scope-document.md` 未涵蓋的工作量，須在產出中標明並回補。**
- **B — 只修新閘門**：新的產生器進 `devDependencies`，既有兩處不動。範圍最小，
  但在 Q1=A 之下製造上述雙路徑矛盾；在 Q1=B／C 之下沒有這個矛盾（不同套件）。
- **C — 沿用現況（新閘門也用 `npx --yes`）**：與既有實作完全對稱，零額外工作。
  把「CI 執行未鎖定第三方程式碼」列為**已接受的風險**寫進 `security-requirements.md`，
  並明寫它的失敗模式（registry 上該版本被替換或撤下時，閘門會用不同的程式碼比對，
  或直接無法執行）。

[Answer]: A <!-- answered 2026-09-28T03:01:49Z — 一併修既有兩處：產生器進 devDependencies 由 lockfile 鎖住，四道型別閘門皆用本地解析版本 -->

## Q3 — `Sec-WebSocket-Protocol` 的 subprotocol 名稱與格式，歸誰定？

`functional-spec.md §八` 第四列逐字把它列為**最靜默的一個**缺口：它是前後端必須逐字一致的
共用字串，而 `K-12:876` 只規定「token 走該標頭」、全檔未定其值格式；**沒有任何契約定義
它的值**。前端改了格式而後端沒跟上時，**握手直接失敗且沒有任何閘門會紅燈**。
它是 token 的載體，屬 `ADR-0006` 的 network exposure 面，所以落在本站的判定表上。

- **A（建議）— 由本單元納入 `ws-contract.json`，取得兩道閘門的保護**：
  在契約模組內定義它（例如一個常數與其格式說明），dump 進規格檔、產生進型別檔。
  前後端各自從同一個來源取值，格式改動會被兩道閘門擋下。
  **代價：這是本單元第三次擴充 `K-02` 的範圍**（前兩次是審查 R-01 的 `ready` 與
  R-02 的 `select_clarify_candidate`），需與那兩項一併送上游追認。
- **B — 維持現況，留給 `U13` 或一次 `K-12` 修訂**：本單元範圍不變、不再動 `K-02`。
  代價是這個缺口原樣留著——它**不會**因為被寫進某份文件而消失，只有進契約檔才有閘門。
- **C — 在契約模組內定義為常數，但不進 `ws-contract.json`**：前後端至少有單一來源
  （後端定義、前端手抄或由別的途徑取得），但仍無閘門——只是把「兩處字串」變成
  「一處定義 ＋ 一處手抄」，失敗模式不變。

[Answer]: A <!-- answered 2026-09-28T03:01:49Z — 由本單元納入 ws-contract.json，取得兩道閘門的保護 -->

## Q4 — `BR1.4`／`BR1.5`／`BR4.4` 三條可機械驗證的規則，要在本單元就實作為斷言嗎？

`rules.md §三` 已逐條給出判定式，並建議在 `code-generation` 實作。本題定的是**範圍**：
它們要不要成為 `NFR5`（WebSocket 契約閘門）的一部分，也就是要不要進 `--check` 的斷言集合。

三條分別是：`BR1.4`（type 列舉與 payload 實體兩集合等勢且可正規化對應）、
`BR1.5`（終止事件 payload 的 `turnId` == envelope 的 `turnId`）、
`BR4.4`（產生的型別檔在 `sideEffect` 欄位保留說明註解）。

- **A（建議）— 三條全部實作**：`BR1.4` 與 `BR4.4` 落在 `dump_ws_contract.py --check`
  與型別產生後的檢查（皆屬本單元交付），`BR1.5` 落在後端模型的 validator。
  這讓 `NFR5` 的「斷言兩端一致」不只是形狀一致，還涵蓋本站自己新增的三條不變量。
  代價是本單元的交付從「一支 dump ＋ 一支 check」變成「一支 dump ＋ 三組斷言」。
- **B — 只實作 `BR1.4`**：它是新增訊息型別時最容易漏的一步（加了 type 沒加 payload
  就是一個沒有形狀的死值），且純靠集合運算、成本最低。`BR1.5` 與 `BR4.4` 留 `U13`／
  `code-generation`。
- **C — 三條都留給 `code-generation`／`U13`**：本單元只交付契約與兩道形狀閘門。
  代價是這三條退化為只寫在文件裡的規則——`rules.md` 對 `BR1.4` 逐字寫過
  「**這是可機械驗證的**」，不實作等於自己放棄那句話。

[Answer]: A <!-- answered 2026-09-28T03:01:49Z — BR1.4／BR1.5／BR4.4 三條全部實作為斷言 -->

## Q5 — 「閘門步驟本身被刪掉」要不要有偵測？

事實 5：`ci.yml` 已在 `REQUIRED_FILES` 內，但 `REQUIRED_TEXT` 沒有 `ci.yml` 這一鍵。
所以今天若有人把 `npm run check:types` 那一步從 `ci.yml` 刪掉，**沒有任何機制會發現**。
本單元要新增兩道閘門，同樣的失敗模式會複製過來。這是本 repo 反覆在意的「無聲失敗」形狀。

- **A（建議）— 在 `REQUIRED_TEXT` 為 `ci.yml` 新增一鍵，斷言四道型別閘門的指令字串都在**：
  既有機制、零新工具、二元可判，`validate_repo_contract.py` 本來就在 CI 的
  `repo-contract` job 跑。**代價：涵蓋既有兩道即為本階段新增、scope 未涵蓋的工作量**
  （只涵蓋新的兩道則是不對稱的保護）。另一個真實代價是字串比對很脆——改個寫法就假紅燈。
- **B — 不做，與既有兩道閘門同等待遇**：依賴 code review。範圍最小、誠實一致，
  但把一個**已知可在五分鐘內關掉的無聲失敗**留著。若選此項，`security-requirements.md`
  須把它列為已接受的風險並寫出後果。
- **C — 本單元新增一支專門的檢查腳本**（解析 `ci.yml` 的 YAML、斷言四個步驟存在）：
  比字串比對穩健。代價是新增一支要維護的腳本，而它保護的是 CI 設定本身——
  收益與成本的比例需要使用者判斷。

[Answer]: A <!-- answered 2026-09-28T03:01:49Z — 在 REQUIRED_TEXT 為 ci.yml 新增一鍵，斷言四道型別閘門的指令字串都在 -->

---

<!-- 時間戳更正：五個 [Answer] 註解初寫時我填了一個未經 `date -u` 取得的值
     （2026-09-28T02:58:14Z），已全部改為實際執行 `date -u` 取得的 2026-09-28T03:01:49Z。
     依 project.md `user-stories:260822-us-L1`，時間戳一律取值而非估寫。 -->

## 收齊答案後的矛盾與覆蓋檢查（stage 檔 Step 4，必做）

### 模糊語檢查

五個答案全部是具體的機制選擇，無「夠快」「高可用」「安全」這類不可量測的詞。
本站的兩份產出也不含任何延遲／吞吐／可用度目標——`U2` 的 kind 是 `spec`，
那四類產出已被 `produces_kinds` 濾掉。**無模糊項。**

### 跨題矛盾檢查

| 組合 | 有無矛盾 | 說明 |
|---|---|---|
| Q1=A × Q2=A | **無，且相加才乾淨** | Q2 的題幹已揭露：Q1=A 配「只修新的」會讓同一個套件有兩條解析路徑。兩題都選 A 正好消除它。 |
| Q1=A × Q3=A | **需要一個機制決定，見下** | `openapi-typescript` 只為 `components.schemas` 產生型別，不會為任意 `x-` 擴充欄位產生任何繫結。所以「把 subprotocol 放進規格檔」不能用 `x-subprotocol` 這種寫法承載，否則前端拿不到型別、閘門等於不存在。 |
| Q1=A × Q4=A | **無** | `BR4.4` 靠 `description` → JSDoc，`openapi-typescript` 既有行為即滿足；斷言只需檢查產出的 `.d.ts` 在該欄位上方有該段文字。 |
| Q2=A × Q5=A | **無，方向一致** | 兩者都在收斂「建置期保證」的可信度：Q2 修「執行什麼程式碼」，Q5 修「那段檢查還在不在」。 |
| Q3=A × 上游 | **需上游追認（已知代價）** | 這是本單元第三次擴充 `K-02`。前兩次為審查 R-01（`ready`）與 R-02（`select_clarify_candidate`）。三項一併送上游追認。 |

### Q1=A × Q3=A 的機制決定（本站就地收斂，不留給下游猜）

subprotocol 不以擴充欄位承載，而是**做成一個 Pydantic 模型進 `components.schemas`**，
兩個欄位皆為字面型別：

```python
class WsSubprotocol(BaseModel):
    """握手用 subprotocol 的格式；實際值為 f"{scheme}{separator}{token}"。"""
    scheme: Literal["bearer"]
    separator: Literal["."]
```

`openapi-typescript` 會把它產成 `{ scheme: "bearer"; separator: "." }`。前端據此宣告：

```ts
type Sub = components['schemas']['WsSubprotocol'];
const SCHEME: Sub['scheme'] = 'bearer';
const SEP: Sub['separator'] = '.';
```

**閘門為何成立**：後端若把 `scheme` 改成 `Literal["brain"]`，重 dump 後 `.d.ts` 的字面型別
變成 `"brain"`，前端那一行 `= 'bearer'` 立即是型別錯誤、`tsc -b` 紅燈。
這正是 `functional-spec.md §八` 第四列所說「沒有任何閘門會紅燈」的相反面。

**這個機制的殘餘缺口，必須寫下而不是假裝沒有**：閘門只在前端**真的用那兩個常數組字串**時
才成立。前端若自己寫死 `` `bearer.${token}` ``，型別層碰不到它。故本站把
「前端必須由產生的型別取值」列為 `U14` 的落點，寫進 `security-requirements.md`，
而不是宣稱契約已經擋住它。

### 覆蓋檢查（已定案的驗證計畫 vs 最高風險的失敗模式）

| 本單元最高風險的失敗模式 | 有無對應的已定案機制 |
|---|---|
| 後端改了訊息形狀，規格檔沒重 dump | 第一道閘門（`K-02` 已定） |
| 規格檔重 dump 了，型別檔沒重產 | 第二道閘門（`K-02` 已定；`BR4.3` 逐字寫這條路徑會靜默通過） |
| 加了 type 卻沒加 payload（死值） | Q4=A 的 `BR1.4` 斷言 |
| 終止事件兩份 `turnId` 不一致 | Q4=A 的 `BR1.5` validator |
| `sideEffect` 哨兵語意在型別檔消失 | Q4=A 的 `BR4.4` 斷言 |
| subprotocol 格式前後端不一致 | Q3=A ＋ 上方機制（**殘餘缺口已列明**） |
| CI 取到被替換的產生器 | Q2=A（lockfile 鎖定） |
| 有人把閘門步驟從 `ci.yml` 刪掉 | Q5=A（`REQUIRED_TEXT`） |
| **前端沒有使用產生的 subprotocol 常數** | **無機制——已列為 `U14` 的落點與已接受的殘餘風險** |
| **`error.message` 含內部實作細節（`BR2.9`）** | **無機制——本單元是型別來源，型別擋不住字串內容；落點 `U13`** |

最後兩列是覆蓋檢查查出的**真缺口**，不是矛盾。兩者都不由本單元承載，故不另開題，
但必須在 `security-requirements.md` 逐條寫出落點與後果。

### 本階段新增、已核可 scope 尚未涵蓋（需回補）

| 項 | 新增了什麼 | 觸發 |
|---|---|---|
| **S-1** | 修改**既有**的 `frontend/scripts/check-api-types.mjs` 與 `package.json` 的 `gen:types`（移除 `npx --yes`、改用 lockfile 鎖定的本地版本） | Q2=A |
| **S-2** | `K-02` 的**第三次**擴充：subprotocol 的名稱與格式納入契約 | Q3=A |
| **S-3** | `scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT` 新增 `ci.yml` 一鍵，且涵蓋**既有兩道**閘門 | Q5=A |

三項皆在提問當下的選項文字中揭露過代價，非事後補記。

---

## Consolidated Summary Confirmation

<!-- 第一次確認（Summary Authorization Id c9604b10…）已失效：確認取得之後，
     送審前自檢 6（可算的數字先算再寫）查出兩處實算錯誤並修正——
     (1) `REQUIRED_TEXT` 由「八鍵」更正為實算的**四鍵**（初版用 regex 抓到的是詞條值不是鍵）；
     (2) `tech-stack-decisions.md` 的「十八個以上的模型」改為 `entities.md` 實算的 22 個實體。
     另依自檢 1 修正一條不可達的判準（`NFR5.2` 原寫「無網路下 `npm ci`」），
     並依自檢 2 補上兩處「誰清」（閘門詞條的移除義務、產生器升級時兩個型別檔的同步義務）。
     **五題的定案完全不受影響**，改動的是支撐事實的精確度與兩條判準的可執行性。
     依 `project.md` `scope-definition:e8146aa4`，產出定稿後須重取確認。 -->

[Answer]: Looks correct <!-- answered 2026-09-28T03:12:00Z（第二次；第一次因自檢查出的實算更正而失效） -->
