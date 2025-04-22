#!/usr/bin/env python3
"""
LCD display control for the photobooth.
"""

from RPLCD.i2c import CharLCD
from logit import get_logger, log

# Get logger
logger = get_logger(__name__)

# Global LCD instance
_lcd = None

# Track last displayed text
_last_line1 = None
_last_line2 = None

def init_lcd():
    """Initialize the LCD display"""
    global _lcd
    if _lcd is not None:
        return _lcd
        
    try:
        # Initialize LCD with PCF8574 I2C backpack
        _lcd = CharLCD('PCF8574', 0x27)
        log("LCD initialized successfully")
        return _lcd
    except Exception as e:
        log(f"Error initializing LCD: {e}")
        return None

def set_lcd_text(line1, line2):
    """Set text on the LCD display. Assumes LCD is already initialized."""
    global _lcd, _last_line1, _last_line2
    
    # Early exit if no text has changed
    if line1 == _last_line1 and line2 == _last_line2:
        return True
        
    try:
        # Update line1 if it changed
        if line1 != _last_line1:
            _lcd.cursor_pos = (0, 0)  # Move to first line
            _lcd.write_string(line1[:16].ljust(16))  # First line, padded to 16 chars
            _last_line1 = line1
            
        # Update line2 if it changed
        if line2 != _last_line2:
            _lcd.cursor_pos = (1, 0)  # Move to second line
            _lcd.write_string(line2[:16].ljust(16))  # Second line, padded to 16 chars
            _last_line2 = line2
            
        return True
    except Exception as e:
        log(f"Error setting LCD text: {e}")
        return False