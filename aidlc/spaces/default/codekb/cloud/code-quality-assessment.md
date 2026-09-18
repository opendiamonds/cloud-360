# 程式碼品質評估（Code Quality Assessment）

> Reverse Engineering 合成產物｜repo `cloud`｜commit `8c90f40`｜intent `260806-a1-a3-ux`

## 測試、Lint 與 CI

| 面向 | 現況 | 評估 |
|---|---|---|
| Backend unit／property | `backend/tests`：unittest＋Hypothesis（含 `test_diagram_builder`、`test_design_agent`） | 核心路徑有測試基礎；符合 ADR-0006 的方向，但需確認 agent routing／builder 幾何屬性覆蓋是否足以鎖住 edge／port 回歸 |
| Frontend unit | 無 React 元件單元測試 | A1 殼層與 canvas 橋幾乎無自動化單元防護 |
| Frontend e2e | Playwright（`frontend/tests/e2e`、`npm run test:e2e`）＋ gh-aw ui-regression | 有 UI 回歸能力；尚不知是否覆蓋 undo／sidebar collapse／refusal |
| Coverage gate | 無強制 coverage 門檻於 CI 描述中 | bugfix scope 以回歸測試為主；建議本 intent 為每個 UX 缺陷補最小回歸 |
| Lint／型別 | ESLint 10＋TS `tsc -b`；backend 依 CI | 建置期型別檢查健全 |
| Repo contract | `validate_repo_contract.py` 於 CI 先行 | 文件語言、禁止路徑／內容有硬門禁 |
| CI 管線 | contract → lint／build → unittest → Docker；`ut` → deploy | 與 org deploy-on-merge 一致 |
| 文件 | Specs／ADR／AIDLC artifacts 繁中（ADR-0009） | 方法論文檔品質高；執行時 embed 協議文件不足 |

總評：平台級治理（contract、CI、deploy、specs）成熟於功能級前端品質網；A1／A3 UX 債務集中在「可觀察但未測試鎖死」的互動路徑。

## 技術債與 A1／A3 UX Hotspots

下列債項應進入本 intent 的修正與回歸清單（與 architecture 改善機會對齊）：

1. **App Sidebar 固定 `w-64`、不可收合**（`Layout.tsx`／`Sidebar.tsx`）。僅 `WorkspacePage.chatCollapsed` 可收聊天區，畫布仍被全局側欄擠壓。  
2. **Edges 重疊圖示**（`diagram_builder.py`）：連線缺 exit／entry ports；edge `parent` 恆 `"1"`；image shapes 使正交邊穿越圖示。  
3. **Draw.io save／exit 未處理**（`DrawioCanvas.tsx`）：只接 init＋autosave；`ui=min`；儲存／離開工作流不完整。  
4. **Undo 損壞**：autosave → `setXml` → `postMessage` load 清空 iframe history；焦點常在 iframe 外導致快捷鍵失效。  
5. **無 prompt refusal**：`design_agent`／`agent_router` 未拒絕變更 Cloud-360 DB／API key／credential／系統值之類提示——屬安全／完整性缺口，不只 UX。  
6. **Sidebar 扁平 IA**：缺 A→A1／A3、J→admin 的 story-group 巢狀；`RolePermissionsPage` 的 pillars 未反射到導覽模型。

其他债：前端缺單元測試、coverage 無門檻、第三方 embed 契約未版本化。

## 建議品質護欄（bugfix 導向）

- 每個 hotspot 至少一條自動化回歸：builder 幾何用 Hypothesis／單元；canvas 行為用 Playwright（undo、autosave 不 reload、可選 collapse）。  
- Refusal：在 agent 入口加明確拒絕案例測試（提示含 credential／schema 變更關鍵字）。  
- 變更 `diagram_builder` 時保留金色 XML／snapshot 或 property（邊不穿越節點邊界盒）。  
- 文件：在 codekb／設計稿中固定 embed `postMessage` 事件清單，避免再漏接 save／exit。  
- 維持 contract＋既有 suite 全綠；不為本 intent 引入 production 路徑或 secret 檔。
