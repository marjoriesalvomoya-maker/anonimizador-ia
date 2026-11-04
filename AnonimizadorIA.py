"""Punto de entrada para el ejecutable (PyInstaller)."""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if len(sys.argv) > 1 and sys.argv[1] in ("anonimizar", "revertir", "revertir-texto", "instruccion"):
        from anonimizador.cli import main
        sys.exit(main())
    from anonimizador.app import main
    main()
