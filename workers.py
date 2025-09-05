import os
import json
import time
import re
import difflib
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QFont
from icoextract import IconExtractor

class SteamAppListLoader(QThread):
    list_loaded = pyqtSignal(list)

    def run(self):
        try:
            response = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/", timeout=15)
            if response.status_code == 200:
                data = response.json()
                apps = data.get("applist", {}).get("apps", [])
                with open('steam_app_list.json', 'w', encoding='utf-8') as f:
                    json.dump(apps, f, indent=4, ensure_ascii=False)
                self.list_loaded.emit(apps)
            else:
                self.list_loaded.emit([])
        except Exception:
            self.list_loaded.emit([])

class SteamDetailsDownloader(QThread):
    details_processed = pyqtSignal(object)

    def __init__(self, game, steam_app_list, parent=None):
        super().__init__(parent)
        self.game = game
        self.steam_app_list = steam_app_list
        self.banners_dir = "game_banners"
        os.makedirs(self.banners_dir, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _fetch_steam_reviews(self, app_id):
        try:
            url = f"https://store.steampowered.com/app/{app_id}"
            cookies = {'birthtime': '568022401', 'wants_mature_content': '1'}
            response = requests.get(url, headers=self.headers, cookies=cookies, timeout=10)

            if response.status_code != 200:
                return None, None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            summary_element = soup.find('span', class_='game_review_summary')
            tooltip_element = soup.find('div', class_='user_reviews_summary_row')
            
            summary = "N/A"
            percentage = None

            if summary_element:
                summary = summary_element.get_text(strip=True)

            if tooltip_element and 'data-tooltip-text' in tooltip_element.attrs:
                tooltip_text = tooltip_element['data-tooltip-text']
                match = re.search(r'(\d+)%', tooltip_text)
                if match:
                    percentage = int(match.group(1))
            
            return summary, percentage

        except requests.exceptions.RequestException:
            return None, None
        except Exception:
            return None, None

    def run(self):
        has_banner = self.game.banner_path and os.path.exists(self.game.banner_path)
        has_description = self.game.description and self.game.description != "Описание отсутствует."
        has_sys_req = self.game.system_requirements
        has_reviews = self.game.review_summary is not None

        if has_banner and has_description and has_sys_req and has_reviews:
            return

        if not self.steam_app_list:
            self.details_processed.emit(self.game)
            return

        game_name = self.game.name
        all_app_names = [app['name'] for app in self.steam_app_list]
        matches = difflib.get_close_matches(game_name, all_app_names, n=1, cutoff=0.6)

        if not matches:
            self.details_processed.emit(self.game)
            return

        best_match_name = matches[0]
        app_id = next((app['appid'] for app in self.steam_app_list if app['name'] == best_match_name), None)
        
        if not app_id:
            self.details_processed.emit(self.game)
            return
        
        if not has_reviews:
            summary, percentage = self._fetch_steam_reviews(app_id)
            self.game.review_summary = summary
            self.game.review_percentage = percentage

        if not has_banner:
            try:
                banner_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
                response = requests.get(banner_url, timeout=10)
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    safe_name = re.sub(r'[^\w]', '', self.game.name)[:30]
                    banner_path = os.path.join(self.banners_dir, f"{safe_name}.jpg")
                    with open(banner_path, 'wb') as f:
                        f.write(response.content)
                    self.game.banner_path = banner_path
            except Exception:
                pass

        if not has_description or not has_sys_req:
            try:
                details_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=russian"
                response = requests.get(details_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    app_data = data.get(str(app_id))
                    if app_data and app_data.get('success'):
                        game_data = app_data['data']
                        
                        description_html = game_data.get('short_description', '')
                        self.game.description = re.sub(r'<.*?>', '', description_html).strip()
                        
                        pc_requirements = game_data.get('pc_requirements', {})
                        if isinstance(pc_requirements, dict):
                            requirements_html = pc_requirements.get('minimum', 'Системные требования не найдены.')
                            soup = BeautifulSoup(requirements_html, 'html.parser')
                            for tag in soup.find_all(['ul', 'li']):
                                tag.replace_with(tag.get_text() + '\n')
                            self.game.system_requirements = soup.get_text(separator='\n').strip()
            except Exception:
                pass

        self.details_processed.emit(self.game)

class IconExtractorWorker(QThread):
    icon_processed = pyqtSignal(object, QPixmap)
    
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.icons_dir = "game_icons"
        os.makedirs(self.icons_dir, exist_ok=True)

    def run(self):
        try:
            if self.game.icon_path and os.path.exists(self.game.icon_path):
                pixmap = QPixmap(self.game.icon_path)
                if not pixmap.isNull():
                    self.icon_processed.emit(self.game, pixmap)
                    return

            safe_name = re.sub(r'[^\w]', '', (self.game.name or "game"))[:30]
            output_path = os.path.join(self.icons_dir, f"{safe_name}.png")
            
            try:
                extractor = IconExtractor(self.game.exe_path)
                extractor.export_icon(output_path) 
                self.game.icon_path = output_path
                pixmap = QPixmap(output_path)
                self.icon_processed.emit(self.game, pixmap)
            except Exception:
                pixmap = self.generate_placeholder_icon()
                self.icon_processed.emit(self.game, pixmap)
        except Exception:
            pixmap = self.generate_placeholder_icon()
            self.icon_processed.emit(self.game, pixmap)

    def generate_placeholder_icon(self):
        pixmap = QPixmap(256, 256)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, 256, 256)
        gradient.setColorAt(0, QColor("#333333"))
        gradient.setColorAt(1, QColor("#1a1a1a"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 256, 256, 30, 30)
        letter = (self.game.name[0].upper() if self.game.name else "G")
        font = QFont("Segoe UI", 100, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#f0f4f6"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, letter)
        painter.end()
        self.save_icon(pixmap)
        return pixmap

    def save_icon(self, pixmap):
        try:
            safe_name = re.sub(r'[^\w]', '', (self.game.name or ""))[:30]
            filename = safe_name + ".png"
            icon_path = os.path.join(self.icons_dir, filename)
            pixmap.save(icon_path, "PNG")
            self.game.icon_path = icon_path 
        except Exception:
            pass