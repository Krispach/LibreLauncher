import os
import sys
import json
import time
import subprocess

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QListWidgetItem, QVBoxLayout,
    QHBoxLayout, QFrame, QSplitter, QFileDialog, QDesktopWidget,
    QMessageBox, QTextEdit, QApplication, QLabel, QPushButton, QDialog,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor

from game import Game, resolve_shortcut
from workers import SteamAppListLoader, SteamDetailsDownloader, IconExtractorWorker
from ui_components import CustomTitleBar, GameListItem
from dialogs import EditGameDialog


class GameLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreLauncher")
        self.setGeometry(100, 100, 1160, 680)
        self.setAcceptDrops(True)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.center()
        
        self.games = self.load_games()
        self.current_game = None
        self.steam_app_list = self.load_steam_app_list()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_running_games)
        self.timer.start(1000)

        self.icon_workers = []
        self.details_workers = []
        self.pending_icons = {}

        self.init_ui()
        if not self.steam_app_list:
            self.load_steam_app_list_async()
        self.populate_games_list()

        if self.games:
            self.games_list.setCurrentRow(0)

    def load_steam_app_list(self):
        steam_app_list_file = 'steam_app_list.json'
        if os.path.exists(steam_app_list_file):
            try:
                with open(steam_app_list_file, 'r', encoding='utf-8') as f:
                    apps = json.load(f)
                    return apps
            except Exception:
                return []
        return []

    def load_steam_app_list_async(self):
        self.app_list_loader = SteamAppListLoader()
        self.app_list_loader.list_loaded.connect(self.on_steam_app_list_loaded)
        self.app_list_loader.start()

    def on_steam_app_list_loaded(self, app_list):
        self.steam_app_list = app_list

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        bg_frame = QFrame()
        bg_frame.setStyleSheet("QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0f1011, stop:0.5 #0f1011, stop:1 #0c0d0d); }")
        bg_layout = QVBoxLayout(bg_frame)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)
        main_layout.addWidget(bg_frame)
        
        self.title_bar = CustomTitleBar(self)
        self.title_bar.search.textChanged.connect(self.filter_games_list)
        bg_layout.addWidget(self.title_bar)
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)
        bg_layout.addLayout(content_layout, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        content_layout.addWidget(splitter)
        
        left_panel = QFrame()
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(320)
        left_panel.setStyleSheet("QFrame { background-color: rgba(22, 22, 22, 0.7); border-radius: 10px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)
        
        library_header = QLabel("Библиотека")
        library_header.setStyleSheet("QLabel { color: #d9dde0; font-weight: 700; font-size: 13px; padding-top: 6px; padding-left: 4px; }")
        left_layout.addWidget(library_header)

        self.games_list = QListWidget()
        self.games_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; padding: 4px; }
            QListWidget::item { background: transparent; margin: 4px 0; }
            QListWidget::item:selected { background: rgba(255,255,255,0.04); border-radius: 8px; }
            QListWidget::item:hover { background: rgba(255,255,255,0.03); border-radius: 8px; }
        """)
        self.games_list.setFocusPolicy(Qt.NoFocus)
        self.games_list.itemSelectionChanged.connect(self.show_game_details)
        left_layout.addWidget(self.games_list, 1)

        add_game_btn = QPushButton("Добавить игру")
        add_game_btn.setFixedHeight(40)
        add_game_btn.setStyleSheet("""
            QPushButton { background: #2a2a2a; color: #f1f4f6; font-weight: 700; border: 1px solid #2e2e2e; border-radius: 8px; padding: 6px 10px; font-size: 13px; }
            QPushButton:hover { background: #313131; }
        """)
        add_game_btn.clicked.connect(self.add_game_dialog)
        left_layout.addWidget(add_game_btn)
        
        splitter.addWidget(left_panel)

        self.game_details_panel = QFrame()
        self.game_details_panel.setStyleSheet("QFrame { background-color: rgba(19, 19, 19, 0.7); border-radius: 10px; }")
        details_layout = QVBoxLayout(self.game_details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(0) 

        self.banner_label = QLabel()
        self.banner_label.setMinimumHeight(240)
        self.banner_label.setMaximumHeight(240)
        self.banner_label.setAlignment(Qt.AlignCenter)
        self.banner_label.setStyleSheet("background-color: #1a1a1a; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        banner_shadow = QGraphicsDropShadowEffect(self.banner_label)
        banner_shadow.setBlurRadius(20)
        banner_shadow.setYOffset(6)
        banner_shadow.setColor(QColor(0, 0, 0, 180))
        self.banner_label.setGraphicsEffect(banner_shadow)
        details_layout.addWidget(self.banner_label)

        content_widget = QWidget()
        content_main_layout = QVBoxLayout(content_widget)
        content_main_layout.setContentsMargins(25, 20, 25, 20)
        content_main_layout.setSpacing(15)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        title_play_layout = QVBoxLayout()
        title_play_layout.setSpacing(10)
        
        self.game_title_label = QLabel("Выберите игру")
        self.game_title_label.setStyleSheet("QLabel { color:#f0f4f6; font-weight:700; font-size:26px; }")
        self.game_title_label.setWordWrap(True)
        title_play_layout.addWidget(self.game_title_label)
        
        play_info_layout = QHBoxLayout()
        play_info_layout.setSpacing(20)
        play_info_layout.setAlignment(Qt.AlignLeft)

        self.play_button = QPushButton("ИГРАТЬ")
        self.play_button.setMinimumSize(160, 50)
        self.play_button.setStyleSheet("""
            QPushButton { background: #28a745; color: white; font-weight: 800; font-size: 15px; border: none; border-radius: 10px; padding: 10px 20px; }
            QPushButton:hover { background: #218838; }
            QPushButton:pressed { background: #1e7e34; }
            QPushButton:disabled { background: #555; color: #888; }
        """)
        self.play_button.clicked.connect(self.launch_current_game)
        play_info_layout.addWidget(self.play_button)

        play_time_v_layout = QVBoxLayout()
        play_time_v_layout.setSpacing(2)
        self.play_time_label = QLabel("0ч 0м")
        self.play_time_label.setStyleSheet("color:#e1e6ea; font-size:16px; font-weight:600;")
        play_time_v_layout.addWidget(self.play_time_label)
        play_time_header = QLabel("Время в игре")
        play_time_header.setStyleSheet("color:#8a9298; font-size:11px;")
        play_time_v_layout.addWidget(play_time_header)
        play_info_layout.addLayout(play_time_v_layout)

        last_played_v_layout = QVBoxLayout()
        last_played_v_layout.setSpacing(2)
        self.last_played_date = QLabel("-")
        self.last_played_date.setStyleSheet("color:#e1e6ea; font-size:16px; font-weight:600;")
        last_played_v_layout.addWidget(self.last_played_date)
        last_played_header = QLabel("Последний запуск")
        last_played_header.setStyleSheet("color:#8a9298; font-size:11px;")
        last_played_v_layout.addWidget(last_played_header)
        play_info_layout.addLayout(last_played_v_layout)

        title_play_layout.addLayout(play_info_layout)
        top_layout.addLayout(title_play_layout, 1)

        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(8)
        action_buttons_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self.settings_button = QPushButton("⚙️")
        self.settings_button.setFixedSize(42, 42)
        self.settings_button.setStyleSheet("""
            QPushButton { background: #2f2f2f; color: #d7dbde; font-weight:700; font-size: 20px; border: 1px solid #3a3a3a; border-radius: 21px; }
            QPushButton:hover { background: #3a3a3a; }
            QPushButton:disabled { color: #555; border-color: #282828; background: #222; }
        """)
        self.settings_button.clicked.connect(self.edit_current_game)
        action_buttons_layout.addWidget(self.settings_button)
        
        top_layout.addLayout(action_buttons_layout)
        content_main_layout.addLayout(top_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(25)

        self.game_description_label = QTextEdit()
        self.game_description_label.setReadOnly(True)
        self.game_description_label.setStyleSheet("QTextEdit { color:#c9ced3; background:transparent; border:none; font-size: 14px; }")
        bottom_layout.addWidget(self.game_description_label, 70)

        right_info_panel = QVBoxLayout()
        right_info_panel.setSpacing(15)

        review_frame = QFrame()
        review_frame.setStyleSheet("QFrame { background: rgba(0,0,0,0.1); border-radius: 8px; }")
        review_layout = QVBoxLayout(review_frame)
        review_layout.setContentsMargins(12, 8, 12, 8)
        review_layout.setSpacing(2)
        review_header = QLabel("Отзывы в Steam:")
        review_header.setStyleSheet("color:#8a9298; font-size:11px; background: transparent;")
        review_layout.addWidget(review_header)
        
        self.review_summary_label = QLabel("N/A")
        self.review_summary_label.setStyleSheet("color:#aaaaaa; font-size:16px; font-weight:bold; background: transparent;")
        review_layout.addWidget(self.review_summary_label)
        
        self.review_percentage_label = QLabel("")
        self.review_percentage_label.setStyleSheet("color:#aab1b6; font-size:11px; background: transparent;")
        review_layout.addWidget(self.review_percentage_label)
        
        right_info_panel.addWidget(review_frame)
        
        sys_req_frame = QFrame()
        sys_req_frame.setStyleSheet("QFrame { background: rgba(0,0,0,0.1); border-radius: 8px; }")
        sys_req_layout = QVBoxLayout(sys_req_frame)
        sys_req_layout.setContentsMargins(12, 8, 12, 8)
        sys_req_layout.setSpacing(4)
        sys_req_header = QLabel("Системные требования:")
        sys_req_header.setStyleSheet("color:#8a9298; font-size:11px; font-weight:bold; background: transparent;")
        sys_req_layout.addWidget(sys_req_header)
        self.sys_req_label = QTextEdit()
        self.sys_req_label.setReadOnly(True)
        self.sys_req_label.setText("Не загружены...")
        self.sys_req_label.setStyleSheet("QTextEdit { color:#c9ced3; background:transparent; border:none; font-size: 11px; }")
        sys_req_layout.addWidget(self.sys_req_label)
        right_info_panel.addWidget(sys_req_frame)
        
        bottom_layout.addLayout(right_info_panel, 30)
        content_main_layout.addLayout(bottom_layout, 1)

        details_layout.addWidget(content_widget, 1)
        splitter.addWidget(self.game_details_panel)
        splitter.setSizes([280, 880])
    
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def populate_games_list(self, filter_text=""):
        self.games_list.clear()
        sorted_games = sorted(self.games, key=lambda g: g.name.lower())
        
        for game in sorted_games:
            if filter_text.lower() in game.name.lower():
                item = QListWidgetItem(self.games_list)
                widget = GameListItem(game)
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.UserRole, game)
                self.games_list.addItem(item)
                self.games_list.setItemWidget(item, widget)

                if not getattr(game, "icon_loaded", False):
                    self.pending_icons[game.exe_path] = item
                    worker = IconExtractorWorker(game)
                    worker.icon_processed.connect(self.on_icon_processed)
                    self.icon_workers.append(worker)
                    worker.start()

    def filter_games_list(self, text):
        self.populate_games_list(filter_text=text)

    def on_icon_processed(self, game, pixmap):
        game.icon_loaded = True
        if game.exe_path in self.pending_icons:
            item = self.pending_icons.pop(game.exe_path)
            widget = self.games_list.itemWidget(item)
            if widget:
                widget.game.icon_path = game.icon_path
                widget.load_icon()
        self.save_games()

    def on_details_processed(self, game):
        self.save_games()
        if self.current_game and self.current_game.exe_path == game.exe_path:
            self.show_game_details()

    def show_game_details(self):
        selected_items = self.games_list.selectedItems()
        if not selected_items:
            self.current_game = None
            self.update_ui_for_no_game()
            return
        
        item = selected_items[0]
        self.current_game = item.data(Qt.UserRole)

        if not self.current_game.description or not self.current_game.system_requirements or self.current_game.review_summary is None:
            self.start_steam_details_download(self.current_game)
        
        self.game_title_label.setText(self.current_game.name)
        self.game_description_label.setText(self.current_game.description or "Описание отсутствует.")
        self.sys_req_label.setText(self.current_game.system_requirements or "Не загружены...")
        self.play_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        
        self.update_play_time_display()
        self.update_review_display()
        
        banner_pixmap = QPixmap()
        if self.current_game.banner_path and os.path.exists(self.current_game.banner_path):
            banner_pixmap.load(self.current_game.banner_path)
        
        if banner_pixmap.isNull():
            self.banner_label.setText("Баннер не найден")
            self.banner_label.setStyleSheet("background-color: #1a1a1a; border-top-left-radius: 10px; border-top-right-radius: 10px; color: #555; font-size: 16px;")
        else:
            scaled_pixmap = banner_pixmap.scaled(self.banner_label.width(), self.banner_label.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.banner_label.setPixmap(scaled_pixmap)
            self.banner_label.setText("")

    def start_steam_details_download(self, game):
        for worker in self.details_workers:
            if worker.game.exe_path == game.exe_path and worker.isRunning():
                return
        
        worker = SteamDetailsDownloader(game, self.steam_app_list)
        worker.details_processed.connect(self.on_details_processed)
        self.details_workers.append(worker)
        worker.start()

    def update_ui_for_no_game(self):
        self.game_title_label.setText("Выберите игру из списка")
        self.banner_label.setText("")
        self.banner_label.setStyleSheet("background-color: #1a1a1a; border-top-left-radius: 10px; border-top-right-radius: 10px;")
        self.game_description_label.clear()
        self.play_time_label.setText("0ч 0м")
        self.last_played_date.setText("-")
        self.play_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.sys_req_label.setText("")
        self.review_summary_label.setText("N/A")
        self.review_summary_label.setStyleSheet("color:#aaaaaa; font-size:16px; font-weight:bold; background: transparent;")
        self.review_percentage_label.setText("")

    def update_play_time_display(self):
        if self.current_game:
            seconds = self.current_game.play_time
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            self.play_time_label.setText(f"{hours}ч {minutes}м")
            
            if self.current_game.last_played:
                try:
                    formatted_date = time.strftime("%d %B %Y", time.localtime(self.current_game.last_played)).replace("January", "января").replace("February", "февраля").replace("March", "марта").replace("April", "апреля").replace("May", "мая").replace("June", "июня").replace("July", "июля").replace("August", "августа").replace("September", "сентября").replace("October", "октября").replace("November", "ноября").replace("December", "декабря")
                    self.last_played_date.setText(formatted_date)
                except Exception:
                    self.last_played_date.setText("-")
            else:
                self.last_played_date.setText("Никогда")
    
    def update_review_display(self):
        if self.current_game and self.current_game.review_summary:
            summary = self.current_game.review_summary
            percentage = self.current_game.review_percentage
            
            self.review_summary_label.setText(summary)
            
            color = "#a8a8a8"
            if "Положительные" in summary or "Positive" in summary:
                color = "#66c0f4"
            elif "Смешанные" in summary or "Mixed" in summary:
                color = "#b9940a"
            elif "Отрицательные" in summary or "Negative" in summary:
                color = "#c1483d"
            
            self.review_summary_label.setStyleSheet(f"color: {color}; font-size:16px; font-weight:bold; background: transparent;")
            
            if percentage is not None:
                self.review_percentage_label.setText(f"({percentage}% положительных)")
            else:
                self.review_percentage_label.setText("")
        else:
            self.review_summary_label.setText("N/A")
            self.review_summary_label.setStyleSheet("color:#aaaaaa; font-size:16px; font-weight:bold; background: transparent;")
            self.review_percentage_label.setText("")

    def launch_current_game(self):
        if self.current_game and not self.current_game.process:
            try:
                self.current_game.start_time = time.time()
                self.current_game.last_played = time.time()
                self.current_game.process = subprocess.Popen([self.current_game.exe_path])
                self.play_button.setText("ЗАПУЩЕНО")
                self.play_button.setDisabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка запуска", f"Не удалось запустить игру: {e}")
                self.current_game.process = None

    def check_running_games(self):
        for game in self.games:
            if getattr(game, "process", None) and game.process.poll() is not None:
                elapsed_time = time.time() - game.start_time
                game.play_time += elapsed_time
                game.process = None
                game.start_time = None
                self.save_games()

                if self.current_game and self.current_game.exe_path == game.exe_path:
                    self.play_button.setText("ИГРАТЬ")
                    self.play_button.setEnabled(True)
                    self.update_play_time_display()
                
                for i in range(self.games_list.count()):
                    item = self.games_list.item(i)
                    if item.data(Qt.UserRole).exe_path == game.exe_path:
                        widget = self.games_list.itemWidget(item)
                        if widget:
                            widget.time_label.setText(widget.format_time(game.play_time))
                        break

    def edit_current_game(self):
        if not self.current_game:
            return

        dialog = EditGameDialog(self.current_game, self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            if dialog.delete_requested:
                self.delete_game_files(self.current_game)
                try:
                    self.games = [g for g in self.games if g.exe_path != self.current_game.exe_path]
                except Exception:
                    if self.current_game in self.games:
                        self.games.remove(self.current_game)
                self.current_game = None
                self.populate_games_list()
                self.update_ui_for_no_game()
            else:
                new_name = dialog.name_edit.text().strip()
                new_path = dialog.path_edit.text().strip()
                new_desc = dialog.desc_edit.toPlainText()

                if new_path and new_path.lower().endswith('.lnk'):
                    resolved = resolve_shortcut(new_path)
                    if resolved and os.path.exists(resolved) and resolved.lower().endswith('.exe'):
                        new_path = resolved

                target = next((g for g in self.games if g.exe_path == self.current_game.exe_path), None)
                if target:
                    if new_name:
                        target.name = new_name
                    if new_path:
                        target.exe_path = new_path
                    target.description = new_desc

                self.populate_games_list()
                for i in range(self.games_list.count()):
                    if self.games_list.item(i).data(Qt.UserRole).exe_path == (new_path or self.current_game.exe_path):
                        self.games_list.setCurrentRow(i)
                        break

            self.save_games()

    def delete_game_files(self, game):
        try:
            if getattr(game, "icon_path", None) and os.path.exists(game.icon_path):
                os.remove(game.icon_path)
        except Exception:
            pass

        try:
            if getattr(game, "banner_path", None) and os.path.exists(game.banner_path):
                os.remove(game.banner_path)
        except Exception:
            pass

    def add_game_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Выберите исполняемые файлы игр или ярлыки", "", "Исполняемые файлы и ярлыки (*.exe *.lnk)")
        if file_paths:
            added = False
            for file_path in file_paths:
                if not file_path:
                    continue

                resolved_path = file_path
                if file_path.lower().endswith('.lnk'):
                    resolved = resolve_shortcut(file_path)
                    if resolved and os.path.exists(resolved) and resolved.lower().endswith('.exe'):
                        resolved_path = resolved
                    else:
                        continue

                if not resolved_path.lower().endswith('.exe'):
                    continue

                if any(g.exe_path == resolved_path for g in self.games):
                    continue
                game_name = os.path.splitext(os.path.basename(resolved_path))[0]
                new_game = Game(game_name, resolved_path)
                self.games.append(new_game)
                added = True
            if added:
                self.save_games()
                self.populate_games_list()
                if self.games_list.count() > 0:
                    self.games_list.setCurrentRow(self.games_list.count()-1)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fp = url.toLocalFile().lower()
                if fp.endswith('.exe') or fp.endswith('.lnk'):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        added = False
        for url in urls:
            file_path = url.toLocalFile()
            if not file_path:
                continue

            if file_path.lower().endswith('.lnk'):
                resolved = resolve_shortcut(file_path)
                if resolved and os.path.exists(resolved) and resolved.lower().endswith('.exe'):
                    file_path = resolved
                else:
                    continue

            if file_path.lower().endswith('.exe'):
                if any(g.exe_path == file_path for g in self.games):
                    continue
                game_name = os.path.splitext(os.path.basename(file_path))[0]
                new_game = Game(game_name, file_path)
                self.games.append(new_game)
                added = True
        if added:
            self.save_games()
            self.populate_games_list()

    def save_games(self):
        try:
            with open('games.json', 'w', encoding='utf-8') as f:
                json.dump([game.to_dict() for game in self.games], f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def load_games(self):
        if os.path.exists('games.json'):
            try:
                with open('games.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [Game.from_dict(game_data) for game_data in data]
            except Exception:
                return []
        return []

    def closeEvent(self, event):
        self.save_games()
        event.accept()
