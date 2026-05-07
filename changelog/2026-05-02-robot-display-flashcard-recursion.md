# 2026-05-02 — Robot Display Flashcard Recursion Fix

## Summary

- Fixed infinite recursion in `frontend/robot_display/index.html`.
- Captured the base `showFlashcard()` function in `_origShowFlashcard` before overriding it.
- Changed the enhancement from a hoisted function declaration to `showFlashcard = function(data) { ... }` so the saved original reference does not point back to the wrapper.

## Verification

- `python3 tests/run_tests.py` -> 374/374 PASS.
