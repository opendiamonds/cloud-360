# Security Design — `U2 brain-ws-contract`（`spec`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: brain-ws-contract · kind: spec -->

## 這份檔在做什麼

上一站（`nfr-requirements`）定了**要達成什麼**（`NFR5.1`–`NFR5.7`）。本檔定**怎麼達成**：
每一條的具體機制、它的失敗語意、以及它在什麼條件下才真的成立。

`U2` 沒有使用者、沒有端點、沒有資料。它的攻擊面全部在**建置期**，所以本檔的威脅模型
對象是**產生鏈本身**：誰產生契約、誰執行產生器、誰驗證產物、以及那些驗證會不會被無聲關掉。

`produces_kinds` 把本站七項產出濾成兩項（`security-design.md` ＋ `traceability.json`）——
`logical-components` 的 kind 清單是 `[service, ui, library]`，不含 `spec`。這是設計上的缺席。

**讀進來的上游**：`nfr-requirements/{security-requirements.md,tech-stack-decisions.md}`、
`functional-design/{functional-spec.md,rules.md,entities.md}`、
`contract-design/contract-summary.md`（`K-02`／`K-12`）。

---

## 〇、本階段新增、已核可 scope 尚未涵蓋（**需回補**）

上一站已列 S-1…S-3（改既有型別閘門的供應鏈、`K-02` 第三次擴充、`REQUIRED_TEXT` 涵蓋既有兩道）。
本站再新增三項：

| 項 | 新增了什麼 | 觸發 | 後果 |
|---|---|---|---|
| **S-4** | **修改既有的 `frontend/eslint.config.js`**（新增一條 error 級自訂規則），並在**同一個 PR** 內處理 `frontend/src/pages/BrainPage.tsx:83` 現存的字串字面量 | `[Q1]`=B | 見 `§三` 的排序約束。不處理而先開規則 = 自己製造一次 CI 紅燈 |
| **S-5** | **`U2` 的交付物開始含執行期程式碼**（`BR1.5` 的 Pydantic validator）及其測試與突變驗證 | `[Q3]`=A | `unit-of-work.md:69` 給 `U2` 的字面是「型別來源 ＋ 一道 CI 檢查」，不含執行期行為；`functional-spec.md:11` 更逐字寫「沒有執行期程式碼」。見 `§四` 的更正 |
| **S-6** | **新增 `ADR-0019`** | `[Q4]`=A | `<record>/inception/decisions/0019-*.md`；全樹既有最大號為 `ADR-0018`，`0019` 未被占用（本站實查） |

---

## 一、威脅模型：STRIDE 套在產生鏈上

對象不是執行期的 WebSocket（那是 `U13`／`K-12`），而是**「契約如何從人手改的模型變成兩個
衍生物、以及那些變換如何被驗證」**這條鏈。

| 類別 | 本單元的具體威脅 | 處置 | 落點 |
|---|---|---|---|
| **S — Spoofing** | npm registry 上 `openapi-typescript@7.13.0` 被替換或該套件被接管，CI 執行的不是我們以為的程式碼 | `NFR5.2`：進 `devDependencies` 精確釘選、由 `package-lock.json`（含 integrity 雜湊）鎖定；四道閘門皆用本地解析版本 | 本單元 |
| **T — Tampering** | 有人手改 `ws-contract.json` 或 `ws-contract.d.ts`，讓型別看起來對而後端行為不對 | `BR4.1` ＋ 兩道閘門：任一衍生物被手改，對應那道即紅燈 | 本單元 |
| **T — Tampering（第二種）** | 客戶端訊息夾帶身分或 `turnId`，把授權判定交給客戶端 | `NFR5.7`：**白名單**斷言（見 `§五`），任何未宣告的欄位皆紅燈 | 本單元 |
| **R — Repudiation** | — | 本單元不產生執行期稽核記錄。它產生的是 **CI 的判決**，而判決的可信度由 `NFR5.2`／`NFR5.3` 承載 | — |
| **I — Information Disclosure** | 規格檔落到 `frontend/public/`，完整訊息地圖（9 種伺服器訊息、6 種客戶端訊息與全部 payload 欄位）對未認證訪客公開 | `NFR5.6`：repo 根、不得被前端 import；可機械檢查 | 本單元 |
| **D — Denial of Service** | 不適用——本單元無執行期資源可被耗盡 | — | — |
| **E — Elevation of Privilege** | subprotocol 格式前後端不一致 → 握手全面失敗（可用性），或前端寫死字串使 `NFR5.4` 的保護形同不存在 | `NFR5.4` 的承載 ＋ `[Q1]`=B 的 lint 規則（見 `§三`） | 本單元 ＋ `U14` |

**兩個刻意留空的格子**：Repudiation 與 DoS 判為不適用並附理由，不留空白——
`project.md` 的既有教訓是「缺一不可型 hard constraint 以逐項判定表呈現，
判定為不適用的項目一律附理由」。

---

## 二、ADR-0006 Security Baseline 四面向（本站決定的判定）

本表判的是**本站新增的設計解**，與上一站的同名表互補而非重複。

| 面向 | 判定 | 本站的設計解 |
|---|---|---|
| **IAM** | **適用** | `§五` 的白名單斷言。上一站的禁用名單改為由契約推導的白名單——差別不是精確度而是**封閉性**：禁用名單永遠列不完（身分等價欄位的命名空間是開放的），白名單由構造封閉 |
| **Encryption** | **適用（處置全在別的單元）** | 本單元不引入連線、不持久化資料。唯一相關的設計解是 `NFR5.6` 的否定式規則（規格檔不得公開可讀）。對話內容的靜態加密是 `OQ-3`，落 `U5` |
| **Network exposure** | **適用** | `§三`：subprotocol 是 token 的載體，本站給它**消費端的強制機制**（lint 規則），而不只是型別上的定義 |
| **Audit logging** | **適用** | `§六`：四道閘門的失敗語意必須 fail-closed，且 `NFR5.3` 的詞條在閘門被正當移除時必須同步移除——否則永久假紅燈，而假紅燈久了會被整條註解掉，等於自己關掉這道保護 |

**PBT hard constraint**：**不適用，附理由。** 本單元的新增交付中，唯一的執行期程式碼是
`BR1.5` 的 validator，它是一個兩值相等的比較，沒有值域可供性質測試；
`rules.md` 的 `calculation` category 實算為 **0**。PBT 在本 intent 的落點是 `U11` 與 `U6`。

---

## 三、`NFR5.4` 的消費端強制（`[Q1]`=B）

### 問題再述

上一站把 subprotocol 納入契約並驗證了型別層的保護（後端改 `scheme` → 前端的
`const SCHEME: Sub['scheme'] = 'bearer'` 立即 `tsc -b` 紅燈）。但那條保護**只在前端真的
由型別取值時成立**。前端若寫死 `` `bearer.${token}` ``，型別層碰不到它，而失敗是靜默的：
後端改格式時**握手全面失敗，四道閘門全綠**。

### 設計解

在 `frontend/eslint.config.js` 新增一條 **error 級**規則：**`new WebSocket` 的第二引數
不得出現字串字面量或模板字面量**。

```js
// 形狀示意（≤15 行，非實作）
{
  selector: "NewExpression[callee.name='WebSocket'] > ArrayExpression > :matches(Literal, TemplateLiteral)",
  message: "subprotocol 必須由 ws-contract.d.ts 的 WsSubprotocol 取值，不得寫死字串",
}
```

**必須是 `error`**：CI 跑 `npm run lint` = `eslint .`，**未加** `--max-warnings 0`
（`team.md` `## Code Style` 記載，本站複查屬實）。warn 級規則等於沒有閘門。

### 這條規則的排序約束（**本站實測後補**，不寫下會在啟用當下撞到）

`grep -rn "new WebSocket" frontend/src/` 全樹兩個命中：

| 檔 | 第二引數 | 新規則下 |
|---|---|---|
| `frontend/src/hooks/useCollaboration.ts:25` | 無第二引數 | 不受影響 |
| `frontend/src/pages/BrainPage.tsx:83` | `` [`bearer.${token}`] `` | **立刻紅燈** |

第二個是本 session 為展示加的 demo-scope 頁面，**它正是這條規則要抓的形狀**——
規則有效，不是誤判。因此：

> **這條規則不得在 `BrainPage.tsx` 仍持有字面量時啟用。** 同一個 PR 內必須二擇一：
> (a) 把 demo 頁改為由產生的型別取值；或 (b) 先刪掉 demo 頁（`U13`／`U14` 本來就會取代它）。

### 這條規則擋不住的（誠實記載）

只擋「第二引數直接寫字面量」這一種形狀。先把字串存進變數再傳入**不會**被擋
（AST 選擇器碰不到跨陳述的資料流）。要完全封住需要型別層的手段，而
TypeScript 的模板字面量型別無法區分「由常數組出的 `bearer.x`」與「手寫的 `bearer.x`」。
**本設計接受這個殘餘**：它把無心之失擋掉，擋不住刻意繞過——而刻意繞過會在 code review
留下痕跡，無心之失不會。

---

## 四、`NFR5.5` 的 `BR1.5` 落點，以及一處必須更正的上游敘述（`[Q3]`=A）

### 決定

`BR1.5`（`done`／`error` 的 `payload.turnId` 必須等於 `envelope.turnId`）以
**Pydantic `@model_validator`** 實作，**放在契約模組 `backend/services/brain_ws_contract.py` 內**。

**理由**：`BR1.5` 是契約不變量，它的自然歸屬就是契約本身。放到 `U13` 會讓「契約說什麼」
與「誰強制它」分家——而 `BR4.3` 那套兩道閘門的整個設計理念，正是不讓宣告與強制分離。

### 上游有一句話因此不再成立，在此更正（不回改已核可產出）

`functional-spec.md:11` 逐字：「本單元是 `spec` 類單元，交付的是型別與兩道 CI 閘門，
**沒有執行期程式碼**」。

`@model_validator` 會在**每一次**訊息構造時執行，是執行期程式碼。**那句話自本決定起過窄。**

依 `project.md` 的處置形狀（標出落差、指明現行規格，不逕自修改已通過 reviewer 的上游產出）：

> **現行規格以本檔為準**：`U2` 交付**型別 ＋ 兩道 CI 閘門 ＋ 一條 lint 規則 ＋ 一段
> 契約不變量 validator**。`functional-spec.md:11` 與 `unit-of-work.md:69` 的字面範圍
> 較窄，屬本站擴充，已列為 **S-5**。

**這個矛盾是我在上一站製造的**：`nfr-requirements` 的 `NFR5.5` 把落點寫成「後端模型的
validator」，同時上游說「沒有執行期程式碼」，兩句話並存了一整站才被本站的自檢抓到。
記在此處以免下游把它讀成「上游改了主意」——不是，是上游從一開始就自相矛盾。

### 連帶的測試義務

依 `construction.md`（測試需涵蓋 happy path ＋ 至少兩種錯誤／邊界）與本 repo 的
測試標準（`test-case-authoring.md` §5 的突變驗證）：

| 項 | 要求 |
|---|---|
| 落點 | `backend/tests/test_ws_contract.py`（`unittest`，非 pytest；首行 `import tests.helpers` 裝 psycopg2 樁） |
| 案例 | (1) 兩份 `turnId` 相等 → 通過；(2) 不相等 → `ValidationError`；(3) `payload.turnId` 缺失 → `ValidationError` |
| 突變驗證 | 把 validator 改成恆真、確認上述 (2)(3) 轉紅、還原複驗綠。結果寫進 `code-generation` 的計畫 |

---

## 五、`NFR5.7` 的斷言形狀：由禁用名單改為白名單（`[Q2]`=A）

### 為什麼改

上一站的可測判準是「欄位名集合與一份禁用名單的交集為空」，名單以「等」收尾。
審查 R-01 判為 Minor：不是封閉集合。但更根本的問題不是精確度，是**強度**——
禁用名單擋不住叫別的名字的身分欄位（`actor`、`onBehalfOf`、`impersonate`…），
而那個命名空間是開放的，列不完。

### 設計解

斷言**七個客戶端物件的欄位名集合「等於」一份釘在 dump 腳本內的預期集合**：

| 物件 | 來源 |
|---|---|
| `WsClientEnvelope` | `entities.md` |
| `HelloPayload`／`UserMessagePayload`／`SelectClarifyCandidatePayload`／`CorrectWorkItemPayload`／`SetSharingModePayload`／`SetWorkTargetPayload` | `entities.md`（六個 client payload，對應 `WsClientMessageType` 的六值） |

判定式：對 `ws-contract.json` 的 `components.schemas` 取上述七個 schema 的 `properties`
鍵集合，與預期集合**逐一相等比較**；任一不等即 exit 1。

**它由構造封閉**：任何新欄位——不管叫什麼——都會讓斷言紅燈，直到有人**刻意**去改
`dump_ws_contract.py` 內的預期集合。那個「刻意」正是本條要的東西：
新增一個客戶端欄位不再是一個人可以順手做完的事。

### 代價（寫下而非假裝沒有）

新增合法欄位要改兩處（Pydantic 模型 ＋ 預期集合）。這比禁用名單多一個動作，
而且**紅燈訊息不會告訴你「這個欄位是身分欄位」**——它只會說「欄位集合與預期不符」。
診斷性較差，換到的是封閉性。取捨明確：本條防的是授權繞過，漏掉一個比多紅一次嚴重。

### 與 `BR2.13` 的分工

`BR2.13`（客戶端不得攜帶 `turnId`，伺服器收到即回 `INVALID_REQUEST`）是**執行期**拒絕，
屬 `U13`。本條是**建置期**的不可構造。兩者是同一個不變量的兩層，缺一都有一條路徑：
只有建置期 → 惡意客戶端仍可手工送出帶 `turnId` 的 JSON；只有執行期 → 契約可以悄悄長出
一個身分欄位而沒人察覺。

---

## 六、四道閘門的失敗語意（fail-closed）

`NFR5.1`／`NFR5.2`／`NFR5.3` 共同依賴一件事：**閘門的綠燈必須代表「驗過且通過」，
而不是「沒驗成」**。

| 情形 | 必須的行為 | 理由 |
|---|---|---|
| `ws-contract.json` 不存在 | `--check` **exit 1** 並指明要跑 dump | 沿用 `dump_openapi.py` 既有形狀（該檔對缺檔明確 return 1） |
| 契約模組 import 失敗 | exit 非 0 | 不得以 try/except 吞掉後回報「無漂移」 |
| 產生器執行失敗（`npm run check:ws-types`） | exit 非 0 | 同上 |
| 白名單斷言或 `BR1.4`／`BR4.4` 斷言拋例外 | exit 非 0 | 斷言失敗與斷言跑不動，兩者都不得等同於通過 |

**這一條不是空話**：`construction.md` 的 `## Error Handling` 逐字要求
「Errors must be surfaced to the caller or logged — silent failures are not acceptable」，
而一個把例外吞掉回報 0 的檢查腳本，正是它禁止的形狀。

### `NFR5.3` 詞條的生命週期（「誰清」的執行設計）

上一站補了「閘門被正當改名或移除時必須同步移除詞條」的義務，本站給它可執行的形狀：

`REQUIRED_TEXT` 的 `ci.yml` 詞條與 `ci.yml` 的步驟是**一對一**的。
改動任一道閘門的指令字串時，`python3 scripts/validate_repo_contract.py` 會立即紅燈——
**那個紅燈就是提醒**。處置只有兩種：改詞條（閘門還在，只是換了寫法）或刪詞條
（閘門確實不需要了，而刪除本身要在 PR 描述說明理由）。

**不得**做的第三種：把該詞條整條註解掉「之後再處理」。那等於關掉這道保護而不留痕跡。

---

## 七、`NFR5.1`／`NFR5.2`／`NFR5.6` 的設計解（承接上一站，本站只補機制細節）

| 需求 | 上一站已定 | 本站補的機制 |
|---|---|---|
| `NFR5.1` 兩道閘門 | 指令、斷言對象、職責分工 | 失敗語意（`§六`）；`dump_ws_contract.py` 只 import 契約模組、不 import `main`，故閘門訊號只代表契約本身 |
| `NFR5.2` 依賴鎖定 | 進 `devDependencies` 精確釘 `7.13.0`、移除 `npx --yes` | `package-lock.json` 的 `integrity` 欄是實際的完整性保證（不只是版本號）；升版義務寫進 `ADR-0019` |
| `NFR5.6` 規格檔放置 | repo 根、不得進 `frontend/public/`、不得被前端 import | 可機械檢查：`ws-contract.json` 不得存在於 `frontend/public/`；`grep -r "ws-contract.json" frontend/src/` 須為空。兩者可併入 `validate_repo_contract.py`，但**本站不指定落點**——它是一條檢查而非一道新閘門，由 `code-generation` 決定併在哪 |

---

## 八、上一站審查 R-02 的處置

審查指出 `tech-stack-decisions.md §四` 用 `project.md` 的「單一可行解不出成題目」規則
同時為兩件事背書。本站引用 D-4 時分兩層陳述，並記下上游那一句的範圍過寬：

| 層 | 主張 | 強度 |
|---|---|---|
| (a) | 契約模組**不得**寫在 `U13` 的 router 檔內 | **被迫**——`unit-of-work.md:69` 給 `U2` 的擁有與交付是「型別來源」，寫在 `U13` 內即與已核可的單元邊界矛盾 |
| (b) | 它該放 `backend/services/` 而非 `backend/models/` 或新的 `backend/contracts/` | **慣例選擇**——延續 `team.md` 記載的既有分層（`wa_rule_engine.py` 等純引擎模組放 `services/`）。合法的替代目錄存在，只是不延續慣例 |

**上游把 (b) 也掛在「單一可行解」之下，範圍過寬。** 不回改上游，在此標明。

---

## 九、Assumptions & Open Questions

- **ESLint 自訂規則的實作形式未定**：`no-restricted-syntax` 配 AST 選擇器（零新依賴）
  vs 自寫 plugin（較好的訊息與測試）。本站不預選，留 `code-generation`；
  **但無論哪種都必須是 `error` 級**（`§三`）。
- **`§三` 的排序約束有時效**：它只在 `BrainPage.tsx` 仍存在時成立。若 `U13`／`U14`
  先落地並取代該頁，約束自動消失。屆時執行者須複查，不得照抄本節。
- **白名單的預期集合放在 dump 腳本內是本站的選擇**，替代方案是放獨立的 JSON。
  放腳本內的理由是「改它需要碰一支有 review 的程式碼」；放 JSON 較易讀但較易被順手改。
  未實測兩者在 review 中的實際差別。
- **`NFR5.6` 的兩條機械檢查未指定落點**（見 `§七`），由 `code-generation` 決定。
- **`ADR-0019` 的編號已實查未被占用**（全樹既有最大為 `ADR-0018`，位於
  `260916-estimate-upload-rework/inception/decisions/0018-catalog-price-api-credentials.md`）。
  注意本 repo 的 ADR 編號是**跨 intent 全域遞增**，但實體檔案分散在各 intent 的
  `decisions/` 下，且歷史上出現過跨 intent 撞號（`0013`／`0014` 各有兩份）——
  本站沿用全域遞增，不重用。
