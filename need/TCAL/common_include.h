#ifndef __TCAL_COMMON_INCLUDE__
#define __TCAL_COMMON_INCLUDE__

#include <unistd.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/time.h>
#include <stdarg.h>
#include <ctype.h>
#include <math.h>

//To avoid warnings, declare these here:
struct sockaddr_nl;
struct nlmsghdr;
struct rtattr;
struct qdisc_util;
typedef uint32_t u_int32_t;
typedef uint8_t u_int8_t;

#endif
