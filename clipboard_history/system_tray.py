from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon


class SystemTray(QSystemTrayIcon):
    """系统托盘，提供右键菜单和双击显隐。"""

    def __init__(self, floating_window, history_manager, hotkey_manager=None):
        super().__init__()
        self.floating_window = floating_window
        self.history_manager = history_manager
        self.hotkey_manager = hotkey_manager

        self.setIcon(self._make_icon())
        self.setToolTip("剪贴板历史")

        self._setup_menu()
        self.activated.connect(self._on_activated)

    def _make_icon(self):
        """生成托盘图标——纯色方块，备用。"""
        from PyQt5.QtGui import QPainter, QColor, QPixmap
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#4A90D9"))
        painter.setPen(QColor("#2C6FB0"))
        painter.drawRoundedRect(4, 4, 24, 24, 5, 5)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), 0x0084, "C")  # Qt.AlignCenter
        painter.end()
        return QIcon(pixmap)

    def _setup_menu(self):
        menu = QMenu()

        toggle_action = menu.addAction("显示/隐藏")
        toggle_action.triggered.connect(self._toggle_window)

        menu.addSeparator()

        if self.hotkey_manager:
            settings_action = menu.addAction("设置快捷键...")
            settings_action.triggered.connect(self.hotkey_manager.open_settings)

        clear_action = menu.addAction("全部清空")
        clear_action.triggered.connect(self._clear_all)

        menu.addSeparator()

        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self._quit)

        self.setContextMenu(menu)

    def _toggle_window(self):
        if self.floating_window.isVisible():
            self.floating_window.hide()
        else:
            self.floating_window.show()
            self.floating_window.refresh()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_window()

    def _clear_all(self):
        self.history_manager.clear()
        self.floating_window.refresh()

    def _quit(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()
