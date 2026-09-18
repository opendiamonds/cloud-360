# Code Summary — api-type-contract（U5）

## 實際產出

| 檔案 | 內容 |
|---|---|
| `backend/scripts/dump_openapi.py` | 90 行。`--check` 供 CI 比對；不啟動服務、不連資料庫（mock psycopg2、惰性引擎） |
| `openapi.json` | 68,951 bytes、36 paths、**29 schemas**（新增 `UserListPage`） |
| `frontend/scripts/check-api-types.mjs` | 48 行。重產到暫存檔後比對，不寫入 `src/` |
| `frontend/src/types/api.d.ts` | 2,385 行（產生物，committed） |
| `frontend/package.json` | 兩個 script：`gen:types`、`check:types`。**`dependencies` 與 `devDependencies` 皆零變動** |
| `backend/requirements.txt` | `fastapi`／`pydantic` 改為 `==` 精確釘選 |
| `.github/workflows/ci.yml` | 三個新步驟：兩道漂移 gate ＋ 靜態暴露檢查 |

## 與設計的偏離：產生器不進 devDependency

C-8 原假設產生器成為 `devDependency` 並一併 commit lockfile。**實作時發現不可行**：本專案 TypeScript 為 `~6.0.2`，而該產生器**所有已發佈版本**的 peer 皆為 `^5.x`，`npm install` 直接 `ERESOLVE` 失敗。

三個選項中選了成本最低且不說謊的一個：**不加依賴，以釘住版本的 `npx` 一次性呼叫**。

| 被否決的選項 | 理由 |
|---|---|
| `--legacy-peer-deps` | 會改變**整個 repo** 的安裝語意，影響面遠大於本 feature |
| `overrides` 強制 peer | 等於宣稱一個未經驗證的相容性 |

**代價（如實記載）**：產生器的傳遞依賴不進 lockfile。緩解：產生器自身版本被精確釘在**兩處**（`package.json` 的 `gen:types`、漂移檢查腳本內的常數），兩處必須一致 —— 不一致會讓 gate 比對到不同產生器的輸出而誤報。

**附帶結果**：AD-5「不引入新依賴」在實作上比 AD-9 預期的**更完整地**成立。AD-9 的 Consequences 仍寫著「新增一個 devDependency」，該項已被本實作取代（上游不回改，交叉註記於本單元的 `../nfr-requirements/security-requirements.md` S-3）。

## 三道 gate 皆已以刻意違反實測

| Gate | 乾淨時 | 刻意違反時 |
|---|---|---|
| 規格漂移（backend job） | exit 0 | **exit 1** |
| 型別漂移（frontend job） | exit 0 | **exit 1** |
| 規格不得被靜態供出（frontend job） | 通過 | **命中並 exit 1**（把規格檔複製進 `dist/` 後） |

第三道是 reviewer 指出「S-1 有威脅模型與契約，但沒有自動化執行」後補上的 —— 把「天然安全的形狀」由設計性質升格為**機械保證**。

**這三次實測是本單元唯一的外部驗證**：交付物即 gate，不刻意弄壞一次就無從得知它們是否真的會失敗。
