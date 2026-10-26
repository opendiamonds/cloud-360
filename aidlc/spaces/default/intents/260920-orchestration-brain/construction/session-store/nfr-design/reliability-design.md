# Reliability Design — `U10 session-store`

> 設計階段產出。`[D2]`=A 的逾時／重試／不熔斷在此落為具體參數與其理由。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `reliability-requirements.md` | `NFR4.50`（`noeviction`）、`NFR4.51`（降級形狀）、`NFR4.52`（AOF）、`NFR4.53`–`NFR4.57`（還原的五項對象） |
| `performance-requirements.md` | `NFR3.40`–`NFR3.43` 的預算——重試會動到它的尾端 |
| `scalability-requirements.md` | `NFR4.40` 的容量承諾與「先壞什麼」 |
| `security-requirements.md` | `NFR4.46` 的委派模型——`K-07` 失敗時的傳遞行為 |
| `observability-requirements.md` | `NFR4.62` 的兩種原因碼——本檔的失敗分類必須餵得出它們 |
| `tech-stack-decisions.md` | `NFR8.41` 的客戶端選型條件（須能區分 OOM） |
| `functional-spec.md` | `W8` 的失效路徑；`W7` 的到期路徑 |
| `contract-summary.md`（`K-09`） | `raises: [SessionBackendUnavailable]` 與冪等性分界 |

## 一、彈性模式：選了什麼、刻意不選什麼（`[D2]`=A）

| 模式 | 採用？ | 參數與理由 |
|---|---|---|
| **Timeout** | ✅ | 連線 2 秒、指令 1 秒。`nfr-design-guide.md` 逐字「Every external call **without exception**」 |
| **Retry with backoff** | ✅ **僅冪等方法** | `load`／`touch`／`set_work_target`／`set_sharing_mode` 至多 2 次、指數退避**含抖動**（`nfr-design-patterns.md` 逐字「Always add jitter」）。`append_message` **不重試**——`K-09` 逐字它非冪等，重試會製造重複訊息 |
| **Circuit Breaker** | ❌ **刻意不採用** | 它在本單元**沒有可降級的對象**：`BR6.1` 禁止降級，所以開路後的行為與逾時後的行為**完全相同**（`SessionBackendUnavailable`）。它唯一的好處是省掉等待，而 Redis 是同一台主機的內部服務，不存在「拖垮上游」的情境。**更關鍵的是它的狀態要放哪裡**——放行程記憶體與 `NFR4`／`BR1.2` 的精神衝突且多 worker 各有一份，放 Redis 則荒謬（Redis 掛了就讀不到熔斷器狀態） |
| **Bulkhead** | ❌ | 本單元只有一個下游依賴（Redis）。隔離艙要隔離的是「依賴之間互相搶資源」，單一依賴時它退化成連線池上限，而那已經有了 |
| **Fallback** | ❌ | `BR6.1` 逐字禁止。回空 session 是最壞的 fallback——它與 TTL 到期不可區分 |
| **Rate Limiter** | ❌ | 本單元是同進程元件，沒有自己的對外面（`BR5.3`）。限流屬 `U13` |

**不採用的四項各自寫出理由，而不是略過**——下一個讀這份檔的人會想知道
「為什麼沒有熔斷器」，而答案不是「忘了」。

## 二、失敗分類：三種成因必須可區分（`NFR4.62`）

```
Redis 呼叫失敗
├── 連線層失敗（拒絕連線、逾時、網路不可達）  → 原因碼 redis_unreachable
├── OOM（noeviction 下的寫入拒絕）            → 原因碼 redis_oom
└── 其他指令錯誤（ACL 拒絕、腳本錯誤）         → 原因碼 redis_command_error
```

三者**都**對外呈現為 `SessionBackendUnavailable`（`K-09` 的契約只有這一個例外型別，
不改它），但**例外攜帶原因碼**，日誌依 `NFR4.62` 記錄它。

**第三類是本檔新增的**：`security-design.md` 把 `EVAL` 的 ACL 可行性列為部署時
查核項——若查核沒做而 ACL 真的拒絕 `EVAL`，失敗會發生在**每一次** `append_message`
上。若它與連線失敗同碼，排查會往網路方向走而完全找錯方向。

## 三、原子性與崩潰一致性

| 操作 | 原子性來源 | 崩潰時的狀態 |
|---|---|---|
| `append_message` ＋ 修剪 ＋ 續期 | **Lua 腳本**（`[D1]`=A）——Redis 單執行緒執行，腳本內不會被打斷 | 要嘛整個生效、要嘛完全沒發生。**不會出現「追加了但沒修剪」**（筆數 201）或「修剪了但沒續期」 |
| `set_work_target` | `K-07` 解析（唯讀）＋ 一次 `HSET` | `K-07` 逐字「唯讀且冪等」，故解析成功而寫入失敗**不留下任何不一致**，重試安全 |
| `set_sharing_mode` ＋ 建段 ＋ 複製作業對象（`W3`） | **須在同一支 Lua 內**——這是本檔的設計要求 | 若分三次呼叫，崩潰可能留下「模式已改為 isolated 但段不存在」，直接違反 `EC3` |
| `load` | 單次 `HGETALL` | 唯讀 |

**第三列是本檔查出的一項**：`W3` 的第 4、5、6 步（建段、複製作業對象、改 `pageModes`）
在 `functional-spec.md` 是三個步驟，而 `EC3` 要求「`pageModes[P] == isolated` ⇒
`segments[P]` 必存在」是一個**不變量**。三次獨立寫入之間崩潰就會破壞它。
**設計處置：這三步必須是一支 Lua 腳本。** 上游沒有說，因為上游在描述順序而不是
原子性——順序正確不等於原子。

## 四、`NFR4.53`–`NFR4.57` 的還原五項與 Hash 結構的對應

| 還原對象 | Hash 落點 | 它會不會因設計而遺漏 |
|---|---|---|
| `NFR4.53` 每一個存在的段 | `seg:*` 欄位的存在與否 | 不會——欄位不存在即段不存在，語意一致 |
| `NFR4.54` 每段的訊息與順序 | `seg:<id>` 的 JSON 陣列順序 | 不會——陣列有序 |
| `NFR4.55` 每段各自的作業對象 | `tgt:<id>` 欄位 | 不會 |
| `NFR4.56` `pageModes` | `meta` 欄位內 | **最容易漏的一項**——它是指標不是資料。放進 `meta` 而非散落，使 `HGETALL` 一次就帶回 |
| `NFR4.57` 剩餘 TTL | key 的 TTL | 不會——TTL 在 key 上，AOF 載入時 Redis 自行還原剩餘秒數（**不是重設為滿額**） |

## 五、健康檢查與單點

- **既有 healthcheck 的已知限制**（`deploy/docker-compose.deploy.yml:258-261` 實讀）：
  `redis-cli ping | grep -q PONG`，而註解逐字自承「**this does NOT prove the ACL user
  works**（ping passes as `default`），and it passes during AOF loading」。
  本單元**不依賴它**判斷可用性——真正的判準是第一次實際呼叫是否成功。
- **應用層不另加 Redis 健康檢查端點**：那會變成第二個要維護的真相來源，而
  `BR5.3` 禁止本單元暴露端點。
- **單點**：Redis 單一實例、無副本。`reliability-requirements.md` 已明寫並接受。
  本檔不重述，只補一句設計後果：**因為沒有副本，`[D2]`=A 的重試只能救網路抖動，
  救不了實例掛掉**——後者的復原時間等於容器重啟 ＋ AOF 載入。

## 六、備份：刻意不做

`reliability-requirements.md` 已定 RPO 為「24 小時內的 session 資料可接受全失」。
**設計後果**：`redis_aof` volume 的存在是為了**重啟還原**（`NFR4.52`），
**不是**為了備份——它不在任何備份排程內，也不應該被誤讀成有。
這句話寫在這裡，是因為「有 AOF volume」很容易被下一個人讀成「有備份」。
