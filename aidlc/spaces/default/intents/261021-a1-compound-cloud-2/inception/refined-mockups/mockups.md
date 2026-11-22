# Refined Mockups & UI Layout Specifications — A1 混合雲繪圖功能

> Stage: refined-mockups (2.5) · Phase: Inception · Scope: feature · Depth: Standard
> 追溯上游基準：
> - [wireframes](../../ideation/rough-mockups/wireframes.md)
> - [user-flow](../../ideation/rough-mockups/user-flow.md)
> - [stories](../user-stories/stories.md)
> - [requirements](../requirements-analysis/requirements.md)
> - [team-practices](../practices-discovery/team-practices.md)

---

## 1. 畫面佈局總覽與高保真線框 (UI Screens Overview)

本規格定義 A1 混合雲繪圖功能之 4 個核心畫面與狀態的高保真視覺表現，落實雙重觸發入口、Hub-and-Spoke 空間佈局、跨雲直角折線與灰底 SVG Fallback 機制。

### Screen 1: WorkspacePage 頂部 Toolbar 與 Provider 下拉選單

```
+----------------------------------------------------------------------------------------------------+
|  [Logo] Cloud-360 / A1 Design Studio       [ Untitled Architecture 1 ]        [Save] [Export XML]  |
+----------------------------------------------------------------------------------------------------+
|  Provider: [ Compound (混合雲) ▼ ] | Zoom: [ 85% ▼ ] [Fit-to-Window] | Grid: [On] | Layout: [Auto] |
|            | AWS              |                                                                    |
|            | Azure            |                                                                    |
|            | GCP              |                                                                    |
|            |------------------|                                                                    |
|            | ✓ Compound       |                                                                    |
|            +------------------+                                                                    |
+----------------------------------------------------------------------------------------------------+
```

- **視覺特徵**:
  - Provider 下拉選單位於畫布左上方次導航列，寬度 160px，背景 `#FFFFFF`，邊框 `#CBD5E1`。
  - 當選中「Compound (混合雲)」時，按鈕文字加上藍色圓點識別 Badge，並同步全域狀態 `provider = "compound"`。

---

## 2. 對話式意圖識別與串流反饋畫面 (Screen 2: ChatBox Multi-Cloud Intent)

```
+-------------------------------------------------------------+
| Chat Assistant                                          [-] |
+-------------------------------------------------------------+
| [User]: 請幫我設計一個跨 AWS 與 GCP 的金融混合雲架構，      |
|         AWS 放置核心交易服務，GCP 放置 BigQuery 數據分析。  |
|                                                     14:02   |
|                                                             |
| [Agent]: 好的！偵測到多雲整合意圖，已自動為您切換至         |
|          [ ☁️ 混合雲 (Compound) 模式 ]。                    |
|                                                             |
|          正在規劃拓撲：                                     |
|          1. 中央核心：AWS Cloud (寬度 480px)                 |
|          2. 數據分析翼：GCP Cloud (寬度 360px)              |
|          3. 跨雲連線：Direct Connect + Dedicated Interconnect|
|                                                             |
|          [ ⏳ 正在透過 n8n 取得服務圖示 (compound)... ]     |
|          [ 🎨 拓撲幾何組裝完成，正在自動縮放畫布... ]       |
|                                                     14:03   |
+-------------------------------------------------------------+
| [ 請輸入架構調整指令或追問...                             ] |
+-------------------------------------------------------------+
```

- **交互反饋**:
  - Agent 在回覆開頭以 High-contrast Badge `[ ☁️ 混合雲 (Compound) 模式 ]` 提示切換，前端 Toolbar 狀態即時連動。
  - 產圖期間透過 SSE 串流提供步驟式狀態提示，產圖完成後發送畫布重繪信號。

---

## 3. DrawioCanvas 混合雲全貌渲染與空間幾何 (Screen 3: Canvas Layout)

依據 Hub-and-Spoke 幾何佈局計算，中央核心雲加寬至 480px，左右雙翼各為 360px，雲與雲之間保留 120px 跨雲緩衝走廊：

```
+--------------------------------------------------------------------------------------------------------------------+
|  DrawioCanvas (自動 Fit-to-Window, 250ms ease-out, Padding: 32px)                                                  |
|                                                                                                                    |
|   ┌── Azure Cloud (360px) ──┐        ◄- 120px -►        ┌── AWS Cloud (480px, Hub) ──┐        ◄- 120px -► ...     |
|   │                         │     [Buffer Corridor]     │                            │     [Buffer Corridor]       |
|   │  ┌─ VNet (West US) ──┐  │                           │  ┌─ VPC (us-east-1) ────┐  │                             |
|   │  │                   │  │                           │  │                      │  │                             |
|   │  │   [ Azure AD ]    │  │                           │  │   [ EKS Cluster ]    │  │                             |
|   │  │        │          │  │                           │  │          │           │  │                             |
|   │  └────────┼──────────┘  │                           │  │          ▼           │  │                             |
|   └───────────┼─────────────┘                           │  │      [ RDS DB ]      │  │                             |
|               │                                         │  └──────────┬───────────┘  │                             |
|               │                                         └─────────────┼──────────────┘                             |
|               │                                                       │                                            |
|               └──────[ 直角折線: 邊緣錨定 ]────────────────────────────┘                                            |
|                              │                                                                                     |
|                              ▼                                                                                     |
|                   ┌──────────────────────┐                                                                         |
|                   │  🔒 VPN Tunnel (IPSec)│ ◄── 純白膠囊圓角背景 (#FFFFFF, border: 1px solid #CBD5E1)              |
|                   └──────────────────────┘                                                                         |
+--------------------------------------------------------------------------------------------------------------------+
```

- **幾何佈局規範**:
  - `aws_cloud` (中央)：寬度 480px，邊框色 `#FF9900` (AWS 橘)，背景色 `#FFF7ED` (5% 不透明度)。
  - `azure_cloud` (左翼)：寬度 360px，邊框色 `#0078D4` (Azure 藍)，背景色 `#F0F9FF`。
  - `gcp_cloud` (右翼)：寬度 360px，邊框色 `#4285F4` (GCP 藍/紅/黃/綠)，背景色 `#F8FAFC`。
  - 走廊間距：跨雲群組邊界橫向間距嚴格保證 $\ge 120\text{px}$。
  - 直角折線：跨雲連線一律使用 `orthogonalEdgeStyle`，中點渲染協議膠囊標籤。

---

## 4. n8n 服務異常容錯狀態 (Screen 4: Fallback SVG Component)

當向 `${N8N_WEBHOOK_URL}` 發送 `provider="compound"` 遭遇逾時（> 5.0 秒）或 HTTP 非 200 時，回退至灰底文字向量 SVG：

```
       +───────────────────────────────────+
       |   40px                            |
       |   ┌───────────────────────────┐   |
       |   │  #F1F5F9 (灰底)           │   |
       |40px  border: 1px solid #94A3B8│   |
       |   │                           │   |
       |   │          [ EC2 ]          │   | ◄── #475569 (深灰文字, 11px Bold)
       |   │                           │   |
       |   └───────────────────────────┘   |
       +───────────────────────────────────+
```

- **特性說明**:
  - 向量 SVG 採純程式碼內聯產生（Data URI `data:image/svg+xml,...`），不依賴外部網路資源。
  - 前端 mxGraph cell 正常渲染此向量圖形，產圖流程不報錯、無破圖紅叉，架構師依然能清楚識別服務名稱。

