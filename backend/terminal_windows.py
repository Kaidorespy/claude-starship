"""
Windows Terminal Handler
Uses winpty or subprocess for terminal emulation on Windows
"""

import asyncio
import subprocess
import os
from typing import Optional
import sys

# Try to import winpty for better terminal support
try:
    import winpty
    HAS_WINPTY = True
except ImportError:
    HAS_WINPTY = False


class WindowsTerminal:
    """
    Windows terminal handler.
    Uses winpty if available, falls back to subprocess.
    """

    def __init__(self, terminal_id: str):
        self.terminal_id = terminal_id
        self.process: Optional[subprocess.Popen] = None
        self.pty = None
        self.shell = os.environ.get('COMSPEC', 'cmd.exe')
        self.running = False
        self._output_buffer = ""
        self._read_task = None

    async def start(self):
        """Start the terminal process."""
        if HAS_WINPTY:
            await self._start_winpty()
        else:
            await self._start_subprocess()

        self.running = True

    async def _start_winpty(self):
        """Start terminal using winpty for full PTY support."""
        try:
            self.pty = winpty.PtyProcess.spawn(self.shell)
        except Exception as e:
            # Fall back to subprocess if winpty fails
            await self._start_subprocess()

    async def _start_subprocess(self):
        """Start terminal using subprocess (limited but works without winpty)."""
        # Use PowerShell for better experience
        shell = 'powershell.exe'

        self.process = subprocess.Popen(
            [shell, '-NoLogo', '-NoExit', '-Command', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            bufsize=0
        )

        # Start async reader
        self._read_task = asyncio.create_task(self._read_subprocess_output())

    async def _read_subprocess_output(self):
        """Read output from subprocess asynchronously."""
        loop = asyncio.get_event_loop()

        while self.running and self.process and self.process.poll() is None:
            try:
                # Read in a thread to not block
                data = await loop.run_in_executor(
                    None,
                    lambda: self.process.stdout.read(1024) if self.process.stdout else b''
                )
                if data:
                    self._output_buffer += data.decode('utf-8', errors='replace')
            except Exception:
                break

            await asyncio.sleep(0.01)

    async def write(self, data: str):
        """Write input to terminal."""
        if self.pty:
            self.pty.write(data)
        elif self.process and self.process.stdin:
            try:
                self.process.stdin.write(data.encode('utf-8'))
                self.process.stdin.flush()
            except Exception:
                pass

    async def read(self) -> str:
        """Read output from terminal."""
        if self.pty:
            try:
                if self.pty.isalive():
                    # Read available data
                    data = self.pty.read(1024)
                    return data if data else ""
            except Exception:
                return ""

        # For subprocess
        if self._output_buffer:
            output = self._output_buffer
            self._output_buffer = ""
            return output

        return ""

    async def resize(self, cols: int, rows: int):
        """Resize terminal window."""
        if self.pty:
            try:
                self.pty.setwinsize(rows, cols)
            except Exception:
                pass

    async def send_signal(self, sig):
        """Send signal to terminal process."""
        if self.process:
            try:
                if sig == 2:  # SIGINT
                    # On Windows, we can't easily send SIGINT
                    # Instead, write Ctrl+C character
                    await self.write('\x03')
            except Exception:
                pass

    async def close(self):
        """Close the terminal."""
        self.running = False

        if self._read_task:
            self._read_task.cancel()

        if self.pty:
            try:
                self.pty.close()
            except Exception:
                pass

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
