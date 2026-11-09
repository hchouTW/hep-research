# g4sim_digi: the digitization of scintillation bins in C++ (g4sim S8, Section 10.5). C++17 standard library only, no Geant4.
# -ffp-contract=off and no -ffast-math: it must agree with core/simulation/digitize.py bit for bit where the C library agrees with Python.
cmake_minimum_required(VERSION 3.16...3.27)
project(g4sim_digi CXX)
add_executable(g4sim_digi g4sim_digi.cc)
target_include_directories(g4sim_digi PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/../g4sim)
target_compile_features(g4sim_digi PRIVATE cxx_std_17)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(g4sim_digi PRIVATE -ffp-contract=off)
endif()
