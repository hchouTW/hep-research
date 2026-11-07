# simreco: digitization and reconstruction of element_sim events (Geant4 program B2.1). C++17 standard library only,
# no Geant4: built by geant4_run.py build-sim --program simreco, by the CI job "simreco", or by hand. Built with
# -ffp-contract=off so that the Box-Muller deviates agree across compilers to a relative 1e-12 (SimHash.hh).
cmake_minimum_required(VERSION 3.16...3.27)
project(simreco CXX)
foreach(program simreco simreco_strip)  # simreco_strip: registered as simreco-strip, stage 5 of the g4sim response pipeline
  add_executable(${program} ${program}.cc)
  target_include_directories(${program} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../g4sim)
  target_compile_features(${program} PRIVATE cxx_std_17)
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${program} PRIVATE -ffp-contract=off)
  endif()
endforeach()
