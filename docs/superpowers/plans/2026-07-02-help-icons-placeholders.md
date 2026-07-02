# Help Icons And Placeholders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add placeholder text for configuration inputs across the app, replace `(?)` help markers with immediate-show circular help icons, and add a global settings toggle for showing help icons.

**Architecture:** Centralize help-icon and field-caption behavior in `scr/ui/page_base.py`, then update each configuration page to opt into shared placeholders and tooltips. Persist the new feature flag in settings and let `WorkbenchWindow` broadcast visibility refreshes to already-created pages.

**Tech Stack:** Python 3.12, PySide6, pytest

---

### Task 1: Cover shared help-icon behavior with tests

**Files:**
- Modify: `scr/tests/test_direct_app_entry.py`
- Modify: `scr/tests/test_core_services.py`
- Modify: `scr/services/settings_service.py`
- Modify: `scr/ui/page_base.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_default_settings_enable_help_icons(tmp_path):
    from scr.services.settings_service import build_default_settings
    settings = build_default_settings(tmp_path)
    assert settings["features"]["show_help_icons"] is True

def test_pages_expose_help_icons_and_placeholders(tmp_path):
    ...
    assert train_page.edits["epochs"].placeholderText()
    assert train_page.help_icon_count() >= 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run pytest scr/tests/test_core_services.py::test_default_settings_enable_help_icons scr/tests/test_direct_app_entry.py::test_pages_expose_help_icons_and_placeholders -v`
Expected: FAIL because `show_help_icons` and shared help-icon support do not exist yet.

- [ ] **Step 3: Write minimal shared implementation**

```python
class HelpIcon(QLabel):
    def enterEvent(self, event):
        QToolTip.showText(...)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run pytest scr/tests/test_core_services.py::test_default_settings_enable_help_icons scr/tests/test_direct_app_entry.py::test_pages_expose_help_icons_and_placeholders -v`
Expected: PASS

### Task 2: Apply shared placeholders and help metadata across pages

**Files:**
- Modify: `scr/ui/views/convert.py`
- Modify: `scr/ui/views/training.py`
- Modify: `scr/ui/views/validation.py`
- Modify: `scr/ui/views/preview.py`
- Modify: `scr/ui/views/rename.py`
- Modify: `scr/ui/views/resize.py`
- Modify: `scr/ui/views/settings.py`

- [ ] **Step 1: Write the failing UI tests**

```python
def test_settings_toggle_controls_help_icon_visibility(tmp_path):
    ...
    assert train_page.visible_help_icon_count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pixi run pytest scr/tests/test_direct_app_entry.py::test_settings_toggle_controls_help_icon_visibility -v`
Expected: FAIL because no global toggle refresh exists yet.

- [ ] **Step 3: Implement page-level help text and placeholders**

```python
self.field("命名前缀", "A", placeholder="例如 weld")
self.create_checkbox_row("HSV", "控制色相、饱和度、亮度增强")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pixi run pytest scr/tests/test_direct_app_entry.py::test_settings_toggle_controls_help_icon_visibility -v`
Expected: PASS

### Task 3: Verify the targeted UI and regression suite

**Files:**
- Modify: `scr/theme.py`
- Modify: `scr/ui/window.py`

- [ ] **Step 1: Run focused checks for touched tests**

Run: `pixi run pytest scr/tests/test_core_services.py::test_default_settings_enable_help_icons scr/tests/test_direct_app_entry.py::test_pages_expose_help_icons_and_placeholders scr/tests/test_direct_app_entry.py::test_settings_toggle_controls_help_icon_visibility -v`
Expected: PASS

- [ ] **Step 2: Run the broader UI regression file**

Run: `pixi run pytest scr/tests/test_direct_app_entry.py -v`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `pixi run test`
Expected: PASS
