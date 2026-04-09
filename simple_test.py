from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
import sys

class YellowWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Yellow Window with Purple Dot')
        self.setGeometry(100, 100, 400, 300)
        self.setStyleSheet("background-color: #FFFFE0;")
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        try:
            # 绘制紫色点在左下角
            painter.setPen(QPen(QColor(255, 0, 255), 2))  # 亮紫色，线宽2
            painter.setBrush(QColor(255, 0, 255))  # 亮紫色
            # 绘制15x15点
            painter.drawEllipse(0, self.height() - 15, 15, 15)
        finally:
            painter.end()

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
    sys.exit(app.exec_())