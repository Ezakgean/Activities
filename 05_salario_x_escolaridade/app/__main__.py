from __future__ import annotations

import sys


GUI_DEPENDENCIES = {"tkinter", "_tkinter", "customtkinter"}


def main() -> None:
    try:
        from .gui import main as gui_main
    except ModuleNotFoundError as exc:
        if exc.name not in GUI_DEPENDENCIES:
            raise

        from .analise import main as cli_main

        print(
            "Interface grafica indisponivel: dependencia ausente "
            f"({exc.name}). Executando em modo linha de comando.",
            file=sys.stderr,
        )
        print(
            "Para habilitar a GUI no Linux, instale `python3-tk` e as "
            "dependencias Python do projeto.",
            file=sys.stderr,
        )
        cli_main()
        return

    gui_main()


if __name__ == "__main__":
    main()
