# Native part of adapters/acts-tracking (T07): the data-side driver and probes, against ACTS 48.2.0. Everything that shapes a generator's
# build lives in t07_generators.cmake, the one build file in the generators' hash (t04-values-v4.md section 2.1), so a later driver stage
# can add its sources here without touching a frozen file. Put none in acts_tracking_common.
cmake_minimum_required(VERSION 3.28)
project(acts_tracking CXX)
include(t07_generators.cmake)

add_executable(acts_tracking_driver acts_tracking_driver.cpp kalman_refit.cpp)
target_link_libraries(acts_tracking_driver PRIVATE acts_tracking_common)

# The CAI-T07-3 probe: data side, so it links no generator code.
add_executable(cai_payload_probe cai_payload_probe.cpp payload_geometry.cpp kalman_refit.cpp)
target_link_libraries(cai_payload_probe PRIVATE acts_tracking_common)

# What the refit's start does to a noiseless fit. Data side too.
add_executable(cai_refit_start_probe cai_refit_start_probe.cpp kalman_refit.cpp)
target_link_libraries(cai_refit_start_probe PRIVATE acts_tracking_common)
