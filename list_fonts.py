from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase
import sys

# Create QApplication instance
app = QApplication(sys.argv)

# Create QFontDatabase instance
font_db = QFontDatabase()

# Get all available font families
font_families = font_db.families()

# Print the list of font families
print("Available font families:")
for font in font_families:
    print(f"- {font}")

print(f"\nTotal fonts: {len(font_families)}")
