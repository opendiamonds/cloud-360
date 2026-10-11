# Performance Design — `U10 session-store`

> 設計階段產出：描述架構模式與取捨，不是實作。程式片段僅作說明用，≤15 行。

## 本檔的上游

| 上游 | 它給了什麼 |
|---|---|
| `performance-requirements.md` | `NFR3.40`／`NFR3.41`（P95 ≤ 20ms）、`NFR3.42`（P95 ≤ 150ms，含 PostgreSQL）、`NFR3.43`（排除使用者網路）、`NFR2.40`（扇出 P95 ≤ 200ms） |
| `scalability-requirements.md` | `NFR4.40` 的 300 session 承諾與 300 KB／session 的上界算式 |
| `reliability-requirements.md` | `NFR4.51` 的降級形狀（寫入失敗、讀取可用） |
| `security-requirements.md` | `NFR4.47` 的逐段授權驗證——它決定 `set_work_target` 的呼叫次數 |
| `observability-requirements.md` | `NFR4.61`／`NFR4.62` 的日誌要求（每次拋出一筆 ERROR） |
| `tech-stack-decisions.md` | `NFR8.41`：Redis 客戶端為新增依賴，選型由 `code-generation` 定 |
| `functional-spec.md` | `W1`／`W2`／`W6` 三條流程的步驟順序 |
| `contract-summary.md`（`K-09`） | 五個方法的同步形式與冪等性 |

## 核心設計：Hash ＋ Lua（`[D1]`=A）

單一 session key 之下是一個 **Redis Hash**：

| Hash 欄位 | 內容 |
|---|---|
| `seg:shared` | 共享段的訊息陣列（JSON 編碼） |
| `seg:workspace`／`seg:assessment` | 該頁獨立段的訊息陣列；**不存在即該段未建立**（`EC3`／`BR2.4`） |
| `tgt:shared`／`tgt:workspace`／`tgt:assessment` | 該段的三層作業對象（`[S3]`=A） |
| `meta` | `userId`、`pageModes`、各段 `createdAt` |

**效能上的直接後果**，逐項對應已定案的預算：

| 設計選擇 | 它讓哪一條預算成立 |
|---|---|
| 追加訊息只碰 `seg:<該段>` 一個欄位 | `NFR3.41`：傳輸量與**該段**大小相關，而非與整個 session（三段共 300 KB）相關。**單一 blob 方案會讓這條預算隨對話累積而逐漸失守**，而失守的方式是漸進的、沒有明確的紅線 |
| 追加＋修剪在 Lua 內一次完成 | `NFR3.41`：**一次** round-trip 而非「讀→改→寫」三次。少兩次 RTT 直接進入 20ms 預算 |
| `load` 以單次 `HGETALL` 取回 | `NFR3.40`：一次 round-trip |
| TTL 續期併入同一支 Lua／同一次管線 | `BR1.3` 的「每個方法都續期」不額外增加一次 RTT |

### Lua 腳本的職責邊界（**唯一載體**原則）

```lua
-- 說明用，非實作。append(key, field, msg_json, cap, ttl)
local arr = cjson.decode(redis.call('HGET', KEYS[1], ARGV[1]) or '[]')
arr[#arr+1] = cjson.decode(ARGV[2])
while #arr > tonumber(ARGV[3]) do table.remove(arr, 1) end   -- BR3.4：丟最舊
redis.call('HSET', KEYS[1], ARGV[1], cjson.encode(arr))
redis.call('EXPIRE', KEYS[1], ARGV[4])                        -- BR1.3
return #arr
```

**`BR3.4` 的修剪語意只能有一個載體。** Python 端**不得**另外實作一次修剪——
兩份實作遲早分歧，而分歧的徵兆是「筆數偶爾是 201」這種沒人會注意的東西。
這一點在 `[D1]` 的選項說明中已標為該選項的代價，此處是它的處置。

## 連線池（本站自行決定，附算式）

`nfr-design-patterns.md` 逐字公式：
`Pool size = (Requests per second) × (Average request duration in seconds) × 1.5`

| 輸入 | 值 | 來源 |
|---|---|---|
| 平均請求時間 | **0.02 秒** | `NFR3.40`／`NFR3.41` 的 P95 上界，取為保守的平均值代入 |
| 峰值 RPS | **300** | 以 `NFR4.40` 承諾的 300 個同時存活 session、**每個每秒一次互動**代入。這是**刻意高估**——自有 staging 的實際使用者數遠低於此 |

```
300 × 0.02 × 1.5 = 9
```

**設定：min 5 / max 20。** `min 5` 讓閒置期維持暖連線（避免首次互動吃到建立連線的
成本）；`max 20` 為算式結果的兩倍餘裕。`idle timeout 10 分鐘`、`max lifetime 30 分鐘`
沿用 `nfr-design-patterns.md` 的建議值。

**這個算式的輸入有一項是假設**（每個 session 每秒一次互動），如實標明；
若未來有實測 RPS 須重算。

## 逾時與重試對尾端延遲的影響（`[D2]`=A）

| 參數 | 值 | 對預算的影響 |
|---|---|---|
| 連線逾時 | 2 秒 | 只在建立連線時發生；`min 5` 的暖連線使它不在穩態路徑上 |
| 指令逾時 | 1 秒 | **它是 P99 的上界，不是 P95 的**。`NFR3.40`／`NFR3.41` 的 20ms 是 P95，而一次逾時會產生一個 1 秒的樣本 |
| 冪等方法重試 | 至多 2 次，指數退避含抖動 | 最壞情況 `1s + backoff + 1s + backoff + 1s ≈ 3.3s`。**這超過 `NFR3` 的 2 秒首字預算**——明寫而非隱含：重試只保護**可救的抖動**，Redis 真的不可用時使用者會等到逾時鏈走完 |
| `append_message` | **不重試**（`BR6.2` 非冪等） | 其尾端為單次 1 秒逾時 |

**上一列是本檔最需要被讀到的一句**：`[D2]`=A 的重試在最壞情況下會把一次互動
拉到 3 秒以上，而 `NFR3` 的首字預算是 2 秒。兩者不矛盾（`NFR3` 是 **P50**、
這是極端尾端），但如果有人把 `NFR3` 誤讀成 P99，這個設計看起來就是違反的。
`NFR3` 的判定方式逐字是「以 **P50** 為門檻（非平均值）」——此處引用它以免下游誤判。

## 不做的效能設計（附理由）

| 常見手段 | 為何不做 |
|---|---|
| 應用層快取 session | `NFR4`／`BR1.2` 逐字禁止行程記憶體持有狀態。快取就是行程記憶體 |
| 批次化多個 Redis 呼叫 | 一輪互動本來就只有 2–3 次呼叫；批次化省下的 RTT 小於它引入的順序耦合 |
| 壓縮 Hash 欄位值 | 300 KB 的上界之下，CPU 成本換不回有意義的記憶體；且壓縮會讓 Lua 無法解碼修剪 |
| 讀寫分離／副本 | Redis 為單一實例（`reliability-requirements.md` 已明寫此單點並接受） |
