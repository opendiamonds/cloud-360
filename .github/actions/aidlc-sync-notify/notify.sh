#!/usr/bin/env bash
#
# notify.sh — U-5「通報」的全部邏輯。
#
# 本檔承載 [ad:C-5 notifier]：機制失敗時開一則 issue 叫人，**而且不重複叫**。
# 它的記憶不是任何資料庫或狀態檔——**記憶就是 GitHub issue 本身**（[ad:decisions.md]
# ADR-A8 的 [Q5=A]，零新增持久狀態）。與 U-1 的 map.sh、U-2 的 block.sh 不同，本檔
# 做真實網路 I/O；與 U-3 的 board.sh 也不同——它打的是 **Issues REST**（`gh issue`
# 子命令），不是 Projects v2 GraphQL。
#
# ==========================================================================
# 契約（呼叫端依賴，請勿變更）
# ==========================================================================
# 兩個 operation（component-methods.md §C-5，簽章的語意一字未改）：
#
#   notify           (FailureIdentity, detail) -> IssueRef
#                    FailureIdentity = { intent_id, reason_code }。以該鍵搜尋
#                    **開啟中**的通報 issue，依命中筆數走三支（R-2 群）：
#                      0 筆  → 開新 issue，action=created、count=1
#                      1 筆  → 追加 comment ＋ 標題計數 +1，action=commented
#                      >1 筆 → 取**編號最小者**追加 ＋ 計數 +1，其餘同鍵 issue
#                              關閉並註明「與 #<最舊> 重複」，action=deduplicated
#                    issue_number 一律是承載本次通報的那一則（>1 筆時＝最舊者）。
#
#   resolve_if_open  (FailureIdentity)   ——本檔接受**批次鍵**（Plan Approval 裁決 1）
#                    keys 為換行分隔的 `<intent_id>/<reason_code>`，一鍵即一行。
#                    **一次**列舉全部開啟中通報 issue（[Q2=A]），逐則解析內文首行的
#                    機器可讀鍵：鍵 ∈ keys → 關閉並註明「本輪未再發生」；鍵 ∉ keys
#                    → **不動**（R-3.2，涵蓋「仍失敗」與「不屬本輪」兩種）；keys 中
#                    沒有對應 issue 的鍵 → no-op（§C-5 逐字）。
#                    **每個鍵的語意與單獨呼叫完全相同**，批次只是允許一次帶多個——
#                    逐鍵呼叫而每次都列舉正是 [Q2=B] 被否決的 30 次呼叫。
#
# 通報 issue 的可搜尋形狀（domain-entities.md）：
#   label     aidlc-sync-alert（單一 label，讓「一次列舉全部」成為一次查詢）
#   標題      [aidlc-sync] <intent_id> / <reason_code> (×N)
#   內文首行  <!-- aidlc-alert: intent=<intent_id> reason=<reason_code> -->
#
# **比對只用內文首行的機器可讀鍵，逐字相符**（R-2.1）。標題同時承擔「人看的摘要」
# 與「機器搜尋的鍵」兩個角色，而人**會**編輯標題——把鍵複製一份到內文的 HTML 註解
# 裡，讓比對不依賴標題的完整性。標題的 ×N **是給人看的，不是判定依據**：判定依據
# 永遠是實際的 comment 數與 issue 開關狀態（domain-entities.md 逐字）。
#
# ==========================================================================
# 通報與紅燈是兩件事（business-rules.md R-1 群）
# ==========================================================================
# 不得以其中一個推導另一個（R-1.1）。Aborted 與 CannotCreate 是「通報但不紅燈」的
# 存在證明。
#
#   reason_code / 結果                                    通報   紅燈
#   ------------------------------------------------------------------
#   suppressed / parked / unparseable /
#   whitelisted / undecidable（機制的正常判斷）             否     否
#   Aborted（回讀不符，[req:FR-C1] 的主動中止）             是     否
#   CannotCreate（欄位建不出來）                            是     否
#   ExternalError                                           是     是
#   Rejected                                                是     是
#   Failed（write_field／write_body 的不連坐失敗）          是     否
#   對帳成功補平（[US:S-7 AC 5]）                           否     否
#
# 「紅燈」是**呼叫端**的事（workflow 層），本檔不決定它——本檔只負責「通報」那一欄。
# 五種正常判斷碼傳入本檔即 **exit 2**（介面誤用）：依 R-1 它們**根本不該呼叫**
# notify，靜默接受等於把呼叫端的 bug 變成一則假告警，而假告警比沒有告警更難發現。
# reason_code 的允許集合為五個失敗碼（含 Failed，Plan Approval 裁決 2）——U-6 的
# R-5.12 逐字「每一種失敗都交 C-5 notify」且其 R-6.1b 的鍵值域含 Failed。
#
# ==========================================================================
# 錯誤模型（本檔只有一種）
# ==========================================================================
#   ExternalError   **例外式，非零 exit（1）**。任何 gh 呼叫失敗。exit 前先寫出
#                   result=external_error 與 message 兩個 output（供 if failure()
#                   的步驟取用），再非零 exit——workflow 因此紅燈。
#   介面誤用        exit 2，**不寫 result**。呼叫端 bug（未知 operation、缺必要
#                   input、reason_code 不在允許集合、keys 格式不合）。
#
# **R-4：通報本身失敗 → 拋，不遞迴通報。** 本檔在任何失敗路徑上**都不會**再開一則
# 「通報失敗」的 issue——那會在 GitHub API 持續失敗時產生無限迴圈。拋出後由 workflow
# 層紅燈，人從 workflow log 看到。run-stub-tests.py 有一條斷言鎖住這件事（API 失敗
# 後**零**第二次 create）。這是本檔唯一會「拋」的路徑。
#
# ==========================================================================
# 安全邊界
# ==========================================================================
# SEC-1  **本檔會關閉別人看得到的 issue**——notify 的去重分支（R-2 第 4 步）與
#        resolve_if_open 的關閉（R-3 第 3 步）是本單元僅有的兩個**破壞性動作**。
#        關閉條件必須是「內文首行的機器可讀鍵**逐字相符**」，**不得**以標題比對：
#        標題可被任何有 issue 權限的人編輯，以標題比對時，一個把自己的 issue 標題
#        改成通報格式的人（或一次無意的複製貼上）就會讓機制關掉不該關的 issue。
#        後果**不可自動復原**——重開的是新 issue，原本的討論串斷了。
# SEC-1  憑證只經 env GH_TOKEN 傳入（gh CLI 原生讀取），action.yml 不宣告任何憑證型
#        input。本檔不讀、不印、不落地 token。
# SEC-2  **通報內容出現在公開 issue 上**（本 repo 為 public）。呼叫端的 detail 不得
#        含完整 API 回應 body 或任何標頭；本檔另做一層防禦性清洗（scrub_detail：
#        遮罩 GitHub token 形狀字串與 Authorization 行、單行化、截 2000 位元組）。
#        **兩邊都要守**——只守一邊時另一邊仍會洩漏。這層清洗是兜底，**不是**授權
#        呼叫端亂傳；它不做也做不到語意過濾。
# 稽核   通報 issue **就是**面向人的稽核紀錄（ADR-0006 的 audit logging 面向）。
#        本檔保證 [req:FR-E3] 的三要素（intent 識別字、stage 標識、ISO 8601 時間戳）
#        寫進內文，**不保證**呼叫端給的 detail 有用。
#
# 規格正本：
#   ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
#     U-5-notifier/functional-design/business-rules.md        （R-1〜R-4 群）
#     U-5-notifier/functional-design/domain-entities.md       （issue 的可搜尋形狀）
#     U-5-notifier/functional-design/business-logic-model.md  （四支分流／邊界情形）
#     U-5-notifier/nfr-requirements/security-requirements.md  （K-1／SEC-1／SEC-2）
#     U-5-notifier/nfr-requirements/tech-stack-decisions.md   （不用 gh search issues）
#     U-5-notifier/code-generation/code-generation-plan.md    （Step 1〜9 與五項裁決）
#
# 依賴：gh（GitHub CLI，runner 預裝）、jq、sed。**不使用 gh search issues**——
# GitHub 的 issue 搜尋索引對剛建立的 issue 有延遲，而收斂演算法恰好依賴「立刻找得到
# 剛開的 issue」。改用 gh issue list --label ＋ 本地比對後，讀的是即時狀態而非索引。
# 一律以 --json 取結構化輸出再交 jq，**不得**解析人類可讀的表格輸出（欄寬與截斷會
# 隨內容改變）。
# 相容性：以 bash 3.2 可執行為底線（macOS 內建版本），不使用關聯陣列、mapfile、
# ${var^^} 等 bash 4+ 語法。GitHub runner 的 bash 5 亦可執行。
#
# 用法（operation 由 $AIDLC_OPERATION 指定；argv 第一參數可覆寫，測試用）：
#   notify.sh                依 env 執行一個 operation
#   notify.sh codes          診斷：印出兩組 reason_code 的允許／拒絕集合（stub 互鎖用）
#   notify.sh truncate T N   診斷：印出 truncate_bytes "T" N 的**原始位元組**（stub 用）

set -euo pipefail

# 固定 locale：本檔對機器可讀鍵做**逐位元組**的字面比對，也對 detail 做位元組級
# 截斷。不依賴任何 locale 相依的字元類別或排序（與 U-1／U-2／U-3 同一理由）。
export LC_ALL=C

# $GITHUB_OUTPUT 的多行分隔符（本檔的 output 值皆單行——見下方 closed_numbers 的
# 註解——heredoc 形式對單行值同樣合法，沿用 U-2〜U-4 的做法）。
GH_DELIM="__AIDLC_SYNC_NOTIFY_EOF__"

# 列舉開啟中通報 issue 的上限。gh 內部分頁（每頁 100），正常情況下通報 issue 只有
# 個位數、第一頁就結束，所以把上限開大不花額外呼叫。命中上限時**不靜默**：
# 兩種操作的降級方向都是安全的（resolve 少關幾則、notify 多開一則而下輪收斂），
# 但「安全地降級」不等於「可以不說」——見 warn_if_truncated。
LIST_LIMIT=500

# detail 的截斷長度（**位元組**，之後對齊 UTF-8 邊界，故實際可能略少）。
DETAIL_MAX=2000

# gh 錯誤訊息的截斷長度（SEC-2：只留定位資訊，不留 body）。
ERRMSG_MAX=300

LABEL_COLOR="B60205"
LABEL_DESC="AI-DLC 同步機制的失敗通報（由 .github/actions/aidlc-sync-notify 自動維護）"

# 五個失敗碼＝notify 的允許集合（Plan Approval 裁決 2）。
FAILURE_CODES="ExternalError Rejected Aborted CannotCreate Failed"
# 五種正常判斷碼＝**根本不該呼叫 notify** 的集合（R-1）。傳入即 exit 2。
NORMAL_CODES="suppressed parked unparseable whitelisted undecidable"

# ==========================================================================
# 小工具（fail／emit／gh_output 沿用 U-2〜U-4 的形狀）
# ==========================================================================

fail() {
  printf 'notify.sh: %s\n' "$1" >&2
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

# 把可能含換行的文字壓成單行。**本檔的每一個 output 值都是單行**：emit 對 stdout
# 用的是 name=value 的單行形式，多行值會讓 stdout 與 $GITHUB_OUTPUT 兩邊的解讀不
# 一致（呼叫端與測試 harness 都讀 stdout）。closed_numbers 因此是**空白分隔**，
# 不是計畫括號裡寫的換行分隔——見 code-summary 的實作定案。
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

# 以位元組為單位截斷，再把尾端不完整的 UTF-8 序列砍掉（LC_ALL=C 之下 ${s:0:n} 是
# 位元組切割，在中文內容上會切出半個字元；半個字元寫進 issue 會變成亂碼）。
#
# **契約的精確邊界（reviewer iteration 2／3 要求寫清楚）**：本函式保證「**輸出的尾端
# 必為一個合法的 UTF-8 序列**」——輸出必為輸入的位元組前綴，且尾端經完整的合法性
# 表驗證（含 overlong／surrogate／超界，不只數長度）。它**不是**
# 一個清洗器：輸入自己中間就有的畸形位元組會原樣留在保留的前綴裡，且 ${#s} <= max
# 時原樣回傳、一個位元組都不動。先前這裡寫「從不產生無效 UTF-8」，對畸形輸入是
# 過度承諾。真正需要防的是「合法輸入被我們切壞」，那一項由下面的收斂迴圈保證。
# 位元組的判定用 case 的範圍樣式，**不用** printf '%d' "'<byte>"：bash 3.2 的
# printf 把 >0x7F 的位元組當成有號字元（0xAD → -83），bash 5 回 173——同一段程式
# 在兩個版本上分歧，而分歧的那一半會靜默留下半個中文字。case 的範圍樣式在
# LC_ALL=C 之下是位元組比對，兩版行為一致（本站實測）。
#
# 演算法：**先問「尾端那個序列完不完整」，再決定砍不砍**。
#   1. cut = 前 max 個位元組。
#   2. 從尾端往前找第一個非 continuation 的位元組，記其距尾端的位置 k（1-based，
#      最多回看 4 個——UTF-8 序列最長 4 個位元組）。
#   3. 由該位元組判定這個序列**需要**幾個位元組 need：
#      \x01-\x7F → 1、\xC0-\xDF → 2、\xE0-\xEF → 3、\xF0-\xF7 → 4、其餘 → 0（孤立
#      continuation 或非法 lead）。
#   4. k == need ⇒ 序列剛好完整落在切點內，**不砍**；否則砍掉尾端那 k 個位元組。
#
# 第 4 步的「不砍」是這支函式先前的 bug 所在：**完整字元的尾端本來就是 continuation
# byte**，而舊版無條件把尾端的 continuation byte 往前砍（最多 3 次），於是
#   truncate_bytes "😀ABC" 4  → 只剩孤立的 lead byte \xF0 ＋ 省略號＝**無效 UTF-8**
#   truncate_bytes "測試ABC" 6 → 完整的「試」被誤刪，得到「測…」
# 兩者在 bash 3.2 與 bash 5 上一致地錯（不是版本分歧，是演算法錯）。
#
# k > need 在合法 UTF-8 輸入下不可達（ASCII 位元組後面不會跟著 continuation），
# 故第 4 步以 k != need 表達；輸入本身已非法時它會多砍一個位元組，代價是少一個
# 字元，換得輸出必為合法 UTF-8。
# 注意 $'\000' 在 bash 展開成空字串（NUL 無法存在於 bash 字串中），寫成
# [$'\000'-$'\177'] 會退化成 [-\177] 這個只配對 "-" 與 \x7F 的錯誤樣式，所以
# ASCII 範圍從 \001 起算。
truncate_bytes() {
  local s="$1" max="$2" cut seq k ok
  if [ "${#s}" -le "$max" ]; then
    printf '%s' "$s"
    return 0
  fi
  cut="${s:0:$max}"

  # 「尾端不是一個**合法**的 UTF-8 序列就丟掉最後一個位元組，再看一次」，直到尾端
  # 合法或字串為空。每一輪必定丟掉一個位元組，故必然停機。
  #
  # 判定用的是**完整的 UTF-8 合法性表**，不是「lead byte 說要幾個位元組就數幾個」。
  # 只數長度會放行三類永遠非法的序列（reviewer iteration 3 Critical，於生產常數
  # DETAIL_MAX=2000／ERRMSG_MAX=300 上實測重現）：
  #   * overlong：\300\200、\301\277（C0／C1 這兩個 lead 永遠非法）
  #   * surrogate：\355\240\200〜\355\277\277（ED 之後只允許 \200-\237）
  #   * 超出 Unicode 上界：\365-\377（F5 起已停用）、\360 之後未達 \220、
  #     \364 之後超過 \217
  # 條件式子範圍（\340／\355／\360／\364 的第二位元組）因此逐一寫出。
  while [ -n "$cut" ]; do
    ok=0
    k=1
    while [ "$k" -le 4 ] && [ "$k" -le "${#cut}" ]; do
      # ${cut: -$k}＝最後 k 個位元組（冒號後的空白不可省，否則會被讀成 :- 的
      # 預設值展開）。bash 3.2 與 5 在 LC_ALL=C 下同為位元組語意（本站實測）。
      seq="${cut: -$k}"
      case "$seq" in
        [$'\001'-$'\177']) ok=1 ;;                                                       # 1 位元組（NUL 不可能存在於 bash 字串，故自 \001 起）
        [$'\302'-$'\337'][$'\200'-$'\277']) ok=1 ;;                                      # 2 位元組（C2-DF；C0／C1 為 overlong）
        $'\340'[$'\240'-$'\277'][$'\200'-$'\277']) ok=1 ;;                               # E0 後須 A0-BF（否則 overlong）
        [$'\341'-$'\354'][$'\200'-$'\277'][$'\200'-$'\277']) ok=1 ;;                     # E1-EC
        $'\355'[$'\200'-$'\237'][$'\200'-$'\277']) ok=1 ;;                               # ED 後須 80-9F（排除 surrogate）
        [$'\356'-$'\357'][$'\200'-$'\277'][$'\200'-$'\277']) ok=1 ;;                     # EE-EF
        $'\360'[$'\220'-$'\277'][$'\200'-$'\277'][$'\200'-$'\277']) ok=1 ;;             # F0 後須 90-BF（否則 overlong）
        [$'\361'-$'\363'][$'\200'-$'\277'][$'\200'-$'\277'][$'\200'-$'\277']) ok=1 ;;   # F1-F3
        $'\364'[$'\200'-$'\217'][$'\200'-$'\277'][$'\200'-$'\277']) ok=1 ;;             # F4 後須 80-8F（U+10FFFF 上界）
      esac
      [ "$ok" -eq 1 ] && break
      k=$((k + 1))
    done
    [ "$ok" -eq 1 ] && break
    cut="${cut%?}"
  done
  printf '%s…' "$cut"
}

# ==========================================================================
# 輸入驗證（介面誤用一律 exit 2 fail fast——這不是判定結果，是呼叫端 bug）
# ==========================================================================

OPERATION="${AIDLC_OPERATION:-}"
INTENT_ID="${AIDLC_INTENT_ID:-}"
REASON_CODE="${AIDLC_REASON_CODE:-}"
STAGE="${AIDLC_STAGE:-}"
DETAIL_RAW="${AIDLC_DETAIL:-}"
KEYS_RAW="${AIDLC_KEYS:-}"
LABEL="${AIDLC_LABEL:-aidlc-sync-alert}"
ALERT_REPO=""

# intent_id 會逐字成為機器可讀鍵的一部分，而該鍵是**破壞性動作的唯一判準**
# （SEC-1）。因此禁止會讓鍵無法逐字比對或可被構造出歧義的字元：空白（鍵在
# HTML 註解內以空白分隔欄位）、< >（會提前關掉註解）。其餘一律放行——過度限制
# 會把合法的 intent 識別字擋在門外，而那是靜默失去通報的方式。
validate_intent_id() {
  local v="$1"
  [ -n "$v" ] || fail "缺少 intent_id（FailureIdentity 的前半）"
  case "$v" in
    *[[:space:]]*) fail "intent_id 不得含空白字元，得到：'${v}'" ;;
    *"<"*|*">"*)   fail "intent_id 不得含 < 或 > 字元（會破壞內文首行的 HTML 註解鍵），得到：'${v}'" ;;
  esac
  if [ "${#v}" -gt 200 ]; then
    fail "intent_id 過長（上限 200 位元組），得到 ${#v} 位元組"
  fi
}

# reason_code 的三分法：允許（五個失敗碼）／R-1 明文不該呼叫（五個正常判斷碼）／
# 其他（純粹的未知值）。三者的錯誤訊息不同——診斷資訊本身就是產出的一部分。
validate_reason_code() {
  local v="$1" c
  [ -n "$v" ] || fail "缺少 reason_code（FailureIdentity 的後半）。允許值：${FAILURE_CODES}"
  for c in $FAILURE_CODES; do
    if [ "$v" = "$c" ]; then
      return 0
    fi
  done
  for c in $NORMAL_CODES; do
    if [ "$v" = "$c" ]; then
      fail "reason_code '${v}' 屬機制的正常判斷，**不該通報也不該紅燈**（business-rules.md R-1）——呼叫端不應呼叫本方法。允許值：${FAILURE_CODES}"
    fi
  done
  fail "未知的 reason_code '${v}'。允許值：${FAILURE_CODES}"
}

require_repo() {
  local repo="${AIDLC_ALERT_REPO:-}"
  # alert_repo 留空時取 runner 提供的 GITHUB_REPOSITORY（action.yml 的 default 為
  # 空字串，實際的預設值在這裡解析——composite action 的 default 拿不到 runner 的
  # 執行期環境）。
  [ -n "$repo" ] || repo="${GITHUB_REPOSITORY:-}"
  [ -n "$repo" ] || fail "缺少 alert_repo，且環境中沒有 GITHUB_REPOSITORY（runner 提供的 owner/repo）"
  case "$repo" in
    */*/*) fail "alert_repo 格式須為 owner/repo，得到：'${repo}'" ;;
    */*) ;;
    *) fail "alert_repo 格式須為 owner/repo，得到：'${repo}'" ;;
  esac
  ALERT_REPO="$repo"
}

require_label() {
  [ -n "$LABEL" ] || fail "label 不得為空"
  case "$LABEL" in
    *[[:space:]]*) fail "label 不得含空白字元，得到：'${LABEL}'" ;;
  esac
}

# ==========================================================================
# SEC-2 清洗
# ==========================================================================
# 遮罩 GitHub token 的所有已知前綴形狀與 Authorization 標頭行。**前綴集合刻意大於
# 計畫逐字列出的三個**（ghp_／gho_／github_pat_）：ghu_／ghs_／ghr_ 是同一族的
# user-to-server／server-to-server／refresh token，遮罩它們是嚴格的超集，不會讓任何
# 依計畫撰寫的斷言失敗，而漏掉它們的後果是把憑證印在公開 issue 上。
#
# 這**不是**語意過濾（做不到也不該做）：它擋的是「不小心把 stderr 原樣轉貼」這一類，
# 擋不掉「刻意把機敏內容寫進 detail」。SEC-2 的主要防線在呼叫端。
#
# **本函式的本質限制，逐條寫明，不要讀成「已完全防護」**：
#   - sed 是行導向的，正則不跨行。呼叫端因此必須先 single_line（見 scrub_detail），
#     否則被換行切開的 Authorization 標頭只會遮到標頭那一行，續行原樣留下。
#   - 即使已單行化，任何**把 token 切成兩段**的方式仍能逃逸：中間插空白、插零寬
#     字元、或前一層先截斷過。`ghp_ABC DEFGHIJKLMNOP` 的兩段各自都短於 {6,}，
#     兩種順序都不會命中（本站實測）。
#   - {6,} 的下限也表示 token 的**尾段**若被切到別處，遮罩只吃掉前段，後段照樣
#     寫進公開 issue。
#   遮罩式清洗防的是「不小心貼上」，不是「刻意規避」，也不是「被任意切割後仍可還原」。
scrub_secrets() {
  printf '%s' "$1" | sed -E \
    -e 's/[Aa][Uu][Tt][Hh][Oo][Rr][Ii][Zz][Aa][Tt][Ii][Oo][Nn]:.*/Authorization: [REDACTED]/' \
    -e 's/github_pat_[A-Za-z0-9_]{6,}/[REDACTED]/g' \
    -e 's/gh[pousr]_[A-Za-z0-9_]{6,}/[REDACTED]/g'
}

# single_line **在 scrub_secrets 之前**：順序反過來時，含字面換行的 Authorization
# 標頭（`Authorization:\ntoken ghp_XXXXX`）會讓正則在換行處斷開，遮罩只吃到標頭那
# 一行，續行裡的 token 原樣寫進公開 issue——等 single_line 把它接成單行時，遮罩已經
# 跑完了。代價是 `Authorization:` 之後的 `.*` 現在吃到**整段 detail 的結尾**而不只
# 是該行結尾，標頭之後的診斷文字會一併被遮掉；SEC-2 的成本不對稱（少一段診斷 vs
# 公開一個憑證），故接受。
scrub_detail() {
  local s
  s="$(single_line "$1")"
  s="$(scrub_secrets "$s")"
  truncate_bytes "$s" "$DETAIL_MAX"
}

scrub_errmsg() {
  local s
  s="$(single_line "$1")"
  s="$(scrub_secrets "$s")"
  truncate_bytes "$s" "$ERRMSG_MAX"
}

# ==========================================================================
# gh 包裝
# ==========================================================================
# gh issue／label 子命令的失敗以**非零 exit code** 表現（不像 GraphQL 那樣藏在
# HTTP 200 的 body 裡，tech-stack-decisions.md），所以錯誤偵測只需檢查一層。
#
# 成功：回 0，GH_STDOUT 為 stdout。
# 失敗：回 1，GH_ERRMSG 為**清洗並截斷後**的 stderr、GH_STATUS 為抓得到的 HTTP 碼。
#       stderr 之所以仍要過 scrub_errmsg：gh 子命令的 stderr 是簡短的人類訊息而非
#       完整 body，但那是我們對它形狀的**假設**，不是保證——這些訊息會被寫進公開
#       issue，假設出錯的代價不對稱。
GH_STDOUT=""
GH_ERRMSG=""
GH_STATUS=""

gh_call() {
  local stderr_file rc=0 stderr_content=""
  GH_STDOUT=""; GH_ERRMSG=""; GH_STATUS=""
  stderr_file="$(mktemp)"
  if ! GH_STDOUT="$(gh "$@" 2>"$stderr_file")"; then
    rc=1
  fi
  stderr_content="$(cat "$stderr_file" 2>/dev/null || true)"
  rm -f "$stderr_file"
  if [ "$rc" -eq 0 ]; then
    return 0
  fi
  GH_ERRMSG="$(scrub_errmsg "$stderr_content")"
  [ -n "$GH_ERRMSG" ] || GH_ERRMSG="gh 呼叫失敗且無可解析的錯誤訊息"
  local re='HTTP ([0-9]{3})'
  if [[ "$stderr_content" =~ $re ]]; then
    GH_STATUS="${BASH_REMATCH[1]}"
  fi
  return 1
}

# ExternalError 的唯一出口：先寫出 result／message（供 if failure() 的步驟取用），
# 再非零 exit（例外式——[ad:component-methods.md] 的「拋」，workflow 因此紅燈）。
#
# **R-4：這裡不會、也不得再呼叫 notify。** 通報失敗時再開一則「通報失敗」的通報，
# 在 GitHub API 持續失敗時會產生無限迴圈。本函式只寫 output 與 stderr 然後 exit。
external_error() {
  local where="$1" msg="$2" status="${3:-}"
  local text="${where}：${msg}"
  [ -n "$status" ] && text="${text}（HTTP ${status}）"
  emit result external_error
  emit message "$(single_line "$text")"
  printf 'notify.sh: ExternalError（%s）：%s\n' "$where" "$msg" >&2
  exit 1
}

# ==========================================================================
# 鍵與標題的正規形式（domain-entities.md）
# ==========================================================================

# 內文首行的機器可讀鍵。**這是唯一的比對依據**（R-2.1）。
key_marker() {
  printf '<!-- aidlc-alert: intent=%s reason=%s -->' "$1" "$2"
}

# 標題。×N 給人看，不是判定依據。
issue_title() {
  printf '[aidlc-sync] %s / %s (×%s)' "$1" "$2" "$3"
}

# 從既有標題解析 ×N。解析不到回非零（呼叫端改以「既有 comment 數＋1」重算）。
# 以 case 做字面切割而非正規表示式：標題含多位元組字元（×），LC_ALL=C 之下的
# 字元類別比對不可靠，而字面切割是位元組安全的。
parse_count() {
  local title="$1" tail
  case "$title" in
    *"(×"*")")
      tail="${title##*"(×"}"
      tail="${tail%")"}"
      if is_positive_integer "$tail"; then
        printf '%s' "$tail"
        return 0
      fi
      ;;
  esac
  return 1
}

utc_now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

warn_if_truncated() {
  local n="$1" where="$2"
  if [ "$n" -ge "$LIST_LIMIT" ]; then
    printf 'notify.sh: 警告（%s）：開啟中的通報 issue 已達列舉上限 %s，本次比對可能不完整。\n' \
      "$where" "$LIST_LIMIT" >&2
    TRUNCATED_NOTE="；警告：命中列舉上限 ${LIST_LIMIT}，比對可能不完整"
  fi
}
TRUNCATED_NOTE=""

# ==========================================================================
# label 冪等建立（Plan Approval 裁決 3）
# ==========================================================================
# repo 目前沒有 aidlc-sync-alert。若把它列為部署前置條件，第一次真實通報會因
# --label 不存在而失敗——而那正是需要通報的時刻。
#
# 只在**即將開新 issue 時**呼叫（notify 的 0 筆分支）：gh issue list --label 對
# 不存在的 label 回空陣列且 exit 0（本站實測），只有 gh issue create --label 需要它
# 先存在。resolve_if_open 只讀與關閉，不需要，也就不該為它多發一次寫入路徑的呼叫。
LABEL_CREATED=0

ensure_label() {
  local names line
  if ! gh_call label list --repo "$ALERT_REPO" --json name --limit 200; then
    external_error "gh label list ${ALERT_REPO}" "$GH_ERRMSG" "$GH_STATUS"
  fi
  names="$(printf '%s' "$GH_STDOUT" | jq -r '.[].name')"
  while IFS= read -r line; do
    if [ "$line" = "$LABEL" ]; then
      return 0
    fi
  done <<< "$names"

  if ! gh_call label create "$LABEL" --repo "$ALERT_REPO" \
        --color "$LABEL_COLOR" --description "$LABEL_DESC"; then
    # 競態：另一個並行的 run 剛好在 list 與 create 之間建好了。目標狀態已達成，
    # 不是失敗——但也不謊稱是本次建立的。
    case "$GH_ERRMSG" in
      *"already exists"*) return 0 ;;
    esac
    external_error "gh label create ${LABEL}" "$GH_ERRMSG" "$GH_STATUS"
  fi
  LABEL_CREATED=1
  return 0
}

# ==========================================================================
# 列舉與比對（R-2.1：只比內文首行的鍵，逐字相符；**不比標題**）
# ==========================================================================
# GitHub 取回的 issue body 可能是 \r\n 行尾（經 web UI 編輯過的），故比對前先去掉
# 首行尾端的 \r。除此之外**不做任何 trim 或正規化**——任何寬鬆化都會擴大破壞性
# 動作的命中面。
MATCH_JQ='[.[] | select(((.body // "") | split("\n")[0] | sub("\r$";"")) == $m)] | sort_by(.number)'

# 結果放進全域 LIST_JSON 而**不是**印到 stdout。理由不是風格：external_error 會
# emit output 再 exit，而 emit 寫的是 stdout——若本函式以 `x="$(list_open_alerts …)"`
# 的形式被呼叫，那些 output 會被命令替換吞進變數裡，呼叫端 workflow 的
# `if failure()` 步驟就讀不到 result／message。本站首跑 stub 測試時實際踩到。
LIST_JSON=""

list_open_alerts() {
  local fields="$1"
  LIST_JSON=""
  if ! gh_call issue list --repo "$ALERT_REPO" --label "$LABEL" --state open \
        --json "$fields" --limit "$LIST_LIMIT"; then
    external_error "gh issue list ${ALERT_REPO} --label ${LABEL}" "$GH_ERRMSG" "$GH_STATUS"
  fi
  LIST_JSON="$GH_STDOUT"
}

# ==========================================================================
# operation: notify（R-2 群四支分流）
# ==========================================================================

op_notify() {
  require_repo
  require_label
  validate_intent_id "$INTENT_ID"
  validate_reason_code "$REASON_CODE"
  [ -n "$STAGE" ] || fail "缺少 stage（[req:FR-E3] 三要素之一）"

  local detail marker list_json total matched n_matched
  detail="$(scrub_detail "$DETAIL_RAW")"
  [ -n "$detail" ] || detail="（呼叫端未提供細節）"
  marker="$(key_marker "$INTENT_ID" "$REASON_CODE")"

  list_open_alerts number,title,body
  list_json="$LIST_JSON"
  total="$(printf '%s' "$list_json" | jq 'length')"
  warn_if_truncated "$total" "notify"

  matched="$(printf '%s' "$list_json" | jq -r --arg m "$marker" "${MATCH_JQ} | .[].number")"
  n_matched="$(printf '%s' "$list_json" | jq --arg m "$marker" "${MATCH_JQ} | length")"

  if [ "$n_matched" -eq 0 ]; then
    notify_create "$marker" "$detail"
  else
    notify_append "$list_json" "$marker" "$detail" "$matched" "$n_matched"
  fi
}

# 0 筆 → 開新 issue。內文第一行是機器可讀鍵，其後是 [req:FR-E3] 的三要素
# （intent 識別字、stage 標識、ISO 8601 時間戳）與 detail。
notify_create() {
  local marker="$1" detail="$2" body title number url

  ensure_label

  title="$(issue_title "$INTENT_ID" "$REASON_CODE" 1)"
  body="$(printf '%s\n\n%s\n\n- intent：`%s`\n- stage：`%s`\n- reason_code：`%s`\n- 首次發生（UTC）：%s\n\n細節：%s\n\n%s\n' \
    "$marker" \
    "AI-DLC 同步機制回報一則需要人處理的失敗。" \
    "$INTENT_ID" "$STAGE" "$REASON_CODE" "$(utc_now)" "$detail" \
    "<!-- 本 issue 由 .github/actions/aidlc-sync-notify 自動維護。第一行的機器可讀鍵是收斂比對的唯一依據，請勿修改（標題可以改，改了仍能命中）。標題的 ×N 為累計次數。 -->")"

  if ! gh_call issue create --repo "$ALERT_REPO" --title "$title" --body "$body" --label "$LABEL"; then
    # **R-4：此處不遞迴通報。** 只寫 output ＋ 非零 exit。
    external_error "gh issue create ${ALERT_REPO}" "$GH_ERRMSG" "$GH_STATUS"
  fi

  # gh issue create 把新 issue 的 URL 印在 stdout。解析不出編號時**大聲失敗**——
  # 靜默回空的 issue_number 會讓呼叫端以為通報成功卻指不出是哪一則。
  url="$(printf '%s' "$GH_STDOUT" | tr -d '\r' | grep -E '/issues/[0-9]+$' | tail -n 1 || true)"
  number="${url##*/}"
  if ! is_positive_integer "$number"; then
    external_error "解析 gh issue create 的輸出" \
      "取不到新 issue 的編號（stdout 不含 .../issues/<n> 形式的 URL）"
  fi

  emit result ok
  emit issue_number "$number"
  emit action created
  emit count 1
  emit closed_numbers ""
  emit closed 0
  emit message "已為 ${INTENT_ID} / ${REASON_CODE} 開新的通報 issue #${number}（label 本次新建：${LABEL_CREATED}）${TRUNCATED_NOTE}"
}

# ≥1 筆 → 取**編號最小者**（R-2.2：編號單調遞增，不受時區或 API 回傳格式影響）
# 追加 comment ＋ 計數 +1；>1 筆時其餘同鍵 issue 關閉並註明「與 #<最舊> 重複」。
notify_append() {
  local list_json="$1" marker="$2" detail="$3" matched="$4" n_matched="$5"
  local oldest oldest_title new_count comment_body closed_list="" closed_n=0 num action

  oldest="$(printf '%s\n' "$matched" | head -n 1)"
  is_positive_integer "$oldest" || fail "內部錯誤：解析出的 issue 編號不是正整數：'${oldest}'"

  oldest_title="$(printf '%s' "$list_json" | jq -r --argjson n "$oldest" '.[] | select(.number == $n) | .title')"

  if new_count="$(parse_count "$oldest_title")"; then
    new_count=$((new_count + 1))
  else
    # 標題被人改過、×N 沒了 → 以既有 comment 數重算。計數是給人看的，判定依據
    # 永遠是實際的 comment 數與開關狀態（domain-entities.md 逐字）。
    if ! gh_call issue view "$oldest" --repo "$ALERT_REPO" --json comments; then
      external_error "gh issue view #${oldest}" "$GH_ERRMSG" "$GH_STATUS"
    fi
    new_count="$(printf '%s' "$GH_STDOUT" | jq '.comments | length')"
    new_count=$((new_count + 1))
  fi

  comment_body="$(printf '再次發生（UTC）：%s\n\n- stage：`%s`\n- reason_code：`%s`\n- 細節：%s\n' \
    "$(utc_now)" "$STAGE" "$REASON_CODE" "$detail")"

  if ! gh_call issue comment "$oldest" --repo "$ALERT_REPO" --body "$comment_body"; then
    external_error "gh issue comment #${oldest}" "$GH_ERRMSG" "$GH_STATUS"
  fi
  if ! gh_call issue edit "$oldest" --repo "$ALERT_REPO" \
        --title "$(issue_title "$INTENT_ID" "$REASON_CODE" "$new_count")"; then
    external_error "gh issue edit #${oldest} --title" "$GH_ERRMSG" "$GH_STATUS"
  fi

  action="commented"
  if [ "$n_matched" -gt 1 ]; then
    action="deduplicated"
    while IFS= read -r num; do
      [ -n "$num" ] || continue
      [ "$num" = "$oldest" ] && continue
      if ! gh_call issue close "$num" --repo "$ALERT_REPO" --comment \
            "與 #${oldest} 重複：同一個 (intent, reason_code) 只保留編號最小的那一則。本則由 AI-DLC 同步機制自動關閉，後續追蹤請看 #${oldest}。"; then
        external_error "gh issue close #${num}（去重）" "$GH_ERRMSG" "$GH_STATUS"
      fi
      closed_list="${closed_list}${closed_list:+ }${num}"
      closed_n=$((closed_n + 1))
    done <<< "$matched"
  fi

  emit result ok
  emit issue_number "$oldest"
  emit action "$action"
  emit count "$new_count"
  emit closed_numbers "$closed_list"
  emit closed "$closed_n"
  emit message "${INTENT_ID} / ${REASON_CODE} 的通報 issue #${oldest} 已追加一則 comment（×${new_count}）；本次關閉重複 ${closed_n} 則${TRUNCATED_NOTE}"
}

# ==========================================================================
# operation: resolve_if_open（R-3 群，批次鍵）
# ==========================================================================

op_resolve() {
  require_repo
  require_label
  [ -n "$KEYS_RAW" ] || fail "缺少 keys（換行分隔的 <intent_id>/<reason_code>，至少一行）"

  # keys → 目標鍵集合（以 marker 的正規形式存放，逐行、逐字比對）。
  local line intent reason markers="" n_keys=0
  while IFS= read -r line; do
    line="${line%$'\r'}"
    # 去掉前後空白：keys 是 YAML 多行字串常見的縮排來源，容忍縮排不會擴大命中面
    # （鍵本身仍逐字比對）。
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] || continue
    case "$line" in
      */*) ;;
      *) fail "keys 的每一行都必須是 <intent_id>/<reason_code>，得到：'${line}'" ;;
    esac
    # reason_code 不含 /，故以**最後一個** / 切割；intent_id 因此可以含 /。
    reason="${line##*/}"
    intent="${line%/*}"
    validate_intent_id "$intent"
    validate_reason_code "$reason"
    markers="${markers}$(key_marker "$intent" "$reason")"$'\n'
    n_keys=$((n_keys + 1))
  done <<< "$KEYS_RAW"

  [ "$n_keys" -gt 0 ] || fail "keys 解析後沒有任何有效的鍵"

  # **一次**列舉（[Q2=A]）。批次鍵的整個重點就在這裡：n 個鍵仍然只有這一次查詢。
  local list_json total pairs num first closed_list="" closed_n=0
  list_open_alerts number,body
  list_json="$LIST_JSON"
  total="$(printf '%s' "$list_json" | jq 'length')"
  warn_if_truncated "$total" "resolve_if_open"

  # 每則 issue 輸出一行 "<number>\t<內文首行（已去掉尾端 \r）>"。
  pairs="$(printf '%s' "$list_json" \
    | jq -r '.[] | "\(.number)\t\(((.body // "") | split("\n")[0] | sub("\r$";"")))"')"

  while IFS=$'\t' read -r num first; do
    [ -n "$num" ] || continue
    is_positive_integer "$num" || continue
    # 鍵 ∉ keys → **不動**（R-3.2：涵蓋「仍失敗」與「不屬本輪」；本輪沒有資訊
    # 可判定它，關掉它就是關掉一則仍然成立的告警）。
    if ! marker_in_set "$first" "$markers"; then
      continue
    fi
    if ! gh_call issue close "$num" --repo "$ALERT_REPO" --comment \
          "本輪未再發生此失敗，由 AI-DLC 同步機制自動關閉。若再度發生會自動開一則新的通報 issue。"; then
      # 關閉失敗 → 非零 exit（呼叫端 U-6 R-6.1c：只記 log 與紅燈，不回滾已寫入
      # 看板的內容）。**同樣不遞迴通報**。
      external_error "gh issue close #${num}（resolve_if_open）" "$GH_ERRMSG" "$GH_STATUS"
    fi
    closed_list="${closed_list}${closed_list:+ }${num}"
    closed_n=$((closed_n + 1))
  done <<< "$pairs"

  emit result ok
  emit closed "$closed_n"
  emit closed_numbers "$closed_list"
  emit message "以 ${n_keys} 個鍵掃過 ${total} 則開啟中的通報 issue，關閉 ${closed_n} 則${TRUNCATED_NOTE}"
}

# 逐行逐字比對（bash 3.2 沒有關聯陣列；鍵的數量是本輪 intent 數 × 5，量級很小）。
marker_in_set() {
  local needle="$1" haystack="$2" line
  while IFS= read -r line; do
    if [ -n "$line" ] && [ "$line" = "$needle" ]; then
      return 0
    fi
  done <<< "$haystack"
  return 1
}

# ==========================================================================
# 進入點
# ==========================================================================

main() {
  local op="${1:-${OPERATION}}"

  command -v gh >/dev/null 2>&1 || fail "找不到 gh（GitHub CLI）"
  command -v jq >/dev/null 2>&1 || fail "找不到 jq"

  case "$op" in
    notify)          op_notify ;;
    resolve_if_open) op_resolve ;;

    codes)
      # 診斷子命令（不在 action.yml 介面上）：印出兩組 reason_code 集合，供 stub
      # 測試鎖住 R-1 的分界，避免測試自己抄一份而漂移。
      emit failure_codes "$FAILURE_CODES"
      emit normal_codes "$NORMAL_CODES"
      emit list_limit "$LIST_LIMIT"
      emit detail_max "$DETAIL_MAX"
      ;;

    truncate)
      # 診斷子命令（不在 action.yml 介面上）：把 truncate_bytes 這支純函式直接暴露
      # 給測試。**刻意不走 emit**——emit 的 name=value 框架與 $GITHUB_OUTPUT 寫出
      # 對純函式探針沒有意義，而測試要驗的正是輸出的**位元組**是否為合法 UTF-8，
      # 多一層框架就多一層要剝的東西；而且 emit 一個名字就得讓 output 契約測試的
      # 排除集合跟著長大，等於為了測試把正式契約的檢查放寬。
      # 尾端不補換行：測試比對的是原始位元組，多一個 \n 就得在斷言裡剝一次。
      [ "$#" -ge 3 ] || fail "用法：notify.sh truncate <text> <max>"
      is_positive_integer "$3" || [ "$3" = "0" ] || fail "truncate 的 max 須為非負整數，得到：'$3'"
      truncate_bytes "$2" "$3"
      ;;

    "")
      fail "operation 未指定。有效值：notify / resolve_if_open"
      ;;
    *)
      fail "未知的 operation: ${op}。有效值：notify / resolve_if_open"
      ;;
  esac
}

main "$@"
