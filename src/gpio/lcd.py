#!/usr/bin/env python3
"""
LCD display control for the photobooth.
"""

from RPLCD.i2c import CharLCD
from common.logit import get_logger, log

# Get logger
logger = get_logger(__name__)

def init_lcd():
    """Initialize the LCD display"""
    try:
        # Initialize LCD with PCF8574 I2C backpack
        # lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2)
        lcd = CharLCD('PCF8574', 0x27)
        return lcd
    except Exception as e:
        log(f"Error initializing LCD: {e}")
        return None

def set_lcd_text(line1, line2):
    """Set text on the LCD display"""
    lcd = init_lcd()
    if not lcd:
        return False
        
    try:
        # Clear display and set text
        lcd.clear()
        lcd.write_string(line1[:16].ljust(16))  # First line, padded to 16 chars
        lcd.cursor_pos = (1, 0)  # Move to second line
        lcd.write_string(line2[:16].ljust(16))  # Second line, padded to 16 chars
        return True
    except Exception as e:
        log(f"Error setting LCD text: {e}")
        return False