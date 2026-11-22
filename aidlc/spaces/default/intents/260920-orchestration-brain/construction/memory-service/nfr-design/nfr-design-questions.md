# NFR Design 問題檔 — `U8 memory-service`

> `service` kind，七份產出全部適用。本站把 `nfr-requirements` 的 27 條 `NFRx.y`
> 轉成具體設計。
>
> **本站只問一題**：刪除路徑的記憶枚舉 oracle。其餘設計面已由上游鎖定或由
> repo 既有先例決定（見 §〇）。

## 〇、不重問的事

| 事項 | 依據 |
|---|---|
| 四層形狀（router → facade → service → 純函式） ＋ facade 為 `sole_entry` | `tech-stack-decisions.md §三`；`K-08` |
| 兩套授權模型的分工（擁有者 vs 角色） | `security-requirements.md §五`；`BR2`／`BR4` vs `BR5`／`BR6` |
| 不加快取、不加 retry、不加 circuit breaker | `scalability-requirements.md §三`；`reliability-requirements.md §三` |
| 分頁採 offset／limit | repo 既有先例 `/api/auth/list`（含 `total`），照既有形狀不自創 |
| HNSW 索引與其 opclass 一致性斷言 | `[N2]`=B；`NFR3.22` ＋ `N8-12` 的判準前提 |
| `search` 本體 P95 ≤ 150ms、不含向量產生 | `[N1]`=A（修訂後） |
| 無 SLO（repo 無 metrics 承載機制） | `observability-requirements.md §二` |
| AWS Well-Architected 的服務選擇面 | **不適用**：本 repo 為自架單主機 compose（ADR-0007），無 AWS 資源。六大支柱作為檢查結構仍有用，服務選擇不適用 |

---

## 一、`[D1]` 刪除路徑的記憶枚舉 oracle 要不要關？

### 查證到的事實（比 `nfr-requirements` 當時的描述更嚴重）

`functional-spec.md §1.4`（刪除）的順序是**先取記憶、後判擁有者**：

| 步 | 動作 | 回應 |
|---|---|---|
| 2 | 取記憶 M；不存在 | `MemoryNotFound` → **404** |
| 3 | `M.ownerUserId` ≠ 呼叫者 | `MemoryForbidden(reason="owner")` → **403** |

對照 §1.5（放寬可見範圍）**刻意**先判角色再取記憶，且該站寫明理由
就是避免存在性 oracle。**刪除路徑做了相反的事。**

**而 id 是可枚舉的**：

| 查證項 | 結果 |
|---|---|
| `memory_records` 的主鍵（`schema_rbac.sql:453`） | `id SERIAL PRIMARY KEY`——**連續整數** |
| `K-08` 的 `delete` 宣告 | `raises: [MemoryForbidden, MemoryNotFound]`；HTTP 半邊宣告 `403` 與 `404` |

**後果**：任何已認證使用者可對 `DELETE /api/memory/records/{id}` 走訪
`1..N`，以 403／404 的差異取得**全表哪些 id 存在**——
亦即其他使用者的記憶總量與分布。
這不是「某個 id 是否存在」的單點洩漏（我在 `nfr-requirements` 當時的描述），
**是整張表的枚舉**。STRIDE 分類為 Information Disclosure。

**它不會刪到別人的資料**（`BR4.1` 的擁有者判定仍然有效），洩漏的是後設資料。

### 選項

| 選項 | 做法 | 代價與後果 |
|---|---|---|
| **A（建議）** | **刪除路徑把兩種失敗收斂為同一個回應（`404`）**：非擁有者與不存在皆回 404。facade 內部仍可區分（稽核與日誌用 `reason`），只有對外的 HTTP 狀態碼收斂 | oracle 關閉——枚舉者無法區分「不存在」與「別人的」。代價：**偏離 `K-08` 宣告的 `403`**（契約的 HTTP 半邊列了 403／404 兩者），需在下一輪契約修訂追認；且擁有者誤刪已刪除的記憶時仍得 404（行為不變）。**`NFR7.24` 的判準要跟著改**（原為「他人 → 403」） |
| **B** | **維持 `K-08` 原樣（403／404 分離）**，把 oracle 記為已接受的風險 | 零契約偏離、零文件連動。代價：枚舉 oracle 留著，而它**現在就可被任何已認證使用者利用**；且本單元兩條路徑（刪除 vs 放寬）對同一個威脅採相反處置，而那個不一致已被 `functional-design` 的審查以 Major 指出 |
| **C** | 維持分離，另加速率限制 | 減緩枚舉速度但不關閉它。且 repo **沒有任何速率限制基礎設施**（新機制、新依賴），而 `NFR8.20` 要求本單元零新部署設定 |

[Answer]: A 收斂為同一回應（404）
<!-- **寫回時間 2026-10-09T09:01:50Z（以 `date -u` 取值），晚於實際作答。** 這是我的疏失，
     如實記載而非偽裝成同時發生：裁決在本 session 內由使用者以選單作答取得
     （選項 A「收斂為同一回應(404)」），但我當時直接去寫產出，**沒有在同一個
     動作內寫回本檔**——違反 `project.md` 的 `user-stories:260822-us-L2`
     （「人工裁決一取得，就在同一個動作內寫回問題檔」）。
     本缺口由本站審查以 `R-01`（Critical）查出：`[Answer]` 欄位為空白，
     且 audit shard 內無對應事件，使一處對已核可契約 `K-08` 的安全相關偏離
     在紀錄上無法被證實。
     作答內容未被改寫——它就是使用者選的那一項；被補的是紀錄，不是決定。 -->
