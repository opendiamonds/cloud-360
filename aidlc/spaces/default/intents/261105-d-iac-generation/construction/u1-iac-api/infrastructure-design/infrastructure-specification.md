# Infrastructure Specification — u1-iac-api

> Q1–Q4=A · 沿用 ADR-0007 staging；無新雲端 production／apply。

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute | 既有 **backend Docker** 容器（compose） | 單進程 in-memory；與現況一致 |
| Networking | Cloudflare Tunnel → staging 主機 → nginx／compose 網路 | ADR-0007；不新開公網 LB |
| Storage | **無**本 unit 持久磁碟；session 僅記憶體 | FD／NFR |
| Environments | 本機 dev／CI test／staging deploy 三分離 | env contract |
| IaC approach | **不**用 Terraform 部署本 API；產品產出的 HCL 不 apply | 範圍邊界 |
| Sizing | 單 replica；generate ≤2 in-flight／進程 | NFR bulkhead |
| Checkov | **釘版安裝於 backend image** | Q1=A |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| PostgreSQL | database（既有） | 既有 staging DB；本 unit **不**新增表除非後續 ADR | Session 不落 DB |
| OpenRouter／LLM | 外部 API | 金鑰經 env／`render-env.sh` | Q2=A；不入映像 |
| Checkov CLI | 掃描工具 | 映像內 PATH；版本釘選 | 缺則 D2 失敗 |
| Redis／Queue／CDN | — | **不部署** | NFR 明確不做 |

## Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| staging compose／nginx／Tunnel | 平台（既有） | u1-iac-api、u2-iac-ui | HTTP `/api/iac`；同源前端 |
| JWT／RBAC | 既有 auth | u1 | `require_story_action` |
| LLM API key env | 平台 env | u1 Generator | 僅後端進程 |

<!-- confirmed: Looks correct -->
