# Simple test to open COM6
import serial

try:
    print("Trying to open COM6...")
    ser = serial.Serial('COM6', 9600, timeout=2)
    print("Successfully opened COM6")
    ser.close()
    print("Successfully closed COM6")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()