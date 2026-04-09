from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
import sys

class TestWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Test Purple Dot')
        self.setGeometry(100, 100, 400, 300)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        try:
            # 绘制紫色点
            painter.setPen(QPen(QColor(128, 0, 128), 1))  # 紫色
            painter.setBrush(QColor(128, 0, 128))
            # 绘制10x10点
            painter.drawEllipse(50, 250, 10, 10)
        finally:
            painter.end()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = TestWidget()
    widget.show()
    sys.exit(app.exec_())