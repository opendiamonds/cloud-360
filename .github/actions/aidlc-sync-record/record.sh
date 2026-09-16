#!/usr/bin/env bash
#
# record.sh — U-4「record 回寫與同步狀態」的全部邏輯。
#
# 本檔承載 [ad:C-4 binding-store]：整個同步機制中**唯一會寫回 repo** 的元件。
# 與 U-1 的 map.sh、U-2 的 block.sh 不同，本檔不是純函式——它做**檔案系統與 git
# I/O**；與 U-3 的 board.sh 也不同——它不碰任何 GitHub API、不持有任何 token，
# 只用 git 與 jq。驗證方式因此是「④git 與 repo 行為」（unit-of-work.md），不是
# fixture、不是 API。
#
# ==========================================================================
# 契約（呼叫端依賴，請勿變更）
# ==========================================================================
# 五個 operation（component-methods.md §C-4，簽章一字未改）：
#
#   read_binding      (record_path) -> int | null
#                     取 <record>/sync-state.json 的 .binding；檔案或欄位缺席回
#                     null（output 空字串）——此值**觸發首建**（R-1.1）。
#   write_binding     (record_path, issue_number)
#                     ＝ write_sync_state 帶 {binding: N}（N 為正整數）。檔案寫入
#                     失敗 → ExternalError（R-1.2）。
#   read_sync_state   (record_path) -> SyncState
#                     檔案缺席 → 全部預設值（R-2.2）；欄位缺席 → 補預設（R-2.2）；
#                     未知欄位**原樣保留在輸出內**（R-2.3 的讀取半邊）；
#                     schema_version 高於本檔 → **不拒絕**、原樣帶出（R-2.4）；
#                     JSON 不合法或型別損壞 → ExternalError（那是損壞，不是舊格式）。
#   write_sync_state  (record_path, state)
#                     state 是**部分物件（patch）**（Plan Approval 裁決 5）：只給要改
#                     的欄位，其餘由 read-modify-write 保留。jq '. + $patch' 就地
#                     合併，未知欄位保留（R-2.3 的寫入半邊）；pending_reverse 以
#                     整個鍵為單位覆寫（物件層淺合併）；schema_version 取
#                     max(現值, patch 值, SCHEMA_VERSION)——只增不減（R-2.4）；
#                     已知欄位若仍缺席補預設；寫同目錄暫存檔再 mv（原子）。
#   commit_and_push   (branch, paths, message) -> Pushed | Rejected
#                     在暫存 git worktree 內 commit，push 至 origin 的 <branch>。
#                     呼叫端 checkout **一個檔案都不動**（pull_request 事件下它是
#                     merge ref、可能 detached；Plan Approval 裁決 3）。細節見下方
#                     「commit_and_push 的三步與內部重試」。
#
# 四個存取器操作的是**同一份檔案** <record>/sync-state.json（缺口 L-1 定案）；
# read_binding／write_binding 是它 .binding 欄位的投影，不是第二份資料。
#
# sync-state.json 的 schema（domain-entities.md；SCHEMA_VERSION=1）：
#   schema_version      正整數，只增不改
#   binding             整數 | null      綁定的 issue 編號；null＝尚未首建
#   last_status         Status | null    本檔不解讀、不驗證（值域由 U-1 擁有）
#   last_field_value    字串 | null
#   last_reason_code    ReasonCode | null
#   managed_block_hash  sha256 | null    由 U-2 產生，本檔只儲存（不得自算）
#   last_synced_at      ISO 8601 | null
#   pending_reverse     物件 | null      由 U-8 寫、本機制不清除；本檔只保存
# 型別檢查只做 schema_version 與 binding，其餘七欄一律不解讀（「本單元只負責
# 讀寫與保存」）。
#
# ==========================================================================
# 錯誤模型（讀之前先讀這段——三種結局的 exit code 與傳播方式**不同**）
# ==========================================================================
#   Pushed                        exit 0。result=pushed、commit_sha、attempts。
#                                 含內部重試後成功。attempts=0 是合法值：工作樹
#                                 內容與 origin/<branch> 已一致、無需新 commit
#                                 （重跑同一輪的冪等情形，[US:S-1 AC 6] 的精神）
#                                 ——此時 commit_sha 為 origin 上既有的 HEAD。
#   Rejected                      **exit 3**。result=rejected、reason ∈
#                                 { policy | branch_protection |
#                                   non_fast_forward_exhausted }。三者都是
#                                 「需要人介入」的紅燈（[ad:services.md]），交 C-5
#                                 通報。exit 前已寫出 result／reason／attempts／
#                                 message 四個 output，供 if failure() 的通報步驟
#                                 取用。
#   ExternalError                 **exit 1**。result=external_error、message。
#                                 檔案讀寫失敗、JSON 損壞、fetch／worktree／commit
#                                 失敗、push 失敗但 stderr 無法歸類（網路、認證）。
#                                 例外式——[ad:component-methods.md] 對
#                                 write_binding 的「拋」。
#   介面誤用                      **exit 2**（fail）。operation 未知、record_path
#                                 形狀不對或不存在、paths 越出白名單、message 缺
#                                 [aidlc-sync]、issue_number 非正整數、patch 非
#                                 JSON 物件。這是呼叫端 bug，不是判定結果，**不**
#                                 寫 result output。
#
# R-3.1 的三條線（讀這段時請把「平台會擋」這個直覺放下）：
#   * main：branch protection 含 enforce_admins: true → 平台以 GH006 拒絕擁有者
#     token 的直推。本檔仍在介面層先擋，不依賴平台。
#   * **ut：branch protection 的 enforce_admins 為 false，而同步憑證是擁有者
#     token（admin）——平台不會擋直推 ut，會成功。** R-3.1「不得推 ut／main」
#     因此**只有本檔這一道防線**（Plan Approval 裁決 1）。branch ∈ {ut, main} 時在
#     **任何 git 動作之前**回 rejected／policy。這不是 fail（exit 2）：事件路徑上
#     branch=ut 是可達的正常輸入（管理員直推 ut 的 record 變更會觸發 U-6），不該用
#     接線錯誤的通道；用 reason 讓 C-5 說得出是哪一種拒絕。
#   * 其餘分支：feature 分支無任何保護（requirements.md A-8 在現況成立）。
#
# ==========================================================================
# commit_and_push 的三步與內部重試（business-logic-model.md；R-3.5）
# ==========================================================================
#   (1) 前置檢查——全部在任何 git 動作之前：branch 合法且 ∉ {ut, main}；message
#       含 [aidlc-sync]（R-3.3；這是 U-6 R-4.2 整輪 skip 的**唯一**依據，缺了會
#       讓機制自己觸發自己）；paths 逐一等於 <record_path>/sync-state.json
#       （R-3.2，L-1 併檔後白名單只有一個檔）；檔案存在於呼叫端工作樹。
#   (2) 取 origin/<branch> 的最新 SHA（ls-remote ＋ fetch；分支不存在 → 以呼叫端
#       HEAD 為分叉點建立——U-8 的 aidlc-sync/reverse/* 與 U-7 從 ut 分叉的自建
#       分支都走這條）；在暫存目錄 git worktree add；**以三方鍵層合併**把本輪變更
#       套進去（見下）；git add 限白名單；commit（身分見 SEC-4）；push
#       HEAD:refs/heads/<branch>。
#   (3) push 失敗時**解析 stderr**（兩種失敗都是非零 exit，只看 exit code 分不出）：
#         非快轉（non-fast-forward／fetch first／[rejected]）→ 重取、重合併、重推，
#           push 總次數上限 MAX_RETRIES=3，用罄 → rejected／non_fast_forward_exhausted
#         分支保護（GH006／protected branch／Changes must be made through a pull
#           request／hook declined）→ rejected／branch_protection，**立即**不重試
#           （重試一百次也一樣）
#         其餘 → ExternalError
#       非快轉的判定**先於**分支保護：任何 pre-receive hook 拒絕都會讓 git 印出
#       「hook declined」，若先判分支保護，一個回報非快轉的 hook 會被誤判為永久
#       失敗而不重試。
#
# 三方鍵層合併（Plan Approval 裁決 2）——**每一次嘗試都做，不只重試時**：
#   base   ＝ 呼叫端 HEAD:<path>（本輪起點的版本；缺席視為 {}）
#   ours   ＝ 呼叫端工作樹現檔（本輪寫入層的產物）
#   theirs ＝ 剛 fetch 到的 origin/<branch>:<path>（缺席視為 {}）
#   result ＝ theirs ＋ { ours 中值與 base 不同的頂層鍵 }
# 首次嘗試也合併的理由：fetch 到的 origin/<branch> 可能已經領先呼叫端 HEAD
# （並行寫入者在本輪開始前就推了），此時「複製檔案進 worktree」會把對方的欄位
# 靜默抹掉、且**不會**觸發非快轉（因為我們 fetch 過了）——那正是重試機制要避免
# 的資料遺失，只是發生在另一個時間點。theirs == base 時 result == ours（ours
# 不刪鍵；寫入層從不刪鍵）。**已知邊界**：只比對頂層鍵；巢狀物件（pending_reverse）
# 以整鍵為單位；ours 相對 base 刪除的鍵不會傳播（寫入層沒有刪鍵的語意）。
#
# ==========================================================================
# 安全邊界（security-requirements.md）
# ==========================================================================
# SEC-1  paths 白名單是**介面約束，不是權限約束**：憑證擁有整個 repo 的內容寫入
#        權，白名單擋的是本檔的正確實作。action.yml 不宣告任何憑證型 input；本檔
#        不讀、不印、不落地任何 token——push 走 origin，沿用呼叫端 checkout 已持
#        久化的憑證（U-6／U-7／U-8 必須以同步 token 做 actions/checkout）。
# SEC-2  [aidlc-sync] 標記可被任何有推送權的人放進自己的 commit 訊息而讓一輪同步
#        整個 skip。記載它，不修它（防線①是結構性的，正確性不受影響）。
# SEC-3  commit 歷史是稽核紀錄，[aidlc-sync] 是它的索引（git log --grep）。commit
#        訊息**不得**含 Status 以外的 record 內容摘要——訊息由呼叫端給、本檔不加料。
# SEC-4  同步身分**顯式**設定：以 GIT_AUTHOR_*／GIT_COMMITTER_* 只作用於 commit
#        那一個指令，不寫任何 git config（呼叫端的 repo config 與全域設定一律不碰；
#        比計畫「只設在 worktree 的 repo 層級 config」更窄——linked worktree 的
#        repo 層級 config 其實與呼叫端共用）。預設 aidlc-sync／
#        aidlc-sync@users.noreply.github.com，呼叫端可覆寫但不得為空。
# 對外的 message output 只含本檔自己的定位文字與 push stderr 中以 remote:／! 起頭
# 的行（單行化、截斷）——不含本機路徑、不含完整 stderr。此值會被 C-5 寫進公開
# issue（本 repo 為 public）。
#
# 規格正本：
#   ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
#     U-4-binding-store/functional-design/business-rules.md         （R-1〜R-4 群）
#     U-4-binding-store/functional-design/domain-entities.md        （schema／相容規則／回傳）
#     U-4-binding-store/functional-design/business-logic-model.md   （資料流／三步／邊界）
#     U-4-binding-store/nfr-requirements/security-requirements.md   （SEC-1〜SEC-4）
#     U-4-binding-store/nfr-requirements/tech-stack-decisions.md    （git 不用 gh；jq 就地更新）
#     U-4-binding-store/code-generation/code-generation-plan.md     （五項裁決）
#
# 依賴：git、jq（runner 預裝）。不依賴 gh。
# 相容性：以 bash 3.2 可執行為底線（macOS 內建版本），不使用關聯陣列、mapfile、
# ${var^^} 等 bash 4+ 語法。GitHub runner 的 bash 5 亦可執行。
#
# 用法（operation 由 $AIDLC_OPERATION 指定；argv 第一參數可覆寫，測試用）：
#   record.sh                       依 env 執行一個 operation
#   record.sh defaults              診斷：印出 SCHEMA_VERSION 與預設值物件（測試用）

set -euo pipefail

# 固定 locale：本檔做字面比對，不依賴環境的 collation（與 U-1〜U-3 同一理由）。
export LC_ALL=C

# 不得在 CI 卡在憑證互動提示上；缺憑證要快速失敗成 ExternalError。
export GIT_TERMINAL_PROMPT=0

# ==========================================================================
# 常數
# ==========================================================================

SCHEMA_VERSION=1

# push 總次數上限（含首次）。business-rules.md R-3.5 自陳 N=3 沒有上游依據；
# 「若實測發現不足，改的是這個數字，不是規則形狀」。
MAX_RETRIES=3

# R-3.3 的標記。U-6 R-4.2 以 HEAD commit 訊息含它作為整輪 skip 的唯一依據。
SYNC_MARKER="[aidlc-sync]"

# 白名單唯一允許的檔名（L-1 併檔後只有一個）。
STATE_FILE_NAME="sync-state.json"

# R-3.1 的介面層防線：不得直推的分支（空白分隔）。
PROTECTED_BRANCHES="ut main"

# push 的目標 remote。本檔不接受覆寫：呼叫端 checkout 的 origin 就是回寫對象。
REMOTE="origin"

# $GITHUB_OUTPUT 的多行分隔符（本檔的 output 值皆單行；heredoc 形式對單行值同樣
# 合法，故不分兩種寫法——沿用 U-2／U-3）。
GH_DELIM="__AIDLC_SYNC_RECORD_EOF__"

# jq 在下面就要用到（預設值表），先於 main 的檢查確認它存在。
command -v jq >/dev/null 2>&1 || { printf 'record.sh: 找不到 jq\n' >&2; exit 2; }

# 已知欄位的預設值表。**只在這裡列一次**；讀取層以 `$defaults + .` 補缺席欄位，
# 寫入層以同一份補寫完檔案——這樣未知欄位永遠不會被「列舉已知欄位」的寫法丟掉。
DEFAULTS="$(jq -n -c --argjson v "$SCHEMA_VERSION" '{
  schema_version: $v,
  binding: null,
  last_status: null,
  last_field_value: null,
  last_reason_code: null,
  managed_block_hash: null,
  last_synced_at: null,
  pending_reverse: null
}')"

# ==========================================================================
# 小工具（fail／emit／gh_output 沿用 U-2／U-3 的形狀）
# ==========================================================================

fail() {
  printf 'record.sh: %s\n' "$1" >&2
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

# ExternalError 的唯一出口：先寫出 output，再以 exit 1 收場（例外式）。
# $1 = 定位前綴（本檔自己的文字）；$2 = 訊息（已清洗，不含本機路徑以外的東西……
# 本檔的訊息只含檔案的 repo 相對路徑，那本來就是 public 的）。
external_error() {
  local where="$1" msg="$2"
  emit result external_error
  emit message "$(single_line "${where}：${msg}")"
  printf 'record.sh: ExternalError（%s）：%s\n' "$where" "$msg" >&2
  exit 1
}

# Rejected 的唯一出口：四個 output 寫齊再 exit 3。
rejected() {
  local reason="$1" attempts="$2" msg="$3"
  emit result rejected
  emit reason "$reason"
  emit attempts "$attempts"
  emit commit_sha ""
  emit message "$(single_line "$msg")"
  printf 'record.sh: Rejected（%s，attempts=%s）：%s\n' "$reason" "$attempts" "$msg" >&2
  exit 3
}

# ==========================================================================
# 輸入驗證（介面誤用一律 exit 2 fail fast——這不是判定結果，是呼叫端 bug）
# ==========================================================================

RECORD_PATH=""     # 正規化後（無尾端斜線）的 record 目錄，相對 cwd
STATE_FILE=""      # <record>/sync-state.json，相對 cwd

# record_path 必須是 aidlc/spaces/<space>/intents/<slug>/ 的形狀、相對路徑、
# 不含 ..，且目錄存在。
require_record_path() {
  local raw="${AIDLC_RECORD_PATH:-}" p space slug
  [ -n "$raw" ] || fail "缺少 record_path"
  p="${raw%/}"
  case "$p" in
    /*) fail "record_path 必須是相對 repo 根的路徑，得到：'${raw}'" ;;
  esac
  local re='^aidlc/spaces/([A-Za-z0-9._-]+)/intents/([A-Za-z0-9._-]+)$'
  if [[ ! "$p" =~ $re ]]; then
    fail "record_path 必須是 aidlc/spaces/<space>/intents/<slug>/ 的形狀，得到：'${raw}'"
  fi
  space="${BASH_REMATCH[1]}"
  slug="${BASH_REMATCH[2]}"
  case "$space" in .|..) fail "record_path 的 <space> 不得為 '.' 或 '..'" ;; esac
  case "$slug" in .|..) fail "record_path 的 <slug> 不得為 '.' 或 '..'" ;; esac
  [ -d "$p" ] || fail "record_path 目錄不存在：'${p}'（相對 cwd $(pwd)）"
  RECORD_PATH="$p"
  STATE_FILE="${p}/${STATE_FILE_NAME}"
}

# R-3.2 白名單：每一路徑必須逐字等於 <record_path>/sync-state.json。
# 不合即 fail（exit 2）——那是呼叫端接線錯誤，不是 Rejected。
# 輸入以空白／換行分隔（白名單內的路徑不含空白，故可安全切分）；重複項合併。
VALIDATED_PATHS=""   # 換行分隔、去重後的清單
require_paths() {
  local raw="${AIDLC_PATHS:-}" p n=0 seen=""
  VALIDATED_PATHS=""
  # 無引號展開在此是**刻意**的（要按空白／換行切成多個路徑），但 glob 展開不是：
  # 沒有 set -f 時，一個含 `*` 的 paths 會先被 shell 依當前工作目錄展開成一組真實
  # 檔名，於是白名單比對看到的字串不再是呼叫端傳入的那一個。目前不出事只因為白名單
  # 是逐字相等比對（fail-closed），那是巧合而非防護。set -f 讓「只做 word-splitting」
  # 成為事實（reviewer iteration 1 Minor 1）。
  set -f
  for p in $raw; do
    p="${p#./}"
    if [ "$p" != "$STATE_FILE" ]; then
      fail "paths 越出白名單（R-3.2）：'${p}' 不等於 '${STATE_FILE}'"
    fi
    case "$seen" in
      *"|${p}|"*) continue ;;
    esac
    seen="${seen}|${p}|"
    [ -f "$p" ] || fail "paths 指定的檔案不存在於呼叫端工作樹：'${p}'"
    if [ -n "$VALIDATED_PATHS" ]; then
      VALIDATED_PATHS="${VALIDATED_PATHS}"$'\n'"${p}"
    else
      VALIDATED_PATHS="$p"
    fi
    n=$((n + 1))
  done
  set +f
  [ "$n" -gt 0 ] || fail "paths 為空——commit_and_push 至少需要一個檔案"
}

require_issue_number() {
  is_positive_integer "${AIDLC_ISSUE_NUMBER:-}" \
    || fail "issue_number 必須是正整數，得到：'${AIDLC_ISSUE_NUMBER:-}'"
}

BRANCH=""
require_branch() {
  local raw="${AIDLC_BRANCH:-}"
  [ -n "$raw" ] || fail "缺少 branch"
  case "$raw" in
    refs/*|*/) fail "branch 必須是純分支名（不含 refs/ 前綴、不以 / 結尾），得到：'${raw}'" ;;
  esac
  git check-ref-format --branch "$raw" >/dev/null 2>&1 \
    || fail "branch 不是合法的分支名：'${raw}'"
  BRANCH="$raw"
}

require_message() {
  local msg="${AIDLC_MESSAGE:-}"
  [ -n "$msg" ] || fail "缺少 message"
  case "$msg" in
    *"$SYNC_MARKER"*) ;;
    *) fail "message 必須含 ${SYNC_MARKER}（R-3.3：這是 U-6 自我排除的唯一依據），得到：'$(single_line "$msg")'" ;;
  esac
}

GIT_USER_NAME=""
GIT_USER_EMAIL=""
require_identity() {
  # 「未設定」才套預設（${var-default}），「設定為空」是呼叫端明確傳了空值 → fail。
  GIT_USER_NAME="${AIDLC_GIT_USER_NAME-aidlc-sync}"
  GIT_USER_EMAIL="${AIDLC_GIT_USER_EMAIL-aidlc-sync@users.noreply.github.com}"
  [ -n "$GIT_USER_NAME" ] || fail "git_user_name 不得為空（SEC-4：同步身分必須顯式）"
  [ -n "$GIT_USER_EMAIL" ] || fail "git_user_email 不得為空（SEC-4：同步身分必須顯式）"
}

# ==========================================================================
# 讀取層（R-1.1、R-2.2〜R-2.4）
# ==========================================================================

# 讀現檔 → RAW_STATE（JSON 文字）。檔案缺席 → "{}"（不視為錯誤，R-2.2）。
# 存在但不是合法 JSON 物件、或 schema_version／binding 型別損壞 → ExternalError。
RAW_STATE=""
STATE_EXISTS="false"
load_state_file() {
  RAW_STATE="{}"
  STATE_EXISTS="false"
  [ -e "$STATE_FILE" ] || return 0
  STATE_EXISTS="true"
  [ -f "$STATE_FILE" ] || external_error "讀取 ${STATE_FILE}" "不是一般檔案"
  if ! RAW_STATE="$(cat "$STATE_FILE" 2>/dev/null)"; then
    external_error "讀取 ${STATE_FILE}" "檔案無法讀取"
  fi
  if ! printf '%s' "$RAW_STATE" | jq -e 'type == "object"' >/dev/null 2>&1; then
    external_error "讀取 ${STATE_FILE}" "內容不是合法的 JSON 物件（損壞，不是舊格式）"
  fi
  check_typed_fields "$RAW_STATE" || external_error "讀取 ${STATE_FILE}" \
    "schema_version 必須是正整數、binding 必須是整數或 null（型別損壞）"
}

# 只檢查兩個有型別約束的欄位；其餘欄位不解讀。缺席（null）視為合法。
check_typed_fields() {
  printf '%s' "$1" | jq -e '
    ((.schema_version == null)
      or ((.schema_version | type) == "number"
          and .schema_version == (.schema_version | floor)
          and .schema_version >= 1))
    and
    ((.binding == null)
      or ((.binding | type) == "number"
          and .binding == (.binding | floor)))
  ' >/dev/null 2>&1
}

# 正規化：預設值 + 現檔（現檔的鍵覆蓋預設；未知鍵原樣保留在後）。
normalized_state() {
  printf '%s' "$1" | jq -c --argjson d "$DEFAULTS" '$d + .'
}

binding_of() {
  printf '%s' "$1" | jq -r 'if .binding == null then "" else (.binding | tostring) end'
}

op_read_sync_state() {
  require_record_path
  load_state_file
  local state
  state="$(normalized_state "$RAW_STATE")"
  emit state_json "$state"
  emit binding "$(binding_of "$state")"
}

op_read_binding() {
  require_record_path
  load_state_file
  emit binding "$(binding_of "$RAW_STATE")"
}

# ==========================================================================
# 寫入層（R-1.2、R-2.1〜R-2.4）
# ==========================================================================

# read-modify-write：
#   現檔（缺席視為 {}）+ patch（就地合併，未知欄位保留）
#   → schema_version = max(現值, patch 值, SCHEMA_VERSION)（不降版）
#   → 預設值 + 結果（已知欄位若仍缺席補預設，讓檔案自述完整）
#   → 寫同目錄暫存檔再 mv（原子替換）
# **不得**改成 jq -n '{...}' 重建物件——那會把未知欄位丟掉（tech-stack-decisions.md
# 的寫法對照表；R-2.3 反直覺、必須被 fixture 鎖住的那條）。
write_state_with_patch() {
  local patch="$1" merged dir tmp
  if ! printf '%s' "$patch" | jq -e 'type == "object"' >/dev/null 2>&1; then
    fail "state_json 必須是 JSON 物件（部分物件／patch），得到：'$(single_line "$patch")'"
  fi
  check_typed_fields "$patch" \
    || fail "state_json 的 schema_version 必須是正整數、binding 必須是整數或 null"
  load_state_file
  merged="$(printf '%s' "$RAW_STATE" | jq -c \
    --argjson patch "$patch" --argjson d "$DEFAULTS" --argjson sv "$SCHEMA_VERSION" '
      . as $cur
      | ($cur + $patch)
      | .schema_version = ([($cur.schema_version // 0), (.schema_version // 0), $sv] | max)
      | $d + .
    ')" || external_error "寫入 ${STATE_FILE}" "合併 patch 失敗"
  dir="$(dirname "$STATE_FILE")"
  if ! tmp="$(mktemp "${dir}/.${STATE_FILE_NAME}.tmp.XXXXXX" 2>/dev/null)"; then
    external_error "寫入 ${STATE_FILE}" "無法在 ${dir} 建立暫存檔（目錄不可寫？）"
  fi
  if ! printf '%s' "$merged" | jq . > "$tmp" 2>/dev/null; then
    rm -f "$tmp"
    external_error "寫入 ${STATE_FILE}" "暫存檔寫入失敗"
  fi
  if ! mv -f "$tmp" "$STATE_FILE" 2>/dev/null; then
    rm -f "$tmp"
    external_error "寫入 ${STATE_FILE}" "原子替換失敗"
  fi
  emit result written
  emit state_json "$merged"
  emit binding "$(binding_of "$merged")"
}

op_write_sync_state() {
  require_record_path
  [ -n "${AIDLC_STATE_JSON:-}" ] || fail "缺少 state_json（部分物件；空物件請傳 '{}'）"
  write_state_with_patch "$AIDLC_STATE_JSON"
}

op_write_binding() {
  require_record_path
  require_issue_number
  write_state_with_patch "$(jq -n -c --argjson n "$AIDLC_ISSUE_NUMBER" '{binding: $n}')"
}

# ==========================================================================
# commit_and_push（R-3 群；Plan Approval 裁決 1〜4）
# ==========================================================================

WORKTREE=""       # 暫存 worktree 目錄（trap 清理）
TMP_ROOT=""       # 暫存根目錄
REPO_PREFIX=""    # cwd 相對 repo 根的前綴（git rev-parse --show-prefix）
THEIRS_SHA=""     # origin/<branch> 的 SHA；分支不存在時為空
FORK_SHA=""       # 分支不存在時的分叉點（呼叫端 HEAD）
LAST_PUSH_STDERR=""

cleanup_worktree() {
  if [ -n "$WORKTREE" ] && [ -d "$WORKTREE" ]; then
    git worktree remove --force "$WORKTREE" >/dev/null 2>&1 || rm -rf "$WORKTREE"
  fi
  git worktree prune >/dev/null 2>&1 || true
  if [ -n "$TMP_ROOT" ] && [ -d "$TMP_ROOT" ]; then
    rm -rf "$TMP_ROOT"
  fi
}

require_git_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || fail "cwd 不在 git 工作樹內：$(pwd)"
  REPO_PREFIX="$(git rev-parse --show-prefix 2>/dev/null || true)"
  git remote get-url "$REMOTE" >/dev/null 2>&1 \
    || fail "找不到 remote '${REMOTE}'（回寫對象就是呼叫端 checkout 的 origin）"
}

# 取 origin/<branch> 的最新 SHA。分支不存在 → THEIRS_SHA=""（ls-remote --exit-code
# 以 2 表示零命中）；其他失敗（網路、認證）→ ExternalError。
refresh_theirs() {
  local rc=0 err
  err="$(mktemp)"
  THEIRS_SHA=""
  if git ls-remote --exit-code --heads "$REMOTE" "refs/heads/${BRANCH}" >/dev/null 2>"$err"; then
    rc=0
  else
    rc=$?
  fi
  if [ "$rc" -eq 2 ]; then
    rm -f "$err"
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    local detail
    detail="$(scrub_git_stderr "$(cat "$err")")"
    rm -f "$err"
    external_error "ls-remote ${REMOTE} ${BRANCH}" "無法查詢遠端分支（網路或認證）：${detail}"
  fi
  if ! git fetch --quiet "$REMOTE" "refs/heads/${BRANCH}" 2>"$err"; then
    local detail
    detail="$(scrub_git_stderr "$(cat "$err")")"
    rm -f "$err"
    external_error "fetch ${REMOTE} ${BRANCH}" "無法取得遠端分支：${detail}"
  fi
  rm -f "$err"
  THEIRS_SHA="$(git rev-parse --verify --quiet 'FETCH_HEAD^{commit}' 2>/dev/null || true)"
  [ -n "$THEIRS_SHA" ] || external_error "fetch ${REMOTE} ${BRANCH}" "FETCH_HEAD 無法解析為 commit"
}

# 從 git stderr 中只保留 remote:／! 起頭的行（伺服器訊息與 ref 結果），單行化、
# 截斷至 300 字元。不含本機路徑、不含完整 stderr——這段會進 C-5 的公開 issue。
scrub_git_stderr() {
  local text="$1" line out=""
  while IFS= read -r line; do
    # 去前導空白後才比對：git 的 **client-side** 拒絕行長這樣（注意行首一個空格）
    #   ` ! [rejected]        HEAD -> branch (fetch first)`
    # 而伺服器端的是 `remote: ...` 與 ` ! [remote rejected] ...`。先前的樣式
    # （`remote:*|"! "*|!*`）對兩者的 `!` 行都不命中，於是非快轉耗盡時 message
    # 只剩「（stderr 無 remote:／! 行）」——通報給人的訊息裡沒有任何原因。
    # 修 reviewer iteration 1 Minor 2 時實測撞出的既有缺陷。
    while :; do
      case "$line" in
        " "*|"	"*) line="${line#?}" ;;
        *) break ;;
      esac
    done
    case "$line" in
      remote:*|"! "*|!*)
        line="${line#remote: }"
        if [ -n "$out" ]; then out="${out}; ${line}"; else out="$line"; fi
        ;;
    esac
  done <<< "$text"
  [ -n "$out" ] || out="（stderr 無 remote:／! 行）"
  out="$(single_line "$out")"
  if [ "${#out}" -gt 300 ]; then out="${out:0:300}…"; fi
  printf '%s' "$out"
}

# push 失敗成因分類（R-3.5：只看 exit code 分不出，必須解析 stderr）。
# 非快轉先判——任何 pre-receive hook 拒絕都會讓 git 印「hook declined」，若先判
# 分支保護，回報非快轉的 hook 會被誤判為永久失敗。
classify_push_stderr() {
  local lower
  lower="$(to_lower "$1")"
  case "$lower" in
    *non-fast-forward*|*"fetch first"*|*"[rejected]"*)
      printf 'non_fast_forward'; return 0 ;;
  esac
  case "$lower" in
    *gh006*|*"protected branch"*|*"changes must be made through a pull request"*|*"hook declined"*)
      printf 'branch_protection'; return 0 ;;
  esac
  printf 'other'
}

# 讀 <sha>:<repo 相對路徑> 的內容；缺席 → "{}"；其他錯誤 → 回 1。
# 以 -C 指定在哪個工作樹解析（呼叫端或暫存 worktree，兩者共用同一個 object store）。
blob_or_empty_object() {
  local dir="$1" spec="$2" content
  if git -C "$dir" cat-file -e "$spec" 2>/dev/null; then
    content="$(git -C "$dir" show "$spec" 2>/dev/null)" || return 1
    printf '%s' "$content"
  else
    printf '{}'
  fi
}

# 三方鍵層合併（裁決 2）：theirs + { ours 中值與 base 不同的頂層鍵 }。
three_way_merge() {
  local base="$1" ours="$2" theirs="$3"
  jq -n -c --argjson base "$base" --argjson ours "$ours" --argjson theirs "$theirs" '
    $theirs + ([ $ours | to_entries[] | select(.value != $base[.key]) ] | from_entries)
  '
}

# 把本輪變更套進 worktree（每一次嘗試都做）。回 0＝有東西可 commit；回 1＝無變更。
stage_changes_in_worktree() {
  local p rp base ours theirs merged origin_sha v
  origin_sha="${THEIRS_SHA:-$FORK_SHA}"
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    rp="${REPO_PREFIX}${p}"
    base="$(blob_or_empty_object . "HEAD:${rp}")" \
      || external_error "三方合併 ${rp}" "無法讀取呼叫端 HEAD 的版本（base）"
    theirs="$(blob_or_empty_object "$WORKTREE" "${origin_sha}:${rp}")" \
      || external_error "三方合併 ${rp}" "無法讀取 ${REMOTE}/${BRANCH} 的版本（theirs）"
    ours="$(cat "$p")" || external_error "三方合併 ${rp}" "無法讀取工作樹現檔（ours）"
    for v in "$base" "$ours" "$theirs"; do
      printf '%s' "$v" | jq -e 'type == "object"' >/dev/null 2>&1 \
        || external_error "三方合併 ${rp}" "base／ours／theirs 之一不是合法的 JSON 物件，無法做鍵層合併"
    done
    merged="$(three_way_merge "$base" "$ours" "$theirs")" \
      || external_error "三方合併 ${rp}" "jq 合併失敗"
    mkdir -p "$(dirname "${WORKTREE}/${rp}")" \
      || external_error "worktree" "無法建立目錄 $(dirname "$rp")"
    printf '%s' "$merged" | jq . > "${WORKTREE}/${rp}" \
      || external_error "worktree" "無法寫入 ${rp}"
    git -C "$WORKTREE" add -- "$rp" >/dev/null 2>&1 \
      || external_error "git add" "無法 stage ${rp}"
  done <<< "$VALIDATED_PATHS"
  # stdout 一律導掉：git 2.51 對「新增檔案」即使加了 --quiet 仍會印出 diff 標頭，
  # 而本檔的 stdout 是 name=value 的 output 通道，不得混入。
  if git -C "$WORKTREE" diff --cached --quiet --no-ext-diff >/dev/null 2>&1; then
    return 1
  fi
  return 0
}

op_commit_and_push() {
  # ---- (1) 前置檢查：全部在任何 git 網路動作之前 ----
  require_record_path
  require_branch
  local b
  set -f  # 同 require_paths：只要 word-splitting，不要 glob（reviewer iteration 1 Minor 1）
  for b in $PROTECTED_BRANCHES; do
    if [ "$BRANCH" = "$b" ]; then
      rejected policy 0 "branch '${BRANCH}' 是整合主幹／發布線，R-3.1 禁止直推（ut 的平台保護對同步憑證不生效，本檢查是唯一防線）"
    fi
  done
  set +f
  require_message
  require_paths
  require_identity
  require_git_repo

  # ---- (2) 暫存 worktree ----
  FORK_SHA="$(git rev-parse --verify --quiet 'HEAD^{commit}' 2>/dev/null || true)"
  [ -n "$FORK_SHA" ] || external_error "worktree" "呼叫端 HEAD 無法解析（空 repo？）"

  TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/aidlc-sync-record.XXXXXX")" \
    || external_error "worktree" "無法建立暫存目錄"
  trap cleanup_worktree EXIT
  WORKTREE="${TMP_ROOT}/wt"

  local attempts=0 err rc kind commit_sha target
  refresh_theirs
  target="${THEIRS_SHA:-$FORK_SHA}"
  if ! git worktree add --quiet --detach "$WORKTREE" "$target" >/dev/null 2>&1; then
    external_error "worktree" "git worktree add 失敗（${target}）"
  fi

  while :; do
    if ! stage_changes_in_worktree; then
      # 無變更：內容已與 origin/<branch> 一致。分支存在 → 不需要新 commit，回
      # pushed（冪等重跑）；分支不存在 → 仍要 push 才會建立分支。
      if [ -n "$THEIRS_SHA" ]; then
        emit result pushed
        emit reason ""
        emit attempts "$attempts"
        emit commit_sha "$THEIRS_SHA"
        emit message "工作樹內容與 ${REMOTE}/${BRANCH} 已一致，未產生新 commit（attempts=${attempts}）"
        return 0
      fi
    else
      if ! GIT_AUTHOR_NAME="$GIT_USER_NAME" GIT_AUTHOR_EMAIL="$GIT_USER_EMAIL" \
           GIT_COMMITTER_NAME="$GIT_USER_NAME" GIT_COMMITTER_EMAIL="$GIT_USER_EMAIL" \
           git -C "$WORKTREE" -c commit.gpgsign=false commit --quiet -m "$AIDLC_MESSAGE" >/dev/null 2>&1; then
        external_error "git commit" "在暫存 worktree 內 commit 失敗"
      fi
    fi

    attempts=$((attempts + 1))
    err="$(mktemp)"
    rc=0
    git -C "$WORKTREE" push "$REMOTE" "HEAD:refs/heads/${BRANCH}" >/dev/null 2>"$err" || rc=$?
    LAST_PUSH_STDERR="$(cat "$err" 2>/dev/null || true)"
    rm -f "$err"

    if [ "$rc" -eq 0 ]; then
      commit_sha="$(git -C "$WORKTREE" rev-parse HEAD)"
      emit result pushed
      emit reason ""
      emit attempts "$attempts"
      emit commit_sha "$commit_sha"
      emit message "已推送至 ${REMOTE}/${BRANCH}（attempts=${attempts}）"
      return 0
    fi

    # 本檔自己的 stderr 就是 GitHub Actions 的 workflow log，而本 repo 為 public——
    # 它與 message output 一樣公開可讀，故**同樣**先過 scrub_git_stderr，不印原始
    # stderr（reviewer iteration 1 Minor 2）。先前只清洗 output 那一邊，等於把
    # SEC-2「不把收到的東西原樣貼出去」只守了一半，且其安全性依賴兩個未寫下的外部
    # 假設（checkout 用 extraheader 而非 URL 內嵌 token、GitHub 會自動遮罩 secret）。
    printf 'record.sh: push 第 %s 次失敗（exit %s）：%s\n' \
      "$attempts" "$rc" "$(scrub_git_stderr "$LAST_PUSH_STDERR")" >&2
    kind="$(classify_push_stderr "$LAST_PUSH_STDERR")"
    case "$kind" in
      branch_protection)
        rejected branch_protection "$attempts" \
          "push 被分支保護拒絕（不重試）：$(scrub_git_stderr "$LAST_PUSH_STDERR")"
        ;;
      non_fast_forward)
        if [ "$attempts" -ge "$MAX_RETRIES" ]; then
          rejected non_fast_forward_exhausted "$attempts" \
            "非快轉重試 ${MAX_RETRIES} 次後仍失敗：$(scrub_git_stderr "$LAST_PUSH_STDERR")"
        fi
        # 重取最新的 origin/<branch>、worktree 重設、下一輪迴圈重新合併。
        refresh_theirs
        target="${THEIRS_SHA:-$FORK_SHA}"
        git -C "$WORKTREE" reset --quiet --hard "$target" >/dev/null 2>&1 \
          || external_error "worktree" "重設至 ${target} 失敗"
        ;;
      *)
        external_error "git push ${REMOTE} ${BRANCH}" \
          "push 失敗且 stderr 無法歸類為非快轉或分支保護（網路、認證？）：$(scrub_git_stderr "$LAST_PUSH_STDERR")"
        ;;
    esac
  done
}

# ==========================================================================
# 進入點
# ==========================================================================

main() {
  local op="${1:-${AIDLC_OPERATION:-}}"

  command -v git >/dev/null 2>&1 || fail "找不到 git"
  command -v jq >/dev/null 2>&1 || fail "找不到 jq"

  case "$op" in
    read_binding)      op_read_binding ;;
    write_binding)     op_write_binding ;;
    read_sync_state)   op_read_sync_state ;;
    write_sync_state)  op_write_sync_state ;;
    commit_and_push)   op_commit_and_push ;;

    defaults)
      # 診斷子命令（不在 action.yml 介面上）：印出版本與預設值物件，供測試鎖住
      # schema 的八個鍵與 SCHEMA_VERSION。
      emit schema_version "$SCHEMA_VERSION"
      emit defaults_json "$DEFAULTS"
      emit max_retries "$MAX_RETRIES"
      ;;

    "")
      fail "operation 未指定。有效值：read_binding / write_binding / read_sync_state / write_sync_state / commit_and_push"
      ;;

    *)
      fail "未知的 operation: ${op}。有效值：read_binding / write_binding / read_sync_state / write_sync_state / commit_and_push"
      ;;
  esac
}

main "$@"
