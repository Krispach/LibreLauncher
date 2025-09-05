import sys
from PyQt5.QtWidgets import QApplication
from launcher import GameLauncher

if __name__ == '__main__':
    app = QApplication(sys.argv)
    launcher = GameLauncher()
    launcher.show()
    sys.exit(app.exec_())