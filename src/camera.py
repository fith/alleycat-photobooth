#!/usr/bin/env python3
"""
Camera functionality for the Alleycat Photobooth.
Handles video recording and processing.
"""

import os
import time
from datetime import datetime
import ffmpeg
from logit import log
from settings import load_settings

# Global state
recording = False
stream_process = None

# Constants
VIDEO_DIR_IN = '/data/videos/in'
VIDEO_DIR_PROC = '/data/videos/processing'
VIDEO_DIR_OUT = '/data/videos/out'

def record_video(player_data=None):
    """Record a video with the webcam"""
    global recording, stream_process
    
    if recording:
        log("Already recording")
        return False
    
    try:
        recording = True
        log("Starting video recording")
        
        # Load settings
        settings = load_settings(force_reload=True)
        device = settings.get('webcam_device', '/dev/video0')
        resolution = settings.get('webcam_resolution', '1280x720')
        rotation = settings.get('webcam_rotation', 0)
        duration = settings.get('video_duration', 5)  # Default 5 seconds
        
        # Generate filename
        if player_data:
            filename = f"{player_data['role']}-{player_data['name']}-{player_data['neoId']}.mp4"
        else:
            filename = f"video-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"
        
        output_path = os.path.join(VIDEO_DIR_IN, filename)
        
        # Create output directory if it doesn't exist
        os.makedirs(VIDEO_DIR_IN, exist_ok=True)
        
        # Build FFmpeg command
        stream = ffmpeg.input(device, s=resolution, framerate=30)
        if rotation:
            stream = stream.filter('transpose', rotation)
        
        stream = stream.output(
            output_path,
            vcodec='h264_v4l2m2m',
            pix_fmt='yuv420p',
            t=duration + 3,  # Add 3 second buffer
            movflags='+faststart'
        )
        
        # Run the command
        stream.run(capture_stdout=True, capture_stderr=True)
        log(f"Video recorded successfully: {filename}")
        return filename
        
    except ffmpeg.Error as e:
        log(f"Error recording video: {e.stderr.decode()}")
        return False
    except Exception as e:
        log(f"Error recording video: {e}")
        return False
    finally:
        recording = False
        if stream_process:
            try:
                stream_process.terminate()
                stream_process.wait(timeout=1)
            except:
                pass
            stream_process = None


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