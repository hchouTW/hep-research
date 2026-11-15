# What the T07 fixture generators are built from: the build settings, the common library and their targets. In the generators' hash
# (t04-values-v4.md section 2.1). The fixture digests depend on these settings: Release by default, and no contraction of floating-point
# expressions. Truth and seed code (t07_truth_file, t07_event_generator, t07_cai_*, t07_seed_stream, t07_generation_constants.hpp) belongs to
# the generators only: the driver never links it (sheet, Input; A09).
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

add_executable(t07_fixture_generator t07_fixture_generator.cpp t07_event_generator.cpp t07_seed_stream.cpp t07_truth_file.cpp)
target_link_libraries(t07_fixture_generator PRIVATE acts_tracking_common)

# t07-telescope-cai/1 is a program of its own, so the target above builds as before.
add_executable(t07_cai_fixture_generator t07_cai_fixture_generator.cpp t07_cai_event_generator.cpp t07_seed_stream.cpp t07_truth_file.cpp)
target_link_libraries(t07_cai_fixture_generator PRIVATE acts_tracking_common)
