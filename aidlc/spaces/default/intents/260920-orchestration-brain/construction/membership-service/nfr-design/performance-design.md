# 效能設計 — `U19 membership-service`

> 本站設計上游 `nfr-requirements` 的 **29 條 `NFR12.x`** 的承載形式。
> 本站**不複寫** `functional-design` 的 29 條 `BR` 規則（`team.md` 的單一真實來源）。
>
> `U19` 是 `service`，故六份設計產出全部適用（`U5`／`U18` 只有 `security-design`）。


## 〇、兩條查詢路徑的具體形狀

本站把 `NFR12.8`–`NFR12.12` 的目標落為查詢形狀。**本單元零新進程**，
故沒有連線池、快取層或非同步化的設計面。

## 一、`resolveProjectRole`：一次索引查詢（`NFR12.8`／`NFR12.9`）

```
WHERE project_id = ? AND user_id = ?     -- 回該列的 role，或無列時回 None
```

覆蓋者是 `U18` 已交付的 `uq_project_members_project_user`（以 `project_id` 為前導欄的
btree 唯一索引）。**本站不新增索引**——`U18` 的 `security-design.md §四之一` 已逐項
列出已覆蓋的查詢，而這一條在其中。

**`NFR12.9`（不加快取）的設計後果，寫明以免被讀成待辦**：
本單元**刻意不設計**任何快取層、失效策略或 TTL。它不是省略，是
`performance-requirements.md §一` 的決定：快取授權結論會引入「權限已撤銷但快取未失效」
的窗口，而撤銷正是本單元的核心功能。

## 二、`assertCanDeactivate`：聚合查詢（`NFR12.10`–`NFR12.12`）

```
-- 找出「該使用者是最後一位管理者」的全部專案
SELECT project_id
FROM project_members
WHERE project_id IN (該使用者具 project_admin 的專案)
  AND role = 'project_admin'
GROUP BY project_id
HAVING count(*) = 1
```

**一次查詢，與該使用者的專案數無關**。

### 2.1 它與單專案判定函式的關係（`NFR12.11`，回應審查 `R-03`）

| 層 | 形狀 | 誰用 |
|---|---|---|
| 單專案判定 | `admin_count_after(projectId, 假設的變更) >= 1` | `removeMember`／`changeRole` |
| 集合版 | 上面的 `HAVING count(*) = 1` | `assertCanDeactivate` |

**不變量只有一個；集合版是單專案判定的量化形式。** `NFR12.12` 的等價測試
（對隨機成員集合比對兩者結果）是讓這句話可被驗證而非只是宣稱——
**這是對審查 `R-03` 的直接回應**，該發現指出三條路徑在文件上沒有證明共用同一判定。

### 2.2 本站查出的一件事：這個查詢的索引覆蓋**不完整**

該查詢以 `role = 'project_admin'` 過濾，而 `U18` 交付的索引是
`(project_id, user_id)` 的唯一索引——**沒有任何索引含 `role`**。
故 `HAVING` 之前的過濾需要讀出該專案的全部成員列再過濾 role。

| 情境 | 影響 |
|---|---|
| 每專案成員數小（本系統的實際情境） | 可忽略——讀幾列再過濾 |
| 每專案成員數大 | 線性於成員數 |

**本站的設計決定：不加索引。** 理由是 `U18` 的
`security-design.md §四之三` 已立下同形判準——「不需要的索引有寫入成本，
而『以後可能要』不是現在建的依據」，而每專案成員數受人工邀請速度限制。
**但把它寫下來**，因為下一個人看到這個查詢會想加 `(project_id, role)`，
而那個決定需要競爭資料支撐。記為 `OPEN-ND19-3`。

## 三、刻意不設計的（附理由）

| 不設計 | 理由 |
|---|---|
| 快取層／失效策略 | `NFR12.9`：正確性優先於延遲（見 §一） |
| 連線池調整 | 零新進程；沿用既有 `SessionLocal` |
| 非同步化 | 本單元的操作都是使用者等待結果的同步動作（邀請、改角色、停用） |
| 鎖等待逾時 | `NFR12.1` 的鎖只序列化同一專案，而同一專案的並行管理動作罕見。設一個逾時值需要競爭資料 |
