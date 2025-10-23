from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets

from db import init_db, seed_if_empty, search_people

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, expected_user: str, expected_pass: str):
        super().__init__()
        self.setWindowTitle("Secure Login")
        self.setModal(True)
        self.setFixedSize(360, 220)

        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Account Login")
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        self.user_edit = QtWidgets.QLineEdit()
        self.pass_edit = QtWidgets.QLineEdit()
        self.pass_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        form.addRow("Username", self.user_edit)
        form.addRow("Password", self.pass_edit)
        layout.addLayout(form)

        self.error_label = QtWidgets.QLabel()
        self.error_label.setStyleSheet("color: #d9534f")
        layout.addWidget(self.error_label)

        btn = QtWidgets.QPushButton("Login")
        btn.clicked.connect(lambda: self._try_login(expected_user, expected_pass))
        layout.addWidget(btn)

        self.user_edit.setFocus()

    def _try_login(self, expected_user: str, expected_pass: str):
        if self.user_edit.text() == expected_user and self.pass_edit.text() == expected_pass:
            self.accept()
        else:
            self.error_label.setText("Invalid credentials")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, video_path: Path):
        super().__init__()
        self.setWindowTitle("Forensic Search Console")
        self.resize(1000, 640)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)

        # Left: search panel
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)

        search_label = QtWidgets.QLabel("Search people")
        font = search_label.font()
        font.setPointSize(12)
        font.setBold(True)
        search_label.setFont(font)
        left_layout.addWidget(search_label)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Type a name, email, city, country…")
        left_layout.addWidget(self.search_edit)

        self.list_view = QtWidgets.QListWidget()
        left_layout.addWidget(self.list_view, 1)

        root.addWidget(left, 3)

        # Right: video panel
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)

        self.video_widget = QtMultimediaWidgets.QVideoWidget()
        right_layout.addWidget(self.video_widget, 1)

        # Media player setup (Qt6 style)
        self.media_player = QtMultimedia.QMediaPlayer()
        try:
            # Optional audio output if available
            self.audio_output = QtMultimedia.QAudioOutput()
            self.media_player.setAudioOutput(self.audio_output)
        except Exception:
            self.audio_output = None
        self.media_player.setVideoOutput(self.video_widget)

        # Load video
        if video_path.exists():
            url = QtCore.QUrl.fromLocalFile(str(video_path))
            # Qt6 API uses setSource
            try:
                self.media_player.setSource(url)
            except Exception:
                # Fallback for older bindings
                content = QtMultimedia.QMediaContent(url)
                self.media_player.setMedia(content)
        else:
            placeholder = QtWidgets.QLabel("Video not found: " + str(video_path))
            placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            right_layout.addWidget(placeholder)

        root.addWidget(right, 5)

        # Wire search
        self.search_edit.textChanged.connect(self.on_search)
        self.list_view.itemSelectionChanged.connect(self.on_select)

    @QtCore.Slot()
    def on_search(self):
        text = self.search_edit.text().strip()
        self.list_view.clear()
        if not text:
            return
        results = search_people(text, limit=50)
        for _id, first, last, email, city, country in results:
            self.list_view.addItem(f"{first} {last} <{email}> — {city}, {country}")
        # Auto play video when a search occurs
        try:
            self.media_player.stop()
            self.media_player.play()
        except Exception:
            pass

    @QtCore.Slot()
    def on_select(self):
        # Potential place to seek or overlay details in the future
        pass


def run():
    config = load_config()
    init_db()
    seed_if_empty(200)

    app = QtWidgets.QApplication([])

    login = LoginDialog(config["login"]["username"], config["login"]["password"])
    if login.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return

    video_path = (APP_DIR / config["video"]["path"]).resolve()
    win = MainWindow(video_path)
    win.show()

    app.exec()


if __name__ == "__main__":
    run()
