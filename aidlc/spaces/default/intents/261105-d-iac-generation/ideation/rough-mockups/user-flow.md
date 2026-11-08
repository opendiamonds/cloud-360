# User Flow — IaC Generation (Rough)

## Happy Path

依 scope：D1 → D2 → D3；平台不代 apply。[Q2][scope]

```text
[Workspace]
    |
    v
[點「生成 IaC」] ---- Coming Soon 改為進入 IaC 工作區
    |
    v
[選架構圖／脈絡] ---- 既有圖資產
    |
    v
[D1 agent 生成] ---- 顯示進度（對齊 A／C agent 語彙）
    |
    v
[檢視草稿] <---+ 檔案樹 + HCL 主區
    |          |
    |     [下載／複製]
    v
[D2 agent 掃描] ---- findings 列表（次欄／步驟）
    |
    v
[D3 secrets 提示] ---- 去明文／SM 引用提示（不代寫 production secret）
    |
    v
[結束] ---- 使用者帶走草稿；不 apply
```

[Q2][Q3]

## Alternate / Edge Paths

| Path | Behavior |
|---|---|
| 無可用架構圖 | 阻擋生成，提示先完成／開啟圖面 [Q1] |
| D1 失敗 | 錯誤狀態＋重試；不進 D2 [Q2] |
| 跳過 D2／D3 | Must 範圍不鼓勵跳過；若 UI 提供略過需在 requirements 再定 [scope Must] |
| 權限不足 | RBAC 拒絕；對齊既有 Workspace 錯誤樣式 [scope] |

## Alignment with A／C

流程殼層（側欄、agent 進度、結果面板）與 Design／Assessment／成本工作區同一套互動語彙。[Q4][intent]
