# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

if("/home/daedalus/Documents/aeron4need/cppbuild/googletest-release-1.8.0.zip" STREQUAL "")
  message(FATAL_ERROR "LOCAL can't be empty")
endif()

if(NOT EXISTS "/home/daedalus/Documents/aeron4need/cppbuild/googletest-release-1.8.0.zip")
  message(FATAL_ERROR "File not found: /home/daedalus/Documents/aeron4need/cppbuild/googletest-release-1.8.0.zip")
endif()

if("MD5" STREQUAL "")
  message(WARNING "File will not be verified since no URL_HASH specified")
  return()
endif()

if("adfafc8512ab65fd3cf7955ef0100ff5" STREQUAL "")
  message(FATAL_ERROR "EXPECT_VALUE can't be empty")
endif()

message(STATUS "verifying file...
     file='/home/daedalus/Documents/aeron4need/cppbuild/googletest-release-1.8.0.zip'")

file("MD5" "/home/daedalus/Documents/aeron4need/cppbuild/googletest-release-1.8.0.zip" actual_value)

if(NOT "${actual_value}" STREQUAL "adfafc8512ab65fd3cf7955ef0100ff5")
  message(FATAL_ERROR "error: MD5 hash of
  /home/daedalus/Documents/aeron4need/cppbuild/googletest-release-1.8.0.zip
does not match expected value
  expected: 'adfafc8512ab65fd3cf7955ef0100ff5'
    actual: '${actual_value}'
")
endif()

message(STATUS "verifying file... done")
