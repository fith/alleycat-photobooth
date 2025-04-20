import os
import json
import subprocess
import base64
import time
import signal
import threading
from flask import Flask, jsonify, request, Response
from common.logit import log
from common.settings import load_settings
import ffmpeg
import requests
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Constants
DATA_DIR = "/data"
PHOTO_FILE = os.path.join(DATA_DIR, "webcam_photo.png")
PHOTO_BASE64_FILE = os.path.join(DATA_DIR, "webcam_photo.png.base64.txt")

VIDEO_DIR_STOCK = os.path.join(DATA_DIR, "videos", "stock")
VIDEO_DIR_IN = os.path.join(DATA_DIR, "videos", "in")
VIDEO_DIR_PROC = os.path.join(DATA_DIR, "videos", "proc")
VIDEO_DIR_OUT = os.path.join(DATA_DIR, "videos", "out")

# Global variables
recording = False
stream_process = None
webcam_device = None

def get_webcam_device():
    """Find the first available webcam device"""
    global webcam_device
    
    # If we already have a device, return it
    if webcam_device:
        return webcam_device
        
    # Otherwise, find a new device
    for i in range(10):  # Check up to /dev/video9
        device = f"/dev/video{i}"
        if os.path.exists(device):
            webcam_device = device
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

def update_lcd(message):
    """Update LCD display via gpio container"""
    try:
        requests.get(f'http://gpio:5000/lcd?line1={message}&line2=', timeout=1)
    except Exception as e:
        # Log the error but don't crash
        log(f"Warning: Could not update LCD: {e}")
        pass

def process_video(input_file: str, output_file: str, rotation: int = 0) -> bool:
    """
    Process a video file with optional rotation and other effects.
    Returns True if processing was successful, False otherwise.
    """
    try:
        if rotation == 0:
            # No processing needed, just move the file
            os.rename(input_file, output_file)
            return True
            
        log(f"Processing video: rotation={rotation}")
        
        # Read the input file
        stream = ffmpeg.input(input_file)
        
        # Apply rotation
        stream = stream.filter('transpose', rotation)
        
        # Encode with hardware acceleration
        process = (
            stream
            .output(output_file,
                   vcodec='h264_v4l2m2m',
                   b='2M',
                   g=30,
                   pix_fmt='yuv420p',
                   f='mp4')
            .overwrite_output()
        )
        
        # Run the processing command
        out, err = process.run(capture_stdout=True, capture_stderr=True)
        if err:
            log(f"FFmpeg processing stderr output: {err.decode()}")
        
        # Remove the input file after successful processing
        os.remove(input_file)
        return True
        
    except Exception as e:
        log(f"Error processing video: {str(e)}")
        return False

@app.route('/status')
def status():
    """Get system status including webcam information"""
    log("Status endpoint called")
    device = get_webcam_device()
    log(f"Webcam device: {device}")
    
    resolutions = get_webcam_resolutions(device) if device else []
    log(f"Supported resolutions: {resolutions}")
    
    disk_space = get_disk_space()
    samba_connected = check_samba_connection()
    
    status = {
        'webcam_found': device is not None,
        'webcam_device': device,
        'supported_resolutions': resolutions,
        'free_space': disk_space,
        'samba_connected': samba_connected
    }
    log(f"Returning status: {status}")
    
    return jsonify(status)

@app.route('/live')
def live_stream():
    """Stream video from webcam"""
    global recording, stream_process, webcam_device
    
    if recording:
        log("Camera busy - recording in progress")
        return "Camera Busy", 503
    
    # Clean up any existing stream process
    if stream_process:
        try:
            log("Terminating previous stream process")
            stream_process.terminate()
            try:
                stream_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                log("Force killing previous stream process")
                stream_process.kill()
                stream_process.wait()
        except Exception as e:
            log(f"Error cleaning up previous stream: {str(e)}")
        finally:
            stream_process = None
            # Add a small delay to ensure device is released
            time.sleep(0.5)
    
    # Use the global device instance
    if not webcam_device:
        webcam_device = get_webcam_device()
    
    if not webcam_device:
        log("No camera device found")
        update_lcd("No Camera")
        return "No camera found", 503
    
    try:
        settings = load_settings(force_reload=True)
        
        # Calculate half resolution from settings
        full_res = settings.get('webcam_resolution', '1280x720')
        width, height = full_res.split('x')
        half_res = f"{int(width)//2}x{int(height)//2}"
        
        # Get rotation from settings
        rotation = settings.get('webcam_rotation', 0)
        
        log(f"Starting video stream: device={webcam_device}, resolution={half_res}, rotation={rotation}")
        
        # Start with basic input
        stream = (
            ffmpeg
            .input(webcam_device, 
                   s=half_res,
                   framerate=5)
        )
        
        # Apply rotation if specified
        if rotation != 0:
            stream = stream.filter('transpose', rotation)
        
        # Add output settings
        stream_process = (
            stream
            .output('pipe:', 
                   format='mpjpeg',
                   vcodec='mjpeg',
                   pix_fmt='yuvj422p',
                   q=2)
            .run_async(pipe_stdout=True)
        )
        
        log("Video stream started successfully")
        
        def generate():
            global stream_process
            try:
                buffer = b''
                while True:
                    if not stream_process:
                        log("Stream process not initialized", "ERROR")
                        break
                    
                    # Read a chunk of data
                    chunk = stream_process.stdout.read(4096)  # Read 4KB at a time
                    if not chunk:
                        break
                        
                    buffer += chunk
                    
                    # Look for JPEG markers
                    start = buffer.find(b'\xff\xd8')
                    if start != -1:
                        end = buffer.find(b'\xff\xd9', start)
                        if end != -1:
                            # Found a complete JPEG frame
                            jpeg_frame = buffer[start:end+2]
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame + b'\r\n')
                            # Keep any remaining data
                            buffer = buffer[end+2:]
            except Exception as e:
                log(f"Error in stream generation: {str(e)}", "ERROR")
            finally:
                if stream_process:
                    try:
                        log("Terminating stream process in generator")
                        stream_process.terminate()
                        try:
                            stream_process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            log("Force killing stream process in generator")
                            stream_process.kill()
                            stream_process.wait()
                    except Exception as e:
                        log(f"Error terminating stream in generator: {str(e)}")
                    finally:
                        stream_process = None
        
        return Response(
            generate(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        log(f"Error starting stream: {str(e)}")
        if stream_process:
            try:
                log("Terminating stream process in error handler")
                stream_process.terminate()
                try:
                    stream_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    log("Force killing stream process in error handler")
                    stream_process.kill()
                    stream_process.wait()
            except Exception as e:
                log(f"Error terminating stream in error handler: {str(e)}")
            finally:
                stream_process = None
        update_lcd("Stream Error")
        return str(e), 500

@app.route('/video', methods=['POST'])
def video():
    """Record a video"""
    global recording, stream_process
    
    if recording:
        return jsonify({'status': 'error', 'message': 'Already recording'}), 409
    
    try:
        # Stop any active stream
        if stream_process:
            try:
                log("Terminating live stream for recording")
                stream_process.terminate()
                try:
                    stream_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    log("Force killing live stream")
                    stream_process.kill()
                    stream_process.wait()
            except Exception as e:
                log(f"Error cleaning up stream: {str(e)}")
            finally:
                stream_process = None
                # Add a small delay to ensure device is released
                time.sleep(0.5)
        
        recording = True
        update_lcd("Recording")
        
        # Load latest settings
        settings = load_settings(force_reload=True)
        device = settings['webcam_device']
        resolution = settings['webcam_resolution']
        duration = settings.get('video_duration', 5)  # Default to 5 seconds
        rotation = settings.get('webcam_rotation', 0)
        
        # Generate filename
        filename = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_file = os.path.join(VIDEO_DIR_IN, f"{filename}.mp4")
        proc_file = os.path.join(VIDEO_DIR_PROC, f"{filename}.mp4")
        output_file = os.path.join(VIDEO_DIR_OUT, f"{filename}.mp4")
        
        # Record with stream copy for maximum quality
        stream = (
            ffmpeg
            .input(device, 
                   f='v4l2',
                   input_format='mjpeg',
                   s=resolution,
                   r=30)
        )
        
        # Record the video with stream copy
        stream_process = (
            stream
            .output(input_file, 
                   t=duration + 3,  # Record 3 seconds longer to account for warm-up
                   ss=3,  # Skip first 3 seconds
                   vcodec='copy',  # Copy stream without re-encoding
                   f='mp4')
            .overwrite_output()
        )
        
        log(f"Starting video recording: device={device}, resolution={resolution}, duration={duration}s")
        
        # Run the recording command
        try:
            out, err = stream_process.run(capture_stdout=True, capture_stderr=True)
            if err:
                log(f"FFmpeg stderr output: {err.decode()}")
        except ffmpeg.Error as e:
            log(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        
        # Process the video
        if not process_video(input_file, output_file, rotation):
            # If processing fails, move input file to output directory
            os.rename(input_file, output_file)
        
        log(f"Video recorded successfully: {filename}")
        return jsonify({'status': 'success', 'filename': filename})
    except Exception as e:
        log(f"Error recording video: {str(e)}")
        # Clean up files if they exist
        for file in [input_file, proc_file]:
            if os.path.exists(file):
                os.remove(file)
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        recording = False
        update_lcd("")

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(VIDEO_DIR_STOCK, exist_ok=True)
    os.makedirs(VIDEO_DIR_IN, exist_ok=True)
    os.makedirs(VIDEO_DIR_PROC, exist_ok=True)
    os.makedirs(VIDEO_DIR_OUT, exist_ok=True)
    
    # Start the server
    app.run(host='0.0.0.0', port=5000, debug=False) 