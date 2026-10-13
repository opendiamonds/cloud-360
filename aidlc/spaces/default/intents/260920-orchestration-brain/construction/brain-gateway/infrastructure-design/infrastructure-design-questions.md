# Infrastructure Design 問題檔 — `U13 brain-gateway`

> 本站出 **1 題**（`IG1`）。其餘指派事項的做法都由上游定案與 repo 現況決定，不需使用者在多個可行方案間選擇；逐項判定見下表與
> `infrastructure-specification.md` 第十一節。**本站仍須派審查員**：基礎設施面有真實內容（逐跳透傳查證、同批約束、啟動語意改變、
> 一處 CI 檢查的空轉揭露），不屬「無標的、by-reference」的精簡情形。

## 一、上游已定案、本站不重問

| 事項 | 定案出處 |
|---|---|
| 子協定方案（雙子協定、只回送 `cloud360.brain.v1`） | functional-design `[GW1]`=A |
| 連線數、頻率、訊框上限在**應用層**設（不交部署層） | nfr-requirements `[GWN1]`=A；`nfr-requirements-questions.md:64-65` 的選項 D 未被選 |
| 第 11 條連線拒絕、舊分頁不受影響 | nfr-design `[GWND1]`=A |
| 所有數值為模組常數、不新增環境變數 | `NFR13.44` |
| 單一行程、embedded 部署 | `K-12`；`functional-spec.md:22` |
| `U13` 與 `U14` 同屬 B6 | delivery-planning `[D3]`=B |
| 空金鑰時入口頁的**行為**（每輪 `error(INTERNAL_ERROR)`，不降級） | functional-design `BR67.1`、`H-21` |

## 二、stage 檔六個 focus area 的逐項判定

| focus area | 判定 | 依據（本站實測） |
|---|---|---|
| 部署策略 | **有標的：同批約束與事後實測** | 本 intent 83 個 commit 皆未進 `ut`；DEMO 與 `U13` 同路徑；子協定透傳只有部署後才能在 Cloudflare 那兩跳實測。見 `infrastructure-specification.md` 第四、五節 |
| 運算／儲存／網路 | **無新資源；有一項查證** | embedded 於既有 uvicorn 行程；`location /api/` 已承載 WS 升級（`frontend/nginx.conf:16-32`）；nginx 這一跳靜態判定透傳，Cloudflare 兩跳未查證 |
| 監控 | **無新管線** | 只用既有容器 log；查詢指令見 `monitoring-design.md` 第四節 |
| CI/CD | **無新 job；三個實作約束** | 既有 `backend` job 撿得到新測試；C-a／C-b／C-c 見 `cicd-pipeline.md` 第二節 |
| Secrets | **有標的：`OPENROUTER_API_KEY` 的部署面要不要擋（`IG1`）** | `render-env.sh:21`／`:109` 為 optional；`deploy.yml:71-91` 不檢查它 |
| 擴縮 | **無標的** | 單一行程假設；上限皆為應用層常數（`NFR13.17`／`NFR13.18`） |

## 三、問題

### IG1. staging 部署時，`OPENROUTER_API_KEY` 為空要不要擋下部署？（`OPEN-GW13-7`，承接 `intent-router` 的 `I-1`）

**背景**：今天這把金鑰在部署流程裡是「選填」（`render-env.sh:21` 註解逐字「A1 design agent; empty disables generation」，
`:109` 為 `${OPENROUTER_API_KEY:-}`），部署前的必要 secret 檢查（`deploy.yml:71-91`）只檢查 `POSTGRES_PASSWORD`、`JWT_SECRET`、
`REDIS_PASSWORD` 三個。`U13` 上線後，金鑰為空的後果會從「A1 不能產圖、A3／優化失敗或降級」擴大成「**大腦入口頁的每一則訊息
都回『內部錯誤』**」——因為每一輪的第一步就是呼叫計費模型分類，沒有不經模型的快路徑。這個行為（大聲失敗、不猜）已在
functional-design 定案；本題只決定**部署流程要不要事先攔住這個狀態**。無論怎麼選，CI 的測試 stack 仍刻意用空金鑰
（`docker-compose.test.yml:83`），不受本題影響。

A) **改為部署時必要：金鑰為空就不部署**（建議）：只在 `deploy.yml` 的 deploy job 必要 secret 檢查（`:71-91`）加
   `OPENROUTER_API_KEY`；**不**加進 `render-env.sh` 的拒絕清單（`:71` 附近），使 rollback job（它只經 `render-env.sh`，
   `deploy.yml:617`）在金鑰被清空時仍能回滾。同步改寫 `render-env.sh:21` 的註解、`deploy/.env.example` 與 `DEPLOY.md:24` 的說明。
   得到：入口頁不可能在「金鑰沒設」的狀態下被部署上線；失敗發生在部署當下、訊息指名缺哪個 secret。
   代價：A1／A3／成本建議原本在無金鑰時「降級但照常部署」的行為消失——secret 一旦被清空，**整個 staging 都不會更新**
   （包括與 LLM 無關的修正）。只檢查「是否為空」，**無法**發現金鑰已失效或餘額用盡（那仍表現為每輪內部錯誤）。
B) **維持選填，但部署時發出看得見的警告**：在 deploy job 加一步，金鑰為空時以 `::warning::` 寫進 Actions 摘要並帶進既有的
   Slack 部署通知；不擋部署、不印出金鑰值。
   得到：既有的降級部署行為不變；有人看部署通知就會知道入口頁不能用。代價：多一個 workflow 步驟；警告可被忽略，
   入口頁仍可能在全面失敗的狀態下上線。
C) **維持現狀，只改文件**：`render-env.sh:21` 註解、`DEPLOY.md:24` 與 `LOCAL-DEV.md` 的功能表補上「入口頁每輪失敗」。
   得到：零管線變更。代價：唯一的發現途徑是使用者回報或有人去看 log 的 `outcome=error:INTERNAL_ERROR`（`monitoring-design.md`）。
D) **其他**：請說明。

[Answer]: A <!-- 2026-10-13T01:56:38Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->

### IG2. DEMO 後端在合併進 `ut` 前的處置（產出時發現，追加）

DEMO `brain_router.py:275` 把 `bearer.<jwt>` 回送到回應標頭，而它與其他單元在同一分支、尚未進 `ut`。若本分支分批合併，DEMO 可能早於 U13 部署到公開 staging。

A) **第一次合併進 `ut` 就移除 DEMO 後端（或關掉回送 token 的寫法）**（建議）：不論之後一次或分批合併都安全；代價是 U13／U14 完成前示範頁不能用。
B) 整個 intent 完成後一次合併。
C) 先改 DEMO 不回送 token，示範頁前端配合帶兩個子協定（計畫外修改）。

[Answer]: A <!-- 2026-10-13T01:56:38Z 使用者經選單作答（選項順序與本檔一致，建議項為 A） -->
