-- script: update_work_item
--
-- `U12 work-orchestrator`／`BR52.7`：工作項的**比對後寫入**。
--
-- 原子地讀欄位 → 比對 `status` 在預期集合內**且** `dispatchStage` 等於預期值 →
-- 皆符合才把**補丁**合併進讀到的當前值後回寫。`session_types.ref_update_work_item`
-- 是同一語意的參考實作（替身與一致性測試用）。
--
-- 為什麼收**補丁**而不是整個物件（`code-generation-plan.md` §二 第 4、7、24 項）：
--   呼叫端若送整個物件，它手上那份可能早於另一個寫入者寫進的欄位（例如成本項的
--   `estimateSetId`），回寫就會用過期值蓋掉它。合併在腳本內、以**讀到的當前值**
--   為底，只覆寫補丁裡出現的欄位，故未出現的欄位不可能被過期值覆寫。
--
-- 補丁語意：
--   * 補丁中出現的欄位一律覆寫；值為 JSON `null` 即設為 null（`cjson.null`
--     會被原樣編碼回 `null`），**不是**刪除該欄位。
--   * 補丁中沒有出現的欄位不動。
--   * 以 `cjson.decode_array_with_array_mt(true)` 解碼，使空陣列回寫後仍是
--     `[]` 而不是 `{}`。這個設定是 cjson 模組的**行程級狀態**，故腳本結束前
--     一律還原為 false（含錯誤路徑，以 `pcall` 包住），不影響其他腳本。
--
-- **非冪等**：呼叫端以 `eval_script(..., idempotent=False)` 執行，傳輸層不自動
-- 重送；連線錯誤時結果未知，由呼叫端重讀確認（`WorkOrchestrator._cas`）。
--
-- **不改 TTL**、key 不存在即回 0 且不建 key（`NFR12.18`）。
--
-- **已結束保留數**（合併前必修第 18 項、`OPEN-N10-3`；`code-generation-plan.md`
-- §六 Step 13）：補丁使本項**由非終態轉為終態**時，若終態項（含本項）超過
-- `ARGV[5]` 筆，依 `createdAt`（同值再以欄位名，決定性）由舊到新 `HDEL` 其他
-- 終態項，直到不超過為止。
--   * 只刪終態項，**永不刪**進行中（處理中、等待中）的項。
--   * **不刪剛轉終態的這一項**：`createdAt` 是建立時間而非結束時間，一個執行很久的
--     項可能比 20 筆已結束的項都舊；若把它列入候選，它會在自己完成的那一刻就被
--     刪掉，使用者在清單上永遠看不到它的結果。排除它之後，候選至少有 `ARGV[5]`
--     筆（總數已超過上限），故終態總數仍收斂到上限以內。
--   * 只在「非終態 → 終態」那一次觸發；終態項的後續補丁（如在途存檔收尾改
--     `sideEffect`）不觸發。
--
-- KEYS[1] session key
-- ARGV[1] 欄位名（`wi:<workItemId>`）
-- ARGV[2] 預期 status 的 JSON 陣列
-- ARGV[3] 預期 dispatchStage
-- ARGV[4] 補丁（JSON 物件）
-- ARGV[5] 已結束保留數（整數字串）
-- ARGV[6] 終態 status 的 JSON 陣列
--
-- 回傳 1＝已寫入；0＝key 或欄位不存在、或比對不符（皆未寫入）

local key = KEYS[1]
local field = ARGV[1]

local function prune_terminal(terminal, keep)
  local flat = redis.call('HGETALL', key)
  local others = {}
  local count = 0
  for i = 1, #flat, 2 do
    local name = flat[i]
    if string.sub(name, 1, 3) == 'wi:' then
      local other = cjson.decode(flat[i + 1])
      if terminal[other.status] then
        count = count + 1
        if name ~= field then
          local created = other.createdAt
          if type(created) ~= 'string' then
            created = ''
          end
          others[#others + 1] = { name = name, created = created }
        end
      end
    end
  end
  if count <= keep then
    return
  end
  table.sort(others, function(a, b)
    if a.created ~= b.created then
      return a.created < b.created
    end
    return a.name < b.name
  end)
  local index = 1
  while count > keep and index <= #others do
    redis.call('HDEL', key, others[index].name)
    count = count - 1
    index = index + 1
  end
end

local function run()
  if redis.call('EXISTS', key) == 0 then
    return 0
  end
  local raw = redis.call('HGET', key, field)
  if not raw then
    return 0
  end
  local item = cjson.decode(raw)
  local expected = cjson.decode(ARGV[2])
  local status_ok = false
  for _, value in ipairs(expected) do
    if item.status == value then
      status_ok = true
      break
    end
  end
  if not status_ok then
    return 0
  end
  if item.dispatchStage ~= ARGV[3] then
    return 0
  end
  local terminal = {}
  for _, value in ipairs(cjson.decode(ARGV[6])) do
    terminal[value] = true
  end
  local was_terminal = terminal[item.status] == true
  local patch = cjson.decode(ARGV[4])
  for name, value in pairs(patch) do
    item[name] = value
  end
  redis.call('HSET', key, field, cjson.encode(item))
  if not was_terminal and terminal[item.status] then
    prune_terminal(terminal, tonumber(ARGV[5]))
  end
  return 1
end

local has_array_mt = type(cjson.decode_array_with_array_mt) == 'function'
if has_array_mt then
  cjson.decode_array_with_array_mt(true)
end
local ok, result = pcall(run)
if has_array_mt then
  cjson.decode_array_with_array_mt(false)
end
if not ok then
  error(result)
end
return result
