#!/usr/bin/env python3
"""
Web interface for the Alleycat Photobooth.
Handles the Flask web server and API endpoints.
"""

from flask import Flask, render_template, Response, request, jsonify
import ffmpeg
import subprocess
from logit import log
from settings import load_settings, save_settings

# Global state
recording = False
stream_process = None
webcam_device = None

app = Flask(__name__)

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

# Web Interface Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        try:
            # Get form data
            settings_data = {
                'webcam_device': request.form.get('webcam_device'),
                'webcam_resolution': request.form.get('webcam_resolution'),
                'webcam_rotation': int(request.form.get('webcam_rotation', 0)),
                'video_duration': int(request.form.get('video_duration')),
                'video_framerate': int(request.form.get('video_framerate'))
            }
            
            # Save settings
            if save_settings(settings_data):
                message = {'type': 'success', 'text': 'Settings saved successfully!'}
            else:
                message = {'type': 'error', 'text': 'Failed to save settings'}
        except Exception as e:
            log(f"Error saving settings: {e}")
            message = {'type': 'error', 'text': f'Error saving settings: {str(e)}'}
    else:
        message = None
    
    # Load current settings for the form
    current_settings = load_settings()
    return render_template('settings.html', settings=current_settings, message=message)

@app.route('/preview')
def preview():
    return render_template('preview.html')

@app.route('/api/preview')
def api_preview():
    """Stream MJPEG from webcam"""
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
        # low res and bc it's just for preview
        stream = (
            ffmpeg
            .input(webcam_device, 
                   f='v4l2',
                   input_format='mjpeg',
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
                   vcodec='mjpeg',  # Use mjpeg encoding since we might have rotation
                   pix_fmt='yuvj422p',
                   q=2)  # Quality setting for mjpeg encoding
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
        return jsonify({'error': 'Failed to start webcam stream'}), 500

def run_flask():
    """Run the Flask admin interface in a separate thread"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False) 