#!/bin/bash
set -euo pipefail

# On any failure, print the actual exit code, but trigger exit code 1 for consistency
trap 'ret=$?; echo "ERROR: Build failed with exit code $ret"; exit 1' ERR

pushd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Find CMake, preferring the CMake.app
CMAKE_BIN="/Applications/CMake.app/Contents/bin/cmake"
if [ ! -x "$CMAKE_BIN" ]; then
  CMAKE_BIN="$(command -v cmake || true)"
  if [ -z "$CMAKE_BIN" ]; then
    echo "ERROR: cmake not found. Install CMake or ensure /Applications/CMake.app is present."
    exit 1
  fi
fi

echo "Using cmake: $CMAKE_BIN"

"$CMAKE_BIN" -S . -B build/macOS-Debug-arm64-x86_64 -DCMAKE_BUILD_TYPE=Debug
"$CMAKE_BIN" -S . -B build/macOS-Release-arm64-x86_64 -DCMAKE_BUILD_TYPE=Release
"$CMAKE_BIN" --build build/macOS-Debug-arm64-x86_64
"$CMAKE_BIN" --build build/macOS-Release-arm64-x86_64

echo "macOS build successful!"
popd

exit 0
