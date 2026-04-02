import serial

print(f"pySerial version: {serial.__version__}")

# 测试是否支持exclusive参数
try:
    # 尝试使用exclusive参数
    ser = serial.Serial(
        port='COM5',  # 假设COM5存在
        baudrate=9600,
        exclusive=False
    )
    print("exclusive参数支持成功")
    ser.close()
except Exception as e:
    print(f"exclusive参数不支持: {str(e)}")

# 测试不使用exclusive参数
try:
    # 不使用exclusive参数
    ser = serial.Serial(
        port='COM5',  # 假设COM5存在
        baudrate=9600
    )
    print("不使用exclusive参数成功")
    ser.close()
except Exception as e:
    print(f"不使用exclusive参数失败: {str(e)}")