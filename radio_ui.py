#!/usr/bin/python3
import sys
import os
import json
import re
import subprocess
import urllib.request
from mpd import MPDClient
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QScroller
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QFont

RASPOTIFY_MARKER = "__raspotify__"
RASPOTIFY_STATUS_FILE = '/tmp/raspotify_status'
SPOTIFY_EMBED_URL = 'https://open.spotify.com/embed/track/{}'

class RadioController(QWidget):
    def __init__(self):
        super().__init__()
        self.client = MPDClient()
        self._track_cache = {}
        self.init_ui()
        self.connect_mpd()

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_loop)
        self.status_timer.start(1000)

    def init_ui(self):
        self.setStyleSheet("background-color: #000000;")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.playlist = QListWidget()
        self.playlist.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.playlist.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.playlist.setWordWrap(False)
        QScroller.grabGesture(self.playlist.viewport(), QScroller.LeftMouseButtonGesture)

        # Consistent font color for all items in CSS
        self.playlist.setStyleSheet("""
            QListWidget {
                font-size: 14pt;
                background-color: #0a0a0a;
                color: #00FF00;
                border: 1px solid #333;
                border-radius: 5px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 1px solid #222;
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: #1a1a1a;
            }
        """)
        self.playlist.itemClicked.connect(self.play_selected)

        self.btn_action = QPushButton("▶")
        self.btn_action.setMinimumHeight(95)
        self.btn_action.clicked.connect(self.toggle_playback)

        self.play_style = "background-color: #008000; font-size: 42pt; color: white; border-radius: 12px; border: 2px solid #555;"
        self.stop_style = "background-color: #cc0000; font-size: 42pt; color: white; border-radius: 12px; border: 2px solid #555;"

        self.btn_action.setStyleSheet(self.play_style)

        layout.addWidget(self.playlist, 1)
        layout.addWidget(self.btn_action)
        self.setLayout(layout)
        self.setFixedSize(480, 320)

    def connect_mpd(self):
        try:
            self.client.connect("localhost", 6600)
            self.refresh_playlist()
        except: pass

    def update_loop(self):
        mpd_state = 'stop'
        current_id = None
        current = {}
        try:
            status = self.client.status()
            current = self.client.currentsong()
            mpd_state = status.get('state', 'stop')
            current_id = current.get('id')
        except:
            try: self.client.connect("localhost", 6600)
            except: pass

        rasp = self._get_raspotify_status()
        rasp_playing = rasp and rasp['status'] == 'Playing'

        # If Spotify is playing and MPD starts, stop Spotify (MPD takes priority)
        if rasp_playing and mpd_state == 'play':
            self._raspotify_stop()
            rasp_playing = False
            rasp = None
        # If Spotify is playing and MPD is not, that's fine — Spotify has the floor
        # If MPD is playing and Spotify is not, that's fine — MPD has the floor

        # Update main button — reflects global playback state
        if mpd_state == 'play' or rasp_playing:
            self.btn_action.setText("■")
            self.btn_action.setStyleSheet(self.stop_style)
        else:
            self.btn_action.setText("▶")
            self.btn_action.setStyleSheet(self.play_style)
            # If nothing is playing, make sure raspotify is available for Spotify Connect
            if mpd_state != 'play':
                self._ensure_raspotify_running()

        # Update MPD items
        for i in range(self.playlist.count()):
            item = self.playlist.item(i)
            if item.data(Qt.UserRole) == RASPOTIFY_MARKER:
                continue
            item_id = item.data(Qt.UserRole + 1)
            base_name = item.data(Qt.UserRole + 2)
            font = item.font()
            if item_id == current_id:
                prefix = "▶ " if mpd_state == 'play' else "■ "
                song_title = current.get('title', '...')
                item.setText(f"{prefix}{base_name}\n {song_title}")
                font.setBold(True)
            else:
                item.setText(base_name)
                font.setBold(False)
            item.setFont(font)
            item.setForeground(QColor("#00FF00"))

        # Update Raspotify item
        last = self.playlist.item(self.playlist.count() - 1)
        if last and last.data(Qt.UserRole) == RASPOTIFY_MARKER:
            font = last.font()
            if rasp and rasp['status'] == 'Playing':
                name = self._resolve_track(rasp.get('track_id', ''))
                last.setText(f"▶ Spotify\n {name}" if name else "▶ Spotify")
                font.setBold(True)
            elif rasp and rasp['status'] == 'Paused':
                name = self._resolve_track(rasp.get('track_id', ''))
                last.setText(f"⏸ Spotify\n {name}" if name else "⏸ Spotify")
                font.setBold(False)
            else:
                last.setText("Spotify")
                font.setBold(False)
            last.setFont(font)
            last.setForeground(QColor("#00FF00"))

    def refresh_playlist(self):
        self.playlist.clear()
        try:
            queue = self.client.playlistinfo()
            for stream in queue:
                name = stream.get('name') or stream.get('title') or "Station"
                item = QListWidgetItem(name)
                item.setSizeHint(QSize(100, 70))
                item.setData(Qt.UserRole, stream.get('pos'))
                item.setData(Qt.UserRole + 1, stream.get('id'))
                item.setData(Qt.UserRole + 2, name)
                self.playlist.addItem(item)
        except: pass
        spot = QListWidgetItem("Spotify")
        spot.setSizeHint(QSize(100, 70))
        spot.setData(Qt.UserRole, RASPOTIFY_MARKER)
        spot.setData(Qt.UserRole + 2, "Spotify")
        spot.setForeground(QColor("#00FF00"))
        self.playlist.addItem(spot)

    # ---- Raspotify (file-based) helpers ----

    def _resolve_track(self, track_id):
        if not track_id:
            return ''
        if track_id in self._track_cache:
            return self._track_cache[track_id]
        try:
            url = SPOTIFY_EMBED_URL.format(track_id)
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            # Extract track title from first link, artist from second link
            links = re.findall(r'<a[^>]*>([^<]+)</a>', html)
            title = ''
            artist = ''
            for link in links:
                if not title and link.strip() not in ('', 'Preview'):
                    title = link.strip()
                elif title and link.strip() not in ('', 'Preview', title):
                    artist = link.strip()
                    break
            if artist and title:
                name = f"{artist} \u2014 {title}"
            elif title:
                name = title
            else:
                name = ''
            self._track_cache[track_id] = name
            return name
        except:
            return ''

    def _get_raspotify_status(self):
        try:
            with open(RASPOTIFY_STATUS_FILE, 'r') as f:
                data = json.load(f)
            return data if data.get('status') else None
        except:
            return None

    def _raspotify_stop(self):
        try:
            subprocess.run(
                ['systemctl', '--user', 'stop', 'raspotify'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=5
            )
            try: os.remove(RASPOTIFY_STATUS_FILE)
            except OSError: pass
        except: pass

    def _raspotify_start(self):
        try:
            subprocess.Popen(
                ['systemctl', '--user', 'start', 'raspotify'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except: pass

    # ---- Playback control ----

    def toggle_playback(self):
        mpd_playing = False
        try:
            mpd_playing = self.client.status().get('state') == 'play'
        except: pass

        rasp = self._get_raspotify_status()
        rasp_playing = rasp and rasp['status'] == 'Playing'

        if mpd_playing or rasp_playing:
            if mpd_playing:
                try: self.client.stop()
                except: pass
            if rasp_playing:
                self._raspotify_stop()
        else:
            selected = self.playlist.currentItem()
            if selected and selected.data(Qt.UserRole) != RASPOTIFY_MARKER:
                self._raspotify_stop()
                try: self.client.play(selected.data(Qt.UserRole))
                except: pass
            elif not selected:
                try: self.client.play()
                except: pass

    def play_selected(self, item):
        if item.data(Qt.UserRole) == RASPOTIFY_MARKER:
            pass  # Spotify playback is controlled from the Spotify app
        else:
            self._raspotify_stop()
            try: self.client.play(item.data(Qt.UserRole))
            except: pass

    def _ensure_raspotify_running(self):
        """Make sure raspotify is running so Spotify Connect can find it."""
        try:
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', 'raspotify'],
                capture_output=True, text=True, timeout=2
            )
            if result.stdout.strip() != 'active':
                self._raspotify_start()
        except: pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.BlankCursor)
    window = RadioController()
    window.showFullScreen()
    sys.exit(app.exec_())
