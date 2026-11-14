# CI/CD Pipeline — `U16 object-picker-ui`

> 撰寫時間 2026-10-18T02:25:30Z（`date -u` 取值）。精簡版（by-reference），理由見 `infrastructure-specification.md` 前言。

## 不新增任何 CI job

本單元的檢查全部由既有閘門撿到（`tech-stack-decisions.md` 的 `OPN-23`）：

| Stage | Gate | 本單元落點 |
|---|---|---|
| frontend：lint | `npm run lint`（`ci.yml:198`） | 選單檔案集合的 lint 區塊（`security-design.md` §一、`D-06`） |
| frontend：typecheck ＋ build | `tsc -b`、`npm run build` | 選單元件與純函式；id 型別邊界（`OPN-21`） |
| WS 漂移閘門 | `dump_ws_contract.py --check`、`npm run check:ws-types` | 本單元不改契約；`ws-contract.json` 前後雜湊比對（`logical-components.md` §三） |
| ui-regression | Playwright（`stats.unexpected` 非 0 即紅） | `object-picker.spec.ts`；`a11y.spec.ts` 兩個新掃描點 |
| deploy | `deploy.yml`（合併進 `ut` 觸發） | 隨前端 image，無額外步驟 |

## 合併順序

B7（`U15`、`U16`）。本單元修改 `U14` 的 `ContextBar.tsx` 與 `U17` 的 `a11y.spec.ts`，兩者都須已在分支上；合併前跑全部既有 brain e2e 與 `U17` 的 22 個測試。

## 本機執行（無 Docker 時）

`npm run build` → `npx vite preview --port 4173 --strictPort`（背景）→ `BASE_URL=http://localhost:4173 npx playwright test object-picker.spec.ts a11y.spec.ts` → 結束後停止 preview。
請求計數類案例必須對 preview（正式建置）執行（`D-01`）。
