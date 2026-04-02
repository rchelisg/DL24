import serial
import time
import ctypes

print("Testing COM6 with different approaches...")

# 尝试1: 使用pySerial的默认方法
print("\nAttempt 1: pySerial default")
try:
    ser = serial.Serial('COM6', 9600, timeout=2)
    print("Success!")
    ser.close()
except Exception as e:
    print(f"Failed: {e}")

# 尝试2: 使用pySerial的SerialBase
print("\nAttempt 2: SerialBase")
try:
    from serial.serialutil import SerialBase
    ser = SerialBase()
    ser.port = 'COM6'
    ser.baudrate = 9600
    ser.open()
    print("Success!")
    ser.close()
except Exception as e:
    print(f"Failed: {e}")

# 尝试3: 检查端口是否存在
print("\nAttempt 3: Check if port exists")
try:
    ports = serial.tools.list_ports.comports()
    com6_available = any('COM6' in str(port) for port in ports)
    print(f"COM6 available: {com6_available}")
    for port in ports:
        print(f"Port: {port.device}, Description: {port.description}")
except Exception as e:
    print(f"Failed: {e}")

# 尝试4: 使用不同的超时值
print("\nAttempt 4: Different timeouts")
timeouts = [0, 0.1, 1, 2, 5]
for timeout in timeouts:
    try:
        ser = serial.Serial('COM6', 9600, timeout=timeout)
        print(f"Success with timeout={timeout}!")
        ser.close()
        break
    except Exception as e:
        print(f"Failed with timeout={timeout}: {e}")

print("\nAll attempts completed.")