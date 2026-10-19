# Code Generation 問題檔 — `U17 a11y-gate`

## 核可範圍說明

本題核可的是同目錄下的 `code-generation-plan.md`（15 步，含其內嵌的 Testing Contract，`test-after`、`standard`）與 `unit-test-instructions.md`。明白揭露（逐條對應計畫第四、八節）：

- **交付規模**：`frontend/package.json`／`package-lock.json`（新增一個 devDependency `@axe-core/playwright`）、新檔 `frontend/tests/e2e/a11y.spec.ts`（21 個 `test()`）與 `frontend/tests/e2e/a11y-baseline.json`。零後端、零 DDL、零環境變數、零 secret、零 workflow 檔變更。
- **可能重開已交付單元**：第一次實跑若掃出本 intent 新元件的違規，本單元會改 `U14`／`U15`／`U23`／`U24` 的元件檔，**限無障礙屬性**（`aria-*`、`role`、`alt`、`<label>`、標題層級、對比色 class），不改行為、test-id、版面結構。單一元件需結構性改動或新元件違規超過 10 筆時停下回報。
- **頁殼既存違規**依 `[A11Y-Q1]`=A 列入基準清單；交界類規則（landmark／region／標題層級）一律停下回報，不進基準、不自行修頁殼。
- **`/admin/*` 維持不掃**（`UG-5` 重審結論，沿用 `[DM:D11]`=A）。
- **`playwright.config.ts` 預設不改**；僅在重試排程實證會讓過期檢查誤紅時，依 `D-03` 備案改。
- **本機無 Docker**：以 `vite preview` 跑；spec 全走攔截層，與 compose stack 的差異不影響掃描結果。
- **不修的已知缺口**：`ui-regression` 無 artifact 上傳（綠燈時 axe 結果零留存）、契約 `brain-*` 前綴與實作不符——兩者交 `build-and-test`。
- **追溯 sensor** 會報 no NFRx.y IDs（上游無無障礙 NFR），照實保留。

## Plan Approval

[Approval Fingerprint]: sha256:v3:0febdc507df7d336f3ed045c2af2a282772894adebe7e7be1f9182fee505f42b
[Planned Source]: 2871fd723b13aedaf0d7b286b700192910149fb8118501a26596f7503e512f67
- "Approve Plan" — proceed to code generation
- "Request Changes" — revise the plan
[Answer]: Approve Plan
