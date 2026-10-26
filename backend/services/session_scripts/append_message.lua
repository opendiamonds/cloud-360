-- script: append_message
--
-- `U10 session-store`／`BR3.4` 修剪的**唯一生產載體**。
--
-- `session_types.trim_history` 是同一語意的**參考實作**，只給 property-based
-- 測試與 in-memory 替身用；Python 端在生產路徑上一行修剪都不跑。
-- `performance-design.md` 逐字：「`BR3.4` 的修剪語意只能有一個載體……兩份實作
-- 遲早分歧，而分歧的徵兆是『筆數偶爾是 201』這種沒人會注意的東西。」
--
-- 為什麼是一支 Lua 而不是「讀→改→寫」三次：
--   * `NFR3.41`：**一次** round-trip 而非三次，少兩次 RTT 直接進入 20ms 預算。
--   * `reliability-design.md §三`：Redis 單執行緒執行腳本，腳本內不會被打斷，
--     故**不會出現**「追加了但沒修剪」（筆數 201）或「修剪了但沒續期」。
--
-- 安全邊界（`security-design.md §二`）：
--   * 本檔是**靜態常數**，由 `redis_gateway.script_source()` 從檔案讀取。
--     使用者文字一律經 `ARGV` 傳入，**絕不**以字串拼接組成腳本。
--   * 成本上界由 `BR3.4` 的筆數上限與 `OPEN-N10-6` 的單則長度上限共同封住。
--     **不得**在此迴圈掃描全部欄位或做任何與 session 數量相關的工作——
--     腳本阻塞的是整個 Redis。
--   * `ARGV` 的內容**不得被記錄**：本腳本不呼叫 `redis.log`。
--
-- KEYS[1] session key
-- ARGV[1] 段欄位名（`seg:<segmentId>`）
-- ARGV[2] 本則訊息（JSON 物件）
-- ARGV[3] 該段的筆數上限（`BRAIN_SESSION_HISTORY_MAX`）
-- ARGV[4] TTL 秒數（`BR1.3`：每次互動續期）
-- ARGV[5] 該段序列化後的位元組上限（`DEFAULT_SEGMENT_MAX_BYTES`，200 KB；
--         `merge-blockers.md` 第 18 項）
--
-- 回傳 {修剪後的筆數, 本次丟棄的筆數}
--   第二個值餵 `session_history_trimmed` 的 DEBUG 日誌（`droppedCount`）。
--   **日誌只記數量，不記被丟棄的內容。**

local key = KEYS[1]
local field = ARGV[1]
local cap = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
local max_bytes = tonumber(ARGV[5])

local raw = redis.call('HGET', key, field)
if not raw then raw = '[]' end
local arr = cjson.decode(raw)

-- `BR3.3`：段內 `sequence` 單調遞增，且**在腳本內**計算。
-- Python 端算它需要先讀一次（讀→改→寫），而那正是 `[D1]`=A 用 Lua 取代的
-- 三次 round-trip；更要緊的是兩個並行追加會算出同一個序號。
local message = cjson.decode(ARGV[2])
local next_seq = 1
if #arr > 0 and arr[#arr].sequence then
  next_seq = arr[#arr].sequence + 1
end
message.sequence = next_seq

arr[#arr + 1] = message
local before = #arr

-- `BR3.4`：自**最舊**端丟棄，直到「筆數 ≤ cap **且** 整段位元組 ≤ max_bytes」
-- 兩者都成立（取較嚴者，`merge-blockers.md` 第 18 項）。丟最新會讓 `U11` 的
-- 「第 N−1 輪產出」永遠查不到，而長度看起來完全正常。
--
-- 位元組以 `string.len`（位元組，不是字元）量 `cjson.encode` 的輸出：整段
-- `[a,b,…]` 的長度 = 2（括號）＋ 各則長度 ＋ (n−1)（逗號），故每則只編碼一次，
-- 不在迴圈內反覆編碼整段（成本與段大小成正比，而段大小已被本上限封住）。
-- `session_types.trim_history` 以同一個算式量同一個東西（`cjson_encoded_size`）。
--
-- 剩一則時停止：最新的一則永遠保留。單則訊息不可能超過上限（後端建構時以算式
-- 確認），這條界線只保證段不會被清空——cjson 會把空表編成 `{}` 而非 `[]`。
local sizes = {}
local total = 2
for i = 1, #arr do
  sizes[i] = string.len(cjson.encode(arr[i]))
  total = total + sizes[i]
end
total = total + (#arr - 1)

while #arr > 1 and (#arr > cap or total > max_bytes) do
  total = total - sizes[1] - 1
  table.remove(sizes, 1)
  table.remove(arr, 1)
end

redis.call('HSET', key, field, cjson.encode(arr))
redis.call('EXPIRE', key, ttl)

return {#arr, before - #arr}
