import serial
import time

print("Testing COM6 with minimal parameters...")

# 尝试最简单的连接方式
try:
    # 只指定端口和波特率
    ser = serial.Serial('COM6', 9600)
    print("Successfully connected to COM6!")
    print(f"Port: {ser.port}")
    print(f"Baudrate: {ser.baudrate}")
    print(f"Timeout: {ser.timeout}")
    
    # 尝试读取数据
    print("\nWaiting for data...")
    start_time = time.time()
    
    while time.time() - start_time < 10:
        try:
            data = ser.read(1)
            if data:
                print(f"Received: {data}")
                print(f"Hex: {data.hex()}")
        except Exception as e:
            print(f"Error reading: {e}")
        time.sleep(0.1)
    
    ser.close()
    print("\nTest completed.")
    
except Exception as e:
    print(f"Error: {str(e)}")
    
    # 尝试使用不同的端口名称格式
    print("\nTrying with \\.\\COM6 format...")
    try:
        ser = serial.Serial('//./COM6', 9600)
        print("Successfully connected with \\.\\COM6 format!")
        ser.close()
    except Exception as e2:
        print(f"Error with \\.\\COM6 format: {str(e2)}")

print("\nAll tests completed.")