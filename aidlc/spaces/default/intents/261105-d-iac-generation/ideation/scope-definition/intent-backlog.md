# Intent Backlog (Proto-Units)

優先序依 dependency-first；MoSCoW 見 `scope-document.md`。[Q4][Q2]

## Proto-Unit Board

| ID | Proto-Unit | MoSCoW | Depends on | Notes |
|---|---|---|---|---|
| PU-D0 | Workspace IaC 入口＋RBAC／OpenAPI 接線（對齊 A／C layout） | Must | — | 可與 D1 並行 [Q3] |
| PU-D1 | D1 agent：架構圖 → Terraform／OpenTofu 草稿（可下載／可檢視） | Must | PU-D0（UI／權限） | 一 agent [Q1][Q2] |
| PU-D2 | D2 agent：草稿靜態掃描＋結果呈現；預設引擎＋可配置（Should） | Must（可配置為 Should） | PU-D1 | 一 agent；整合既有 CLI [Q2][Q3] |
| PU-D3 | D3 agent：Secret Manager 引用／去明文 | Must | PU-D2（建議在掃描後收斂 secrets） | 一 agent；成功形狀待 requirements [Q1][Q3] |
| PU-DX | 多掃描引擎 | Could | PU-D2 | 非本 intent 阻塞 [Q2] |

## Suggested Delivery Sequence

1. PU-D0＋PU-D1（並行起 UI／權限與生成）  
2. PU-D2  
3. PU-D3  
4. PU-DX（若有餘力）

[Q3][Q4]

## Explicit Non-Goals (backlog)

不建立代 apply、production 憑證管線、商業 IaC 平台嵌入、自研掃描引擎之 proto-unit。[Q6]

## Deadline

無能力綁定硬性 deadline。[Q5]
