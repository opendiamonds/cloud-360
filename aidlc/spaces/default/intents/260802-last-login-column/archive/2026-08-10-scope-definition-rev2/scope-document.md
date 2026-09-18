# Scope Document — 帳號最後活動時間（稽核欄位）

<!-- Stage: scope-definition（Ideation 1.4）· 來源標籤定義見 scope-definition-questions.md 的 ## Sources。
     [Q<n>] 指本 stage 問題檔的已選答案；[intent:*]／[feas:*] 指上游 artifact 的已確認決定。 -->

## 上游輸入

- **intent-statement**（`../intent-capture/intent-statement.md`）：問題陳述、受益者與已確認的產品邊界（`feature`）。
- **feasibility-assessment**（`../feasibility/feasibility-assessment.md`）：conditional GO 結論與四個前提（活動語意定錨、空窗接受、套用路徑、風險接受）。
- **constraint-register**（`../feasibility/constraint-register.md`）：技術／組織／法規約束，本文件的邊界劃定以其為底。
- market-research 已依 scope 跳過，無市場面輸入。

## 範圍邊界

### In scope（全部 Must，一起上線才算完成 [Q1]）

| # | 能力 | 說明 | Source |
| --- | --- | --- | --- |
| (a) | 記錄帳號最後活動時間 | 任何以有效憑證發出的請求都更新該帳號的最後活動時間；只留最後一次 | [feas:Q1] [intent:Q9] |
| (b) | 管理介面顯示該欄位 | 使用者管理介面為每個帳號顯示最後活動時間；無紀錄者顯示「無紀錄」 | [intent:Q3] [feas:Q2] |
| (c) | 逾期未活動視覺標示 | 超過 N 天未活動的帳號帶視覺標示（N 於 requirements-analysis 定案；空值不套標示） | [intent:Q3] [feas:Q2] |
| (d) | `Security_Reviewer` 檢視權限開通 | 開通使用者管理介面的檢視權限，使稽核受益者可直接取用 | [intent:Q10/Q12] |
| (e) | 行動響應式卡片改造 | 使用者管理頁在小螢幕改為卡片式佈局（桌面維持表格），含新欄位與逾期標示的呈現；無障礙底線為 WCAG 2.1 AA、全裝置適用 | [rm:Q5] [rm:Q5a]（見 Revision 1） |

部署資產同步義務（`schema_rbac.sql`／`DEPLOY.md` 同步更新，blocking）**內建於 (a) 與 (d) 的 Definition of Done**，不另立項 [Q4] [memory:M1]。(e) 為純前端改造，不觸發部署資產同步。

### Won't Have（本次明確排除 [Q3]）

| 排除項 | 理由 |
| --- | --- |
| 登入／活動歷史紀錄 | 僅預留資料模型擴充路徑，不實作 [intent:Q9] |
| 門檻 N 的可設定介面 | N 為固定值（值待定案），不做管理介面 [intent:Q14] |
| 欄位級權限控制 | 維持 story × action 權限粒度 [intent:Q11] |
| 依最後活動時間排序／篩選 | 顯示即可，不做互動排序／篩選 [intent:Q3] |

### 未承諾（不在範圍、亦未列入排除）

- 稽核報表匯出：未被任何已選選項納入範圍，使用者亦選擇不將其列入 Won't Have [Q3]；狀態為「未承諾」，未來要做需重新立項。

## MoSCoW 總表

- **Must**：(a) 記錄、(b) 顯示、(c) 視覺標示、(d) 權限開通、(e) 行動響應式卡片改造 — 五項缺一不可 [Q1] [rm:Q5a]。
- **Should／Could**：無 — 使用者明確選擇不設次級優先層 [Q1]。
- **Won't**：上表四項排除項 [Q3]。

## 價值流

```
[使用者以有效憑證活動] --> [系統記錄最後活動時間] --> [管理介面顯示 + 逾期標示]
                                                        |
                                                        v
                                  [管理類角色（含 Security_Reviewer）判讀帳號活躍度]
                                                        |
                                                        v
                                  [存取稽核判定「帳號是否仍在使用」-> 帳號治理決策]
```

<!-- Text fallback: 使用者活動被系統記錄為最後活動時間，經管理介面顯示與逾期標示，供含 Security_Reviewer 在內的管理類角色判讀，最終支撐存取稽核與帳號治理決策。 -->

價值終點是 intent-statement 所載的稽核查驗能力：`Security_Reviewer` 取得帳號活動證據、`Platform_Admin` 免另行查詢 [intent:Q10/Q12]。

## 排序原則

**Dependency-first** [Q2]：依賴鏈 (a) → (b) → (c) → (e) 依序交付（卡片改造涵蓋含新欄位與標示的最終欄面，故排在 (c) 之後），(d) 權限開通與依賴鏈無技術耦合、排序殿後。細部的 Bolt 切分與經濟排序留給 delivery-planning，本文件只固定依賴序。

## Assumptions & Open Questions

- [assumption] 視覺標示 (c) 為 Must 且門檻 N 未定 [Q1] [intent:Q3]；「N 於 requirements-analysis 定案」因此成為上線前置依賴，N 不定案則 Must 集合不可完整交付
- [assumption] 稽核報表匯出處於「未承諾」狀態 [Q3]：不在範圍、不在排除清單；本階段不推定其未來去向
- [assumption] 活動資料保存上限的值未定（承 feasibility-assessment 的既有 assumption），與本範圍的 (a) 能力共享同一個 requirements-analysis 定案時點 [feas:Q4]
- [assumption] 卡片改造 (e) 動到既有使用者管理頁的表格架構，對既有功能（操作、啟停用等）構成前端回歸風險 [rm:Q5]；回歸涵蓋面於 PU-5 的 DoD 落實，具體測試範圍留待 inception 界定
