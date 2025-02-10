Small python-Script to set the URL of a Chromium Browser with MQTT

Chromium needs to be started with the option --remote-debugging-port=9222

Example for Chromium in Kiosk mode:
chromium --remote-debugging-port=9222 --remote-allow-origins=* --start-fullscreen --kiosk --force-device-scale-factor=1 --incognito --noerrdialogs --no-first-run --disk-cache-dir=/dev/null 'about:blank'
