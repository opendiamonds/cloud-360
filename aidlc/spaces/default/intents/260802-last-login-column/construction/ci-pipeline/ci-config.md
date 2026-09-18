# CI Configuration

> 檔案：`.github/workflows/ci.yml`。本 intent **新增三個步驟**，不新增 job、不改觸發條件、不改 `concurrency`。

## 既有結構（未變動）

| Job | 內容 | 觸發 |
|---|---|---|
| `repo-contract` | `python scripts/validate_repo_contract.py` | PR ＋ push 到 `main`／`ut`／`danniel/**`／`chore/**` |
| `frontend` | `npm ci` → lint → build（含 `tsc -b`） | 同上 |
| `backend` | `pip install` → import smoke → `unittest discover` | 同上 |
| `docker-build` | buildx 建兩個 image（`push: false`） | 同上 |

`concurrency` 取消同 ref 的舊 run；`permissions: contents: read`。**四項皆未變動。**

## 本 intent 新增的三個步驟

| # | 步驟 | 所在 job | 位置 | 指令 |
|---|---|---|---|---|
| 1 | `API type contract drift` | **frontend** | lint 之後、build 之前 | `npm run check:types` |
| 2 | `Spec must not be served statically` | **frontend** | build **之後**（需要 `dist/` 已存在） | `find dist -type f \( -name 'openapi*' … \)` |
| 3 | `OpenAPI spec drift` | **backend** | import smoke 之後、unittest 之前 | `python scripts/dump_openapi.py --check` |

### 為何 1 與 3 分屬兩個 job（不是可以合併的重複）

規格檔的 gate 只保證「規格 == 後端程式碼」。若有人重新 dump 了規格卻**忘了重產型別檔**，型別檔仍宣告舊形狀，而 `tsc -b` 檢查的是「用法是否符合型別檔」而非「型別檔是否符合規格檔」—— 那條路徑會**靜默通過**。

**backend job 沒有 node，結構上不可能重產型別檔**，所以第二道 gate 必須在 frontend job（該 job 為全樹 checkout，讀得到 repo 根的規格檔）。

### 為何 2 必須在 build 之後

它檢查的是 `dist/` 的內容 —— build 之前那個目錄不存在。

## 環境變數

步驟 3 需要 `DATABASE_URL` 與 `JWT_SECRET`（與既有的 import smoke 相同的 CI-only 假值）。**不需要真實資料庫** —— 規格可在不啟動服務、不連線的前提下由程式碼取得（連線引擎為惰性建立）。

## 未變動的事

- **不新增 job** —— 三個步驟都掛在既有 job 內，不增加 runner 數量
- **不改觸發條件、不改 `permissions`、不改 `concurrency`**
- **`docker-build` 完全不受影響** —— 型別檔已 commit 進 `frontend/src/`，前端映像的 build context 內容不變（這正是 C-8 的 Q6=A 定案要保住的性質）
- `deploy.yml` **一字未改**
