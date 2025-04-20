#!/usr/bin/env python3
"""
Web server for the Photobooth application.
Provides web interface for webcam preview and video recording.
"""

from flask import Flask, request, jsonify, render_template, send_from_directory, flash, Response, redirect
import os
import json
import requests
from datetime import datetime
import time
from common.logit import get_logger, log
from common.settings import load_settings, save_settings

DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Get logger
logger = get_logger(__name__)

# Create Flask application
app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for flash messages

# Directory for data storage
DATA_DIR = "/data"
VIDEOS_DIR = os.path.join(DATA_DIR, "video/in")

def get_player_from_api(player_id):
    """Get player data from the remote API"""
    settings = load_settings()
    try:
        response = requests.get(f"{settings['remote_api_url']}/players/{player_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('errors'):
                log(f"API returned errors: {data['errors']}")
                return None
            player_data = data.get('data', {})
            # Ensure all required fields are present
            player = {
                'id': player_data.get('id', ''),
                'name': player_data.get('name', 'Unknown'),
                'hunter': bool(player_data.get('hunter', 0)),  # Convert 1/0 to True/False
                'allegiance': player_data.get('allegiance', 0),
                'faction': player_data.get('faction', ''),
                'neoId': player_data.get('neoId', '')
            }
            return player
        else:
            log(f"API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log(f"Error calling remote API: {e}")
        return None

@app.route('/')
def index():
    """Main page"""
    settings = load_settings()
    return render_template('index.html', settings=settings)

@app.route('/webcam')
def webcam_preview():
    """Webcam preview page"""
    return render_template('webcam.html')

@app.route('/player/lookup')
def player_lookup():
    """Webcam preview page"""
    return render_template('player_lookup.html')

@app.route('/player/<player_id>')
def player_info_page(player_id):
    """Player info page"""
    player_data = get_player_from_api(player_id)
    return render_template('player_info.html', player=player_data)

@app.route('/settings')
def settings():
    """Settings page"""
    settings = load_settings(force_reload=True)
    return render_template('settings.html', settings=settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        settings = load_settings(force_reload=True)
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
    
    return redirect('/settings')

@app.route('/api/webcam/preview')
def webcam_preview_proxy():
    """Proxy the MJPEG stream from avclub"""
    try:
        response = requests.get('http://avclub:5000/live', stream=True)
        return Response(
            response.iter_content(chunk_size=1024),
            content_type=response.headers['content-type']
        )
    except requests.exceptions.RequestException as e:
        log(f"Error proxying webcam stream: {str(e)}")
        return "Error loading webcam feed", 500

@app.route('/record')
def record_video():
    """Trigger video recording and redirect to index"""
    try:
        # Call avclub service to record video
        response = requests.post('http://avclub:5000/video')
        if response.status_code == 200:
            flash('Video recording started successfully!', 'success')
        else:
            flash('Error starting video recording', 'error')
    except Exception as e:
        log(f"Error recording video: {str(e)}")
        flash('Error starting video recording', 'error')
    
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=DEBUG) 