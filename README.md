# BZFlag Dependencies

This repository contains files used to build third-party dependencies for [BZFlag][1]. On Windows, running `buildWindows.bat` will compile for x86 and x64
by default. On macOS, the `buildmacOS.sh` script will compile for Universal Binary 2, targeting arm64 and x86_64.

## Requirements

* For Windows: Visual Studio with the "Desktop Development with C++" workload
* For macOS: Xcode with command line tools installed
* [CMake][2]

## Technical Information

This uses the ExternalProject feature of CMake to fetch source archives for most of our dependencies. The regex files
used for Windows are shipped with the repository. The download URLs and SHA256 hashes of the source archives are stored
in `sources.cmake`, while the actual build steps are defined in `CMakeLists.txt`. Generally, just updating the URLs and
hashes should be enough, but at times it may be necessary (or beneficial) to update the build steps. For instance, if a
new feature is added to curl that we don't need, we could disable it.

## Roadmap

GitHub Actions are currently being created to automate the workflows of this repository. The goals for now are:
- [ ] Automatically detect updated dependencies and open a Pull Request to merge the updated `sources.cmake`
- [ ] Automatically delete the `update-*` branch when the associated PR is merged or closed
- [ ] Automatically run CI builds on push and PR
- [ ] Automatically build and publish binary assets for Windows and macOS when a tag is created

[1]: https://github.com/BZFlag-Dev/bzflag
[2]: https://cmake.org/download/
