#!/bin/bash

pushd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

/Applications/CMake.app/Contents/bin/cmake -S . -B build/macOS-Debug-arm64-x86_64 -DCMAKE_BUILD_TYPE=Debug
/Applications/CMake.app/Contents/bin/cmake -S . -B build/macOS-Release-arm64-x86_64 -DCMAKE_BUILD_TYPE=Release
/Applications/CMake.app/Contents/bin/cmake --build build/macOS-Debug-arm64-x86_64
/Applications/CMake.app/Contents/bin/cmake --build build/macOS-Release-arm64-x86_64

popd

