import sys
from PyQt5.QtWidgets import QApplication

from history_manager import HistoryManager
from clipboard_monitor import ClipboardMonitor
from floating_window import FloatingWindow
from system_tray import SystemTray
from hotkey_manager import HotkeyManager


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，保留托盘

    # 初始化模块
    hm = HistoryManager(max_entries=30)
    monitor = ClipboardMonitor()
    window = FloatingWindow(hm, monitor)
    hotkey = HotkeyManager(window)
    tray = SystemTray(window, hm, hotkey)
    tray.show()

    # 连接信号：新剪贴板内容 → 添加到历史 → 刷新列表
    # 注意：itemClicked 已在 floating_window._setup_ui() 中连接，此处不重复
    monitor.changed.connect(lambda text: _on_new_clipboard(text, hm, window, monitor))

    # 显示窗口
    window.show()
    window.refresh()

    sys.exit(app.exec_())


def _on_new_clipboard(text: str, hm: HistoryManager, window: FloatingWindow, monitor: ClipboardMonitor):
    if hm.add(text):
        window.refresh()


if __name__ == "__main__":
    main()
