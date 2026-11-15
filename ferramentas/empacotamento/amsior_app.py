# Amsior — Copyright (c) 2026 Ruan D'Agostin. Todos os direitos reservados.
"""Ponto de entrada do executável (PyInstaller): janela, servidor e processo de cálculo."""

import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()  # o processo de cálculo do executável nasce por spawn
    from amsior.janela import main

    main()
