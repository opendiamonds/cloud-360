-- script: switch_to_isolated
--
-- 建段 ＋ 複製作業對象 ＋ 改 `pageModes`，**一支腳本**（`reliability-design.md
-- §三` 第 3 列的設計要求）。
--
-- 為什麼不能是三次獨立寫入：`EC3` 要求「`pageModes[P] == isolated` ⇒
-- `segments[P]` 必存在」是一個**不變量**，而三次寫入之間崩潰就會留下
-- 「模式已改為 isolated 但段不存在」——該頁於是進入一個不存在的段。
-- 上游的 `functional-spec.md W3` 把它寫成三個步驟，因為上游在描述**順序**
-- 而不是原子性；**順序正確不等於原子**。
--
-- `BR2.4`：段已存在則**原樣重入**，不清空、不新建（`[S2]`=A 的可重入）。
-- 每次都新建會讓單一 key 無上界成長。
--
-- `BR4.2`：首次建立時以共享段當下的三個作業對象**逐欄複製**初始化（含 null）。
-- `BR4.7` 的例外逐字記於 `rules.md`：複製來源是**已驗證過的**共享段值，
-- 故這條路徑不重驗——這是唯一的例外，不留給實作推測。
--
-- KEYS[1]  session key
-- ARGV[1]  目標段欄位（`seg:<scope>`）
-- ARGV[2]  目標段的作業對象欄位（`tgt:<scope>`）
-- ARGV[3]  複製來源的作業對象欄位（`tgt:shared`）
-- ARGV[4]  meta 欄位名
-- ARGV[5]  頁面範圍（`workspace`／`assessment`）
-- ARGV[6]  本段的 createdAt
-- ARGV[7]  TTL 秒數
-- ARGV[8]  空歷程的 JSON（`[]`）
-- ARGV[9]  空作業對象的 JSON（三層皆 null）
-- ARGV[10] meta 不存在時的預設 JSON
--
-- 回傳 {是否新建(0/1)}
--   `1` 餵 `session_segment_created` 的 INFO 日誌（只帶 sessionKey 與 segmentId）。

local key = KEYS[1]
local seg_field = ARGV[1]
local tgt_field = ARGV[2]
local source_tgt_field = ARGV[3]
local meta_field = ARGV[4]
local scope = ARGV[5]
local created_at = ARGV[6]
local ttl = tonumber(ARGV[7])
local empty_messages = ARGV[8]
local empty_target = ARGV[9]
local default_meta = ARGV[10]

local created = 0
if redis.call('HEXISTS', key, seg_field) == 0 then
  redis.call('HSET', key, seg_field, empty_messages)
  local source = redis.call('HGET', key, source_tgt_field)
  if not source then source = empty_target end
  redis.call('HSET', key, tgt_field, source)
  created = 1
end

local meta_raw = redis.call('HGET', key, meta_field)
if not meta_raw then meta_raw = default_meta end
local meta = cjson.decode(meta_raw)

if meta.pageModes == nil then meta.pageModes = {} end
meta.pageModes[scope] = 'isolated'

if created == 1 then
  if meta.createdAt == nil then meta.createdAt = {} end
  meta.createdAt[scope] = created_at
end

redis.call('HSET', key, meta_field, cjson.encode(meta))
redis.call('EXPIRE', key, ttl)

return {created}
