"""大腦 WebSocket 契約模型的不變量測試（`U2 brain-ws-contract`）。

覆蓋 `backend/services/brain_ws_contract.py` 的四條可機械斷言的不變量：
`BR1.5`（終止事件兩份 turnId 必須相等）、`BR1.6`（turnId 的輪次／非輪次二分）、
`BR2.13`（客戶端封包不得攜帶 turnId）與 `WsSubprotocol` 的字面型別（`NFR5.4`）。

**本檔不需要任何 mock**：契約模組是純 Pydantic 模型，無 I/O、無 DB、無網路。
`import tests.helpers` 放在**第一個 import**（它在任何 DB import 之前裝 psycopg
樁），形狀比照 `test_database_security.py`／`test_diagram_icons.py`／
`test_llm_provider.py`／`test_wa_rule_engine.py` 四個既有先例：docstring 在前、
該 import 為首個 import。本單元的契約模組其實不 import 任何 DB——沿用以免例外。

**`WsSubprotocol` 的兩個值刻意不寫死字串**（見 `test_ws_subprotocol_*`）：從模型的
型別註解取值。寫死字串會讓測試與被測物件同時錯，而那正是 `NFR5.4` 在防的形狀。

`@api`／`@ui` 兩個標記在本檔**刻意缺席**：本單元不新增任何 HTTP 端點（WebSocket
端點是 `U13`）也不碰任何頁面，依 `project.md` 的既有更正「受測對象既無端點也無 UI
時寧可缺、不得捏造」。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg stub before services import

import unittest
from typing import get_args

from pydantic import ValidationError

from services.brain_ws_contract import (
    WsClientEnvelope,
    WsEnvelope,
    WsServerMessageType,
    WsSubprotocol,
)
from services.brain_ws_contract import (
    _SESSION_SCOPED_TYPES,
    _TERMINAL_TYPE_VALUES,
    _TURN_SCOPED_TYPES,
)

TURN_ID = "turn-0001"

# 每個伺服器 type 的最小合法 payload。`done`／`error` 的 turnId 由呼叫端填，
# 因為 BR1.5 要求它與 envelope 的那一份相等。
_SERVER_PAYLOAD_SAMPLES = {
    WsServerMessageType.READY: {"protocolVersion": 1},
    WsServerMessageType.TOKEN: {"text": "第一個字"},
    WsServerMessageType.CLARIFY: {
        "candidates": [
            {"id": "c1", "label": "建一張架構圖", "capability": "A1", "confidence": 0.42}
        ]
    },
    WsServerMessageType.WORK_ITEMS: {"items": []},
    WsServerMessageType.COST_CARD: {
        "estimateSetId": 7,
        "savingText": None,
        "comparisonText": None,
        "qualityText": None,
        "unavailableReasons": None,
        "costPageUrl": "/cost",
    },
    WsServerMessageType.SHARING_MODE: {"mode": "shared"},
    WsServerMessageType.WORK_TARGET: {"projectId": None, "systemId": None, "diagramId": None},
    WsServerMessageType.DONE: {"turnId": None},
    WsServerMessageType.ERROR: {
        "code": "INTERNAL_ERROR",
        "message": "這一輪沒有完成",
        "turnId": None,
    },
}


def payload_for(message_type: WsServerMessageType, turn_id: str | None) -> dict:
    """取該 type 的最小合法 payload；終止事件的 payload turnId 填入 `turn_id`。"""
    sample = dict(_SERVER_PAYLOAD_SAMPLES[message_type])
    if message_type.value in _TERMINAL_TYPE_VALUES:
        sample["turnId"] = turn_id
    return sample


class WsEnvelopeTurnIdConsistencyTest(unittest.TestCase):
    """`BR1.5` — 終止事件 payload 的 turnId 必須等於其 envelope 的 turnId。"""

    def test_terminal_event_with_matching_turn_ids_is_accepted(self):
        """
        @purpose 終止事件的兩份 turnId 相等時必須可構造——否則 BR1.5 會變成一條
                 讓合法訊息也無法送出的死規則。
        @given 契約模組 backend/services/brain_ws_contract.py 已載入
        @step 以 turnId=turn-0001 構造 done envelope，payload.turnId 同值 | 構造成功
        @step 以同樣形狀構造 error envelope（code=INTERNAL_ERROR）| 構造成功
        @step 讀回兩者的 envelope.turnId 與 payload.turnId | 兩份皆為 turn-0001
        @pass 兩則終止事件皆構造成功，且兩份 turnId 讀回同值
        @story US8.1
        @note 這是 BR1.5 的 happy path。它與下面兩個否定案例一起才構成完整的斷言：
              只有否定案例時，一個「永遠拋錯」的 validator 也會讓它們全綠。
        """
        for message_type in (WsServerMessageType.DONE, WsServerMessageType.ERROR):
            with self.subTest(type=message_type.value):
                envelope = WsEnvelope(
                    v=1,
                    type=message_type.value,
                    turnId=TURN_ID,
                    payload=payload_for(message_type, TURN_ID),
                )
                self.assertEqual(envelope.turnId, TURN_ID)
                self.assertEqual(envelope.payload.turnId, TURN_ID)

    def test_terminal_event_with_mismatched_turn_ids_is_rejected(self):
        """
        @purpose 兩份 turnId 不一致必須被拒——消費端會把終止事件歸到錯誤的一輪，
                 而那個錯誤在畫面上看起來像「上一輪突然結束了」。
        @given 契約模組已載入
        @step 構造 done envelope，envelope.turnId=turn-0001、payload.turnId=turn-0002 | 拋 ValidationError
        @step 讀錯誤訊息 | 訊息含 BR1.5 並同時印出兩個不一致的值
        @step 對 error envelope 重複同一組操作 | 同樣拋 ValidationError 且訊息含 BR1.5
        @pass 兩則皆拋 ValidationError，訊息含字串 BR1.5
        @story US8.1
        @note 斷言訊息含 BR1.5 而非只斷言拋錯：turnId 是必填欄位，所以「拋了錯」
              有好幾個來源，只有訊息能證明拒絕它的是 BR1.5 那條規則。
        """
        for message_type in (WsServerMessageType.DONE, WsServerMessageType.ERROR):
            with self.subTest(type=message_type.value):
                with self.assertRaises(ValidationError) as ctx:
                    WsEnvelope(
                        v=1,
                        type=message_type.value,
                        turnId=TURN_ID,
                        payload=payload_for(message_type, "turn-0002"),
                    )
                self.assertIn("BR1.5", str(ctx.exception))

    def test_terminal_event_without_payload_turn_id_is_rejected(self):
        """
        @purpose payload 完全沒有 turnId 時必須被 BR1.5 擋下並說出「缺欄位」而不是
                 「不一致」——排查的人否則會去找兩個不一致的值而其中一個不存在。
        @given 契約模組已載入
        @step 構造 done envelope，envelope.turnId=turn-0001、payload 為空物件 | 拋 ValidationError
        @step 讀錯誤訊息 | 訊息含 BR1.5
        @step 對 error envelope 以只有 code 與 message 的 payload 重複 | 同樣拋 ValidationError 且含 BR1.5
        @pass 兩則皆拋 ValidationError，訊息含字串 BR1.5
        @story US8.1
        @note 這一項要求 BR1.5 跑在 payload 自身的必填檢查**之前**（實作上是
              mode="before" 的 model validator）。若它跑在之後，DonePayload 自己的
              「field required」會先擋下，訊息不會提到 BR1.5，而讀訊息的人只會以為
              漏填了一個欄位，不知道那個欄位的值受另一個欄位約束。
        """
        cases = {
            WsServerMessageType.DONE: {},
            WsServerMessageType.ERROR: {"code": "INTERNAL_ERROR", "message": "沒有完成"},
        }
        for message_type, payload in cases.items():
            with self.subTest(type=message_type.value):
                with self.assertRaises(ValidationError) as ctx:
                    WsEnvelope(v=1, type=message_type.value, turnId=TURN_ID, payload=payload)
                self.assertIn("BR1.5", str(ctx.exception))


class WsEnvelopeTurnIdPartitionTest(unittest.TestCase):
    """`BR1.6` — 九個伺服器 type 分輪次／非輪次兩類，互斥且窮盡。"""

    def test_turn_scoped_type_requires_non_null_turn_id(self):
        """
        @purpose 輪次訊息缺 turnId 必須被拒——消費端無法把它歸到任何一輪，
                 而訊息仍會被渲染，所以失敗是靜默的。
        @given 契約模組已載入；_TURN_SCOPED_TYPES 為 token/clarify/cost_card/done/error
        @step 對每個非終止的輪次型別（token、clarify、cost_card）以 turnId=None 構造 | 拋 ValidationError 且訊息含 BR1.6
        @step 對兩個終止型別（done、error）以 turnId=None 構造 | 拋 ValidationError（見 note）
        @step 確認輪次型別集合恰為五個 | 集合大小為 5
        @pass 五個輪次型別在 turnId=None 時全部被拒；三個非終止型別的訊息含 BR1.6
        @story US8.1
        @note 終止型別的訊息**不**斷言含 BR1.6，理由是實作順序：done／error 的
              payload 也帶一份 turnId，envelope 的 null 會先在 BR1.5 的相等比對
              或 DonePayload.turnId 的 str 型別上被擋下，比 BR1.6 早。三條路徑
              拒絕的是同一個不變量，所以這裡只斷言「被拒」，不假裝知道是誰拒的。
        """
        self.assertEqual(len(_TURN_SCOPED_TYPES), 5)
        for message_type in sorted(_TURN_SCOPED_TYPES, key=lambda t: t.value):
            with self.subTest(type=message_type.value):
                with self.assertRaises(ValidationError) as ctx:
                    WsEnvelope(
                        v=1,
                        type=message_type.value,
                        turnId=None,
                        payload=payload_for(message_type, None),
                    )
                if message_type.value not in _TERMINAL_TYPE_VALUES:
                    self.assertIn("BR1.6", str(ctx.exception))

    def test_session_scoped_type_forbids_turn_id(self):
        """
        @purpose 非輪次訊息帶 turnId 必須被拒——它們不屬於任何一輪，帶了值會讓
                 消費端把狀態訊息誤歸到某一輪並在該輪的對話裡渲染它。
        @given 契約模組已載入；_SESSION_SCOPED_TYPES 為 ready/sharing_mode/work_target/work_items
        @step 對四個非輪次型別各以 turnId=turn-0001 構造 | 皆拋 ValidationError 且訊息含 BR1.6
        @step 對同四個型別以 turnId=None 構造 | 皆構造成功
        @step 確認非輪次型別集合恰為四個 | 集合大小為 4
        @pass 四個型別在 turnId 非 null 時全被拒、為 null 時全通過
        @story US8.1
        @note 正反兩面都測：只測「帶了值被拒」時，一個把四個型別全部拒掉的
              validator 也會全綠，而那會讓 ready 與三個狀態訊息完全無法送出。
        """
        self.assertEqual(len(_SESSION_SCOPED_TYPES), 4)
        for message_type in sorted(_SESSION_SCOPED_TYPES, key=lambda t: t.value):
            with self.subTest(type=message_type.value, turnId="非 null"):
                with self.assertRaises(ValidationError) as ctx:
                    WsEnvelope(
                        v=1,
                        type=message_type.value,
                        turnId=TURN_ID,
                        payload=payload_for(message_type, TURN_ID),
                    )
                self.assertIn("BR1.6", str(ctx.exception))
            with self.subTest(type=message_type.value, turnId="null"):
                envelope = WsEnvelope(
                    v=1,
                    type=message_type.value,
                    turnId=None,
                    payload=payload_for(message_type, None),
                )
                self.assertIsNone(envelope.turnId)


class WsClientEnvelopeTest(unittest.TestCase):
    """`BR2.13`／`BR2.12` — 客戶端封包不得攜帶 turnId 或身分。"""

    def test_client_envelope_rejects_turn_id_and_identity_fields(self):
        """
        @purpose 客戶端封包在型別層就不得攜帶 turnId 或身分欄位——principal 綁在
                 連線上，客戶端能指定這些欄位即為一個授權繞過。
        @given 契約模組已載入
        @step 檢視 WsClientEnvelope 的欄位集合 | 恰為 v、type、payload，不含 turnId
        @step 以 turnId=turn-0001 構造 hello 客戶端封包 | 拋 ValidationError 且訊息含 turnId
        @step 分別以 userId、role、token、actor、onBehalfOf 五個多餘欄位構造 | 五者皆拋 ValidationError
        @pass 欄位集合不含 turnId，且六種多餘欄位全部無法構造
        @story US8.1
        @note 關鍵在於「拋錯」而不是「被忽略」：Pydantic 的預設是 extra="ignore"，
              那會讓客戶端以為自己成功指定了輪次而伺服器其實丟掉了那個值——
              靜默忽略比拒絕更糟。身分欄位一併測，是因為 BR2.12 與 BR2.13 由
              同一個 extra="forbid" 承載，測一個等於沒測另一個。
        """
        self.assertEqual(set(WsClientEnvelope.model_fields), {"v", "type", "payload"})
        self.assertNotIn("turnId", WsClientEnvelope.model_fields)

        for field in ("turnId", "userId", "role", "token", "actor", "onBehalfOf"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as ctx:
                    WsClientEnvelope(
                        **{
                            "v": 1,
                            "type": "hello",
                            "payload": {"v": 1},
                            field: "偷帶的值",
                        }
                    )
                self.assertIn(field, str(ctx.exception))


class WsSubprotocolTest(unittest.TestCase):
    """`NFR5.4`／`ADR-0019 §3` — 握手 subprotocol 的兩個欄位為字面型別。"""

    def test_subprotocol_fields_are_literals_and_reject_other_values(self):
        """
        @purpose subprotocol 的名稱與分隔字元必須是字面型別，前端才能由型別取值；
                 後端改值時前端那一行即為型別錯誤。這是 NFR5.4 的型別層基礎。
        @given 契約模組已載入
        @step 由 WsSubprotocol 的型別註解取出 scheme 與 separator 的字面值 | 各恰有一個字面值
        @step 以取出的兩個值構造 WsSubprotocol | 構造成功且讀回同值
        @step 以 scheme 加一個字元構造 | 拋 ValidationError
        @step 以 separator 換成另一個字元構造 | 拋 ValidationError
        @pass 兩個欄位各只有一個合法值，其餘值皆無法構造
        @story US8.1
        @note 兩個值**從模型取**而非寫死 'bearer' 與 '.'：寫死會讓測試與被測物件
              同時錯（後端改成 brain. 時測試也一起改成 brain.，然後綠燈），
              而那正是 NFR5.4 在防的失敗形狀。後端改字面值的實際紅燈落在
              `npm run build`（前端的 const SCHEME: Sub['scheme'] = 'bearer'），
              不在本檔——本檔只保證那兩個欄位真的是字面型別。
        """
        scheme_literals = get_args(WsSubprotocol.model_fields["scheme"].annotation)
        separator_literals = get_args(WsSubprotocol.model_fields["separator"].annotation)
        self.assertEqual(len(scheme_literals), 1)
        self.assertEqual(len(separator_literals), 1)

        scheme, separator = scheme_literals[0], separator_literals[0]
        subprotocol = WsSubprotocol(scheme=scheme, separator=separator)
        self.assertEqual(subprotocol.scheme, scheme)
        self.assertEqual(subprotocol.separator, separator)

        with self.assertRaises(ValidationError):
            WsSubprotocol(scheme=scheme + "x", separator=separator)
        with self.assertRaises(ValidationError):
            WsSubprotocol(scheme=scheme, separator=separator + separator)


if __name__ == "__main__":
    unittest.main()
