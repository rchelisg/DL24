import sys
import time
from datetime import datetime
import os
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QGroupBox, QCheckBox,
    QDoubleSpinBox, QGridLayout, QMessageBox, QSizePolicy, QInputDialog,
    QDialog, QFormLayout, QDialogButtonBox, QSpacerItem, QLineEdit,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsView, QGraphicsScene,
    QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QFont, QFontMetrics, QPen, QColor, QPainter
import pyqtgraph as pg
import serial
import serial.tools.list_ports

# 版本号管理
VERSION = "0.0.81"
BUILD_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 计算代码哈希的函数
def calculate_code_hash():
    """计算当前代码的哈希值，用于检测代码变化"""
    hash_obj = hashlib.md5()
    # 读取当前文件的内容
    with open(__file__, 'rb') as f:
        content = f.read()
        hash_obj.update(content)
    return hash_obj.hexdigest()

# 管理版本号的函数
def get_revision():
    """获取当前版本号，如果代码有变化则自动递增"""
    revision_file = "revision.txt"
    current_hash = calculate_code_hash()

    try:
        # 尝试读取当前版本号和哈希值
        with open(revision_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                stored_revision = lines[0].strip()
                stored_hash = lines[1].strip()

                # 如果哈希值相同，返回当前版本号
                if stored_hash == current_hash:
                    return stored_revision
                # 如果哈希值不同，递增版本号
                else: 
                    major, minor, patch = map(int, stored_revision.split('.')) 
                    patch += 1
                    new_revision = f"{major}.{minor}.{patch:02d}"
            else:
                # 文件格式不正确，使用默认版本号
                new_revision = "0.0.00"
    except FileNotFoundError:
        # 文件不存在，使用默认版本号
        new_revision = "0.0.00"

    # 保存新的版本号和哈希值
    with open(revision_file, 'w') as f:
        f.write(f"{new_revision}\n{current_hash}\n")

    return new_revision

# 获取当前版本号
REVISION = get_revision()

# Test comment to trigger revision increment - updated again

class AxisRangeDialog(QDialog):
    def __init__(self, axis_type, current_min, current_max, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"设置{axis_type}轴范围")
        self.setModal(True)
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # 最大值输入
        self.max_input = QDoubleSpinBox()
        self.max_input.setRange(current_min + 0.1, 1000)
        self.max_input.setValue(current_max)
        self.max_input.setDecimals(1)
        form_layout.addRow("最大值:", self.max_input)
        
        # 最小值输入
        self.min_input = QDoubleSpinBox()
        self.min_input.setRange(0, current_max - 0.1)
        self.min_input.setValue(current_min)
        self.min_input.setDecimals(1)
        form_layout.addRow("最小值:", self.min_input)
        
        # 信号连接，确保最小值小于最大值
        self.min_input.valueChanged.connect(self.update_max_range)
        self.max_input.valueChanged.connect(self.update_min_range)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def update_max_range(self):
        min_val = self.min_input.value()
        self.max_input.setMinimum(min_val + 0.1)
    
    def update_min_range(self):
        max_val = self.max_input.value()
        self.min_input.setMaximum(max_val - 0.1)
    
    def get_values(self):
        return self.min_input.value(), self.max_input.value()

class OverlayWidget(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        # 设置透明背景
        self.setStyleSheet("background-color: transparent;")
        self.plot_window = None
        self.main_window = main_window
        
        # 添加Zone1标签
        self.zone1_label = QLabel("实时放电曲线", self)
        self.zone1_label.setAlignment(Qt.AlignCenter)
        self.zone1_label.setStyleSheet("font-size: 32px; color: black;")
        self.zone1_label.setFixedSize(600, 60)  # 增加宽度以容纳20个中文字符
        self.zone1_label.setCursor(Qt.PointingHandCursor)
        self.zone1_label.mouseDoubleClickEvent = self.on_label_double_click
    
    def set_plot_window(self, plot_window):
        self.plot_window = plot_window
    
    def set_main_window(self, main_window):
        self.main_window = main_window
    
    def on_label_double_click(self, event):
        # 打开输入对话框让用户编辑标签内容
        current_text = self.zone1_label.text()
        
        # 创建自定义输入对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle("编辑标签")
        dialog.setLabelText("请输入新的标签内容:")
        dialog.setTextValue(current_text)
        dialog.setTextEchoMode(QLineEdit.Normal)
        dialog.resize(400, 150)  # 调整对话框大小以容纳长文本
        
        # 设置对话框样式
        dialog.setStyleSheet("QInputDialog { background-color: white; } QLabel { color: black; } QLineEdit { background-color: white; color: black; border: 1px solid gray; }")
        
        if dialog.exec_() == QDialog.Accepted:
            new_text = dialog.textValue()
            if new_text:
                # 限制输入长度：最多20个中文字符或40个英文字母
                if len(new_text) <= 20:
                    self.zone1_label.setText(new_text)
                else:
                    # 截断到20个字符
                    self.zone1_label.setText(new_text[:20])
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 定位标签到Zone1的中心，靠近顶部
        if self.parent():
            parent_width = self.parent().width()
            label_x = (parent_width - self.zone1_label.width()) // 2
            label_y = 20  # 距离顶部20像素（增加以适应更大的标签）
            self.zone1_label.move(label_x, label_y)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.plot_window:
            return
        
        # 获取PlotWindow的位置和大小
        plot_geometry = self.plot_window.geometry()
        x, y, width, height = plot_geometry.x(), plot_geometry.y(), plot_geometry.width(), plot_geometry.height()
        
        # 创建QPainter对象
        painter = QPainter(self)
        try:
            # 计算可绘制区域的位置（与原浅灰色框相同的区域）
            # 考虑布局的边距：left=0, top=10, right=30, bottom=0
            plottable_x = x + 0  # 左侧边距
            plottable_y = y + 10  # 顶部边距
            plottable_width = width - 30  # 宽度减去右侧边距
            plottable_height = height - 10  # 高度减去顶部边距
            
            # 绘制紫色点在左上角（原浅灰色框的左边缘和上边缘的交点）
            # 点的大小与原浅灰色框的线宽相同，居中绘制
            painter.setPen(QPen(QColor(128, 0, 128), 1))
            painter.setBrush(QColor(128, 0, 128))
            # 调整位置使4x4点居中在角落
            painter.drawEllipse(int(plottable_x) - 2, int(plottable_y) - 2, 4, 4)
            
            # 绘制黑色点在左下角（原浅灰色框的左边缘和下边缘的交点）
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(QColor(0, 0, 0))
            # 调整位置使4x4点居中在角落
            painter.drawEllipse(int(plottable_x) - 2, int(plottable_y + plottable_height) - 2, 4, 4)
            
            # 绘制粉色点在右下角（原浅灰色框的右边缘和下边缘的交点）
            painter.setPen(QPen(QColor(255, 192, 203), 1))
            painter.setBrush(QColor(255, 192, 203))
            # 调整位置使4x4点居中在角落
            painter.drawEllipse(int(plottable_x + plottable_width) - 2, int(plottable_y + plottable_height) - 2, 4, 4)
            
            # 绘制深粉色点在右上角（原浅灰色框的右边缘和上边缘的交点）
            painter.setPen(QPen(QColor(255, 105, 180), 1))
            painter.setBrush(QColor(255, 105, 180))
            # 调整位置使4x4点居中在角落
            painter.drawEllipse(int(plottable_x + plottable_width) - 2, int(plottable_y) - 2, 4, 4)
            
            # 绘制浅灰色线连接紫色点和深粉色点
            painter.setPen(QPen(QColor(200, 200, 200), 1))  # 浅灰色，线宽1，更明显
            # 绘制连接线，直接使用坐标
            painter.drawLine(int(plottable_x), int(plottable_y), int(plottable_x + plottable_width), int(plottable_y))
            
            # 设置虚线笔用于网格线，使用自定义虚线模式使其更稀疏
            dashed_pen = QPen(QColor(200, 200, 200), 1)
            # 设置自定义虚线模式：4像素实线，8像素空白（更稀疏的虚线）
            dashed_pen.setDashPattern([4, 8])
            painter.setPen(dashed_pen)
            
            # 绘制水平网格线（与垂直刻度标记对齐）
            if self.main_window:
                # 绘制水平网格线（与垂直刻度标记对齐）
                vertical_scales = [self.main_window.scale_line, self.main_window.scale_line2, self.main_window.scale_line3]
                for scale in vertical_scales:
                    if hasattr(scale, 'orientation') and scale.orientation == "vertical":
                        num_markers = scale.num_markers
                        # 每个标记都绘制网格线
                        for i in range(num_markers):
                            # 计算y位置（从顶部到底部）
                            y = plottable_y + (i / (num_markers - 1)) * plottable_height
                            # 绘制水平网格线
                            painter.drawLine(int(plottable_x), int(y), int(plottable_x + plottable_width), int(y))
                
                # 绘制垂直网格线（与水平刻度标记对齐）
                horizontal_scale = self.main_window.scale_line4
                if hasattr(horizontal_scale, 'orientation') and horizontal_scale.orientation == "horizontal":
                    num_markers = horizontal_scale.num_markers
                    # 每个标记都绘制网格线
                    for i in range(num_markers):
                        # 计算x位置（从左侧到右侧）
                        x = plottable_x + (i / (num_markers - 1)) * plottable_width
                        # 绘制垂直网格线
                        painter.drawLine(int(x), int(plottable_y), int(x), int(plottable_y + plottable_height))
        finally:
            painter.end()
    


class ScaleLineWidget(QWidget):
    # 定义信号，当刻度线被双击时发射
    from PyQt5.QtCore import pyqtSignal
    doubleClicked = pyqtSignal()
    
    def __init__(self, parent=None, height=300, scale_width=300, num_markers=6, min_value=0, max_value=200, color=QColor(255, 165, 0), label="(W)", marker_direction="right", alignment="left", orientation="vertical"):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        # 确保widget接收鼠标事件
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        if orientation == "vertical":
            self.setMinimumSize(150, height)
        else:
            self.setMinimumSize(scale_width, 100)
        self.height = height
        self.scale_width = scale_width
        self.num_markers = num_markers
        self.min_value = min_value
        self.max_value = max_value
        self.line_width = 3  # 刻度线和标记的宽度
        self.marker_length = 20  # 标记长度
        self.font = QFont("Arial Narrow", 9)  # 更改为Arial Narrow，字体大小改为9
        self.padding = 50  # 边距，为粗体标签留出空间
        self.color = color  # 刻度线颜色
        self.label = label  # 刻度线标签
        self.marker_direction = marker_direction  # 标记方向："left", "right", "up", "down"
        self.alignment = alignment  # 数字对齐方式："left" 或 "right"
        self.orientation = orientation  # 方向："vertical" 或 "horizontal"
    
    def mouseDoubleClickEvent(self, event):
        # 当双击时直接打开对话框
        from PyQt5.QtWidgets import QDialog
        dialog = ScaleRangeDialog(self.min_value, self.max_value, self.parent())
        if dialog.exec_() == QDialog.Accepted:
            new_min, new_max = dialog.get_values()
            if new_min is not None and new_max is not None:
                # 更新刻度范围
                self.set_range(new_min, new_max)
                # 强制刷新显示
                self.update()
        super().mouseDoubleClickEvent(event)
    
    def set_height(self, height):
        """设置刻度线高度"""
        self.height = height
        self.setMinimumSize(150, int(height + 2 * self.padding))
        self.update()
    
    def set_width(self, scale_width):
        """设置刻度线宽度"""
        self.scale_width = scale_width
        # 增加额外宽度以容纳右侧标签
        self.setMinimumSize(int(scale_width + 2 * self.padding + 150), 100)
        self.update()
    
    def set_range(self, min_value, max_value):
        """设置刻度范围"""
        self.min_value = min_value
        self.max_value = max_value
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        # 创建QPainter对象
        painter = QPainter(self)
        try:
            if self.orientation == "vertical":
                # 计算实际刻度线高度（减去上下边距）
                actual_height = int(self.height)
                start_y = self.padding
                end_y = start_y + actual_height
                
                # 绘制垂直刻度线
                painter.setPen(QPen(self.color, self.line_width))
                # 对于左指向标记，将刻度线向右移动，为左侧文本留出空间
                if self.marker_direction == "left":
                    scale_line_x = self.width() - 20  # 刻度线靠近右侧
                else:
                    scale_line_x = 20  # 刻度线靠近左侧
                painter.drawLine(scale_line_x, start_y, scale_line_x, end_y)
                
                # 绘制圆点在刻度线的顶部和底部，使用与刻度线相同的颜色和大小
                painter.setPen(QPen(self.color, 2))
                painter.setBrush(self.color)
                # 顶部圆点，大小与刻度线宽度相同，精确居中在刻度线起点
                painter.drawEllipse(int(scale_line_x - self.line_width/2), int(start_y - self.line_width/2), self.line_width, self.line_width)
                # 底部圆点，大小与刻度线宽度相同，精确居中在刻度线终点
                painter.drawEllipse(int(scale_line_x - self.line_width/2), int(end_y - self.line_width/2), self.line_width, self.line_width)
                
                # 在刻度线顶部添加标签
                # 创建粗体字体
                bold_font = QFont(self.font)
                bold_font.setBold(True)
                painter.setFont(bold_font)
                painter.setPen(QPen(self.color, 1))  # 使用与刻度线相同的颜色
                # 对于左指向标记，调整标签位置
                if self.marker_direction == "left":
                    painter.drawText(scale_line_x - 20, start_y - 25, self.label)  # 向上移动一行，确保标签完全可见
                else:
                    painter.drawText(scale_line_x - 10, start_y - 25, self.label)  # 向上移动一行，确保标签完全可见
                
                # 绘制标记和数字
                painter.setFont(self.font)
                for i in range(self.num_markers):
                    # 计算标记位置，0在底部，5在顶部
                    marker_y = end_y - (i * actual_height / (self.num_markers - 1))
                    
                    # 绘制标记
                    painter.setPen(QPen(self.color, self.line_width))  # 使用指定颜色，线宽3
                    if self.marker_direction == "right":
                        # 绘制标记指向右侧
                        painter.drawLine(scale_line_x, int(marker_y), scale_line_x + self.marker_length, int(marker_y))
                        # 计算文本位置 - 对于右指向标记，文本应该在标记右侧
                        text_x = scale_line_x + self.marker_length + 5
                    else:
                        # 绘制标记指向左侧
                        painter.drawLine(scale_line_x, int(marker_y), scale_line_x - self.marker_length, int(marker_y))
                        # 计算文本位置 - 对于左指向标记，文本应该在标记左侧，留出5px空间
                        text_x = scale_line_x - self.marker_length - 5 - 80  # 5px空间，与橙色刻度线保持一致
                    
                    # 计算标记值
                    value = self.min_value + (i * (self.max_value - self.min_value) / (self.num_markers - 1))
                    
                    # 格式化数字为xxx.x格式，显示前导零，根据对齐方式格式化
                    if self.alignment == "right":
                        formatted_value = f"{value:>5.1f}"
                        align_flag = Qt.AlignRight
                    else:
                        formatted_value = f"{value:<5.1f}"
                        align_flag = Qt.AlignLeft
                    # 绘制数字
                    painter.setPen(QPen(QColor(64, 64, 64), 1))  # 深灰色，线宽1
                    # 创建文本区域，增加高度和宽度以显示完整数字
                    # 固定文本矩形高度，确保所有数字对齐一致
                    text_rect = QRect(text_x, int(marker_y) - 12, 80, 24)  # 固定尺寸
                    painter.drawText(text_rect, align_flag | Qt.AlignVCenter, formatted_value)
            else:  # 水平刻度线
                # 计算实际刻度线宽度（减去左右边距）
                actual_width = int(self.scale_width)
                start_x = self.padding
                end_x = start_x + actual_width
                
                # 绘制水平刻度线
                painter.setPen(QPen(self.color, self.line_width))
                # 对于下指向标记，将刻度线上移，为下方文本留出空间
                if self.marker_direction == "down":
                    scale_line_y = 50  # 刻度线上移
                else:
                    scale_line_y = 50  # 刻度线居中
                painter.drawLine(start_x, scale_line_y, end_x, scale_line_y)
                
                # 绘制圆点在刻度线的左侧和右侧，使用与刻度线相同的颜色和大小
                painter.setPen(QPen(self.color, 2))
                painter.setBrush(self.color)
                # 左侧圆点，大小与刻度线宽度相同
                painter.drawEllipse(int(start_x - self.line_width/2), int(scale_line_y - self.line_width/2), self.line_width, self.line_width)
                # 右侧圆点，大小与刻度线宽度相同
                painter.drawEllipse(int(end_x - self.line_width/2), int(scale_line_y - self.line_width/2), self.line_width, self.line_width)
                
                # 在刻度线右侧添加标签
                # 创建粗体字体
                bold_font = QFont(self.font)
                bold_font.setBold(True)
                painter.setFont(bold_font)
                painter.setPen(QPen(self.color, 1))  # 使用与刻度线相同的颜色
                # 创建文本区域，位于刻度线右侧，垂直居中，向下移动1.5行，向右移动2字母
                # 增加宽度以确保完整显示标签
                label_rect = QRect(end_x + 30, scale_line_y + 24, 150, 24)  # 150px width, 24px height，向下移动1.5行，向右移动2字母
                painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, self.label)
                
                # 绘制标记和数字
                painter.setFont(self.font)
                for i in range(self.num_markers):
                    # 计算标记位置，0在左侧，5在右侧
                    marker_x = start_x + (i * actual_width / (self.num_markers - 1))
                    
                    # 绘制标记
                    painter.setPen(QPen(self.color, self.line_width))  # 使用指定颜色，线宽3
                    if self.marker_direction == "up":
                        # 绘制标记指向上方
                        painter.drawLine(int(marker_x), scale_line_y, int(marker_x), scale_line_y - self.marker_length)
                        # 计算文本位置 - 对于上指向标记，文本垂直居中对齐标记
                        text_y = scale_line_y - self.marker_length - 12  # 12是文本高度的一半（24/2）
                    else:
                        # 绘制标记指向下方
                        painter.drawLine(int(marker_x), scale_line_y, int(marker_x), scale_line_y + self.marker_length)
                        # 计算文本位置 - 对于下指向标记，文本直接位于标记下方
                        text_y = scale_line_y + self.marker_length + 5  # 5px spacing below marker
                    
                    # 计算标记值
                    value = self.min_value + (i * (self.max_value - self.min_value) / (self.num_markers - 1))
                    
                    # 格式化数字为xxx.x格式，显示前导零，水平居中对齐
                    formatted_value = f"{value:^5.1f}"
                    align_flag = Qt.AlignCenter
                    # 绘制数字
                    painter.setPen(QPen(QColor(64, 64, 64), 1))  # 深灰色，线宽1
                    # 创建文本区域，增加高度和宽度以显示完整数字
                    # 固定文本矩形宽度，确保所有数字对齐一致
                    text_rect = QRect(int(marker_x) - 40, int(text_y), 80, 24)  # 固定尺寸
                    painter.drawText(text_rect, align_flag | Qt.AlignVCenter, formatted_value)
        finally:
            painter.end()

class ScaleRangeDialog(QDialog):
    def __init__(self, current_min, current_max, parent=None):
        from PyQt5.QtWidgets import QLineEdit, QLabel, QVBoxLayout, QGridLayout, QPushButton, QHBoxLayout
        super().__init__(parent)
        self.setWindowTitle("设置刻度范围")
        
        layout = QVBoxLayout(self)
        
        # 创建输入控件
        grid_layout = QGridLayout()
        
        grid_layout.addWidget(QLabel("最大值:"), 0, 0)
        self.max_edit = QLineEdit(str(current_max))
        grid_layout.addWidget(self.max_edit, 0, 1)
        
        grid_layout.addWidget(QLabel("最小值:"), 1, 0)
        self.min_edit = QLineEdit(str(current_min))
        grid_layout.addWidget(self.min_edit, 1, 1)
        
        layout.addLayout(grid_layout)
        
        # 创建按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
    
    def get_values(self):
        try:
            min_val = float(self.min_edit.text())
            max_val = float(self.max_edit.text())
            return min_val, max_val
        except ValueError:
            return None, None

class PlotWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置背景颜色为非常浅的黄色
        self.setStyleSheet("background-color: #FFFFE0;")
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 30, 0)  # 增加右侧和顶部边距以容纳线条
        
        # 创建PlotWidget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        
        # 隐藏默认坐标轴
        self.plot_widget.hideAxis('left')
        self.plot_widget.hideAxis('bottom')
        
        # 设置背景颜色
        self.plot_widget.setBackground('#FFFFE0')
        
        # 创建4条曲线，每条曲线使用不同的颜色
        self.curves = []
        colors = ['r', 'g', 'b', 'y']
        for i in range(4):
            # 创建曲线
            curve = self.plot_widget.plot(pen=colors[i])
            self.curves.append(curve)
    

    


class DisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置背景颜色为白色
        self.setStyleSheet("background-color: white;")
        self.info_text = ""
        
        # 创建PlotWindow
        self.plot_window = PlotWindow(self)
        
        # 创建覆盖层widget
        self.overlay = OverlayWidget(self)
        self.overlay.set_plot_window(self.plot_window)
        self.overlay.show()
        self.overlay.raise_()
    
    def paintEvent(self, event):
        # 调用父类的paintEvent
        super().paintEvent(event)
        
        # 获取widget的大小
        width = self.width()
        height = self.height()
        
        # 创建QPainter对象
        painter = QPainter(self)
        try:
            # 显式填充背景为白色
            painter.fillRect(0, 0, width, height, QColor(255, 255, 255))
            
            # 绘制红色原点
            origin_x = 0
            origin_y = height
            painter.setPen(QPen(QColor(255, 0, 0), 4))
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(origin_x - 3, origin_y - 3, 6, 6)
        finally:
            painter.end()
        
        # 计算PlotWindow的位置和大小
        left_space = width / 8  # 增加25%
        right_space = (width / 16) * 0.7  # 减少30%
        bottom_space = height / 10  # 保持不变
        top_space = height * 3 / 40  # 增加50%
        
        plot_width = width - left_space - right_space
        plot_height = height - top_space - bottom_space
        
        # 设置PlotWindow的位置和大小
        self.plot_window.setGeometry(
            int(left_space),
            int(top_space),
            int(plot_width),
            int(plot_height)
        )
        # 设置覆盖层的大小和位置，使其覆盖整个DisplayWidget
        self.overlay.setGeometry(0, 0, width, height)
        # 强制PlotWindow和覆盖层更新
        self.plot_window.update()
        self.overlay.update()
    
    def update_info(self, info_text):
        # 更新标签内容
        self.info_text = info_text
        self.update()

class DL24App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_timer()
        self.is_connected = False
        self.serial_port = None
        self.mode = 0  # 0: CC, 1: CV, 2: CP
        self.is_parameter_editable = False
        self.serial_buffer = bytearray()  # 用于存储串口接收到的数据
        
    def init_ui(self):
        # 初始化数据结构（在方法开始时就初始化，确保在任何使用之前都已存在）
        self.data = {
            'time': [],
            'I': [],
            'V': [],
            'P': [],
            'Vcut': []
        }
        self.curves = {}
        self.axis_ranges = {
            'V': {'min': 2, 'max': 5},
            'I': {'min': 0, 'max': 10},
            'P': {'min': 0, 'max': 50},
            'time': {'min': 0, 'max': 300}
        }
        self.Vset = 0.00  # 初始化截止电压变量
        self.Iset = 0.00  # 初始化负载电流变量
        
        # 设置窗口大小为屏幕的80%
        screen = QApplication.desktop().screenGeometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.8)
        self.setGeometry(100, 100, width, height)
        self.setWindowTitle("DL24 上位机软件")
        
        # 设置全局字体
        self.font = QFont("Microsoft YaHei", 10)
        QApplication.setFont(self.font)
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 1. 显示widget (Zone 1)
        self.display_widget = DisplayWidget(main_widget)
        self.display_widget.setStyleSheet("background-color: white;")
        # 设置OverlayWidget的main_window引用
        self.display_widget.overlay.set_main_window(self)
        
        # 2. 显示widget (Zone 2)
        self.zone2_widget = QWidget(main_widget)
        self.zone2_widget.setStyleSheet("background-color: white; border: 1px solid purple;")
        
        # 创建Zone2的布局为垂直布局
        self.zone2_layout = QVBoxLayout(self.zone2_widget)
        # 设置布局边距
        self.zone2_layout.setContentsMargins(0, 20, 0, 0)  # 顶部边距20px
        # 设置垂直间距为0
        self.zone2_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone2_layout.setAlignment(Qt.AlignTop)
        
        # 设置初始字体
        font = QFont("Courier New", 14, QFont.Light)  # 使用更薄的等宽字体
        
        # 3. 显示 widget (Zone 3)
        self.zone3_widget = QWidget(main_widget)
        self.zone3_widget.setStyleSheet("background-color: white;")
        # 设置 Zone3 的字体大小为原来的 1.875 倍 (1.5 * 1.25)
        zone3_font = QFont("Courier New", 26, QFont.Light)
        self.zone3_widget.setFont(zone3_font)
        
        # 创建Zone3的布局为垂直布局
        self.zone3_layout = QVBoxLayout(self.zone3_widget)
        # 设置布局边距
        self.zone3_layout.setContentsMargins(0, 20, 0, 20)  # 顶部和底部边距都是 20px
        # 设置垂直间距为0
        self.zone3_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone3_layout.setAlignment(Qt.AlignTop)
        
        # 添加 Zone3 标题
        self.zone3_title = QLabel('<span style="color: grey;">&nbsp;&nbsp;&nbsp;参数设置</span>')
        self.zone3_title.setAlignment(Qt.AlignLeft)  # 左对齐
        self.zone3_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 使用 Expanding 以填充水平空间
        self.zone3_title.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")  # 移除内边距和外边距
        self.zone3_layout.addWidget(self.zone3_title)
        
        # 添加一行间距
        font_metrics = QFontMetrics(self.zone3_title.font())
        line_height = font_metrics.height()
        zone3_spacer = QSpacerItem(10, line_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone3_layout.addItem(zone3_spacer)
        
        # 添加 Mode 标签和下拉菜单
        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(5)
        
        # 下拉菜单
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(self.zone3_title.font())
        self.mode_combo.setStyleSheet("border: 1px solid gray; background-color: white; padding: 2px; color: black;")
        self.mode_combo.addItem("CC Constant current", 1)
        self.mode_combo.addItem("CV Constant voltage", 2)
        self.mode_combo.addItem("CP Constant power", 3)
        self.mode_combo.addItem("CR Constant resistance", 4)
        self.mode_combo.setCurrentIndex(0)  # 默认值为 1
        # 禁用 CR 模式选项
        self.mode_combo.model().item(3).setEnabled(False)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
        # 放电模式 标签
        mode_label = QLabel("  放电模式  ")
        mode_label.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")
        # 使用与Zone3标题相同的字体
        mode_label.setFont(self.zone3_title.font())
        mode_layout.addWidget(mode_label)
        
        mode_layout.addWidget(self.mode_combo)
        
        mode_layout.addStretch()  # 添加弹性空间，使内容左对齐
        self.zone3_layout.addWidget(mode_widget)
        
        # 添加一行间距
        font_metrics = QFontMetrics(self.mode_combo.font())
        line_height = int(font_metrics.height() * 1.5)
        mode_spacer = QSpacerItem(10, line_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone3_layout.addItem(mode_spacer)
        
        # 添加 Cutoff Voltage 标签和输入框
        cutoff_widget = QWidget()
        cutoff_layout = QHBoxLayout(cutoff_widget)
        cutoff_layout.setContentsMargins(0, 0, 0, 0)
        cutoff_layout.setSpacing(5)
        
        # 输入框
        self.cutoff_voltage_entry = QLineEdit()
        self.cutoff_voltage_entry.setText("0.00")
        self.cutoff_voltage_entry.setPlaceholderText("0.00")
        self.cutoff_voltage_entry.setFixedWidth(120)
        self.cutoff_voltage_entry.setAlignment(Qt.AlignCenter)
        self.cutoff_voltage_entry.setStyleSheet("border: 1px solid gray; background-color: white; padding: 3px; font-family: 'Microsoft YaHei'; color: black;")
        self.cutoff_voltage_entry.textChanged.connect(self.on_cutoff_voltage_changed)
        
        # 截止电压 标签
        cutoff_label = QLabel("  截止电压  ")
        cutoff_label.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")
        cutoff_label.setMinimumWidth(100)
        cutoff_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # 使用与Zone3标题相同的字体
        cutoff_label.setFont(self.zone3_title.font())
        cutoff_layout.addWidget(cutoff_label)
        
        cutoff_layout.addWidget(self.cutoff_voltage_entry)
        
        # 添加四个空格
        font_metrics = QFontMetrics(cutoff_label.font())
        space_width = font_metrics.width(" ") * 4
        space_spacer = QSpacerItem(space_width, 10, QSizePolicy.Fixed, QSizePolicy.Minimum)
        cutoff_layout.addItem(space_spacer)
        
        # 添加设置按钮
        self.vset_button = QPushButton("   设置   ")
        self.vset_button.setMinimumSize(180, 45)
        self.vset_button.setMaximumSize(180, 45)
        self.vset_button.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
        cutoff_layout.addWidget(self.vset_button)
        
        cutoff_layout.addStretch()  # 添加弹性空间，使内容左对齐
        self.zone3_layout.addWidget(cutoff_widget)
        
        # 添加一行间距
        cutoff_spacer = QSpacerItem(10, line_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone3_layout.addItem(cutoff_spacer)
        
        # 添加 Load Current 标签和输入框
        load_widget = QWidget()
        load_layout = QHBoxLayout(load_widget)
        load_layout.setContentsMargins(0, 0, 0, 0)
        load_layout.setSpacing(5)
        
        # 输入框
        self.load_current_entry = QLineEdit()
        self.load_current_entry.setText("0.00")
        self.load_current_entry.setPlaceholderText("0.00")
        self.load_current_entry.setFixedWidth(120)
        self.load_current_entry.setAlignment(Qt.AlignCenter)
        self.load_current_entry.setStyleSheet("border: 1px solid gray; background-color: white; padding: 3px; font-family: 'Microsoft YaHei'; color: black;")
        self.load_current_entry.textChanged.connect(self.on_load_current_changed)
        
        # 负载电流 标签
        load_label = QLabel("  负载电流  ")
        load_label.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")
        load_label.setMinimumWidth(100)
        load_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # 使用与Zone3标题相同的字体
        load_label.setFont(self.zone3_title.font())
        load_layout.addWidget(load_label)
        
        load_layout.addWidget(self.load_current_entry)
        
        # 添加四个空格
        font_metrics = QFontMetrics(load_label.font())
        space_width = font_metrics.width(" ") * 4
        space_spacer = QSpacerItem(space_width, 10, QSizePolicy.Fixed, QSizePolicy.Minimum)
        load_layout.addItem(space_spacer)
        
        # 添加设置按钮
        self.iset_button = QPushButton("   设置   ")
        self.iset_button.setMinimumSize(180, 45)
        self.iset_button.setMaximumSize(180, 45)
        self.iset_button.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
        load_layout.addWidget(self.iset_button)
        
        load_layout.addStretch()  # 添加弹性空间，使内容左对齐
        self.zone3_layout.addWidget(load_widget)
        
        # 4. 显示 widget (Zone 4)
        self.zone4_widget = QWidget(main_widget)
        
        # 6. 按钮 widget (below Zone 4)
        self.buttons_widget = QWidget(main_widget)
        
        # 创建按钮布局
        self.buttons_layout = QHBoxLayout(self.buttons_widget)
        self.buttons_layout.setContentsMargins(20, 20, 20, 20)  # 边距
        self.buttons_layout.setSpacing(20)  # 按钮间距
        
        # 清除数据按钮
        self.clear_data_btn = QPushButton("清除数据")
        self.clear_data_btn.setMinimumSize(180, 45)
        self.clear_data_btn.setMaximumSize(180, 45)
        self.clear_data_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
        self.clear_data_btn.setToolTip("清除数据")
        
        # 启动按钮
        self.start_btn = QPushButton("启动")
        self.start_btn.setMinimumSize(180, 45)
        self.start_btn.setMaximumSize(180, 45)
        self.start_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
        self.start_btn.setToolTip("启动")
        
        # 添加弹性空间和按钮，使按钮均匀分布
        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.clear_data_btn)
        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.start_btn)
        self.buttons_layout.addStretch()
        
        # 5. 调试窗口
        self.debug_window = QTextEdit(main_widget)
        self.debug_window.setStyleSheet("background-color: lightgrey; color: black; font-family: Courier New; font-size: 24px;")
        self.debug_window.setReadOnly(True)
        self.debug_window.setLineWrapMode(QTextEdit.NoWrap)
        # 添加测试消息
        self.add_debug_message("Debug window initialized")
        self.zone4_widget.setStyleSheet("background-color: white;")
        
        # 创建Zone4的布局为垂直布局
        self.zone4_layout = QVBoxLayout(self.zone4_widget)
        # 设置布局边距
        self.zone4_layout.setContentsMargins(0, 20, 0, 20)  # 顶部和底部边距都是 20px
        # 设置垂直间距为0
        self.zone4_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone4_layout.setAlignment(Qt.AlignTop)
        
        # 添加 Zone4 标题
        self.zone4_title = QLabel('<span style="color: grey;">&nbsp;&nbsp;&nbsp;通信设置</span>')
        self.zone4_title.setAlignment(Qt.AlignLeft)  # 左对齐
        self.zone4_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 使用 Expanding 以填充水平空间
        self.zone4_title.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")  # 移除内边距和外边距
        self.zone4_layout.addWidget(self.zone4_title)
        
        # 添加一行间距
        font_metrics = QFontMetrics(self.zone4_title.font())
        line_height = font_metrics.height()
        zone4_spacer = QSpacerItem(10, line_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone4_layout.addItem(zone4_spacer)
        
        # 添加 Port 标签和下拉菜单
        port_widget = QWidget()
        port_layout = QHBoxLayout(port_widget)
        port_layout.setContentsMargins(0, 0, 0, 0)
        port_layout.setSpacing(10)
        
        # 端口 标签
        port_label = QLabel("  端口  ")
        port_label.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")
        port_layout.addWidget(port_label)
        
        # 下拉菜单
        self.port_combo = QComboBox()
        self.port_combo.setFont(port_label.font())
        self.port_combo.setStyleSheet("border: 1px solid gray; background-color: white; padding: 2px; color: black;")
        self.refresh_serial_ports()
        port_layout.addWidget(self.port_combo)
        
        # 添加三个空格
        font_metrics = QFontMetrics(self.port_combo.font())
        space_width = font_metrics.width(" ") * 3
        space_spacer = QSpacerItem(space_width, 10, QSizePolicy.Fixed, QSizePolicy.Minimum)
        port_layout.addItem(space_spacer)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setMinimumSize(48, 45)
        self.refresh_btn.setMaximumSize(48, 45)
        self.refresh_btn.setStyleSheet("border: 1px solid gray; background-color: #0078D7; font-size: 29px; color: white; padding: 0px; margin: 0px; font-weight: bold;")
        self.refresh_btn.clicked.connect(self.refresh_serial_ports)
        self.refresh_btn.setToolTip("Refresh serial ports")
        port_layout.addWidget(self.refresh_btn)
        
        # 添加三个空格
        space_spacer2 = QSpacerItem(space_width, 10, QSizePolicy.Fixed, QSizePolicy.Minimum)
        port_layout.addItem(space_spacer2)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setMinimumSize(180, 45)
        self.connect_btn.setMaximumSize(180, 45)
        self.connect_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
        self.connect_btn.setToolTip("连接到串口")
        self.connect_btn.clicked.connect(self.toggle_connection)
        port_layout.addWidget(self.connect_btn)
        
        # 添加三个空格
        space_spacer3 = QSpacerItem(space_width, 10, QSizePolicy.Fixed, QSizePolicy.Minimum)
        port_layout.addItem(space_spacer3)
        
        # 创建垂直布局用于放置TxStatus和RxStatus图标
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setSpacing(5)
        status_layout.setContentsMargins(5, 0, 0, 0)  # 添加5px左边距，将图标向内移动
        
        # TxStatus图标
        self.tx_status_icon = QLabel("●")
        self.tx_status_icon.setFont(QFont("Arial", 16))
        self.tx_status_icon.setStyleSheet("color: darkgrey;")
        self.tx_status_icon.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.tx_status_icon)
        
        # RxStatus图标
        self.rx_status_icon = QLabel("●")
        self.rx_status_icon.setFont(QFont("Arial", 16))
        self.rx_status_icon.setStyleSheet("color: darkgrey;")
        self.rx_status_icon.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.rx_status_icon)
        
        # 设置status_widget的大小
        status_widget.setMinimumSize(30, 45)
        status_widget.setMaximumSize(30, 45)
        
        # 将status_widget添加到主布局
        port_layout.addWidget(status_widget)
        
        port_layout.addStretch()  # 添加弹性空间，使内容左对齐
        self.zone4_layout.addWidget(port_widget)
        
        # 添加Zone2标题
        self.zone2_title = QLabel('<span style="color: grey;">&nbsp;&nbsp;&nbsp;实时数据</span>')
        self.zone2_title.setAlignment(Qt.AlignLeft)  # 左对齐
        self.zone2_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 使用Expanding以填充水平空间
        self.zone2_title.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")  # 移除内边距和外边距
        self.zone2_layout.addWidget(self.zone2_title)
        
        # 添加空行（使用 QSpacerItem 创建垂直空间）
        font_metrics = QFontMetrics(self.zone2_title.font())
        line_height = font_metrics.height()
        spacer = QSpacerItem(10, line_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone2_layout.addItem(spacer)
        
        # 创建三个标签，分别显示每行数据
        # 第1行： 000.00V 000.00A
        self.zone2_line1 = QLabel('<span style="color: blue;">&nbsp;000.00V</span><span style="color: red;">&nbsp;000.00A</span>')
        self.zone2_line1.setAlignment(Qt.AlignLeft)  # 左对齐
        self.zone2_line1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 使用Expanding以填充水平空间
        self.zone2_line1.setFont(font)
        self.zone2_line1.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")  # 移除内边距和外边距
        self.zone2_layout.addWidget(self.zone2_line1)
        
        # 添加空行（高度为line1字体高度的40%）
        font_metrics = QFontMetrics(font)
        line_height = font_metrics.height()
        spacer_height = int(line_height * 0.4)
        self.spacer_line1 = QSpacerItem(10, spacer_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone2_layout.addItem(self.spacer_line1)
        
        # 第2行： 000.00W 000.00mAh
        self.zone2_line2 = QLabel('<span style="color: orange;">&nbsp;000.00W</span><span style="color: purple;">&nbsp;000.00mAh</span>')
        self.zone2_line2.setAlignment(Qt.AlignLeft)  # 左对齐
        self.zone2_line2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 使用Expanding以填充水平空间
        self.zone2_line2.setFont(font)
        self.zone2_line2.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")  # 移除内边距和外边距
        self.zone2_layout.addWidget(self.zone2_line2)
        
        # 添加空行（高度为line2字体高度的40%）
        font_metrics = QFontMetrics(font)
        line_height = font_metrics.height()
        spacer_height = int(line_height * 0.4)
        self.spacer_line2 = QSpacerItem(10, spacer_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone2_layout.addItem(self.spacer_line2)
        
        # 第3行： 000.00Wh
        self.zone2_line3 = QLabel('<span style="color: darkgreen;">&nbsp;000.00Wh</span>')
        self.zone2_line3.setAlignment(Qt.AlignLeft)  # 左对齐
        self.zone2_line3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 使用Expanding以填充水平空间
        self.zone2_line3.setFont(font)
        self.zone2_line3.setStyleSheet("border: none; background-color: transparent; padding: 0; margin: 0;")  # 移除内边距和外边距
        self.zone2_layout.addWidget(self.zone2_line3)
        
        # 添加空行（高度为line3字体高度的40%）
        font_metrics = QFontMetrics(font)
        line_height = font_metrics.height()
        spacer_height = int(line_height * 0.4)
        self.spacer_line3 = QSpacerItem(10, spacer_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.zone2_layout.addItem(self.spacer_line3)
        
        # 3. 刻度线widget
        self.scale_line = ScaleLineWidget(main_widget)
        self.scale_line.setParent(main_widget)
        
        # 4. 第二个刻度线widget（自定义）
        from PyQt5.QtGui import QColor
        self.scale_line2 = ScaleLineWidget(
            main_widget, 
            min_value=0, 
            max_value=30, 
            color=QColor(0, 0, 255),  # 蓝色
            label="(V)", 
            marker_direction="left",  # 标记指向左侧
            alignment="right"  # 数字右对齐，与橙色刻度线保持一致
        )
        self.scale_line2.setParent(main_widget)
        
        # 5. 第三个刻度线widget（I Scale）
        self.scale_line3 = ScaleLineWidget(
            main_widget, 
            min_value=0, 
            max_value=15, 
            color=QColor(255, 0, 0),  # 红色
            label="(A)", 
            marker_direction="left",  # 标记指向左侧，与V Scale一致
            alignment="right"  # 数字右对齐，与V Scale一致
        )
        self.scale_line3.setParent(main_widget)
        
        # 6. 第四个刻度线widget（T Scale，水平）
        from PyQt5.QtGui import QColor
        self.scale_line4 = ScaleLineWidget(
            main_widget, 
            scale_width=300,  # 初始宽度
            min_value=0, 
            max_value=300,  # 范围改为0-300
            color=QColor(128, 128, 128),  # 灰色
            label="(S)", 
            marker_direction="down",  # 标记指向下方
            alignment="center",  # 数字居中对齐
            orientation="horizontal"  # 水平方向
        )
        self.scale_line4.setParent(main_widget)
        
        # 连接窗口大小变化信号
        self.resizeEvent = self.on_resize
        
        # 连接刻度线双击信号
        self.scale_line.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line))
        self.scale_line2.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line2))
        self.scale_line3.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line3))
        self.scale_line4.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line4))
        
        # 2. 版本号标签
        self.revision_label = QLabel(f"Revision: {REVISION}")
        self.revision_label.setParent(main_widget)
        
        # 初始调整大小
        self.on_resize(None)
        
        # 暂时移除轴的双击事件，因为我们已经重新设计了曲线显示区域
        
    def on_mode_changed(self, index):
        # 当下拉菜单选择改变时，更新 mode 变量
        self.mode = self.mode_combo.currentData()
        
    def on_cutoff_voltage_changed(self, text):
        # 当截止电压输入框改变时，更新 Vset 变量
        try:
            value = float(text)
            if 0 <= value <= 50:
                self.Vset = value
                # 保留两位小数
                self.cutoff_voltage_entry.setText(f"{value:.2f}")
            else:
                # 超出范围，恢复为之前值
                self.cutoff_voltage_entry.setText(f"{self.Vset:.2f}")
        except ValueError:
            # 无效输入，保持当前值
            pass
        
    def on_load_current_changed(self, text):
        # 当负载电流输入框改变时，更新 Iset 变量
        try:
            value = float(text)
            if 0 <= value <= 50:
                self.Iset = value
                # 保留两位小数
                self.load_current_entry.setText(f"{value:.2f}")
            else:
                # 超出范围，恢复为之前值
                self.load_current_entry.setText(f"{self.Iset:.2f}")
        except ValueError:
            # 无效输入，保持当前值
            pass
        
    def refresh_serial_ports(self):
        # 刷新串口列表
        self.port_combo.clear()
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            self.port_combo.addItem(port.device, port.device)
        
    def set_control_font_size(self, font_size):
        # 设置所有控件的字体大小
        for widget in self.findChildren((QLabel, QComboBox, QPushButton, QDoubleSpinBox)):
            widget.setStyleSheet(f"font-size: {font_size}px;")
    
    def on_x_axis_double_click(self, event):
        # 双击X轴修改时间最大值
        current_max = self.axis_ranges['time']['max']
        new_max, ok = QInputDialog.getDouble(self, "设置时间最大值", "输入新的时间最大值（秒）:", current_max, 10, 3600, 0)
        if ok:
            self.axis_ranges['time']['max'] = new_max
            # 移除对plot_widget的引用，因为我们已经替换为DisplayWidget
    
    def on_y_axis_double_click(self, axis_type, event):
        # 双击Y轴修改标度
        current_min = self.axis_ranges[axis_type].get('min', 0)
        current_max = self.axis_ranges[axis_type]['max']
        
        # 使用自定义对话框同时设置最小值和最大值
        dialog = AxisRangeDialog(axis_type, current_min, current_max, self)
        if dialog.exec_() == QDialog.Accepted:
            new_min, new_max = dialog.get_values()
            
            # 计算留白，确保标度数字不被切掉
            range_diff = new_max - new_min
            padding = range_diff * 0.05  # 5%的留白
            padded_min = new_min - padding
            padded_max = new_max + padding
            
            # 更新轴范围
            self.axis_ranges[axis_type]['min'] = new_min
            self.axis_ranges[axis_type]['max'] = new_max
            
            # 更新对应轴的范围，使用带有留白的值
            # 移除对plot_widget的引用，因为我们已经替换为DisplayWidget
            # 强制刷新显示
            self.display_widget.update()
            
            # 刷新整个图形
        self.display_widget.update()
    
    def on_scale_double_click(self, scale_widget):
        # 双击刻度线修改范围
        current_min = scale_widget.min_value
        current_max = scale_widget.max_value
        
        # 使用自定义对话框同时设置最小值和最大值
        dialog = ScaleRangeDialog(current_min, current_max, self)
        if dialog.exec_() == QDialog.Accepted:
            new_min, new_max = dialog.get_values()
            if new_min is not None and new_max is not None:
                # 更新刻度范围
                scale_widget.set_range(new_min, new_max)
                # 强制刷新显示
                scale_widget.update()
        
    def on_resize(self, event):
        """窗口大小变化时更新显示widget的位置和大小"""
        # 调用父类的resizeEvent
        if event:
            super().resizeEvent(event)
        
        # 获取UI屏幕大小
        ui_width = self.width()
        ui_height = self.height()
        
        # 计算边距
        left_margin = ui_width / 40  # 减少50%
        top_margin = ui_height / 30  # 减少50%
        bottom_margin = ui_height / 7.5  # 减少1/3 (从1/5变为1/7.5)
        right_margin = left_margin  # 右侧边距与左侧边距相同
        
        # 计算中间间距（与左侧边距相同）
        middle_spacing = left_margin
        
        # 计算Zone1的大小和位置（恢复原始大小）
        zone1_width = (ui_width - left_margin - right_margin - middle_spacing) * 0.7  # 保留Zone1的主要宽度
        zone1_height = ui_height - top_margin - bottom_margin
        
        # 计算Zone2的位置
        zone2_x = left_margin + zone1_width + middle_spacing
        zone2_width = ui_width - zone2_x - right_margin  # 确保右侧边距与左侧边距相同
        
        # 计算三行文本的字体大小，使其填充整个宽度
        if hasattr(self, 'zone2_line1') and hasattr(self, 'zone2_line2') and hasattr(self, 'zone2_line3'):
            # 计算适合的字体大小
            def calculate_font_size(text, width):
                font_size = 10  # 起始字体大小
                max_font_size = 200  # 最大字体大小，防止无限循环
                font = QFont("Courier New", font_size, QFont.Light)  # 使用更薄的等宽字体
                while font_size < max_font_size:
                    font.setPointSize(font_size)
                    font_metrics = QFontMetrics(font)
                    text_width = font_metrics.width(text)
                    if text_width > width * 0.95:  # 留5%的余量
                        return font_size - 1
                    font_size += 1
                return max_font_size
            
            # 获取每行文本（无格式，用于计算字体大小）
            line1_text_plain = " 000.00V 000.00A"
            line2_text_plain = " 000.00W 000.00mAh"
            line3_text_plain = " 000.00Wh"
            
            # 计算每行的字体大小
            line1_font_size = calculate_font_size(line1_text_plain, zone2_width)
            line2_font_size = calculate_font_size(line2_text_plain, zone2_width)
            line3_font_size = calculate_font_size(line3_text_plain, zone2_width)
            
            # 使用最小的字体大小以确保所有行都能容纳
            font_size = min(line1_font_size, line2_font_size, line3_font_size)
            
            # 应用字体大小
            font = QFont("Courier New", int(font_size), QFont.Light)  # 使用更薄的等宽字体
            
            # 获取Zone2标题的字体
            zone2_title_font = self.zone2_title.font()
            
            # 更新Zone3和Zone4的标题字体以匹配Zone2的标题字体
            if hasattr(self, 'zone3_title'):
                self.zone3_title.setFont(zone2_title_font)
            if hasattr(self, 'zone4_title'):
                self.zone4_title.setFont(zone2_title_font)
            
            # 计算Zone2的高度：从顶部到line3底部
            # 计算标题高度
            title_font_metrics = QFontMetrics(self.zone2_title.font())
            title_height = title_font_metrics.height()
            
            # 计算数据行高度
            data_font_metrics = QFontMetrics(font)
            data_line_height = data_font_metrics.height()
            
            # 计算总高度：标题 + 标题下空行 + 3行数据 + 3行空行（每行空行为数据行高度的40%）
            zone2_height = (
                title_height +  # 标题
                title_height +  # 标题下空行
                data_line_height +  # 第1行
                data_line_height * 0.4 +  # 第1行下空行
                data_line_height +  # 第2行
                data_line_height * 0.4 +  # 第2行下空行
                data_line_height +  # 第3行
                data_line_height * 0.4  # 第3行下空行
            )
            
            # 使用绝对定位设置Zone1的位置和大小
            self.display_widget.setGeometry(
                int(left_margin),
                int(top_margin),
                int(zone1_width),
                int(zone1_height)
            )
            
            # 使用绝对定位设置Zone2的位置和大小
            self.zone2_widget.setGeometry(
                int(zone2_x),
                int(top_margin),
                int(zone2_width),
                int(zone2_height)
            )
            
            # 计算Zone3的位置和大小
            zone3_x = zone2_x
            zone3_y = top_margin + zone2_height + top_margin  # 与Zone2的间距与Zone2上方的间距相同
            zone3_width = zone2_width  # 与Zone2宽度相同
            # 精确计算 Zone3 高度以确保底部边距与顶部边距相同（20px）
            # 确保所有绿色间距保持不变
            zone3_height = 350  # 进一步增加高度以完全显示按钮
            
            # 使用绝对定位设置Zone3的位置和大小
            self.zone3_widget.setGeometry(
                int(zone3_x),
                int(zone3_y),
                int(zone3_width),
                int(zone3_height)
            )
            
            # 计算 Zone4 的位置和大小
            zone4_x = zone2_x
            zone4_y = zone3_y + zone3_height + top_margin  # 与 Zone3 的间距与 Zone2 和 Zone3 之间的间距相同
            zone4_width = zone2_width  # 与 Zone2 宽度相同
            
            # Zone4 标题顶部到 Zone4 顶部的间距（即 zone4_layout 的顶部边距）
            zone4_title_spacing = 20  # setContentsMargins 中设置的顶部边距
            
            # 计算字体和高度
            title_font_metrics = QFontMetrics(self.zone4_title.font())
            title_height = title_font_metrics.height()
            
            # 计算空行高度（与标题字体相同）
            line_height = title_height
            
            port_font_metrics = QFontMetrics(self.port_combo.font())
            port_label_height = port_font_metrics.height()
            port_combo_height = 30  # pull-down menu 高度
            button_height = 45  # refresh_btn 和 connect_btn 高度
            spacing_height = 10  # 各元素之间的间距
            
            # 计算 Zone4 的高度：顶部边距 + 标题 + 空行 + port_widget 高度 + 底部边距
            # port_widget 高度 = max(port_combo_height, button_height)  # 取较大值
            port_widget_height = max(port_combo_height, button_height)  # 下拉菜单和按钮的最大高度
            zone4_height = zone4_title_spacing + title_height + line_height + port_widget_height + zone4_title_spacing  # 顶部边距 + 标题 + 空行 + 内容高度 + 底部边距
            
            # 使用绝对定位设置 Zone4 的位置和大小
            self.zone4_widget.setGeometry(
                int(zone4_x),
                int(zone4_y),
                int(zone4_width),
                int(zone4_height)
            )
            
            # 计算按钮 widget 的位置和大小（位于 Zone4 下方）
            buttons_x = zone4_x
            buttons_y = zone4_y + zone4_height + top_margin  # 与 Zone4 的间距与其他区域之间的间距相同
            buttons_width = zone4_width  # 与 Zone4 宽度相同
            buttons_height = 100  # 按钮区域高度
            
            # 使用绝对定位设置按钮 widget 的位置和大小
            self.buttons_widget.setGeometry(
                int(buttons_x),
                int(buttons_y),
                int(buttons_width),
                int(buttons_height)
            )
            
            # 计算并显示 Zone4 的间距
            # Zone4 结构：顶部边距 (20px) + title + 空行 (line_height) + port_widget(包含 port_label + spacing + combo + spacing + buttons) + 底部边距 (20px)
            # port_widget 底部到 Zone4 底部的间距应该等于 zone4_title_spacing (20px)
            # port_widget 底部位置 = zone4_title_spacing + title_height + line_height + port_label_height + spacing_height + port_combo_height + spacing_height + button_height
            # port_widget 底部到 Zone4 底部 = zone4_height - (zone4_title_spacing + title_height + line_height + port_label_height + spacing_height + port_combo_height + spacing_height + button_height)
            port_widget_bottom_to_zone4_bottom = zone4_height - (zone4_title_spacing + title_height + line_height + port_label_height + spacing_height + port_combo_height + spacing_height + button_height)
            
            # 计算调试窗口的位置和大小
            # 调试窗口高度（3行文本的高度）
            debug_window_height = 120
            # 定位到最底部，在所有区域下方
            debug_window_y = ui_height - debug_window_height
            self.debug_window.setGeometry(
                int(left_margin),
                int(debug_window_y),
                int(ui_width - left_margin - right_margin),
                int(debug_window_height)
            )
            

            
            # 更新标签文本和字体
            self.zone2_line1.setText('<span style="color: blue;">&nbsp;000.00V</span><span style="color: red;">&nbsp;000.00A</span>')
            self.zone2_line2.setText('<span style="color: orange;">&nbsp;000.00W</span><span style="color: purple;">&nbsp;000.00mAh</span>')
            self.zone2_line3.setText('<span style="color: darkgreen;">&nbsp;000.00Wh</span>')
            
            # 确保大小策略为Expanding以填充水平空间
            self.zone2_line1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.zone2_line2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.zone2_line3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            
            self.zone2_line1.setFont(font)
            self.zone2_line2.setFont(font)
            self.zone2_line3.setFont(font)
            
            # 更新line1下方的空行高度（为line1字体高度的40%）
            if hasattr(self, 'spacer_line1'):
                font_metrics = QFontMetrics(font)
                line_height = font_metrics.height()
                spacer_height = int(line_height * 0.4)
                # 移除旧的spacer
                self.zone2_layout.removeItem(self.spacer_line1)
                # 创建新的spacer
                self.spacer_line1 = QSpacerItem(10, spacer_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
                # 插入到line1之后的位置
                self.zone2_layout.insertItem(self.zone2_layout.indexOf(self.zone2_line1) + 1, self.spacer_line1)
            
            # 更新line2下方的空行高度（为line2字体高度的40%）
            if hasattr(self, 'spacer_line2'):
                font_metrics = QFontMetrics(font)
                line_height = font_metrics.height()
                spacer_height = int(line_height * 0.4)
                # 移除旧的spacer
                self.zone2_layout.removeItem(self.spacer_line2)
                # 创建新的spacer
                self.spacer_line2 = QSpacerItem(10, spacer_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
                # 插入到line2之后的位置
                self.zone2_layout.insertItem(self.zone2_layout.indexOf(self.zone2_line2) + 1, self.spacer_line2)
            
            # 更新line3下方的空行高度（为line3字体高度的40%）
            if hasattr(self, 'spacer_line3'):
                font_metrics = QFontMetrics(font)
                line_height = font_metrics.height()
                spacer_height = int(line_height * 0.4)
                # 移除旧的spacer
                self.zone2_layout.removeItem(self.spacer_line3)
                # 创建新的spacer
                self.spacer_line3 = QSpacerItem(10, spacer_height, QSizePolicy.Minimum, QSizePolicy.Fixed)
                # 插入到line3之后的位置
                self.zone2_layout.insertItem(self.zone2_layout.indexOf(self.zone2_line3) + 1, self.spacer_line3)
            
            # 强制更新布局
            self.zone2_widget.update()
            self.zone2_widget.repaint()
        
        # 定位版本号标签到左下角
        if hasattr(self, 'revision_label'):
            label_x = left_margin
            label_y = ui_height - bottom_margin + 10  # 10像素的偏移量       
            self.revision_label.setGeometry(int(label_x), int(label_y), 200, 30)
        
        # 计算PlotWindow的大小（与DisplayWidget中相同的计算方式）
        left_space = zone1_width / 8
        right_space = (zone1_width / 16) * 0.7
        bottom_space = zone1_height / 10
        top_space = zone1_height * 3 / 40
        plot_width = zone1_width - left_space - right_space
        plot_height = zone1_height - top_space - bottom_space
        
        # 获取实际widget大小
        actual_width = self.display_widget.width()
        actual_height = self.display_widget.height()
        
        # 强制重绘以确保矩形和原点显示
        self.display_widget.update()
        
        # 定位第一个刻度线widget（P Scale）到右侧，使其橙色点与浅灰色框的右上角和右下角点精确对齐
        # 计算可绘制区域的宽度和位置
        plottable_width = plot_width - 30  # 宽度减去右侧边距
        plottable_height = plot_height - 10  # 高度减去顶部边距
        plottable_x = left_margin + left_space  # 可绘制区域的左侧x坐标
        plottable_y = top_margin + top_space + 10  # 可绘制区域的顶部y坐标
        
        # 计算P Scale的位置和高度（确保点的中心精确对齐）
        # 目标：
        # 顶部橙色点中心 = 深粉色点中心 = (plottable_x + plottable_width, plottable_y)
        # 底部橙色点中心 = 粉色点中心 = (plottable_x + plottable_width, plottable_y + plottable_height)
        
        # P Scale内部坐标系统：
        # 顶部橙色点中心：(20, 50) 相对P Scale widget
        # 底部橙色点中心：(20, 50 + scale_height) 相对P Scale widget
        
        # 计算P Scale widget的位置
        scale_x = (plottable_x + plottable_width) - 20  # 20是P Scale内部橙色点中心x坐标
        scale_y = plottable_y - 50  # 50是P Scale内部顶部橙色点中心y坐标
        scale_height = plottable_height  # 确保底部点对齐
        scale_width = 150  # 保持宽度以显示完整数字
        
        self.scale_line.set_height(scale_height)
        self.scale_line.setGeometry(int(scale_x), int(scale_y), scale_width, int(scale_height + 2 * self.scale_line.padding))
        
        # 定位第三个刻度线widget（I Scale），使其红色点与浅灰色框的左上角和左下角点垂直对齐，并水平居中在Zone 1左边缘和PlotWindow左边缘之间
        # 计算可绘制区域的宽度和位置
        plottable_width = plot_width - 30  # 宽度减去右侧边距
        plottable_height = plot_height - 10  # 高度减去顶部边距
        plottable_x = left_margin + left_space  # 可绘制区域的左侧x坐标
        plottable_y = top_margin + top_space + 10  # 可绘制区域的顶部y坐标
        
        # 计算I Scale的位置和高度
        # 目标：
        # 顶部红色点中心y = 紫色点中心y = plottable_y
        # 底部红色点中心y = 黑色点中心y = plottable_y + plottable_height
        # 红色点中心x = (0 + plottable_x) / 2  # 中间位置（Zone 1左边缘到PlotWindow左边缘）
        
        # I Scale内部坐标系统（marker_direction="left"）：
        # 顶部红色点中心：(scale3_width - 20, 50) 相对I Scale widget
        # 底部红色点中心：(scale3_width - 20, 50 + scale3_height) 相对I Scale widget
        
        # 计算I Scale widget的位置
        scale3_width = 200  # 宽度与V Scale一致，以容纳左侧文本
        # 向左移动10%：当前位置是70%，移动后为60%的位置
        red_dot_x = (0 + plottable_x) * 0.6  # 60%的位置
        scale3_x = red_dot_x - (scale3_width - 20)  # 20是I Scale内部红色点中心x坐标（从右侧边缘）
        scale3_y = plottable_y - 50  # 50是I Scale内部顶部红色点中心y坐标
        scale3_height = plottable_height  # 确保底部点对齐
        
        self.scale_line3.set_height(scale3_height)
        self.scale_line3.setGeometry(int(scale3_x), int(scale3_y), scale3_width, int(scale3_height + 2 * self.scale_line3.padding))
        
        # 定位第二个刻度线widget（V Scale）到右侧，使其蓝色点与浅灰色框的左上角和左下角点精确对齐
        # 计算V Scale的位置和高度（确保点的中心精确对齐）
        # 目标：
        # 顶部蓝色点中心 = 紫色点中心 = (plottable_x, plottable_y)
        # 底部蓝色点中心 = 黑色点中心 = (plottable_x, plottable_y + plottable_height)
        
        # V Scale内部坐标系统：
        # 顶部蓝色点中心：(V Scale宽度 - 20, 50) 相对V Scale widget
        # 底部蓝色点中心：(V Scale宽度 - 20, 50 + scale2_height) 相对V Scale widget
        
        # 计算V Scale widget的位置
        scale2_width = 200  # 增加宽度以容纳左侧的文本
        scale2_x = plottable_x - (scale2_width - 20)  # 20是V Scale内部蓝色点中心x坐标（从右侧边缘）
        scale2_y = plottable_y - 50  # 50是V Scale内部顶部蓝色点中心y坐标
        scale2_height = plottable_height  # 确保底部点对齐
        self.scale_line2.set_height(scale2_height)
        self.scale_line2.setGeometry(int(scale2_x), int(scale2_y), scale2_width, int(scale2_height + 2 * self.scale_line2.padding))
        
        # 定位第四个刻度线widget（T Scale，水平）到主布局的下方，使其灰色点与浅灰色框的左下角和右下角点精确对齐
        # 计算可绘制区域的宽度和位置
        plottable_width = plot_width - 30  # 宽度减去右侧边距
        plottable_x = left_margin + left_space  # 可绘制区域的左侧x坐标
        plottable_bottom_y = top_margin + top_space + plot_height  # 可绘制区域的底部y坐标
        
        # 计算T Scale的位置和宽度（确保点的中心精确对齐）
        # 目标：
        # 左侧灰色点中心 = 黑色点中心 = (plottable_x, plottable_y + plottable_height)
        # 右侧灰色点中心 = 粉色点中心 = (plottable_x + plottable_width, plottable_y + plottable_height)
        
        # T Scale内部坐标系统：
        # 左侧灰色点中心：(50, 50) 相对T Scale widget （padding=50）
        # 右侧灰色点中心：(50 + scale4_width, 50) 相对T Scale widget
        
        # 计算T Scale widget的位置
        scale4_width = plottable_width  # 确保宽度匹配可绘制区域
        scale4_x = plottable_x - 50  # 50是T Scale内部左侧灰色点中心x坐标
        scale4_y = (plottable_y + plottable_height) - 50  # 50是T Scale内部灰色点中心y坐标
        
        self.scale_line4.set_width(scale4_width)
        self.scale_line4.setGeometry(int(scale4_x), int(scale4_y), int(scale4_width + 2 * self.scale_line4.padding), 100)
        
    def init_timer(self):
        # 数据更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(1000)  # 1秒更新一次
        
        # 曲线显示定时器
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start(5000)  # 5秒更新一次
        
        # 参数读取定时器
        self.param_timer = QTimer()
        self.param_timer.timeout.connect(self.get_parameter)
        self.param_timer.start(5000)  # 5秒更新一次
        
        # 时间计数
        self.start_time = time.time()
        self.time_max = 300  # 默认5分钟
        
    def toggle_curve(self, key, state):
        self.curves[key].setVisible(state == Qt.Checked)
        
    def set_mode(self, index):
        if index != self.mode:
            self.mode = index
            # 这里应该调用setMode函数
            print(f"设置工作模式: {index}")
            
    def set_current(self, value):
        # 这里应该调用setCurrent函数
        print(f"设置负载电流: {value}")
        
    def set_vcut(self, value):
        # 这里应该调用setVcut函数
        print(f"设置截止电压: {value}")
        # 更新Vcut曲线
        self.update_vcut_curve(value)
        
    def toggle_parameter_edit(self, event):
        self.is_parameter_editable = not self.is_parameter_editable
        self.set_parameter_editable(self.is_parameter_editable)
        
    def set_parameter_editable(self, editable):
        # 暂时注释掉，因为我们移除了右侧面板
        # self.mode_combo.setEnabled(editable)
        # self.current_spin.setEnabled(editable)
        # self.vcut_spin.setEnabled(editable)
        pass
        
    def get_parameter(self):
        # 这里应该调用getParameter函数获取参数
        # 从主机读取参数
        print("读取参数")
        # 实际应用中，这里应该通过串口读取数据并解析
        # 现在使用固定值
        # 固定模式：0 (CC)
        mode = 0
        # 固定电流：1.0A
        current = 1.0
        # 固定截止电压：3.5V
        vcut = 3.5
        
        # 更新显示 - 暂时注释掉，因为我们移除了右侧面板
        # self.mode_combo.setCurrentIndex(mode)
        # self.current_spin.setValue(current)
        # self.vcut_spin.setValue(vcut)
        
        # 更新Vcut曲线
        self.update_vcut_curve(vcut)
        
    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        
    def toggle_connection(self):
        if not self.is_connected:
            # 立即更改按钮为黄色，显示"连接中"
            self.connect_btn.setText("连接中")
            self.connect_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: yellow; padding: 0px; margin: 0px;")
            
            # 强制UI更新
            QApplication.processEvents()
            
            # 连接串口
            port = self.port_combo.currentText()
            if port:
                try:
                    # 检查端口是否存在
                    ports = [p.device for p in serial.tools.list_ports.comports()]
                    if port not in ports:
                        QMessageBox.warning(self, "错误", f"串口 {port} 不存在或不可用")
                        # 连接失败，恢复按钮原始状态
                        self.connect_btn.setText("连接")
                        self.connect_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
                        return
                    
                    # 尝试多次打开串口，处理有数据输入的情况
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            # 尝试使用不同的端口名称格式
                            port_name = port
                            if not port.startswith('COM'):
                                port_name = 'COM' + port
                            print(f"Attempt {attempt+1} to connect to {port_name}")
                            
                            # 对于所有端口，使用标准参数
                            self.serial_port = serial.Serial(
                                port=port_name,
                                baudrate=9600,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=2
                            )
                            
                            # 清除缓冲区
                            if hasattr(self.serial_port, 'in_waiting'):
                                if self.serial_port.in_waiting:
                                    self.serial_port.read_all()
                            
                            self.is_connected = True
                            self.connect_btn.setText("断开连接")
                            self.connect_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: lightgreen; padding: 0px; margin: 0px;")
                            # 更改端口下拉菜单为绿色并禁用
                            self.port_combo.setStyleSheet("border: 1px solid green; background-color: white; padding: 2px;")
                            self.port_combo.setEnabled(False)
                            break
                        except Exception as e:
                            if attempt == max_attempts - 1:
                                raise
                            # 等待一段时间后重试
                            import time
                            time.sleep(0.5)
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"无法连接到串口 {port}: {str(e)}")
                    # 连接失败，恢复按钮原始状态
                    self.connect_btn.setText("连接")
                    self.connect_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
        else:
            # 断开串口
            if self.serial_port:
                try:
                    self.serial_port.close()
                except Exception as e:
                    pass
                finally:
                    self.serial_port = None
            self.is_connected = False
            self.connect_btn.setText("连接")
            self.connect_btn.setStyleSheet("border: 1px solid gray; border-radius: 22px; background-color: white; padding: 0px; margin: 0px;")
            # 恢复端口下拉菜单为原始颜色并启用
            self.port_combo.setStyleSheet("border: 1px solid gray; background-color: white; padding: 2px;")
            self.port_combo.setEnabled(True)
            
    def update_data(self):
        # 从串口接收数据并更新
        # 目前使用固定值，实际应用中应该从串口读取数据
        current_time = time.time() - self.start_time
        
        # 固定初始值
        voltage = 4.0
        current = 1.0
        power = voltage * current
        capacity = current * current_time / 3600 * 1000  # mAh
        energy = power * current_time / 3600  # Wh
        
        # 存储数据
        self.data['time'].append(current_time)
        self.data['I'].append(current)
        self.data['V'].append(voltage)
        self.data['P'].append(power)
        
        # 检查时间是否超过最大值
        if current_time > self.time_max:
            self.time_max += 60  # 自动增加1分钟
        
        # 读取串口数据并显示在调试窗口
        if self.is_connected and self.serial_port:
            try:
                # 读取可用数据
                        if hasattr(self.serial_port, 'in_waiting'):
                            if self.serial_port.in_waiting > 0:
                                # 正在接收数据
                                self.update_rx_status(True)
                                data = self.serial_port.read(self.serial_port.in_waiting)
                                # 检查是否以 ff 55 开头
                                if not (len(data) >= 2 and data[0] == 0xff and data[1] == 0x55):
                                    # 转换为十六进制格式
                                    hex_data = ' '.join([f'{b:02x}' for b in data])
                                    # 显示在调试窗口
                                    self.add_debug_message(hex_data)
                                # 添加数据到缓冲区
                                self.serial_buffer.extend(data)
                                # 解码数据
                                self.decode_serial_data()
                                # 短暂延迟后恢复状态
                        QTimer.singleShot(500, lambda: self.update_rx_status(False))
            except Exception as e:
                pass
    
    def send_data(self, data):
        # 发送数据到串口
        if self.is_connected and self.serial_port:
            try:
                # 正在发送数据
                self.update_tx_status(True)
                self.serial_port.write(data)
                # 短暂延迟后恢复状态
                QTimer.singleShot(500, lambda: self.update_tx_status(False))
                return True
            except Exception as e:
                print(f"发送数据失败: {e}")
                self.update_tx_status(False)
                return False
        return False
    
    def update_tx_status(self, transmitting):
        # 更新TxStatus图标颜色
        if hasattr(self, 'tx_status_icon'):
            if transmitting:
                self.tx_status_icon.setStyleSheet("color: green;")
            else:
                self.tx_status_icon.setStyleSheet("color: darkgrey;")
    
    def update_rx_status(self, receiving):
        # 更新RxStatus图标颜色
        if hasattr(self, 'rx_status_icon'):
            if receiving:
                self.rx_status_icon.setStyleSheet("color: green;")
            else:
                self.rx_status_icon.setStyleSheet("color: darkgrey;")
    
    def decode_serial_data(self):
        # 查找 0xFF 0x55 头
        header_index = self.serial_buffer.find(b'\xff\x55')
        while header_index != -1:
            # 检查缓冲区是否有足够的数据（36字节）
            if len(self.serial_buffer) - header_index >= 36:
                # 提取36字节的数据帧
                frame = self.serial_buffer[header_index:header_index+36]
                
                # 解码参数
                try:
                    # 电压 (SV) - 3字节, 除以100
                    sv = int.from_bytes(frame[4:7], byteorder='big') / 100
                    
                    # 电流 (SI) - 3字节, 除以1000
                    si = int.from_bytes(frame[7:10], byteorder='big') / 1000
                    
                    # 容量 (SAh) - 3字节, 除以1000
                    sah = int.from_bytes(frame[10:13], byteorder='big') / 1000
                    
                    # 能量 (SWh) - 3字节, 除以100
                    swh = int.from_bytes(frame[13:16], byteorder='big') / 100
                    
                    # 时间/持续时间 (SH) - 2字节, 直接使用
                    sh = int.from_bytes(frame[18:20], byteorder='big')
                    
                    # 定时器分钟 (SM) - 1字节, 直接使用
                    sm = frame[20]
                    
                    # 定时器秒 (SS) - 1字节, 直接使用
                    ss = frame[21]
                    
                    # 限制电压 (SVcutoff) - 2字节, 除以10
                    svcutoff = int.from_bytes(frame[22:24], byteorder='big') / 10
                    
                    # 限制电流 (SIset) - 2字节, 除以100
                    iset = int.from_bytes(frame[24:26], byteorder='big') / 100
                    
                    # 限制功率 (SWset) - 1字节, 直接使用
                    swset = frame[26]
                    
                    # 模式 (Smode) - 假设在某个位置，需要根据实际帧定义调整
                    # 这里假设在第27字节
                    smode = frame[27] if len(frame) > 27 else 0
                    
                    # 状态 (Sstate) - 假设在某个位置，需要根据实际帧定义调整
                    # 这里假设在第28字节
                    sstate = frame[28] if len(frame) > 28 else 0
                    
                    # 输出解码后的数据到控制台
                    print(f"SV: {sv} V")
                    print(f"SI: {si} A")
                    print(f"SAh: {sah} Ah")
                    print(f"SWh: {swh} Wh")
                    print(f"SH: {sh} s")
                    print(f"SM: {sm} min")
                    print(f"SS: {ss} sec")
                    print(f"SVcutoff: {svcutoff} V")
                    print(f"SIset: {iset} A")
                    print(f"SWset: {swset} W")
                    print(f"Smode: {smode}")
                    print(f"Sstate: {sstate}")
                    print("------------------------")
                except Exception as e:
                    print(f"解码错误: {str(e)}")
                
                # 移除已处理的数据
                self.serial_buffer = self.serial_buffer[header_index+36:]
                header_index = self.serial_buffer.find(b'\xff\x55')
            else:
                # 数据不足，保留剩余部分
                self.serial_buffer = self.serial_buffer[header_index:]
                break
    
    def add_debug_message(self, message):
        # 添加调试信息到调试窗口
        if hasattr(self, 'debug_window'):
            # 获取当前时间的分钟和秒
            import datetime
            now = datetime.datetime.now()
            timestamp = f"{now.minute:02d}.{now.second:02d}"
            # 添加时间戳到消息
            message_with_timestamp = f"{timestamp}  {message}"
            # 获取当前内容
            current_text = self.debug_window.toPlainText()
            # 拆分为行
            lines = current_text.strip().split('\n')
            # 保留最后2行，加上新消息（总共3行）
            lines = lines[-2:] + [message_with_timestamp]
            # 重新组合
            new_text = '\n'.join(lines)
            # 更新调试窗口
            self.debug_window.setPlainText(new_text)
            # 滚动到底部
            self.debug_window.verticalScrollBar().setValue(self.debug_window.verticalScrollBar().maximum())
            
    def update_vcut_curve(self, vcut_value):
        # 更新Vcut曲线
        if hasattr(self, 'data') and 'time' in self.data:
            if self.data['time']:
                self.data['Vcut'] = [vcut_value] * len(self.data['time'])
            else:
                self.data['Vcut'] = []
        
    def update_plot(self):
        # 由于我们已经重新设计了曲线显示区域，不再显示曲线
        # 这里只保留基本的数据更新逻辑，以保持与原有代码的兼容性
        pass
        
    def clear_plot(self):
        # 清除曲线数据
        for key in self.data:
            self.data[key] = []
        
        # 重置时间
        self.start_time = time.time()
        self.time_max = 300  # 恢复默认5分钟
        
        # 由于我们已经重新设计了曲线显示区域，不再更新曲线
            
    def mouseDoubleClickEvent(self, event):
        # 双击空白处清除曲线
        if event.button() == Qt.LeftButton:
            # 检查点击位置是否在曲线区域
            pos = event.pos()
            if self.display_widget.geometry().contains(pos):
                # 使用屏幕坐标直接判断，避免坐标转换问题
                plot_rect = self.display_widget.geometry()
                # 计算曲线区域的中心点
                center_x = plot_rect.left() + plot_rect.width() // 2
                center_y = plot_rect.top() + plot_rect.height() // 2
                # 计算点击位置到中心点的距离
                distance = ((pos.x() - center_x) ** 2 + (pos.y() - center_y) ** 2) ** 0.5
                # 设定一个合适的半径（以像素为单位）
                radius = 50  # 大约15个字符的宽度
                
                if distance <= radius:
                    reply = QMessageBox.question(
                        self, '确认', '确定要清除曲线数据吗？',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self.clear_plot()
                    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DL24App()
    window.show()
    sys.exit(app.exec_())