import json
import os
import ctypes
from ctypes import wintypes

from PyQt5.QtCore import QAbstractNativeEventFilter, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_HOTKEY = "Alt+P"
WM_HOTKEY = 0x0312

MOD_MAP = {
    Qt.ControlModifier: 0x0002,  # MOD_CONTROL
    Qt.AltModifier: 0x0001,      # MOD_ALT
    Qt.ShiftModifier: 0x0004,    # MOD_SHIFT
    Qt.MetaModifier: 0x0008,     # MOD_WIN
}

VK_MAP = {
    # 字母 A-Z
    **{chr(ord('A') + i): ord('A') + i for i in range(26)},
    # 数字 0-9
    **{str(i): ord(str(i)) for i in range(10)},
    # 功能键 F1-F12
    **{f"F{i}": 0x70 + i - 1 for i in range(1, 13)},
    # 特殊键（键名需大写，与 parse_key_sequence 中 .upper() 一致）
    "SPACE": 0x20,
    "TAB": 0x09,
    "RETURN": 0x0D,
    "ENTER": 0x0D,
    "BACKSPACE": 0x08,
    "ESCAPE": 0x1B,
    "DELETE": 0x2E,
    "INSERT": 0x2D,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "PRINT": 0x2C,
    "SCROLL": 0x91,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
}

# 注册热键
HOTKEY_ID = 1
user32 = ctypes.windll.user32


def parse_key_sequence(key_seq: str) -> tuple:
    """解析 'Alt+P' 这样的字符串，返回 (modifiers_int, vk) 元组。"""
    parts = key_seq.split("+")
    modifiers = 0
    vk = 0

    for part in parts:
        part = part.strip()
        if part == "Ctrl" or part == "Control":
            modifiers |= MOD_MAP[Qt.ControlModifier]
        elif part == "Alt":
            modifiers |= MOD_MAP[Qt.AltModifier]
        elif part == "Shift":
            modifiers |= MOD_MAP[Qt.ShiftModifier]
        elif part == "Meta" or part == "Win":
            modifiers |= MOD_MAP[Qt.MetaModifier]
        else:
            # 普通按键
            upper = part.upper()
            if upper in VK_MAP:
                vk = VK_MAP[upper]
            elif len(part) == 1:
                vk = ord(upper)
            else:
                raise ValueError(f"无法识别的按键: {part}")

    if modifiers == 0 or vk == 0:
        raise ValueError(f"无效的快捷键: '{key_seq}' (需要至少一个修饰键 + 一个普通键)")

    return (modifiers, vk)


def key_sequence_to_string(key_seq: str) -> str:
    """规范化快捷键字符串。"""
    # 转换为 QKeySequence 再转回字符串实现规范化
    qks = QKeySequence(key_seq)
    return qks.toString()


def load_hotkey() -> str:
    """从 config.json 加载快捷键，失败则返回默认值。"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("hotkey", DEFAULT_HOTKEY)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_HOTKEY


def save_hotkey(key_seq: str):
    """保存快捷键到 config.json。"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"hotkey": key_seq}, f, ensure_ascii=False, indent=2)


class HotkeyManager(QAbstractNativeEventFilter):
    """使用 Windows RegisterHotKey API 注册全局热键。"""

    def __init__(self, floating_window):
        super().__init__()
        self.floating_window = floating_window
        self._key_seq = ""
        self._register(load_hotkey())

        # 安装原生事件过滤器
        QApplication.instance().installNativeEventFilter(self)

    def _register(self, key_seq: str):
        """注册全局热键。"""
        # 先注销旧热键
        if self._key_seq:
            user32.UnregisterHotKey(None, HOTKEY_ID)

        try:
            modifiers, vk = parse_key_sequence(key_seq)
            result = user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk)
            if result:
                self._key_seq = key_seq
                save_hotkey(key_seq)
        except ValueError:
            pass  # 快捷键无效，保持旧设置

    def nativeEventFilter(self, event_type, message):
        """处理 Windows 原生事件，捕获 WM_HOTKEY。"""
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self._toggle_window()
                return True, 0
        return False, 0

    def _toggle_window(self):
        if self.floating_window.isVisible():
            self.floating_window.hide()
        else:
            self.floating_window.show()
            self.floating_window.refresh()

    def get_current_hotkey(self) -> str:
        """返回当前快捷键字符串。"""
        return self._key_seq

    def open_settings(self):
        from settings_dialog import SettingsDialog
        dialog = SettingsDialog(self._key_seq, self.floating_window)
        if dialog.exec_():
            new_seq = dialog.get_key_sequence()
            if new_seq:
                self._register(new_seq)
