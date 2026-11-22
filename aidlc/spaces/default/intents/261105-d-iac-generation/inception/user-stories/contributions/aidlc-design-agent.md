**Collaborator:** aidlc-design-agent

## Contribution

視角：persona 保真、UX 流程對齊 rough-mockups、空／錯誤態、WCAG 2.1 AA、US1.3 切圖清空、自由檢視 vs 執行閘。盲審 Round 1；未讀 sibling contributions；未改 lead artifacts。

### 0. 對照基準（已核對）

| # | 基準 | 來源 |
|---|---|---|
| V-1 | 切法＝工作流程；Alex 主路徑；Elena／Fiona 各 ≥1 Must；R-01＝執行 D3 需 D2 成功；切圖＝清空 | `user-stories-questions.md` Q1–Q5＝A |
| V-2 | Screen 1 入口；Screen 2 草稿為主＋步驟 nav＋aside 脈絡／Agent 狀態／下載複製；Screen 3 findings 文字嚴重度；Screen 4 Secrets 警告、無 apply | `wireframes.md` |
| V-3 | Happy path：進工作區→選圖→D1→檢視／下載→D2→D3→帶走；無圖阻擋；D1 失敗＋重試；權限不足 | `user-flow.md`（線框同目錄，流程對照用） |
| V-4 | 自由**檢視**步驟；執行 D2／D3／下載需 D1 成功草稿；Advisory 不擋進 Secrets UI | `requirements.md` FR6.1–FR6.2、FR3.2 |
| V-5 | NFR5：步驟／findings／下載可鍵盤；嚴重度不單靠顏色 | `requirements.md` NFR5 |
| V-6 | 現況入口仍為 Coming Soon stub（`showComingSoon('IaC 代碼生成')`），矩陣種子領先實作 | `WorkspacePage.tsx`；`RolePermissionsPage` D1／D2 欄名 |

### 1. Persona 保真

| Persona | 故事主角落點 | 判定 |
|---|---|---|
| Alex | US1.1–1.2、US2.*、US4.*、US5.1、US6.2 | 符合 Q5=A 主路徑；選圖→D1→閘門→下載完整 |
| Elena | **僅** US1.3（切圖清空） | 滿足「≥1 Must」字面；但其核心目標「多檔模組樹＋可下載＋掃描可讀」沒有她為主角的 Must——模組樹在 US2.1（Alex）、掃描在 US3.*（Fiona） |
| Fiona | US3.1–3.2、US5.2、US6.1 | 掃描可見性、改寫後下載、授權雙向——對齊痛點；US6.1 偏系統品質仍合理掛安全利害 |

「不做」邊界（代 apply、寫入雲端 SM）有 AC5.1.1／FR4.3 承接，persona 與故事一致。

### 2. UX 流程 × 線框 × 故事

| 線框／流程節點 | 故事落點 | 判定 |
|---|---|---|
| Screen 1「生成 IaC」可點 | AC1.1.1／1.1.2 | 覆蓋（有權進、無權 hide／disabled＋說明） |
| 自動帶入活躍圖／改選／上傳 | AC1.2.1–1.2.3 | 覆蓋；補上線框當時未釘死的選圖模型（對齊 FR1.2–1.4） |
| 無圖阻擋＋回 Workspace CTA | AC1.2.4 | 覆蓋 user-flow「無可用架構圖」 |
| Screen 2 草稿主區＋檔案樹＋HCL | AC2.1.1 | 覆蓋 |
| aside Agent 狀態／產生中進度 | **無 AC** | 線框與 user-flow「顯示進度」未進故事；僅有失敗態 US2.3 |
| footer「執行 D1」vs「下一步：掃描」 | 由 FR6.1／US4.2 自由檢視政策間接消歧 | 半覆蓋：可開步驟畫面已定；「下一步」是否＝純導覽未寫進 AC |
| Screen 3 findings 文字嚴重度 | AC3.1.1、AC3.2.2 | 覆蓋「不單靠顏色」 |
| Advisory 仍可進 Secrets UI | AC3.2.1 | 覆蓋 FR3.2 |
| 執行 D2 需 D1 草稿 | AC3.1.2 | 覆蓋執行閘 |
| 掃描步驟**無草稿時的空狀態畫面** | **無對等 US** | 見 OBJECT-1（僅 Secrets 有 US4.2） |
| 執行 D3 需 D2 成功 | AC4.1.1–4.1.2 | 覆蓋 R-01；優於線框 Screen 4（當時未畫執行閘） |
| 自由打開 Secrets、執行仍 disabled | AC4.2.1 | 覆蓋 FR6.1 在 D3 的落點 |
| 下載／複製／無 apply | AC5.1.1–5.1.3 | 覆蓋 Screen 2 aside＋Non-goals |
| HIGH／CRITICAL 下載前摘要 | AC5.1.4 | 覆蓋 FR3.3；摘要 dialog 的焦點／鍵盤未進 AC |
| 切圖清空產物＋提示 | AC1.3.1 | 覆蓋 Q4=A／R-02；提示的 a11y 未釘 |
| D1 失敗＋重試、不整段清空 | AC2.3.1 | 覆蓋 |
| D2／D3 失敗＋重試 | **無專屬 AC** | FR7.3 要求三者；故事只寫 D1（US2.3） |
| 上傳失敗脈絡不變 | US7.2 Should | 可接受（Q2 標準粒度）；非本輪擋項 |

整體：工作流程切法與 Screen 1→4 順序一致；自由檢視 vs 執行閘在 **Secrets／D3** 寫清楚，是本輪對線框最大的設計加值。缺口集中在「載入中」、D2 空狀態對稱、D2／D3 錯誤態、鍵盤 AC。

### 3. 空／錯誤／部分態盤點

| 態 | 故事覆蓋 | 缺口 |
|---|---|---|
| 空：無圖 | AC1.2.4 | — |
| 空：無 D1 草稿仍開 Secrets | AC4.2.1 | — |
| 空：無 D1 草稿仍開**掃描**步驟 | 僅 AC3.1.2（執行 disabled） | 未要求可見空狀態／說明文案（對齊 FR6.1） |
| 空：D3「無可改寫項」 | AC4.1.2 | — |
| 空：D2「無 finding」 | AC3.1.1 | — |
| 載入：D1／D2／D3 進行中 | 無 | 線框 Agent 狀態、user-flow 進度 |
| 錯誤：D1 | AC2.3.1 | — |
| 錯誤：D2／D3 | 無 GWT | FR7.3 |
| 部分：切圖後回「無草稿」disabled | AC1.3.1 | — |
| 部分：有 HIGH／CRITICAL 仍可進 Secrets | AC3.2.1–3.2.2 | — |
| 權限不足入口 | AC1.1.2 | — |

### 4. 無障礙（對 NFR5／線框 a11y 註記）

已有：AC3.2.2 嚴重度「不單靠顏色」——對齊 Screen 3 a11y 與 NFR5 後半。

未落到 GWT 的 NFR5／線框註記：

- 步驟按鈕、findings 列、下載／複製／執行控制的**鍵盤可達與可見焦點**
- 切圖提示、D1／D2／D3 錯誤、下載前摘要確認是否以文字＋非僅色票，且動態變更可被輔助技術得知（`status`／`alert`／`aria-live` 級——細節可留 refined-mockups，但故事層至少要有一條可失敗的鍵盤／宣告 AC）
- Screen 4「警告用 status／alert 語意」無對應 AC

### 5. US1.3 切圖清空（焦點評）

AC1.3.1 一次釘死：清空當次 D1／D2／D3 產物、顯示提示、下載／執行 D2／D3 回「無草稿」disabled 直到新 D1 成功。對 Elena 痛點與 Q4=A 清楚可測。

建議 lead 在折入時補兩點（非改寫清空政策）：

1. 提示須為可感知文字（不只 toast 色塊），且切圖當下輔助技術能得知「產物已清空」。
2. 若切圖當下有進行中的 D1／D2／D3 請求，故事或 OQ 應寫「取消／作廢進行中工作」或「完成後丟棄」——否則 refined-mockups 會在競態上猜。

### 6. 自由檢視 vs 執行閘（焦點評）

| 閘 | 故事 | 評 |
|---|---|---|
| 檢視 Secrets ≠ 執行 D3 | US4.2 + US4.1 | **清楚**；關閉 R-01 |
| 執行 D2 需 D1 | AC3.1.2 | **清楚** |
| 下載需 D1；HIGH／CRITICAL 需摘要 | AC5.1.3–5.1.4 | **清楚** |
| 檢視掃描步驟 ≠ 執行 D2（無草稿空態） | 缺與 US4.2 對稱的 Must／AC | **不對稱**——實作者可能做成「無草稿就不能點進掃描步驟」，違反 FR6.1 |
| Advisory：有 HIGH／CRITICAL 仍可進 Secrets **畫面** | AC3.2.1 | **清楚**；與「執行 D3 仍要 D2 成功報告」不衝突 |

### 7. 建議補 AC（供 lead 折入，本檔不改 stories）

**US3.x 或擴 AC3.1.x — 掃描步驟自由檢視空態（對齊 US4.2）**

- Given 無 D1 成功草稿，When 我切到掃描步驟，Then 畫面可開並顯示空狀態／說明，執行掃描控制項 disabled＋說明（不可進入成功 loading）。

**US2.x / US3 / US4 — 進行中態**

- Given 我已觸發 D1（或 D2／D3），When 請求尚未結束，Then 該步驟顯示進行中狀態（對齊 Workspace agent 語彙），執行按鈕不可重複送出成功態。

**US3.x / US4.x — 失敗重試（承接 FR7.3）**

- Given D2（或 D3）失敗，When 我看該步驟，Then 有錯誤訊息與重試；已存在的 D1 草稿（及 D2 成功報告，若 D3 失敗）仍可檢視，不整段清空工作階段。

**NFR5 落地 AC（可掛 US1.1 或 US6）**

- Given 有權使用者只使用鍵盤，When 操作步驟切換、執行／disabled 控制、findings 列、下載與複製，Then 每一項可聚焦並啟動（disabled 者可聚焦或具名說明且不可啟動）；焦點可見；嚴重度與切圖提示不單靠顏色。

**US1.3 補則（可選 And）**

- And 清空提示為可見文字；And 進行中之生成／掃描／改寫不得在切圖後仍把舊圖產物寫回目前工作區（取消或丟棄策略於設計釘死前，AC 至少禁止「舊圖產物殘留為可下載草稿」）。

## Positions

- AGREE: Q1=A 工作流程切法與線框 Screen 1→4／user-flow Happy Path 一致；Q5=A Alex 主路徑＋Elena／Fiona 各 ≥1 Must 字面成立。
- AGREE: US4.1＋US4.2 把「自由檢視 Secrets」與「執行 D3 需 D2 成功報告」拆開，正確關閉 R-01，並補上線框 Screen 4 未畫的執行閘——這是本輪對互動模型最大的澄清。
- AGREE: US1.3／AC1.3.1 切圖清空政策清楚可測（產物清空＋提示＋下載／D2／D3 回無草稿 disabled），對齊 Q4=A 與 Elena 痛點。
- AGREE: AC1.2.4 無圖阻擋、AC2.3.1 D1 失敗重試、AC3.2.1–3.2.2 Advisory＋嚴重度不單靠顏色、AC5.1.1 無 apply、AC5.1.4 下載前 HIGH／CRITICAL 摘要——空／風險／邊界態多數有落點。
- AGREE: 選圖模型（活躍圖／改選／上傳）寫進 US1.2，消除 rough-mockups 審查時「aside 脈絡已選、互動未畫」的歧義。

- OBJECT: **FR6.1 自由檢視在掃描步驟未對稱落地。** Secrets 有 US4.2／AC4.2.1；掃描僅有「執行 disabled」（AC3.1.2）。實作可合法做成「無草稿不可進入掃描步驟 UI」，直接違反 FR6.1 與線框步驟 nav 可點模型。須補與 US4.2 同形的 Must／AC。
- OBJECT: **NFR5（步驟／findings／下載鍵盤可達、焦點可見）只有需求列、沒有故事 GWT。** AC3.2.2 只覆蓋「不單靠顏色」。涵蓋欄若掛 NFR5 而無失敗面，refined-mockups／e2e 無法從故事驗收 WCAG 操作面。
- OBJECT: **載入／進行中態缺失。** 線框 Screen 2「Agent 狀態」與 user-flow「顯示進度」無任何 AC；只有失敗 US2.3。缺少進行中 AC 會讓重複提交、焦點陷阱、狀態可見性在設計細化時無上游錨點。
- OBJECT: **FR7.3 的 D2／D3 失敗＋重試未進故事 AC**（僅 US2.3 覆蓋 D1）。錯誤態不完整；與「設計最壞情境」原則不符，且與 Q2「每 Must 步驟含錯誤／空狀態」不完全一致。
- OBJECT（較輕／persona）: **Elena 僅掛 US1.3，其核心目標「模組樹品質」無她為主角的 Must。** 不違反 Q5 字面，但 persona 保真偏薄——建議至少讓 US2.1 的 As a 改為 Elena，或加一則 Elena 檢視模組樹／變數輸出的短 Must，避免下游把模組形狀只當成 Alex 附帶。
