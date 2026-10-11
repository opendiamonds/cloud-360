"""intent_routing_context.py — `U11 intent-router` 的 **L2**：prompt 組裝（純函式）

**契約（同進程呼叫端依賴，請勿變更）**

本檔**是純函式層**，而那是刻意設計的：取資料的 I/O 放在它之外
（`intent_routing.fetch_routing_context` 先取好再傳進來），使 `BR6.1`
「最少上下文」可以被一個**不需要 mock 的測試**驗證。那是本單元測試策略的
基礎（`logical-components.md` §二）。

硬約束
------

- **零 I/O、零 DB、零網路、零 session 型別。** 本檔**不 import `BrainSession`、
  簽章也不接受它**（`NFR9.60`）——**不給它，它就送不出去**。這是本單元最接近
  「用型別擋住人」的一處：資料外送最小化靠「拿不到」比靠「記得不要送」可靠。
- **輸出長度有上界，且不隨歷程長度成長**（`NFR9.61`）。歷程上限是**每段
  200 則**，而每輪成本與歷程長度線性相關——整段附上會逼近 Jev 的 context
  32000 上界。本檔在**自己這一層**再截一次（呼叫端 L0 已先截），兩層都有不是
  重複而是縱深。

`BR6.1` 同時是資料外送最小化（ADR-0006 encryption 面）
----------------------------------------------------

本單元的 `external_dependencies` 含 **OpenRouter（third-party-api）**，
亦即**使用者的自然語言輸入會離開本平台**。附上整段對話歷程等於把更多個人
內容送出去——`cost_discipline` 的原文只講成本，本檔明記它也是安全邊界。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional, Sequence, Tuple

from services.intent_routing_types import (
    MAX_CANDIDATES_PER_SLOT,
    MAX_SLOTS,
    REFERENT_ABSENT,
    REFERENT_RESOLVED,
    REFERENT_UNRESOLVED,
    ROUTABLE_CAPABILITIES,
)

#: 帶進 prompt 的歷程則數上界（`NFR9.61`）。
DEFAULT_MESSAGE_LIMIT: Final = 6

#: 單則歷程的字元上界。單則訊息本身的上界是 4000 字元（`U10` 的
#: `DEFAULT_MESSAGE_MAX_CHARS`），6 則 × 4000 已是 24000 字元——逼近 Jev 的
#: context 32000。故本層另有一個遠小的上界。
DEFAULT_MESSAGE_CHARS: Final = 400

#: 帶進 prompt 的記憶筆數上界。記憶的用途是**理解偏好與術語**（`BR5.5`），
#: 不是全文檢索。
DEFAULT_MEMORY_LIMIT: Final = 5

#: 使用者輸入帶進 prompt 的字元上界。它**大於**歷程的上界——這一句才是要被
#: 分類的對象，截掉它會直接損害 `FR1.1`。
DEFAULT_TEXT_CHARS: Final = 4000

#: 能力 id → 一句人話。**刻意是 tuple of pairs 而不是 dict**：`NFR3.67`
#: 禁止行程內的共享可變狀態，而一個模組層 `dict` 即使只當查表用也是可變綁定
#: ——`tests/test_intent_routing_structure.py` 以 AST 掃描模組層的
#: `dict`／`list`／`set` 字面值，而「它只是常數」這種例外一旦開了，下一個真的
#: 是狀態的 dict 也會以同樣的理由被放進來。
_CAPABILITY_HINTS: Final = (
    ("architecture-design", "產生或修改架構圖（draw.io 元件與連線）"),
    ("well-architected-review", "以 Well-Architected 支柱評核架構並列出風險與建議"),
    ("cost-finops", "依官方估價表計算成本與 FinOps 建議"),
)


@dataclass(frozen=True)
class RoutingPrompt:
    """送給模型的兩段文字。**刻意不含任何 session 物件。**"""

    system: str
    user: str

    @property
    def text(self) -> str:
        """兩段合起來的長度，用於 `NFR9.61` 的長度斷言。"""
        return f"{self.system}\n{self.user}"


def _capability_catalogue() -> str:
    hints = dict(_CAPABILITY_HINTS)
    lines = []
    for capability in ROUTABLE_CAPABILITIES:
        hint = hints.get(capability, "")
        lines.append(f"- `{capability}`：{hint}" if hint else f"- `{capability}`")
    return "\n".join(lines)


def build_system_prompt() -> str:
    """固定的系統指示。**不含任何使用者資料**，故它是常數級的字串。

    它要交代四件模型必須知道、而我方會驗證的事：
    封閉列舉（`V-2`）、槽位編號自 0 連續與其上界（`V-3`）、組內 `rank`
    自 1 連續（`V-4`）、以及 `tied_with_next` 與 `referent_state` 的語意
    （`BR3.3`／`EC3`）。
    """
    return (
        "你是 Cloud-360 的意圖路由層。你的唯一工作是把一句使用者需求判定成"
        "一或多個「要系統做的事」，並為每一件事列出可能的讀法。"
        "你**不執行**任何能力、**不產生**任何成果、**不決定**執行順序。\n"
        "\n"
        "可路由的能力（封閉列舉，不得發明新值）：\n"
        f"{_capability_catalogue()}\n"
        "\n"
        "輸出規則：\n"
        f"1. 一句話含 N 件可分離的事，就用 N 個槽位（`slot` 自 0 連續，最多 "
        f"{MAX_SLOTS} 個）。單一意圖就是 N=1。\n"
        "2. **同一個槽位內的候選是互斥的**（對同一件事的幾種讀法）；"
        "**不同槽位之間是並存的**（兩件事都要做）。不要把兩件事放進同一個槽位，"
        "也不要把同一件事的兩種讀法拆成兩個槽位。\n"
        f"3. 每個槽位的 `rank` 自 1 連續且唯一，最多 {MAX_CANDIDATES_PER_SLOT} "
        "個候選。\n"
        "4. `tied_with_next` 表示「這個候選與下一名之間**沒有**嚴格優先」"
        "（也就是並列、分不出哪個更對）。最後一名一律填 false。"
        "**這個欄位決定系統要不要回頭問使用者，請誠實填寫**：分不出來就填 true，"
        "不要為了看起來有把握而填 false。\n"
        f"5. `referent_state` 取 `{REFERENT_ABSENT}`（這句話沒有指涉詞）、"
        f"`{REFERENT_UNRESOLVED}`（有指涉詞但無法判定指哪一個）或 "
        f"`{REFERENT_RESOLVED}`（已解析，`referent` 填出對象）。"
        "**無法判定時填 unresolved，不要擅自挑一個。**\n"
        "6. `slot_labels` 與槽位等長，每個是該件事的一句人話描述"
        "（例如「改架構圖」「估成本差額」）。\n"
        "7. `score` 是 0 到 1 的信心值。**若你無法給出可互相比較的分數，"
        "全部填 null**——不要只給其中幾個。\n"
    )


def build_routing_prompt(
    *,
    user_text: str,
    work_target_hint: Optional[str] = None,
    recent_messages: Sequence[Tuple[str, str]] = (),
    memory_notes: Sequence[str] = (),
    message_limit: int = DEFAULT_MESSAGE_LIMIT,
    message_chars: int = DEFAULT_MESSAGE_CHARS,
    memory_limit: int = DEFAULT_MEMORY_LIMIT,
    text_chars: int = DEFAULT_TEXT_CHARS,
) -> RoutingPrompt:
    """組出**最少上下文**的 prompt（`BR6.1`／`NFR9.60`／`NFR9.61`）。

    **簽章刻意只收四樣已取得的資料**（作業對象、最後 K 則歷程、記憶筆記、
    使用者文字），**不收 `BrainSession`**。`BrainSession` 持有**全部三段**的
    完整歷程；把它傳進來就等於讓這一層有能力把 600 則訊息送出平台，
    而「它實際上沒送」只能靠 review 確認。

    截斷在本層**無條件**發生，不依賴呼叫端先截——`message_limit` 是參數而不是
    呼叫端的自律。
    """
    lines = []
    if work_target_hint:
        lines.append(f"目前的作業對象：{work_target_hint}")
    else:
        lines.append("目前的作業對象：尚未選定")
    lines.append(
        "**若使用者在這句話裡直接點名了對象，以句中的對象為準，"
        "優先於上面這個目前值**（BR5.3）。"
    )

    tail = list(recent_messages)[-message_limit:] if message_limit > 0 else []
    if tail:
        lines.append("")
        lines.append(f"這一段對話的最後 {len(tail)} 則（**刻意只給這幾則**）：")
        for role, text in tail:
            lines.append(f"- {role}：{str(text)[:message_chars]}")

    notes = [note for note in list(memory_notes)[:memory_limit] if note]
    if notes:
        lines.append("")
        lines.append(
            "這位使用者的術語與偏好（**只用於理解用詞，"
            "不得用來決定指涉對象指誰**，BR5.5）："
        )
        for note in notes:
            lines.append(f"- {note[:message_chars]}")

    lines.append("")
    lines.append("使用者這一句需求：")
    lines.append(str(user_text)[:text_chars])
    return RoutingPrompt(system=build_system_prompt(), user="\n".join(lines))


__all__ = [
    "DEFAULT_MEMORY_LIMIT",
    "DEFAULT_MESSAGE_CHARS",
    "DEFAULT_MESSAGE_LIMIT",
    "DEFAULT_TEXT_CHARS",
    "RoutingPrompt",
    "build_routing_prompt",
    "build_system_prompt",
]
