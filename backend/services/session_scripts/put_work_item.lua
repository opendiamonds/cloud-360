-- script: put_work_item
--
-- `U12 work-orchestrator`／`BR52.4`：新建一個工作項欄位（`wi:<workItemId>`）。
--
-- `session_types.ref_put_work_item` 是同一語意的**參考實作**，只給 in-memory
-- 替身與 `tests_redis/` 的一致性測試用；生產路徑只跑本腳本。
--
-- 為什麼是 Lua 而不是 `HSETNX`：
--   * key 不存在時**必須拒絕**（`BR52.4`、`NFR12.18`）。單獨的 `HSETNX` 會在
--     key 不存在時**建立**一個沒有到期時間、沒有 `meta` 欄位的 key——工作階段
--     已到期，而那個殘留 key 永遠不會過期。「先 `EXISTS` 再 `HSETNX`」兩次
--     round-trip 之間 key 可能剛好到期，故兩步放在同一支腳本內。
--   * 欄位已存在即拒絕（同一個 workItemId 不得被覆寫）。
--
-- **不改 TTL**：工作項隨工作階段的既有到期時間到期（`BR52.4`），本腳本不呼叫
-- `EXPIRE`。
--
-- 安全邊界（沿用 `append_message.lua`）：本檔是靜態常數，工作項 JSON 一律經
-- `ARGV` 傳入；本腳本不記錄任何 `ARGV` 內容。
--
-- **進行中筆數上限**（合併前必修第 18 項、`OPEN-N10-3`；`code-generation-plan.md`
-- §六 Step 13）：同一工作階段的工作項只要 `status` 不屬於終態（處理中、等待中）
-- 就計入；已達上限即回 `-1`，不寫入。計數與寫入在同一支腳本內，故同一工作階段
-- 的兩個併發交辦不會各自讀到「還有空位」而一起越過上限。上限值與終態集合都由
-- 呼叫端經 `ARGV` 傳入（正本在 `work_orchestrator_rules`），本檔不抄第二份。
--
-- KEYS[1] session key
-- ARGV[1] 欄位名（`wi:<workItemId>`）
-- ARGV[2] 工作項 JSON 物件
-- ARGV[3] 進行中筆數上限（整數字串）
-- ARGV[4] 終態 status 的 JSON 陣列
--
-- 回傳 1＝已寫入；0＝key 不存在或欄位已存在（皆未寫入）；-1＝進行中已達上限（未寫入）

local key = KEYS[1]
local field = ARGV[1]
if redis.call('EXISTS', key) == 0 then
  return 0
end
if redis.call('HEXISTS', key, field) == 1 then
  return 0
end

local max_active = tonumber(ARGV[3])
local terminal = {}
for _, value in ipairs(cjson.decode(ARGV[4])) do
  terminal[value] = true
end

-- **掃描成本的取捨**（合併前必修第 36 列 (a)；review-02 R-05）：下面的 `HGETALL`
-- 讀回**整個** session hash——不只 `wi:*`，也含 `meta`、`tgt:*` 與三段對話
-- `seg:*`——再於 Lua 內篩 `wi:` 前綴，成本隨整個 hash 的大小線性成長（O(n)），
-- 且每一次建項都付一次。
--   * 現行量級下接受：`wi:*` 欄位在每支腳本結束時最多「進行中上限＋已結束保留數」
--     個（前者由本腳本擋住、後者由 `update_work_item.lua` 修剪），每筆另有位元組
--     上界；對話段各有位元組上限。整個 hash 的序列化上界見 `DEPLOY.md` 的 Redis
--     容量表（本檔不抄數字，理由同上：避免兩處漂移）。
--   * 須改寫的時機：調高進行中上限、已結束保留數或段位元組上限**之前**；或
--     staging 的 `SLOWLOG` 出現本腳本。改法二選一——以 `HKEYS` 篩出 `wi:*` 後逐一
--     `HGET`（不再讀回對話段），或在 hash 內另存進行中筆數的計數欄位（由本腳本與
--     `update_work_item.lua` 在同一次執行內原子維護）。兩者都改變腳本行為面，須
--     連同 `session_types.ref_put_work_item` 與 `tests_redis/` 的一致性測試一起改。
local flat = redis.call('HGETALL', key)
local active = 0
for i = 1, #flat, 2 do
  if string.sub(flat[i], 1, 3) == 'wi:' then
    local item = cjson.decode(flat[i + 1])
    if not terminal[item.status] then
      active = active + 1
    end
  end
end
if active >= max_active then
  return -1
end

return redis.call('HSETNX', key, field, ARGV[2])
