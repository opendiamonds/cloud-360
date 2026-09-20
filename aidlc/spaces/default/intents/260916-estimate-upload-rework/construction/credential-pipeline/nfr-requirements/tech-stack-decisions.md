# Tech Stack Decisions — credential-pipeline

> Unit: `credential-pipeline`（U4／B3）· kind: **packaging** · Q4=A、Q5=A。

| 面向 | 決策 | 理由 |
|---|---|---|
| Secret 儲存 | **GitHub Secrets**（既有 deploy workflow） | FR5.8／FR11.1；不引入 Vault（Q4=A） |
| 設定產生 | **`deploy/render-env.sh` → `deploy/.env`** | 既有 env contract；`validate_env_contract.py` 強制 |
| 容器注入 | **`deploy/docker-compose.deploy.yml`** | 與現行 staging 路徑一致 |
| 本機／範本 | **`backend/.env.example`、`deploy/.env.example`、`LOCAL-DEV.md`** | FR11.3；變數名可出現、值留空 |
| Contract 閘門 | **`validate_repo_contract.py`（值樣式）＋ `validate_env_contract.py`** | Q1=A；六檔 env 同步（FR9.8「增」側） |
| CI test stack | **不注入 AWS／GCP 密鑰** | Q2=A；FR11.4 |
| 新執行期依賴 | **無** | packaging only；無 Python／Node 套件 |
| 規則文件 | **ADR-0018 於本 unit code-gen 開頭先寫** | Q5=A；取代 `project.md`／`team.md`／ADR-0017 §8 矛盾句後才改 deploy |

## 變數清單（本 unit 負責「增」側）

| 變數 | 用途 | 必填 |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Price List Query（boto3） | 否（缺則 U5 降級） |
| `AWS_SECRET_ACCESS_KEY` | 同上 | 否 |
| `AWS_DEFAULT_REGION` | 預設 `us-east-1` | 否（有預設） |
| `GCP_BILLING_API_KEY` | Cloud Billing Catalog | 否 |

Azure Retail：無憑證變數。

## 與 U3 的協調（非 tech 新增）

FR9.8「減」舊 C1 參數屬 U3；本 unit 只做憑證「增」。Delivery 已要求 U4 在 U3 部署前完成，避免 env contract 中間態紅燈。

<!-- confirmed: Looks correct -->
