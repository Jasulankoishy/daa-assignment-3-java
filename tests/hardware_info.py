import ctypes
import winreg


def hardware_info():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in
            ('total_physical', 'available_physical', 'total_page', 'available_page',
             'total_virtual', 'available_virtual', 'extended_virtual')]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
        cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    return {'cpu': cpu, 'ram_bytes': status.total_physical}
