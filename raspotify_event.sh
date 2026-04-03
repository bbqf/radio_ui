#!/bin/bash
# Called by librespot via --onevent
# Writes playback state to /tmp/raspotify_status as JSON
# Known PLAYER_EVENT values: playing, paused, stopped, start, changed, volume_set

STATUS_FILE="/tmp/raspotify_status"
EVENT="${PLAYER_EVENT:-unknown}"

case "$EVENT" in
    start|playing|changed)
        echo "{\"status\": \"Playing\", \"track_id\": \"${TRACK_ID:-}\"}" > "$STATUS_FILE"
        /usr/bin/mpc stop 2>/dev/null
        ;;
    paused)
        echo "{\"status\": \"Paused\", \"track_id\": \"${TRACK_ID:-}\"}" > "$STATUS_FILE"
        ;;
    stopped)
        echo "{\"status\": \"Stopped\"}" > "$STATUS_FILE"
        ;;
    *)
        ;;
esac
