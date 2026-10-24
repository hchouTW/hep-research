# element_sim and simroot: the box-element Geant4 program of adapters/geant4 and its event-file reader (Geant4 program
# B1). Built by geant4_run.py build-sim --program element_sim against a Geant4 installation made by geant4_build.py
# (or any 11.4 installation the user names). Shared headers live in ../g4sim; simroot's source is ../simroot.
cmake_minimum_required(VERSION 3.16...3.27)
project(element_sim CXX)

find_package(Geant4 11.4 REQUIRED)
include(${Geant4_USE_FILE})

add_executable(element_sim element_sim.cc Spec.cc Detector.cc Field.cc Actions.cc EventFile.cc)
target_include_directories(element_sim PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../g4sim)
target_link_libraries(element_sim PRIVATE ${Geant4_LIBRARIES})
target_compile_features(element_sim PRIVATE cxx_std_17)
option(ELEMENT_SIM_TEST_HOOKS "tests only: the UI commands /element_sim/test/..." OFF)
if(ELEMENT_SIM_TEST_HOOKS)
  target_compile_definitions(element_sim PRIVATE ELEMENT_SIM_TEST_HOOKS)
endif()

# simroot links only Geant4's analysis library (and what it needs); it creates no run manager
add_executable(simroot ${CMAKE_CURRENT_SOURCE_DIR}/../simroot/simroot.cc)
target_include_directories(simroot PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../g4sim)
if(TARGET Geant4::G4analysis)
  target_link_libraries(simroot PRIVATE Geant4::G4analysis)
else()
  target_link_libraries(simroot PRIVATE ${Geant4_LIBRARIES})
endif()
target_compile_features(simroot PRIVATE cxx_std_17)
