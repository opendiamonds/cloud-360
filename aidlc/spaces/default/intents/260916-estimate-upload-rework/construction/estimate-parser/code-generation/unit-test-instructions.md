# Unit Test Instructions — estimate-parser

> Unit: `estimate-parser` · Standard · test-after  
> 測試對象：`backend/cost/estimate_parser.py`、`estimate_validator.py`（純函式；無 HTTP／DB）。

## Framework

- Python 內建 `unittest` + 既有 `hypothesis`
- **不**引入 pytest
- CI：`cd backend && python -m unittest discover -s tests -v`

## Exact unit-scoped command（須在第一個實作測試前可跑）

```bash
cd backend && python3 -m unittest tests.test_estimate_parser tests.test_estimate_validator -v
```

## Cases（目標 5–8+；含 PBT）

| # | 模組 | 情境 | 期望 |
|---|---|---|---|
| 1 | parser | 最小合法 AWS CSV fixture | `detection.status=resolved`、`cloud=aws`、≥1 parsed 列 |
| 2 | parser | 超量列或超 32 MiB（NFR3.1） | ambiguous＋`lines=[]`，不 raise |
| 3 | parser | 金額無法解析的列 | `parseStatus=unidentifiable`、保留 rawText；整份不失敗 |
| 4 | validator | 幣別多數決＋offender | BR4.1 |
| 5 | validator | 負 quantity | BR4.2 offenders |
| 6 | validator | 有 unidentifiable → 跳過對帳 | BR4.4 `attempted=false` |
| 7+ | 兩者 | **≥3 Hypothesis 性質**（NFR4.1）：同入同出；禁 import 副作用（可靜態／執行後 assert）；BR4 對帳容差 deterministic | 通過 |

## Coverage / mocking

- 無 coverage.py 閘門；以案例與 PBT 二元通過為準
- 假估價表僅 tempfile／字串 fixture，不 commit 真實客戶資料
- 不 mock 正則／BR 邏輯本身

## Out of scope

- TestClient／Playwright
- U2 上傳魔數／5 MB HTTP 拒絕
- TCMS 手寫
