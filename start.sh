#!/usr/bin/env bash
# Convenience wrapper around the discord-recall CLI.
#
# Reads configuration from .env (see .env.example). Any arguments are passed
# straight through to the CLI, e.g.:
#   ./start.sh listen
#   ./start.sh digest --server <id> --send
set -e

if [ ! -f .env ]; then
    echo "No .env found. Copy the template first: cp .env.example .env"
    exit 1
fi

exec uv run discord-recall "$@"
