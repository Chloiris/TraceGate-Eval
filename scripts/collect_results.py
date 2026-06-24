from __future__ import annotations

import sys

from tracegate.cli import main


if __name__ == "__main__":
    main(["collect-results", *sys.argv[1:]])

