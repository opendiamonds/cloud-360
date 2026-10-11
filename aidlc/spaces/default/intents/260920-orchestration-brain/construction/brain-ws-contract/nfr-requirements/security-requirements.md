# Security Requirements — `U2 brain-ws-contract`（`spec`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: brain-ws-contract · kind: spec -->

## 這份檔在做什麼

`U2` 交付的是**前後端共用的 WebSocket 訊息型別來源**與**兩道 CI 一致性閘門**。
它沒有執行期程式碼，也不含任何受保護操作——`K-02` 的
`behaviour_semantics.authorization_responsibility` 逐字寫「**無**」。

所以本單元的安全面不是「誰能做什麼」，而是三件事：

1. **建置期供應鏈**——閘門所執行的程式碼是否可信、閘門本身是否還在；
2. **契約檔的放置**——規格檔不得落到未認證訪客拿得到的地方；
3. **讓授權繞過在型別層不可構造**——`BR2.12`（客戶端訊息不得攜帶身分）與
   `BR2.13`（不得攜帶 `turnId`）是否真的在型別上無法構造。

本檔可獨立閱讀。每一條需求繼承 inception 的 `NFR{n}` 編號並附子號（stage 檔要求）。

**讀進來的上游**：`functional-spec.md` 與 `rules.md`（本單元 `functional-design` 的產出）、
`requirements.md`（NFR 與 ADR-0006 四面向判定表）、`contract-summary.md`（`K-02` 的
`derived_artifacts`／`ci_gates`／`behaviour_semantics`，`K-12` 的硬約束與授權責任）、
`technology-stack.md`（codekb，基準 `dc4b687`）。

**`produces_kinds` 的濾除不是漏寫**：`U2` 的 kind 是 `spec`，而 performance／
scalability／reliability／observability 四項產出的 kind 清單只含 `service`
（performance 另含 `ui`），故本站對本單元只產出三份。

---

## 〇、本階段新增、已核可 scope 尚未涵蓋（**需回補**）

依 `project.md` 的規則逐處標明，不當作既有能力項的自然延伸吸收。
三項的代價都在提問當下的選項文字中揭露過，非事後補記。

| 項 | 新增了什麼 | 觸發 | 後果 |
|---|---|---|---|
| **S-1** | **修改既有的 `frontend/scripts/check-api-types.mjs` 與 `frontend/package.json` 的 `gen:types`**：移除 `npx --yes`、改用 `package-lock.json` 鎖定的本地版本、刪掉重複的版本字串 | `[Q2]`=A | `scope-document.md` 沒有「既有型別閘門的供應鏈強化」這個能力項。本單元原本的範圍是「新增一組閘門」，現含**改既有的一組**。落地後 `frontend/package.json` 的 `devDependencies` 由 17 項變 18 項，且 `api.d.ts` 須在同一個 PR 內複驗（見 `NFR5.2`） |
| **S-2** | **`K-02` 的第三次擴充**：subprotocol 的名稱與格式納入契約 | `[Q3]`=A | 前兩次擴充為 `functional-design` 審查 R-01（`ready`）與 R-02（`select_clarify_candidate`）。三項須一併送上游追認；在追認之前，本單元的契約範圍**大於**已核可的 `K-02` |
| **S-3** | **`scripts/validate_repo_contract.py` 的 `REQUIRED_TEXT` 新增 `ci.yml` 一鍵，且涵蓋既有兩道閘門** | `[Q5]`=A | 該檔的 `REQUIRED_TEXT` 實算為**四鍵**、無 `ci.yml`。只涵蓋新的兩道會是不對稱的保護，故涵蓋四道——涵蓋既有兩道即為新增工作量 |

---

## 一、ADR-0006 Security Baseline 四面向逐項判定

`project.md` 明列此為 hard constraint，**四面向缺一不可**；判定為不適用者亦須附理由。
本表與 `functional-spec.md §七之二` 的同名表**互補而非重複**：那一張判的是**契約本身**
的四面向，這一張判的是**本站新增的建置期與供應鏈決定**的四面向。

| 面向 | 對本站決定的判定 | 具體要求 |
|---|---|---|
| **IAM** | **適用（處置為「讓繞過在型別層不可構造」）** | `NFR5.7`。本單元不含任何受保護操作，它唯一的授權相關規則 `BR2.12` 是**否定式**的——客戶端訊息不得攜帶使用者 id／角色／token 或等價欄位，principal 綁在連線上（`K-12` `x-authorization-responsibility.per_connection_principal` 逐字）。`BR2.13` 同形：客戶端不得攜帶 `turnId`。兩者都必須是**型別上不可構造**，不是「約定俗成」——故它們是閘門的斷言對象，見 `NFR5.7` |
| **Encryption** | **適用（處置全在別的單元）** | 本單元不引入任何連線、不持久化任何資料。但 `UserMessagePayload.text` 與 `TokenPayload.text` 攜帶使用者的對話內容，其**靜態**加密要求是 `OQ-3`（指派 `nfr-design`），落在 `U5 memory-data` 的資料範圍。傳輸加密由 `wss` 承載（`K-12` `servers.staging.protocol` 逐字），屬 `U13`。本站的相關要求只有一條且是**否定式**的：`NFR5.6`——規格檔不得落到公開可讀的路徑，因為它是完整的訊息地圖 |
| **Network exposure** | **適用（本站的主要安全面之一）** | `NFR5.4`（subprotocol 的名稱與格式納入契約）與 `NFR5.6`（規格檔的放置）。`K-12:853` 逐字「本 intent **唯一**新增的對外網路面」，而 subprotocol 是 **token 的載體**——它的格式若前後端不一致，握手直接失敗；更重要的是它今天**沒有任何契約定義它的值**（`functional-spec.md §八` 第四列逐字「不只是『不在本契約檔內』，是**根本沒有被定義過**」） |
| **Audit logging** | **適用（本站的處置是「讓閘門的判決可信」）** | `NFR5.2` 與 `NFR5.3`。本單元不產生任何執行期稽核記錄，但它產生**CI 的判決**——而一個執行未鎖定第三方程式碼的閘門、或一個可以被五分鐘刪掉而無人察覺的閘門，它的綠燈不構成證據。把這兩項判為不適用，等於把「閘門的判決是否可信」從判定表上移除 |

**ADR-0006 property-based testing hard constraint 的判定**：**不適用，附理由。**
該約束點名 IaC generator、cost calculator、agent routing 三類純計算模組，本單元
不含其中任何一個。更根本的是 `rules.md` 的 category 分佈中 `calculation` 為 **0**
（腳本實算）——本單元交付的是型別宣告與建置期斷言，沒有值域可供性質測試的純函式。
**PBT 在本 intent 的真實落點**是 `U11` 的 IntentRouter 門檻純函式與 `U6` 的
EmbeddingPort，兩者皆已由 `contract-summary.md` 記載。

---

## 二、安全需求（逐條，含可測判準）

### `NFR5.1` — 契約的唯一真實來源與兩道閘門

**繼承**：`NFR5`（WebSocket 契約閘門）。**承接**：`K-02` `source_of_truth` ＋ `ci_gates`；
`BR4.1`／`BR4.3`。

| 項 | 值 |
|---|---|
| 唯一人手改的來源 | `backend/services/brain_ws_contract.py`（純 Pydantic 模型，無 router） |
| 衍生物 1 | repo 根 `ws-contract.json`，由 `backend/scripts/dump_ws_contract.py` 產生 |
| 衍生物 2 | `frontend/src/types/ws-contract.d.ts`，由衍生物 1 產生 |
| 第一道閘門 | CI backend job：`python scripts/dump_ws_contract.py --check`，斷言「規格檔 == 程式碼」 |
| 第二道閘門 | CI frontend job：`npm run check:ws-types`，斷言「committed 型別檔 == 由規格檔重產」 |

**可測判準**：手改任一衍生物後跑 CI，對應那一道必須紅燈；兩個衍生物皆未改時必須綠燈。

**為何兩道缺一不可**（`BR4.3` 逐字）：只有第一道時，開發者重 dump 了規格卻忘了重產型別檔，
型別檔仍宣告舊形狀，而 `tsc -b` 檢查的是「用法是否符合型別檔」、**不是**「型別檔是否符合
規格檔」——那條路徑會靜默通過，前端在執行期拿到未定義值。

### `NFR5.2` — 閘門所執行的程式碼必須被鎖定（**本站新增，`[Q2]`=A**）

**繼承**：`NFR5`。**觸發**：本站實測。

**問題（機械事實，非推論）**：`frontend/package-lock.json` 對 `openapi-typescript` 的
`grep -c` 回 **0**。既有的第二道閘門由
`npx --yes openapi-typescript@7.13.0` 在**每一次 CI** 從 npm registry 取回並執行，
`npm ci` 完全不覆蓋它。版本字串重複在兩處：`frontend/package.json` 的 `gen:types`
與 `frontend/scripts/check-api-types.mjs:21` 的 `GENERATOR` 常數（該檔註解逐字自述
「兩處若不一致，這道 gate 會比對到不同產生器的輸出而誤報」）。

所以 `K-02` `derived_artifacts` 逐字的「產生器版本須與 `package.json` 釘同一版」，
在既有實作中是**字串重複**，不是依賴鎖定。

**要求**：

1. `openapi-typescript` 加入 `frontend/package.json` 的 `devDependencies`，
   **精確釘選 `"7.13.0"`（不得用 `^` 或 `~`）**，並由 `npm ci` 從 `package-lock.json` 安裝。
   精確釘選的理由與 `backend/requirements.txt` 對 `fastapi`／`pydantic` 的理由相同：
   產生器版本一變，型別檔的位元就變，閘門會在程式碼沒改時紅燈。
2. **四道**型別閘門（既有兩道 ＋ 新增兩道）都改用本地解析的版本，
   移除 `gen:types` 與 `check-api-types.mjs` 的 `npx --yes` 與重複的版本字串。
3. **同一個 PR 內必須複驗既有的 `frontend/src/types/api.d.ts`**：理論上同一版本應產生
   同一位元，但 `npx --yes` 過去實際解析到什麼並無紀錄。若重產後有差異，
   **必須把新的 `api.d.ts` 一併 commit**，不得讓差異留到之後某個無關的 PR 才爆。

**可測判準**：`grep -c 'npx --yes' frontend/package.json frontend/scripts/*.mjs` 回 `0`；
`grep -c 'openapi-typescript' frontend/package-lock.json` 回非 `0`；
**`npm ci` 完成之後**，跑 `npm run check:types` 與 `npm run check:ws-types` 不再發生任何
registry 取用（以 `npm_config_offline=true` 執行兩道閘門仍成功即為通過）。

<!-- 自檢 1（可達性）更正：初版的判準寫「在無網路的環境下 `npm ci && ...` 仍可完成」，
     那是不可達的——`npm ci` 本身就要從 registry 取套件，該判準永遠無法通過，
     於是它會變成一條看起來有守門、實際上沒人驗得了的需求。本條要防的是
     「`npm ci` 之後還額外取東西」，判準因此改錨在 `npm ci` 之後的兩道閘門上。 -->

**失敗模式（未做的後果）**：npm registry 上 `7.13.0` 被替換、撤下或該套件被接管時，
CI 會用**不同的程式碼**做型別比對，或直接無法執行。閘門的綠燈在那之後不構成任何證據，
而這件事**不會有任何訊號**——它看起來就像一次正常的 CI 通過。

**「誰清」（自檢 2 補）**：升級 `openapi-typescript` 時，**同一個 PR 內必須重產並
commit 兩個型別檔**（`api.d.ts` 與 `ws-contract.d.ts`）。這與
`backend/requirements.txt:1–7` 對 `fastapi`／`pydantic` 的既有義務同形，理由也相同：
產生器版本一變輸出就變，不同步重產會讓兩道閘門在一個與型別無關的 PR 上紅燈。

**已接受的殘餘**：`npm ci` 仍從 registry 取套件，本條消除的是「未鎖定版本」而非
「不信任 registry」。完全離線的供應鏈（vendoring、私有 proxy）不在本 intent 範圍。

### `NFR5.3` — 閘門的存在本身必須被斷言（**本站新增，`[Q5]`=A**）

**繼承**：`NFR5`。**觸發**：本站實測。

**問題**：`.github/workflows/ci.yml` 已在 `scripts/validate_repo_contract.py` 的
`REQUIRED_FILES` 內（`:30`），但 `REQUIRED_TEXT` **沒有** `ci.yml` 這一鍵
（**以 `ast` 解析該 dict 實算為四鍵**：`README.md`、`CLAUDE.md`、
`aidlc/spaces/default/memory/team.md`、`aidlc/spaces/default/memory/project.md`；
`schema_rbac.sql` 與 `DEPLOY.md` 在 `:129–130`，是 `project.md` 那一鍵**要求出現的詞**，
不是鍵）。
所以今天若有人把 `npm run check:types` 那一步從 `ci.yml` 刪掉，**沒有任何機制會發現**。
本單元要新增兩道閘門，同樣的失敗模式會原樣複製過來。

**要求**：`REQUIRED_TEXT` 新增 `.github/workflows/ci.yml` 一鍵，其詞條集合涵蓋
**四道**型別閘門的指令字串：

- `scripts/dump_openapi.py --check`
- `npm run check:types`
- `scripts/dump_ws_contract.py --check`
- `npm run check:ws-types`

**可測判準**：把任一步驟從 `ci.yml` 刪掉後執行
`python3 scripts/validate_repo_contract.py`，必須 exit 非 0 並指名缺哪一條。

**「誰清」（自檢 2 補）**：任何一道閘門被**正當地**改名或移除時（例如指令搬進一支
shell script），**必須在同一個 PR 內同步移除或改寫對應的詞條**。否則 `REQUIRED_TEXT`
會變成永久的假紅燈，而假紅燈久了就會被整條註解掉——那等於把這道保護自己關掉。

**已知的脆弱處，必須寫下**：這是**字串比對**，改個寫法（例如把指令搬進一支 shell script、
或改用 `working-directory` 的不同寫法）會造成**假紅燈**。這是刻意接受的代價——
假紅燈會被立刻發現並修正，而漏偵測不會。若日後假紅燈頻繁，升級路徑是改為解析 YAML
斷言步驟存在（本站 `[Q5]` 的選項 C），不是移除這道檢查。

### `NFR5.4` — 契約必須涵蓋 subprotocol 的名稱與格式（**本站新增，`[Q3]`=A**）

**繼承**：`NFR5`。**ADR-0006 面向**：Network exposure。
**觸發**：`functional-spec.md §八` 第四列。

**問題（逐字引用上游）**：subprotocol 是前後端必須逐字一致的共用字串，而 `K-12:876`
只規定「token 走該標頭」、全檔未定其值格式。`functional-spec.md §八` 對它的評語是
「**最靜默的一個**……前端改了格式而後端沒跟上時，**握手直接失敗且沒有任何閘門會紅燈**」，
並明寫它與同表前三項的差別：「前三項至少有一個契約（`K-12`）明文擁有並定義了它們；
第四項**沒有任何契約定義它的值**」。

**要求**：在契約模組內定義它，使它進入兩道閘門的保護範圍。
**承載形式已在本站就地決定**（因為 `openapi-typescript` **不會**為任意 `x-` 擴充欄位
產生任何 TypeScript 繫結——用擴充欄位承載等於前端拿不到型別、閘門等於不存在）：

```python
class WsSubprotocol(BaseModel):
    """握手用 subprotocol 的格式；實際值為 f"{scheme}{separator}{token}"。"""
    scheme: Literal["bearer"]
    separator: Literal["."]
```

它進 `components.schemas`，產生器輸出字面型別。**本站已實測驗證**此形狀：

```ts
WsSubprotocol: {
    /** @constant */
    scheme: "bearer";
    /** @constant */
    separator: ".";
};
```

前端據此宣告，**閘門即成立**：

```ts
type Sub = components['schemas']['WsSubprotocol'];
const SCHEME: Sub['scheme'] = 'bearer';
const SEP: Sub['separator'] = '.';
```

後端若把 `scheme` 改成 `Literal["brain"]`，重 dump 後 `.d.ts` 的字面型別變成 `"brain"`，
前端那一行 `= 'bearer'` 立即是型別錯誤、`tsc -b` 紅燈。

**可測判準**：把後端的 `scheme` 改成別的字面值、重跑 dump 與型別產生、
在前端維持 `= 'bearer'`，`npm run build` 必須紅燈；還原後必須綠燈（突變驗證）。

**殘餘缺口（必須寫下，不得宣稱契約已擋住）**：
閘門只在**前端真的用那兩個常數組字串**時成立。前端若自己寫死
`` `bearer.${token}` ``，型別層碰不到它，這條保護即不存在。
**落點 `U14`**：前端建立 WebSocket 時必須由產生的型別取值，不得寫死字串。
本站不宣稱契約已擋住這件事——見 `§三`。

### `NFR5.5` — 閘門的斷言集合必須涵蓋三條可機械驗證的不變量（**`[Q4]`=A**）

**繼承**：`NFR5`。**承接**：`rules.md §三` 的三條判定式。

`NFR5` 的字面要求是「斷言兩端一致」。本條把它擴為「也斷言本站新增的三條不變量」，
理由是 `rules.md` 對 `BR1.4` 逐字寫過「**這是可機械驗證的**」——不實作等於自己
放棄那句話，讓它退化為只寫在文件裡的規則。

| 規則 | 斷言落點 | 判定式 |
|---|---|---|
| `BR1.4` type 列舉與 payload 實體兩集合等勢且可對應 | `dump_ws_contract.py --check` | payload 實體＝名稱以 `Payload` 結尾者（排除 `ClarifyCandidate`／`WorkItem` 兩個子實體、三個 Envelope、兩個列舉、`WsSubprotocol`）；對應為 snake_case→PascalCase ＋ `Payload` 後綴；斷言三件事：每個 type 正規化後存在同名 payload、每個 payload 反推回某個 type、兩集合等勢（目前 **9** 與 **6**） |
| `BR1.5` 終止事件 payload 的 `turnId` == envelope 的 `turnId` | 後端模型的 validator | `payload.turnId == envelope.turnId`（`done`／`error` 兩型） |
| `BR4.4` 型別檔保留 `sideEffect` 哨兵值的說明註解 | 型別產生後的檢查 | 產生的 `.d.ts` 在 `sideEffect` 欄位上方存在含 `"none"` 與 `"unknown"` 兩個哨兵值語意的 `@description` 段 |

**`BR4.4` 的可行性已實測**：`openapi-typescript@7.13.0` 把 JSON Schema 的 `description`
原樣輸出為 `/** @description ... */`，中文字元保留。所以該斷言的前提是
**Pydantic 欄位必須帶 `description=`**——這一點本身也要進斷言，否則註解會靜默消失。

**可測判準**：三條各做一次突變驗證（加一個沒有 payload 的 type；讓 `done` 的兩份
`turnId` 不同；拿掉 `sideEffect` 的 `description=`），各自必須紅燈，還原後綠燈。

### `NFR5.6` — 規格檔不得落到未認證訪客可讀的路徑

**繼承**：`NFR5`。**ADR-0006 面向**：Encryption（資訊揭露面）／Network exposure。
**承接**：`K-02` `derived_artifacts[0].path`（repo 根 `ws-contract.json`）
＋ `dump_openapi.py` docstring 的既有理由。

**要求**：`ws-contract.json` 寫在 **repo 根**，**不得**寫進 `frontend/public/`
或任何會被 Vite 複製進 `dist/` 的路徑。

**理由逐字沿用既有先例**：`dump_openapi.py` 的 docstring 寫「Vite 會把 `public/` 原樣
複製進 `dist/`。規格檔落在那裡等於把完整的 API 地圖（含全部使用者管理與權限端點）
對未認證訪客公開」。對 WS 契約而言洩漏的是**完整的訊息地圖**——九種伺服器訊息、
六種客戶端訊息與全部 payload 欄位，等於把大腦的內部協定與能力邊界公開。

**本條額外禁止一件既有先例沒碰到的事**：型別檔 `frontend/src/types/ws-contract.d.ts`
會被編譯進 bundle，**但 `.d.ts` 只有型別、不產生執行期程式碼**，所以它本身不是洩漏面；
反過來說，**不得**為了方便而把規格檔（`.json`）import 進前端程式碼——那會讓完整的
訊息地圖進 bundle。

**可測判準**：`ws-contract.json` 不在 `frontend/public/` 下；
`grep -r "ws-contract.json" frontend/src/` 回空。

### `NFR5.7` — 授權繞過必須在型別層不可構造

**繼承**：`NFR5`。**ADR-0006 面向**：IAM。**承接**：`BR2.12`、`BR2.13`。

本單元不含任何受保護操作，所以它的 IAM 面是**否定式**的：讓「客戶端自稱身分」與
「客戶端指定輪次」這兩件事在型別上無法構造。

**要求**：

1. `WsClientEnvelope` 與**六個** client payload 的欄位集合，**都不得**含
   使用者 id、角色、token 或等價欄位（`BR2.12`）。principal 綁在連線上。
2. `WsClientEnvelope` **不得**含 `turnId` 欄位（`BR2.13`）；型別上不可構造是第一層，
   伺服器收到即回 `error(INVALID_REQUEST)`（而非靜默忽略）是第二層，屬 `U13`。

**可測判準**：對產生的 `ws-contract.d.ts` 斷言——六個 client payload 與
`WsClientEnvelope` 的欄位名集合與一份禁用名單（`userId`／`user_id`／`role`／`token`／
`turnId` 等）的交集為空。這一條與 `NFR5.5` 的三條同為 dump 期斷言，建議一併實作。

**為何要機械斷言而非靠 review**：`BR2.13` 的由來正是一次 review 沒抓到的缺口——
`functional-design` 初版把 `turnId` 定為客戶端封包的**選填**欄位，同時宣告「客戶端
沒有它」，兩句話並存了一整輪才被審查 R-20 抓到。

---

## 三、覆蓋檢查查出的兩個真缺口（不由本單元承載，逐條寫明落點）

這兩項不是矛盾，是**已定案的驗證計畫涵蓋不到的失敗模式**。依 `project.md` 的處置形狀，
標出缺口、寫明它讓哪一條要求失效、指派具體落點與修法，**不逕自擴張本單元範圍**。

| 缺口 | 它讓什麼失效 | 落點與修法 |
|---|---|---|
| **前端未使用產生的 subprotocol 常數** | `NFR5.4` 的整條保護。閘門只在前端真的由型別取值時成立；寫死 `` `bearer.${token}` `` 時型別層碰不到它，而**畫面上看不出差別**——直到後端改了格式，握手才全面失敗 | **`U14`**。修法：前端建立 WebSocket 時以 `const SCHEME: Sub['scheme'] = 'bearer'` 形狀宣告並組字串，禁止字面量。可加一條 lint 規則（禁止 `new WebSocket` 的第二引數出現字串字面量），但本站不預選手段 |
| **`BR2.9`（`error.message` 不得含內部實作細節）** | ADR-0006 的資訊揭露面。`error` 走對外網路面，堆疊、SQL、內部路徑或模組名洩漏在此是常見路徑 | **`U13`**。本單元是型別來源，型別擋不住字串**內容**——`message: str` 無論如何都通過。修法屬伺服器端的錯誤構造（統一的 `error` 工廠 ＋ 不得把例外訊息原樣帶出） |

---

## 四、本單元未承載的 inception NFR，與它們的真正落點

逐條列出並附理由，**不留空白**——`project.md` 的既有教訓是「缺一不可型 hard constraint
以逐項判定表呈現，判定為不適用的項目一律附理由」。

| NFR | 判定 | 理由與真正落點 |
|---|---|---|
| `NFR1` 意圖識別準確率 | N/A | 屬 `U11 intent-router`；量測機制落 `build-and-test`。本單元不在該路徑上 |
| `NFR2` 跨頁面上下文保留率 | N/A | 屬 `U10 session-store` 的行為 ＋ `build-and-test` 的量測 |
| `NFR3` 首字回應時間 | N/A | 預算幾乎全被路由層的 LLM 呼叫吃掉（`requirements.md` NFR3 逐字）。本單元不新增任何請求處理 |
| `NFR4` 狀態外部化與重啟還原 | N/A | 屬 `U10`。本單元無執行期狀態 |
| **`NFR5` WebSocket 契約閘門** | **OK** | **本單元的核心**，見 `§二` 的七條 |
| `NFR6` 記憶層 schema 隔離 | N/A | 屬 `U5 memory-data` |
| `NFR7` episodic memory 保存與刪除稽核 | N/A | 屬 `U5`／`U8`。本單元只定義對話內容**在傳輸中**的形狀，不定義它落地後怎麼存；靜態加密手段是 `OQ-3`，指派 `nfr-design` |
| `NFR8` 新增元件的部署設定完整性 | N/A | 該條的對象是 compose 服務與其環境變數（Redis 為第 5 個容器）。本單元不新增任何服務或環境變數；它新增的是一個 devDependency 與兩個 CI 步驟，其完整性保護在 `NFR5.2`／`NFR5.3` |
| `NFR9` 成本原則 | N/A | 本單元不呼叫任何模型 |
| `NFR10` 路由層模型的可替換性 | N/A | **承接站是本 stage，但不是本單元**——它屬 `U11 intent-router` 的 `nfr-requirements` 迭代，`OQ-4` 仍未定案。這是它第二次在別的單元跑過本站（前一次為 `brain-infra`），兩次都不是它的承接點。**在此明記以免它因為「本 stage 又跑過一次」而被當成已定案** |
| `NFR11` 跨功能任務的頁面切換次數 | N/A | 屬 UI 單元 ＋ `build-and-test` 的量測 |

---

## 五、Assumptions & Open Questions

- **`WsSubprotocol` 的具體值（`bearer` ＋ `.`）是本站的提案，不是上游定案。**
  上游對它一字未定（這正是 `NFR5.4` 的由來）。選這個值的理由是它與 HTTP 的
  `Authorization: Bearer` 慣例一致、且 `.` 不出現在 base64url 的 JWT 分隔之外的位置有歧義
  風險——**這一點須由 `U13` 在實作前複核**：JWT 本身以 `.` 分三段，故
  `bearer.<jwt>` 的解析必須以**第一個** `.` 切分，不得以 `split('.')` 取兩段。
  這是一個實作陷阱，在此先寫下。
- **`K-02` 的三項擴充尚未取得上游追認**（`ready`、`select_clarify_candidate`、
  `WsSubprotocol`）。在追認之前，本單元的契約範圍大於已核可的 `K-02`。
- **`[Q2]`=A 的「同版本應產生同位元」尚未實測**：本站驗證了
  `openapi-typescript@7.13.0` 對 components-only 文件的行為，但**沒有**驗證
  「`npx --yes` 取回的 7.13.0」與「lockfile 鎖定的 7.13.0」產生的 `api.d.ts` 逐位元相同。
  該複驗是 `NFR5.2` 要求 3 的內容，落在 `code-generation`。
- **`NFR5.3` 的詞條字串形式尚未定稿**：`REQUIRED_TEXT` 該存「完整指令」還是
  「腳本檔名」影響假紅燈的頻率。本站給出四條指令字串作為起點，最終形式由
  `code-generation` 依 `ci.yml` 屆時的實際寫法定，**但不得因為難寫而省略這一鍵**。
