import sys
import time
from datetime import datetime
import os
import hashlib
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QGroupBox, QCheckBox,
    QDoubleSpinBox, QGridLayout, QMessageBox, QSizePolicy, QInputDialog,
    QDialog, QFormLayout, QDialogButtonBox, QSpacerItem, QLineEdit,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsView, QGraphicsScene,
    QTextEdit, QFrame, QColorDialog
)
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QFont, QFontMetrics, QPen, QColor, QPainter
from PySide6.QtGui import QGuiApplication
import pyqtgraph as pg
import serial
import serial.tools.list_ports

# Global color variables
ColorP = QColor(255, 165, 0)  # Orange
ColorV = QColor(0, 0, 255)  # Blue
ColorA = QColor(255, 0, 0)  # Red

# Global temperature variable
MosT = 0.0  # Initial temperature

# Global runtime variable
RunTime = 0  # Initial runtime in seconds

# X resolution for curve plotting
XResolution = 300

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
                    # 如果patch达到99，重置为00并递增minor
                    if patch > 99:
                        patch = 0
                        minor += 1
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
        self.show_curves = True  # 控制是否显示曲线
        
        # 添加Zone1标签
        self.zone1_label = QLabel("实时放电曲线", self)
        self.zone1_label.setAlignment(Qt.AlignCenter)
        self.zone1_label.setStyleSheet("font-size: 26px; color: black;")
        self.zone1_label.setFixedSize(600, 60)  # 增加宽度以容纳20个中文字符
        self.zone1_label.setCursor(Qt.PointingHandCursor)
        self.zone1_label.mouseDoubleClickEvent = self.on_label_double_click
    
    def mouseDoubleClickEvent(self, event):
        # 双击时隐藏曲线，恢复整个绘图区域
        self.show_curves = False
        self.update()
    
    def mousePressEvent(self, event):
        # 单击时重新绘制曲线
        self.show_curves = True
        self.update()
        

    
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
        
        if dialog.exec() == QDialog.Accepted:
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
        # 定位标签到Zone1的中心，位于顶部和图表区域顶部的中间
        if self.parent():
            parent_width = self.parent().width()
            label_x = (parent_width - self.zone1_label.width()) // 2
            
            # 计算标签y坐标：位于Zone1顶部和图表区域顶部的中间，再向上移动25px
            if self.plot_window:
                # 获取图表区域的顶部位置
                plot_y = self.plot_window.y()
                # 计算中间位置并向上移动25px
                label_y = (plot_y // 2) - 25
                # 确保标签不会超出顶部边界
                label_y = max(0, label_y)
            else:
                #  fallback 位置，向上移动25px
                label_y = max(0, 20 - 25)
                
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
            

            

            

            

            
            # 绘制VIP曲线
            if self.show_curves and self.main_window:
                # 获取实际刻度值
                try:
                    # V scale (scale_line2)
                    v_min = self.main_window.scale_line2.min_value
                    v_max = self.main_window.scale_line2.max_value
                    
                    # I scale (scale_line3)
                    i_min = self.main_window.scale_line3.min_value
                    i_max = self.main_window.scale_line3.max_value
                    
                    # P scale (scale_line)
                    p_min = self.main_window.scale_line.min_value
                    p_max = self.main_window.scale_line.max_value
                    
                    # T scale (scale_line4)
                    t_scale_min = self.main_window.scale_line4.min_value
                    t_scale_max = self.main_window.scale_line4.max_value
                except Exception:
                    #  fallback to default values if scale widgets not available
                    v_min, v_max = 2, 5
                    i_min, i_max = 0, 10
                    p_min, p_max = 0, 50
                    t_scale_min, t_scale_max = 0, 300
                
                # 设置裁剪区域，确保曲线不超出边界
                painter.setClipRect(int(plottable_x), int(plottable_y), int(plottable_width), int(plottable_height))
                
                # 获取数据
                if hasattr(self.main_window, 'data'):
                    time_data = self.main_window.data.get('time', [])
                    voltage_data = self.main_window.data.get('V', [])
                    current_data = self.main_window.data.get('I', [])
                    power_data = self.main_window.data.get('P', [])
                    
                    # 确保数据长度匹配
                    data_points = min(len(time_data), len(voltage_data), len(current_data), len(power_data))
                    if data_points > 1:
                        # 获取当前RunTime，只绘制RunTime之后的数据
                        current_runtime = getattr(self.main_window, 'RunTime', 0)
                        
                        # 绘制V曲线（蓝色）
                        try:
                            if hasattr(self.main_window, 'CheckboxV') and self.main_window.CheckboxV.isChecked():
                                painter.setPen(QPen(ColorV, 2))
                                prev_x, prev_y = None, None
                                for i in range(data_points):
                                    t = time_data[i]
                                    if t >= current_runtime:
                                        v = voltage_data[i]
                                        t_ratio = (t - t_scale_min) / (t_scale_max - t_scale_min)
                                        v_ratio = (v - v_min) / (v_max - v_min)
                                        x = plottable_x + t_ratio * plottable_width
                                        y = plottable_y + (1 - v_ratio) * plottable_height
                                        x = max(plottable_x, min(plottable_x + plottable_width, x))
                                        y = max(plottable_y, min(plottable_y + plottable_height, y))
                                        if prev_x is not None and prev_y is not None:
                                            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
                                        prev_x, prev_y = x, y
                        except Exception:
                            pass
                        
                        # 绘制I曲线（红色）
                        try:
                            if hasattr(self.main_window, 'CheckboxA') and self.main_window.CheckboxA.isChecked():
                                painter.setPen(QPen(ColorA, 2))
                                prev_x, prev_y = None, None
                                for i in range(data_points):
                                    t = time_data[i]
                                    if t >= current_runtime:
                                        i_val = current_data[i]
                                        t_ratio = (t - t_scale_min) / (t_scale_max - t_scale_min)
                                        i_ratio = (i_val - i_min) / (i_max - i_min)
                                        x = plottable_x + t_ratio * plottable_width
                                        y = plottable_y + (1 - i_ratio) * plottable_height
                                        x = max(plottable_x, min(plottable_x + plottable_width, x))
                                        y = max(plottable_y, min(plottable_y + plottable_height, y))
                                        if prev_x is not None and prev_y is not None:
                                            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
                                        prev_x, prev_y = x, y
                        except Exception:
                            pass
                        
                        # 绘制P曲线（橙色）
                        try:
                            if hasattr(self.main_window, 'CheckboxP') and self.main_window.CheckboxP.isChecked():
                                painter.setPen(QPen(ColorP, 2))
                                prev_x, prev_y = None, None
                                for i in range(data_points):
                                    t = time_data[i]
                                    if t >= current_runtime:
                                        p = power_data[i]
                                        t_ratio = (t - t_scale_min) / (t_scale_max - t_scale_min)
                                        p_ratio = (p - p_min) / (p_max - p_min)
                                        x = plottable_x + t_ratio * plottable_width
                                        y = plottable_y + (1 - p_ratio) * plottable_height
                                        x = max(plottable_x, min(plottable_x + plottable_width, x))
                                        y = max(plottable_y, min(plottable_y + plottable_height, y))
                                        if prev_x is not None and prev_y is not None:
                                            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
                                        prev_x, prev_y = x, y
                        except Exception:
                            pass

            
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
    from PySide6.QtCore import Signal
    doubleClicked = Signal()
    
    def __init__(self, parent=None, height=300, scale_width=300, num_markers=6, min_value=0, max_value=200, color=QColor(255, 165, 0), label="(W)", marker_direction="right", alignment="left", orientation="vertical", scale_type="P"):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        # 确保widget接收鼠标事件
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        # 不要设置最小大小，让调用者通过setGeometry控制
        self.setMinimumSize(0, 0)
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
        self.scale_type = scale_type  # 刻度类型："V", "A", "P", "T"
    
    def mouseDoubleClickEvent(self, event):
        # 检查点击位置是否在刻度线或标记区域内
        pos = event.pos()
        
        # 计算实际刻度线位置
        if self.orientation == "vertical":
            # 垂直刻度线
            if self.marker_direction == "left":
                # 左指向标记：刻度线在右侧
                scale_line_x = self.width() - 20
                # 检查区域：刻度线附近及左侧标记区域
                line_left = scale_line_x - self.marker_length - 10
                line_right = scale_line_x + 10
            else:
                # 右指向标记：刻度线在左侧
                scale_line_x = 20
                # 检查区域：刻度线附近及右侧标记区域
                line_left = scale_line_x - 10
                line_right = scale_line_x + self.marker_length + 10
            
            # 垂直范围：刻度线上下区域
            line_top = self.padding - 10
            line_bottom = self.padding + self.height + 10
        else:
            # 水平刻度线
            # 刻度线在中间
            scale_line_y = 50
            # 检查区域：刻度线附近及下方标记区域
            line_left = self.padding - 10
            line_right = self.padding + self.scale_width + 10
            line_top = scale_line_y - 10
            line_bottom = scale_line_y + self.marker_length + 10
        
        # 只在刻度线或标记区域内响应双击
        if line_left <= pos.x() <= line_right and line_top <= pos.y() <= line_bottom:
            # 当双击时直接打开对话框
            from PySide6.QtWidgets import QDialog
            dialog = ScaleRangeDialog(self.min_value, self.max_value, self.scale_type, self.parent())
            if dialog.exec() == QDialog.Accepted:
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
        self.update()
    
    def set_width(self, scale_width):
        """设置刻度线宽度"""
        self.scale_width = scale_width
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
                pen = QPen()
                pen.setColor(self.color)
                pen.setWidth(self.line_width)
                painter.setPen(pen)
                # 对于左指向标记，将刻度线向右移动，为左侧文本留出空间
                if self.marker_direction == "left":
                    scale_line_x = self.width() - 20  # 刻度线靠近右侧
                else:
                    scale_line_x = 20  # 刻度线靠近左侧
                painter.drawLine(scale_line_x, start_y, scale_line_x, end_y)
                

                
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
                    pen = QPen()
                    pen.setColor(self.color)
                    pen.setWidth(self.line_width)
                    painter.setPen(pen)  # 使用指定颜色，线宽3
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
                    pen = QPen()
                    pen.setColor(QColor(64, 64, 64))
                    pen.setWidth(1)
                    painter.setPen(pen)  # 深灰色，线宽1
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
                pen = QPen()
                pen.setColor(self.color)
                pen.setWidth(self.line_width)
                painter.setPen(pen)
                # 对于下指向标记，将刻度线上移，为下方文本留出空间
                if self.marker_direction == "down":
                    scale_line_y = 50  # 刻度线上移
                else:
                    scale_line_y = 50  # 刻度线居中
                painter.drawLine(start_x, scale_line_y, end_x, scale_line_y)
                

                
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
                    pen = QPen()
                    pen.setColor(self.color)
                    pen.setWidth(self.line_width)
                    painter.setPen(pen)  # 使用指定颜色，线宽3
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
                    pen = QPen()
                    pen.setColor(QColor(64, 64, 64))
                    pen.setWidth(1)
                    painter.setPen(pen)  # 深灰色，线宽1
                    # 创建文本区域，增加高度和宽度以显示完整数字
                    # 固定文本矩形宽度，确保所有数字对齐一致
                    text_rect = QRect(int(marker_x) - 40, int(text_y), 80, 24)  # 固定尺寸
                    painter.drawText(text_rect, align_flag | Qt.AlignVCenter, formatted_value)
        finally:
            painter.end()

class ScaleRangeDialog(QDialog):
    def __init__(self, current_min, current_max, scale_type, parent=None):
        from PySide6.QtWidgets import QLineEdit, QLabel, QVBoxLayout, QGridLayout, QPushButton, QHBoxLayout, QMessageBox
        super().__init__(parent)
        self.setWindowTitle("设置刻度范围")
        self.scale_type = scale_type
        
        # 定义各刻度类型的允许范围
        self.ranges = {
            "V": [0, 30],  # 电压
            "A": [0, 30],  # 电流
            "P": [0, 180],  # 功率
            "T": [0, 3600]  # 时间
        }
        
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
            
            # 检查值是否在允许范围内
            if self.scale_type in self.ranges:
                min_range, max_range = self.ranges[self.scale_type]
                if min_val < min_range:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "输入错误", f"最小值不能小于 {min_range}")
                    return None, None
                if max_val > max_range:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "输入错误", f"最大值不能大于 {max_range}")
                    return None, None
            
            # 检查最小值是否小于最大值
            if min_val >= max_val:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "输入错误", "最小值必须小于最大值")
                return None, None
            
            return min_val, max_val
        except ValueError:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "输入错误", "请输入有效的数字")
            return None, None

class PurpleDotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置透明背景
        self.setStyleSheet("background-color: transparent;")
    
    def paintEvent(self, event):
        # 绘制紫色点
        painter = QPainter(self)
        try:
            painter.setPen(QPen(QColor(128, 0, 128), 1))  # 紫色
            painter.setBrush(QColor(128, 0, 128))
            # 左下角，中心对齐于黄色区域的左边缘和下边缘的交点
            painter.drawEllipse(0, self.height() - 5, 10, 10)
        finally:
            painter.end()

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
        # 全局时间变量
        self.H = 0
        self.M = 0
        self.S = 0
        
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
        screen = QGuiApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.8)
        self.setGeometry(100, 100, width, height)
        self.setFixedSize(width, height)  # 使窗口不可调整大小
        self.setWindowTitle(f"DL24P Host {REVISION}")
        
        # 设置全局字体
        self.font = QFont("Microsoft YaHei", 10)
        QApplication.setFont(self.font)
        
        # 主布局
        main_widget = QWidget()
        main_widget.setStyleSheet("border: none;")  # 移除边框
        self.setCentralWidget(main_widget)
        
        # 1. 显示widget (Zone 1)
        self.display_widget = DisplayWidget(main_widget)
        self.display_widget.setStyleSheet("background-color: white;")
        # 设置OverlayWidget的main_window引用
        self.display_widget.overlay.set_main_window(self)
        
        # 2. 显示widget (Zone 2)
        self.zone2_widget = QWidget(main_widget)
        # 移除背景颜色和边框
        
        # 创建Zone2的布局为垂直布局
        self.zone2_layout = QVBoxLayout(self.zone2_widget)
        # 设置布局边距
        self.zone2_layout.setContentsMargins(0, 20, 0, 0)  # 顶部边距20px
        # 设置垂直间距为0
        self.zone2_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone2_layout.setAlignment(Qt.AlignTop)
        
        # 设置初始字体
        font = QFont("SimHei", 14, QFont.Light)  # 使用黑体字体
        
        # 3. 显示 widget (Zone 3)
        self.zone3_widget = QWidget(main_widget)

        # 设置 Zone3 的字体大小为原来的 1.875 倍 (1.5 * 1.25)
        zone3_font = QFont("Courier New", 26, QFont.Light)
        self.zone3_widget.setFont(zone3_font)
        
        # 创建Zone3的布局为垂直布局
        self.zone3_layout = QVBoxLayout(self.zone3_widget)
        # 设置布局边距
        self.zone3_layout.setContentsMargins(0, 0, 0, 20)  # 顶部0px边距，底部边距都是 20px
        # 设置垂直间距为0
        self.zone3_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone3_layout.setAlignment(Qt.AlignTop)
        
        # 添加新行（3列）在Zone3顶部
        new_row_layout = QHBoxLayout()
        new_row_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        new_row_layout.setSpacing(0)  # 0间距
        
        # 列1：5%宽度
        col1 = QWidget()
        new_row_layout.addWidget(col1)
        new_row_layout.setStretch(0, 5)  # 5%
        
        # 列2：剩余宽度（90%），添加"参数设置"标签
        col2 = QWidget()
        col2_layout = QHBoxLayout(col2)
        col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        col2_layout.setSpacing(0)
        
        label = QLabel("参数设置")
        font = QFont("Microsoft YaHei", 14)  # 雅黑，14px
        label.setFont(font)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        label.setStyleSheet("color: grey;")  # 设置文字颜色为灰色
        col2_layout.addWidget(label)
        
        new_row_layout.addWidget(col2)
        new_row_layout.setStretch(1, 90)  # 90%
        
        # 列3：5%宽度
        col3 = QWidget()
        new_row_layout.addWidget(col3)
        new_row_layout.setStretch(2, 5)  # 5%
        
        # 设置行高
        new_row_widget = QWidget()
        new_row_widget.setLayout(new_row_layout)
        new_row_widget.setMinimumHeight(30)  # 调整行高以容纳14px字体
        new_row_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 添加新行到Zone3布局
        self.zone3_layout.addWidget(new_row_widget)
        
        # 添加行下方的7px间距
        spacer_below_row1 = QWidget()
        spacer_below_row1.setMinimumHeight(7)  # 默认7px高度
        self.zone3_layout.addWidget(spacer_below_row1)
        
        # 添加 row2：3列 10% 30% 60%
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row2_layout.setSpacing(0)  # 0间距
        
        # 列1：10%宽度
        row2_col1 = QWidget()
        row2_layout.addWidget(row2_col1)
        row2_layout.setStretch(0, 10)  # 10%
        
        # 列2：30%宽度，添加"放电模式"标签
        row2_col2 = QWidget()
        row2_col2_layout = QHBoxLayout(row2_col2)
        row2_col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row2_col2_layout.setSpacing(0)
        
        row2_label = QLabel("放电模式")
        font = QFont("SimHei", 12)  # 黑体，12px
        row2_label.setFont(font)
        row2_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row2_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        row2_col2_layout.addWidget(row2_label)
        
        row2_layout.addWidget(row2_col2)
        row2_layout.setStretch(1, 30)  # 30%
        
        # 列3：60%宽度，添加下拉列表
        row2_col3 = QWidget()
        row2_col3_layout = QHBoxLayout(row2_col3)
        row2_col3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row2_col3_layout.setSpacing(0)
        
        # 添加下拉列表
        self.row2_combo = QComboBox()
        font = QFont("SimHei", 12)  # 黑体，12px
        self.row2_combo.setFont(font)
        self.row2_combo.setStyleSheet("border: none; padding: 2px; color: black;")
        self.row2_combo.addItem("CC - 恒电流放电", 1)
        self.row2_combo.setCurrentIndex(0)  # 默认值为CC
        # 禁用下拉列表，只允许CC模式
        self.row2_combo.setEnabled(False)
        row2_col3_layout.addWidget(self.row2_combo)
        
        row2_layout.addWidget(row2_col3)
        row2_layout.setStretch(2, 60)  # 60%
        
        # 设置行高
        row2_widget = QWidget()
        row2_widget.setLayout(row2_layout)
        row2_widget.setMinimumHeight(25)  # 调整行高以容纳12px字体
        row2_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 添加行到Zone3布局
        self.zone3_layout.addWidget(row2_widget)
        
        # 添加 row3：5列 10% 30% 25% 10% 25%
        row3_layout = QHBoxLayout()
        row3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row3_layout.setSpacing(0)  # 0间距
        
        # 列1：10%宽度
        row3_col1 = QWidget()
        row3_layout.addWidget(row3_col1)
        row3_layout.setStretch(0, 10)  # 10%
        
        # 列2：30%宽度，添加"截止电压"标签
        row3_col2 = QWidget()
        row3_col2_layout = QHBoxLayout(row3_col2)
        row3_col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row3_col2_layout.setSpacing(0)
        
        row3_label = QLabel("截止电压")
        font = QFont("SimHei", 12)  # 黑体，12px
        row3_label.setFont(font)
        row3_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row3_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        row3_col2_layout.addWidget(row3_label)
        
        row3_layout.addWidget(row3_col2)
        row3_layout.setStretch(1, 30)  # 30%
        
        # 列3：25%宽度，添加数据输入框
        row3_col3 = QWidget()
        row3_col3_layout = QHBoxLayout(row3_col3)
        row3_col3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row3_col3_layout.setSpacing(0)
        
        # 添加数据输入框
        self.row3_entry = QLineEdit()
        font = QFont("SimHei", 12)  # 黑体，12px
        self.row3_entry.setFont(font)
        self.row3_entry.setText("0.00")
        self.row3_entry.setPlaceholderText("0.00")
        self.row3_entry.setAlignment(Qt.AlignCenter)
        self.row3_entry.setStyleSheet("border: none; padding: 2px; color: black;")
        
        # 输入框事件处理
        row3_old_value = ""
        
        def on_row3_focus_in():
            # 开始编辑时停止MainLoop并设置黄色背景
            nonlocal row3_old_value
            if self.main_loop_timer.isActive():
                self.main_loop_timer.stop()
            # 保存当前值
            row3_old_value = self.row3_entry.text()
            self.row3_entry.setStyleSheet("border: none; padding: 2px; color: black; background-color: yellow;")
            # 清空输入框并设置光标位置
            self.row3_entry.clear()
            self.row3_entry.setCursorPosition(0)
        
        def on_row3_focus_out():
            # 失去焦点时恢复颜色和值
            nonlocal row3_old_value
            self.row3_entry.setStyleSheet("border: none; padding: 2px; color: black;")
            # 恢复旧值
            self.row3_entry.setText(row3_old_value)
            # 重新启动MainLoop
            if not self.main_loop_timer.isActive():
                self.main_loop_timer.start(1000)
        
        def on_row3_key_press(event):
            nonlocal row3_old_value
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # 按Enter键完成编辑
                try:
                    voltage = float(self.row3_entry.text())
                    if self.is_connected:
                        success = self.SetVset(voltage)
                        if success:
                            print(f"SetVset successful: {voltage}V")
                            # 更新旧值
                            row3_old_value = f"{voltage:.2f}"
                except ValueError:
                    print("Invalid voltage value")
                # 恢复颜色并重新启动MainLoop
                self.row3_entry.setStyleSheet("border: none; padding: 2px; color: black;")
                if not self.main_loop_timer.isActive():
                    self.main_loop_timer.start(1000)
                # 移除焦点
                self.row3_entry.clearFocus()
            elif event.key() == Qt.Key_Escape:
                # 按ESC键取消编辑
                self.row3_entry.setStyleSheet("border: none; padding: 2px; color: black;")
                # 恢复旧值
                self.row3_entry.setText(row3_old_value)
                if not self.main_loop_timer.isActive():
                    self.main_loop_timer.start(1000)
                # 移除焦点
                self.row3_entry.clearFocus()
            else:
                # 其他键交给默认处理
                QLineEdit.keyPressEvent(self.row3_entry, event)
        
        # 连接信号
        self.row3_entry.focusInEvent = lambda event: (QLineEdit.focusInEvent(self.row3_entry, event), on_row3_focus_in())
        self.row3_entry.focusOutEvent = lambda event: (QLineEdit.focusOutEvent(self.row3_entry, event), on_row3_focus_out())
        self.row3_entry.keyPressEvent = on_row3_key_press
        
        self.row3_entry.textChanged.connect(self.on_cutoff_voltage_changed)
        row3_col3_layout.addWidget(self.row3_entry)
        
        row3_layout.addWidget(row3_col3)
        row3_layout.setStretch(2, 25)  # 25%
        
        # 列4：10%宽度，添加"V"标签
        row3_col4 = QWidget()
        row3_col4_layout = QHBoxLayout(row3_col4)
        row3_col4_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row3_col4_layout.setSpacing(0)
        
        row3_unit_label = QLabel("V")
        font = QFont("SimHei", 12)  # 黑体，12px
        row3_unit_label.setFont(font)
        row3_unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row3_unit_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        row3_col4_layout.addWidget(row3_unit_label)
        
        row3_layout.addWidget(row3_col4)
        row3_layout.setStretch(3, 10)  # 10%
        
        # 列5：25%宽度（保留空间）
        row3_col5 = QWidget()
        row3_layout.addWidget(row3_col5)
        row3_layout.setStretch(4, 25)  # 25%
        
        # 设置行高
        row3_widget = QWidget()
        row3_widget.setLayout(row3_layout)
        row3_widget.setMinimumHeight(25)  # 调整行高以容纳12px字体
        row3_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 添加行到Zone3布局
        self.zone3_layout.addWidget(row3_widget)
        
        # 添加 row4：5列 10% 30% 25% 10% 25%
        row4_layout = QHBoxLayout()
        row4_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row4_layout.setSpacing(0)  # 0间距
        
        # 列1：10%宽度
        row4_col1 = QWidget()
        row4_layout.addWidget(row4_col1)
        row4_layout.setStretch(0, 10)  # 10%
        
        # 列2：30%宽度，添加"负载电流"标签
        row4_col2 = QWidget()
        row4_col2_layout = QHBoxLayout(row4_col2)
        row4_col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row4_col2_layout.setSpacing(0)
        
        row4_label = QLabel("负载电流")
        font = QFont("SimHei", 12)  # 黑体，12px
        row4_label.setFont(font)
        row4_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row4_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        row4_col2_layout.addWidget(row4_label)
        
        row4_layout.addWidget(row4_col2)
        row4_layout.setStretch(1, 30)  # 30%
        
        # 列3：25%宽度，添加数据输入框
        row4_col3 = QWidget()
        row4_col3_layout = QHBoxLayout(row4_col3)
        row4_col3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row4_col3_layout.setSpacing(0)
        
        # 添加数据输入框
        self.row4_entry = QLineEdit()
        font = QFont("SimHei", 12)  # 黑体，12px
        self.row4_entry.setFont(font)
        self.row4_entry.setText("0.00")
        self.row4_entry.setPlaceholderText("0.00")
        self.row4_entry.setAlignment(Qt.AlignCenter)
        self.row4_entry.setStyleSheet("border: none; padding: 2px; color: black;")
        
        # 输入框事件处理
        row4_old_value = ""
        
        def on_row4_focus_in():
            # 开始编辑时停止MainLoop并设置黄色背景
            nonlocal row4_old_value
            if self.main_loop_timer.isActive():
                self.main_loop_timer.stop()
            # 保存当前值
            row4_old_value = self.row4_entry.text()
            self.row4_entry.setStyleSheet("border: none; padding: 2px; color: black; background-color: yellow;")
            # 清空输入框并设置光标位置
            self.row4_entry.clear()
            self.row4_entry.setCursorPosition(0)
        
        def on_row4_focus_out():
            # 失去焦点时恢复颜色和值
            nonlocal row4_old_value
            self.row4_entry.setStyleSheet("border: none; padding: 2px; color: black;")
            # 恢复旧值
            self.row4_entry.setText(row4_old_value)
            # 重新启动MainLoop
            if not self.main_loop_timer.isActive():
                self.main_loop_timer.start(1000)
        
        def on_row4_key_press(event):
            nonlocal row4_old_value
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # 按Enter键完成编辑
                try:
                    current = float(self.row4_entry.text())
                    if self.is_connected:
                        success = self.SetIset(current)
                        if success:
                            print(f"SetIset successful: {current}A")
                            # 更新旧值
                            row4_old_value = f"{current:.2f}"
                except ValueError:
                    print("Invalid current value")
                # 恢复颜色并重新启动MainLoop
                self.row4_entry.setStyleSheet("border: none; padding: 2px; color: black;")
                if not self.main_loop_timer.isActive():
                    self.main_loop_timer.start(1000)
                # 移除焦点
                self.row4_entry.clearFocus()
            elif event.key() == Qt.Key_Escape:
                # 按ESC键取消编辑
                self.row4_entry.setStyleSheet("border: none; padding: 2px; color: black;")
                # 恢复旧值
                self.row4_entry.setText(row4_old_value)
                if not self.main_loop_timer.isActive():
                    self.main_loop_timer.start(1000)
                # 移除焦点
                self.row4_entry.clearFocus()
            else:
                # 其他键交给默认处理
                QLineEdit.keyPressEvent(self.row4_entry, event)
        
        # 连接信号
        self.row4_entry.focusInEvent = lambda event: (QLineEdit.focusInEvent(self.row4_entry, event), on_row4_focus_in())
        self.row4_entry.focusOutEvent = lambda event: (QLineEdit.focusOutEvent(self.row4_entry, event), on_row4_focus_out())
        self.row4_entry.keyPressEvent = on_row4_key_press
        
        self.row4_entry.textChanged.connect(self.on_load_current_changed)
        row4_col3_layout.addWidget(self.row4_entry)
        
        row4_layout.addWidget(row4_col3)
        row4_layout.setStretch(2, 25)  # 25%
        
        # 列4：10%宽度，添加"A"标签
        row4_col4 = QWidget()
        row4_col4_layout = QHBoxLayout(row4_col4)
        row4_col4_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        row4_col4_layout.setSpacing(0)
        
        row4_unit_label = QLabel("A")
        font = QFont("SimHei", 12)  # 黑体，12px
        row4_unit_label.setFont(font)
        row4_unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row4_unit_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        row4_col4_layout.addWidget(row4_unit_label)
        
        row4_layout.addWidget(row4_col4)
        row4_layout.setStretch(3, 10)  # 10%
        
        # 列5：25%宽度（保留空间）
        row4_col5 = QWidget()
        row4_layout.addWidget(row4_col5)
        row4_layout.setStretch(4, 25)  # 25%
        
        # 设置行高
        row4_widget = QWidget()
        row4_widget.setLayout(row4_layout)
        row4_widget.setMinimumHeight(25)  # 调整行高以容纳12px字体
        row4_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 添加行到Zone3布局
        self.zone3_layout.addWidget(row4_widget)
        
        # 4. 显示 widget (Zone 4)
        self.zone4_widget = QWidget(main_widget)
        self.zone4_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 清除数据按钮
        self.clear_data_btn = QPushButton("清除数据")
        self.clear_data_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: white; padding: 0px; margin: 0px; font-size: 17px;")
        self.clear_data_btn.setToolTip("清除数据")
        
        # 按钮点击行为
        def on_clear_data_clicked():
            if not self.is_connected:
                print("Device not connected, cannot reset counters")
                return
            
            # 设置按钮为黄色
            self.clear_data_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: yellow; padding: 0px; margin: 0px; font-size: 17px;")
            
            # 强制UI更新
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # 等待MainLoop完成
            import time
            while self.main_loop_running:
                time.sleep(0.1)
                QApplication.processEvents()
            
            # 调用SetResetCounters函数
            success = self.SetResetCounters()
            if success:
                print("Counters reset successful")
                # 清除曲线数据
                self.clear_plot()
            else:
                print("Failed to reset counters")
            
            # 恢复按钮颜色
            self.clear_data_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: white; padding: 0px; margin: 0px; font-size: 17px;")
        
        self.clear_data_btn.clicked.connect(on_clear_data_clicked)
        
        # 启动按钮
        self.start_btn = QPushButton("启动")
        self.start_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: white; padding: 0px; margin: 0px; font-size: 17px;")
        self.start_btn.setToolTip("启动")
        self.start_btn.clicked.connect(self.on_onoff_button_clicked)
        
        # 5. 显示 widget (Zone 5)
        self.zone5_widget = QWidget(main_widget)
        # 移除背景颜色，继承父容器的背景
        
        # 6. 显示 widget (Zone 6)
        self.zone6_widget = QWidget(main_widget)
        
        # 创建Zone6的布局为垂直布局
        self.zone6_layout = QVBoxLayout(self.zone6_widget)
        # 设置布局边距
        self.zone6_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        # 设置垂直间距为0
        self.zone6_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone6_layout.setAlignment(Qt.AlignTop)
        
        # 添加 row1：4列 20% 20% 20% 40%
        zone6_row1_layout = QHBoxLayout()
        zone6_row1_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone6_row1_layout.setSpacing(0)  # 0间距
        
        # 列1：20%宽度，添加复选框、细线和标签
        self.zone6_col1 = QWidget()
        zone6_row1_col1_layout = QHBoxLayout(self.zone6_col1)
        zone6_row1_col1_layout.setContentsMargins(0, 0, 0, 0)
        zone6_row1_col1_layout.setSpacing(5)
        
        # 左侧间隔（12.5%）
        left_spacer1 = QWidget()
        zone6_row1_col1_layout.addWidget(left_spacer1)
        zone6_row1_col1_layout.setStretch(0, 1)
        
        # 复选框
        self.CheckboxV = QCheckBox()
        self.CheckboxV.setMinimumSize(15, 15)
        self.CheckboxV.setMaximumSize(15, 15)
        # 设置初始样式（选中状态）
        self.CheckboxV.setStyleSheet("background-color: blue; color: black;")
        self.CheckboxV.setChecked(True)  # 默认选中
        # 连接状态变化信号
        self.CheckboxV.stateChanged.connect(lambda state: 
            self.CheckboxV.setStyleSheet("background-color: blue; color: black;") if state else 
            self.CheckboxV.setStyleSheet("background-color: lightgrey; color: black;")
        )
        zone6_row1_col1_layout.addWidget(self.CheckboxV)
        
        # 细线
        self.lineV = QFrame()
        self.lineV.setFrameShape(QFrame.HLine)
        self.lineV.setFrameShadow(QFrame.Sunken)
        self.lineV.setMinimumHeight(2)
        self.lineV.setMaximumHeight(2)
        self.lineV.setStyleSheet("background-color: blue;")
        self.lineV.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        zone6_row1_col1_layout.addWidget(self.lineV)
        zone6_row1_col1_layout.setStretch(2, 4)
        
        # 标签
        self.labelV = QLabel("V")
        self.labelV.setStyleSheet("color: blue;")
        self.labelV.setAlignment(Qt.AlignCenter)
        zone6_row1_col1_layout.addWidget(self.labelV)
        zone6_row1_col1_layout.setStretch(3, 1)
        
        # 右侧间隔（12.5%）
        right_spacer1 = QWidget()
        zone6_row1_col1_layout.addWidget(right_spacer1)
        zone6_row1_col1_layout.setStretch(4, 1)
        
        zone6_row1_layout.addWidget(self.zone6_col1)
        zone6_row1_layout.setStretch(0, 20)  # 20%
        
        # 列2：20%宽度，添加复选框、细线和标签
        self.zone6_col2 = QWidget()
        zone6_row1_col2_layout = QHBoxLayout(self.zone6_col2)
        zone6_row1_col2_layout.setContentsMargins(0, 0, 0, 0)
        zone6_row1_col2_layout.setSpacing(5)
        
        # 左侧间隔（12.5%）
        left_spacer2 = QWidget()
        zone6_row1_col2_layout.addWidget(left_spacer2)
        zone6_row1_col2_layout.setStretch(0, 1)
        
        # 复选框
        self.CheckboxP = QCheckBox()
        self.CheckboxP.setMinimumSize(15, 15)
        self.CheckboxP.setMaximumSize(15, 15)
        # 设置初始样式（选中状态）
        self.CheckboxP.setStyleSheet("background-color: orange; color: black;")
        self.CheckboxP.setChecked(True)  # 默认选中
        # 连接状态变化信号
        self.CheckboxP.stateChanged.connect(lambda state: 
            self.CheckboxP.setStyleSheet("background-color: orange; color: black;") if state else 
            self.CheckboxP.setStyleSheet("background-color: lightgrey; color: black;")
        )
        zone6_row1_col2_layout.addWidget(self.CheckboxP)
        
        # 细线
        self.lineP = QFrame()
        self.lineP.setFrameShape(QFrame.HLine)
        self.lineP.setFrameShadow(QFrame.Sunken)
        self.lineP.setMinimumHeight(2)
        self.lineP.setMaximumHeight(2)
        self.lineP.setStyleSheet("background-color: orange;")
        self.lineP.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        zone6_row1_col2_layout.addWidget(self.lineP)
        zone6_row1_col2_layout.setStretch(2, 4)
        
        # 标签
        self.labelP = QLabel("P")
        self.labelP.setStyleSheet("color: orange;")
        self.labelP.setAlignment(Qt.AlignCenter)
        zone6_row1_col2_layout.addWidget(self.labelP)
        zone6_row1_col2_layout.setStretch(3, 1)
        
        # 右侧间隔（12.5%）
        right_spacer2 = QWidget()
        zone6_row1_col2_layout.addWidget(right_spacer2)
        zone6_row1_col2_layout.setStretch(4, 1)
        
        zone6_row1_layout.addWidget(self.zone6_col2)
        zone6_row1_layout.setStretch(1, 20)  # 20%
        
        # 列3：20%宽度，添加复选框、细线和标签
        self.zone6_col3 = QWidget()
        zone6_row1_col3_layout = QHBoxLayout(self.zone6_col3)
        zone6_row1_col3_layout.setContentsMargins(0, 0, 0, 0)
        zone6_row1_col3_layout.setSpacing(5)
        
        # 左侧间隔（12.5%）
        left_spacer3 = QWidget()
        zone6_row1_col3_layout.addWidget(left_spacer3)
        zone6_row1_col3_layout.setStretch(0, 1)
        
        # 复选框
        self.CheckboxA = QCheckBox()
        self.CheckboxA.setMinimumSize(15, 15)
        self.CheckboxA.setMaximumSize(15, 15)
        # 设置初始样式（选中状态）
        self.CheckboxA.setStyleSheet("background-color: red; color: black;")
        self.CheckboxA.setChecked(True)  # 默认选中
        # 连接状态变化信号
        self.CheckboxA.stateChanged.connect(lambda state: 
            self.CheckboxA.setStyleSheet("background-color: red; color: black;") if state else 
            self.CheckboxA.setStyleSheet("background-color: lightgrey; color: black;")
        )
        zone6_row1_col3_layout.addWidget(self.CheckboxA)
        
        # 细线
        self.lineA = QFrame()
        self.lineA.setFrameShape(QFrame.HLine)
        self.lineA.setFrameShadow(QFrame.Sunken)
        self.lineA.setMinimumHeight(2)
        self.lineA.setMaximumHeight(2)
        self.lineA.setStyleSheet("background-color: red;")
        self.lineA.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        zone6_row1_col3_layout.addWidget(self.lineA)
        zone6_row1_col3_layout.setStretch(2, 4)
        
        # 标签
        self.labelA = QLabel("A")
        self.labelA.setStyleSheet("color: red;")
        self.labelA.setAlignment(Qt.AlignCenter)
        zone6_row1_col3_layout.addWidget(self.labelA)
        zone6_row1_col3_layout.setStretch(3, 1)
        
        # 右侧间隔（12.5%）
        right_spacer3 = QWidget()
        zone6_row1_col3_layout.addWidget(right_spacer3)
        zone6_row1_col3_layout.setStretch(4, 1)
        
        zone6_row1_layout.addWidget(self.zone6_col3)
        zone6_row1_layout.setStretch(2, 20)  # 20%
        
        # 列4：40%宽度
        zone6_row1_col4 = QWidget()
        zone6_row1_layout.addWidget(zone6_row1_col4)
        zone6_row1_layout.setStretch(3, 40)  # 40%
        
        # 设置行高
        zone6_row1_widget = QWidget()
        zone6_row1_widget.setLayout(zone6_row1_layout)
        zone6_row1_widget.setMinimumHeight(50)  # 与Zone6高度一致
        zone6_row1_widget.setMaximumHeight(50)  # 与Zone6高度一致
        
        # 添加行到Zone6布局
        self.zone6_layout.addWidget(zone6_row1_widget)
        
        # 安装事件过滤器以处理双击事件
        self.zone6_col1.installEventFilter(self)
        self.zone6_col2.installEventFilter(self)
        self.zone6_col3.installEventFilter(self)
        
        # 创建Zone5的布局为垂直布局
        self.zone5_layout = QVBoxLayout(self.zone5_widget)
        # 设置布局边距
        self.zone5_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        # 设置垂直间距为0
        self.zone5_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone5_layout.setAlignment(Qt.AlignTop)
        
        # 添加 row1：2列 50% 50%
        zone5_row1_layout = QHBoxLayout()
        zone5_row1_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone5_row1_layout.setSpacing(0)  # 0间距
        
        # 列1：50%宽度 - 清除数据按钮 (80% width)
        col1_layout = QHBoxLayout()
        col1_layout.setContentsMargins(0, 0, 0, 0)
        col1_layout.setSpacing(0)
        col1_layout.addStretch(10)  # 10% space on left
        self.clear_data_btn.setMinimumSize(0, 45)  # 高度45px，宽度自适应
        self.clear_data_btn.setMaximumSize(16777215, 45)  # 高度45px，宽度自适应
        self.clear_data_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 宽度自适应，高度固定
        col1_layout.addWidget(self.clear_data_btn, 80)  # 80% width
        col1_layout.addStretch(10)  # 10% space on right
        col1_widget = QWidget()
        col1_widget.setLayout(col1_layout)
        zone5_row1_layout.addWidget(col1_widget)
        zone5_row1_layout.setStretch(0, 50)  # 50% column width
        
        # 列2：50%宽度 - 启动/停止按钮 (80% width)
        col2_layout = QHBoxLayout()
        col2_layout.setContentsMargins(0, 0, 0, 0)
        col2_layout.setSpacing(0)
        col2_layout.addStretch(10)  # 10% space on left
        self.start_btn.setMinimumSize(0, 45)  # 高度45px，宽度自适应
        self.start_btn.setMaximumSize(16777215, 45)  # 高度45px，宽度自适应
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 宽度自适应，高度固定
        col2_layout.addWidget(self.start_btn, 80)  # 80% width
        col2_layout.addStretch(10)  # 10% space on right
        col2_widget = QWidget()
        col2_widget.setLayout(col2_layout)
        zone5_row1_layout.addWidget(col2_widget)
        zone5_row1_layout.setStretch(1, 50)  # 50% column width
        
        # 设置行高
        zone5_row1_widget = QWidget()
        zone5_row1_widget.setLayout(zone5_row1_layout)
        zone5_row1_widget.setMinimumHeight(45)  # 固定行高45px
        zone5_row1_widget.setMaximumHeight(45)  # 固定行高45px
        
        # 添加行到Zone5布局
        self.zone5_layout.addWidget(zone5_row1_widget)
        
        # 6. 按钮 widget (below Zone 5)
        self.buttons_widget = QWidget(main_widget)
        
        # 创建按钮布局
        self.buttons_layout = QHBoxLayout(self.buttons_widget)
        self.buttons_layout.setContentsMargins(20, 20, 20, 20)  # 边距
        self.buttons_layout.setSpacing(20)  # 按钮间距
        
        # 按钮已移动到Zone5，这里不再需要
        self.buttons_layout.addStretch()
        


        # 移除背景颜色
        
        # 创建Zone4的布局为垂直布局
        self.zone4_layout = QVBoxLayout(self.zone4_widget)
        # 设置布局边距
        self.zone4_layout.setContentsMargins(0, 0, 0, 20)  # 顶部边距为0，底部边距为20px
        # 设置垂直间距为0
        self.zone4_layout.setSpacing(0)
        # 设置布局对齐方式为顶部
        self.zone4_layout.setAlignment(Qt.AlignTop)
        
        # 添加新行：3列 5% 90% 5%
        zone4_row1_layout = QHBoxLayout()
        zone4_row1_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row1_layout.setSpacing(0)  # 0间距
        
        # 列1：5%宽度
        zone4_row1_col1 = QWidget()
        zone4_row1_layout.addWidget(zone4_row1_col1)
        zone4_row1_layout.setStretch(0, 5)  # 5%
        
        # 列2：90%宽度，添加"通信设置"标签
        zone4_row1_col2 = QWidget()
        zone4_row1_col2_layout = QHBoxLayout(zone4_row1_col2)
        zone4_row1_col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row1_col2_layout.setSpacing(0)
        
        self.zone4_row1_label = QLabel("通信设置")
        font = QFont("Microsoft YaHei", 14)  # 雅黑，14px
        self.zone4_row1_label.setFont(font)
        self.zone4_row1_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.zone4_row1_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        self.zone4_row1_label.setStyleSheet("color: grey;")  # 设置文字颜色为灰色
        zone4_row1_col2_layout.addWidget(self.zone4_row1_label)
        
        zone4_row1_layout.addWidget(zone4_row1_col2)
        zone4_row1_layout.setStretch(1, 90)  # 90%
        
        # 列3：5%宽度
        zone4_row1_col3 = QWidget()
        zone4_row1_layout.addWidget(zone4_row1_col3)
        zone4_row1_layout.setStretch(2, 5)  # 5%
        
        # 设置行高
        zone4_row1_widget = QWidget()
        zone4_row1_widget.setLayout(zone4_row1_layout)
        zone4_row1_widget.setMinimumHeight(30)  # 调整行高以容纳14px字体
        zone4_row1_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 添加新行到Zone4布局
        self.zone4_layout.addWidget(zone4_row1_widget)
        
        # 添加7px间距
        spacer_below_row1 = QWidget()
        spacer_below_row1.setMinimumHeight(7)  # 7px高度
        self.zone4_layout.addWidget(spacer_below_row1)
        
        # 添加新行：5列 10% 30% 10% 40% 10%
        zone4_row2_layout = QHBoxLayout()
        zone4_row2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row2_layout.setSpacing(0)  # 0间距
        
        # 列1：10%宽度
        zone4_row2_col1 = QWidget()
        zone4_row2_layout.addWidget(zone4_row2_col1)
        zone4_row2_layout.setStretch(0, 10)  # 10%
        
        # 列2：30%宽度，添加下拉菜单
        zone4_row2_col2 = QWidget()
        zone4_row2_col2_layout = QHBoxLayout(zone4_row2_col2)
        zone4_row2_col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row2_col2_layout.setSpacing(0)
        

        
        # 下拉菜单
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet("border: none; background-color: white; padding: 0px; margin: 0px; color: black; font-size: 16px;")
        self.port_combo.setMinimumHeight(33)  # 减少5%高度 (35 * 0.95 = 33.25)
        self.port_combo.setMaximumHeight(33)  # 减少5%高度
        self.port_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)  # 宽度适应内容，高度固定
        self.refresh_serial_ports()
        
        # 左对齐下拉菜单
        zone4_row2_col2_layout.addWidget(self.port_combo)
        
        zone4_row2_layout.addWidget(zone4_row2_col2)
        zone4_row2_layout.setStretch(1, 30)  # 30%
        
        # 列3：10%宽度，添加刷新按钮
        zone4_row2_col3 = QWidget()
        zone4_row2_col3_layout = QHBoxLayout(zone4_row2_col3)
        zone4_row2_col3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row2_col3_layout.setSpacing(0)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setMinimumSize(35, 35)  # 固定高度
        self.refresh_btn.setMaximumSize(35, 35)  # 固定高度
        self.refresh_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 固定大小
        self.refresh_btn.setStyleSheet("border: none; background-color: #0078D7; font-size: 20px; color: white; padding: 0px; margin: 0px; font-weight: bold;")
        self.refresh_btn.clicked.connect(self.refresh_serial_ports)
        self.refresh_btn.setToolTip("Refresh serial ports")
        
        # 添加按下和释放事件处理
        self.refresh_btn.pressed.connect(self.on_refresh_button_pressed)
        self.refresh_btn.released.connect(self.on_refresh_button_released)
        
        zone4_row2_col3_layout.addWidget(self.refresh_btn)
        
        zone4_row2_layout.addWidget(zone4_row2_col3)
        zone4_row2_layout.setStretch(2, 10)  # 10%
        
        # 列4：40%宽度，添加连接按钮
        zone4_row2_col4 = QWidget()
        zone4_row2_col4_layout = QHBoxLayout(zone4_row2_col4)
        zone4_row2_col4_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row2_col4_layout.setSpacing(0)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setMinimumHeight(35)  # 固定高度
        self.connect_btn.setMaximumHeight(35)  # 固定高度
        self.connect_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)  # 不填充宽度，使用首选大小
        self.connect_btn.setMaximumWidth(100)  # 减少20%宽度
        self.connect_btn.setStyleSheet("border: none; border-radius: 17px; background-color: white; padding: 0px; margin: 0px; font-size: 16px;")
        self.connect_btn.setToolTip("连接到串口")
        self.connect_btn.clicked.connect(self.toggle_connection)
        zone4_row2_col4_layout.addWidget(self.connect_btn)
        
        zone4_row2_layout.addWidget(zone4_row2_col4)
        zone4_row2_layout.setStretch(3, 40)  # 恢复到40%宽度
        
        # 列5：10%宽度，添加状态图标
        zone4_row2_col5 = QWidget()
        zone4_row2_col5_layout = QVBoxLayout(zone4_row2_col5)
        zone4_row2_col5_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        zone4_row2_col5_layout.setSpacing(0)  # 0间距
        zone4_row2_col5_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
        
        # TxStatus图标
        self.tx_status_icon = QLabel("●")
        self.tx_status_icon.setFont(QFont("Arial", 12))
        self.tx_status_icon.setStyleSheet("color: darkgrey; padding: 0px; margin: 0px;")
        self.tx_status_icon.setAlignment(Qt.AlignCenter)
        self.tx_status_icon.setMinimumHeight(17)  # 固定高度
        self.tx_status_icon.setMaximumHeight(17)  # 固定高度
        self.tx_status_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 固定大小
        zone4_row2_col5_layout.addWidget(self.tx_status_icon)
        
        # RxStatus图标
        self.rx_status_icon = QLabel("●")
        self.rx_status_icon.setFont(QFont("Arial", 12))
        self.rx_status_icon.setStyleSheet("color: darkgrey; padding: 0px; margin: 0px;")
        self.rx_status_icon.setAlignment(Qt.AlignCenter)
        self.rx_status_icon.setMinimumHeight(17)  # 固定高度
        self.rx_status_icon.setMaximumHeight(17)  # 固定高度
        self.rx_status_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 固定大小
        zone4_row2_col5_layout.addWidget(self.rx_status_icon)
        
        zone4_row2_layout.addWidget(zone4_row2_col5)
        zone4_row2_layout.setStretch(4, 10)  # 恢复到10%宽度
        
        # 设置行高
        zone4_row2_widget = QWidget()
        zone4_row2_widget.setLayout(zone4_row2_layout)
        zone4_row2_widget.setMinimumHeight(35)  # 调整行高
        zone4_row2_widget.setStyleSheet("border: none;")  # 移除边框
        
        # 添加新行到Zone4布局
        self.zone4_layout.addWidget(zone4_row2_widget)
        

        
        # 添加新行（3列）在现有行1上方
        # 创建行布局，设置0间距
        new_row_layout = QHBoxLayout()
        new_row_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        new_row_layout.setSpacing(0)  # 0间距
        
        # 列1：5%宽度
        col1 = QWidget()
        new_row_layout.addWidget(col1)
        new_row_layout.setStretch(0, 5)  # 5%
        
        # 列2：剩余宽度（90%），添加"实时数据"标签
        col2 = QWidget()
        col2_layout = QHBoxLayout(col2)
        col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        col2_layout.setSpacing(0)
        
        label = QLabel("实时数据")
        font = QFont("Microsoft YaHei", 14)  # 雅黑，14px
        label.setFont(font)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
        label.setStyleSheet("color: grey;")  # 设置文字颜色为灰色
        col2_layout.addWidget(label)
        
        new_row_layout.addWidget(col2)
        new_row_layout.setStretch(1, 90)  # 90%
        
        # 列3：5%宽度，添加状态指示器
        col3 = QWidget()
        col3_layout = QHBoxLayout(col3)
        col3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
        col3_layout.setSpacing(0)  # 0间距
        
        # 添加状态指示器
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 12))
        self.status_indicator.setStyleSheet("color: #FFFF99; padding: 0px; margin: 0px;")  # 初始为浅黄色
        self.status_indicator.setAlignment(Qt.AlignCenter)  # 水平居中
        self.status_indicator.setMinimumHeight(17)  # 固定高度
        self.status_indicator.setMaximumHeight(17)  # 固定高度
        self.status_indicator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 固定大小
        col3_layout.addWidget(self.status_indicator)
        col3_layout.setAlignment(Qt.AlignCenter)  # 水平居中
        col3_layout.setAlignment(Qt.AlignVCenter)  # 垂直居中
        
        new_row_layout.addWidget(col3)
        new_row_layout.setStretch(2, 5)  # 5%
        
        # 设置行高
        new_row_widget = QWidget()
        new_row_widget.setLayout(new_row_layout)
        new_row_widget.setMinimumHeight(30)  # 调整行高以容纳14px字体
        # 移除边框
        
        # 添加新行到Zone2布局
        self.zone2_layout.addWidget(new_row_widget)
        
        # 添加行1下方的7px间距
        self.spacer_below_row1 = QWidget()
        self.spacer_below_row1.setMinimumHeight(7)  # 默认7px高度
        self.zone2_layout.addWidget(self.spacer_below_row1)
        
        # 标签文本列表
        labels = ["电压", "电流", "功耗", "容量", "功率", "耗时"]
        # 单位列表
        units = ["V", "A", "Wh", "mAh", "W", "HMS"]
        
        # 添加6行数据，每行4列
        for i in range(6):
            # 创建行布局，设置0间距
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
            row_layout.setSpacing(0)  # 0间距
            
            # 列1：10%宽度
            col1 = QWidget()
            row_layout.addWidget(col1)
            row_layout.setStretch(0, 10)  # 10%
            
            # 列2：20%宽度，添加标签
            col2 = QWidget()
            col2_layout = QHBoxLayout(col2)
            col2_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
            col2_layout.setSpacing(0)
            
            label = QLabel(labels[i])
            font = QFont("SimHei", 16)  # 黑体，16px
            label.setFont(font)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
            col2_layout.addWidget(label)
            
            row_layout.addWidget(col2)
            row_layout.setStretch(1, 20)  # 20%
            
            # 列3：50%宽度，添加参数值
            col3 = QWidget()
            col3_layout = QHBoxLayout(col3)
            col3_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
            col3_layout.setSpacing(0)  # 0间距
            
            # 创建参数值标签
            value_label = QLabel("00.000" if i == 0 else "00.000" if i == 1 else "0000.0" if i == 2 else "00000" if i == 3 else "000.00" if i == 4 else "")
            # 为第6行（耗时）设置不同的字体大小
            font_size = 20 if i == 5 else 24
            font = QFont("Arial", font_size)  # Arial
            value_label.setFont(font)
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setContentsMargins(0, 0, 0, 0)  # 0边距
            col3_layout.addWidget(value_label)
            
            # 存储标签引用以便后续更新
            if not hasattr(self, 'zone2_value_labels'):
                self.zone2_value_labels = []
            self.zone2_value_labels.append(value_label)
            
            row_layout.addWidget(col3)
            row_layout.setStretch(2, 40)  # 40%
            
            # 列4：剩余宽度（30%），添加单位标签
            col4 = QWidget()
            col4_layout = QHBoxLayout(col4)
            col4_layout.setContentsMargins(0, 0, 0, 0)  # 0边距
            col4_layout.setSpacing(0)
            
            unit_label = QLabel(units[i])
            font = QFont("Arial", 18)  # Arial，18pt
            unit_label.setFont(font)
            unit_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            unit_label.setContentsMargins(5, 0, 0, 0)  # 仅左侧5px边距，无上下边距
            col4_layout.addWidget(unit_label)
            
            row_layout.addWidget(col4)
            row_layout.setStretch(3, 30)  # 30%
            
            # 设置行高
            row_widget = QWidget()
            row_widget.setLayout(row_layout)
            row_widget.setMinimumHeight(35)  # 调整行高以容纳16px字体
            # 移除边框
            
            # 添加行到Zone2布局
            self.zone2_layout.addWidget(row_widget)
        
        # 添加行7下方的3px间距
        self.spacer_after_row7 = QWidget()
        self.spacer_after_row7.setMinimumHeight(3)  # 默认3px高度
        self.zone2_layout.addWidget(self.spacer_after_row7)
        
        # 3. 刻度线widget (Power)
        self.scale_line = ScaleLineWidget(
            main_widget, 
            min_value=0, 
            max_value=50, 
            color=ColorP,  # 使用全局变量
            label="(W)",
            scale_type="P"
        )
        self.scale_line.setParent(main_widget)
        
        # 4. 温度显示widget
        self.temperature_label = QLabel("0.0°C", main_widget)
        font = QFont("Arial", 14)
        self.temperature_label.setFont(font)
        self.temperature_label.setStyleSheet("color: purple;")
        self.temperature_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        
        # 4. 第二个刻度线widget（Voltage）
        self.scale_line2 = ScaleLineWidget(
            main_widget, 
            min_value=2, 
            max_value=5, 
            color=ColorV,  # 使用全局变量
            label="(V)", 
            marker_direction="left",  # 标记指向左侧
            alignment="right",  # 数字右对齐，与橙色刻度线保持一致
            scale_type="V"
        )
        self.scale_line2.setParent(main_widget)
        
        # 5. 第三个刻度线widget（Current）
        self.scale_line3 = ScaleLineWidget(
            main_widget, 
            min_value=0, 
            max_value=10, 
            color=ColorA,  # 使用全局变量
            label="(A)", 
            marker_direction="left",  # 标记指向左侧，与V Scale一致
            alignment="right",  # 数字右对齐，与V Scale一致
            scale_type="A"
        )
        self.scale_line3.setParent(main_widget)
        
        # 6. 第四个刻度线widget（T Scale，水平）
        from PySide6.QtGui import QColor
        self.scale_line4 = ScaleLineWidget(
            main_widget, 
            scale_width=300,  # 初始宽度
            min_value=0, 
            max_value=300,  # 范围改为0-300
            color=QColor(128, 128, 128),  # 灰色
            label="(S)", 
            marker_direction="down",  # 标记指向下方
            alignment="center",  # 数字居中对齐
            orientation="horizontal",  # 水平方向
            scale_type="T"
        )
        self.scale_line4.setParent(main_widget)
        
        # 连接窗口大小变化信号
        self.resizeEvent = self.on_resize
        
        # 连接刻度线双击信号
        self.scale_line.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line))
        self.scale_line2.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line2))
        self.scale_line3.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line3))
        self.scale_line4.doubleClicked.connect(lambda: self.on_scale_double_click(self.scale_line4))
        

        
        # 初始调整大小
        self.on_resize(None)
        
        # 暂时移除轴的双击事件，因为我们已经重新设计了曲线显示区域
        
    def on_mode_changed(self, index):
        # 当下拉菜单选择改变时，更新 mode 变量
        self.mode = self.row2_combo.currentData()
        
    def on_cutoff_voltage_changed(self, text):
        # 当截止电压输入框改变时，更新 Vset 变量
        try:
            value = float(text)
            if 0 <= value <= 50:
                self.Vset = value
        except ValueError:
            pass
        
    def on_load_current_changed(self, text):
        # 当负载电流输入框改变时，更新 Iset 变量
        try:
            value = float(text)
            if 0 <= value <= 50:
                self.Iset = value
        except ValueError:
            pass
        
    def on_refresh_button_pressed(self):
        # 当刷新按钮被按下时
        self.refresh_btn.setMinimumSize(28, 28)  # 减小尺寸
        self.refresh_btn.setMaximumSize(33, 33)
        self.refresh_btn.setStyleSheet("border: 1px solid gray; background-color: #005A9E; font-size: 18px; color: white; padding: 0px; margin: 0px; font-weight: bold;")  # 改变颜色
        
    def on_refresh_button_released(self):
        # 当刷新按钮被释放时
        self.refresh_btn.setMinimumSize(30, 30)  # 恢复尺寸
        self.refresh_btn.setMaximumSize(35, 35)
        self.refresh_btn.setStyleSheet("border: 1px solid gray; background-color: #0078D7; font-size: 20px; color: white; padding: 0px; margin: 0px; font-weight: bold;")  # 恢复颜色
        
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
        if dialog.exec() == QDialog.Accepted:
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
    
    def update_t_scale(self, new_max):
        """更新T刻度范围"""
        if hasattr(self, 'scale_line4'):
            current_min = self.scale_line4.min_value
            self.scale_line4.set_range(current_min, new_max)
            self.scale_line4.update()
            self.display_widget.update()
    
    def on_scale_double_click(self, scale_widget):
        # 双击刻度线修改范围
        current_min = scale_widget.min_value
        current_max = scale_widget.max_value
        
        # 使用自定义对话框同时设置最小值和最大值
        dialog = ScaleRangeDialog(current_min, current_max, self)
        if dialog.exec() == QDialog.Accepted:
            new_min, new_max = dialog.get_values()
            if new_min is not None and new_max is not None:
                # 更新刻度范围
                scale_widget.set_range(new_min, new_max)
                # 强制刷新显示
                scale_widget.update()
                
                # 检查是否为T scale
                if hasattr(scale_widget, 'scale_type') and scale_widget.scale_type == "T":
                    # 检查RunTime是否大于等于Tmax
                    global RunTime
                    if RunTime >= new_max:
                        # 自动调整Tmax为RunTime + 60
                        new_tmax = RunTime + 60
                        self.update_t_scale(new_tmax)
        
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
        
        # Zone2 is now empty, so no font size calculation needed
        # 使用默认字体作为Zone2的字体
        zone2_title_font = QFont("SimHei", 14, QFont.Light)  # 使用黑体字体
        
        # 更新Zone3和Zone4的标题字体以匹配Zone2的字体
        # Zone3 title removed, font setting commented out
        # if hasattr(self, 'zone3_title'):
        #     self.zone3_title.setFont(zone2_title_font)
        if hasattr(self, 'zone4_row1_label'):
            self.zone4_row1_label.setFont(zone2_title_font)
        
        # 计算Zone2的高度：标题高度
        # 计算标题高度
        title_font_metrics = QFontMetrics(zone2_title_font)
        title_height = title_font_metrics.height()
        
        # 计算Zone2的高度：标题高度
        zone2_height = title_height + 20  # 标题高度加上一些边距
            
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
        
        # 计算3%的水平间距
        horizontal_spacing = zone2_width * 0.03
        
        # 调整间距高度，与Zone2宽度成比例
        # 默认宽度200px对应指定的间距值
        base_width = 200
        
        # 计算新的间距高度
        if hasattr(self, 'spacer_below_row1'):
            # 7px间距
            spacer_below_height = int((zone2_width / base_width) * 7)
            spacer_below_height = max(3, min(spacer_below_height, 14))
            self.spacer_below_row1.setMinimumHeight(spacer_below_height)
            self.spacer_below_row1.setMaximumHeight(spacer_below_height)
        
        if hasattr(self, 'spacer_after_row7'):
            # 3px间距
            spacer_after_height = int((zone2_width / base_width) * 3)
            spacer_after_height = max(1, min(spacer_after_height, 6))
            self.spacer_after_row7.setMinimumHeight(spacer_after_height)
            self.spacer_after_row7.setMaximumHeight(spacer_after_height)
        
        # 计算Zone2高度：行高 + 间距高度
        row1_height = 30  # 第一行高度
        row_height = 35  # 其他行高度
        num_rows = 7  # 1新行 + 6原有行
        
        # 计算所有间距的总高度
        total_spacer_height = 0
        if hasattr(self, 'spacer_below_row1'):
            total_spacer_height += self.spacer_below_row1.minimumHeight()
        if hasattr(self, 'spacer_after_row7'):
            total_spacer_height += self.spacer_after_row7.minimumHeight()
        
        # 计算总高度
        zone2_height = row1_height + (row_height * 6) + total_spacer_height
        
        # 重新设置Zone2大小
        self.zone2_widget.setGeometry(
            int(zone2_x),
            int(top_margin),
            int(zone2_width),
            int(zone2_height)
        )
        
        # 调整Zone2布局的边距，不设置任何间距
        self.zone2_layout.setContentsMargins(0, 0, 0, 0)
            
        # 计算Zone3的位置和大小
        zone3_x = zone2_x
        zone3_y = top_margin + zone2_height + top_margin  # 与Zone2的间距与Zone2上方的间距相同
        zone3_width = zone2_width  # 与Zone2宽度相同
        # 精确计算 Zone3 高度以确保底部边距与顶部边距相同（20px）
        # 确保所有绿色间距保持不变
        zone3_height = 120  # 调整高度以正好容纳四行内容
        
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
        zone4_title_spacing = 0  # setContentsMargins 中设置的顶部边距
        
        # 计算字体和高度
        title_font_metrics = QFontMetrics(self.zone4_row1_label.font())
        title_height = title_font_metrics.height()
        
        # 计算空行高度（与标题字体相同）
        line_height = title_height
        
        port_font_metrics = QFontMetrics(self.port_combo.font())
        port_label_height = port_font_metrics.height()
        port_combo_height = 30  # pull-down menu 高度
        button_height = 45  # refresh_btn 和 connect_btn 高度
        spacing_height = 10  # 各元素之间的间距
        
        # 计算 Zone4 的高度：顶部边距 + 标题 + 7px间距 + 新行高度 + port_widget 高度 + 底部边距
        # port_widget 高度 = max(port_combo_height, button_height)  # 取较大值
        port_widget_height = max(port_combo_height, button_height)  # 下拉菜单和按钮的最大高度
        row2_height = 35  # 新行的高度
        spacing_below_row1 = 7  # 7px间距
        zone4_height = zone4_title_spacing + title_height + spacing_below_row1 + row2_height + port_widget_height + zone4_title_spacing  # 顶部边距 + 标题 + 7px间距 + 新行 + 内容高度 + 底部边距
        
        # 使用绝对定位设置 Zone4 的位置和大小
        self.zone4_widget.setGeometry(
            int(zone4_x),
            int(zone4_y),
            int(zone4_width),
            int(zone4_height)
        )
        
        # 计算 Zone5 的位置和大小
        zone5_x = zone2_x
        zone5_y = zone4_y + zone4_height + top_margin  # 与 Zone4 的间距与其他区域之间的间距相同
        zone5_width = zone2_width  # 与 Zone2 宽度相同
        zone5_height = 45  # 调整高度以正好容纳45px行
        
        # 使用绝对定位设置 Zone5 的位置和大小
        self.zone5_widget.setGeometry(
            int(zone5_x),
            int(zone5_y),
            int(zone5_width),
            int(zone5_height)
        )
        
        # 计算按钮 widget 的位置和大小（位于 Zone5 下方）
        buttons_x = zone5_x
        buttons_y = zone5_y + zone5_height + top_margin  # 与 Zone5 的间距与其他区域之间的间距相同
        buttons_width = zone5_width  # 与 Zone5 宽度相同
        buttons_height = 100  # 按钮区域高度
        
        # 使用绝对定位设置按钮 widget 的位置和大小
        self.buttons_widget.setGeometry(
            int(buttons_x),
            int(buttons_y),
            int(buttons_width),
            int(buttons_height)
        )
        
        # 计算 Zone6 的位置和大小
        zone6_x = left_margin  # 与 Zone1 相同的 x 位置
        zone6_width = zone1_width  # 与 Zone1 相同的宽度
        zone6_height = 50  # 合理的高度
        
        # 计算垂直空间：Zone1 底部到主布局底部
        zone1_bottom = top_margin + zone1_height
        vertical_space = ui_height - zone1_bottom
        
        # 垂直居中：Zone6 位于 Zone1 底部和主布局底部的中间
        zone6_y = zone1_bottom + (vertical_space - zone6_height) / 2
        
        # 使用绝对定位设置Zone6的位置和大小
        self.zone6_widget.setGeometry(
            int(zone6_x),
            int(zone6_y),
            int(zone6_width),
            int(zone6_height)
        )
        
        # 定位温度显示标签到右下角，所有其他widget下方
        temperature_x = ui_width - right_margin - 150  # 150px width
        temperature_y = ui_height - 40  # 40px from bottom
        self.temperature_label.setGeometry(
            int(temperature_x),
            int(temperature_y),
            150,
            30
        )
        self.temperature_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        # 确保温度标签在最上层
        self.temperature_label.raise_()
        
        # 计算并显示 Zone4 的间距
        # Zone4 结构：顶部边距 (20px) + title + 空行 (line_height) + port_widget(包含 port_label + spacing + combo + spacing + buttons) + 底部边距 (20px)
        # port_widget 底部到 Zone4 底部的间距应该等于 zone4_title_spacing (20px)
        # port_widget 底部位置 = zone4_title_spacing + title_height + line_height + port_label_height + spacing_height + port_combo_height + spacing_height + button_height
        # port_widget 底部到 Zone4 底部 = zone4_height - (zone4_title_spacing + title_height + line_height + port_label_height + spacing_height + port_combo_height + spacing_height + button_height)
        port_widget_bottom_to_zone4_bottom = zone4_height - (zone4_title_spacing + title_height + line_height + port_label_height + spacing_height + port_combo_height + spacing_height + button_height)
        

        

        
        # Zone2 is now empty, so no label updates needed
        # 强制更新布局
        self.zone2_widget.update()
        self.zone2_widget.repaint()
        

        
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
        
        # 计算Zone5的位置和宽度
        zone5_x = zone2_x
        
        # 确保P Scale的右侧不与Zone5重叠
        scale_width = zone5_x - scale_x - 10  # 10px margin
        if scale_width < 50:
            scale_width = 50  # 最小宽度
        
        # 保持P Scale的实际高度不变，确保刻度线延伸到T Scale
        self.scale_line.set_height(plottable_height)
        
        # 设置widget的几何形状，使其足够大以包含完整的刻度线
        # 包括底部与T Scale对齐的点
        self.scale_line.setGeometry(int(scale_x), int(scale_y), int(scale_width), int(plottable_height + 2 * self.scale_line.padding))
        
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
        
        # 主循环执行状态标志
        self.main_loop_running = False
        
        # 主循环定时器 - 设置为最高优先级
        self.main_loop_timer = QTimer()
        self.main_loop_timer.setTimerType(Qt.PreciseTimer)  # 使用精确定时器
        self.main_loop_timer.timeout.connect(self.MainLoop)
        self.main_loop_timer.start(1000)  # 1秒更新一次
        
        # 时间计数
        self.start_time = time.time()
        self.time_max = 300  # 默认5分钟
        
    def toggle_curve(self, key, state):
        self.curves[key].setVisible(state == Qt.Checked)
        
    def set_mode(self, index):
        if index != self.mode:
            self.mode = index
            # 这里应该调用setMode函数
        pass
    
    def set_current(self, value):
        # 这里应该调用setCurrent函数
        pass
    
    def set_voltage(self, value):
        # 这里应该调用setVoltage函数
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
        
    def MainLoop(self):
        # 主循环函数
        self.main_loop_running = True
        
        # 声明全局变量
        global RunTime
        
        import datetime
        current_time = datetime.datetime.now().strftime('%M:%S')
        print(f"MainLoop [{current_time}]")
        
        # 更新状态指示器为红色（MainLoop执行中）
        if hasattr(self, 'status_indicator') and self.is_connected:
            self.status_indicator.setStyleSheet("color: red; padding: 0px; margin: 0px;")
            # 强制UI更新
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        
        # 使用PX100协议查询设备数据
        if self.is_connected:
            import time
            
            # 初始化QueryTimedOut标志
            if not hasattr(self, 'QueryTimedOut'):
                self.QueryTimedOut = 0
            
            # 设置参数
            TTimeOut = 0.1  # 100ms
            TDelay = 0.001  # 1ms
            
            # 1. 开始查询序列前的准备
            # 1.1 清除接收缓冲区
            self.serial_buffer.clear()
            # 1.2 设置QueryTimedOut标志为0
            self.QueryTimedOut = 0
            
            # 2. 运行10个查询
            queries = [
                ('ReadLStatus', b'\xb1\xb2\x10\x00\x00\xb6', 0x10),  # 第一次ReadLStatus，响应将被忽略
                ('ReadLStatus', b'\xb1\xb2\x10\x00\x00\xb6', 0x10),  # 第二次ReadLStatus，使用此响应
                ('ReadSmV', b'\xb1\xb2\x11\x00\x00\xb6', 0x11),
                ('ReadSmA', b'\xb1\xb2\x12\x00\x00\xb6', 0x12),
                ('ReadSTimer', b'\xb1\xb2\x13\x00\x00\xb6', 0x13),
                ('ReadSmAh', b'\xb1\xb2\x14\x00\x00\xb6', 0x14),
                ('ReadSmWh', b'\xb1\xb2\x15\x00\x00\xb6', 0x15),
                ('ReadMosT', b'\xb1\xb2\x16\x00\x00\xb6', 0x16),
                ('ReadIset', b'\xb1\xb2\x17\x00\x00\xb6', 0x17),
                ('ReadVset', b'\xb1\xb2\x18\x00\x00\xb6', 0x18),
                ('ReadTset', b'\xb1\xb2\x19\x00\x00\xb6', 0x19)  # 一次ReadTset
            ]
            
            # 存储查询结果
            results = {}
            
            # 跟踪ReadLStatus的次数
            readlstatus_count = 0
            
            for query_name, command, third_byte in queries:
                # 2.2.1 清除接收缓冲区
                self.serial_buffer.clear()
                # 2.2.2 发送查询
                self.send_data(command)
                # 2.2.3 等待响应，超时时间为TTimeOut
                start_time = time.time()
                response = None
                while time.time() - start_time < TTimeOut:
                    if hasattr(self.serial_port, 'in_waiting'):
                        if self.serial_port.in_waiting > 0:
                            data = self.serial_port.read(self.serial_port.in_waiting)
                            self.serial_buffer.extend(data)
                            # 2.2.4 扫描并搜索头部，验证头部和尾部
                            header = b'\xca\xcb'
                            trailer = b'\xce\xcf'
                            header_index = self.serial_buffer.find(header)
                            while header_index != -1:
                                if len(self.serial_buffer) >= header_index + 7:
                                    if self.serial_buffer[header_index + 5:header_index + 7] == trailer:
                                        # 找到有效的响应
                                        response = self.serial_buffer[header_index:header_index + 7]
                                        break
                                header_index = self.serial_buffer.find(header, header_index + 1)
                            if response:
                                break
                    # 小延迟避免忙等
                    time.sleep(0.01)
                
                # 处理响应
                if response:
                    # 2.2.4.2 有效响应，填充全局变量
                    if query_name == 'ReadLStatus':
                        readlstatus_count += 1
                        # 忽略第一次ReadLStatus的响应，只使用第二次的
                        if readlstatus_count == 2:
                            results['status'] = response[4]
                    elif query_name == 'ReadSmV':
                        results['voltage'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadSmA':
                        results['current'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadSTimer':
                        # 提取时间数据 (SH, SM, SS)
                        self.H = response[2]  # 小时
                        self.M = response[3]  # 分钟
                        self.S = response[4]  # 秒
                        # 计算RunTime
                        RunTime = self.S + self.M * 60 + self.H * 3600
                        
                        # 检查RunTime是否大于等于Tmax
                        if hasattr(self, 'scale_line4'):
                            tmax = self.scale_line4.max_value
                            if RunTime >= tmax:
                                # 自动调整Tmax为RunTime + 60
                                new_tmax = RunTime + 60
                                self.update_t_scale(new_tmax)
                        results['timer'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadSmAh':
                        results['capacity'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadSmWh':
                        results['energy'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadMosT':
                        smost = (response[2] << 16) | (response[3] << 8) | response[4]
                        results['most'] = smost
                        # Update global MosT variable
                        global MosT
                        MosT = smost  # Use raw SMosT value
                    elif query_name == 'ReadIset':
                        results['iset'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadVset':
                        results['vset'] = (response[2] << 16) | (response[3] << 8) | response[4]
                    elif query_name == 'ReadTset':
                        results['tset'] = (response[2] << 16) | (response[3] << 8) | response[4]
                else:
                    # 2.2.4.1 超时，设置QueryTimedOut标志为查询的第三个字节
                    self.QueryTimedOut = third_byte
                    print(f"Query timed out: 0x{third_byte:02X}")
                
                # 2.2.5 延迟TDelay并移至下一个查询
                time.sleep(TDelay)
            
            # 分配变量
            energy = results.get('energy')
            capacity = results.get('capacity')
            iset = results.get('iset')
            vset = results.get('vset')
            voltage = results.get('voltage')
            current = results.get('current')
            
            Wh = energy / 1000 if energy is not None else None
            mAh = capacity if capacity is not None else None
            Iset = iset / 100 if iset is not None else None
            Vset = vset / 100 if vset is not None else None
            
            # 计算实时数据变量
            V = voltage / 1000 if voltage is not None else None
            A = current / 1000 if current is not None else None
            W = (voltage * current) / 1000000 if voltage is not None and current is not None else None
            
            # 存储为实例变量，供update_data方法使用
            self.V = V if V is not None else 4.0
            self.A = A if A is not None else 1.0
            

            
            # 更新Zone2显示标签
            if hasattr(self, 'zone2_value_labels') and len(self.zone2_value_labels) >= 6:
                if V is not None:
                    self.zone2_value_labels[0].setText(f"{V:06.3f}")  # 电压 (V) - 00.000格式
                if A is not None:
                    self.zone2_value_labels[1].setText(f"{A:06.3f}")  # 电流 (A) - 00.000格式
                if Wh is not None:
                    self.zone2_value_labels[2].setText(f"{Wh:06.1f}")  # 功耗 (Wh) - 0000.0格式
                if mAh is not None:
                    self.zone2_value_labels[3].setText(f"{mAh:05.0f}")  # 容量 (mAh) - 00000格式
                if W is not None:
                    self.zone2_value_labels[4].setText(f"{W:06.2f}")  # 功率 (W) - 000.00格式
                # 显示时间 HH:MM:SS
                time_str = f"{self.H:02d}:{self.M:02d}:{self.S:02d}"
                self.zone2_value_labels[5].setText(time_str)
            
            if hasattr(self, 'row3_entry') and Vset is not None:
                # Update Vset entry box
                self.row3_entry.setText(f"{Vset:.2f}")
                self.Vset = Vset
            
            if hasattr(self, 'row4_entry') and Iset is not None:
                # Update Iset entry box
                self.row4_entry.setText(f"{Iset:.2f}")
                self.Iset = Iset

            # 更新温度显示
            if hasattr(self, 'temperature_label'):
                self.update_temperature_display()

            # 根据SLStatus更新OnOff按钮状态
            status = results.get('status')
            # 存储状态为实例变量，供OverlayWidget使用
            self.status = status if status is not None else 0
            
            if status is not None:
                if status == 1:
                    # SLStatus=1, 设备运行中
                    self.start_btn.setText("停止")
                    self.start_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: red; color: white; padding: 0px; margin: 0px; font-size: 17px;")
                    # 打印RunTime和V(Runtime)到控制台
                    V = voltage / 1000 if voltage is not None else None
                    print(f"{RunTime}     {V if V is not None else 'N/A'}")
                    # 只有当SLStatus=1时才添加新数据点
                    self.update_data()
                else:
                    # SLStatus=0, 设备停止
                    self.start_btn.setText("启动")
                    self.start_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: white; padding: 0px; margin: 0px; font-size: 17px;")
        
        # 更新状态指示器为绿色（MainLoop执行完成）
        if hasattr(self, 'status_indicator') and self.is_connected:
            self.status_indicator.setStyleSheet("color: green; padding: 0px; margin: 0px;")
            # 强制UI更新
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        
        # 主循环执行完成
        self.main_loop_running = False
        
    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        
    def toggle_connection(self):
        if not self.is_connected:
            # 立即更改按钮为黄色，显示"连接中"
            self.connect_btn.setText("连接中")
            self.connect_btn.setStyleSheet("border: none; border-radius: 17px; background-color: yellow; padding: 0px; margin: 0px; font-size: 12px;")
            
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
                        self.connect_btn.setStyleSheet("border: none; border-radius: 17px; background-color: white; padding: 0px; margin: 0px; font-size: 16px;")
                        return
                    
                    # 尝试多次打开串口，处理有数据输入的情况
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            # 尝试使用不同的端口名称格式
                            port_name = port
                            if not port.startswith('COM'):
                                port_name = 'COM' + port
                            
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
                            self.connect_btn.setStyleSheet("border: none; border-radius: 17px; background-color: lightgreen; padding: 0px; margin: 0px; font-size: 16px;")
                            # 更改端口下拉菜单为绿色并禁用
                            self.port_combo.setStyleSheet("border: none; background-color: white; padding: 2px; font-size: 16px;")
                            self.port_combo.setEnabled(False)
                            # 更新状态指示器为绿色（初始状态，MainLoop未执行）
                            if hasattr(self, 'status_indicator'):
                                self.status_indicator.setStyleSheet("color: green; padding: 0px; margin: 0px;")
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
                    self.connect_btn.setStyleSheet("border: none; border-radius: 17px; background-color: white; padding: 0px; margin: 0px; font-size: 12px;")
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
            self.connect_btn.setStyleSheet("border: none; border-radius: 17px; background-color: white; padding: 0px; margin: 0px; font-size: 16px;")
            # 恢复端口下拉菜单为原始颜色并启用
            self.port_combo.setStyleSheet("border: none; background-color: white; padding: 2px; font-size: 16px;")
            self.port_combo.setEnabled(True)
            # 更新状态指示器为浅黄色
            if hasattr(self, 'status_indicator'):
                self.status_indicator.setStyleSheet("color: #FFFF99; padding: 0px; margin: 0px;")
            
    def update_data(self):
        # 只有当SLStatus=1时才更新数据
        sl_status = getattr(self, 'status', 0)
        if sl_status != 1:
            return
        
        # 使用全局RunTime作为时间值
        global RunTime
        current_time = RunTime
        
        # 使用实际电压数据，如果没有则使用默认值
        voltage = getattr(self, 'V', 4.0)  # 使用从MainLoop获取的电压值
        current = getattr(self, 'A', 1.0)  # 使用从MainLoop获取的电流值
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
    
    def send_data(self, data):
        # 发送数据到串口
        if self.is_connected and self.serial_port:
            try:
                # 清除接收缓冲区
                self.serial_buffer.clear()
                # 正在发送数据
                self.update_tx_status(True)
                self.serial_port.write(data)
                # 短暂延迟后恢复状态
                QTimer.singleShot(500, lambda: self.update_tx_status(False))
                return True
            except Exception as e:
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
    
    def process_serial_data(self):
        """Process serial data continuously to detect 36-byte frames"""
        if self.is_connected and self.serial_port:
            try:
                # 读取可用数据
                if hasattr(self.serial_port, 'in_waiting'):
                    if self.serial_port.in_waiting > 0:
                        # 正在接收数据
                        self.update_rx_status(True)
                        data = self.serial_port.read(self.serial_port.in_waiting)
                        # 添加数据到缓冲区
                        self.serial_buffer.extend(data)
                        # 处理串行缓冲区，检测数据帧
                        self.process_serial_buffer()
                        # 短暂延迟后恢复状态
                        QTimer.singleShot(500, lambda: self.update_rx_status(False))
            except Exception as e:
                pass
    
    def process_serial_buffer(self):
        """Process serial buffer to detect and handle 36-byte data frames"""
        buffer = self.serial_buffer
        frame_start = b'\xff\x55\x01'
        frame_length = 36
        
        # 搜索帧起始序列
        start_index = buffer.find(frame_start)
        
        while start_index != -1:
            # 检测到头部，显示header...
            print("header...", end="")
            # 检查是否有足够的数据来完成帧
            if len(buffer) >= start_index + frame_length:
                # 提取完整帧
                frame = buffer[start_index:start_index + frame_length]
                # 输出状态帧信息
                print("status frame")
                # 从缓冲区中移除已处理的帧
                self.serial_buffer = buffer[start_index + frame_length:]
                # 继续搜索下一个帧
                buffer = self.serial_buffer
                start_index = buffer.find(frame_start)
            else:
                # 没有足够的数据，保留当前缓冲区
                break
    
    # PX100 Protocol Command Functions
    def SetOff(self):
        """Send SetOff command"""
        if not self.is_connected:
            return False
        command = b'\xb1\xb2\x01\x00\x00\xb6'
        return self.send_data(command)
    
    def SetOn(self):
        """Send SetOn command"""
        if not self.is_connected:
            return False
        command = b'\xb1\xb2\x01\x01\x00\xb6'
        return self.send_data(command)
    
    def SetIset(self, current):
        """Send SetIset command with current value"""
        if not self.is_connected:
            return False
        # current format: integer and decimal (00..99)
        integer_part = int(current)
        decimal_part = int((current - integer_part) * 100)
        command = bytes([0xb1, 0xb2, 0x02, integer_part, decimal_part, 0xb6])
        return self.send_data(command)
    
    def SetVset(self, voltage):
        """Send SetVset command with voltage value"""
        if not self.is_connected:
            return False
        # voltage format: integer and decimal (00..99)
        integer_part = int(voltage)
        decimal_part = int((voltage - integer_part) * 100)
        command = bytes([0xb1, 0xb2, 0x03, integer_part, decimal_part, 0xb6])
        return self.send_data(command)
    
    def SetTset(self, time):
        """Send SetTset command with time value"""
        if not self.is_connected:
            return False
        # time as 16-bit unsigned integer
        time_value = int(time)
        high_byte = (time_value >> 8) & 0xff
        low_byte = time_value & 0xff
        command = bytes([0xb1, 0xb2, 0x04, high_byte, low_byte, 0xb6])
        return self.send_data(command)
    
    def SetResetCounters(self):
        """Send SetResetCounters command"""
        if not self.is_connected:
            return False
        command = b'\xb1\xb2\x05\x00\x00\xb6'
        return self.send_data(command)
    
    # PX100 Protocol Query Functions with retry logic
    def _send_query(self, command, expected_response_length):
        """Send query and wait for response with timeout and retry"""
        if not self.is_connected:
            return None
        
        max_retries = 3
        timeout = 0.005  # 5ms timeout
        header = b'\xca\xcb'
        trailer = b'\xce\xcf'
        
        for attempt in range(max_retries):
            # Clear serial buffer
            self.serial_buffer.clear()
            
            # Send command
            if not self.send_data(command):
                # Wait 1ms before next try if not the last attempt
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.001)  # 1ms delay between retries
                continue
            
            # Wait for response
            import time
            start_time = time.time()
            while time.time() - start_time < timeout:
                if hasattr(self.serial_port, 'in_waiting'):
                    if self.serial_port.in_waiting > 0:
                        data = self.serial_port.read(self.serial_port.in_waiting)
                        self.serial_buffer.extend(data)
                        
                        # Search for header in the buffer
                        header_index = self.serial_buffer.find(header)
                        while header_index != -1:
                            # Check if there's enough data for the full response
                            if len(self.serial_buffer) >= header_index + expected_response_length:
                                # Check if trailer is at the correct position
                                trailer_position = header_index + expected_response_length - 2
                                if self.serial_buffer[trailer_position:trailer_position + 2] == trailer:
                                    # Found valid response
                                    return self.serial_buffer[header_index:header_index + expected_response_length]
                            # Continue searching for next header
                            header_index = self.serial_buffer.find(header, header_index + 1)
                # Small delay to avoid busy waiting
                time.sleep(0.01)
            
            # Wait 1ms before next try if not the last attempt
            if attempt < max_retries - 1:
                time.sleep(0.001)  # 1ms delay between retries
        
        return None
    
    def ReadLStatus(self):
        """Read SLStatus"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x10\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            return response[4]  # SLStatus = xx
        return None
    
    def ReadSmV(self):
        """Read SmV"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x11\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SmV = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadSmA(self):
        """Read SmA"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x12\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SmA = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadSTimer(self):
        """Read STimer (SH, SM, SS)"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x13\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SH=xx, SM=yy, SS=zz
            return {
                'SH': response[2],
                'SM': response[3],
                'SS': response[4]
            }
        return None
    
    def ReadSmAh(self):
        """Read SmAh"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x14\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SmAh = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadSmWh(self):
        """Read SmWh"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x15\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SmWh = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadMosT(self):
        """Read SMosT"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x16\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SMosT = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadIset(self):
        """Read SIset"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x17\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SIset = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadVset(self):
        """Read SVset"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x18\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SVset = 0xxxyyzz
            value = (response[2] << 16) | (response[3] << 8) | response[4]
            return value
        return None
    
    def ReadTset(self):
        """Read Tset (SHset, SMset, SSset)"""
        if not self.is_connected:
            return None
        command = b'\xb1\xb2\x19\x00\x00\xb6'
        response = self._send_query(command, 7)  # Expected response length: 7 bytes
        
        if response and len(response) == 7 and response[0] == 0xca and response[1] == 0xcb and response[5] == 0xce and response[6] == 0xcf:
            # SHset=hh, SMset=mm, SSset=ss
            return {
                'SHset': response[2],
                'SMset': response[3],
                'SSset': response[4]
            }
        return None
    

    
    def on_onoff_button_clicked(self):
        """Handle OnOff button click"""
        if self.is_connected:
            # Check current button text to determine action
            if self.start_btn.text() == "启动":
                # Send SetOn command
                success = self.SetOn()
                if success:
                    # Immediately update button state to reflect new status
                    self.start_btn.setText("停止")
                    self.start_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: red; color: white; padding: 0px; margin: 0px; font-size: 17px;")
            else:
                # Send SetOff command
                success = self.SetOff()
                if success:
                    # Immediately update button state to reflect new status
                    self.start_btn.setText("启动")
                    self.start_btn.setStyleSheet("border: 1px solid gray; border-radius: 16px; background-color: white; padding: 0px; margin: 0px; font-size: 17px;")
    

            
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
                    
    def update_scale_colors(self):
        """更新所有刻度线的颜色"""
        # 更新V刻度线颜色
        self.scale_line2.color = ColorV
        self.scale_line2.update()
        # 更新P刻度线颜色
        self.scale_line.color = ColorP
        self.scale_line.update()
        # 更新A刻度线颜色
        self.scale_line3.color = ColorA
        self.scale_line3.update()

    def update_temperature_display(self):
        """更新温度显示"""
        global MosT, RunTime
        self.temperature_label.setText(f"{RunTime}S   {MosT:.1f}°C")

    def eventFilter(self, obj, event):
        """处理事件过滤器，捕获双击事件"""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonDblClick and hasattr(event, 'button') and event.button() == Qt.LeftButton:
            # 处理颜色选择 - 整个列作为热区
            if obj == self.zone6_col1:
                # 处理V颜色
                global ColorV
                color = QColorDialog.getColor(ColorV, self, "选择V颜色")
                if color.isValid():
                    ColorV = color
                    # 更新视觉效果
                    color_str = f"rgb({color.red()}, {color.green()}, {color.blue()})"
                    self.CheckboxV.setStyleSheet(f"background-color: {color_str}; color: black;")
                    self.lineV.setStyleSheet(f"background-color: {color_str};")
                    self.labelV.setStyleSheet(f"color: {color_str};")
                    # 更新刻度线颜色
                    self.update_scale_colors()
            elif obj == self.zone6_col2:
                # 处理P颜色
                global ColorP
                color = QColorDialog.getColor(ColorP, self, "选择P颜色")
                if color.isValid():
                    ColorP = color
                    # 更新视觉效果
                    color_str = f"rgb({color.red()}, {color.green()}, {color.blue()})"
                    self.CheckboxP.setStyleSheet(f"background-color: {color_str}; color: black;")
                    self.lineP.setStyleSheet(f"background-color: {color_str};")
                    self.labelP.setStyleSheet(f"color: {color_str};")
                    # 更新刻度线颜色
                    self.update_scale_colors()
            elif obj == self.zone6_col3:
                # 处理A颜色
                global ColorA
                color = QColorDialog.getColor(ColorA, self, "选择A颜色")
                if color.isValid():
                    ColorA = color
                    # 更新视觉效果
                    color_str = f"rgb({color.red()}, {color.green()}, {color.blue()})"
                    self.CheckboxA.setStyleSheet(f"background-color: {color_str}; color: black;")
                    self.lineA.setStyleSheet(f"background-color: {color_str};")
                    self.labelA.setStyleSheet(f"color: {color_str};")
                    # 更新刻度线颜色
                    self.update_scale_colors()
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DL24App()
    window.show()
    sys.exit(app.exec())