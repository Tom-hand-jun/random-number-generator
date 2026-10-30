# -*- coding: utf-8 -*-
"""main.py —— 随机数生成器入口"""

from __future__ import annotations

import sys


def enable_high_dpi():
    """Windows 高 DPI 屏幕下保持字体清晰。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
    except Exception:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    enable_high_dpi()
    from app import RandomApp
    app = RandomApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())