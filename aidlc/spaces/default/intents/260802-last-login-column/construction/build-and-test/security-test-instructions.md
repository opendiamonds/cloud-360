# Security Test Instructions

## 本 intent 的安全面共四項，三項有自動化斷言、一項為人工

| # | 安全主張 | 驗證 | 能否真的失敗 |
|---|---|---|---|
| 1 | 分頁查詢參數在邊界被驗證，非法值不進查詢層（NFR-8） | `test_illegal_parameters_are_rejected_without_leaking_data`（7 種非法值皆 422 且回應不含 `items`）、`test_negative_values_never_reach_the_query_layer` | ✅ |
| 2 | 授權矩陣變更是**單向**的（只開 `Security_Reviewer` 的 `J3a:view`） | `test_j3a_view_permission.py` 的 allow 1 ＋ deny 5 | ✅ |
| 3 | 完整 API 地圖不得對未認證訪客公開 | CI 的 `Spec must not be served statically`（`dist/` 內不得出現 `openapi*`） | ✅ |
| 4 | 分頁不改變任何角色的可見資料範圍 | **人工** —— 靜態檢查清單端點的授權依賴鏈未變 | ❌ |

## 為何第 1 項的斷言不只是「回 422」

非法值若原樣進入查詢層，**SQLite 對 `LIMIT -1` 會回傳整表剩餘** —— 也就是說「不驗證」的後果不是報錯，而是**靜默地把整份清單交出去**，正是 NFR-8 要防的暴露面。故該測試除了斷言 422，另斷言「回應筆數不超過每頁筆數上限」這條**不變量** —— 後者在「照收非法值並回整表」的實作上會紅，前者不會。

## 為何第 2 項需要 deny 側

只驗「`Security_Reviewer` 可以」的單向測試，對「把整欄 `J3a.can_view` 都翻成 `true`」這種錯誤照樣通過。deny 側逐一斷言 `Developer`／`Project_Editor`／`FinOps_Analyst` **仍然不可**檢視，且 `Security_Reviewer` 的 `edit`／`review`／`J3b` **未被一併開啟**。

## 第 3 項已以刻意違反實測

把規格檔複製進 `dist/` 後該檢查確實命中並 `exit 1`，移除後回到通過。**不刻意弄壞一次就無從得知 gate 是否真的會失敗。**

## 三道 CI gate 的有效性皆已實測

| Gate | 乾淨時 | 刻意違反時 |
|---|---|---|
| OpenAPI 規格漂移 | exit 0 | **exit 1** |
| 前端型別漂移 | exit 0 | **exit 1** |
| 規格不得被靜態供出 | 通過 | **命中並 exit 1** |

## 不在本 intent 處理的既有安全落差（如實記載，不使其惡化）

| 項目 | 狀態 |
|---|---|
| 稽核軌跡易失性（權限變更記錄保存期約等於兩次部署間隔） | requirements C-7 已記為已知限制；本 intent 產生一筆這樣的記錄，**不使其惡化亦不修復** |
| `validate_repo_contract.py` 的 secret 掃描看不到 `backend/`／`frontend/` | `team.md` 已記載為既有機制落差；本 intent 未擴大該落差 |
| 「誰查看了活動資料」不記錄 | 本站 Q2=A 的定案，判定理由見 U2 的 `security-requirements.md` S-3 |
