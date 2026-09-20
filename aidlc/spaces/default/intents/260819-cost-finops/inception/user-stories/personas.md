# Personas — 成本估算與 FinOps（C1 第一輪）

<!-- Stage: user-stories（Inception 2.4）· 角色名與 RBAC 沿用 baseline `260802-default` 的 Alex／David／Hannah。
     本檔只寫本 intent 的三個受益者；不複製 baseline 其餘 persona（Ben、Catherine…）。
     C2／C3 痛點（Spot／RI、Egress 熱點）本輪不寫進目標。 -->

## 上游輸入

- **requirements**（`../requirements-analysis/requirements.md`）
- **business-overview**（`aidlc/spaces/default/codekb/cloud/business-overview.md`）
- **baseline personas**（`aidlc/spaces/default/intents/260802-default/inception/user-stories/personas.md`）
- **Q1=A**：三人皆完整 persona；無 C1 view 者看不到入口

## 優先序

| 順位 | Persona | RBAC | 本輪 C1 主要動作 |
|---|---|---|---|
| 1 | Alex | `Project_Architect` | 看估價、改每日時數與估價區域、從產圖 CTA 進入 |
| 2 | David | `FinOps_Analyst` | 指定 SKU／覆寫單價、設預算、看超支 |
| 3 | Hannah | `Project_Editor` | 設預算、看超支橫幅；不改時數、不覆寫單價 |

無 C1 `view` 的角色：Sidebar 無「成本」組；開成本頁看到既有 Forbidden（`/403`）；`/api/cost*` 無權回 HTTP 403。本輪不為其發明利益。

---

## P-1 Alex — 雲端架構師

- **情境**：要向利害關係人說明「這張圖一個月大概多少錢」，且數字必須對到圖上的機器，不能是另一份試算表。
- **職責**：設計並迭代架構圖；設定該圖的估價區域與每日時數。
- **本輪在意**：C1 第一段（擷取、官方價或未定價、圓餅、總額、入口）；第二段超支時也是橫幅收件人。
- **核心目標**：產圖後幾分鐘內拿到可對外說明的每月 USD list-price 估價。
- **核心痛點**：報價對不到圖上資源；區域與時數假設不清楚時，同一張圖會算出兩套數。
- **使用場景**：Workspace 產圖成功卡點「查看預估成本」；Sidebar「成本 → 預估成本」選圖；登入後任一受保護頁看到超支橫幅。
- **不做**：覆寫單價、設預算（403）。

## P-2 David — FinOps 分析師

- **情境**：架構師丟來一張圖要估價。公開價目對不到或 API 失敗時，他必須能補上 SKU 或小時 list price，並標 Manual Override，而不是去開 Cost Explorer。
- **職責**：維護可報價狀態、設每圖月預算、查看超支。
- **本輪在意**：C1 單價路徑與第二段預算。
- **核心目標**：每一列要麼有可追溯的官方價，要麼有他簽過名的覆寫；超支時他一進產品就看得到。
- **核心痛點**：缺價被當成 0；覆寫沒有稽核；預算被架構師改掉。
- **使用場景**：成本頁補 SKU／覆寫單價；寫入每月預算。
- **不做**：改每日時數、改估價區域（403）。本輪不做 Spot／RI（C2）與 Egress 熱點（C3）。

## P-3 Hannah — 工程主管

- **情境**：團隊在圖上加機器時，她要知道會不會把該圖的月預算撐破；超支時不能靠有人轉寄 inbox。
- **職責**：與 David 共同設每圖月預算；看成本畫面與進產品橫幅。
- **本輪在意**：C1 第二段預算與超支可見性。
- **核心目標**：預算變更可稽核；超支期間每次進入受保護頁都看到橫幅。
- **核心痛點**：加機器當下沒有預算訊號；警告可以被關掉後再也看不見。
- **使用場景**：成本頁改預算；登入後任一受保護頁看到超支橫幅。
- **不做**：改時數、改估價區域、覆寫單價（403）。
