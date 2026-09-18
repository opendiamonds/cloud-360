# Operation

> AI-DLC 🟡 operation phase artifacts for Cloud-360。
> Cloud-360 operation 階段產出根目錄。

### 目的

本目錄（`<record>/operation/`）存放 AI-DLC operation 階段的文件產出：部署說明、可觀測性、事故應變。
可執行的部署程式與 compose 設定仍放在 repo 根目錄的 `deploy/`、`.github/workflows/deploy.yml`；本目錄負責**可稽核的 operation artifacts**，並以連結指向實作位置。

### 目錄結構

子目錄名對應 v2 的 operation 階段 stage slug。

| 路徑 | 對應 stage | 說明 | 狀態 |
|---|---|---|---|
| `deployment-execution/` | `deployment-execution` | 部署流程摘要、與 staging 管線對照；含 **A3 上線檢查清單** | 🔄 baseline + A3 checklist |
| `observability-setup/` | `observability-setup` | 監控、日誌、告警設計與 runbook 索引 | ⏳ 待補 |
| `incident-response/` | `incident-response` | 事故應變手冊（`runbooks.md`：SLO + 7 則 playbook） | 🔄 已有 runbooks |

### 現有來源（尚未全部搬進本目錄）

| 來源 | 說明 |
|---|---|
| [`deploy/`](../../../../../../deploy/) | self-hosted compose、cloudflared、環境變數範本 |
| [`DEPLOY.md`](../../../../../../DEPLOY.md) | 人工／環境變數部署說明 |
| [`deployment-execution/a3-go-live-checklist.md`](deployment-execution/a3-go-live-checklist.md) | **A3** Well-Architected 上線檢查清單（DB／權限／smoke／回滾） |
| [`.github/workflows/deploy.yml`](../../../../../../.github/workflows/deploy.yml) | push `ut` → self-hosted runner 自動部署 |
| [`ADR-0007`](../inception/decisions/0007-self-hosted-deployment-pipeline.md) | self-hosted + Cloudflare Tunnel 決策 |

### 維護準則

- 本目錄下所有 `.md` 一律繁體中文（ADR-0009）。
- 變更部署邊界、對外暴露或 secret 處理方式時，須更新或新增 ADR；階段事件由引擎寫入 `<record>/audit/` shard。
- 禁止在本目錄放入 production credentials、private key 或環境專用密文（repo contract）。
