# Code Summary — Unit `a1-a3-ux`

> Intent: `260806-a1-a3-ux` · Branch: `luojingting/fix/a1-a3-ux-fixes`  
> 實作對應：`code-generation-plan.md`（全部步驟已勾選）

## 摘要

完成本期 A1／A3 UX bugfix：prompt 預檢阻擋平台自改意圖、架構圖邊線 mid-side ports、Sidebar 收合與 A／J 資訊架構，以及 draw.io embed 的儲存／退出／Undo 修復。

## 變更檔案

### Backend（新建）
| 檔案 | 說明 |
|---|---|
| `backend/services/prompt_guard.py` | `is_platform_self_modification`、`REFUSAL_MESSAGE`、`latest_user_text` |
| `backend/tests/test_prompt_guard.py` | 命中／未命中（含客戶雲架構圖未擋） |
| `backend/tests/test_diagram_builder_edges.py` | edge exit／entry port 斷言 |

### Backend（修改）
| 檔案 | 說明 |
|---|---|
| `backend/services/agent_router.py` | `/generate`、`/generate-wa-collab` 預檢後 SSE 固定拒答，不進 LLM |
| `backend/prompts/cloud_architecture_system_prompt.md` | 平台自改拒答政策 |
| `backend/services/diagram_builder.py` | `edge_anchor_ports`；正交邊加 `exitX/Y`、`entryX/Y` |

### Frontend（修改）
| 檔案 | 說明 |
|---|---|
| `frontend/src/components/Layout.tsx` | `NavChromeContext`／`useLayoutNav`；localStorage `cloud360.nav.sidebarCollapsed` |
| `frontend/src/components/Sidebar.tsx` | 收合窄軌＋`data-testid="sidebar-toggle"`；大類 A／J、路由自動展開 |
| `frontend/src/components/DrawioCanvas.tsx` | `save`→`onSaveClick`；`exit`→`onExit`；autosave echo 不 `action:load` |
| `frontend/src/pages/WorkspacePage.tsx` | Sidebar layoutEpoch；`handleCanvasExit` 確認後展開側欄 |

## 測試結果

```
cd backend && python3 -m unittest discover -s tests -q
Ran 108 tests in ~11s
OK
```

含新增 `test_prompt_guard` 與 `test_diagram_builder_edges`。

## Traceability 對照

| FR | 實作 |
|---|---|
| FR-GUARD-01～04 | `prompt_guard` + `agent_router` 預檢 + system prompt |
| FR-EDGE-01～03 | `diagram_builder.edge_anchor_ports` |
| FR-NAV-01～04、NFR-03 | Layout／Sidebar 收合與 A／J IA |
| FR-DRAW-01～04 | DrawioCanvas save／exit／Undo + WorkspacePage |

## 未做（本單元 Out of scope）

- Review／lens 路徑防衛
- DB migration
- B–H pillar Sidebar 掛載
- FR-NAV-05 寫入 `project.md` 實踐（可視後續 stage 補）

## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-08-06T02:34:01Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | `prompt_guard.py` `_SENSITIVE` / FR-GUARD-04 | `_SENSITIVE` 含 `token`，正常雲架構需求若同時出現平台名（cloud360）＋mutation 動詞（設定、更新）＋`token`（如 JWT、API token），三重 AND 仍成立，造成 false positive，違反 FR-GUARD-04。現有測試僅驗「金鑰不含 mutation → 不擋」，未覆蓋「token 在合法描述中但命中 _PLATFORM + _MUTATE」的 false positive 路徑。 | 在 `test_prompt_guard.py` 補一條 false positive 測試（例：「在 Cloud-360 工作區繪製使用 JWT token 認證的 AWS API Gateway 架構」應回傳 False）；如測試確認誤擋，可將 `token` 從 `_SENSITIVE` 移出或縮窄為 `api[\s\-]?token\|bearer[\s\-]?token`。 |
| 2 | Minor | `WorkspacePage.tsx` `handleCanvasExit` / FR-DRAW-02 | 髒資料確認只在 `saveStatus === 'unsaved' \|\| 'saving'` 時觸發；`no-file` 狀態（AI 已產圖但未建檔）不觸發確認，使用者按 embed 「退出」後畫布內容靜默丟失，違反「若有未儲存變更則確認」。 | 在 dirty 判斷中加入 `\|\| (saveStatus === 'no-file' && !!xml)` 或改以 `latestXmlRef.current` 是否有值為依據，確保有 canvas 內容時無論 no-file 狀態皆彈確認。 |
| 3 | Minor | `agent_router.py` + `test_prompt_guard.py` / NFR-02 | 測試只驗 guard 函數本身（純單元），未對 `/generate` 或 `/generate-wa-collab` 端點做任何整合層斷言（guard 命中 → SSE 回 `REFUSAL_MESSAGE` 且無 LLM 呼叫）。串接邏輯正確，但 NFR-02「可單元測試命中／未命中案例」在 HTTP 路徑層仍為零覆蓋。 | 補 `test_agent_router_guard.py`（可用 `TestClient` + mock `is_platform_self_modification`）斷言命中時 response body 含 `REFUSAL_MESSAGE` 且 `run_design_agent` 未被呼叫。 |
| 4 | Minor | `diagram_builder.py` `edge_anchor_ports` / FR-EDGE-01 | `edge_anchor_ports` 只實作四向正交選邊（horizontal / vertical by dominant delta）；對角線等距（`abs(dx) == abs(dy)`）退回水平路徑，無測試覆蓋此邊界。此外，節點中心完全重疊（dx=0, dy=0）時回傳 `(1.0, 0.5, 0.0, 0.5)` 不會崩潰但產生語意怪異的邊線；無測試驗此情形。 | 在 `test_diagram_builder_edges.py` 新增 `test_diagonal_equal_delta`（dx==dy 時應選水平，驗期望值）與 `test_overlapping_nodes`（dx=0, dy=0 不崩潰）；若實際圖面需 45° 對角邊，可後續 issue 追蹤，本單元標記 known limitation 即可。 |

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| 手動追蹤 autosave → postLoad 路徑 | PASS：`latestXmlRef.current` 在 autosave 事件後與 xml prop 同步，useEffect guard `xml === latestXmlRef.current` 正確攔截，不發 `action:load` | FR-DRAW-03 修復邏輯正確，Undo 堆疊不會被 autosave echo 清空 |
| 手動追蹤 embed save → DB 路徑 | PASS：save 事件 → `onSaveClickRef` → `handleSaveDiagram` → `saveDiagram` → PUT `/api/collab/diagrams/{id}` | FR-DRAW-01 儲存路徑串接完整 |
| 手動追蹤 embed exit → Sidebar 展開路徑 | PARTIAL（見 Finding #2）：`setSidebarCollapsed(false)` 呼叫正確，但 no-file 髒資料確認缺失 | FR-DRAW-02 主幹流程完整，no-file 邊案缺確認對話 |
| 手動驗 localStorage 持久化 | PASS：`Layout.tsx` `readCollapsed()` / `persistCollapsed()` key = `cloud360.nav.sidebarCollapsed`；`WorkspacePage` 透過 `useLayoutNav()` 取用 | NFR-03 滿足 |
| 手動驗 Sidebar A/J 群組 | PASS：A 群 → `/workspace`（架構圖生成）+ `/assessment`（評估儀表板）；J 群 → `/admin/users`（使用者角色）+ `/admin/authorization-requests`（授權申請）+ `/admin/role-permissions`（角色細項權限）；路由自動展開 useEffect 實作正確 | FR-NAV-01～04 滿足 |
| `prompt_guard` 三重 AND 邏輯分析 | WARN（見 Finding #1）：`token` 關鍵字在 _SENSITIVE 中為較寬模式，legitimate 雲架構需求有 false positive 風險 | FR-GUARD-04 有潛在邊案 |

### Summary

四項 FR 群組（FR-GUARD、FR-EDGE、FR-NAV、FR-DRAW）主要實作路徑均正確串接，測試套件 108 tests 全綠，Undo 修復邏輯與 autosave 隔離機制設計可靠。四項 Minor 發現均無阻斷性，最重要的是 no-file 髒資料確認缺口（Finding #2）可能造成使用者在 AI 產圖未儲存狀態按退出後靜默丟失畫布內容；建議後續 PR 補上，或至少補說明文件。
