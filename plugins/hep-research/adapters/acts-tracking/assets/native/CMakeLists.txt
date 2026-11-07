# Native part of adapters/acts-tracking (T07): the data-side driver and the fixture generator, against ACTS 48.2.0.
# Truth and seed code (t07_truth_file, t07_event_generator, t07_seed_stream, t07_generation_constants.hpp) belongs to the generator
# only: the driver never links it (sheet, Input; A09). The build settings live here, not in a job script, because the fixture
# digests depend on them: Release by default, and no contraction of floating-point expressions.
cmake_minimum_required(VERSION 3.28)
project(acts_tracking CXX)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_STANDARD 23)  # the standard ACTS 48.2.0 requires through Acts::Core
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_compile_options(-ffp-contract=off)
find_package(Acts 48.2.0 CONFIG REQUIRED COMPONENTS Core)

add_library(acts_tracking_common STATIC sha256.cpp t07_data_file.cpp native_product.cpp telescope_geometry.cpp plane_propagation.cpp)
target_include_directories(acts_tracking_common PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(acts_tracking_common PUBLIC Acts::Core)

add_executable(acts_tracking_driver acts_tracking_driver.cpp kalman_refit.cpp)
target_link_libraries(acts_tracking_driver PRIVATE acts_tracking_common)

add_executable(t07_fixture_generator t07_fixture_generator.cpp t07_event_generator.cpp t07_seed_stream.cpp t07_truth_file.cpp)
target_link_libraries(t07_fixture_generator PRIVATE acts_tracking_common)

# t07-telescope-cai/1 is a program of its own, so the two targets above are built as before (Freeze A amendment 1).
add_executable(t07_cai_fixture_generator t07_cai_fixture_generator.cpp t07_cai_event_generator.cpp t07_seed_stream.cpp t07_truth_file.cpp)
target_link_libraries(t07_cai_fixture_generator PRIVATE acts_tracking_common)

# The CAI-T07-3 probe: data side, so it links no generator code.
add_executable(cai_payload_probe cai_payload_probe.cpp payload_geometry.cpp kalman_refit.cpp)
target_link_libraries(cai_payload_probe PRIVATE acts_tracking_common)

# What the refit's start does to a noiseless fit (d1-stage2-report.md, Fix round 1). Data side too.
add_executable(cai_refit_start_probe cai_refit_start_probe.cpp kalman_refit.cpp)
target_link_libraries(cai_refit_start_probe PRIVATE acts_tracking_common)
