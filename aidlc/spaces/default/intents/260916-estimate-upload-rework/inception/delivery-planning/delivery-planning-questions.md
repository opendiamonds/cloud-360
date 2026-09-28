# Delivery Planning 問答：C1 估價表上傳

本站選**經濟路徑**：在 units 的 DAG 上決定 Bolt 順序與打包。Bolt＝一次 Construction 建置切片（可含一個或多個 Unit），結束時要有可驗證的完成定義。

## Sources

- **[S1]** 九單元 DAG：根集合 `{U1,U3,U4,U6}`；U2←U1；U5←U4；U7←{U6,U2}；U8←U2；U9←{U8,U7}。U7 **不**依賴 U5。
- **[S2]** 同批部署：U3＋U8；FR9.8 建議 U3＋U4 同批或 U4 先行；U2↔U3 router 衝突宜同 Bolt。
- **[S3]** ideation value-first（SD-7）：先上傳與明細、建議後補；窗口期「有明細沒建議」要主動壓縮。
- **[S4]** AH-2：兩人以上可平行；team-formation SKIP → mob 預設 `aidlc-developer-agent`。
- **[S5]** scope `skeleton: off`；org 預設 deploy-on-merge、`ut` squash。
- **[S6]** requirements OQ2：PU-13 分享是 Must 但不在 value-first 核心路徑——本站裁決。

---

## Q1 排序啟發式

- **A.** Value-first（對齊 SD-7）：儘早讓使用者看到上傳＋明細；建議路徑緊接其後壓縮窗口
- **B.** Risk-first：先 LangGraph 骨架（U6）與憑證／repo contract（U4），再做可見功能
- **C.** 混合：第一個 Bolt 用最薄端到端（解析→上傳→一頁明細）證明管線；其餘 value-first
- **D.** WSJF 正式打分後排序
- **X.** Other (please specify)

[Answer]: A — Value-first：儘早上傳＋明細；建議緊接其後壓縮窗口

---

## Q2 Bolt 粒度

- **A.** 多數 Bolt＝1 Unit；僅強制同批者捆綁（U3＋U8；必要時 U2＋U3）
- **B.** 較粗：相關 Unit 捆成 4–5 個 Bolt（例如「解析＋API」「退場＋明細 UI」「建議後端＋建議 UI」）
- **C.** 更細：Unit 內再切薄片（本站不建議——DAG 已是 Unit 級）
- **X.** Other (please specify)

[Answer]: A — 多數 Bolt＝1 Unit；僅強制同批捆綁（U3＋U8）

---

## Q3 平行度

- **A.** 根集合與無相依 Bolt 盡量雙人平行（對齊 AH-2）
- **B.** 全程串行（單人主做）
- **C.** 僅前兩個 Bolt 平行，其後串行
- **X.** Other (please specify)

[Answer]: A — 根集合與無相依 Bolt 盡量雙人平行

---

## Q4 分享（U2 內 FR6.6）與歷史（U8 內 FR6.3）何時算「完成」

分享是 Must，但不在「先看到東西」的最短路徑上。

- **A.** 與明細同 Bolt 交付（U2／U8 的 DoD 含分享＋歷史）—— Must 不拖延
- **B.** 明細 Bolt 先上（無分享也可看自己的表）；下一 Bolt 補分享／歷史完善
- **C.** 分享延到建議路徑之後的獨立 Bolt
- **X.** Other (please specify)

[Answer]: A — 分享與歷史納入明細同 Bolt 的 DoD（Must 不拖延）

---

## Q5 最擔心哪件事（決定是否提前插入去風險 Bolt）

- **A.** LangGraph＋OpenRouter 接不通或太慢
- **B.** 三雲解析格式／靜默錯欄
- **C.** U3＋U8 同批部署與 OpenAPI／e2e 一次改爆
- **D.** 憑證管線／repo contract（FR11.2）改壞 CI
- **X.** Other (please specify)

[Answer]: A — 最擔心 LangGraph＋OpenRouter → U6 與價值路徑根集合平行起跑去風險

---

## Q6 查價 Port（U5）放哪

U7 不依賴 U5；可後掛。

- **A.** 建議路徑完成後的獨立 Bolt（Should，不擋 Must）
- **B.** 與 U7 同一 Bolt（建議一上線就能查價）
- **C.** 與 U4 捆成「憑證＋查價」Bolt，仍在建議之前或平行
- **X.** Other (please specify)

[Answer]: A — U5 在建議路徑完成後的獨立 Bolt

---

## Consolidated Summary Confirmation

**啟發式**：Value-first（Q1=A），但因 Q5=A，**U6 LangGraph 與 U1／U4 平行起跑**——這不是改成 risk-first，而是在價值路徑旁加一條去風險軌（寫入 risk-and-sequencing-rationale）。

**Bolt 序列（草案）**

| Bolt | Units | 平行 | DoD 要點 | 信心假設 |
|---|---|---|---|---|
| B1 | U1 `estimate-parser` | ∥ B2、B3 | 三雲樣本可解析；PBT／CI 邊界綠 | 格式可穩定解析 |
| B2 | U6 `langgraph-runtime` | ∥ B1、B3 | OpenRouter 一次成功推論 | 框架＋模型路徑可行（Q5） |
| B3 | U4 `credential-pipeline` | ∥ B1、B2 | contract／env 綠；無憑證可啟動 | FR11 改得動 CI |
| B4 | U2 `estimate-intake-api` | 需 B1 | 上傳／讀取／**分享 API**／稽核；觸發建議掛點 | 上傳面可用 |
| B5 | **U3＋U8** | 需 B4；（與 B6 可平行若 B2 完） | 舊路徑刪淨＋`/cost` 上傳明細歷史分享；**同批部署** | `/cost` 不死窗 |
| B6 | U7 `cost-advice-agent` | 需 B4、B2；（∥ B5） | 省錢建議＋SSE＋Advice 持久化 | 建議在 5 分鐘內可產出 |
| B7 | U9 `advice-presentation-ui` | 需 B5、B6 | 建議區進度與三態 | 窗口期結束 |
| B8 | U5 `pricing-lookup-port` | 需 B3；（建議在 B6 後） | 目錄價查詢＋降級；不回寫明細 | Should 查價可掛上 |

**約束已嵌入**：U3＋U8 同 Bolt；U4 在 U3 部署前完成（FR9.8）；U2 在 U3 前完成以降低 router 衝突；分享／歷史在 B4／B5 DoD（Q4=A）。

**不採用 walking skeleton 儀式**（scope `skeleton: off`）。B1→B4→B5 仍形成「解析→API→可見頁」的實質薄切片，但不單獨閘門。

**Team**：team-formation SKIP → 所有 Bolt 預設 `aidlc-developer-agent`；平行時兩條 worktree（AH-2）。

[Answer]: Looks correct

照此產生 bolt-plan 等四份產出。
