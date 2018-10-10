from ctypes import CDLL, c_float, CFUNCTYPE, c_voidp, c_int, c_ulong, c_uint

if __name__ == '__main__':
    TCAL = CDLL("./libTCAL.so")
    TCAL.init(55)
    TCAL.tearDown()
