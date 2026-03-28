import sys
import time
from datetime import datetime
import os
import hashlib
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QGroupBox, QCheckBox,
    QDoubleSpinBox, QGridLayout, QMessageBox, QSizePolicy, QInputDialog,
    QDialog, QFormLayout, QDialogButtonBox,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsView, QGraphicsScene
)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QFont, QPen, QColor, QPainter
import pyqtgraph as pg
import serial
import serial.tools.list_ports

# 版本号管理
VERSION = "0.00.80"
BUILD_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 计算代码哈希值的函数
def calculate_code_hash():
    """计算当前代码的哈希值，用于检测代码变化"""
    hash_obj = hashlib.md5()
    # 读取当前文件的内容
    with open(__file__, 'rb') as f:
        content = f.read()
        hash_obj.update(content)
    return hash_obj.hexdigest()

# 跟踪版本号的函数
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
                new_revision = "1.0.00"
    except FileNotFoundError:
        # 文件不存在，使用默认版本号
        new_revision = "1.0.00"
    
    # 保存新的版本号和哈希值
    with open(revision_file, 'w') as f:
        f.write(f"{new_revision}\n{current_hash}\n")
    
    return new_revision

# 获取当前版本号
REVISION = get_revision()

# Test comment to trigger revision increment

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
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置透明背景
        self.setStyleSheet("background-color: transparent;")
        self.plot_window = None
    
    def set_plot_window(self, plot_window):
        self.plot_window = plot_window
    
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
            # 绘制紫色原点（PlotWindow的左下角）
            origin_x = x
            origin_y = y + height
            painter.setPen(QPen(QColor(128, 0, 128), 4))
            painter.setBrush(QColor(128, 0, 128))
            painter.drawEllipse(origin_x - 3, origin_y - 3, 6, 6)
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
    
    def paintEvent(self, event):
        # 调用父类的paintEvent
        super().paintEvent(event)
        
        # 获取widget的大小
        width = self.width()
        height = self.height()
        
        # 创建QPainter对象
        painter = QPainter(self)
        try:
            # 绘制紫色原点（左下角）
            origin_x = 0
            origin_y = height
            painter.setPen(QPen(QColor(128, 0, 128), 4))
            painter.setBrush(QColor(128, 0, 128))
            painter.drawEllipse(origin_x - 3, origin_y - 3, 6, 6)
        finally:
            painter.end()

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
        
        # 2. 版本号标签
        self.revision_label = QLabel(f"Revision: {REVISION}")
        self.revision_label.setParent(main_widget)
        
        # 连接窗口大小变化信号
        self.resizeEvent = self.on_resize
        
        # 初始调整大小
        self.on_resize(None)
        
        # 暂时移除轴的双击事件，因为我们已经重新设计了曲线显示区域
        
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
        right_margin = ui_width * 4/15  # 减少20% (从1/3变为4/15)
        
        # 计算显示widget的大小和位置
        widget_width = ui_width - left_margin - right_margin
        widget_height = ui_height - top_margin - bottom_margin
        
        # 使用绝对定位设置widget的位置和大小
        self.display_widget.setGeometry(
            int(left_margin),
            int(top_margin),
            int(widget_width),
            int(widget_height)
        )
        
        # 获取实际widget大小
        actual_width = self.display_widget.width()
        actual_height = self.display_widget.height()
        
        # 强制重绘以确保矩形和原点显示
        self.display_widget.update()
        
        # 定位版本号标签到主布局的左下角
        label_x = left_margin
        label_y = ui_height - bottom_margin + 10  # 10像素的偏移量
        self.revision_label.setGeometry(int(label_x), int(label_y), 200, 30)
        
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
            # 连接串口
            port = self.port_combo.currentText()
            if port:
                try:
                    # 检查端口是否存在
                    ports = [p.device for p in serial.tools.list_ports.comports()]
                    if port not in ports:
                        QMessageBox.warning(self, "错误", f"串口 {port} 不存在或不可用")
                        return
                    
                    # 尝试多次打开串口，处理有数据输入的情况
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            # 配置串口参数：9600 8 N 1
                            self.serial_port = serial.Serial(
                                port,
                                baudrate=9600,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=2,
                                write_timeout=2,
                                exclusive=True
                            )
                            # 清除缓冲区
                            if self.serial_port.in_waiting:
                                self.serial_port.read_all()
                            self.is_connected = True
                            self.connect_btn.setText("断开")
                            self.connect_btn.setStyleSheet("background-color: lightgreen")
                            print(f"已连接到串口: {port}")
                            break
                        except Exception as e:
                            if attempt == max_attempts - 1:
                                raise
                            # 等待一段时间后重试
                            import time
                            time.sleep(0.5)
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"无法连接到串口 {port}: {str(e)}")
        else:
            # 断开串口
            if self.serial_port:
                try:
                    self.serial_port.close()
                except Exception as e:
                    print(f"断开串口时出错: {str(e)}")
                finally:
                    self.serial_port = None
            self.is_connected = False
            self.connect_btn.setText("连接")
            self.connect_btn.setStyleSheet("")
            print("已断开串口连接")
            
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