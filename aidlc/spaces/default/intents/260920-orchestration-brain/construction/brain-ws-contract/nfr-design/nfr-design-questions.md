# NFR Design 問題檔 — `U2 brain-ws-contract`（`spec`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: brain-ws-contract · kind: spec -->

## 前言：本站問什麼、不問什麼

`U2` 的 kind 是 `spec`，`produces_kinds` 把七項產出濾成**兩項**：`security-design.md`
與 `traceability.json`（`logical-components` 的 kind 清單是 `[service, ui, library]`，
不含 `spec`）。本站要為上一站的 `NFR5.1`–`NFR5.7` 七條需求各給出**具體的設計解**。

上一站已經把大部分機制定到相當具體的程度（產生器、規格檔形狀、`WsSubprotocol` 的承載、
四道閘門的指令）。本站因此**只問四件上一站刻意留下或留錯的事**，其餘不重問。

### 上一站已定案、本站不重問（每項附可引用的依據）

| 事項 | 定案 | 依據 |
|---|---|---|
| 型別產生器 | `openapi-typescript@7.13.0` | `[Q1]`=A；`tech-stack-decisions.md` D-1，含本站實測 |
| 規格檔形狀 | 最小 OpenAPI 3.1 外殼 ＋ `components.schemas` | D-2 |
| 依賴鎖定 | 進 `devDependencies` 精確釘 `7.13.0`，四道閘門皆用本地解析版本 | `[Q2]`=A；`NFR5.2` |
| subprotocol 承載 | `WsSubprotocol` 模型（`scheme`／`separator` 皆字面型別） | `[Q3]`=A；D-5；已實測產出字面型別 |
| 閘門存在性偵測 | `REQUIRED_TEXT` 新增 `ci.yml` 一鍵，涵蓋四道 | `[Q5]`=A；`NFR5.3` |
| 契約模組落點 | `backend/services/brain_ws_contract.py` | D-4 |
| 規格檔放置 | repo 根，不得進 `frontend/public/`、不得被前端 import | `NFR5.6` |

### 上一站審查留下的兩項 Minor，本站的處置

| 發現 | 本站處置 |
|---|---|
| **R-01**：`NFR5.7` 的禁用欄位名單以「等」收尾，不是封閉集合，與同文件其他判準有精確度落差 | **本站 Q2 就是它的收斂點。** 把需求轉成可執行的設計解正是本站職責，不需回頭解凍已凍結的 `nfr-requirements` 產出 |
| **R-02**：`tech-stack-decisions.md §四` 用「單一可行解」規則同時為「不得在 `U13` 內」（被迫）與「該放 `backend/services/`」（慣例選擇）兩件事背書 | 不改上游。本站的 `security-design.md` 在引用 D-4 時**分兩層陳述**，並註明上游那一句的範圍過寬 |

---

## 本站查證到的事實（供題幹引用，非來源標籤）

1. **`functional-spec.md:11` 逐字**：「本單元是 `spec` 類單元，交付的是型別與兩道 CI 閘門，
   **沒有執行期程式碼**」。
2. **`unit-of-work.md:69` 逐字**給 `U2` 的擁有與交付：「前後端共用的 WS 訊息型別來源 ＋
   一道新的 CI 一致性檢查（N-1）」——未提任何執行期行為。
3. **上一站的 `NFR5.5` 把 `BR1.5` 的斷言落點寫成「後端模型的 validator」**。
   Pydantic 的 `@model_validator` 會在**每一次**訊息構造時執行，是執行期程式碼。
   → 事實 1／2 與事實 3 **不能同時為真**。這是我在上一站自己製造的矛盾，本站 Q3 解它。
4. **`entities.md` 宣告的六個 client payload**：`HelloPayload`、`UserMessagePayload`、
   `SelectClarifyCandidatePayload`、`CorrectWorkItemPayload`、`SetSharingModePayload`、
   `SetWorkTargetPayload`；加上 `WsClientEnvelope` 本身。這七個物件的欄位集合是封閉且
   可從契約檔機械讀出的。
5. **`frontend/` 的 ESLint 是 flat config**（`eslint.config.js`），CI 跑 `eslint .`
   且**未加** `--max-warnings 0`，故只擋 error 級。自訂規則若設為 warn 等於沒有閘門。
6. **repo 既有 ADR 編號已用到 ADR-0018**（`project.md` 的 `## Forbidden` 引用到它）。

---

## Q1 — `GAP-1`（前端可能不使用產生的 subprotocol 常數）要給什麼設計解？

上一站把它標為 `GAP`，落點 `U14`，並誠實寫下「閘門只在前端真的由型別取值時成立」。
本站要決定**那個落點拿到的是什麼**——一句叮嚀，還是一個機制。

失敗模式再述一次：前端寫死 `` `bearer.${token}` ``，型別層碰不到它；後端改格式時
**握手全面失敗，而四道閘門全綠**。

- **A（建議）— 契約多產生一支執行期常數模組**：dump 之後再產生
  `frontend/src/types/ws-contract.consts.ts`（`export const WS_SUBPROTOCOL = { scheme: 'bearer', separator: '.' } as const;`），
  前端必須 import 它。後端改值 → 該檔重產 → 前端若寫死字串，值就與常數不符（但**型別仍通過**
  ——所以本選項真正的保護是「只有一個地方有那個字串」，不是型別錯誤）。
  代價：第三個衍生物 ＋ 第三道閘門（committed 常數檔 == 由規格檔重產）。
- **B — ESLint 規則：禁止 `new WebSocket` 的第二引數出現字串字面量**：成本最低
  （一條 flat config 規則），直接擋住「寫死」這個具體動作。**必須設為 `error`**——
  事實 5：CI 未加 `--max-warnings 0`，warn 級規則等於沒有閘門。
  代價：只擋字面量這一種寫法，繞過方式（先存成變數）不會被擋。
- **C — 維持現狀（只在 `U14` 的 code review 把關）**：零成本。
  代價是把一個已知的靜默失敗留給人眼，而 `GAP-1` 的整段論證就是在說人眼看不出它。

[Answer]: B <!-- answered 2026-09-28T03:56:07Z — ESLint error 規則：禁止 new WebSocket 第二引數出現字串字面量。
     **更正（2026-09-28T03:56:28Z）**：初寫誤記為 A。提問時我把 ESLint 那個選項排到第一位（為了讓建議項排前面），
     寫回時卻依**位置**而非依**內容**對應——這正是 project.md `feasibility:7e354cfd` 記載過的同一個失誤，
     本專案第二次發生。使用者實選的內容是本檔的 **B**（ESLint 規則），不是 A（多產一支常數模組）。
     Q2／Q3／Q4 已逐一回頭以**內容**核對，三題的選單第一項都確實對應本檔的 A，無誤記。 -->

## Q2 — `NFR5.7` 的機械斷言要用「禁用名單」還是「由契約推導的白名單」？（直接收斂審查 R-01）

上一站寫的是禁用名單並以「等」收尾。審查判為 Minor：不是封閉集合，`code-generation`
需要猜。本站要給出封閉的形狀。

- **A（建議）— 反向改為白名單：斷言七個客戶端物件的欄位集合「等於」契約宣告的集合**：
  依事實 4，`WsClientEnvelope` ＋ 六個 client payload 的欄位名是封閉且可從
  `ws-contract.json` 機械讀出的。斷言式為「實際欄位集合 == 一份釘在 dump 腳本內的預期集合」。
  **它由構造封閉**：任何新欄位——不管叫 `userId`、`actor`、`onBehalfOf` 還是別的——
  都會讓斷言紅燈，直到有人**刻意**去改那份預期集合。禁用名單則永遠列不完
  （身分等價欄位的命名空間是開放的）。
  代價：新增合法欄位時要改兩處（模型 ＋ 預期集合），比禁用名單多一個動作——
  但那個多出來的動作正是本條要的「刻意」。
- **B — 維持禁用名單，但收斂成封閉清單**：列出 `userId`／`user_id`／`role`／`roles`／
  `token`／`accessToken`／`turnId` 等具體名稱，並指名誰負責維護。
  比現況精確，但**保護強度不變**：叫別的名字的身分欄位仍然通得過。
- **C — 兩者並用**：白名單擋結構、禁用名單擋命名，紅燈訊息更好讀。
  代價是兩份東西要維護，而白名單已經涵蓋禁用名單能擋的全部情形。

[Answer]: A <!-- answered 2026-09-28T03:56:07Z — 反向改為白名單：斷言七個客戶端物件的欄位集合等於釘在 dump 腳本內的預期集合 -->

## Q3 — `BR1.5` 的 validator 要不要放進本單元？（事實 1／2 與事實 3 的矛盾）

上一站的 `NFR5.5` 把 `BR1.5`（`done`／`error` 的 payload `turnId` 必須等於 envelope 的
`turnId`）落點寫成「後端模型的 validator」。但 `functional-spec.md:11` 逐字說本單元
「**沒有執行期程式碼**」，而 Pydantic 的 `@model_validator` 每次構造訊息都會跑。
**兩句話不能同時為真**，這是我在上一站製造的矛盾，本站必須擇一。

- **A（建議）— validator 留在契約模組內，並更正「沒有執行期程式碼」這句話**：
  `BR1.5` 是**契約不變量**，它的自然歸屬就是契約本身；放到 `U13` 會讓「契約說什麼」
  與「誰強制它」分家，而那正是 `BR4.3` 那套兩道閘門在防的形狀。
  代價：`U2` 的交付物確實含一段會在請求路徑上跑的程式碼，上游那句描述要在本站產出中
  **明確標為過窄並更正**（不回改已核可的 `functional-spec.md`，依 `project.md` 的處置形狀
  標出落差、指明現行規格以本站為準）。另：那段 validator 需要測試與突變驗證。
- **B — validator 移交 `U13`，本單元只留文件敘述**：上游那句話維持為真、`U2` 的邊界最乾淨。
  代價是 `BR1.5` 在 `U2` 落地時**沒有任何強制**，而 `rules.md` 對它逐字寫過
  「**可機械驗證**：後端模型的 validator 可直接斷言，建議在 `code-generation` 實作」——
  移交等於把一條已判定可機械驗證的規則降級為口頭約定，直到 `U13` 那個 Bolt 為止。
- **C — 改為建置期斷言（不進執行期）**：在 `dump_ws_contract.py --check` 內斷言
  「`DonePayload` 與 `ErrorPayload` 都宣告了 `turnId` 欄位且型別與 envelope 的一致」。
  這保住「沒有執行期程式碼」，但**它驗的是型別宣告、不是值**——`BR1.5` 要求的是
  兩個**值**相等，建置期碰不到值。誠實地說，這個選項只擋得住結構性漂移，擋不住實際不一致。

[Answer]: A <!-- answered 2026-09-28T03:56:07Z — validator 留在契約模組；上游「沒有執行期程式碼」一句在本站產出中標為過窄並更正 -->

## Q4 — 本單元的決定要不要開一份 ADR？

`project.md` 逐字要求「架構級決策開 ADR 於 `<record>/inception/decisions/NNNN-*.md`」。
本單元有兩項決定的影響**超出本單元**：`[Q2]`=A 改變了既有兩道型別閘門的依賴取得方式
（動到 `frontend/package.json` 與 `check-api-types.mjs`）；`[Q3]`=A 把 subprotocol 的
名稱與格式納入契約，是 `K-02` 的第三次擴充。既有 ADR 編號已用到 ADR-0018（事實 6）。

- **A（建議）— 開一份 ADR-0019，涵蓋「WS 契約閘門與型別產生器的供應鏈」**：
  把 Q1／Q2／Q5 三題的決定與其對既有資產的影響寫成一份可被未來引用的決策紀錄。
  理由：`[Q2]`=A 改的是**全 repo 的型別產生方式**，不只本單元；下一個碰 `gen:types`
  的人需要知道為什麼那裡不再有 `npx --yes`。代價：多一份文件與一次 contract 驗證。
- **B — 不開 ADR，理由寫進本站產出**：本單元的決定都已寫在 `tech-stack-decisions.md`
  與 `security-design.md`，且三項都已列為需回補 scope 的 S 項、會再被看到一次。
  代價：`frontend/package.json` 的改動理由只存在於一個 intent 的 record 深處。
- **C — 開 ADR，但只涵蓋 `K-02` 的三次擴充**（`ready`／`select_clarify_candidate`／
  `WsSubprotocol`）：那三項本來就需要上游追認，一份 ADR 正好作為追認的載體。
  供應鏈那一項留在本站產出內。

[Answer]: A <!-- answered 2026-09-28T03:56:07Z — 開 ADR-0019，涵蓋 WS 契約閘門與型別產生器的供應鏈 -->

---

## 收齊答案後的矛盾與覆蓋檢查（stage 檔 Step 3，必做）

**定案（以內容為準，非選單位置）**：Q1=**B**（ESLint error 規則）、Q2=**A**（白名單）、
Q3=**A**（validator 留契約模組）、Q4=**A**（開 ADR-0019）。

### 模糊語檢查

四個答案都是具體機制，無「看情況」「大概」「混用」這類詞。**無模糊項。**

### 跨題矛盾檢查

| 組合 | 判定 | 說明 |
|---|---|---|
| Q1=B × Q3=A | **無矛盾，但兩者都擴大了 `U2` 的交付物種類** | Q3=A 讓 `U2` 含一段執行期程式碼（validator）；Q1=B 讓它再含一條前端 lint 規則。兩者都超出 `unit-of-work.md:69` 的「型別來源 ＋ 一道 CI 檢查」字面。已列為 S 項 |
| Q2=A × `entities.md` | **無矛盾** | 白名單的來源正是 `entities.md` 宣告的七個客戶端物件（事實 4），由契約自身推導而非另立一份清單 |
| Q4=A × `project.md` | **無矛盾** | 「架構級決策開 ADR」逐字要求；`[Q2]`=A 改的是全 repo 的型別產生方式，符合「影響超出本單元」的判準 |

### Q1=B 的可達性與假紅燈檢查（`project.md` 自檢 1，**本站實測**）

出題時沒查這件事，答案定案後補查 —— 結果它直接決定這條規則什麼時候才能開啟。
`grep -rn "new WebSocket" frontend/src/` 全樹**兩個**命中：

| 檔 | 第二引數 | 新規則下的判定 |
|---|---|---|
| `frontend/src/hooks/useCollaboration.ts:25` | **無第二引數** | 不受影響 |
| `frontend/src/pages/BrainPage.tsx:83` | `` [`bearer.${token}`] `` | **會立刻紅燈** |

第二個命中是本 session 為今晚展示加的 demo-scope 頁面，而它**正是這條規則要抓的那個形狀**
——規則有效，不是誤判。但這產生一條真實的排序約束：

> **這條 lint 規則不得在 `BrainPage.tsx` 仍持有字面量時啟用。** 同一個 PR 內必須二擇一：
> (a) 把 demo 頁改為由產生的型別取值，或 (b) 先刪掉 demo 頁（`U13`／`U14` 本來就會取代它）。
> 兩者皆未做而先開規則，等於自己製造一次 CI 紅燈。

**這一點必須寫進 `security-design.md`**，否則 `code-generation` 會在啟用規則的那一刻撞到它。

### 覆蓋檢查（七條 `NFRx.y` 是否都拿到設計解）

| 需求 | 本站的設計解 |
|---|---|
| `NFR5.1` 契約來源與兩道閘門 | 上一站已定到可執行程度；本站只補威脅模型與失敗語意 |
| `NFR5.2` 閘門程式碼必須鎖定 | 上一站已定；本站補 ADR-0019（Q4=A）作為跨 intent 可引用的決策紀錄 |
| `NFR5.3` 閘門存在性必須被斷言 | 上一站已定；本站補「詞條被正當移除時的同步義務」的執行設計 |
| `NFR5.4` 契約涵蓋 subprotocol | 上一站定了承載形式；**本站補它的消費端強制**（Q1=B） |
| `NFR5.5` 三條機械斷言 | **本站定 `BR1.5` 的落點**（Q3=A）與其測試義務 |
| `NFR5.6` 規格檔放置 | 上一站已定；本站補可機械檢查的形式 |
| `NFR5.7` 授權繞過不可構造 | **本站把斷言由禁用名單改為白名單**（Q2=A），收斂審查 R-01 |

七條皆有落點，無遺漏。

### 本階段新增、已核可 scope 尚未涵蓋（需回補）

| 項 | 新增了什麼 | 觸發 |
|---|---|---|
| **S-4** | 修改既有的 `frontend/eslint.config.js`（新增一條 error 級自訂規則）＋ 同一個 PR 內處理 `BrainPage.tsx:83` 的字面量 | Q1=B |
| **S-5** | `U2` 的交付物含執行期程式碼（`BR1.5` 的 Pydantic validator）及其測試與突變驗證 | Q3=A |
| **S-6** | 新增一份 ADR（`ADR-0019`） | Q4=A |

S-1…S-3 由上一站列出，本站不重複。

### 一處必須揭露的紀錄瑕疵

**本輪的 `QUESTION_ANSWERED` audit 事件把 Q1 記成 `A`，內容敘述則是正確的 ESLint 規則。**
成因是提問時我把 ESLint 選項排到第一位、寫回時依位置而非依內容對應——
即 `project.md` `feasibility:7e354cfd` 記載過的同一個失誤，本專案**第二次**發生。
問題檔已就地更正為 `B` 並附理由；audit shard 的那一筆無法補記（引擎要求新的人工回合才接受
第二次 `answer`，這是正確的防護）。**現行定案以本檔為準。**

## Consolidated Summary Confirmation

[Answer]: Looks correct <!-- answered 2026-09-28T04:01:03Z -->
