# Geant4 through geant4-config instead of find_package(Geant4) (adapters/geant4 0.6.0). For an installation whose
# CMake configuration cannot be used, typically one that ships the Geant4 libraries but not the development files of
# the external packages Geant4Config.cmake looks for (a conda-forge environment without the expat, zlib, freetype or
# Qt development packages). Selected only explicitly, by geant4_run.py build-sim --configure-with geant4-config
# (-DG4SIM_GEANT4_CONFIG=<path>) or geant4_examples.py build --configure-with geant4-config; never a fallback.
# In:  G4SIM_GEANT4_CONFIG (path of geant4-config), G4SIM_GEANT4_MIN_VERSION (optional),
#      G4SIM_GEANT4_CONFIG_GUI (ON: --cflags and --libs; default OFF: --cflags-without-gui and --libs-without-gui).
# Out: the interface target g4sim_geant4 (compile flags, libraries, and a run path to every -L folder, so the program
#      finds the libraries without LD_LIBRARY_PATH or DYLD_LIBRARY_PATH), Geant4_LIBRARIES = g4sim_geant4, Geant4_VERSION.
if(NOT EXISTS "${G4SIM_GEANT4_CONFIG}")
  message(FATAL_ERROR "G4SIM_GEANT4_CONFIG=${G4SIM_GEANT4_CONFIG} does not exist")
endif()
execute_process(COMMAND "${G4SIM_GEANT4_CONFIG}" --version OUTPUT_VARIABLE Geant4_VERSION
                OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE _g4sim_rc)
if(NOT _g4sim_rc EQUAL 0)
  message(FATAL_ERROR "${G4SIM_GEANT4_CONFIG} --version failed (${_g4sim_rc})")
endif()
if(G4SIM_GEANT4_MIN_VERSION AND Geant4_VERSION VERSION_LESS G4SIM_GEANT4_MIN_VERSION)
  message(FATAL_ERROR "Geant4 ${Geant4_VERSION} from ${G4SIM_GEANT4_CONFIG}: ${G4SIM_GEANT4_MIN_VERSION} or later needed")
endif()
if(G4SIM_GEANT4_CONFIG_GUI)
  set(_g4sim_flags --cflags --libs)
else()
  set(_g4sim_flags --cflags-without-gui --libs-without-gui)
endif()
list(GET _g4sim_flags 0 _g4sim_cflag)
list(GET _g4sim_flags 1 _g4sim_lflag)
foreach(_g4sim_kind cflag lflag)
  execute_process(COMMAND "${G4SIM_GEANT4_CONFIG}" ${_g4sim_${_g4sim_kind}} OUTPUT_VARIABLE _g4sim_out
                  OUTPUT_STRIP_TRAILING_WHITESPACE RESULT_VARIABLE _g4sim_rc)
  if(NOT _g4sim_rc EQUAL 0)
    message(FATAL_ERROR "${G4SIM_GEANT4_CONFIG} ${_g4sim_${_g4sim_kind}} failed (${_g4sim_rc})")
  endif()
  separate_arguments(_g4sim_${_g4sim_kind}_list UNIX_COMMAND "${_g4sim_out}")
endforeach()
set(_g4sim_rpath)
foreach(_g4sim_item IN LISTS _g4sim_lflag_list)
  if(_g4sim_item MATCHES "^-L(.+)$")
    list(APPEND _g4sim_rpath "${CMAKE_MATCH_1}")
  endif()
endforeach()
list(REMOVE_DUPLICATES _g4sim_rpath)
add_library(g4sim_geant4 INTERFACE)
target_compile_options(g4sim_geant4 INTERFACE ${_g4sim_cflag_list})
target_link_libraries(g4sim_geant4 INTERFACE ${_g4sim_lflag_list})
foreach(_g4sim_dir IN LISTS _g4sim_rpath)
  target_link_options(g4sim_geant4 INTERFACE "LINKER:-rpath,${_g4sim_dir}")
endforeach()
set(Geant4_LIBRARIES g4sim_geant4)
message(STATUS "Geant4 ${Geant4_VERSION} from ${G4SIM_GEANT4_CONFIG} (${_g4sim_cflag} ${_g4sim_lflag}; run path ${_g4sim_rpath})")
