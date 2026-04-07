import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import datetime

class TestApp:
    def __init__(self):
        print("Initializing test app...")
        self.timer = QTimer()
        self.timer.timeout.connect(self.MainLoop)
        self.timer.start(1000)  # 1秒更新一次
        print("Timer started")
    
    def MainLoop(self):
        current_time = datetime.datetime.now().strftime('%M:%S')
        output = f"MainLoop - {current_time}"
        print(output)
        # 写入文件以验证执行
        with open('mainloop_test.log', 'a') as f:
            f.write(output + '\n')

if __name__ == "__main__":
    print("Starting test...")
    app = QApplication([])
    test_app = TestApp()
    print("Test app created, entering event loop...")
    # 运行5秒后退出
    QTimer.singleShot(5000, app.quit)
    app.exec()
    print("Test completed")