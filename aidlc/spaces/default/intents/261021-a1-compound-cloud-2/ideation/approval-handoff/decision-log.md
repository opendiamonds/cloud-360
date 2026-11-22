# Decision Log — Ideation Phase 全階段決策記錄

> Stage: approval-handoff (1.7) · Phase: Ideation · Scope: feature
> 記錄 Ideation 階段 (1.1 ~ 1.7) 所有關鍵架構、業務、範疇與技術選型決策。

## Stage 1.1 Intent Capture & Framing Decisions

- **D-1.1-1 (核心目標)**：明確本項目為 A1 混合雲架構繪圖，單張圖同時繪製 AWS、Azure、GCP 三大雲端服務提供商。
- **D-1.1-2 (上行協議)**：確認向 n8n 服務發送之上行參數統一為 `provider = "compound"`。
- **D-1.1-3 (工作範疇)**：工作範疇確認為 feature Scope（共 34 階段，Standard 深度）。
- **D-1.1-4 (審查結果)**：獲 Product Lead 評定為 READY，使用者於 Gate 正式 Approved。

## Stage 1.2 Market Research Decisions

- **D-1.2-1 (階段略過)**：依據 condition（內部專有系統功能擴充，非面向公開市場之全新產品），經判定並由使用者指示略過 (skipped)。

## Stage 1.3 Feasibility & Constraints Decisions

- **D-1.3-1 (幾何佈局選型)**：經比較垂直堆疊、橫向排列與環狀佈局後，決策選定中央核心雲加寬、左右雙翼對稱分佈之 **Hub-and-Spoke** 空間幾何佈局。
- **D-1.3-2 (上行 Payload 規範)**：上行至 n8n 之 payload 統一明確給定 `provider = "compound"`，不得退回單一雲 fallback。
- **D-1.3-3 (跨雲連線規範)**：跨雲連線支援直角折線與協議標籤（如 VPN Tunnel、HTTPS API 等），端點錨定於各群組邊緣。
- **D-1.3-4 (前端入口模式)**：前端同時支援 Toolbar 選單手動選擇與對話模型自動識別切換。
- **D-1.3-5 (測試策略)**：新增專屬單元測試集 `test_diagram_builder_compound.py`，不影響既有測試集。
- **D-1.3-6 (假設清除)**：全數主張完成代碼查證，`Assumptions: None.`，獲審查通過並 Approved。

## Stage 1.4 Scope Definition & Prioritization Decisions

- **D-1.4-1 (交付切片)**：採整包交付 (All-in-One Must)，包含 Tool 定義、幾何佈局、n8n compound 上行、前端選單與單元測試集。
- **D-1.4-2 (排程策略)**：採技術依賴鏈優先 (Dependency-first) 推進：Prompt/Tool → Builder 幾何與 n8n 通訊 → 前端觸發 → 單元測試。
- **D-1.4-3 (邊界排除)**：明確排除真實雲端資源同步、第四雲擴充、成本自動試算與網絡遙測，防止範疇蔓延。
- **D-1.4-4 (Proto-Units 劃分)**：劃分為 7 個 Proto-Units，形成清楚之依賴關係鏈。

## Stage 1.5 Team Formation Decisions

- **D-1.5-1 (團隊模式)**：依據 condition（solo/small team 開發，無需複雜跨團隊 Mob 組建），由使用者指示略過 (skipped)。

## Stage 1.6 Rough Mockups Decisions

- **D-1.6-1 (UI 空間分佈)**：中央核心雲加寬（480px），GCP (360px) 與 Azure (360px) 分居兩側，留有 120px 跨雲走廊。
- **D-1.6-2 (前端選單狀態)**：Toolbar 新增 Compound 按鈕，支援雙向選單狀態同步與反白高亮。
- **D-1.6-3 (連線路徑優化)**：跨雲 edges 採直角折線 (Orthogonal Routing)，大幅減輕多雲連線交叉重疊。
- **D-1.6-4 (畫布視角)**：初始載入採 Fit-to-Window 自動最佳化視角，並保留平移與縮放能力。
- **D-1.6-5 (無障礙與容錯)**：符合 WCAG 2.1 AA 標準，並在 n8n 服務異常時提供優雅降級 (Fallback)。
- **D-1.6-6 (審查結果)**：獲 Product Lead 評定為 READY，使用者於 Gate 正式 Approved。

## Stage 1.7 Approval & Handoff Decisions

- **D-1.7-1 (交接彙整確認)**：全體利害關係人針對 Intent、Scope、Feasibility、Mockup 達成一致，順利完成 Consolidated Summary 確認。
- **D-1.7-2 (推進裁決)**：正式簽署 GO 建議，由 Ideation 階段交接至 Inception 階段（首站為 Stage 2.1 Reverse Engineering）。
