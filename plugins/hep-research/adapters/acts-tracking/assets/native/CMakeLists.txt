# Native part of adapters/acts-tracking (T07): the data-side driver and probes, against ACTS 48.2.0. Everything that shapes a generator's
# build lives in t07_generators.cmake, the one build file in the generators' hash (t04-values-v4.md section 2.1), so a later driver stage
# can add its sources here without touching a frozen file. Put none in acts_tracking_common.
cmake_minimum_required(VERSION 3.28)
project(acts_tracking CXX)
include(t07_generators.cmake)

# D1 stage 9 (CAI-T07-3): the refit applies an alignment payload through the placement route, so the driver compiles the payload reader and payload_geometry.cpp,
# data side both: no generator, seed or truth code reaches them (tests/adapters/test_acts_tracking.py).
add_executable(acts_tracking_driver acts_tracking_driver.cpp kalman_refit.cpp payload_geometry.cpp alignment_payload.cpp)
target_link_libraries(acts_tracking_driver PRIVATE acts_tracking_common)

# Pattern recognition, recipe reco.track.acts-ckf-planar/1: a program of its own, with no route for a hit set or any other truth-assisted input.
# Data side: it links no generator, seed code or truth reader (section 3.1), which the build job checks on the binary. With --vertex-recipe it also runs
# recipe reco.vertex.acts-amvf/1 on its delivered tracks (track_vertexing.cpp, compiled here and nowhere else).
add_executable(acts_tracking_finder acts_tracking_finder.cpp track_finding.cpp kalman_refit.cpp track_vertexing.cpp)
target_link_libraries(acts_tracking_finder PRIVATE acts_tracking_common)

# Section 7's truth-seeded run, a comparator: scoring side, never reported as finding. Its own program (decisions.md, "T07 stage 5"), so the finder above stays
# truth-free: truth_seeded_search.cpp, the only definition of find_from_starts, is compiled here and nowhere else, and the finder's link line and symbols are read by
# the build job. The steps after the start are track_finding.cpp's, the same source the finder compiles. It links no generator, seed code or truth reader either:
# its truth comes in as a start file the scoring side writes.
add_executable(acts_truth_seeded_run acts_truth_seeded_run.cpp truth_seeded_search.cpp track_finding.cpp kalman_refit.cpp)
target_link_libraries(acts_truth_seeded_run PRIVATE acts_tracking_common)

# Whether a seed's start lies on the helix through its hits, read through the ACTS propagator. Data side too: hand-set tracks, no fixture event.
add_executable(seed_start_probe seed_start_probe.cpp track_finding.cpp kalman_refit.cpp)
target_link_libraries(seed_start_probe PRIVATE acts_tracking_common)

# The CAI-T07-3 probe: data side, so it links no generator code.
add_executable(cai_payload_probe cai_payload_probe.cpp payload_geometry.cpp kalman_refit.cpp)
target_link_libraries(cai_payload_probe PRIVATE acts_tracking_common)

# What the refit's start does to a noiseless fit. Data side too.
add_executable(cai_refit_start_probe cai_refit_start_probe.cpp kalman_refit.cpp)
target_link_libraries(cai_refit_start_probe PRIVATE acts_tracking_common)

# CAI-T07-2 and the R33 cross-checks against ACTS's own unbiased state (D1 stage 8): data side, it links no generator code. The placement route is payload_geometry.cpp's.
add_executable(cai_track_output_check cai_track_output_check.cpp payload_geometry.cpp kalman_refit.cpp)
target_link_libraries(cai_track_output_check PRIVATE acts_tracking_common)
