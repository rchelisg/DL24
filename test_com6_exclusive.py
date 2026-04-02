import serial
import time

print("Testing COM6 with different pySerial parameters...")

# 尝试不同的参数组合
attempts = [
    # 基本参数
    {'port': 'COM6', 'baudrate': 9600, 'exclusive': False},
    # 无超时
    {'port': 'COM6', 'baudrate': 9600, 'timeout': None, 'exclusive': False},
    # 短超时
    {'port': 'COM6', 'baudrate': 9600, 'timeout': 0.1, 'exclusive': False},
    # 标准参数
    {'port': 'COM6', 'baudrate': 9600, 'bytesize': 8, 'parity': 'N', 'stopbits': 1, 'exclusive': False},
    # 尝试使用不同的端口名称格式
    {'port': '//./COM6', 'baudrate': 9600, 'exclusive': False},
]

for i, params in enumerate(attempts):
    print(f"\nAttempt {i+1}: {params}")
    try:
        ser = serial.Serial(**params)
        print("SUCCESS: Connected to COM6!")
        print(f"Port: {ser.port}")
        print(f"Baudrate: {ser.baudrate}")
        
        # 尝试读取数据
        print("Waiting for data...")
        start_time = time.time()
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"Received: {data}")
                print(f"Hex: {' '.join([f'{b:02x}' for b in data])}")
            time.sleep(0.1)
        
        ser.close()
        print("Connection closed.")
        break
    except Exception as e:
        print(f"FAILED: {str(e)}")

print("\nTest completed.")