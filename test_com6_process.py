import win32com.client

print("Checking processes using COM ports...")

try:
    # 连接到WMI
    wmi = win32com.client.GetObject("winmgmts:")
    
    # 查询所有进程
    processes = wmi.ExecQuery("SELECT * FROM Win32_Process")
    
    print(f"Found {len(processes)} processes")
    
    # 检查每个进程
    for process in processes:
        try:
            # 获取进程的命令行
            cmdline = process.CommandLine
            if cmdline and ("COM6" in cmdline or "com6" in cmdline):
                print(f"Process using COM6: {process.Name} (PID: {process.ProcessId})")
                print(f"Command line: {cmdline}")
        except Exception as e:
            pass
    
    # 查询串口信息
    print("\nSerial ports information:")
    serial_ports = wmi.ExecQuery("SELECT * FROM Win32_SerialPort")
    for port in serial_ports:
        print(f"Port: {port.DeviceID}, Name: {port.Name}, Description: {port.Description}")
        
    # 查询PnP设备
    print("\nPnP devices:")
    pnp_devices = wmi.ExecQuery("SELECT * FROM Win32_PnPEntity WHERE Name LIKE '%COM%'")
    for device in pnp_devices:
        print(f"Device: {device.Name}, Status: {device.Status}")
        
    print("\nCheck completed.")
    
except Exception as e:
    print(f"Error: {e}")
    
print("Test completed.")