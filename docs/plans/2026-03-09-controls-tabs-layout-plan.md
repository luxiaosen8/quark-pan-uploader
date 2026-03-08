# Controls-First Tabs Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the main PySide6 window so the controls area becomes the full-width top workspace and the lower area becomes tabbed views for tasks, remote folders, and logs.

**Architecture:** Keep the existing widget instances and controller wiring, but reorganize `MainWindow` into a top controls card with an embedded status summary and a bottom `QTabWidget`. Keep all behavior changes confined to UI composition and tests.

**Tech Stack:** Python 3.12, PySide6 Widgets, pytest, pytest-qt

---

### Task 1: Describe the new layout with failing GUI tests

**Files:**
- Modify: `tests/gui/test_main_window.py`

**Step 1: Write the failing test**
- Assert the root layout places `controls_card` first and `workspace_tabs` second.
- Assert the tab order is `上传任务` / `目标网盘目录` / `运行日志`.
- Assert the default selected tab is `上传任务`.

**Step 2: Run test to verify it fails**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest tests/gui/test_main_window.py -q`
Expected: FAIL because `workspace_tabs` and the new root structure do not exist yet.

**Step 3: Write minimal implementation**
- Introduce `QTabWidget` layout and move existing cards into tabs.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 2: Rebuild the controls area into a full-width operation workspace

**Files:**
- Modify: `src/quark_uploader/gui/main_window.py`

**Step 1: Write the failing test**
- Assert the controls area remains scroll-light at default window size.
- Assert the selected remote summary remains visible from the top controls area.

**Step 2: Run test to verify it fails**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest tests/gui/test_main_window.py -q`
Expected: FAIL until the controls content is reorganized.

**Step 3: Write minimal implementation**
- Nest the summary strip inside the controls card.
- Arrange operation widgets into connection/source/action subsections.
- Keep business widget instances unchanged.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 3: Update docs and validate the entire suite

**Files:**
- Modify: `AGENTS.md`
- Create: `docs/plans/2026-03-09-controls-tabs-layout-design.md`
- Create: `docs/plans/2026-03-09-controls-tabs-layout-plan.md`

**Step 1: Run focused GUI tests**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest tests/gui/test_main_window.py -q`
Expected: PASS

**Step 2: Run full suite**

Run: `C:/Users/78221/Desktop/workspace/trae-cn/号池/wangpan/.venv/Scripts/python.exe -m pytest -q`
Expected: PASS

**Step 3: Commit**

```bash
git add AGENTS.md docs/plans/2026-03-09-controls-tabs-layout-design.md docs/plans/2026-03-09-controls-tabs-layout-plan.md tests/gui/test_main_window.py src/quark_uploader/gui/main_window.py
git commit -m "feat: prioritize controls workspace with tabs"
```
