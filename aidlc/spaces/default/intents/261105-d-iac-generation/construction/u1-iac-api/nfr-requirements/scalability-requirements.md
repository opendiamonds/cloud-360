# Scalability Requirements — u1-iac-api

> Unit: `u1-iac-api`（service）· Q4=A · 單進程 staging（Q5=A）。

## 容量模型

| ID | 維度 | 目標 | 機制 |
|---|---|---|---|
| NFR-SCALE-1.1 | 每 user 活躍 `diagram_id` 槽 | **≤ 3** | 超出淘汰最舊槽（FIFO／LRU 擇一，code-gen 釘死並測） |
| NFR-SCALE-1.2 | 每槽草稿＋報告合計 | **≤ 16 MiB** | 超出 → 422／明確碼；不靜默截斷 |
| NFR-SCALE-1.3 | 同槽寫入併發 | **1 in-flight** POST | 其餘拒絕或忽略後寫（對齊切圖／busy 語意；與 U2 約定一致） |

## 成長預期

- 本輪受眾：內部 staging／演示；**不**承諾多租戶水平擴展。
- 水平擴展前置：須先改掉 in-memory（見 reliability Q5）；本 NFR **不**假設 sticky session 叢集。

## 降級順序（逼近上限時）

1. 拒絕新槽／超大 payload（明確錯誤）。
2. 淘汰最舊槽。
3. **不**為省記憶體而寫入磁碟或外洩密文到 swap 檔（禁止自管臨時檔含明文 secret）。

## 不做

- 不定「無限併發使用者」。
- 本輪不引入 Redis／共享 session 店（除非未來 intent＋改 FD）。

<!-- confirmed: Looks correct -->
