# Upload Mode Button Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Finalize the controller and GUI tests so they match the new checkable upload-mode buttons already used by the main window.

**Architecture:** Keep `_set_upload_mode()` as the single mode-switch entry point. Replace residual radio-button signal wiring and test references with the current button widgets.

**Tech Stack:** Python 3.12, PySide6 Widgets, pytest, pytest-qt

---

### Task 1: Align controller signal wiring with the new widgets

**Files:**
- Modify: `src/quark_uploader/gui/controller.py`

**Step 1: Update signal connections**
- Replace the old radio toggle binding with click handlers for the two current mode buttons.

**Step 2: Remove dead code**
- Delete the obsolete radio toggle callback.

### Task 2: Sync GUI tests to the current widgets

**Files:**
- Modify: `tests/gui/test_controller.py`
- Modify: `tests/gui/test_interactions.py`

**Step 1: Update controller test references**
- Switch remaining `upload_mode_single_radio` usage to `upload_mode_single_button`.

**Step 2: Tighten interaction assertion**
- Verify `single_target` mode marks the single-target button as checked.

### Task 3: Verify and commit

**Step 1: Run focused tests**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest tests/gui/test_controller.py tests/gui/test_interactions.py -q`
Expected: PASS

**Step 2: Run full suite**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest -q`
Expected: PASS

**Step 3: Commit**

```bash
git add AGENTS.md docs/plans/2026-03-09-upload-mode-button-sync-design.md docs/plans/2026-03-09-upload-mode-button-sync-plan.md src/quark_uploader/gui/controller.py tests/gui/test_controller.py tests/gui/test_interactions.py
git commit -m "fix: sync upload mode button wiring"
```
