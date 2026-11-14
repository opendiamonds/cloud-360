# CI/CD Pipeline — `a11y-gate`（U17，`kind: packaging`）

<!-- Stage: infrastructure-design（Construction 3.4）· Unit: a11y-gate · Record: 260920-orchestration-brain -->

## 本單元在管線中的位置

本單元不新增管線、不改任何工作流程檔。它是既有 `ui-regression` 的一支新 spec。

| 管線 | 本單元是否參與 | 方式 |
|---|---|---|
| `ci.yml` 的 `frontend` job（lint ＋ `tsc -b` ＋ build） | 間接 | `frontend/tests` 不在任何 tsconfig 內，spec 本身不受 `tsc -b` 檢查（`entry-page-ui` 的 `unit-test-instructions.md` 已記載此事實）；`eslint .` 會掃到它。新增的 devDependency 會進 `npm ci` |
| `ui-regression`（gh-aw，每個 PR） | **是，這就是閘門** | `timeout 15m npx playwright test` 撿起 `a11y.spec.ts`；post-steps 以 `stats.unexpected` 判紅 |
| `deploy.yml` | 否 | 不跑 e2e；devDependency 不進產品 image（`A11Y-S1`） |

## 執行順序（一次 `ui-regression` 中）

1. `timeout 3m npm ci` —— 安裝含新套件的依賴樹（`A11Y-S2`：lockfile 必須同 commit 更新，否則 `npm ci` 失敗）。
2. `timeout 8m npx playwright install --with-deps chromium` —— 不變。
3. compose stack 起好（既有步驟）。
4. `timeout 15m npx playwright test` —— 全部 spec，`fullyParallel: false`、`workers: 1`，`a11y.spec.ts` 與其他 spec 依檔名順序執行。
5. post-steps：讀 `pw-report.json`，`stats.unexpected` 非 0 即 `exit 1`。
6. Kiwi TCMS 回報（best-effort，不擋）。

## Stage → Gate

| Stage | Gate | 本單元貢獻的失敗原因 |
|---|---|---|
| `npm ci` | lockfile 不一致即失敗 | `package.json` 與 `package-lock.json` 未同步 |
| `playwright test` | `stats.unexpected` 非 0 | 新違規、就緒失敗、隔離層偵測到漏攔截、基準清單過期或違規收錄規則 |
| `timeout 15m` | 逾時即整個 job 失敗 | 18 次掃描的耗時（未量測，交接 H-2） |

## 部署策略與回滾

不適用：本單元不部署。回滾即 revert 引入它的 commit——移除 spec 與 devDependency 不影響任何執行期行為。

## 閘門本身的回滾路徑（需要時怎麼關掉它）

若閘門在合併後持續誤紅、擋住所有 PR：

1. **首選**：修 spec 或基準清單。
2. **暫時**：在 `a11y.spec.ts` 的 `describe` 加 `test.skip` 並附 issue 連結。這會讓 TCMS 的 21 個案例顯示為 skipped，**看得出閘門被關掉**——比刪掉 spec 好，後者讓案例變成沒有執行紀錄的孤兒（`test-case-authoring.md` §4.4 第 1 條）。
3. **不得**：以 `--grep-invert` 或改 `playwright.config.ts` 的 `testIgnore` 靜默排除——設定層的排除不會出現在任何報告裡。

## Secrets in CI/CD

無。spec 不需要任何 secret；攔截層的 token 是寫在 spec 內的假值（`A11Y-S6`）。

## 合併順序

`U17` 依賴 `U14`／`U15`／`U23`／`U24` 的頁面已存在（`unit-of-work.md` 的依賴邊）。它掃的 test-id 全部在那四個單元裡；若 `U17` 先於任一者合併進 `ut`，對應掃描點的就緒層會紅。`delivery-planning` 的 `bolt-plan.md` 把 `U17` 放在 `B8`，而執行順序 `B1 → B10 → B2 → B11 → B3 → B12 → B13 → B4 → B5 → B6 → B7 → B8 → B9` 使 `B8` 排在 `U24` 所在的 `B12`、`U23` 所在的 `B13` 之後——這條順序已由該站以腳本驗證，本單元照它合併即可，不需另訂。
