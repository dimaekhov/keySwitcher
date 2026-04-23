try:
    from .app import main
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from keyswitcher.app import main


if __name__ == "__main__":
    raise SystemExit(main())
