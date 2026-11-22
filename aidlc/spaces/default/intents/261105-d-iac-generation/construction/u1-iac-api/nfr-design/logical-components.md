# Logical Components — u1-iac-api

> Q5=A · 橋接 Infrastructure Design／code-gen。

## 元件清單

| 元件 | 職責 | 失敗域 |
|---|---|---|
| **IacRouter** | FastAPI 路由、RBAC、驗證、request_id | 薄；委派下列 |
| **IacSessionStore** | `(user, diagram)` 槽、LRU、體積、in-flight 鎖 | 進程記憶體；重啟即失 |
| **IacGenerator** | 圖→HCL；LLM port；90s／≤2 併發 | 慢失敗；不堵短路徑 |
| **IacScanner** | 呼叫 Checkov；映射 findings | CLI／超時失敗 |
| **IacRedactor** | 密文改寫純函式＋結果摘要 | CPU；無出站 |

## 依賴

```text
Router → Store
Router → Generator → (LLM Port)
Router → Scanner → (Checkov Port)
Router → Redactor
Generator／Scanner／Redactor → Store（讀寫槽產物）
```

## Blast radius

- Generator 掛死／慢：僅占满 generate 信號量；session／download 仍可用。
- Store 損壞／重啟：該進程所有使用者槽清空。
- Checkov 不可用：僅 D2 失敗；D1／D3／download（既有草稿）不受阻（D3 仍需成功 scan 報告——依 FD 閘）。

## 共享資源

- 進程內 Store 單例；Checkov 可執行檔路徑；LLM API 金鑰（既有 env，不入 log）。

<!-- confirmed: Looks correct -->
