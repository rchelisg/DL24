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
else:
    print("Successfully opened COM6 with Windows API!")
    
    # 尝试读取数据
    buffer = ctypes.create_string_buffer(1024)
    bytes_read = ctypes.c_ulong()
    
    print("Waiting for data...")
    for i in range(10):
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