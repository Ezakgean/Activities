from __future__ import annotations

import sys

from app.analise import main as cli_main


if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        cli_main()
    else:
        from app.gui import main as gui_main

        gui_main()
