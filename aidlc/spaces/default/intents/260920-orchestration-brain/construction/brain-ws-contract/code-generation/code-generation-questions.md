# Code Generation 問題檔 — `U2 brain-ws-contract`

<!-- Stage: code-generation（Construction 3.5）· Unit: brain-ws-contract · kind: spec -->

本站只有一個關卡：Plan Approval。計畫本身與單元測試指示是它的兩個綁定對象。

<!-- 結構注意：`## Plan Approval` 之下不得有任何子標題。
     `latestPlanApproval`（aidlc-testing-posture.ts:1264）在遇到任何 heading 時
     就離開該區段，子標題會把 [Approval Fingerprint]／[Planned Source]／[Answer]
     隔到區段外，導致「fingerprint does not match」——本站實際踩過一次。
     故摘要全部放在本標題之前。 -->

## 核可對象（三者一併）

1. `code-generation-plan.md` — 11 個實作步驟
2. 該檔內嵌的 `## Testing Contract`（`methodology: test-after`、`test_strategy: standard`、
   `contract_sha256: sha256:1f0b6822…`，由 `testing-posture render` 原樣產生，未經任何改寫）
3. `unit-test-instructions.md` — 13 個測試、5 項突變驗證、本單元專用的執行指令

## 計畫摘要

| Step | 內容 | 動到的既有資產 |
|---|---|---|
| 1 | 供應鏈修補：產生器進 `devDependencies` 精確釘 `7.13.0`、移除兩處 `npx --yes`、新增兩個 npm script | **`frontend/package.json`、`frontend/scripts/check-api-types.mjs`（S-1）** |
| 2 | 驗證測試 runner 並記錄本單元指令（brownfield，runner 已存在） | — |
| 3 | 實作契約模組 `backend/services/brain_ws_contract.py`（2 列舉、3 envelope、15 payload、2 子實體、`WsSubprotocol`、`BR1.5`／`BR1.6` validator） | — |
| 4 | 寫並跑 7 個模型測試 ＋ 突變 M1／M2 | — |
| 5 | 實作 `backend/scripts/dump_ws_contract.py`（`--check`、`BR1.4` 等勢斷言、`NFR5.7` 白名單、fail-closed） | — |
| 6 | 寫並跑 6 個 dump 測試 ＋ 突變 M3／M4／M5 | — |
| 7 | Repository／API 兩層不適用，明文記載 | — |
| 8 | 第二道閘門 `check-ws-types.mjs`、產生型別檔、ESLint error 規則、**改 `BrainPage.tsx` 為由型別取值** | **`frontend/eslint.config.js`、`frontend/src/pages/BrainPage.tsx`（S-4）** |
| 9 | 四項閘門突變驗證（含「改 `scheme` 讓前端編譯紅燈」，證明 `NFR5.4` 真的成立） | — |
| 10 | `ci.yml` 兩個新步驟 ＋ `REQUIRED_TEXT` 的 `ci.yml` 一鍵 | **`.github/workflows/ci.yml`、`scripts/validate_repo_contract.py`（S-3）** |
| 11 | docstring、`source-manifest.json`、`traceability.json`、`code-summary.md` | — |

## 單元測試指示摘要

- **框架零新增**：backend 用既有的內建 `unittest`；**前端不新增任何測試**
  （本單元沒有可由 Playwright 觀察的使用者行為，驗證面是 `eslint` 與 `tsc -b`）。
- **執行指令（本單元專用）**：
  `cd backend && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_ws_contract tests.test_dump_ws_contract -v`
  —— `PYTHONDONTWRITEBYTECODE=1` 不是可選的：`__pycache__` 不在引擎的來源指紋排除清單內，
  在審查窗口內產生 `.pyc` 會讓議決記不進去（本 session 已為此吃過兩次虧）。
- **13 個測試**：契約模組 7、dump 腳本 6（Standard strategy 的每元件 5–8）。
- **5 項突變驗證**，每一項都要看它紅過一次；突變本身也要開檔確認真的生效。
- **`team.md` 的 A／B／C 三條測試底線對本單元皆不適用**（不動 RBAC seed、不新增端點、
  不改使用者可見的資料形狀），逐項附理由而非略過。
- **ADR-0006 PBT** 判不適用附理由（`calculation` category 實算為 0）。

## 一個需要你一併裁決的衝突

`ADR-0019 §5` 的 ESLint 規則**一開即會讓 `frontend/src/pages/BrainPage.tsx:83` 紅燈**——
那行現持有 `` [`bearer.${token}`] ``，正是規則要抓的形狀，而那是今晚要展示的 demo 頁。

**計畫採 (a)：改 `BrainPage.tsx` 為由產生的型別取值，不刪除它。**
三行改動，demo 保住，而且它會成為這套機制的**第一個真實消費端**——
`NFR5.4` 的整條保護第一次有人證明它真的會動。
若你要改採 (b)（先刪 demo 頁），選 Request Changes 並說明，Step 8 會改寫。

## Plan Approval

[Approval Fingerprint]: sha256:v3:3ecf804cff2fe7edd6f70b2cbea6d51031b267be4879a5628df98e49284b9224
[Planned Source]: ecf079d60bb5fd020e9a7729c8b98ed0ea8181df2f4a9350b4094621252c670c

- **Approve Plan** — 進入程式碼產生
- **Request Changes** — 修改計畫

[Answer]: Approve Plan
