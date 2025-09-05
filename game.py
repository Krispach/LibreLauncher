import os
import re
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QFont

def resolve_shortcut(path):
    if not path:
        return None

    if not path.lower().endswith('.lnk'):
        return path

    try:
        from win32com.client import Dispatch
    except Exception:
        return None

    try:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(path)
        target = shortcut.Targetpath
        if target:
            return target
        else:
            return None
    except Exception:
        return None

class Game:
    def __init__(self, name, exe_path, icon_path=None, banner_path=None, description="", play_time=0, last_played=None, is_favorite=False, review_summary=None, review_percentage=None, system_requirements=None):
        self.name = name
        self.exe_path = exe_path
        self.icon_path = icon_path
        self.banner_path = banner_path
        self.description = description
        self.play_time = play_time
        self.last_played = last_played
        self.is_favorite = is_favorite
        self.review_summary = review_summary
        self.review_percentage = review_percentage
        self.system_requirements = system_requirements
        self.process = None
        self.start_time = None
        self.icon_loaded = False

    def to_dict(self):
        return {
            'name': self.name,
            'exe_path': self.exe_path,
            'icon_path': self.icon_path,
            'banner_path': self.banner_path,
            'description': self.description,
            'play_time': self.play_time,
            'last_played': self.last_played,
            'is_favorite': self.is_favorite,
            'review_summary': self.review_summary,
            'review_percentage': self.review_percentage,
            'system_requirements': self.system_requirements
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['name'],
            data['exe_path'],
            data.get('icon_path'),
            data.get('banner_path'),
            data.get('description', ""),
            data.get('play_time', 0),
            data.get('last_played'),
            data.get('is_favorite', False),
            data.get('review_summary'),
            data.get('review_percentage'),
            data.get('system_requirements')
        )