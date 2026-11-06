"""Entrypoint: runs the sync once and exits (0 on success). Used by the Docker image."""

import sys

from kbsync.job import main

if __name__ == "__main__":
    sys.exit(main())
