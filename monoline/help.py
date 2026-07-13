"""The ? help overlay."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

KEYMAP = """\
[b]monoline[/b] — draw with the mouse

 drag            draw          Ctrl+drag   snap to shape
 d / e           pen / eraser  1-9         pick color
 p / P           palette       s           symmetry
 g               grid          u / Ctrl+Z  undo
 r / Ctrl+Y      redo          Ctrl+S      save
 x               export (.txt ANSI / .svg) c  clear
 i          import image/video/3D  v   paste media
 a / A      play / cycle reveal animation (drop, rain, scan…)
 Shift+drag rotate & move 3D model (when loaded)
 ?               this help     q           quit
"""


class HelpScreen(ModalScreen):
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    HelpScreen > Vertical { width: 64; height: auto; padding: 1 2;
                            background: $surface; border: round $accent; }
    """
    BINDINGS = [
        Binding("escape", "dismiss_help", "Close"),
        Binding("question_mark", "dismiss_help", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(KEYMAP)

    def action_dismiss_help(self) -> None:
        self.dismiss()
