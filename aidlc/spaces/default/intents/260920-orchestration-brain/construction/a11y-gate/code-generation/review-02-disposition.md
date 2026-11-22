# code-generation review-02 處置紀錄 — `a11y-gate`（U17）

<!-- Stage: code-generation（Construction 3.5）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

本檔記錄對 `reviews/review-02.md` 的處置。本單元已審查的產出（`code-generation-plan.md`、`code-summary.md`、`unit-test-instructions.md`、`traceability.json`、`source-manifest.json`）凍結不改；凡與那幾份檔的敘述衝突者，以本檔為準。本檔所有數字皆取自 2026-10-24 實際執行的指令輸出。

## 一、使用者裁決

2026-10-24，使用者對 review-02 裁決：**現在補掃描點，並修正對比**（針對 `R-08`）。不採「明確接受缺口、改人工驗證」的另一條路。

## 二、新增的三個掃描點（`frontend/tests/e2e/a11y.spec.ts`）

三點皆沿用該檔既有四層形狀（隔離 → 狀態 → 就緒／排除 → 掃描；先寫結果檔再斷言），規格註解含 `@purpose`／`@given`／`@step`／`@pass`／`@ui`／`@story`／`@note`，不寫 `@api`；`describe('U17 a11y gate')` 未改；訊框一律由 `src/brain/testing/wsFrames.ts` 的建構器產生（`F.tokenFrame`、`F.errorFrame`、`F.encodeFrame`，沿用檔內既有的 `connectedSnapshot()` 握手）。

| 編號 | test 名稱 | 狀態層 | 就緒 | 排除 |
|---|---|---|---|---|
| 23 | `23 入口頁對話系統提示列` | 已連線入口頁；收到 `user_message` 時先送該輪 `token`，再送 `turnId=null` 的 `INVALID_REQUEST` error（`entry-page.spec.ts` 的 mb1 形狀） | `brain-entry-page`、`brain-system-notice`、`brain-stream-message`；`brain-user-message` 的 `data-pending=true` | 含「這句沒有送達」的 `brain-user-message`、`brain-stream-retry` |
| 24 | `24 入口頁原句未送達` | 已連線入口頁；收到 `user_message` 時不開輪次，直接送 `turnId=null` 的 error（mb5 形狀） | 含「這句沒有送達」的 `brain-user-message`、`brain-stream-retry`、`brain-system-notice`；`data-pending=false` | `brain-stream-message` |
| 25 | `25 成員清單查不到專案` | `/api/auth/me` 帶 K3 view+edit；成員清單 GET 回 404 | `members-list-page`、含「查不到這個專案」的 `member-list-error` | `member-list-table`、「載入中…」 |

23 與 24 刻意區分兩個不同畫面：23 是「該輪已開始回覆後才收到非輪次錯誤」（只多一則系統提示、原句不判為被拒），24 是「尚未開輪次即被拒」（原句標為未送達並提供重試）。若兩點都照「送一句、立刻回 null error」的同一形狀造，掃到的會是同一個畫面。

為支撐新就緒條件，`Probe` 型別增加一種「某 test-id 且其文字含某字串」的形式（`{ testid, hasText }`）。理由：「這句沒有送達」與「重試」在同一個 `<span>` 內，既有的精確文字定位器比對不到；「查不到這個專案」同時出現在 LiveRegion，頁面層級的文字定位器會同時命中兩個節點。

連帶更新的靜態數字：掃描點區塊標頭由「21 個掃描點」改為「24 個掃描點」；過期檢查的規格註解由「讀回 21 個／恰為 21 檔／檔數為 21」改為 24。過期檢查本身以 `ALL_SCANS` 動態計算期望檔名，程式邏輯不需改。

## 三、axe 結果與對比修正

第一次以生產建置實跑（修正前）：**26 passed、1 failed**，失敗的是第 24 點，掃描層回報 2 筆 `color-contrast`（impact `serious`，兩筆 `inNewRoot: true`）：

| axe target | 穩定選擇器 | axe 訊息（逐字） |
|---|---|---|
| `.mt-1` | 取不到（`null`） | `Element has insufficient color contrast of 4.23 (foreground color: #dbeafe, background color: #2563eb, font size: 9.0pt (12px), font weight: normal). Expected contrast ratio of 4.5:1` |
| `.ml-2` | `[data-testid="brain-stream-retry"]` | 同上，4.23 |

第 23、25 點在第一次實跑即無違規。

**量測值與審查估計的比較**：審查員依 `index.css` 色值靜態推算「約 4.2:1」；axe 實測 **4.23**；以 WCAG 相對亮度公式重算（`python3` 計算，來源色值 `index.css:9` `--color-brand-100: #dbeafe`、`:14` `--color-brand-600: #2563eb`）為 **4.24**。三者一致，審查疑慮屬實。

**修正**：`frontend/src/components/brain/ConversationView.tsx:25` 的 `text-brand-100` 改為 `text-brand-50`（`index.css:8` `--color-brand-50: #eff6ff`）。同一公式算得 `brand-50` 對 `brand-600` 為 **4.75**（`white` 為 5.17，未採用，以保留與泡泡本文的區隔）。重試鈕繼承同一色，故一處修正同時解掉兩筆。改後重跑，axe 對第 24 點不再回報任何違規。

依計畫第四節第 1 類處置：只改對比色的 Tailwind class，不改行為、test-id、版面結構；**未**列入 `a11y-baseline.json`。`a11y-baseline.json` 維持 `"entries": []`，sha256 改動前後皆為 `7c1051f6e2bc3943b7c1dbe4da229694455681b8875a346c99279e555edb733f`。

**歸屬注意**：`ConversationView.tsx` 由 `entry-page-ui` 單元的 `source-manifest.json` 認領（`grep -rln "ConversationView.tsx" … --include=source-manifest.json` 唯一命中 `construction/entry-page-ui/code-generation/source-manifest.json`），不屬本單元。本次只改一個 class；該檔相對 HEAD 的 `git diff --stat` 為 27 行，其餘差異是 entry-page-ui 本輪合併前必修的既有未提交變更，不是本單元所為。`entry-page-ui` 的追溯檔未由本單元修改，需由該單元或 `build-and-test` 確認是否要把這一處變更記入其 manifest。

修正後全量實跑：**27 passed**（24 個掃描點 ＋ 1 個手機寬度 ＋ 2 個基準檢查）。

## 四、回歸與閘門

| 檢查 | 指令 | 結果 |
|---|---|---|
| U17 全檔 | `BASE_URL=http://localhost:4394 frontend/node_modules/.bin/playwright test --config frontend/playwright.config.ts tests/e2e/a11y.spec.ts --retries=0` | 27 passed（18.8s） |
| 入口頁與成員頁回歸 | 同上，改跑 `tests/e2e/entry-page.spec.ts tests/e2e/member-pages.spec.ts` | 72 passed（46.6s） |
| lint | `npm --prefix frontend run lint` | 0 errors、2 warnings（`AssessmentPage.tsx:395`、`WorkspacePage.tsx:344`，皆 `exhaustive-deps`，與本次改動無關） |
| 型別 | `tsc -b frontend` | exit 0、無輸出 |
| repo contract | `python3 scripts/validate_repo_contract.py` | `Cloud-360 repository contract validation passed.` |

前端皆以 `npm --prefix frontend run build` 的生產建置 ＋ `vite preview` 服務。回歸是在對比修正之後的建置上跑的。

## 五、突變驗證

| 突變 | 內容 | 結果 |
|---|---|---|
| 1 — 移除狀態產生步驟 | 第 24 點的 `stageConversation` 回呼改為 `() => undefined`（收到 `user_message` 不再送 null error） | 紅在**就緒層**：`[就緒層] brain-user-message 含「這句沒有送達」 須可見`，`element(s) not found` |
| 1 還原 | 改回原回呼 | spec sha256 `111c0a78c1d074feb6d3719ff44c663946ff1752caaca3687e498bbe95d5864b`，與突變前記錄的值相同；其後全檔 27 passed |
| 2 — 還原對比色 | `ConversationView.tsx:25` 改回 `text-brand-100`，重建並重啟 preview | 紅在**掃描層**：第 24 點回報同樣 2 筆 `color-contrast`（`.mt-1`、`[data-testid="brain-stream-retry"]`） |
| 2 還原 | 改回 `text-brand-50`，重建並重啟 preview | 全檔 27 passed；`ConversationView.tsx` sha256 為 `077f3e9269a8b79735e7ba05a194eec63c4cb1864a8d2529f56fc3b78456f65b` |

## 六、Minor 項目處置

### R-10：現況數量表（取代凍結檔中的舊數字）

`code-generation-plan.md` 與 `unit-test-instructions.md` 寫的「21 個 test、18 個掃描點、讀回 18 個結果檔」，以及 `code-summary.md` 各處的數字，皆已過時。現況以本表為準（數自 `a11y.spec.ts` 實檔與本輪實跑）：

| 項目 | 數量 | 明細 |
|---|---|---|
| `test()` 總數 | 27 | Playwright 實跑「Running 27 tests」 |
| 掃描點 | 24 | 01–18、20–25（19 不是掃描點） |
| 手機寬度檢查 | 1 | 19 |
| 基準清單檢查 | 2 | 「基準清單只收頁殼既有違規」、「基準清單沒有過期條目」 |
| 過期檢查讀回的結果檔 | 24 | 每個掃描點一檔 |
| 基準條目 | 0 | `a11y-baseline.json` 為 `"entries": []` |

`unit-test-instructions.md` 第四節「18 個畫面狀態全部被掃描」的覆蓋目標同樣以本表的 24 點取代。

### R-09：Sidebar 對比問題的現況

`code-summary.md` 第四節、第五節與第十四節第 9 點仍寫 Sidebar 空選單提示的對比（約 2.6:1）「已列入基準」。實際是已在 `frontend/src/components/Sidebar.tsx:325` 修掉：該行現為 `<p className="px-4 text-xs text-gray-600 leading-relaxed">`（`sed -n 323,327p` 實讀），不在基準中，基準清單為空。若該節點退步，掃描層會變紅。上述 `code-summary.md` 段落以本節為準。

### 其他

本輪只處置 `R-08`、`R-09`、`R-10`。`R-01`–`R-07` 屬 review-01 的發現，review-02 標為「本輪未複驗」，本輪未改動。
