#!/usr/bin/python3
import sys
from mpd import MPDClient
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QScroller
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QFont

class RadioController(QWidget):
    def __init__(self):
        super().__init__()
        self.client = MPDClient()
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
        try:
            status = self.client.status()
            current = self.client.currentsong()
            state = status.get('state')
            current_id = current.get('id')

            # Update Main Button
            if state == 'play':
                self.btn_action.setText("■")
                self.btn_action.setStyleSheet(self.stop_style)
            else:
                self.btn_action.setText("▶")
                self.btn_action.setStyleSheet(self.play_style)

            # Update List Highlighting (Weight only)
            for i in range(self.playlist.count()):
                item = self.playlist.item(i)
                item_id = item.data(Qt.UserRole + 1)
                base_name = item.data(Qt.UserRole + 2)

                font = item.font()
                if item_id == current_id:
                    prefix = "▶ " if state == 'play' else "■ "
                    song_title = current.get('title', '...')
                    item.setText(f"{prefix}{base_name}\n {song_title}")

                    font.setBold(True)
                    item.setFont(font)
                else:
                    item.setText(base_name)
                    font.setBold(False)
                    item.setFont(font)

                # Ensure color stays consistent across all items
                item.setForeground(QColor("#00FF00"))
        except:
            try: self.client.connect("localhost", 6600)
            except: pass

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

    def toggle_playback(self):
        try:
            status = self.client.status()
            if status.get('state') == 'play':
                self.client.stop()
            else:
                selected = self.playlist.currentItem()
                if selected:
                    self.client.play(selected.data(Qt.UserRole))
                else:
                    self.client.play()
        except: pass

    def play_selected(self, item):
        try: self.client.play(item.data(Qt.UserRole))
        except: pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setOverrideCursor(Qt.BlankCursor)
    window = RadioController()
    window.showFullScreen()
    sys.exit(app.exec_())
