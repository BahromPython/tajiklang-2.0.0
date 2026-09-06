"""Нуқтаи оғоз — kept so `py main.py барнома.tj` keeps working.

The real entry point is `tajiklang.cli`, which is also what the installed
`tajik` command runs.
"""

from tajiklang.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
