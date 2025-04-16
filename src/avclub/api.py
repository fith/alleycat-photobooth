import os
import json
import subprocess
import base64
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from common.logit import get_logger, log
import time
from datetime import datetime
import ffmpeg

# Initialize Flask app
app = Flask(__name__)
socketio = SocketIO(app)

# Get logger
logger = get_logger(__name__)

# Constants
DATA_DIR = "/data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
PREVIEW_FILE = os.path.join(DATA_DIR, "webcam_preview.png")
PREVIEW_BASE64_FILE = os.path.join(DATA_DIR, "webcam_preview.png.base64.txt")

VIDEO_DIR_STOCK = os.path.join(DATA_DIR, "videos", "stock")
VIDEO_DIR_IN = os.path.join(DATA_DIR, "videos", "in")
VIDEO_DIR_PROC = os.path.join(DATA_DIR, "videos", "proc")
VIDEO_DIR_OUT = os.path.join(DATA_DIR, "videos", "out")

def load_settings():
    """Load settings from settings.json"""
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def get_webcam_device():
    """Find the first available webcam device"""
    for i in range(10):  # Check up to /dev/video9
        device = f"/dev/video{i}"
        if os.path.exists(device):
            return device
    return None

def get_webcam_resolutions(device):
    """Get list of supported resolutions for the webcam using ffmpeg-python"""
    try:
        # Probe the device
        probe = ffmpeg.probe(device)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        # Get available frame sizes
        resolutions = set()
        for frame_size in video_info.get('frame_sizes', []):
            if 'x' in frame_size:
                resolutions.add(frame_size)
        
        # If no frame sizes listed, use the current one
        if not resolutions and 'width' in video_info and 'height' in video_info:
            resolutions.add(f"{video_info['width']}x{video_info['height']}")
            
        return sorted(list(resolutions))
    except Exception as e:
        log(f"Error getting webcam resolutions: {str(e)}")
        return []

def get_disk_space():
    """Get free space on the data directory"""
    stat = os.statvfs(DATA_DIR)
    return stat.f_bavail * stat.f_frsize

def check_samba_connection():
    """Check if we can connect to the Samba share"""
    settings = load_settings()
    samba_share = settings.get("samba_share", "")
    if not samba_share:
        return False
    
    # TODO: Implement Samba connection check
    return True

@app.route('/status')
def status():
    """Get system status including webcam information"""
    device = get_webcam_device()
    resolutions = get_webcam_resolutions(device) if device else []
    disk_space = get_disk_space()
    samba_connected = check_samba_connection()
    
    return jsonify({
        'webcam_found': device is not None,
        'webcam_device': device,
        'supported_resolutions': resolutions,
        'free_space': disk_space,
        'samba_connected': samba_connected
    })

@app.route('/preview', methods=['GET'])
def preview():
    try:
        settings = load_settings()
        device = settings['webcam_device']
        resolution = settings['webcam_resolution']
        
        # Capture preview using ffmpeg-python
        stream = (
            ffmpeg
            .input(device, f='v4l2', video_size=resolution)
            .output(PREVIEW_FILE, vframes=1)
            .overwrite_output()
        )
        stream.run(capture_stdout=True, capture_stderr=True)
        
        # Read and encode image
        with open(PREVIEW_FILE, 'rb') as f:
            image_data = f.read()
        
        # Save base64 encoded image
        with open(PREVIEW_BASE64_FILE, 'w') as f:
            f.write(image_data.hex())
        
        log("Preview captured successfully")
        return jsonify({'status': 'success'})
    except ffmpeg.Error as e:
        log(f"FFmpeg error capturing preview: {e.stderr.decode()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        log(f"Error capturing preview: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/video', methods=['POST'])
def video():
    try:
        settings = load_settings()
        device = settings['webcam_device']
        resolution = settings['webcam_resolution']
        duration = settings.get('video_duration', 10)
        
        # Generate filename
        filename = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(VIDEO_DIR_IN, f"{filename}.mp4")
        
        # Record video using ffmpeg-python
        stream = (
            ffmpeg
            .input(device, f='v4l2', video_size=resolution)
            .output(output_file, t=duration, vcodec='libx264', preset='ultrafast')
            .overwrite_output()
        )
        stream.run(capture_stdout=True, capture_stderr=True)
        
        log(f"Video recorded successfully: {filename}")
        return jsonify({'status': 'success', 'filename': filename})
    except ffmpeg.Error as e:
        log(f"FFmpeg error recording video: {e.stderr.decode()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        log(f"Error recording video: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(VIDEO_DIR_STOCK, exist_ok=True)
    os.makedirs(VIDEO_DIR_IN, exist_ok=True)
    os.makedirs(VIDEO_DIR_PROC, exist_ok=True)
    os.makedirs(VIDEO_DIR_OUT, exist_ok=True)
    
    # Start the server
    socketio.run(app, host='0.0.0.0', port=5000) 