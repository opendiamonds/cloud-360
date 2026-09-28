"""`backend/scripts/dump_ws_contract.py` 的閘門語意測試（`U2 brain-ws-contract`）。

覆蓋第一道 CI 閘門的四件事：`--check` 的 **fail-closed** 語意（`nfr-design §六`）、
`BR1.4`（type 列舉與 payload 實體兩集合等勢且可對應）、`NFR5.7`（客戶端欄位白名單）
與 `BR4.2`／`BR4.6`（序列化的決定性與冪等）。

**不得寫到 repo 根的真實 `ws-contract.json`**：本檔全部檔案操作都在
`tempfile.TemporaryDirectory()` 內，並以 `mock.patch.object` 把模組的 `SPEC_PATH`
指到那裡。讓測試寫到真實規格檔會讓 CI 的第一道閘門看到被測試改過的檔——一道
斷言「規格檔 == 程式碼」的閘門，不能由一個會改規格檔的測試來驗。

**`BR1.4`／白名單的突變測試不改動真實模組**：兩者的判定式都接受一個 schemas
字典，測試傳入真實 schemas 的**深拷貝**並在拷貝上注入缺陷，用完即丟。

腳本位於 `backend/scripts/`（不是套件），故以 `importlib.util` 依路徑載入，形狀
比照 `test_repo_contract_secret_patterns.py`／`test_repo_contract_production_paths.py`
兩個既有先例。

`@api`／`@ui` 兩個標記在本檔**刻意缺席**：受測對象是一支 CLI 腳本，既無 HTTP 端點
也無頁面，依 `project.md` 的既有更正「寧可缺、不得捏造」。
"""

import tests.helpers  # noqa: F401  -- installs the psycopg2 stub before services import

import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "backend" / "scripts" / "dump_ws_contract.py"


def _load_dump_module():
    spec = importlib.util.spec_from_file_location(
        "cloud360_dump_ws_contract_under_test", SCRIPT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module spec from {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dump = _load_dump_module()


def _run_main(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = dump.main(argv)
    return code, out.getvalue(), err.getvalue()


def _live_schemas() -> dict[str, Any]:
    """真實契約的 schemas 深拷貝，供注入缺陷用。"""
    return copy.deepcopy(dump.build_spec()["components"]["schemas"])


class DumpCheckModeTest(unittest.TestCase):
    """`--check` 的 fail-closed 語意。"""

    def test_check_fails_closed_when_spec_file_is_absent(self):
        """
        @purpose 規格檔不存在時 `--check` 必須 exit 非 0 並指向 dump 指令——
                 「沒驗成」不得與「驗過且通過」在退出碼上長得一樣。
        @given 一個空的暫存目錄，模組的 SPEC_PATH 指向其中一個不存在的檔名
        @step 執行 main(["--check"]) | 回傳碼為 1
        @step 讀 stderr | 含「規格檔不存在」與 `scripts/dump_ws_contract.py` 指令
        @step 讀 stdout | 不含任何表示一致的字串
        @pass 回傳碼為 1，且 stderr 指名要跑哪一個指令修它
        @story US8.1
        @note 斷言訊息含指令字串，不只斷言 exit 1：一道紅燈若沒說怎麼修，
              下一個人的最短路徑會是把它從 ci.yml 刪掉。
        """
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "ws-contract.json"
            with mock.patch.object(dump, "SPEC_PATH", absent):
                code, out, err = _run_main(["--check"])
        self.assertEqual(code, 1)
        self.assertIn("規格檔不存在", err)
        self.assertIn("scripts/dump_ws_contract.py", err)
        self.assertNotIn("一致", out)

    def test_check_passes_when_spec_matches_the_models(self):
        """
        @purpose 規格檔與契約模組一致時必須 exit 0——否則閘門在沒有漂移時紅燈，
                 而假紅燈與真漂移在訊號上不可區分，久了整道閘門會被繞過。
        @given 暫存目錄內寫入 render_spec() 的輸出，SPEC_PATH 指向它
        @step 執行 main(["--check"]) | 回傳碼為 0
        @step 讀 stdout | 含「一致」
        @pass 回傳碼為 0 且 stdout 明說一致
        @story US8.1
        @note 這是閘門的 happy path。缺它的話一個「永遠 exit 1」的腳本也會讓
              其餘三個否定案例全綠。
        """
        with tempfile.TemporaryDirectory() as tmp:
            spec_file = Path(tmp) / "ws-contract.json"
            spec_file.write_text(dump.render_spec(), encoding="utf-8")
            with mock.patch.object(dump, "SPEC_PATH", spec_file):
                code, out, err = _run_main(["--check"])
        self.assertEqual(code, 0, err)
        self.assertIn("一致", out)

    def test_check_detects_a_hand_edited_spec_file(self):
        """
        @purpose 手改衍生物必須被抓到（`BR4.1`：規格檔與型別檔皆為衍生物、不得手改）
                 ——手改能讓型別看起來對而後端行為不對，那正是這道閘門要消除的失敗模式。
        @given 暫存目錄內寫入正確的規格檔，SPEC_PATH 指向它
        @step 把規格檔的 info.version 手改成 9.9.9 後存回 | 檔案內容已變更
        @step 執行 main(["--check"]) | 回傳碼為 1
        @step 讀 stderr | 含「漂移」與 `services/brain_ws_contract.py`
        @pass 回傳碼為 1，且 stderr 指名真實來源是哪一支模組
        @story US8.1
        @note 改的是 info.version 而非某個 schema：它證明比對是**逐位元全檔**，
              不是只比 components.schemas 那一段。
        """
        with tempfile.TemporaryDirectory() as tmp:
            spec_file = Path(tmp) / "ws-contract.json"
            spec_file.write_text(dump.render_spec(), encoding="utf-8")
            tampered = json.loads(spec_file.read_text(encoding="utf-8"))
            tampered["info"]["version"] = "9.9.9"
            spec_file.write_text(
                json.dumps(tampered, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(dump, "SPEC_PATH", spec_file):
                code, out, err = _run_main(["--check"])
        self.assertEqual(code, 1)
        self.assertIn("漂移", err)
        self.assertIn("services/brain_ws_contract.py", err)


class TypePayloadParityTest(unittest.TestCase):
    """`BR1.4` — 兩個 type 列舉與對應方向的 payload 實體集合等勢且可一一對應。"""

    def test_parity_assertion_catches_a_type_without_a_payload(self):
        """
        @purpose 加了一個 type 卻沒有對應的 payload 實體必須被擋下——消費端收到
                 該 type 時無從處理它的形狀，而那在型別檔上看不出來。
        @given 真實 schemas 的深拷貝
        @step 對未注入的真實 schemas 跑 assert_type_payload_parity | 不拋例外
        @step 在拷貝的 WsServerMessageType.enum 尾端加一個 extra_type | 拷貝已變更
        @step 對拷貝跑 assert_type_payload_parity | 拋 ContractAssertionError，訊息指名 ExtraTypePayload
        @step 另取一份拷貝，加入一個沒有任何 type 對應的 GhostPayload schema | 拋 ContractAssertionError 並稱它為死碼
        @pass 正反兩個方向（有 type 沒 payload、有 payload 沒 type）都被擋下，
              且訊息指名缺的／多的是哪一個
        @story US8.1
        @note 斷言訊息含 ExtraTypePayload 而非只斷言拋錯：兩集合大小不等也會拋，
              所以只斷言拋錯無法區分「抓到的是缺哪一個」還是「只是數字不一樣」。
              這個區別是 M3 突變驗證能不能被看見的關鍵。
        """
        schemas = _live_schemas()
        dump.assert_type_payload_parity(schemas)  # 未注入時必須通過

        with_extra_type = _live_schemas()
        with_extra_type[dump.SERVER_TYPE_ENUM]["enum"].append("extra_type")
        with self.assertRaises(dump.ContractAssertionError) as ctx:
            dump.assert_type_payload_parity(with_extra_type)
        self.assertIn("ExtraTypePayload", str(ctx.exception))

        with_orphan_payload = _live_schemas()
        with_orphan_payload["GhostPayload"] = {"type": "object", "properties": {}}
        with self.assertRaises(dump.ContractAssertionError) as ctx:
            dump.assert_type_payload_parity(with_orphan_payload)
        self.assertIn("GhostPayload", str(ctx.exception))
        self.assertIn("死碼", str(ctx.exception))


class ClientFieldWhitelistTest(unittest.TestCase):
    """`NFR5.7` — 七個客戶端物件的欄位名集合逐一等於釘住的預期集合。"""

    def test_whitelist_assertion_catches_an_undeclared_client_field(self):
        """
        @purpose 客戶端物件長出任何未宣告的欄位都必須紅燈——身分等價欄位的命名空間
                 是開放的（userId／actor／onBehalfOf…），禁用名單列不完，白名單由
                 構造封閉。這是 NFR5.7 在建置期的那一半。
        @given 真實 schemas 的深拷貝；白名單釘在 dump_ws_contract.py 內
        @step 對未注入的真實 schemas 跑 assert_client_field_whitelist | 不拋例外
        @step 在拷貝的 WsClientEnvelope.properties 注入一個 onBehalfOf 欄位 | 拋 ContractAssertionError，訊息指名 onBehalfOf
        @step 另取一份拷貝，從 SetWorkTargetPayload.properties 刪掉 systemId | 拋 ContractAssertionError，訊息指名 systemId
        @pass 多一個欄位與少一個欄位兩個方向都被擋下，訊息指名是哪一個欄位
        @story US8.1
        @note 「少一個欄位」這一半非測不可：它是這道斷言用**相等**而不是**包含**
              的唯一證據。若判定式鬆成「預期是實際的子集就通過」，多欄位那一半
              會靜默放行，而多欄位正是身分欄位進來的方向。
              注入的欄位名刻意選 onBehalfOf——它不在任何禁用名單上，用它才證明
              白名單擋的是「未宣告」而不是「名字看起來像身分」。
        """
        dump.assert_client_field_whitelist(_live_schemas())  # 未注入時必須通過

        with_extra_field = _live_schemas()
        with_extra_field["WsClientEnvelope"]["properties"]["onBehalfOf"] = {"type": "string"}
        with self.assertRaises(dump.ContractAssertionError) as ctx:
            dump.assert_client_field_whitelist(with_extra_field)
        self.assertIn("onBehalfOf", str(ctx.exception))

        with_missing_field = _live_schemas()
        del with_missing_field["SetWorkTargetPayload"]["properties"]["systemId"]
        with self.assertRaises(dump.ContractAssertionError) as ctx:
            dump.assert_client_field_whitelist(with_missing_field)
        self.assertIn("systemId", str(ctx.exception))


class SerialisationDeterminismTest(unittest.TestCase):
    """`BR4.2`／`BR4.6` — 輸出必須與 dict 插入順序無關，且重跑冪等。"""

    def test_render_is_byte_identical_and_key_order_is_sorted(self):
        """
        @purpose 輸出必須與 dict 插入順序無關，否則閘門會在程式碼沒改時紅燈，
                 而那種紅燈與真的漂移在訊號上不可區分，閘門隨即失去信任。
        @given 契約模組已載入
        @step 連續呼叫 render_spec() 兩次並比對 | 兩次輸出逐位元相同
        @step 以 object_pairs_hook 解析輸出，走訪每一個 JSON 物件 | 每個物件的鍵皆為已排序
        @step 檢查輸出結尾 | 以單一換行結束
        @pass 兩次輸出相同、全檔每個物件的鍵都已排序、結尾有換行
        @story US8.1
        @note 只比「連跑兩次相同」**抓不到** sort_keys 被拿掉——同一個行程內
              dict 的插入順序是穩定的，兩次輸出仍會一樣。真正鎖住 BR4.2 的是
              第二步的鍵序斷言：sort_keys 一被拿掉，頂層就會是插入序
              openapi/info/paths/components 而不是字典序。這一點是本 repo
              `{} or {...}` 那次教訓的同型陷阱。
        """
        first = dump.render_spec()
        second = dump.render_spec()
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))
        self.assertFalse(first.endswith("\n\n"))

        unsorted_paths: list[str] = []

        def check(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            keys = [key for key, _ in pairs]
            if keys != sorted(keys):
                unsorted_paths.append(",".join(keys[:6]))
            return dict(pairs)

        json.loads(first, object_pairs_hook=check)
        self.assertEqual(unsorted_paths, [], f"有 {len(unsorted_paths)} 個物件的鍵未排序")


if __name__ == "__main__":
    unittest.main()
