# Intent Backlog — 帳號最後活動時間（稽核欄位）

<!-- Stage: scope-definition（Ideation 1.4）· 來源標籤定義見 scope-definition-questions.md 的 ## Sources。
     Proto-Units 為 inception units-generation 的前身：以能力為單位，不預作技術切分。 -->

## 上游輸入

- 能力集與邊界承襲本階段 `scope-document.md`，其上游為 **intent-statement**（問題與受益者）、**feasibility-assessment**（可行前提）與 **constraint-register**（約束）。
- market-research 已依 scope 跳過，無市場面輸入。

## Proto-Units（依交付順位排列）

### PU-1 記錄帳號最後活動時間 — Must

- **價值**：稽核證據的資料來源；沒有它其餘能力皆為空殼 [intent:Q1]
- **內容**：任何以有效憑證發出的請求都更新該帳號的最後活動時間；只留最後一次，資料模型預留歷史擴充路徑 [feas:Q1] [intent:Q9]
- **依賴**：無（鏈頭）
- **DoD 要點**：含對應的部署資產同步（`schema_rbac.sql`／`DEPLOY.md`）[Q4] [memory:M1]；含寫入頻率緩解手段的設計決定（承 feasibility raid-log R1，設計階段必答）
- **順位理由**：dependency-first 鏈頭 [Q2]，亦為不確定性最高的一項

### PU-2 管理介面顯示欄位 — Must

- **價值**：`Platform_Admin` 在管理介面直接看到帳號活躍度，不需另行查詢 [intent:Q10/Q12]
- **內容**：使用者管理介面為每個帳號顯示最後活動時間；無紀錄顯示「無紀錄」[feas:Q2]
- **依賴**：PU-1（無資料無可顯示）
- **DoD 要點**：顯示值可依受控測試驗證（比對任何活動的時刻）[feas:Q6/Q6a]

### PU-3 逾期未活動視覺標示 — Must

- **價值**：稽核查驗「帳號是否仍在使用」的即讀訊號 [intent:Q3]
- **內容**：超過 N 天未活動的帳號帶視覺標示；空值（無紀錄）不套用標示 [feas:Q2]
- **依賴**：PU-2（標示疊加在顯示之上）；**N 值於 requirements-analysis 定案為上線前置** [intent:Q14]
- **DoD 要點**：N 為固定值，不做可設定介面（Won't Have）[Q3]

### PU-5 行動響應式卡片改造 — Must（Revision 1 新增）

- **價值**：小螢幕上使用者管理頁可用，含新欄位與逾期標示的完整呈現 [rm:Q5]
- **內容**：小螢幕改為卡片式佈局、桌面維持表格；無障礙底線 WCAG 2.1 AA 全裝置適用（對比、鍵盤可達、screen reader 可讀）[rm:Q5] [rm:Q5a]
- **依賴**：PU-2（欄位存在）、PU-3（標示樣式定案）— 卡片改造涵蓋含新欄位與標示的最終欄面
- **DoD 要點**：既有頁面功能（角色調整、啟停用、授權操作）在卡片佈局下全數可用；前端回歸驗證涵蓋既有功能；純前端改造，不觸發部署資產同步
- **順位理由**：依賴鏈末端；改造以最終欄面為輸入，避免重工

### PU-6 使用者清單分頁 — Must（**Revision 2 新增**）

- **價值**：清單回應不再隨帳號數線性成長；管理頁在帳號數成長後仍可用 [nfr:U2-Q1]
- **內容**：使用者清單端點不再一次回傳全部帳號；回應與**兩種佈局**（表格、卡片）皆支援分頁。**分頁是本次新增的唯一清單互動** —— 不連帶解除「依最後活動時間排序／篩選」的排除
- **依賴**：**技術上無前置**（清單端點為既有功能，不需等 PU-1〜3）。但與 **PU-5 有重工關係**，見下方順位理由
- **DoD 要點**：回應契約變更已反映於前端型別；表格與卡片兩種佈局的分頁互動皆可用；純應用層變更，**不觸發部署資產同步**（無 schema 或 seed 變更）
- **順位理由**：**必須在 PU-5 之前定案分頁互動**。卡片佈局若先以「一次拿到全部」為前提設計完成，加分頁時要重做一次；反之先定分頁形式，PU-5 只需設計一次。這不是技術依賴，是**避免重工的排序約束**

### PU-4 Security_Reviewer 檢視權限開通 — Must

- **價值**：稽核受益者親自取用證據，免經轉手 [intent:Q10]
- **內容**：開通使用者管理介面的檢視權限；權限粒度維持現狀（story × action），4 個管理類角色可見 [intent:Q11/Q12]
- **依賴**：與 PU-1～3 無技術依賴，可平行；排序殿後 [Q2]
- **DoD 要點**：含對應的部署資產同步（權限 seed 值變更屬 M1 觸發條件）[Q4] [memory:M1]；風險接受已記入 feasibility raid-log R3 [feas:Q7]

## 排序與依賴總覽

```
PU-1 --> PU-2 --> PU-3 --> PU-5
                   ^          ^
                   |          | (分頁形式先定案，避免卡片重工)
                   |        PU-6
                   | (N 值定案 @ requirements-analysis)
PU-4 ---------------------- 平行，排序殿後
```

<!-- Text fallback: PU-1 至 PU-3 至 PU-5 為線性依賴鏈（PU-5 卡片改造以最終欄面為輸入）；PU-3 另需 N 值於 requirements-analysis 定案；PU-6 分頁與該鏈無技術依賴，但必須在 PU-5 之前定案分頁互動，否則卡片佈局要設計兩次；PU-4 與鏈無技術依賴、平行進行但排序殿後。 -->

**六項**全為 Must、一起上線才算完成 [Q1] [rm:Q5a]（PU-6 見 **Revision 2**）；不設 Should／Could 層。細部 Unit 切分與 Bolt 經濟排序交由 inception 的 units-generation 與 delivery-planning。

### PU-6 對既有排序的影響（Revision 2 如實記載）

現行的交付順位是 dependency-first。PU-6 加入後，**唯一的排序約束是「PU-6 在 PU-5 之前」**，且該約束的性質是**避免重工**而非技術依賴 —— units-generation 與 delivery-planning 若判斷有更好的經濟排序，可覆寫它，但須記明如何避免卡片佈局重做。

## Assumptions & Open Questions

- [assumption] （**Revision 2 新增**）PU-6 的分頁形式（頁碼式／游標式、每頁筆數、回應是否包 envelope）屬設計決定，留 application-design 定案
- [assumption] （**Revision 2 新增**）PU-6 與 PU-3 的互動 —— 逾期帳號可能散落在多頁，稽核者是否需要跨頁彙總，留 refined-mockups 評估
- [assumption] （**Revision 2 新增**）PU-6 對 PU-5 的排序約束是避免重工而非技術依賴，下游可在記明重工緩解方式的前提下覆寫

- [assumption] PU-3 的 Must 地位使 N 值定案成為整體上線的前置條件 [Q1] [intent:Q14]；若 requirements-analysis 未定 N，Must 集合不可完整交付
- [assumption] 五項 proto-unit 的粒度是否即為最終 Unit 切分，由 units-generation 檢驗；本清單不預作技術切分承諾
- [assumption] （開放問題）PU-1 的寫入頻率緩解手段（節流／彙整／非同步）尚未選定，承 feasibility-assessment 的 R1，設計階段必答
- [assumption] PU-5 的前端回歸驗證涵蓋面（既有管理頁功能在卡片佈局下的測試範圍）尚未界定，留待 inception [rm:Q5]
