# Gym Scanner Daemon (Raspberry Pi)

Headless Python 3.11 daemon for two QR scanners (IN/OUT) on Raspberry Pi. Reads USB HID keyboards or serial scanners, maps them to turnstile directions, and calls backend endpoints `/api/scan/in` and `/api/scan/out` with `X-TURNSTILE-API-KEY`.

## Configuration (env or `.env`)
- `BACKEND_BASE_URL` (required) – e.g. `https://gym-api.example.com`
- `TURNSTILE_API_KEY` (required)
- `SCANNER_IN_DEVICE` (required) – e.g. `/dev/input/by-id/usb-XYZ-event-kbd`
- `SCANNER_OUT_DEVICE` (required) – e.g. `/dev/input/by-id/usb-ABC-event-kbd`
- `SCANNER_IN_MODE` (optional, default `hid`) – `hid` or `serial`
- `SCANNER_OUT_MODE` (optional, default `hid`) – `hid` or `serial`
- `DEVICE_ID_IN` (optional, default `in-1`)
- `DEVICE_ID_OUT` (optional, default `out-1`)
- `LOG_PATH` (optional) – default `/var/log/gym-scanner-daemon.log`
- `LOG_LEVEL` (optional) – `INFO` default
- `REQUEST_TIMEOUT` (optional) – seconds, default `5.0`
- `RETRY_ATTEMPTS` / `RETRY_BACKOFF` (optional) – default `3` / `0.5` (backoff sequence 0.5s, 1.5s)

## Install dependencies (Raspberry Pi)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scanner_daemon/requirements.txt
```

## Run
```bash
source .venv/bin/activate
python scanner_daemon/main.py
```

## Systemd service (example)
`/etc/systemd/system/gym-scanner-daemon.service`:
```
[Unit]
Description=Gym Scanner Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/GymScanner
EnvironmentFile=/home/pi/GymScanner/.env
ExecStart=/home/pi/GymScanner/.venv/bin/python -m scanner_daemon.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Reload and enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gym-scanner-daemon.service
```

## Logs
- File: `/var/log/gym-scanner-daemon.log` (rotation 5 MB, 3 backups)
- Tokens are masked to first 4 characters.
