#!/bin/sh
set -eu

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

if [ ! -d /root/.hermes ] || [ -z "$(ls -A /root/.hermes 2>/dev/null)" ]; then
  echo "Hermes is not configured yet."
  echo "Run these once:"
  echo "  docker compose run --rm hermes-agent hermes setup"
  echo "  docker compose run --rm hermes-agent hermes gateway setup"
  echo "Then start everything with:"
  echo "  docker compose up -d"
  exit 1
fi

exec hermes --gateway
