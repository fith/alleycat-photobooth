import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time
import sys
import spidev
import subprocess
import urllib.parse
import os
import json
from threading import Thread

# Import from our custom logger module
from .logger import log, DEBUG

# URL of the webserver API
WEBSERVER_URL = "http://webserver:8080/api/rfid/"

# Paths for various files
LCD_COMMAND_FILE = "/data/hardware/lcd.txt"
WEBCAM_CONFIG_FILE = "/data/hardware/webcam.txt"
WEBCAM_PREVIEW_FILE = "/data/hardware/webcam_preview.jpg"
WEBCAM_TRIGGER_FILE = "/data/hardware/webcam_trigger.txt"
VIDEOS_DIR = "/data/videos"

# Ensure directories exist
os.makedirs("/data/hardware", exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Initialize LCD command file if it doesn't exist
if not os.path.exists(LCD_COMMAND_FILE):
    # Get hostname and IP for initial display
    try:
        hostname = subprocess.check_output("hostname", shell=True).decode().strip()
        ip = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True).decode().strip()
        with open(LCD_COMMAND_FILE, "w") as f:
            f.write(f"{hostname}\n{ip}")
    except Exception as e:
        with open(LCD_COMMAND_FILE, "w") as f:
            f.write("RFID Reader\nStarted")

# Initialize webcam config file if it doesn't exist
if not os.path.exists(WEBCAM_CONFIG_FILE):
    with open(WEBCAM_CONFIG_FILE, 'w') as f:
        json.dump({
            "device": "/dev/video0",
            "rotation": 0
        }, f, indent=2)

# Debounce time in seconds
DEBOUNCE_TIME = 10

# Initialize LCD display
try:
    from RPLCD.i2c import CharLCD
    import smbus2
    
    # Use the standard I2C address for the LCD
    try:
        lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
        lcd.backlight_enabled = True  # Always keep backlight on
        lcd_address = 0x27
        log("LCD initialized with address 0x27")
    except Exception as e:
        log(f"Failed to initialize LCD: {e}")
        lcd = None
        lcd_address = None
except ImportError as e:
    log(f"LCD libraries not available: {e}")
    lcd = None
    lcd_address = None

# Webcam functions
def get_webcam_device():
    """Get the webcam device path from webcam config file"""
    device = "/dev/video0"  # Default fallback
    
    try:
        if os.path.exists(WEBCAM_CONFIG_FILE):
            with open(WEBCAM_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                device = config.get("device", "/dev/video0")
                if device:
                    log(f"Using webcam device from config: {device}")
                else:
                    log("Empty webcam device in config, using default")
                    device = "/dev/video0"
        else:
            log(f"Webcam config file not found, using default: {device}")
    except Exception as e:
        log(f"Error reading webcam config file: {e}")
    
    return device

def load_webcam_config():
    """Load webcam configuration from file"""
    default_config = {
        "device": "/dev/video0",
        "rotation": 0
    }
    
    try:
        if os.path.exists(WEBCAM_CONFIG_FILE):
            with open(WEBCAM_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                log(f"Loaded webcam config: {config}")
                # Ensure device exists in config
                if "device" not in config or not config["device"]:
                    config["device"] = default_config["device"]
                # Ensure rotation exists in config
                if "rotation" not in config:
                    config["rotation"] = default_config["rotation"]
                return config
    except Exception as e:
        log(f"Error loading webcam config: {e}")
    
    # Return default config if anything fails
    return default_config

def capture_preview():
    """Capture a preview image from the webcam using v4l2-ctl"""
    config = load_webcam_config()
    device_path = config.get("device")
    rotation = int(config.get("rotation", 0))
    
    try:
        # Use v4l2-ctl to capture a single frame
        # First set format to MJPG and resolution
        format_cmd = [
            "v4l2-ctl",
            "--device", device_path,
            "--set-fmt-video=width=1280,height=720,pixelformat=MJPG"
        ]
        
        subprocess.run(format_cmd, check=True)
        
        # Capture a single frame to file
        capture_cmd = [
            "v4l2-ctl",
            "--device", device_path,
            "--stream-mmap",
            "--stream-count=1",
            "--stream-to=" + WEBCAM_PREVIEW_FILE
        ]
        
        result = subprocess.run(capture_cmd, check=True)
        
        # Handle rotation if needed using jpegtran (assumes available in system)
        if rotation > 0:
            # Create a temporary file for the rotated image
            temp_file = WEBCAM_PREVIEW_FILE + ".tmp"
            
            # Map rotation value to jpegtran rotation argument
            rotate_arg = ""
            if rotation == 90:
                rotate_arg = "90"
            elif rotation == 180:
                rotate_arg = "180"
            elif rotation == 270:
                rotate_arg = "270"
            
            if rotate_arg:
                # Try to use a simple rotation tool if available
                try:
                    rotation_cmd = f"jpegtran -rotate {rotate_arg} -outfile {temp_file} {WEBCAM_PREVIEW_FILE}"
                    subprocess.run(rotation_cmd, shell=True, check=True)
                    # Replace original with rotated file
                    os.rename(temp_file, WEBCAM_PREVIEW_FILE)
                except:
                    log(f"Warning: Rotation tool not available, image will not be rotated")
        
        log(f"Preview saved to {WEBCAM_PREVIEW_FILE}")
        return True
    
    except Exception as e:
        log(f"Error capturing preview: {e}")
        return False

def capture_video(filename):
    """Capture a 5-second video from the webcam using v4l2-ctl"""
    config = load_webcam_config()
    device_path = config.get("device")
    
    # Ensure filename is safe
    safe_filename = os.path.basename(filename)
    if not safe_filename.endswith('.mjpg'):
        safe_filename += '.mjpg'
    
    output_path = os.path.join(VIDEOS_DIR, safe_filename)
    
    try:
        # Set format first
        format_cmd = [
            "v4l2-ctl",
            "--device", device_path,
            "--set-fmt-video=width=1280,height=720,pixelformat=MJPG"
        ]
        
        subprocess.run(format_cmd, check=True)
        
        # Capture video frames (5 seconds at approximately 30fps = 150 frames)
        capture_cmd = [
            "v4l2-ctl",
            "--device", device_path,
            "--stream-mmap",
            "--stream-count=150",
            "--stream-to=" + output_path
        ]
        
        result = subprocess.run(capture_cmd, check=True)
        
        log(f"Video saved to {output_path}")
        return True, output_path
    
    except Exception as e:
        log(f"Error capturing video: {e}")
        return False, None

def display_message(line1, line2=""):
    """Display a message on the LCD display"""
    if lcd is None:
        log(f"LCD not available for message display: {line1} / {line2}")
        return
    
    try:
        lcd.clear()
        lcd.write_string(line1[:16])  # Limit to 16 chars
        if line2:
            lcd.cursor_pos = (1, 0)
            lcd.write_string(line2[:16])
        log(f"LCD display: '{line1}' / '{line2}'")
    except Exception as e:
        log(f"Error displaying message on LCD: {e}")

def lcd_monitor_thread():
    """Thread function to monitor the LCD command file and update display"""
    last_modified_time = 0
    last_content = None
    
    while True:
        try:
            # Check if file exists
            if os.path.exists(LCD_COMMAND_FILE):
                # Get file modification time
                mod_time = os.path.getmtime(LCD_COMMAND_FILE)
                
                # Only read file if it has been modified
                if mod_time > last_modified_time:
                    with open(LCD_COMMAND_FILE, "r") as f:
                        lines = f.readlines()
                    
                    # Process the content - first two lines only
                    line1 = lines[0].strip()[:16] if len(lines) > 0 else ""
                    line2 = lines[1].strip()[:16] if len(lines) > 1 else ""
                    
                    # Only update display if content has changed
                    content = f"{line1}\n{line2}"
                    if content != last_content:
                        display_message(line1, line2)
                        log(f"Updated LCD from file: '{line1}' / '{line2}'")
                        last_content = content
                    
                    last_modified_time = mod_time
        except Exception as e:
            log(f"Error in LCD monitor thread: {e}")
        
        # Check file every second
        time.sleep(1)

def webcam_trigger_thread():
    """Thread function to monitor the webcam trigger file"""
    last_processed_time = 0
    
    while True:
        try:
            # Check if trigger file exists
            if os.path.exists(WEBCAM_TRIGGER_FILE):
                # Get file stats
                file_stat = os.stat(WEBCAM_TRIGGER_FILE)
                mod_time = file_stat.st_mtime
                file_size = file_stat.st_size
                
                # Only process if file has been modified and has content
                if mod_time > last_processed_time and file_size > 0:
                    with open(WEBCAM_TRIGGER_FILE, 'r') as f:
                        trigger = f.read().strip()
                    
                    log(f"Processing webcam trigger: {trigger}")
                    
                    # Clear file immediately to prevent repeated processing
                    with open(WEBCAM_TRIGGER_FILE, 'w') as f:
                        f.write("")
                    
                    # Process trigger based on format
                    if trigger.startswith("preview:"):
                        success = capture_preview()
                        log(f"Preview capture result: {'Success' if success else 'Failed'}")
                        display_message("Webcam Preview", "Captured" if success else "Failed")
                    
                    elif trigger.startswith("video:"):
                        parts = trigger.split(":", 2)
                        if len(parts) >= 2:
                            filename = parts[1]
                            success, path = capture_video(filename)
                            log(f"Video capture result: {'Success' if success else 'Failed'}")
                            display_message("Video Captured" if success else "Video Failed", 
                                          os.path.basename(path)[:16] if success else "")
                    
                    last_processed_time = mod_time
            
            # Sleep for a short time to avoid high CPU usage
            time.sleep(0.5)
            
        except Exception as e:
            log(f"Error in webcam trigger thread: {e}")
            time.sleep(1)  # Longer sleep on error

def main():
    log("Starting RC522 RFID Reader Test...")
    log("Press Ctrl+C to exit")
    
    # Write LCD status info to the command file
    with open(LCD_COMMAND_FILE, "w") as f:
        f.write("RFID Reader\nStarting...")
    
    # Start the LCD monitor thread
    lcd_thread = Thread(target=lcd_monitor_thread, daemon=True)
    lcd_thread.start()
    log("LCD monitor thread started")
    
    # Start the webcam trigger thread
    trigger_thread = Thread(target=webcam_trigger_thread, daemon=True)
    trigger_thread.start()
    log("Webcam trigger thread started")
    
    # Create an empty trigger file if it doesn't exist
    if not os.path.exists(WEBCAM_TRIGGER_FILE):
        with open(WEBCAM_TRIGGER_FILE, 'w') as f:
            f.write("")
    
    # Display LCD info
    if lcd:
        log(f"LCD display available at address 0x{lcd_address:02X}")
        display_message("RFID Reader", "Starting...")
    else:
        log("LCD display not available")
    
    # Set GPIO mode (already set at the beginning)
    GPIO.setwarnings(DEBUG)
    log(f"GPIO warnings set according to DEBUG flag")
    
    # Explicitly configure RST pin with pull-up
    GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)
    log(f"RST pin (GPIO {RST_PIN}) configured with pull-up")
    
    # First, test SPI communication directly
    test_spi()
    
    try:
        # Try to initialize MFRC522 on both SPI devices
        reader, spi_device = try_both_spi_devices()
        
        if reader is None:
            log("Failed to initialize RC522 on any SPI device")
            display_message("RFID ERROR", "No reader found")
            with open(LCD_COMMAND_FILE, "w") as f:
                f.write("RFID ERROR\nNo reader found")
            return
        
        log(f"RC522 Reader initialized with RST on GPIO {RST_PIN}")
        log(f"SPI configured on bus 0, device {spi_device}")
        log(f"MOSI: GPIO 10, MISO: GPIO 9, SCLK: GPIO 11, SDA: GPIO {8 if spi_device == 0 else 7}")
        
        # Configure antenna gain for optimal reading
        reader.AntennaOn()
        
        # Update LCD with ready status
        with open(LCD_COMMAND_FILE, "w") as f:
            f.write("RFID Reader\nReady")
        
        log("Starting continuous card scanning...")
        log("Press Ctrl+C to exit")
        log(f"Webserver notifications will be sent to {WEBSERVER_URL}")
        log(f"Debounce time: {DEBOUNCE_TIME} seconds")
        
        # Track the last seen card to avoid duplicate logs
        last_seen_uid = None
        # Track the last notified card for debouncing
        last_notified = {
            "uid": None,
            "time": 0
        }
        
        while True:
            # Reset the antenna gain for optimal reading distance
            reader.AntennaOn()
            
            # Look for cards
            (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
            
            if status == reader.MI_OK:
                # Get the UID of the card
                (status, uid) = reader.MFRC522_Anticoll()
                
                if status == reader.MI_OK:
                    # Format the UID for display
                    uid_str = '-'.join([f"{x:02x}" for x in uid])
                    
                    # Only log if this is a different card than the last one we saw
                    if uid_str != last_seen_uid:
                        log(f"NEOBAND detected! Type: {TagType}")
                        log(f"NEOBAND UID: {uid_str}")
                        
                        # Update LCD with card info
                        display_message("NEOBAND Detected", uid_str[:16])
                        with open(LCD_COMMAND_FILE, "w") as f:
                            f.write(f"NEOBAND Detected\n{uid_str[:16]}")
                        
                        # Check if we should notify the webserver (debounce)
                        current_time = time.time()
                        if uid_str != last_notified["uid"] or (current_time - last_notified["time"]) > DEBOUNCE_TIME:
                            if notify_webserver(uid_str):
                                last_notified["uid"] = uid_str
                                last_notified["time"] = current_time
                                log(f"Webserver notified of card {uid_str}")
                                log(f"Debouncing for {DEBOUNCE_TIME} seconds")
                        else:
                            log(f"Skipping webserver notification (debounced)")
                        
                        # Update last seen card
                        last_seen_uid = uid_str
                    
                    # Select the card
                    reader.MFRC522_SelectTag(uid)
                    
                    # Halt the card to release it
                    reader.MFRC522_StopCrypto1()
            else:
                # Reset last seen card if no card is present
                last_seen_uid = None
            
            time.sleep(0.5)  # Short delay between scans
            
    except KeyboardInterrupt:
        log("Script terminated by user")
        with open(LCD_COMMAND_FILE, "w") as f:
            f.write("RFID Reader\nStopped")
    except Exception as e:
        log(f"Fatal error: {str(e)}")
        log(f"Error type: {type(e).__name__}")
        if hasattr(e, 'args'):
            log(f"Error args: {e.args}")
            with open(LCD_COMMAND_FILE, "w") as f:
                f.write(f"RFID ERROR\n{str(e)[:16]}")
    finally:
        GPIO.cleanup()
        log("GPIO cleanup completed")

if __name__ == "__main__":
    try:
        log("Entering main function")
        main()
    except Exception as e:
        log(f"Unhandled exception: {str(e)}")
        log(f"Error type: {type(e).__name__}")
        if hasattr(e, 'args'):
            log(f"Error args: {e.args}")
        # Try to update LCD with error
        try:
            with open(LCD_COMMAND_FILE, "w") as f:
                f.write(f"Fatal Error\n{str(e)[:16]}")
        except:
            pass
        sys.exit(1)
