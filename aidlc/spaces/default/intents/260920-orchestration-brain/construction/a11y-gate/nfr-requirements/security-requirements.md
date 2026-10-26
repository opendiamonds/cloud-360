# Security Requirements — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: nfr-requirements（Construction 3.2）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 本單元是什麼、不是什麼

`U17` 交付兩樣東西：一個 devDependency（`@axe-core/playwright`），以及一支跑在既有 Playwright 層、對本 intent 新增的四類頁面做 14 次無障礙掃描的 spec（12 次來自無障礙清單、2 次來自契約，見 `A11Y-S10`）。掃到違規就讓 `ui-regression` 變紅（`accessibility-checklist.md`「驗證機制」節，`[DM:D6]`=A）。

它**不是**執行期程式碼：不進 `frontend/src` 的產品 bundle，不新增 HTTP 端點、WebSocket 訊息、資料表、環境變數或 compose 服務。所以本單元的安全面只剩兩塊：**供應鏈**（一個新的 npm 套件樹）與**閘門本身的可信度**（它會不會在該紅的時候綠）。後者寫在安全需求裡，因為一道會靜默放行的閘門，等於讓「已通過無障礙掃描」變成一個沒有證據的主張。

依 stage 檔的 `produces_kinds`，`performance-requirements`／`scalability-requirements`／`reliability-requirements`／`observability-requirements` 只適用於 `service`／`ui`，本單元不產出。

## 需求 ID 的來源（先講明，否則追溯會失真）

stage 檔要求每條細項需求承接一個 inception `NFR{n}` 再加子編號。**本單元找不到誠實的上游 NFR**：

- `requirements.md` 的 `NFR1`–`NFR11` 沒有任何一條談無障礙（全文 `axe`／`WCAG`／`無障礙` 命中數為 0，2026-10-17 實查）。
- 無障礙的上游是 `[R7]`（WCAG 2.1 AA），它只以 `AC-A11Y.1`／`AC-A11Y.2` 兩條驗收條件存在於 `stories.md:652-653`，掃描閘門本身則由 `refined-mockups` 的 `[DM:D6]`=A 定案。
- 把本單元的需求掛在 `NFR5`（WebSocket 契約閘門）或 `NFR9`（成本原則）底下，只因為它們也是「CI 檢查」或「省」，會讓下游以為那兩條 NFR 涵蓋了無障礙。

因此本單元的細項需求一律使用**單元內編號 `A11Y-S<n>`**，inception 的 11 條 NFR 在 `traceability.json` 逐條標 `N/A` 並附理由。**已知後果**：下一站 `nfr-design` 的 traceability sensor 會回報「no NFRx.y IDs」，因為它只認 `NFR\d+\.\d+`。這不是本站漏寫，是上游缺少無障礙 NFR 的直接結果；`nfr-design` 屆時須如實處置，不得為了讓 sensor 過關而補一個假的父 ID。

## 細項需求

| ID | 需求 | 可驗證條件 | 它要防的失敗 |
|---|---|---|---|
| **A11Y-S1** | `@axe-core/playwright` 只能出現在 `devDependencies`，且不得被 `frontend/src/` 任何檔案 import | `frontend/package.json` 的 `dependencies` 不含它；`grep -rn "axe-core" frontend/src` 命中 0；`npm run build` 產出的 `dist/` 內 `axe` 字串命中 0 | 測試工具被打包進產品，對所有使用者多送一份整套 axe 規則引擎，且擴大產品的供應鏈曝險面 |
| **A11Y-S2** | 新套件以 `npm install --save-dev` 加入，`package-lock.json` 同一個 commit 更新並帶 `integrity` 雜湊；CI 一律 `npm ci` | `package-lock.json` 內 `node_modules/@axe-core/playwright` 與 `node_modules/axe-core` 兩個條目都有 `integrity` 欄；`git diff` 顯示 `package.json` 與 `package-lock.json` 同時變更 | lockfile 未更新時，CI 各次執行解析到不同版本，而 `npm ci` 會因兩檔不一致直接失敗——後者是好的失敗，前者是無聲的漂移 |
| **A11Y-S3** | 選定的版本在選定當天已發布**至少 14 天**，且其 `peerDependencies` 涵蓋已安裝的 `@playwright/test`（目前 `1.61.1`） | `code-generation` 的 `code-summary.md` 記下選定版本、發布日期與 `npm view` 的 peer 範圍輸出 | 剛發布的版本來不及被社群發現的惡意或破壞性變更；peer 範圍不相容時 npm 只警告不報錯，掃描可能以不明方式失效 |
| **A11Y-S4** | 新增的套件樹（`@axe-core/playwright` 與其相依）在 `npm audit` 下不得有 high／critical | `npm audit --omit=dev` 不適用（它是 dev 套件）；改以 `npm audit` 的全量輸出，過濾出新套件樹的條目，記入 `code-summary.md`。若有 high／critical，停下來回報，不得以 `--force` 處置 | 引入一個已知有漏洞的套件；dev 套件雖不進產品，但會在 CI runner 上執行 |
| **A11Y-S5** | 掃描一律在 `page.route` 攔截的頁面上執行；spec 不得觸及任何 LLM 路徑、不得連外 | spec 內每一個被造訪的頁面，其 `/api/**` 請求都有對應的 `route` 處理；以 `page.on('request')` 記錄未被攔截的 `/api/` 請求，數量須為 0 | e2e 碰到 LLM 路徑會讓每個 PR 花錢且不穩（`test-case-authoring.md` §4.3）；連外會讓閘門受外部服務狀態影響而誤紅 |
| **A11Y-S6** | 掃描結果的附件（違規 JSON、DOM 片段）不得含任何真實憑證 | spec 使用的 token 一律是固定的假值（與既有 `member-pages.spec.ts` 等的 stub 同形狀）；附件只包含 axe 回報的 `violations` 與 `incomplete` 兩個欄位，不附整頁 HTML | `ui-regression` 的報告是 Actions artifact，而本 repo 為 public——一份帶真實 token 的附件等同公開發布（`project.md ## Mandated` 的 secrets／variables 那條規則，同一個風險） |
| **A11Y-S7** | **閘門不得在沒掃到東西時通過**。每次掃描前先斷言該狀態的關鍵元素已渲染，掃描後斷言 axe 的 `passes` 非空 | 每個掃描點有一行 `await expect(<該狀態的 test-id>).toBeVisible()` 在 `analyze()` 之前；`results.passes.length > 0` | 授權被導回 `/login`、`/403`，或資料尚未載入時掃到的是空頁——空頁沒有違規，閘門會綠，而實際受測的畫面從未被掃過 |
| **A11Y-S8** | 規則集限定為 WCAG 2.1 AA：`withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa'])`。只有 `violations` 擋 PR；`incomplete`（axe 判不定、需人工）不擋，但必須附在報告裡 | spec 內 `withTags` 的參數逐字如上；`incomplete` 以 `testInfo.attach` 附上 | 不限定規則集時，axe 的 best-practice 規則會讓閘門的標準悄悄高於已核可的 AA；`incomplete` 若被丟掉，`[人工]` 項目就失去唯一的線索 |
| **A11Y-S9** | **既存違規基準清單**（`[A11Y-Q1]`=A）：頁殼（`Layout`、`Sidebar` 既有部分）在第一次實跑時已存在的違規，以「掃描點 ＋ 規則 id ＋ 元素選擇器」逐筆列進 spec 旁的基準檔；只擋清單以外的違規 | 見下方「基準清單的四條規則」 | 不處理時，既有技術債讓本 intent 的閘門一上線就紅（與 `[DM:D11]`=A 不掃 `/admin/*` 同一個理由）；處理得太寬時，新違規被藏進清單 |

| **A11Y-S10** | **掃描面是兩份已核可上游的聯集，不是其中一份**：`accessibility-checklist.md` 修訂 1 的 12 次掃描，加上 `contract-summary.md` 的 `K-19`／`K-20` 列為「必須存在且可被 axe 掃描」、而清單沒有列的兩個畫面——**專案建立頁**（`K-19` `test_target_surface.routes`）與**成員詳情頁**（`K-20` `test_target_surface.routes`）——共 **14 次** | spec 內的掃描點與下表逐列對應，數量為 14 | 只照清單掃，`K-19`／`K-20` 對 `U23`／`U24` 課的「可被 axe 掃描」義務就沒有任何消費端兌現——契約有一端懸空 |

### 掃描面（`A11Y-S10`）

| # | 畫面／狀態 | 來源 |
|---|---|---|
| 1 | 入口頁 | 清單 ＋ `K-13` `provides_to_U17`（route `/`） |
| 2 | `/memory` | 清單 ＋ `K-14` |
| 3 | 專案清單 | 清單 ＋ `K-19` |
| 4–6 | 專案詳情：總覽／需求／記憶摘要三籤各一次 | 清單 ＋ `K-19` |
| 7 | **專案建立頁** | **只在 `K-19`**——本站補入 |
| 8–9 | 成員清單：admin-view、member-view | 清單 ＋ `K-20` |
| 10 | **成員詳情頁**（角色下拉、移出專案、變更紀錄） | **只在 `K-20`**——本站補入 |
| 11–12 | 邀請對話框：default、denied | 清單 ＋ `K-20` |
| 13–14 | 改選橫幅：single、multi-expanded | 清單 ＋ `K-20` |

**兩份上游為何不一致、為何取聯集**：清單的掃描點是 `refined-mockups` 修訂 1（2026-10-02）依線框節次列的；`K-19`／`K-20` 是之後的 `contract-design` 依頁面列的，清單的掃描點表沒有為多出的兩個畫面各開一列。成員詳情對應線框 §25；建立頁對應的線框節次本站未查證。兩份上游都已核可、彼此不矛盾，聯集是唯一不讓任一份的義務落空的讀法。本站不回改清單（`refined-mockups:c3`），在此明記為對齊修正。

**改選橫幅的掛載點**：`K-20` 寫明橫幅掛在「使用者**自己的落地頁**（不限入口頁）」。落地頁若是本 intent 不管的既有頁（例如 `/workspace`），整頁掃描會掃進既有頁面。故第 13–14 次掃描以**落地頁為入口頁的視角**執行；其他落地頁上的橫幅以 `AxeBuilder.include()` 限縮到橫幅節點，交 `code-generation` 決定是否增列，並受 `A11Y-S7`／`A11Y-S9` 約束。

### 基準清單的四條規則（`A11Y-S9` 的可驗證條件）

1. **只准收頁殼的既有節點**。清單內任何一筆的選擇器若落在本 intent 新元件的根節點之內（入口頁、`/memory`、專案頁、成員頁的頁面容器），或指向 `Sidebar` 的**三個新增項**（入口／專案／我的記憶），測試失敗。新元件的違規沒有理由被列入基準。
2. **過期的條目會讓測試失敗**。清單內每一筆都必須在當次掃描中真的出現；某筆不再出現（因為有人修好了），測試失敗並要求刪掉那一筆。這是「只准縮小」的機械形式。
3. **不得擴大由程式碼審查把關，不是由測試**。測試沒有歷史可比對，它看不出某一筆是第一次實跑就有的、還是後來加進去的。所以清單第一次建立時，`code-generation` 必須在 `code-summary.md` 記下當時的完整清單與筆數；之後任何新增都是 diff 上可見的變更，審查者以那份記錄為比對基準。**這一條的強度是審查，不是閘門**，明寫在此以免被讀成機械保證。
4. **每一筆附一行說明**：違規內容的白話描述、為何屬於頁殼既有問題。沒有說明的條目，審查者無從判斷它該不該在那裡。

已知的弱點（`[A11Y-Q1]` 選項 A 揭露過）：同一條規則在同一個舊元素上換了寫法、但選擇器沒變，會被誤放行。本站接受這個風險，理由是它只發生在本 intent 不管的頁殼上。

## ADR-0006 四面向逐項判定

`project.md` 要求逐項判定、不適用者附理由，且判 N/A 之前先問「它要防的失敗模式在本單元以別的形式存在嗎」。

| 面向 | 判定 | 理由 | 失敗模式是否以別的形式存在 |
|---|---|---|---|
| **IAM** | 不適用 | 不新增身分、角色、權限或 `role_permissions` 列；spec 用的 token 是攔截層的假值，不經真實認證 | **存在一個變形**：掃描狀態依賴「以某角色進入頁面」，若攔截的 `/me` 回錯角色，掃到的是另一個視角（例如 member-view 掃成 admin-view）。由 `A11Y-S7` 承接——掃描前斷言該視角專屬的 test-id |
| **Encryption** | 不適用 | 不儲存、不傳輸任何資料；套件經 npm registry 的 HTTPS 下載並由 lockfile `integrity` 驗證 | 套件完整性由 `A11Y-S2` 承接 |
| **Network exposure** | 不適用 | 不開 port、不新增服務；只在 CI runner 上執行 | **存在一個變形**：測試若連外，CI 結果受外部狀態影響。由 `A11Y-S5` 承接 |
| **Audit logging** | 不適用 | 沒有任何需要稽核的執行期動作 | **存在一個變形**：這道閘門的結果是「新頁面通過 AA 自動檢查」這個主張唯一的證據，證據若只是一個綠燈而無內容就無從複查。由 `A11Y-S8` 承接——違規與 `incomplete` 一律附進報告 |

**PBT（ADR-0006 第二條 hard constraint）**：不適用。14 個掃描點是固定的狀態集合，沒有值域可探索；本單元也不是 IaC generator、cost calculator 或 agent routing。

**法規框架**：無外部法規適用（`requirements.md` `C-R1`：只部署至自有 staging）。WCAG 2.1 AA 是本 intent 自訂的品質目標，不是法規義務。

## 交接事項

| # | 事項 | 承接站 |
|---|---|---|
| H-1 | **`/admin/*` 是否納入掃描的重審**（`unit-of-work.md` 的 `UG-5`）。本站不翻案 `[DM:D11]`=A；但若 `code-generation` 決定以 `.include()` 對 §27 的錯誤態做範圍受限掃描，它同樣受 `A11Y-S7`／`A11Y-S8`／`A11Y-S9` 約束 | `code-generation`（ALWAYS） |
| H-2 | **`ui-regression` 的時間預算**。`U14` 新增 54 案時已記為未量測；本單元再加 14 次掃描。逾 15 分鐘時 `ui-regression` 會因 `timeout 15m` 變紅 | `build-and-test`（實測整體耗時） |
| H-3 | **`[人工]` 項目**：axe 只判得到約三成；鍵盤可走完流程（O-1）、焦點陷阱與返還（O-12）、播報內容是否有意義（R-4）等仍須人工驗證 | `build-and-test` ＋ `tcms-test-cases` |
| H-4 | **上游缺少無障礙 NFR**（見「需求 ID 的來源」）。下一站 `nfr-design` 的 traceability sensor 會因此回報 no NFRx.y IDs | `nfr-design`（如實處置，不補假父 ID） |

## Assumptions & Open Questions

- 頁殼目前有多少既存違規，**本站未實跑**，所以基準清單的大小未知 [assumption]。若第一次實跑發現頁殼違規多到基準清單失去意義（例如超過新元件違規的數倍），`code-generation` 應停下來回報，而不是照單全收。
- `accessibility-checklist.md` 自己記載「本站未實跑驗證每一個 `[axe]` 標記是否真的被該工具涵蓋」[assumption]，本站沿用這個未驗證狀態，不加以宣稱。
