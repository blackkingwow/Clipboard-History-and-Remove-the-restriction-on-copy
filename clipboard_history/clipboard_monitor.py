from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication


class ClipboardMonitor(QObject):
    """定时轮询系统剪贴板，检测到文本变化时通过信号通知。"""

    changed = pyqtSignal(str)  # 携带新的文本内容

    def __init__(self, interval_ms=500):
        super().__init__()
        self.clipboard = QApplication.clipboard()
        self._last_text = ""
        self._skip_next = False

        self.timer = QTimer()
        self.timer.timeout.connect(self._check)
        self.timer.start(interval_ms)

    def skip_next(self):
        """标记跳过下一次轮询（程序自身写入剪贴板后调用）。"""
        self._skip_next = True

    def _check(self):
        if self._skip_next:
            self._skip_next = False
            self._last_text = ""
            return

        text = self.clipboard.text()
        if text and text != self._last_text:
            self._last_text = text
            self.changed.emit(text)
