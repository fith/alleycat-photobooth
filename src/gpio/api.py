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
from logit import log
from lcd import set_lcd_text

# Create Flask application
app = Flask(__name__)

# Paths for scripts
LCD_SCRIPT = os.path.join(os.path.dirname(__file__), "lcd.py")

# Paths for data
DATA_DIR = "/data"

def get_container_ip_address():
    """Get the IP address of the Docker container"""
    try:
        # Get the IP address of the container
        ip_address = subprocess.check_output(['hostname', '-i']).decode('utf-8').strip()
        
        log(f"Container IP address: {ip_address}")
        return ip_address
    except Exception as e:
        log(f"Error getting container IP address: {e}")
        return None



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
    set_lcd_text("Started @", get_container_ip_address())
    # Start the app
    app.run(host='0.0.0.0', port=5000, debug=False) 