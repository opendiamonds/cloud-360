#!/usr/bin/env bash
#
# board.sh — U-3「看板客戶端」的全部邏輯。
#
# 本檔承載 [ad:C-3 board-client]：整個同步機制中**唯一**碰 Projects v2 與 GitHub
# Issues API 的元件。與 U-1 的 map.sh、U-2 的 block.sh 不同，**本檔不是純函式**——
# 它做真實網路 I/O、持有憑證，也因此是三個 library 單元中唯一會產生紅燈級錯誤的。
#
# ==========================================================================
# 契約（呼叫端依賴，請勿變更）
# ==========================================================================
# 七個 operation（component-methods.md §C-3 ＋ ADR-0015 §11 的 write_body）：
#
#   read_item        (binding, Config) -> ItemState
#                    {status, field_value, managed_block_hash, issue_number,
#                     issue_state} 五欄，空字串＝null。零筆分支（R-1.3）回全 null；
#                    同 Project 多筆（R-1.4）→ ExternalError。
#   create_item      (intent_id, Config) -> binding
#                    AIDLC_EXISTING_BINDING 非空 → 不建、原值回傳、零 API 呼叫
#                    （R-3.1）。首建前解析 Config 的 Project 並驗證可寫（R-3.2）。
#                    **不回寫綁定編號**（R-3.3，那是 U-4 的職責）。
#   write_status     (binding, expected, desired) -> WriteResult
#                    必先回讀（R-2.1）；actual != expected → Aborted{actual,
#                    expected}，不送出寫入、不開 issue、不紅燈（R-2.2／R-2.3）。
#                    item 不在板上（R-1.3 零筆）→ 同樣 Aborted，actual 為空、
#                    message 說明無寫入對象；**本 operation 不產生 Failed**
#                    （上游契約把 Failed 限定為 write_field／write_body）。
#                    只比對 Status 欄位；AIDLC_EXPECTED_STATUS 空值＝期望未設值
#                    （Plan Approval 定案）。欄位解析（name→option id）在回讀
#                    之前完成，回讀與 mutation 之間沒有其他呼叫。
#   write_field      (binding, value) -> WriteResult
#                    欄位不存在時嘗試建立；任何失敗 → Failed{http_status, message}
#                    回傳值，不連坐 Status 寫入（R-4.1）。
#   ensure_field     (Config) -> FieldRef | CannotCreate
#                    兩種可達失敗前提（憑證缺 Projects 寫入權／同名欄位型別不同）
#                    → CannotCreate（ADR-0016 §1：「組織政策阻擋」不可達，不實作）。
#   read_issue_state (binding) -> "open" | "closed"
#   write_body       (binding, block_text) -> WriteResult
#                    受管區塊唯一的持久化路徑（R-6 群）。無標記附加、有標記整段
#                    替換（R-6.3）；標記損壞 → Failed，不猜不附加（R-6.6）；
#                    不做長度截斷（R-6.5）；失敗不連坐（R-6.4）。
#
# Config 承載為三個 env：AIDLC_PROJECT_OWNER／AIDLC_PROJECT_NUMBER／
# AIDLC_FIELD_NAME。issue 所在 repo 取自 GITHUB_REPOSITORY（runner 提供）。
#
# ==========================================================================
# 錯誤模型（讀之前先讀這段——四個型別的傳播方式**不同**，不能混為一談）
# ==========================================================================
# business-logic-model.md 定死的混合形狀：
#
#   ExternalError { http_status }   **例外式，非零 exit**。API 呼叫失敗、R-1.4 的
#                                   多筆斷言、Status 寫入路徑的任何失敗。workflow
#                                   因此紅燈（[ad:services.md] 明列的兩種紅燈之一）。
#                                   exit 前已寫出 result=external_error／http_status
#                                   ／message 三個 output，供 if failure() 的通報
#                                   步驟取用。
#   Aborted { actual, expected }    **回傳值，exit 0**。回讀不符的主動中止
#                                   （[req:FR-C1]），屬機制的正常判斷，不紅燈。
#                                   兩種來源：actual != expected；item 不在板上
#                                   （item 存在是回讀比對的前置條件，前置條件
#                                   不成立即為不符）。兩者都附 message。
#   Failed { http_status, message } **回傳值，exit 0**。write_field／write_body
#                                   專屬，不連坐 Status 寫入、不紅燈。
#   CannotCreate                    **回傳值，exit 0**。ensure_field 專屬，交 C-5
#                                   通報「需人工建立欄位」，不紅燈。
#
# 不得把「有回讀比對」讀成「寫入是原子的」：R-2.1 擋的是上一輪之後、本輪回讀之前
# 的改動，**擋不掉回讀之後的**。Projects v2 沒有 compare-and-swap，回讀與 mutation
# 之間的競態視窗（R-2.4）**無兜底**——視窗內被覆寫的協作者改動會靜默丟失，反向
# 同步也不會發現（機制自己的回寫會把雜湊比對基準重置成自己寫的值）。此代價已由
# ADR-0015 §2 綁進 Bolt 1 gate 的揭露項；本檔不做、也做不出任何補救。
# 欄位解析（list_fields／resolve_status_option）在回讀之前完成，視窗內只有一次
# mutation 往返——這是 business-rules.md R-2.4 對 Bolt 1 gate 揭露的視窗量級
# （「約為單次 mutation 往返時間」），實作不得在回讀與 mutation 之間插入其他呼叫。
#
# 每一次 gh api graphql 呼叫都檢查**兩層**：exit code **與** body 的 .errors——
# GraphQL 在錯誤時仍回 HTTP 200 並把錯誤放在 body（tech-stack-decisions.md：只檢查
# 其中一層即為缺陷）。`NOT_FOUND` 同時涵蓋「不存在」與「無權限」（ADR-0016 §4.3），
# **不得**把它對應成「這張卡不在板上」——R-1.3 的零筆分支只能由「查詢成功且過濾後
# 為零筆」進入；誤對應的後果是權限退化時靜默走上補建分支且不會紅燈。
#
# ==========================================================================
# 安全邊界
# ==========================================================================
# SEC-1  憑證只經 env GH_TOKEN 傳入（gh CLI 原生讀取），action.yml 不宣告任何
#        憑證型 input。本檔不讀、不印、不落地 token。
# SEC-4  對外的 message 只含 GraphQL errors[].message（或 REST 的 message 欄位）
#        與 HTTP 狀態碼，**不含完整請求／回應 body、不含任何標頭**——這些訊息會被
#        C-5 寫進公開 issue（本 repo 為 public）。見 clean 系列函式。
# R-5    本檔不提供任何「推 commit」或「改 record 目錄以外的檔案」的 operation；
#        未知 operation 一律非零 exit。但「介面不提供」≠「嘗試時回 403」
#        （SEC-2）——憑證本身帶 repo 寫入權，介面約束靠 review 與 stub 斷言維持。
# 隔離   測試看板與正式看板（#16）的隔離靠 Config 的 Project 編號，**不靠權限**
#        （SEC-3）。本檔不硬編任何 Project 編號；run-live-tests.py 進場斷言
#        AIDLC_PROJECT_NUMBER != 16。
#
# 受管標記的**單一真實來源在 U-2**（R-6.2）：本檔於執行期自 ../aidlc-sync-block/
# block.sh 萃取 MARKER_SIGIL／MARKER_END 的賦值行，不得複製字面常數進本檔——
# 副本會落在 U-2 的 R-4 群互鎖之外。萃取失敗即 fail fast（exit 2）。
#
# 規格正本：
#   ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
#     U-3-board-client/functional-design/business-rules.md        （R-1〜R-6 群）
#     U-3-board-client/functional-design/domain-entities.md       （ItemState／錯誤型別）
#     U-3-board-client/functional-design/business-logic-model.md  （資料流／混合錯誤形狀）
#     U-3-board-client/nfr-requirements/tech-stack-decisions.md   （兩層錯誤檢查）
#     U-3-board-client/nfr-requirements/security-requirements.md  （SEC-1〜SEC-4）
#     ../PRE-1-results.md 第四〜六輪 ＋ ../../inception/decisions/0016-*.md
#     （查詢根 user(login:)、錯誤分類法、name→id 執行期解析、R-1.4 冪等實測）
#
# 依賴：gh（GitHub CLI，runner 預裝）、jq、sha256 由 U-2 的 block.sh 間接使用。
# 相容性：以 bash 3.2 可執行為底線（macOS 內建版本），不使用關聯陣列、mapfile、
# ${var^^} 等 bash 4+ 語法。GitHub runner 的 bash 5 亦可執行。
#
# 用法（operation 由 $AIDLC_OPERATION 指定；argv 第一參數可覆寫，測試用）：
#   board.sh                            依 env 執行一個 operation
#   board.sh markers                    診斷：印出自 U-2 萃取的標記常數（stub 互鎖用）
#   board.sh resolve_status <名稱>      診斷：解析一個 Status 選項名稱的 option id
#                                       （live 測試 (d) 用；會發真實查詢）

set -euo pipefail

# 固定 locale：本檔做字面比對與 jq 過濾，不做排序，但不依賴「目前沒有排序」這個
# 會被未來改動打破的前提（與 U-1／U-2 同一理由）。
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# U-2 的 block.sh：受管標記與雜湊的單一真實來源。路徑為 sibling action——兩支
# action 同進 repo、同進 checkout，這個相對路徑在 runner 與本機都成立。
BLOCK_SH="${SCRIPT_DIR}/../aidlc-sync-block/block.sh"

# $GITHUB_OUTPUT 的多行分隔符（本檔的 output 值皆單行，heredoc 形式對單行值同樣
# 合法，故不分兩種寫法——沿用 U-2 的做法）。
GH_DELIM="__AIDLC_SYNC_BOARD_EOF__"

# ==========================================================================
# 小工具（emit／gh_output 沿用 U-2 的形狀）
# ==========================================================================

fail() {
  printf 'board.sh: %s\n' "$1" >&2
  exit 2
}

emit() {
  local name="$1" value="$2"
  printf '%s=%s\n' "$name" "$value"
  gh_output "$name" "$value"
}

gh_output() {
  local name="$1" value="$2"
  [ -n "${GITHUB_OUTPUT-}" ] || return 0
  case "$value" in
    *"$GH_DELIM"*)
      fail "output ${name} 的值含 GITHUB_OUTPUT 分隔符 ${GH_DELIM}，拒絕寫出"
      ;;
  esac
  printf '%s<<%s\n%s\n%s\n' "$name" "$GH_DELIM" "$value" "$GH_DELIM" >> "$GITHUB_OUTPUT"
}

# 把可能含換行的文字壓成單行（output 為 name=value 單行形式；GraphQL 的
# errors[].message 偶含換行）。
single_line() {
  local s="$1"
  s="${s//$'\r'/ }"
  s="${s//$'\n'/ }"
  printf '%s' "$s"
}

is_positive_integer() {
  case "$1" in
    ""|*[!0-9]*) return 1 ;;
    0*) return 1 ;;
  esac
  return 0
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

# 從多行 name=value 輸出中取一個值（讀 U-2 block.sh 的 stdout 用）。
line_value() {
  local text="$1" name="$2" line
  while IFS= read -r line; do
    case "$line" in
      "$name="*)
        printf '%s' "${line#"$name"=}"
        return 0
        ;;
    esac
  done <<< "$text"
  return 1
}

# ==========================================================================
# 輸入驗證（介面誤用一律 exit 2 fail fast——這不是判定結果，是呼叫端 bug）
# ==========================================================================

PROJECT_OWNER="${AIDLC_PROJECT_OWNER:-}"
PROJECT_NUMBER="${AIDLC_PROJECT_NUMBER:-}"
FIELD_NAME="${AIDLC_FIELD_NAME:-}"

require_project_config() {
  [ -n "$PROJECT_OWNER" ] || fail "缺少 AIDLC_PROJECT_OWNER（Config）"
  is_positive_integer "$PROJECT_NUMBER" || fail "AIDLC_PROJECT_NUMBER 必須是正整數，得到：'${PROJECT_NUMBER}'"
}

require_field_name() {
  [ -n "$FIELD_NAME" ] || fail "缺少 AIDLC_FIELD_NAME（Config）"
}

REPO_OWNER=""
REPO_NAME=""
require_repo() {
  local repo="${GITHUB_REPOSITORY:-}"
  [ -n "$repo" ] || fail "缺少 GITHUB_REPOSITORY（runner 提供的 owner/repo）"
  case "$repo" in
    */*) ;;
    *) fail "GITHUB_REPOSITORY 格式須為 owner/repo，得到：'${repo}'" ;;
  esac
  REPO_OWNER="${repo%%/*}"
  REPO_NAME="${repo#*/}"
}

require_binding() {
  is_positive_integer "${AIDLC_BINDING:-}" || fail "binding 必須是正整數（issue 編號），得到：'${AIDLC_BINDING:-}'"
}

# ==========================================================================
# GraphQL 包裝：兩層檢查 ＋ SEC-4 清洗
# ==========================================================================
# 每次呼叫後檢查 (1) exit code 與 (2) body 的 .errors——GraphQL 在錯誤時仍回
# HTTP 200 並把錯誤放在 body（tech-stack-decisions.md：只檢查一層即為缺陷；
# gh 自己雖然也會對 GraphQL errors 非零 exit，但本檔不依賴工具的這個行為）。
#
# 成功：回 0，GQL_BODY 為回應 JSON。
# 失敗：回 1，並設定——
#   GQL_STATUS    HTTP 狀態碼；GraphQL 層錯誤（body 有 .errors）時為 200；
#                 stderr 抓得到 "HTTP nnn" 時用抓到的值；否則為空（無法判定）
#   GQL_ERRMSG    **SEC-4 清洗後**的訊息：只含 errors[].message 的串接；body 無
#                 可解析 errors 時為固定文字。不含 body 全文、不含標頭。
#   GQL_ERRTYPES  errors[].type 的空白分隔串（ensure_field 的分類用）
GQL_BODY=""
GQL_STATUS=""
GQL_ERRMSG=""
GQL_ERRTYPES=""

gql() {
  local stderr_file rc=0 stderr_content="" nerr="0"
  GQL_BODY=""; GQL_STATUS=""; GQL_ERRMSG=""; GQL_ERRTYPES=""
  stderr_file="$(mktemp)"
  if ! GQL_BODY="$(gh api graphql "$@" 2>"$stderr_file")"; then
    rc=1
  fi
  stderr_content="$(cat "$stderr_file" 2>/dev/null || true)"
  rm -f "$stderr_file"

  if [ -n "$GQL_BODY" ] && printf '%s' "$GQL_BODY" | jq -e . >/dev/null 2>&1; then
    nerr="$(printf '%s' "$GQL_BODY" | jq -r '(.errors // []) | length')"
  fi

  if [ "$rc" -eq 0 ] && [ "$nerr" = "0" ]; then
    return 0
  fi

  # ---- 失敗分類與 SEC-4 清洗 ----
  if [ "$nerr" != "0" ]; then
    GQL_ERRMSG="$(printf '%s' "$GQL_BODY" | jq -r '[.errors[].message] | join("; ")')"
    GQL_ERRTYPES="$(printf '%s' "$GQL_BODY" | jq -r '[.errors[] | (.type // "UNKNOWN")] | join(" ")')"
    GQL_STATUS="200"
  else
    # HTTP／CLI 層失敗且 body 無可解析的 errors。**不得**把 body 或 stderr 全文
    # 塞進訊息（SEC-4：錯誤輸出可能回顯請求內容）。
    GQL_ERRMSG="API 呼叫失敗（回應無可解析的 GraphQL errors）"
  fi
  local re='HTTP ([0-9]{3})'
  if [[ "$stderr_content" =~ $re ]]; then
    GQL_STATUS="${BASH_REMATCH[1]}"
  fi
  GQL_ERRMSG="$(single_line "$GQL_ERRMSG")"
  return 1
}

# REST 包裝（issue 的 GET／POST／PATCH 走 REST）。錯誤時只取回應 JSON 的 .message
# 欄位與 stderr 的 HTTP 狀態碼——同一條 SEC-4 清洗規則。
REST_BODY=""
REST_STATUS=""
REST_ERRMSG=""

rest() {
  local stderr_file rc=0 stderr_content=""
  REST_BODY=""; REST_STATUS=""; REST_ERRMSG=""
  stderr_file="$(mktemp)"
  if ! REST_BODY="$(gh api "$@" 2>"$stderr_file")"; then
    rc=1
  fi
  stderr_content="$(cat "$stderr_file" 2>/dev/null || true)"
  rm -f "$stderr_file"
  if [ "$rc" -eq 0 ]; then
    return 0
  fi
  if [ -n "$REST_BODY" ] && printf '%s' "$REST_BODY" | jq -e '.message' >/dev/null 2>&1; then
    REST_ERRMSG="$(printf '%s' "$REST_BODY" | jq -r '.message')"
  else
    REST_ERRMSG="API 呼叫失敗（回應無可解析的錯誤訊息）"
  fi
  local re='HTTP ([0-9]{3})'
  if [[ "$stderr_content" =~ $re ]]; then
    REST_STATUS="${BASH_REMATCH[1]}"
  fi
  REST_ERRMSG="$(single_line "$REST_ERRMSG")"
  return 1
}

# ExternalError 的唯一出口：先寫出三個 output（供 if failure() 的通報步驟取用），
# 再非零 exit（例外式——[ad:component-methods.md] 的「拋」，workflow 因此紅燈）。
# $1 = 定位前綴（本檔自己的文字，說明失敗發生在哪一步；不含任何 API 回應內容以外
# 的機敏資料），$2 = 清洗後的錯誤訊息，$3 = HTTP 狀態碼（可為空）。
external_error() {
  local where="$1" msg="$2" status="${3:-}"
  emit result external_error
  emit http_status "$status"
  emit message "$(single_line "${where}：${msg}")"
  printf 'board.sh: ExternalError（%s）：%s\n' "$where" "$msg" >&2
  exit 1
}

# ==========================================================================
# 受管標記：執行期自 U-2 萃取（R-6.2 的單一真實來源；Plan Approval 定案）
# ==========================================================================
# 讀 block.sh 的 MARKER_SIGIL=／MARKER_END= 賦值行取值。**不得**把字面常數複製進
# 本檔——副本會落在 U-2 的 R-4 群互鎖（格式變更必須 bump 版本＋重建 golden）之外，
# U-2 改格式時本檔會拿著舊標記靜默錯位。萃取失敗即 fail fast：這是環境問題
# （sibling action 不在、或 U-2 重構了常數形狀），不是判定結果。
MARKER_SIGIL=""
MARKER_END=""

extract_marker() {
  # $1 = 變數名。印出賦值行引號內的值。
  local name="$1" line=""
  [ -f "$BLOCK_SH" ] || fail "找不到 U-2 的 block.sh（${BLOCK_SH}），無法萃取受管標記"
  line="$(grep -E "^${name}=\"" "$BLOCK_SH" | head -n 1 || true)"
  [ -n "$line" ] || fail "無法自 block.sh 萃取 ${name} 的賦值行（R-6.2 的單一真實來源）"
  line="${line#"${name}"=\"}"
  line="${line%\"}"
  printf '%s' "$line"
}

load_markers() {
  MARKER_SIGIL="$(extract_marker MARKER_SIGIL)"
  MARKER_END="$(extract_marker MARKER_END)"
  # 形狀 sanity check：兩者都是 HTML 註解（domain-entities.md 的標記定義）。萃取到
  # 別的東西代表 U-2 重構了常數形狀，寧可停下也不帶著錯的標記去改 issue body。
  case "$MARKER_SIGIL" in
    "<!--"*) ;;
    *) fail "萃取到的 MARKER_SIGIL 形狀不對：'${MARKER_SIGIL}'" ;;
  esac
  case "$MARKER_END" in
    "<!--"*"-->") ;;
    *) fail "萃取到的 MARKER_END 形狀不對：'${MARKER_END}'" ;;
  esac
}

# 呼叫 U-2 的 block.sh 時（內部 library 呼叫）**必須**清空 GITHUB_OUTPUT——否則
# block.sh 的 parse 輸出（found／block_*）會污染本 action 的 output 檔。呼叫點
# 一律以 env 前綴直接掛在 bash 指令上（不掛在 shell function 上——bash 對「env
# 前綴 ＋ function 呼叫」的變數存續語意有歷史歧義，不賭它）。

# ==========================================================================
# 查詢字串（實測依據：PRE-1 第四〜六輪；查詢根 user(login:) 為 ADR-0016 §4.1）
# ==========================================================================

# read_item 的反查（[Q1=A]：Issue.projectItems，不列舉整個 Project；同擁有者即可
# 反查，不需 repo↔project link——PRE-1 第五輪實測）。first:50 不分頁：[Q1=A] 已
# 消掉本路徑的分頁（domain-entities.md），一個 issue 同時屬於 50+ 個 Project 不是
# 本機制可解釋的狀態。
READ_ITEM_QUERY='query($owner:String!,$name:String!,$number:Int!,$fieldName:String!){
  repository(owner:$owner,name:$name){
    issue(number:$number){
      state
      body
      projectItems(first:50){
        totalCount
        nodes{
          id
          project{ id number owner{ ... on User{ login } ... on Organization{ login } } }
          statusValue: fieldValueByName(name:"Status"){
            ... on ProjectV2ItemFieldSingleSelectValue{ name }
          }
          customValue: fieldValueByName(name:$fieldName){
            ... on ProjectV2ItemFieldTextValue{ text }
          }
        }
      }
    }
  }
}'

ISSUE_STATE_QUERY='query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){
    issue(number:$number){ state }
  }
}'

PROJECT_QUERY='query($owner:String!,$number:Int!){
  user(login:$owner){
    projectV2(number:$number){ id viewerCanUpdate }
  }
}'

# 欄位列舉（唯一需要分頁的地方——domain-entities.md「需要分頁的地方」；游標分頁
# 形狀經 PRE-1 第五輪實測）。ProjectV2SingleSelectField 的 options 供 name→id
# 解析（R-4.4）。
FIELDS_QUERY='query($owner:String!,$number:Int!,$cursor:String){
  user(login:$owner){
    projectV2(number:$number){
      fields(first:50,after:$cursor){
        pageInfo{ hasNextPage endCursor }
        nodes{
          ... on ProjectV2FieldCommon{ id name dataType }
          ... on ProjectV2SingleSelectField{ options{ id name } }
        }
      }
    }
  }
}'

UPDATE_SELECT_MUTATION='mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){
  updateProjectV2ItemFieldValue(input:{
    projectId:$projectId,itemId:$itemId,fieldId:$fieldId,
    value:{singleSelectOptionId:$optionId}
  }){ projectV2Item{ id } }
}'

UPDATE_TEXT_MUTATION='mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$text:String!){
  updateProjectV2ItemFieldValue(input:{
    projectId:$projectId,itemId:$itemId,fieldId:$fieldId,
    value:{text:$text}
  }){ projectV2Item{ id } }
}'

CREATE_FIELD_MUTATION='mutation($projectId:ID!,$name:String!){
  createProjectV2Field(input:{projectId:$projectId,dataType:TEXT,name:$name}){
    projectV2Field{ ... on ProjectV2FieldCommon{ id name } }
  }
}'

ADD_ITEM_MUTATION='mutation($projectId:ID!,$contentId:ID!){
  addProjectV2ItemById(input:{projectId:$projectId,contentId:$contentId}){
    item{ id }
  }
}'

# ==========================================================================
# 讀取層
# ==========================================================================

# read_item 的核心：反查 → R-1.2 過濾 → 依筆數分支。成功回 0 並設定：
#   ISSUE_STATE（小寫 open/closed）、ISSUE_BODY、ITEM_COUNT（過濾後筆數）、
#   ITEM_ID／ITEM_PROJECT_ID／ITEM_STATUS／ITEM_FIELD_VALUE（僅 ITEM_COUNT=1 時有值）
# 失敗（API 錯誤）回 1，錯誤內容在 GQL_*。**R-1.4（多筆）不在這裡裁定**——由呼叫端
# 統一以 external_error 收場，因為每一條經過查找的路徑都必須套用同一條斷言。
ISSUE_STATE=""
ISSUE_BODY=""
ITEM_COUNT=""
ITEM_ID=""
ITEM_PROJECT_ID=""
ITEM_STATUS=""
ITEM_FIELD_VALUE=""

read_item_core() {
  local matches
  gql -f query="$READ_ITEM_QUERY" \
      -f owner="$REPO_OWNER" -f name="$REPO_NAME" \
      -F number="$AIDLC_BINDING" -f fieldName="$FIELD_NAME" || return 1

  ISSUE_STATE="$(to_lower "$(printf '%s' "$GQL_BODY" | jq -r '.data.repository.issue.state')")"
  ISSUE_BODY="$(printf '%s' "$GQL_BODY" | jq -r '.data.repository.issue.body // ""')"

  # R-1.2 的過濾：反查會拿到 issue 所屬的**全部** Project（PRE-1 第五輪實測
  # totalCount:2 的形狀），過濾出 Config 指定的那一個。Project 編號精確比對；
  # 擁有者 login 依 GitHub 自己的語意做 ASCII 不分大小寫比對——login 在 GitHub
  # 是不分大小寫的識別字，逐字元比對會把 Config 大小寫差異誤判成「不在板上」，
  # 而那個誤判正是 ADR-0016 §4.3 警告的靜默補建路徑。
  matches="$(printf '%s' "$GQL_BODY" | jq -c \
    --arg owner "$PROJECT_OWNER" --argjson num "$PROJECT_NUMBER" \
    '[.data.repository.issue.projectItems.nodes[]
      | select(.project.number == $num
               and ((.project.owner.login // "") | ascii_downcase) == ($owner | ascii_downcase))]')"

  ITEM_COUNT="$(printf '%s' "$matches" | jq -r 'length')"
  ITEM_ID=""
  ITEM_PROJECT_ID=""
  ITEM_STATUS=""
  ITEM_FIELD_VALUE=""
  if [ "$ITEM_COUNT" = "1" ]; then
    ITEM_ID="$(printf '%s' "$matches" | jq -r '.[0].id')"
    ITEM_PROJECT_ID="$(printf '%s' "$matches" | jq -r '.[0].project.id')"
    ITEM_STATUS="$(printf '%s' "$matches" | jq -r '.[0].statusValue.name // ""')"
    ITEM_FIELD_VALUE="$(printf '%s' "$matches" | jq -r '.[0].customValue.text // ""')"
  fi
  return 0
}

# R-1.4：同一 Project 內多於一筆 item ⇒ 看板狀態已壞，不猜哪一筆（與 [req:FR-C1]
# 「拿不準時不寫」同精神）。**防禦性斷言，無可構造的反例**（ADR-0016 §6：
# addProjectV2ItemById 冪等，本機制自己的 mutation 產生不出兩筆；本分支由 stub
# 測試覆蓋，不發明假的 live 觸發途徑）。
assert_single_item() {
  if [ "$ITEM_COUNT" != "0" ] && [ "$ITEM_COUNT" != "1" ]; then
    external_error "read_item" \
      "R-1.4：issue #${AIDLC_BINDING} 在 Project #${PROJECT_NUMBER} 內有 ${ITEM_COUNT} 筆 item，看板狀態非本機制可解釋，拒絕繼續" \
      "200"
  fi
}

# managed_block_hash：把 issue body 轉交 U-2 的 parse ＋ hash。**不是本檔算的**
# （domain-entities.md：自算即第二份格式物化，違反單一真實來源）。parse 回
# found=false（無標記／版本不可解析／版本較新）時為 null（空字串）。
MANAGED_HASH=""
compute_managed_hash() {
  local body="$1" parse_out hash_out found
  MANAGED_HASH=""
  parse_out="$(AIDLC_ISSUE_BODY="$body" GITHUB_OUTPUT= bash "$BLOCK_SH" parse)"
  found="$(line_value "$parse_out" found || true)"
  [ "$found" = "true" ] || return 0
  hash_out="$(
    AIDLC_BLOCK_FORMAT_VERSION="$(line_value "$parse_out" block_format_version || true)" \
    AIDLC_BLOCK_STATUS="$(line_value "$parse_out" block_status || true)" \
    AIDLC_BLOCK_TRACEABLE_ROW="$(line_value "$parse_out" block_traceable_row || true)" \
    AIDLC_BLOCK_REASON_CATEGORY="$(line_value "$parse_out" block_reason_category || true)" \
    AIDLC_BLOCK_DECIDED_AT="$(line_value "$parse_out" block_decided_at || true)" \
    AIDLC_BLOCK_SCOPE_NOTE="$(line_value "$parse_out" block_scope_note || true)" \
    AIDLC_BLOCK_REJECTION_CLOSED_AT="$(line_value "$parse_out" block_rejection_closed_at || true)" \
    GITHUB_OUTPUT= bash "$BLOCK_SH" hash
  )"
  MANAGED_HASH="$(line_value "$hash_out" content_hash || true)"
}

op_read_item() {
  require_binding
  require_project_config
  require_field_name
  require_repo

  if ! read_item_core; then
    external_error "read_item" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  assert_single_item

  if [ "$ITEM_COUNT" = "0" ]; then
    # R-1.3 的零筆分支：**只能**由「查詢成功且過濾後為零筆」進入（NOT_FOUND 走的
    # 是上面的 external_error，不會到這裡——ADR-0016 §4.3）。回全 null 的
    # ItemState（code-generation plan 定案：status／field_value／managed_block_hash
    # 皆 null；issue_number 與 issue_state 是 issue 本身的事實，照實回）。
    emit status ""
    emit field_value ""
    emit managed_block_hash ""
    emit issue_number "$AIDLC_BINDING"
    emit issue_state "$ISSUE_STATE"
    return 0
  fi

  compute_managed_hash "$ISSUE_BODY"
  emit status "$ITEM_STATUS"
  emit field_value "$ITEM_FIELD_VALUE"
  emit managed_block_hash "$MANAGED_HASH"
  emit issue_number "$AIDLC_BINDING"
  emit issue_state "$ISSUE_STATE"
}

op_read_issue_state() {
  require_binding
  require_repo
  if ! gql -f query="$ISSUE_STATE_QUERY" \
           -f owner="$REPO_OWNER" -f name="$REPO_NAME" -F number="$AIDLC_BINDING"; then
    external_error "read_issue_state" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  emit issue_state "$(to_lower "$(printf '%s' "$GQL_BODY" | jq -r '.data.repository.issue.state')")"
}

# ==========================================================================
# 欄位解析層（R-4.4／R-4.5：name→id 一律執行期 per-project 解析，不得寫死——
# 實測 #16 與 #23 的同名選項 option id 不同；比對大小寫敏感、精確比對）
# ==========================================================================

PROJECT_ID=""
PROJECT_CAN_UPDATE=""
resolve_project() {
  gql -f query="$PROJECT_QUERY" -f owner="$PROJECT_OWNER" -F number="$PROJECT_NUMBER" || return 1
  PROJECT_ID="$(printf '%s' "$GQL_BODY" | jq -r '.data.user.projectV2.id // ""')"
  PROJECT_CAN_UPDATE="$(printf '%s' "$GQL_BODY" | jq -r '.data.user.projectV2.viewerCanUpdate // false')"
  if [ -z "$PROJECT_ID" ]; then
    GQL_ERRMSG="user(login:\"${PROJECT_OWNER}\").projectV2(number:${PROJECT_NUMBER}) 解析為空"
    GQL_STATUS="200"
    return 1
  fi
  return 0
}

# 列舉 Project 的欄位定義（含單選選項），游標分頁。結果放 FIELDS_JSON（陣列）。
FIELDS_JSON="[]"
list_fields() {
  local cursor="" nodes hasNext
  FIELDS_JSON="[]"
  while :; do
    if [ -n "$cursor" ]; then
      gql -f query="$FIELDS_QUERY" -f owner="$PROJECT_OWNER" -F number="$PROJECT_NUMBER" \
          -f cursor="$cursor" || return 1
    else
      gql -f query="$FIELDS_QUERY" -f owner="$PROJECT_OWNER" -F number="$PROJECT_NUMBER" || return 1
    fi
    nodes="$(printf '%s' "$GQL_BODY" | jq -c '.data.user.projectV2.fields.nodes // []')"
    FIELDS_JSON="$(printf '%s' "$FIELDS_JSON" | jq -c --argjson new "$nodes" '. + $new')"
    hasNext="$(printf '%s' "$GQL_BODY" | jq -r '.data.user.projectV2.fields.pageInfo.hasNextPage // false')"
    if [ "$hasNext" != "true" ]; then
      break
    fi
    cursor="$(printf '%s' "$GQL_BODY" | jq -r '.data.user.projectV2.fields.pageInfo.endCursor // ""')"
    [ -n "$cursor" ] || break
  done
  return 0
}

# 依名稱找欄位（**大小寫敏感、精確比對**——名稱端政策，R-4.5 要求明文記載：平台
# 對 option id 大小寫敏感，本檔對「名稱」端採同樣嚴格的精確比對，不做任何正規化；
# 名稱打錯寧可失敗也不猜）。設 FIELD_ID／FIELD_TYPE／FIELD_OPTIONS。找不到回 1。
FIELD_ID=""
FIELD_TYPE=""
FIELD_OPTIONS="[]"
find_field() {
  local name="$1" row
  row="$(printf '%s' "$FIELDS_JSON" | jq -c --arg n "$name" '[.[] | select(.name == $n)] | .[0] // empty')"
  [ -n "$row" ] || return 1
  FIELD_ID="$(printf '%s' "$row" | jq -r '.id')"
  FIELD_TYPE="$(printf '%s' "$row" | jq -r '.dataType')"
  FIELD_OPTIONS="$(printf '%s' "$row" | jq -c '.options // []')"
  return 0
}

# Status 選項的 name→id 解析（R-4.4）。找不到選項名稱 ⇒ 看板選項集與機制的映射
# 不一致（ADR-A3 的限定條件被破壞的形狀）⇒ ExternalError。
resolve_status_option() {
  local desired="$1"
  if ! find_field "Status"; then
    external_error "write_status" "Project #${PROJECT_NUMBER} 沒有名為 Status 的欄位" "200"
  fi
  if [ "$FIELD_TYPE" != "SINGLE_SELECT" ]; then
    external_error "write_status" "Status 欄位型別為 ${FIELD_TYPE}，非 SINGLE_SELECT" "200"
  fi
  OPTION_ID="$(printf '%s' "$FIELD_OPTIONS" | jq -r --arg n "$desired" '[.[] | select(.name == $n)] | .[0].id // ""')"
  if [ -z "$OPTION_ID" ]; then
    external_error "write_status" \
      "Status 選項 '${desired}' 不存在於 Project #${PROJECT_NUMBER}（比對為大小寫敏感精確比對）" \
      "200"
  fi
}
OPTION_ID=""

op_ensure_field() {
  require_project_config
  require_field_name

  if ! resolve_project; then
    external_error "ensure_field" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  if ! list_fields; then
    external_error "ensure_field" "$GQL_ERRMSG" "$GQL_STATUS"
  fi

  if find_field "$FIELD_NAME"; then
    if [ "$FIELD_TYPE" = "TEXT" ]; then
      emit result ok
      emit field_id "$FIELD_ID"
      emit field_created false
      return 0
    fi
    # 可達失敗前提之二：同名欄位型別不同（ADR-0016 §1）。
    emit result cannot_create
    emit reason "同名欄位型別不同：'${FIELD_NAME}' 現為 ${FIELD_TYPE}，需要 TEXT"
    emit field_id ""
    emit field_created false
    return 0
  fi

  # 缺欄位 → 自動建立（[US:S-5 AC 2] 的「可自動建立」支，PRE-1 第五輪實測可用）。
  if gql -f query="$CREATE_FIELD_MUTATION" -f projectId="$PROJECT_ID" -f name="$FIELD_NAME"; then
    emit result ok
    emit field_id "$(printf '%s' "$GQL_BODY" | jq -r '.data.createProjectV2Field.projectV2Field.id // ""')"
    emit field_created true
    return 0
  fi
  # 可達失敗前提之一：憑證缺 Projects 寫入權——以 GraphQL 錯誤型別判定。其餘錯誤
  # 型別不屬於 CannotCreate 的兩種可達前提，走 ExternalError。
  case " $GQL_ERRTYPES " in
    *" FORBIDDEN "*|*" INSUFFICIENT_SCOPES "*)
      emit result cannot_create
      emit reason "憑證缺 Projects 寫入權：${GQL_ERRMSG}"
      emit field_id ""
      emit field_created false
      return 0
      ;;
  esac
  external_error "ensure_field" "$GQL_ERRMSG" "$GQL_STATUS"
}

# ==========================================================================
# 寫入層
# ==========================================================================

op_write_status() {
  require_binding
  require_project_config
  require_field_name
  require_repo
  local desired="${AIDLC_DESIRED_STATUS:-}" expected="${AIDLC_EXPECTED_STATUS:-}"
  [ -n "$desired" ] || fail "write_status 需要 desired_status（「決定不寫」不會走到本 operation）"

  # 欄位解析**先於**回讀（reviewer iteration 1 Major）：list_fields 只吃 Config、
  # resolve_status_option 只吃 FIELDS_JSON 與 desired，兩者都不依賴回讀結果。放在
  # 回讀之前，R-2.4 的競態視窗（自回讀起、至 mutation 止）內就只剩單一 mutation
  # 往返，與 business-rules.md R-2.4 對 Bolt 1 gate 揭露的量級一致。代價如實記載：
  # 下面兩條 Aborted 分支（item 不在板上／回讀不符）現在會先付一次（分頁時多次）
  # 欄位列舉呼叫才中止；desired 對應的選項不存在時也會在回讀之前就以 ExternalError
  # 紅燈，不再有機會以 Aborted 收場（映射不一致本就該紅燈，不該被 Aborted 遮住）。
  # Status 寫入路徑上的任何 API 失敗都是 ExternalError（紅燈）——Failed 是
  # write_field／write_body 專屬的不連坐通道，**本 operation 不產生 Failed**。
  if ! list_fields; then
    external_error "write_status 的欄位解析" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  resolve_status_option "$desired"

  # R-2.1：必先回讀。R-2.4 的競態視窗從這次回讀開始、到下面的 mutation 送出為止，
  # 中間不得再有任何其他 API 呼叫。**無兜底**（檔頭錯誤模型段）。
  if ! read_item_core; then
    external_error "write_status 的回讀" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  assert_single_item

  if [ "$ITEM_COUNT" = "0" ]; then
    # R-1.3 的零筆分支：item 不在板上（綁定過期，或 item 已被人移出看板）。這條
    # 檢查**先於** status 比對——不論 expected 為何，沒有寫入對象就沒有可比對的
    # 對象；「item 存在」是回讀比對的前置條件，前置條件不成立即為回讀不符，走
    # Aborted（不送出寫入、不開 issue、不紅燈）。**不走 Failed**：上游契約
    # （domain-entities.md／business-logic-model.md）把 Failed 限定為 write_field
    # ／write_body 專屬，U-6 的 R-5.12 也只認得 write_status 的 Aborted 與
    # ExternalError；C-5 的通報讓人看見綁定過期，補建與否由呼叫端決定（首建是
    # create_item 的職責，本 operation 不越權）。
    emit result aborted
    emit actual_status ""
    emit expected_status "$expected"
    emit message "write_status：issue #${AIDLC_BINDING} 不在 Project #${PROJECT_NUMBER} 上（綁定過期或 item 已被移出看板），無寫入對象，未送出寫入"
    return 0
  fi

  # 只比對 Status 欄位（Plan Approval 定案）；空字串＝未設值。
  local actual="$ITEM_STATUS"
  if [ "$actual" != "$expected" ]; then
    # Aborted：不送出寫入、不開 issue（開 issue 是 C-5 的職責）、不紅燈
    # （R-2.1／R-2.2／R-2.3）。message 給 C-5 現成的一行可用。
    emit result aborted
    emit actual_status "$actual"
    emit expected_status "$expected"
    emit message "write_status：回讀不符（actual='${actual}'，expected='${expected}'），未送出寫入"
    return 0
  fi

  if ! gql -f query="$UPDATE_SELECT_MUTATION" \
           -f projectId="$ITEM_PROJECT_ID" -f itemId="$ITEM_ID" \
           -f fieldId="$FIELD_ID" -f optionId="$OPTION_ID"; then
    external_error "write_status 的寫入" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  emit result written
}

# write_field 的失敗出口：R-4.1 的不連坐——**回傳值**、exit 0、不紅燈。
write_field_failed() {
  emit result failed
  emit http_status "${2:-}"
  emit message "$(single_line "write_field：$1")"
  exit 0
}

op_write_field() {
  require_binding
  require_project_config
  require_field_name
  require_repo
  local value="${AIDLC_FIELD_VALUE:-}"

  # 本 operation 內的一切失敗（含內部讀取）都走 Failed，不紅燈——唯一的例外是
  # R-1.4 的多筆斷言（assert_single_item），那是看板損壞而非「欄位寫入失敗」。
  if ! read_item_core; then
    write_field_failed "回讀失敗：${GQL_ERRMSG}" "$GQL_STATUS"
  fi
  assert_single_item
  if [ "$ITEM_COUNT" = "0" ]; then
    write_field_failed "issue #${AIDLC_BINDING} 不在 Project #${PROJECT_NUMBER} 上，無寫入對象"
  fi

  if ! resolve_project; then
    write_field_failed "Project 解析失敗：${GQL_ERRMSG}" "$GQL_STATUS"
  fi
  if ! list_fields; then
    write_field_failed "欄位列舉失敗：${GQL_ERRMSG}" "$GQL_STATUS"
  fi

  if ! find_field "$FIELD_NAME"; then
    # 欄位不存在 → 嘗試建立；建立失敗 → Failed（R-4.1，**不是** CannotCreate——
    # 那是 ensure_field 的回傳型別；本 operation 的契約是 WriteResult）。
    if ! gql -f query="$CREATE_FIELD_MUTATION" -f projectId="$PROJECT_ID" -f name="$FIELD_NAME"; then
      write_field_failed "欄位 '${FIELD_NAME}' 不存在且建立失敗：${GQL_ERRMSG}" "$GQL_STATUS"
    fi
    FIELD_ID="$(printf '%s' "$GQL_BODY" | jq -r '.data.createProjectV2Field.projectV2Field.id // ""')"
    FIELD_TYPE="TEXT"
  fi
  if [ "$FIELD_TYPE" != "TEXT" ]; then
    write_field_failed "欄位 '${FIELD_NAME}' 型別為 ${FIELD_TYPE}，非 TEXT，無法寫入文字值"
  fi

  if ! gql -f query="$UPDATE_TEXT_MUTATION" \
           -f projectId="$ITEM_PROJECT_ID" -f itemId="$ITEM_ID" \
           -f fieldId="$FIELD_ID" -f text="$value"; then
    write_field_failed "寫入失敗：${GQL_ERRMSG}" "$GQL_STATUS"
  fi
  emit result written
}

op_create_item() {
  local existing="${AIDLC_EXISTING_BINDING:-}"

  # R-3.1：record 已有綁定編號 → 不建、原值回傳。**這條路徑零 API 呼叫**——
  # 它是「每 push 一次多一張卡」的唯一攔截（business-rules.md 的失敗模式重述：
  # 它攔得住 workflow 重跑，攔不住回寫失敗——後者的防線是 U-4 的 Rejected 紅燈）。
  if [ -n "$existing" ]; then
    is_positive_integer "$existing" || fail "existing_binding 必須是正整數，得到：'${existing}'"
    emit binding "$existing"
    emit created false
    return 0
  fi

  require_project_config
  require_repo
  local intent_id="${AIDLC_INTENT_ID:-}"
  [ -n "$intent_id" ] || fail "create_item 需要 intent_id（或 existing_binding）"
  local title="${AIDLC_ISSUE_TITLE:-}"
  [ -n "$title" ] || title="$intent_id"

  # R-3.2（首建專屬檢查）：解析 Config 指定的 Project 並驗證可寫，不符即中止。
  # 中止走 ExternalError（紅燈）：Config 錯誤或權限退化必須大聲失敗，不能靜默。
  if ! resolve_project; then
    external_error "create_item 的 Project 解析（R-3.2）" "$GQL_ERRMSG" "$GQL_STATUS"
  fi
  if [ "$PROJECT_CAN_UPDATE" != "true" ]; then
    external_error "create_item（R-3.2）" \
      "Config 指定的 Project #${PROJECT_NUMBER} 不可寫（viewerCanUpdate=false），中止首建" \
      "200"
  fi

  # 開 issue（REST；body 留空——受管區塊由 write_body 寫入，本 operation 不越權）。
  if ! rest -X POST "repos/${REPO_OWNER}/${REPO_NAME}/issues" -f title="$title"; then
    external_error "create_item 的開 issue" "$REST_ERRMSG" "$REST_STATUS"
  fi
  local number node_id
  number="$(printf '%s' "$REST_BODY" | jq -r '.number // ""')"
  node_id="$(printf '%s' "$REST_BODY" | jq -r '.node_id // ""')"
  if [ -z "$number" ] || [ -z "$node_id" ]; then
    external_error "create_item 的開 issue" "回應缺 number 或 node_id，無法繼續" "${REST_STATUS:-}"
  fi

  # 加進看板（addProjectV2ItemById 冪等——ADR-0016 §6 實測，重跑不會產生第二筆）。
  # 失敗時 issue 已建立：訊息帶上編號讓人工可回收，仍紅燈——半完成狀態不能靜默。
  if ! gql -f query="$ADD_ITEM_MUTATION" -f projectId="$PROJECT_ID" -f contentId="$node_id"; then
    external_error "create_item 的加入看板" \
      "issue #${number} 已建立但 addProjectV2ItemById 失敗：${GQL_ERRMSG}" "$GQL_STATUS"
  fi

  # R-3.3：**不回寫綁定編號**——回寫是 U-4 的職責。本 operation 到此為止。
  emit binding "$number"
  emit created true
}

# write_body 的失敗出口：R-6.4 的不連坐——**回傳值**、exit 0、不紅燈。
write_body_failed() {
  emit result failed
  emit http_status "${2:-}"
  emit message "$(single_line "write_body：$1")"
  exit 0
}

op_write_body() {
  require_binding
  require_repo
  local block_text="${AIDLC_BLOCK_TEXT:-}"
  # 空 block_text 是介面誤用（R-6 群沒有「刪除區塊」的語意），fail fast。
  [ -n "$block_text" ] || fail "write_body 需要 block_text（U-2 render 的輸出）"

  load_markers

  # 取回當前 body（本 operation 自行取回再 PATCH——read_item 的回讀是另一條路徑，
  # 不在此重用，避免把 R-1 群的斷言連坐進 body 寫入）。
  if ! rest "repos/${REPO_OWNER}/${REPO_NAME}/issues/${AIDLC_BINDING}"; then
    write_body_failed "取回 issue body 失敗：${REST_ERRMSG}" "$REST_STATUS"
  fi
  # 以哨兵保住 body 的尾端換行：jq 的輸出經 $( ) 會被剝掉全部尾端換行，直接取值
  # 等於靜默改寫 body 結尾——違反 R-6.2 的「其餘內容一字不動」。在 jq 層補一個
  # \x01 哨兵再於 shell 層剝掉，取回的字串與原 body 逐位元一致。
  local old_body
  old_body="$(printf '%s' "$REST_BODY" | jq -r '(.body // "") + "\u0001"')"
  old_body="${old_body%$'\001'}"

  # 標記判定交 U-2 的 has_marker 述詞（與萃取的常數同源，雙保險）。
  local hm_out has_marker
  hm_out="$(AIDLC_ISSUE_BODY="$old_body" GITHUB_OUTPUT= bash "$BLOCK_SH" has_marker)"
  has_marker="$(line_value "$hm_out" has_marker || true)"

  # render 的輸出以一個 LF 結尾（U-2 的格式契約）；拼接以「行」為單位，先剝掉
  # 那一個尾端換行，重組時統一以 LF 接合。
  local block_core="${block_text%$'\n'}"

  local new_body=""
  if [ "$has_marker" != "true" ]; then
    # R-6.3 前半：無標記 → 附加於既有內容之後（既有內容一字不動，中間隔一個空行）。
    if [ -z "$old_body" ]; then
      new_body="$block_core"
    else
      new_body="${old_body}"$'\n\n'"${block_core}"
    fi
  else
    # R-6.3 後半：有標記 → 替換 BEGIN〜END 整段（含兩者）。BEGIN 行是以
    # MARKER_SIGIL 開頭的**整行**（code-generation plan 定案）；比對時容忍行尾
    # CR（GitHub web 端提交的 body 是 CRLF），但 prefix／suffix 保留原始行內容
    # 一字不動——只有受管區塊那一段被換掉。
    local line stripped idx=0 begin_idx=0 end_idx=0
    while IFS= read -r line || [ -n "$line" ]; do
      idx=$((idx + 1))
      stripped="${line%$'\r'}"
      if [ "$begin_idx" -eq 0 ]; then
        case "$stripped" in
          "$MARKER_SIGIL"*) begin_idx="$idx" ;;
        esac
      fi
      if [ "$end_idx" -eq 0 ] && [ "$stripped" = "$MARKER_END" ]; then
        end_idx="$idx"
      fi
    done <<< "$old_body"

    # R-6.6：有 BEGIN 無 END、順序顛倒、或標記存在但不成行（sigil 出現在行中）
    # ⇒ body 已損壞。回 Failed 交 C-5 通報，**不猜、不附加**——附加會產生第二個
    # BEGIN，使下一輪的定位更不確定。
    if [ "$begin_idx" -eq 0 ]; then
      write_body_failed "body 含受管標記但無合法的 BEGIN 行（標記未獨立成行），視為損壞，不猜、不附加（R-6.6）"
    fi
    if [ "$end_idx" -eq 0 ]; then
      write_body_failed "body 有 BEGIN 標記但無 END 標記，視為損壞，不猜、不附加（R-6.6）"
    fi
    if [ "$end_idx" -lt "$begin_idx" ]; then
      write_body_failed "body 的受管標記順序顛倒（END 在 BEGIN 之前），視為損壞，不猜、不附加（R-6.6）"
    fi

    local out="" emitted=0
    idx=0
    while IFS= read -r line || [ -n "$line" ]; do
      idx=$((idx + 1))
      if [ "$idx" -lt "$begin_idx" ] || [ "$idx" -gt "$end_idx" ]; then
        if [ "$emitted" -eq 0 ]; then
          out="$line"
          emitted=1
        else
          out="${out}"$'\n'"${line}"
        fi
      elif [ "$idx" -eq "$begin_idx" ]; then
        if [ "$emitted" -eq 0 ]; then
          out="$block_core"
          emitted=1
        else
          out="${out}"$'\n'"${block_core}"
        fi
      fi
      # begin_idx < idx <= end_idx 的行：舊區塊內容，整段丟棄（被 block_core 取代）。
    done <<< "$old_body"
    new_body="$out"
    # 尾端換行不需另行補償：old_body 的捕捉已用哨兵保住結尾，而 <<< 補給 read
    # 迴圈的那一個換行會讓「以換行結尾的 body」多出一個空字串行，重組時自然還原
    # 成同一個結尾——行為由 stub 測試逐位元鎖定。
  fi

  # R-6.5：不做長度截斷——受管區塊無長度上限，Config.field_max_length 只約束
  # 自訂欄位。PATCH 先把 JSON payload 落到暫存檔再 --input：payload 不經 argv
  # （超長 body 不撐爆 argv），rest() 也不落入 pipeline 的 subshell（否則它設定的
  # REST_ERRMSG 會遺失）。
  local payload_file
  payload_file="$(mktemp)"
  printf '%s' "$new_body" | jq -Rs '{body: .}' > "$payload_file"
  if ! rest -X PATCH "repos/${REPO_OWNER}/${REPO_NAME}/issues/${AIDLC_BINDING}" --input "$payload_file"; then
    rm -f "$payload_file"
    write_body_failed "PATCH issue body 失敗：${REST_ERRMSG}" "$REST_STATUS"
  fi
  rm -f "$payload_file"
  emit result written
}

# ==========================================================================
# 進入點
# ==========================================================================

main() {
  local op="${1:-${AIDLC_OPERATION:-}}"

  command -v gh >/dev/null 2>&1 || fail "找不到 gh（GitHub CLI）"
  command -v jq >/dev/null 2>&1 || fail "找不到 jq"

  case "$op" in
    read_item)        op_read_item ;;
    create_item)      op_create_item ;;
    write_status)     op_write_status ;;
    write_field)      op_write_field ;;
    ensure_field)     op_ensure_field ;;
    read_issue_state) op_read_issue_state ;;
    write_body)       op_write_body ;;

    markers)
      # 診斷子命令（不在 action.yml 介面上）：印出自 U-2 萃取的標記常數。
      # run-stub-tests.py 用它斷言「萃取值與 block.sh render 實際輸出首尾行一致」。
      load_markers
      emit MARKER_SIGIL "$MARKER_SIGIL"
      emit MARKER_END "$MARKER_END"
      ;;

    resolve_status)
      # 診斷子命令：解析一個 Status 選項名稱的 option id（發真實查詢）。
      # run-live-tests.py 的完成判準 (d) 用它斷言六個選項全數命中且非硬編碼。
      require_project_config
      local name="${2:-}"
      [ -n "$name" ] || fail "resolve_status 需要選項名稱參數"
      if ! list_fields; then
        external_error "resolve_status" "$GQL_ERRMSG" "$GQL_STATUS"
      fi
      resolve_status_option "$name"
      emit option_id "$OPTION_ID"
      ;;

    "")
      fail "operation 未指定。有效值：read_item / create_item / write_status / write_field / ensure_field / read_issue_state / write_body"
      ;;

    *)
      # R-5 的介面邊界在這裡強制：不存在「推 commit」「改檔案」之類的 operation，
      # 未知值一律非零 exit，不靜默回空值。
      fail "未知的 operation: ${op}。有效值：read_item / create_item / write_status / write_field / ensure_field / read_issue_state / write_body"
      ;;
  esac
}

main "$@"
