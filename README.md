# Raspberry Pi MPD Touch Radio

A lightweight, touch-optimized Python UI for controlling an MPD (Music Player Daemon) server. Designed specifically for 3.5" Raspberry Pi touchscreens (480x320 or 320x240).

---

## 1. System Prerequisites

Before setting up the UI, you must install the MPD server, the MPC controller client, and the necessary Python/X11 dependencies on your Raspberry Pi OS (Desktop version).

Run the following commands:

    sudo apt update
    sudo apt install mpd mpc python3-mpd2 python3-pyqt5 x11-xserver-utils -y

---

## 2. Project Setup

### Create Directory and Environment
On newer Raspberry Pi OS versions (like Bookworm), you must use a Virtual Environment that can access system-level packages to avoid "externally-managed-environment" errors.

    mkdir ~/pi-radio && cd ~/pi-radio
    python3 -m venv --system-site-packages radio_env
    cd -

### Copy the radio_ui.py script into the ~/pi-radio
    cp radio_ui.py ~/pi-radio

---

## 3. MPD Configuration

MPD needs a list of stations to play. You can add your favorite internet radio streams to the MPD queue using the mpc tool:

    mpc add http://your-favorite-stream-url.mp3
    mpc add http://another-radio-station.com/stream

To verify they are added, run:

    mpc playlist

---

## 4. Service Installation (Auto-Start)

To make the UI start automatically on the local display when the Pi boots into the desktop, create a systemd service file:

    sudo nano /etc/systemd/system/radio_ui.service

Paste the following configuration into that file:

    [Unit]
    Description=Pi Radio Touch UI
    After=network.target mpd.service

    [Service]
    Type=simple
    User=pi
    Environment=DISPLAY=:0
    Environment=XAUTHORITY=/home/pi/.Xauthority
    ExecStart=/home/pi/pi-radio/radio_env/bin/python3 /home/pi/pi-radio/radio_ui.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=graphical.target

Enable and start the service:

    sudo systemctl daemon-reload
    sudo systemctl enable radio_ui.service
    sudo systemctl start radio_ui.service

---

## 5. Troubleshooting

* Display Permissions: If you are testing the script via SSH and the window does not appear on the Pi screen, run the following command on the physical Pi terminal:
  DISPLAY=:0 xhost +localhost

* Resolution: The script is optimized for 480x320. If your screen is 320x240, edit radio_ui.py and change the line self.setFixedSize(480, 320) to (320, 240).

* Audio Issues: Ensure the pi user is part of the audio group. If there is no sound, check /etc/mpd.conf to verify the audio_output settings match your hardware.

