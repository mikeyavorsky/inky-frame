# boot.py - runs automatically on every power-up / wake, before main.py.
#
# Rolls back a previous update that booted but never confirmed itself (see
# ota.mark_boot_ok). Runs offline so a bad update that breaks WiFi can still
# be undone. Resets if it rolls back.
#
# WiFi and the OTA check itself happen in main.py - the Inky Frame deep-sleeps
# between cycles, so each wake naturally re-runs main.py with a fresh OTA poll.

import ota
ota.confirm_or_rollback()
# Execution continues into main.py
