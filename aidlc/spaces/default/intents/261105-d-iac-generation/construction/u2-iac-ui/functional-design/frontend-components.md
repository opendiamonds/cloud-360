# Frontend Components — U2 `u2-iac-ui`

> Q1=A：落在 Workspace 路由內；對齊 refined-mockups test-id。  
> 名稱為設計錨點；code-gen 可微調檔名，勿只改文案丟掉 test-id。

## 層級

```
WorkspaceShell
└── IacEntryControl (iac-entry)
└── IacWorkspacePage
    ├── IacStepNav (iac-step-*)
    ├── IacDraftPane (iac-file-tree, iac-hcl-preview)
    ├── IacAside
    │   ├── IacDiagramPicker (iac-diagram-select, iac-diagram-upload)
    │   ├── IacAgentStatus (iac-agent-status)
    │   ├── IacFindingsPanel (iac-findings)          // scan
    │   └── IacRewritePanel (iac-rewrite-list)       // secrets
    ├── IacStepActions (iac-run-d1|d2|d3, busy)
    ├── IacFooterNav (prev/next 僅導覽)
    ├── IacDownloadBar (iac-download, iac-copy)
    └── IacDownloadConfirmModal (iac-download-confirm)
```

## 元件表

| 元件 | 職責 | data-testid／錨點 | 主要 props／state |
|---|---|---|---|
| `IacEntryControl` | Workspace「生成 IaC」；無權 disabled＋說明 | `iac-entry` | `canViewD1`, `missingPermissionHint` |
| `IacWorkspacePage` | 三欄殼與步驟狀態機 | — | `activeStep`, `diagramId`, `busy` |
| `IacStepNav` | 左步驟；可自由點 | `iac-step-generate`／`scan`／`secrets` | `activeStep`, `onSelect` |
| `IacDiagramPicker` | 活躍圖／下拉／上傳 | `iac-diagram-select`／`upload` | `diagramId`, `onChange`, `onUploadFail` |
| `IacDraftPane` | 檔案樹＋HCL 預覽 | `iac-file-tree`／`iac-hcl-preview` | `moduleTree`, `selectedPath` |
| `IacAgentStatus` | 進行中／錯誤文案 | `iac-agent-status` | `phaseText`; `aria-live=polite` |
| `IacStepActions` | 各步執行主鈕；busy 防重送 | `iac-run-d1`／`d2`／`d3` | `disabledReason`, `busy`, `onRun` |
| `IacFindingsPanel` | findings 嚴重度文字 | `iac-findings` | `findings[]` |
| `IacRewritePanel` | 改寫清單／無可改寫 | `iac-rewrite-list` | `rewrittenPaths[]` |
| `IacFooterNav` | 上一步／下一步僅導覽 | — | `onPrev`, `onNext` |
| `IacDownloadBar` | 下載／複製 | `iac-download`／`iac-copy` | `canDownload`, `onDownload`, `onCopy` |
| `IacDownloadConfirmModal` | HIGH／CRITICAL 摘要 | `iac-download-confirm` | `counts`, `onConfirm`, `onCancel`（Esc） |

## 互動要點

| 情境 | 行為 |
|---|---|
| 切圖 | 先可見提示 → 清空本機草稿／報告檢視；abort／忽略 in-flight（Q2） |
| API 422 | 以 `error.code` 對照文案表（Q3） |
| 403 | 缺權說明（story＋action） |
| 平行 stub | MSW 回契約 JSON／zip；test-id 不變（Q4） |
| 無 apply | 元件樹不得出現 apply／destroy |

## API 對應

| UI 動作 | HTTP |
|---|---|
| 執行 D1／D2／D3 | POST `/api/iac/generate`／`scan`／`secrets/rewrite`（皆帶 `diagram_id`） |
| 刷新殼 | GET `/api/iac/session?diagram_id=` |
| 下載 | GET `/api/iac/download?diagram_id=`（modal 之後） |
