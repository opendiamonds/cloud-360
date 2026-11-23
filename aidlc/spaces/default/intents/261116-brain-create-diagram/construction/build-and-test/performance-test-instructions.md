# 效能與準確率測試說明（261116-brain-create-diagram）

> 涵蓋 `requirements.md` 的 NFR1（判定準確率）與 NFR2（首字延遲）。兩者都需要**真實的路由模型**與**部署後的程式**，本機做不到。

## 1. 為什麼本機做不到

- NFR1、NFR2 量的是 LLM 路由的實際行為與延遲。單元測試以替身取代路由模型，量不到任何準確率或延遲。
- 前例（`260920-orchestration-brain/operation/performance-validation/test-results.md`）是在 staging（`cloud360-backend-1`，`BRAIN_ROUTER_MODEL=typesafe/jev-1.14`）以一次性分支跑量測 workflow，從 artifact 以指令計算數字。也就是說，量測對象必須是**已部署到 staging 的這版程式**——本分支尚未合併、尚未部署。
- 本 session 的約束：不得從容器取出 `OPENROUTER_API_KEY`，觸發 CI／workflow 需使用者同意。

## 2. 量測方式（合併並部署到 staging 之後）

| 目標 | 量測 | 門檻 | 來源 |
|---|---|---|---|
| NFR1-a | 沿用 `260920` 的 60 句標註集重跑路由層量測，取準確率 | ≥ 80%；未達標依該 intent 的校正程序由決策者裁決，**不得自動改寫門檻** | `requirements.md` NFR1 |
| NFR1-b | 新增至少 10 句「新建／修改／應反問」標註，報告準確率、反問率、交辦錯筆數 | 同上 | `requirements.md` NFR1 |
| NFR2 | 伺服器端 `turn_end` 分段（`preClassifyMs`＋`classifyMs`＋`toFirstContentMs`）的首字 P50 | ≤ 2000 ms（既有 NFR3） | `requirements.md` NFR2 |

做法：比照前例，以一次性分支觸發量測 workflow（**須先取得使用者同意**），數字一律由 artifact 以指令計算，不手寫。

## 3. 本機已能確認的結構性前提

- 「是否要新的一張」併入同一次路由請求、不多發模型呼叫：`tests/test_brain_diagram_creation_flow.py` 斷言路由請求只發一次（NFR2 的結構前提）。這不是延遲量測，只確認沒有多一次往返。
