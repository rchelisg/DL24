try:
    import win32com.client
    print("win32com is available")
    
    # 尝试使用win32com打开COM6
    try:
        ser = win32com.client.Dispatch("SerialPort.SerialPort")
        ser.Port = "COM6"
        ser.BaudRate = 9600
        ser.Open()
        print("Successfully opened COM6 with win32com")
        ser.Close()
    except Exception as e:
        print(f"Error with win32com: {str(e)}")
        
    # 尝试使用WMI获取端口信息
    try:
        wmi = win32com.client.GetObject("winmgmts:")
        ports = wmi.ExecQuery("SELECT * FROM Win32_SerialPort")
        print("\nAvailable serial ports:")
        for port in ports:
            print(f"{port.DeviceID}: {port.Name}")
    except Exception as e:
        print(f"Error with WMI: {str(e)}")
        
except ImportError:
    print("win32com is not available")
    
print("Test completed.")