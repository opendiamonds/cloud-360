# Code Generation Plan — api-type-contract（U5）

> Unit: `api-type-contract`（C-8）· Kind `packaging`：完全在建置期，不部署、不進執行路徑。
> 上游：`../../../inception/application-design/components.md` 的 C-8、`decisions.md` 的 AD-9、本單元的 `../nfr-requirements/*`。

## 四個組成 ＋ 兩道 gate

| 組成 | 位置 | commit |
|---|---|---|
| 規格 dump 腳本 | `backend/scripts/dump_openapi.py` | 是 |
| 規格檔 | **repo 根** `openapi.json` | 是 |
| 型別檔 | `frontend/src/types/api.d.ts` | 是 |
| 型別漂移檢查腳本 | `frontend/scripts/check-api-types.mjs` | 是 |
| 規格漂移 gate | CI **backend** job | — |
| 型別漂移 gate | CI **frontend** job | — |

**兩道分屬兩個 job 的理由**：backend job 沒有 node，結構上不可能重產型別檔。

## 位置約束（安全，非偏好）

規格檔與型別檔**皆不得**落在會被靜態服務原樣供出的路徑。`frontend/public/` 會被 Vite 原樣複製進 `dist/`，而 nginx 直接供出 `dist/` —— 規格檔落在那裡會把完整 API 地圖對未認證訪客公開。

## 版本釘選

`fastapi`／`pydantic` 精確等值釘選。規格輸出在同一組版本下位元決定性、跨版本會飄；不釘會讓 gate 在無關的 PR 上變紅，而該紅燈與真漂移不可區分。

## 採用時必須做的一件事

**以一次刻意的漂移實測兩道 gate 確實變紅** —— 本單元的交付物就是 gate，這是自我驗證，沒有外部機制保證它們真的會失敗。
