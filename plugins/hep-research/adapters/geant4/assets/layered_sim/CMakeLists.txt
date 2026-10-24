# layered_sim: the layered-geometry Geant4 program of adapters/geant4 (WP1 M2). Built by geant4_run.py build-sim
# against a Geant4 installation made by geant4_build.py (or any 11.4 installation the user names). Shared headers
# (MiniJson, SimHash, SimSeed, SimSummary, SimProbe) live in ../g4sim.
cmake_minimum_required(VERSION 3.16...3.27)
project(layered_sim CXX)

find_package(Geant4 11.4 REQUIRED)
include(${Geant4_USE_FILE})

add_executable(layered_sim layered_sim.cc Spec.cc Detector.cc Physics.cc Actions.cc)
target_include_directories(layered_sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../g4sim)
target_link_libraries(layered_sim PRIVATE ${Geant4_LIBRARIES})
target_compile_features(layered_sim PRIVATE cxx_std_17)
option(LAYERED_SIM_TEST_HOOKS "tests only: the UI command /layered_sim/test/probeAfterInitialize" OFF)
if(LAYERED_SIM_TEST_HOOKS)
  target_compile_definitions(layered_sim PRIVATE LAYERED_SIM_TEST_HOOKS)
endif()
