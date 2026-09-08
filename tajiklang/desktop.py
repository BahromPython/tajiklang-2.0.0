"""Windowed TajikLang Studio launcher.

This exists separately from the `tajik` command so the desktop application
never opens a console window. The installer points its shortcuts here.
"""

from tajiklang.ide import main


if __name__ == "__main__":
    raise SystemExit(main())
