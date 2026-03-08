# Tab Interaction Follow-up Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the minimal tab interaction behavior so clicking the start button always returns the workspace to the task tab without changing upload business logic.

**Architecture:** Keep all behavior inside `MainWindow` by exposing lightweight tab-navigation helpers and wiring the start button to the task tab. Avoid controller changes because the current workspace already contains unrelated controller edits.

**Tech Stack:** Python 3.12, PySide6 Widgets, pytest, pytest-qt

---

### Task 1: Capture the new task-tab behavior with a failing GUI test

**Files:**
- Modify: `tests/gui/test_main_window.py`

**Step 1: Write the failing test**
- Add a test that switches to the log tab, clicks `start_button`, and asserts the selected tab becomes `上传任务`.

**Step 2: Run test to verify it fails**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest tests/gui/test_main_window.py::test_start_button_returns_focus_to_task_tab -q`
Expected: FAIL because clicking the button does not yet change the selected tab.

**Step 3: Write minimal implementation**
- Add `show_task_tab()` helper in `MainWindow`.
- Connect `start_button.clicked` to `show_task_tab()`.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 2: Verify the rest of the UI still behaves correctly

**Files:**
- Modify: `AGENTS.md`
- Create: `docs/plans/2026-03-09-tab-interaction-followup-design.md`
- Create: `docs/plans/2026-03-09-tab-interaction-followup-plan.md`

**Step 1: Run focused GUI tests**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest tests/gui/test_main_window.py -q`
Expected: PASS

**Step 2: Run full suite**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest -q`
Expected: PASS

**Step 3: Commit**

```bash
git add AGENTS.md docs/plans/2026-03-09-tab-interaction-followup-design.md docs/plans/2026-03-09-tab-interaction-followup-plan.md tests/gui/test_main_window.py src/quark_uploader/gui/main_window.py
git commit -m "feat: keep task tab focused on upload start"
```
