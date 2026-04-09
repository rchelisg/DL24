import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class YellowWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Yellow Window with Purple Dot')
        self.setGeometry(100, 100, 400, 300)
        self.setStyleSheet("background-color: #FFFFE0;")
        
        # 创建紫色点标签
        self.purple_dot = QLabel(self)
        self.purple_dot.setStyleSheet("background-color: purple; border-radius: 5px;")
        self.purple_dot.setFixedSize(10, 10)
        self.purple_dot.show()
        
    def resizeEvent(self, event):
        # 调用父类的resizeEvent
        super().resizeEvent(event)
        # 定位紫色点标签在黄色区域的左下角
        self.purple_dot.setGeometry(-5, self.height() - 5, 10, 10)
        self.purple_dot.raise_()

class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Main Widget')
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("background-color: white;")
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建黄色窗口
        self.yellow_window = YellowWindow(self)
        layout.addWidget(self.yellow_window)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = MainWidget()
    widget.show()
    sys.exit(app.exec())