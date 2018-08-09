cmake_minimum_required(VERSION 3.0)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
project(dynamic_pipeline)

set(CMAKE_CXX_STANDARD 14)

find_package(PkgConfig REQUIRED)
pkg_search_module(GST REQUIRED gstreamer-1.0)
pkg_search_module(GSTMM REQUIRED gstreamermm-1.0)

include_directories(${GSTMM_INCLUDE_DIRS} )
link_directories(${GSTMM_LIBRARY_DIRS} )

add_executable(rtmpsrc_vsink_cc rtmpsrc_vsink.cc)
target_link_libraries(rtmpsrc_vsink_cc ${GSTMM_LIBRARIES})
# target_compile_options(rtmpsrc_vsink_cc PUBLIC ${GSTMM_CFLAGS} ${GSTMM_CFLAGS_OTHER})

add_executable(rtmpsrc_vsink rtmpsrc_vsink.c)
target_link_libraries(rtmpsrc_vsink ${GST_LIBRARIES})
# target_compile_options(rtmpsrc_vsink PUBLIC ${GSTMM_CFLAGS} ${GSTMM_CFLAGS_OTHER})
