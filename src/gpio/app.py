#!/usr/bin/env python3
"""
Main application for the GPIO container.
Runs both the RFID reader and Flask API.
"""

import threading
import signal
import sys
from common.logit import get_logger, log
from rfid import init_rfid, scan_rfid, cleanup as rfid_cleanup
from api import app as flask_app
from lcd import set_lcd_text
from common.settings import load_settings

# Get logger
logger = get_logger(__name__)

# Global flag for controlling the RFID thread
running = True

def rfid_thread():
    """Thread function for RFID scanning"""
    reader = init_rfid()
    if not reader:
        log("Failed to initialize RFID reader")
        return

    try:
        while running:
            # Scan for RFID tags with a 1-second timeout
            uid = scan_rfid(reader, timeout=1)
            if uid:
                log(f"RFID tag detected: {uid}")
                # TODO: Handle RFID tag detection (e.g., emit socket event)
    finally:
        rfid_cleanup()

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global running
    log("Shutting down...")
    running = False
    sys.exit(0)

if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start RFID thread
    rfid_thread = threading.Thread(target=rfid_thread, daemon=True)
    rfid_thread.start()

    # Set initial LCD text
    settings = load_settings()
    set_lcd_text("Started @", settings['hostname'])

    # Start Flask app
    flask_app.run(host='0.0.0.0', port=5000, debug=False) 