#!/usr/bin/env bash

set -ex

# shellcheck disable=SC1091
source /emsdk-portable/emsdk_env.sh &> /dev/null

# emsdk-portable provides a node binary, but we need version 8 to run wasm
# NOTE: Do not forget to sync Node.js version with `emscripten.sh`!
export PATH="/node-v14.17.0-linux-x64/bin:$PATH"

exec "$@"
