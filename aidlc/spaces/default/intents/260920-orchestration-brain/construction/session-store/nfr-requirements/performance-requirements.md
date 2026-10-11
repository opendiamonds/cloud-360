# Performance Requirements — `U10 session-store`

> 編號自 `.40` 起，與既有 12 個單元的子編號不重疊（已實測：`NFR3` 用到 24、
> `NFR2` 未被任何單元使用）。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `requirements.md:482-498`（`NFR3`） | 首字回應 **P50 ≤ 2 秒**，並逐字說明「這條預算幾乎全部被**路由層的 LLM 呼叫**吃掉。FR4 的 Redis 往返在同一個 compose 網路內**約 1ms，可忽略**」 |
| `requirements.md:430-445`（`NFR2`） | 跨頁面上下文保留率 **≥ 95%**，量測母體為三處之間的頁面切換事件，落點 `build-and-test` |
| `functional-spec.md`（本單元） | `W1`／`W2`／`W6` 三條流程決定了本單元在首字預算中的位置 |
| `rules.md`（本單元） | `BR1.3`（每個方法都續期 TTL）使**每一次呼叫都是一次寫入**，這是本檔預算的根據 |
| `contract-summary.md:684-742`（`K-09`） | 五個方法的同步形式與冪等性 |
| `codekb/chiton/technology-stack.md:18`／`:168` | Redis 為 `redis:8-alpine`，且 compose 檔頭逐字「Only nginx is reachable from outside. backend, db, redis and ollama have no …」——**本單元與 Redis 在同一個 compose 內部網路**，這是 `NFR3` 稱往返「約 1ms」的前提；本檔的 20ms 上界即建立在它之上，網路拓樸若改變須重訂 |

## 本檔的立場：把上游的「可忽略」變成可驗證的上界

`NFR3` 逐字稱 Redis 往返「約 1ms，可忽略」。**那是一個未經量測的判斷**，而本單元
是唯一能讓它成立或不成立的地方。若 `load` 實際要 300ms，`NFR3` 的 2 秒預算就少了
15%，而沒有任何人會發現——因為沒有人在量它。本檔不推翻該判斷，只給它一個**會紅的
上界**。

| ID | 需求 | 判定方式 | 來源 |
|---|---|---|---|
| **NFR3.40** | `SessionStore.load` 的伺服器端耗時 **P95 ≤ 20ms**（自方法進入到回傳，不含呼叫端處理） | 伺服器端計時。`load` 是 `W1` 第 2 步，位於首字預算的最前端 | `NFR3`；`K-09.load` |
| **NFR3.41** | `SessionStore.append_message` 的伺服器端耗時 **P95 ≤ 20ms**，含 `BR3.4` 的上限修剪 | 同上。修剪是 `O(丟棄筆數)`，穩態下每次至多丟 1 則 | `NFR3`；`BR3.4` |
| **NFR3.42** | `SessionStore.set_work_target` 的伺服器端耗時 **P95 ≤ 150ms**，**含** `K-07` 的 `resolve_work_target` | 伺服器端計時。**本條的上界明顯寬於前兩條，理由是它會打 PostgreSQL**（`hierarchy_service.resolve_work_target` 對每一層各做一次擁有者檢查），不是 Redis 級的操作。把它與前兩條混在同一個數字下，會讓「Redis 慢了」與「DB 慢了」不可區分 | `NFR3`；`BR4.6`；`K-07` |
| **NFR3.43** | 上述三條的量測**必須排除**使用者網路往返 | 與 `NFR3` 的判定方式一致（逐字「伺服器端以該兩個時刻的差計時，不含使用者的網路往返」） | `NFR3` |
| **NFR2.40** | 狀態變更到該 session key 全部存活連線**送出**訊息，伺服器端耗時 **P95 ≤ 200ms** | 伺服器端計時，自狀態寫入成功到最後一條連線的訊息送出。**本數字是推導值不是量測值**：`NFR3` 給首字 2 秒，本條取其 **10%** 作為狀態扇出的預算上限——推導過程寫在這裡，不是憑感覺挑的 | `NFR2`；`BR2.7`；`x-concurrent-connections.state_change_fanout` |

## 與 `NFR2` 的 95% 門檻的關係（本單元**不**擁有那個比率）

`NFR2` 的 ≥ 95% 是**情境級**的比率，其量測機制由 `requirements.md:440-445` 逐字
指派給 `build-and-test`（3.6），並明寫**不能**由 `ui-regression` 的既有閘門承載
（它只能產出全過／失敗，照字面執行門檻會變成 100%）。

本單元提供的是**機制**，不是門檻：三頁讀同一個 `shared` 段（`BR2.2`）、狀態在單一
Redis key（`BR1.2`）、變更扇出給全部存活連線（`BR2.7`）。**若這三條成立，單次切換
的命中與否就不是機率問題而是確定的**——95% 這個數字真正要抓的是本機制之外的失誤
（連線斷掉、客戶端沒套用、競態）。本檔只為機制面設上界（`NFR2.40`），不複製門檻。

## 本單元**不**負責的效能面（明列，避免被誤讀為已涵蓋）

| 項目 | 歸屬 | 理由 |
|---|---|---|
| 首字 P50 ≤ 2 秒本身 | `U11 intent-router` ＋ `U13 brain-gateway` | `NFR3` 逐字「這條預算幾乎全部被路由層的 LLM 呼叫吃掉」 |
| 意圖識別準確率（`NFR1`） | `U11` | 與本單元無關 |
| 頁面切換次數（`NFR11`） | 情境級量測，`build-and-test` | 本單元是其機制的一部分，不擁有門檻 |
| 向量檢索延遲（`NFR3.20`／`.21`） | `U8 memory-service` | 已完成，與本單元無重疊 |

## 量測承載機制的誠實限定

本 repo **沒有任何伺服器端延遲量測機制**——無 APM、無 metrics endpoint、無
structured timing log。故上述五條在今天**無法被持續量測**，只能在
`build-and-test`（3.6，`ALWAYS`）以測試內計時斷言。這與 `team.md` 對 80% 覆蓋率的
處理方式相同：**如實記載「是宣告而非持續閘門」，不假裝它已被承載**。
承載機制的建立列入 `observability-requirements.md` 的 `NFR4.60`。
