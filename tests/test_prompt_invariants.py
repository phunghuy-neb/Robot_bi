#!/usr/bin/env python3
"""Standalone invariant tests for Robot Bi prompt/persona contracts.

Run:
    python tests/test_prompt_invariants.py
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


VIETNAMESE_DIACRITICS = set(
    "ăâđêôơư"
    "ĂÂĐÊÔƠƯ"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệ"
    "íìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữự"
    "ýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆ"
    "ÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰ"
    "ÝỲỶỸỴ"
)


def _has_vietnamese_diacritic(text: str) -> bool:
    return any(ch in VIETNAMESE_DIACRITICS for ch in text)


def _count_vietnamese_diacritics(text: str) -> int:
    return sum(1 for ch in text if ch in VIETNAMESE_DIACRITICS)


def test_import_prompts() -> None:
    module = importlib.import_module("src.ai.prompts")
    assert module is not None


def test_prompt_exports_exist() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    required = [
        "FRIEND_PROMPT",
        "TEACHER_PROMPT",
        "PARENT_CHILD_PROMPT",
        "PARENT_ADVISOR_PROMPT",
        "MAIN_SYSTEM_PROMPT",
        "SAFETY_CHECK_PROMPT",
        "REFUSAL_RESPONSE",
        "ERROR_RESPONSE",
        "GREETING",
        "PROMPT_VERSION",
        "build_system_prompt",
    ]
    missing = [name for name in required if not hasattr(prompts, name)]
    assert not missing, f"missing exports: {missing}"
    assert callable(prompts.build_system_prompt)


def test_main_system_prompt_alias() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    assert prompts.MAIN_SYSTEM_PROMPT is prompts.FRIEND_PROMPT


def test_prompt_version_format() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    assert re.match(r"^v\d+\.\d+$", prompts.PROMPT_VERSION), prompts.PROMPT_VERSION


def test_child_prompts_are_unaccented() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    for name in ("FRIEND_PROMPT", "TEACHER_PROMPT"):
        value = getattr(prompts, name)
        count = _count_vietnamese_diacritics(value)
        assert count == 0, f"{name} contains {count} Vietnamese diacritic chars"


def test_parent_prompts_are_accented() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    for name in ("PARENT_CHILD_PROMPT", "PARENT_ADVISOR_PROMPT"):
        value = getattr(prompts, name)
        assert _has_vietnamese_diacritic(value), f"{name} should contain Vietnamese diacritics"


def test_core_guardrail_substrings() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    all_prompt_text = "\n".join(
        [
            prompts.FRIEND_PROMPT,
            prompts.TEACHER_PROMPT,
            prompts.PARENT_CHILD_PROMPT,
            prompts.PARENT_ADVISOR_PROMPT,
            prompts.SAFETY_CHECK_PROMPT,
        ]
    ).lower()
    assert "dat ten" in all_prompt_text
    assert "dap an ngay" in all_prompt_text
    assert "nguy hiem" in all_prompt_text
    assert "khong the huong dan" in prompts.REFUSAL_RESPONSE.lower()


def test_build_system_prompt_returns_bi_text() -> None:
    prompts = importlib.import_module("src.ai.prompts")
    result = prompts.build_system_prompt(
        {"name": "Bi", "playfulness": 80, "energy": 80, "extraversion": 20}
    )
    assert isinstance(result, str)
    assert result.strip()
    assert "Bi" in result


def test_role_and_persona_public_symbols() -> None:
    role_manager = importlib.import_module("src.ai.role_manager")
    persona_manager = importlib.import_module("src.ai.persona_manager")
    assert hasattr(role_manager, "RoleManager")
    assert hasattr(role_manager, "detect_distress")
    assert hasattr(persona_manager, "PersonaManager")


TESTS = [
    test_import_prompts,
    test_prompt_exports_exist,
    test_main_system_prompt_alias,
    test_prompt_version_format,
    test_child_prompts_are_unaccented,
    test_parent_prompts_are_accented,
    test_core_guardrail_substrings,
    test_build_system_prompt_returns_bi_text,
    test_role_and_persona_public_symbols,
]


def main() -> int:
    failures = []
    for test_fn in TESTS:
        try:
            test_fn()
        except Exception as exc:  # noqa: BLE001 - standalone test runner reports all failures.
            failures.append((test_fn.__name__, exc))
            print(f"FAIL {test_fn.__name__}: {exc}")
        else:
            print(f"PASS {test_fn.__name__}")

    total = len(TESTS)
    passed = total - len(failures)
    print(f"\nSummary: {passed}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
