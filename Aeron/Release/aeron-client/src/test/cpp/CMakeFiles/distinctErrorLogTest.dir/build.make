# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.13

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:


#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:


# Remove some rules from gmake that .SUFFIXES does not remove.
SUFFIXES =

.SUFFIXES: .hpux_make_needs_suffix_list


# Suppress display of executed commands.
$(VERBOSE).SILENT:


# A target that is always out of date.
cmake_force:

.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /usr/local/bin/cmake

# The command to remove a file.
RM = /usr/local/bin/cmake -E remove -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /home/daedalus/Documents/aeron4need

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /home/daedalus/Documents/aeron4need/cppbuild/Release

# Include any dependencies generated for this target.
include aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/depend.make

# Include the progress variables for this target.
include aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/progress.make

# Include the compile flags for this target's objects.
include aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/flags.make

aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.o: aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/flags.make
aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.o: ../../aeron-client/src/test/cpp/concurrent/DistinctErrorLogTest.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/daedalus/Documents/aeron4need/cppbuild/Release/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.o"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp && /usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.o -c /home/daedalus/Documents/aeron4need/aeron-client/src/test/cpp/concurrent/DistinctErrorLogTest.cpp

aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.i"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/daedalus/Documents/aeron4need/aeron-client/src/test/cpp/concurrent/DistinctErrorLogTest.cpp > CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.i

aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.s"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/daedalus/Documents/aeron4need/aeron-client/src/test/cpp/concurrent/DistinctErrorLogTest.cpp -o CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.s

# Object files for target distinctErrorLogTest
distinctErrorLogTest_OBJECTS = \
"CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.o"

# External object files for target distinctErrorLogTest
distinctErrorLogTest_EXTERNAL_OBJECTS =

binaries/distinctErrorLogTest: aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/concurrent/DistinctErrorLogTest.cpp.o
binaries/distinctErrorLogTest: aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/build.make
binaries/distinctErrorLogTest: lib/libaeron_client.a
binaries/distinctErrorLogTest: lib/libaeron_client_test.a
binaries/distinctErrorLogTest: thirdparty/gmock/src/gmock-build/googlemock/./libgmock.a
binaries/distinctErrorLogTest: thirdparty/gmock/src/gmock-build/googlemock/./libgmock_main.a
binaries/distinctErrorLogTest: lib/libaeron_client.a
binaries/distinctErrorLogTest: aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/home/daedalus/Documents/aeron4need/cppbuild/Release/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Linking CXX executable ../../../../binaries/distinctErrorLogTest"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp && $(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/distinctErrorLogTest.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/build: binaries/distinctErrorLogTest

.PHONY : aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/build

aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/clean:
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp && $(CMAKE_COMMAND) -P CMakeFiles/distinctErrorLogTest.dir/cmake_clean.cmake
.PHONY : aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/clean

aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/depend:
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/daedalus/Documents/aeron4need /home/daedalus/Documents/aeron4need/aeron-client/src/test/cpp /home/daedalus/Documents/aeron4need/cppbuild/Release /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp /home/daedalus/Documents/aeron4need/cppbuild/Release/aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : aeron-client/src/test/cpp/CMakeFiles/distinctErrorLogTest.dir/depend
