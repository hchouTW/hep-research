# g4sim_run: the g4sim execution program of adapters/geant4 (g4sim plan, Section 8). Shared headers live in ../g4sim.
cmake_minimum_required(VERSION 3.16...3.27)
project(g4sim_run CXX)

if(G4SIM_GEANT4_CONFIG)
  set(G4SIM_GEANT4_MIN_VERSION 11.4)
  include(${CMAKE_CURRENT_SOURCE_DIR}/../g4sim/Geant4FromConfig.cmake)
else()
  find_package(Geant4 11.4 REQUIRED)
  include(${Geant4_USE_FILE})
endif()

add_executable(g4sim_run g4sim_run.cc GeometryCheck.cc
  legacy_element/Run.cc legacy_element/Spec.cc legacy_element/Detector.cc legacy_element/Field.cc legacy_element/Actions.cc legacy_element/EventFile.cc
  legacy_layered/Run.cc legacy_layered/Spec.cc legacy_layered/Detector.cc legacy_layered/Physics.cc legacy_layered/Actions.cc)
set_source_files_properties(legacy_element/Run.cc legacy_element/Spec.cc legacy_element/Detector.cc legacy_element/Field.cc legacy_element/Actions.cc
  legacy_element/EventFile.cc PROPERTIES INCLUDE_DIRECTORIES ${CMAKE_CURRENT_SOURCE_DIR}/legacy_element)
set_source_files_properties(legacy_layered/Run.cc legacy_layered/Spec.cc legacy_layered/Detector.cc legacy_layered/Physics.cc legacy_layered/Actions.cc
  PROPERTIES INCLUDE_DIRECTORIES ${CMAKE_CURRENT_SOURCE_DIR}/legacy_layered)
target_include_directories(g4sim_run PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../g4sim)
target_link_libraries(g4sim_run PRIVATE ${Geant4_LIBRARIES})
target_compile_features(g4sim_run PRIVATE cxx_std_17)
