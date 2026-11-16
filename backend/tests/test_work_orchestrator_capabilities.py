"""`U12 work-orchestrator` Step 6：資料存取層（對既有能力的呼叫）測試。

對應 `unit-test-instructions.md §三` 的第二列 `CapabilityClient`。替身 app 一次回傳
完整 SSE 本體（與 `httpx.ASGITransport` 的緩衝同形）；另以「分段送出本體」的 app
驗證判定只看收齊後的本體（`NFR12.29`）。
"""

import tests.helpers  # noqa: F401  必須最先匯入：處理 sys.path 與 psycopg stub

import asyncio
import logging
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from services.work_orchestrator_capabilities import (
    ADVICE_COMPLETED,
    ADVICE_FAILED,
    ADVICE_GENERATING,
    ADVICE_TIMEOUT,
    COST_LIST_PAGE_SIZE,
    CapabilityClient,
    CapabilityError,
    judge_a1,
    judge_a3,
    judge_advice_snapshot,
    parse_sse,
)
from tests.work_orchestrator_fakes import CostListApp, sse


def run(coro):
    return asyncio.run(coro)


class A1JudgementTest(unittest.TestCase):
    def test_a1_with_xml_takes_the_last_xml_and_joins_messages(self):
        """① 有 xml → 取最後一份；message 依序串接（`BR58.3`）。"""

        async def scenario():
            app = CostListApp()
            app.a1_events = [
                {"type": "message", "content": "第一段"},
                {"type": "progress", "content": "..."},
                {"type": "xml", "content": "<old/>"},
                {"type": "message", "content": "第二段"},
                {"type": "xml", "content": "<new/>"},
            ]
            async with CapabilityClient(app, "tok") as client:
                return await client.generate_architecture("需求", "<cur/>")

        result = run(scenario())
        self.assertIsNone(result.failure)
        self.assertEqual(result.xml, "<new/>")
        self.assertEqual(result.message_text, "第一段\n第二段")

    def test_a1_error_or_missing_xml_is_a_failure_even_with_http_200(self):
        """② HTTP 200 不等於成功（`BR56.5`）：error → a1_failed；無 xml → a1_no_xml 並保留說明。"""
        errored = judge_a1([{"type": "xml", "content": "<x/>"}, {"type": "error", "content": "boom"}])
        self.assertEqual(errored.failure, "a1_failed")
        self.assertIsNone(errored.xml)
        no_xml = judge_a1([{"type": "message", "content": "請問要哪一雲？"}, {"type": "complete"}])
        self.assertEqual(no_xml.failure, "a1_no_xml")
        self.assertEqual(no_xml.message_text, "請問要哪一雲？")


class A3JudgementTest(unittest.TestCase):
    def test_a3_complete_error_and_unfinished(self):
        """③ complete → 成功（分數、發現數）；error → 失敗；結束無 complete → 失敗。"""

        async def scenario():
            app = CostListApp()
            async with CapabilityClient(app, "tok") as client:
                return await client.start_review(12)

        ok = run(scenario())
        self.assertIsNone(ok.failure)
        self.assertEqual((ok.overall_score, ok.findings_count), (82, 2))
        self.assertEqual(
            judge_a3([{"type": "complete", "findings": []}, {"type": "error"}]).failure,
            "a3_failed",
        )
        self.assertEqual(judge_a3([{"type": "rules_done"}]).failure, "a3_incomplete")


class StatusMappingTest(unittest.TestCase):
    def test_non_2xx_raise_with_the_status_code_only(self):
        """④ 401／403／404／5xx 皆以 `CapabilityError(kind=http, status_code)` 拋出。"""
        for status in (401, 403, 404, 500, 503):
            with self.subTest(status=status):

                async def scenario():
                    app = CostListApp()
                    app.status_overrides["GET /api/collab/diagrams/12"] = status
                    async with CapabilityClient(app, "tok") as client:
                        await client.get_diagram(12)

                with self.assertRaises(CapabilityError) as ctx:
                    run(scenario())
                self.assertEqual((ctx.exception.kind, ctx.exception.status_code), ("http", status))

    def test_every_request_carries_the_users_bearer_token(self):
        async def scenario():
            app = CostListApp()
            async with CapabilityClient(app, "user-token-1") as client:
                await client.get_diagram(12)
                await client.get_advice_snapshot(7)
            return app

        app = run(scenario())
        self.assertEqual(app.auth_headers, ["Bearer user-token-1"] * 2)


class CostListPagingTest(unittest.TestCase):
    def _pages(self, target_page):
        pages = []
        for page in range(3):
            chunk = [
                {"id": page * 100 + i, "diagram_id": None if i % 2 else 999,
                 "advice_status": "completed"}
                for i in range(COST_LIST_PAGE_SIZE)
            ]
            pages.append(chunk)
        if target_page is not None:
            pages[target_page][3] = {"id": 4242, "diagram_id": 12, "advice_status": "completed"}
        return pages

    def test_search_stops_at_the_first_page_with_a_match(self):
        """⑤ `NFR12.4`：3 頁、符合者在第 1 頁 → 只讀 1 頁。"""

        async def scenario(target_page):
            app = CostListApp()
            app.estimate_pages = self._pages(target_page)
            async with CapabilityClient(app, "tok") as client:
                found = await client.find_latest_estimate_set({12})
                return found, client.cost_pages_read

        found, pages = run(scenario(0))
        self.assertEqual((found["id"], pages), (4242, 1))
        found, pages = run(scenario(2))
        self.assertEqual((found["id"], pages), (4242, 3))
        found, pages = run(scenario(None))
        self.assertEqual((found, pages), (None, 3))

    def test_estimate_sets_without_a_diagram_are_never_chosen(self):
        async def scenario():
            app = CostListApp()
            app.estimate_pages = [[{"id": 1, "diagram_id": None}, {"id": 2, "diagram_id": 5}]]
            async with CapabilityClient(app, "tok") as client:
                return await client.find_latest_estimate_set({5})

        self.assertEqual(run(scenario())["id"], 2)


class AdviceSnapshotJudgementTest(unittest.TestCase):
    NOW = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)

    def test_generating_older_than_five_minutes_is_a_timeout(self):
        """⑥ `BR57.4`：快照端點不回收過期列，本單元以 `started_at` 自行判定。"""
        fresh = {"status": "generating", "started_at": (self.NOW - timedelta(minutes=4)).isoformat()}
        stale = {"status": "generating", "started_at": (self.NOW - timedelta(minutes=6)).isoformat()}
        self.assertEqual(judge_advice_snapshot(fresh, self.NOW), ADVICE_GENERATING)
        self.assertEqual(judge_advice_snapshot(stale, self.NOW), ADVICE_TIMEOUT)

    def test_failed_is_split_into_timeout_and_failure(self):
        self.assertEqual(
            judge_advice_snapshot({"status": "failed", "unavailable_reasons": {"timed_out": True}}, self.NOW),
            ADVICE_TIMEOUT,
        )
        self.assertEqual(judge_advice_snapshot({"status": "failed"}, self.NOW), ADVICE_FAILED)
        self.assertEqual(judge_advice_snapshot({"status": "completed"}, self.NOW), ADVICE_COMPLETED)
        self.assertEqual(judge_advice_snapshot({"status": "weird"}, self.NOW), ADVICE_FAILED)


class NoLeakTest(unittest.TestCase):
    def test_token_does_not_appear_in_the_exception_or_logs(self):
        """⑦ `NFR12.6`（帶入項 17）：token 出現在 app 例外訊息時，也不進入本單元的例外與 log。"""
        token = f"tok-{uuid.uuid4()}"

        async def scenario():
            app = CostListApp()
            app.raise_in["GET /api/collab/diagrams/12"] = RuntimeError(f"bad header Bearer {token}")
            async with CapabilityClient(app, token) as client:
                await client.get_diagram(12)

        with self.assertLogs("cloud360", level=logging.DEBUG) as logs:
            logging.getLogger("cloud360.work_orchestrator").debug("sentinel")
            with self.assertRaises(CapabilityError) as ctx:
                run(scenario())
        error = ctx.exception
        self.assertNotIn(token, str(error))
        self.assertNotIn(token, repr(error.__cause__))
        self.assertIsNone(error.__cause__)
        self.assertNotIn(token, "\n".join(logs.output))
        # raise_app_exceptions=False：app 內未處理例外落成 500，而不是例外原文。
        self.assertEqual((error.kind, error.status_code), ("http", 500))

    def test_transport_failure_keeps_only_the_class_name(self):
        token = f"tok-{uuid.uuid4()}"

        async def broken_app(scope, receive, send):
            raise ConnectionResetError(f"peer reset {token}")

        async def scenario():
            async with CapabilityClient(broken_app, token) as client:
                await client.get_diagram(1)

        with self.assertRaises(CapabilityError) as ctx:
            run(scenario())
        self.assertNotIn(token, str(ctx.exception))


class BufferedBodyTest(unittest.TestCase):
    def test_judgement_uses_the_complete_body_even_if_sent_in_chunks(self):
        """⑧ `NFR12.29`：本體分多段送出，判定仍以完整本體進行、結果相同。"""
        body = sse([
            {"type": "message", "content": "說明"},
            {"type": "xml", "content": "<final/>"},
        ])

        async def chunked_app(scope, receive, send):
            await receive()
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"text/event-stream")]})
            for i in range(0, len(body), 7):
                await send({"type": "http.response.body", "body": body[i:i + 7], "more_body": True})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        async def scenario():
            async with CapabilityClient(chunked_app, "tok") as client:
                return await client.generate_architecture("x", None)

        result = run(scenario())
        self.assertEqual((result.xml, result.message_text, result.failure), ("<final/>", "說明", None))
        self.assertEqual(len(parse_sse(body.decode())), 2)

    def test_empty_token_is_refused(self):
        with self.assertRaises(ValueError):
            CapabilityClient(object(), "")


if __name__ == "__main__":
    unittest.main()
