import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor

class DisplayWidget(QWidget):
    def paintEvent(self, event):
        # 调用父类的paintEvent
        super().paintEvent(event)
        
        # 获取widget的大小
        width = self.width()
        height = self.height()
        
        # 计算可用绘图区域（留出边距）
        margin = 20
        plot_width = width - 2 * margin
        plot_height = height - 2 * margin
        
        # 创建QPainter对象
        painter = QPainter(self)
        
        # 设置画笔 - 确保使用黑色，线宽为2
        pen = QPen(QColor(0, 0, 0), 2)
        painter.setPen(pen)
        
        # 绘制矩形表示最大绘图区域
        painter.drawRect(margin, margin, plot_width, plot_height)
        
        # 绘制红色原点
        origin_x = margin
        origin_y = margin + plot_height
        painter.setPen(QPen(QColor(255, 0, 0), 4))
        painter.setBrush(QColor(255, 0, 0))
        painter.drawEllipse(origin_x - 3, origin_y - 3, 6, 6)

class TestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # 设置窗口大小
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle("Display Widget Test")
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(main_widget)
        
        # 添加DisplayWidget
        self.display_widget = DisplayWidget()
        self.display_widget.setStyleSheet("background-color: white;")
        main_layout.addWidget(self.display_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestApp()
    window.show()
    sys.exit(app.exec_())