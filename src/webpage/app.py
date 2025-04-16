#!/usr/bin/env python3
"""
Web server for the Photobooth application.
Provides web interface for webcam preview and video recording.
"""

from flask import Flask, request, jsonify, render_template, send_from_directory, flash, redirect, url_for
import os
import json
import requests
from datetime import datetime
import time
from common.logit import get_logger, log

# Get logger
logger = get_logger(__name__)

# Create Flask application
app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for flash messages

# Directory for data storage
DATA_DIR = "/data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
VIDEOS_DIR = os.path.join(DATA_DIR, "video/in")

def load_settings():
    """Load settings from JSON file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings
        except Exception as e:
            log(f"Error loading settings: {e}")
    return {}

def save_settings(settings):
    """Save settings to JSON file"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        log(f"Error saving settings: {e}")
        return False

def get_player_from_api(player_id):
    """Get player data from the remote API"""
    settings = load_settings()
    try:
        response = requests.get(f"{settings['remote_api_url']}/api/players/{player_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            log(f"API error: {response.status_code} - {response.text}")
            return {"errors": [f"API returned status code {response.status_code}"], "data": None}
    except Exception as e:
        log(f"Error calling remote API: {e}")
        return {"errors": [str(e)], "data": None}

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/webcam')
def webcam_preview():
    """Webcam preview page"""
    try:
        with open(os.path.join(DATA_DIR, "webcam_preview.png.base64.txt"), 'r') as f:
            preview_image = f.read()
    except Exception as e:
        log(f"Error reading preview image: {e}")
        preview_image = ""
    
    return render_template('webcam.html', preview_image=preview_image)

@app.route('/player/<player_id>')
def player_info_page(player_id):
    """Player info page"""
    player_data = get_player_from_api(player_id)
    return render_template('player_info.html', player=player_data)

@app.route('/settings')
def settings():
    """Settings page"""
    settings = load_settings()
    return render_template('settings.html', settings=settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        settings = load_settings()
        for key in settings:
            if key in request.form:
                value = request.form[key]
                if key in ['webcam_rotation', 'video_duration']:
                    settings[key] = int(value)
                else:
                    settings[key] = value
        
        if save_settings(settings):
            flash('Settings saved successfully!', 'success')
        else:
            flash('Error saving settings', 'error')
    except Exception as e:
        log(f"Error updating settings: {e}")
        flash(f'Error updating settings: {str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/api/webcam/preview')
def trigger_webcam_preview():
    """Trigger webcam preview capture"""
    try:
        settings = load_settings()
        response = requests.get(f"{settings['remote_api_url']}/webcam/preview")
        if response.status_code == 200:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to capture preview"}), 500
    except Exception as e:
        log(f"Error triggering webcam preview: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/webcam/video')
def trigger_webcam_video():
    """Trigger webcam video recording"""
    try:
        settings = load_settings()
        response = requests.get(f"{settings['remote_api_url']}/webcam/video")
        if response.status_code == 200:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to record video"}), 500
    except Exception as e:
        log(f"Error triggering webcam video: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/lcd')
def lcd_endpoint():
    """Update LCD display"""
    line1 = request.args.get('line1', '')
    line2 = request.args.get('line2', '')
    
    try:
        settings = load_settings()
        response = requests.get(f"{settings['remote_api_url']}/lcd?line1={line1}&line2={line2}")
        if response.status_code == 200:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to update LCD"}), 500
    except Exception as e:
        log(f"Error updating LCD: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False) 