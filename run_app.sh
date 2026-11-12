#!/bin/bash
# Start the app from the repository's own virtual environment, wherever the repository lies.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
source venv/bin/activate
python3 Application.py
