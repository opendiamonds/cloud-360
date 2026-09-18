# Build Instructions — A1/A3 UX bugfix

> Intent: `260806-a1-a3-ux` · Consumes: `construction/a1-a3-ux/code-generation/code-summary.md`

## Prerequisites

- Python 3.12+（後端）、Node.js 20+／npm（前端）
- PostgreSQL（本機或 docker-compose）
- 環境：`OPENROUTER_API_KEY`（實際呼叫 Design Agent 時；單元測試可不設）

## Dependency Install

```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

## Build Commands

```bash
# Frontend typecheck + production bundle
cd frontend && npm run build

# Backend 無獨立 compile；以 import／unittest 驗證
cd backend && python3 -c "from services.prompt_guard import REFUSAL_MESSAGE; print(REFUSAL_MESSAGE)"
```

## Verification

1. `npm run build` 結束碼 0
2. `python3 -m unittest discover -s tests -q` 結束碼 0
3. （建議）`npm run lint` 無 **error**（既有 pages 可能仍有 warning）

## Troubleshooting

| 現象 | 處理 |
|---|---|
| React Fast Refresh lint on Layout | `useLayoutNav` 須在 `NavChromeContext.tsx`，勿與 `Layout` 同檔 export |
| draw.io Undo 無效 | 確認 autosave 不會再次 `action:load`（見 DrawioCanvas） |
| prompt 拒答不出現 | 確認走 `/generate` 或 `/generate-wa-collab`，且訊息命中 `prompt_guard` |
