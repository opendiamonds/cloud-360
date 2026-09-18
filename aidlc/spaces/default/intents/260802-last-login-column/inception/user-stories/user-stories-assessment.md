 

# User Stories 適用性判定

<!-- Stage: user-stories（Inception 2.4）· 依 stage 檔 Step 2 的 condition 條款逐項判定。 -->

判定

**Execute。**

## 逐項對照 condition 條款

stage 檔的 condition 為：「Execute when user-facing features, multiple personas, complex business logic, or cross-team work is involved. Skip for pure refactoring, isolated bug fixes, infrastructure-only changes, or developer tooling.」

| 條款                             | 是否成立      | 依據                                                                                                                                                                        |
| -------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **User-facing features**   | ✅ 成立       | 本 intent 在使用者管理頁新增可見欄位、新增逾期視覺標示、改造小螢幕佈局，皆為終端使用者直接感知的變更（requirements FR-2、FR-3、FR-5）                                       |
| **Multiple personas**      | ✅ 成立       | 兩類已確認受益者：`Platform_Admin`（日常帳號管理）與 `Security_Reviewer`（存取稽核），兩者使用同一畫面但目的與動線不同（intent-statement、user-flow 的 Flow 1／Flow 2） |
| **Complex business logic** | ⚠️ 部分成立 | 邏輯本身不複雜（單一時間欄位＋門檻比較），但存在跨層的權限判定與節流語意（requirements FR-1.3、FR-4）                                                                       |
| **Cross-team work**        | ❌ 不成立     | 單一決策者＋AI agents 執行，無跨團隊協調需求（team-formation 依 scope 跳過）                                                                                                |
| Skip：純重構                     | ❌ 不適用     | 本 intent 新增能力，非行為不變的重構                                                                                                                                        |
| Skip：孤立 bug fix               | ❌ 不適用     | 非修復既有缺陷（既有缺陷已明確排除於範圍外，見 requirements）                                                                                                               |
| Skip：純基礎設施                 | ❌ 不適用     | 變更觸及前端呈現層與使用者流程                                                                                                                                              |
| Skip：開發者工具                 | ❌ 不適用     | 使用者為平台的管理與稽核角色，非開發者工具                                                                                                                                  |

四個 Execute 條款中兩項明確成立、一項部分成立；四個 Skip 條款全數不適用。**判定為 Execute。**

## 故事最能增值之處

本階段的 user stories 對下列三處提供的價值高於 requirements 單獨提供的：

1. **兩類受益者的動線差異**：`Security_Reviewer` 是「查驗全表、抄錄證據」的批次掃讀，`Platform_Admin` 是「處理特定帳號時順帶參考」的單點查看。同一個欄位服務兩種截然不同的使用節奏，requirements 的功能條列無法表達這個差異，故事可以。
2. **無紀錄態的使用者處境**：上線初期**所有帳號**都是無紀錄態（requirements C-1），這意味著功能上線後有一段時間對稽核毫無幫助。這個處境需要以故事形式讓決策者看見，而非藏在約束條款裡。
3. **驗收標準的可執行化**：practices-discovery 新增的三項測試底線（授權雙向測試／端點測試／e2e 斷言）需要落到具體的 Given/When/Then，故事的 AC 是其自然載體。

## 與上游的關係

本判定不改變任何已核可範圍。故事集合完全承接 requirements 的 FR-1～FR-5（對應 scope 的五項 Must），不新增能力、不擴大邊界。

## Revision 1（2026-08-11）— PU-6 使用者清單分頁

**判定不變：Execute。** scope-document Revision 2 新增的 Must 能力 (f)（使用者清單分頁）不改變上表任何一格的判定，反而加強其中兩項：

| 條款 | Revision 1 後的變化 |
| --- | --- |
| **User-facing features** | 更強 —— 分頁控制是本 intent 新增的**唯一可觸發互動元件**（既有變更皆為顯示層），使用者要主動操作它 |
| **Multiple personas** | 不變 —— 兩類受益者共用同一分頁控制，`Security_Reviewer` 的逐帳號查驗工作流對「處置後停在原頁」（AC-5.6）的敏感度明顯高於 `Platform_Admin` |
| **Complex business logic** | 不變（仍為部分成立）—— 分頁本身不含業務規則；複雜度來自跨層（後端序列化、型別契約、前端三層）而非邏輯 |
| **Cross-team work** | 不變（不成立） |
| 四個 Skip 條款 | 全數仍不適用 |

**本輪 mob 的實際增值**（可核對，非宣稱）：三位協作者盲審共提出 **29 項 OBJECT**（design 12、developer 7、quality 10），其中 **3 條 AC 被查出恆真或不可二元判定**（AC-5.2 的存在性斷言、AC-5.5 的兩個互斥結果、AC-5.8 的頁次不進入判定路徑），依 `project.md` 的 correction 改寫落點而非刪除；**2 條 AC 為 mob 新增**（AC-5.10 切換期間控制不消失、AC-5.11 非分頁參數不改變結果），前者是三個已核可決定的算術結果、後者補上 FR-6.7 在契約層唯一正向可測的落點；另更正 **1 項事實錯誤**（DoD 原宣稱 e2e「無可執行驗收路徑」，實際既有 e2e 已在用公開註冊端點建帳號）與 **1 項過度宣稱**（追溯表原稱 C-9 已由兩條 AC 涵蓋，實際型別契約同步無 AC 落點）。

這些是 requirements 層看不出來的：三條恆真 AC 在需求文件上都讀得通，要對照**實作路徑**（`isOverdue` 由呼叫端算好傳入、Pydantic 預設值、SQLite 對負數 LIMIT 的行為）才看得出它們驗不到東西。
