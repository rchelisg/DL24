import serial
import serial.tools.list_ports

print("Testing serial port COM6...")

# List all available ports
ports = list(serial.tools.list_ports.comports())
print(f"Available ports: {[p.device for p in ports]}")

# Check if COM6 is in the list
if 'COM6' in [p.device for p in ports]:
    print("COM6 is found in available ports")
    
    # Try different approaches to open COM6
    approaches = [
        "Standard with timeout",
        "No timeout",
        "With write_timeout=0"
    ]
    
    for approach in approaches:
        print(f"\nTrying approach: {approach}")
        try:
            if approach == "Standard with timeout":
                ser = serial.Serial(
                    'COM6',
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=2,
                    write_timeout=2
                )
            elif approach == "No timeout":
                ser = serial.Serial(
                    'COM6',
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=None
                )
            elif approach == "With write_timeout=0":
                ser = serial.Serial(
                    'COM6',
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=2,
                    write_timeout=0
                )
            
            print(f"Successfully opened COM6 with {approach}!")
            ser.close()
            print("Successfully closed COM6")
            break
        except Exception as e:
            print(f"Error opening COM6: {type(e).__name__}: {str(e)}")
else:
    print("COM6 is not found in available ports")