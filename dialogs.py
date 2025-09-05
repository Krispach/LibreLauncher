import os
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, 
                             QDialogButtonBox, QGridLayout, QHBoxLayout, QFileDialog,
                             QMessageBox, QVBoxLayout)
from PyQt5.QtCore import Qt
from game import Game, resolve_shortcut

class EditGameDialog(QDialog):
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование игры")
        self.setFixedSize(520, 420)
        self.setStyleSheet("""
            QDialog { background-color: #151515; color: #e6edf1; }
            QLabel { color: #d1d7da; font-size: 13px; }
            QLineEdit, QTextEdit { background-color: #1c1c1c; color: #f0f4f6; border: 1px solid #272829; border-radius: 6px; padding: 8px; }
            QPushButton { background-color: #232323; color: #f0f4f6; border: none; border-radius: 6px; padding: 7px 12px; }
            QPushButton:hover { background-color: #2b2b2b; }
            QPushButton#deleteButton { background-color: #332424; }
            QPushButton#deleteButton:hover { background-color: #3f2b2b; }
        """)

        self.game = game
        self.delete_requested = False

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        layout.addWidget(QLabel("Название:"), 0, 0)
        self.name_edit = QLineEdit(game.name)
        layout.addWidget(self.name_edit, 0, 1, 1, 2)

        layout.addWidget(QLabel("Путь к EXE:"), 1, 0)
        self.path_edit = QLineEdit(game.exe_path)
        self.browse_button = QPushButton("Обзор...")
        self.browse_button.clicked.connect(self.browse_exe)
        layout.addWidget(self.path_edit, 1, 1)
        layout.addWidget(self.browse_button, 1, 2)

        layout.addWidget(QLabel("Описание:"), 2, 0)
        self.desc_edit = QTextEdit(game.description)
        self.desc_edit.setMinimumHeight(110)
        layout.addWidget(self.desc_edit, 2, 1, 1, 2)

        layout.addWidget(QLabel("Баннер:"), 3, 0)
        self.banner_button = QPushButton("Загрузить баннер" if not game.banner_path else "Изменить баннер")
        self.banner_button.clicked.connect(self.load_banner)
        layout.addWidget(self.banner_button, 3, 1, 1, 2)

        layout.addWidget(QLabel("Иконка:"), 4, 0)
        self.icon_button = QPushButton("Загрузить иконку" if not game.icon_path else "Изменить иконку")
        self.icon_button.clicked.connect(self.load_icon)
        layout.addWidget(self.icon_button, 4, 1, 1, 2)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.delete_button = QPushButton("Удалить игру")
        self.delete_button.setObjectName("deleteButton")
        self.delete_button.clicked.connect(self.confirm_delete)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(button_box)

        layout.addLayout(buttons_layout, 5, 0, 1, 3)

    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите исполняемый файл игры или ярлык", "", "Исполняемые файлы и ярлыки (*.exe *.lnk)")
        if file_path:
            if file_path.lower().endswith('.lnk'):
                resolved = resolve_shortcut(file_path)
                if resolved and os.path.exists(resolved):
                    self.path_edit.setText(resolved)
                else:
                    self.path_edit.setText(file_path)
            else:
                self.path_edit.setText(file_path)

    def load_banner(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение для баннера", "", "Изображения (*.png *.jpg *.jpeg)")
        if file_path:
            self.game.banner_path = file_path
            self.banner_button.setText("Баннер загружен")

    def load_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение для иконки", "", "Изображения (*.png *.jpg *.jpeg *.ico)")
        if file_path:
            self.game.icon_path = file_path
            self.icon_button.setText("Иконка загружена")

    def confirm_delete(self):
        reply = QMessageBox.question(self, "Подтверждение удаления", f"Вы уверены, что хотите удалить игру '{self.game.name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.delete_requested = True
            self.accept()

    def get_updated_game(self):
        updated = Game(
            self.name_edit.text().strip() or self.game.name,
            self.path_edit.text().strip() or self.game.exe_path,
            icon_path=self.game.icon_path,
            banner_path=self.game.banner_path,
            description=self.desc_edit.toPlainText(),
            play_time=self.game.play_time,
            last_played=self.game.last_played,
            is_favorite=self.game.is_favorite,
            review_summary=self.game.review_summary,
            review_percentage=self.game.review_percentage,
            system_requirements=self.game.system_requirements
        )
        return updated

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("INFO")
        self.setFixedSize(300, 200)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #d1d7da; }
            QLabel { color: #d1d7da; padding: 5px; }
            QPushButton { background-color: #2a2a2a; color: #d1d7da; border: none; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("LibreLauncher"))
        layout.addWidget(QLabel("Версия: Beta 0.1"))
        layout.addWidget(QLabel("Автор: Krispach (qwe0x322)"))
        layout.addWidget(QLabel("GitHub: https://github.com/your-repo"))
        button = QPushButton("Закрыть")
        button.clicked.connect(self.accept)
        layout.addWidget(button)