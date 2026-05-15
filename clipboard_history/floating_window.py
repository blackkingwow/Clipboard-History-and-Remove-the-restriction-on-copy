import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel, QApplication
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QCursor


# SendInput 结构体 —— 必须用 Union，否则结构大小对不上
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]


TITLE_HEIGHT = 26
BTN_SIZE = 22
LEFT_PAD = 6
RIGHT_PAD = 6
ITEM_SPACING = 4


class FloatingWindow(QWidget):
    """始终置顶的无边框悬浮窗口，展示剪贴板历史列表。
    鼠标悬停时完全不透明，移开后降为 20% 透明度。
    图钉按钮可锁定 100% 不透明。
    """

    def __init__(self, history_manager, clipboard_monitor=None):
        super().__init__()
        self.history_manager = history_manager
        self.clipboard_monitor = clipboard_monitor

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)  # 不抢焦点
        self.setMouseTracking(True)

        self._drag_pos = None
        self._pinned = False          # 锁定透明度：True 时始终 100% 不透明
        self.setWindowOpacity(0.2)

        self._setup_ui()
        self._position_default()

        self.list_widget.viewport().installEventFilter(self)

    # ===== 透明度 =====

    def enterEvent(self, event):
        self.setWindowOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._pinned:
            return  # 锁定状态不降透明度
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.setWindowOpacity(0.2)
        super().leaveEvent(event)

    # ===== UI 构建 =====

    def _setup_ui(self):
        self.setMinimumWidth(260)
        self.setMaximumWidth(520)
        self.resize(360, 400)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 标题栏（拖拽把手 + 按钮组） ----
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(TITLE_HEIGHT)
        self.title_bar.setStyleSheet(
            "QWidget { background: #4A90D9; border-top-left-radius: 4px; border-top-right-radius: 4px; }"
        )
        self.title_bar.setMouseTracking(True)
        self.title_bar.mousePressEvent = self._title_mouse_press
        self.title_bar.mouseMoveEvent = self._title_mouse_move
        self.title_bar.enterEvent = self._title_enter
        self.title_bar.leaveEvent = self._title_leave

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 0, 4, 0)
        title_layout.setSpacing(2)

        title_label = QLabel("剪贴板历史")
        title_label.setStyleSheet("color: white; font-size: 11px; background: transparent;")
        title_layout.addWidget(title_label, 1)

        # 图钉按钮：锁定透明度
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(BTN_SIZE, BTN_SIZE)
        self.pin_btn.setToolTip("锁定窗口不透明")
        self.pin_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.2); border-radius: 3px; }"
        )
        self.pin_btn.setVisible(False)
        self.pin_btn.clicked.connect(self._on_pin)
        title_layout.addWidget(self.pin_btn, 0)

        # 隐藏按钮：最小化到系统托盘
        self.hide_btn = QPushButton("➖")
        self.hide_btn.setFixedSize(BTN_SIZE, BTN_SIZE)
        self.hide_btn.setToolTip("隐藏到系统托盘")
        self.hide_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.2); border-radius: 3px; }"
        )
        self.hide_btn.setVisible(False)
        self.hide_btn.clicked.connect(self.hide)
        title_layout.addWidget(self.hide_btn, 0)

        root.addWidget(self.title_bar)

        # ---- 列表区域 ----
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 2, 2)
        content_layout.setSpacing(2)

        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.NoFocus)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setMouseTracking(True)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        content_layout.addWidget(self.list_widget, 1)

        clear_btn = QPushButton("全部清空")
        clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._on_clear)
        content_layout.addWidget(clear_btn)

        root.addWidget(content, 1)

    def _title_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _title_mouse_move(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    def _title_enter(self, event):
        self.pin_btn.setVisible(True)
        self.hide_btn.setVisible(True)

    def _title_leave(self, event):
        self.pin_btn.setVisible(False)
        self.hide_btn.setVisible(False)

    def _on_pin(self):
        """切换透明度锁定：锁定后窗口始终 100% 不透明，不受鼠标离开影响。"""
        self._pinned = not self._pinned
        if self._pinned:
            self.pin_btn.setText("🔒")
            self.pin_btn.setToolTip("解除锁定")
            self.setWindowOpacity(1.0)
        else:
            self.pin_btn.setText("📌")
            self.pin_btn.setToolTip("锁定窗口不透明")

    # ===== 事件过滤器：列表空白区拖拽 =====

    def eventFilter(self, obj, event):
        if obj is self.list_widget.viewport():
            etype = event.type()
            if etype == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                # 保存点击前的系统前台窗口句柄
                self._last_foreground = ctypes.windll.user32.GetForegroundWindow()
                item = self.list_widget.itemAt(event.pos())
                if item is None:
                    self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    return True
            elif etype == QEvent.MouseMove and self._drag_pos is not None:
                if event.buttons() == Qt.LeftButton:
                    self.move(event.globalPos() - self._drag_pos)
                    return True
            elif etype == QEvent.MouseButtonRelease:
                self._drag_pos = None
        return super().eventFilter(obj, event)

    # ===== 窗口级拖拽 =====

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    # ===== 默认位置 =====

    def showEvent(self, event):
        """窗口首次显示后，通过 Windows API 禁止鼠标点击激活本窗口。"""
        super().showEvent(event)
        if not hasattr(self, '_no_activate_set'):
            self._no_activate_set = True
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            user32 = ctypes.windll.user32
            current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current | WS_EX_NOACTIVATE)

    def nativeEvent(self, event_type, message):
        """拦截 WM_MOUSEACTIVATE，返回 MA_NOACTIVATE(3) 防止被点击时激活。"""
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == 0x0021:  # WM_MOUSEACTIVATE
                return True, 3         # MA_NOACTIVATE
        return False, 0

    def _position_default(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.left() + 20, screen.bottom() - self.height() - 60)

    # ===== 列表刷新 =====

    def refresh(self):
        self.list_widget.clear()
        entries = self.history_manager.get_all()
        for text in entries:
            self._add_item(text)

    def _update_item_widths(self):
        """窗口或列表宽度变化时，更新所有条目 widget 宽度，防止删除按钮被挤出。"""
        vp_width = self.list_widget.viewport().width()
        if vp_width <= 0:
            return
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if w:
                w.setFixedWidth(vp_width)
                label = w.findChild(QLabel)
                if label:
                    text = item.data(Qt.UserRole)
                    if text:
                        available = vp_width - LEFT_PAD - RIGHT_PAD - BTN_SIZE - ITEM_SPACING
                        elided = label.fontMetrics().elidedText(
                            text.replace('\n', ' ').replace('\r', '').strip(),
                            Qt.ElideRight, available
                        )
                        label.setText(elided)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_item_widths()

    def _add_item(self, text):
        display = text.replace('\n', ' ').replace('\r', ' ').strip()

        item_widget = QWidget()
        vp_width = self.list_widget.viewport().width()
        if vp_width > 0:
            item_widget.setFixedWidth(vp_width)

        hbox = QHBoxLayout(item_widget)
        hbox.setContentsMargins(LEFT_PAD, 3, RIGHT_PAD, 3)
        hbox.setSpacing(ITEM_SPACING)

        label = QLabel()
        label.setCursor(Qt.PointingHandCursor)
        font = label.font()
        font.setPointSize(10)
        label.setFont(font)
        label.setSizePolicy(label.sizePolicy().horizontalPolicy(), label.sizePolicy().verticalPolicy())
        available = vp_width - LEFT_PAD - RIGHT_PAD - BTN_SIZE - ITEM_SPACING
        if available > 20:
            elided = label.fontMetrics().elidedText(display, Qt.ElideRight, available)
            label.setText(elided)
        else:
            label.setText(display)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(BTN_SIZE, BTN_SIZE)
        del_btn.setStyleSheet(
            "QPushButton { border: none; color: #999; font-size: 14px; }"
            "QPushButton:hover { color: #e00; }"
        )
        del_btn.clicked.connect(lambda checked, t=text: self._on_delete(t))

        hbox.addWidget(label, 1)
        hbox.addWidget(del_btn, 0)

        list_item = QListWidgetItem()
        list_item.setData(Qt.UserRole, text)
        list_item.setSizeHint(item_widget.sizeHint())

        self.list_widget.addItem(list_item)
        self.list_widget.setItemWidget(list_item, item_widget)

    # ===== 用户操作 =====

    def _on_item_clicked(self, item):
        text = item.data(Qt.UserRole)
        self._type_text(text)  # 不碰剪贴板，直接模拟字符输入
        entries = self.history_manager.get_all()
        try:
            idx = entries.index(text)
            self.history_manager.move_to_top(idx)
            self.refresh()
        except ValueError:
            pass

    def _type_text(self, text):
        """使用 SendInput 模拟 Unicode 字符输入，不经过剪贴板、不模拟 Ctrl+V。"""
        user32 = ctypes.windll.user32

        # 恢复点击前的前台窗口，确保字符输入到正确目标
        if hasattr(self, '_last_foreground') and self._last_foreground:
            ASFW_ANY = 2
            user32.AllowSetForegroundWindow(ASFW_ANY)
            user32.SetForegroundWindow(self._last_foreground)

        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1
        NULL_PTR = ctypes.POINTER(ctypes.c_ulong)()

        count = len(text) * 2
        InputArray = INPUT * count
        inputs = InputArray()

        for i, ch in enumerate(text):
            scan = ord(ch)
            # 按下
            inputs[i * 2].type = INPUT_KEYBOARD
            inputs[i * 2].u.ki.wVk = 0
            inputs[i * 2].u.ki.wScan = scan
            inputs[i * 2].u.ki.dwFlags = KEYEVENTF_UNICODE
            inputs[i * 2].u.ki.time = 0
            inputs[i * 2].u.ki.dwExtraInfo = NULL_PTR
            # 释放
            inputs[i * 2 + 1].type = INPUT_KEYBOARD
            inputs[i * 2 + 1].u.ki.wVk = 0
            inputs[i * 2 + 1].u.ki.wScan = scan
            inputs[i * 2 + 1].u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            inputs[i * 2 + 1].u.ki.time = 0
            inputs[i * 2 + 1].u.ki.dwExtraInfo = NULL_PTR

        user32.SendInput(count, ctypes.byref(inputs), ctypes.sizeof(INPUT))

    def _on_delete(self, text):
        entries = self.history_manager.get_all()
        try:
            idx = entries.index(text)
            self.history_manager.remove(idx)
            self.refresh()
        except ValueError:
            pass

    def _on_clear(self):
        self.history_manager.clear()
        self.refresh()

    # ===== 关闭行为 =====

    def closeEvent(self, event):
        event.ignore()
        self.hide()
