#!/bin/sh
set -eu

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ ! -d /root/.hermes ] || [ -z "$(ls -A /root/.hermes 2>/dev/null)" ]; then
  echo "Hermes is not configured yet."
  echo "Run these once:"
  echo "  docker compose run --rm pyagent hermes setup"
  echo "  docker compose run --rm pyagent hermes gateway setup"
  echo "Then start the long-running gateway with:"
  echo "  docker compose up -d"
  exit 1
fi

exec hermes gateway

