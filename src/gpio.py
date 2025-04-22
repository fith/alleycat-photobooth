#!/usr/bin/env python3
"""
GPIO control for the photobooth.
"""

import RPi.GPIO as GPIO
from logit import get_logger, log

# Get logger
logger = get_logger(__name__)

# GPIO Pin Assignments (BCM mode)
# All pins are referenced by their BCM number
BUTTON_PIN = 16        # Button input
BUTTON_LED_PIN = 20    # Button LED

# Stage LED pins
STAGE_LEDS = {
    'green': 21,   # Green LED
    'yellow': 23,  # Yellow LED (Physical pin 16)
    'red': 15,     # Red LED (Physical pin 10)
    'blue': 24     # Blue LED (Physical pin 18)
}

# Global state
gpio_initialized = False

def init_gpio():
    """Initialize GPIO pins"""
    global gpio_initialized
    if gpio_initialized:
        return True
        
    try:
        # Disable GPIO warnings
        GPIO.setwarnings(False)
        
        # Set GPIO mode to BCM
        GPIO.setmode(GPIO.BCM)
        
        # Setup button pin
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup LED pins
        GPIO.setup(BUTTON_LED_PIN, GPIO.OUT)
        GPIO.output(BUTTON_LED_PIN, GPIO.LOW)
        log(f"Button LED pin {BUTTON_LED_PIN} set to output and LOW")
        
        for color, pin in STAGE_LEDS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            log(f"{color} LED pin {pin} set to output and LOW")
            # Verify the pin state
            if GPIO.input(pin) != GPIO.LOW:
                log(f"Warning: {color} LED pin {pin} is not LOW after initialization")
        
        gpio_initialized = True
        log("GPIO initialized successfully")
        return True
    except Exception as e:
        log(f"Warning: GPIO initialization failed: {e}")
        log("Continuing without GPIO functionality")
        return False

def cleanup():
    """Clean up GPIO resources"""
    if gpio_initialized:
        GPIO.cleanup()
        log("GPIO cleanup completed") 