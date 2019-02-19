# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

if("/home/daedalus/Documents/aeron4need/cppbuild/HdrHistogram_c-0.9.8.zip" STREQUAL "")
  message(FATAL_ERROR "LOCAL can't be empty")
endif()

if(NOT EXISTS "/home/daedalus/Documents/aeron4need/cppbuild/HdrHistogram_c-0.9.8.zip")
  message(FATAL_ERROR "File not found: /home/daedalus/Documents/aeron4need/cppbuild/HdrHistogram_c-0.9.8.zip")
endif()

if("MD5" STREQUAL "")
  message(WARNING "File will not be verified since no URL_HASH specified")
  return()
endif()

if("2f38e8fea8484bf51ce895cd22ca9775" STREQUAL "")
  message(FATAL_ERROR "EXPECT_VALUE can't be empty")
endif()

message(STATUS "verifying file...
     file='/home/daedalus/Documents/aeron4need/cppbuild/HdrHistogram_c-0.9.8.zip'")

file("MD5" "/home/daedalus/Documents/aeron4need/cppbuild/HdrHistogram_c-0.9.8.zip" actual_value)

if(NOT "${actual_value}" STREQUAL "2f38e8fea8484bf51ce895cd22ca9775")
  message(FATAL_ERROR "error: MD5 hash of
  /home/daedalus/Documents/aeron4need/cppbuild/HdrHistogram_c-0.9.8.zip
does not match expected value
  expected: '2f38e8fea8484bf51ce895cd22ca9775'
    actual: '${actual_value}'
")
endif()

message(STATUS "verifying file... done")
