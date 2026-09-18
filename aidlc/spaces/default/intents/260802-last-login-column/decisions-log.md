
### 2026-08-10 — 清單端點分頁納入本 intent 範圍

**Decision / 決議**: 使用者清單端點的分頁納入本 intent 實作範圍。依 `project.md` 規則，須回跳上游 stage 以 Modify 模式疊加修訂並重走 approval gate，不在下游 stage 擅自擴大範圍。
**Context / 背景**: Construction 3.2（NFR Requirements）為 U2 `user-object-serialization` 出題時，實測發現清單端點為 `.all()`、無分頁無上限，且迴圈內已有對待授權使用者的 N+1 查詢。本單元新增的每列成本雖為純記憶體計算、零新增查詢，但決策者判定應直接訂下分頁需求而非僅記載現況。
**Trigger / 觸發語**: 「訂分頁需求」→ 二次確認「回跳上游修訂，本 intent 實作分頁」
**Related / 相關**: intent `260802-last-login-column`；波及 scope-definition、requirements-analysis、user-stories、refined-mockups、application-design（C-4）、units-generation、delivery-planning，以及 U2／U3／U5 的 3.1 產出
