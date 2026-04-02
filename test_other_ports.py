import serial
import time

# 测试COM5, COM9, COM10
ports_to_test = ['COM5', 'COM9', 'COM10']

for port in ports_to_test:
    print(f"\nTesting {port}...")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )
        print(f"Successfully opened {port}!")
        print(f"Port: {ser.port}")
        print(f"Baudrate: {ser.baudrate}")
        
        # 尝试读取数据
        print("Waiting for data...")
        start_time = time.time()
        while time.time() - start_time < 3:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"Received: {data}")
                print(f"Hex: {' '.join([f'{b:02x}' for b in data])}")
            time.sleep(0.1)
        
        ser.close()
        print(f"Closed {port}")
    except Exception as e:
        print(f"Error opening {port}: {str(e)}")

print("\nAll tests completed.")