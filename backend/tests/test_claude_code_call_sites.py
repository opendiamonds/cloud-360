"""A3 的兩個 LLM 呼叫點在本機 `LLM_PROVIDER=claude-code` 下仍能用。

由來：build-and-test `test-results.md` 待修 4（intent-router Minor (b)）——`review_agent` 的
串流與 `wa_lens_engine` 的 JSON 擷取都改經 `langgraph_runtime.chat_model` factory，但
`ClaudeCodeChatModel` 沒有 `_astream`（只有 `_generate`／`_agenerate`），而這兩個呼叫點
從未在 claude-code 下被測過；本機驗證也把「A3 評估頁」列為未驗。

兩個風險都是「乾淨環境會過、開發者機器會壞」那一類：

1. `review_agent.run_review_agent` 以 `stream_mode="messages"` 取文字。若模型不串流時
   LangGraph 一個訊息都不吐，呼叫端會拋「ReviewAgent 未產出 suggestions」，而 CI 永遠不會
   走到這條路（CI 不設 `APP_ENV=local`）。
2. `wa_lens_engine.answer_lens_with_agent` 從模型文字擷取 JSON。`claude` CLI 的回覆常以
   ```json 圍欄包住，擷取若只認裸 JSON，整份 lens 會落到 `RuntimeError` 再由呼叫端退回
   啟發式——畫面上看起來仍有分數，錯誤是靜默的。

假的 `claude` 沿用 `test_claude_code_chat.FakeCliCase`（暫存目錄、前置到 `PATH`，不連外）。
本功能屬 code-generation 新增、scope 尚未涵蓋（traceability `LOCAL-LLM-PROVIDER`），
故 `@story` 如實標「無」；測試直接呼叫服務函式、不經 HTTP 端點也不碰頁面，依撰寫標準
`tcms-test-cases:c20`，`@api`／`@ui` 寧缺不造。
"""

from __future__ import annotations

import asyncio
import json

from services import review_agent, wa_lens_engine
from tests.test_claude_code_chat import FakeCliCase

_SUGGESTION = "建議一：把資料庫移到私有子網路。建議二：為 ALB 加上 WAF。"


def _collect(agen) -> list[str]:
    async def _run() -> list[str]:
        return [chunk async for chunk in agen]

    return asyncio.run(_run())


class ReviewAgentUnderClaudeCode(FakeCliCase):
    def test_review_agent_streams_cli_text_as_suggestions(self) -> None:
        """
        @purpose A3 改善建議在 claude-code 下要真的產出文字，而不是因為模型不串流而拋
                 「ReviewAgent 未產出 suggestions」。
        @given APP_ENV=local、LLM_PROVIDER=claude-code；PATH 前置一支假 claude，固定回一段建議文字
        @step 以一份含一項 HIGH_RISK finding 的評核結果呼叫 run_review_agent 並收齊所有 chunk | 收到至少 1 個 chunk
        @step 把 chunk 串起來 | 等於假 CLI 回的那段建議文字，一字不差
        @step 檢視假 CLI 收到的 stdin | 包含 finding 的 code「SEC-01」（評核摘要確實送到模型）
        @pass 串起來的文字等於假 CLI 的回覆，且 stdin 含「SEC-01」
        @story 無（本階段新增、scope 尚未涵蓋；traceability LOCAL-LLM-PROVIDER）
        @note 回歸防護：ClaudeCodeChatModel 沒有 _astream，若 LangGraph 的 messages 串流模式
              對不串流的模型一個訊息都不吐，run_review_agent 會在最後拋 RuntimeError。突變把
              stream_mode 改成 "values"（只吐 state、不吐訊息）時本案紅燈。
        """
        self.install_response(_SUGGESTION)

        chunks = _collect(
            review_agent.run_review_agent(
                {"nodes": [{"label": "RDS"}, {"label": "ALB"}], "node_count": 2},
                {
                    "overall_score": 61,
                    "findings": [
                        {
                            "code": "SEC-01",
                            "severity": "HIGH_RISK",
                            "title": "資料庫位於公有子網路",
                            "recommendation_hint": "移到私有子網路",
                        }
                    ],
                },
            )
        )

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual("".join(chunks), _SUGGESTION)
        self.assertIn("SEC-01", self.captured("stdin.txt"))


class LensAgentUnderClaudeCode(FakeCliCase):
    def _lens_and_first_question(self) -> tuple[dict, dict]:
        lens = wa_lens_engine.load_lens(provider="aws")
        questions = wa_lens_engine.list_questions(lens)
        self.assertTrue(questions, "內建 AWS lens 應至少有一題")
        return lens, questions[0]

    def test_lens_agent_reads_fenced_json_from_cli(self) -> None:
        """
        @purpose A3 lens 填答在 claude-code 下，CLI 以 ```json 圍欄包住的回覆仍要被擷取成答案，
                 而不是擷取失敗後靜默退回啟發式。
        @given APP_ENV=local、LLM_PROVIDER=claude-code；假 claude 回「說明文字＋```json 圍欄」，
               圍欄內為內建 AWS lens 第一題選第一個 choice，另附一個不存在的題號
        @step 呼叫 answer_lens_with_agent | 不拋例外
        @step 檢視回傳的答案 | 恰含第一題，值為 [第一個 choice id]
        @step 檢視回傳的答案 | 不得含那個不存在的題號
        @pass 回傳值恰為 {第一題 id: [第一個 choice id]}
        @story 無（本階段新增、scope 尚未涵蓋；traceability LOCAL-LLM-PROVIDER）
        @note 回歸防護：若擷取只認裸 JSON（json.loads(text)），圍欄回覆會拋例外、
              answer_lens_with_agent 往上拋，呼叫端退回啟發式而畫面照樣有分數——錯誤是靜默的。
              突變把 _extract_json_payload 換成 json.loads 時本案紅燈。
        """
        lens, first = self._lens_and_first_question()
        qid = first["question_id"]
        cid = first["choices"][0]["id"]
        body = json.dumps(
            {
                "answers": [
                    {"question_id": qid, "selected_choice_ids": [cid]},
                    {"question_id": "NO-SUCH-QUESTION", "selected_choice_ids": ["x"]},
                ]
            },
            ensure_ascii=False,
        )
        self.install_response(f"以下是我的判讀：\n```json\n{body}\n```\n")

        answers = asyncio.run(
            wa_lens_engine.answer_lens_with_agent({"nodes": [{"label": "ALB"}]}, lens)
        )

        self.assertEqual(answers, {qid: [cid]})
        self.assertNotIn("NO-SUCH-QUESTION", answers)
