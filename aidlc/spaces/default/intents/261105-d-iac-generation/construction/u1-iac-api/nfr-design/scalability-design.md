# Scalability Design — u1-iac-api

> Q3=A · NFR-SCALE-1.1–1.3。

## 單進程模型

- 水平擴展**非**本輪目標；無 sticky session 叢集假設。
- Store＝進程單例；多 worker 部署＝多孤立記憶體（文件化預期）。

## 槽位與 LRU（Q3=A）

| 規則 | 行為 |
|---|---|
| 每 user ≤3 `diagram_id` | 第 4 個活躍存取 → 淘汰 **LRU** 槽（讀寫皆更新 recency） |
| 每槽 ≤16 MiB | 超過拒絕寫入；不截斷密文殘留 |
| 同槽寫入 | 單一 in-flight POST；其餘拒絕／忽略後寫（與 U2 busy 對齊） |

## 降級

1. 拒超大 payload  
2. LRU 淘汰  
3. **不**溢寫磁碟密文暫存

<!-- confirmed: Looks correct -->
