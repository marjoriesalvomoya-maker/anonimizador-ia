"""`python -m anonimizador` abre la ventana; con argumentos, usa la línea de comandos."""
import sys

if len(sys.argv) > 1:
    from .cli import main
    sys.exit(main())
else:
    from .app import main
    main()
