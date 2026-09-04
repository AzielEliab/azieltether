"""Allow ``python -m azieltether`` to invoke the CLI."""

from azieltether.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
