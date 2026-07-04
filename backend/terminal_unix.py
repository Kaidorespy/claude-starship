"""
Unix/Linux/macOS Terminal Handler
Uses pty for full terminal emulation
"""

import asyncio
import os
import pty
import select
import signal
import struct
import fcntl
import termios
from typing import Optional


class UnixTerminal:
    """
    Unix terminal handler using PTY.
    Provides full terminal emulation on Linux/macOS.
    """

    def __init__(self, terminal_id: str):
        self.terminal_id = terminal_id
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.shell = os.environ.get('SHELL', '/bin/bash')
        self.running = False

    async def start(self):
        """Start the terminal process."""
        # Create pseudo-terminal
        self.master_fd, self.slave_fd = pty.openpty()

        # Set non-blocking
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Fork the process
        self.pid = os.fork()

        if self.pid == 0:
            # Child process
            os.close(self.master_fd)

            # Create new session
            os.setsid()

            # Set up slave as controlling terminal
            os.dup2(self.slave_fd, 0)  # stdin
            os.dup2(self.slave_fd, 1)  # stdout
            os.dup2(self.slave_fd, 2)  # stderr

            if self.slave_fd > 2:
                os.close(self.slave_fd)

            # Set environment
            env = os.environ.copy()
            env['TERM'] = 'xterm-256color'
            env['COLORTERM'] = 'truecolor'

            # Execute shell
            os.execvpe(self.shell, [self.shell], env)

        else:
            # Parent process
            os.close(self.slave_fd)
            self.slave_fd = None
            self.running = True

    async def write(self, data: str):
        """Write input to terminal."""
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, data.encode('utf-8'))
            except OSError:
                pass

    async def read(self) -> str:
        """Read output from terminal."""
        if self.master_fd is None:
            return ""

        try:
            # Check if data is available
            ready, _, _ = select.select([self.master_fd], [], [], 0)

            if ready:
                data = os.read(self.master_fd, 4096)
                return data.decode('utf-8', errors='replace')

        except OSError:
            pass

        return ""

    async def resize(self, cols: int, rows: int):
        """Resize terminal window."""
        if self.master_fd is not None:
            try:
                # TIOCSWINSZ - set window size
                winsize = struct.pack('HHHH', rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

                # Send SIGWINCH to notify process of resize
                if self.pid:
                    os.kill(self.pid, signal.SIGWINCH)

            except (OSError, IOError):
                pass

    async def send_signal(self, sig):
        """Send signal to terminal process."""
        if self.pid:
            try:
                os.kill(self.pid, sig)
            except OSError:
                pass

    async def close(self):
        """Close the terminal."""
        self.running = False

        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)

                # Wait for process to exit
                for _ in range(10):
                    pid, status = os.waitpid(self.pid, os.WNOHANG)
                    if pid != 0:
                        break
                    await asyncio.sleep(0.1)
                else:
                    # Force kill if still running
                    os.kill(self.pid, signal.SIGKILL)
                    os.waitpid(self.pid, 0)

            except (OSError, ChildProcessError):
                pass

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass

        self.master_fd = None
        self.pid = None
