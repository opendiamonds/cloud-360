**Collaborator:** aidlc-quality-agent

## Contribution

<!-- 視角：Given/When/Then 可測試性、INVEST Testable、DoD≠AC、403 allow/deny、
     具名 PBT 性質、Playwright 斷言內容、第一段／第二段可獨立驗收。
     Stance: refute。本檔不改 stories.md／personas.md。 -->

### 0. 計數與結構

`stories.md` 現有 **33 條 AC**（C1-1：10、C1-2：5、C1-3：8、C1-4：4、C1-5：6）。**DoD 只出現在 C1-1 與 C1-3**；C1-2／C1-4／C1-5 無 DoD。Q3=A 原文要把 PBT／403／e2e **寫進 AC**；requirements DoD 則明定這些是「交付條件，不是系統行為驗收句」。草稿把 PBT／Playwright 放進 DoD、把 403 放進部分 AC——方向對，但落點不完整，且有反向錯誤（把靜態禁止寫成使用者 AC）。

判定基準：QA 能否寫出一支**實作做錯就會失敗**的測試（`unittest`＋Hypothesis、`TestClient`、Playwright，或標明人工／靜態檢查）。`TESTING.md` 禁止預期結果用「正常／成功」。

---

### 1. 第一段 vs 第二段無法獨立驗收

Q4=A 要求「第一段故事的 AC 不要求橫幅」。草稿 C1-1～C1-3 **確實沒有正向要求橫幅**，但有兩個對 QA 同等致命的缺口。

**缺口 A — 第一段 AC 不禁止第二段 UI。** C1-1～C1-3 沒有任何 Then 寫「不出現可編輯預算欄／『已超支』／進產品橫幅」。第一段建置若提前掛上橫幅或預算欄，C1-1～C1-3 仍全綠。第一段「可單獨上線」因此無法被 QA 簽字。

**缺口 B — 禁止句掛在第二段故事上，Given 在交付時為假。**

- AC-4.4 Given「僅第一段已上線」→ Then 不出現預算欄，並寫「本故事的 AC 在第二段交付時才全部可驗」
- AC-5.6 Given「僅第一段已上線」→ Then 不出現超支橫幅

C1-4／C1-5 **交付當下** Given 不成立，這兩條無法 pass/fail。第一段交付當下，這兩條又不屬於第一段故事，測試計畫沒有掛點。結果：兩個增量都驗不到「第一段不含第二段 UI」。

**缺口 C — 第一段 AC 反向洩漏第二段／C1-3 能力。**

- AC-1.5 And「只改 label 時同一 `id` 的時數**與覆寫**仍在」——覆寫是 C1-3。第一段只交 C1-1 時此 And 無法布置。
- AC-1.10 Then「含**已覆寫單價**的顯示值」——同上，C1-1 獨立驗收需要 C1-3 資料。

建議：把「無預算欄、無『已超支』、無橫幅」寫成 **C1-1 的負向 AC**（第一段 DoD 一併列 Playwright：受保護頁 `getByText('已超支')` 與橫幅 test-id **0 命中**）。AC-1.5／AC-1.10 的覆寫子句移到 C1-3（AC-3.8 已涵蓋重擷取不蓋覆寫；第二人可見覆寫值另開 C1-3 AC）。刪除或降級 AC-4.4／AC-5.6，避免第二段故事帶一個永遠驗不到的 Given。

---

### 2. 公式只有兩個例子，沒有具名 PBT 性質

AC-2.2 全文只重複 FR-3.2 的兩個數字例子：小時價 1 × 時數 24 → 720；月價 730／730、時數 24 → 720。這正是 ADR-0006／NFR-3／team-practices 禁止的形狀：**example-based 當唯一覆蓋**。

C1-3 DoD 寫「Hypothesis 覆蓋加總、公式、未定價排除、覆寫優先於 list price」——這是主題清單，**不是性質名稱**，且掛在 C1-3（覆寫故事），不掛在公式故事 C1-2。C1-2 無 DoD。第一段若先交 C1-1＋C1-2、C1-3 尚未開始，calculator 的 blocking PBT 沒有故事掛點。

另：AC-2.2 Then「浮點誤差在**設計指定**小數位內」——小數位尚未定（requirements 留給設計），**此刻無法 pass/fail**。

AC-1.7「總額等於已定價列小計之和」亦是單次觀察，未承接 FR-3.1「加入或移除一筆未定價列，總額不變」。

建議在 C1-2 DoD（及 C1-1 加總）具名下列性質，example 只當 smoke，不得當唯一覆蓋：

| 性質 ID | 陳述（對任意合法輸入成立） |
|---|---|
| `prop_hours_formula` | 小時價 `p`、每日時數 `h` ∈ 允許閉區間 → 小計 = `p * h * 30`（小數位由設計凍結後寫入容差） |
| `prop_monthly_sku_hourly` | 僅月價 `M` → 小時價 = `M / 730` |
| `prop_total_is_sum_of_priced` | 總額 = 所有已定價列小計之和 |
| `prop_unpriced_excluded` | 未定價列（含官方價失敗、覆寫前）不進入總額；增刪未定價列總額不變 |
| `prop_override_precedes_list` | 列有 Manual Override 時小計用覆寫路徑，不用 list price |

並補 **h=0、h=8、h=24** 三個邊界 example（0 與 8 目前零覆蓋）。`h` 上界是否允許 >24 必須在設計凍結前寫進 AC，否則 Hypothesis 的 domain 無法定。

---

### 3. 403 allow/deny 不雙向

team-practices Q3：第一個 C1 HTTP 端點「有權 2xx」與「無權 403」**缺一不可**；規則 A 要求角色能做到／其他角色做不到成對。

| 變更 | deny（403） | allow（2xx＋欄位集） |
|---|---|---|
| 讀取成本 | AC-1.1 Then 有；C1-1 DoD 有 | **僅 C1-1 DoD**；AC-1.1 無有權 2xx |
| 改時數 | AC-2.3 有 | **無**（C1-2 無 DoD；AC-2.5 只驗瀏覽器持久化，不驗 HTTP 欄位集） |
| 改估價區域 | AC-2.4 有 403 | And「Alex 設定成功後」——用了禁止詞，且不是 TestClient 欄位集 |
| 覆寫／指定 SKU | AC-3.5 有 | C1-3 DoD「有權 2xx 欄位集」有；AC 無 Alex／Hannah deny 以外的正向 HTTP |
| 改預算 | AC-4.2 有 403 **且** David／Hannah 讀回等於寫入 | 此條是全檔唯一接近 allow/deny 成對的 AC；C1-4 仍無 DoD 把 TestClient 變成交付條件 |

AC-1.1 還把兩個 When 疊在一條：When 是「檢視 Sidebar」，Then 卻要求「直接開成本路徑得到 403」。Sidebar 不可見 ≠ HTTP 403。須拆成 UI 隱藏 vs `GET` 成本路徑 403，並在 Then 寫出有權角色得到 2xx（或把 HTTP 對留在該故事 DoD，但 C1-2／C1-4 必須補上）。

---

### 4. Playwright 沒有寫「斷言什麼」

C1-1 DoD：「成本頁**或** Sidebar C 入口至少一個 case：可達且總額**或**空狀態可見」。

兩個「或」讓最小實作即可過：只加 Sidebar 連結、成本頁空白；或成本頁只有空狀態文案、從未渲染總額／列。這與 team-practices 規則 C（表頭出現、至少一列顯示值或既定佔位）以及「後端漏欄位 → 前端空白、六道閘門全綠」的失敗路徑相反。

建議 C1-1 至少一支 Playwright（規則 C 觸發條件：全新 Cost 頁）**同時**斷言：

- Sidebar：「架構」與「系統管理」之間有「成本」→「預估成本」（現況 `Sidebar.tsx` 大類標籤確為「系統管理」，AC-1.1 用詞正確，優於 FR-5.1 的 `Admin`）
- 有圖已選：出現總額數字（USD）、資源列表頭、至少一列資源名；未定價時字串「N 項尚未定價」的 N 等於列數
- 無圖：空狀態可見**且**總額數字不存在（不要「總額或空狀態」二選一）
- 無 C1 view：Sidebar 無「成本」組

C1-2 應斷言改時數後**該列小計與頁面總額數字變更**（前端唯一自動化層是 e2e）。C1-5 應斷言成本頁「已超支」文字，以及登入後受保護頁橫幅存在、無「永遠不要再顯示」；**C1-5 無 DoD，橫幅目前零自動化掛點。**

---

### 5. 無法被 QA pass/fail 的 AC

**AC-1.3** Then「不顯示捏造總額」——「捏造」不是觀察量。改為：無圖／未選圖時，總額數字節點不存在（或空狀態 test-id 存在且金額節點 0 命中）。

**AC-1.8** When「系統準備查官方價」、Then「不呼叫官方價」——不是使用者動作；Playwright 須 `page.route` 攔截官方價 URL 且斷言 0 次，AC 未寫。畫面「區域必填」可留作 UI AC；「不呼叫」屬 TestClient／網路攔截 DoD。

**AC-2.2** 小數位未定 → 見 §2。

**AC-2.4** Then「Alex 設定**成功**後」違反 `TESTING.md`。改為：Alex `PUT` 區域後回應 2xx，讀回 body 的區域碼等於請求值。

**AC-3.1** When「查價**成功**」；Then 只要求單價「大於 0」。硬編碼 `0.01` 即過，抓不到「與官方 list price 不一致」。When 改為可布置的前置（對照表唯一命中＋定價 stub 回已知 `p`）；Then 單價等於 `p` 且來源時間符合 ISO-8601 UTC。

**AC-3.3**「小計使用覆寫值與 C1-2 同一套時數公式」——覆寫是月費還是小時價未定，QA 算不出預期數字。必須寫死：覆寫值 `O`、時數 `h` 時小計的具體式（例如 `O` 即月費不再乘時數，或 `O/730 * h * 30`），否則性質 `prop_override_precedes_list` 也寫不出。

**AC-3.4** Then「成功則 AC-3.1，失敗則 AC-3.2」——一條 AC 兩個互斥結果，寫不出唯一預期。拆成兩條，或指定 stub：指定 SKU 後定價回 `p` → 走 AC-3.1 數字；stub 失敗 → 走 AC-3.2 文字。

**AC-3.6** Given「系統設定與程式」／Then 不出現 Cost Explorer 憑證路徑——這是 team-practices Forbidden／靜態檢查，不是使用者可觀察行為。應移出 AC、寫進 C1-3 DoD（`grep` 測試或 code review 清單）。**DoD 被寫成使用者 AC。**

**AC-3.7／AC-4.3** Then「可查出一筆紀錄」——未指定受測介面（HTTP？管理頁？log？）。`TESTING.md` 受測介面要比對 `openapi.json`／路由表；此刻 QA 無法執行。改為：呼叫稽核查詢端點（路徑於 OpenAPI 定案後填入）回 2xx，body 含操作者、時間、圖 id、舊值、新值；或標明「人工：查 DB 列」直到設計給介面。

**AC-4.1** When「判定超支」、Then「僅圖 A 超支」——超支標示是 C1-5。C1-4 獨立交付時沒有「已超支」可斷言。預算隔離應寫成：讀圖 A／圖 B 的預算欄位分別為 100／1000；超支 UI 留在 C1-5，用同一組 fixture。

**AC-5.5**「系統中無通知中心／未讀數／通知歷史」——全稱否定，與 AC-3.6 同型。可留人工／靜態；不要假裝是 e2e 可窮舉的 AC。

**NFR-1／NFR-2／NFR-4** 寫在 C1-1「涵蓋」，但 **0 條 AC**：對比 4.5:1、鍵盤可達、窄視窗捲動、50 列 5 秒。現行前端無 axe（team-practices 不採規則 D）。須：可自動化者寫進 AC／DoD（鍵盤 Tab 至圖下拉／時數；5 秒計時自已認證請求至總額節點），必然人工者標「人工」，不得用「涵蓋」冒充已可驗。

**FR-5.4**（頁首下拉切圖）在 C1-1 涵蓋 FR-5，但第一段無 AC；只出現在 AC-5.4 And。第一段多圖切換無法驗。

**AC-1.4** 只排除「連線與無文字裝飾」，未寫 `group`／`swimlane`／`container=1`（FR-1.1 可估價節點定義）。fixture 含 VPC 容器時，QA 與實作會對「列數」各算各的。

---

### 6. 尚可測、應保留的形狀

- AC-1.4 列名 = 去 HTML 後 label、列數 = 可估價節點數：fixture XML 可二元判定。
- AC-1.6 N = 未定價列數、小計不進總額：已知 fixture 可判定。
- AC-2.1 新列時數 24、無頁面級時數控件：頁面範圍內可斷言。
- AC-3.2 「官方價取得失敗」文字、與從未對到 SKU 可區分、不只靠顏色：可斷言文字節點。
- AC-5.1／AC-5.2：總額 > 預算有「已超支」；≤（含相等）沒有。相等邊界寫死，QA 可寫兩支。
- AC-5.3：關閉瀏覽器再登入仍見橫幅、無「永遠不要再顯示」——Playwright 可做；須補 DoD。
- AC-5.4 不鎖定排序、只要求預選**一張超支圖**：可斷言「預選 id ∈ 超支集合」，不必等 OQ 排序。這比 requirements FR-6.6「第一張」更可測。

---

### 7. INVEST Testable 與 DoD／AC 分工建議

C1-1～C1-3 因缺口 A/C **Testable 不成立**（第一段無法獨立簽字）。C1-4 Testable 被 AC-4.1／AC-4.4 拖垮。C1-5 缺 Playwright DoD。

建議分工（對齊 requirements DoD 原文，修正 Q3 把交付條件塞進使用者 AC 的字面）：

- **AC**：只寫使用者／API 可觀察行為（含 403 畫面與控件不可編輯）。
- **DoD**：Hypothesis 具名性質、每個新端點 TestClient 2xx 欄位集＋403、規則 C 的 Playwright **具體斷言清單**、schema／OpenAPI 同步。
- **靜態 Forbidden**（AC-3.6）：DoD 或 review 清單，不是 GWT。

C1-2／C1-4／C1-5 必須補 DoD，否則時數 403、預算 TestClient、橫幅 e2e 在 Construction 沒有故事級掛點。

## Positions

- AGREE: **C1-1～C1-3 沒有正向要求橫幅，Q4=A 的「第一段 AC 不要求橫幅」字面有做到。**
- AGREE: **AC-1.1 大類錨點用「系統管理」與現行 `Sidebar.tsx` 標籤一致**，比 FR-5.1 寫 `Admin` 更可拿去對 UI。
- AGREE: **PBT／Playwright 放在 DoD 而非獨立 QA 故事，符合 requirements DoD「交付條件 ≠ 系統行為驗收句」。**
- AGREE: **AC-5.1／AC-5.2 把相等當成未超支、超支要文字不只靠顏色，QA 可寫成兩支互斥案例。**
- AGREE: **AC-5.4 改為預選「一張超支圖」而非未定義的「第一張」，使「預選 id ∈ 超支集合」可判定。**
- AGREE: **AC-3.2 官方價失敗與從未對到 SKU 用不同文字區分，給得出不只靠顏色的斷言。**
- AGREE: **personas 與故事的 403 職責切齊**（Alex 時數／區域、David 覆寫、David／Hannah 預算），三角色沒有寫成同一人可做全部變更。

- OBJECT: **第一段無法獨立驗收：C1-1～C1-3 不禁止預算欄／『已超支』／橫幅；禁止句 AC-4.4／AC-5.6 的 Given 在第二段交付時為假，QA 兩邊都 pass/fail 不了。** 把負向斷言移到 C1-1 AC＋Playwright 0 命中；刪或降級 AC-4.4／AC-5.6。
- OBJECT: **AC-1.5／AC-1.10 把 C1-3 覆寫洩進第一段 AC，C1-1 單獨上線時無法布置。** 覆寫子句移到 C1-3。
- OBJECT: **AC-2.2 只用 FR-3.2 兩個數字例子當公式覆蓋，且小數位未定、無法 pass/fail；具名 PBT 只以主題清單出現在 C1-3 DoD，C1-2 無 DoD。** 違反 ADR-0006／NFR-3。補 `prop_hours_formula` 等性質（§2）與 h=0／8／24 邊界。
- OBJECT: **403 多數只有 deny。** 改時數／區域無有權 2xx＋欄位集；讀取 allow 只在 DoD；C1-2／C1-4 無 DoD。違反 team-practices Q3 allow/deny 成對。
- OBJECT: **C1-1 Playwright DoD 兩個「或」會讓空白成本頁過關，未規定表頭／列值／USD／『N 項尚未定價』。** C1-2 小計重算與 C1-5 橫幅零 e2e 掛點。違反規則 C。
- OBJECT: **AC-3.6 把 Forbidden 靜態檢查寫成使用者 GWT（DoD 被寫成 AC）。** 移出驗收標準。
- OBJECT: **AC-3.1 When 使用「成功」，且 Then「單價 > 0」對硬編碼正數恆真；AC-2.4「設定成功」同樣違反 `TESTING.md`。**
- OBJECT: **AC-3.3 覆寫×時數公式未寫死算式，QA 算不出預期小計；AC-3.4 一條兩結果，寫不出唯一預期。**
- OBJECT: **AC-1.3「捏造總額」、AC-1.8「不呼叫官方價」、AC-3.7／AC-4.3「可查出」皆無可執行觀察面或受測介面。**
- OBJECT: **AC-4.1 用超支判定驗預算隔離，C1-4 不能獨立於 C1-5 驗收。**
- OBJECT: **C1-1 宣稱涵蓋 NFR-1／2／4 與 FR-5，但無對比／鍵盤／5 秒／頁首切圖 AC；AC-1.4 漏 `group`／`swimlane`／`container=1`，列數會與 FR-1.1 打架。**
