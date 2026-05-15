from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QLineEdit, QPushButton)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence


class SettingsDialog(QDialog):
    """快捷键设置对话框，用户可点击输入框后按下组合键来设置。"""

    def __init__(self, current_hotkey: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置快捷键")
        self.setFixedSize(320, 140)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self._result = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("按下你想要的组合键来设置显隐快捷键："))

        self.input = QLineEdit()
        self.input.setPlaceholderText("点击此处，然后按下组合键...")
        self.input.setText(current_hotkey)
        self.input.setReadOnly(True)
        self.input.keyPressEvent = self._on_key_press
        layout.addWidget(self.input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self._on_ok)
        ok_btn.setDefault(True)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def _on_key_press(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return  # 忽略单独的修饰键

        parts = []
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.MetaModifier:
            parts.append("Meta")

        key_str = QKeySequence(key).toString()
        if key_str:
            parts.append(key_str)

        if parts:
            self.input.setText("+".join(parts))

    def _on_ok(self):
        self._result = self.input.text()
        self.accept()

    def get_key_sequence(self) -> str:
        return self._result
