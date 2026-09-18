# Requirements — A1/A3 UX bugfix

> Intent: `260806-a1-a3-ux` · Scope: `bugfix` · Branch: `luojingting/fix/a1-a3-ux-fixes`  
> 問答：`requirements-analysis-questions.md`（確認：Looks correct）  
> Codekb：`aidlc/spaces/default/codekb/cloud/` @ `8c90f40`

## Intent Analysis

| 項目 | 判定 |
|---|---|
| 目標 | 修復 Workspace（A1）與導覽（Sidebar IA）的數項 UX／安全缺陷，讓架構圖可舒適編輯、連線可讀、embed 儲存／退出／Undo 可用，並阻擋對 Cloud-360 平台自身的危險提示 |
| 類型 | Bug fix／UX hardening（brownfield） |
| 清晰度 | 高（六項明示＋六題澄清已決） |
| 範圍 | 多元件：`Layout`／`Sidebar`／`WorkspacePage`／`DrawioCanvas`／`diagram_builder`／`design_agent`／`agent_router` |
| 複雜度 | Standard（跨 FE embed 協定＋BE builder＋prompt 預檢） |
| Depth | Minimal（bugfix） |

## Functional Requirements

### FR-NAV — Sidebar 資訊架構與收合

| ID | 需求 |
|---|---|
| FR-NAV-01 | Sidebar 須可**獨立收合／展開**（與 Chat 收合互不綁定；**不**另設單一「全螢幕模式」）（Q1=C） |
| FR-NAV-02 | Sidebar 收合後 Workspace 畫布須佔用釋出寬度；並觸發既有 `layoutEpoch`／resize 讓 draw.io 重新適配 |
| FR-NAV-03 | 導覽依 **user story 大類** 分層：至少大類 **A**、**J**；A 下第二層為 **A1 架構圖生成**、**A3 評估儀表板**；J 下為既有管理項（使用者角色、授權申請、角色細項權限） |
| FR-NAV-04 | 進入對應路由時，**自動展開所屬大類**（Q6=A）；無權限的項目不顯示 |
| FR-NAV-05 | 後續新增 story 功能時，Sidebar 須比照「大類 → 故事層」慣例（寫入 project 實踐） |

### FR-DRAW — Draw.io embed 行為

| ID | 需求 |
|---|---|
| FR-DRAW-01 | 處理 embed `save` 事件：行為與標題列「儲存架構圖」相同，呼叫 collab `PUT/POST` 持久化（Q3=A） |
| FR-DRAW-02 | 處理 embed `exit` 事件：若有未儲存變更則確認；確認後**留在 Workspace**、**展開 Sidebar**、Chat 依使用者偏好（Q2=A） |
| FR-DRAW-03 | 停止因「每次 autosave 回寫 `xml` → `action: load`」而清空 Undo 堆疊；Undo／Redo 與 **Ctrl+Z／Ctrl+Y（或 Cmd）** 在**畫布／iframe 焦點內**必須有效（Q4=A） |
| FR-DRAW-04 | 僅在真正需要置換整圖（載入他圖、AI merge 結果）時才對 embed 發 `load`；一般 autosave／本地編輯不得 `load` 清空 Undo（實作細節可由 Construction 決定；源自 D5，非獨立產品決策） |

### FR-EDGE — 連線不覆蓋 icon／文字

| ID | 需求 |
|---|---|
| FR-EDGE-01 | `diagram_builder` 產生的邊線須帶合理 **exit／entry** 連接點（及必要 waypoint），避免正交線穿過元件 image icon |
| FR-EDGE-02 | 既存／新產生之 AWS／GCP／Azure 圖在重新產生或局部更新後皆適用 FR-EDGE-01 |
| FR-EDGE-03 | 不把「線不重疊」的主修法放在前端 post-process（已決 builder 路徑） |
| FR-EDGE-04 | 避障盒須含節點下方標籤文字區（`verticalLabelPosition=bottom`），邊線應盡量不蓋住節點名稱 |

### FR-LAYOUT — 節點落在所屬 layer 內並置中

| ID | 需求 |
|---|---|
| FR-LAYOUT-01 | AI 產圖組裝時，節點（含下方標籤高度）須落在所屬最小 layer／group 內容區內，不得超出底部／側邊 |
| FR-LAYOUT-02 | 同層多個節點以網格排布後，整體須水平與垂直置中；空間不足時可擴大該 group（及必要祖先） |
| FR-LAYOUT-03 | 本期僅套用自動產圖（`diagram_builder`），不含手動拖曳時的邊界鎖定 |
| FR-LAYOUT-04 | 同層 sibling layer／group 須對齊（列內頂對齊或上下列左緣對齊、等距）且互不重疊（含固定間距）；必要時平移子樹並擴大父層；父子連結在排版初期鎖定，避免兄弟互吞 |
| FR-LAYOUT-05 | icon 水平間距須依標籤寬度拉開，避免節點名稱文字互相重疊 |
| FR-LAYOUT-06 | 有所屬 layer 的節點，其 icon 與標籤文字須完整落在該 layer 內（必要時撐大 layer）；無所屬者不受此限 |
| FR-LAYOUT-07 | 同 layer 內 icon＋標籤不得互疊（含評核改圖後） |
| FR-LAYOUT-08 | 若非端點的邊線穿過 icon／標籤，須於同一 layer 內平移至過線較少（理想為零）的空位後再最終連線 |

### FR-REVIEW-UX — 評核階段提示與建議排版

| ID | 需求 |
|---|---|
| FR-REVIEW-01 | Design 第一次產圖完成後，須以**聊天室系統訊息**提醒：「接下來會進入評核、請稍待；評核期間請先不要異動架構圖」；並搭配 progress 文案 |
| FR-REVIEW-02 | Review Agent（A3）建議輸出為**純文字**（禁止 Markdown）；Workspace 協作對話與 Assessment「改善建議」皆以一般文字排版顯示 |

### FR-GUARD — Prompt 防衛

| ID | 需求 |
|---|---|
| FR-GUARD-01 | 在 `POST /api/architecture/generate` 與 `POST /api/architecture/generate-wa-collab` **進入 Design Agent 前**做預檢（Q5=A） |
| FR-GUARD-02 | 命中「變更 Cloud-360 自身之資料庫／系統值／API key／金鑰（credentials）／等價表述」時：**不呼叫 LLM**，回覆固定語意：「此需求毫無相關，請重新輸入」 |
| FR-GUARD-03 | 以 system prompt 補強同一政策（防漏檢時模型仍拒答） |
| FR-GUARD-04 | 正常架構圖繪製／修改雲端架構需求不受影響 |

## Non-Functional Requirements

| ID | 需求 |
|---|---|
| NFR-01 | 不新增 production／secrets 路徑；不提交憑證 |
| NFR-02 | Prompt 預檢須可單元測試（命中／未命中案例）；既有 backend unittest 須維持綠色 |
| NFR-03 | Sidebar 收合狀態**須**以 localStorage 持久化（類似 chat collapse），重新整理後保留 |
| NFR-04 | 文件與 AIDLC 產出維持繁體中文（ADR-0009） |
| NFR-05 | 安全：預檢為防禦深度之一層，不取代既有 Agent tool sandbox |

## User Scenarios

1. **專注編輯**：使用者收合 Sidebar（與／或 Chat），在大畫布上編輯；展開後版面正確。
2. **儲存**：在 draw.io 內按儲存 → 與標題列儲存相同，狀態徽章更新為已儲存。
3. **退出**：按退出 →（若髒）確認 → 仍在 Workspace，Sidebar 展開。
4. **Undo**：在畫布焦點下 Ctrl+Z 回到上一步編輯。
5. **連線可讀**：AI 產圖後箭頭接在 icon 邊，不穿過圖示。
6. **惡意／跑題提示**：要求「改我們 DB 的 connection string／寫死 API key」→ 固定拒答，不進 agent。
7. **導覽**：在 A3 時 Sidebar 顯示大類 A 展開，可見 A1／A3；管理員見大類 J 子項。

## Constraints & Assumptions

| 類型 | 內容 |
|---|---|
| Constraint | 繼續使用 `embed.diagrams.net` JSON proto；不換成自研畫布 |
| Constraint | 不為此 bugfix 做 DB migration（除非實作中証明必須；預設不要） |
| Assumption | 「金耀」＝「金鑰」；預檢詞庫含 credentials／secret／api key／資料庫連線字串等 |
| Assumption | 僅 A／J 大類本期必交；其他 pillar 可之後再掛 |
| Out of scope | 原生 iOS／Android；雲端供應商 production 寫入；Review／lens 路徑防衛（Q5 未選） |

## Traceability

| 來源 | 覆蓋 |
|---|---|
| 使用者六項原述 | FR-NAV、FR-DRAW、FR-EDGE、FR-GUARD |
| Q1–Q6 | 見各 FR 括註 |
| Codekb hotspots | architecture／code-quality 所列缺陷 |

## Acceptance Criteria（交付檢查）

- [ ] Sidebar 可收合；畫布變寬且 draw.io 正常 resize
- [ ] Sidebar 呈 A→A1/A3、J→管理項；路由自動展開
- [ ] draw.io 儲存寫入後端；退出確認後回 Workspace 並展開 Sidebar
- [ ] 畫布焦點下 Undo／Ctrl+Z 有效（連續編輯多步可撤回）
- [ ] 新產圖邊線不貫穿 icon（至少抽樣 2 張不同服務組合之 AWS 產圖）
- [ ] generate／wa-collab 對封鎖樣本回固定拒答且無 LLM 呼叫；正常產圖仍可用

## Review

**Verdict:** READY
**Reviewer:** aidlc-product-lead-agent
**Date:** 2026-08-06T02:14:44Z
**Iteration:** 1

### Findings

| # | Severity | Location | Finding | Recommendation |
|---|---|---|---|---|
| 1 | Minor | NFR-03 | 「建議持久化（localStorage）」以「建議」措辭使此 NFR 可選，QA 無法寫出明確通過／失敗準則 | 改為強制（「Sidebar 收合狀態**須**以 localStorage 持久化，重新整理後保留」）或移入 Open Questions 作為之後決定的事項 |
| 2 | Minor | FR-DRAW-04 | 「與遠端協作更新衝突時優先保畫布歷史」的衝突解決策略未出現在 Q/D 任一決議中，由 AI 自行推論補入，超出 D5 確認範圍 | 在備注中明示「源自 D5 的實作推論，非 user 明確確認」，或在下一階段 functional-design 再決定細節 |
| 3 | Minor | Acceptance Criteria（FR-EDGE 列） | 「抽樣 AWS 產圖」未定義抽樣數量、元件組合、複雜度，QA 不知最少要跑幾張圖 | 加最低測試條件，例如「至少抽樣 2 張不同服務組合之 AWS 產圖，邊線均不貫穿 icon」 |

### Summary

整份 requirements 的六項 user 需求完整對映至 FR-NAV／FR-DRAW／FR-EDGE／FR-GUARD 四個群組，Q1–Q6 答案均有括號回溯標注，D1–D7 全數覆蓋，無雙語英文段落，無 prod/secrets 路徑，Acceptance Criteria 整體可測試。三項 Minor 不構成阻擋，工程階段可同步修正。
