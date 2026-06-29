# inky-frame

MicroPython app for a Pimoroni Inky Frame 5.7" that shows NASA's Astronomy
Picture of the Day, refreshed every 4 hours. Supports over-the-air (OTA)
updates pulled from this repo, so you can ship fixes without physically
reflashing the device.

## Hardware

- [Pimoroni Inky Frame 5.7"](https://shop.pimoroni.com/products/inky-frame-5-7)
  (600x448 7-colour e-ink with on-board Pico W and battery holder)

Needs the [Pimoroni MicroPython build for Inky Frame](https://github.com/pimoroni/pimoroni-pico/releases)
flashed — it bundles `picographics`, `inky_frame`, `inky_helper`, and `jpegdec`.

## Files

| File | Role |
|------|------|
| `boot.py` | Runs on every wake/reset: rolls back the previous update if it never confirmed itself. Offline so a bad update that breaks WiFi can still be undone. |
| `main.py` | Connects WiFi, checks for an OTA update, then loads the app selected in `state.json` (NASA APOD by default) and deep-sleeps between refreshes. |
| `nasa_apod.py` | Fetches the daily APOD JPEG and draws it on the e-ink panel. |
| `ota.py` | Pull-based OTA updater. Stages files to `.new` names, then commits by renaming, so a dropped connection can't corrupt running code. Backs up the old version and rolls back if a new one fails to boot. |
| `manifest.json` | Version marker and the list of files an update covers. |

## Setup

1. Create your WiFi credentials file:
   ```
   # secrets.py
   WIFI_SSID     = "your-ssid"
   WIFI_PASSWORD = "your-wifi-password"
   ```
   `secrets.py` is gitignored, so it stays off the repo.
2. Edit `ota.py` and point `GITHUB_USER` / `GITHUB_REPO` at your fork.
3. Copy `boot.py`, `main.py`, `nasa_apod.py`, `ota.py`, `manifest.json`, and
   `secrets.py` onto the Inky Frame.
4. Hold buttons **A + E** while pressing Reset to enter the launcher and pick
   NASA APOD. After that, the device boots straight into the app on each wake.

## Shipping an update

1. Change the code.
2. Bump `version` in `manifest.json` and make sure `files` lists everything
   that changed.
3. Push to the branch the device polls (`main` by default).

On its next wake (every 4 hours by default, or whenever it next refreshes) the
device sees the new version, downloads the listed files, commits them, and
resets into the updated code.

### Safe updates

Two safeguards protect against a broken update:

- **Staging.** Files are downloaded to `.new` names and only swapped over the
  live files once every download succeeds, so a dropped connection mid-download
  can't leave the device running half-new code.
- **Boot confirmation / rollback.** A freshly applied update is committed but
  marked *pending*, with the previous version backed up to `.bak`. `main.py`
  calls `ota.mark_boot_ok()` once it reaches a clean running state. If a bad
  update never gets there, the next boot (`boot.py` → `ota.confirm_or_rollback()`)
  restores the backed-up version and records the failed version so it isn't
  re-applied in a loop.

If an update crashes the app while running, `main.py` falls into a recovery
path that polls for a fix and deep-sleeps, so the device keeps cycling through
boot → OTA check until a working version lands.

### Why no long-running poll loop

Unlike the pico-display app (which polls every 5 minutes while running), the
Inky Frame deep-sleeps for hours between refreshes to preserve battery. Every
wake is effectively a fresh boot through `boot.py` → `main.py`, so the OTA
check happens once per cycle without any extra polling.
