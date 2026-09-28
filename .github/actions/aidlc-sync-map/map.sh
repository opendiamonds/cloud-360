#!/usr/bin/env bash
#
# map.sh — U-1「映射與解析」的全部邏輯。
#
# 這支腳本承載 [ad:C-1 sync-map] 與 [ad:C-2 record-reader] 兩個元件：把一個 record 的
# **文字**變成一個**決定**。
#
#   零 I/O：本檔不開任何檔案、不發任何網路請求、不寫 log。
#   輸入一律來自環境變數，輸出一律往 stdout（並在 $GITHUB_OUTPUT 存在時附加一份）。
#
# 這個限制不是潔癖——它是 [US:S-10 AC 1] 的前提：aidlc-sync-selftest.yml 要用純文字
# fixture 驅動它。任何 I/O 都會讓 fixture 驅動失效，也會讓 run-fixtures.py 無法在不起
# workflow 的情況下斷言。讀 fixture 檔的是測試框架，不是這裡。
#
# 規格正本：
#   ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
#     U-1-map-parse-action/functional-design/business-rules.md        （可判定的規則）
#     U-1-map-parse-action/functional-design/business-logic-model.md  （演算法與介面）
#     U-1-map-parse-action/functional-design/domain-entities.md       （型別語意）
#
# 用法：
#   map.sh                       跑完整管線，輸出五個 name=value
#   map.sh get_field <欄位名>    直接取一個欄位（供測試斷言 R-1 群；見下方「退出碼」）
#   map.sh list_stages           印出 stage 清單，每行 "<checkbox>\t<slug>\t<EXECUTE|SKIP>"
#   map.sh scope_note            只印 scope_note
#
# 退出碼（僅 get_field / list_stages 子命令使用）：
#   0  成功
#   3  get_field：欄位**缺席**（R-1.3 的 null）。與「存在但空」（退出 0 ＋ 空 stdout）
#      是兩件事，這個區分是安全關鍵，見下方 NULL_SENTINEL 的註解。
#   4  list_stages：無 ## Stage Progress 區塊（R-2.5）
#   5  list_stages：區塊在但零行 match（R-2.4）
#
# 相容性：本檔以 **bash 3.2** 可執行為底線（macOS 內建版本），因此不使用關聯陣列、
# mapfile、${var^^} 等 bash 4+ 語法。GitHub runner 的 bash 5 亦可執行。

set -euo pipefail

# --------------------------------------------------------------------------
# null 的承接方式（哨兵字串）
# --------------------------------------------------------------------------
# bash 沒有原生的 null。而 business-rules.md 的 R-1.2（欄位存在但值為空 → 回空字串）
# 與 R-1.3（欄位完全缺席 → 回 null）的區分被該檔明文標為**安全關鍵**：
# 現況 record 的 ## Runtime State 只有 `- **Revision Count**: 0`，`Parked` 是**缺席**
# 而非空值。若把 R-1.3 實作成回空字串，兩者就無法區分——而它們在 map 的第 1 條判定上
# **結論相同**（都是「未暫停」），所以這個錯誤**不會被判定結果暴露**，只會在未來某個
# 依賴該區分的呼叫端悄悄出錯。
#
# tech-stack-decisions.md 舉例的 \x00 在 bash **不可行**：bash 變數無法存放 NUL 位元組
# （指令替換會把它剝掉）。改用 \x01（SOH）：它是控制字元，不會出現在 markdown 狀態檔裡。
#
# 而且我們不只是「賭它不會出現」——下方 sanitise() 會在解析前把輸入中的 \x01 全部剝除，
# 使哨兵在結構上**不可能**被輸入偽造。這是 bash 能給的最強保證。
NULL_SENTINEL=$'\001ABSENT\001'

# em dash（U+2014）。以位元組明寫，避免任何編輯器或編碼轉換把它換成 hyphen——
# 換掉的話 stage 行會全部 match 不到，R-2.4 才會把它變成可觀察的失敗。
EM_DASH=$'\xe2\x80\x94'

# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------

# trim：複製 JS String.prototype.trim() 的行為（引擎 getField 對取到的值做的最後一步）。
trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# sanitise：剝除哨兵字元與 CR。見上方 NULL_SENTINEL 的說明。
sanitise() {
  local s="$1"
  s="${s//$'\001'/}"
  s="${s//$'\r'/}"
  printf '%s' "$s"
}

# --------------------------------------------------------------------------
# C-2 get_field — R-1 群
# --------------------------------------------------------------------------
# 複製引擎 getField() 的語意（[req:FR-J6]）。正本是 .claude/tools/aidlc-lib.ts:2676：
#
#   new RegExp(`^- \\*\\*${field}\\*\\*:[ \\t]*(.*)$`, "m")  →  match[1].trim()
#
# 逐條對應：
#   R-1.1 全檔搜尋、**第一個** match 即回傳（JS 的 .match 無 /g 只回第一個）
#   R-1.2 [ \t]* 而非 \s*，所以「存在但空」回空字串，**不是**下一行的內容
#   R-1.3 找不到回 null（本檔以 NULL_SENTINEL 表達）
#   R-1.4 ^- 錨在行首第 0 欄，縮排的 `  - **X**: ` **不視為 match**
#
# 回傳：欄位值（可能是空字串），或 NULL_SENTINEL 代表缺席。永遠 exit 0。
get_field() {
  local text="$1" name="$2"
  local prefix="- **${name}**:"
  local line rest

  while IFS= read -r line; do
    case "$line" in
      "$prefix"*)
        rest="${line#"$prefix"}"
        trim "$rest"
        return 0
        ;;
    esac
  done <<< "$text"

  printf '%s' "$NULL_SENTINEL"
  return 0
}

is_null() { [ "$1" = "$NULL_SENTINEL" ]; }

# null 與空字串在「是否非空」這個問題上結論相同（都是「否」），這個 helper 讓呼叫端
# 不必每次重寫；但**不要**用它取代 is_null——那正是 R-1.3 要防的合併。
is_blank() { [ "$1" = "$NULL_SENTINEL" ] || [ -z "$1" ]; }

# --------------------------------------------------------------------------
# C-2 list_stages — R-2 群
# --------------------------------------------------------------------------
# 逐檔解析 stage 清單，**不寫死**（[req:FR-J4]）。
#
#   R-2.1 只有形如 `- [<c>] <slug> — <EXECUTE|SKIP>` 的行算 stage 行
#   R-2.2 in_scope = (尾綴 == "EXECUTE")
#   R-2.3 區塊內不 match 的行一律靜默略過（### <PHASE> PHASE、HTML 註解、Per unit: [TBD]）
#   R-2.4 區塊在但零行 match → Unparseable{missing:["stage-lines"]}
#   R-2.5 無區塊 → Unparseable{missing:["stage-progress-section"]}
#
# 產出寫進全域 STAGES（每行 "<checkbox>\t<slug>\t<EXECUTE|SKIP>"），
# 失敗時寫進全域 PARSE_MISSING。
STAGES=""
PARSE_MISSING=""

list_stages() {
  local text="$1"
  local in_section=0 has_section=0 found=0
  local line
  local re='^- \[(.)\] (.+) '"$EM_DASH"' (EXECUTE|SKIP)$'

  STAGES=""
  PARSE_MISSING=""

  while IFS= read -r line; do
    # reviewer(code-generation) Major，2026-08-30T07:34:51Z：先前用 "## Stage Progress"* 前綴 glob，
    # 使 `## Stage Progress Notes (deprecated)` 這類誘餌標題被當成真區塊，其 stage 行
    # 靜默併進真清單。R-2.4／R-2.5 都抓不到——它們檢的是「零行 match」與「無區塊」，
    # 而誤匹配的 match 數非零。改為**精確比對**，僅容忍尾端空白。
    line_exact="${line%"${line##*[![:space:]]}"}"
    case "$line_exact" in
      "## Stage Progress")
        in_section=1
        has_section=1
        continue
        ;;
      "## "*)
        in_section=0
        continue
        ;;
    esac

    [ "$in_section" -eq 1 ] || continue

    # R-2.3：不 match 的行靜默略過。這裡沒有 else 分支，就是那條規則。
    if [[ "$line" =~ $re ]]; then
      STAGES="${STAGES}${BASH_REMATCH[1]}"$'\t'"${BASH_REMATCH[2]}"$'\t'"${BASH_REMATCH[3]}"$'\n'
      found=1
    fi
  done <<< "$text"

  if [ "$has_section" -eq 0 ]; then
    PARSE_MISSING="stage-progress-section"
    return 4
  fi
  if [ "$found" -eq 0 ]; then
    # R-2.4 的存在理由：只有 R-2.1–2.3 時，引擎若改變尾綴寫法，整批 stage 會被讀成
    # 非 stage 行 → stages 為空 → 判定第 6 條命中 → **誤判為 Ready 且不報錯**。
    # 這條檢查把那個靜默誤判變成可觀察的失敗。
    PARSE_MISSING="stage-lines"
    return 5
  fi
  return 0
}

# --------------------------------------------------------------------------
# scope_note — business-rules.md 的 scope_note 群（R-6.1–6.5）
# --------------------------------------------------------------------------
# 承載 [req:FR-F3]／U-2 的 R-1.2：`[S]`（在 scope 內被跳過）與 `— SKIP`（不在 scope 內）
# 的差別必須在受管區塊上看得見。
#
#   R-6.2 skipped-in-scope = in_scope 為真且 checkbox 為 "S" 的 slug
#         out-of-scope     = in_scope 為假的 slug
#   R-6.3 兩個分段一律都出現，該類為空時寫 none
#   R-6.4 依 record 內的**出現順序**排列，不排序、不去重、不截斷
#   R-6.5 兩類皆空時為 "skipped-in-scope: none; out-of-scope: none"，**不是空字串**
#
# R-6.4 的「不排序」不是隨便寫的：本欄位會進 Block 進而進 content_hash，順序一變雜湊
# 就變，每一輪都會判定為漂移而重寫。
compute_scope_note() {
  local skipped="" outs=""
  local cb slug sc

  while IFS=$'\t' read -r cb slug sc; do
    [ -n "$slug" ] || continue
    if [ "$sc" = "EXECUTE" ]; then
      if [ "$cb" = "S" ]; then
        skipped="${skipped:+$skipped, }$slug"
      fi
    else
      outs="${outs:+$outs, }$slug"
    fi
  done <<< "$STAGES"

  printf 'skipped-in-scope: %s; out-of-scope: %s' "${skipped:-none}" "${outs:-none}"
}

# --------------------------------------------------------------------------
# C-1 field_value_for — R-5 群
# --------------------------------------------------------------------------
# 格式 `<短前綴><stage-slug> (<編號>)`，前綴四選一。
#
#   R-5.1 超出上限時，**只截斷 stage-slug 的尾端**
#   R-5.2 前綴與 `(<編號>)` **永遠完整**，任何情況下不截斷
#   R-5.3 slug 可被截到**零長度**（此時前綴與左括號之間留原本的空格）
#   R-5.4 前綴 ＋ 編號本身已超過上限時，**照寫且允許超過上限**
#
# R-5.4 是刻意違反上限，不是漏判——**不要「順手修掉」它**。這個欄位存在的目的是讓人
# 看到「哪一個 intent 走到哪一站」（[US:S-5]）；狀態訊號（前綴）與可追溯的編號是它的
# 全部價值，截掉任一個，欄位就同時失去兩者。完整敘述仍在受管區塊，兩處不一致時以受管
# 區塊為準（[ad:decisions.md] ADR-A4）。
#
# 連帶約束（給 U-3）：board-client 的 write_field **不得**對本值做二次截斷。
build_field_value() {
  local prefix="$1" stage_part="$2" ident="$3" maxlen="$4"
  local suffix=" (${ident})"
  local value="${prefix}${stage_part}${suffix}"
  local budget

  if [ "${#value}" -le "$maxlen" ]; then
    printf '%s' "$value"
    return 0
  fi

  budget=$(( maxlen - ${#prefix} - ${#suffix} ))
  if [ "$budget" -lt 0 ]; then
    budget=0
  fi
  # R-5.3：budget 可以是 0，slug 就變成零長度。
  # R-5.4：budget 為 0 時結果仍可能超過 maxlen——照寫，不再截。
  printf '%s' "${prefix}${stage_part:0:$budget}${suffix}"
}

# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

# reviewer(code-generation) Minor #1，2026-08-30T07:34:51Z：先前只有 STATE_MD 經過 sanitise，
# 但上方 NULL_SENTINEL 的註解宣稱「輸入中的 \x01 全部剝除」。reviewer 查證該宣稱
# 目前不可利用（其餘輸入從不與哨兵比對），但**宣稱與實作不符本身就是缺陷**——
# 下一個新增「拿某個輸入與哨兵比對」的人會理所當然地相信那句註解。
# 處置是**讓宣稱成真**（把 sanitise 套到全部字串輸入），而不是把註解改弱。
STATE_MD="$(sanitise "${AIDLC_STATE_MD-}")"
RECORD_PATH="$(sanitise "${AIDLC_RECORD_PATH-}")"
RECORD_ROOT="$(sanitise "${AIDLC_RECORD_ROOT-}")"
FIELD_MAX_LENGTH="${AIDLC_FIELD_MAX_LENGTH-50}"
WHITELIST="$(sanitise "${AIDLC_WHITELIST-}")"
REVERSE_PENDING="$(sanitise "${AIDLC_REVERSE_PENDING-}")"

# AIDLC_INTENTS_JSON 是已核可介面的 7 個 input 之一，但**本檔目前不消費它**。
# 誠實記載為什麼（不要當成漏寫）：business-logic-model.md §步驟 1 第 3 點要求由
# intents_json 取綁定編號成為 ParsedRecord.binding，但
#   (a) 本 action 的五個 output 沒有一個承載 binding，R-1～R-6 沒有一條規則讀它；
#   (b) 綁定編號在 intents.json 裡的**鍵名上游從未指定**；
#   (c) [ad:component-methods.md] 把 read_binding(record_path) 定為 C-4（U-4）的方法，
#       與「從 intents_json 取」是兩個互相衝突的上游敘述。
# 在鍵名未定的情況下寫一個沒有任何讀者的解析器，只會產生一個看起來很權威、實際是猜的
# 值。已列為交付回報中的 open item，待閘門裁決後再補。
: "${AIDLC_INTENTS_JSON-}"

# intent_id：由 record_path 推導，**不從內文取**（domain-entities.md）。
# record_root 參與推導而非被寫死（[F1=A]）：優先取 record_path 相對於 record_root 的
# 第一段；record_path 不在 record_root 底下時退回 basename。
derive_intent_id() {
  local p="${1%/}" root="${2%/}" rel
  if [ -n "$root" ] && [ "${p#"$root"/}" != "$p" ]; then
    rel="${p#"$root"/}"
    printf '%s' "${rel%%/*}"
  else
    printf '%s' "${p##*/}"
  fi
}

# 換行分隔的集合成員判定（[Q1=A]／[Q2=A] 的承載形式：換行分隔，空字串為空集合）。
set_contains() {
  local needle="$1" haystack="$2" item
  [ -n "$needle" ] || return 1
  while IFS= read -r item; do
    item="$(trim "$item")"
    [ -n "$item" ] || continue
    [ "$item" = "$needle" ] && return 0
  done <<< "$haystack"
  return 1
}

emit() {
  local name="$1" value="$2"
  value="$(sanitise "$value")"
  value="${value//$'\n'/ }"
  printf '%s=%s\n' "$name" "$value"
  if [ -n "${GITHUB_OUTPUT-}" ]; then
    printf '%s=%s\n' "$name" "$value" >> "$GITHUB_OUTPUT"
  fi
}

run_pipeline() {
  local intent_id current_stage runtime_status parked parked_at_stage
  local status="" reason_code="" traceable_row="" field_value="" scope_note=""
  local rc=0

  intent_id="$(derive_intent_id "$RECORD_PATH" "$RECORD_ROOT")"

  # ---- 步驟 1：parse -------------------------------------------------------
  current_stage="$(get_field "$STATE_MD" "Current Stage")"
  runtime_status="$(get_field "$STATE_MD" "Status")"
  parked="$(get_field "$STATE_MD" "Parked")"
  parked_at_stage="$(get_field "$STATE_MD" "Parked At Stage")"

  set +e
  list_stages "$STATE_MD"
  rc=$?
  set -e

  scope_note="$(compute_scope_note)"

  if [ "$rc" -ne 0 ]; then
    # ---- Unparseable：R-4 群 ---------------------------------------------
    # R-4.3：白名單**只對 Unparseable 生效**，不影響可解析 record 的判定
    #        （[req:FR-J5] 的白名單豁免的是解析失敗，不是判定結果）。
    if set_contains "$intent_id" "$WHITELIST"; then
      reason_code="whitelisted"
      traceable_row="R-4.1 whitelisted (missing: ${PARSE_MISSING})"
    else
      reason_code="unparseable"
      traceable_row="R-4.2 unparseable (missing: ${PARSE_MISSING})"
    fi
    status=""
    field_value=""
    # scope_note 在此路徑上沒有 stages 可推導，依 R-6.5 給非空的雙 none。
    # 這是 open-items.md 的 B:m-5（Unparseable 路徑的 scope_note 值未定義），
    # 落點為 Bolt 1 gate；此處採 R-6.5 的字面要求，不是新裁決。
  else
    # ---- 步驟 2：map 的七條判定順序（R-3 群），先到先得，命中即停 ---------
    local cb slug sc
    local has_question=0 has_progress=0 all_untouched=1

    while IFS=$'\t' read -r cb slug sc; do
      [ -n "$slug" ] || continue
      [ "$sc" = "EXECUTE" ] || continue
      case "$cb" in
        '?') has_question=1 ;;
        '-'|'R') has_progress=1 ;;
      esac
      # R-3.6 的「動過」定義：in-scope stage 的 checkbox 全部落在 {" ", "S"}。
      # **"S"（--stage/--phase jump 跳過）不算動過。**
      #
      # 不要把 "S" 移出這個集合。[req:FR-B3] 的驗收逐字要求「兩個只在 [S]／— SKIP 上
      # 不同的 record 產出**相同**的 Status」（[US:S-2 AC 5] 同）：— SKIP 的孿生 record
      # 中該 stage 不在 in_scope，其餘 in-scope 全為 [ ] ⇒ 命中 R-3.6 ⇒ Ready。
      # 若 "S" 算動過，[S] 那一個就落到 R-3.7 ⇒ undecidable ⇒ 兩者 Status 不同，
      # AC 直接失敗。差別不會因此消失——它由 R-5 的 `skipped ` 前綴與 scope_note 承接。
      case "$cb" in
        ' '|'S') ;;
        *) all_untouched=0 ;;
      esac
    done <<< "$STAGES"

    if ! is_blank "$parked"; then
      # R-3.1 parked 為非空字串（R-1.3 的 null 與 R-1.2 的空字串都不觸發）
      status=""; reason_code="parked"; traceable_row="R-3.1 parked"
    elif set_contains "$intent_id" "$REVERSE_PENDING"; then
      # R-3.2 有未處理反向紀錄（[req:FR-G3]；集合由 workflow 層在迴圈前算好傳入）
      status=""; reason_code="suppressed"; traceable_row="R-3.2 suppressed"
    elif [ "$runtime_status" = "Completed" ]; then
      # R-3.3 讀 Status 欄位而非推導 checkbox（[US:S-2 AC 3]）。
      # 先於第 4／5 條是刻意的：Completed 的 record 不應因殘留的 [?] 而回退。
      status="Done"; reason_code="mapped"; traceable_row="R-3.3 runtime-status-completed"
    elif [ "$has_question" -eq 1 ]; then
      status="In review"; reason_code="mapped"; traceable_row="R-3.4 in-scope-checkbox-question"
    elif [ "$has_progress" -eq 1 ]; then
      status="In progress"; reason_code="mapped"; traceable_row="R-3.5 in-scope-checkbox-in-progress"
    elif [ "$all_untouched" -eq 1 ]; then
      status="Ready"; reason_code="mapped"; traceable_row="R-3.6 no-in-scope-stage-touched"
    else
      # R-3.7 是窮盡二分的另一半，不是防禦性程式碼——它保證了總函式性（[US:S-2 AC 15]）。
      status=""; reason_code="undecidable"; traceable_row="R-3.7 undecidable"
    fi

    # ---- 步驟 3：field_value_for -----------------------------------------
    field_value="$(compose_field_value \
      "$reason_code" "$current_stage" "$parked" "$parked_at_stage" "$intent_id")"
  fi

  emit status        "$status"
  emit field_value   "$field_value"
  emit reason_code   "$reason_code"
  emit traceable_row "$traceable_row"
  emit scope_note    "$scope_note"
}

# 前綴選擇 ＋ 組值。前綴四選一：無／`parked @ `／`skipped `／`frozen: `，
# 描述的是**當前 stage** 的處境（business-logic-model.md §步驟 3 第 1 點）。
compose_field_value() {
  local reason="$1" current_stage="$2" parked="$3" parked_at_stage="$4" ident="$5"
  local prefix="" stage_part="" cb slug sc cur_cb="" cur_scope=""

  # undecidable 沒有對應的前綴。[ad:component-methods.md] 經 ADR-0015 §14 標記：
  # 「在此之前 undecidable 的自訂欄位行為未定義，**實作不得自行猜**」。
  # 因此這裡不寫值（Decision.field_value 的值域明訂「可為空」），而不是掰一個前綴。
  # 確認人為 Bolt 1 的 gate。
  if [ "$reason" = "undecidable" ]; then
    printf ''
    return 0
  fi

  is_null "$current_stage" && current_stage=""
  is_null "$parked_at_stage" && parked_at_stage=""

  stage_part="$current_stage"

  # 找出「當前 stage」在 stage 清單中的那一列，用來判斷 skipped / frozen。
  if [ -n "$current_stage" ]; then
    while IFS=$'\t' read -r cb slug sc; do
      [ -n "$slug" ] || continue
      if [ "$slug" = "$current_stage" ]; then
        cur_cb="$cb"
        cur_scope="$sc"
        break
      fi
    done <<< "$STAGES"
  fi

  if ! is_blank "$parked"; then
    prefix="parked @ "
    # domain-entities.md：parked_at_stage「僅用於組 field_value 的 `parked @ ` 前綴
    # 內容」。缺席時退回 current_stage，讓欄位仍然指得出一站。
    if [ -n "$parked_at_stage" ]; then
      stage_part="$parked_at_stage"
    fi
  elif [ "$cur_cb" = "S" ]; then
    prefix="skipped "
  elif [ -n "$cur_scope" ] && [ "$cur_scope" != "EXECUTE" ]; then
    # [req:FR-B3] 的 `— SKIP` 情形：當前 stage 根本不在 scope 內。
    prefix="frozen: "
  fi

  build_field_value "$prefix" "$stage_part" "$ident" "$FIELD_MAX_LENGTH"
}

# --------------------------------------------------------------------------
# 進入點
# --------------------------------------------------------------------------
main() {
  local cmd="${1:-run}"
  local rc=0
  local v

  case "$cmd" in
    run)
      run_pipeline
      ;;
    get_field)
      [ $# -ge 2 ] || { printf 'usage: map.sh get_field <field-name>\n' >&2; exit 2; }
      v="$(get_field "$STATE_MD" "$2")"
      if is_null "$v"; then
        # R-1.3：缺席。退出碼 3 讓呼叫端能與「存在但空」（退出 0 ＋ 空 stdout）分辨。
        exit 3
      fi
      printf '%s' "$v"
      ;;
    list_stages)
      set +e
      list_stages "$STATE_MD"
      rc=$?
      set -e
      if [ "$rc" -ne 0 ]; then
        printf '%s\n' "$PARSE_MISSING" >&2
        exit "$rc"
      fi
      printf '%s' "$STAGES"
      ;;
    scope_note)
      set +e
      list_stages "$STATE_MD"
      set -e
      compute_scope_note
      printf '\n'
      ;;
    *)
      printf 'map.sh: unknown subcommand: %s\n' "$cmd" >&2
      exit 2
      ;;
  esac
}

main "$@"
