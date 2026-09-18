# Build Instructions

> Stage: build-and-test（Construction 3.6）· 上游：五個單元的 `../*/code-generation/code-summary.md`。
> **全部指令皆已實際執行過**，下方記載的是實測結果而非預期值。

## 前置

| 需求 | 版本 | 備註 |
|---|---|---|
| Python | 3.12（CI）／3.13（本機實測） | 兩者皆通過 |
| Node | 22（CI） | |
| Docker | 任一近期版本 | 只有 e2e 需要 |

## Backend

```bash
cd backend
pip install -r requirements.txt
```

`fastapi` 與 `pydantic` 為**精確等值釘選**（`==`），其餘 10 支未 pin（既有現況）。釘選這兩支是 OpenAPI 規格漂移 gate 的前提 —— 詳見 `../api-type-contract/code-generation/code-summary.md`。

## Frontend

```bash
cd frontend
npm ci
npm run build     # = tsc -b && vite build
```

`dependencies` 與 `devDependencies` **零變動**，故 `package-lock.json` 未變。型別產生器以釘住版本的 `npx` 一次性呼叫，不進依賴樹。

## 產生物的重產（改了後端 API 形狀時**必須**做）

```bash
cd backend && python scripts/dump_openapi.py    # → repo 根的 openapi.json
cd ../frontend && npm run gen:types             # → src/types/api.d.ts
```

兩者**都要 commit**。漏做任一個，對應的 CI gate 會紅 —— 那是刻意的攔截點。

## e2e 用的短生命週期 stack

```bash
docker compose -f deploy/docker-compose.test.yml up -d --build
# 等 http://localhost:8090 可用後
cd frontend && BASE_URL=http://localhost:8090 npx playwright test
docker compose -f deploy/docker-compose.test.yml down -v
```

首次執行需 `npx playwright install chromium`（本機實測時確實需要 —— CI 的 gh-aw workflow 另行處理）。
