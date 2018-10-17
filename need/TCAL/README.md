# TCAL
Traffic controll abstraction layer

##Build instructions

Make sure you have the libutc submodule

You will need the musl-gcc wrapper!

Run make

##How to use
The Makefile produces a libTCAL.so shared library.
Check TCAL.h for the exposed interface.

Be carefull though, as this library cannot be linked against.

Instead it must be loaded dynamically at runtime (with dlopen)

An example is provided in test.c

(the reason for this is because we statically link musl libc inside the .so, 
That is not supposed to be supported, but we need a .so that will work in any environment without compiling)

