"""Main TUI implementation.

Terminal user interface for OpenClaw.
"""

from __future__ import annotations

from .types import TUIOptions


class TUI:
    """Terminal UI for OpenClaw.

    Provides an interactive terminal chat interface.
    """

    def __init__(self, options: TUIOptions | None = None):
        """Initialize TUI.

        Args:
            options: TUI options
        """
        self.options = options or TUIOptions()
        self.running = False

    async def start(self) -> None:
        """Start TUI."""
        self.running = True
        print("OpenClaw TUI")
        print("=" * 60)
        print(f"Agent: {self.options.agent_id}")
        print("Type your message and press Enter to chat.")
        print("Type /exit to quit.")
        print("=" * 60)

        # Main loop
        while self.running:
            try:
                user_input = input("\n> ")

                if user_input.strip() == "/exit":
                    break

                if user_input.strip():
                    await self._handle_input(user_input)

            except KeyboardInterrupt:
                break
            except EOFError:
                break

        print("\nGoodbye!")

    async def _handle_input(self, text: str) -> None:
        """Handle user input.

        Args:
            text: User input text
        """
        # In production, would use get_reply() from auto_reply
        print(f"[Bot]: I received: {text}")
        print("[Bot]: (Full TUI implementation would show agent response here)")


async def run_tui(options: TUIOptions | None = None) -> None:
    """Run TUI.

    Args:
        options: TUI options
    """
    tui = TUI(options)
    await tui.start()
