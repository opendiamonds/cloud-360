"""BrainDiagramCreation：大腦新建架構圖的判定、取名與建草稿（261116-brain-create-diagram）。

契約（同進程呼叫端依賴，請勿變更）
------------------------------------

ADR-001 的三層形狀：

| 層 | 函式 | 性質 |
|---|---|---|
| 判定 | `decide(p, t, target_kind, has_diagrams, has_drafts)` | **純函式**：不讀 DB、不連外、不拋 `HTTPException`；hypothesis 鎖住 FR2.3 四項性質（ADR-0006 agent routing） |
| 取名 | `make_title(text, system_name, existing_titles)` | **純函式**：同上 |
| 紀錄文字 | `creation_change_texts(title)` | **純函式**：C5 的摘要與標籤 |
| 建草稿 | `create_draft(client, ...)` | I/O：經 `CapabilityClient.create_diagram`（使用者 token、固定 `as_draft=true`），**不重試** |
| 變更紀錄 | `record_creation(facade, ...)` | I/O：經 `HierarchyFacade.record_diagram_change`，**失敗只記 log** |

閘道（`brain_gateway.py`）在交辦前呼叫本模組（ADR-008）；工作編排不建圖。

日誌一律不含使用者原文與圖名（`requirements.md` ADR-0006 audit logging 面向）。
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Final, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("cloud360.brain_diagram_creation")

# ---------------------------------------------------------------------------
# 判定（FR2.2 判定表 ＋ FR6.3a 優先序）
# ---------------------------------------------------------------------------

TARGET_NONE: Final = "none"
TARGET_PROJECT: Final = "project"
TARGET_SYSTEM: Final = "system"
TARGET_DIAGRAM: Final = "diagram"
TARGET_KINDS: Final = (TARGET_NONE, TARGET_PROJECT, TARGET_SYSTEM, TARGET_DIAGRAM)

#: 在作業對象的系統下新建一張草稿並交辦產圖。
CREATE: Final = "create"
#: 修改目前的圖（作業對象是圖、或系統下恰一張；多張時由閘道改送 `pick_diagram`）。
MODIFY: Final = "modify"
#: 反問「新建或修改」（`new_or_modify`）。
ASK_NEW_OR_MODIFY: Final = "new_or_modify"
#: 反問「接著畫哪一張草稿，或新建一張」（FR6.3a，`resume_draft_or_new`）。
ASK_RESUME_DRAFT: Final = "resume_draft_or_new"
#: 反問「要掛在哪個系統」（FR3.1，`pick_system`）。
ASK_PICK_SYSTEM: Final = "pick_system"
#: 系統下沒有圖、使用者卻要修改：回覆沒有圖可改並反問是否新建（FR2.4）。
NO_DIAGRAM_TO_MODIFY: Final = "no_diagram_to_modify"

DECISIONS: Final = (
    CREATE, MODIFY, ASK_NEW_OR_MODIFY, ASK_RESUME_DRAFT, ASK_PICK_SYSTEM, NO_DIAGRAM_TO_MODIFY,
)

#: 判定類別（觀測用，NFR4）：新建／修改／反問／回覆。不含原文與圖名。
CATEGORY_CREATE: Final = "create"
CATEGORY_MODIFY: Final = "modify"
CATEGORY_CLARIFY: Final = "clarify"
CATEGORY_REPLY: Final = "reply"

_ZONE_NEW = "new"
_ZONE_MODIFY = "modify"
_ZONE_UNCLEAR = "unclear"


def _zone(p: Optional[float], t: float) -> str:
    """p ≥ t → 要新的；p ≤ 1 − t → 要修改；之間（或沒有 p）→ 不明。"""
    if p is None:
        return _ZONE_UNCLEAR
    if p >= t:
        return _ZONE_NEW
    if p <= 1.0 - t:
        return _ZONE_MODIFY
    return _ZONE_UNCLEAR


def decide(
    p: Optional[float],
    t: float,
    target_kind: str,
    has_diagrams: bool,
    has_drafts: bool,
) -> str:
    """新建或修改的判定。**純函式。**

    :param p: 路由多問的一題「是否要一張新的圖」的機率（0–1）。`None` 表示這一輪沒有
        取得（例如本機工具呼叫路徑沒有這一題）——視為「不明」。
    :param t: 信心門檻，必須落在 (0.5, 1]（`BRAIN_ROUTER_CONFIDENCE_THRESHOLD`）。
    :param target_kind: `TARGET_*` 之一。
    :param has_diagrams: 作業對象是系統時：系統下是否有任何圖（**含草稿**）。
    :param has_drafts: 作業對象是系統時：系統下是否有草稿；是圖時：該圖本身是否為草稿。
    :raises ValueError: `t` 不在 (0.5, 1]、`p` 不在 [0, 1]、或 `target_kind` 不認得。

    判定表（FR2.2）與優先序：

    - 沒有作業對象或只是專案：要修改 → `MODIFY`（沿用既有「請先選定」路徑）；
      其餘 → `ASK_PICK_SYSTEM`（FR3.1）。
    - 系統、沒有圖：要修改 → `NO_DIAGRAM_TO_MODIFY`（FR2.4）；其餘 → `CREATE`（FR1.2）。
    - 系統、有草稿（**優先於**判定表第二列，FR6.3a）：要修改 → `MODIFY`；
      其餘（含 p ≥ t）→ `ASK_RESUME_DRAFT`。
    - 系統、有圖但沒有草稿：新 → `CREATE`；改 → `MODIFY`；不明 → `ASK_NEW_OR_MODIFY`。
    - 某張正式圖：新 → `CREATE`；改 → `MODIFY`；不明 → `ASK_NEW_OR_MODIFY`。
    - 某張草稿（FR6.3「再說一次，接著畫同一張草稿」）：新或改 → `MODIFY`；
      不明 → `ASK_NEW_OR_MODIFY`。〔推導：判定表第三列寫「某張圖（含草稿）p ≥ t →
      新建」，與 FR6.3／FR6.3b 的「再說一次不另建新圖」直接衝突——同一句「幫我畫一張…」
      的 p 正落在 ≥ t。此處以較具體、有可測形式的 FR6.3b 為準。〕
    """
    if not (0.5 < t <= 1.0):
        raise ValueError("門檻 t 必須落在 (0.5, 1]")
    if p is not None and not (0.0 <= p <= 1.0):
        raise ValueError("機率 p 必須落在 [0, 1]")
    if target_kind not in TARGET_KINDS:
        raise ValueError("未知的作業對象種類")
    zone = _zone(p, t)

    if target_kind in (TARGET_NONE, TARGET_PROJECT):
        return MODIFY if zone == _ZONE_MODIFY else ASK_PICK_SYSTEM
    if target_kind == TARGET_SYSTEM:
        if not has_diagrams:
            return NO_DIAGRAM_TO_MODIFY if zone == _ZONE_MODIFY else CREATE
        if has_drafts:
            return MODIFY if zone == _ZONE_MODIFY else ASK_RESUME_DRAFT
        return {_ZONE_NEW: CREATE, _ZONE_MODIFY: MODIFY}.get(zone, ASK_NEW_OR_MODIFY)
    # TARGET_DIAGRAM
    if has_drafts:
        return ASK_NEW_OR_MODIFY if zone == _ZONE_UNCLEAR else MODIFY
    return {_ZONE_NEW: CREATE, _ZONE_MODIFY: MODIFY}.get(zone, ASK_NEW_OR_MODIFY)


def decision_category(decision: str) -> str:
    """判定 → 觀測類別（NFR4）。"""
    if decision == CREATE:
        return CATEGORY_CREATE
    if decision == MODIFY:
        return CATEGORY_MODIFY
    if decision == NO_DIAGRAM_TO_MODIFY:
        return CATEGORY_REPLY
    return CATEGORY_CLARIFY


# ---------------------------------------------------------------------------
# 取名（FR5.1～FR5.4；契約 C7 naming）
# ---------------------------------------------------------------------------

#: 主題最多幾個**可見字元**（Q4=A）。
TITLE_TOPIC_MAX_GRAPHEMES: Final = 30
#: 指令詞（契約 C7）。依長度由長到短比對，避免「一張」先被「一」之類的短詞截斷。
COMMAND_WORDS: Final = (
    "幫我", "請", "麻煩", "畫", "做", "建", "一張", "一個", "新的", "另一張", "架構圖", "的",
)
TITLE_SUFFIX: Final = "架構圖"
#: 名稱總長的**碼位**上限（修訂 1，FR5.3）。等於 `collab_router.MAX_DIAGRAM_TITLE_CHARS`
#: （端點以 pydantic `max_length` 計碼位）；本模組是純函式、不 import router，兩者相等由
#: `tests/test_brain_diagram_creation.py` 鎖住。可見字元上限擋不住「一個可見字元帶上百個組合
#: 記號」的輸入（zalgo、長 ZWJ 序列），沒有這一層會讓端點回 422、而且每次重說都失敗。
TITLE_MAX_CODEPOINTS: Final = 200
#: 為重名後綴「（n）」預留的碼位數（n 最多 10 位數）。
_DEDUP_SUFFIX_RESERVE: Final = 12
#: 主題（或系統名）可用的碼位數：總上限扣掉「 架構圖」與重名後綴預留。
_TOPIC_MAX_CODEPOINTS: Final = TITLE_MAX_CODEPOINTS - len(" ") - 3 - _DEDUP_SUFFIX_RESERVE
#: 主題頭尾要去掉的標點與空白。
_EDGE_PUNCTUATION: Final = " \t　,.!?;:，。！？；：、「」『』\"'()（）[]【】"
#: 標記：HTML／XML 標籤與 Markdown 強調、程式碼、標題記號。
_TAG_RE: Final = re.compile(r"<[^<>]*>")
_MARKUP_CHARS: Final = frozenset("<>`*#_~|")
_ZWJ: Final = "‍"
_SORTED_COMMAND_WORDS: Final = tuple(sorted(COMMAND_WORDS, key=len, reverse=True))


def _is_extender(ch: str) -> bool:
    """與前一字元合成同一個可見字元的碼位：組合記號、變體選擇器、膚色修飾。"""
    if unicodedata.combining(ch):
        return True
    category = unicodedata.category(ch)
    if category in ("Mn", "Me", "Mc"):
        return True
    code = ord(ch)
    return 0xFE00 <= code <= 0xFE0F or 0x1F3FB <= code <= 0x1F3FF or 0xE0100 <= code <= 0xE01EF


def graphemes(text: str) -> List[str]:
    """把字串切成可見字元（近似 Unicode grapheme cluster；不需要第三方套件）。

    合成規則：組合記號／變體選擇器／膚色修飾附在前一個字元；零寬連接符（ZWJ）把前後
    兩個字元連成一個（例如家庭 emoji）。不處理的少數情況（韓文字母組合、區域旗幟）
    會被切成多個——只會讓截長**更保守**，不會切斷組合字元。
    """
    clusters: List[str] = []
    join_next = False
    for ch in text:
        if clusters and (join_next or _is_extender(ch) or ch == _ZWJ):
            clusters[-1] += ch
            join_next = ch == _ZWJ
            continue
        clusters.append(ch)
        join_next = False
    return clusters


def _sanitize(text: str) -> str:
    """去除控制字元、格式字元（ZWJ 只在 emoji 序列中保留）與標記。"""
    without_tags = _TAG_RE.sub("", text or "")
    out = []
    for ch in without_tags:
        if ch in _MARKUP_CHARS:
            continue
        category = unicodedata.category(ch)
        if category == "Cc" or (category == "Cf" and ch != _ZWJ) or category in ("Cs", "Co", "Cn"):
            continue
        if ch in "  ":
            continue
        out.append(ch)
    cleaned = "".join(out)
    # 孤立的 ZWJ（前後不是可見字元）沒有意義，去掉；其餘保留讓 emoji 序列完整。
    cleaned = re.sub(r"^‍+|‍+$", "", cleaned)
    cleaned = re.sub(r"\s+‍|‍\s+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned)


def _strip_command_words(text: str) -> str:
    """反覆去掉**頭尾**的指令詞與標點，直到不再變動。

    只動頭尾：「的」「建」「畫」等單字在句中可能是主題的一部分（例如「建築」），
    逐字全刪會把主題切壞。
    """
    previous = None
    current = text.strip(_EDGE_PUNCTUATION)
    while current != previous:
        previous = current
        for word in _SORTED_COMMAND_WORDS:
            if current.startswith(word):
                current = current[len(word):].strip(_EDGE_PUNCTUATION)
                break
            if current.endswith(word):
                current = current[: -len(word)].strip(_EDGE_PUNCTUATION)
                break
    return current


def _truncate_graphemes(text: str, limit: int) -> str:
    """取前 `limit` 個可見字元，且總碼位不超過 `_TOPIC_MAX_CODEPOINTS`。

    以**整個可見字元**為單位停止，不切斷組合字元；單一可見字元本身就超過碼位預算時，
    截到它之前為止（寧可主題變短或變空、退回系統名，也不送出端點必拒的長度）。
    """
    kept: List[str] = []
    used = 0
    # 開頭落單的組合記號／ZWJ 沒有可附著的字元：先去掉，避免名稱以它開頭。
    text = text.lstrip(_ZWJ)
    while text and _is_extender(text[0]):
        text = text[1:].lstrip(_ZWJ)
    for cluster in graphemes(text)[:limit]:
        if used + len(cluster) > _TOPIC_MAX_CODEPOINTS:
            break
        kept.append(cluster)
        used += len(cluster)
    return "".join(kept).rstrip(_EDGE_PUNCTUATION)


def make_title(text: str, system_name: str, existing_titles: Iterable[str]) -> str:
    """由使用者的句子取出新圖名稱。**純函式。**

    1. 去控制字元與標記（FR5.3）；
    2. 去頭尾的指令詞（FR5.1，契約 C7 的清單）；
    3. 主題截到 30 個可見字元，不切斷組合字元，且碼位總長留在端點上限內（FR5.3）；
    4. 主題為空 → 「<系統名> 架構圖」（FR5.2）；否則「<主題> 架構圖」；
    5. 與 `existing_titles` 重名 → 加「（n）」，n 從 2 起（FR5.4）。
    """
    topic = _truncate_graphemes(
        _strip_command_words(_sanitize(text)), TITLE_TOPIC_MAX_GRAPHEMES
    )
    if topic:
        base = f"{topic} {TITLE_SUFFIX}"
    else:
        system = _truncate_graphemes(_sanitize(system_name).strip(), TITLE_TOPIC_MAX_GRAPHEMES)
        base = f"{system} {TITLE_SUFFIX}" if system else TITLE_SUFFIX
    taken = {str(t) for t in existing_titles}
    if base not in taken:
        return base
    n = 2
    while f"{base}（{n}）" in taken:
        n += 1
    return f"{base}（{n}）"


# ---------------------------------------------------------------------------
# 變更紀錄文字（契約 C5，FR7.1）
# ---------------------------------------------------------------------------

CREATION_LABEL: Final = "大腦建立架構圖"


def creation_change_texts(title: str) -> Tuple[str, str]:
    """`(requirement_summary, requirement_label)`。摘要非空白（資料表 CHECK 要求）。"""
    return f"經大腦建立「{title}」", CREATION_LABEL


# ---------------------------------------------------------------------------
# I/O（ADR-008：閘道在交辦前呼叫）
# ---------------------------------------------------------------------------

#: 大腦新建時送出的空白骨架（契約 C1；可通過 `_validate_diagram_payload`）。
BLANK_DIAGRAM_XML: Final = (
    '<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/></root></mxGraphModel>'
)


async def create_draft(client: Any, *, title: str, system_id: int) -> int:
    """以使用者 token 建一張草稿，回新圖 id。**不重試**（結果未知時重試會多出一張圖）。

    `CapabilityError` 原樣往外拋，由閘道依契約 C5 的錯誤表回覆使用者。
    """
    return await client.create_diagram(
        title=title, xml_data=BLANK_DIAGRAM_XML, system_id=int(system_id)
    )


def record_creation(facade: Any, principal: Any, *, diagram_id: int, title: str) -> bool:
    """經大腦建立後記一筆變更紀錄（FR7.1）。**任何例外只記 log、回 False**，不影響交辦。

    與 `work_orchestrator._record_change` 相同的處置（契約 C5 錯誤表）。
    log 只含圖 id 與例外類別，不含圖名。
    """
    summary, label = creation_change_texts(title)
    try:
        facade.record_diagram_change(
            principal,
            diagram_id=int(diagram_id),
            requirement_summary=summary,
            requirement_label=label,
            actor_user_id=principal.user_id,
        )
    except Exception as exc:  # noqa: BLE001 - 整合邊界：降級並記 log，不得靜默
        logger.error(
            "brain_diagram_creation change_record_failed diagram=%s error=%s",
            diagram_id,
            type(exc).__name__,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# 反問候選（契約 C6）——純函式
# ---------------------------------------------------------------------------

#: 每種新反問最多列幾筆（FR3.6／契約 C6）；`resume_draft_or_new` 另加一筆「新建」。
CANDIDATE_LIMIT: Final = 10

ACTION_CREATE: Final = "create"
ACTION_MODIFY: Final = "modify"
ACTION_SYSTEM: Final = "system"
ACTION_DIAGRAM: Final = "diagram"

LABEL_CREATE: Final = "新建一張架構圖"
LABEL_MODIFY: Final = "修改目前的圖"
LABEL_NO_DIAGRAM_CREATE: Final = "目前沒有圖可以修改——改為新建一張架構圖"
DRAFT_MARK: Final = "（草稿）"


@dataclass(frozen=True)
class Choice:
    """候選在伺服器端的對照（存在連線上的 `PendingClarify`，不上線）。"""

    action: str
    system_id: Optional[int] = None
    diagram_id: Optional[int] = None


@dataclass(frozen=True)
class Candidate:
    id: str
    label: str
    choice: Choice
    action_wire: Optional[str] = None  # ClarifyCandidate.action（create／modify）


def system_candidates(systems: Sequence[Tuple[int, int, str, str]]) -> Tuple[Tuple[Candidate, ...], bool]:
    """`pick_system`：`(project_id, system_id, system_name, project_name)` → 候選。

    排序：系統名稱、再 id 升冪（契約 C6）。回 `(候選, 是否截斷)`。
    """
    ordered = sorted(systems, key=lambda s: (s[2], s[1]))
    shown = ordered[:CANDIDATE_LIMIT]
    out = tuple(
        Candidate(
            id=f"system-{n}",
            label=f"{name}（專案：{project_name}）",
            choice=Choice(ACTION_SYSTEM, system_id=int(sid)),
        )
        for n, (_pid, sid, name, project_name) in enumerate(shown, start=1)
    )
    return out, len(ordered) > CANDIDATE_LIMIT


def _diagram_label(title: str, status: str) -> str:
    return f"{title}{DRAFT_MARK}" if status == "draft" else title


def diagram_candidates(diagrams: Sequence[Tuple[int, str, str]]) -> Tuple[Tuple[Candidate, ...], bool]:
    """`pick_diagram`：系統下的圖（**含草稿**，已依契約 C5 新到舊排序）→ 候選。"""
    shown = list(diagrams)[:CANDIDATE_LIMIT]
    out = tuple(
        Candidate(
            id=f"diagram-{n}",
            label=_diagram_label(title, status),
            choice=Choice(ACTION_DIAGRAM, diagram_id=int(did)),
        )
        for n, (did, title, status) in enumerate(shown, start=1)
    )
    return out, len(diagrams) > CANDIDATE_LIMIT


def resume_candidates(
    drafts: Sequence[Tuple[int, str, str]], system_id: int
) -> Tuple[Tuple[Candidate, ...], bool]:
    """`resume_draft_or_new`：草稿（C5 順序，最多 10）＋「新建」在最後。"""
    only_drafts = [d for d in drafts if d[2] == "draft"]
    shown = only_drafts[:CANDIDATE_LIMIT]
    out = [
        Candidate(
            id=f"draft-{n}",
            label=f"接著畫「{title}」{DRAFT_MARK}",
            choice=Choice(ACTION_DIAGRAM, diagram_id=int(did)),
            action_wire=ACTION_MODIFY,
        )
        for n, (did, title, _status) in enumerate(shown, start=1)
    ]
    out.append(
        Candidate(
            id="new",
            label=LABEL_CREATE,
            choice=Choice(ACTION_CREATE, system_id=int(system_id)),
            action_wire=ACTION_CREATE,
        )
    )
    return tuple(out), len(only_drafts) > CANDIDATE_LIMIT


def new_or_modify_candidates(*, can_modify: bool) -> Tuple[Candidate, ...]:
    """`new_or_modify`：新建在前（契約 C6）。沒有圖可改時只列新建（FR2.4）。"""
    create = Candidate(
        id="create",
        label=LABEL_CREATE if can_modify else LABEL_NO_DIAGRAM_CREATE,
        choice=Choice(ACTION_CREATE),
        action_wire=ACTION_CREATE,
    )
    if not can_modify:
        return (create,)
    return (
        create,
        Candidate(id="modify", label=LABEL_MODIFY, choice=Choice(ACTION_MODIFY), action_wire=ACTION_MODIFY),
    )


#: FR3.6：候選超過上限時的說明。ClarifyPayload 沒有說明文字欄，故附在最後一筆候選的標籤後。
TRUNCATED_NOTE: Final = "（其餘請用切換對象選取）"


def with_truncation_note(candidates: Tuple[Candidate, ...], truncated: bool) -> Tuple[Candidate, ...]:
    if not truncated or not candidates:
        return candidates
    last = candidates[-1]
    return candidates[:-1] + (
        Candidate(last.id, f"{last.label}{TRUNCATED_NOTE}", last.choice, last.action_wire),
    )


# ---------------------------------------------------------------------------
# 作業對象的事實（I/O：經 HierarchyFacade；閘道在 asyncio.to_thread 內呼叫）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetFacts:
    """判定所需的作業對象事實。由 `load_target_facts` 以使用者自己的範圍取得。"""

    kind: str
    project_id: Optional[int]
    system_id: Optional[int]
    system_name: str
    diagram_id: Optional[int]
    #: 作業對象所屬系統下、使用者自己的圖：`(id, title, status)`，**含草稿**，C5 順序。
    diagrams: Tuple[Tuple[int, str, str], ...]
    target_is_draft: bool
    can_edit: bool

    @property
    def has_diagrams(self) -> bool:
        return bool(self.diagrams)

    @property
    def has_drafts(self) -> bool:
        if self.kind == TARGET_DIAGRAM:
            return self.target_is_draft
        return any(status == "draft" for _id, _t, status in self.diagrams)


def load_target_facts(
    db: Any,
    principal: Any,
    *,
    facade: Any,
    membership: Any,
    project_id: Optional[int],
    system_id: Optional[int],
    diagram_id: Optional[int],
) -> TargetFacts:
    """重新驗證並取得作業對象的事實。**每一層都以使用者自己的範圍解析**（FR4.3）。

    `membership` 是注入的成員關係 facade（ADR-0022 D-6）；每個受守門的 facade 呼叫都**就地**
    以 `membership.project_visibility(principal)` 注入可見性判定（ADR-0022 D-8，由
    `test_project_visibility_static` 的第 3 條鎖住——不得傳入一個事先取好的閉包）。
    `HierarchyNotFound`／`HierarchyForbidden` 原樣往外拋，由閘道處置。
    權限預檢（ADR-009）與端點同一個函式 `user_can_arch(edit)`。
    """
    from models import User, UserDiagram
    from services.rbac import user_can_arch

    resolved = facade.resolve_work_target(
        principal,
        project_visible=membership.project_visibility(principal),
        project_id=project_id,
        system_id=system_id,
        diagram_id=diagram_id,
    )
    rid_project, rid_system, rid_diagram = (
        resolved.get("projectId"), resolved.get("systemId"), resolved.get("diagramId"),
    )
    if rid_diagram is not None:
        kind = TARGET_DIAGRAM
    elif rid_system is not None:
        kind = TARGET_SYSTEM
    elif rid_project is not None:
        kind = TARGET_PROJECT
    else:
        kind = TARGET_NONE

    diagrams: Tuple[Tuple[int, str, str], ...] = ()
    system_name = ""
    if rid_system is not None:
        rows = facade.list_diagrams_of_system(principal, system_id=rid_system, include_drafts=True)
        diagrams = tuple((int(r[0]), str(r[1]), str(r[2])) for r in rows)
        names = facade.describe_work_target(
            principal, project_visible=membership.project_visibility(principal), system_id=rid_system
        )
        system_name = (names or {}).get("systemName") or ""
    target_is_draft = False
    if rid_diagram is not None:
        status = (
            db.query(UserDiagram.status)
            .filter(UserDiagram.id == int(rid_diagram), UserDiagram.user_id == principal.user_id)
            .scalar()
        )
        target_is_draft = status == "draft"
    user = db.get(User, principal.user_id)
    can_edit = bool(
        user is not None
        and getattr(user, "is_active", True)
        and user_can_arch(
            db,
            user.role,
            "edit",
            authorization_status=getattr(user, "authorization_status", "approved"),
        )
    )
    return TargetFacts(
        kind=kind,
        project_id=rid_project,
        system_id=rid_system,
        system_name=system_name,
        diagram_id=rid_diagram,
        diagrams=diagrams,
        target_is_draft=target_is_draft,
        can_edit=can_edit,
    )


def list_owned_systems(principal: Any, *, facade: Any, membership: Any) -> List[Tuple[int, int, str, str]]:
    """FR3.1：使用者**擁有的**系統 `(project_id, system_id, name, project_name)`。

    `list_projects` 已套擁有者範圍 ∩ 可見性（BR6.1／ADR-0022），系統沿用同一範圍。
    可見性判定就地注入（ADR-0022 D-8），理由同 `load_target_facts`。
    """
    out: List[Tuple[int, int, str, str]] = []
    for project in facade.list_projects(
        principal, project_visible=membership.project_visibility(principal)
    ):
        for system in facade.list_systems(
            principal,
            project_id=project.id,
            project_visible=membership.project_visibility(principal),
        ):
            out.append((int(project.id), int(system.id), str(system.name), str(project.name)))
    return out


__all__ = [
    "ACTION_CREATE",
    "ACTION_DIAGRAM",
    "ACTION_MODIFY",
    "ACTION_SYSTEM",
    "CANDIDATE_LIMIT",
    "Candidate",
    "Choice",
    "TargetFacts",
    "diagram_candidates",
    "list_owned_systems",
    "load_target_facts",
    "new_or_modify_candidates",
    "resume_candidates",
    "system_candidates",
    "with_truncation_note",
    "ASK_NEW_OR_MODIFY",
    "ASK_PICK_SYSTEM",
    "ASK_RESUME_DRAFT",
    "BLANK_DIAGRAM_XML",
    "CATEGORY_CLARIFY",
    "CATEGORY_CREATE",
    "CATEGORY_MODIFY",
    "CATEGORY_REPLY",
    "COMMAND_WORDS",
    "CREATE",
    "CREATION_LABEL",
    "DECISIONS",
    "MODIFY",
    "NO_DIAGRAM_TO_MODIFY",
    "TARGET_DIAGRAM",
    "TARGET_KINDS",
    "TARGET_NONE",
    "TARGET_PROJECT",
    "TARGET_SYSTEM",
    "TITLE_TOPIC_MAX_GRAPHEMES",
    "create_draft",
    "creation_change_texts",
    "decide",
    "decision_category",
    "graphemes",
    "make_title",
    "record_creation",
]
