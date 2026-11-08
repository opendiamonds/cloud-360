# Logical Components — u2-iac-ui

> Q4=A。

## 元件

| 元件 | 職責 |
|---|---|
| **IacWorkspacePage** | 路由殼、步驟狀態、切圖協調、busy |
| **IacApiClient** | `/api/iac` 呼叫、Abort、error.code 正規化；MSW 可替換 |
| **IacStepPanels** | Generate／Scan／Secrets 面板與 test-id |
| **IacDownloadConfirmModal** | HIGH／CRITICAL 確認；a11y dialog |

## 依賴

```text
Page → ApiClient → (/api/iac | MSW)
Page → StepPanels
Page → DownloadConfirmModal
```

## 失敗域

- ApiClient 失敗：面板顯示錯誤；不污染其他步驟草稿檢視（保留先前成功預覽）。
- Modal 僅擋下載確認；不擋步驟切換（除 busy 規則）。

## 與 U1

- 不嵌入 SessionStore／Checkov；只經 HTTP 契約。

<!-- confirmed: Looks correct -->
