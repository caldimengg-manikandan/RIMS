"""
WebSocket submit_answer: Redis-backed idempotency + evaluation replay (interview_controller).
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.services.interview_engine import interview_controller as ic


def _base_state():
    return {
        "role": "Software Engineer",
        "experience": "Mid-Level",
        "skills": ["Python"],
        "difficulty": "medium",
        "history": [],
        "current_question": {
            "question": "What is a list?",
            "expected_points": ["mutability"],
        },
    }


class TestWsSubmitIdempotency(unittest.TestCase):
    def tearDown(self):
        ic.interview_state.pop("ws-test-session", None)

    def test_first_submit_evaluates_and_caches(self):
        async def run():
            ic.interview_state["ws-test-session"] = _base_state()
            with (
                patch(
                    "app.services.interview_engine.interview_controller.evaluate_answer",
                    new_callable=AsyncMock,
                ) as ev,
                patch(
                    "app.services.interview_engine.interview_controller.session_manager.send_personal_message",
                    new_callable=AsyncMock,
                ) as send,
                patch(
                    "app.services.interview_engine.interview_controller.cache_get",
                    return_value=None,
                ),
                patch(
                    "app.services.interview_engine.interview_controller.cache_set",
                ) as cs,
                patch(
                    "app.services.interview_engine.interview_controller.is_duplicate_request",
                    return_value=False,
                ),
            ):
                ev.return_value = {"technical_accuracy": 7, "feedback_text": "ok"}
                await ic.process_interview_message(
                    "ws-test-session",
                    {"action": "submit_answer", "answer": "answer text", "request_id": "rid-ws-1"},
                )
                self.assertTrue(ev.called)
                cs.assert_called()
                eval_calls = [c for c in send.call_args_list if c[0][0].get("type") == "evaluation"]
                self.assertEqual(len(eval_calls), 1)
                self.assertEqual(eval_calls[0][0][0]["score"], 7)

        asyncio.run(run())

    def test_cached_evaluation_skips_ai(self):
        async def run():
            ic.interview_state["ws-test-session"] = _base_state()
            cached = {"type": "evaluation", "score": 9, "feedback": "cached"}
            with (
                patch(
                    "app.services.interview_engine.interview_controller.evaluate_answer",
                    new_callable=AsyncMock,
                ) as ev,
                patch(
                    "app.services.interview_engine.interview_controller.session_manager.send_personal_message",
                    new_callable=AsyncMock,
                ) as send,
                patch(
                    "app.services.interview_engine.interview_controller.cache_get",
                    return_value=cached,
                ),
            ):
                await ic.process_interview_message(
                    "ws-test-session",
                    {"action": "submit_answer", "answer": "anything", "request_id": "rid-ws-2"},
                )
                self.assertFalse(ev.called)
                last_eval = [c for c in send.call_args_list if c[0][0] == cached]
                self.assertTrue(last_eval)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
