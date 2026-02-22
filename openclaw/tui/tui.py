"""Main TUI orchestrator — pi_tui based.

Mirrors TypeScript openclaw/src/tui/tui.ts using the same component stack:
  - ProcessTerminal + TUI  for differential-rendering
  - Editor                 for multi-line text input
  - Text/Markdown          for chat message rendering
  - Container              for layout

Falls back to a simple readline loop when pi_tui cannot start (non-TTY,
import error, etc.).

Architecture::

    TUI (this file)
      ├── GatewayChat  – WebSocket RPC connection to gateway
      ├── StreamAssembler  – Assembles delta events into display text
      ├── ChatLog component – Conversation history renderer
      └── pi_tui.TUI  – Differential-rendering terminal engine
              ├── pi_tui.Text / Markdown  – message blocks
              └── pi_tui.Editor           – user input
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from .gateway_chat import GatewayChat, GatewayChatEvent
from .stream_assembler import StreamAssembler
from .components.chat_log import ChatLog
from .components.assistant_message import AssistantMessageComponent
from .components.user_message import UserMessageComponent
from .components.tool_execution import ToolExecutionComponent

logger = logging.getLogger(__name__)


class TUIOptions:
    """TUI startup options."""

    def __init__(
        self,
        gateway_port: int = 18789,
        auth_token: str | None = None,
        session_key: str = "agent:main:default",
        agent_id: str = "main",
        verbose: bool = False,
        show_thinking: bool = False,
    ) -> None:
        self.gateway_port = gateway_port
        self.auth_token = auth_token or os.environ.get("OPENCLAW_TOKEN", "")
        self.session_key = session_key
        self.agent_id = agent_id
        self.verbose = verbose
        self.show_thinking = show_thinking


# ─── ANSI helpers ────────────────────────────────────────────────────────────

def _dim(s: str) -> str:
    return f"\x1b[2m{s}\x1b[22m"

def _bold(s: str) -> str:
    return f"\x1b[1m{s}\x1b[22m"

def _cyan(s: str) -> str:
    return f"\x1b[36m{s}\x1b[39m"

def _green(s: str) -> str:
    return f"\x1b[32m{s}\x1b[39m"

def _yellow(s: str) -> str:
    return f"\x1b[33m{s}\x1b[39m"


class TUI:
    """Full-featured terminal UI for openclaw.

    Connects to the gateway WebSocket, renders conversations using pi_tui
    differential rendering, and handles user input via pi_tui.Editor.
    """

    def __init__(self, options: TUIOptions | None = None) -> None:
        self.options = options or TUIOptions()
        self._gateway = GatewayChat(
            port=self.options.gateway_port,
            auth_token=self.options.auth_token,
            on_event=self._on_gateway_event,
        )
        self._assembler = StreamAssembler(verbose=self.options.verbose)
        self._chat_log = ChatLog()
        self._running = False
        self._current_run_id: str | None = None

        # pi_tui components (set up in start())
        self._tui: Any | None = None
        self._editor: Any | None = None
        self._terminal: Any | None = None
        self._width = 80
        self._height = 24

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the TUI."""
        self._running = True

        try:
            import shutil
            cols, rows = shutil.get_terminal_size(fallback=(80, 24))
            self._width = cols
            self._height = rows
            self._chat_log.resize(cols, max(rows - 6, 10))
        except Exception:
            pass

        # Try to connect to gateway
        gateway_connected = False
        try:
            await self._gateway.connect()
            gateway_connected = True
            await self._load_history()
        except Exception as exc:
            logger.warning("Gateway not reachable: %s", exc)

        # Choose TUI mode: pi_tui (TTY) or readline fallback
        if (gateway_connected and sys.stdin.isatty() and sys.stdout.isatty()):
            try:
                await self._run_pi_tui()
                return
            except Exception as exc:
                logger.warning("pi_tui failed (%s), falling back to readline mode", exc)

        # Readline fallback
        await self._run_readline(gateway_connected=gateway_connected)

    # ------------------------------------------------------------------
    # pi_tui based interactive loop
    # ------------------------------------------------------------------

    async def _run_pi_tui(self) -> None:
        """Run the full pi_tui differential-rendering loop."""
        from pi_tui import (
            TUI as PiTUI,
            ProcessTerminal,
            Editor,
            EditorTheme,
            Text,
            Spacer,
            CombinedAutocompleteProvider,
            SlashCommand,
        )

        terminal = ProcessTerminal()
        tui = PiTUI(terminal)
        self._tui = tui
        self._terminal = terminal

        # ── Chat area ─────────────────────────────────────────────────────
        chat_container = _ChatContainer(
            chat_log=self._chat_log,
            width=self._width,
            height=max(self._height - 5, 8),
        )
        tui.add_child(chat_container)

        # ── Separator ─────────────────────────────────────────────────────
        sep = _SeparatorLine(self._width)
        tui.add_child(sep)

        # ── Editor ────────────────────────────────────────────────────────
        slash_commands = [
            SlashCommand(name="exit",   description="Exit the TUI"),
            SlashCommand(name="quit",   description="Exit the TUI"),
            SlashCommand(name="clear",  description="Clear conversation"),
            SlashCommand(name="abort",  description="Abort current run"),
            SlashCommand(name="help",   description="Show help"),
        ]
        autocomplete = CombinedAutocompleteProvider(commands=slash_commands)

        editor_theme = EditorTheme(
            border_color=_dim,
        )
        editor = Editor(tui, editor_theme)
        self._editor = editor
        tui.add_child(editor)

        # ── Status line ───────────────────────────────────────────────────
        status = _StatusLine(
            session_key=self.options.session_key,
            width=self._width,
        )
        tui.add_child(status)

        # ── Submit handler (sync, threadsafe) ────────────────────────────
        main_loop = asyncio.get_running_loop()

        def on_submit_sync(text: str) -> None:
            asyncio.run_coroutine_threadsafe(
                self._handle_submit_pi(text, editor, chat_container, status, tui),
                main_loop,
            )

        editor.on_submit = on_submit_sync
        tui.set_focus(editor)

        # ── Start TUI and run main loop ───────────────────────────────────
        tui.start()
        try:
            while not tui.stopped:
                await asyncio.sleep(0.05)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            if not tui.stopped:
                tui.stop()

        await self._gateway.disconnect()

    async def _handle_submit_pi(
        self,
        text: str,
        editor: Any,
        chat_container: "_ChatContainer",
        status: "_StatusLine",
        tui: Any,
    ) -> None:
        """Handle a submitted message in pi_tui mode."""
        text = text.strip()
        if not text:
            return

        editor.set_text("")
        if hasattr(editor, "add_to_history"):
            editor.add_to_history(text)

        if text.lower() in ("/exit", "/quit"):
            tui.stop()
            return
        if text == "/clear":
            self._chat_log.clear()
            chat_container.invalidate()
            tui.request_render()
            return
        if text == "/abort":
            await self._gateway.disconnect()
            try:
                await self._gateway.connect()
            except Exception:
                pass
            status.set_status("Aborted")
            tui.request_render()
            return
        if text == "/help":
            help_lines = [
                "/exit  – exit",
                "/clear – clear conversation",
                "/abort – abort current run",
            ]
            for line in help_lines:
                self._chat_log.add_message(role="system", content=_dim(line))
            chat_container.invalidate()
            tui.request_render()
            return

        await self._send_message_pi(text, chat_container, status, tui)

    async def _send_message_pi(
        self,
        text: str,
        chat_container: Any,
        status: Any,
        tui: Any,
    ) -> None:
        """Send a message and update pi_tui components."""
        self._chat_log.add_message(role="user", content=text)
        chat_container.invalidate()
        tui.request_render()

        status.set_status(_dim("thinking…"))
        tui.request_render()

        try:
            run_id = await self._gateway.chat_send(
                session_key=self.options.session_key,
                message=text,
            )
            self._current_run_id = run_id

            while True:
                state = self._assembler.get_or_create(run_id)
                if state.is_done:
                    break
                await asyncio.sleep(0.05)
                chat_container.invalidate()
                tui.request_render()

            final_text = self._assembler.get_display_text(run_id)
            self._chat_log.update_last_assistant(final_text)
            chat_container.invalidate()
            status.set_status("")
            tui.request_render()

        except Exception as exc:
            self._chat_log.add_message(role="assistant", content=f"Error: {exc}")
            chat_container.invalidate()
            status.set_status(_yellow("Error"))
            tui.request_render()
        finally:
            self._current_run_id = None

    # ------------------------------------------------------------------
    # Readline fallback loop
    # ------------------------------------------------------------------

    async def _run_readline(self, gateway_connected: bool = False) -> None:
        """Simple readline input loop (non-TTY or pi_tui failure)."""
        self._render_header()

        if not gateway_connected:
            self._print(
                f"{_yellow('⚠ Gateway not running.')}"
                f" Start it with: openclaw gateway start\n"
            )

        while self._running:
            try:
                user_input = await self._readline_async()
                if user_input is None:
                    break
                user_input = user_input.strip()
                if not user_input:
                    continue
                if user_input.lower() in ("/exit", "/quit", "quit", "exit"):
                    break
                if not gateway_connected:
                    self._print("[offline] No gateway connected.\n")
                    continue
                await self._send_message_readline(user_input)
            except (KeyboardInterrupt, EOFError):
                break

        if gateway_connected:
            await self._gateway.disconnect()
        self._print(f"\n{_dim('Goodbye!')}\n")

    async def _send_message_readline(self, text: str) -> None:
        """Send message in readline mode."""
        self._chat_log.add_message(role="user", content=text)
        self._print(f"\n{_bold('You')}: {text}\n")
        self._print(_dim("…\n"))

        try:
            run_id = await self._gateway.chat_send(
                session_key=self.options.session_key,
                message=text,
            )
            self._current_run_id = run_id
            await self._wait_for_run(run_id)

            final_text = self._assembler.get_display_text(run_id)
            self._print(f"\n{_bold('Assistant')}: {final_text}\n")
        except Exception as exc:
            self._print(f"\n{_yellow(f'Error: {exc}')}\n")
        finally:
            self._current_run_id = None

    # ------------------------------------------------------------------
    # History loading
    # ------------------------------------------------------------------

    async def _load_history(self) -> None:
        """Load recent chat history from gateway."""
        try:
            history = await self._gateway.chat_history(self.options.session_key)
            for msg in history[-20:]:
                role = msg.get("role", "user")
                content_blocks = msg.get("content", [])
                if isinstance(content_blocks, str):
                    text = content_blocks
                else:
                    text = " ".join(
                        b.get("text", "") for b in content_blocks
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                if text:
                    self._chat_log.add_message(role=role, content=text)
        except Exception as exc:
            logger.debug("Could not load history: %s", exc)

    # ------------------------------------------------------------------
    # Gateway event handler
    # ------------------------------------------------------------------

    def _on_gateway_event(self, event: GatewayChatEvent) -> None:
        """Handle streaming chat events from the gateway."""
        run_id = event.run_id or self._current_run_id or ""

        if event.type == "started":
            self._assembler.get_or_create(run_id)
            # Pre-add empty assistant message to log
            self._chat_log.add_message(role="assistant", content="")

        elif event.type == "delta":
            text = event.text or ""
            if text:
                self._assembler.on_delta(run_id, text)
                assembled = self._assembler.get_display_text(run_id)
                self._chat_log.update_last_assistant(assembled)

        elif event.type == "final":
            self._assembler.on_final(run_id, event.message)
            final_text = self._assembler.get_display_text(run_id)
            self._chat_log.update_last_assistant(final_text)

        elif event.type == "error":
            self._assembler.on_final(run_id, None, stop_reason="error")

        elif event.type == "aborted":
            self._assembler.on_final(run_id, None, stop_reason="aborted")

        # Trigger re-render in readline fallback (non-pi_tui mode)
        if self._tui is None:
            pass  # readline mode: messages rendered on run completion

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _render_header(self) -> None:
        width = self._width
        self._print("=" * width + "\n")
        title = "OpenClaw"
        pad = (width - len(title)) // 2
        self._print(" " * pad + _bold(title) + "\n")
        self._print(f"{_dim(f'Session: {self.options.session_key}')}\n")
        self._print("=" * width + "\n")
        self._print(f"{_dim('Type /exit to quit | /clear to clear | /abort to cancel')}\n\n")

    async def _wait_for_run(self, run_id: str, timeout: float = 120.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self._assembler.get_or_create(run_id)
            if state.is_done:
                return
            await asyncio.sleep(0.1)

    async def _readline_async(self) -> str | None:
        sys.stdout.write(f"\n{_bold('>')}\u00a0")
        sys.stdout.flush()
        loop = asyncio.get_event_loop()
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            return line.rstrip("\n") if line else None
        except Exception:
            return None

    def _print(self, text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()


# ─── pi_tui Component helpers ─────────────────────────────────────────────────

class _ChatContainer:
    """pi_tui Component that renders ChatLog lines."""

    def __init__(self, chat_log: ChatLog, width: int, height: int) -> None:
        self._log = chat_log
        self._width = width
        self._height = height
        self._cache: list[str] | None = None

    def render(self, width: int) -> list[str]:
        if self._cache is not None:
            return self._cache
        lines = self._log.render()
        # Keep last _height lines
        if len(lines) > self._height:
            lines = lines[-self._height:]
        # Pad to _height
        while len(lines) < self._height:
            lines.append("")
        self._cache = lines
        return lines

    def invalidate(self) -> None:
        self._cache = None

    def handle_input(self, data: str) -> None:
        pass


class _SeparatorLine:
    """Thin separator line."""

    def __init__(self, width: int) -> None:
        self._width = width
        self._line = [_dim("─" * width)]

    def render(self, width: int) -> list[str]:
        return self._line

    def invalidate(self) -> None:
        pass

    def handle_input(self, data: str) -> None:
        pass


class _StatusLine:
    """One-line status/footer bar."""

    def __init__(self, session_key: str, width: int) -> None:
        self._session_key = session_key
        self._width = width
        self._status = ""

    def set_status(self, text: str) -> None:
        self._status = text

    def render(self, width: int) -> list[str]:
        key_part = _dim(f" {self._session_key}")
        status_part = f"  {self._status}" if self._status else ""
        line = key_part + status_part
        return [line]

    def invalidate(self) -> None:
        pass

    def handle_input(self, data: str) -> None:
        pass


async def run_tui(options: TUIOptions | None = None) -> None:
    """Start the TUI. This is the main entry point."""
    tui = TUI(options)
    await tui.start()
