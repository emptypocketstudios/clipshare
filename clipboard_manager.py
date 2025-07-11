#!/usr/bin/env python3
"""
Clipboard Manager - Handles clipboard operations for different platforms.
"""

import subprocess
import sys


class ClipboardManager:
    """Handles clipboard operations for different platforms."""
    
    @staticmethod
    def get_clipboard() -> str:
        """Return current clipboard contents."""
        if sys.platform.startswith("linux"):
            try:
                result = subprocess.run([
                    "wl-paste",
                    "-n",
                ], capture_output=True, text=True, check=True, timeout=1)
                return result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return ""
        elif sys.platform.startswith("win"):
            try:
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=1
                )
                return result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                return ""
        else:
            raise NotImplementedError("Unsupported platform")

    @staticmethod
    def set_clipboard(text: str) -> None:
        """Set clipboard contents to text."""
        if sys.platform.startswith("linux"):
            try:
                subprocess.run([
                    "wl-copy",
                ], input=text, text=True, check=True, timeout=2)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        elif sys.platform.startswith("win"):
            try:
                subprocess.run(
                    ["powershell", "-command", "Set-Clipboard"],
                    input=text,
                    text=True,
                    check=True,
                    timeout=2
                )
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                pass
        else:
            raise NotImplementedError("Unsupported platform") 