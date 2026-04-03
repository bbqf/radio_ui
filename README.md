# Raspberry Pi MPD Touch Radio

A lightweight, touch-optimized Python UI for controlling an MPD (Music Player Daemon) server with Spotify Connect integration via Raspotify. Designed specifically for 3.5" Raspberry Pi touchscreens (480x320 or 320x240).

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

---

## 6. Spotify Connect (Raspotify) Integration

The UI supports displaying and controlling Spotify Connect playback via a local [Raspotify](https://github.com/dtcooper/raspotify) instance. A "Spotify" entry appears as the last item in the playlist and shows the currently playing track (artist and title) when Spotify is active.

### How It Works

- Raspotify runs [librespot](https://github.com/librespot-org/librespot) as a user-level systemd service, making the Pi visible as a Spotify Connect device.
- Librespot's `--onevent` hook calls a shell script (`raspotify_event.sh`) on playback events, which writes the current state and track ID to `/tmp/raspotify_status`.
- The Python UI reads that file every second and displays the playback state. Track names (artist and title) are resolved via Spotify's public embed page and cached in memory.

### Mutual Exclusion

Only one audio source plays at a time:

- **Spotify starts while radio is playing**: The event script runs `mpc stop` to stop MPD. The UI also enforces this in its update loop as a fallback.
- **Radio station selected while Spotify is playing**: The UI stops the raspotify service (`systemctl --user stop raspotify`) synchronously before starting MPD playback.
- **Stop button**: Stops whichever source is currently active (MPD, Spotify, or both).
- **Raspotify auto-restart**: When nothing is playing, the UI automatically restarts the raspotify service so the Pi remains discoverable on Spotify Connect.

### Setup

#### 1. Install Raspotify

Follow the [official instructions](https://github.com/dtcooper/raspotify) or install via:

    curl -sL https://dtcooper.github.io/raspotify/install.sh | sh

#### 2. User-level systemd service

Raspotify should run as a user-level systemd service (not system-level) so it has access to the session D-Bus and audio. Create `~/.config/systemd/user/raspotify.service`:

    [Unit]
    Description=Raspotify
    Wants=pulseaudio.service

    [Service]
    Restart=always
    RestartSec=10
    Environment="DEVICE_NAME=raspotify (%H)"
    Environment="BITRATE=160"
    Environment="CACHE_ARGS=--disable-audio-cache"
    Environment="VOLUME_ARGS=--enable-volume-normalisation --volume-ctrl linear --initial-volume=100"
    Environment="BACKEND_ARGS=--backend alsa"
    Environment="ONEVENT=--onevent /home/pi/pi-radio/raspotify_event.sh"
    EnvironmentFile=-/etc/default/raspotify
    ExecStart=/usr/bin/librespot --name ${DEVICE_NAME} $BACKEND_ARGS --bitrate ${BITRATE} $CACHE_ARGS $VOLUME_ARGS $ONEVENT $OPTIONS

    [Install]
    WantedBy=default.target

Enable and start:

    systemctl --user daemon-reload
    systemctl --user enable raspotify
    systemctl --user start raspotify

#### 3. Event script

Copy `raspotify_event.sh` to the Pi alongside `radio_ui.py` and make it executable:

    cp raspotify_event.sh ~/pi-radio/
    chmod +x ~/pi-radio/raspotify_event.sh

The event script handles the following librespot events:

| Event | Action |
|-------|--------|
| `start`, `playing`, `changed` | Writes `Playing` status + track ID to `/tmp/raspotify_status`, runs `mpc stop` |
| `paused` | Writes `Paused` status + track ID |
| `stopped` | Writes `Stopped` status |

#### 4. Verify

Play something from the Spotify app targeting the Pi. Then check:

    cat /tmp/raspotify_status

You should see JSON like:

    {"status": "Playing", "track_id": "34K7nU8EWQIRI93RfqhdRJ"}

The UI will display the Spotify entry as **▶ Spotify** with the resolved artist and track name below.

