import serial
import serial.tools.list_ports

print("Testing serial ports...")

# List all available ports
ports = list(serial.tools.list_ports.comports())
print(f"Available ports: {[p.device for p in ports]}")

# Test each port
for port_info in ports:
    port = port_info.device
    print(f"\nTesting port: {port}")
    try:
        ser = serial.Serial(
            port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )
        print(f"  ✓ Successfully opened {port}")
        ser.close()
        print(f"  ✓ Successfully closed {port}")
    except Exception as e:
        print(f"  ✗ Error opening {port}: {type(e).__name__}: {str(e)}")

print("\nTest completed.")