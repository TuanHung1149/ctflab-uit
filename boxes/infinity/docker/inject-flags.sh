#!/usr/bin/env bash
# Entrypoint wrapper that injects runtime-generated flags into the container.
# Called at container start; falls back to build-time flags if FLAGS_JSON is unset.
set -euo pipefail

if [ -z "${FLAGS_JSON:-}" ]; then
    echo "FLAGS_JSON not set, using build-time flags"
    exit 0
fi

python3 /root/infinity/docker/inject-flags.py
