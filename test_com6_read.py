import serial
import time

print("Testing COM6 connection...")

try:
    # 尝试连接COM6
    ser = serial.Serial(
        port='COM6',
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=2
    )
    
    print("Successfully connected to COM6!")
    print(f"Port: {ser.port}")
    print(f"Baudrate: {ser.baudrate}")
    
    # 尝试读取数据
    print("\nWaiting for data...")
    start_time = time.time()
    
    while time.time() - start_time < 10:  # 等待10秒
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            print(f"Received: {data}")
            print(f"Hex: {' '.join([f'{b:02x}' for b in data])}")
        time.sleep(0.1)
    
    ser.close()
    print("\nTest completed.")
    
except Exception as e:
    print(f"Error: {str(e)}")
    
    # 尝试其他参数
    print("\nTrying alternative parameters...")
    try:
        ser = serial.Serial('COM6', 9600, timeout=0.1)
        print("Successfully connected with alternative parameters!")
        ser.close()
    except Exception as e2:
        print(f"Alternative parameters also failed: {str(e2)}")