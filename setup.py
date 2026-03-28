from cx_Freeze import setup, Executable

setup(
    name="DL24",
    version="0.00.00",
    description="DL24 上位机软件",
    executables=[Executable("main.py", base="Win32GUI", target_name="DL24.exe")],
    options={
        "build_exe": {
            "packages": ["PyQt5", "pyqtgraph", "serial", "serial.tools.list_ports"],
            "excludes": ["tkinter"],
            "include_files": [],
        }
    },
)