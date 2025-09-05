import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QFont


class GameListItem(QWidget):
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setStyleSheet("border-radius:8px;")
        self.load_icon()

        # drop shadow effect (QGraphicsDropShadowEffect is in QtWidgets)
        effect = QGraphicsDropShadowEffect(self.icon_label)
        effect.setBlurRadius(10)
        effect.setXOffset(0)
        effect.setYOffset(1)
        effect.setColor(QColor(0, 0, 0, 140))
        self.icon_label.setGraphicsEffect(effect)

        layout.addWidget(self.icon_label)

        name_layout = QVBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(1)

        self.name_label = QLabel(game.name)
        self.name_label.setStyleSheet("QLabel { color: #eef2f4; font-size: 13px; font-weight: 600; }")
        name_layout.addWidget(self.name_label)

        self.time_label = QLabel(self.format_time(game.play_time))
        self.time_label.setStyleSheet("QLabel { color: #aab1b6; font-size: 11px; }")
        name_layout.addWidget(self.time_label)

        layout.addLayout(name_layout, 1)

    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}ч {minutes}м"

    def load_icon(self):
        pixmap = QPixmap()
        if getattr(self.game, "icon_path", None) and os.path.exists(self.game.icon_path):
            pixmap.load(self.game.icon_path)

        if pixmap.isNull():
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            gradient = QLinearGradient(0, 0, 48, 48)
            gradient.setColorAt(0, QColor("#333333"))
            gradient.setColorAt(1, QColor("#222222"))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, 48, 48, 8, 8)

            font = QFont("Segoe UI", 18, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#f2f5f6"))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, (self.game.name[0].upper() if self.game.name else "G"))
            painter.end()

        self.icon_label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.parent = parent
        self.drag_position = None
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        title_label = QLabel("LibreLauncher")
        title_label.setStyleSheet("QLabel { color: #e0e3e6; font-weight: 600; font-size: 13px; }")
        layout.addWidget(title_label)
        layout.addStretch(1)

        self.info_button = QPushButton("i")
        self.info_button.setFixedSize(28, 28)
        self.info_button.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,0.1); color: #d7dcdf; border: none; border-radius: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: rgba(255,255,255,0.2); }"
        )
        self.info_button.clicked.connect(self.show_info)
        layout.addWidget(self.info_button)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск игр")
        self.search.setFixedWidth(220)
        self.search.setStyleSheet(
            "QLineEdit { background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.03); padding: 6px 8px; border-radius: 8px; color: #d7dcdf; font-size: 12px; }"
            "QLineEdit:focus { border: 1px solid rgba(255,255,255,0.06); }"
        )
        layout.addWidget(self.search)

        self.minimize_button = QPushButton("—")
        self.minimize_button.setFixedSize(34, 28)
        self.minimize_button.setStyleSheet(
            "QPushButton { background: transparent; color: #d6d9db; border: none; font-size: 14px; }"
            "QPushButton:hover { background-color: rgba(255,255,255,0.03); border-radius:4px; }"
        )
        self.minimize_button.clicked.connect(self.parent.showMinimized)
        layout.addWidget(self.minimize_button)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(34, 28)
        self.close_button.setStyleSheet(
            "QPushButton { background: transparent; color: #ebc4c4; border: none; font-size: 14px; }"
            "QPushButton:hover { background-color: rgba(231, 76, 60, 0.07); border-radius:4px; }"
        )
        self.close_button.clicked.connect(self.parent.close)
        layout.addWidget(self.close_button)

    def show_info(self):
        from dialogs import AboutDialog
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.parent.move(self.parent.pos() + event.globalPos() - self.drag_position)
            self.drag_position = event.globalPos()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            event.accept()
