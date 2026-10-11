# 效能設計 — `U8 memory-service`

> `[N1]`=A（修訂後）把量測邊界定為「取得查詢向量之後 → 回傳」，
> 故本檔設計的是**那一段**：一次 SQL、兩道過濾、一次排序。

## 〇、上游依據

| 上游 | 本檔用到它的什麼 |
|---|---|
| `nfr-requirements/performance-requirements.md` | `NFR3.20`–`NFR3.24` 與 `[N1]`=A 的修訂、`[N2]`=B 的 HNSW 決定、`N8-12` 的判準前提 |
| `functional-design/functional-spec.md` | §1.2 檢索的七個步驟、§1.3 列出路徑不做相似度 |
| `functional-design/rules.md` | `BR2.2`（可見範圍）、`BR3.1`（三種皆可取）、`BR3.2`（模型分群）、`BR3.3`（無向量） |
| `nfr-requirements/tech-stack-decisions.md` | 四層形狀；純函式層是 `NFR3.24` 的結構前提 |

## 一、檢索的查詢設計：一次 SQL，不是三次

**兩道過濾與排序必須在同一個查詢內**，理由是正確性而非效能：

| 做法 | 後果 |
|---|---|
| **單一 SQL（採用）**：`WHERE` 含可見範圍 ＋ `embeddingModel`，`ORDER BY` 距離，`LIMIT n` | `LIMIT` 作用在**已過濾**的集合上，故回傳筆數正確，且索引可被用於排序 |
| 先查再於應用層過濾 | `LIMIT n` 在過濾前取 n 筆，過濾後可能剩不足 n——**檢索筆數錯**，且不可見的列會先進入進程（洩漏面擴大） |

**過濾順序在 SQL 內由 planner 決定**，設計上只要求兩者都在 `WHERE` 內。
`functional-spec.md §1.2` 的步 3→步 4 順序描述的是**語意**（可見範圍是候選集合的
構成條件，不是排序權重），不是對 SQL 子句順序的要求。

## 二、`[N2]`=B 的索引設計

| 項目 | 設計 |
|---|---|
| 型態 | HNSW（空表可建；ivfflat 的 `lists` 需先有資料） |
| 落點 | `schema_rbac.sql` 的 `I)` 區塊 |
| opclass | **必須與查詢的距離運算子一致**；本站不預選運算子，但要求兩者同一個 PR 內一致（`N8-4`） |
| 連帶 blocking | 四項：`schema_rbac.sql`／`DEPLOY.md`／`run_meta_schema_migration.py` 的 `EXPECTED_INDEXES`／`verify_memory_schema.sql` 的新 `S` 斷言 |

### 2.1 `NFR3.22` 的斷言設計（承 `N8-12`）

planner 是 cost-based 的，在小表上幾乎必定選 `Seq Scan` **即使索引完全正確**。
故斷言設計採**隔離單一變數**的做法：

| 步 | 動作 |
|---|---|
| 1 | `SET enable_seqscan = off` |
| 2 | 對代表性查詢取 `EXPLAIN` |
| 3 | 斷言計畫中出現該 HNSW 索引的掃描節點 |

**為什麼選這個而非灌大量 fixture**：它直接驗證 `NFR3.22` 真正要防的事
——**opclass 不符導致索引不可用**。若 opclass 不符，即使關掉 seqscan，
planner 仍無法使用該索引，斷言就會失敗。灌 fixture 則同時驗了
「planner 會不會選它」，那是另一個問題且需要數百至數千列。

**兩者不互斥**：若日後要驗 planner 的選擇傾向，另加一條帶 fixture 的測試。

## 三、`NFR3.20`（150ms）的預算分解

| 組成 | 設計上的處置 |
|---|---|
| SQL 往返 | 同一 compose 網路，約 1ms（沿用 `NFR3` 原文對 Redis 的同類估計） |
| 兩道過濾 | 可見範圍走 `ix_memory_records_owner_user_id`；`embeddingModel` 走 `ix_memory_records_embedding_model`（兩者皆既有） |
| 距離計算與排序 | 走新增的 HNSW 索引 |
| 純函式次級排序 | `memory_ranking.py`，無 I/O |
| **不含** | 向量產生（`[N1]`=A 已切出，屬 `U6`／`N8-11`） |

**150ms 仍是工程判斷而非實測**，故 `NFR3.21` 的實測要求保留
（須記錄 `memory_records` 列數）。本站不調整數字。

## 四、快取：刻意不加

| 理由 | 說明 |
|---|---|
| 正確性風險 | 記憶讀取按呼叫者過濾（`BR2.2`），快取鍵必須含 principal；漏掉 principal 即跨使用者洩漏，而那個錯誤在功能上看不出來 |
| 收益不明 | 本單元無既有流量基準，無法判斷命中率 |
| `NFR8.20` | 新快取層（Redis 鍵空間或行程內容器）會引入部署設定或行程內狀態，後者直接違反 `NFR4.20` |

**若日後要加**，前提是先有 `NFR3.21` 的實測顯示瓶頸在重複查詢。

## 五、非同步：不適用

本單元的全部操作都是請求範圍內完成的同步操作。
`write` 雖然要等 `U6` 產生向量，但**那是呼叫端等待的一部分**，
不是可以背景化的工作——背景化會讓「寫入成功」在記憶還不可檢索時就回傳，
而使用者隨即在記憶頁看不到剛寫的那一筆。
