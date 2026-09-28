# Functional Design Questions — `U2 brain-ws-contract`（`spec`）

## 前言：上游已定案、本站不重問

`K-02`（`contract-summary.md:171–305`）與 `K-12`（`:853–997`）已經把這個單元定得很細。
下列各項**可引用到具體定案**，本站不重問：

| 已定案 | 出處 |
|---|---|
| 後端 Pydantic 模型為唯一真實來源，兩個衍生物 commit 進版控但不得手改 | `[C2]`=A，`K-02` `source_of_truth`／`derived_artifacts` |
| 兩道 CI gate 的分工（backend 驗「規格檔＝程式碼」、frontend 驗「型別檔＝規格檔重產」） | `K-02` `ci_gates`；理由沿用 `frontend/scripts/check-api-types.mjs` 既有註解 |
| 為何需要新閘門（WS 不在 `openapi.json` 的 42 個 path 內） | `K-02` `why_new_gate_is_needed` |
| envelope 三個必填欄位 `v`／`type`／`turnId` | `K-02` `envelope.required_fields` |
| 八種 server→client 與五種 client→server 訊息型別及其 payload | `K-02` `types`／`client_to_server` |
| `confidence` 為選填且不得列為必填 | `components.md` 逐字、`mockups.md` H-2 |
| `status` 五值為下限、`estimateSetId` 為 required | `[RA:FR1.2]`、`K-02` X-01 |
| 版本協商走**首則 `hello` 訊息**而非 HTTP upgrade 階段 | `K-12` `x-handshake.version_note`（兩個已定案相加後的唯一解） |
| 終止語意（`done` 需非空白內容、`EMPTY_RESPONSE`、每輪至多一個終止事件） | `K-12` `x-termination-semantics` |
| 本契約無授權責任、無執行期副作用、dump 與型別產生皆冪等 | `K-02` `behaviour_semantics` |
| 扇出假設單一後端行程（`backend/Dockerfile:37` 無 `--workers`） | `K-12` `fanout_mechanism_and_its_assumption` |

---

## Q1：`error` 訊息的 `code` 集合——`K-02` 指向 `K-12`，但 `K-12` 沒有定義它

**這是一個懸空引用，不是我沒找到。** `K-02:269` 逐字寫「終止事件。code 的集合見 K-12」，
而 `K-12` 的 `x-close-codes` 是 **WebSocket 關閉碼**（`4401`／`4403`／`4400`／`1011`）——
那是連線層的關閉原因，不是 `error` **訊息** payload 裡的 `code` 字串。全檔唯一具名的
error code 是 `EMPTY_RESPONSE`（來自回補項 `N-14`）。

這件事對本單元是實質的：`code` 是 `error` payload 的必填欄位，而本單元要產生型別。
「開放字串」與「封閉列舉」產生的型別不同，前端能不能 `switch` 窮盡也不同。

- **A**（建議）**封閉列舉，本站定義初版集合，並把「新增 code 必須改契約」寫成規則。**
  初版至少含 `EMPTY_RESPONSE`（`N-14` 已定）、`INTERNAL_ERROR`（對應 `1011` 的訊息層）、
  `UNAUTHORIZED`（對應無權限但連線仍在的情形）。前端可窮盡 `switch`，漏處理會被 `tsc` 抓到。
  代價：每新增一種錯誤都要改後端模型並重跑兩道 gate（這正是閘門存在的目的，但確實是摩擦）。
- **B**：**開放字串 ＋ 前端必須有 default 分支。** 後端可自由新增 code 不必改契約。
  代價：型別退化為 `string`，`tsc` 對「前端漏處理新 code」完全無感——而這正是本 repo
  `team.md` 記載的既有痛點（手寫 interface 讓 schema 落差靜默通過）。
- **C**：**封閉列舉，但初版只放 `EMPTY_RESPONSE`**，其餘等實際需要時再加。
  最小承諾，但 `1011` 內部錯誤發生時沒有對應的訊息層 code 可送。
- **D**：不在本站定，記為 open question 交給 `U13 brain-gateway` 的 functional-design。
  代價：`U2` 要先於 `U13` 交付（DAG 上 `U13` 依賴 `U2`），所以型別會在 code 未定時就凍結。

[Answer]: A  <!-- answered 2026-09-27T16:02:35Z -->

---

## Q2：協定版本 `v` 的初值與「相容」的判準

`K-12` 定了版本協商的**機制**（客戶端送 `hello { v }`、伺服器比對、不相容以 `4400` 關閉
並帶 `expected` 與 `received`），但**沒有定初值，也沒有定「相容」是什麼意思**。
本單元是型別來源，`v` 的型別與語意屬於本契約。

- **A**（建議）**`v: 1`，相容判準為「完全相等」。**
  最簡單且二元可判：`received !== expected` 即 `4400`。本 intent 是第一版，沒有需要
  向後相容的既有客戶端。代價：任何契約變更都會讓舊分頁被踢掉——但那正是想要的行為
  （舊分頁拿著舊型別，繼續連線只會在執行期拿到未定義值）。
- **B**：`v: 1`，相容判準為「伺服器 `v` ≥ 客戶端 `v`」（向後相容）。
  舊分頁可繼續運作。代價：伺服器必須真的維持舊形狀，而本契約**沒有任何機制**強制它——
  兩道 gate 只驗「當前程式碼與當前規格一致」，不驗「新規格與舊規格相容」。
  選 B 等於做出一個沒有承載機制的承諾。
- **C**：語意化版本（`major.minor`），major 不等即不相容。
  表達力最強，代價是 `v` 從 integer 變成 string，與 `K-02` 逐字的
  `v: { type: integer }` 衝突——選它需要同時修改已核可的 `K-02`。

[Answer]: A  <!-- answered 2026-09-27T16:02:35Z -->

---

## Q3：`sideEffect` 的型別——`enum: none|unknown|string` 無法直接產生型別

`K-02` 的 `work_items.items.sideEffect` 逐字是 `"enum: none|unknown|string"`。
這不是一個可產生的型別：前兩個是字面值、第三個是型別名。而 `unknown` 有明確的上游語意
（`components.md` 逐字「系統不承諾停掉時不留半成品」），不能被合併掉。

- **A**（建議）**`"none" | "unknown" | string`（即 TS 的 `string`，但保留兩個具名常數）。**
  忠實於原意：有兩個有意義的哨兵值，其餘是自由描述文字。實作上前端以 `=== "none"`／
  `=== "unknown"` 判斷，其餘視為描述。代價：TS 會把這個聯集塌縮成 `string`，
  IDE 不會提示那兩個字面值——需要在型別旁加註解說明。
- **B**：拆成兩個欄位——`sideEffectKind: "none" | "unknown" | "described"` ＋
  `sideEffectText: string | null`。型別完全可判，前端能窮盡 `switch`。
  代價：改變了 `K-02` 已核可的 payload 形狀（一個欄位變兩個），屬於對上游契約的修改，
  需明標為本站新增。
- **C**：`"none" | "unknown"` 兩值封閉列舉，自由文字另放 `detail: string | null`。
  與 B 類似但語意更清楚（kind 與 detail 正交）。同樣改動了上游形狀。

[Answer]: A  <!-- answered 2026-09-27T16:02:35Z -->

---

## Q4：`ws-contract.json` 的涵蓋範圍

`K-02` 說本契約是「訊息型別來源」，`K-12` 另外持有端點、握手、關閉碼與終止語意。
但**兩道 CI gate 只保護寫進 `ws-contract.json` 的東西**——沒進去的部分漂移時無人察覺。

- **A**（建議）**只放訊息型別（envelope ＋ 兩個方向的 payload），關閉碼與端點路徑不進。**
  嚴格對應 `K-02` 的擁有範圍，不越界進 `K-12`。代價：關閉碼與端點路徑沒有漂移保護——
  但它們屬 `U13` 的交付，由 `U13` 自己的驗證承擔，本站明寫此界線。
- **B**：訊息型別 ＋ **關閉碼常數**（`4400`／`4401`／`4403`／`1011`）。
  前端需要這些數字來分辨關閉原因，放進共用契約可避免前後端各寫一份。
  代價：`U2` 開始持有 `K-12` 的一部分，兩個契約的擁有邊界變模糊。
- **C**：訊息型別 ＋ 關閉碼 ＋ 端點路徑 ＋ 協定版本常數（全部 WS 相關常數）。
  前端完全不必硬寫任何 WS 常數。代價同 B 但更重。

[Answer]: A  <!-- answered 2026-09-27T16:02:35Z -->

---

## Q5：`J-10`（`mockups.md` H-7 改寫）落在本站——做，還是轉走？

`contract-summary.md:1473` 的交接表把 `J-10` 指派給 **`functional-design`（3.1）**，
內容是把 `mockups.md` 的 H-7 依 `N-14` 改寫為描述 `EMPTY_RESPONSE` 與
「零內容 `done` ＝契約違規」兩種情境；並註明「CONDITIONAL；skip 轉 `code-generation`」。

本站**沒有被 skip**，所以這個指派現在落在我身上。但它改的是 `refined-mockups` 的已核可
產出，而 `project.md` 的既有形狀是「發現上游缺口時標出缺口、指派落點，**不逕自修改已通過
reviewer 的上游產出**」。兩者有張力。

- **A**（建議）**不改 `mockups.md`，改在本站的 `functional-spec.md` 寫明這兩種情境的前端義務，
  並在產出中標明「`J-10` 的實質內容已在此承載，`mockups.md` H-7 仍為舊描述」。**
  滿足指派的**意圖**（讓這兩種情境有落點）而不違反「不回改已核可上游」。
  代價：`mockups.md` 與 `functional-spec.md` 對 H-7 的描述不一致，需要明寫哪一份是現行的。
- **B**：照指派字面改 `mockups.md` H-7。
  交接表明文指派本站，照做最直接。代價：修改已通過 reviewer 的上游產出，
  與 `project.md` 的既有處置形狀相反；且 `refined-mockups` 的核可狀態會變得可疑。
- **C**：兩者都做——`functional-spec.md` 寫實質內容，同時在 `mockups.md` H-7 加一行指向它
  （不改原描述，只加指標）。代價：仍然動到已核可產出，但改動是**純附加**、不推翻原文。
- **D**：轉給 `code-generation`（交接表為 skip 情形指定的落點）。
  代價：本站沒有被 skip，所以這是把一個現在就能處理的指派往後推，且 `code-generation` 的
  範圍是產生程式碼，不是改 mockup 文件。

[Answer]: A  <!-- answered 2026-09-27T16:02:35Z -->

---

## Q6（一致性追問，Step 3 歧義分析查出）：`v` 的**值** `1` 住在哪裡？

Q2=A 定了 `v: 1` 且相容判準為完全相等；Q4=A 定了「只放訊息型別，關閉碼與端點路徑不進」。
兩者相加留下一個缺口：**envelope 的 `v` 欄位是訊息型別（在契約內），但值 `1` 呢？**
前端必須送 `hello { v: 1 }`，那個 `1` 得有來源。Q4-C 才明確包含「協定版本常數」，
而使用者選的是 Q4-A。

這不是措辭問題：若前端硬寫 `1`，那是 `team.md` 的「單一真實來源」明令禁止的第二份副本，
而且契約升到 `2` 時**沒有任何機制**會讓前端紅燈——正好是本單元存在的理由的反面。

- **A**（建議）**把 `v` 的型別從 `integer` 收窄為字面型別 `1`。**
  值住在型別裡，型別住在契約裡，兩道 gate 自動保護它。前端寫 `{ v: 1 }`；契約升到 `2` 時
  前端的 `1` 立刻是型別錯誤，`tsc -b` 紅燈。**不需要新增任何常數欄位，Q4-A 的範圍不變。**
  代價：字面型別 `1` 比 `K-02` 逐字的 `v: { type: integer }` 更窄——這是收窄而非改形狀，
  且「完全相等」在型別層的忠實表達就是字面值，但仍須明標為本站對上游的收窄。
- **B**：`ws-contract.json` 增加一個 `protocolVersion: 1` 常數欄位（實質等於 Q4-B 的一小步）。
  明確、易讀。代價：契約檔開始承載「非訊息型別」的東西，Q4-A 的界線被自己破一個口，
  之後「關閉碼為什麼不能也放進來」就沒有原則性答案了。
- **C**：前端硬寫 `1`，並加一個測試斷言它等於契約檔裡的值。
  代價：仍是兩份副本，只是加了鎖。而 `team.md` 的規則允許這種形狀的前提是「確實無法避免」
  ——這裡 A 已證明可以避免，所以這條不成立。

[Answer]: A  <!-- answered 2026-09-27T16:23:50Z -->

---

## Assumptions & Open Questions

- `U2` 在 DAG 上是可平行根（無依賴），被 `U13`、`U14` 依賴——所以本站的決定會直接約束
  那兩個單元，且它們無法反過來影響本站。
- 本單元承載 `US1.2`（AC1.2.1–AC1.2.4）與 `US8.1`（AC8.1.1–AC8.1.4）兩則故事，但**只承載
  它們的型別面**：`AC1.2.1` 的信心值門檻判斷在 `U11`，`AC8.1.2` 的活動記錄在 `U13`，
  `AC8.1.3` 的 token 傳輸在 `U13`。本站的 traceability 會如實反映這個界線，不宣稱覆蓋。
- `AC1.2.4` 要求路由層輸出 0–1 信心值，而 `stories.md:655–657` 記載 `OQ-10` 質疑路由層
  能否產出可比較的信心值。若該 OQ 收斂為「不能」，`clarify.candidates[].confidence`
  的型別（目前 `number|null`）不需改（已容許 null），但 `AC1.2.1` 的門檻判斷會改寫——
  那在 `U11`，不在本站。

---

## Consolidated Summary Confirmation

六項定案彙整（每一項都會直接決定產出的內容）：

| # | 定案 | 後果 |
|---|---|---|
| Q1 | `error.code` 為**封閉列舉**，初版三個：`EMPTY_RESPONSE`、`INTERNAL_ERROR`、`UNAUTHORIZED` | 前端可窮盡 `switch`，漏處理被 `tsc` 抓到；新增 code 必須改後端模型並重跑兩道 gate |
| Q2 | `v: 1`，相容判準為**完全相等** | `received !== expected` 即以 `4400` 關閉；舊分頁會被踢掉（刻意） |
| Q3 | `sideEffect` 保留原形狀：`"none" \| "unknown" \| string` | 不改動 `K-02` 已核可的 payload 形狀；TS 會塌縮成 `string`，需在型別旁加註解保住兩個哨兵值的語意 |
| Q4 | `ws-contract.json` **只放訊息型別**（envelope ＋ 兩方向 payload） | 關閉碼與端點路徑**沒有漂移保護**，由 `U13` 自己的驗證承擔，本站明寫此界線 |
| Q5 | **不改** `mockups.md`，`J-10` 的實質內容寫進 `functional-spec.md` | 滿足指派的意圖而不回改已核可上游；兩份檔對 H-7 的描述不一致，須明寫哪一份是現行的 |
| Q6 | `v` 的型別由 `integer` **收窄為字面型別 `1`** | 值住在型別裡、型別住在契約裡，兩道 gate 自動保護；**這是對 `K-02` 逐字 `type: integer` 的收窄**，須明標 |

**兩項必須在產出中顯性標示的收窄／偏離**（不是悄悄做掉）：

1. **Q6 對 `K-02` 的收窄**：上游逐字 `v: { type: integer }`，本站收窄為字面 `1`。
   理由是「完全相等」在型別層的忠實表達就是字面值，且它讓值不必存在第二份副本。
2. **Q5 造成的文件不一致**：`mockups.md` H-7 仍是舊描述，現行描述在本站的 `functional-spec.md`。

**一項本站查出、要回報給上游的契約缺口**：`K-02:269` 寫「`error` 的 `code` 集合見 `K-12`」，
而 `K-12` 只定義了 **WebSocket 關閉碼**（`4401`／`4403`／`4400`／`1011`），沒有定義 `error`
訊息的 `code`。這是懸空引用，本站以 Q1 補上並在產出標明它原本無來源。

- Looks correct
- Request changes

[Answer]: Looks correct  <!-- answered 2026-09-27T16:25:18Z via picker -->
