#!/usr/bin/env python3
"""Entry point for running the Bridge SDK CLI.

This file exists for sandbox execution which runs:
    .venv/bin/python3 main.py config get-dsl
    .venv/bin/python3 main.py run --step <name> ...
"""

from bridge_sdk.cli import main

if __name__ == "__main__":
    main()
