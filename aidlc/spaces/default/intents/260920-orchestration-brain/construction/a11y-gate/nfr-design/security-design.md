# Security Design — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: nfr-design（Construction 3.3）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 範圍與上游

本站把 `nfr-requirements` 的需求落成**掃描 spec 的結構設計**。上游有兩份，讀法依更正附錄的規則：

- `../nfr-requirements/security-requirements.md`（`A11Y-S1`–`A11Y-S10`，已凍結）
- `../nfr-requirements/security-requirements-corrections.md`（`C-01`–`C-08`，**衝突時以它為準**）

依 `produces_kinds`，`performance-design`／`scalability-design`／`reliability-design`／`observability-design`／`logical-components` 不適用於 `packaging`，本單元只產出本檔與 `traceability.json`。

本站**不提問**：每一個設計決定都已由上游定案（`[DM:D6]`=A、`[A11Y-Q1]`=A、更正附錄的處置經使用者選擇），剩下的是把它們排成一個可實作的結構。決定若在實作時發現不可行，由 `code-generation` 在計畫中揭露，不回到本站。

## 一、結構總覽

```
frontend/tests/e2e/
  a11y.spec.ts          ← 21 個 test()：18 個掃描點 ＋ 1 個手機寬度檢查 ＋ 2 個基準清單檢查
  a11y-baseline.json    ← 頁殼既存違規基準（A11Y-S9 ＋ C-03）
```

`a11y.spec.ts` 內部分四層，每一層只做一件事：

| 層 | 職責 | 承接需求 |
|---|---|---|
| **隔離層** `isolate(page)` | 註冊兜底偵測器、接管兩條 WebSocket、記錄所有 WebSocket URL | `A11Y-S5` ＋ `C-01` |
| **狀態層** `stage<掃描點>(page)` | 以具體端點 handler 造出該掃描點的資料狀態並導航 | `A11Y-S10` ＋ `C-04`／`C-07` |
| **就緒層** `ready(page, spec)` | 斷言就緒 test-id 可見、排除 test-id 為 0 | `A11Y-S7` ＋ `C-02` |
| **掃描層** `scan(page, testInfo, opts)` | 跑 axe、套用基準、附報告、斷言無新違規 | `A11Y-S8`／`A11Y-S9` ＋ `C-03` |

每個 `test()` 依序呼叫四層，最後斷言隔離層的偵測記錄為空。四層分開是為了讓突變驗證能逐層打：拿掉任一層的一條斷言，都要有對應的突變讓它紅。

## 二、隔離層（`A11Y-S5`／`C-01`）

**順序是設計的一部分**：Playwright 以**後註冊者優先**比對 route，所以兜底必須**最先**註冊、具體 handler 在狀態層**之後**註冊。

```ts
// 示意，非實作
const leaked: string[] = [];
await page.route('**/api/**', (r) => { leaked.push(r.request().url()); return r.abort(); });
await page.routeWebSocket(/\/api\/brain\/ws(\?.*)?$/, () => {});
await page.routeWebSocket('**/api/collab/ws/**', () => {});
const sockets: string[] = [];
page.on('websocket', (ws) => sockets.push(ws.url()));
// test() 結尾：expect(leaked).toEqual([]); 每個 sockets 項目都符合兩個樣式之一
```

- 兜底**用 `abort()` 而不是回 `200 []`**：既有 spec 的兜底回看起來正常的值（`entry-page.spec.ts:200`），那是功能測試的合理選擇，但對「不得漏接」的閘門而言，一個看起來正常的回應等於掩護。
- `/api/brain/ws` 的接管 handler 是**空的**（不回任何訊息）：掃描點 1 只需要入口頁的靜態結構可被掃描。若 `code-generation` 發現入口頁在握手未完成時不渲染 `brain-entry-page`，改為送出最小的 `ready` 訊息，形狀沿用 `entry-page.spec.ts` 既有的 fixture，並記入 `code-summary.md`。

## 三、狀態層（`A11Y-S10`／`C-04`／`C-07`）

18 個掃描點的清單以更正附錄 `C-02` 的表為準（第 1–17 列）加上 `C-07` 的非入口頁橫幅（第 18 個）。資料形狀的來源：

- **優先借用既有 spec 的 fixture 形狀**（`entry-page.spec.ts`、`memory-page.spec.ts`、`project-pages.spec.ts`、`member-pages.spec.ts`），以複製最小資料到 `a11y.spec.ts` 的方式借用，**不抽共用模組**。理由：抽共用模組會改到四支已交付單元的 spec，屬重開已交付單元；複製的代價是資料形狀可能隨原 spec 漂移，而那種漂移的後果是就緒斷言失敗（大聲），不是靜默放行。
- 每個掃描點只註冊它用得到的端點；用不到的請求落進兜底、被記錄、讓測試紅——這正是隔離層要的行為，也逼使狀態層把「這個畫面到底打了哪些 API」寫清楚。

**第 18 個掃描點（非入口頁的橫幅，`C-07`）**：攔截的 `/me` 不帶 `C1 view`，讓 `DefaultRedirect` 落在非入口頁；該落地頁本身是本 intent 不管的既有頁，所以這一個掃描以 `AxeBuilder.include('[data-testid="reselection-banner-host"]')` 限縮。落地頁會打它自己的 API，這些 API 同樣要在狀態層註冊，否則被隔離層擋下。若某個落地頁的 API 面太大而不實際，`code-generation` 可改選一個 API 面最小的落地頁，並在 `code-summary.md` 記下選了哪一個與理由。

## 四、就緒層（`A11Y-S7`／`C-02`）

每個掃描點帶一份規格：`{ ready: string[], absent: string[] }`，值為 `C-02` 表中的 test-id（或文字定位器，如「載入中…」）。

```ts
// 示意
for (const id of spec.ready)  await expect(page.getByTestId(id)).toBeVisible();
for (const id of spec.absent) await expect(page.getByTestId(id)).toHaveCount(0);
```

- **不使用任何 axe 結果欄位當作「有掃到」的證據**（`C-02` 刪除了 `passes.length > 0`）。
- 「視角正確」的證據寫在 `absent` 裡，而不是 `ready` 裡——例如 member-view 的證據是 `member-list-invite-button` **不存在**。admin-view 掃成 member-view 時，就緒層會紅。

## 五、掃描層（`A11Y-S8`／`A11Y-S9`／`C-03`）

```ts
// 示意
const results = await new AxeBuilder({ page })
  .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
  .include(opts.include ?? 'body')
  .analyze();
const fresh = results.violations.flatMap(toEntries).filter((e) => !baseline.has(key(e)));
await testInfo.attach('axe', { body: JSON.stringify({ violations: results.violations, incomplete: results.incomplete }), contentType: 'application/json' });
expect(fresh).toEqual([]);
```

**基準的四＋一條規則落在哪裡**：

| 規則 | 落點 |
|---|---|
| 1. 只收頁殼既有節點 | 一個獨立的 `test('基準清單不得收新元件節點')`：載入 `a11y-baseline.json`，對每筆的選擇器檢查不落在 `C-03` 列舉的根節點清單內（以選擇器字串比對根節點的 test-id 與 `Sidebar` 三個新 `<nav>` 的 `aria-label`）。**這一個 test 不開瀏覽器頁面**，只做檔案層的比對 |
| 2. 過期條目讓測試失敗 | 每個掃描 `test()` 把它實際看到的「規則 id ＋ 穩定選擇器」**寫成磁碟上的一個檔**（每個掃描點一檔，位於 `testInfo.project.outputDir` 下的固定子目錄，同名覆寫——所以重試後留下的是最後一次嘗試）；檔案最末一個 `test('基準清單沒有過期條目')` 讀回全部 18 個檔，**所有掃描點都沒出現**的條目列為過期並讓測試失敗；檔案數不足 18 時直接失敗（表示有掃描點沒跑完，過期判定無效） |
| 3. 不得擴大 | 由審查把關（`A11Y-S9` 規則 3 原文），本站無機械設計 |
| 4. 每筆附說明 | `a11y-baseline.json` 每筆必填 `reason` 欄；規則 1 的那個 test 一併檢查非空 |
| 5. 交界類規則不得進基準 | 規則 1 的 test 一併檢查每筆的規則 id 不在 `C-03` 規則 5 的清單內 |

**穩定選擇器的取得**：axe 回報的 `target` 可能是 `nth-child` 型。掃描層把每個違規節點**重新定位**為穩定選擇器（依序嘗試 `id`、`data-testid`、`aria-label`、role ＋ 可及名稱）；四者都取不到的節點**不得進基準**，只能修掉或停下來回報。這一條讓 `C-03` 的「不得使用 `nth-child`」可以被機械執行，而不是只靠撰寫者自律。

**為什麼不用記憶體集合加 `afterAll`**（寫設計時自查改掉的第一版）：`playwright.config.ts:14,17-18` 為 `fullyParallel: false`、CI 下 `retries: 1`、`workers: 1`。Playwright 在 test 失敗後會**丟棄該 worker、另起新 worker** 重試並跑完剩下的 test，worker 範圍的記憶體集合因此只剩後半段的結果；若重試通過，`afterAll` 會把前半段掃描點看到的條目全部誤判為過期——一個 flaky 的掃描點就會讓整個閘門紅。寫檔讓結果跨 worker 存活，且同名覆寫自然得到「最後一次嘗試」的語意。過期檢查的 test 須在檔案最末，且依賴 `fullyParallel: false` 的檔內順序；`code-generation` 若改動該設定，須同步改這個機制。

## 六、手機寬度檢查（`C-06`）

獨立的第 19 個 `test()`：`page.setViewportSize({ width: 375, height: 812 })`，走與掃描點 1 相同的隔離層與狀態層，就緒後斷言 `document.documentElement.scrollWidth <= document.documentElement.clientWidth`。不跑 axe。

## 七、供應鏈與附件（`A11Y-S1`–`A11Y-S4`、`A11Y-S6`）

這幾條是交付與審查時的檢查，不是 spec 的結構：

- `A11Y-S1`：`code-generation` 的完成條件加一條 `grep -rn "axe-core" frontend/src` 為 0、`dist/` 內 `axe` 為 0。
- `A11Y-S2`／`A11Y-S3`／`A11Y-S4`：`code-generation` 在 `code-summary.md` 記下版本、發布日期、peer 範圍、`npm audit` 新套件樹的結果、授權（`tech-stack-decisions.md` T-1 交辦）。
- `A11Y-S6`：附件只放 `violations` 與 `incomplete`（見第五節的示意），token 一律用既有 spec 的假值。

## 八、突變驗證清單（交 `code-generation` 實跑）

| # | 突變 | 必須紅在 |
|---|---|---|
| M1 | 拿掉某掃描點的一個具體端點 handler | 隔離層（`leaked` 非空） |
| M2 | 拿掉 `/api/brain/ws` 的 `routeWebSocket` | 隔離層（WebSocket URL 不符樣式），且**不得**連到真實閘道 |
| M3 | 攔截的 `/me` 改為無權限（導向 `/403`） | 就緒層 |
| M4 | member-view 的 `/me` 改為 admin 權限 | 就緒層（`member-list-invite-button` 出現） |
| M5 | 在新元件內加一個無 `alt` 的 `<img>` 或無 label 的 `<input>` | 掃描層（新違規） |
| M6 | 把一筆新元件節點的違規加進基準 | 規則 1 的 test |
| M7 | 在基準裡加一筆實際不存在的違規 | 規則 2 的過期檢查 test |
| M10 | 讓某一個掃描點第一次嘗試失敗、重試通過（例如以環境變數注入一次性延遲） | **不得**讓過期檢查誤紅——這是第五節改用寫檔的理由，必須實證 |
| M8 | 在基準裡加一筆 `duplicate-id-aria` 的條目 | 規則 5（規則 1 的 test） |
| M9 | 讓入口頁在 375px 寬度下溢出 | 手機寬度 test |

## 八之一、與 `contract-summary.md` 的對照（契約端另一側的現況）

本單元的四個掃描對象由 `contract-summary.md` 的 `K-13`／`K-14`／`K-19`／`K-20` 定義為 `U17` 的 `test-target`。對照已交付的程式，有一處契約字面與實作不一致，記在此處讓 `code-generation` 不會照契約字面去找元素：

- `K-19`（`contract-summary.md:1986`）與 `K-20`（`:2023`）寫 `data_testid_prefix: "brain-*"`，`K-13` 的 `provides_to_U17.testids` 也寫「`brain-*` 前綴」。實讀 `frontend/src`（2026-10-17）：入口頁確實是 `brain-entry-page`，但 `U23`／`U24`／`U15` 的頁面用的是 `projects-list-page`、`project-*`、`members-list-page`、`member-*`、`invite-dialog`、`reselection-banner-*`、`memory-page` 等**不帶 `brain-` 前綴**的 id。
- 本站的就緒規格（第四節，沿用 `C-02` 表）**以實際程式的 id 為準**，不以契約字面為準——照契約字面寫 `brain-*` 的選擇器，就緒層會在每個非入口頁的掃描點都紅。
- 這是 `U23`／`U24`／`U15` 交付時與契約的落差，不是本單元能修的；本單元只是第一個照契約去消費這些 id 的單元，所以由這裡回報。承接：`build-and-test`（跨單元一致性檢查）或下一次碰到 `contract-summary.md` 的修訂。

## 八之二、其他單元指派給本單元的兩個開放項（`nfr-requirements` 漏收，本站補收）

寫本站時以 `a11y-gate`／`U17` 掃全部 construction 產出，查出兩項由其他單元明文指派給本單元、而 `nfr-requirements` 沒有收進來的事項：

| 開放項 | 出處 | 內容 | 本站處置 |
|---|---|---|---|
| **`OPEN-ND24-1`** | `member-pages-ui/nfr-design/logical-components.md:131-137`；`memory-page-ui/functional-design/frontend-components.md:205-207` 為同形殘留 | 成員頁與記憶頁掛載時，文件中同時有**兩個** `role="status"`（`Layout` 的橫幅宿主 ＋ 該頁的 `<LiveRegion />`），兩者同時變動時的播報順序未定義 | **axe 判不到**——它只檢查 role 是否合法，不檢查兩個 live region 的播報先後。本單元不自行訂一個順序規則（同 `U24` 的理由：沒有上游需求支持的規則不會被任何工具檢查）。處置為**列入 `build-and-test` 的人工驗證**：以螢幕閱讀器在成員頁同時觸發「待確認的改選橫幅」與「載入完成播報」，記錄兩筆是否都被朗讀、先後為何、是否有一筆被吞掉。若有一筆被吞掉，那是 `U24`／`U15` 的缺陷，回報給它們；本單元的自動化範圍不擴大 |
| **`OPEN-MP15-4`** | `memory-page-ui/functional-design/functional-spec.md:315` | 記憶頁的 test id 片段（`procedural`）與 API 值（`procedure`）不一致，以顯式映射處理；「若 `U17` 的掃描需要 test id 清單，以 `frontend-components.md §九` 的映射表為準」 | 掃描點 2 的就緒規格寫「至少一個 `memory-zone-*`」，不依賴具體片段，所以不受影響。`code-generation` 若要指定某一區，以該映射表為準，不得以 API 值拼 test id |

**為什麼前一站漏收**：`nfr-requirements` 只讀了 stage 宣告的 consumes（`requirements.md`、`contract-summary.md`、codekb），而這兩項寫在**其他單元的 construction 產出**裡，不在任何 consumes 清單上。可執行補強已寫入 stage 日記：每個單元開工時，先以單元名與單元編號各 grep 一次全部 construction 產出，找出別人指派過來的事項。

## 九、ADR-0006 與 PBT

四面向的判定沿用 `security-requirements.md`「ADR-0006 四面向逐項判定」，本站不重判；本站的設計只是把那張表最右欄的三個「變形」落到具體結構——IAM 變形落在就緒層的 `absent`、Network exposure 變形落在隔離層、Audit logging 變形落在掃描層的附件。PBT 維持不適用（固定狀態集合）。

## 十、需求 ID 與追溯 sensor

上游沒有 `NFRx.y`（`security-requirements.md` 交接 H-4），所以本站的 `traceability.json` 以 `A11Y-S1`–`A11Y-S10` 與 `C-01`–`C-08` 為上游 id。traceability sensor 只認 `NFR\d+\.\d+`，會回報「no NFRx.y IDs」——**這是預期中的結果，不是本站漏寫**，處置是如實保留，不補假父 ID（同 `rbac-story-ids` 的 nfr-design 現況）。
