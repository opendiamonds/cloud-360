# Risk and Sequencing Rationale — 為何是這兩條 Bolt

> Stage: delivery-planning（Inception 2.8）· Intent: `260819-cost-finops`
> 上游：`requirements.md`、`stories.md`、`mockups.md`、`components.md`、`unit-of-work.md`、`unit-of-work-dependency.md`、`unit-of-work-story-map.md`、`team-practices.md`。

## 啟發法

**不使用正式 WSJF 表**（Q2=A）。候選有意義的部署只有兩個，分數不會翻轉排序。

實際採用的混合：

| Bolt | 啟發法 | 一句話 |
|---|---|---|
| B1 | value-first + risk-reduction | 故事第一段可單獨上線；同時把種子 no-op、擷取、pricing Port 放到使用者碰得到的第一次部署 |
| B2 | value-first（第二段 Must） | 預算／橫幅依賴已存在的總額（`stories.md`：C1-6 → C1-7 建在 C1-2 上） |

**不是** walking-skeleton-first 儀式：`team.md` 已對本 intent 定 `skeleton: off`。B1 雖然打通新 bounded context 的表／library／HTTP／頁，但仍標為普通 Construction Bolt（無額外 skeleton gate）。mvp scope 檔的 `skeleton: on` 不覆寫這次人工定案。

## 為何不走其他合法拓樸

DAG 允許先單獨合 `cost-schema-rbac` 或 `cost-calculator`。那些路徑**拓樸合法、經濟不合法**：

| 被拒路徑 | 擋下規則 |
|---|---|
| 五個 merge（一 unit 一 Bolt） | `delivery-planning:c3` 無畫面假說；`delivery-planning:c6` api／ui 分批 |
| 單一 Bolt 包五 unit | `stories.md` 第一段可單獨上線；第二段缺陷會擋住第一段 |
| B2 與 B1 平行 | yaml 邊 `cost-budget-banner` depends_on api+ui；ADR-C1-08 禁止第一段掛橫幅 |
| 先合 calculator PBT 再做頁 | 風險確實高，但 PBT 綠燈對 Alex 不可見，仍須捆進 B1 |

**無拓樸偏離**：B1 的四 unit 在同一部署內，邊的方向仍是 ui→api→{schema,calculator}。B2 在 B1 之後。不需要「偏離理由」，只需要「在多條合法序中選捆綁」的理由（本節）。

## 最早要打掉的風險（Q5=A）

| 風險 | 為何最早 | 落在 |
|---|---|---|
| `ensure_role_permissions_seeded(force=False)` 全表 no-op | staging 已有列時新 `C1h` 等永不出現，403 測試在空表 CI 仍綠 | B1 `cost-schema-rbac` |
| extractor 誤用 `parse_diagram_summary` | 列集合對錯圖，C1-1 全部 AC 假綠 | B1 `cost-api` |
| 未設區域仍打價目 URL | 違反 FR-4／AC-1.8 | B1 `cost-api` |
| 第一段誤掛橫幅 DOM | AC-1.16 失敗；第二段無法當增量 | B1 `cost-ui` 負向 |

公開價目 HTTP 失敗**不是** B1 的完成閘：Port 三分 Hit／Miss／Unsupported + stub 已覆蓋契約。真實 URL 是 infra-design 的 OQ-3，失敗時列 `price_fetch_failed`。

## 規模直覺（非正式 WSJF）

| Bolt | 相對規模 | 使用者價值 | 風險降低 |
|---|---|---|---|
| B1 | L（四 unit） | 高（入口＋總額＋時數＋覆寫） | 高（種子／擷取／Port） |
| B2 | M（一 unit） | 高（超支雙方可見）但依賴總額已存在 | 中（橫幅掛載） |

排序 B1 再 B2 與故事增量一致，無需打分表。
