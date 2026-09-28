#!/usr/bin/env bash
#
# block.sh — U-2「受管區塊渲染與雜湊」的全部邏輯。
#
# 本檔承載 [ad:C-6 block-renderer]：把一個「決定」變成 issue body 裡的一段**受管區塊
# 文字**，把那段文字讀回成 Block，並對 Block 算 sha256。
#
#   零 I/O：本檔不開任何檔案、不發任何網路請求。輸入一律來自環境變數（或測試用的
#   argv 子命令），輸出一律往 stdout（並在 $GITHUB_OUTPUT 存在時附加一份）。
#
# 與 U-1 的 map.sh 同一形狀，理由相同：fixtures/ 與 run-fixtures.py 要能在**不起
# workflow** 的情況下直接斷言。邏輯若內嵌進 action.yml 就做不到。
#
# 規格正本：
#   ../../../aidlc/spaces/default/intents/260822-gh-projects-sync/construction/
#     U-2-managed-block/functional-design/business-rules.md        （R-1〜R-4 群）
#     U-2-managed-block/functional-design/domain-entities.md       （Block／Context 的值域）
#     U-2-managed-block/functional-design/business-logic-model.md  （演算法與資料流）
#     U-2-managed-block/nfr-requirements/tech-stack-decisions.md   （operation 分派）
#     U-2-managed-block/nfr-requirements/security-requirements.md  （SEC-1〜SEC-5）
#
# 用法（operation 由 $AIDLC_OPERATION 指定；argv 第一參數可覆寫，測試用）：
#   render      吃 Decision ＋ Context，吐區塊文字（stdout 為**原始多行文字**）
#   parse       吃 issue body，吐 name=value（found／has_marker ＋ Block 七欄）
#   hash        吃 Block 七欄，吐 content_hash=<sha256>
#   has_marker  吃 issue body，吐 has_marker=true|false（ADR-0015 §6 修法 (b)）
#
# 額外的診斷子命令（只能由 argv 呼叫，不在 action.yml 的介面上）：
#   serialize        印出 Block 的正規化序列化（雜湊的實際輸入位元組）
#   format_version   印出 FORMAT_VERSION（R-4.2 互鎖用）
#
# 相容性：以 **bash 3.2** 可執行為底線（macOS 內建版本），故不使用關聯陣列、mapfile、
# ${var^^} 等 bash 4+ 語法。GitHub runner 的 bash 5 亦可執行。

set -euo pipefail

# 固定 locale。tech-stack-decisions.md 明列「locale 影響排序」為 bash 序列化的三個風險
# 之一：同一輸入在不同 runner 上得到不同雜湊，是 ADR-A6 點名的最危險失敗模式的一種
# 觸發方式。本檔不做任何排序，但仍固定 LC_ALL——不依賴「目前沒有排序」這個會被未來
# 改動打破的前提。CJK 字面值在 LC_ALL=C 下以位元組處理，而本檔只做字面子字串比對與
# 取代，不做大小寫轉換或字元計數，故不受影響。
export LC_ALL=C

# ==========================================================================
# 錯誤模型（讀之前先讀這段，這裡最容易「順手加驗證」而破壞反向同步）
# ==========================================================================
# business-logic-model.md 的「錯誤處理」定死：**本單元不拋例外、不設 exit code**，
# 唯一的失敗表達是 parse 回 null，因為 [ad:services.md] 規定「機制的正常判斷不使
# workflow 紅燈」。本檔對這條規則的落實方式是——
#
#   會失敗（非零 exit）的只有三種，全部是**介面誤用或環境問題**，不是判定結果：
#     1. operation 缺少或不合法（[Q1=A] 選項本文明訂的承接方式：立即非零 exit，
#        不得靜默回空值）
#     2. render 的輸入值含 CR／LF 或受管標記字首（見 validate_render_value）
#     3. 找不到 sha256 工具
#
#   **hash 完全不做驗證，永遠成功。** 這一點是刻意的，且極容易被後人「修掉」：
#   parse 的輸入是**人可以編輯的** issue body，所以 parse 出來的 Block 完全可能違反
#   domain-entities.md 的互斥不變式（例如有人把 Status 那一行刪掉）。而那正是反向
#   同步要偵測的情形——U-8 的流程是 read_item → parse → content_hash → 比對。若
#   hash 在此非零 exit，一次**正常的人為編輯**就會讓 workflow 紅燈，而不是開出反向
#   PR。互斥不變式對 render 出來的 Block 由 derive_block_from_decision **在構造上**
#   保證（見該函式），不需要、也不應該在 hash 這一端再驗一次。
# ==========================================================================

# ==========================================================================
# 格式常數（本單元擁有的格式契約；受 R-4 群互鎖約束——R-4.1～R-4.5 共五道）
# ==========================================================================
# 改動本節任何一個值都是一次**格式變更**：必須 bump FORMAT_VERSION、更新 golden
# fixture、並在同一個 PR 內於 format-migrations.md 增列重新基準化說明。三者缺一
# run-fixtures.py 就會紅燈（R-4.1／R-4.2／R-4.3）。
#
# **互鎖的天花板（誠實記載，不要試圖修掉）**：它們保證作者**無法「忘記」**重新
# 基準化，**不保證他「做了」**——format-migrations.md 的那一列可以被寫成空殼（加一列、
# 把說明欄填滿、但不真的執行基準化）。這是 [Q1=C] 選項本文即已載明的取捨，不是缺陷。
# 唯一能保證「做了」的形狀是 [Q1=B]（格式指紋 ＋ 錯配時自動重新基準化），但它會把
# ADR-A6 的「單一 PR 一次性遷移」改成「逐 item 惰性遷移」，屬對已核可 ADR 的**實質
# 變更**；兩者的取捨已在 Q1 呈現並由人裁定，實作端不重開。

# FORMAT_VERSION 起始值為 1（Plan Approval 裁決）。
# ADR-0015 §12 把「Block 增設 rejection_notice」定為一次 format_version bump，但本
# intent 是**首次上線，既有受管 item 數為 0**——起始即含該欄位，等價於在零成本時點
# 完成那次 bump。format-migrations.md 的首筆已載明此事。
FORMAT_VERSION=1

# 已知版本集合（空白分隔）。parse 只對集合內的版本套用解析器；高於 FORMAT_VERSION
# 的一律回 null（R-3.4）。日後 bump 時，這裡要同時列出仍在看板上的舊版本，並為每個
# 舊版本保留一支 parse_v<n>——遷移期間新舊區塊必然並存。
KNOWN_VERSIONS="1"

# 受管標記。domain-entities.md「受管標記（marker）」節逐字定義，兩者皆為 HTML 註解，
# 在 issue 的 markdown 呈現中不可見。
#
# MARKER_SIGIL 與 MARKER_BEGIN_PREFIX 是**兩個不同用途**的字串，不要合併：
#   MARKER_SIGIL        用於 has_managed_marker——刻意**不含版本**，因為那個述詞要
#                       回答的是「這裡已經有一段受管區塊了嗎」，即使版本壞掉或版本
#                       比自己新也算有。這正是 ADR-0015 §6 修法 (b) 的全部意義。
#   MARKER_BEGIN_PREFIX 用於 parse 的版本分派，必須含 `v=` 才能取出版本。
MARKER_SIGIL="<!-- aidlc-sync:begin"
MARKER_BEGIN_PREFIX="<!-- aidlc-sync:begin v="
MARKER_END="<!-- aidlc-sync:end -->"

BLOCK_HEADING="### AI-DLC 同步紀錄"

# 欄位標籤。parse 以「行首字首完全相符」取值，故標籤之間不得互為字首。
LABEL_STATUS="- **Status**: "
LABEL_TRACEABLE_ROW="- **對照表列**: "
LABEL_REASON="- **未寫入 Status 的原因**: "
LABEL_DECIDED_AT="- **判定時間**: "
LABEL_SCOPE_NOTE="- **範圍註記**: "
LABEL_REJECTION="- **該次人工改動未被採納**（反向 PR 關閉時刻）: "

# R-1.3／R-1.4 的兩段固定說明，**逐字**。它們是渲染器常數而非 Block 欄位
# （domain-entities.md 明訂），所以不被 parse 取回、也不進 content_hash。
FIXED_NOTE_AUTHORITY="Status 欄位為權威來源；本 issue 依 OOS-2 不自動關閉，其開／關狀態不表示進度。"
FIXED_NOTE_EMPTY_FIELD="自訂欄位為空的 item 不由本機制維護。"

# $GITHUB_OUTPUT 的多行分隔符。block_text 是多行的，不能用 U-1 emit() 的
# `name=value` 單行形式（那會把換行壓成空格，區塊立刻壞掉）。
GH_DELIM="__AIDLC_SYNC_BLOCK_EOF__"

# ==========================================================================
# 小工具
# ==========================================================================

fail() {
  printf 'block.sh: %s\n' "$1" >&2
  exit 2
}

# 寫一筆 output。stdout 一律有一份；$GITHUB_OUTPUT 存在時以 heredoc 形式再寫一份
# （heredoc 形式對單行值同樣合法，故不分兩種寫法）。
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

# ==========================================================================
# Block 的七個欄位（domain-entities.md 的 `Block` 表，順序逐字沿用）
# ==========================================================================
# 用全域變數承載，因為 bash 3.2 沒有結構型別、也不能從函式回傳多值。
BLOCK_FORMAT_VERSION=""
BLOCK_STATUS=""
BLOCK_TRACEABLE_ROW=""
BLOCK_REASON_CATEGORY=""
BLOCK_DECIDED_AT=""
BLOCK_SCOPE_NOTE=""
BLOCK_REJECTION_CLOSED_AT=""

BLOCK_FOUND=0
BLOCK_HAS_MARKER=0

reset_block() {
  BLOCK_FORMAT_VERSION=""
  BLOCK_STATUS=""
  BLOCK_TRACEABLE_ROW=""
  BLOCK_REASON_CATEGORY=""
  BLOCK_DECIDED_AT=""
  BLOCK_SCOPE_NOTE=""
  BLOCK_REJECTION_CLOSED_AT=""
  BLOCK_FOUND=0
}

# --------------------------------------------------------------------------
# 為什麼空字串可以代表 null（與 U-1 的 NULL_SENTINEL 不同的處理，必須說明）
# --------------------------------------------------------------------------
# U-1 的 get_field 必須區分「存在但空」與「缺席」，因為兩者在 record 裡都真的會出現
# 且語意不同，所以它用了 \x01 哨兵。**本單元不需要哨兵**，理由是可逐欄查證的：
#
#   status              非 null 時值域為 Ready/In progress/In review/Done，皆非空
#   traceable_row       非 null 時為「命中的對照表列」，U-1 明訂**一律非空**
#   reason_category     非 null 時為 ReasonCode，六個字面值皆非空
#   decided_at          非 null 時為 ISO 8601 字串，非空
#   scope_note          恆非 null，且 U-1 的 R-6.5 保證非空（空類寫 none）
#   rejection_notice    非 null 時為 { closed_at: ISO 8601 }，非空
#   format_version      恆非 null，正整數
#
# 也就是說**沒有任何一欄的非 null 值域包含空字串**，空字串因此可以無歧義地表達
# null。這不是省事，是這個型別的性質；若日後有欄位的值域允許空字串，這個等價就會
# 失效，屆時必須改用哨兵（並且那是一次格式變更）。

# ==========================================================================
# render — R-1 群
# ==========================================================================

# 只在 render 路徑上做的輸入驗證。
#
# 這裡失敗是刻意的，且與上面「hash 不驗證」不矛盾：render 的輸入來自機制自己
# （U-1 的 Decision ＋ U-6 組出的 Context），**不可能來自人為編輯**，所以違反前提就是
# 呼叫端的 bug，屬介面誤用而非判定結果。
#
# 兩條規則各自防的東西不同：
#   CR／LF     值裡的換行會多出一整行，可以注入假的欄位行甚至假的結束標記；而且它會
#              直接破壞 scope_note 的逐字 round-trip（ADR-0015 §10 的雜湊等價不變式
#              依賴那個 round-trip）。
#   標記字首   縱深防禦。目前所有值都被寫在 `- **X**: ` 之後，不可能出現在行首，故
#              parse 不會誤判；但格式一旦改動（例如某個值改成獨立成行），這條就從
#              「多餘」變成「唯一的防線」。不要因為現在用不到就拿掉。
validate_render_value() {
  local name="$1" value="$2"
  case "$value" in
    *$'\n'*) fail "render 的輸入 ${name} 含換行字元；受管區塊的每個值必須是單行" ;;
    *$'\r'*) fail "render 的輸入 ${name} 含 CR 字元；受管區塊的每個值必須是單行" ;;
  esac
  case "$value" in
    *"$MARKER_SIGIL"*) fail "render 的輸入 ${name} 含受管標記字首 ${MARKER_SIGIL}" ;;
  esac
  case "$value" in
    *"$MARKER_END"*) fail "render 的輸入 ${name} 含受管標記結尾 ${MARKER_END}" ;;
  esac
}

# 由 Decision ＋ Context 推導出 Block。
#
# domain-entities.md 明文：「Block 的互斥性是**渲染時**由 Decision 推導出來的，
# **它不繼承** reason_code 的非空保證」。這個函式就是那句話的實作，也是本檔唯一
# 需要理解 Decision 與 Block 差別的地方：
#
#   Decision.reason_code  **一律非空**（[US:S-2 AC 15] 的總函式性），status 非 null
#                         時它是 "mapped"
#   Block.reason_category **只在 status 為 null 時非空**
#
# 因此推導規則是：status 非空 → reason_category 與 decided_at 皆為 null；
#                 status 為空 → traceable_row 為 null。
#
# 這個推導使「status 與 reason_category 恰有一個非 null」「decided_at 與
# reason_category 同進退」兩條不變式在**構造上**成立，不需要另外驗證。
derive_block_from_decision() {
  local status="$1" traceable_row="$2" reason_code="$3"
  local scope_note="$4" decided_at="$5" rejection_closed_at="$6"

  BLOCK_FORMAT_VERSION="$FORMAT_VERSION"
  BLOCK_SCOPE_NOTE="$scope_note"
  BLOCK_REJECTION_CLOSED_AT="$rejection_closed_at"

  if [ -n "$status" ]; then
    BLOCK_STATUS="$status"
    BLOCK_TRACEABLE_ROW="$traceable_row"
    BLOCK_REASON_CATEGORY=""
    # [US-OQ-3] 的必載內容原文是「目前 Status 與其 traceable_row；**或**機制決定不寫
    # 的原因類別與 ISO 8601 時間戳」——時間戳只掛在後半支。domain-entities.md 於
    # iteration 4 據此把 Block.decided_at 的值域改為 `ISO 8601 | null`。
    # **不要因為「有時間戳比較好看」就把它加回這一支**：那會擴張一個已核可的必載
    # 清單，而且是一次格式變更。
    BLOCK_DECIDED_AT=""
  else
    BLOCK_STATUS=""
    BLOCK_TRACEABLE_ROW=""
    BLOCK_REASON_CATEGORY="$reason_code"
    BLOCK_DECIDED_AT="$decided_at"
  fi
  BLOCK_FOUND=1
}

# 組出區塊文字。輸出**以一個 LF 結尾**（golden fixture 是逐位元比對，這個尾端換行
# 是格式的一部分，不是排版習慣）。
render_block() {
  local out=""

  # 1. 版本標記（domain-entities.md「為什麼 format_version 要進區塊」）
  out="${MARKER_BEGIN_PREFIX}${BLOCK_FORMAT_VERSION} -->"$'\n'
  out="${out}${BLOCK_HEADING}"$'\n'
  out="${out}"$'\n'

  # 2. 二分支（business-logic-model.md 的組成序列第 2 步）。
  #    這個二分是窮盡的：Decision 的 status 與 reason_code 恰有一個表達「有寫」。
  if [ -n "$BLOCK_STATUS" ]; then
    out="${out}${LABEL_STATUS}${BLOCK_STATUS}"$'\n'
    out="${out}${LABEL_TRACEABLE_ROW}${BLOCK_TRACEABLE_ROW}"$'\n'
  else
    out="${out}${LABEL_REASON}${BLOCK_REASON_CATEGORY}"$'\n'
    out="${out}${LABEL_DECIDED_AT}${BLOCK_DECIDED_AT}"$'\n'
  fi

  # 3. scope_note（R-1.2；[S] 與 — SKIP 的差別在此可見，[req:FR-F3]）
  out="${out}${LABEL_SCOPE_NOTE}${BLOCK_SCOPE_NOTE}"$'\n'

  # 4. R-1.5：rejection_notice 為 null 時**完全不渲染這一段**。
  #    兩個只差這一欄的 Context 必須產生可區分的區塊文字，且 parse 回來分別為該值
  #    與 null——這是 R-1.5「可判定方式」欄的逐字要求。
  if [ -n "$BLOCK_REJECTION_CLOSED_AT" ]; then
    out="${out}${LABEL_REJECTION}${BLOCK_REJECTION_CLOSED_AT}"$'\n'
  fi

  # 5. 兩段固定說明（R-1.3／R-1.4，逐字）
  out="${out}"$'\n'
  out="${out}> ${FIXED_NOTE_AUTHORITY}"$'\n'
  out="${out}> ${FIXED_NOTE_EMPTY_FIELD}"$'\n'
  out="${out}${MARKER_END}"$'\n'

  printf '%s' "$out"
}

# ==========================================================================
# has_managed_marker — ADR-0015 §6 修法 (b)
# ==========================================================================
# 廉價述詞：issue body 裡有沒有一段受管區塊的起始標記。**不看版本、不解析**。
#
# 它存在的唯一理由是關掉 R-3.4 的 Critical：parse 的簽章 (issue_body) -> Block | null
# 讓 R-3.1（完全沒有標記）與 R-3.4（標記版本高於當前渲染器）回**同一個 null**，於是
# 呼叫端最自然的實作「parse 回 null ⇒ 渲染一個寫進去」恰恰是 R-3.4 要防的覆寫。
#
# 有了這個述詞，呼叫端可以分辨：
#   parse=null 且 has_marker=false → 全新的 issue，該渲染
#   parse=null 且 has_marker=true  → 有別人的區塊（版本較新或格式壞掉），**不得覆寫**
#
# **本單元只提供能力，不能替呼叫端執行它。** R-3.4 的保護要真正生效，取決於 U-6 在
# 寫入前確實呼叫本述詞並在 true 時跳過。若 U-6 沒有接上，保護仍然不存在——這句話
# 不是免責聲明，是給讀 U-6 程式碼的人的檢查項。
has_managed_marker() {
  case "$1" in
    *"$MARKER_SIGIL"*) return 0 ;;
  esac
  return 1
}

# ==========================================================================
# parse — R-3 群
# ==========================================================================

is_positive_integer() {
  case "$1" in
    ""|*[!0-9]*) return 1 ;;
    0*) return 1 ;;   # 0 不是正整數；前導零也不是規範寫法（會讓同一版本有兩種字面）
  esac
  return 0
}

version_is_known() {
  local want="$1" v
  for v in $KNOWN_VERSIONS; do
    [ "$v" = "$want" ] && return 0
  done
  return 1
}

# 在區塊內文中以「行首字首完全相符」取一個標籤的值。
#
# **不 trim**。scope_note 必須能原樣取回（ADR-0015 §10 的雜湊等價不變式依賴它），
# 而 trim 會吃掉值本身合法的前後空白。唯一被剝掉的是行尾的 CR，那是為了容忍 CRLF
# 傳輸；render 已禁止值含 CR，所以剝它不會損及任何合法值。
extract_label() {
  local text="$1" label="$2" line
  while IFS= read -r line; do
    line="${line%$'\r'}"
    case "$line" in
      "$label"*)
        printf '%s' "${line#"$label"}"
        return 0
        ;;
    esac
  done <<< "$text"
  return 1
}

# 版本 1 的解析器。日後 bump 時新增 parse_v2 並保留本函式——遷移期間看板上新舊
# 區塊必然並存，舊解析器不能刪。
parse_v1() {
  local inner="$1"
  BLOCK_STATUS="$(extract_label "$inner" "$LABEL_STATUS" || true)"
  BLOCK_TRACEABLE_ROW="$(extract_label "$inner" "$LABEL_TRACEABLE_ROW" || true)"
  BLOCK_REASON_CATEGORY="$(extract_label "$inner" "$LABEL_REASON" || true)"
  BLOCK_DECIDED_AT="$(extract_label "$inner" "$LABEL_DECIDED_AT" || true)"
  BLOCK_SCOPE_NOTE="$(extract_label "$inner" "$LABEL_SCOPE_NOTE" || true)"
  BLOCK_REJECTION_CLOSED_AT="$(extract_label "$inner" "$LABEL_REJECTION" || true)"
  BLOCK_FOUND=1
}

# parse 的版本分派（business-logic-model.md「parse 的版本分派」）。
#
#   缺失／不可解析 ──────────► null（R-3.1／R-3.2）
#   高於當前 FORMAT_VERSION ─► null（R-3.4，保守：不用舊規則猜新格式）
#   在已知版本集合內 ───────► 套用該版本的解析器 ► Block（R-3.3）
#
# 三種 null 都是**正常判定結果**，一律 exit 0。
parse_block() {
  local body="$1"
  local in_block=0 closed=0 ver="" inner="" line

  reset_block
  BLOCK_HAS_MARKER=0
  if has_managed_marker "$body"; then
    BLOCK_HAS_MARKER=1
  fi

  while IFS= read -r line; do
    line="${line%$'\r'}"
    if [ "$in_block" -eq 0 ]; then
      # 取**第一個**起始標記。人若把整段複製貼上多次，以第一段為準。
      case "$line" in
        "$MARKER_BEGIN_PREFIX"*" -->")
          ver="${line#"$MARKER_BEGIN_PREFIX"}"
          ver="${ver% -->}"
          in_block=1
          ;;
      esac
    elif [ "$line" = "$MARKER_END" ]; then
      closed=1
      break
    else
      inner="${inner}${line}"$'\n'
    fi
  done <<< "$body"

  # 有起始標記但沒有結束標記＝區塊被截斷，屬 R-3.2 的「不可解析」。
  [ "$closed" -eq 1 ] || return 0
  is_positive_integer "$ver" || return 0
  # 高於當前渲染器 → R-3.4。用字串比較不行（"10" < "9"），用 -gt 做數值比較。
  [ "$ver" -gt "$FORMAT_VERSION" ] && return 0
  version_is_known "$ver" || return 0

  BLOCK_FORMAT_VERSION="$ver"
  case "$ver" in
    1) parse_v1 "$inner" ;;
    *) return 0 ;;   # KNOWN_VERSIONS 有列但沒有解析器＝設定錯誤，保守回 null
  esac
}

# ==========================================================================
# content_hash — R-2 群
# ==========================================================================
#
# 簽章是 (Block) -> sha256——**吃的是 parse 後的結構，不是渲染出來的字串**
# （[ad:component-methods.md] 逐字）。因此需要一份**正規化序列化**：固定欄位順序、
# 固定分隔符、固定跳脫規則。
#
# 三項具體決定與其理由：
#
#   欄位順序   逐字沿用 domain-entities.md 的 `Block` 表由上而下的順序：
#              format_version, status, traceable_row, reason_category, decided_at,
#              scope_note, rejection_closed_at。
#              **不是**字母序、也不是渲染順序——沿用型別定義的順序，任何人要核對
#              「雜湊涵蓋範圍有沒有漏欄位」時，可以把這裡的七行與那張表逐列並排。
#
#   分隔符     每欄一行 `<欄名>=<跳脫後的值>`，以 LF 結尾。欄名寫進序列化（而不是只
#              靠位置）是為了讓序列化本身可讀——出問題時 `block.sh serialize` 的輸出
#              直接看得懂是哪一欄不同，不必去數第幾行。
#
#   跳脫規則   反斜線 → \\，LF → \n，CR → \r，**依此順序**。反斜線必須先跳脫，否則
#              後兩條產生的反斜線會被再跳脫一次。
#
# **為什麼這樣就不會有歧義**：跳脫後的值不可能含 LF，所以每欄恰好佔一行；行數固定
# 為七、欄名固定、順序固定，因此 Block → 序列化字串是單射的（兩個不同的 Block 不可能
# 得到同一個序列化）。這正是 R-2.2「任一欄位不同必得不同雜湊」的依據。
#
# tech-stack-decisions.md 列的三個 bash 特有風險在此的處置：
#   欄位值含分隔符  → 跳脫規則使 LF 不可能出現在值裡；`=` 不需跳脫，因為序列化只被
#                     產生、不被反向解析（雜湊不需要可逆）
#   尾端換行        → 序列化以 printf 直接寫進 pipe，不經過 $( )（$( ) 會吃掉尾端換行）
#   locale 影響排序 → 檔頭 export LC_ALL=C；且本檔不做任何排序

escape_value() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  printf '%s' "$s"
}

serialize_field() {
  printf '%s=%s\n' "$1" "$(escape_value "$2")"
}

serialize_block() {
  serialize_field format_version      "$BLOCK_FORMAT_VERSION"
  serialize_field status              "$BLOCK_STATUS"
  serialize_field traceable_row       "$BLOCK_TRACEABLE_ROW"
  serialize_field reason_category     "$BLOCK_REASON_CATEGORY"
  # ---- R-2.3：decided_at 在涵蓋範圍內（[Q2=A]）。以下這段依賴必須被讀到 ----
  #
  # 兩次語意相同的判定會有不同的 decided_at ⇒ 不同雜湊。**churn 不會發生，只因為**
  # [ad:services.md] 的 S-A 明文「有漂移才寫」——語意沒變就不會走到重寫這條路。
  #
  # **這條依賴不在任何依賴圖上，也沒有任何測試會在它被破壞時失敗。** 若未來有人讓
  # 區塊在無漂移時也重寫（例如加一個「定期刷新」或「每輪都蓋一次以自癒」），看板上
  # 每個 item 每輪都會變一次，而且**反向同步會把它讀成人為變更**——那正是 ADR-A6
  # 點名的最危險失敗模式。[Q2=A] 的選項本文已載明此代價。
  #
  # 附帶收益（iteration 4 把 decided_at 移出 mapped 支之後才成立）：最常走的 mapped
  # 分支上 decided_at 為 null，該支的 Block 不含隨輪變動的時間戳，語意相同的兩輪
  # **必得相同雜湊**。churn 隱憂只作用在「決定不寫」那一支。
  serialize_field decided_at          "$BLOCK_DECIDED_AT"
  serialize_field scope_note          "$BLOCK_SCOPE_NOTE"
  serialize_field rejection_closed_at "$BLOCK_REJECTION_CLOSED_AT"
}

sha256_of_stdin() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  else
    fail "找不到 sha256sum 或 shasum，無法計算 content_hash"
  fi
}

content_hash() {
  serialize_block | sha256_of_stdin
}

# ==========================================================================
# 進入點
# ==========================================================================
#
# operation 由 $AIDLC_OPERATION 指定（action.yml 的介面），argv 第一參數可覆寫
# （run-fixtures.py 用它直接呼叫，不必先起 workflow）。
main() {
  local op="${1:-${AIDLC_OPERATION:-}}"
  local rendered=""

  case "$op" in
    render)
      validate_render_value status              "${AIDLC_STATUS:-}"
      validate_render_value traceable_row       "${AIDLC_TRACEABLE_ROW:-}"
      validate_render_value reason_code         "${AIDLC_REASON_CODE:-}"
      validate_render_value scope_note          "${AIDLC_SCOPE_NOTE:-}"
      validate_render_value decided_at          "${AIDLC_DECIDED_AT:-}"
      validate_render_value rejection_closed_at "${AIDLC_REJECTION_CLOSED_AT:-}"
      # reviewer(code-generation) Major，2026-08-30T12:28:35Z：先前 status 與 reason_code **同時為空**
      # 時 exit 0，渲染出一個兩個必載欄位都空白的區塊（違反 R-1.1）並寫進真實 issue。
      #
      # 這不是人為編輯，是**呼叫端接線 bug**（U-6 沒把 Decision 的欄位接上）——與
      # validate_render_value 攔的是同一類問題，理應套用同一條哲學：呼叫端 bug 快速失敗。
      # 對照 hash：那裡刻意不驗，因為它的輸入來自人可編輯的 issue body（見檔頭錯誤模型）。
      # 兩者的差別是**輸入來源**，不是不變式本身。
      if [ -z "${AIDLC_STATUS:-}" ] && [ -z "${AIDLC_REASON_CODE:-}" ]; then
        printf 'aidlc-sync-block: render 需要 status 或 reason_code 其中之一，兩者皆空代表呼叫端未接上 Decision\n' >&2
        exit 2
      fi
      derive_block_from_decision \
        "${AIDLC_STATUS:-}" "${AIDLC_TRACEABLE_ROW:-}" "${AIDLC_REASON_CODE:-}" \
        "${AIDLC_SCOPE_NOTE:-}" "${AIDLC_DECIDED_AT:-}" "${AIDLC_REJECTION_CLOSED_AT:-}"
      # render 的 stdout 是**原始多行文字**，不是 name=value——這是四個 operation 中
      # 唯一的例外，因為值本身是多行的。$GITHUB_OUTPUT 那一份用 heredoc 形式。
      #
      # $( ) 會吃掉尾端換行，而那個換行是格式的一部分（golden fixture 逐位元比對），
      # 所以補回來。stdout 那一份直接 printf，不經過 $( )。
      rendered="$(render_block)"
      printf '%s\n' "$rendered"
      gh_output block_text "${rendered}"$'\n'
      ;;

    parse)
      parse_block "${AIDLC_ISSUE_BODY:-}"
      if [ "$BLOCK_FOUND" -eq 1 ]; then
        emit found true
      else
        emit found false
      fi
      if [ "$BLOCK_HAS_MARKER" -eq 1 ]; then
        emit has_marker true
      else
        emit has_marker false
      fi
      emit block_format_version      "$BLOCK_FORMAT_VERSION"
      emit block_status              "$BLOCK_STATUS"
      emit block_traceable_row       "$BLOCK_TRACEABLE_ROW"
      emit block_reason_category     "$BLOCK_REASON_CATEGORY"
      emit block_decided_at          "$BLOCK_DECIDED_AT"
      emit block_scope_note          "$BLOCK_SCOPE_NOTE"
      emit block_rejection_closed_at "$BLOCK_REJECTION_CLOSED_AT"
      ;;

    hash)
      load_block_from_env
      emit content_hash "$(content_hash)"
      ;;

    has_marker)
      if has_managed_marker "${AIDLC_ISSUE_BODY:-}"; then
        emit has_marker true
      else
        emit has_marker false
      fi
      ;;

    serialize)
      # 診斷／測試子命令：印出雜湊的實際輸入位元組。
      load_block_from_env
      serialize_block
      ;;

    format_version)
      # R-4.2 互鎖用：讓 run-fixtures.py 不必去 grep 這支腳本的原始碼。
      printf '%s\n' "$FORMAT_VERSION"
      ;;

    known_versions)
      # 診斷／測試子命令：印出 KNOWN_VERSIONS（空白分隔）。互鎖用來確認沒有幽靈
      # 版本（列在這裡但登錄表沒有），以及最大值等於 FORMAT_VERSION。
      printf '%s\n' "$KNOWN_VERSIONS"
      ;;

    "")
      fail "operation 未指定。有效值：render / parse / hash / has_marker"
      ;;

    *)
      # [Q1=A] 的承接方式逐字要求：operation 不合法時**立即非零 exit**，不得靜默
      # 回空值。單一 action 的 inputs/outputs 是四種操作的聯集，YAML 層看不出哪些
      # 組合合法，這個非零 exit 是唯一擋得住錯誤組合的地方。
      fail "未知的 operation: ${op}。有效值：render / parse / hash / has_marker"
      ;;
  esac
}

# hash／serialize 的輸入是 Block 七欄，欄名與 parse 的 output 完全一致，讓
# parse → hash 可以直接對接（U-8 的 read_item → parse → content_hash 就是這條路）。
#
# **這裡不做任何驗證**，理由見檔頭「錯誤模型」：parse 的輸入是人可以編輯的 issue
# body，人為編輯出來的 Block 可能違反互斥不變式，而那正是反向同步要偵測的情形。
load_block_from_env() {
  BLOCK_FORMAT_VERSION="${AIDLC_BLOCK_FORMAT_VERSION:-}"
  BLOCK_STATUS="${AIDLC_BLOCK_STATUS:-}"
  BLOCK_TRACEABLE_ROW="${AIDLC_BLOCK_TRACEABLE_ROW:-}"
  BLOCK_REASON_CATEGORY="${AIDLC_BLOCK_REASON_CATEGORY:-}"
  BLOCK_DECIDED_AT="${AIDLC_BLOCK_DECIDED_AT:-}"
  BLOCK_SCOPE_NOTE="${AIDLC_BLOCK_SCOPE_NOTE:-}"
  BLOCK_REJECTION_CLOSED_AT="${AIDLC_BLOCK_REJECTION_CLOSED_AT:-}"
}

main "$@"
