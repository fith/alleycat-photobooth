#!/usr/bin/env python3
"""
Simple API for hardware control in the gpio container.
Provides endpoints for LCD, webcam, and RFID operations.
"""

from flask import Flask, request, jsonify
import subprocess
import sys
import os
import time
from common.logit import get_logger, log
from common.settings import load_settings
from lcd import set_lcd_text

# Get logger
logger = get_logger(__name__)

# Create Flask application
app = Flask(__name__)

def get_hostname():
    """Get the hostname from settings.json"""
    settings = load_settings()
    return settings['hostname']

def run_command(cmd, timeout=None):
    """Run a command and return result"""
    try:
        log(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        # Log command output
        if result.stdout:
            log(f"Command stdout: {result.stdout}")
        if result.stderr:
            log(f"Command stderr: {result.stderr}")
            
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        log(f"Command timed out after {timeout} seconds")
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        log(f"Error running command: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/lcd')
def update_lcd():
    """Update LCD display"""
    line1 = request.args.get('line1', '')
    line2 = request.args.get('line2', '')
    
    if set_lcd_text(line1, line2):
        return '', 200
    else:
        return '', 500

if __name__ == '__main__':
    set_lcd_text("Started @", get_hostname())
    # Start the app
    app.run(host='0.0.0.0', port=5000, debug=False) 