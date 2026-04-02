import ctypes
import time

# 定义Windows API常量
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000

# 加载kernel32.dll
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# 定义CreateFile函数
def create_file(filename, access, mode, security_attrs, creation_disposition, flags, template_file):
    return kernel32.CreateFileW(
        ctypes.c_wchar_p(filename),
        access,
        mode,
        security_attrs,
        creation_disposition,
        flags,
        template_file
    )

# 定义CloseHandle函数
def close_handle(handle):
    return kernel32.CloseHandle(handle)

# 定义ReadFile函数
def read_file(handle, buffer, bytes_to_read, bytes_read, overlapped):
    return kernel32.ReadFile(
        handle,
        buffer,
        bytes_to_read,
        ctypes.byref(bytes_read),
        overlapped
    )

# 定义SetCommState函数
def set_comm_state(handle, dcb):
    return kernel32.SetCommState(handle, ctypes.byref(dcb))

# 定义DCB结构
class DCB(ctypes.Structure):
    _fields_ = [
        ("DCBlength", ctypes.c_uint32),
        ("BaudRate", ctypes.c_uint32),
        ("fBinary", ctypes.c_uint8),
        ("fParity", ctypes.c_uint8),
        ("fOutxCtsFlow", ctypes.c_uint8),
        ("fOutxDsrFlow", ctypes.c_uint8),
        ("fDtrControl", ctypes.c_uint8),
        ("fDsrSensitivity", ctypes.c_uint8),
        ("fTXContinueOnXoff", ctypes.c_uint8),
        ("fOutX", ctypes.c_uint8),
        ("fInX", ctypes.c_uint8),
        ("fErrorChar", ctypes.c_uint8),
        ("fNull", ctypes.c_uint8),
        ("fRtsControl", ctypes.c_uint8),
        ("fAbortOnError", ctypes.c_uint8),
        ("fDummy2", ctypes.c_uint8 * 17),
        ("wReserved", ctypes.c_uint16),
        ("XonLim", ctypes.c_uint16),
        ("XoffLim", ctypes.c_uint16),
        ("ByteSize", ctypes.c_uint8),
        ("Parity", ctypes.c_uint8),
        ("StopBits", ctypes.c_uint8),
        ("XonChar", ctypes.c_uint8),
        ("XoffChar", ctypes.c_uint8),
        ("ErrorChar", ctypes.c_uint8),
        ("EofChar", ctypes.c_uint8),
        ("EvtChar", ctypes.c_uint8),
        ("wReserved1", ctypes.c_uint16),
    ]

print("Testing COM6 with Windows API...")

# 尝试打开COM6
handle = create_file(
    "\\\\.\\COM6",  # 使用\\.\\前缀
    GENERIC_READ | GENERIC_WRITE,
    0,  # 独占访问
    None,
    OPEN_EXISTING,
    0,  # 非重叠
    None
)

if handle == -1:
    error = ctypes.get_last_error()
    print(f"Failed to open COM6, error: {error}")
    print(f"Error description: {ctypes.FormatError(error)}")
else:
    print("Successfully opened COM6 with Windows API!")
    
    # 配置串口
    dcb = DCB()
    dcb.DCBlength = ctypes.sizeof(DCB)
    dcb.BaudRate = 9600
    dcb.ByteSize = 8
    dcb.Parity = 0  # 无校验
    dcb.StopBits = 0  # 1停止位
    
    if set_comm_state(handle, dcb):
        print("Successfully configured COM6")
    else:
        error = ctypes.get_last_error()
        print(f"Failed to configure COM6: {error}")
    
    # 尝试读取数据
    buffer = ctypes.create_string_buffer(1024)
    bytes_read = ctypes.c_ulong()
    
    print("Waiting for data...")
    for i in range(5):
        success = read_file(handle, buffer, 1024, bytes_read, None)
        if success:
            if bytes_read.value > 0:
                data = buffer.raw[:bytes_read.value]
                print(f"Received: {data}")
                print(f"Hex: {' '.join([f'{b:02x}' for b in data])}")
        time.sleep(1)
    
    # 关闭句柄
    close_handle(handle)
    print("Connection closed.")

print("Test completed.")