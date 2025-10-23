from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets

from db import (
    init_db,
    seed_if_empty,
    seed_geo_if_empty,
    seed_camera_if_empty,
    search_people,
    list_countries,
    search_landmarks,
    search_government,
    search_people_by_country,
    delete_people,
    delete_landmarks,
    delete_government,
    search_cameras,
    insert_camera,
    delete_cameras,
    list_cameras_for_person,
    link_camera_to_person,
    unlink_cameras_from_person,
)
from geo import geolocate

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, expected_user: str, expected_pass: str, logo_path: Optional[Path] = None):
        super().__init__()
        self.setWindowTitle("Secure Login")
        self.setModal(True)
        self.setFixedSize(360, 220)

        layout = QtWidgets.QVBoxLayout(self)

        # Logo (optional)
        if logo_path and logo_path.exists():
            logo_label = QtWidgets.QLabel()
            pix = QtGui.QPixmap(str(logo_path))
            if not pix.isNull():
                logo_label.setPixmap(pix.scaledToWidth(120, QtCore.Qt.TransformationMode.SmoothTransformation))
                logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(logo_label)

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

        # Person-camera linking panel
        link_group = QtWidgets.QGroupBox("Linked cameras (authorized only)")
        link_layout = QtWidgets.QVBoxLayout(link_group)
        self.person_cam_list = QtWidgets.QListWidget()
        link_layout.addWidget(self.person_cam_list)
        link_btns = QtWidgets.QHBoxLayout()
        self.link_add_btn = QtWidgets.QPushButton("Link selected camera from Cameras tab")
        self.link_del_btn = QtWidgets.QPushButton("Unlink selected")
        link_btns.addWidget(self.link_add_btn)
        link_btns.addWidget(self.link_del_btn)
        link_layout.addLayout(link_btns)
        right_layout.addWidget(link_group)

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

        # Tab 3: Cameras
        cam_tab = QtWidgets.QWidget()
        cam_layout = QtWidgets.QVBoxLayout(cam_tab)

        cam_controls = QtWidgets.QHBoxLayout()
        self.cam_country = QtWidgets.QComboBox()
        self.cam_country.addItem("All countries", userData=None)
        for code, name in list_countries():
            self.cam_country.addItem(f"{name} ({code})", userData=code)
        self.cam_query = QtWidgets.QLineEdit()
        self.cam_query.setPlaceholderText("Search cameras by name or location…")
        self.cam_public = QtWidgets.QCheckBox("Public only")
        self.cam_public.setChecked(True)
        self.cam_fixed = QtWidgets.QCheckBox("Fixed only")
        self.cam_fixed.setChecked(True)
        cam_controls.addWidget(QtWidgets.QLabel("Country:"))
        cam_controls.addWidget(self.cam_country, 1)
        cam_controls.addWidget(self.cam_query, 2)
        cam_controls.addWidget(self.cam_public)
        cam_controls.addWidget(self.cam_fixed)
        cam_layout.addLayout(cam_controls)

        cam_split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.cam_list = QtWidgets.QListWidget()
        self.cam_list.setMinimumWidth(360)
        cam_split.addWidget(self.cam_list)

        self.cam_video = QtMultimediaWidgets.QVideoWidget()
        cam_split.addWidget(self.cam_video)
        cam_layout.addWidget(cam_split, 1)

        # Media player for cameras (separate from main video)
        self.cam_player = QtMultimedia.QMediaPlayer()
        try:
            self.cam_audio = QtMultimedia.QAudioOutput()
            self.cam_player.setAudioOutput(self.cam_audio)
        except Exception:
            self.cam_audio = None
        self.cam_player.setVideoOutput(self.cam_video)

        cam_btns = QtWidgets.QHBoxLayout()
        self.cam_add_btn = QtWidgets.QPushButton("Add camera")
        self.cam_del_btn = QtWidgets.QPushButton("Delete selected")
        cam_btns.addWidget(self.cam_add_btn)
        cam_btns.addWidget(self.cam_del_btn)
        cam_layout.addLayout(cam_btns)

        tabs.addTab(cam_tab, "Cameras")

        # Tab 4: Geolocate
        geoip_tab = QtWidgets.QWidget()
        geoip_layout = QtWidgets.QVBoxLayout(geoip_tab)
        geoip_form = QtWidgets.QHBoxLayout()
        self.geoip_target = QtWidgets.QLineEdit()
        self.geoip_target.setPlaceholderText("Enter IP address or domain name…")
        self.geoip_btn = QtWidgets.QPushButton("Lookup")
        geoip_form.addWidget(self.geoip_target, 1)
        geoip_form.addWidget(self.geoip_btn)
        geoip_layout.addLayout(geoip_form)

        self.geoip_output = QtWidgets.QTextEdit()
        self.geoip_output.setReadOnly(True)
        geoip_layout.addWidget(self.geoip_output, 1)

        tabs.addTab(geoip_tab, "Geolocate")

        # Wire search
        self.search_edit.textChanged.connect(self.on_search)
        self.list_view.itemSelectionChanged.connect(self.on_select)
        self.geo_query.textChanged.connect(self.on_geo_search)
        self.country_combo.currentIndexChanged.connect(self.on_geo_search)

        self.cam_query.textChanged.connect(self.on_cam_search)
        self.cam_country.currentIndexChanged.connect(self.on_cam_search)
        self.cam_public.stateChanged.connect(self.on_cam_search)
        self.cam_fixed.stateChanged.connect(self.on_cam_search)
        self.cam_list.itemSelectionChanged.connect(self.on_cam_select)
        self.cam_add_btn.clicked.connect(self.on_cam_add)
        self.cam_del_btn.clicked.connect(self.on_cam_delete)

        self.list_view.itemSelectionChanged.connect(self.refresh_person_cameras)
        self.link_add_btn.clicked.connect(self.on_link_selected_camera_to_person)
        self.link_del_btn.clicked.connect(self.on_unlink_selected_cameras)

        self.geoip_btn.clicked.connect(self.on_geoip_lookup)

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

    def _selected_person_id(self) -> Optional[int]:
        # Mirror current People results to get ID by row
        text = self.search_edit.text().strip()
        results = search_people(text, limit=500)
        selected = self.list_view.selectedIndexes()
        if not selected:
            return None
        row = selected[0].row()
        if row < 0 or row >= len(results):
            return None
        return int(results[row][0])

    @QtCore.Slot()
    def refresh_person_cameras(self):
        person_id = self._selected_person_id()
        self.person_cam_list.clear()
        if person_id is None:
            return
        for cam_id, name, location, country_name, url in list_cameras_for_person(person_id):
            item = QtWidgets.QListWidgetItem(f"{name} — {location} ({country_name})")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, cam_id)
            self.person_cam_list.addItem(item)

    @QtCore.Slot()
    def on_link_selected_camera_to_person(self):
        person_id = self._selected_person_id()
        if person_id is None:
            return
        # Use current selection in Cameras tab to link
        items = self.cam_list.selectedItems()
        if not items:
            return
        data = items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        cam_id = int(data.get("id"))
        link_camera_to_person(person_id, cam_id)
        self.refresh_person_cameras()

    @QtCore.Slot()
    def on_unlink_selected_cameras(self):
        person_id = self._selected_person_id()
        if person_id is None:
            return
        ids = []
        for item in self.person_cam_list.selectedItems():
            ids.append(int(item.data(QtCore.Qt.ItemDataRole.UserRole)))
        if not ids:
            return
        unlink_cameras_from_person(person_id, ids)
        self.refresh_person_cameras()

    @QtCore.Slot()
    def on_cam_search(self):
        text = self.cam_query.text().strip()
        code = self.cam_country.currentData()
        self.cam_list.clear()
        cams = search_cameras(
            query=text,
            country_code=code,
            public_only=self.cam_public.isChecked(),
            fixed_only=self.cam_fixed.isChecked(),
            limit=200,
        )
        for _id, name, location, country_name, url, is_public, is_fixed in cams:
            label = f"{name} — {location} ({country_name})"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, {"id": _id, "url": url})
            self.cam_list.addItem(item)

    @QtCore.Slot()
    def on_cam_select(self):
        items = self.cam_list.selectedItems()
        if not items:
            return
        data = items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        url = data.get("url")
        if not url:
            return
        qurl = QtCore.QUrl.fromLocalFile(str((APP_DIR / url).resolve())) if not url.startswith("http") else QtCore.QUrl(url)
        try:
            self.cam_player.setSource(qurl)
        except Exception:
            self.cam_player.setMedia(QtMultimedia.QMediaContent(qurl))
        self.cam_player.stop()
        self.cam_player.play()

    @QtCore.Slot()
    def on_cam_add(self):
        # Simple add dialog
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Add camera")
        layout = QtWidgets.QFormLayout(dlg)
        name = QtWidgets.QLineEdit()
        location = QtWidgets.QLineEdit()
        country = QtWidgets.QComboBox()
        for code, cname in list_countries():
            country.addItem(f"{cname} ({code})", userData=code)
        url = QtWidgets.QLineEdit()
        is_public = QtWidgets.QCheckBox()
        is_public.setChecked(True)
        is_fixed = QtWidgets.QCheckBox()
        is_fixed.setChecked(True)
        layout.addRow("Name", name)
        layout.addRow("Location", location)
        layout.addRow("Country", country)
        layout.addRow("Stream URL or File Path", url)
        layout.addRow("Public", is_public)
        layout.addRow("Fixed", is_fixed)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        if not name.text().strip() or not url.text().strip():
            return
        insert_camera(
            name=name.text().strip(),
            location=location.text().strip(),
            country_code=country.currentData(),
            url=url.text().strip(),
            is_public=is_public.isChecked(),
            is_fixed=is_fixed.isChecked(),
        )
        self.on_cam_search()

    @QtCore.Slot()
    def on_cam_delete(self):
        ids = []
        for item in self.cam_list.selectedItems():
            data = item.data(QtCore.Qt.ItemDataRole.UserRole)
            ids.append(int(data.get("id")))
        if not ids:
            return
        delete_cameras(ids)
        self.on_cam_search()

    @QtCore.Slot()
    def on_geoip_lookup(self):
        target = self.geoip_target.text().strip()
        if not target:
            return
        cfg = load_config().get("geolocation", {})
        endpoint = cfg.get("endpoint", "https://ipapi.co/{target}/json/")
        api_key = cfg.get("api_key")
        self.geoip_output.setPlainText("Looking up…")
        QtCore.QCoreApplication.processEvents()
        try:
            data = geolocate(target, endpoint_template=endpoint, api_key=api_key)
            lines = []
            for k in [
                "ip","city","region","country","country_code","postal","latitude","longitude","timezone","org"
            ]:
                if data.get(k) is not None:
                    lines.append(f"{k}: {data.get(k)}")
            if data.get("error"):
                lines.append(f"error: {data['error']}")
            self.geoip_output.setPlainText("\n".join(lines) or "No data")
        except Exception as e:
            self.geoip_output.setPlainText(f"Lookup failed: {e}")

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
    seed_camera_if_empty()

    app = QtWidgets.QApplication([])

    branding_logo = config.get("branding", {}).get("logo_path")
    logo_path = (APP_DIR / branding_logo).resolve() if branding_logo else None
    login = LoginDialog(config["login"]["username"], config["login"]["password"], logo_path=logo_path)
    if login.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return

    video_path = (APP_DIR / config["video"]["path"]).resolve()
    win = MainWindow(video_path)
    win.show()

    app.exec()


if __name__ == "__main__":
    run()
