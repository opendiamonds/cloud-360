# Phase Boundary Verification — IDEATION → INCEPTION

<!-- 由 approval-handoff（1.7）Step 5 產出。方法論見 .claude/knowledge/aidlc-shared/verification.md。
     PHASE_VERIFIED 事件由引擎在 advance 時發出，不在此手寫。 -->

- **邊界**：IDEATION → INCEPTION（approval-handoff → reverse-engineering）
- **檢查項**（依 verification.md）：Intent → Scope → Intent Backlog 一致性；所有 scope 項目有可行性支撐
- **執行時點**：IDEATION 最後一站的 gate 之前

## 檢查一：Intent → Scope 覆蓋

逐條把 intent-statement 的元素對回 scope-document 的能力清單。

| Intent 元素 | 承接能力 | 判定 |
| --- | --- | --- |
| 問題：狀態失真 | CAP-2、CAP-3、CAP-4、CAP-6、**CAP-11** | 完整 |
| 問題：重複記帳 | CAP-1～CAP-4 | 完整 |
| 問題：需求來源分散 | CAP-8（README 指路）＋ 決策 D-7（正本置於看板） | 完整 |
| 問題：對外可視性不足 | CAP-1、CAP-2、CAP-3、CAP-7 | 完整 |
| 指標：零人工更新 | CAP-1～CAP-4 | 完整 |
| 指標：一致率 | CAP-4、CAP-6 ＋ 決策 D-12（分母定義） | 完整 |
| 指標：可追溯（每次狀態變更能說出是哪個 intent、哪個 stage、什麼時間） | 無明確承接能力 | **⚠ 部分** |
| 受益者：唯一開發者 | CAP-1～CAP-4 | 完整 |
| 受益者：其他協作者 | CAP-2、CAP-3、CAP-7、**CAP-11**（在看板上的操作算數，不會被彈回） | 完整 |
| 受益者：不參與開發的觀看者 | CAP-1、CAP-7 | 完整 |
| 受益者：未來的自己（回溯某功能走過哪些 stage） | 無明確承接能力 | **⚠ 部分** |

**覆蓋率：9／11 完整，2 部分（82%）。**

## 檢查二：Scope → Intent Backlog 對應

| 能力 | Proto-Unit | 判定 |
| --- | --- | --- |
| CAP-1 | PU-1 | 完整 |
| CAP-2 | PU-4 | 完整 |
| CAP-3 | PU-3 | 完整 |
| CAP-4 | PU-6 | 完整 |
| CAP-5 | PU-5 | 完整 |
| CAP-6 | PU-2 | 完整 |
| CAP-7 | PU-7 | 完整 |
| CAP-8 | PU-9 | 完整 |
| CAP-9 | PU-0 | 完整 |
| CAP-10 | PU-8 | 完整 |
| CAP-11 | PU-10 | 完整 |

**覆蓋率：11／11（100%）。無孤兒 Proto-Unit，無未落地的能力。**

## 檢查三：Scope 項目的可行性支撐

| 能力 | 可行性支撐 | 判定 |
| --- | --- | --- |
| CAP-1 | feasibility Q7／Q8（自動建立與確定綁定） | 有 |
| CAP-2 | feasibility Q2、技術可行性表「讀取 AI-DLC 進度」列 | 有 |
| CAP-3 | feasibility Q2／Q9 | 有 |
| CAP-4 | intent Q6；feasibility 技術可行性表未單獨列排程對帳一列，其可行性由「寫入看板狀態」列一併涵蓋 | 有（間接） |
| CAP-5 | feasibility 的外部查證 E4（框架具備對應輸出型別） | 有 |
| CAP-6 | feasibility Q10 | 有 |
| CAP-7 | feasibility Q4 定其存在，但建立欄位的可行性**未知**（U-2） | **⚠ 條件性** |
| CAP-8 | 單段文字，無技術風險 | 有 |
| CAP-9 | 其本身即為 RSK-7 的處置動作 | 有 |
| CAP-10 | feasibility Q6 | 有 |
| CAP-11 | **無本 intent 的 feasibility 評估**；依據來自 ADR-0012 已完成的推理（防迴圈三道防線、狀態欄位單向、反向一律開 PR） | **⚠ 缺** |

**9／11 有明確支撐，1 項為已宣告的條件性（CAP-7），1 項無本 intent 的評估（CAP-11）。**

## 警告

| # | 警告 | 性質 | 建議處置 |
| --- | --- | --- | --- |
| W-1 | 成功指標「可追溯」沒有任何能力明確承接。CAP-7 只呈現**目前** stage，不含歷史、時間戳與變更來源；工作流程執行紀錄雖含這些資訊，但那是附帶產物而非宣告的能力，且公開 repo 的執行紀錄有保存期限 | 部分可追溯（指標無承接） | 於 requirements-analysis（2.3）把此指標拆成可驗證的需求，並決定由誰承接：可能落在 CAP-5 的通報內容、CAP-7 的欄位設計，或需新增一項能力 |
| W-2 | 受益者「未來的自己」的痛點是**回溯歷史**，而全部十一項能力都只處理當下狀態，無一產生歷史軌跡 | 部分可追溯（受益者無承接） | 與 W-1 同源，一併於 requirements-analysis 處理 |
| W-3 | CAP-7 的可行性為條件性（U-2）；若建立欄位不可行且退回人工，其上線前置依賴的性質會從「機制自我完成」變為「外部人工」 | 已宣告的條件 | 已由 [Q1] 人工確認接受，指派 application-design |
| W-4 | **CAP-11 未經本 intent 的 feasibility 評估**。它於 Revision 1 由 ADR-0013 直接納入範圍，繞過了 feasibility 這一站；該站的技術可行性表、風險分析與 ADR-0006 四面向判定都不涵蓋 GitHub → repo 路徑 | 覆蓋缺口（新增） | 已由 [Q4] 人工確認接受並指派 application-design（U-6）；補評估須含 IAM 面重新判定 |

## 一致性檢查

- **無矛盾**：intent-statement、scope-document、intent-backlog 三者對範圍邊界的描述一致；Won't Have 三項未與任何 In Scope 能力重疊（原第四項「反向同步」已於 Revision 1 移出並成為 CAP-11）。
- **取代關係已顯式記錄**：D-7 取代原始描述的 README 定位、D-15 取代原本的推測式綁定、D-26 第四項由 Q8 補正。三處皆保留原答案並加註，未改寫已核可內容。
- **假設狀態變更已追蹤**：intent-capture 的憑證假設已在 feasibility 的 raid-log 標為被取代。
- **Revision 1 的取代關係已顯式記錄**：D-26 的反向同步排除項由 D-34（ADR-0013 決定 2）推翻，原紀錄以刪除線保留於 scope-document，未改寫。

## 判定

**通過（附四項警告）**。

W-1 與 W-2 是同一個缺口的兩面，且**不阻擋 phase 邊界**——它們是需求層的缺口，而 requirements-analysis（2.3）正是下一個 phase 內處理需求的站點，缺口在該站被承接是流程的正常運作而非遺漏。W-3 與 W-4 已分別由 [Q1] 與 [Q4] 人工確認接受。W-4 是本次 Revision 引入的新缺口——一個能力繞過 feasibility 直接進入範圍，其可行性依據來自他人的推理而非本 intent 的評估。它不阻擋 phase 邊界（INCEPTION 的設計工作正是補齊它的地方），但下游若把 ADR-0012 的推理當成已完成的評估，這個缺口會靜默消失。

未發現孤兒 artifact、未發現矛盾、未發現不可解的斷鏈。

## 人工核可

- [ ] 已檢視本驗證報告並接受四項警告（於 approval-handoff 的 gate 一併確認）

## Revision 1（2026-08-23）

**觸發**：ADR-0013 把 CAP-11 反向同步納入範圍，能力數由 10 增為 11。

**重算結果**：

| 檢查 | Revision 前 | Revision 後 |
| --- | --- | --- |
| Intent → Scope | 9／11 完整，2 部分 | **不變**（CAP-11 不承接「可追溯」與「未來的自己」，那兩項缺口與本次修訂無關） |
| Scope → Intent Backlog | 10／10 | **11／11** |
| Scope 項目的可行性支撐 | 9／10，1 條件性 | **9／11，1 條件性、1 無評估** |
| 警告數 | 3 | **4** |

**新增警告 W-4**：CAP-11 繞過 feasibility 直接入範圍。這是回跳修訂的固有後果——scope-definition 在 feasibility 下游，回跳到它並不會讓 feasibility 重跑。選擇不連帶回跳 feasibility 是 [Q4] 的明示決定（選項 B 即為「U-6 先回跳 feasibility」，未被選取）。
