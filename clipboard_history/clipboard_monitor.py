import ctypes
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication


class ClipboardMonitor(QObject):
    """定时轮询系统剪贴板，通过序列号检测每一次复制操作（即使内容相同也能识别）。"""

    changed = pyqtSignal(str)

    def __init__(self, interval_ms=300):
        super().__init__()
        self.clipboard = QApplication.clipboard()
        self._last_seq = self._get_seq()

        self.timer = QTimer()
        self.timer.timeout.connect(self._check)
        self.timer.start(interval_ms)

    def _get_seq(self):
        """获取 Windows 剪贴板序列号，每次写入都递增，内容不变也会变。"""
        return ctypes.windll.user32.GetClipboardSequenceNumber()

    def _check(self):
        seq = self._get_seq()
        if seq == self._last_seq:
            return
        self._last_seq = seq

        text = self.clipboard.text()
        if text:
            self.changed.emit(text)
