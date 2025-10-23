from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets

from db import (
    init_db,
    seed_if_empty,
    seed_geo_if_empty,
    search_people,
    list_countries,
    search_landmarks,
    search_government,
    search_people_by_country,
    delete_people,
    delete_landmarks,
    delete_government,
)

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

        tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(tabs)

        # Tab 1: People search
        people_tab = QtWidgets.QWidget()
        ppl_layout = QtWidgets.QHBoxLayout(people_tab)

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

        self.delete_people_btn = QtWidgets.QPushButton("Delete selected")
        self.delete_people_btn.clicked.connect(self.on_delete_people)
        left_layout.addWidget(self.delete_people_btn)

        ppl_layout.addWidget(left, 3)

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

        ppl_layout.addWidget(right, 5)

        tabs.addTab(people_tab, "People")

        # Tab 2: Geo search (landmarks, government, locals)
        geo_tab = QtWidgets.QWidget()
        geo_layout = QtWidgets.QVBoxLayout(geo_tab)

        controls = QtWidgets.QHBoxLayout()
        self.country_combo = QtWidgets.QComboBox()
        self.country_combo.addItem("All countries", userData=None)
        for code, name in list_countries():
            self.country_combo.addItem(f"{name} ({code})", userData=code)
        controls.addWidget(QtWidgets.QLabel("Country:"))
        controls.addWidget(self.country_combo, 1)

        self.geo_query = QtWidgets.QLineEdit()
        self.geo_query.setPlaceholderText("Find landmarks, government officials, or locals…")
        controls.addWidget(self.geo_query, 2)

        geo_layout.addLayout(controls)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        # Landmarks list
        self.landmark_list = QtWidgets.QListWidget()
        self.landmark_list.setMinimumWidth(280)
        splitter.addWidget(self.landmark_list)
        # Government list
        self.gov_list = QtWidgets.QListWidget()
        self.gov_list.setMinimumWidth(280)
        splitter.addWidget(self.gov_list)
        # Locals list
        self.locals_list = QtWidgets.QListWidget()
        splitter.addWidget(self.locals_list)

        # Delete buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.delete_landmark_btn = QtWidgets.QPushButton("Delete landmarks")
        self.delete_landmark_btn.clicked.connect(self.on_delete_landmarks)
        self.delete_gov_btn = QtWidgets.QPushButton("Delete government")
        self.delete_gov_btn.clicked.connect(self.on_delete_government)
        self.delete_locals_btn = QtWidgets.QPushButton("Delete locals")
        self.delete_locals_btn.clicked.connect(self.on_delete_locals)
        btn_row.addWidget(self.delete_landmark_btn)
        btn_row.addWidget(self.delete_gov_btn)
        btn_row.addWidget(self.delete_locals_btn)
        geo_layout.addLayout(btn_row)

        geo_layout.addWidget(splitter, 1)

        tabs.addTab(geo_tab, "Geo")

        # Wire search
        self.search_edit.textChanged.connect(self.on_search)
        self.list_view.itemSelectionChanged.connect(self.on_select)
        self.geo_query.textChanged.connect(self.on_geo_search)
        self.country_combo.currentIndexChanged.connect(self.on_geo_search)

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

    @QtCore.Slot()
    def on_geo_search(self):
        text = self.geo_query.text().strip()
        code = self.country_combo.currentData()
        self.landmark_list.clear()
        self.gov_list.clear()
        self.locals_list.clear()
        if not text and code is None:
            return
        for _id, name, city, country_name in search_landmarks(text or "", code, limit=50):
            item = QtWidgets.QListWidgetItem(
                f"{name}" + (f" — {city}" if city else "") + f" ({country_name})"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, ("landmark", _id))
            self.landmark_list.addItem(item)
        for _id, office, person_name, country_name in search_government(text or "", code, limit=50):
            item = QtWidgets.QListWidgetItem(f"{office}: {person_name} ({country_name})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, ("government", _id))
            self.gov_list.addItem(item)
        for _id, first, last, email, city, country in search_people_by_country(text or "", code, limit=50):
            item = QtWidgets.QListWidgetItem(f"{first} {last} <{email}> — {city}, {country}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, ("person", _id))
            self.locals_list.addItem(item)
        try:
            self.media_player.stop()
            self.media_player.play()
        except Exception:
            pass

    @QtCore.Slot()
    def on_delete_people(self):
        # People tab list doesn't store IDs; perform a fresh filtered query to get IDs
        text = self.search_edit.text().strip()
        results = search_people(text, limit=500)
        selected_rows = set(idx.row() for idx in self.list_view.selectedIndexes())
        ids = [r[0] for i, r in enumerate(results) if i in selected_rows]
        if not ids:
            return
        deleted = delete_people(ids)
        self.on_search()

    @QtCore.Slot()
    def on_delete_landmarks(self):
        ids = []
        for item in self.landmark_list.selectedItems():
            kind, _id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if kind == "landmark":
                ids.append(int(_id))
        if not ids:
            return
        delete_landmarks(ids)
        self.on_geo_search()

    @QtCore.Slot()
    def on_delete_government(self):
        ids = []
        for item in self.gov_list.selectedItems():
            kind, _id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if kind == "government":
                ids.append(int(_id))
        if not ids:
            return
        delete_government(ids)
        self.on_geo_search()

    @QtCore.Slot()
    def on_delete_locals(self):
        ids = []
        for item in self.locals_list.selectedItems():
            kind, _id = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if kind == "person":
                ids.append(int(_id))
        if not ids:
            return
        delete_people(ids)
        self.on_geo_search()


def run():
    config = load_config()
    init_db()
    seed_if_empty(200)
    seed_geo_if_empty()

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
