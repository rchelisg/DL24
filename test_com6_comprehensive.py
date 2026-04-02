import serial
import time

print("Testing COM6 with different port name formats...")

# 尝试不同的端口名称格式
port_formats = [
    'COM6',
    '//./COM6',
    'COM6:',
    'COM6'
]

# 尝试不同的参数组合
param_sets = [
    # 标准参数
    {'baudrate': 9600, 'bytesize': 8, 'parity': 'N', 'stopbits': 1, 'timeout': 2},
    # 无超时
    {'baudrate': 9600, 'bytesize': 8, 'parity': 'N', 'stopbits': 1},
    # 最小参数
    {'baudrate': 9600},
    # 短超时
    {'baudrate': 9600, 'timeout': 0.1},
    # 不同的字节大小
    {'baudrate': 9600, 'bytesize': 7, 'parity': 'E', 'stopbits': 1},
]

for port_format in port_formats:
    print(f"\nTesting port format: {port_format}")
    for i, params in enumerate(param_sets):
        print(f"  Attempt {i+1}: {params}")
        try:
            ser = serial.Serial(port=port_format, **params)
            print(f"    SUCCESS: Connected to {port_format}!")
            print(f"    Port: {ser.port}")
            print(f"    Baudrate: {ser.baudrate}")
            
            # 尝试读取数据
            print("    Waiting for data...")
            for j in range(3):
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    print(f"    Received: {data}")
                    print(f"    Hex: {' '.join([f'{b:02x}' for b in data])}")
                time.sleep(1)
            
            ser.close()
            print("    Connection closed.")
            break
        except Exception as e:
            print(f"    FAILED: {str(e)}")

print("\nAll tests completed.")