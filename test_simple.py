# Test script to check COM port access
import os
import sys

print("Testing COM port access...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# Try to import serial
try:
    import serial
    import serial.tools.list_ports
    print("Successfully imported serial library")
    
    # List all ports
    ports = list(serial.tools.list_ports.comports())
    print(f"Found {len(ports)} ports:")
    for port in ports:
        print(f"  - {port.device}")
        
    # Try to open COM6 specifically
    if 'COM6' in [p.device for p in ports]:
        print("\nTrying to open COM6...")
        try:
            ser = serial.Serial('COM6', 9600, timeout=2)
            print("✓ Successfully opened COM6")
            ser.close()
            print("✓ Successfully closed COM6")
        except Exception as e:
            print(f"✗ Error opening COM6: {type(e).__name__}: {str(e)}")
    else:
        print("COM6 not found in available ports")
        
except Exception as e:
    print(f"Error with serial library: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

print("\nTest completed.")