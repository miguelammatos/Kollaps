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
CMAKE_SOURCE_DIR = /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build

# Include any dependencies generated for this target.
include test/CMakeFiles/donotoptimize_test.dir/depend.make

# Include the progress variables for this target.
include test/CMakeFiles/donotoptimize_test.dir/progress.make

# Include the compile flags for this target's objects.
include test/CMakeFiles/donotoptimize_test.dir/flags.make

test/CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.o: test/CMakeFiles/donotoptimize_test.dir/flags.make
test/CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.o: /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark/test/donotoptimize_test.cc
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object test/CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.o"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test && /usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.o -c /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark/test/donotoptimize_test.cc

test/CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.i"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark/test/donotoptimize_test.cc > CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.i

test/CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.s"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark/test/donotoptimize_test.cc -o CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.s

# Object files for target donotoptimize_test
donotoptimize_test_OBJECTS = \
"CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.o"

# External object files for target donotoptimize_test
donotoptimize_test_EXTERNAL_OBJECTS =

test/donotoptimize_test: test/CMakeFiles/donotoptimize_test.dir/donotoptimize_test.cc.o
test/donotoptimize_test: test/CMakeFiles/donotoptimize_test.dir/build.make
test/donotoptimize_test: src/libbenchmark.a
test/donotoptimize_test: /usr/lib/librt.so
test/donotoptimize_test: test/CMakeFiles/donotoptimize_test.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Linking CXX executable donotoptimize_test"
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test && $(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/donotoptimize_test.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
test/CMakeFiles/donotoptimize_test.dir/build: test/donotoptimize_test

.PHONY : test/CMakeFiles/donotoptimize_test.dir/build

test/CMakeFiles/donotoptimize_test.dir/clean:
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test && $(CMAKE_COMMAND) -P CMakeFiles/donotoptimize_test.dir/cmake_clean.cmake
.PHONY : test/CMakeFiles/donotoptimize_test.dir/clean

test/CMakeFiles/donotoptimize_test.dir/depend:
	cd /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark/test /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test /home/daedalus/Documents/aeron4need/cppbuild/Release/thirdparty/google_benchmark/src/google_benchmark-build/test/CMakeFiles/donotoptimize_test.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : test/CMakeFiles/donotoptimize_test.dir/depend
