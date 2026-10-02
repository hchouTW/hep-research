cmake_minimum_required(VERSION 3.16)
project(root_analysis_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ROOT REQUIRED COMPONENTS RIO Tree Hist Graf Graf3d Gpad ROOTDataFrame)

add_executable(analysis rdf_analysis.cpp)
target_include_directories(analysis PRIVATE ${ROOT_INCLUDE_DIRS})
target_link_libraries(analysis PRIVATE ${ROOT_LIBRARIES})
