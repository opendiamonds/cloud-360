# Bolt Plan — Story D IaC

> Stage: delivery-planning · Intent: `261105-d-iac-generation`  
> Q1–Q5=A；Looks correct 已核可。  
> **Bolt**＝一次 Construction 建置切片（可含一個或多個 Unit），結束時要有可驗證的完成定義與信心假設。

## 適用的既有實務（自 memory 層解析，非本站新定）

| 事項 | 定案 | 來源層 |
|---|---|---|
| Construction worktree base／merge target | `ut` | `org.md ## Way of Working` |
| Bolt 分支合併 | Construction Bolt **squash-merge** 進 `ut`；一般 PR 維持 merge commit | `team.md`／[tp] |
| Walking skeleton | **本 intent `skeleton: off`**；第一 Bolt 無額外 skeleton gate | [tp]／`team.md` |
| 部署 | **deploy-on-merge** 至自有 staging | `org.md`／`project.md ## Deployment` |
| 設計迭代 | **`stage-major`**（預設；不呼叫 `set-construction-iteration`） | 本站：兩 Bolt 可平行，仍以 stage 為主軸掃過各 unit |
| Bolt 執行 | **允許 B1∥B2 平行**（Q3=A） | 本站 |

## 序列總覽

```
B1  u1-iac-api     ∥  B2  u2-iac-ui
    （經濟敘事：風險／閘優先證明 U1；拓樸無 depends_on，允許平行）
    → 各 squash-merge ut → staging → 驗收
B2 完成後 → 端到端多角色演示（US6.2）就緒
```

**DAG 相容性**：`unit-of-work-dependency.md` 兩 unit 皆 `depends_on: []`。B1∥B2 **無拓樸偏離**。經濟啟發式為風險／閘優先（Q1=A），不強制串行合入順序。

每個 Bolt 跑 Construction 對應 unit 的設計／建置階段（functional-design …）。intent 級 `tcms-test-cases` 在兩 Bolt 可演示路徑就緒後執行一次，不另開 Bolt。

---

## B1 — `u1-iac-api`（閘與契約）

**包含單元**：U1 `u1-iac-api`（service，embedded backend）

**Walking skeleton 標記**：否

**對應故事（主責）**：US1.3、US2.*、US3.1、US4.1、US5.1（API）、US5.2、US6.1、US6.2（API）

**Definition of Done**：

- `/api/iac` 落地：`generate`／`scan`／`secrets/rewrite`／`session`／`download`；OpenAPI 無 drift
- **關閉契約 advisory R-01／R-02**（Q4=A）：`GET /download` 具名 story action；`/scan`／`/secrets/rewrite` 強制 `diagram_id`（或明文解析＋對應 `error.code`）
- 閘：無草稿／無 D2 成功報告 → **422**＋穩定 `error.code`；切圖作廢舊 `report_id`；不得以舊 id 執行 D3
- US6.1：第一個落地的 D 執行 HTTP **成對** TestClient 403／2xx
- 三核心 PBT（Generator／Scanner／Redactor）；回應／log／zip **無** D3 前明文樣式
- OpenAPI／工具清單靜態斷言：**無** apply／destroy；不寫入雲端 SM
- Agent 經 `langgraph_runtime`（可 stub）

**信心假說**：*無法繞過 D2 執行 D3；無權呼叫為 403；有權路徑回契約成功態。*

**預期展示**：TestClient／staging API：無權 403；有 D1 草稿可 scan；僅 D1 不可 rewrite；rewrite／download 後抽樣無明文密文。

**已知風險**：行程內狀態機／舊 report_id（Q5=A）。見 `risk-and-sequencing-rationale.md`。

---

## B2 — `u2-iac-ui`（工作區可見面）

**包含單元**：U2 `u2-iac-ui`（ui，embedded frontend）

**Walking skeleton 標記**：否

**對應故事（主責）**：US1.1、US1.2、US1.4、US3.2、US4.2、US5.1（UI）、US6.2（UI）

**Definition of Done**：

- Workspace「生成 IaC」入口；無權 disabled＋說明（非隱藏）
- 三步驟殼＋選圖／上傳／切圖清空提示；對齊 refined-mockups test-id
- 消費 `/api/iac`；執行鈕 busy；空／錯／進行中態
- 下載：HIGH／CRITICAL 先 modal（確認／取消／Esc）；無 apply UI
- US6.2 UI：各步可觀察成功態；端到端演示在 B1 API 可用後驗證（平行時可用 stub／合併後 e2e）

**信心假說**：*有權使用者可走完選圖→生成→掃描→Secrets→下載確認的可見路徑；無權者看不到可執行入口。*

**預期展示**：Playwright／手動：Alex 選圖→D1 預覽→Fiona 掃描／改寫→下載 modal→zip；無 D1 view 帳號入口 disabled。

**平行約束（Q3=A）**：可與 B1 同時開工；對真實 `/api/iac` 的 e2e／Playwright 等 U1 至少有 D1 2xx stub 或 B1 合併後再跑。

---

## Bolt 間約束

| 約束 | 說明 |
|---|---|
| 契約 Owner | U1；破壞性變更同 PR 更新 OpenAPI＋UI＋TestClient |
| US5.1／US6.2 | U1 部分∈B1 DoD；U2 部分∈B2 DoD；B2＋可用 API 後才算演示就緒 |
| US7.1 | 本輪不建（Should／GAP，已接受） |
| 部署 | 各 Bolt squash-merge → deploy-on-merge staging |
