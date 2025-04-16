#!/usr/bin/env python3
"""
LCD display control for the photobooth.
"""

from RPLCD.gpio import CharLCD
from common.logit import get_logger, log

# Get logger
logger = get_logger(__name__)

def init_lcd():
    """Initialize the LCD display"""
    try:
        # Initialize LCD with PCF8574 I2C backpack
        lcd = CharLCD('PCF8574', 0x27, cols=16, rows=2)
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

def main():
    """Main function for CLI usage"""
    import sys
    if len(sys.argv) != 3:
        print("Usage: python lcd.py <line1> <line2>")
        sys.exit(1)
        
    line1 = sys.argv[1]
    line2 = sys.argv[2]
    
    if set_lcd_text(line1, line2):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main() 