import serial
import time

print("Testing COM6 with minimal parameters...")

# 尝试不同的参数组合
attempts = [
    {'port': 'COM6', 'baudrate': 9600},
    {'port': 'COM6', 'baudrate': 9600, 'timeout': 0},
    {'port': 'COM6', 'baudrate': 9600, 'timeout': 1},
    {'port': 'COM6', 'baudrate': 9600, 'exclusive': False},
]

for i, params in enumerate(attempts):
    print(f"\nAttempt {i+1}: {params}")
    try:
        ser = serial.Serial(**params)
        print("SUCCESS: Connected to COM6!")
        
        # 尝试读取数据
        print("Waiting for data...")
        for j in range(5):
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"Received: {data}")
                print(f"Hex: {' '.join([f'{b:02x}' for b in data])}")
            time.sleep(1)
        
        ser.close()
        print("Connection closed.")
        break
    except Exception as e:
        print(f"FAILED: {str(e)}")

print("\nTest completed.")