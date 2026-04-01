import win32com.client

print("Testing COM ports using win32com...")

try:
    wmi = win32com.client.GetObject("winmgmts:")
    ports = wmi.InstancesOf("Win32_SerialPort")
    
    print("Available COM ports:")
    for port in ports:
        print(f"  {port.DeviceID}")
        
    print("\nTest completed successfully.")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()