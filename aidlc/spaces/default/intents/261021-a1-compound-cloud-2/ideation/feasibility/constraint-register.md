# Constraint Register — A1 混合雲架構繪圖

<!-- Stage: feasibility（Ideation 1.3）· 來源標籤定義見 feasibility-questions.md 的 ## Sources。 -->

## 上游輸入

- 約束的業務脈絡承襲 intent-capture 的 **intent-statement**（`../intent-capture/intent-statement.md`）：混合雲架構展示需求、跨三雲整合邊界與 n8n 上行 provider = compound 之核心規定 [intent:Q1] [intent:Q3]。
- market-research 已依條件判定跳過（內部既有畫布延伸擴充，不涉及外部市場定位與競品研究），本登錄無市場面約束來源。

## 技術約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| T1 | n8n Webhook 上行必須帶入 `provider = "compound"` | 向 n8n 發出的 payload 必須明確給定 `provider = "compound"`，不得直接填入單一雲別（AWS/GCP/Azure），確保後端與 n8n 通訊契約一致 | [desc] [Q2] [code:C2] |
| T2 | 幾何佈局採中央核心＋雙翼 (Hub-and-Spoke) 架構 | 需在 `diagram_builder.py` 中支援計算中心雲與兩側輔助雲之座標與空間偏移，避免容器碰撞或遮擋 | [Q1] [code:C1] |
| T3 | 三雲頂層群組容器需共存於單一 mxGraph XML 中 | 單一畫布 XML 必須能同時承載 `aws_cloud`、`azure_cloud`、`gcp_cloud`，且其各自內部子網與服務元件正常階層歸屬 | [intent:Q3] [code:C1] |
| T4 | 跨雲連線需支援協議標籤與跨容器避障 | 跨雲 edges 錨定於不同頂層容器之節點時，需確保連線幾何路徑不被容器 AABB 誤判為非法阻擋，並可呈現連線文字標籤 | [Q3] |
| T5 | 前端選單需新增「混合雲 (Compound)」選項並支援對話識別 | 前端 Provider 選單需具備混合雲選項，並在對話偵測到跨雲時自動切換至 compound 模式 | [Q4] |
| T6 | `draw_architecture_diagram` LLM Tool 定義擴充 | 必須擴充 tool schema 支援 `provider: "compound"`，並更新提示詞以指引 LLM 正確輸出三雲群組結構 | [code:C3] |

## 組織與流程約束

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| O1 | 混合雲繪圖核心幾何邏輯必須具備單元測試防護 | 必須新增 `test_diagram_builder_compound.py` 專屬測試集，覆蓋 compound 幾何組裝與 n8n mock 呼叫 | [Q5] [memory:M2] |
| O2 | 依循既有 A1 單雲繪圖實作慣例，以能打通 n8n compound 流程為最高優先 | 實作時優先複用既有 `diagram_builder.py` 穩定模組，不引入不必要的第三方圖形依賴 | [intent:Q6] |
| O3 | 程式碼與變數維持英文，文件與對話維持繁體中文 | 所有程式碼識別字、commit、API 維持英文；所有規格文件與使用者溝通一律使用繁體中文 | [memory:M1] |

## 法規與政策約束

security baseline 四面向逐項判定（不得留空）[memory:M2]：

| 面向 | 判定 | 處置 | Source |
| --- | --- | --- | --- |
| IAM | **不適用** | 本功能純屬架構圖繪製與渲染，不涉及後端授權矩陣或使用者角色權限之異動 | [Q5] |
| encryption | **不適用** | 傳輸經由既有 HTTPS；繪圖資料為架構拓樸 XML，不包含機敏金鑰或個人隱私資料 | [memory:M1] |
| network exposure | **適用（出站）** | 後端僅向已配置之 `N8N_WEBHOOK_URL` 發出 POST 請求以取得圖示；不得開立任何外部非必要入站端口 | [code:C2] [memory:M1] |
| audit logging | **適用** | 繪圖操作與 n8n 通訊之警告（如圖示回傳失敗降級）需維持既有 logger.warning 輸出，便於維運排查 | [code:C2] |

| # | 約束 | 影響 | Source |
| --- | --- | --- | --- |
| R1 | 禁止 commit 私鑰或雲端供應商 Production Credentials | n8n 連線資訊一律由環境變數讀取，禁止將任何真實帳號憑證硬編碼至程式庫 | [memory:M1] |
| R2 | 雲端 Production 環境為 Out of Scope | 本功能專注於架構圖視覺化呈現，嚴禁進行任何對真實雲端資源的破壞性或變更操作 | [memory:M1] |

## Assumptions & Open Questions

None.
