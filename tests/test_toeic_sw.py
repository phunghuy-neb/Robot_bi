#!/usr/bin/env python3
"""Offline tests for TOEIC Speaking & Writing backend helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_robot_bi_testing_only_32chars!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("SKIP_LLM", "1")


def _item(qid="q1", qtype="toeic_writing", topic="email", points=5):
    return {
        "question_id": qid,
        "answer": "",
        "explanation": "",
        "question_type": qtype,
        "question": "Write an email to your friend.",
        "question_vi": "Viết email trả lời bạn.",
        "topic": topic,
        "points": points,
        "order_index": 0,
    }


def _paper(skill="writing"):
    return {"skill": skill, "pass_percent": 60, "subject": "toeic_sw"}


def test_constants_exist():
    from src.api.routers import exam_router as r

    assert r.TOEIC_SW_SUBJECT == "toeic_sw"
    assert r.TOEIC_SPEAKING_TYPE in r.TOEIC_SW_QUESTION_TYPES
    assert r.TOEIC_WRITING_TYPE in r.TOEIC_SW_QUESTION_TYPES
    assert "ước tính" in r.TOEIC_ESTIMATE_DISCLAIMER


def test_estimated_200_bounds():
    from src.api.routers.exam_router import _estimate_200

    assert _estimate_200(0, 5) == 0
    assert _estimate_200(2.5, 5) == 100
    assert _estimate_200(99, 5) == 200
    assert _estimate_200(1, 0) == 0


def test_empty_writing_scores_zero_without_llm():
    from src.api.routers.exam_router import SubmitToeicSW, _grade_toeic_sw_attempt

    body = SubmitToeicSW(responses={"q1": ""}, time_spent_seconds=3)
    result = _grade_toeic_sw_attempt(_paper("writing"), [_item()], body, "writing")
    assert result["score"] == 0
    assert result["estimated_200"] == 0
    assert result["review"][0]["score"] == 0


def test_writing_grades_and_persists_payload_shape():
    from src.api.routers.exam_router import SubmitToeicSW, _grade_toeic_sw_attempt

    text = "Hello, thank you for your email. I can attend the meeting tomorrow and bring the book."
    body = SubmitToeicSW(responses={"q1": text}, time_spent_seconds=30)
    result = _grade_toeic_sw_attempt(_paper("writing"), [_item()], body, "writing")
    assert result["score"] > 0
    assert 0 <= result["estimated_200"] <= 200
    assert result["answers_payload"]["responses"]["q1"] == text
    assert "q1" in result["answers_payload"]["rubric"]
    assert result["disclaimer"] == result["answers_payload"]["disclaimer"]


def test_speaking_transcript_path():
    from src.api.routers.exam_router import SubmitToeicSW, _grade_toeic_sw_attempt

    item = _item(qtype="toeic_speaking", topic="read_aloud", points=3)
    transcript = "The weather is nice today and I want to practice English with Robot Bi."
    body = SubmitToeicSW(transcripts={"q1": transcript}, test_mode=True)
    result = _grade_toeic_sw_attempt(_paper("speaking"), [item], body, "speaking")
    assert result["score"] > 0
    assert result["review"][0]["given"] == transcript
    assert result["review"][0]["max_score"] == 3


def test_non_toeic_questions_are_ignored_by_helper():
    from src.api.routers.exam_router import SubmitToeicSW, _grade_toeic_sw_attempt

    item = _item(qtype="mcq")
    body = SubmitToeicSW(responses={"q1": "A"})
    result = _grade_toeic_sw_attempt(_paper("writing"), [item], body, "writing")
    assert result["review"] == []
    assert result["score"] == 0


def test_track_catalog_contains_toeic_sw_levels():
    from src.api.routers.exam_router import ROADMAP_LEVELS, TRACK_CATALOG

    assert TRACK_CATALOG["toeic_sw"]["kind"] == "roadmap"
    assert ROADMAP_LEVELS["toeic_sw"] == [
        "toeic_sw_100",
        "toeic_sw_120",
        "toeic_sw_140",
        "toeic_sw_160",
        "toeic_sw_180",
        "toeic_sw_200",
    ]


TESTS = [
    test_constants_exist,
    test_estimated_200_bounds,
    test_empty_writing_scores_zero_without_llm,
    test_writing_grades_and_persists_payload_shape,
    test_speaking_transcript_path,
    test_non_toeic_questions_are_ignored_by_helper,
    test_track_catalog_contains_toeic_sw_levels,
]


def main() -> int:
    failed = []
    for test in TESTS:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - standalone runner reports all cases.
            failed.append((test.__name__, exc))
            print(f"FAIL {test.__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\nSummary: {len(TESTS) - len(failed)}/{len(TESTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
