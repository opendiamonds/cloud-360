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
-- KEYS[1] session key
-- ARGV[1] 欄位名（`wi:<workItemId>`）
-- ARGV[2] 工作項 JSON 物件
--
-- 回傳 1＝已寫入；0＝key 不存在或欄位已存在（皆未寫入）

local key = KEYS[1]
if redis.call('EXISTS', key) == 0 then
  return 0
end
return redis.call('HSETNX', key, ARGV[1], ARGV[2])
