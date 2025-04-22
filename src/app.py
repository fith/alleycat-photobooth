#!/usr/bin/env python3
"""
Main application for the Alleycat Photobooth.
Handles RFID reading, button control, video recording, and state management.
"""

import os
import time
import csv
from datetime import datetime
import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import ffmpeg
from logit import log, DEBUG
from settings import load_settings, save_settings
import threading
from gpio import init_gpio, cleanup, BUTTON_PIN, BUTTON_LED_PIN, STAGE_LEDS
from led import turn_on_all_leds, turn_on_stage_led, turn_on_button_led, turn_off_button_led
from rfid import scan_rfid
from lcd import init_lcd, set_lcd_text
from web import run_flask

# Global state
current_stage = 'init'
last_state_change = time.time()
last_button_state = GPIO.HIGH  # Initialize to HIGH (not pressed)
button_press_time = 0
player_data = None
button_timeout = None
recording = False

# Constants
BUTTON_HOLD_TIME = 0.5  # seconds
STARTUP_TIMEOUT = 30  # seconds

def check_button_press():
    """Check for button press and return True if button is pressed"""
    return GPIO.input(BUTTON_PIN) == GPIO.LOW

def handle_init_state():
    """Handle the initialization state - runs only once at application start"""
    log("Entering init state")
    
    # Initialize GPIO
    log("Initializing GPIO...")
    gpio_initialized = init_gpio()
    
    if not gpio_initialized:
        log("Failed to initialize GPIO, staying in init state")
        set_lcd_text("GPIO Init Failed", "Check Connections")
        return 'init'
    
    log("GPIO initialized successfully")
    
    # Initialize LCD
    log("Initializing LCD...")
    if not init_lcd():
        log("Failed to initialize LCD, staying in init state")
        return 'init'
    
    log("LCD initialized successfully")
    set_lcd_text("Initializing...", "Please Wait")
    
    # Set up button interrupt
    try:
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_callback, bouncetime=300)
        log("Button detection enabled")
    except Exception as e:
        log(f"Warning: Failed to set up button detection: {e}")
        log("Continuing without button detection")
    
    # Start Flask web server in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    log("Flask thread started")
    
    # Wait a few seconds to ensure everything is stable
    log("Waiting for hardware to stabilize...")
    time.sleep(3)
    
    # Initialization complete, move to startup state
    log("Init complete, moving to startup state")
    set_lcd_text("Init Complete", "Starting Up")
    return 'startup'

def handle_startup_state():
    """Handle startup state"""
    global current_stage, last_state_change

    turn_on_all_leds()
    
    # Check for button press
    if check_button_press():
        log("Button pressed, moving to ready state")
        current_stage = 'ready'
        last_state_change = time.time()
        return 'ready'
    
    # Update LCD with startup message
    set_lcd_text("Alleycat", "Photobooth")
    
    # If we've been in startup state for too long, move to ready anyway
    if time.time() - last_state_change > STARTUP_TIMEOUT:
        log("Startup timeout reached, moving to ready state")
        current_stage = 'ready'
        last_state_change = time.time()
        return 'ready'
    
    return 'startup'

def handle_rfid_wait_state():
    """Handle the RFID wait state"""
    log("Entering rfid_wait state")
    set_lcd_text("Scan RFID Band", "")
    turn_on_stage_led('green')
    
    data = scan_rfid()
    if data:
        log(f"RFID band scanned: {data}")
        return 'button_wait', data, time.time() + 30
    
    log("No RFID band detected, staying in rfid_wait")
    return 'rfid_wait', None, None

def handle_button_wait_state(player_data, button_timeout):
    """Handle the button wait state"""
    log("Entering button_wait state")
    name = player_data.get('name', 'Unknown')
    if len(name) > 16:  # Truncate long names
        name = name[:13] + "..."
    set_lcd_text("Press Button", name)
    turn_on_stage_led('yellow')
    turn_on_button_led()
    
    if time.time() >= button_timeout:
        log("Button wait timeout, transitioning to rfid_wait")
        return 'rfid_wait', None, None
    
    if check_button_press():
        log("Button pressed, starting recording")
        return 'recording', player_data, None
    
    return 'button_wait', player_data, button_timeout

def handle_recording_state(player_data):
    """Handle the recording state"""
    log("Entering recording state")
    set_lcd_text("Recording...", "")
    turn_on_stage_led('red')
    turn_off_button_led()
    
    if record_video():
        log("Video recorded successfully, transitioning to processing")
        return 'processing', player_data
    
    log("Video recording failed, transitioning to rfid_wait")
    return 'rfid_wait', None

def handle_processing_state(player_data):
    """Handle the processing state"""
    log("Entering processing state")
    set_lcd_text("Processing...", "")
    turn_on_stage_led('blue')
    
    # TODO: Process and upload video
    
    log("Processing complete, transitioning to rfid_wait")
    return 'rfid_wait', None

def state_machine():
    """Main state machine loop"""
    global current_stage, player_data, button_timeout
    
    # Track if initialization has been handled
    init_handled = False
    
    log("Starting state machine")
    
    while True:
        # Handle each state
        if current_stage == 'init':
            if not init_handled:
                current_stage = handle_init_state()
                init_handled = True
            else:
                # Stay in init state for testing
                log("Staying in init state")
                time.sleep(1)
            
        elif current_stage == 'startup':
            current_stage = handle_startup_state()
            
        elif current_stage == 'rfid_wait':
            current_stage, player_data, button_timeout = handle_rfid_wait_state()
            
        elif current_stage == 'button_wait':
            current_stage, player_data, button_timeout = handle_button_wait_state(player_data, button_timeout)
            
        elif current_stage == 'recording':
            current_stage, player_data = handle_recording_state(player_data)
            
        elif current_stage == 'processing':
            current_stage, player_data = handle_processing_state(player_data)
        
        time.sleep(0.1)

def button_callback(channel):
    """Handle button press"""
    global current_stage, button_timeout
    
    # Ignore button presses during startup
    if current_stage == 'startup':
        return
        
    if current_stage == 'button_wait' and button_timeout and time.time() < button_timeout:
        current_stage = 'recording'
        turn_off_button_led()  # Only turn off button LED when moving to recording state
        turn_on_stage_led("red")
        
        # Record video
        if record_video():
            current_stage = 'processing'
            
            # TODO: Process and upload video
            
            # Reset to initial state
            current_stage = 'rfid_wait'
            player_data = None
            button_timeout = None

if __name__ == '__main__':
    try:
        # Start in initialization state
        current_stage = 'init'
        state_machine()
        
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Clean up GPIO if it was initialized
        cleanup() 