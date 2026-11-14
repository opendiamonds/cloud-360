# Tech Stack Decisions — `U2 brain-ws-contract`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: brain-ws-contract · kind: spec -->

## 這份檔在做什麼

`K-02` 定了「後端 Pydantic 模型為唯一真實來源」「兩個衍生物」「兩道閘門」與
「產生器版本須釘」，但**沒有指定用哪一支產生器**，也就連帶沒有定
`ws-contract.json` 本身要長成什麼形狀（產生器決定它吃什麼）。本檔定這些，
並記錄依賴管理的決定與其代價。

本檔可獨立閱讀。**不重述** `K-02` 已定案的部分，只在需要引用時指名。

---

## 一、決定總表

| # | 決定 | 來源 | 動到的既有資產 |
|---|---|---|---|
| D-1 | 型別產生器沿用 **`openapi-typescript@7.13.0`** | `[Q1]`=A | 無（新增用途） |
| D-2 | `ws-contract.json` 為**最小 OpenAPI 3.1 外殼**（`paths: {}` ＋ `components.schemas`） | D-1 的直接後果 | 無 |
| D-3 | 產生器改由 `devDependencies` **精確釘選** `7.13.0` 並由 `package-lock.json` 鎖定；四道型別閘門皆用本地解析版本 | `[Q2]`=A | **`frontend/package.json`、`frontend/scripts/check-api-types.mjs`（S-1）** |
| D-4 | 契約模組落點 `backend/services/brain_ws_contract.py`（純 Pydantic，無 router）；dump **不 import `main`** | 單一可行解，見 `§四` | 無 |
| D-5 | subprotocol 以 **`WsSubprotocol` 模型**承載，不用 `x-` 擴充欄位 | `[Q3]`=A ＋ 本站實測 | 無 |
| D-6 | 三條可機械驗證的規則實作為斷言（`BR1.4` 進 dump、`BR1.5` 進 validator、`BR4.4` 進型別產生後檢查） | `[Q4]`=A | 無 |
| D-7 | `REQUIRED_TEXT` 新增 `ci.yml` 一鍵，涵蓋四道閘門 | `[Q5]`=A | **`scripts/validate_repo_contract.py`（S-3）** |

---

## 二、D-1 型別產生器：沿用 `openapi-typescript@7.13.0`

### 決定

沿用既有的那一支，不引入第二支，也不自寫。

### 依據（本站實測，非推論）

| # | 事實 | 取得方式 |
|---|---|---|
| 1 | 既有第二道閘門用 `openapi-typescript@7.13.0` | `[讀]` `frontend/package.json` `gen:types`、`frontend/scripts/check-api-types.mjs:21` |
| 2 | 它**只吃 OpenAPI 3.x 文件**，不吃任意 JSON Schema | `[讀]` 套件契約；Pydantic 的 `model_json_schema()` 產出的是 JSON Schema（`$defs`／`#/$defs/...` refs） |
| 3 | 它接受 `openapi: 3.1.0` ＋ `paths: {}` 的 components-only 文件，正常產出 `components.schemas` | **`[執行]` 本站以最小樣本實跑 `npx openapi-typescript@7.13.0`，18.9ms 成功** |
| 4 | `const: "bearer"` → 字面型別 `scheme: "bearer"`（帶 `@constant`） | **`[執行]` 同一次實跑** |
| 5 | `description` → `/** @description ... */`，中文字元原樣保留 | **`[執行]` 同一次實跑** |

事實 3–5 是 D-1、D-5 與 `NFR5.5`（`BR4.4` 斷言）三者共同的前提，**本站實際跑過**，
不是照文件推論。

### 取捨

**得到**：零新工具、零新學習成本；兩個型別檔（`api.d.ts`／`ws-contract.d.ts`）
輸出風格一致；失敗模式與既有閘門完全相同，reviewer 不需要理解第二套機制；
`BR4.4` 的註解保留由既有行為滿足（事實 5）。

**付出**：`ws-contract.json` 會帶一層與 WebSocket 無關的 OpenAPI 外殼
（`paths: {}`、`webhooks`、`operations` 等空殼）。檔案本身略顯彆扭，**這是刻意接受的**
——彆扭的是檔案外觀，換到的是零新增的供應鏈面與零新增的工具鏈知識。

### 未採用的替代方案

| 方案 | 不採用的理由 |
|---|---|
| **`json-schema-to-typescript`** | `ws-contract.json` 可以是乾淨的 JSON Schema、形狀最自然，但這是**第二支產生器**：若沿用 `npx --yes` 就是把 `NFR5.2` 的供應鏈面再加一份；即使進 lockfile 也是多一個要跟版的依賴。且兩個型別檔的判別 union 產出形狀會不同，讀 `api.d.ts` 的人無法直接讀 `ws-contract.d.ts` |
| **自寫產生器（一支 `.mjs`）** | CI 不執行任何第三方程式碼，對新閘門而言 `NFR5.2` 的洞直接不存在——這是它真正的優點。但我們要自己維護判別 union 的正確性與 `BR4.4` 的註解保留（事實 4、5 在此都要自己實作並自己驗），而這兩件事正是產生器最容易出錯的地方。在既有工具已經被驗證過的前提下，收益小於成本 |

---

## 三、D-2 `ws-contract.json` 的形狀

### 決定

```jsonc
{
  "openapi": "3.1.0",
  "info": { "title": "Brain WS Contract", "version": "1.0.0" },
  "paths": {},
  "components": { "schemas": { /* 全部 Pydantic 模型 */ } }
}
```

由 `pydantic.json_schema.models_json_schema(..., ref_template="#/components/schemas/{model}")`
產生 `components.schemas`——**這正是 FastAPI 自己在做的事**，不是本站發明的手法。

### 序列化形狀（承接 `K-02` `derived_artifacts[0].note`，不重新決定）

`json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)` ＋ 尾端換行。
與 `backend/scripts/dump_openapi.py:render_spec()` 逐字相同，理由亦同：
`sort_keys` 讓輸出與 dict 插入順序無關（`BR4.2`）、`ensure_ascii=False` 讓中文
`description` 以原字元存放使 diff 可讀、尾端換行符合文字檔慣例。

### 落點

| 資產 | 路徑 | 依據 |
|---|---|---|
| dump 腳本 | `backend/scripts/dump_ws_contract.py` | `K-02` 逐字 `generated_by: "python scripts/dump_ws_contract.py"`，而 CI 的 backend job 以 `backend/` 為工作目錄執行（既有 `dump_openapi.py` 同形） |
| 規格檔 | repo 根 `ws-contract.json` | `K-02` `derived_artifacts[0].path`；放置的安全理由見 `security-requirements.md` `NFR5.6` |
| 型別檔 | `frontend/src/types/ws-contract.d.ts` | `K-02` `derived_artifacts[1].path` |

---

## 四、D-4 契約模組的落點與 dump 的 import 範圍

### 決定

`backend/services/brain_ws_contract.py`——**純 Pydantic 模型，無 router、無 FastAPI 依賴**，
由 `U13` import。`dump_ws_contract.py` **只 import 該模組**。

### 這不是一個選擇題（故本站未出成題目）

`unit-of-work.md:69` 給 `U2` 的擁有與交付逐字是「前後端共用的 WS 訊息型別來源」。
模型若寫在 `U13` 的 router 檔內，`U2` 就不擁有它，與已核可的單元邊界直接矛盾。
依 `project.md` 的 `requirements-analysis:260822-ra-c5`（單一可行解不出成題目，
改在彙整摘要揭露後果），本站改為在此寫明決定與理由。

### 與既有先例的差別，以及那個差別的實際後果

`dump_openapi.py` **必須** import `main` 才拿得到 `app.openapi()`，並因此需要
`sys.modules.setdefault("psycopg2", MagicMock())` 這個 DB 樁（該檔 `:41–43`）。

`dump_ws_contract.py` **不需要**——它只需要 Pydantic 模型本身。少 import 的實際差別有三：

1. **閘門的訊號變乾淨**：應用程式任何 import 失敗（新依賴沒裝、某個 router 打字錯）
   都不會讓本閘門連帶紅燈。紅燈只代表契約本身漂移。
2. **不需要 DB 樁**：少一處與 `tests/helpers.py` 耦合的前置。
3. **契約的邊界更誠實**：模型定義了即進契約，與它有沒有被某個 router 用到無關——
   對一個 `spec` 單元而言這是對的，`U2` 交付的就是型別本身。

---

## 五、D-3 依賴管理：把產生器從 `npx --yes` 改為 lockfile 鎖定

### 現況（機械事實）

`grep -c 'openapi-typescript' frontend/package-lock.json` 回 **0**。
它由 `npx --yes openapi-typescript@7.13.0` 在每次 CI 從 npm registry 取回並執行，
`npm ci` 完全不覆蓋。版本字串重複在兩處，`check-api-types.mjs:19–21` 的註解逐字自述
「與 `package.json` 的 `gen:types` 釘同一個版本。兩處若不一致，這道 gate 會比對到
不同產生器的輸出而誤報」。

所以 `K-02` 逐字的「產生器版本須與 `package.json` 釘同一版」在既有實作中是
**字串重複**，不是依賴鎖定。

### 決定

| 項 | 決定 |
|---|---|
| 宣告位置 | `frontend/package.json` 的 `devDependencies` |
| 版本 | **精確 `"7.13.0"`，不得用 `^` 或 `~`** |
| 安裝 | `npm ci`（CI 已在用） |
| 四道閘門的取得方式 | 本地解析（npm script 會把 `node_modules/.bin` 放進 PATH） |
| 移除 | `gen:types` 與 `check-api-types.mjs` 的 `npx --yes` 與重複的版本字串 |

**精確釘選的理由**與 `backend/requirements.txt:1–7` 對 `fastapi`／`pydantic` 的理由同源：
產生器版本一變，型別檔的位元就變，閘門會在程式碼沒改時紅燈。用 `^7.13.0` 時
`npm ci` 可能解析到 `7.14.x`，committed 的 `api.d.ts` 隨即漂移——而那會發生在
一個與型別無關的 PR 上，看起來像隨機紅燈。

### 這動到既有資產（S-1），代價逐項

1. `frontend/package.json`：`devDependencies` 由 **17** 項變 **18** 項；`gen:types` 改寫。
2. `frontend/scripts/check-api-types.mjs`：`GENERATOR` 常數與 `execFileSync('npx', ['--yes', ...])`
   改寫；`:19–21` 那段「兩處若不一致」的註解隨之作廢，應一併改寫成新的事實。
3. **`frontend/src/types/api.d.ts` 必須在同一個 PR 內複驗**：理論上同版本產生同位元，
   但 `npx --yes` 過去實際解析到什麼並無紀錄。有差異就把新的一併 commit——
   不得讓差異留到之後某個無關的 PR 才爆（見 `security-requirements.md` `NFR5.2` 要求 3）。

### 本站未驗證的部分（誠實記載）

「`npx --yes` 取回的 7.13.0」與「lockfile 鎖定的 7.13.0」產生的 `api.d.ts` 是否逐位元相同，
**本站沒有實測**。本站只驗證了 `7.13.0` 對 components-only 文件的行為。
該複驗是 `code-generation` 的內容。

---

## 六、D-5 subprotocol 的承載形式

### 為什麼不能用 `x-` 擴充欄位

`openapi-typescript` **不會**為任意 `x-` 擴充欄位產生任何 TypeScript 繫結。
用 `x-subprotocol: "bearer.{token}"` 承載，等於前端拿不到型別——
`[Q3]`=A 的整個目的（讓格式改動被閘門擋下）隨即落空，而文件上看起來已經解決。

### 決定

做成一個進 `components.schemas` 的模型，兩個欄位皆為字面型別：

```python
class WsSubprotocol(BaseModel):
    """握手用 subprotocol 的格式；實際值為 f"{scheme}{separator}{token}"。"""
    scheme: Literal["bearer"]
    separator: Literal["."]
```

**本站實測的產出**：

```ts
WsSubprotocol: {
    /** Scheme @constant */
    scheme: "bearer";
    /** Separator @constant */
    separator: ".";
};
```

前端以 `const SCHEME: Sub['scheme'] = 'bearer'` 形狀取值，格式改動即 `tsc -b` 紅燈。
完整的判準、突變驗證方式與**殘餘缺口**見 `security-requirements.md` `NFR5.4`。

### 一個必須先寫下的實作陷阱

JWT 本身以 `.` 分三段，所以 `bearer.<jwt>` 的解析必須以**第一個** `.` 切分
（`split('.', 1)`），不得以 `split('.')` 取兩段——後者在任何真實 token 上都會拿到四段。
落點 `U13`。

---

## 七、釘版現況與本單元造成的變化

| 面向 | 本單元之前 | 本單元之後 |
|---|---|---|
| 前端依賴鎖定 | `package-lock.json` 已 commit，CI 用 `npm ci`；**但型別產生器不在其中** | 產生器進 lockfile；`devDependencies` 17 → 18 |
| 型別產生器的取得 | 每次 CI 從 npm registry 取（兩處 `npx --yes`） | 本地解析，**零處** `npx --yes` |
| 版本字串的物化份數 | **2**（`package.json` ＋ `check-api-types.mjs`），靠註解提醒同步 | **1**（`package.json` 的 `devDependencies`） |
| 型別閘門數 | 2（OpenAPI 一組） | **4**（OpenAPI 一組 ＋ WS 一組） |
| 閘門存在性的保護 | **無** | `REQUIRED_TEXT` 的 `ci.yml` 一鍵涵蓋四道（D-7） |
| 後端依賴 | 17 項宣告、5 支精確釘選、無 lockfile | **不變**——`dump_ws_contract.py` 只用 `pydantic`（已精確釘選 `2.13.4`）與標準庫 |

**後端不變這一列值得單獨指出**：本單元的後端側交付（契約模組 ＋ dump 腳本）
**不引入任何新的 Python 依賴**。`pydantic==2.13.4` 已精確釘選，
`models_json_schema` 是它自帶的 API。所以 codekb 記載的「backend 無 lockfile、
11 支未 pin」這個既有風險，本單元**不加重也不改善**。

---

## 八、CI 落點

| job | 新增步驟 | 位置參照 |
|---|---|---|
| `backend` | `python scripts/dump_ws_contract.py --check` | 既有 `python scripts/dump_openapi.py --check` 在 `ci.yml:260`，新步驟緊接其後 |
| `frontend` | `npm run check:ws-types` | 既有 `npm run check:types` 在 `ci.yml:198`，新步驟緊接其後 |

**兩道不得合併成一道**：`BR4.3` 逐字寫了理由——第一道驗「規格檔 == 程式碼」、
第二道驗「型別檔 == 由規格檔重產」，而 `tsc -b` 驗的是第三件事「用法符不符合型別檔」。
三者缺一都有一條靜默通過的路徑。

**兩道不得改成同一個 job**：第一道需要 Python 與後端依賴、第二道需要 Node 與
`node_modules`。合併會讓其中一個 job 多裝一整套工具鏈，且違反既有兩道的分工形狀。

---

## 九、Assumptions & Open Questions

- **`openapi-typescript@7.13.0` 對「`entities.md` 實算的 22 個實體（含互相 `$ref`）＋ 判別 union」的產出品質，
  本站只以兩個模型的最小樣本驗證過。** 判別 union（`WsEnvelope` 依 `type` 判別九種 payload）
  在 OpenAPI 中以 `oneOf` ＋ `discriminator` 表達，而 Pydantic 的
  `Field(discriminator="type")` 會產生該形狀。**`code-generation` 的第一步應是先跑一次
  完整 dump 並人工檢視產出的 `.d.ts`**，確認判別 union 真的可用（能在 `switch (msg.type)`
  之後收窄到正確的 payload 型別）。若不可用，退路是把 envelope 拆成九個具名型別的聯集，
  代價是型別檔較冗長但語意不變。
- **`WsSubprotocol` 的具體值（`bearer` ＋ `.`）是本站的提案，上游對它一字未定**，
  須隨 `K-02` 的三項擴充一併送上游追認。
- **`ci.yml` 的 `REQUIRED_TEXT` 詞條最終形式未定稿**：存「完整指令」還是「腳本檔名」
  影響假紅燈的頻率。本站給四條指令字串作為起點，最終形式由 `code-generation` 依
  `ci.yml` 屆時的實際寫法定，**但不得因為難寫而省略這一鍵**。
- **`NFR10`／`OQ-4`（路由層模型 `typesafe/jev-1.13`）不在本檔範圍**。它的承接站是本
  stage 但屬 `U11 intent-router` 的迭代，仍未定案。這是它第二次在別的單元跑過本站，
  **兩次都不是它的承接點**——在此明記以免被誤當成已定案。
