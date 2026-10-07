# CMake and root-config Builds

## Minimal CMake project

```cmake
cmake_minimum_required(VERSION 3.16)
project(root_analysis_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ROOT REQUIRED COMPONENTS RIO Tree Hist Graf Graf3d Gpad ROOTDataFrame)

add_executable(analysis src/analysis.cpp)
target_include_directories(analysis PRIVATE ${ROOT_INCLUDE_DIRS})
target_link_libraries(analysis PRIVATE ${ROOT_LIBRARIES})
```

Build and run:

```bash
cmake -S . -B build
cmake --build build -j
./build/analysis input.root output.root
```

If using ROOT dictionaries, add dictionary generation separately with ROOT's CMake
helpers (`ROOT_GENERATE_DICTIONARY` or `root_generate_dictionary`, depending on the
installed release).

## Scaffolding a new project

`<plugin root>/skills/hep-computing/scripts/new_root_cpp_project.sh <project-name>` generates this `CMakeLists.txt` plus
a `src/` directory as a starting point. `<plugin root>/skills/hep-computing/scripts/check_root_cpp_env.sh` verifies that
`root`, `root-config`, and a compiler are on `PATH` before a build is attempted, and
prints the resolved versions and `root-config --cflags` output.

## Notes

- Match the ROOT components requested in `find_package` to what the code actually
  uses; requesting unused components is harmless but requesting too few produces link
  errors that look like missing symbols rather than a CMake configuration problem (see
  [Debugging](root-debugging.md)).
- Prefer building against the ROOT version already installed in the analysis
  environment rather than assuming API compatibility across releases.
- In a hand-written Makefile, generate dependencies with `-MMD -MP`. Without `-MP`, a `.d` file written before a
  header was moved or deleted still names it, and `make` stops with "No rule to make target"; `-MP` adds an empty
  rule per header (not for the main source, so a `.d` from before a source moved must be deleted once). Headers found
  through `CPLUS_INCLUDE_PATH` count as system headers and are left out of `-MMD` output: list such project headers as
  explicit prerequisites, or reach them with `-I`.
