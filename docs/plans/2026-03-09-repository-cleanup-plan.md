# Repository Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove local-only artifacts and add ignore rules so the repository is ready for publishing without touching unrelated source changes.

**Architecture:** Limit permanent repository changes to `.gitignore`, `AGENTS.md`, and cleanup docs. Perform filesystem cleanup only on build caches, runtime outputs, and debug directories. Keep existing uncommitted source edits untouched.

**Tech Stack:** Git, Python 3.12, local filesystem cleanup

---

### Task 1: Record cleanup scope

**Files:**
- Create: `docs/plans/2026-03-09-repository-cleanup-design.md`
- Create: `docs/plans/2026-03-09-repository-cleanup-plan.md`

**Step 1: Write the cleanup doc**
- Document what can be deleted and what must remain untouched.

**Step 2: Verify files exist**

Run: `python -c "from pathlib import Path; print(Path('docs/plans/2026-03-09-repository-cleanup-design.md').exists(), Path('docs/plans/2026-03-09-repository-cleanup-plan.md').exists())"`
Expected: `True True`

### Task 2: Add ignore rules for local debug/output leftovers

**Files:**
- Modify: `.gitignore`
- Modify: `AGENTS.md`

**Step 1: Update `.gitignore`**
- Add `debug_large/`, `debug_small/`, `debug_stop/`, `cleanup-output/`, `custom-output/`

**Step 2: Update `AGENTS.md`**
- Record the repository cleanup rule so future sessions keep these local artifacts out of version control.

**Step 3: Verify with git status**

Run: `git status --short --untracked-files=all`
Expected: debug artifacts no longer appear after cleanup.

### Task 3: Remove local artifacts and verify repository state

**Files:**
- Filesystem cleanup only

**Step 1: Delete local-only directories**
- Remove `build/`, `dist/`, `output/`, `.local/`, `.pytest_cache/`, `debug_large/`, `debug_small/`, `debug_stop/`, `cleanup-output/`, `custom-output/`, and all `__pycache__/`

**Step 2: Verify repository state**

Run: `git status --short --ignored`
Expected: only unrelated pre-existing source edits remain; cleaned artifact directories are absent or ignored.

**Step 3: Commit**

```bash
git add .gitignore AGENTS.md docs/plans/2026-03-09-repository-cleanup-design.md docs/plans/2026-03-09-repository-cleanup-plan.md
git commit -m "chore: prepare repository for publishing"
```
