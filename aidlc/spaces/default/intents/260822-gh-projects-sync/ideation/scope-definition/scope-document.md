# Scope Document — AI-DLC 與 GitHub Projects 的進度同步

<!-- Stage: scope-definition（Ideation 1.4）· 來源標籤定義見 scope-definition-questions.md 的 ## Sources。
     [Q<n>] 指本 stage 的已選答案；[intent:*]／[feas:*] 指上游 artifact；[memory:M*] 指 memory 層規則。 -->

## 上游輸入

- **intent-statement**（`../intent-capture/intent-statement.md`）：問題陳述、四類受益者、三項成功指標與使用者確認的產品邊界。
- **feasibility-assessment**（`../feasibility/feasibility-assessment.md`）：conditional GO 判定、7 條風險、ADR-0006 四面向判定。
- **constraint-register**（`../feasibility/constraint-register.md`）：技術 9 條、組織與流程 6 條、法規與政策 4 條約束。

## 範圍邊界

### In Scope

| # | 能力 | 分級 | 來源 |
| --- | --- | --- | --- |
| CAP-1 | 綁定建立：intent 誕生時自動開 issue、加入看板、設 In progress，並把 issue 編號寫回 intent 的紀錄 | Must | [Q2] |
| CAP-2 | 推送觸發的狀態同步 | Must | [Q2] |
| CAP-3 | PR 觸發的狀態同步（優先於推送） | Must | [Q2] |
| CAP-4 | 排程對帳：低頻掃描並補齊差異 | Must | [Q2] |
| CAP-5 | 失敗通報：紅燈＋自動開 issue；對帳不一致亦視為失敗 | Must | [Q2b] |
| CAP-6 | 寫入前回讀確認：不符即中止寫入並開 issue | Must | [Q2b] |
| CAP-7 | 細粒度 stage 進展外置至看板自訂欄位，欄位由機制自動建立；框架不支援時退回人工建立 | Must | [Q4] [Q9] |
| CAP-8 | README 增加一段指向 Project #16 的指路文字 | Must（單段文字，不另分級） | [intent:Q11] |
| CAP-9 | 憑證可行性實測 | Must，但**不構成交付批次** | [Q2b] [Q3] |
| CAP-10 | 驗證層：映射邏輯 dry-run 斷言 ＋ 真實測試項目端到端 | Must | [Q2b] |
| CAP-11 | **反向同步**：定時把看板端的狀態變更（含人工拖動卡片）拉回並開 PR 更新 record；含防迴圈機制 | Must | ADR-0013 決定 2 |

全部十一項均列為 Must（CAP-11 由 Revision 1 新增）[Q2] [Q2b] [ADR-0013]。本專案的既有實務接受此形狀，並以 MoSCoW 加依賴序表達優先，不做 WSJF／RICE 數值評分——單一決策者且依賴序已定時，相對分數沒有真實輸入，屬虛假精確（`project.md ## Corrections`）。

### Won't Have（本次明確排除）

| # | 排除項 | 來源 |
| --- | --- | --- |
| ~~W-1~~ | ~~反向同步~~ — **已於 Revision 1 移出排除清單並納入範圍（CAP-11）**，依據 ADR-0013 決定 2。原列入紀錄保留作為決策軌跡 | [Q5] → ADR-0013 |
| W-2 | 跨 repo 支援：其他 repo 的 intent 也同步到本看板 | [Q5] |
| W-3 | 自動關閉 issue：完成時除設 Done 外亦關閉對應 issue | [Q5] |
| W-4 | 既有 71 個項目的一次性對正（歷史漂移修正） | [Q5]（經 [Q8] 補上）[Q7] |

W-4 與 [intent:Q12] 一致：未綁定的既有項目本就不進一致率分母，本次不碰它們，並明確宣告排除以免下游自行補上。

### 未承諾（不在範圍、不在排除清單）

- 無。本輪的候選排除項均已明確歸入 In Scope 或 Won't Have。

## 最小可行範圍與交付意向

- 使用者選擇**一次做完全部、不分批** [Q1]。此為**範圍層的交付意向**，宣告的是「這些能力合起來才算完成」（Revision 1 後為十一項），而非決定 Construction 要切成幾個 Bolt。
- Bolt 切分屬 delivery-planning（2.8）的職責。該站會面對一個真實張力：`org.md ## Way of Working` 的短生命週期分支（1–2 天內解決）與「十一項全 Must 一次交付」在 deploy-on-merge 之下正面相交。本站不預先替該站決定，但明記此張力存在，避免下游把 [Q1] 讀成「必須單一 Bolt」。
- 排序偏好為 **risk-first**，但 CAP-9 不佔交付批次 [Q3]：它是 application-design 展開前的一次性驗證動作。

## 價值流

從能力到受益者成果的路徑（本節依 `project.md ## Corrections` 併入本文件表達，不自創檔案）：

```
intent 誕生
   |
   v
CAP-1 綁定建立 ---> 看板出現對應項目（設 In progress）
   |                          |
   |                          v
   |                 受益者：只看看板的觀看者第一次看得到這件事存在 [intent:Q10]
   v
stage 推進（本機）--push--> CAP-2 狀態同步 --+
                                            |--> CAP-6 寫入前回讀 --> 看板狀態正確
PR 開啟／合併 --------------> CAP-3（優先）--+
   |                                            |
   |                                            v
   |                              受益者：開發者不再手動改狀態 [intent:Q2]
   v
CAP-7 細粒度進展 ---> 自訂欄位顯示目前 stage
   |
   v
CAP-4 排程對帳 ---> 發現落差 ---> CAP-5 失敗通報（紅燈＋開 issue）
                                       |
                                       v
                        受益者：錯誤不再靜默，可追溯到 intent 與 stage [intent:Q3]

看板端狀態變更（人拖卡片）
   |
   v
CAP-11 反向同步 ---> 開 PR 更新 record ---> 人審後合併
   |
   v
   受益者：協作者在看板上的操作算數，不會被下次同步彈回 [ADR-0013]
```

<!-- Text fallback: intent 誕生後由 CAP-1 建立綁定並在看板產生項目；其後兩條觸發路徑（推送經 CAP-2、PR 經 CAP-3 且優先）都先通過 CAP-6 的寫入前回讀才寫入看板；CAP-7 另以自訂欄位呈現細粒度進展；CAP-4 定期對帳，發現落差交由 CAP-5 通報。四個受益者成果分別掛在 CAP-1（觀看者看得到）、CAP-2/3（開發者免手動）、CAP-4/5（錯誤不靜默）與 CAP-11（協作者在看板上的操作算數）。CAP-11 是反向路徑：看板端的狀態變更由定時同步拉回並開 PR，人審後才進 record。 -->

## 上線前置依賴

以下事項機制無法自我完成，未完成前對應能力無法運作：

| # | 前置 | 阻擋 | 來源 |
| --- | --- | --- | --- |
| P-1 | 於組織下建立應用程式、設定組織層看板讀寫權限、產生私鑰並安裝至本 repo | CAP-1～CAP-7 的任何實際寫入，以及 CAP-9 本身 | [feas:DEP-1] |
| P-2 | 將應用程式識別碼與私鑰存入 repo 的變數與 secret | 同上 | [feas:DEP-2] |
| P-3 | CAP-9 的實測結果 | application-design 對載體的最終定案 | [Q3] [feas:RSK-7] |
| P-4 | 看板自訂欄位存在（自動建立或退回人工） | CAP-7 | [Q9] |
| P-5 | 反向同步所需的權限（回寫 repo 一律開 PR，不直接推 `ut`） | CAP-11 | ADR-0013 沿用 ADR-0012 第 5 點 |

## Assumptions & Open Questions

- [Q9] 選擇由機制自動建立看板自訂欄位，但**框架文件的安全輸出清單並未列出建立欄位的型別**（僅見建立看板與建立檢視）。CAP-7 的可行性因此與 CAP-9 同屬待驗證，而非已確認；若不可行則依 [Q9] 退回人工建立。 [assumption]
- P-4 的退路（人工建立）尚未指定由誰在何時完成；若自動建立不可行，此項會成為與 P-1 同類的外部人工依賴。 [assumption]
- 新增自訂欄位會使既有 71 個項目該欄位為空；此空值是否對看板使用者造成困擾未經確認。 [assumption]
- 反向同步（CAP-11）未經本 intent 的 feasibility 評估；其可行性依據來自 ADR-0012 已完成的推理（防迴圈三道防線、狀態欄位單向、反向一律開 PR），而非本站上游的技術可行性表。指派 application-design 補齊，包含 ADR-0006 四面向對這條新路徑的重新判定（特別是 IAM——回寫 repo 需要比目前更大的權限面）。 [assumption]
- [Q1] 的「一次做完全部」與 `org.md` 短生命週期分支實務的張力，其解法留待 delivery-planning 決定；本站不預設 Bolt 數量。 [assumption]
- CAP-9 被列為 Must 但不構成交付批次 [Q3]，其產物（實測結論）如何在 Construction 留下可追溯的證據尚未定義。 [assumption]

## Revision 1（2026-08-23）

**觸發**：reverse-engineering 開始前發現 ADR-0012（Accepted 2026-08-16）涵蓋本 intent 主題卻全程未被引用。其對反向同步的論證——「repo 永遠贏、GitHub 純鏡像」等於告訴協作者不要在看板上操作，而拖動的卡片會被下次同步彈回原位，比沒有同步更糟——具決定性且本站原先未曾考慮。經使用者裁決後開立 ADR-0013。

**改動**：

- 新增 **CAP-11 反向同步**（Must），對應新增 **PU-10**。
- **W-1 移出 Won't Have**，原列入紀錄以刪除線保留，不改寫。
- 新增前置依賴 **P-5**（反向同步的權限與 PR 化路徑）。
- 統計數字由「十項」更新為「十一項」。

**未改動**：映射層級、承載形式、階段順序三項經 ADR-0013 確認與本站原決定一致，維持不變。Q1～Q4、Q6～Q9 的答案不受影響。

**未解事項**：反向同步在 feasibility 階段未被評估——該站的技術可行性表、風險分析與 ADR-0006 四面向判定均不涵蓋 GitHub → repo 的路徑。ADR-0013 沿用 ADR-0012 已推理完成的防迴圈三道防線與 PR 化控制作為替代依據，但那不等同於本 intent 自己的可行性評估。此缺口記入下方 Assumptions，並指派 application-design 補齊。
