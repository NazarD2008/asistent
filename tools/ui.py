"""Windows UI Automation tools for JARVIS.

Primary desktop perception layer before Vision fallback.
Uses the Microsoft UI Automation provider through the `uiautomation` package.
"""

from __future__ import annotations

try:
    import uiautomation as auto
except ImportError:
    auto = None


def _require():
    if auto is None:
        raise RuntimeError(
            "uiautomation не встановлений. Виконай: pip install uiautomation"
        )


def _control_name(control) -> str:
    try:
        return (control.Name or "").strip()
    except Exception:
        return ""


def _control_type(control) -> str:
    try:
        return str(control.ControlTypeName or "")
    except Exception:
        return ""


def _is_useful(control) -> bool:
    name = _control_name(control)
    ctype = _control_type(control)
    return bool(name or ctype)


def inspect_ui(max_depth: int = 3, max_items: int = 80) -> str:
    """Повертає коротке дерево доступних UI-елементів foreground-вікна."""
    _require()

    root = auto.GetForegroundControl()
    if root is None:
        return "Не вдалося отримати foreground-вікно."

    lines = []
    seen = 0

    def walk(control, depth: int):
        nonlocal seen
        if seen >= max_items or depth > max_depth:
            return

        if _is_useful(control):
            name = _control_name(control) or "без назви"
            ctype = _control_type(control) or "невідомий"
            lines.append(f"{'  ' * depth}- {ctype}: {name}")
            seen += 1

        if depth >= max_depth or seen >= max_items:
            return

        try:
            children = control.GetChildren()
        except Exception:
            return

        for child in children:
            if seen >= max_items:
                break
            walk(child, depth + 1)

    walk(root, 0)

    if not lines:
        return "UI Automation не знайшов доступних елементів."

    header_name = _control_name(root) or "Foreground window"
    return f"Foreground: {header_name}\n" + "\n".join(lines)


def find_element(name: str):
    """Шукає елемент за Name у foreground-вікні."""
    _require()

    query = str(name or "").strip()
    if not query:
        return None

    root = auto.GetForegroundControl()
    if root is None:
        return None

    try:
        exact = root.Control(searchDepth=10, Name=query)
        if exact.Exists(0.5):
            return exact
    except Exception:
        pass

    query_lower = query.lower()
    queue = [root]
    visited = 0

    while queue and visited < 5000:
        control = queue.pop(0)
        visited += 1

        name_value = _control_name(control)
        if name_value and query_lower in name_value.lower():
            return control

        try:
            queue.extend(control.GetChildren())
        except Exception:
            continue

    return None


def click_element(name: str) -> str:
    """Знаходить UI-елемент за назвою та активує його."""
    control = find_element(name)
    if control is None:
        return f"Не знайшов UI-елемент: {name}."

    try:
        control.SetFocus()
    except Exception:
        pass

    try:
        if control.IsEnabled:
            control.Click()
            return f"Натиснув елемент: {control.Name}."
    except Exception:
        pass

    try:
        control.GetClickablePoint()
        control.Click()
        return f"Натиснув елемент: {control.Name}."
    except Exception as e:
        return f"Знайшов {control.Name}, але не зміг натиснути: {e}"


def get_foreground_name() -> str:
    _require()
    root = auto.GetForegroundControl()
    if root is None:
        return "Foreground-вікно не знайдено."
    return f"Активне вікно: {_control_name(root) or 'без назви'}."
