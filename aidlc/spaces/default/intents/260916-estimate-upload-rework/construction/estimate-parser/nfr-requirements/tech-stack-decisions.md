# Tech Stack Decisions — estimate-parser

> Unit: `estimate-parser`（U1）· kind: **library** · Q5=A、Q3=A、Q4=A。

| 面向 | 決策 | 理由 |
|---|---|---|
| 語言／執行期 | **既有 Python 3**（backend） | brownfield；無新 runtime |
| 模組位置 | **`backend/cost/estimate_parser.py`、`estimate_validator.py`**（＋同套件讀取器） | FD 已釘；FR9.6 邊界腳本改指此處 |
| CSV | **標準庫 `csv`** | 零新依賴；AWS／GCP 主格式 |
| Azure XLSX | **新增 `openpyxl==3.1.5`**（`backend/requirements.txt`） | Q5=A；repo 目前無 xlsx 讀取庫；釘死 3.1.5（2024–2025 穩定線，code-gen 若 PyPI 已有更新 patch 可升同 minor，不得用預覽版） |
| 測試 | **`unittest` + `hypothesis`**（既有） | NFR4.1／FR2.4；不引入 pytest |
| 邊界閘門 | **擴充 `scripts/validate_cost_calculator_boundary.py`** | FR9.6；掃 parser／validator／讀取器 |
| HTTP／DB／LLM | **禁止** | FR2.3；library 邊界 |
| 新基礎設施 | **無**（無佇列、無新服務、無 Playwright） | NFR8 精神；library 不部署獨立元件 |

## 依賴變更（code-gen 必做）

| 套件 | 動作 | 備註 |
|---|---|---|
| `openpyxl` | **新增 `openpyxl==3.1.5`** | 僅本 unit 讀 XLSX；禁止預覽／yanked 版 |

## 不做

- 不引入 pandas／numpy 作為解析核心（過重、邊界難控）
- 不在本 unit 安裝 Playwright／瀏覽器（NFR8 反面教材）
- 不新增前端或 HTTP 框架

<!-- confirmed: Looks correct -->
