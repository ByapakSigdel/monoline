"""Modal dialogs: text prompt and confirm."""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Static


class TextPrompt(ModalScreen[Optional[str]]):
    DEFAULT_CSS = """
    TextPrompt { align: center middle; }
    TextPrompt > Vertical { width: 60; height: auto; padding: 1 2;
                            background: $surface; border: round $accent; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str, placeholder: str = "") -> None:
        super().__init__()
        self._prompt = prompt
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._prompt)
            yield Input(placeholder=self._placeholder)

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class Confirm(ModalScreen[bool]):
    DEFAULT_CSS = """
    Confirm { align: center middle; }
    Confirm > Vertical { width: 50; height: auto; padding: 1 2;
                         background: $surface; border: round $accent; }
    """
    BINDINGS = [
        Binding("y", "yes", "Yes"),
        Binding("n", "no", "No"),
        Binding("escape", "no", "No"),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._message)
            yield Static("[b]y[/b]es / [b]n[/b]o")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)
